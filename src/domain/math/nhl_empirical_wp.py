"""
NHL empirical win probability lookup.

Loads precomputed table from data/nhl_empirical_win_table.json (built by
scripts/build_nhl_empirical_table.py).

Returns empirical p(leading team wins) given (period, abs_score_diff,
seconds_remaining). Final outcome includes OT/SO via MoneyPuck final scores.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

TABLE_PATH = Path("data/nhl_empirical_win_table.json")


@lru_cache(maxsize=1)
def _load_table() -> dict:
    if not TABLE_PATH.exists():
        raise FileNotFoundError(
            f"Empirical WP table not found at {TABLE_PATH}. "
            f"Run scripts/build_nhl_empirical_table.py first."
        )
    with open(TABLE_PATH) as f:
        return json.load(f)


def leading_team_win_probability_empirical(
    period: int,
    abs_score_diff: int,
    seconds_remaining: int,
) -> float | None:
    """
    Empirical P(leading team is final winner) from MoneyPuck 2022-25 data.

    Args:
        period: 1, 2, 3 (regulation only — OT/SO outcome bucketed into final)
        abs_score_diff: 0 (tied), 1, 2, 3, 4, 5+ (capped at deficit_cap)
        seconds_remaining: regulation total left (0 - 3600)

    Returns:
        Empirical probability, or None if bucket has too few samples.
    """
    if abs_score_diff < 0:
        raise ValueError("abs_score_diff must be non-negative")
    if abs_score_diff == 0:
        return 0.5

    table = _load_table()
    deficit_clamped = min(abs_score_diff, table["metadata"]["deficit_cap"])
    bucket_size = table["metadata"]["time_bucket_sec"]
    seconds_bucket = (seconds_remaining // bucket_size) * bucket_size

    key = f"{period}_{deficit_clamped}_{seconds_bucket}"
    entry = table["win_probability"].get(key)

    if entry is None:
        return None
    if entry["n_games"] < table["metadata"]["min_sample_size"]:
        return None

    return entry["p_win"]


def trailing_team_win_probability_empirical(
    period: int,
    deficit: int,
    seconds_remaining: int,
) -> float | None:
    """Convenience: 1 - leading_p_win. None if leader bucket insufficient."""
    p_lead = leading_team_win_probability_empirical(period, deficit, seconds_remaining)
    if p_lead is None:
        return None
    return 1.0 - p_lead


def get_table_metadata() -> dict:
    """Return metadata for diagnostic logging."""
    return _load_table()["metadata"]
