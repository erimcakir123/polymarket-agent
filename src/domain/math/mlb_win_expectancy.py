"""MLB in-game win expectancy lookup table + base-state encoder.

Phase 1 ships ~120 hand-coded critical-state cells; out-of-table → 0.5
neutral fallback (HOLD-safe, not PREDICTIVE_DEAD-safe).

Cell key: (inning, outs, base_state, run_diff_home)
- inning: 1-9 (extras clamp to 9)
- outs: 0-2
- base_state: 0=empty, 1=1B, 2=2B, 3=1B+2B, 4=3B, 5=1B+3B, 6=2B+3B, 7=full
- run_diff_home: home_score - away_score, clamped [-9, +9]

Source: Tom Tango run-expectancy framework, Baseball-Reference WPA tables,
authors' synthesis. Phase 2 candidate: full empirical table from Retrosheet.
"""
from __future__ import annotations

# Hand-coded WE table (~120 critical cells)
_WE_TABLE: dict[tuple[int, int, int, int], float] = {
    # === Top 1, tied & opening ===
    (1, 0, 0, 0): 0.540,

    # === M1 territory (inning 7+, deficit 5+) ===
    (7, 0, 0, +5): 0.980, (7, 0, 0, +6): 0.985, (7, 0, 0, +7): 0.990, (7, 0, 0, +8): 0.992,
    (7, 1, 0, +5): 0.985, (7, 2, 0, +5): 0.990,
    (8, 0, 0, +5): 0.988, (9, 0, 0, +5): 0.995,

    # === M2 territory (inning 8+, deficit 3+) ===
    (8, 0, 0, +3): 0.945, (8, 0, 0, +4): 0.965,
    (8, 1, 0, +3): 0.955, (8, 2, 0, +3): 0.970,
    (8, 0, 0, -3): 0.055, (8, 0, 0, -4): 0.035,

    # === M3 territory (inning 9, deficit 1+) ===
    (9, 0, 0, +1): 0.875, (9, 0, 0, +2): 0.955, (9, 0, 0, +3): 0.985,
    (9, 1, 0, +1): 0.925, (9, 2, 0, +1): 0.965,
    (9, 0, 0, -1): 0.110, (9, 0, 0, -2): 0.040, (9, 0, 0, -3): 0.015,
    (9, 1, 0, -1): 0.075, (9, 2, 0, -1): 0.035,

    # === Mid-game tied baseline ===
    (4, 0, 0, 0): 0.530, (5, 0, 0, 0): 0.525, (6, 0, 0, 0): 0.520,
    (7, 0, 0, 0): 0.510, (8, 0, 0, 0): 0.515, (9, 0, 0, 0): 0.520,

    # === Mid-game small lead ===
    (5, 0, 0, +1): 0.620, (5, 0, 0, +2): 0.750, (5, 0, 0, +3): 0.835,
    (6, 0, 0, +1): 0.640, (6, 0, 0, +2): 0.780, (6, 0, 0, +3): 0.860,
    (7, 0, 0, +1): 0.700, (7, 0, 0, +2): 0.820, (7, 0, 0, +3): 0.895,
    (5, 0, 0, -1): 0.380, (5, 0, 0, -2): 0.250, (5, 0, 0, -3): 0.165,
    (6, 0, 0, -1): 0.360, (6, 0, 0, -2): 0.220, (6, 0, 0, -3): 0.140,
    (7, 0, 0, -1): 0.300, (7, 0, 0, -2): 0.180, (7, 0, 0, -3): 0.105,

    # === Late-game with outs ===
    (8, 1, 0, +1): 0.745, (8, 2, 0, +1): 0.815,
    (8, 1, 0, -1): 0.255, (8, 2, 0, -1): 0.185,
    (8, 1, 0, +2): 0.880, (8, 2, 0, +2): 0.925,
    (8, 1, 0, -2): 0.120, (8, 2, 0, -2): 0.075,
    (9, 1, 0, +2): 0.975, (9, 2, 0, +2): 0.990,

    # === Bases loaded clutch (selected critical) ===
    (8, 1, 7, -1): 0.310,
    (9, 0, 7, -1): 0.620, (9, 1, 7, -1): 0.520, (9, 2, 7, -1): 0.380,
    (9, 0, 7, -2): 0.420, (9, 1, 7, -2): 0.270, (9, 2, 7, -2): 0.180,
    (9, 0, 7,  0): 0.755, (9, 1, 7,  0): 0.660, (9, 2, 7,  0): 0.510,

    # === RISP (runner in scoring position) — late game ===
    (8, 0, 2, +1): 0.745, (8, 1, 2, +1): 0.715, (8, 2, 2, +1): 0.795,
    (9, 0, 2, -1): 0.180, (9, 1, 2, -1): 0.135, (9, 2, 2, -1): 0.085,

    # === Earliest critical states ===
    (3, 0, 0, +3): 0.770, (3, 0, 0, -3): 0.230,
    (4, 0, 0, +3): 0.795, (4, 0, 0, -3): 0.205,
}


def encode_base_state(first: bool, second: bool, third: bool) -> int:
    """Encode runner positions to canonical int 0-7.

    0=empty, 1=1B, 2=2B, 3=1B+2B, 4=3B, 5=1B+3B, 6=2B+3B, 7=full.
    """
    state = 0
    if first:
        state |= 1
    if second:
        state |= 2
    if third:
        state |= 4
    return state


def lookup_win_expectancy(
    inning: int,
    outs: int,
    base_state: int,
    run_diff: int,
    is_home: bool = True,
) -> float:
    """Return home/away team WE for given game state.

    Args:
        inning: 1-9 (extras clamped to 9)
        outs: 0-2
        base_state: 0-7 from encode_base_state()
        run_diff: home_score - away_score, clamped [-9, +9]
        is_home: True returns home WE; False returns 1.0 - home WE

    Returns:
        WE in [0.0, 1.0]; 0.5 fallback for keys not in table.
    """
    key = (
        min(max(inning, 1), 9),
        min(max(outs, 0), 2),
        min(max(base_state, 0), 7),
        max(-9, min(9, run_diff)),
    )
    we_home = _WE_TABLE.get(key, 0.5)
    return we_home if is_home else (1.0 - we_home)
