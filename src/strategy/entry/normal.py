"""Normal entry kararı — bookmaker P(YES) vs market yes_price → Signal.

Pure: domain'den calculate_edge + position_sizer kullanır.
"""
from __future__ import annotations

from src.domain.analysis.edge import calculate_edge
from src.domain.analysis.probability import BookmakerProbability
from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.signal import Signal


def evaluate(
    market: MarketData,
    bm_prob: BookmakerProbability,
    min_edge: float = 0.06,
    spread: float = 0.0,
    slippage: float = 0.0,
) -> Signal | None:
    """Normal entry: edge varsa Signal döner, yoksa None.

    Pozisyon boyutu bu aşamada 0 — gate orchestrator sizing uygular.
    """
    if bm_prob.confidence == "C":
        return None  # C-conf = girmez

    direction, edge = calculate_edge(
        anchor_prob=bm_prob.probability,
        market_yes_price=market.yes_price,
        min_edge=min_edge,
        confidence=bm_prob.confidence,
        spread=spread,
        slippage=slippage,
    )
    if direction == Direction.SKIP:
        return None

    return Signal(
        condition_id=market.condition_id,
        direction=direction,
        anchor_probability=bm_prob.probability,
        market_price=market.yes_price,
        edge=edge,
        confidence=bm_prob.confidence,
        size_usdc=0.0,  # Gate sizing uygulayacak
        entry_reason=EntryReason.NORMAL,
        bookmaker_prob=bm_prob.bookmaker_prob,
        num_bookmakers=bm_prob.num_bookmakers,
        has_sharp=bm_prob.has_sharp,
        sport_tag=market.sport_tag,
        event_id=market.event_id or "",
    )
