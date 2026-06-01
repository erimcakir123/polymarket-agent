"""Force-close alert state — per-condition tek seferlik bildirim.

Kullanıcı kararı (2026-06-01):
  Force-close artık otomatik exit YAPMAZ. Eşik geçince:
    1. Tek seferlik Telegram alarm
    2. Dashboard'da kırmızı border (computed.py okur)
    3. Pozisyon hold — kullanıcı manuel karar verir

Bu modül o tek-seferlik bildirimin durumunu tutar (atomic JSON write).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


_DEFAULT_PATH = Path("data/force_close_alerts.json")


class ForceCloseAlertStore:
    """{condition_id: alert_timestamp_iso}. Tek seferlik bildirim takibi."""

    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self._path = path
        self._state: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("force_close_alerts load failed: %s", exc)
            return {}

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def is_alerted(self, condition_id: str) -> bool:
        return condition_id in self._state

    def mark_alerted(self, condition_id: str, at_utc: str) -> None:
        self._state[condition_id] = at_utc
        self._persist()

    def alerted_condition_ids(self) -> set[str]:
        """Dashboard için: kırmızı border isteyen pozisyon set'i."""
        return set(self._state.keys())

    def clear(self, condition_id: str) -> None:
        """Pozisyon kapatıldığında alarm state'i temizle."""
        if condition_id in self._state:
            del self._state[condition_id]
            self._persist()


def load_alerted_ids(path: Optional[Path] = None) -> set[str]:
    """Standalone helper — dashboard computed.py için tek-shot okuma."""
    store = ForceCloseAlertStore(path or _DEFAULT_PATH)
    return store.alerted_condition_ids()
