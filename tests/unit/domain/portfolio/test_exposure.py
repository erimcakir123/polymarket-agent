"""exposure.py için birim testler."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.portfolio.exposure import (
    available_under_cap,
    fill_ratio,
)


@dataclass
class _FakePos:
    size_usdc: float


def test_fill_ratio_empty() -> None:
    assert fill_ratio({}, total_portfolio_value=1000) == 0.0


def test_fill_ratio_half() -> None:
    positions = {"a": _FakePos(250), "b": _FakePos(250)}
    assert fill_ratio(positions, total_portfolio_value=1000) == 0.5


def test_fill_ratio_zero_portfolio() -> None:
    assert fill_ratio({"a": _FakePos(100)}, total_portfolio_value=0) == 0.0


def test_available_under_cap_soft_cap_not_reached_returns_full_buffer() -> None:
    positions = {"a": _FakePos(100.0)}
    avail = available_under_cap(positions, total_portfolio_value=1000.0,
                                soft_cap_pct=0.50, overflow_pct=0.02)
    assert avail == 420.0


def test_available_under_cap_soft_cap_exactly_at_limit() -> None:
    positions = {"a": _FakePos(500.0)}
    avail = available_under_cap(positions, 1000.0, 0.50, 0.02)
    assert avail == 20.0


def test_available_under_cap_hard_cap_fully_used_returns_zero() -> None:
    positions = {"a": _FakePos(520.0)}
    avail = available_under_cap(positions, 1000.0, 0.50, 0.02)
    assert avail == 0.0


def test_available_under_cap_negative_over_hard_cap_clamps_to_zero() -> None:
    positions = {"a": _FakePos(600.0)}
    avail = available_under_cap(positions, 1000.0, 0.50, 0.02)
    assert avail == 0.0


def test_available_under_cap_zero_portfolio_returns_zero() -> None:
    avail = available_under_cap({}, 0.0, 0.50, 0.02)
    assert avail == 0.0
