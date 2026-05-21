"""position_sizer.py için birim testler (DECISIONS §6.5, SPEC-P 2026-05-21)."""
from __future__ import annotations

from src.domain.risk.position_sizer import (
    POLYMARKET_MIN_ORDER_USDC,
    confidence_position_size,
)

# Test fixture — production config.yaml > risk.fixed_bet_usdc mirror.
FIXED_BET_USDC: dict[str, float] = {"A": 50.0, "B": 30.0}


def test_A_confidence_returns_fixed_50() -> None:
    assert confidence_position_size("A", fixed_bet_usdc=FIXED_BET_USDC) == 50.0


def test_B_confidence_returns_fixed_30() -> None:
    assert confidence_position_size("B", fixed_bet_usdc=FIXED_BET_USDC) == 30.0


def test_C_confidence_returns_zero() -> None:
    assert confidence_position_size("C", fixed_bet_usdc=FIXED_BET_USDC) == 0.0


def test_unknown_tier_returns_zero() -> None:
    assert confidence_position_size("Z", fixed_bet_usdc=FIXED_BET_USDC) == 0.0


def test_polymarket_min_constant() -> None:
    assert POLYMARKET_MIN_ORDER_USDC == 5.0
