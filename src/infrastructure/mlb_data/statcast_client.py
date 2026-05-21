"""Statcast event aggregation to PA outcome rates (via pybaseball).

SPEC-R Plan 3 T2. Wraps pybaseball.statcast_batter / statcast_pitcher to fetch
pitch-by-pitch data, filters to PA-ending events, aggregates to outcome rates.

Optional file cache (JSON) keyed by (mlbam_id, season, role) to avoid re-fetching.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

try:
    import pybaseball
except ImportError as e:
    pybaseball = None  # type: ignore[assignment]
    _IMPORT_ERROR: Exception | None = e
else:
    _IMPORT_ERROR = None

logger = logging.getLogger(__name__)


class StatcastError(Exception):
    """Raised when Statcast fetch or import fails."""


_EVENT_MAP: dict[str, str] = {
    "strikeout": "K",
    "strikeout_double_play": "K",
    "walk": "BB",
    "intent_walk": "BB",
    "hit_by_pitch": "HBP",
    "home_run": "HR",
    "single": "1B",
    "double": "2B",
    "triple": "3B",
    # All others (field_out, force_out, double_play, sac_fly, fielders_choice, etc.)
    # → OUT_IN_PLAY (handled as default in _aggregate_rates)
}

_ALL_OUTCOMES: tuple[str, ...] = ("K", "BB", "HBP", "HR", "1B", "2B", "3B", "OUT_IN_PLAY")


def _aggregate_rates(events_series: Any) -> dict[str, float]:
    """Aggregate pandas Series of event strings to PA outcome rates dict.

    Drops NaN rows (non-AB-ending pitches) before counting. Returns empty dict
    when zero PA-ending events found.
    """
    # dropna() removes float NaN values produced by pandas for missing cells
    non_null = events_series.dropna().tolist()
    # Further filter empty strings just in case
    pa_events = [ev for ev in non_null if ev]

    n_pa = len(pa_events)
    if n_pa == 0:
        return {}

    counts: dict[str, int] = {o: 0 for o in _ALL_OUTCOMES}
    for ev in pa_events:
        outcome = _EVENT_MAP.get(ev, "OUT_IN_PLAY")
        counts[outcome] += 1

    return {o: counts[o] / n_pa for o in _ALL_OUTCOMES}


class StatcastClient:
    """Fetches Statcast pitch-by-pitch data and returns PA outcome rates.

    Uses pybaseball under the hood. Optionally caches results to JSON files
    on disk keyed by (role, mlbam_id, season) to avoid redundant API calls.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        if pybaseball is None:
            raise StatcastError(
                f"pybaseball not installed: {_IMPORT_ERROR}. "
                "Install via: pip install pybaseball>=2.2"
            )
        self.cache_dir = cache_dir
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_path(self, mlbam_id: int, season: int, role: str) -> Path | None:
        if self.cache_dir is None:
            return None
        return self.cache_dir / f"{role}_{mlbam_id}_{season}.json"

    def _read_cache(self, path: Path | None) -> dict[str, float] | None:
        if path is None or not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Cache read failed %s: %s", path, exc)
            return None

    def _write_cache(self, path: Path | None, rates: dict[str, float]) -> None:
        if path is None:
            return
        try:
            path.write_text(json.dumps(rates), encoding="utf-8")
        except OSError as exc:
            logger.warning("Cache write failed %s: %s", path, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_batter_rates(self, mlbam_id: int, season: int) -> dict[str, float]:
        """Return PA outcome rates for a batter in a given season.

        Keys: K, BB, HBP, HR, 1B, 2B, 3B, OUT_IN_PLAY. Sum == 1.0 if data
        exists. Returns empty dict when no PA-ending events found.

        Raises:
            StatcastError: on pybaseball API failure.
        """
        cache_path = self._cache_path(mlbam_id, season, "batter")
        cached = self._read_cache(cache_path)
        if cached is not None:
            return cached

        try:
            start = f"{season}-03-01"
            end = f"{season}-11-30"
            df = pybaseball.statcast_batter(start, end, mlbam_id)
        except Exception as exc:
            logger.error(
                "statcast_batter failed for mlbam_id=%d season=%d: %s",
                mlbam_id,
                season,
                exc,
            )
            raise StatcastError(
                f"statcast_batter {mlbam_id} {season}: {exc}"
            ) from exc

        if "events" not in df.columns or len(df) == 0:
            return {}

        rates = _aggregate_rates(df["events"])
        self._write_cache(cache_path, rates)
        return rates

    def get_pitcher_rates(self, mlbam_id: int, season: int) -> dict[str, float]:
        """Return PA outcome rates for a pitcher in a given season.

        Keys: K, BB, HBP, HR, 1B, 2B, 3B, OUT_IN_PLAY. Sum == 1.0 if data
        exists. Returns empty dict when no PA-ending events found.

        Raises:
            StatcastError: on pybaseball API failure.
        """
        cache_path = self._cache_path(mlbam_id, season, "pitcher")
        cached = self._read_cache(cache_path)
        if cached is not None:
            return cached

        try:
            start = f"{season}-03-01"
            end = f"{season}-11-30"
            df = pybaseball.statcast_pitcher(start, end, mlbam_id)
        except Exception as exc:
            logger.error(
                "statcast_pitcher failed for mlbam_id=%d season=%d: %s",
                mlbam_id,
                season,
                exc,
            )
            raise StatcastError(
                f"statcast_pitcher {mlbam_id} {season}: {exc}"
            ) from exc

        if "events" not in df.columns or len(df) == 0:
            return {}

        rates = _aggregate_rates(df["events"])
        self._write_cache(cache_path, rates)
        return rates
