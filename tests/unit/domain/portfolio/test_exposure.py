"""exposure.py için birim testler (SPEC-P 2026-05-21 — yumuşak cap)."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.portfolio.exposure import at_or_over_cap, fill_ratio


@dataclass
class _FakePos:
    size_usdc: float


def test_at_or_over_cap_under_limit() -> None:
    positions = {"a": _FakePos(100), "b": _FakePos(100)}
    # 200/1000 = 20% < 50% → False (yeni trade alınabilir)
    assert at_or_over_cap(positions, total_portfolio_value=1000, soft_cap_pct=0.50) is False


def test_at_or_over_cap_exactly_at_limit_blocks() -> None:
    positions = {"a": _FakePos(500)}
    # 500/1000 = 50% (== cap) → True (blok)
    assert at_or_over_cap(positions, total_portfolio_value=1000, soft_cap_pct=0.50) is True


def test_at_or_over_cap_over_limit_blocks() -> None:
    positions = {"a": _FakePos(530)}
    # 530/1000 = 53% > 50% → True (örn. önceki trade cap'i geçti, sonraki blok)
    assert at_or_over_cap(positions, total_portfolio_value=1000, soft_cap_pct=0.50) is True


def test_at_or_over_cap_just_below_limit_allows() -> None:
    positions = {"a": _FakePos(489)}
    # 489/1000 = 48.9% < 50% → False; sonraki $50 trade cap'i geçebilir (yumuşak cap)
    assert at_or_over_cap(positions, total_portfolio_value=1000, soft_cap_pct=0.50) is False


def test_at_or_over_cap_zero_portfolio_blocks() -> None:
    assert at_or_over_cap({}, total_portfolio_value=0, soft_cap_pct=0.50) is True


def test_at_or_over_cap_empty_positions_allows() -> None:
    assert at_or_over_cap({}, total_portfolio_value=1000, soft_cap_pct=0.50) is False


def test_fill_ratio_empty() -> None:
    assert fill_ratio({}, total_portfolio_value=1000) == 0.0


def test_fill_ratio_half() -> None:
    positions = {"a": _FakePos(250), "b": _FakePos(250)}
    assert fill_ratio(positions, total_portfolio_value=1000) == 0.5


def test_fill_ratio_zero_portfolio() -> None:
    assert fill_ratio({"a": _FakePos(100)}, total_portfolio_value=0) == 0.0
