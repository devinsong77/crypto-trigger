"""
Binance data source for market feeds.
"""

import asyncio
import json
import logging
import urllib.parse
import urllib.request
from typing import List

import websockets

from .models import Candle

LOG = logging.getLogger(__name__)


class BinanceSource:
    """Fetches market data from Binance REST and WebSocket."""

    def __init__(self, symbol: str, interval: str, backfill_limit: int = 500):
        self.symbol = symbol.upper()
        self.interval = interval
        self.backfill_limit = min(int(backfill_limit), 1000)
        self.rest_base = "https://api.binance.com"
        self.ws_url = f"wss://data-stream.binance.vision/ws/{self.symbol.lower()}@kline_{self.interval}"

    def fetch_backfill(self) -> List[Candle]:
        """Fetch historical klines from Binance REST API."""
        url = (
            f"{self.rest_base}/api/v3/klines?"
            + urllib.parse.urlencode(
                {"symbol": self.symbol, "interval": self.interval, "limit": self.backfill_limit}
            )
        )
        req = urllib.request.Request(url, headers={"User-Agent": "btc-monitor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        candles = []
        for row in raw:
            candles.append(
                Candle(
                    open_time=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    close_time=int(row[6]),
                    closed=True,
                )
            )
        return candles

    async def stream(self):
        """Stream market data from Binance WebSocket."""
        while True:
            try:
                LOG.info("Connecting Binance websocket: %s", self.ws_url)
                async with websockets.connect(
                    self.ws_url, ping_interval=20, ping_timeout=60, close_timeout=10
                ) as ws:
                    async for message in ws:
                        yield json.loads(message)
            except Exception as e:
                LOG.warning("WebSocket disconnected: %s. Reconnecting in 3s.", e)
                await asyncio.sleep(3)
