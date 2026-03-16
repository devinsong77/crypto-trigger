#!/usr/bin/env python3
"""
Crypto Trigger - BTCUSDT monitor for OpenClaw.

What it does:
- Backfills historical klines from Binance REST.
- Subscribes to Binance Spot WebSocket kline stream.
- Computes common technical indicators in pure Python:
  SMA, EMA, RSI, MACD, Bollinger Bands, ATR, volume SMA, ROC.
- Evaluates configurable alert rules.
- Triggers a local OpenClaw agent through /hooks/agent.

Modular structure:
- src/utils.py: Utility functions
- src/models.py: Data models (Candle)
- src/indicators.py: Technical indicators (IndicatorEngine)
- src/rules.py: Rule evaluation (RuleEngine)
- src/exchange.py: Binance data source (BinanceSource)
- src/notifier.py: OpenClaw notifications (OpenClawNotifier)
- src/monitor.py: Main monitoring service (MonitorService)
- src/main.py: Entry point

Dependencies:
  pip install -r requirements.txt

Run:
  python btc_monitor.py --config config_comprehensive.json
"""

from src.main import main

if __name__ == "__main__":
    main()
