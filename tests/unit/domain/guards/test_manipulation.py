"""manipulation.py için birim testler (TDD §6.16)."""
from __future__ import annotations

from src.domain.guards.manipulation import (
    ManipulationCheck,
    adjust_position_size,
    check_market,
)


def test_clean_market_is_safe() -> None:
    r = check_market(
        question="Will Lakers beat Celtics?",
        liquidity=50_000,
    )
    assert r.safe is True
    assert r.risk_level == "low"
    assert r.flags == []


def test_self_resolving_trump_tweet_blocked() -> None:
    r = check_market(
        question="Will Trump tweet about inflation tomorrow?",
        liquidity=50_000,
    )
    assert r.safe is False
    assert r.risk_level == "high"
    assert any("SELF_RESOLVING" in f for f in r.flags)


def test_self_resolving_requires_subject_and_verb() -> None:
    # Sadece 'trump' var ama self-resolving verb yok
    r = check_market(
        question="Will Trump's net worth exceed Bezos'?",
        liquidity=50_000,
    )
    # No self-resolving verb → safe (low)
    assert r.risk_level == "low"


def test_low_liquidity_increases_risk() -> None:
    r = check_market(
        question="Will Lakers beat Celtics?",
        liquidity=5_000,
    )
    # Liquidity <$10K → risk +1 → still low (<2), safe
    assert r.risk_level == "low"


def test_zero_liquidity_medium() -> None:
    # $0 likidite → risk +2 → medium
    r = check_market(
        question="Random market?",
        liquidity=0,
    )
    assert r.risk_level == "medium"
    assert r.safe is True


def test_self_resolving_low_liquidity_high() -> None:
    # Self-resolving (+3) + low liquidity (+1) = high
    r = check_market(
        question="Will Trump tweet today?",
        liquidity=5_000,
    )
    assert r.risk_level == "high"
    assert r.safe is False


def test_adjust_size_high_returns_zero() -> None:
    check = ManipulationCheck(safe=False, risk_level="high", flags=[], recommendation="")
    assert adjust_position_size(40.0, check) == 0.0


def test_adjust_size_medium_halves() -> None:
    check = ManipulationCheck(safe=True, risk_level="medium", flags=[], recommendation="")
    assert adjust_position_size(40.0, check) == 20.0


def test_adjust_size_low_unchanged() -> None:
    check = ManipulationCheck(safe=True, risk_level="low", flags=[], recommendation="")
    assert adjust_position_size(40.0, check) == 40.0
