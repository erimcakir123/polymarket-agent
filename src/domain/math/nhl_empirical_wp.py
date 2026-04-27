"""
NHL empirical win probability lookup (pure domain logic).

Computes empirical p(leading team wins) from a preloaded MoneyPuck table.
No I/O — table must be loaded by the infrastructure layer and passed in.

Table loader: src/infrastructure/repositories/nhl_wp_repository.load_table()

Returns empirical p(leading team wins) given (period, abs_score_diff,
seconds_remaining). Final outcome includes OT/SO via MoneyPuck final scores.
"""
from __future__ import annotations


def leading_team_win_probability_empirical(
    period: int,
    abs_score_diff: int,
    seconds_remaining: int,
    *,
    table: dict,
) -> float | None:
    """
    Empirical P(leading team is final winner) from MoneyPuck 2022-25 data.

    Args:
        period: 1, 2, 3 (regulation only — OT/SO outcome bucketed into final)
        abs_score_diff: 0 (tied), 1, 2, 3, 4, 5+ (capped at deficit_cap)
        seconds_remaining: regulation total left (0 - 3600)
        table: preloaded dict from nhl_wp_repository.load_table()

    Returns:
        Empirical probability, or None if bucket has too few samples.
    """
    if abs_score_diff < 0:
        raise ValueError("abs_score_diff must be non-negative")
    if abs_score_diff == 0:
        return 0.5

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
    *,
    table: dict,
) -> float | None:
    """Convenience: 1 - leading_p_win. None if leader bucket insufficient."""
    p_lead = leading_team_win_probability_empirical(
        period, deficit, seconds_remaining, table=table
    )
    if p_lead is None:
        return None
    return 1.0 - p_lead


def get_table_metadata(table: dict) -> dict:
    """Return metadata for diagnostic logging."""
    return table["metadata"]
