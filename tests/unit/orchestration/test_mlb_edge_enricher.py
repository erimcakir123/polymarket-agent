# tests/unit/orchestration/test_mlb_edge_enricher.py
from unittest.mock import MagicMock
from datetime import datetime, timezone

import pytest

from src.orchestration.mlb_edge_enricher import (
    MLBEdgeEnricher,
    MLBEnrichedData,
)
from src.infrastructure.apis.mlb_stats_client import (
    ProbablePitchers, ProbablePitcher, TeamSeasonStats,
)
from src.infrastructure.apis.openweather_client import WeatherSnapshot


@pytest.fixture
def stats_client():
    m = MagicMock()
    m.get_probable_pitchers.return_value = ProbablePitchers(
        home=ProbablePitcher(player_id=11, name="Pitcher A"),
        away=ProbablePitcher(player_id=22, name="Pitcher B"),
    )
    m.get_team_season_stats.return_value = TeamSeasonStats(
        wins=85, losses=70, runs_per_game=4.5,
        runs_allowed_per_game=4.0, earned_run_average=3.85,
    )
    m.get_pitcher_era.return_value = 3.50
    return m


@pytest.fixture
def weather_client():
    m = MagicMock()
    m.get_forecast.return_value = WeatherSnapshot(
        rain_chance=0.10, wind_speed_mph=8.0, wind_direction_deg=180,
        temperature_f=72.0, rain_volume_mm=0.0,
    )
    return m


def test_enrich_happy_path(stats_client, weather_client):
    e = MLBEdgeEnricher(stats_client=stats_client, weather_client=weather_client)
    data = e.enrich(
        game_pk=778899, home_abbr="ATL", away_abbr="DET",
        game_time=datetime.now(timezone.utc), season=2026,
    )
    assert data is not None
    assert data.pitcher_confirmed_home is True
    assert data.pitcher_confirmed_away is True
    assert data.home_pitcher_era == pytest.approx(3.50, abs=0.01)
    assert data.rain_chance == pytest.approx(0.10, abs=0.01)


def test_enrich_pitcher_unconfirmed_returns_none(stats_client, weather_client):
    """If either pitcher missing → None (gate will SKIP)."""
    stats_client.get_probable_pitchers.return_value = ProbablePitchers(home=None, away=None)
    e = MLBEdgeEnricher(stats_client=stats_client, weather_client=weather_client)
    data = e.enrich(
        game_pk=778899, home_abbr="ATL", away_abbr="DET",
        game_time=datetime.now(timezone.utc), season=2026,
    )
    assert data is None


def test_enrich_weather_failure_still_returns_data(stats_client, weather_client):
    """Weather is optional — pitchers are mandatory."""
    weather_client.get_forecast.return_value = None
    e = MLBEdgeEnricher(stats_client=stats_client, weather_client=weather_client)
    data = e.enrich(
        game_pk=778899, home_abbr="ATL", away_abbr="DET",
        game_time=datetime.now(timezone.utc), season=2026,
    )
    assert data is not None
    assert data.rain_chance == 0.0  # default neutral when weather unavailable


def test_enrich_missing_team_stats_returns_none(stats_client, weather_client):
    stats_client.get_team_season_stats.return_value = None
    e = MLBEdgeEnricher(stats_client=stats_client, weather_client=weather_client)
    data = e.enrich(
        game_pk=778899, home_abbr="ATL", away_abbr="DET",
        game_time=datetime.now(timezone.utc), season=2026,
    )
    assert data is None
