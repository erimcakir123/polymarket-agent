"""Sackmann ATP CSV reader (1968-present, MIT licensed).

GitHub: https://github.com/JeffSackmann/tennis_atp
Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §3.1
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ITF Futures tourney_level codes (Sackmann convention).
# WTA "qual_itf" CSVs mix WTA qualifying + ITF; filter on level keeps only ITF.
# ATP "futures" CSVs are pure ITF but we filter uniformly for defensiveness.
# Levels 15/25/60 cover $15K/$25K/$60K prize money. 75/100 exist for larger ITF
# events. Anything else (S=qualifying, A=ATP/WTA, M=Masters, G=Grand Slam,
# C=Challenger) is excluded.
_ITF_TOURNEY_LEVELS = frozenset({"15", "25", "60", "75", "100"})


@dataclass
class SackmannMatch:
    """Single ATP match record from Sackmann CSV.

    Field names match Sackmann CSV columns (49 columns).
    """
    tourney_id: str
    tourney_name: str
    surface: str  # "Hard" / "Clay" / "Grass" / "Carpet"
    draw_size: int
    tourney_level: str  # "G"=GrandSlam, "M"=Masters, "A"=ATP500/250, "C"=Challenger
    match_date: datetime
    match_num: int
    winner_id: str
    winner_name: str
    winner_hand: str
    loser_id: str
    loser_name: str
    loser_hand: str
    score: str
    best_of: int
    round: str
    minutes: Optional[int]
    # Serve stats - winner
    w_ace: Optional[int]
    w_df: Optional[int]
    w_svpt: Optional[int]
    w_1stIn: Optional[int]
    w_1stWon: Optional[int]
    w_2ndWon: Optional[int]
    w_SvGms: Optional[int]
    w_bpSaved: Optional[int]
    w_bpFaced: Optional[int]
    # Serve stats - loser
    l_ace: Optional[int]
    l_df: Optional[int]
    l_svpt: Optional[int]
    l_1stIn: Optional[int]
    l_1stWon: Optional[int]
    l_2ndWon: Optional[int]
    l_SvGms: Optional[int]
    l_bpSaved: Optional[int]
    l_bpFaced: Optional[int]
    winner_rank: Optional[int]
    winner_rank_points: Optional[int]
    loser_rank: Optional[int]
    loser_rank_points: Optional[int]


class SackmannCsvClient:
    """Sackmann ATP CSV reader.

    Tek sorumluluk: yıllık CSV'yi parse et, SackmannMatch listesi döndür.
    Veri silimi/güncelleme YOK — sadece okur.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)

    def load_year(self, year: int) -> list[SackmannMatch]:
        """Tek yılın ATP main-draw CSV'sini oku. Dosya yoksa boş döner."""
        path = self._cache_dir / f"atp_matches_{year}.csv"
        if not path.exists():
            logger.warning("Sackmann CSV missing: %s", path)
            return []
        matches: list[SackmannMatch] = []
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                m = self._parse_row(row)
                if m is not None:
                    matches.append(m)
        logger.info("Loaded %d matches from %s", len(matches), path.name)
        return matches

    def load_wta_year(self, year: int) -> list[SackmannMatch]:
        """Tek yılın WTA main-draw CSV'sini oku. Dosya yoksa boş döner.

        WTA CSV formatı ATP ile aynı 49-kolon — sadece dosya adı 'wta_matches_'.
        """
        path = self._cache_dir / f"wta_matches_{year}.csv"
        if not path.exists():
            logger.warning("Sackmann WTA CSV missing: %s", path)
            return []
        matches: list[SackmannMatch] = []
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                m = self._parse_row(row)
                if m is not None:
                    matches.append(m)
        logger.info("Loaded %d WTA matches from %s", len(matches), path.name)
        return matches

    def load_wta_years(self, years: list[int]) -> list[SackmannMatch]:
        """Birden fazla yıl WTA main-draw yükle, birleştir, kronolojik sırala."""
        all_matches: list[SackmannMatch] = []
        for y in years:
            all_matches.extend(self.load_wta_year(y))
        all_matches.sort(key=lambda m: m.match_date)
        return all_matches

    def load_challenger_year(self, year: int) -> list[SackmannMatch]:
        """Tek yılın Challenger CSV'sini oku (sadece tourney_level='C' satırları).

        Dosya: atp_matches_qual_chall_{year}.csv (qualifier+challenger mix).
        Sadece 'C' seviyesi alınır — ATP main draw satırları (G/A/M) atlanır,
        çünkü bunlar load_year() ile zaten dahil edilmiş olacak.
        """
        path = self._cache_dir / f"atp_matches_qual_chall_{year}.csv"
        if not path.exists():
            logger.warning("Sackmann Challenger CSV missing: %s", path)
            return []
        matches: list[SackmannMatch] = []
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("tourney_level", "") != "C":
                    continue
                m = self._parse_row(row)
                if m is not None:
                    matches.append(m)
        logger.info("Loaded %d challenger matches from %s", len(matches), path.name)
        return matches

    def load_years(self, years: list[int]) -> list[SackmannMatch]:
        """Birden fazla yıl ATP main-draw yükle, birleştir, kronolojik sırala."""
        all_matches: list[SackmannMatch] = []
        for y in years:
            all_matches.extend(self.load_year(y))
        all_matches.sort(key=lambda m: m.match_date)
        return all_matches

    def load_challenger_years(self, years: list[int]) -> list[SackmannMatch]:
        """Birden fazla yıl Challenger maç yükle, birleştir, kronolojik sırala."""
        all_matches: list[SackmannMatch] = []
        for y in years:
            all_matches.extend(self.load_challenger_year(y))
        all_matches.sort(key=lambda m: m.match_date)
        return all_matches

    def load_itf_year(self, tour: str, year: int) -> list[SackmannMatch]:
        """ITF Futures CSV for a single year/tour.

        File: {tour}_futures_{year}.csv (must already be in cache_dir from
        fetch_sackmann_data step). Same 49-column schema as ATP/WTA main draw.
        Filters tourney_level to ITF tiers only (15/25/60/75/100); excludes
        WTA qualifying entries which share the same CSV file upstream.
        """
        path = self._cache_dir / f"{tour}_futures_{year}.csv"
        if not path.exists():
            logger.warning("Sackmann ITF CSV missing: %s", path)
            return []
        matches: list[SackmannMatch] = []
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row.get("tourney_level", "") or "") not in _ITF_TOURNEY_LEVELS:
                    continue
                m = self._parse_row(row)
                if m is not None:
                    matches.append(m)
        logger.info("Loaded %d %s ITF matches from %s", len(matches), tour.upper(), path.name)
        return matches

    def load_itf_years(self, tour: str, years: list[int]) -> list[SackmannMatch]:
        """Aggregate multiple years of ITF Futures matches, sorted chronologically."""
        all_matches: list[SackmannMatch] = []
        for y in years:
            all_matches.extend(self.load_itf_year(tour, y))
        all_matches.sort(key=lambda m: m.match_date)
        return all_matches

    def count_doubles_matches_by_player(
        self, tour: str, years: list[int], cutoff_date: datetime,
    ) -> dict[str, int]:
        """Return {player_name: count_of_doubles_matches_since_cutoff_date}.

        Doubles CSV has 4 player columns (winner1_name, winner2_name, loser1_name,
        loser2_name). Each match contributes +1 to count for all 4 players that
        played on/after cutoff_date.

        Used for filter purposes only — doubles results DO NOT update singles Glicko
        ratings (different skill set).
        """
        counts: dict[str, int] = {}
        for year in years:
            path = self._cache_dir / f"{tour}_doubles_{year}.csv"
            if not path.exists():
                logger.warning("Sackmann doubles CSV missing: %s", path)
                continue
            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse date — bail if before cutoff
                    try:
                        dt = datetime.strptime(row.get("tourney_date", "") or "", "%Y%m%d")
                    except ValueError:
                        continue
                    if dt < cutoff_date:
                        continue
                    for col in ("winner1_name", "winner2_name", "loser1_name", "loser2_name"):
                        name = (row.get(col) or "").strip()
                        if name:
                            counts[name] = counts.get(name, 0) + 1
        return counts

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
            logger.warning("Skipping bad row: %s", e)
            return None

    @staticmethod
    def _to_int(v: str | None) -> int | None:
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None
