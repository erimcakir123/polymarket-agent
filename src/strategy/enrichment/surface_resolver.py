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
# 2026-06-10 kullanıcı kararı: FOUND kayıtları 6 ay sonra, turnuva yeniden
# GÖRÜNDÜĞÜNDE Wikipedia'dan sessizce yeniden doğrulanır (takvim değil dönüş tetikler).
_DEFAULT_FOUND_RECHECK_DAYS = 180


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
        found_recheck_days: int = _DEFAULT_FOUND_RECHECK_DAYS,
    ) -> None:
        self._map = surface_map or {}
        self._wiki = wiki
        self._overrides = overrides if overrides is not None else {}
        self._save_fn = save_fn
        self._reload_fn = reload_fn
        self._event = event_tournaments or {}
        self._ttl = ttl_days
        self._found_ttl = found_recheck_days
        self._now = now_iso
        self.unresolved: set[str] = set()
        # 2026-06-10 "görünce-tazele": eski FOUND kaydı yeniden doğrulanırken zemin
        # değiştiyse buraya yazılır → health monitor SURFACE_CHANGED bilgisi yollar.
        self.surface_changes: dict[str, tuple[str, str]] = {}

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
        cached = self._overrides.get(key) or {}
        found_old: str | None = (
            cached.get("surface") if cached.get("surface") not in (None, "UNKNOWN") else None
        )
        # FOUND + taze (≤6 ay) → doğrudan kullan. Eski ise aşağıda yeniden doğrulanır
        # ("görünce-tazele": tetik takvim değil, turnuvanın yeniden görünmesi).
        if found_old is not None and not _is_stale(cached.get("checked_at", ""), now, self._found_ttl):
            return found_old
        if self._wiki is None:
            if found_old is not None:
                return found_old  # doğrulayamayız; eski bilgi > hiç bilgi
            self.unresolved.add(key)
            return None
        # UNKNOWN damgası taze ise (günlük TTL) tekrar sorma.
        if cached and found_old is None and not _is_stale(
            cached.get("checked_at", ""), now, self._ttl,
        ):
            self.unresolved.add(key)
            return None
        surf = self._wiki.resolve_surface(name)
        if found_old is not None:
            old = found_old
            if surf is None or surf == old:
                # Aynı kaldı / doğrulanamadı → eski zemin korunur, damga tazelenir.
                self._overrides[key] = {"surface": old, "checked_at": now}
                self._save()
                return old
            self._overrides[key] = {"surface": surf, "checked_at": now}
            self.surface_changes[key] = (old, surf)
            self._save()
            logger.warning("Tenis zemin DEĞİŞTİ: %s %s→%s (otomatik güncellendi)", name, old, surf)
            return surf
        self._overrides[key] = {"surface": surf or "UNKNOWN", "checked_at": now}
        self._save()
        if surf is None:
            self.unresolved.add(key)
            logger.warning("Tenis zemin çözülemedi (Wiki dahil): %s", name)
        return surf

    def _save(self) -> None:
        if self._save_fn is not None:
            self._save_fn(self._overrides)

    @staticmethod
    def _runtime_now() -> str:
        # UTC-aware: override damgaları diğer yazarlarla (sim/elle ekleme) tutarlı olsun.
        # Eski naive damgalar _is_stale'de TypeError→stale sayılır → kendiliğinden tazelenir.
        from datetime import timezone  # noqa: PLC0415
        return datetime.now(timezone.utc).isoformat()
