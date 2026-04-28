"""Hybrid puck line cover probability — empirical first, Skellam fallback.

Caller pattern:
    table = load_table()  # from infrastructure.repositories.nhl_puck_line_repository
    p, source = p_favorite_covers_hybrid(period, margin, seconds, table=table)
"""
from __future__ import annotations

from src.domain.math.nhl_puck_line import skellam_p_favorite_covers_minus_1_5

_TIME_BUCKET_SEC: int = 30
_MARGIN_CAP: int = 5


def p_favorite_covers_hybrid(
    period: int,
    current_margin: int,
    seconds_remaining: int,
    *,
    table: dict,
) -> tuple[float, str]:
    """P(home favori -1.5 cover) — empirical→Skellam hybrid.

    Returns:
        (probability, source) where source in {"empirical", "skellam_fallback"}.
    """
    margin_clamped = max(-_MARGIN_CAP, min(_MARGIN_CAP, current_margin))
    time_bucket = (seconds_remaining // _TIME_BUCKET_SEC) * _TIME_BUCKET_SEC
    key = f"{period}_{margin_clamped}_{time_bucket}"

    cover_table = table.get("puck_line_cover", {})
    entry = cover_table.get(key)
    if entry is not None and "p_favorite_covers" in entry:
        return float(entry["p_favorite_covers"]), "empirical"

    p = skellam_p_favorite_covers_minus_1_5(current_margin, seconds_remaining)
    return p, "skellam_fallback"
