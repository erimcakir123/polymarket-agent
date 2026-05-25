"""Tennis Data UK historical match + closing odds parser.

Source: http://www.tennis-data.co.uk/ (free, no auth). Provides ATP/WTA
match results with closing odds from Pinnacle (PSW/PSL columns) and B365.

Used by offline calibration scripts (scripts/calibration/) to compare our
Glicko predictions to sharp-money closing odds. NOT used by live bot.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


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
    """Read Tennis Data UK xlsx files (one per year per tour)."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)

    def load_year(self, tour: str, year: int) -> list[TennisDataUKMatch]:
        path = self._cache_dir / f"{tour}_{year}.xlsx"
        if not path.exists():
            logger.warning("Tennis Data UK file missing: %s", path)
            return []
        try:
            import openpyxl
        except ImportError:
            logger.error("openpyxl not installed — cannot parse Tennis Data UK xlsx")
            return []
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = next(rows_iter, None)
        if not headers:
            return []
        idx = {str(h): i for i, h in enumerate(headers) if h is not None}
        matches: list[TennisDataUKMatch] = []
        for row in rows_iter:
            if row is None or all(v is None for v in row):
                continue
            m = self._parse_row(row, idx, tour)
            if m is not None:
                matches.append(m)
        logger.info(
            "Loaded %d Tennis Data UK %s matches from %s",
            len(matches), tour.upper(), path.name,
        )
        return matches

    def load_years(self, tour: str, years: list[int]) -> list[TennisDataUKMatch]:
        out: list[TennisDataUKMatch] = []
        for y in years:
            out.extend(self.load_year(tour, y))
        return out

    @staticmethod
    def _parse_row(
        row: tuple, idx: dict[str, int], tour: str,
    ) -> TennisDataUKMatch | None:
        def get(col: str) -> Any:
            i = idx.get(col)
            return row[i] if i is not None and i < len(row) else None

        try:
            date_raw = get("Date")
            date = str(date_raw)[:10] if date_raw is not None else ""
            return TennisDataUKMatch(
                tour=tour,
                date=date,
                tournament=str(get("Tournament") or ""),
                surface=str(get("Surface") or ""),
                round_=str(get("Round") or ""),
                best_of=int(get("Best of") or 0),
                winner_name=str(get("Winner") or ""),
                loser_name=str(get("Loser") or ""),
                winner_rank=_to_int(get("WRank")),
                loser_rank=_to_int(get("LRank")),
                pinnacle_winner_odds=_to_float(get("PSW")),
                pinnacle_loser_odds=_to_float(get("PSL")),
            )
        except (ValueError, TypeError) as e:
            logger.debug("Skipping bad Tennis Data UK row: %s", e)
            return None


def _to_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _to_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
