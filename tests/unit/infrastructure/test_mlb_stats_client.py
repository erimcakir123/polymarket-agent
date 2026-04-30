from unittest.mock import patch
import pytest

from src.infrastructure.apis.mlb_stats_client import (
    MLBStatsClient,
    ProbablePitcher,
    TeamSeasonStats,
)


@pytest.fixture
def client():
    return MLBStatsClient()


def test_get_probable_pitcher_returns_dataclass(client):
    fake_response = {
        "gameData": {
            "probablePitchers": {
                "home": {"id": 12345, "fullName": "John Smith"},
                "away": {"id": 67890, "fullName": "Jane Doe"},
            },
        },
    }
    with patch("statsapi.get", return_value=fake_response):
        result = client.get_probable_pitchers(game_pk=778899)
    assert result.home is not None
    assert result.home.player_id == 12345
    assert result.home.name == "John Smith"
    assert result.away.player_id == 67890


def test_get_probable_pitcher_unconfirmed_returns_none(client):
    fake_response = {"gameData": {"probablePitchers": {}}}
    with patch("statsapi.get", return_value=fake_response):
        result = client.get_probable_pitchers(game_pk=778899)
    assert result.home is None
    assert result.away is None


def test_api_failure_returns_none(client):
    with patch("statsapi.get", side_effect=Exception("network error")):
        result = client.get_probable_pitchers(game_pk=778899)
    assert result.home is None
    assert result.away is None


def test_get_team_season_stats(client):
    fake_response = {
        "stats": [{"splits": [{"stat": {
            "wins": 90, "losses": 72,
            "runsPerGame": "4.7", "earnedRunAverage": "3.85",
        }}]}],
    }
    with patch("statsapi.get", return_value=fake_response):
        stats = client.get_team_season_stats(team_id=147, season=2026)
    assert stats is not None
    assert stats.wins == 90
    assert stats.losses == 72
    assert stats.runs_per_game == pytest.approx(4.7, abs=0.01)


def test_get_team_season_stats_failure_returns_none(client):
    with patch("statsapi.get", side_effect=Exception("api down")):
        stats = client.get_team_season_stats(team_id=147, season=2026)
    assert stats is None
