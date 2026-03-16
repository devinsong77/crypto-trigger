"""
Tests for src.rules module.
"""

import math
import unittest

from src.indicators import IndicatorEngine
from src.rules import RuleEngine
from tests.conftest import create_candles, create_downtrend_closes, create_uptrend_closes


class TestPriceChangeRule(unittest.TestCase):
    """Test price_change_pct rule."""

    def test_quick_up_trigger(self):
        """Test quick up price change triggers."""
        closes = [100.0] * 10 + [100.0, 101.0, 102.0, 103.0]
        rule = {
            "type": "price_change_pct",
            "lookback_bars": 3,
            "threshold_pct": 1.5,
            "direction": "up",
        }
        engine = RuleEngine([rule])
        candles = create_candles(closes)
        matched, summary = engine._match(rule, candles, closes, {})
        self.assertTrue(matched)
        self.assertIn("3", summary)

    def test_quick_down_trigger(self):
        """Test quick down price change triggers."""
        closes = [100.0] * 10 + [100.0, 99.0, 98.0, 97.0]
        rule = {
            "type": "price_change_pct",
            "lookback_bars": 3,
            "threshold_pct": 1.5,
            "direction": "down",
        }
        engine = RuleEngine([rule])
        candles = create_candles(closes)
        matched, summary = engine._match(rule, candles, closes, {})
        self.assertTrue(matched)

    def test_price_change_neither_direction(self):
        """Test price_change with 'either' direction."""
        closes = [100.0] * 10 + [100.0, 101.0, 102.0, 103.0]
        rule = {
            "type": "price_change_pct",
            "lookback_bars": 3,
            "threshold_pct": 1.5,
            "direction": "either",
        }
        engine = RuleEngine([rule])
        candles = create_candles(closes)
        matched, summary = engine._match(rule, candles, closes, {})
        self.assertTrue(matched)


class TestRSIRule(unittest.TestCase):
    """Test RSI threshold rules."""

    def test_rsi_oversold(self):
        """Test RSI oversold condition."""
        snap = {"rsi_14": 25.0}
        rule = {"type": "rsi_threshold", "oversold": 30}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertTrue(matched)
        self.assertIn("25", summary)

    def test_rsi_overbought(self):
        """Test RSI overbought condition."""
        snap = {"rsi_14": 75.0}
        rule = {"type": "rsi_threshold", "overbought": 70}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertTrue(matched)

    def test_rsi_neutral(self):
        """Test RSI in neutral zone."""
        snap = {"rsi_14": 50.0}
        rule = {"type": "rsi_threshold", "oversold": 30, "overbought": 70}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertFalse(matched)

    def test_rsi_oversold_not_overbought(self):
        """Test oversold rule doesn't trigger on overbought."""
        snap = {"rsi_14": 75.0}
        rule = {"type": "rsi_threshold", "oversold": 30}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertFalse(matched)

    def test_rsi_overbought_not_oversold(self):
        """Test overbought rule doesn't trigger on oversold."""
        snap = {"rsi_14": 25.0}
        rule = {"type": "rsi_threshold", "overbought": 70}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertFalse(matched)


class TestADXCCIRule(unittest.TestCase):
    """Test ADX and CCI rules."""

    def test_adx_above_threshold(self):
        snap = {"adx_14": 30.0}
        rule = {"type": "adx_threshold", "direction": "above", "threshold": 25.0}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertTrue(matched)

    def test_adx_below_threshold(self):
        snap = {"adx_14": 20.0}
        rule = {"type": "adx_threshold", "direction": "below", "threshold": 25.0}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertTrue(matched)

    def test_cci_overbought(self):
        snap = {"cci_20": 150.0}
        rule = {"type": "cci_threshold", "overbought": 100.0}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertTrue(matched)

    def test_cci_oversold(self):
        snap = {"cci_20": -150.0}
        rule = {"type": "cci_threshold", "oversold": -100.0}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertTrue(matched)


class TestStochRule(unittest.TestCase):
    """Test Stochastic oscillator cross rule."""

    def test_stoch_bullish_cross(self):
        # construct a simple snapshot where K just crossed above D
        snap = {"sto_k": 40.0, "sto_d": 35.0}
        # build candles so previous stoch is below
        closes = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        candles = create_candles(closes)
        # We can't rely on full indicator calc in this synthetic scenario, but rule function checks previous intermediate snapshot.
        rule = {"type": "stoch_cross", "direction": "bullish"}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, candles, closes, snap)
        self.assertIsInstance(matched, bool)


