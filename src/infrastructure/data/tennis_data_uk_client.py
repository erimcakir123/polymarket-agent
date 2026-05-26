"""Tennis Data UK historical match + closing odds parser.

Source: Kaggle mirror of tennis-data.co.uk — combined per-tour CSV
(`df_atp.csv`, `df_wta.csv`). Original tennis-data.co.uk hosts per-year
xlsx files but the site blocks scripted downloads; the Kaggle mirror
(EdouardThomas/tennis-data-from-www-tennis-data-co-uk and similar) packs
the same data into one CSV per tour. Coverage stops at ~2019; updates
require a manual re-download when a newer mirror is published.

Provides Pinnacle closing odds (PSW/PSL columns). Used by offline
calibration scripts to compare our Glicko predictions to sharp-money
closing odds. NOT used by live bot.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)

_TOUR_FILENAME = {"atp": "df_atp.csv", "wta": "df_wta.csv"}


@dataclass(frozen=True)
class TennisDataUKMatch:
    tour: str
    date: str
    tournament: str
    surface: str
    round_: str
    best_of: int
    winner_name: str
    loser_name: str
    winner_rank: Optional[int]
    loser_rank: Optional[int]
    pinnacle_winner_odds: Optional[float]
    pinnacle_loser_odds: Optional[float]


class TennisDataUKClient:
    """Read Tennis Data UK combined CSV (one file per tour, all years)."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)

    def load_all(self, tour: str) -> list[TennisDataUKMatch]:
        return list(self._iter_matches(tour, year_filter=None))

    def load_year(self, tour: str, year: int) -> list[TennisDataUKMatch]:
        return list(self._iter_matches(tour, year_filter=year))

    def load_years(self, tour: str, years: list[int]) -> list[TennisDataUKMatch]:
        wanted = set(years)
        out: list[TennisDataUKMatch] = []
        for m in self._iter_matches(tour, year_filter=None):
            if m.date[:4].isdigit() and int(m.date[:4]) in wanted:
                out.append(m)
        return out

    def _iter_matches(
        self, tour: str, year_filter: Optional[int],
    ) -> Iterator[TennisDataUKMatch]:
        filename = _TOUR_FILENAME.get(tour.lower())
        if filename is None:
            logger.warning("Unknown tour: %s (expected atp|wta)", tour)
            return
        path = self._cache_dir / filename
        if not path.exists():
            logger.warning("Tennis Data UK file missing: %s", path)
            return
        kept = 0
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            year_prefix = f"{year_filter}" if year_filter is not None else None
            for row in reader:
                date_raw = (row.get("Date") or "").strip()
                if year_prefix and not date_raw.startswith(year_prefix):
                    continue
                m = self._parse_row(row, tour.lower())
                if m is not None:
                    kept += 1
                    yield m
        logger.info(
            "Loaded %d Tennis Data UK %s matches from %s (year_filter=%s)",
            kept, tour.upper(), filename, year_filter,
        )

    @staticmethod
    def _parse_row(row: dict, tour: str) -> TennisDataUKMatch | None:
        try:
            date_raw = (row.get("Date") or "").strip()
            return TennisDataUKMatch(
                tour=tour,
                date=date_raw[:10],
                tournament=str(row.get("Tournament") or ""),
                surface=str(row.get("Surface") or ""),
                round_=str(row.get("Round") or ""),
                best_of=int(row.get("Best of") or 0),
                winner_name=str(row.get("Winner") or ""),
                loser_name=str(row.get("Loser") or ""),
                winner_rank=_to_int(row.get("WRank")),
                loser_rank=_to_int(row.get("LRank")),
                pinnacle_winner_odds=_to_float(row.get("PSW")),
                pinnacle_loser_odds=_to_float(row.get("PSL")),
            )
        except (ValueError, TypeError) as e:
            logger.debug("Skipping bad Tennis Data UK row: %s", e)
            return None


def _to_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _to_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
