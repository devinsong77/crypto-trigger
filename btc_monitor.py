#!/usr/bin/env python3
"""
BTCUSDT monitor for OpenClaw.

What it does
- Backfills historical klines from Binance REST.
- Subscribes to Binance Spot WebSocket kline stream.
- Computes common technical indicators in pure Python:
  SMA, EMA, RSI, MACD, Bollinger Bands, ATR, volume SMA, ROC.
- Evaluates configurable alert rules.
- Triggers a local OpenClaw agent through /hooks/agent.

Dependencies:
  pip install websockets

Run:
  python btc_monitor.py --config config_default.json
"""

import argparse
import asyncio
import json
import logging
import math
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

try:
    import websockets
except ImportError:
    print("Missing dependency: websockets. Install it with: pip install websockets", file=sys.stderr)
    raise

LOG = logging.getLogger("btc_monitor")


def now_ts() -> float:
    return time.time()


def safe_float(value: Any) -> float:
    return float(value) if value is not None else math.nan


def percent_change(a: float, b: float) -> float:
    if a == 0 or math.isnan(a) or math.isnan(b):
        return math.nan
    return (b - a) / a * 100.0


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def stddev(values: List[float]) -> float:
    if len(values) < 2:
        return math.nan
    m = mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


@dataclass
class Candle:
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool = True


