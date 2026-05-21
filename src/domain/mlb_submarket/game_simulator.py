"""Layer 4: 9-inning game simulator (convolution + DH).

SPEC-R Plan 2 T16.

Given per-inning lineup rate dicts (already adjusted for TTO/bullpen/park/weather
by the caller), this module:
  1. Runs Monte Carlo half-inning simulation for each inning via simulate_inning.
  2. Convolves all inning run distributions into a total team run distribution.
"""
from __future__ import annotations

import numpy as np

from src.domain.mlb_submarket.inning_simulator import simulate_inning

NORMAL_GAME_INNINGS = 9
DH_GAME_INNINGS = 7


def _dict_to_array(d: dict[int, float], max_runs: int) -> np.ndarray:
    arr = np.zeros(max_runs + 1)
    for runs, p in d.items():
        if 0 <= runs <= max_runs:
            arr[runs] = p
    return arr


def _array_to_dict(arr: np.ndarray, tol: float = 1e-12) -> dict[int, float]:
    return {i: float(p) for i, p in enumerate(arr) if p > tol}


def team_run_distribution(inning_dists: list[dict[int, float]]) -> dict[int, float]:
    """Convolve N inning distributions into one total team run distribution.

    Args:
        inning_dists: List of per-inning run distributions ({runs: probability}).

    Returns:
        {total_runs: probability} for the full game. Sums to 1.0.
    """
    if not inning_dists:
        return {0: 1.0}

    max_per_inning = max((max(d.keys(), default=0) for d in inning_dists), default=0)
    arr = _dict_to_array(inning_dists[0], max_per_inning)
    for next_dist in inning_dists[1:]:
        next_max = max(next_dist.keys(), default=0)
        next_arr = _dict_to_array(next_dist, next_max)
        arr = np.convolve(arr, next_arr)

    return _array_to_dict(arr)


def simulate_game(
    home_pa_rates_per_inning: list[list[dict[str, float]]],
    away_pa_rates_per_inning: list[list[dict[str, float]]],
    *,
    dh_game: bool = False,
    mc_iterations: int = 5_000,
    seed: int = 42,
) -> tuple[dict[int, float], dict[int, float]]:
    """Simulate full game and return home/away team run distributions.

    Args:
        home_pa_rates_per_inning: List of length 9 (or 7 for DH). Each element
            is a 9-batter lineup list of outcome-rate dicts.
        away_pa_rates_per_inning: Same shape as home.
        dh_game: If True, expects 7-inning game (split doubleheader).
        mc_iterations: Monte Carlo trials per inning simulation.
        seed: Master RNG seed; each inning gets a deterministic sub-seed.

    Returns:
        (home_runs_dist, away_runs_dist) — each {runs: probability}, sums to 1.

    Raises:
        ValueError: if inning list lengths don't match the expected inning count
            or home/away lengths differ.
    """
    expected_innings = DH_GAME_INNINGS if dh_game else NORMAL_GAME_INNINGS

    if len(home_pa_rates_per_inning) != expected_innings:
        raise ValueError(
            f"home_pa_rates_per_inning must have {expected_innings} innings "
            f"(dh_game={dh_game}), got {len(home_pa_rates_per_inning)}"
        )
    if len(away_pa_rates_per_inning) != expected_innings:
        raise ValueError(
            f"away_pa_rates_per_inning must have {expected_innings} innings "
            f"(dh_game={dh_game}), got {len(away_pa_rates_per_inning)}"
        )

    rng = np.random.default_rng(seed)

    home_innings: list[dict[int, float]] = []
    for lineup in home_pa_rates_per_inning:
        inning_seed = int(rng.integers(0, 2**31 - 1))
        home_innings.append(
            simulate_inning(lineup, lineup_start_idx=0, mc_iterations=mc_iterations, seed=inning_seed)
        )

    away_innings: list[dict[int, float]] = []
    for lineup in away_pa_rates_per_inning:
        inning_seed = int(rng.integers(0, 2**31 - 1))
        away_innings.append(
            simulate_inning(lineup, lineup_start_idx=0, mc_iterations=mc_iterations, seed=inning_seed)
        )

    return team_run_distribution(home_innings), team_run_distribution(away_innings)
