# tests/test_scout_prescan.py
"""Tests for ScoutScheduler daily listing, window queries, batch matching, and pagination."""
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, call

import pytest


def _make_scout():
    """Create a ScoutScheduler with mocked dependencies."""
    from src.scout_scheduler import ScoutScheduler
    sports = MagicMock()
    esports = MagicMock()
    esports.available = False
    with patch("src.scout_scheduler.SCOUT_QUEUE_FILE") as qf:
        qf.exists.return_value = False
        s = ScoutScheduler(sports, esports)
    return s


# --- is_daily_listing_time ---

def test_is_daily_listing_time_hour_0():
    """Returns True when UTC hour is 0."""
    scout = _make_scout()
    with patch("src.scout_scheduler.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.hour = 0
        mock_dt.now.return_value = mock_now
        mock_dt.fromisoformat = datetime.fromisoformat
        assert scout.is_daily_listing_time() is True


def test_is_daily_listing_time_hour_6():
    """Returns False when UTC hour is 6."""
    scout = _make_scout()
    with patch("src.scout_scheduler.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.hour = 6
        mock_dt.now.return_value = mock_now
        mock_dt.fromisoformat = datetime.fromisoformat
        assert scout.is_daily_listing_time() is False


# --- run_daily_listing ---

def test_run_daily_listing_no_enrichment():
    """run_daily_listing must NOT call sports.get_match_context; sports_context must be empty."""
    scout = _make_scout()
    scout._last_daily_ts = 0  # No cooldown

    now = datetime.now(timezone.utc)
    fake_match = {
        "scout_key": "basketball_nba_TeamA_TeamB_20260330",
        "team_a": "TeamA",
        "team_b": "TeamB",
        "question": "TeamA vs TeamB: Who will win?",
        "match_time": (now + timedelta(hours=2)).isoformat(),
        "sport": "basketball",
        "league": "nba",
        "league_name": "NBA",
        "is_esports": False,
        "slug_hint": "bas-team-team",
        "tags": ["sports", "nba"],
    }

    with patch.object(scout, "_fetch_espn_upcoming", return_value=[fake_match]):
        with patch.object(scout, "_fetch_esports_upcoming", return_value=[]):
            with patch.object(scout, "_save_queue"):
                with patch("src.scout_scheduler.SCOUT_MARKER_FILE") as mf:
                    mf.parent = MagicMock()
                    result = scout.run_daily_listing()

    assert result == 1
    entry = scout._queue["basketball_nba_TeamA_TeamB_20260330"]
    assert entry["sports_context"] == ""
    # Enrichment methods must NOT have been called
    scout.sports.get_match_context.assert_not_called()
    scout.esports.get_match_context.assert_not_called()


# --- get_window ---

def test_get_window_returns_chronological():
    """get_window returns entries sorted by match_time ascending."""
    scout = _make_scout()
    now = datetime.now(timezone.utc)

    scout._queue = {
        "late_game": {
            "team_a": "A", "team_b": "B",
            "match_time": (now + timedelta(hours=5)).isoformat(),
            "entered": False,
        },
        "early_game": {
            "team_a": "C", "team_b": "D",
            "match_time": (now + timedelta(hours=1)).isoformat(),
            "entered": False,
        },
        "mid_game": {
            "team_a": "E", "team_b": "F",
            "match_time": (now + timedelta(hours=3)).isoformat(),
            "entered": False,
        },
        "past_game": {
            "team_a": "G", "team_b": "H",
            "match_time": (now - timedelta(hours=1)).isoformat(),
            "entered": False, "matched": False,
        },
    }

    results = scout.get_window(hours_ahead=6)
    assert len(results) == 3  # past_game excluded (match_time < now)
    assert results[0]["scout_key"] == "early_game"
    assert results[1]["scout_key"] == "mid_game"
    assert results[2]["scout_key"] == "late_game"


def test_get_window_skips_entered():
    """get_window excludes entries where entered=True."""
    scout = _make_scout()
    now = datetime.now(timezone.utc)

    scout._queue = {
        "open_game": {
            "team_a": "A", "team_b": "B",
            "match_time": (now + timedelta(hours=2)).isoformat(),
            "entered": False,
        },
        "entered_game": {
            "team_a": "C", "team_b": "D",
            "match_time": (now + timedelta(hours=3)).isoformat(),
            "entered": True,
        },
    }

    results = scout.get_window(hours_ahead=6)
    assert len(results) == 1
    assert results[0]["scout_key"] == "open_game"


# --- match_markets_batch ---

def test_match_markets_batch_single_save():
    """match_markets_batch calls _save_queue exactly once (not per match)."""
    scout = _make_scout()
    scout._queue = {
        "nba_lakers_celtics": {
            "team_a": "Lakers",
            "team_b": "Celtics",
            "entered": False,
            "matched": False,
        },
        "nba_heat_bulls": {
            "team_a": "Heat",
            "team_b": "Bulls",
            "entered": False,
            "matched": False,
        },
    }

    markets = [
        MagicMock(question="Will the Lakers beat the Celtics?", slug="lakers-celtics-nba", condition_id="cid1"),
        MagicMock(question="Will the Heat beat the Bulls?", slug="heat-bulls-nba", condition_id="cid2"),
    ]

    with patch.object(scout, "_save_queue") as mock_save:
        results = scout.match_markets_batch(markets)

    assert len(results) == 2
    mock_save.assert_called_once()


# --- PandaScore pagination ---

def test_pandascore_pagination():
    """When a PandaScore page returns 100 results, fetches page 2."""
    scout = _make_scout()
    scout.esports.available = True
    scout.esports.api_key = "test-key"

    now = datetime.now(timezone.utc)
    future = (now + timedelta(hours=2)).isoformat()

    def make_match(name_a, name_b):
        return {
            "begin_at": future,
            "opponents": [
                {"opponent": {"name": name_a}},
                {"opponent": {"name": name_b}},
            ],
        }

    # Page 1: 100 results (triggers pagination)
    page1 = [make_match(f"TeamA{i}", f"TeamB{i}") for i in range(100)]
    # Page 2: 50 results (no more pages)
    page2 = [make_match(f"TeamC{i}", f"TeamD{i}") for i in range(50)]

    resp_page1 = MagicMock()
    resp_page1.status_code = 200
    resp_page1.json.return_value = page1

    resp_page2 = MagicMock()
    resp_page2.status_code = 200
    resp_page2.json.return_value = page2

    call_count = {"n": 0}

    def mock_get(url, params=None, headers=None, timeout=None):
        call_count["n"] += 1
        if params and params.get("page", 1) == 2:
            return resp_page2
        return resp_page1

    with patch("src.scout_scheduler.requests.get", side_effect=mock_get):
        with patch("src.scout_scheduler.record_call"):
            with patch("src.scout_scheduler.time.sleep"):
                matches = scout._fetch_esports_upcoming()

    # Should have fetched page 2 for at least cs2 (first game)
    # Each game with 100 results on page 1 triggers page 2
    assert call_count["n"] >= 2, f"Expected at least 2 requests (pagination), got {call_count['n']}"
