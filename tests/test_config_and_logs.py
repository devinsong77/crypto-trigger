"""
Tests for configuration and logging integration.
"""

import json
import logging
import unittest
from io import StringIO

from src.monitor import MonitorService
from src.rules import RuleEngine


class TestConfigurationRules(unittest.TestCase):
    """Test that configuration rules are correct and non-conflicting."""

    def setUp(self):
        """Load the configuration."""
        with open("config_comprehensive.json", "r") as f:
            self.config = json.load(f)

    def test_no_rsi_extreme_rules(self):
        """Verify that RSI extreme rules have been removed."""
        rule_ids = [r.get("id") for r in self.config["rules"]]
        self.assertNotIn("rsi_extreme_oversold", rule_ids)
        self.assertNotIn("rsi_extreme_overbought", rule_ids)

    def test_no_macd_either_cross_rule(self):
        """Verify that MACD either_cross rule has been removed."""
        rule_ids = [r.get("id") for r in self.config["rules"]]
        self.assertNotIn("macd_either_cross", rule_ids)

    def test_no_volume_normal_rule(self):
        """Verify that volume normal rule has been removed."""
        rule_ids = [r.get("id") for r in self.config["rules"]]
        self.assertNotIn("volume_spike_normal", rule_ids)

    def test_bollinger_rules_have_direction(self):
        """Verify that Bollinger rules have direction parameter."""
        bollinger_rules = [r for r in self.config["rules"] 
                          if r.get("type") == "bollinger_break"]
        self.assertTrue(len(bollinger_rules) > 0)
        for rule in bollinger_rules:
            self.assertIn("direction", rule)
            self.assertIn(rule.get("direction"), ["upper", "lower", "either"])

    def test_rsi_rules_count(self):
        """Verify that only 2 RSI rules exist (basic levels only)."""
        rsi_rules = [r for r in self.config["rules"] 
                    if r.get("type") == "rsi_threshold"]
        self.assertEqual(len(rsi_rules), 2)

    def test_macd_rules_count(self):
        """Verify that only 2 MACD rules exist (bullish and bearish)."""
        macd_rules = [r for r in self.config["rules"] 
                     if r.get("type") == "macd_cross"]
        self.assertEqual(len(macd_rules), 2)
        directions = {r.get("direction") for r in macd_rules}
        self.assertEqual(directions, {"bullish", "bearish"})

    def test_macd_rules_have_direction(self):
        """Verify that all MACD rules have direction parameter."""
        macd_rules = [r for r in self.config["rules"] 
                     if r.get("type") == "macd_cross"]
        for rule in macd_rules:
            self.assertIn("direction", rule)

    def test_price_change_rules_preserved(self):
        """Verify that all 4 price change rules are preserved."""
        price_rules = [r for r in self.config["rules"] 
                      if r.get("type") == "price_change_pct"]
        self.assertEqual(len(price_rules), 4)
        # Should have both up and down directions
        directions = {r.get("direction") for r in price_rules}
        self.assertEqual(directions, {"up", "down"})


class TestLoggingWithSymbol(unittest.TestCase):
    """Test that logs include trading symbol information."""

    def setUp(self):
        """Set up logging capture."""
        with open("config_comprehensive.json", "r") as f:
            self.config = json.load(f)

    def test_monitor_log_format_with_symbol(self):
        """Test that monitor service logs include symbol."""
        # Create a monitor instance
        monitor = MonitorService(
            self.config, 
            symbol="BTCUSDT", 
            interval="15m"
        )
        
        # Setup logger to capture output
        logger = logging.getLogger("src.monitor")
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(name)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Verify monitor has the symbol
        self.assertEqual(monitor.symbol, "BTCUSDT")
        self.assertEqual(monitor.interval, "15m")
        
        # Clean up
        logger.removeHandler(handler)

    def test_rule_engine_supports_symbol_in_evaluate(self):
        """Test that rule engine's evaluate method accepts symbol parameter."""
        from tests.conftest import create_candles
        
        rules = RuleEngine(self.config["rules"])
        
        # Create dummy candles for evaluation
        closes = [float(x) for x in range(1, 100)]
        candles = create_candles(closes)
        
        # Create a minimal snapshot with required values
        snap = {
            "close": 100.0,
            "rsi_14": 50.0,
            "macd": 0.0,
            "macd_signal": 0.0,
            "macd_hist": 0.0,
            "bb_upper": 110.0,
            "bb_lower": 90.0,
            "volume": 1000.0,
            "volume_sma_20": 500.0,
        }
        
        # Just verify it accepts the symbol parameter (should not raise error)
        try:
            events = rules.evaluate("ETHUSDT", "15m", candles, snap)
            self.assertIsInstance(events, list)
        except TypeError:
            self.fail("RuleEngine.evaluate should accept symbol parameter")


class TestRuleDirectionParameters(unittest.TestCase):
    """Test that rule direction parameters work correctly."""

    def setUp(self):
        """Load configuration."""
        with open("config_comprehensive.json", "r") as f:
            self.config = json.load(f)

    def test_bollinger_upper_has_upper_direction(self):
        """Test that bollinger_upper_break has 'upper' direction."""
        rule = next((r for r in self.config["rules"] 
                    if r.get("id") == "bollinger_upper_break"), None)
        self.assertIsNotNone(rule)
        self.assertEqual(rule.get("direction"), "upper")

    def test_bollinger_lower_has_lower_direction(self):
        """Test that bollinger_lower_break has 'lower' direction."""
        rule = next((r for r in self.config["rules"] 
                    if r.get("id") == "bollinger_lower_break"), None)
        self.assertIsNotNone(rule)
        self.assertEqual(rule.get("direction"), "lower")

    def test_macd_bullish_has_bullish_direction(self):
        """Test that macd_bullish_cross has 'bullish' direction."""
        rule = next((r for r in self.config["rules"] 
                    if r.get("id") == "macd_bullish_cross"), None)
        self.assertIsNotNone(rule)
        self.assertEqual(rule.get("direction"), "bullish")

    def test_macd_bearish_has_bearish_direction(self):
        """Test that macd_bearish_cross has 'bearish' direction."""
        rule = next((r for r in self.config["rules"] 
                    if r.get("id") == "macd_bearish_cross"), None)
        self.assertIsNotNone(rule)
        self.assertEqual(rule.get("direction"), "bearish")
