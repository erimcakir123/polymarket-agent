"""Basic tests for TheSportsDBClient."""
from unittest.mock import patch, MagicMock
from src.thesportsdb import TheSportsDBClient


def _client():
    return TheSportsDBClient()


def test_extract_teams_vs_pattern():
    c = _client()
    a, b = c._extract_teams("Uruguay vs Brazil: Who will win?")
    assert a == "Uruguay"
    assert b == "Brazil"


def test_extract_teams_will_beat_pattern():
    c = _client()
    a, b = c._extract_teams("Will Argentina beat Colombia?")
    assert a == "Argentina"
    assert b == "Colombia"


def test_extract_teams_fails_gracefully():
    c = _client()
    a, b = c._extract_teams("Who will win the election?")
    assert a == "" or b == ""  # At least one fails for non-team question


def test_get_match_context_returns_none_on_api_failure():
    c = _client()
    with patch.object(c, "_get", return_value=None):
        result = c.get_match_context("Uruguay vs Brazil: Who will win?")
    assert result is None


def test_get_match_context_returns_string_with_data():
    c = _client()
    # Mock team search
    c._team_cache["uruguay"] = ("134715", 9e9)
    c._team_cache["brazil"] = ("134716", 9e9)
    # Mock events
    c._events_cache["134715"] = ([
        {"opponent": "Bolivia", "won": True, "score": "2-1", "home_away": "H", "date": "2026-03-20", "league": "FIFA WC Qualifying"},
        {"opponent": "Colombia", "won": False, "score": "0-1", "home_away": "A", "date": "2026-03-15", "league": "FIFA WC Qualifying"},
    ], 9e9)
    c._events_cache["134716"] = ([
        {"opponent": "Argentina", "won": True, "score": "1-0", "home_away": "H", "date": "2026-03-20", "league": "FIFA WC Qualifying"},
    ], 9e9)

    result = c.get_match_context("Uruguay vs Brazil: Who will win?")
    assert result is not None
    assert "Uruguay" in result
    assert "Brazil" in result
    assert "TheSportsDB" in result
    assert "1W-1L" in result  # Uruguay's record
