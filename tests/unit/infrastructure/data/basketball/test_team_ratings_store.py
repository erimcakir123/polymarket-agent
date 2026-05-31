"""Team ratings store — atomic write, read, merge."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from src.infrastructure.data.basketball.team_ratings_store import (
    load_team_snapshots, save_team_snapshots, upsert_snapshot,
)
from src.infrastructure.data.basketball.schemas import TeamSnapshot


@pytest.fixture
def sample_snap():
    return TeamSnapshot(
        team="LAL", league="nba",
        elo_rating=1520.4, elo_games=82,
        adj_o=118.2, adj_d=112.8, adj_pace=99.4,
        last_updated_utc="2024-11-01T00:00:00Z",
    )


def test_save_and_load_round_trip(tmp_path: Path, sample_snap):
    target = tmp_path / "nba_ratings.json"
    save_team_snapshots(target, [sample_snap])
    loaded = load_team_snapshots(target, league="nba")
    assert len(loaded) == 1
    assert loaded["LAL"].elo_rating == 1520.4


def test_load_missing_file_returns_empty(tmp_path: Path):
    target = tmp_path / "missing.json"
    out = load_team_snapshots(target, league="nba")
    assert out == {}


def test_save_uses_atomic_write_no_partial_file(tmp_path: Path, sample_snap):
    target = tmp_path / "nba_ratings.json"
    save_team_snapshots(target, [sample_snap])
    assert target.exists()
    assert not (target.parent / (target.name + ".tmp")).exists()


def test_upsert_replaces_existing_team(tmp_path: Path, sample_snap):
    target = tmp_path / "nba_ratings.json"
    save_team_snapshots(target, [sample_snap])
    updated = sample_snap.model_copy(update={"elo_rating": 1550.0, "elo_games": 83})
    upsert_snapshot(target, updated, league="nba")
    loaded = load_team_snapshots(target, league="nba")
    assert loaded["LAL"].elo_rating == 1550.0
    assert loaded["LAL"].elo_games == 83


def test_load_filters_by_league(tmp_path: Path, sample_snap):
    target = tmp_path / "mixed_ratings.json"
    wnba_snap = sample_snap.model_copy(update={"team": "LVA", "league": "wnba"})
    save_team_snapshots(target, [sample_snap, wnba_snap])
    nba_only = load_team_snapshots(target, league="nba")
    assert "LAL" in nba_only and "LVA" not in nba_only
