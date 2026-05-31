"""Schema validation testleri — pozitif yol + drift yakalama."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.infrastructure.data.basketball.schemas import (
    GameRecord,
    RefresherResult,
    SourceStatus,
    TeamSnapshot,
)


def test_game_record_validates_complete_payload():
    rec = GameRecord(
        game_id="0022400001",
        season="2024-25",
        game_date_utc="2024-10-22T23:30:00Z",
        home_team="LAL",
        away_team="GSW",
        home_score=110,
        away_score=104,
        home_possessions=98.5,
        away_possessions=98.5,
        is_final=True,
        league="nba",
    )
    assert rec.is_final is True
    assert rec.home_score > rec.away_score


def test_game_record_rejects_negative_score():
    with pytest.raises(ValidationError):
        GameRecord(
            game_id="0022400001",
            season="2024-25",
            game_date_utc="2024-10-22T23:30:00Z",
            home_team="LAL", away_team="GSW",
            home_score=-1, away_score=104,
            home_possessions=98.5, away_possessions=98.5,
            is_final=True, league="nba",
        )


def test_game_record_rejects_unknown_league():
    with pytest.raises(ValidationError):
        GameRecord(
            game_id="X", season="2024-25",
            game_date_utc="2024-10-22T23:30:00Z",
            home_team="LAL", away_team="GSW",
            home_score=100, away_score=99,
            home_possessions=95.0, away_possessions=95.0,
            is_final=True, league="cricket",
        )


def test_team_snapshot_round_trip():
    snap = TeamSnapshot(
        team="LAL", league="nba",
        elo_rating=1520.4, elo_games=82,
        adj_o=118.2, adj_d=112.8, adj_pace=99.4,
        last_updated_utc="2024-11-01T00:00:00Z",
    )
    payload = snap.model_dump()
    restored = TeamSnapshot.model_validate(payload)
    assert restored == snap


def test_refresher_result_counts_match():
    res = RefresherResult(
        source="nba_api", league="nba",
        games_fetched=12, games_persisted=12,
        ok=True, error=None,
    )
    assert res.ok is True


def test_source_status_tracks_failures():
    st = SourceStatus(
        source="nba_api",
        last_success_utc="2024-11-01T01:00:00Z",
        last_fail_utc=None,
        consecutive_fails=0,
        active=True,
    )
    assert st.active is True
