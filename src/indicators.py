"""
Technical indicators calculation engine.
"""

import math
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import talib

from .models import Candle
from .utils import mean, percent_change, stddev


class IndicatorEngine:
    """Computes technical indicators: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ROC, Volume SMA."""

    @staticmethod
    def sma(values: List[float], period: int) -> float:
        """Simple Moving Average."""
        if period <= 0 or len(values) < period:
            return math.nan

        arr = np.asarray(values, dtype=float)
        out = talib.SMA(arr, timeperiod=period)
        result = out[-1]
        return float(result) if not np.isnan(result) else math.nan

    @staticmethod
    def ema_series(values: List[float], period: int) -> List[float]:
        """Exponential Moving Average series."""
        if period <= 0 or len(values) < period:
            return []

        arr = np.asarray(values, dtype=float)
        out = talib.EMA(arr, timeperiod=period)
        cleaned = [float(x) for x in out.tolist() if not np.isnan(x)]
        return cleaned

    @staticmethod
    def ema(values: List[float], period: int) -> float:
        """Exponential Moving Average."""
        if period <= 0:
            return math.nan

        series = IndicatorEngine.ema_series(values, period)
        return series[-1] if series else math.nan

    @staticmethod
    def rsi(values: List[float], period: int = 14) -> float:
        """Relative Strength Index."""
        if period <= 0 or len(values) < period + 1:
            return math.nan

        if len(set(values)) == 1:
            return 100.0

        arr = np.asarray(values, dtype=float)
        out = talib.RSI(arr, timeperiod=period)
        result = float(out[-1])
        return result if not np.isnan(result) else math.nan

    @staticmethod
    def macd(
        values: List[float], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[float, float, float]:
        """MACD (Moving Average Convergence Divergence)."""
        if fast <= 0 or slow <= 0 or signal <= 0 or len(values) < slow + signal:
            return math.nan, math.nan, math.nan

        arr = np.asarray(values, dtype=float)
        macd_line, signal_line, hist = talib.MACD(
            arr, fastperiod=fast, slowperiod=slow, signalperiod=signal
        )

        ml = float(macd_line[-1]) if not np.isnan(macd_line[-1]) else math.nan
        sl = float(signal_line[-1]) if not np.isnan(signal_line[-1]) else math.nan
        h = float(hist[-1]) if not np.isnan(hist[-1]) else math.nan

        return ml, sl, h

    @staticmethod
    def bollinger(
        values: List[float], period: int = 20, std_mult: float = 2.0
    ) -> Tuple[float, float, float]:
        """Bollinger Bands."""
        if period <= 0 or len(values) < period:
            return math.nan, math.nan, math.nan

        arr = np.asarray(values, dtype=float)
        upper, mid, lower = talib.BBANDS(
            arr, timeperiod=period, nbdevup=std_mult, nbdevdn=std_mult
        )

        u = float(upper[-1]) if not np.isnan(upper[-1]) else math.nan
        m = float(mid[-1]) if not np.isnan(mid[-1]) else math.nan
        l = float(lower[-1]) if not np.isnan(lower[-1]) else math.nan

        return u, m, l

    @staticmethod
    def true_range(cur: Candle, prev_close: float) -> float:
        """Calculate true range for ATR."""
        return max(
            cur.high - cur.low, abs(cur.high - prev_close), abs(cur.low - prev_close)
        )

    @staticmethod
    def atr(candles: List[Candle], period: int = 14) -> float:
        """Average True Range."""
        if period <= 0 or len(candles) < period + 1:
            return math.nan

        highs = np.asarray([c.high for c in candles], dtype=float)
        lows = np.asarray([c.low for c in candles], dtype=float)
        closes = np.asarray([c.close for c in candles], dtype=float)

        out = talib.ATR(highs, lows, closes, timeperiod=period)
        result = out[-1]
        return float(result) if not np.isnan(result) else math.nan

    @staticmethod
    def roc(values: List[float], period: int = 12) -> float:
        """Rate of Change."""
        if period <= 0 or len(values) <= period:
            return math.nan

        arr = np.asarray(values, dtype=float)
        out = talib.ROC(arr, timeperiod=period)
        result = out[-1]
        return float(result) if not np.isnan(result) else math.nan

    @staticmethod
    def adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Average Directional Index."""
        if period <= 0 or len(closes) < period:
            return math.nan

        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        c = np.asarray(closes, dtype=float)

        out = talib.ADX(h, l, c, timeperiod=period)
        result = out[-1]
        return float(result) if not np.isnan(result) else math.nan

    @staticmethod
    def cci(highs: List[float], lows: List[float], closes: List[float], period: int = 20) -> float:
        """Commodity Channel Index."""
        if period <= 0 or len(closes) < period:
            return math.nan

        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        c = np.asarray(closes, dtype=float)

        out = talib.CCI(h, l, c, timeperiod=period)
        result = out[-1]
        return float(result) if not np.isnan(result) else math.nan

    @staticmethod
    def stoch(
        highs: List[float], lows: List[float], closes: List[float],
        fastk_period: int = 14, slowk_period: int = 3, slowd_period: int = 3
    ) -> Tuple[float, float]:
        """Stochastic oscillator (slow K, slow D)."""
        min_length = fastk_period + slowk_period - 1
        if fastk_period <= 0 or slowk_period <= 0 or slowd_period <= 0 or len(closes) < min_length:
            return math.nan, math.nan

        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        c = np.asarray(closes, dtype=float)

        slowk, slowd = talib.STOCH(
            h,
            l,
            c,
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowk_matype=0,
            slowd_period=slowd_period,
            slowd_matype=0,
        )
        k = float(slowk[-1]) if not np.isnan(slowk[-1]) else math.nan
        d = float(slowd[-1]) if not np.isnan(slowd[-1]) else math.nan
        return k, d

    @staticmethod
    def volume_sma(volumes: List[float], period: int = 20) -> float:
        """Volume Simple Moving Average."""
        return IndicatorEngine.sma(volumes, period)

    @staticmethod
    def snapshot(candles: List[Candle]) -> Dict[str, float]:
        """Generate a snapshot of all indicators."""
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [c.volume for c in candles]
        _ = highs, lows  # kept for symmetry and future extension

        macd_line, macd_signal, macd_hist = IndicatorEngine.macd(closes)
        bb_upper, bb_mid, bb_lower = IndicatorEngine.bollinger(closes)
        adx_14 = IndicatorEngine.adx(highs, lows, closes, 14)
        cci_20 = IndicatorEngine.cci(highs, lows, closes, 20)
        sto_k, sto_d = IndicatorEngine.stoch(highs, lows, closes, 14, 3, 3)

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
            "adx_14": adx_14,
            "cci_20": cci_20,
            "sto_k": sto_k,
            "sto_d": sto_d,
            "volume": volumes[-1] if volumes else math.nan,
            "volume_sma_20": IndicatorEngine.volume_sma(volumes, 20),
            "roc_12": IndicatorEngine.roc(closes, 12),
            "close_change_1": (
                percent_change(closes[-2], closes[-1]) if len(closes) >= 2 else math.nan
            ),
            "close_change_5": (
                percent_change(closes[-6], closes[-1]) if len(closes) >= 6 else math.nan
            ),
            "close_change_15": (
                percent_change(closes[-16], closes[-1])
                if len(closes) >= 16
                else math.nan
            ),
        }
        return snap
