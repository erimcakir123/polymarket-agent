"""Hybrid puck line cover probability — empirical first, Skellam fallback.

Caller pattern:
    table = load_table()  # from infrastructure.repositories.nhl_puck_line_repository
    p, source = p_favorite_covers_hybrid(period, margin, seconds, table=table)
"""
from __future__ import annotations

from src.domain.math.nhl_puck_line import skellam_p_favorite_covers_minus_1_5
from src.domain.sports.nhl_match_clock import REGULATION_PERIOD_SECONDS

_TIME_BUCKET_SEC: int = 30
_MARGIN_CAP: int = 5


def _period_from_seconds(time_bucket: int) -> int:
    # Empirical tablo periyot konvansiyonu: time_bucket "geriye kalan saniye"
    # cinsinden ifade edildiği period namespace'ine yerleştirilir.
    # Sınır anlarda (P2 sonu = P3 başı) caller'ın period parametresi
    # bir geride olabilir; lookup time_bucket'tan türeyen period ile yapılır.
    if time_bucket > 2 * REGULATION_PERIOD_SECONDS:
        return 1
    if time_bucket > REGULATION_PERIOD_SECONDS:
        return 2
    return 3


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

    # OT/SO (period >= 4): empirical tablo sadece regulation kapsıyor.
    # Doğrudan Skellam'a düş; aksi halde sec_remaining=0 → "3_X_0" yanlış hit.
    if period >= 4:
        p = skellam_p_favorite_covers_minus_1_5(current_margin, seconds_remaining)
        return p, "skellam_fallback"

    lookup_period = _period_from_seconds(time_bucket)
    key = f"{lookup_period}_{margin_clamped}_{time_bucket}"

    cover_table = table.get("puck_line_cover", {})
    entry = cover_table.get(key)
    if entry is not None and "p_favorite_covers" in entry:
        return float(entry["p_favorite_covers"]), "empirical"

    p = skellam_p_favorite_covers_minus_1_5(current_margin, seconds_remaining)
    return p, "skellam_fallback"
