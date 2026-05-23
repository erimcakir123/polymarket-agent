"""Tennis EdgeCandidate -> Signal adapter (Stage 2 PLAN-TENNIS-001).

Tennis predictor (Klaassen-Magnus + features) outputs a P(YES)-aligned
probability (see src/strategy/enrichment/tennis_market_enricher.py:220-225 —
`model_p = prediction.probability` is compared against `market.yes_price`).
This module wraps a qualified EdgeCandidate plus its source MarketData into
a Signal that the main EntryProcessor can consume.

The function is pure: no I/O, no global state, no side effects.
Sizing (size_usdc) is intentionally 0.0 — the entry gate computes size later.
"""
from __future__ import annotations

from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.signal import Signal
from src.strategy.entry.tennis_entry import EdgeCandidate

# sport_tag (2026-05-24): dashboard Sport ROI treemap `<category>_<league>` formatına
# göre grup yapıyor (trade_logger._split_sport_tag). gamma_client wta-/atp- slug'ları
# her ikisini de "tennis"e normalize ediyor; tour ayrımı candidate.tour üzerinden
# (parser slug prefix'inden çıkarır) gelir → ATP "tennis_atp", WTA "tennis_wta".
_TENNIS_ATP_SPORT_TAG = "tennis_atp"
_TENNIS_WTA_SPORT_TAG = "tennis_wta"


def tennis_candidate_to_signal(
    candidate: EdgeCandidate,
    market: MarketData,
    tier: str,
) -> Signal:
    """Convert a tennis EdgeCandidate (+ its MarketData) into a Signal.

    Args:
        candidate: Qualified tennis prediction with signed `edge`.
        market: Source Polymarket market the candidate was computed against.
        tier: Confidence tier from `classify_tier` — "A" or "B".

    Returns:
        Signal with anchor_probability = candidate.model_p (already P(YES)),
        direction derived from sign(edge), all bookmaker fields zeroed (tennis
        has no bookmaker consensus), and sport_tag derived from candidate.tour
        ("atp" → "tennis_atp", "wta" → "tennis_wta").
    """
    direction = Direction.BUY_YES if candidate.edge > 0 else Direction.BUY_NO
    # sport_tag derived from candidate.tour (parser sets it from slug prefix)
    sport_tag = _TENNIS_WTA_SPORT_TAG if candidate.tour == "wta" else _TENNIS_ATP_SPORT_TAG

    return Signal(
        condition_id=market.condition_id,
        direction=direction,
        anchor_probability=candidate.model_p,  # P(YES) — preserved, NOT remapped
        market_price=candidate.market_p,
        edge=candidate.edge,
        confidence=tier,
        size_usdc=0.0,  # gate sizing computes later
        entry_reason=EntryReason.TENNIS,
        bookmaker_prob=0.0,  # tennis has no bookmaker consensus
        num_bookmakers=0,
        has_sharp=False,
        sport_tag=sport_tag,
        event_id=market.event_id or "",
    )
