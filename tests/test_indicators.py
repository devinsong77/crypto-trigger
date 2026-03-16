"""
Tests for src.indicators module.
"""

import math
import unittest

from src.indicators import IndicatorEngine
from src.models import Candle
from tests.conftest import create_candles, create_downtrend_closes, create_flat_closes, create_uptrend_closes


class TestSMA(unittest.TestCase):
    """Test Simple Moving Average."""

    def test_sma_basic(self):
        """Test basic SMA calculation."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = IndicatorEngine.sma(values, 3)
        # Average of last 3: (3+4+5)/3 = 4
        self.assertAlmostEqual(result, 4.0, places=2)

    def test_sma_insufficient_data(self):
        """Test SMA with insufficient data."""
        values = [1.0, 2.0]
        result = IndicatorEngine.sma(values, 5)
        self.assertTrue(math.isnan(result))

    def test_sma_period_zero(self):
        """Test SMA with period 0."""
        values = [1.0, 2.0, 3.0]
        result = IndicatorEngine.sma(values, 0)
        self.assertTrue(math.isnan(result))

    def test_sma_full_period(self):
        """Test SMA with all values."""
        values = [10.0, 20.0, 30.0, 40.0]
        result = IndicatorEngine.sma(values, 4)
        # (10+20+30+40)/4 = 25
        self.assertAlmostEqual(result, 25.0, places=2)


class TestEMA(unittest.TestCase):
    """Test Exponential Moving Average."""

    def test_ema_basic(self):
        """Test basic EMA calculation."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        result = IndicatorEngine.ema(values, 3)
        # First EMA = (1+2+3)/3 = 2
        # Then apply alpha = 2/(3+1) = 0.5
        self.assertGreater(result, 0)
        self.assertLess(result, 10)

    def test_ema_insufficient_data(self):
        """Test EMA with insufficient data."""
        values = [1.0, 2.0]
        result = IndicatorEngine.ema(values, 5)
        self.assertTrue(math.isnan(result))

    def test_ema_series(self):
        """Test EMA series generation."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        series = IndicatorEngine.ema_series(values, 2)
        self.assertEqual(len(series), 4)  # 5 - 2 + 1
        self.assertGreater(series[-1], series[0])


class TestRSI(unittest.TestCase):
    """Test Relative Strength Index."""

    def test_rsi_uptrend(self):
        """Test RSI in uptrend (should be > 50)."""
        values = list(range(1, 16))  # [1, 2, 3, ..., 15]
        result = IndicatorEngine.rsi(values, 14)
        self.assertGreater(result, 70)  # Strong uptrend
        self.assertLessEqual(result, 100)

    def test_rsi_downtrend(self):
        """Test RSI in downtrend (should be < 50)."""
        values = list(range(15, 0, -1))  # [15, 14, 13, ..., 1]
        result = IndicatorEngine.rsi(values, 14)
        self.assertLess(result, 30)  # Strong downtrend
        self.assertGreaterEqual(result, 0)

    def test_rsi_range(self):
        """Test RSI range."""
        values = [100.0] * 15  # All the same
        result = IndicatorEngine.rsi(values, 14)
        # When no changes, losses = 0, so RSI = 100
        self.assertAlmostEqual(result, 100.0, places=1)

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        values = [1.0, 2.0, 3.0]
        result = IndicatorEngine.rsi(values, 14)
        self.assertTrue(math.isnan(result))


class TestMACD(unittest.TestCase):
    """Test MACD indicator."""

    def test_macd_returns_tuple(self):
        """Test MACD returns tuple of 3 values."""
        values = [float(x) for x in range(1, 40)]
        macd_line, signal_line, histogram = IndicatorEngine.macd(values)
        self.assertIsInstance(macd_line, float)
        self.assertIsInstance(signal_line, float)
        self.assertIsInstance(histogram, float)

    def test_macd_histogram_consistency(self):
        """Test MACD histogram = line - signal."""
        values = [float(x) for x in range(1, 40)]
        macd_line, signal_line, histogram = IndicatorEngine.macd(values)
        expected_hist = macd_line - signal_line
        self.assertAlmostEqual(histogram, expected_hist, places=4)

    def test_macd_insufficient_data(self):
        """Test MACD with insufficient data."""
        values = [1.0, 2.0, 3.0]
        macd_line, signal_line, histogram = IndicatorEngine.macd(values)
        self.assertTrue(math.isnan(macd_line))
        self.assertTrue(math.isnan(signal_line))
        self.assertTrue(math.isnan(histogram))

    def test_macd_uptrend(self):
        """Test MACD in uptrend (positive line)."""
        values = [float(x) for x in range(1, 40)]
        macd_line, signal_line, histogram = IndicatorEngine.macd(values)
        self.assertGreater(macd_line, 0)


class TestBollingerBands(unittest.TestCase):
    """Test Bollinger Bands."""

    def test_bollinger_basic(self):
        """Test basic Bollinger Bands calculation."""
        values = [float(x) for x in range(1, 21)]
        upper, mid, lower = IndicatorEngine.bollinger(values, 20, 2.0)
        self.assertGreater(upper, mid)
        self.assertGreater(mid, lower)

    def test_bollinger_symmetry(self):
        """Test Bollinger Bands symmetry."""
        # Symmetric data around center
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 14.0, 13.0, 12.0, 11.0]
        upper, mid, lower = IndicatorEngine.bollinger(values, 10, 2.0)
        # Upper and lower should be equidistant from mid
        self.assertAlmostEqual(upper - mid, mid - lower, places=4)

    def test_bollinger_insufficient_data(self):
        """Test Bollinger Bands with insufficient data."""
        values = [1.0, 2.0, 3.0]
        upper, mid, lower = IndicatorEngine.bollinger(values, 20)
        self.assertTrue(math.isnan(upper))

    def test_bollinger_width(self):
        """Test Bollinger Bands width."""
        values = [float(x) for x in range(1, 21)]
        upper, mid, lower = IndicatorEngine.bollinger(values, 20, 2.0)
        width = upper - lower
        self.assertGreater(width, 0)


class TestATR(unittest.TestCase):
    """Test Average True Range."""

    def test_atr_basic(self):
        """Test basic ATR calculation."""
        candles = [
            Candle(1000, 1999, 100.0, 110.0, 95.0, 105.0, 1000.0),
            Candle(2000, 2999, 105.0, 115.0, 100.0, 110.0, 1100.0),
            Candle(3000, 3999, 110.0, 120.0, 105.0, 115.0, 1200.0),
        ] + [
            Candle(i * 1000, i * 1000 + 999, 100.0 + i, 110.0 + i, 95.0 + i, 105.0 + i, 1000.0)
            for i in range(4, 16)
        ]
        result = IndicatorEngine.atr(candles, 14)
        self.assertGreater(result, 0)

    def test_atr_insufficient_data(self):
        """Test ATR with insufficient data."""
        candles = [
            Candle(1000, 1999, 100.0, 110.0, 95.0, 105.0, 1000.0),
            Candle(2000, 2999, 105.0, 115.0, 100.0, 110.0, 1100.0),
        ]
        result = IndicatorEngine.atr(candles, 14)
        self.assertTrue(math.isnan(result))


class TestROC(unittest.TestCase):
    """Test Rate of Change."""

    def test_roc_positive(self):
        """Test ROC with positive change."""
        values = [100.0] * 10 + [110.0]  # Change from 100 to 110
        result = IndicatorEngine.roc(values, 10)
        self.assertAlmostEqual(result, 10.0, places=2)

    def test_roc_negative(self):
        """Test ROC with negative change."""
        values = [100.0] * 10 + [90.0]  # Change from 100 to 90
        result = IndicatorEngine.roc(values, 10)
        self.assertAlmostEqual(result, -10.0, places=2)

    def test_roc_insufficient_data(self):
        """Test ROC with insufficient data."""
        values = [1.0, 2.0, 3.0]
        result = IndicatorEngine.roc(values, 5)
        self.assertTrue(math.isnan(result))


class TestIndicatorSnapshot(unittest.TestCase):
    """Test indicator snapshot generation."""

    def test_snapshot_all_fields(self):
        """Test snapshot generates all required fields."""
        closes = [float(x) for x in range(1, 70)]
        volumes = [1000.0 + x for x in range(69)]
        candles = create_candles(closes)
        for i, candle in enumerate(candles):
            candle.volume = volumes[i]

        snap = IndicatorEngine.snapshot(candles)

        # Check all required fields exist
        required_fields = [
            "close",
            "sma_9",
            "sma_20",
            "sma_50",
            "ema_9",
            "ema_21",
            "rsi_14",
            "macd",
            "macd_signal",
            "macd_hist",
            "bb_upper",
            "bb_mid",
            "bb_lower",
            "atr_14",
            "volume",
            "volume_sma_20",
            "roc_12",
            "close_change_1",
            "close_change_5",
            "close_change_15",
        ]

        for field in required_fields:
            self.assertIn(field, snap, f"Field {field} missing from snapshot")
            self.assertIsInstance(snap[field], float, f"Field {field} not a float")

    def test_snapshot_insufficient_data(self):
        """Test snapshot with minimal data."""
        candles = [Candle(1000, 1999, 100.0, 101.0, 99.0, 100.0, 1000.0)]
        snap = IndicatorEngine.snapshot(candles)

        # Should have NaN for most indicators due to insufficient data
        self.assertTrue(math.isnan(snap["sma_9"]))
        self.assertTrue(math.isnan(snap["rsi_14"]))
        self.assertEqual(snap["close"], 100.0)


if __name__ == "__main__":
    unittest.main()
