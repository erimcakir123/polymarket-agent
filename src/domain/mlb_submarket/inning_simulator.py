"""Layer 3: Monte Carlo half-inning simulator.

SPEC-R Plan 2 T15. Reproducible (seeded). Returns probability distribution
over runs scored in one half-inning.
"""
from __future__ import annotations

import numpy as np

from src.domain.mlb_submarket.base_out_states import (
    INITIAL_STATE,
    INNING_ENDED,
    decode,
)
from src.domain.mlb_submarket.markov import transition

LINEUP_SIZE = 9
MAX_PA_PER_INNING = 30
DP_PROBABILITY = 0.40
SAC_FLY_PROBABILITY = 0.20


def simulate_inning(
    batter_rates_list: list[dict[str, float]],
    lineup_start_idx: int = 0,
    mc_iterations: int = 10_000,
    seed: int = 42,
) -> dict[int, float]:
    """Monte Carlo simulate one half-inning.

    Args:
        batter_rates_list: 9 batter rate dicts (each = outcome → probability).
        lineup_start_idx: index of leadoff batter for this inning.
        mc_iterations: number of MC trials.
        seed: numpy RNG seed for reproducibility.

    Returns:
        {runs_scored: probability}. Sum = 1.0.

    Raises:
        ValueError: if mc_iterations <= 0 or lineup wrong size.
    """
    if mc_iterations <= 0:
        raise ValueError(f"mc_iterations must be > 0, got {mc_iterations}")
    if len(batter_rates_list) != LINEUP_SIZE:
        raise ValueError(f"batter_rates_list must have {LINEUP_SIZE} entries")

    rng = np.random.default_rng(seed)
    counts: dict[int, int] = {}

    # Precompute outcome arrays for each batter for fast sampling
    outcome_keys = list(batter_rates_list[0].keys())
    probs_per_batter = [
        np.array([batter[k] for k in outcome_keys]) for batter in batter_rates_list
    ]

    for _ in range(mc_iterations):
        state = INITIAL_STATE
        runs = 0
        lineup_idx = lineup_start_idx
        pa_count = 0
        while state != INNING_ENDED and pa_count < MAX_PA_PER_INNING:
            probs = probs_per_batter[lineup_idx]
            outcome_idx = rng.choice(len(outcome_keys), p=probs)
            outcome = outcome_keys[outcome_idx]

            force_dp = False
            force_sac_fly = False
            if outcome == "OUT_IN_PLAY" and state != INNING_ENDED:
                outs, (r1, _r2, r3) = decode(state)
                if r1 and outs < 2 and rng.random() < DP_PROBABILITY:
                    force_dp = True
                elif r3 and rng.random() < SAC_FLY_PROBABILITY:
                    force_sac_fly = True

            state, scored = transition(
                state, outcome, force_dp=force_dp, force_sac_fly=force_sac_fly,
            )
            runs += scored
            lineup_idx = (lineup_idx + 1) % LINEUP_SIZE
            pa_count += 1

        counts[runs] = counts.get(runs, 0) + 1

    return {r: c / mc_iterations for r, c in counts.items()}
