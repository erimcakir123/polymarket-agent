import pytest
from src.domain.mlb_submarket.spread_pricer import spread_probability


def test_home_covers_minus_1_5() -> None:
    """Home wins 5-3, home_line=-1.5 → spread = 5-3 = 2 > 1.5 → home covers."""
    p_home, p_away = spread_probability({5: 1.0}, {3: 1.0}, home_line=-1.5)
    assert p_home == 1.0
    assert p_away == 0.0


def test_home_does_not_cover_minus_1_5_on_close_win() -> None:
    """Home wins 4-3 (by 1), home_line=-1.5 → does not cover."""
    p_home, p_away = spread_probability({4: 1.0}, {3: 1.0}, home_line=-1.5)
    assert p_home == 0.0
    assert p_away == 1.0


def test_home_easily_covers_plus_1_5() -> None:
    """Home wins 5-3, home_line=+1.5 → 5+1.5=6.5 > 3 → home covers."""
    p_home, p_away = spread_probability({5: 1.0}, {3: 1.0}, home_line=+1.5)
    assert p_home == 1.0


def test_home_covers_plus_1_5_even_when_losing_by_one() -> None:
    """Home loses 3-4 (by 1), home_line=+1.5 → 3+1.5=4.5 > 4 → home covers."""
    p_home, p_away = spread_probability({3: 1.0}, {4: 1.0}, home_line=+1.5)
    assert p_home == 1.0


def test_home_does_not_cover_plus_1_5_when_losing_by_3() -> None:
    """Home loses 2-5 (by 3), home_line=+1.5 → 2+1.5=3.5 < 5 → away covers."""
    p_home, p_away = spread_probability({2: 1.0}, {5: 1.0}, home_line=+1.5)
    assert p_home == 0.0
    assert p_away == 1.0


def test_distribution_sums_to_one_for_half_line() -> None:
    """With .5 lines there's no push, so p_home + p_away = 1."""
    home = {3: 0.5, 4: 0.5}
    away = {2: 0.5, 3: 0.5}
    p_home, p_away = spread_probability(home, away, home_line=-1.5)
    assert abs((p_home + p_away) - 1.0) < 1e-9


def test_returns_floats_in_unit_interval() -> None:
    home = {2: 0.3, 3: 0.4, 4: 0.3}
    away = {1: 0.5, 2: 0.5}
    p_home, p_away = spread_probability(home, away, home_line=-1.5)
    assert 0.0 <= p_home <= 1.0
    assert 0.0 <= p_away <= 1.0
    assert abs((p_home + p_away) - 1.0) < 1e-9
