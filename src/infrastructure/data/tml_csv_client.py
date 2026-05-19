"""TML-Database (Tennismylife) CSV reader — backup data source.

GitHub: https://github.com/Tennismylife/TML-Database
TML schema has additional 'indoor' column; otherwise SackmannMatch-compatible.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §3.1
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.infrastructure.data.sackmann_csv_client import SackmannMatch

logger = logging.getLogger(__name__)


class TmlCsvClient:
    """TML CSV reader — returns SackmannMatch-compatible records.

    TML schema includes an extra 'indoor' column that this client silently drops.
    All other columns match Sackmann ATP schema 1:1.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)

    def load_year(self, year: int) -> list[SackmannMatch]:
        """Tek yılın CSV'sini oku. Dosya yoksa boş döner."""
        path = self._cache_dir / f"{year}.csv"
        if not path.exists():
            logger.warning("TML CSV missing: %s", path)
            return []
        matches: list[SackmannMatch] = []
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                m = self._parse_row(row)
                if m is not None:
                    matches.append(m)
        logger.info("Loaded %d TML matches from %s", len(matches), path.name)
        return matches

    def _parse_row(self, row: dict[str, str]) -> Optional[SackmannMatch]:
        try:
            return SackmannMatch(
                tourney_id=row.get("tourney_id", ""),
                tourney_name=row.get("tourney_name", ""),
                surface=row.get("surface", ""),
                draw_size=int(row.get("draw_size") or 0),
                tourney_level=row.get("tourney_level", ""),
                match_date=datetime.strptime(row.get("tourney_date", ""), "%Y%m%d"),
                match_num=int(row.get("match_num") or 0),
                winner_id=row.get("winner_id", ""),
                winner_name=row.get("winner_name", ""),
                winner_hand=row.get("winner_hand", ""),
                loser_id=row.get("loser_id", ""),
                loser_name=row.get("loser_name", ""),
                loser_hand=row.get("loser_hand", ""),
                score=row.get("score", ""),
                best_of=int(row.get("best_of") or 3),
                round=row.get("round", ""),
                minutes=self._to_int(row.get("minutes")),
                w_ace=self._to_int(row.get("w_ace")),
                w_df=self._to_int(row.get("w_df")),
                w_svpt=self._to_int(row.get("w_svpt")),
                w_1stIn=self._to_int(row.get("w_1stIn")),
                w_1stWon=self._to_int(row.get("w_1stWon")),
                w_2ndWon=self._to_int(row.get("w_2ndWon")),
                w_SvGms=self._to_int(row.get("w_SvGms")),
                w_bpSaved=self._to_int(row.get("w_bpSaved")),
                w_bpFaced=self._to_int(row.get("w_bpFaced")),
                l_ace=self._to_int(row.get("l_ace")),
                l_df=self._to_int(row.get("l_df")),
                l_svpt=self._to_int(row.get("l_svpt")),
                l_1stIn=self._to_int(row.get("l_1stIn")),
                l_1stWon=self._to_int(row.get("l_1stWon")),
                l_2ndWon=self._to_int(row.get("l_2ndWon")),
                l_SvGms=self._to_int(row.get("l_SvGms")),
                l_bpSaved=self._to_int(row.get("l_bpSaved")),
                l_bpFaced=self._to_int(row.get("l_bpFaced")),
                winner_rank=self._to_int(row.get("winner_rank")),
                winner_rank_points=self._to_int(row.get("winner_rank_points")),
                loser_rank=self._to_int(row.get("loser_rank")),
                loser_rank_points=self._to_int(row.get("loser_rank_points")),
            )
        except (ValueError, KeyError) as e:
            logger.warning("Skipping TML bad row: %s", e)
            return None

    @staticmethod
    def _to_int(v: str | None) -> int | None:
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None
