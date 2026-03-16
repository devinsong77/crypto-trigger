"""
Main entry point for crypto-trigger.
"""

import argparse
import asyncio
import json
import logging
from typing import Any, Dict, List

from .monitor import MonitorService

LOG = logging.getLogger(__name__)


def load_config(path: str) -> Dict[str, Any]:
    """Load JSON configuration file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def run_monitors(services: List[MonitorService]) -> None:
    """Run multiple monitor services concurrently."""
    await asyncio.gather(*[service.run() for service in services])


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="BTCUSDT monitor for OpenClaw")
    parser.add_argument(
        "--config", default="config_comprehensive.json", help="Path to JSON config"
    )
    parser.add_argument(
        "--log-level", default="INFO", help="DEBUG / INFO / WARNING / ERROR"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    cfg = load_config(args.config)

    # Support both single market and multiple markets
    if "markets" in cfg:
        # New format: run multiple monitors
        markets = cfg["markets"]
        services = [
            MonitorService(cfg, market["symbol"], market.get("interval", "1m"))
            for market in markets
        ]
        try:
            asyncio.run(run_monitors(services))
        except KeyboardInterrupt:
            LOG.info("Stopped by user.")
    else:
        # Old format: single monitor
        service = MonitorService(cfg)
        try:
            asyncio.run(service.run())
        except KeyboardInterrupt:
            LOG.info("Stopped by user.")


if __name__ == "__main__":
    main()
