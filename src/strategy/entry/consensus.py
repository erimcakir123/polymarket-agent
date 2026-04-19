"""Consensus entry — bookmaker ve market aynı favoriye işaret ediyor (TDD §6.4).

Mantık:
  is_consensus = (book_prob >= 0.50) == (market.yes_price >= 0.50)
  Eğer is_consensus AND market_price >= min_price (default 65¢):
    direction = favori taraf (BUY_YES if market YES'i favori, else BUY_NO)
    entry_price = effective price
    edge = 0.99 - entry_price (payout potential — hold-to-resolve mantığı)

Bu strateji "iki bağımsız kaynak da X'i favori görüyor" güvencesiyle çalışır.
Edge "neredeyse kesin kazanır → 99¢'e doğru ilerler" varsayımına dayanır.

**EV guard** (84¢ Spurs bug'ı fix'i): Bookmaker'in bizim tarafımıza verdiği
olasılık entry_price'in altındaysa trade NEGATIF EV — reddedilir.
Örnek: book Spurs %82, PM Spurs 84¢ → break-even %84.8 gerekli → SKIP.
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
    max_price: float = 0.75,
) -> Signal | None:
    """Consensus entry kararı. None döner: koşullar uymuyor."""
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

    # max_price tavanı — 75¢+ girişlerde R/R dar (near-resolve 94¢ → ≤19¢ potansiyel)
    # Sinir dahil red: entry_price > max_price (> degil >= cunku 0.80 tam sinirda drift
    # riskli; max_price = 0.75 ile zaten ~5¢ buffer var)
    if entry_price > max_price:
        return None

    # EV guard — bookmaker'in bizim tarafa olasiligi entry'den yuksek olmali
    # (Aksi takdirde payout < stake * win_prob → negatif EV)
    our_side_prob = bm_prob.probability if direction == Direction.BUY_YES else 1.0 - bm_prob.probability
    if our_side_prob < entry_price:
        return None  # Negatif EV — bet reddedilir

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
        sport_tag=market.sport_tag,
        event_id=market.event_id or "",
    )
