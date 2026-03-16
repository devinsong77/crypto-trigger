"""
Data models for crypto-trigger.
"""

from dataclasses import dataclass


@dataclass
class Candle:
    """Represents a trading candle (OHLCV)."""
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool = True
