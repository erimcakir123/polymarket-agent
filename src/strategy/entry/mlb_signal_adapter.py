"""MLB EdgeCandidate → Signal adapter (SPEC-R Plan 4 T1).

Tennis Lab pattern (SPEC-O). Pure function, no I/O.
P(YES) preserved (anchor_probability = candidate.model_p, unchanged).
"""
from __future__ import annotations

from src.domain.mlb_submarket.edge_candidate import EdgeCandidate
from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.signal import Signal


_MLB_SPORT_TAG = "baseball_mlb"


_BIMODAL_MARKET_TYPES: frozenset[str] = frozenset({"totals", "run_line", "spreads"})


def mlb_candidate_to_signal(
    candidate: EdgeCandidate,
    market: MarketData,
    tier: str,
    fixed_bet_usdc: dict[str, float],
    bimodal_bet_usdc: dict[str, float] | None = None,
) -> Signal:
    """Convert MLB EdgeCandidate to a Signal for EntryProcessor.process_signals.

    SPEC-U (2026-05-23): bimodal-aware sizing.
    - moneyline → fixed_bet_usdc (eski sizing)
    - totals + run_line + spreads → bimodal_bet_usdc (tenis paritesi)

    Args:
        candidate: Qualified edge with model_p (P(YES)) and signed edge.
        market: Source Polymarket market.
        tier: Confidence tier ("A" or "B").
        fixed_bet_usdc: Non-bimodal sizing dict.
        bimodal_bet_usdc: Bimodal sizing dict. None → fixed_bet_usdc'ye düşer (backward-compat).

    Returns:
        Signal with model anchor (bookmaker fields zeroed).
    """
    direction = Direction.BUY_YES if candidate.edge > 0 else Direction.BUY_NO
    is_bimodal = candidate.market_type in _BIMODAL_MARKET_TYPES
    if is_bimodal and bimodal_bet_usdc is not None:
        size = bimodal_bet_usdc.get(tier, 0.0)
    else:
        size = fixed_bet_usdc.get(tier, 0.0)
    return Signal(
        condition_id=market.condition_id,
        direction=direction,
        anchor_probability=candidate.model_p,  # P(YES) — preserved
        market_price=candidate.market_p,
        edge=candidate.edge,
        confidence=tier,
        size_usdc=size,
        entry_reason=EntryReason.MLB_SUBMARKET,
        bookmaker_prob=0.0,
        num_bookmakers=0,
        has_sharp=False,
        sport_tag=_MLB_SPORT_TAG,
        event_id=market.event_id or "",
    )
