"""Directional entry (SPEC-017) — bookmaker favoriye fiyat aralığında giriş.

Edge hesabı YOK. Favori + fiyat aralığı + existing gate guards.

Direction:  anchor >= 0.50 → BUY_YES
            anchor <  0.50 → BUY_NO

Effective entry price:  BUY_YES → yes_price
                        BUY_NO  → 1 - yes_price
"""
from __future__ import annotations

from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.position import effective_win_prob
from src.models.signal import Signal


def evaluate_directional(
    market: MarketData,
    anchor: float,
    confidence: str,
    min_favorite_probability: float = 0.60,
    min_entry_price: float = 0.60,
    max_entry_price: float = 0.85,
) -> Signal | None:
    """Directional entry kararı.

    Returns Signal eligible ise, None değilse.
    Edge hesabı yok — favori tarafa makul fiyat aralığında giriş.
    """
    direction = Direction.BUY_YES if anchor >= 0.50 else Direction.BUY_NO
    win_prob = effective_win_prob(anchor, direction.value)

    if win_prob < min_favorite_probability:
        return None

    effective_price = (
        market.yes_price if direction == Direction.BUY_YES
        else 1.0 - market.yes_price
    )
    if not (min_entry_price <= effective_price <= max_entry_price):
        return None

    return Signal(
        condition_id=market.condition_id,
        direction=direction,
        anchor_probability=anchor,
        market_price=market.yes_price,
        confidence=confidence,
        size_usdc=0.0,  # Gate sizing uygulayacak
        entry_reason=EntryReason.DIRECTIONAL,
        bookmaker_prob=anchor,  # anchor IS the bookmaker consensus probability
        sport_tag=market.sport_tag,
        event_id=market.event_id or "",
    )
