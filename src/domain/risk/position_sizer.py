"""Confidence-based position sizing (TDD §6.5) — pure, no I/O.

Confidence bet yuzdeleri config'den gelir (ARCH_GUARD Kural 6).
Sabit tavan (max_single_bet_usdc) KALDIRILDI — yuzde bazli cap yeterli.
"""
from __future__ import annotations

REENTRY_MULTIPLIER = 0.80
POLYMARKET_MIN_ORDER_USDC = 5.0


def confidence_position_size(
    confidence: str,
    bankroll: float,
    confidence_bet_pct: dict[str, float],
    max_bet_pct: float = 0.05,
    is_reentry: bool = False,
) -> float:
    """Confidence tier bazli pozisyon boyutu.

    confidence_bet_pct: config'den gelen {"A": 0.05, "B": 0.04} dict.
    Tabloda olmayan confidence → 0 (entry bloklanir).
    Cap: bankroll × max_bet_pct. Sabit USDC tavan YOK.
    """
    bet_pct = confidence_bet_pct.get(confidence, 0.0)
    if bet_pct == 0.0:
        return 0.0

    if is_reentry:
        bet_pct *= REENTRY_MULTIPLIER

    size = bankroll * bet_pct
    size = min(size, bankroll * max_bet_pct, bankroll)
    return max(0.0, round(size, 2))
