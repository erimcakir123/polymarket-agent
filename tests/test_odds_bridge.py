"""Tests for Odds API bridge infrastructure."""
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


def _make_client():
    """Create OddsAPIClient with no real API key (tests use mocks)."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient.__new__(OddsAPIClient)
    client.api_key = "test-key"
    client._backup_key = ""
    client._using_backup = False
    client._cache = {}
    client._cache_ttl = 28800
    client._hist_cache_ttl = 28800
    client._requests_used = 0
    client._notified_80 = False
    client._notified_95 = False
    client._notifier = None
    return client


class TestRefreshSchedule:
    def test_8_refresh_boundaries(self):
        """Refresh schedule must have 8 boundaries covering NBA prime time."""
        from src.odds_api import OddsAPIClient
        hours = OddsAPIClient._REFRESH_HOURS_UTC
        assert len(hours) == 8
        # Must cover NBA prime time gap: hours 23 and 5 must be present
        assert 23 in hours, "23 UTC missing — NBA tip-off wave 1 uncovered"
        assert 5 in hours, "05 UTC missing — overnight wrap uncovered"
        assert 12 in hours, "12 UTC missing — European midday uncovered"

    def test_boundary_crossed_at_23_utc(self):
        """Cache from 21:30 UTC must be stale at 23:01 UTC (NBA window)."""
        client = _make_client()
        # Simulate cache written at 21:30 UTC today
        cached_dt = datetime.now(timezone.utc).replace(hour=21, minute=30, second=0)
        cached_ts = cached_dt.timestamp()
        # Check at 23:01 UTC
        with patch("src.odds_api.datetime") as mock_dt:
            mock_dt.now.return_value = cached_dt.replace(hour=23, minute=1)
            mock_dt.fromtimestamp = datetime.fromtimestamp
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = client._past_refresh_boundary(cached_ts)
        assert result is True, "21:30→23:01 should cross boundary 23"


class TestWTARouting:
    def test_wta_slug_detected(self):
        """Slug with 'wta' prefix should route to WTA keys."""
        from src.odds_api import OddsAPIClient
        assert OddsAPIClient._is_wta_market("miami open: sabalenka vs baptiste", "wta-miami-open-sabalenka-baptiste") is True

    def test_wta_keyword_in_question(self):
        """Question containing 'wta' should route to WTA."""
        from src.odds_api import OddsAPIClient
        assert OddsAPIClient._is_wta_market("wta miami open: sabalenka vs baptiste", "tennis-sabalenka") is True

    def test_atp_not_detected_as_wta(self):
        """ATP match should NOT be detected as WTA."""
        from src.odds_api import OddsAPIClient
        assert OddsAPIClient._is_wta_market("miami open: sinner vs alcaraz", "atp-miami-sinner") is False

    def test_detect_sport_key_routes_wta_correctly(self):
        """'miami open' question with WTA slug must NOT go to ATP keys."""
        client = _make_client()
        client._cache["_tennis_sports:wta"] = (["tennis_wta_miami_open"], time.time())
        client._cache["_tennis_sports:atp"] = (["tennis_atp_miami_open"], time.time())

        key = client._detect_sport_key(
            "Miami Open: Aryna Sabalenka vs Hailey Baptiste",
            "wta-miami-open-sabalenka-baptiste",
            []
        )
        assert key == "tennis_wta_miami_open", f"Expected WTA key, got {key}"

    def test_detect_sport_key_atp_default(self):
        """'miami open' without WTA signals should go to ATP."""
        client = _make_client()
        client._cache["_tennis_sports:atp"] = (["tennis_atp_miami_open"], time.time())
        client._cache["_tennis_sports:wta"] = (["tennis_wta_miami_open"], time.time())

        key = client._detect_sport_key(
            "Miami Open: Jannik Sinner vs Carlos Alcaraz",
            "atp-miami-sinner-alcaraz",
            []
        )
        assert key == "tennis_atp_miami_open", f"Expected ATP key, got {key}"


class TestDetectAllSportKeys:
    def test_non_tennis_returns_single_key(self):
        """NBA slug should return single-element list."""
        client = _make_client()
        keys = client._detect_all_sport_keys("NBA: Knicks vs Hornets", "nba-knicks-hornets", [])
        assert keys == ["basketball_nba"]

    def test_tennis_returns_all_active_keys(self):
        """Tennis should return ALL active tournament keys, not just first."""
        client = _make_client()
        client._cache["_tennis_sports:atp"] = (
            ["tennis_atp_miami_open", "tennis_atp_french_open", "tennis_atp_wimbledon"],
            time.time()
        )
        keys = client._detect_all_sport_keys(
            "ATP: Sinner vs Alcaraz", "atp-sinner-alcaraz", []
        )
        assert len(keys) == 3
        assert "tennis_atp_miami_open" in keys
        assert "tennis_atp_french_open" in keys

    def test_wta_tennis_returns_wta_keys(self):
        """WTA question should return WTA keys, not ATP."""
        client = _make_client()
        client._cache["_tennis_sports:wta"] = (
            ["tennis_wta_miami_open", "tennis_wta_french_open"],
            time.time()
        )
        client._cache["_tennis_sports:atp"] = (
            ["tennis_atp_miami_open"],
            time.time()
        )
        keys = client._detect_all_sport_keys(
            "Miami Open: Sabalenka vs Baptiste",
            "wta-miami-sabalenka",
            []
        )
        assert len(keys) == 2
        assert all(k.startswith("tennis_wta") for k in keys)


class TestApiRequestRefactor:
    def test_api_request_exists(self):
        """_api_request must exist as the shared HTTP layer."""
        client = _make_client()
        assert hasattr(client, "_api_request")

    @patch("src.odds_api.requests.get")
    def test_api_request_returns_data(self, mock_get):
        """_api_request should make HTTP call and return parsed JSON."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "event1", "home_team": "Lakers"}]
        mock_resp.headers = {"x-requests-remaining": "19000", "x-requests-used": "50"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = _make_client()
        result = client._api_request("/sports/basketball_nba/odds", {"regions": "us"})

        assert result is not None
        assert result[0]["home_team"] == "Lakers"
        mock_get.assert_called_once()

    @patch("src.odds_api.requests.get")
    def test_get_still_works_with_boundary_cache(self, mock_get):
        """_get must still use refresh-boundary caching after refactor."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "e1"}]
        mock_resp.headers = {"x-requests-remaining": "19000", "x-requests-used": "50"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = _make_client()

        # First call — should hit API
        r1 = client._get("/sports/basketball_nba/odds", {"regions": "us"})
        assert r1 is not None
        assert mock_get.call_count == 1

        # Second call — should use cache (no boundary crossed)
        r2 = client._get("/sports/basketball_nba/odds", {"regions": "us"})
        assert r2 is not None
        assert mock_get.call_count == 1  # No new API call


class TestGetFresh:
    def test_bridge_cache_max_age_exists(self):
        """Bridge cache TTL constant must exist."""
        from src.odds_api import OddsAPIClient
        assert hasattr(OddsAPIClient, "_BRIDGE_CACHE_MAX_AGE")
        assert OddsAPIClient._BRIDGE_CACHE_MAX_AGE == 10800  # 3 hours

    @patch("src.odds_api.requests.get")
    def test_get_fresh_bypasses_boundary_cache(self, mock_get):
        """_get_fresh should use TTL, not refresh boundaries."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "e1"}]
        mock_resp.headers = {"x-requests-remaining": "19000", "x-requests-used": "50"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = _make_client()

        # First call
        r1 = client._get_fresh("/sports/basketball_nba/odds", {"regions": "us"})
        assert r1 is not None
        assert mock_get.call_count == 1

        # Second call within TTL — should use cache
        r2 = client._get_fresh("/sports/basketball_nba/odds", {"regions": "us"})
        assert r2 == r1
        assert mock_get.call_count == 1  # Still 1 — cached

    @patch("src.odds_api.requests.get")
    def test_get_fresh_refetches_after_ttl(self, mock_get):
        """_get_fresh should re-fetch when TTL expires."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "e1"}]
        mock_resp.headers = {"x-requests-remaining": "19000", "x-requests-used": "50"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = _make_client()

        # First call
        client._get_fresh("/sports/basketball_nba/odds", {"regions": "us"})

        # Expire the cache manually
        for k in list(client._cache.keys()):
            if k.startswith("bridge_raw:"):
                data, ts = client._cache[k]
                client._cache[k] = (data, ts - 11000)  # 11000s ago > 10800 TTL

        # Second call — should re-fetch
        client._get_fresh("/sports/basketball_nba/odds", {"regions": "us"})
        assert mock_get.call_count == 2


class TestRefreshBridgeEvents:
    @patch("src.odds_api.requests.get")
    def test_refresh_populates_bridge_cache(self, mock_get):
        """refresh_bridge_events must populate bridge:{sport_key} cache entries."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"id": "e1", "home_team": "Lakers", "away_team": "Celtics"},
            {"id": "e2", "home_team": "Knicks", "away_team": "Nets"},
        ]
        mock_resp.headers = {"x-requests-remaining": "19000", "x-requests-used": "50"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = _make_client()
        total = client.refresh_bridge_events()
        assert total > 0
        # Check that bridge cache entries exist
        bridge_keys = [k for k in client._cache if k.startswith("bridge:")]
        assert len(bridge_keys) > 0

    @patch("src.odds_api.requests.get")
    def test_refresh_skips_offseason_sports(self, mock_get):
        """NFL should be skipped in March (offseason)."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.headers = {"x-requests-remaining": "19000", "x-requests-used": "50"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = _make_client()

        with patch("src.odds_api.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.month = 3
            mock_dt.now.return_value = mock_now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            client.refresh_bridge_events()

        # NFL key should NOT be in bridge cache
        nfl_keys = [k for k in client._cache if "americanfootball_nfl" in k and k.startswith("bridge:")]
        assert len(nfl_keys) == 0, "NFL should be skipped in March"

    def test_refresh_returns_zero_without_api_key(self):
        """No API key -> return 0, don't crash."""
        client = _make_client()
        client.api_key = ""
        assert client.refresh_bridge_events() == 0

    @patch("src.odds_api.requests.get")
    def test_refresh_cross_populates_regular_cache(self, mock_get):
        """Bridge refresh should also update the regular _get() cache."""
        events = [{"id": "e1", "home_team": "Lakers", "away_team": "Celtics"}]
        mock_resp = MagicMock()
        mock_resp.json.return_value = events
        mock_resp.headers = {"x-requests-remaining": "19000", "x-requests-used": "50"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = _make_client()
        client.refresh_bridge_events()

        # Regular cache key should also have the data
        regular_keys = [k for k in client._cache
                        if k.startswith("/sports/") and "basketball_nba" in k]
        assert len(regular_keys) > 0, "Bridge refresh should cross-populate regular cache"


class TestBridgeMatch:
    def test_bridge_match_targeted(self):
        """Bridge should match using targeted sport key detection."""
        client = _make_client()
        events = [
            {"id": "e1", "home_team": "New York Knicks", "away_team": "Charlotte Hornets",
             "bookmakers": []},
            {"id": "e2", "home_team": "Houston Rockets", "away_team": "Memphis Grizzlies",
             "bookmakers": []},
        ]
        client._cache["bridge:basketball_nba"] = (events, time.time())

        result = client.bridge_match(
            "NBA: Knicks vs Hornets", "nba-knicks-hornets", []
        )
        assert result is not None
        assert result["home_team"] == "New York Knicks"
        assert result["away_team"] == "Charlotte Hornets"
        assert result["sport_key"] == "basketball_nba"
        assert result["confidence"] >= 0.80

    def test_bridge_match_exhaustive_scan(self):
        """When sport detection fails, bridge should scan ALL cached events."""
        client = _make_client()
        events = [
            {"id": "e1", "home_team": "New York Yankees", "away_team": "Boston Red Sox",
             "bookmakers": []},
        ]
        client._cache["bridge:baseball_mlb"] = (events, time.time())

        result = client.bridge_match(
            "Yankees vs Red Sox", "unknown-slug-yankees-redsox", []
        )
        assert result is not None
        assert result["home_team"] == "New York Yankees"
        assert result["sport_key"] == "baseball_mlb"

    def test_bridge_match_no_vs_returns_none(self):
        """Question without 'vs' separator should return None."""
        client = _make_client()
        result = client.bridge_match(
            "Will the Knicks win the championship?", "nba-knicks-champ", []
        )
        assert result is None

    def test_bridge_match_no_match_returns_none(self):
        """When no event matches, return None (don't crash)."""
        client = _make_client()
        client._cache["bridge:basketball_nba"] = (
            [{"id": "e1", "home_team": "Lakers", "away_team": "Celtics", "bookmakers": []}],
            time.time()
        )
        result = client.bridge_match(
            "NBA: Knicks vs Hornets", "nba-knicks-hornets", []
        )
        assert result is None

    def test_get_bridge_events_returns_cached(self):
        """_get_bridge_events should return all bridge cache entries."""
        client = _make_client()
        client._cache["bridge:basketball_nba"] = ([{"id": "e1"}], time.time())
        client._cache["bridge:baseball_mlb"] = ([{"id": "e2"}], time.time())
        client._cache["other:key"] = ({"x": 1}, time.time())

        results = client._get_bridge_events()
        sport_keys = [sk for sk, _ in results]
        assert "basketball_nba" in sport_keys
        assert "baseball_mlb" in sport_keys
        assert len(results) == 2


class TestCrossPopulate:
    @patch("src.odds_api.requests.get")
    def test_get_bookmaker_odds_populates_bridge_cache(self, mock_get):
        """get_bookmaker_odds should side-effect populate bridge cache."""
        events = [
            {"id": "e1", "home_team": "Los Angeles Lakers", "away_team": "Boston Celtics",
             "bookmakers": [{"title": "DraftKings", "markets": [
                 {"key": "h2h", "outcomes": [
                     {"name": "Los Angeles Lakers", "price": 2.10},
                     {"name": "Boston Celtics", "price": 1.80},
                 ]}
             ]}]},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = events
        mock_resp.headers = {"x-requests-remaining": "19000", "x-requests-used": "50"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = _make_client()
        client.get_bookmaker_odds("NBA: Lakers vs Celtics", "nba-lakers-celtics", [])

        # Bridge cache should now have NBA events
        bridge_key = "bridge:basketball_nba"
        assert bridge_key in client._cache
        bridge_data, _ = client._cache[bridge_key]
        assert len(bridge_data) == 1
        assert bridge_data[0]["home_team"] == "Los Angeles Lakers"


class TestBridgeIntegration:
    """End-to-end smoke tests: bridge_match -> clean names -> correct result."""

    def test_nba_knicks_vs_hornets(self):
        """The exact failure case from production logs."""
        client = _make_client()
        client._cache["bridge:basketball_nba"] = ([
            {"id": "e1", "home_team": "New York Knicks", "away_team": "Charlotte Hornets",
             "bookmakers": []},
            {"id": "e2", "home_team": "Houston Rockets", "away_team": "Memphis Grizzlies",
             "bookmakers": []},
        ], time.time())

        r = client.bridge_match("NBA: Knicks vs Hornets", "nba-knicks-hornets", [])
        assert r is not None
        assert r["home_team"] == "New York Knicks"
        assert r["away_team"] == "Charlotte Hornets"

    def test_wta_miami_open_sabalenka(self):
        """WTA Miami Open — was routing to ATP, now should match WTA."""
        client = _make_client()
        client._cache["_tennis_sports:wta"] = (["tennis_wta_miami_open"], time.time())
        client._cache["bridge:tennis_wta_miami_open"] = ([
            {"id": "t1", "home_team": "Aryna Sabalenka", "away_team": "Hailey Baptiste",
             "bookmakers": []},
        ], time.time())

        r = client.bridge_match(
            "Miami Open: Aryna Sabalenka vs Hailey Baptiste",
            "wta-miami-sabalenka-baptiste", []
        )
        assert r is not None
        assert r["home_team"] == "Aryna Sabalenka"
        assert r["sport_key"] == "tennis_wta_miami_open"

    def test_rockets_vs_grizzlies(self):
        """Another production failure case — stale cache."""
        client = _make_client()
        client._cache["bridge:basketball_nba"] = ([
            {"id": "e1", "home_team": "Houston Rockets", "away_team": "Memphis Grizzlies",
             "bookmakers": []},
        ], time.time())

        r = client.bridge_match("NBA: Rockets vs Grizzlies", "nba-rockets-grizzlies", [])
        assert r is not None
        assert r["home_team"] == "Houston Rockets"
        assert r["away_team"] == "Memphis Grizzlies"
