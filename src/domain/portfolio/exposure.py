"""Exposure guard — pure function (TDD §6.15 cap).

Toplam yatırılan ($size_usdc)/bankroll > max_exposure_pct ise entry bloklanır.
"""
from __future__ import annotations


def exceeds_exposure_limit(
    positions: dict,
    candidate_size: float,
    bankroll: float,
    max_exposure_pct: float,
) -> bool:
    """True: candidate_size eklendiğinde exposure cap aşılır.

    positions: Position objects dict (her biri .size_usdc'ye sahip).
    """
    if bankroll <= 0:
        return True
    total_invested = sum(getattr(p, "size_usdc", 0.0) for p in positions.values())
    return (total_invested + candidate_size) / bankroll > max_exposure_pct


def fill_ratio(positions: dict, bankroll: float) -> float:
    """Pozisyon doluluk oranı = toplam yatırılan / bankroll. 0.0-1.0+."""
    if bankroll <= 0:
        return 0.0
    total_invested = sum(getattr(p, "size_usdc", 0.0) for p in positions.values())
    return total_invested / bankroll
