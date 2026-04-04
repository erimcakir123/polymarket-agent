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
                "key": "h2h_3_way",
                "outcomes": [
                    {"name": "AFC Ajax", "price": 1.50},
                    {"name": "FC Twente", "price": 5.00},
                    {"name": "Draw", "price": 4.50},
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


def test_build_odds_params_soccer():
    """Soccer sport keys get 3 regions + h2h,h2h_3_way markets."""
    client = _make_client()
    params = client._build_odds_params("soccer_epl")
    assert params["regions"] == "us,uk,eu"
    assert params["markets"] == "h2h,h2h_3_way"
    assert "commenceTimeFrom" in params
    assert "commenceTimeTo" in params


def test_build_odds_params_non_soccer():
    """Non-soccer sport keys get 3 regions + h2h only."""
    client = _make_client()
    params = client._build_odds_params("baseball_mlb")
    assert params["regions"] == "us,uk,eu"
    assert params["markets"] == "h2h"
    assert "commenceTimeFrom" in params
    assert "commenceTimeTo" in params


def test_build_odds_params_commence_time_is_hour_rounded():
    """commenceTimeFrom/To must be ISO 8601 Z-suffixed and hour-rounded."""
    import re
    client = _make_client()
    params = client._build_odds_params("soccer_epl")
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:00:00Z$"
    assert re.match(pattern, params["commenceTimeFrom"])
    assert re.match(pattern, params["commenceTimeTo"])


def test_build_odds_params_window_is_24_hours():
    """commenceTimeTo must be exactly 24 hours after commenceTimeFrom."""
    from datetime import datetime
    client = _make_client()
    params = client._build_odds_params("baseball_mlb")
    t_from = datetime.strptime(params["commenceTimeFrom"], "%Y-%m-%dT%H:%M:%SZ")
    t_to = datetime.strptime(params["commenceTimeTo"], "%Y-%m-%dT%H:%M:%SZ")
    delta = t_to - t_from
    assert delta.total_seconds() == 24 * 3600


def test_current_refresh_hours_bootstrap():
    """Before any API call, refresh defaults to 2 hours."""
    client = _make_client()
    assert client._current_refresh_hours() == 2.0


def test_current_refresh_hours_low_usage():
    """Usage below 70% -> 2h refresh."""
    client = _make_client()
    client._last_used = 5000
    client._last_remaining = 15000
    assert client._current_refresh_hours() == 2.0


def test_current_refresh_hours_medium_usage():
    """Usage 70-90% -> 3h refresh."""
    client = _make_client()
    client._last_used = 15000
    client._last_remaining = 5000
    assert client._current_refresh_hours() == 3.0


def test_current_refresh_hours_high_usage():
    """Usage >= 90% -> 4h refresh."""
    client = _make_client()
    client._last_used = 19000
    client._last_remaining = 1000
    assert client._current_refresh_hours() == 4.0


def test_past_refresh_boundary_uses_dynamic_interval():
    """_past_refresh_boundary should respect _current_refresh_hours()."""
    import time
    client = _make_client()
    client._last_used = 18000
    client._last_remaining = 2000
    three_hours_ago = time.time() - (3 * 3600)
    assert client._past_refresh_boundary(three_hours_ago) is False
    five_hours_ago = time.time() - (5 * 3600)
    assert client._past_refresh_boundary(five_hours_ago) is True


def test_get_bookmaker_odds_filters_polymarket(monkeypatch):
    """Polymarket bookmaker must be excluded (circular data prevention)."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient(api_key="test")
    monkeypatch.setattr(client, "_detect_sport_key", lambda q, s, t: "baseball_mlb")

    fake_events = [{
        "home_team": "New York Yankees",
        "away_team": "Boston Red Sox",
        "bookmakers": [
            {"key": "polymarket", "title": "Polymarket", "markets": [{
                "key": "h2h", "outcomes": [
                    {"name": "New York Yankees", "price": 1.80},
                    {"name": "Boston Red Sox", "price": 2.10},
                ]}]},
            {"key": "draftkings", "title": "DraftKings", "markets": [{
                "key": "h2h", "outcomes": [
                    {"name": "New York Yankees", "price": 1.90},
                    {"name": "Boston Red Sox", "price": 2.00},
                ]}]},
        ],
    }]
    monkeypatch.setattr(client, "_get", lambda endpoint, params: fake_events)

    result = client.get_bookmaker_odds(
        question="MLB: New York Yankees vs Boston Red Sox",
        slug="mlb-nyy-bos-2026-04-04",
        tags=[],
    )
    assert result is not None
    assert result["num_bookmakers"] == 1
    assert "polymarket" not in [b.lower() for b in result["bookmakers"]]


def test_get_bookmaker_odds_sharp_weighted_average(monkeypatch):
    """Pinnacle (weight 3) should pull the average toward its value."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient(api_key="test")
    monkeypatch.setattr(client, "_detect_sport_key", lambda q, s, t: "basketball_nba")

    fake_events = [{
        "home_team": "Los Angeles Lakers",
        "away_team": "Boston Celtics",
        "bookmakers": [
            {"key": "pinnacle", "title": "Pinnacle", "markets": [{
                "key": "h2h", "outcomes": [
                    {"name": "Los Angeles Lakers", "price": 1.5625},
                    {"name": "Boston Celtics", "price": 2.7778},
                ]}]},
            {"key": "draftkings", "title": "DraftKings", "markets": [{
                "key": "h2h", "outcomes": [
                    {"name": "Los Angeles Lakers", "price": 1.4286},
                    {"name": "Boston Celtics", "price": 3.3333},
                ]}]},
        ],
    }]
    monkeypatch.setattr(client, "_get", lambda endpoint, params: fake_events)

    result = client.get_bookmaker_odds(
        question="NBA: Los Angeles Lakers vs Boston Celtics",
        slug="nba-lal-bos-2026-04-04",
        tags=[],
    )
    assert result is not None
    assert 0.64 <= result["bookmaker_prob_a"] <= 0.67
    assert result["total_weight"] == 4.0
    assert result["has_sharp"] is True
    assert result["num_bookmakers"] == 2


def test_get_bookmaker_odds_no_sharp_flag(monkeypatch):
    """has_sharp should be False when no sharp book contributes."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient(api_key="test")
    monkeypatch.setattr(client, "_detect_sport_key", lambda q, s, t: "basketball_nba")

    fake_events = [{
        "home_team": "Los Angeles Lakers",
        "away_team": "Boston Celtics",
        "bookmakers": [
            {"key": "draftkings", "title": "DraftKings", "markets": [{
                "key": "h2h", "outcomes": [
                    {"name": "Los Angeles Lakers", "price": 1.90},
                    {"name": "Boston Celtics", "price": 2.00},
                ]}]},
        ],
    }]
    monkeypatch.setattr(client, "_get", lambda endpoint, params: fake_events)

    result = client.get_bookmaker_odds(
        question="NBA: Los Angeles Lakers vs Boston Celtics",
        slug="nba-lal-bos-2026-04-04",
        tags=[],
    )
    assert result is not None
    assert result["has_sharp"] is False


def test_get_bookmaker_odds_soccer_3_way(monkeypatch):
    """Soccer with h2h_3_way should return draw probability and correct win prob."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient(api_key="test")
    monkeypatch.setattr(client, "_detect_sport_key", lambda q, s, t: "soccer_epl")

    fake_events = [{
        "home_team": "Manchester City",
        "away_team": "Arsenal",
        "bookmakers": [
            {"key": "pinnacle", "title": "Pinnacle", "markets": [{
                "key": "h2h_3_way", "outcomes": [
                    {"name": "Manchester City", "price": 2.083},
                    {"name": "Arsenal", "price": 4.00},
                    {"name": "Draw", "price": 3.704},
                ]}]},
        ],
    }]
    monkeypatch.setattr(client, "_get", lambda endpoint, params: fake_events)

    result = client.get_bookmaker_odds(
        question="EPL: Manchester City vs Arsenal",
        slug="epl-mci-ars-2026-04-04",
        tags=["premier-league"],
    )
    assert result is not None
    assert 0.45 <= result["bookmaker_prob_a"] <= 0.51
    assert result["bookmaker_prob_draw"] is not None
    assert 0.24 <= result["bookmaker_prob_draw"] <= 0.30


def test_get_bookmaker_odds_non_soccer_no_draw(monkeypatch):
    """Non-soccer markets should have bookmaker_prob_draw = None."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient(api_key="test")
    monkeypatch.setattr(client, "_detect_sport_key", lambda q, s, t: "baseball_mlb")

    fake_events = [{
        "home_team": "New York Yankees",
        "away_team": "Boston Red Sox",
        "bookmakers": [
            {"key": "draftkings", "title": "DraftKings", "markets": [{
                "key": "h2h", "outcomes": [
                    {"name": "New York Yankees", "price": 1.90},
                    {"name": "Boston Red Sox", "price": 2.00},
                ]}]},
        ],
    }]
    monkeypatch.setattr(client, "_get", lambda endpoint, params: fake_events)

    result = client.get_bookmaker_odds(
        question="MLB: New York Yankees vs Boston Red Sox",
        slug="mlb-nyy-bos-2026-04-04",
        tags=[],
    )
    assert result is not None
    assert result["bookmaker_prob_draw"] is None


def test_get_bookmaker_odds_soccer_skips_2way_bookmakers(monkeypatch):
    """For soccer, bookmakers that only offer 2-way h2h must be skipped —
    mixing their draw-absorbed probabilities with true 3-way quotes would
    produce a distribution where home + away + draw > 1.0."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient(api_key="test")
    monkeypatch.setattr(client, "_detect_sport_key", lambda q, s, t: "soccer_epl")

    fake_events = [{
        "home_team": "Manchester City",
        "away_team": "Arsenal",
        "bookmakers": [
            # Sharp: offers real 3-way — should contribute
            {"key": "pinnacle", "title": "Pinnacle", "markets": [{
                "key": "h2h_3_way", "outcomes": [
                    {"name": "Manchester City", "price": 2.083},
                    {"name": "Arsenal", "price": 4.00},
                    {"name": "Draw", "price": 3.704},
                ]}]},
            # Retail: only 2-way h2h for the same soccer match — MUST be skipped
            {"key": "draftkings", "title": "DraftKings", "markets": [{
                "key": "h2h", "outcomes": [
                    {"name": "Manchester City", "price": 1.60},
                    {"name": "Arsenal", "price": 2.40},
                ]}]},
        ],
    }]
    monkeypatch.setattr(client, "_get", lambda endpoint, params: fake_events)

    result = client.get_bookmaker_odds(
        question="EPL: Manchester City vs Arsenal",
        slug="epl-mci-ars-2026-04-04",
        tags=["premier-league"],
    )
    assert result is not None
    # Only Pinnacle (sharp, weight 3.0) should have contributed.
    assert result["num_bookmakers"] == 1
    assert result["total_weight"] == 3.0
    assert result["has_sharp"] is True
    # Distribution must sum to 1.0 (vig-removed 3-way).
    total = (
        result["bookmaker_prob_a"]
        + result["bookmaker_prob_b"]
        + result["bookmaker_prob_draw"]
    )
    assert abs(total - 1.0) < 0.01
