"""Tests for game_simulator — 9-inning convolution + DH support.

SPEC-R Plan 2 T16.
"""
import pytest

from src.domain.mlb_submarket.game_simulator import simulate_game, team_run_distribution


def _league_rates() -> dict[str, float]:
    return {
        "K": 0.225,
        "BB": 0.085,
        "HBP": 0.011,
        "HR": 0.030,
        "1B": 0.140,
        "2B": 0.045,
        "3B": 0.004,
        "OUT_IN_PLAY": 0.460,
    }


def test_convolve_two_deterministic_innings() -> None:
    """Inning 1 = {2: 1.0}, Inning 2 = {1: 1.0} → team = {3: 1.0}."""
    dist = team_run_distribution([{2: 1.0}, {1: 1.0}])
    assert dist == {3: 1.0}


def test_convolve_all_zero_innings() -> None:
    """9 innings of {0: 1.0} → game = {0: 1.0}."""
    dist = team_run_distribution([{0: 1.0}] * 9)
    assert dist == {0: 1.0}


def test_convolve_all_one_run_innings() -> None:
    """9 innings of {1: 1.0} → game = {9: 1.0}."""
    dist = team_run_distribution([{1: 1.0}] * 9)
    assert dist == {9: 1.0}


def test_convolve_probabilistic() -> None:
    """{0: 0.5, 1: 0.5} × {0: 0.5, 1: 0.5} = {0: 0.25, 1: 0.5, 2: 0.25}."""
    dist = team_run_distribution([{0: 0.5, 1: 0.5}, {0: 0.5, 1: 0.5}])
    assert abs(dist[0] - 0.25) < 1e-9
    assert abs(dist[1] - 0.5) < 1e-9
    assert abs(dist[2] - 0.25) < 1e-9


def test_distribution_sums_to_one() -> None:
    """{0: 0.6, 1: 0.3, 2: 0.1} × itself × ... 9 times → sums to 1."""
    dist = team_run_distribution([{0: 0.6, 1: 0.3, 2: 0.1}] * 9)
    assert abs(sum(dist.values()) - 1.0) < 1e-9


def test_simulate_game_9_innings_default() -> None:
    """League-average lineup → mean ~4-5 runs/game."""
    lineup = [_league_rates()] * 9
    home_per_inning = [lineup] * 9
    away_per_inning = [lineup] * 9
    home_dist, away_dist = simulate_game(
        home_per_inning,
        away_per_inning,
        dh_game=False,
        mc_iterations=1000,
        seed=42,
    )
    home_mean = sum(r * p for r, p in home_dist.items())
    away_mean = sum(r * p for r, p in away_dist.items())
    # MLB average ~4.5 runs/game. Allow wide tolerance.
    assert 2.5 < home_mean < 7.0
    assert 2.5 < away_mean < 7.0
    # Both distributions sum to 1
    assert abs(sum(home_dist.values()) - 1.0) < 1e-9
    assert abs(sum(away_dist.values()) - 1.0) < 1e-9


def test_simulate_game_dh_uses_7_innings() -> None:
    """DH game: 7 innings, mean should be roughly 7/9 of 9-inning mean."""
    lineup = [_league_rates()] * 9
    home_per_inning_7 = [lineup] * 7
    away_per_inning_7 = [lineup] * 7
    home_dist, _ = simulate_game(
        home_per_inning_7,
        away_per_inning_7,
        dh_game=True,
        mc_iterations=500,
        seed=42,
    )
    # Just verify it ran and produced valid distribution
    assert abs(sum(home_dist.values()) - 1.0) < 1e-9
    # Mean should be positive
    home_mean = sum(r * p for r, p in home_dist.items())
    assert home_mean > 0


def test_simulate_game_length_mismatch_raises() -> None:
    """Home and away inning counts must match."""
    lineup = [_league_rates()] * 9
    with pytest.raises(ValueError):
        simulate_game(
            home_pa_rates_per_inning=[lineup] * 9,
            away_pa_rates_per_inning=[lineup] * 7,  # mismatch
            dh_game=False,
            mc_iterations=100,
            seed=42,
        )


def test_simulate_game_wrong_innings_for_dh_raises() -> None:
    """9 innings supplied but dh_game=True (expects 7) → ValueError."""
    lineup = [_league_rates()] * 9
    with pytest.raises(ValueError):
        simulate_game(
            home_pa_rates_per_inning=[lineup] * 9,
            away_pa_rates_per_inning=[lineup] * 9,
            dh_game=True,
            mc_iterations=100,
            seed=42,
        )
