"""Sackmann CSV reader — match records as dataclasses.

Infrastructure layer: file/IO at boundary, returns plain dataclasses to domain.
Bad rows logged + skipped (ARCH_GUARD Kural 12 — infra hatası default ile devam).
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from typing import TextIO

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MatchRecord:
    tourney_id: str
    tourney_date: str  # YYYYMMDD
    surface: str
    winner_name: str
    loser_name: str
    w_svpt: int
    w_1st_in: int
    w_1st_won: int
    w_2nd_won: int
    w_sv_gms: int
    l_svpt: int
    l_1st_in: int
    l_1st_won: int
    l_2nd_won: int
    l_sv_gms: int
    best_of: int
    score: str


def _parse_int(val) -> int | None:
    if val is None:
        return None
    try:
        s = str(val).strip()
        return int(s) if s else None
    except ValueError:
        return None


_NUMERIC_FIELDS = (
    "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon", "w_SvGms",
    "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "l_SvGms",
)


def _row_to_record(row: dict) -> MatchRecord | None:
    numeric: dict[str, int] = {}
    for key in _NUMERIC_FIELDS:
        parsed = _parse_int(row.get(key, ""))
        if parsed is None:
            return None
        numeric[key] = parsed
    return MatchRecord(
        tourney_id=row.get("tourney_id") or "",
        tourney_date=row.get("tourney_date") or "",
        surface=row.get("surface") or "Unknown",
        winner_name=(row.get("winner_name") or "").strip(),
        loser_name=(row.get("loser_name") or "").strip(),
        w_svpt=numeric["w_svpt"],
        w_1st_in=numeric["w_1stIn"],
        w_1st_won=numeric["w_1stWon"],
        w_2nd_won=numeric["w_2ndWon"],
        w_sv_gms=numeric["w_SvGms"],
        l_svpt=numeric["l_svpt"],
        l_1st_in=numeric["l_1stIn"],
        l_1st_won=numeric["l_1stWon"],
        l_2nd_won=numeric["l_2ndWon"],
        l_sv_gms=numeric["l_SvGms"],
        best_of=_parse_int(row.get("best_of", "")) or 3,
        score=row.get("score") or "",
    )


def load_matches_from_csv(handle: TextIO) -> list[MatchRecord]:
    reader = csv.DictReader(handle)
    out: list[MatchRecord] = []
    for row in reader:
        rec = _row_to_record(row)
        if rec is None:
            continue
        out.append(rec)
    return out


def load_matches_from_path(path) -> list[MatchRecord]:
    with open(path, encoding="utf-8") as f:
        return load_matches_from_csv(f)
