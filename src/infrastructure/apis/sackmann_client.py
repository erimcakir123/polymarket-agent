"""Sackmann tennis_atp / tennis_wta CSV client.

Fetches CSVs from GitHub, caches locally, parses player + match data.
Aggregates serve statistics per player (rolling 12-month, optionally
surface-filtered).
"""
from __future__ import annotations

import csv
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import requests

from src.domain.matching.tennis_player_resolver import PlayerRecord


logger = logging.getLogger(__name__)


_SACKMANN_BASE_ATP = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master"
_SACKMANN_BASE_WTA = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master"
_HTTP_TIMEOUT = 30


@dataclass(frozen=True)
class PlayerServeStats:
    name: str
    matches_played: int
    service_points_won_pct: float
    surface: Literal["clay", "hard", "grass"] | None
    last_match_date: str  # ISO YYYY-MM-DD


@dataclass
class SackmannCache:
    cache_dir: Path
    refresh_days: int

    def needs_refresh(self, filename: str) -> bool:
        path = self.cache_dir / filename
        if not path.exists():
            return True
        age_days = (time.time() - path.stat().st_mtime) / 86400.0
        return age_days >= self.refresh_days


def parse_players_csv(path: Path) -> list[PlayerRecord]:
    """Parse Sackmann atp_players.csv into PlayerRecord list."""
    records: list[PlayerRecord] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(PlayerRecord(
                sackmann_id=row.get("player_id", "").strip(),
                first=row.get("name_first", "").strip(),
                last=row.get("name_last", "").strip(),
                hand=row.get("hand", "").strip(),
                country=row.get("country", "").strip(),
            ))
    return records


def parse_matches_csv(path: Path) -> list[dict]:
    """Parse Sackmann atp_matches_YYYY.csv. Returns dict per row."""
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def aggregate_player_stats(
    player_name: str,
    matches: list[dict],
    surface: Literal["clay", "hard", "grass"] | None,
) -> PlayerServeStats | None:
    """Compute serve stats for a player, optionally surface-filtered."""
    matches_filtered = []
    for m in matches:
        if surface is not None:
            row_surface = m.get("surface", "").strip().lower()
            if surface == "clay" and row_surface != "clay":
                continue
            if surface == "hard" and row_surface != "hard":
                continue
            if surface == "grass" and row_surface != "grass":
                continue
        if player_name in (m.get("winner_name", ""), m.get("loser_name", "")):
            matches_filtered.append(m)

    if not matches_filtered:
        return None

    total_pts = 0
    total_won = 0
    last_date = ""

    for m in matches_filtered:
        is_winner = m.get("winner_name") == player_name
        prefix = "w_" if is_winner else "l_"
        try:
            svpt = int(m.get(f"{prefix}svpt", "0") or 0)
            first_won = int(m.get(f"{prefix}1stWon", "0") or 0)
            second_won = int(m.get(f"{prefix}2ndWon", "0") or 0)
        except ValueError:
            continue
        if svpt == 0:
            continue
        total_pts += svpt
        total_won += first_won + second_won
        date_str = m.get("tourney_date", "")
        if date_str > last_date:
            last_date = date_str

    if total_pts == 0:
        return None

    pct = total_won / total_pts
    iso_date = ""
    if len(last_date) == 8:
        iso_date = f"{last_date[:4]}-{last_date[4:6]}-{last_date[6:]}"

    return PlayerServeStats(
        name=player_name,
        matches_played=len(matches_filtered),
        service_points_won_pct=pct,
        surface=surface,
        last_match_date=iso_date,
    )


def fetch_csv_to_cache(
    url: str,
    cache_path: Path,
    timeout: int = _HTTP_TIMEOUT,
) -> bool:
    """Fetch CSV from URL, write to cache_path. Returns True on success."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
        tmp_path.write_text(resp.text, encoding="utf-8")
        os.replace(tmp_path, cache_path)
        logger.info("Sackmann fetched: %s -> %s (%d bytes)", url, cache_path, len(resp.text))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sackmann fetch failed %s: %s", url, exc)
        return False


def refresh_atp_data(cache: SackmannCache, current_year: int) -> dict[str, Path]:
    """Refresh ATP player + recent year matches CSVs. Returns paths."""
    paths: dict[str, Path] = {}
    files = [
        ("atp_players.csv", f"{_SACKMANN_BASE_ATP}/atp_players.csv"),
        (f"atp_matches_{current_year}.csv", f"{_SACKMANN_BASE_ATP}/atp_matches_{current_year}.csv"),
        (f"atp_matches_{current_year - 1}.csv", f"{_SACKMANN_BASE_ATP}/atp_matches_{current_year - 1}.csv"),
    ]
    for filename, url in files:
        cache_path = cache.cache_dir / filename
        if cache.needs_refresh(filename):
            success = fetch_csv_to_cache(url, cache_path)
            if not success and not cache_path.exists():
                continue
        paths[filename] = cache_path
    return paths


def refresh_wta_data(cache: SackmannCache, current_year: int) -> dict[str, Path]:
    """Refresh WTA player + recent year matches CSVs."""
    paths: dict[str, Path] = {}
    files = [
        ("wta_players.csv", f"{_SACKMANN_BASE_WTA}/wta_players.csv"),
        (f"wta_matches_{current_year}.csv", f"{_SACKMANN_BASE_WTA}/wta_matches_{current_year}.csv"),
        (f"wta_matches_{current_year - 1}.csv", f"{_SACKMANN_BASE_WTA}/wta_matches_{current_year - 1}.csv"),
    ]
    for filename, url in files:
        cache_path = cache.cache_dir / filename
        if cache.needs_refresh(filename):
            success = fetch_csv_to_cache(url, cache_path)
            if not success and not cache_path.exists():
                continue
        paths[filename] = cache_path
    return paths