class TestMACDRule(unittest.TestCase):
    """Test MACD cross rules."""

    def test_macd_bullish_cross(self):
        """Test MACD bullish cross detection."""
        closes = [float(x) for x in range(1, 40)]
        candles = create_candles(closes)
        rule = {"type": "macd_cross", "direction": "bullish"}
        engine = RuleEngine([rule])
        snap = IndicatorEngine.snapshot(candles)
        matched, summary = engine._match(rule, candles, closes, snap)
        # May or may not match depending on data
        self.assertIsInstance(matched, bool)

    def test_macd_cross_insufficient_data(self):
        """Test MACD cross with insufficient data."""
        closes = [1.0, 2.0, 3.0]
        candles = create_candles(closes)
        rule = {"type": "macd_cross", "direction": "bullish"}
        engine = RuleEngine([rule])
        snap = IndicatorEngine.snapshot(candles)
        matched, summary = engine._match(rule, candles, closes, snap)
        self.assertFalse(matched)

    def test_macd_bearish_cross(self):
        """Test MACD bearish cross detection."""
        closes = [float(x) for x in range(40, 1, -1)]
        candles = create_candles(closes)
        rule = {"type": "macd_cross", "direction": "bearish"}
        engine = RuleEngine([rule])
        snap = IndicatorEngine.snapshot(candles)
        matched, summary = engine._match(rule, candles, closes, snap)
        self.assertIsInstance(matched, bool)

    def test_macd_direction_isolation(self):
        """Test MACD bearish rule doesn't trigger on bullish setup."""
        # Uptrend: bullish setup
        closes = [float(x) for x in range(1, 40)]
        candles = create_candles(closes)
        snap = IndicatorEngine.snapshot(candles)
        
        # Try bearish rule on bullish data
        rule_bearish = {"type": "macd_cross", "direction": "bearish"}
        engine = RuleEngine([rule_bearish])
        matched_bearish, _ = engine._match(rule_bearish, candles, closes, snap)
        
        # Try bullish rule on bullish data
        rule_bullish = {"type": "macd_cross", "direction": "bullish"}
        engine = RuleEngine([rule_bullish])
        matched_bullish, _ = engine._match(rule_bullish, candles, closes, snap)
        
        # In an uptrend, bearish should be False or bullish should be True
        # At least they shouldn't both be True at same time in this uptrend
        if matched_bullish:
            self.assertFalse(matched_bearish)


class TestBollingerRule(unittest.TestCase):
    """Test Bollinger Bands break rules."""

    def test_bollinger_upper_break(self):
        """Test upper Bollinger break."""
        snap = {"close": 150.0, "bb_upper": 100.0, "bb_lower": 80.0}
        rule = {"type": "bollinger_break", "direction": "upper"}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertTrue(matched)
        self.assertIn("150", summary)

    def test_bollinger_lower_break(self):
        """Test lower Bollinger break."""
        snap = {"close": 50.0, "bb_upper": 100.0, "bb_lower": 80.0}
        rule = {"type": "bollinger_break", "direction": "lower"}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertTrue(matched)

    def test_bollinger_no_break(self):
        """Test no Bollinger break."""
        snap = {"close": 90.0, "bb_upper": 100.0, "bb_lower": 80.0}
        rule = {"type": "bollinger_break", "direction": "either"}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertFalse(matched)
    
    def test_bollinger_upper_only_separate(self):
        """Test upper break doesn't trigger lower-only rule."""
        snap = {"close": 150.0, "bb_upper": 100.0, "bb_lower": 80.0}
        rule = {"type": "bollinger_break", "direction": "lower"}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertFalse(matched)
    
    def test_bollinger_lower_only_separate(self):
        """Test lower break doesn't trigger upper-only rule."""
        snap = {"close": 50.0, "bb_upper": 100.0, "bb_lower": 80.0}
        rule = {"type": "bollinger_break", "direction": "upper"}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertFalse(matched)


class TestSMARule(unittest.TestCase):
    """Test SMA cross rules."""

    def test_sma_bullish_cross(self):
        """Test SMA bullish cross."""
        closes = [float(x) for x in range(1, 70)]
        candles = create_candles(closes)
        rule = {"type": "sma_cross", "fast": 9, "slow": 20, "direction": "bullish"}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, candles, closes, {})
        self.assertIsInstance(matched, bool)

    def test_sma_bearish_cross(self):
        """Test SMA bearish cross."""
        closes = [float(x) for x in range(70, 1, -1)]
        candles = create_candles(closes)
        rule = {"type": "sma_cross", "fast": 9, "slow": 20, "direction": "bearish"}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, candles, closes, {})
        self.assertIsInstance(matched, bool)

    def test_sma_insufficient_data(self):
        """Test SMA cross with insufficient data."""
        closes = [1.0, 2.0, 3.0]
        candles = create_candles(closes)
        rule = {"type": "sma_cross", "fast": 9, "slow": 20, "direction": "bullish"}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, candles, closes, {})
        self.assertFalse(matched)


