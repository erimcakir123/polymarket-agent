"""Confidence-based position sizing (TDD §6.5) — pure, no I/O.

v2: A=%5, B=%4, C=blok (girmez). Ağır favori (eff ≥ %90) × 1.5, lossy reentry × 0.8.
Tek trade max $75, max bankroll %5, Polymarket min $5.
"""
from __future__ import annotations

CONF_BET_PCT: dict[str, float] = {
    "A": 0.05,
    "B": 0.04,
    # C → 0 (girmez)
}

HEAVY_FAVORITE_THRESHOLD = 0.90
HEAVY_FAVORITE_MULTIPLIER = 1.50
REENTRY_MULTIPLIER = 0.80
POLYMARKET_MIN_ORDER_USDC = 5.0


def confidence_position_size(
    confidence: str,
    bankroll: float,
    max_bet_usdc: float = 75.0,
    max_bet_pct: float = 0.05,
    is_reentry: bool = False,
    market_price: float = 0.0,
) -> float:
    """Confidence tier bazlı pozisyon boyutu. C → 0 (entry bloklanır).

    Cap'ler: tek trade max_bet_usdc, bankroll × max_bet_pct, bankroll.
    Polymarket min_order: 5 USDC altı → caller blocked.
    """
    if confidence == "C":
        return 0.0

    bet_pct = CONF_BET_PCT.get(confidence, 0.04)

    if market_price >= HEAVY_FAVORITE_THRESHOLD:
        bet_pct *= HEAVY_FAVORITE_MULTIPLIER

    if is_reentry:
        bet_pct *= REENTRY_MULTIPLIER

    size = bankroll * bet_pct
    size = min(size, max_bet_usdc, bankroll * max_bet_pct, bankroll)
    return max(0.0, round(size, 2))
