"""
OpenClaw notification service.
"""

import json
import logging
import ssl
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, Optional

LOG = logging.getLogger(__name__)


class OpenClawNotifier:
    """Sends notifications to OpenClaw agent."""

    def __init__(self, cfg: Dict[str, Any]):
        self.url = cfg["url"].rstrip("/")
        self.token = cfg["token"]
        self.timeout = cfg.get("timeout_seconds", 10)
        self.name = cfg.get("name", "BTCMonitor")
        self.session_key_prefix = cfg.get("session_key_prefix", "hook:market:")
        self.deliver = bool(cfg.get("deliver", True))
        self.channel = cfg.get("channel", "last")
        self.to: Optional[str] = cfg.get("to")
        self.wake_mode = cfg.get("wake_mode", "now")
        self.model: Optional[str] = cfg.get("model")
        self.thinking: Optional[str] = cfg.get("thinking")
        self.ssl_context = ssl.create_default_context()

    def send(self, symbol: str, title: str, body: str) -> None:
        """Send a notification to OpenClaw."""
        payload = {
            "message": body,
            "name": self.name,
            "sessionKey": f"{self.session_key_prefix}{symbol.lower()}",
            "wakeMode": self.wake_mode,
            "deliver": self.deliver,
            "channel": self.channel,
            "timeoutSeconds": self.timeout
        }
        if self.to:
            payload["to"] = self.to
        if self.model:
            payload["model"] = self.model
        if self.thinking:
            payload["thinking"] = self.thinking

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "btc-monitor/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as resp:
                LOG.info("OpenClaw notified: %s, http=%s", title, resp.status)
        except urllib.error.HTTPError as e:
            LOG.error("OpenClaw HTTP error: %s %s", e.code, e.read().decode("utf-8", errors="ignore"))
        except Exception as e:
            LOG.exception("OpenClaw notify failed: %s", e)
