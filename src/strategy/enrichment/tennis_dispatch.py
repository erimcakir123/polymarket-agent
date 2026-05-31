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

Surface/best_of tahmini Polymarket veri yetersizliği nedeniyle default:
- Surface: "Hard" (Polymarket genelde belirtmez)
- Best_of: 3 (Grand Slam keyword'ü ile 5'e yükseltilir)

Bu defaults Adım 4 (calibration) sonrası rafine edilir.
"""
from __future__ import annotations

from typing import Callable

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
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
_MONEYLINE_TYPES = ("moneyline", "h2h", "")


def _infer_best_of(question: str) -> int:
    q_low = (question or "").lower()
    if any(k in q_low for k in _GRAND_SLAM_KEYWORDS):
        return 5
    return _DEFAULT_BEST_OF


def enrich_with_tennis_dispatch(
    market: MarketData,
    bookmaker_enricher: Callable[[MarketData], EnrichResult],
    ratings: dict[str, PlayerSnapshot],
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

    best_of = _infer_best_of(market.question)
    model_result = enrich_tennis_from_model(
        player_a=player_a,
        player_b=player_b,
        market_type=market_type,
        surface=_DEFAULT_SURFACE,
        best_of=best_of,
        ratings=ratings,
    )
    if model_result.probability is not None:
        return model_result

    # Model fail — moneyline için bookmaker fallback OK; alt market için fail.
    if is_moneyline:
        return bookmaker_enricher(market)
    return model_result
