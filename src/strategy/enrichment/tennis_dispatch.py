"""Tennis market dispatch — model anchor öncelik, moneyline fallback.

Karar matrisi:
  sport != tennis              → bookmaker fallback
  sport == tennis, ratings yok → bookmaker fallback (model çalışmaz)
  sport == tennis, player yok  → bookmaker fallback
  sport == tennis, model OK    → model döner (A confidence)
  sport == tennis, model fail VE moneyline → bookmaker fallback
  sport == tennis, model fail VE alt market → fail (bot trade etmez)

Alt market fallback YASAK — eski cascade bug (h2h fiyatını yapıştırma) bu modülün
çözdüğü asıl sorundur.

Tahminler (Polymarket veri yetersizliği nedeniyle question stringinden):
- Surface: Hard default; Clay/Grass keyword'leri turnuva ismi geçerse
- Best_of: 3 default; Grand Slam keyword'ü ile 5
- line/handicap: market_type'a göre question regex (set/games/handicap)
"""
from __future__ import annotations

import re
from typing import Callable

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.pricing.tennis.calibration import CalibrationCurve
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.models.market import MarketData
from src.strategy.enrichment.question_parser import extract_teams
from src.strategy.enrichment.tennis_anchor_enricher import enrich_tennis_from_model

_DEFAULT_SURFACE = "Hard"
_DEFAULT_BEST_OF = 3
_GRAND_SLAM_KEYWORDS = (
    "grand slam", "us open", "australian open", "wimbledon",
    "french open", "roland garros", "rolandgarros",
)
# Surface inference — turnuva keyword → kort tipi. Sackmann naming convention.
_CLAY_KEYWORDS = (
    "french open", "roland garros", "rolandgarros", "monte carlo",
    "madrid open", "rome", "italian open", "barcelona", "hamburg",
    "estoril", "houston",
)
_GRASS_KEYWORDS = (
    "wimbledon", "queen's", "queens club", "halle", "eastbourne",
    "stuttgart", "mallorca", "newport",
)
_MONEYLINE_TYPES = ("moneyline", "h2h", "")


def _infer_best_of(question: str) -> int:
    q_low = (question or "").lower()
    if any(k in q_low for k in _GRAND_SLAM_KEYWORDS):
        return 5
    return _DEFAULT_BEST_OF


def _resolve_player_name(
    name: str,
    ratings: dict[str, PlayerSnapshot],
) -> str | None:
    """Polymarket name → Sackmann full name eşleme.

    Sıra: exact → case-insensitive exact → last-name substring (tek eşleşme).
    Ambiguous (2+ aynı soyad) → None (güvenli, atla).
    """
    if name in ratings:
        return name
    name_low = name.lower().strip()
    ci_match = [k for k in ratings if k.lower() == name_low]
    if ci_match:
        return ci_match[0]
    parts_match = [k for k in ratings if name_low in k.lower().split()]
    if len(parts_match) == 1:
        return parts_match[0]
    return None


def _infer_surface(question: str) -> str:
    q_low = (question or "").lower()
    if any(k in q_low for k in _CLAY_KEYWORDS):
        return "Clay"
    if any(k in q_low for k in _GRASS_KEYWORDS):
        return "Grass"
    return _DEFAULT_SURFACE


_HANDICAP_RE = re.compile(r"[+-]\d+\.?\d*", re.IGNORECASE)
_OVER_LINE_RE = re.compile(r"(?:over|under|total|totals)\s+(\d+\.?\d*)", re.IGNORECASE)


def _extract_market_params(
    question: str,
    market_type: str,
) -> tuple[float | None, float | None]:
    """Question stringinden line + handicap çıkar (market_type'a göre).

    Returns: (line, handicap). Bulamazsa None.
    """
    q = question or ""
    mt = market_type.lower()
    if mt == "tennis_set_handicap":
        m = _HANDICAP_RE.search(q)
        if m:
            try:
                return None, float(m.group(0))
            except ValueError:
                return None, None
        return None, None
    if mt in ("tennis_match_totals", "tennis_first_set_totals", "tennis_set_totals"):
        m = _OVER_LINE_RE.search(q)
        if m:
            try:
                return float(m.group(1)), None
            except ValueError:
                return None, None
        return None, None
    return None, None


def enrich_with_tennis_dispatch(
    market: MarketData,
    bookmaker_enricher: Callable[[MarketData], EnrichResult],
    ratings: dict[str, PlayerSnapshot],
    calibration_curves: dict[str, CalibrationCurve] | None = None,
) -> EnrichResult:
    """Tennis ise model, değilse veya yetersiz veri ise bookmaker fallback.

    Alt market'lerde fallback YASAK — cascade bug (h2h fiyatını her marketa
    yapıştırma) tam burada kapanır.
    """
    sport = (market.sport_tag or "").lower()
    if sport != "tennis":
        return bookmaker_enricher(market)

    market_type = (market.sports_market_type or "").lower()
    is_moneyline = market_type in _MONEYLINE_TYPES

    if not ratings:
        if is_moneyline:
            return bookmaker_enricher(market)
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.EMPTY_BOOKMAKERS)

    player_a, player_b = extract_teams(market.question)
    if not player_a or not player_b:
        if is_moneyline:
            return bookmaker_enricher(market)
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.TEAM_EXTRACT_FAILED)

    # Polymarket genelde soyadı gönderir ("Hurkacz"), Sackmann full name
    # ("Hubert Hurkacz") saklar. Soyadı substring + ambiguity safety ile çöz.
    resolved_a = _resolve_player_name(player_a, ratings)
    resolved_b = _resolve_player_name(player_b, ratings)
    if resolved_a is None or resolved_b is None:
        if is_moneyline:
            return bookmaker_enricher(market)
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.EVENT_NO_MATCH)
    player_a, player_b = resolved_a, resolved_b

    best_of = _infer_best_of(market.question)
    surface = _infer_surface(market.question)
    line, handicap = _extract_market_params(market.question, market_type)
    model_result = enrich_tennis_from_model(
        player_a=player_a,
        player_b=player_b,
        market_type=market_type,
        surface=surface,
        best_of=best_of,
        ratings=ratings,
        calibration_curves=calibration_curves,
        line=line,
        handicap=handicap,
    )
    if model_result.probability is not None:
        return model_result

    # Model fail — moneyline için bookmaker fallback OK; alt market için fail.
    if is_moneyline:
        return bookmaker_enricher(market)
    return model_result
