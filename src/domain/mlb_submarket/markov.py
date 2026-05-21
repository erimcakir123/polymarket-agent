"""Layer 2: deterministic base/out state transition with DP and SAC FLY handling.

SPEC-R Plan 2 T12. Maps (current state, PA outcome) → (new state, runs scored).
Caller (inning_simulator, Task 15) handles DP/SAC FLY probabilities by passing
force_dp/force_sac_fly flags explicitly.
"""
from __future__ import annotations

from src.domain.mlb_submarket.base_out_states import INNING_ENDED, decode, encode


_KNOWN_OUTCOMES: frozenset[str] = frozenset(
    {"K", "BB", "HBP", "HR", "1B", "2B", "3B", "OUT_IN_PLAY"}
)


def transition(
    state_idx: int,
    pa_outcome: str,
    *,
    force_dp: bool = False,
    force_sac_fly: bool = False,
) -> tuple[int, int]:
    """Compute next base/out state and runs scored from a single PA outcome.

    Args:
        state_idx: current base/out state index 0-23.
        pa_outcome: one of K, BB, HBP, HR, 1B, 2B, 3B, OUT_IN_PLAY.
        force_dp: if True, OUT_IN_PLAY with runner on 1B (outs < 2) applies a
            double play — batter and 1B runner both out (outs += 2, 1B clears).
        force_sac_fly: if True, OUT_IN_PLAY with runner on 3B scores the runner
            (outs += 1, 3B clears, runs += 1).

    Returns:
        (new_state_idx, runs_scored). new_state_idx is INNING_ENDED (-1) when
        outs reach 3 after the play.

    Raises:
        ValueError: if pa_outcome is not a recognised outcome string.
    """
    if pa_outcome not in _KNOWN_OUTCOMES:
        raise ValueError(f"unknown PA outcome: {pa_outcome!r}")

    outs, (r1, r2, r3) = decode(state_idx)
    runs: int = 0

    if pa_outcome == "K":
        outs += 1

    elif pa_outcome == "OUT_IN_PLAY":
        if force_dp and r1 and outs < 2:
            # Double play: batter out + 1B runner out; 1B base clears.
            outs += 2
            r1 = False
        elif force_sac_fly and r3:
            # Sacrifice fly: batter out, 3B runner scores; 3B base clears.
            outs += 1
            r3 = False
            runs += 1
        else:
            outs += 1

    elif pa_outcome in ("BB", "HBP"):
        # Batter takes 1B; force cascade pushes runners only if forced.
        # Chain: 1B runner forced to 2B only if 1B occupied;
        #        2B runner forced to 3B only if both 1B and 2B occupied;
        #        3B runner forced home only if 1B, 2B, and 3B all occupied.
        if r1 and r2 and r3:
            # Bases loaded — 3B runner forced home.
            runs += 1
            # r1, r2, r3 remain True; batter fills 1B (already True).
        elif r1 and r2 and not r3:
            # 1B and 2B occupied — 2B runner forced to 3B; 1B stays; batter fills 1B.
            r3 = True
        elif r1 and not r2 and r3:
            # 1B and 3B occupied (2B empty) — 1B runner forced to 2B;
            # 3B runner NOT forced (no chain from 2B→3B); batter fills 1B.
            r2 = True
        elif r1 and not r2 and not r3:
            # 1B only — 1B runner forced to 2B; batter fills 1B.
            r2 = True
        # All other cases: r1 was False, so no cascade; batter simply takes 1B.
        r1 = True

    elif pa_outcome == "1B":
        # Batter → 1B. Prior 1B runner → 2B. Prior 2B runner → home. Prior 3B → home.
        new_r1 = True
        new_r2 = r1          # prior 1B advances to 2B
        new_r3 = False        # prior 2B and 3B score
        if r2:
            runs += 1
        if r3:
            runs += 1
        r1, r2, r3 = new_r1, new_r2, new_r3

    elif pa_outcome == "2B":
        # Batter → 2B. Prior 1B runner → 3B. Prior 2B and 3B runners → home.
        new_r1 = False
        new_r2 = True         # batter on 2B
        new_r3 = r1           # prior 1B advances to 3B
        if r2:
            runs += 1
        if r3:
            runs += 1
        r1, r2, r3 = new_r1, new_r2, new_r3

    elif pa_outcome == "3B":
        # Batter → 3B. All existing runners score.
        if r1:
            runs += 1
        if r2:
            runs += 1
        if r3:
            runs += 1
        r1, r2, r3 = False, False, True

    elif pa_outcome == "HR":
        # Batter + all runners score; bases clear.
        runs += 1  # batter
        if r1:
            runs += 1
        if r2:
            runs += 1
        if r3:
            runs += 1
        r1, r2, r3 = False, False, False

    if outs >= 3:
        return INNING_ENDED, runs

    return encode(outs, (r1, r2, r3)), runs
