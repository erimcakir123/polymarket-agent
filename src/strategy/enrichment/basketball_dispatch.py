"""Basketball market dispatch — model anchor öncelik, moneyline fallback.

Tennis_dispatch paterni birebir paralel. Sport_tag basketball lig'lerinden ise
(nba/wnba/ncaab/cbb/wncaab/euroleague) model çalışır; aksi halde bookmaker
fallback. Eksik ratings veya bilinmeyen takım slug'ı durumunda:
  - moneyline: bookmaker fallback OK (mevcut güvenlik ağı)
  - alt market (totals/spreads): trade YASAK (cascade bug önleme)

Lig-spesifik parametreler config'den alınır (basketball.leagues[sport]).
"""
from __future__ import annotations

import re
from typing import Callable

from src.config.settings import BasketballConfig
from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.calibration.curve import CalibrationCurve
from src.domain.matching.basketball_team_resolver import resolve_team_pair
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.team_elo import EloRating
from src.models.market import MarketData
from src.strategy.enrichment.basketball_anchor_enricher import (
    enrich_basketball_from_model,
)

_BASKETBALL_LEAGUES = frozenset({
    "nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague",
})
_CBB_ALIAS = "ncaab"  # Polymarket "cbb" tag NCAAB ile aynı lig
_MONEYLINE_TYPES = ("moneyline", "h2h", "")

_OVER_LINE_RE = re.compile(
    r"(?:over|under|total|totals)\s+(\d+\.?\d*)", re.IGNORECASE,
)
_SPREAD_RE = re.compile(r"[+-]\d+\.?\d*")


def _normalize_league(sport_tag: str) -> str:
    """Polymarket sport_tag → basketball lig anahtarı."""
    s = sport_tag.lower()
    if s == "cbb":
        return _CBB_ALIAS
    return s


def _infer_market_type(market: MarketData) -> str:
    """Polymarket bazen sports_market_type'ı boş bırakır; slug'tan çıkar."""
    declared = (market.sports_market_type or "").strip().lower()
    if declared:
        return declared
    slug = (market.slug or "").lower()
    if "spread" in slug:
        return "spreads"
    if "total" in slug or "over" in slug or "under" in slug:
        return "totals"
    return "moneyline"


def _extract_line(question: str, market_type: str) -> float | None:
    """Question stringinden totals/spreads line çıkar."""
    q = question or ""
    mt = market_type.lower()
    if mt == "totals":
        m = _OVER_LINE_RE.search(q)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    if mt == "spreads":
        m = _SPREAD_RE.search(q)
        if m:
            try:
                return float(m.group(0))
            except ValueError:
                return None
    return None


def enrich_with_basketball_dispatch(
    market: MarketData,
    bookmaker_enricher: Callable[[MarketData], EnrichResult],
    ratings: dict[str, dict[str, EloRating]],
    efficiencies: dict[str, dict[str, TeamEfficiency]],
    basketball_cfg: BasketballConfig,
    calibration_curves: dict[str, CalibrationCurve] | None = None,
) -> EnrichResult:
    """Basketball ise model, değilse veya yetersiz veri ise bookmaker fallback.

    ratings/efficiencies: {league: {team: rating/efficiency}}.
    Alt market'lerde fallback YASAK (cascade bug önleme).
    """
    sport = (market.sport_tag or "").lower()
    if sport not in _BASKETBALL_LEAGUES:
        return bookmaker_enricher(market)

    league = _normalize_league(sport)
    market_type = _infer_market_type(market)
    is_moneyline = market_type in _MONEYLINE_TYPES

    league_ratings = ratings.get(league, {})
    league_eff = efficiencies.get(league, {})
    if not league_ratings or not league_eff:
        if is_moneyline:
            return bookmaker_enricher(market)
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_BASKETBALL_DATA_MISSING,
        )

    resolved = resolve_team_pair(market.slug or "", league=league)
    if not resolved.ok or resolved.home is None or resolved.away is None:
        if is_moneyline:
            return bookmaker_enricher(market)
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_TEAM_NOT_IN_RATINGS,
        )

    params = basketball_cfg.leagues.get(league)
    if params is None:
        # Lig config yoksa default (NBA)
        home_adv, blend, m_std, t_std = 100.0, 0.55, 11.0, 20.0
    else:
        home_adv = params.home_advantage
        blend = params.blend_elo
        m_std = params.margin_std
        t_std = params.total_std

    line = _extract_line(market.question or "", market_type)
    model_result = enrich_basketball_from_model(
        home_team=resolved.home, away_team=resolved.away,
        market_type=market_type, league=league,
        ratings=league_ratings, efficiencies=league_eff,
        home_advantage=home_adv, blend_elo=blend,
        line=line, calibration_curves=calibration_curves,
        margin_std=m_std, total_std=t_std,
    )
    if model_result.probability is not None:
        return model_result
    if is_moneyline:
        return bookmaker_enricher(market)
    return model_result
