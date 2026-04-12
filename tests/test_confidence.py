"""Tests for bookmaker-derived confidence tiers."""

import pytest
from src.confidence import derive_confidence


@pytest.mark.parametrize(
    "bm_weight, has_sharp, expected",
    [
        (0, False, "C"),       # zero weight
        (None, False, "C"),    # missing weight
        (4.9, False, "C"),     # just below threshold
        (3, True, "C"),        # sharp but too low weight
        (5, False, "B"),       # exactly at threshold
        (15, False, "B"),      # moderate weight, no sharp
        (50, False, "B"),      # high weight, no sharp
        (5, True, "A"),        # threshold weight + sharp
        (30, True, "A"),       # solid weight + sharp
        (100, True, "A"),      # heavy weight + sharp
    ],
)
def test_derive_confidence(bm_weight, has_sharp, expected):
    assert derive_confidence(bm_weight, has_sharp) == expected
