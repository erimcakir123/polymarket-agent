"""confidence.py için birim testler (TDD §6.2)."""
from __future__ import annotations

from src.domain.analysis.confidence import derive_confidence


def test_sharp_book_returns_A() -> None:
    assert derive_confidence(bm_weight=10, has_sharp=True) == "A"


def test_sharp_at_threshold_returns_A() -> None:
    assert derive_confidence(bm_weight=5, has_sharp=True) == "A"


def test_no_sharp_sufficient_weight_returns_B() -> None:
    assert derive_confidence(bm_weight=10, has_sharp=False) == "B"


def test_no_sharp_at_threshold_returns_B() -> None:
    assert derive_confidence(bm_weight=5, has_sharp=False) == "B"


def test_weight_below_5_returns_C() -> None:
    assert derive_confidence(bm_weight=4.9, has_sharp=True) == "C"


def test_none_weight_returns_C() -> None:
    assert derive_confidence(bm_weight=None, has_sharp=True) == "C"


def test_zero_weight_returns_C() -> None:
    assert derive_confidence(bm_weight=0, has_sharp=False) == "C"
