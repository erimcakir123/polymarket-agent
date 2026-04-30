# tests/unit/domain/math/test_mlb_pythagoras.py
"""Pythagorean winpct anchor tests (Bill James / Steven Miller 2007 verified)."""
import pytest
from src.domain.math.mlb_pythagoras import pythagorean_winpct


def test_balanced_runs_returns_half():
    assert pythagorean_winpct(4.5, 4.5) == pytest.approx(0.5, abs=0.001)


def test_higher_rs_higher_winpct():
    """5.0 RS / 4.0 RA → ~0.604 (Bill James known value)."""
    assert pythagorean_winpct(5.0, 4.0) == pytest.approx(0.604, abs=0.005)


def test_higher_ra_lower_winpct():
    """4.0 RS / 5.0 RA → ~0.396."""
    assert pythagorean_winpct(4.0, 5.0) == pytest.approx(0.396, abs=0.005)


def test_dominant_offense():
    """6.0 RS / 3.5 RA → ~0.728 with exp=1.83 (Steven Miller verified)."""
    assert pythagorean_winpct(6.0, 3.5) == pytest.approx(0.728, abs=0.005)


def test_zero_runs_safe_default():
    """Both teams zero runs → 0.5 (no division by zero)."""
    assert pythagorean_winpct(0, 0) == 0.5
