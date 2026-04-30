"""Hybrid totals probability — empirical first, Poisson fallback."""
from __future__ import annotations

from src.domain.math.nhl_totals import poisson_p_over
from src.domain.sports.nhl_match_clock import REGULATION_PERIOD_SECONDS

_TIME_BUCKET_SEC: int = 30
_TOTAL_CAP: int = 12


def _period_from_seconds(time_bucket: int) -> int:
    # Empirical tablo periyot konvansiyonu: time_bucket geriye-kalan-saniye
    # cinsinden ifade edildiği period namespace'ine yerleştirilir. Sınırda
    # (P2 sonu = P3 başı) caller'ın period parametresi bir geride olabilir.
    if time_bucket > 2 * REGULATION_PERIOD_SECONDS:
        return 1
    if time_bucket > REGULATION_PERIOD_SECONDS:
        return 2
    return 3


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

    # OT/SO (period >= 4): empirical tablo sadece regulation kapsıyor.
    if period >= 4:
        p = poisson_p_over(current_total, target_total, seconds_remaining)
        return p, "skellam_fallback"

    lookup_period = _period_from_seconds(time_bucket)
    key = f"{lookup_period}_{current_clamped}_{time_bucket}_{target_total}"

    over_table = table.get("totals_over", {})
    entry = over_table.get(key)
    if entry is not None and "p_over" in entry:
        return float(entry["p_over"]), "empirical"

    p = poisson_p_over(current_total, target_total, seconds_remaining)
    return p, "skellam_fallback"
