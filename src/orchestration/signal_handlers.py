"""SIGTERM/SIGINT → graceful shutdown. systemd stop temiz kapanma yapsın."""
from __future__ import annotations

import logging
import signal
from typing import Callable

logger = logging.getLogger(__name__)


def build_shutdown_handler(stop_callback: Callable[[], None]) -> Callable[[int, object], None]:
    """Sinyal handler üret — stop_callback'i çağırır, hata bastırır."""
    def _handler(signum: int, _frame: object) -> None:
        logger.info("Signal %s alındı — graceful shutdown başlatılıyor", signum)
        try:
            stop_callback()
        except Exception as e:  # noqa: BLE001 — sinyal handler içinde raise etme
            logger.error("Shutdown callback hatası: %s", e)
    return _handler


def install_graceful_shutdown(stop_callback: Callable[[], None]) -> None:
    """SIGTERM + SIGINT'i graceful stop'a bağla."""
    handler = build_shutdown_handler(stop_callback)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
