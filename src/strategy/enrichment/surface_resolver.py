"""Zemin çözücü: Sackmann harita → override (TTL) → Wikipedia → event-link.
Tek enjekte bağımlılık; dispatch çağırır. _match_surface (pure) tekrar kullanılır."""
from __future__ import annotations

import logging

from src.infrastructure.data.tennis_surface_override_store import is_stale, save_overrides
from src.models.market import MarketData
from src.strategy.enrichment.tennis_dispatch import _extract_location, _match_surface

logger = logging.getLogger(__name__)

_DEFAULT_TTL_DAYS = 3


class SurfaceResolver:
    def __init__(
        self,
        surface_map: dict[str, str],
        wiki=None,
        overrides: dict[str, dict] | None = None,
        override_path=None,
        event_tournaments: dict[str, str] | None = None,
        ttl_days: int = _DEFAULT_TTL_DAYS,
        now_iso: str = "",
    ) -> None:
        self._map = surface_map or {}
        self._wiki = wiki
        self._overrides = overrides if overrides is not None else {}
        self._override_path = override_path
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
        if surf:
            return surf
        # Set-handicap ve benzeri durumlarda question prefix yüzeyden bilgi taşımaz;
        # event_id üzerinden turnuva bağlantısı varsa önce onu dene (Wiki'den önce).
        if market.event_id:
            event_name = self._event.get(market.event_id)
            if event_name and event_name.lower().strip() != name.lower().strip():
                event_surf = _match_surface(event_name, self._map)
                if event_surf:
                    return event_surf
        return self._via_wiki(name)

    def _via_wiki(self, name: str) -> str | None:
        if self._wiki is None:
            self.unresolved.add(name.lower())
            return None
        key = name.lower().strip()
        now = self._now or self._runtime_now()
        cached = self._overrides.get(key)
        if cached:
            if cached["surface"] != "UNKNOWN":
                return cached["surface"]
            if not is_stale(cached.get("checked_at", ""), now, self._ttl):
                self.unresolved.add(key)
                return None
        surf = self._wiki.resolve_surface(name)
        self._overrides[key] = {"surface": surf or "UNKNOWN", "checked_at": now}
        if self._override_path is not None:
            save_overrides(self._overrides, self._override_path)
        if surf is None:
            self.unresolved.add(key)
            logger.warning("Tenis zemin çözülemedi (Wiki dahil): %s", name)
        return surf

    @staticmethod
    def _runtime_now() -> str:
        from datetime import datetime
        return datetime.now().isoformat()
