"""Tests for ESPN data enrichment methods in SportsDataClient."""
from unittest.mock import patch, MagicMock
from src.sports_data import SportsDataClient


def _make_client() -> SportsDataClient:
    """Create SportsDataClient with rate limit disabled."""
    client = SportsDataClient()
    client._last_call = 0.0
    return client


class TestGetTeamInjuries:
    def test_returns_injury_list(self):
        client = _make_client()
        mock_response = {
            "injuries": [
                {
                    "athlete": {
                        "displayName": "Stephen Curry",
                        "position": {"abbreviation": "SG"},
                    },
                    "status": "Doubtful",
                    "type": {"description": "Knee"},
                    "detail": "Left knee soreness",
                }
            ]
        }
        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_team_injuries("basketball", "nba", "10")
        assert len(result) == 1
        assert result[0]["player"] == "Stephen Curry"
        assert result[0]["status"] == "Doubtful"
        assert result[0]["detail"] == "Left knee soreness"
        assert result[0]["position"] == "SG"

    def test_skips_unsupported_sports(self):
        client = _make_client()
        result = client.get_team_injuries("tennis", "atp", "123")
        assert result == []
        result = client.get_team_injuries("mma", "ufc", "456")
        assert result == []

    def test_returns_empty_on_api_error(self):
        client = _make_client()
        with patch.object(client, "_get", return_value=None):
            result = client.get_team_injuries("basketball", "nba", "10")
        assert result == []

    def test_returns_empty_on_no_injuries(self):
        client = _make_client()
        with patch.object(client, "_get", return_value={"injuries": []}):
            result = client.get_team_injuries("basketball", "nba", "10")
        assert result == []


class TestGetStandingsContext:
    def test_returns_standings_dict(self):
        client = _make_client()
        mock_response = {
            "children": [{
                "standings": {
                    "entries": [{
                        "team": {"id": "13", "displayName": "Los Angeles Lakers",
                                 "abbreviation": "LAL"},
                        "stats": [
                            {"abbreviation": "W", "value": 38},
                            {"abbreviation": "L", "value": 29},
                            {"abbreviation": "PCT", "value": 0.567},
                            {"abbreviation": "STRK", "displayValue": "W3"},
                            {"abbreviation": "L10", "displayValue": "7-3"},
                            {"abbreviation": "GB", "value": 5.0},
                            {"abbreviation": "HOME", "displayValue": "22-10"},
                            {"abbreviation": "AWAY", "displayValue": "16-19"},
                        ],
                    }]
                }
            }]
        }
        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_standings_context("basketball", "nba", "13")
        assert result is not None
        assert result["wins"] == 38
        assert result["losses"] == 29
        assert result["home_record"] == "22-10"
        assert result["away_record"] == "16-19"
        assert result["streak"] == "W3"

    def test_returns_none_on_api_error(self):
        client = _make_client()
        with patch.object(client, "_get", return_value=None):
            result = client.get_standings_context("basketball", "nba", "13")
        assert result is None

    def test_returns_none_when_team_not_found(self):
        client = _make_client()
        mock_response = {"children": [{"standings": {"entries": [{
            "team": {"id": "999", "displayName": "Other", "abbreviation": "OTH"},
            "stats": [],
        }]}}]}
        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_standings_context("basketball", "nba", "13")
        assert result is None

    def test_uses_correct_url_path(self):
        """Must use /apis/v2/ not /apis/site/v2/."""
        client = _make_client()
        with patch.object(client, "_get", return_value=None) as mock_get:
            client.get_standings_context("basketball", "nba", "13")
            call_url = mock_get.call_args[0][0]
            assert "/apis/v2/sports/" in call_url
            assert "/standings" in call_url


