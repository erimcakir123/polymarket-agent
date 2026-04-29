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
