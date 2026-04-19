"""position_sizer.py icin birim testler (TDD §6.5) — config-driven."""
from __future__ import annotations

from src.domain.risk.position_sizer import (
    POLYMARKET_MIN_ORDER_USDC,
    confidence_position_size,
)

BET_PCT = {"A": 0.05, "B": 0.04}


def test_A_confidence_5pct_of_bankroll() -> None:
    assert confidence_position_size("A", bankroll=1000, confidence_bet_pct=BET_PCT) == 50.0


def test_B_confidence_4pct_of_bankroll() -> None:
    assert confidence_position_size("B", bankroll=1000, confidence_bet_pct=BET_PCT) == 40.0


def test_C_confidence_returns_zero() -> None:
    assert confidence_position_size("C", bankroll=1000, confidence_bet_pct=BET_PCT) == 0.0


def test_max_bet_usdc_cap_applied() -> None:
    """max_bet_usdc cap: bankroll*pct > cap olsa bile cap devrede (SPEC-010)."""
    result = confidence_position_size(
        "A", bankroll=10_000,
        confidence_bet_pct=BET_PCT,
        max_bet_usdc=50.0,
    )
    # 10_000 × 5% = 500, ama cap 50 → 50
    assert result == 50.0


def test_max_bet_usdc_below_cap_not_clipped() -> None:
    """bankroll dusukse cap devrede degil."""
    result = confidence_position_size(
        "A", bankroll=500,
        confidence_bet_pct=BET_PCT,
        max_bet_usdc=50.0,
    )
    # 500 × 5% = 25, cap 50 → 25
    assert result == 25.0


def test_max_bet_usdc_default_cap_50() -> None:
    """SPEC-010: default max_bet_usdc=50."""
    result = confidence_position_size(
        "A", bankroll=10_000, confidence_bet_pct=BET_PCT,
    )
    # Default max_bet_usdc=50, 10_000 × 5% = 500 → capped at 50
    assert result == 50.0


def test_max_bet_pct_cap() -> None:
    """max_bet_pct cap: pct-tavan, max_bet_usdc=200 ile usdc cap devrede degil."""
    result = confidence_position_size(
        "A", bankroll=10_000, confidence_bet_pct=BET_PCT,
        max_bet_usdc=200.0, max_bet_pct=0.01,
    )
    # 10_000 × 5% = 500, pct cap 0.01 → 100, usdc cap 200 → 100
    assert result == 100.0


def test_reentry_multiplier() -> None:
    result = confidence_position_size(
        "B", bankroll=1000, confidence_bet_pct=BET_PCT, is_reentry=True,
    )
    assert result == 32.0


def test_zero_bankroll_returns_zero() -> None:
    assert confidence_position_size("A", bankroll=0, confidence_bet_pct=BET_PCT) == 0.0


def test_unknown_confidence_returns_zero() -> None:
    assert confidence_position_size("X", bankroll=1000, confidence_bet_pct=BET_PCT) == 0.0


def test_polymarket_min_constant() -> None:
    assert POLYMARKET_MIN_ORDER_USDC == 5.0
