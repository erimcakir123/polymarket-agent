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
    # 2026-06-01 yetki genişletme: gerçek veri kaynağı doğrulandı.
    # nba_api: g_league + summer_league. euroleague-api: eurocup.
    # bsl/acb/lega kapsam dışı (veri kaynağı placeholder).
    "g_league", "summer_league", "eurocup",
})
_CBB_ALIAS = "ncaab"  # Polymarket "cbb" tag NCAAB ile aynı lig
_MONEYLINE_TYPES = ("moneyline", "h2h", "")
# Yetki filtre (2026-06-01): bizim model maç-tipi market'ler için tasarlandı.
# Futures (Champion, MVP), prop (player stats, head coach) modelimiz dışında.
# Slug'da bu pattern'ler varsa model çalışmamalı (cascade bug yerine fail-fast).
_NON_MATCH_SLUG_KEYWORDS = frozenset({
    "champion", "mvp", "draft", "coach", "next-team", "next-coach",
    "to-be-traded", "will-be-traded", "retire", "record-quadruple",
    "rookie-of-the-year", "player-of-the-year", "defensive-player",
    "all-star", "scoring-leader", "assist-leader", "rebound-leader",
    "block-leader", "postseason", "will-anthony", "will-stephen",
    "will-victor", "will-lebron", "cover-athlete", "2k-cover",
})
# Tennis ITF paterni paralel — preseason/exhibition rating güvenilmez (roster
# henüz oturmamış, K-factor yüksek volatilite). Ekim NBA preseason + Kasım NCAAB
# exhibition öncesi yetki filtresi aktif. Slug'da bu pattern varsa model SUS.
_LOW_TIER_SLUG_KEYWORDS = frozenset({
    "preseason", "exhibition", "play-in-tournament",
})
# Elo "phi" karşılığı: yeterli maç oynamamış takım = güvenilmez rating.
# Sezon başı (ilk 2 hafta) volatilite yüksek; ~10+ maç sonrası rating sabitlenir.
_MIN_GAMES_FOR_TRADE = 10


def _is_non_match_market(slug: str, question: str) -> bool:
    """Slug veya question'da futures/prop pattern varsa True."""
    s = (slug or "").lower()
    q = (question or "").lower()
    return any(k in s or k in q for k in _NON_MATCH_SLUG_KEYWORDS)


def _is_low_tier_basket(slug: str, question: str) -> bool:
    """Preseason/exhibition/play-in market'i mi? Yetki dışı (rating güvenilmez)."""
    s = (slug or "").lower()
    q = (question or "").lower()
    return any(k in s or k in q for k in _LOW_TIER_SLUG_KEYWORDS)

_OVER_LINE_RE = re.compile(
    r"(?:over|under|total|totals)\s+(\d+\.?\d*)", re.IGNORECASE,
)
_SPREAD_RE = re.compile(r"[+-]\d+\.?\d*")
# Polymarket slug pattern: "wnba-sea-dal-2026-06-01-total-171pt5" (171.5)
# Slug'da "pt" decimal separator olarak kullanılır (Polymarket convention).
_SLUG_TOTAL_RE = re.compile(r"-total-(\d+)(?:pt(\d+))?", re.IGNORECASE)
_SLUG_SPREAD_RE = re.compile(r"-spread-([+-]?\d+)(?:pt(\d+))?", re.IGNORECASE)


def _slug_line_with_pt(int_part: str, frac_part: str | None) -> float | None:
    """Polymarket 'pt' decimal'i parse et: ('171', '5') → 171.5."""
    try:
        return float(int_part) + (float(f"0.{frac_part}") if frac_part else 0.0)
    except ValueError:
        return None


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


def _extract_line(
    question: str, market_type: str, slug: str = "",
) -> float | None:
    """Totals/spreads line çıkar — önce slug (Polymarket pattern), sonra question fallback."""
    q = question or ""
    s = slug or ""
    mt = market_type.lower()
    if mt == "totals":
        # Önce slug: "...-total-171pt5" → 171.5
        sm = _SLUG_TOTAL_RE.search(s)
        if sm:
            line = _slug_line_with_pt(sm.group(1), sm.group(2))
            if line is not None:
                return line
        # Fallback question
        m = _OVER_LINE_RE.search(q)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    if mt == "spreads":
        # Önce slug: "...-spread-7pt5" → 7.5
        sm = _SLUG_SPREAD_RE.search(s)
        if sm:
            line = _slug_line_with_pt(sm.group(1), sm.group(2))
            if line is not None:
                return line
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

    # Yetki filtre (2026-06-01): futures/prop market'lerde modelimiz konuşamaz.
    # Sadece maç-tipi market'lerde (moneyline/totals/spread/quarter) bahis aç.
    if _is_non_match_market(market.slug or "", market.question or ""):
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_BASKETBALL_DATA_MISSING,
        )

    # Tennis ITF paralel — preseason/exhibition rating güvenilmez. Yetki dışı.
    if _is_low_tier_basket(market.slug or "", market.question or ""):
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_TEAM_NOT_IN_RATINGS,
        )

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

    # Yetki filtresi — tennis phi paralel. Yetersiz maç oynamış takım rating
    # güvenilmez (sezon başı, expansion, yeni promosyon). Pratik eşik: 10+ maç.
    home_rating = league_ratings.get(resolved.home)
    away_rating = league_ratings.get(resolved.away)
    if home_rating is None or away_rating is None:
        if is_moneyline:
            return bookmaker_enricher(market)
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_TEAM_NOT_IN_RATINGS,
        )
    if (home_rating.games < _MIN_GAMES_FOR_TRADE
            or away_rating.games < _MIN_GAMES_FOR_TRADE):
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

    line = _extract_line(
        market.question or "", market_type, slug=market.slug or "",
    )
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
