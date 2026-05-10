"""Vig bounds sanity tests — 2-way vs 3-way bookmaker normalize aralıkları."""
from __future__ import annotations

from src.domain.analysis.vig_bounds import (
    VIG_2WAY_MAX,
    VIG_2WAY_MIN,
    VIG_3WAY_MAX,
    VIG_3WAY_MIN,
)


def test_2way_bounds() -> None:
    assert VIG_2WAY_MIN < 1.0 < VIG_2WAY_MAX


def test_3way_bounds() -> None:
    assert VIG_3WAY_MIN < 1.0 < VIG_3WAY_MAX


def test_3way_max_higher_than_2way() -> None:
    assert VIG_3WAY_MAX > VIG_2WAY_MAX  # 3-way includes draw, more vig room
