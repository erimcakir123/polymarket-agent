"""Reyting veri tazeliği — saf karar (bayat mı?).

newest/today YYYYMMDD string. I/O yok; çağıran tarihleri verir.
"""
from __future__ import annotations

from datetime import date


def _parse(yyyymmdd: str) -> date:
    return date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8]))


def is_ratings_stale(
    newest_yyyymmdd: str | None, today_yyyymmdd: str, threshold_days: int
) -> bool:
    """En yeni maç bugünden threshold_days'ten ESKİYSE bayat. Veri yoksa bayat."""
    if not newest_yyyymmdd:
        return True
    age = (_parse(today_yyyymmdd) - _parse(newest_yyyymmdd)).days
    return age > threshold_days
