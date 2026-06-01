"""Sackmann CSV cache refresher — download orchestration + staleness check.

Sackmann publishes weekly match updates on GitHub. The bot caches CSVs locally
in ``data/sackmann_cache/`` and reads them via ``SackmannCsvClient``. This
module keeps the cache current.

Public API:
  - ``is_cache_stale(cache_dir, max_age_days)``: True if current-year file
    missing or older than threshold.
  - ``refresh_cache(cache_dir, years, http_get)``: download all 5 categories
    (ATP main/Challenger/ITF + WTA main/qual+ITF) for given years.
  - ``refresh_if_stale(cache_dir, max_age_days, years, http_get)``: combined
    check + refresh, returns True if refresh ran.

Atomic writes (tmp → rename) prevent partial files from corrupting the cache
when downloads are interrupted.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import requests

logger = logging.getLogger(__name__)


# Sackmann publishes ~weekly. 3-day threshold gives slack while keeping data
# within the bot's prediction horizon (max_hours_to_start=72h).
_DEFAULT_MAX_AGE_DAYS = 3

# Only the last N years see active updates (historic years are static).
_RECENT_YEARS_TO_REFRESH = 2

# Per-category download spec. URL on Sackmann's GitHub vs cache filename diverge
# for two categories (ITF / WTA qual+ITF) — explicit mapping prevents drift.
_SOURCES: dict[str, dict[str, str]] = {
    "atp_main": {
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{year}.csv",
        "file": "atp_matches_{year}.csv",
    },
    "atp_chall": {
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_qual_chall_{year}.csv",
        "file": "atp_matches_qual_chall_{year}.csv",
    },
    "atp_futures": {
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_futures_{year}.csv",
        "file": "atp_futures_{year}.csv",
    },
    "wta_main": {
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{year}.csv",
        "file": "wta_matches_{year}.csv",
    },
    "wta_futures": {
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_qual_itf_{year}.csv",
        "file": "wta_futures_{year}.csv",
    },
    # Task 2 (2026-06-01): Doubles maçları — Wimbledon Doubles, Roland Garros Doubles
    # gibi Grand Slam doubles market'leri için. Pricer src/domain/pricing/tennis/doubles_pricer.py.
    "atp_doubles": {
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_doubles_{year}.csv",
        "file": "atp_matches_doubles_{year}.csv",
    },
    "wta_doubles": {
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_doubles_{year}.csv",
        "file": "wta_matches_doubles_{year}.csv",
    },
}


def is_cache_stale(
    cache_dir: Path,
    max_age_days: int = _DEFAULT_MAX_AGE_DAYS,
) -> bool:
    """True if the current-year ATP main CSV is missing/old OR any expected file
    (per _SOURCES, including doubles) is missing for the current year.

    Canary file = ATP main + age check (Sackmann updates in lockstep).
    Coverage check = expected files all present (Task 2 doubles fix: yeni source
    eklendi ama canary fresh diye skip oluyordu).
    """
    current_year = datetime.utcnow().year
    canary = cache_dir / f"atp_matches_{current_year}.csv"
    if not canary.exists():
        return True
    age_days = (time.time() - canary.stat().st_mtime) / 86400.0
    if age_days > max_age_days:
        return True
    # 2026-06-01: missing-file detection — _SOURCES'a yeni kategori eklenince
    # eski cache canary'yi fresh sayıp yeni dosyaları indirmeyebilir.
    for spec in _SOURCES.values():
        expected = cache_dir / spec["file"].format(year=current_year)
        if not expected.exists():
            return True
    return False


def _download_one(
    url: str,
    dest: Path,
    http_get: Callable,
    timeout: int = 30,
) -> bool:
    """Download a single CSV with atomic write. Returns True on success.

    Failures (network error, non-200 status) log a warning and return False
    so the caller can continue with other downloads.
    """
    try:
        resp = http_get(url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — infrastructure boundary, log + skip
        logger.warning("Sackmann download failed (network): %s — %s", url, exc)
        return False
    status = getattr(resp, "status_code", 0)
    if status != 200:
        logger.warning("Sackmann download non-200: %s -> %d", url, status)
        return False
    body = getattr(resp, "text", "")
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(dest)
    return True


def refresh_cache(
    cache_dir: Path,
    years: list[int],
    http_get: Callable | None = None,
) -> dict[str, int]:
    """Download all 5 source categories for the given years.

    Returns per-category success counts. Individual failures are logged but
    do not abort the run — partial refresh is better than no refresh.
    """
    if http_get is None:
        http_get = requests.get
    cache_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {k: 0 for k in _SOURCES}
    for year in years:
        for category, spec in _SOURCES.items():
            url = spec["url"].format(year=year)
            dest = cache_dir / spec["file"].format(year=year)
            if _download_one(url, dest, http_get):
                counts[category] += 1
    return counts


def refresh_if_stale(
    cache_dir: Path,
    max_age_days: int = _DEFAULT_MAX_AGE_DAYS,
    years: list[int] | None = None,
    http_get: Callable | None = None,
) -> bool:
    """If cache stale, refresh recent years' CSVs. Returns True if refresh ran.

    Default years: current + previous (Sackmann year-boundary updates may
    backfill into prior year for a few weeks).
    """
    if not is_cache_stale(cache_dir, max_age_days):
        logger.info(
            "Sackmann cache fresh (canary < %d days old) — skip refresh",
            max_age_days,
        )
        return False
    if years is None:
        current = datetime.utcnow().year
        years = [current - i for i in range(_RECENT_YEARS_TO_REFRESH)]
    logger.info("Sackmann cache stale — refreshing years=%s", years)
    counts = refresh_cache(cache_dir, years, http_get=http_get)
    total = sum(counts.values())
    expected = len(years) * len(_SOURCES)
    logger.info(
        "Sackmann refresh: %d/%d files downloaded (counts=%s)",
        total, expected, counts,
    )
    return True
