"""Confidence-based position sizing (TDD §6.5) — pure, no I/O.

Confidence bet yuzdeleri config'den gelir (ARCH_GUARD Kural 6).
max_bet_usdc cap (SPEC-010) + max_bet_pct cap (yuzde) birlikte uygulanir.
SPEC-016: win_probability parametresi stake'i direction-adjusted prob ile carpar.
"""
from __future__ import annotations

REENTRY_MULTIPLIER = 0.80
POLYMARKET_MIN_ORDER_USDC = 5.0


def confidence_position_size(
    confidence: str,
    bankroll: float,
    confidence_bet_pct: dict[str, float],
    max_bet_usdc: float = 50.0,
    max_bet_pct: float = 0.05,
    is_reentry: bool = False,
    win_probability: float = 1.0,
) -> float:
    """Confidence tier + probability-weighted pozisyon boyutu.

    Formula: stake = bankroll × bet_pct × win_probability (SPEC-016)

    Args:
        confidence_bet_pct: config'den {"A": 0.05, "B": 0.04}.
        max_bet_usdc: USDC cinsinden tek-bet tavan (SPEC-010: $50).
        max_bet_pct: bankroll % cinsinden tavan.
        win_probability: direction-adjusted win prob (default 1.0 = legacy).

    Tabloda olmayan confidence → 0. Cap: min(size, max_bet_usdc, max_bet_pct).
    Floor: size < POLYMARKET_MIN_ORDER_USDC → 0 (entry blocked).
    """
    bet_pct = confidence_bet_pct.get(confidence, 0.0)
    if bet_pct == 0.0:
        return 0.0

    if is_reentry:
        bet_pct *= REENTRY_MULTIPLIER

    size = bankroll * bet_pct * win_probability
    size = min(size, max_bet_usdc, bankroll * max_bet_pct, bankroll)
    size = round(size, 2)

    if size < POLYMARKET_MIN_ORDER_USDC:
        return 0.0
    return size
