"""Zemin çözücü: Sackmann harita → override (TTL) → Wikipedia → event-link.
Tek enjekte bağımlılık; dispatch çağırır. _match_surface (pure) tekrar kullanılır."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

from src.models.market import MarketData
from src.strategy.enrichment.tennis_dispatch import _extract_location, _match_surface

logger = logging.getLogger(__name__)

_DEFAULT_TTL_DAYS = 1


def _is_stale(checked_at: str, now_iso: str, ttl_days: int) -> bool:
    """UNKNOWN kaydı TTL'den eski mi (pure). Bozuk damga → stale."""
    try:
        return (datetime.fromisoformat(now_iso) - datetime.fromisoformat(checked_at)).days >= ttl_days
    except (ValueError, TypeError):
        return True


class SurfaceResolver:
    def __init__(
        self,
        surface_map: dict[str, str],
        wiki=None,
        overrides: dict[str, dict] | None = None,
        save_fn: Callable[[dict], None] | None = None,
        event_tournaments: dict[str, str] | None = None,
        ttl_days: int = _DEFAULT_TTL_DAYS,
        now_iso: str = "",
    ) -> None:
        self._map = surface_map or {}
        self._wiki = wiki
        self._overrides = overrides if overrides is not None else {}
        self._save_fn = save_fn
        self._event = event_tournaments or {}
        self._ttl = ttl_days
        self._now = now_iso
        self.unresolved: set[str] = set()

    def set_event_tournaments(self, mapping: dict[str, str]) -> None:
        self._event = mapping or {}

    def resolve(self, market: MarketData) -> str | None:
        name = _extract_location(market.question or "")
        if name is None and market.event_id:
            name = self._event.get(market.event_id)
        if not name:
            return None
        surf = _match_surface(name, self._map)
        return surf if surf else self._via_wiki(name)

    def _via_wiki(self, name: str) -> str | None:
        if self._wiki is None:
            self.unresolved.add(name.lower())
            return None
        key = name.lower().strip()
        now = self._now or self._runtime_now()
        cached = self._overrides.get(key)
        if cached:
            # Bulunan zemin kalıcı kabul edilir (turnuva zemin değiştirirse — çok nadir,
            # ör. Stuttgart 10 yılda bir — Sackmann harita yeniden-build'i yakalar). UNKNOWN ise GÜNLÜK tekrar denenir (TTL=1g).
            if cached["surface"] != "UNKNOWN":
                return cached["surface"]
            if not _is_stale(cached.get("checked_at", ""), now, self._ttl):
                self.unresolved.add(key)
                return None
        surf = self._wiki.resolve_surface(name)
        self._overrides[key] = {"surface": surf or "UNKNOWN", "checked_at": now}
        if self._save_fn is not None:
            self._save_fn(self._overrides)
        if surf is None:
            self.unresolved.add(key)
            logger.warning("Tenis zemin çözülemedi (Wiki dahil): %s", name)
        return surf

    @staticmethod
    def _runtime_now() -> str:
        return datetime.now().isoformat()
