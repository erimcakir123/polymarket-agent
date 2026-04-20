"""Telegram bildirim servisi — entry/exit/circuit breaker olayları.

Rate-limit aware: Telegram 30 msg/sn sınırı. Burada basit throttle (min gap).
LIVE/PAPER/DRY_RUN moddan bağımsız çalışır, config.telegram.enabled kontrol eder.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"
_MIN_GAP_SEC = 0.5  # Ardışık mesajlar arası min bekleme (throttle)
_DEFAULT_TIMEOUT = 5


def _default_http_post(url: str, json: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.post(url, json=json, timeout=timeout)


class TelegramNotifier:
    """Telegram bot mesaj gönderici. enabled=False → no-op (güvenli)."""

    def __init__(
        self,
        enabled: bool = False,
        bot_token: str = "",
        chat_id: str = "",
        http_post: Callable[..., Any] = _default_http_post,
    ) -> None:
        self.enabled = enabled and bool(bot_token) and bool(chat_id)
        self._token = bot_token
        self._chat_id = chat_id
        self._http = http_post
        self._last_send_ts: float = 0.0

    def send(self, text: str) -> bool:
        """Mesaj gönder. enabled=False ise no-op True döner."""
        if not self.enabled:
            return True
        # Throttle
        gap = time.time() - self._last_send_ts
        if gap < _MIN_GAP_SEC:
            time.sleep(_MIN_GAP_SEC - gap)
        try:
            url = _API_BASE.format(token=self._token)
            resp = self._http(url, json={
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }, timeout=_DEFAULT_TIMEOUT)
            self._last_send_ts = time.time()
            return getattr(resp, "status_code", 0) == 200
        except Exception as e:
            logger.warning("Telegram send failed: %s", e)
            return False

    # ── Semantic helpers (entry/exit/breaker) ──

    def notify_entry(self, slug: str, direction: str, entry_price: float,
                     size_usdc: float, confidence: str,
                     entry_reason: str) -> bool:
        msg = (f"🟢 <b>ENTRY</b> — {slug[:50]}\n"
               f"{direction} @ ${entry_price:.3f} × ${size_usdc:.2f}\n"
               f"Conf {confidence} · {entry_reason}")
        return self.send(msg)

    def notify_exit(self, slug: str, exit_price: float,
                    realized_pnl: float, reason: str) -> bool:
        emoji = "✅" if realized_pnl >= 0 else "🔴"
        msg = (f"{emoji} <b>EXIT</b> — {slug[:50]}\n"
               f"@ ${exit_price:.3f} · PnL ${realized_pnl:+.2f}\n"
               f"Reason: {reason}")
        return self.send(msg)

    def notify_circuit_breaker(self, reason: str, active_until: str = "") -> bool:
        msg = f"⚠️ <b>CIRCUIT BREAKER</b>\n{reason}"
        if active_until:
            msg += f"\nUntil: {active_until}"
        return self.send(msg)
