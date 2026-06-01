"""basketball_ratings_builder — build + persist testleri."""
from __future__ import annotations

import json
from pathlib import Path

from src.infrastructure.data.basketball.schemas import GameRecord
from src.orchestration.basketball_ratings_builder import (
    build_and_persist_snapshots,
    build_ratings_from_games,
)


def _game(home, away, hs, as_, date="2024-11-01T00:00:00Z"):
    return GameRecord(
        game_id=f"{home}-{away}-{date}", season="2024-25",
        game_date_utc=date,
        home_team=home, away_team=away,
        home_score=hs, away_score=as_,
        home_possessions=100.0, away_possessions=100.0,
        is_final=True, league="nba",
    )


def test_build_ratings_winner_gains():
    games = [_game("LAL", "GSW", 110, 100)]
    elo, counts = build_ratings_from_games(
        games, league="nba", k_factor=20.0, home_advantage=100.0,
    )
    assert elo["LAL"].rating > 1500.0
    assert elo["GSW"].rating < 1500.0
    assert counts["LAL"] == 1
    assert counts["GSW"] == 1


def test_build_ratings_ignores_other_league():
    games = [_game("LAL", "GSW", 110, 100)]
    elo, _ = build_ratings_from_games(
        games, league="wnba", k_factor=20.0, home_advantage=95.0,
    )
    assert elo == {}


def test_build_ratings_applies_season_reset():
    games = [
        _game("LAL", "GSW", 130, 100, "2024-10-01T00:00:00Z"),
        _game("LAL", "GSW", 130, 100, "2024-10-02T00:00:00Z"),
        _game("LAL", "GSW", 130, 100, "2024-10-03T00:00:00Z"),
        _game("LAL", "GSW", 130, 100, "2024-10-04T00:00:00Z"),
        _game("LAL", "GSW", 130, 100, "2024-10-05T00:00:00Z"),
    ]
    elo_no_reset, _ = build_ratings_from_games(
        games, league="nba", k_factor=20.0, home_advantage=100.0,
        apply_season_reset=False,
    )
    elo_reset, _ = build_ratings_from_games(
        games, league="nba", k_factor=20.0, home_advantage=100.0,
        apply_season_reset=True,
    )
    # Reset uygulanmışsa LAL rating 1500'e yaklaşmış olmalı
    assert abs(elo_reset["LAL"].rating - 1500.0) < abs(elo_no_reset["LAL"].rating - 1500.0)


def test_persist_writes_json_with_team_snapshots(tmp_path: Path):
    games = [_game("LAL", "GSW", 110, 100), _game("LAL", "PHX", 115, 95)]
    out = tmp_path / "nba.json"
    written = build_and_persist_snapshots(
        games, league="nba", k_factor=20.0, home_advantage=100.0,
        output_path=out,
    )
    assert written > 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    teams = {row["team"] for row in payload}
    assert "LAL" in teams


def test_persist_empty_games_returns_zero(tmp_path: Path):
    out = tmp_path / "nba.json"
    written = build_and_persist_snapshots(
        [], league="nba", k_factor=20.0, home_advantage=100.0,
        output_path=out,
    )
    assert written == 0
    assert not out.exists()
