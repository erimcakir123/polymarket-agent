"""Regression tests for odds_api.py bugs (2026-04-04)."""
from unittest.mock import MagicMock


def _make_client():
    """Create OddsAPIClient with no real API key (won't make live calls)."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient(api_key="")
    return client


def test_detect_sport_key_epl_from_slug():
    """Bug 1: EPL slug should resolve without API call."""
    client = _make_client()
    result = client._detect_sport_key(
        question="Will Arsenal beat Chelsea?",
        slug="epl-ars-che-2026-04-04",
        tags=["premier-league"],
    )
    assert result == "soccer_epl"


def test_detect_sport_key_serie_a_from_tag():
    """Bug 1: Tags should resolve when slug prefix matches."""
    client = _make_client()
    result = client._detect_sport_key(
        question="Will SS Lazio win on 2026-04-04?",
        slug="sea-laz-par-2026-04-04-laz",
        tags=["serie-a-2025"],
    )
    # "sea" slug prefix maps to soccer_italy_serie_a
    assert result == "soccer_italy_serie_a"


def test_detect_sport_key_mlb_from_slug():
    """Bug 1: American sports should still work."""
    client = _make_client()
    result = client._detect_sport_key(
        question="MLB: Milwaukee Brewers vs Kansas City Royals",
        slug="mlb-mil-kc-2026-04-03",
        tags=[],
    )
    assert result == "baseball_mlb"


def test_detect_sport_key_eredivisie_from_slug():
    """Bug 1: Eredivisie slug 'ere' should resolve."""
    client = _make_client()
    result = client._detect_sport_key(
        question="Will AFC Ajax win on 2026-04-04?",
        slug="ere-aja-twe-2026-04-04-aja",
        tags=["eredivisie"],
    )
    assert result == "soccer_netherlands_eredivisie"


def test_discover_sport_key_requires_both_teams():
    """Bug 2: Discovery should require BOTH teams, not just one."""
    client = _make_client()
    client._cache = {
        "_active_sports": (["baseball_npb_japan", "icehockey_nhl"], 9999999999),
        "events:baseball_npb_japan": ([
            {"home_team": "Yokohama DeNA BayStars", "away_team": "Tokyo Yakult Swallows"},
        ], 9999999999),
        "events:icehockey_nhl": ([
            {"home_team": "Colorado Avalanche", "away_team": "Dallas Stars"},
        ], 9999999999),
    }
    result = client._discover_sport_key("Avalanche", "Stars")
    assert result == "icehockey_nhl"


# ── Bug 3: Single-team questions ─────────────────────────────────────────

def test_extract_teams_single_team_win():
    """Bug 3: 'Will Ajax win on 2026-04-04?' should extract ('Ajax', None)."""
    client = _make_client()
    a, b = client._extract_teams("Will AFC Ajax win on 2026-04-04?")
    assert a is not None
    assert "ajax" in a.lower()
    assert b is None


def test_extract_teams_vs_still_works():
    """Existing: 'Team A vs Team B' should still return both teams."""
    client = _make_client()
    a, b = client._extract_teams("MLB: Milwaukee Brewers vs Kansas City Royals")
    assert a is not None and "brewers" in a.lower()
    assert b is not None and "royals" in b.lower()


def test_get_bookmaker_odds_single_team(monkeypatch):
    """Bug 3: Single-team question should still fetch odds by finding event."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient(api_key="test_key")

    monkeypatch.setattr(client, "_detect_sport_key", lambda q, s, t: "soccer_netherlands_eredivisie")

    fake_events = [{
        "id": "abc123",
        "home_team": "AFC Ajax",
        "away_team": "FC Twente",
        "bookmakers": [{
            "key": "draftkings",
            "title": "DraftKings",
            "markets": [{
                "key": "h2h",
                "outcomes": [
                    {"name": "AFC Ajax", "price": 1.50},
                    {"name": "FC Twente", "price": 2.80},
                ]
            }]
        }]
    }]
    monkeypatch.setattr(client, "_get", lambda endpoint, params: fake_events)

    result = client.get_bookmaker_odds(
        question="Will AFC Ajax win on 2026-04-04?",
        slug="ere-aja-twe-2026-04-04-aja",
        tags=["eredivisie"],
    )
    assert result is not None
    assert result["bookmaker_prob_a"] > 0.5  # Ajax is the favorite (1.50 odds)
    assert result["num_bookmakers"] >= 1
