"""Veri kaynağı sağlık takibi — fallback state machine.

3 ardışık başarısızlıkta kaynak deaktif olur (yedeğe geçilir). Bir başarı
counter'ı sıfırlar. Persisted JSON state — bot reboot'ta da hatırlanır.

ARCH_GUARD §12 uyumu: sessiz hata yok. Tüm I/O hataları log + degrade.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.infrastructure.data.basketball.schemas import SourceStatus

logger = logging.getLogger(__name__)

FALLBACK_THRESHOLD = 3


class HealthTracker:
    """Veri kaynaklarının (nba_api, espn) sağlık durumunu JSON'da tutar."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._state: dict[str, SourceStatus] = self._load()

    def _load(self) -> dict[str, SourceStatus]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("HealthTracker load failed — starting fresh: %s", exc)
            return {}
        out: dict[str, SourceStatus] = {}
        for row in raw:
            try:
                st = SourceStatus.model_validate(row)
                out[st.source] = st
            except Exception as exc:  # noqa: BLE001
                logger.warning("HealthTracker row drop: %s", exc)
        return out

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [s.model_dump() for s in self._state.values()]
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def _get_or_create(self, source: str) -> SourceStatus:
        if source not in self._state:
            self._state[source] = SourceStatus(
                source=source,  # type: ignore[arg-type]
                last_success_utc=None,
                last_fail_utc=None,
                consecutive_fails=0,
                active=True,
            )
        return self._state[source]

    def is_active(self, source: str) -> bool:
        return self._get_or_create(source).active

    def consecutive_fails(self, source: str) -> int:
        return self._get_or_create(source).consecutive_fails

    def record_success(self, source: str, at_utc: str) -> None:
        cur = self._get_or_create(source)
        self._state[source] = cur.model_copy(update={
            "last_success_utc": at_utc,
            "consecutive_fails": 0,
            "active": True,
        })
        self._persist()

    def record_failure(self, source: str, at_utc: str) -> None:
        cur = self._get_or_create(source)
        new_fails = cur.consecutive_fails + 1
        self._state[source] = cur.model_copy(update={
            "last_fail_utc": at_utc,
            "consecutive_fails": new_fails,
            "active": new_fails < FALLBACK_THRESHOLD,
        })
        self._persist()
        if new_fails >= FALLBACK_THRESHOLD:
            logger.warning("Source %s deactivated after %d consecutive failures", source, new_fails)
