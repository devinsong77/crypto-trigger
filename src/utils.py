"""
Utility functions for crypto-trigger.
"""

import math
import time
from typing import Any, List


def now_ts() -> float:
    """Get current Unix timestamp."""
    return time.time()


def safe_float(value: Any) -> float:
    """Convert value to float, return NaN if None."""
    return float(value) if value is not None else math.nan


def percent_change(a: float, b: float) -> float:
    """Calculate percentage change from a to b."""
    if a == 0 or math.isnan(a) or math.isnan(b):
        return math.nan
    return (b - a) / a * 100.0


def mean(values: List[float]) -> float:
    """Calculate arithmetic mean of values."""
    return sum(values) / len(values) if values else math.nan


def stddev(values: List[float]) -> float:
    """Calculate standard deviation of values."""
    if len(values) < 2:
        return math.nan
    m = mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))
