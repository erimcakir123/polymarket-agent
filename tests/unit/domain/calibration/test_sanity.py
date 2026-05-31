"""Cliprange güvenlik kemeri testleri."""
from __future__ import annotations

from src.domain.calibration.sanity import (
    PROB_CEILING,
    PROB_FLOOR,
    cliprange,
)


def test_cliprange_lower_bound():
    assert cliprange(0.0) == PROB_FLOOR
    assert cliprange(0.01) == PROB_FLOOR
    assert cliprange(-1.0) == PROB_FLOOR


def test_cliprange_upper_bound():
    assert cliprange(1.0) == PROB_CEILING
    assert cliprange(0.99) == PROB_CEILING
    assert cliprange(2.0) == PROB_CEILING


def test_cliprange_normal_passthrough():
    assert cliprange(0.5) == 0.5
    assert cliprange(0.7) == 0.7
    assert cliprange(0.06) == 0.06
    assert cliprange(0.94) == 0.94
