"""
Market monitoring service.
"""

import logging
from collections import deque
from typing import Any, Deque, Dict, List, Tuple

from .exchange import BinanceSource
from .indicators import IndicatorEngine
from .models import Candle
from .notifier import OpenClawNotifier
from .rules import RuleEngine
from .utils import safe_float

LOG = logging.getLogger(__name__)


class MonitorService:
    """Main service for monitoring and alerting on market conditions."""

    def __init__(self, cfg: Dict[str, Any], symbol: str = None, interval: str = None):
        self.cfg = cfg
        # Support both single market (old format) and multiple markets (new format)
        if "markets" in cfg:
            # New format: multiple markets
            market_cfg = next((m for m in cfg["markets"] if m["symbol"].upper() == symbol), None)
            if not market_cfg:
                raise ValueError(f"Market {symbol} not found in configuration")
            market = market_cfg
        else:
            # Old format: single market
            market = cfg["market"]
            symbol = market["symbol"].upper() if not symbol else symbol
            interval = market.get("interval", market.get("interval", "1m")) if not interval else interval

        self.symbol = symbol if isinstance(symbol, str) else market["symbol"].upper()
        self.interval = (
            interval if isinstance(interval, str) else market.get("interval", market.get("interval", "1m"))
        )
        self.max_candles = int(market.get("max_candles", 500))
        self.binance = BinanceSource(self.symbol, self.interval, market.get("backfill_limit", 500))
        self.candles: Deque[Candle] = deque(maxlen=self.max_candles)
        self.notifier = OpenClawNotifier(cfg["openclaw"])
        self.rules = RuleEngine(cfg["rules"])
        self.min_required = max(60, int(market.get("min_required_candles", 60)))

    def load_history(self) -> None:
        """Load historical candles from Binance."""
        history = self.binance.fetch_backfill()
        for candle in history:
            self.candles.append(candle)
        LOG.info("Loaded %s candles for %s %s", len(self.candles), self.symbol, self.interval)

    def _upsert_candle(self, c: Candle) -> None:
        """Update last candle or append new one."""
        if self.candles and self.candles[-1].open_time == c.open_time:
            self.candles[-1] = c
        else:
            self.candles.append(c)

    def _format_message(self, events: List[Dict[str, Any]], snap: Dict[str, float]) -> Tuple[str, str]:
        """
        Format multiple events into a single message.
        Returns: (title, body)
        """
        # Build title
        if len(events) == 1:
            title = events[0]["title"]
        else:
            title = f"多信号触发 ({len(events)}个)"

        # Build body with all event summaries
        event_details = "\n".join([f"  • {e['title']}: {e['summary']}" for e in events])

        body = (
            f"收到本地量化监控告警，请用中文给我一个简短、可执行的判断。\n\n"
            f"市场: {self.symbol}\n"
            f"周期: {self.interval}\n"
            f"触发信号 ({len(events)}个):\n"
            f"{event_details}\n\n"
            f"当前指标:\n"
            f"- close: {snap['close']:.2f}\n"
            f"- RSI14: {snap['rsi_14']:.2f}\n"
            f"- MACD: {snap['macd']:.4f}\n"
            f"- MACD signal: {snap['macd_signal']:.4f}\n"
            f"- MACD hist: {snap['macd_hist']:.4f}\n"
            f"- SMA20: {snap['sma_20']:.2f}\n"
            f"- SMA50: {snap['sma_50']:.2f}\n"
            f"- EMA21: {snap['ema_21']:.2f}\n"
            f"- Bollinger upper/mid/lower: {snap['bb_upper']:.2f} / {snap['bb_mid']:.2f} / {snap['bb_lower']:.2f}\n"
            f"- ATR14: {snap['atr_14']:.2f}\n"
            f"- Volume: {snap['volume']:.4f}\n"
            f"- Volume SMA20: {snap['volume_sma_20']:.4f}\n"
            f"- 1-bar change: {snap['close_change_1']:.2f}%\n"
            f"- 5-bar change: {snap['close_change_5']:.2f}%\n"
            f"- 15-bar change: {snap['close_change_15']:.2f}%\n\n"
            f"请在飞书群里输出：1) 发生了什么 2) 是否是好的交易机会 3) 接下来应该如何操作"
        )

        return title, body

    async def run(self) -> None:
        """Main loop: load history and stream market updates."""
        self.load_history()
        async for msg in self.binance.stream():
            if msg.get("e") != "kline":
                continue
            k = msg["k"]
            candle = Candle(
                open_time=int(k["t"]),
                close_time=int(k["T"]),
                open=safe_float(k["o"]),
                high=safe_float(k["h"]),
                low=safe_float(k["l"]),
                close=safe_float(k["c"]),
                volume=safe_float(k["v"]),
                closed=bool(k["x"]),
            )
            self._upsert_candle(candle)
            if len(self.candles) < self.min_required:
                continue
            if not candle.closed:
                continue  # Use closed candles for cleaner indicator signals.

            candles = list(self.candles)
            snap = IndicatorEngine.snapshot(candles)
            events = self.rules.evaluate(self.symbol, self.interval, candles, snap)

            # Push a single message for all triggered signals
            if events:
                # Log all triggered signals
                for event in events:
                    LOG.info("Triggered [%s] %s: %s", self.symbol, event["title"], event["summary"])

                # Format and send a single consolidated message
                title, body = self._format_message(events, snap)
                self.notifier.send(self.symbol, title, body)
