"""ESPN scoreboard JSON yedek refresher testleri — mocked HTTP."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from src.infrastructure.data.basketball.espn_pbp_refresher import (
    fetch_game_log_via_espn,
    _convert_espn_event_to_game_record,
)
from src.infrastructure.data.basketball.schemas import GameRecord


@pytest.fixture
def fake_espn_event():
    """ESPN scoreboard `events[]` öğesi (basitleştirilmiş)."""
    return {
        "id": "401705270",
        "season": {"year": 2025, "type": 2},
        "date": "2024-10-22T23:30Z",
        "status": {"type": {"completed": True}},
        "competitions": [{
            "competitors": [
                {"homeAway": "home", "team": {"abbreviation": "LAL"},
                 "score": "110", "statistics": [
                    {"name": "fieldGoalsAttempted", "displayValue": "90"},
                    {"name": "freeThrowsAttempted", "displayValue": "22"},
                    {"name": "offensiveRebounds", "displayValue": "12"},
                    {"name": "turnovers", "displayValue": "14"},
                 ]},
                {"homeAway": "away", "team": {"abbreviation": "GSW"},
                 "score": "104", "statistics": [
                    {"name": "fieldGoalsAttempted", "displayValue": "88"},
                    {"name": "freeThrowsAttempted", "displayValue": "20"},
                    {"name": "offensiveRebounds", "displayValue": "10"},
                    {"name": "turnovers", "displayValue": "16"},
                 ]},
            ],
        }],
    }


def test_convert_event_produces_valid_record(fake_espn_event):
    rec = _convert_espn_event_to_game_record(fake_espn_event, league="nba")
    assert rec.home_team == "LAL"
    assert rec.away_team == "GSW"
    assert rec.home_score == 110
    assert rec.away_score == 104


def test_fetch_skips_unfinished_games(fake_espn_event):
    unfinished = dict(fake_espn_event)
    unfinished["status"] = {"type": {"completed": False}}
    http_get = MagicMock()
    http_get.return_value.json.return_value = {"events": [unfinished]}
    http_get.return_value.status_code = 200
    games = fetch_game_log_via_espn(league="nba", date_utc="2024-10-22", http_get=http_get)
    assert games == []


def test_fetch_unknown_league_raises():
    with pytest.raises(ValueError):
        fetch_game_log_via_espn(league="cricket", date_utc="2024-10-22", http_get=MagicMock())


def test_convert_ncaab_event_uses_college_possessions_factor(fake_espn_event):
    """NCAAB possessions factor 0.475 (college standard) — 0.44 NBA'dan farklı."""
    fake_espn_event["competitions"][0]["competitors"][0]["team"]["abbreviation"] = "DUK"
    fake_espn_event["competitions"][0]["competitors"][1]["team"]["abbreviation"] = "UNC"
    rec = _convert_espn_event_to_game_record(fake_espn_event, league="ncaab")
    # NCAAB: 90 + 0.475 × 22 - 12 + 14 = 102.45
    assert abs(rec.home_possessions - 102.45) < 0.01


def test_convert_wncaab_event_uses_college_factor(fake_espn_event):
    fake_espn_event["competitions"][0]["competitors"][0]["team"]["abbreviation"] = "SC"
    fake_espn_event["competitions"][0]["competitors"][1]["team"]["abbreviation"] = "IOW"
    rec = _convert_espn_event_to_game_record(fake_espn_event, league="wncaab")
    assert abs(rec.home_possessions - 102.45) < 0.01


def test_fetch_ncaab_url_uses_mens_college_basketball_path():
    """ESPN endpoint path NCAAB için 'mens-college-basketball'."""
    http_get = MagicMock()
    http_get.return_value.json.return_value = {"events": []}
    http_get.return_value.status_code = 200
    fetch_game_log_via_espn(league="ncaab", date_utc="2024-12-01", http_get=http_get)
    called_url = http_get.call_args[0][0]
    assert "mens-college-basketball" in called_url
    assert "20241201" in called_url
