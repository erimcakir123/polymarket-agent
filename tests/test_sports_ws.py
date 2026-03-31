"""Tests for Polymarket Sports WebSocket client."""
import json
from src.sports_ws import SportsWebSocket


def test_handle_message_stores_state():
    """Verify incoming WS message is stored and queryable."""
    ws = SportsWebSocket()
    msg = json.dumps({
        "gameId": 123,
        "slug": "nba-cha-bkn",
        "status": "InProgress",
        "score": "98-102",
        "period": "4Q",
        "live": True,
        "ended": False,
        "elapsed": "42:18",
    })
    ws._handle_message(msg)

    state = ws.get_match_state("nba-cha-bkn")
    assert state is not None
    assert state["live"] is True
    assert state["ended"] is False
    assert state["score"] == "98-102"
    assert state["elapsed"] == "42:18"


def test_handle_message_ended():
    """Verify is_ended returns True after match ends."""
    ws = SportsWebSocket()
    msg = json.dumps({
        "slug": "nba-cha-bkn",
        "live": False,
        "ended": True,
        "finished_timestamp": "2026-03-31T00:00:00Z",
    })
    ws._handle_message(msg)
    assert ws.is_ended("nba-cha-bkn") is True
    assert ws.is_live("nba-cha-bkn") is False


def test_get_match_state_unknown_slug():
    """Unknown slug returns None."""
    ws = SportsWebSocket()
    assert ws.get_match_state("unknown-slug") is None
    assert ws.is_ended("unknown-slug") is False
    assert ws.is_live("unknown-slug") is False


def test_slug_prefix_matching():
    """Market slug with date suffix should match WS slug without it."""
    ws = SportsWebSocket()
    msg = json.dumps({"slug": "nba-cha-bkn", "live": True, "ended": False})
    ws._handle_message(msg)

    # Market slug has date suffix
    state = ws.get_match_state("nba-cha-bkn-2026-03-30")
    assert state is not None
    assert state["live"] is True
