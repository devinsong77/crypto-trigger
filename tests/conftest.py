"""
Fixtures and utilities for test suite.
"""

import math
from typing import List

from src.models import Candle


def create_candles(closes: List[float]) -> List[Candle]:
    """Create Candle objects from close prices."""
    return [
        Candle(
            open_time=i * 1000,
            close_time=i * 1000 + 999,
            open=closes[i],
            high=closes[i] + 1,
            low=closes[i] - 1,
            close=closes[i],
            volume=1000.0,
            closed=True,
        )
        for i in range(len(closes))
    ]


def create_uptrend_closes(start: float = 100.0, steps: int = 40) -> List[float]:
    """Create uptrend price data."""
    return [start + i * 0.5 for i in range(steps)]


def create_downtrend_closes(start: float = 100.0, steps: int = 40) -> List[float]:
    """Create downtrend price data."""
    return [start - i * 0.5 for i in range(steps)]


def create_flat_closes(value: float = 100.0, steps: int = 40) -> List[float]:
    """Create flat (no change) price data."""
    return [value] * steps


def is_close(a: float, b: float, rel_tol: float = 1e-2) -> bool:
    """Check if two floats are close (handles NaN)."""
    if math.isnan(a) and math.isnan(b):
        return True
    if math.isnan(a) or math.isnan(b):
        return False
    return abs(a - b) <= rel_tol * max(abs(a), abs(b), 1)
