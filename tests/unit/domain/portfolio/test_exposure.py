"""exposure.py için birim testler."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.portfolio.exposure import exceeds_exposure_limit, fill_ratio


@dataclass
class _FakePos:
    size_usdc: float


def test_exposure_under_limit() -> None:
    positions = {"a": _FakePos(100), "b": _FakePos(100)}
    # 200 + 50 = 250; 250/1000 = 25%; cap 50% → OK
    assert exceeds_exposure_limit(positions, candidate_size=50, bankroll=1000, max_exposure_pct=0.50) is False


def test_exposure_over_limit() -> None:
    positions = {"a": _FakePos(300), "b": _FakePos(200)}
    # 500 + 100 = 600; 600/1000 = 60%; cap 50% → BLOCK
    assert exceeds_exposure_limit(positions, candidate_size=100, bankroll=1000, max_exposure_pct=0.50) is True


def test_exposure_exactly_at_limit() -> None:
    positions = {"a": _FakePos(500)}
    # 500 + 0 = 500; 500/1000 = 50%; cap 50% → at limit, > fails → OK
    assert exceeds_exposure_limit(positions, candidate_size=0, bankroll=1000, max_exposure_pct=0.50) is False


def test_zero_bankroll_blocks() -> None:
    assert exceeds_exposure_limit({}, candidate_size=10, bankroll=0, max_exposure_pct=0.50) is True


def test_fill_ratio_empty() -> None:
    assert fill_ratio({}, bankroll=1000) == 0.0


def test_fill_ratio_half() -> None:
    positions = {"a": _FakePos(250), "b": _FakePos(250)}
    assert fill_ratio(positions, bankroll=1000) == 0.5


def test_fill_ratio_zero_bankroll() -> None:
    assert fill_ratio({"a": _FakePos(100)}, bankroll=0) == 0.0
