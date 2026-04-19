"""Confidence-based position sizing (TDD §6.5) — pure, no I/O.

Confidence bet yuzdeleri config'den gelir (ARCH_GUARD Kural 6).
max_bet_usdc cap (SPEC-010) + max_bet_pct cap (yuzde) birlikte uygulanir.
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
) -> float:
    """Confidence tier bazli pozisyon boyutu.

    Args:
        confidence_bet_pct: config'den {"A": 0.05, "B": 0.04}.
        max_bet_usdc: USDC cinsinden tek-bet tavan (SPEC-010: $50).
        max_bet_pct: bankroll % cinsinden tavan.

    Tabloda olmayan confidence → 0 (entry bloklanir).
    Cap: min(bankroll*bet_pct, max_bet_usdc, bankroll*max_bet_pct, bankroll).
    """
    bet_pct = confidence_bet_pct.get(confidence, 0.0)
    if bet_pct == 0.0:
        return 0.0

    if is_reentry:
        bet_pct *= REENTRY_MULTIPLIER

    size = bankroll * bet_pct
    size = min(size, max_bet_usdc, bankroll * max_bet_pct, bankroll)
    return max(0.0, round(size, 2))
