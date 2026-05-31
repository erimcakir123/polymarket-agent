"""nba_api birincil refresher testleri — mocked HTTP, gerçek paket çağrısı yok."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from src.infrastructure.data.basketball.nba_api_refresher import (
    fetch_game_log_via_nba_api,
    _convert_nba_api_row_to_game_record,
)
from src.infrastructure.data.basketball.schemas import GameRecord


@pytest.fixture
def fake_nba_api_row():
    """nba_api leaguegamelog endpoint satır biçimi (DataFrame.to_dict gibi)."""
    return {
        "SEASON_ID": "22024",
        "GAME_ID": "0022400001",
        "GAME_DATE": "2024-10-22",
        "MATCHUP": "LAL vs. GSW",
        "TEAM_ABBREVIATION": "LAL",
        "PTS": 110, "FGA": 90, "FTA": 22, "OREB": 12, "TOV": 14,
        "WL": "W", "MIN": 240,
    }


@pytest.fixture
def fake_opp_row(fake_nba_api_row):
    row = dict(fake_nba_api_row)
    row["TEAM_ABBREVIATION"] = "GSW"
    row["MATCHUP"] = "GSW @ LAL"
    row["PTS"] = 104
    row["FGA"] = 88; row["FTA"] = 20; row["OREB"] = 10; row["TOV"] = 16
    row["WL"] = "L"
    return row


def test_convert_row_produces_valid_game_record(fake_nba_api_row, fake_opp_row):
    rec = _convert_nba_api_row_to_game_record(
        home_row=fake_nba_api_row, away_row=fake_opp_row, league="nba",
    )
    assert isinstance(rec, GameRecord)
    assert rec.home_team == "LAL" and rec.away_team == "GSW"
    assert rec.home_score == 110 and rec.away_score == 104
    assert rec.is_final is True
    # Possessions: FGA + 0.44*FTA - OREB + TOV = 90 + 9.68 - 12 + 14 = 101.68
    assert abs(rec.home_possessions - 101.68) < 0.01


def test_fetch_with_empty_endpoint_returns_empty_list():
    fake_endpoint = MagicMock()
    fake_endpoint.return_value.get_dict.return_value = {"resultSets": [{"rowSet": [], "headers": []}]}
    games = fetch_game_log_via_nba_api(
        league="nba", season="2024-25", endpoint_factory=fake_endpoint,
    )
    assert games == []


def test_fetch_unknown_league_raises_value_error():
    with pytest.raises(ValueError, match="league"):
        fetch_game_log_via_nba_api(
            league="cricket", season="2024-25", endpoint_factory=MagicMock(),
        )
