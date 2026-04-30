import pytest
from src.domain.math.mlb_log5 import log5


def test_equal_teams_returns_half():
    assert log5(0.500, 0.500) == pytest.approx(0.5, abs=0.001)


def test_strong_vs_weak():
    """log5(0.600, 0.450) ≈ 0.647."""
    assert log5(0.600, 0.450) == pytest.approx(0.647, abs=0.005)


def test_dominant_vs_terrible():
    """log5(0.700, 0.300) ≈ 0.845."""
    assert log5(0.700, 0.300) == pytest.approx(0.845, abs=0.005)


def test_inverse_symmetry():
    """log5(p_a, p_b) + log5(p_b, p_a) == 1.0."""
    p_a, p_b = 0.580, 0.420
    assert log5(p_a, p_b) + log5(p_b, p_a) == pytest.approx(1.0, abs=0.001)


def test_clamps_extreme_inputs():
    """Inputs outside (0.01, 0.99) are clamped to avoid div0."""
    assert 0.0 < log5(0.0, 0.5) < 1.0
    assert 0.0 < log5(1.0, 0.5) < 1.0