class TestGetEspnPredictor:
    def test_returns_probabilities_from_core_api(self):
        client = _make_client()
        mock_response = {
            "items": [{
                "homeWinPercentage": 0.634,
                "awayWinPercentage": 0.366,
                "tiePercentage": 0.0,
            }]
        }
        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_espn_predictor("basketball", "nba", "401584701", "401584701")
        assert result is not None
        assert result["home_win_pct"] == 0.634
        assert result["away_win_pct"] == 0.366
        assert result["source"] == "espn_bpi"

    def test_falls_back_to_summary_predictor(self):
        client = _make_client()
        summary_response = {
            "predictor": {
                "header": "ESPN BPI Win Probability",
                "homeTeam": {"gameProjection": "63.4", "teamChanceLoss": "36.6"},
            }
        }
        with patch.object(client, "_get", side_effect=[None, summary_response]):
            result = client.get_espn_predictor("basketball", "nba", "401584701", "401584701")
        assert result is not None
        assert abs(result["home_win_pct"] - 0.634) < 0.01
        assert result["source"] == "espn_bpi"

    def test_returns_none_when_both_fail(self):
        client = _make_client()
        with patch.object(client, "_get", return_value=None):
            result = client.get_espn_predictor("basketball", "nba", "401584701", "401584701")
        assert result is None

    def test_returns_none_for_empty_items(self):
        client = _make_client()
        with patch.object(client, "_get", side_effect=[{"items": []}, None]):
            result = client.get_espn_predictor("basketball", "nba", "401584701", "401584701")
        assert result is None


from datetime import datetime, timezone, timedelta


class TestDetectBackToBack:
    def test_detects_b2b(self):
        client = _make_client()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        games = [
            {"date": "2026-03-15", "opponent": "Team X", "won": True, "score": "110-100", "home_away": "H"},
            {"date": yesterday, "opponent": "Team Y", "won": False, "score": "95-100", "home_away": "A"},
        ]
        assert client.detect_back_to_back(games) is True

    def test_no_b2b_when_last_game_two_days_ago(self):
        client = _make_client()
        two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
        games = [{"date": two_days_ago, "opponent": "Team X", "won": True, "score": "110-100", "home_away": "H"}]
        assert client.detect_back_to_back(games) is False

    def test_empty_games_returns_false(self):
        client = _make_client()
        assert client.detect_back_to_back([]) is False

    def test_no_date_field_returns_false(self):
        client = _make_client()
        assert client.detect_back_to_back([{"opponent": "X"}]) is False


class TestGetHeadToHead:
    def test_finds_h2h_from_schedule(self):
        client = _make_client()
        team_a_data = {
            "team_name": "Lakers", "record": "38-29", "standing": "",
            "recent_games": [
                {"date": "2026-01-15", "opponent": "Boston Celtics", "won": True, "score": "110-100", "home_away": "H"},
                {"date": "2026-02-20", "opponent": "Boston Celtics", "won": False, "score": "95-105", "home_away": "A"},
                {"date": "2026-03-01", "opponent": "Miami Heat", "won": True, "score": "115-100", "home_away": "H"},
            ],
        }
        with patch.object(client, "get_team_record", return_value=team_a_data):
            result = client.get_head_to_head("basketball", "nba", "Lakers", "Celtics")
        assert len(result) == 2
        assert result[0]["opponent"] == "Boston Celtics"
        assert result[0]["won"] is True
        assert result[1]["won"] is False

    def test_returns_empty_when_no_matchups(self):
        client = _make_client()
        team_a_data = {
            "team_name": "Lakers", "record": "38-29", "standing": "",
            "recent_games": [{"date": "2026-03-01", "opponent": "Miami Heat", "won": True, "score": "115-100", "home_away": "H"}],
        }
        with patch.object(client, "get_team_record", return_value=team_a_data):
            result = client.get_head_to_head("basketball", "nba", "Lakers", "Celtics")
        assert result == []

    def test_returns_empty_when_team_not_found(self):
        client = _make_client()
        with patch.object(client, "get_team_record", return_value=None):
            result = client.get_head_to_head("basketball", "nba", "Lakers", "Celtics")
        assert result == []
