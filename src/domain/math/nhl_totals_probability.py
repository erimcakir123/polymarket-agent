"""Hybrid totals probability — empirical first, Poisson fallback."""
from __future__ import annotations

from src.domain.math.nhl_totals import poisson_p_over

_TIME_BUCKET_SEC: int = 30
_TOTAL_CAP: int = 12


def p_over_hybrid(
    period: int,
    current_total: int,
    seconds_remaining: int,
    target_total: float,
    *,
    table: dict,
) -> tuple[float, str]:
    """P(final > target_total) — empirical→Poisson hybrid.

    Returns:
        (probability, source) where source in {"empirical", "skellam_fallback"}.
    """
    current_clamped = min(_TOTAL_CAP, current_total)
    time_bucket = (seconds_remaining // _TIME_BUCKET_SEC) * _TIME_BUCKET_SEC
    key = f"{period}_{current_clamped}_{time_bucket}_{target_total}"

    over_table = table.get("totals_over", {})
    entry = over_table.get(key)
    if entry is not None and "p_over" in entry:
        return float(entry["p_over"]), "empirical"

    p = poisson_p_over(current_total, target_total, seconds_remaining)
    return p, "skellam_fallback"
