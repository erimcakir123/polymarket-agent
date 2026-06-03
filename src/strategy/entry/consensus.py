"""Consensus entry — bookmaker ve market aynı favoriye işaret ediyor (DECISIONS §6.4).

Mantık:
  is_consensus = (book_prob >= 0.50) == (market.yes_price >= 0.50)
  Eğer is_consensus AND market_price >= min_price (default 65¢):
    direction = favori taraf (BUY_YES if market YES'i favori, else BUY_NO)
    entry_price = effective price
    edge = 0.99 - entry_price (payout potential — hold-to-resolve mantığı)

Bu strateji "iki bağımsız kaynak da X'i favori görüyor" güvencesiyle çalışır.
Edge "neredeyse kesin kazanır → 99¢'e doğru ilerler" varsayımına dayanır.
"""
from __future__ import annotations

from src.domain.analysis.probability import BookmakerProbability
from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.signal import Signal


def evaluate(
    market: MarketData,
    bm_prob: BookmakerProbability,
    min_price: float = 0.65,
    min_model_edge: float = 0.0,
) -> Signal | None:
    """Consensus entry kararı. None döner: koşullar uymuyor.

    SPEC-Z13 (2026-06-03): min_model_edge guard. Direction-adjusted model
    edge (anchor vs entry) bu eşiğin altıysa consensus iptal — eski
    "0.99 - entry_price" formülü modeli umursamıyordu, Azkara tipi -%5
    edge trade'leri bypass ediyordu.
    """
    if bm_prob.confidence == "C":
        return None  # Yetersiz veri

    book_favors_yes = bm_prob.probability >= 0.50
    mkt_favors_yes = market.yes_price >= 0.50
    is_consensus = book_favors_yes == mkt_favors_yes

    if not is_consensus:
        return None  # İki kaynak farklı tarafta → consensus yok

    # Hangi taraftayız?
    if book_favors_yes:
        direction = Direction.BUY_YES
        entry_price = market.yes_price
    else:
        direction = Direction.BUY_NO
        entry_price = market.no_price

    # min_price eşiği — 65¢+ "ciddi favori" göstergesi
    if entry_price < min_price:
        return None

    # SPEC-Z13: Model edge direction-adjusted (BUY_YES: P(YES) - YES_price;
    # BUY_NO: P(NO) - NO_price = (1-P(YES)) - (1-YES_price) = YES_price - P(YES)).
    if direction == Direction.BUY_YES:
        model_edge = bm_prob.probability - market.yes_price
    else:  # BUY_NO
        model_edge = market.yes_price - bm_prob.probability
    if model_edge < min_model_edge:
        return None  # Model "ucuz" demiyor → consensus iptal

    edge = max(0.0, 0.99 - entry_price)

    return Signal(
        condition_id=market.condition_id,
        direction=direction,
        anchor_probability=bm_prob.probability,
        market_price=market.yes_price,
        edge=edge,
        confidence=bm_prob.confidence,
        size_usdc=0.0,  # Gate sizing uygular
        entry_reason=EntryReason.CONSENSUS,
        bookmaker_prob=bm_prob.bookmaker_prob,
        num_bookmakers=bm_prob.num_bookmakers,
        has_sharp=bm_prob.has_sharp,
        source=bm_prob.source,
        sport_tag=market.sport_tag,
        event_id=market.event_id or "",
    )
