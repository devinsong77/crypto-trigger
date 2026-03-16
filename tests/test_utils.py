"""
Tests for src.utils module.
"""

import math
import unittest

from src.utils import mean, percent_change, stddev


class TestPercentChange(unittest.TestCase):
    """Test percent_change function."""

    def test_percent_change_positive(self):
        """Test positive price change."""
        result = percent_change(100, 110)
        self.assertAlmostEqual(result, 10.0, places=2)

    def test_percent_change_negative(self):
        """Test negative price change."""
        result = percent_change(100, 90)
        self.assertAlmostEqual(result, -10.0, places=2)

    def test_percent_change_zero(self):
        """Test zero change."""
        result = percent_change(100, 100)
        self.assertAlmostEqual(result, 0.0, places=2)

    def test_percent_change_division_by_zero(self):
        """Test division by zero returns NaN."""
        result = percent_change(0, 100)
        self.assertTrue(math.isnan(result))

    def test_percent_change_with_nan(self):
        """Test NaN input returns NaN."""
        result = percent_change(math.nan, 100)
        self.assertTrue(math.isnan(result))


class TestMean(unittest.TestCase):
    """Test mean function."""

    def test_mean_normal(self):
        """Test mean calculation."""
        result = mean([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertAlmostEqual(result, 3.0, places=2)

    def test_mean_empty(self):
        """Test mean of empty list."""
        result = mean([])
        self.assertTrue(math.isnan(result))

    def test_mean_single(self):
        """Test mean of single value."""
        result = mean([5.0])
        self.assertAlmostEqual(result, 5.0, places=2)


class TestStddev(unittest.TestCase):
    """Test stddev function."""

    def test_stddev_normal(self):
        """Test standard deviation calculation."""
        result = stddev([1.0, 2.0, 3.0, 4.0, 5.0])
        expected = math.sqrt(2.0)  # sqrt(sum((x-3)^2)/5) = sqrt(10/5) = sqrt(2)
        self.assertAlmostEqual(result, expected, places=2)

    def test_stddev_single(self):
        """Test stddev with less than 2 values."""
        result = stddev([5.0])
        self.assertTrue(math.isnan(result))

    def test_stddev_identical(self):
        """Test stddev of identical values."""
        result = stddev([5.0, 5.0, 5.0])
        self.assertAlmostEqual(result, 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
