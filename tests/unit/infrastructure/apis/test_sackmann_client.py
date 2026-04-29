"""Sackmann CSV client tests using fixtures."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.infrastructure.apis.sackmann_client import (
    PlayerServeStats,
    SackmannCache,
    aggregate_player_stats,
    parse_matches_csv,
    parse_players_csv,
)


_FIXTURE_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "sackmann"


def test_parse_players_csv_returns_records() -> None:
    csv_path = _FIXTURE_DIR / "atp_players_sample.csv"
    records = parse_players_csv(csv_path)
    assert len(records) == 10
    medvedev = next(r for r in records if r.last == "Medvedev")
    assert medvedev.first == "Daniil"
    assert medvedev.country == "RUS"


def test_parse_matches_csv_returns_rows() -> None:
    csv_path = _FIXTURE_DIR / "atp_matches_2025_sample.csv"
    matches = parse_matches_csv(csv_path)
    assert len(matches) == 10
    aus_open_final = next(m for m in matches if m["tourney_name"] == "Australian Open" and m["round"] == "F")
    assert aus_open_final["winner_name"] == "Jannik Sinner"
    assert aus_open_final["surface"] == "Hard"


def test_aggregate_player_stats_sinner_overall() -> None:
    matches = parse_matches_csv(_FIXTURE_DIR / "atp_matches_2025_sample.csv")
    stats = aggregate_player_stats("Jannik Sinner", matches, surface=None)
    assert stats is not None
    # Sinner won 2 matches in fixture (Aus Open F, Madrid QF, Wimbledon F)
    assert stats.matches_played >= 3
    # Service points won % should be reasonable (60-80%)
    assert 0.55 < stats.service_points_won_pct < 0.85


def test_aggregate_player_stats_clay_only() -> None:
    matches = parse_matches_csv(_FIXTURE_DIR / "atp_matches_2025_sample.csv")
    stats = aggregate_player_stats("Carlos Alcaraz Garfia", matches, surface="clay")
    assert stats is not None
    # Clay matches only: Madrid QF win, French Open F win
    assert stats.matches_played == 2
    assert stats.surface == "clay"


def test_aggregate_player_stats_unknown_returns_none() -> None:
    matches = parse_matches_csv(_FIXTURE_DIR / "atp_matches_2025_sample.csv")
    stats = aggregate_player_stats("Unknown Player", matches, surface=None)
    assert stats is None


def test_refresh_atp_data_falls_back_through_year_window(tmp_path, monkeypatch):
    """When current and recent years 404, refresh tries older years until one succeeds."""
    from src.infrastructure.apis.sackmann_client import SackmannCache, refresh_atp_data

    cache = SackmannCache(cache_dir=tmp_path, refresh_days=7)

    # Stub fetch: succeeds only for atp_players.csv and atp_matches_2024.csv
    def fake_fetch(url, cache_path, timeout=30):
        # Players file: succeed (write empty CSV)
        if "atp_players.csv" in url:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text("player_id,name_first,name_last,hand,dob,country\n")
            return True
        # Matches: only 2024 succeeds (simulate Sackmann publish lag)
        if "atp_matches_2024.csv" in url:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text("tourney_id,winner_name\n")
            return True
        return False

    monkeypatch.setattr(
        "src.infrastructure.apis.sackmann_client.fetch_csv_to_cache",
        fake_fetch,
    )

    # Pretend it's 2026 — current_year=2026, prev=2025 both 404, must fall back
    paths = refresh_atp_data(cache, current_year=2026)

    # Players file should be present
    assert "atp_players.csv" in paths
    # At least one matches file present (the 2024 one that succeeded)
    matches_keys = [k for k in paths.keys() if "matches" in k]
    assert len(matches_keys) >= 1
    assert any("2024" in k for k in matches_keys)


def test_refresh_atp_data_window_size_four_years(tmp_path, monkeypatch):
    """Year fallback tries up to 4 years (current + 3 previous)."""
    from src.infrastructure.apis.sackmann_client import SackmannCache, refresh_atp_data

    attempted_urls: list[str] = []

    def track_fetch(url, cache_path, timeout=30):
        attempted_urls.append(url)
        # Players succeeds, all match years fail
        if "atp_players.csv" in url:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text("\n")
            return True
        return False

    monkeypatch.setattr(
        "src.infrastructure.apis.sackmann_client.fetch_csv_to_cache",
        track_fetch,
    )

    cache = SackmannCache(cache_dir=tmp_path, refresh_days=7)
    refresh_atp_data(cache, current_year=2026)

    # Should have attempted matches files for 2026, 2025, 2024, 2023
    matches_attempts = [u for u in attempted_urls if "matches" in u]
    years_tried = sorted({int(u.split("matches_")[1].split(".csv")[0]) for u in matches_attempts}, reverse=True)
    assert years_tried == [2026, 2025, 2024, 2023], f"Expected last 4 years, got {years_tried}"
