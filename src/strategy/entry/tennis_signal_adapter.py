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

_DEFAULT_TENNIS_SPORT_TAG = "tennis"


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
        direction derived from sign(edge), and all bookmaker fields zeroed
        (tennis does not use bookmaker consensus).
    """
    direction = Direction.BUY_YES if candidate.edge > 0 else Direction.BUY_NO
    sport_tag = market.sport_tag or _DEFAULT_TENNIS_SPORT_TAG

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
