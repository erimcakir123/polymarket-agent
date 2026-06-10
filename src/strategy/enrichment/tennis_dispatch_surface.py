"""Surface-aware tennis dispatch (üretim — factory yüzey dosyası varsa bunu kullanır).

enrich_with_tennis_dispatch'i sarar: markete zemin çözer, o zeminin reyting
dict'ini seçer, ana dispatch'e devreder. Yetki-dışı/tenis-dışı markette zemin
ARAMAZ (sahte SURFACE_UNKNOWN önlenir). lab_v2 kökenli; 2026-06-02'den beri ana botta.
"""
from __future__ import annotations

from typing import Callable

from src.domain.analysis.enrich_outcome import EnrichResult
from src.domain.pricing.tennis.calibration import CalibrationCurve
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.models.market import MarketData
from src.strategy.enrichment.tennis_dispatch import (
    _is_low_tier_tennis,
    enrich_with_tennis_dispatch as _main_dispatch,
)


def make_surface_aware_dispatch(
    ratings_by_surface: dict[str, dict[str, PlayerSnapshot]],
):
    """Factory: returns enrich function that picks ratings dict by surface.

    Usage:
        dispatch_fn = make_surface_aware_dispatch(load_all_surfaces(...))
        # monkey-patch:
        import src.strategy.enrichment.tennis_dispatch as td
        td.enrich_with_tennis_dispatch = dispatch_fn
    """
    fallback_ratings = ratings_by_surface.get("Hard", {})

    def enrich(
        market: MarketData,
        bookmaker_enricher: Callable[[MarketData], EnrichResult],
        ratings: dict[str, PlayerSnapshot],  # IGNORED — surface'a gore dict secilir
        calibration_curves: dict[str, CalibrationCurve] | None = None,
        glicko_weight: float = 0.6,
        max_phi_for_trade: float = 100.0,
        low_tier_slug_prefixes: tuple[str, ...] = ("itf-", "challenger-", "futures-"),
        low_tier_question_keywords: tuple[str, ...] = (
            "ITF", "Futures", "Challenger", "M15", "M25", "W15", "W25",
        ),
        surface_resolver=None,
        model_ml_disabled_surfaces: tuple[str, ...] = (),
    ) -> EnrichResult:
        # 2026-06-10: tenis-dışı veya yetki-dışı (ITF/Challenger) markette zemin
        # ARANMAZ — bot bunları zaten oynamaz; boşa Wiki sorgusu + sahte
        # SURFACE_UNKNOWN alarmı üretiyordu (03:22 "itf madrid" olayı).
        sport = (market.sport_tag or "").lower()
        skip_resolve = sport != "tennis" or _is_low_tier_tennis(
            market.slug or "", market.question or "",
            slug_prefixes=low_tier_slug_prefixes,
            question_keywords=low_tier_question_keywords,
        )
        surface = (
            surface_resolver.resolve(market)
            if (surface_resolver is not None and not skip_resolve) else None
        )
        chosen = ratings_by_surface.get(surface, fallback_ratings) if surface else fallback_ratings
        return _main_dispatch(
            market=market,
            bookmaker_enricher=bookmaker_enricher,
            ratings=chosen,
            calibration_curves=calibration_curves,
            glicko_weight=glicko_weight,
            max_phi_for_trade=max_phi_for_trade,
            low_tier_slug_prefixes=low_tier_slug_prefixes,
            low_tier_question_keywords=low_tier_question_keywords,
            surface_resolver=surface_resolver,
            model_ml_disabled_surfaces=model_ml_disabled_surfaces,
        )

    return enrich
