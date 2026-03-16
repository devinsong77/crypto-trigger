"""
Rule evaluation engine for trading signals.
"""

import math
from typing import Any, Dict, List, Tuple

from .indicators import IndicatorEngine
from .models import Candle
from .utils import now_ts, percent_change


class RuleEngine:
    """Evaluates trading rules against market data."""

    def __init__(self, rules: List[Dict[str, Any]]):
        self.rules = rules
        self.cooldowns: Dict[str, float] = {}

    def _cooldown_ok(self, key: str, cooldown_secs: int) -> bool:
        """Check if rule has cooled down enough."""
        last = self.cooldowns.get(key, 0.0)
        return now_ts() - last >= cooldown_secs

    def _mark_fired(self, key: str) -> None:
        """Mark a rule as just fired."""
        self.cooldowns[key] = now_ts()

    def evaluate(
        self, symbol: str, interval: str, candles: List[Candle], snap: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Evaluate all rules and return triggered events."""
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
                events.append({
                    "rule_id": rule_id,
                    "title": rule.get("title", rule_id),
                    "summary": summary,
                    "rule": rule,
                })
        return events

    def _match(
        self, rule: Dict[str, Any], candles: List[Candle], closes: List[float], snap: Dict[str, float]
    ) -> Tuple[bool, str]:
        """Match a single rule against market data."""
        rtype = rule["type"]

        if rtype == "price_change_pct":
            lookback = int(rule.get("lookback_bars", 5))
            threshold = float(rule["threshold_pct"])
            direction = rule.get("direction", "either")
            if len(closes) <= lookback:
                return False, ""
            move = percent_change(closes[-lookback - 1], closes[-1])
            if (
                (direction == "up" and move >= threshold)
                or (direction == "down" and move <= -threshold)
                or (direction == "either" and abs(move) >= threshold)
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

        if rtype == "adx_threshold":
            value = snap.get("adx_14", math.nan)
            threshold = float(rule.get("threshold", 25.0))
            direction = rule.get("direction", "above")
            if math.isnan(value):
                return False, ""
            if direction == "above" and value >= threshold:
                return True, f"ADX(14)={value:.2f}，高于 {threshold}"
            if direction == "below" and value <= threshold:
                return True, f"ADX(14)={value:.2f}，低于 {threshold}"
            return False, ""

        if rtype == "cci_threshold":
            value = snap.get("cci_20", math.nan)
            overbought = rule.get("overbought")
            oversold = rule.get("oversold")
            if math.isnan(value):
                return False, ""
            if overbought is not None and value >= float(overbought):
                return True, f"CCI(20)={value:.2f}，高于 {overbought}"
            if oversold is not None and value <= float(oversold):
                return True, f"CCI(20)={value:.2f}，低于 {oversold}"
            return False, ""

        if rtype == "stoch_cross":
            k = snap.get("sto_k", math.nan)
            d = snap.get("sto_d", math.nan)
            if math.isnan(k) or math.isnan(d):
                return False, ""
            prev_snap = IndicatorEngine.snapshot(candles[:-1]) if len(candles) > 1 else None
            if not prev_snap:
                return False, ""
            prev_k = prev_snap.get("sto_k", math.nan)
            prev_d = prev_snap.get("sto_d", math.nan)
            direction = rule.get("direction", "either")
            if direction in ("bullish", "either") and prev_k <= prev_d < k:
                return True, f"Stoch K 上穿 D ({prev_k:.2f}->{k:.2f})"
            if direction in ("bearish", "either") and prev_k >= prev_d > k:
                return True, f"Stoch K 下穿 D ({prev_k:.2f}->{k:.2f})"
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
            direction = rule.get("direction", "either")
            if direction in ("upper", "either") and close > snap["bb_upper"]:
                return True, f"收盘价 {close:.2f} 突破布林上轨 {snap['bb_upper']:.2f}"
            if direction in ("lower", "either") and close < snap["bb_lower"]:
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
