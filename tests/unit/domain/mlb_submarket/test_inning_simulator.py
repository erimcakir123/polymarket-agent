"""Tests for inning_simulator — Monte Carlo half-inning (SPEC-R Plan 2 T15)."""
import pytest
from src.domain.mlb_submarket.inning_simulator import simulate_inning


def _all_k_rates() -> dict[str, float]:
    """All strikeouts → inning ends in 3 PA, 0 runs."""
    return {"K": 1.0, "BB": 0.0, "HBP": 0.0, "HR": 0.0,
            "1B": 0.0, "2B": 0.0, "3B": 0.0, "OUT_IN_PLAY": 0.0}


def _all_hr_rates() -> dict[str, float]:
    """All HR with no outs possible → simulator must hit MAX_PA safety."""
    return {"K": 0.0, "BB": 0.0, "HBP": 0.0, "HR": 1.0,
            "1B": 0.0, "2B": 0.0, "3B": 0.0, "OUT_IN_PLAY": 0.0}


def _league_rates() -> dict[str, float]:
    """Realistic 2023-2025 MLB averages."""
    return {"K": 0.225, "BB": 0.085, "HBP": 0.011, "HR": 0.030,
            "1B": 0.140, "2B": 0.045, "3B": 0.004, "OUT_IN_PLAY": 0.460}


def test_all_strikeouts_zero_runs() -> None:
    lineup = [_all_k_rates()] * 9
    dist = simulate_inning(lineup, mc_iterations=100, seed=42)
    assert dist == {0: 1.0}


def test_distribution_sums_to_one() -> None:
    lineup = [_league_rates()] * 9
    dist = simulate_inning(lineup, mc_iterations=1000, seed=42)
    assert abs(sum(dist.values()) - 1.0) < 1e-9


def test_reproducibility_same_seed_same_result() -> None:
    lineup = [_league_rates()] * 9
    d1 = simulate_inning(lineup, mc_iterations=500, seed=42)
    d2 = simulate_inning(lineup, mc_iterations=500, seed=42)
    assert d1 == d2


def test_different_seeds_different_results() -> None:
    lineup = [_league_rates()] * 9
    d1 = simulate_inning(lineup, mc_iterations=500, seed=42)
    d2 = simulate_inning(lineup, mc_iterations=500, seed=99)
    assert d1 != d2  # not guaranteed but very likely


def test_average_runs_realistic() -> None:
    """League-average lineup should produce ~0.45-0.55 runs/inning."""
    lineup = [_league_rates()] * 9
    dist = simulate_inning(lineup, mc_iterations=5000, seed=42)
    expected_runs = sum(r * p for r, p in dist.items())
    # MLB average is ~4.5 runs/game = 0.5/inning. Allow wide tolerance.
    assert 0.30 < expected_runs < 0.80


def test_all_hr_hits_max_pa_safety() -> None:
    """All HR rates means no outs possible — simulator must cap at MAX_PA_PER_INNING."""
    lineup = [_all_hr_rates()] * 9
    dist = simulate_inning(lineup, mc_iterations=100, seed=42)
    # With 30 PA cap, all 30 are HR → 30 runs. Single outcome.
    assert max(dist.keys()) == 30
    assert dist.get(30, 0) == 1.0


def test_lineup_start_idx_changes_result() -> None:
    """Different lineup start should produce different distribution
    (when lineup is heterogeneous)."""
    weak = _league_rates()
    strong = dict(_league_rates())
    strong["HR"] = 0.10
    # Renormalize
    total = sum(strong.values())
    strong = {k: v / total for k, v in strong.items()}
    lineup = [weak] * 8 + [strong]  # batter 8 is strong
    d_from_0 = simulate_inning(lineup, lineup_start_idx=0, mc_iterations=1000, seed=42)
    d_from_8 = simulate_inning(lineup, lineup_start_idx=8, mc_iterations=1000, seed=42)
    # Starting from index 8 (strong batter) should produce higher mean
    mean_from_0 = sum(r * p for r, p in d_from_0.items())
    mean_from_8 = sum(r * p for r, p in d_from_8.items())
    assert mean_from_8 > mean_from_0


def test_mc_iterations_zero_returns_empty_or_raises() -> None:
    lineup = [_league_rates()] * 9
    with pytest.raises(ValueError):
        simulate_inning(lineup, mc_iterations=0, seed=42)
