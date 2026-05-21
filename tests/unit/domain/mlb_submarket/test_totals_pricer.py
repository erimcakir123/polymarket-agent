import pytest
from src.domain.mlb_submarket.totals_pricer import totals_probability


def test_deterministic_over() -> None:
    """Home=3, Away=2 → total=5, line=4.5 → all over."""
    p_over, p_under = totals_probability({3: 1.0}, {2: 1.0}, line=4.5)
    assert p_over == 1.0
    assert p_under == 0.0


def test_deterministic_under() -> None:
    """Home=3, Away=2 → total=5, line=5.5 → all under."""
    p_over, p_under = totals_probability({3: 1.0}, {2: 1.0}, line=5.5)
    assert p_over == 0.0
    assert p_under == 1.0


def test_integer_line_creates_push() -> None:
    """Home=3, Away=2 → total=5, line=5 (integer) → push, no over or under."""
    p_over, p_under = totals_probability({3: 1.0}, {2: 1.0}, line=5)
    assert p_over == 0.0
    assert p_under == 0.0
    # push = 1 - p_over - p_under = 1.0


def test_half_line_no_push() -> None:
    """Probabilistic case with .5 line → over + under = 1.0."""
    home = {3: 0.5, 4: 0.5}
    away = {2: 0.5, 3: 0.5}
    # Joint: 5: 0.25, 6: 0.5, 7: 0.25
    p_over, p_under = totals_probability(home, away, line=5.5)
    assert abs(p_over - 0.75) < 1e-9  # 6+7 = 0.75
    assert abs(p_under - 0.25) < 1e-9
    assert abs((p_over + p_under) - 1.0) < 1e-9


def test_integer_line_with_push() -> None:
    home = {3: 0.5, 4: 0.5}
    away = {2: 0.5, 3: 0.5}
    # Joint: 5: 0.25, 6: 0.5, 7: 0.25; line=6
    p_over, p_under = totals_probability(home, away, line=6)
    assert abs(p_over - 0.25) < 1e-9  # only 7
    assert abs(p_under - 0.25) < 1e-9  # only 5
    # push = 0.5 (total = 6)


def test_high_scoring_distributions() -> None:
    """Convolution of moderate distributions sums correctly."""
    home = {4: 1.0}
    away = {5: 1.0}
    p_over, p_under = totals_probability(home, away, line=8.5)
    assert p_over == 1.0  # total = 9


def test_low_scoring_distributions() -> None:
    home = {0: 1.0}
    away = {1: 1.0}
    p_over, p_under = totals_probability(home, away, line=0.5)
    assert p_over == 1.0  # total = 1


def test_returns_floats_in_unit_interval() -> None:
    home = {2: 0.3, 3: 0.4, 4: 0.3}
    away = {1: 0.5, 2: 0.5}
    p_over, p_under = totals_probability(home, away, line=4.5)
    assert 0.0 <= p_over <= 1.0
    assert 0.0 <= p_under <= 1.0
    assert (p_over + p_under) <= 1.0 + 1e-9