class IndicatorEngine:
    @staticmethod
    def sma(values: List[float], period: int) -> float:
        if len(values) < period or period <= 0:
            return math.nan
        return sum(values[-period:]) / period

    @staticmethod
    def ema_series(values: List[float], period: int) -> List[float]:
        if len(values) < period or period <= 0:
            return []
        alpha = 2.0 / (period + 1.0)
        result = [sum(values[:period]) / period]
        for v in values[period:]:
            result.append(alpha * v + (1 - alpha) * result[-1])
        return result

    @staticmethod
    def ema(values: List[float], period: int) -> float:
        series = IndicatorEngine.ema_series(values, period)
        return series[-1] if series else math.nan

    @staticmethod
    def rsi(values: List[float], period: int = 14) -> float:
        if len(values) < period + 1:
            return math.nan
        gains = []
        losses = []
        for i in range(1, period + 1):
            delta = values[i] - values[i - 1]
            gains.append(max(delta, 0.0))
            losses.append(max(-delta, 0.0))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        for i in range(period + 1, len(values)):
            delta = values[i] - values[i - 1]
            gain = max(delta, 0.0)
            loss = max(-delta, 0.0)
            avg_gain = ((avg_gain * (period - 1)) + gain) / period
            avg_loss = ((avg_loss * (period - 1)) + loss) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def macd(values: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        if len(values) < slow + signal:
            return math.nan, math.nan, math.nan
        fast_series = IndicatorEngine.ema_series(values, fast)
        slow_series = IndicatorEngine.ema_series(values, slow)
        if not fast_series or not slow_series:
            return math.nan, math.nan, math.nan
        offset = len(fast_series) - len(slow_series)
        macd_series = [fast_series[i + offset] - slow_series[i] for i in range(len(slow_series))]
        signal_series = IndicatorEngine.ema_series(macd_series, signal)
        if not signal_series:
            return math.nan, math.nan, math.nan
        macd_line = macd_series[-1]
        signal_line = signal_series[-1]
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger(values: List[float], period: int = 20, std_mult: float = 2.0) -> Tuple[float, float, float]:
        if len(values) < period:
            return math.nan, math.nan, math.nan
        window = values[-period:]
        mid = mean(window)
        sd = stddev(window)
        return mid + std_mult * sd, mid, mid - std_mult * sd

    @staticmethod
    def true_range(cur: Candle, prev_close: float) -> float:
        return max(cur.high - cur.low, abs(cur.high - prev_close), abs(cur.low - prev_close))

    @staticmethod
    def atr(candles: List[Candle], period: int = 14) -> float:
        if len(candles) < period + 1:
            return math.nan
        trs: List[float] = []
        for i in range(1, len(candles)):
            trs.append(IndicatorEngine.true_range(candles[i], candles[i - 1].close))
        if len(trs) < period:
            return math.nan
        atr = sum(trs[:period]) / period
        for tr in trs[period:]:
            atr = ((atr * (period - 1)) + tr) / period
        return atr

    @staticmethod
    def roc(values: List[float], period: int = 12) -> float:
        if len(values) <= period:
            return math.nan
        old = values[-period - 1]
        return percent_change(old, values[-1])

    @staticmethod
    def volume_sma(volumes: List[float], period: int = 20) -> float:
        return IndicatorEngine.sma(volumes, period)

    @staticmethod
    def snapshot(candles: List[Candle]) -> Dict[str, float]:
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [c.volume for c in candles]
        _ = highs, lows  # kept for symmetry and future extension

        macd_line, macd_signal, macd_hist = IndicatorEngine.macd(closes)
        bb_upper, bb_mid, bb_lower = IndicatorEngine.bollinger(closes)
        snap = {
            "close": closes[-1] if closes else math.nan,
            "sma_9": IndicatorEngine.sma(closes, 9),
            "sma_20": IndicatorEngine.sma(closes, 20),
            "sma_50": IndicatorEngine.sma(closes, 50),
            "ema_9": IndicatorEngine.ema(closes, 9),
            "ema_21": IndicatorEngine.ema(closes, 21),
            "rsi_14": IndicatorEngine.rsi(closes, 14),
            "macd": macd_line,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "bb_upper": bb_upper,
            "bb_mid": bb_mid,
            "bb_lower": bb_lower,
            "atr_14": IndicatorEngine.atr(candles, 14),
            "volume": volumes[-1] if volumes else math.nan,
            "volume_sma_20": IndicatorEngine.volume_sma(volumes, 20),
            "roc_12": IndicatorEngine.roc(closes, 12),
            "close_change_1": percent_change(closes[-2], closes[-1]) if len(closes) >= 2 else math.nan,
            "close_change_5": percent_change(closes[-6], closes[-1]) if len(closes) >= 6 else math.nan,
            "close_change_15": percent_change(closes[-16], closes[-1]) if len(closes) >= 16 else math.nan,
        }
        return snap


class OpenClawNotifier:
    def __init__(self, cfg: Dict[str, Any]):
        self.url = cfg["url"].rstrip("/")
        self.token = cfg["token"]
        self.timeout = cfg.get("timeout_seconds", 10)
        self.name = cfg.get("name", "BTCMonitor")
        self.session_key_prefix = cfg.get("session_key_prefix", "hook:market:")
        self.deliver = bool(cfg.get("deliver", True))
        self.channel = cfg.get("channel", "last")
        self.to = cfg.get("to")
        self.wake_mode = cfg.get("wake_mode", "now")
        self.model = cfg.get("model")
        self.thinking = cfg.get("thinking")
        self.ssl_context = ssl.create_default_context()

    def send(self, symbol: str, title: str, body: str) -> None:
        payload = {
            "message": body,
            "name": self.name,
            "sessionKey": f"{self.session_key_prefix}{symbol.lower()}",
            "wakeMode": self.wake_mode,
            "deliver": self.deliver,
            "channel": self.channel,
            "timeoutSeconds": self.timeout,
        }
        if self.to:
            payload["to"] = self.to
        if self.model:
            payload["model"] = self.model
        if self.thinking:
            payload["thinking"] = self.thinking

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "btc-monitor/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as resp:
                LOG.info("OpenClaw notified: %s, http=%s", title, resp.status)
        except urllib.error.HTTPError as e:
            LOG.error("OpenClaw HTTP error: %s %s", e.code, e.read().decode("utf-8", errors="ignore"))
        except Exception as e:
            LOG.exception("OpenClaw notify failed: %s", e)


class RuleEngine:
    def __init__(self, rules: List[Dict[str, Any]]):
        self.rules = rules
        self.cooldowns: Dict[str, float] = {}

    def _cooldown_ok(self, key: str, cooldown_secs: int) -> bool:
        last = self.cooldowns.get(key, 0.0)
        return now_ts() - last >= cooldown_secs

    def _mark_fired(self, key: str) -> None:
        self.cooldowns[key] = now_ts()

    def evaluate(self, symbol: str, interval: str, candles: List[Candle], snap: Dict[str, float]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        closes = [c.close for c in candles]
        for idx, rule in enumerate(self.rules):
            rule_id = rule.get("id") or f"rule_{idx}"
            cooldown = int(rule.get("cooldown_secs", 600))
            key = f"{symbol}:{interval}:{rule_id}"
            if not self._cooldown_ok(key, cooldown):
                continue
            matched, summary = self._match(rule, candles, closes, snap)
            if matched:
                self._mark_fired(key)
                events.append({"rule_id": rule_id, "title": rule.get("title", rule_id), "summary": summary, "rule": rule})
        return events

    def _match(self, rule: Dict[str, Any], candles: List[Candle], closes: List[float], snap: Dict[str, float]) -> Tuple[bool, str]:
        rtype = rule["type"]

        if rtype == "price_change_pct":
            lookback = int(rule.get("lookback_bars", 5))
            threshold = float(rule["threshold_pct"])
            direction = rule.get("direction", "either")
            if len(closes) <= lookback:
                return False, ""
            move = percent_change(closes[-lookback - 1], closes[-1])
            if (
                (direction == "up" and move >= threshold) or
                (direction == "down" and move <= -threshold) or
                (direction == "either" and abs(move) >= threshold)
            ):
                return True, f"{lookback} 根K线内价格变动 {move:.2f}%"
            return False, ""

        if rtype == "rsi_threshold":
            value = snap["rsi_14"]
            overbought = rule.get("overbought")
            oversold = rule.get("oversold")
            if overbought is not None and value >= float(overbought):
                return True, f"RSI(14)={value:.2f}，高于 {overbought}"
            if oversold is not None and value <= float(oversold):
                return True, f"RSI(14)={value:.2f}，低于 {oversold}"
            return False, ""

        if rtype == "macd_cross":
            if len(closes) < 40:
                return False, ""
            prev_snap = IndicatorEngine.snapshot(candles[:-1])
            prev_diff = prev_snap["macd"] - prev_snap["macd_signal"]
            curr_diff = snap["macd"] - snap["macd_signal"]
            direction = rule.get("direction", "either")
            if direction in ("bullish", "either") and prev_diff <= 0 < curr_diff:
                return True, f"MACD 金叉，hist={snap['macd_hist']:.4f}"
            if direction in ("bearish", "either") and prev_diff >= 0 > curr_diff:
                return True, f"MACD 死叉，hist={snap['macd_hist']:.4f}"
            return False, ""

        if rtype == "bollinger_break":
            close = snap["close"]
            if close > snap["bb_upper"]:
                return True, f"收盘价 {close:.2f} 突破布林上轨 {snap['bb_upper']:.2f}"
            if close < snap["bb_lower"]:
                return True, f"收盘价 {close:.2f} 跌破布林下轨 {snap['bb_lower']:.2f}"
            return False, ""

        if rtype == "sma_cross":
            if len(closes) < 60:
                return False, ""
            fast = int(rule.get("fast", 9))
            slow = int(rule.get("slow", 20))
            prev_fast = IndicatorEngine.sma(closes[:-1], fast)
            prev_slow = IndicatorEngine.sma(closes[:-1], slow)
            curr_fast = IndicatorEngine.sma(closes, fast)
            curr_slow = IndicatorEngine.sma(closes, slow)
            direction = rule.get("direction", "either")
            if direction in ("bullish", "either") and prev_fast <= prev_slow < curr_fast:
                return True, f"SMA{fast} 上穿 SMA{slow}"
            if direction in ("bearish", "either") and prev_fast >= prev_slow > curr_fast:
                return True, f"SMA{fast} 下穿 SMA{slow}"
            return False, ""

        if rtype == "volume_spike":
            mult = float(rule.get("multiple", 2.0))
            vsma = snap["volume_sma_20"]
            if not math.isnan(vsma) and vsma > 0 and snap["volume"] >= vsma * mult:
                return True, f"成交量 {snap['volume']:.4f}，为 20 均量的 {snap['volume']/vsma:.2f} 倍"
            return False, ""

        if rtype == "combo":
            all_of = rule.get("all_of", [])
            summaries = []
            for child in all_of:
                matched, summary = self._match(child, candles, closes, snap)
                if not matched:
                    return False, ""
                summaries.append(summary)
            return True, "；".join(summaries)

        raise ValueError(f"Unsupported rule type: {rtype}")


class BinanceSource:
    def __init__(self, symbol: str, interval: str, backfill_limit: int = 500):
        self.symbol = symbol.upper()
        self.interval = interval
        self.backfill_limit = min(int(backfill_limit), 1000)
        self.rest_base = "https://api.binance.com"
        self.ws_url = f"wss://data-stream.binance.vision/ws/{self.symbol.lower()}@kline_{self.interval}"

    def fetch_backfill(self) -> List[Candle]:
        url = (
            f"{self.rest_base}/api/v3/klines?"
            + urllib.parse.urlencode({"symbol": self.symbol, "interval": self.interval, "limit": self.backfill_limit})
        )
        req = urllib.request.Request(url, headers={"User-Agent": "btc-monitor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        candles = []
        for row in raw:
            candles.append(Candle(
                open_time=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                close_time=int(row[6]),
                closed=True,
            ))
        return candles

    async def stream(self):
        while True:
            try:
                LOG.info("Connecting Binance websocket: %s", self.ws_url)
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=60, close_timeout=10) as ws:
                    async for message in ws:
                        yield json.loads(message)
            except Exception as e:
                LOG.warning("WebSocket disconnected: %s. Reconnecting in 3s.", e)
                await asyncio.sleep(3)


class MonitorService:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        market = cfg["market"]
        self.symbol = market["symbol"].upper()
        self.interval = market["interval"]
        self.max_candles = int(market.get("max_candles", 500))
        self.binance = BinanceSource(self.symbol, self.interval, market.get("backfill_limit", 500))
        self.candles: Deque[Candle] = deque(maxlen=self.max_candles)
        self.notifier = OpenClawNotifier(cfg["openclaw"])
        self.rules = RuleEngine(cfg["rules"])
        self.min_required = max(60, int(market.get("min_required_candles", 60)))

    def load_history(self) -> None:
        history = self.binance.fetch_backfill()
        for candle in history:
            self.candles.append(candle)
        LOG.info("Loaded %s candles for %s %s", len(self.candles), self.symbol, self.interval)

    def _upsert_candle(self, c: Candle) -> None:
        if self.candles and self.candles[-1].open_time == c.open_time:
            self.candles[-1] = c
        else:
            self.candles.append(c)

    def _format_message(self, event: Dict[str, Any], snap: Dict[str, float]) -> str:
        return (
            f"收到本地量化监控告警，请用中文给我一个简短、可执行的判断。\n\n"
            f"市场: {self.symbol}\n"
            f"周期: {self.interval}\n"
            f"规则: {event['title']}\n"
            f"触发原因: {event['summary']}\n\n"
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
            f"请输出：1) 发生了什么 2) 是否值得立刻关注 3) 接下来关注哪两个价位或指标。"
        )

    async def run(self) -> None:
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
            for event in events:
                LOG.info("Triggered %s: %s", event["title"], event["summary"])
                self.notifier.send(self.symbol, event["title"], self._format_message(event, snap))


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="BTCUSDT monitor for OpenClaw")
    parser.add_argument("--config", default="config_default.json", help="Path to JSON config")
    parser.add_argument("--log-level", default="INFO", help="DEBUG / INFO / WARNING / ERROR")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    cfg = load_config(args.config)
    service = MonitorService(cfg)
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        LOG.info("Stopped by user.")


if __name__ == "__main__":
    main()
