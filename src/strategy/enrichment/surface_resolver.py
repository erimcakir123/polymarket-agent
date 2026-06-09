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
        reload_fn: Callable[[], dict] | None = None,
    ) -> None:
        self._map = surface_map or {}
        self._wiki = wiki
        self._overrides = overrides if overrides is not None else {}
        self._save_fn = save_fn
        self._reload_fn = reload_fn
        self._event = event_tournaments or {}
        self._ttl = ttl_days
        self._now = now_iso
        self.unresolved: set[str] = set()

    def set_event_tournaments(self, mapping: dict[str, str]) -> None:
        self._event = mapping or {}

    def refresh_overrides(self) -> None:
        """Override dosyasını yeniden oku (elle eklenen override'lar reload'sız uygulansın).
        reload_fn infra'dan enjekte edilir (factory); resolver infra import etmez."""
        if self._reload_fn is not None:
            fresh = self._reload_fn()
            if isinstance(fresh, dict):
                self._overrides = fresh

    def resolve(self, market: MarketData) -> str | None:
        name = _extract_location(market.question or "")
        if name is None and market.event_id:
            name = self._event.get(market.event_id)
        if not name:
            return None
        surf = _match_surface(name, self._map)
        if surf:
            return surf
        # "Stuttgart Open, Qualification" / "Libema Open (Doubles)" gibi aşama-ekli
        # adlar: ek-öncesi çekirdeğe düş → ana tablonun override'ı/haritası varyantlara
        # miras kalır, çözülemezse alarm da çekirdek adla atılır (tek override hepsini kapatır).
        core = name.split(",", 1)[0].split("(", 1)[0].strip()
        if core and core != name:
            surf = _match_surface(core, self._map)
            if surf:
                return surf
            name = core
        return self._via_wiki(name)

    def _via_wiki(self, name: str) -> str | None:
        # Override kontrolü Wikipedia'dan BAĞIMSIZ: istemci yokken/çökükken bile
        # elle eklenen düzeltmeler uygulanır (2026-06-10).
        key = name.lower().strip()
        now = self._now or self._runtime_now()
        cached = self._overrides.get(key)
        if cached is not None and cached.get("surface") != "UNKNOWN":
            return cached["surface"]
        if self._wiki is None:
            self.unresolved.add(key)
            return None
        # Bulunan zemin kalıcı kabul edilir (yukarıda döndü; turnuva zemin değiştirirse
        # Sackmann harita yeniden-build'i yakalar). UNKNOWN ise GÜNLÜK tekrar denenir (TTL).
        if cached and not _is_stale(cached.get("checked_at", ""), now, self._ttl):
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
