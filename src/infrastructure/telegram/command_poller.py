"""Telegram command poller --- /stop komutu ile botu uzaktan durdurma.

Background thread'de Telegram getUpdates long-poll yapar.
Sadece config'teki chat_id'den gelen /stop komutunu kabul eder.
Callback pattern: Agent request_stop'u callback olarak verir.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org/bot{token}"
_POLL_TIMEOUT_SEC = 10
_ERROR_BACKOFF_SEC = 5


class TelegramCommandPoller:
    """Telegram'dan /stop komutu dinler. enabled=False veya token boşsa no-op."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        on_stop: Callable[[], None],
        http_get: Callable[..., Any] | None = None,
        http_post: Callable[..., Any] | None = None,
    ) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._on_stop = on_stop
        self._http_get = http_get or requests.get
        self._http_post = http_post or requests.post
        self._offset: int = 0
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="tg-cmd-poller")
        self._thread.start()
        logger.info("Telegram command poller started")

    def stop(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        while self._running:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._handle(update)
            except Exception as e:
                logger.warning("Telegram poll error: %s", e)
                time.sleep(_ERROR_BACKOFF_SEC)

    def _get_updates(self) -> list[dict]:
        url = f"{_API_BASE.format(token=self._token)}/getUpdates"
        resp = self._http_get(url, params={
            "offset": self._offset,
            "timeout": _POLL_TIMEOUT_SEC,
            "allowed_updates": '["message"]',
        }, timeout=_POLL_TIMEOUT_SEC + 5)
        data = resp.json()
        return data.get("result", [])

    def _handle(self, update: dict) -> None:
        self._offset = update["update_id"] + 1
        msg = update.get("message", {})
        text = (msg.get("text") or "").strip().lower()
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if chat_id != self._chat_id:
            return

        if text == "/stop":
            logger.info("Telegram /stop received from chat %s", chat_id)
            self._send_reply("Bot durduruluyor...")
            self._on_stop()

    def _send_reply(self, text: str) -> None:
        try:
            url = f"{_API_BASE.format(token=self._token)}/sendMessage"
            self._http_post(url, json={
                "chat_id": self._chat_id,
                "text": text,
            }, timeout=5)
        except Exception as e:
            logger.warning("Telegram reply failed: %s", e)