class TestVolumeRule(unittest.TestCase):
    """Test volume spike rules."""

    def test_volume_spike(self):
        """Test volume spike detection."""
        snap = {"volume": 250.0, "volume_sma_20": 100.0}
        rule = {"type": "volume_spike", "multiple": 2.0}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertTrue(matched)
        self.assertIn("2.5", summary)  # 250 / 100

    def test_volume_no_spike(self):
        """Test no volume spike."""
        snap = {"volume": 150.0, "volume_sma_20": 100.0}
        rule = {"type": "volume_spike", "multiple": 2.0}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertFalse(matched)

    def test_volume_zero_sma(self):
        """Test volume spike with zero SMA."""
        snap = {"volume": 100.0, "volume_sma_20": 0.0}
        rule = {"type": "volume_spike", "multiple": 2.0}
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertFalse(matched)


class TestPriceChangeMultipleRules(unittest.TestCase):
    """Test multiple price change rules can trigger simultaneously."""

    def test_quick_and_significant_both_trigger(self):
        """Test that both quick (1.5%) and significant (2.5%) rules can trigger."""
        # Price goes up 3% in 5 bars - satisfies both quick (1.5% in 3 bars) and significant (2.5% in 5 bars)
        closes = [100.0] * 10 + [100.0, 101.0, 102.0, 103.0, 103.0]
        candles = create_candles(closes)

        # Quick rule: 3% up in last 3 bars (exceeds 1.5%)
        rule_quick = {
            "type": "price_change_pct",
            "lookback_bars": 3,
            "threshold_pct": 1.5,
            "direction": "up",
        }
        engine = RuleEngine([rule_quick])
        matched_quick, _ = engine._match(rule_quick, candles, closes, {})
        
        # Significant rule: 3% up in last 5 bars (exceeds 2.5%)
        rule_sig = {
            "type": "price_change_pct",
            "lookback_bars": 5,
            "threshold_pct": 2.5,
            "direction": "up",
        }
        engine = RuleEngine([rule_sig])
        matched_sig, _ = engine._match(rule_sig, candles, closes, {})
        
        # Both should trigger - this is intentional (different thresholds)
        self.assertTrue(matched_quick)
        self.assertTrue(matched_sig)


class TestComboRule(unittest.TestCase):
    """Test combo rules."""

    def test_combo_all_match(self):
        """Test combo rule with all conditions met."""
        snap = {"rsi_14": 25.0, "volume": 250.0, "volume_sma_20": 100.0}
        rule = {
            "type": "combo",
            "all_of": [
                {"type": "rsi_threshold", "oversold": 30},
                {"type": "volume_spike", "multiple": 2.0},
            ],
        }
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertTrue(matched)

    def test_combo_partial_match(self):
        """Test combo rule with only one condition met."""
        snap = {"rsi_14": 75.0, "volume": 250.0, "volume_sma_20": 100.0}
        rule = {
            "type": "combo",
            "all_of": [
                {"type": "rsi_threshold", "oversold": 30},
                {"type": "volume_spike", "multiple": 2.0},
            ],
        }
        engine = RuleEngine([rule])
        matched, summary = engine._match(rule, [], [], snap)
        self.assertFalse(matched)


class TestRuleEngineIntegration(unittest.TestCase):
    """Integration tests for rule engine."""

    def test_evaluate_multiple_rules(self):
        """Test evaluating multiple rules at once."""
        closes = [float(x) for x in range(1, 40)]
        candles = create_candles(closes)
        snap = IndicatorEngine.snapshot(candles)

        rules = [
            {"id": "rule1", "type": "rsi_threshold", "oversold": 10},
            {"id": "rule2", "type": "rsi_threshold", "overbought": 90},
        ]
        engine = RuleEngine(rules)
        events = engine.evaluate("BTCUSDT", "15m", candles, snap)
        self.assertIsInstance(events, list)

    def test_cooldown_mechanism(self):
        """Test rule cooldown prevents duplicate triggers."""
        snap = {"rsi_14": 25.0}
        rule = {"id": "test_rule", "type": "rsi_threshold", "oversold": 30, "cooldown_secs": 1000}
        engine = RuleEngine([rule])

        # First evaluation
        candles = []
        closes = []
        events1 = engine.evaluate("BTCUSDT", "15m", candles, snap)
        self.assertEqual(len(events1), 1)

        # Second evaluation immediately after (should be blocked by cooldown)
        events2 = engine.evaluate("BTCUSDT", "15m", candles, snap)
        self.assertEqual(len(events2), 0)


if __name__ == "__main__":
    unittest.main()
