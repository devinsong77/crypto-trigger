# BTCUSDT 本地监控服务

文件说明：
- `btc_monitor.py`：主程序
- `config_default.json`：默认配置
- `config_trend_follow.json`：趋势跟随配置
- `config_mean_reversion.json`：均值回归配置
- `config_volatility_watch.json`：波动预警配置

安装：
```bash
pip install websockets
```

运行：
```bash
python btc_monitor.py --config config_default.json
```

如果 OpenClaw 在本机默认端口运行，请确保：
- `hooks.enabled=true`
- `hooks.token` 与配置文件中的 `openclaw.token` 一致
- `url` 指向 `http://127.0.0.1:18789/hooks/agent`
