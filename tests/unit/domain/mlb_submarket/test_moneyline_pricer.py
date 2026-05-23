import math

from src.domain.mlb_submarket.moneyline_pricer import moneyline_probability


def test_home_certain_winner_returns_1() -> None:
    """Home team always scores 5, away always scores 0 → home wins with certainty."""
    home_dist = {5: 1.0}
    away_dist = {0: 1.0}
    p_home, p_away = moneyline_probability(home_dist, away_dist)
    assert math.isclose(p_home, 1.0)
    assert math.isclose(p_away, 0.0)


def test_away_certain_winner_returns_1() -> None:
    """Away team always scores 5, home always scores 0 → away wins with certainty."""
    home_dist = {0: 1.0}
    away_dist = {5: 1.0}
    p_home, p_away = moneyline_probability(home_dist, away_dist)
    assert math.isclose(p_home, 0.0)
    assert math.isclose(p_away, 1.0)


def test_tied_distributions_split_50_50() -> None:
    """MLB no official ties → tied final score assumed 50/50 (extras).

    Both teams score 3 → 50% home wins extras, 50% away wins extras.
    """
    home_dist = {3: 1.0}
    away_dist = {3: 1.0}
    p_home, p_away = moneyline_probability(home_dist, away_dist)
    assert math.isclose(p_home, 0.5)
    assert math.isclose(p_away, 0.5)


def test_mixed_distributions_sum_to_one() -> None:
    """Mixed distributions must produce p_home + p_away = 1.0 (no pushes in moneyline)."""
    home_dist = {2: 0.5, 4: 0.5}
    away_dist = {1: 0.3, 3: 0.4, 5: 0.3}
    p_home, p_away = moneyline_probability(home_dist, away_dist)
    assert math.isclose(p_home + p_away, 1.0, abs_tol=1e-9)


def test_known_joint_probabilities() -> None:
    """Verifiable joint outcome example.

    Home ∈ {2: 0.5, 4: 0.5}, Away ∈ {3: 1.0}
    - (2, 3): home loses, P = 0.5
    - (4, 3): home wins, P = 0.5
    → p_home = 0.5, p_away = 0.5
    """
    home_dist = {2: 0.5, 4: 0.5}
    away_dist = {3: 1.0}
    p_home, p_away = moneyline_probability(home_dist, away_dist)
    assert math.isclose(p_home, 0.5)
    assert math.isclose(p_away, 0.5)
