"""SPEC-Z9 (2026-06-03): Polymarket roster drift detector.

İki katman koruma:
  A) Lig içi takım listesi drift (yeni promosyon / alias değişimi)
  B) Yeni lig keşfi (Polymarket'te aktive ama bizim yok)

Her boot'ta + günde 1 (12h tick) çalışır. Gamma /teams ve /sports endpoint'leri
ile mevcut resolver dict + _SLUG_PREFIX_SPORT karşılaştırılır. Tespit edilen
drift → telegram alert (HealthMonitor Alert pattern paralel).

Otomatik düzeltme YAPILMAZ — sadece tespit + alert. Manuel review tercih
edilir çünkü yeni alias = name değişimi olabilir (örn rebrand) ve standart
abbreviation eşlemesi tahminden öte düşünce gerektirir.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from src.domain.matching.basketball_team_resolver import (
    _ACB_TEAMS,
    _BSL_TEAMS,
    _LEGA_TEAMS,
    _VTB_TEAMS,
)
from src.infrastructure.apis.gamma_client import GammaClient

logger = logging.getLogger(__name__)


# Lig code (Polymarket sport) → resolver dict eşleşmesi.
# Yeni lig eklendikçe genişletilecek (SPEC-EUROBASKET-001 + sonraki sprintler).
_LEAGUE_DICTS: dict[str, dict[str, str]] = {
    "bkligend": _ACB_TEAMS,
    "bkbsl": _BSL_TEAMS,
    "bkseriea": _LEGA_TEAMS,
    "bkvtb": _VTB_TEAMS,
}


@dataclass(frozen=True)
class DriftAlert:
    """Tek drift kaydı. HealthMonitor.Alert ile uyumlu (severity/category/message)."""
    severity: str  # "warning" | "info"
    category: str  # "ROSTER_DRIFT_<league>" | "NEW_LEAGUE_DETECTED"
    message: str


class RosterDriftMonitor:
    """Polymarket /teams + /sports endpoint'i ile dict drift tespiti."""

    def __init__(
        self,
        gamma_client: GammaClient,
        league_dicts: dict[str, dict[str, str]] | None = None,
    ) -> None:
        self._gamma = gamma_client
        self._dicts = league_dicts if league_dicts is not None else _LEAGUE_DICTS

    def check_all(self) -> list[DriftAlert]:
        """4 lig roster drift + yeni lig keşfi → birleşik alert listesi."""
        alerts: list[DriftAlert] = []
        alerts.extend(self.check_roster_drift())
        alerts.extend(self.check_new_leagues())
        return alerts

    def check_roster_drift(self) -> list[DriftAlert]:
        """Her aktif lig için Polymarket slug token'ları ↔ resolver dict diff.

        SADECE `abbreviation` field karşılaştırılır — bu Polymarket'in gerçek
        slug token'ı (örn "rea"). `alias` field human-readable name ("Real
        Madrid") tutar, slug değil → drift detector için yararsız (false pos).

        OBSOLETE check YOK çünkü resolver dict'imiz bilinçli olarak çoklu
        name variant'larla zenginleştirilmiş ("rea"+"madrid"+"realmadrid"
        hepsi RM). Polymarket sadece kanonik abbreviation döner → obsolete
        diff her zaman büyük olur (bilinçli zenginleştirme yanlış teşhis
        edilir). Eksik (MISSING) tek anlamlı sinyal.
        """
        alerts: list[DriftAlert] = []
        for league_code, team_dict in self._dicts.items():
            try:
                teams = self._gamma.fetch_teams_by_league_code(league_code)
            except Exception as exc:  # noqa: BLE001 — API boundary
                logger.warning(
                    "RosterDrift: /teams fetch fail league=%s err=%s", league_code, exc,
                )
                continue
            polymarket_slugs = {
                str(t.get("abbreviation", "")).strip().lower()
                for t in teams if t.get("abbreviation")
            }
            polymarket_slugs.discard("")
            dict_keys = set(team_dict.keys())
            missing = polymarket_slugs - dict_keys
            if missing:
                sample = sorted(missing)[:5]
                name_lookup = {
                    str(t.get("abbreviation", "")).strip().lower(): t.get("name", "?")
                    for t in teams
                }
                detail = ", ".join(f"{a}={name_lookup.get(a, '?')}" for a in sample)
                alerts.append(DriftAlert(
                    severity="warning",
                    category=f"ROSTER_DRIFT_{league_code}",
                    message=(
                        f"Polymarket'te {len(missing)} yeni slug bulundu (resolver'da yok): "
                        f"{detail}. _<LIG>_TEAMS dict'ine eklenmeli, yoksa o maçlar skip edilir."
                    ),
                ))
        return alerts

    def check_new_leagues(self) -> list[DriftAlert]:
        """Polymarket /sports ↔ _SLUG_PREFIX_SPORT diff — bk* yeni lig keşfi."""
        try:
            sports = self._gamma.fetch_sports_metadata()
        except Exception as exc:  # noqa: BLE001
            logger.warning("RosterDrift: /sports fetch fail err=%s", exc)
            return []
        from src.infrastructure.apis.gamma_client import _SLUG_PREFIX_SPORT  # noqa: PLC0415
        known_prefixes = set(_SLUG_PREFIX_SPORT.keys())
        polymarket_bk_codes = {
            str(s.get("sport", "")).strip()
            for s in sports
            if str(s.get("sport", "")).startswith("bk")
        }
        polymarket_bk_codes.discard("")
        missing = polymarket_bk_codes - known_prefixes
        if not missing:
            return []
        # gamma /sports response'unda 'name' field YOK — 'resolution' URL'i
        # kullan (örn 'https://www.acb.com/' → kullanıcı manuel keşfeder)
        url_lookup = {
            str(s.get("sport", "")).strip(): str(s.get("resolution", "")).strip()
            for s in sports
        }
        sample = sorted(missing)
        detail = ", ".join(
            f"{c}={url_lookup.get(c, '?') or '?'}" for c in sample
        )
        return [DriftAlert(
            severity="info",
            category="NEW_LEAGUE_DETECTED",
            message=(
                f"Polymarket'te bizim haritada olmayan {len(missing)} basket lig: "
                f"{detail}. Scraper + resolver dict ekleyerek aktive et."
            ),
        )]
