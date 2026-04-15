"""Bankroll formülü — pure (TDD §6.5).

Tek formül, tek yer. PortfolioManager.recalculate_bankroll ve
presentation/cli bu fonksiyonu kullanır (DRY).
"""
from __future__ import annotations


def compute_bankroll(
    initial_bankroll: float,
    realized_pnl: float,
    total_invested: float,
) -> float:
    """bankroll = initial + realized − açık pozisyon size'larının toplamı."""
    return initial_bankroll + realized_pnl - total_invested
