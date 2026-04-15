"""position_sizer.py için birim testler (TDD §6.5)."""
from __future__ import annotations

from src.domain.risk.position_sizer import (
    CONF_BET_PCT,
    POLYMARKET_MIN_ORDER_USDC,
    confidence_position_size,
)


def test_A_confidence_5pct_of_bankroll() -> None:
    # $1000 × 5% = $50
    assert confidence_position_size("A", bankroll=1000) == 50.0


def test_B_confidence_4pct_of_bankroll() -> None:
    # $1000 × 4% = $40
    assert confidence_position_size("B", bankroll=1000) == 40.0


def test_C_confidence_returns_zero() -> None:
    assert confidence_position_size("C", bankroll=1000) == 0.0


def test_max_single_bet_cap() -> None:
    # $10_000 × 5% = $500, ama cap $75
    assert confidence_position_size("A", bankroll=10_000) == 75.0


def test_max_bet_pct_cap() -> None:
    # Büyük bankroll + düşük cap → cap uygulanır
    # $10_000 × 5% = $500 ama max_bet_pct=0.01 → $100
    # Ayrıca max_bet_usdc=1000 (cap devre dışı)
    result = confidence_position_size("A", bankroll=10_000, max_bet_usdc=1_000, max_bet_pct=0.01)
    assert result == 100.0


def test_reentry_multiplier() -> None:
    # B, reentry → 0.04 × 0.8 = 0.032 → $32
    assert confidence_position_size("B", bankroll=1000, is_reentry=True) == 32.0


def test_zero_bankroll_returns_zero() -> None:
    assert confidence_position_size("A", bankroll=0) == 0.0


def test_conf_bet_pct_table_values() -> None:
    assert CONF_BET_PCT["A"] == 0.05
    assert CONF_BET_PCT["B"] == 0.04
    # C → girmez, tabloda yok
    assert "C" not in CONF_BET_PCT


def test_polymarket_min_constant() -> None:
    assert POLYMARKET_MIN_ORDER_USDC == 5.0
