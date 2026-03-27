# Odds API Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bridge Polymarket markets to Odds API events for clean team names, fixing 80%+ match failures in NBA/NHL/MLB/Tennis.

**Architecture:** Extract a shared `_api_request()` from `_get()` to eliminate duplication. Add `_get_fresh()` (TTL-based) and bridge methods (`refresh_bridge_events`, `bridge_match`) on top. Insert bridge lookup in `entry_gate.py` between scout injection and ESPN/TheSportsDB, with full fallback preservation.

**Tech Stack:** Python 3.11, requests, team_matcher (existing), pytest + unittest.mock

**Files touched (ONLY these 2 production files + 2 test files):**
- `src/odds_api.py` — all bridge + refactor changes
- `src/entry_gate.py` — bridge insertion (lines 304-325)
- `tests/test_odds_bridge.py` — new: unit tests for bridge
- `tests/test_sports_context_pipeline.py` — modify: add bridge-aware test

---

### Task 1: Refresh Schedule — Expand `_REFRESH_HOURS_UTC`

**Files:**
- Modify: `src/odds_api.py:108-114`

- [ ] **Step 1: Write the failing test**

Create `tests/test_odds_bridge.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestRefreshSchedule -v`
Expected: `test_8_refresh_boundaries` FAILS (currently 5 boundaries)

- [ ] **Step 3: Update refresh schedule**

In `src/odds_api.py`, replace lines 108-114:

```python
    # Scheduled refresh times (UTC hours). Cache invalidates when a boundary is crossed.
    # 02:00 UTC = 05:00 TR → late NBA / West Coast games (23:00 ET tip-offs = 02:00 UTC)
    # 05:00 UTC = 08:00 TR → overnight wrap: catch MLB west coast, late NBA results
    # 07:00 UTC = 10:00 TR → morning: full landscape, European football early lines
    # 12:00 UTC = 15:00 TR → midday: European football lineups confirmed
    # 15:00 UTC = 18:00 TR → afternoon: European football, early evening lines
    # 19:00 UTC = 22:00 TR → evening: NBA/NHL pre-game line movement
    # 21:00 UTC = 00:00 TR → pre-NBA batch: 3.5h before early tip-offs (~00:30 UTC)
    # 23:00 UTC = 02:00 TR → NBA tip-off wave 1 (19:00 ET = 00:00 UTC)
    _REFRESH_HOURS_UTC = [2, 5, 7, 12, 15, 19, 21, 23]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestRefreshSchedule -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add tests/test_odds_bridge.py src/odds_api.py
git commit -m "feat(odds): expand refresh schedule to 8 boundaries — cover NBA prime time gap"
```

---

### Task 2: WTA Gender Routing Fix

**Files:**
- Modify: `src/odds_api.py:189-215` (add `_is_wta_market` static method, update `_detect_sport_key`)
- Test: `tests/test_odds_bridge.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_odds_bridge.py`:

```python
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
        # Pre-populate tennis key caches
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestWTARouting -v`
Expected: `_is_wta_market` AttributeError (method doesn't exist yet), `test_detect_sport_key_routes_wta_correctly` FAILS (routes to ATP)

- [ ] **Step 3: Add `_is_wta_market` and update `_detect_sport_key`**

In `src/odds_api.py`, add static method BEFORE `_detect_sport_key` (after line 188):

```python
    @staticmethod
    def _is_wta_market(q_lower: str, slug: str) -> bool:
        """Detect if a tennis market is WTA (women's) based on question/slug cues."""
        _WTA_SIGNALS = ("wta", "women", "ladies")
        slug_lower = slug.lower() if slug else ""
        return any(s in q_lower or s in slug_lower for s in _WTA_SIGNALS)
```

Then update `_detect_sport_key` — replace the `_tennis_atp` handler (lines 199-201):

```python
                if sport_key == "_tennis_atp":
                    gender = "wta" if self._is_wta_market(q_lower, slug) else "atp"
                    keys = self._get_active_tennis_keys(gender)
                    return keys[0] if keys else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestWTARouting -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/odds_api.py tests/test_odds_bridge.py
git commit -m "fix(odds): WTA gender routing — detect WTA from slug/question before defaulting to ATP"
```

---

### Task 3: `_detect_all_sport_keys()` — Multi-Key Tennis Support

**Files:**
- Modify: `src/odds_api.py` (add method after `_detect_sport_key`)
- Test: `tests/test_odds_bridge.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_odds_bridge.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestDetectAllSportKeys -v`
Expected: AttributeError `_detect_all_sport_keys` not found

- [ ] **Step 3: Add `_detect_all_sport_keys` method**

In `src/odds_api.py`, add after `_detect_sport_key` method (after the closing `return None` on line ~215):

```python
    def _detect_all_sport_keys(self, question: str, slug: str, tags: List[str]) -> List[str]:
        """Like _detect_sport_key but returns ALL matching keys (esp. for tennis).

        For tennis, returns all active tournament keys for the detected gender.
        For other sports, returns a single-element list.
        """
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        if slug_prefix in _SPORT_KEYS:
            return [_SPORT_KEYS[slug_prefix]]

        q_lower = question.lower()
        for keyword, sport_key in _QUESTION_SPORT_KEYS.items():
            if keyword in q_lower:
                if sport_key == "_tennis_atp":
                    gender = "wta" if self._is_wta_market(q_lower, slug) else "atp"
                    return self._get_active_tennis_keys(gender)
                if sport_key == "_tennis_wta":
                    return self._get_active_tennis_keys("wta")
                return [sport_key]

        if slug_prefix in ("atp", "tennis"):
            return self._get_active_tennis_keys("atp")
        if slug_prefix == "wta":
            return self._get_active_tennis_keys("wta")

        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestDetectAllSportKeys -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/odds_api.py tests/test_odds_bridge.py
git commit -m "feat(odds): _detect_all_sport_keys — return all active tennis keys for bridge scanning"
```

---

### Task 4: Refactor `_get()` — Extract `_api_request()`

**Files:**
- Modify: `src/odds_api.py:236-294` (refactor `_get` into `_api_request` + thin `_get`)
- Test: `tests/test_odds_bridge.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_odds_bridge.py`:

```python
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

    @patch("src.odds_api.requests.get")
    def test_backup_key_switch_in_api_request(self, mock_get):
        """_api_request should switch to backup key on 401."""
        mock_get.side_effect = [
            MagicMock(
                raise_for_status=MagicMock(side_effect=Exception("401 Unauthorized")),
            ),
        ]

        client = _make_client()
        client._backup_key = "backup-key-123"
        # Should attempt switch to backup (won't succeed in test but logic should run)
        result = client._api_request("/sports/nba/odds", {"regions": "us"})
        # After backup switch, api_key should change
        # (in real code it would retry, in test the mock only has 1 response)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestApiRequestRefactor::test_api_request_exists -v`
Expected: FAIL — `_api_request` does not exist

- [ ] **Step 3: Refactor — extract `_api_request`, slim down `_get`**

In `src/odds_api.py`, replace `_get` method (lines 236-294) with TWO methods:

```python
    def _api_request(self, endpoint: str, params: dict) -> Optional[dict | list]:
        """Shared HTTP layer — makes authenticated GET to The Odds API.

        Handles: auth, quota tracking, notifications, backup key switch.
        Does NOT handle caching — callers (_get, _get_fresh) own their cache strategy.
        """
        if not self.available:
            return None

        params_with_key = {**params, "apiKey": self.api_key}
        try:
            resp = requests.get(f"{ODDS_API_BASE}{endpoint}", params=params_with_key, timeout=10)
            resp.raise_for_status()

            # Track remaining quota from headers
            remaining_str = resp.headers.get("x-requests-remaining", "?")
            used = resp.headers.get("x-requests-used", "?")
            logger.info("Odds API quota: %s used, %s remaining", used, remaining_str)
            self._requests_used += 1
            record_call("odds_api")

            # Quota threshold notifications
            remaining = int(remaining_str) if remaining_str != "?" else -1
            if remaining >= 0:
                total = remaining + self._requests_used
                if total > 0:
                    usage_pct = self._requests_used / total
                    if usage_pct >= 0.95 and not self._notified_95:
                        msg = "\u26a0\ufe0f Odds API %95 kullan\u0131ld\u0131 \u2014 backup key'e ge\u00e7i\u015f yak\u0131n"
                        logger.warning(msg)
                        if self._notifier:
                            self._notifier.send(msg)
                        self._notified_95 = True
                    elif usage_pct >= 0.80 and not self._notified_80:
                        msg = "\ud83d\udcca Odds API %80 kullan\u0131ld\u0131"
                        logger.warning(msg)
                        if self._notifier:
                            self._notifier.send(msg)
                        self._notified_80 = True

            return resp.json()
        except requests.RequestException as e:
            logger.warning("Odds API error: %s", e)
            if "401" in str(e) or "429" in str(e):
                if not self._using_backup and self._backup_key:
                    logger.warning("ODDS_API: Primary key exhausted, switching to backup")
                    self.api_key = self._backup_key
                    self._using_backup = True
                    return self._api_request(endpoint, params)
                logger.warning("Odds API key invalid/expired — disabling for this session")
                self.api_key = ""
            return None

    def _get(self, endpoint: str, params: dict) -> Optional[dict | list]:
        """Make authenticated GET with scheduled refresh-boundary caching."""
        if not self.available:
            return None

        cache_key = f"{endpoint}:{sorted(params.items())}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if not self._past_refresh_boundary(ts):
                return data

        data = self._api_request(endpoint, params)
        if data is not None:
            self._cache[cache_key] = (data, time.time())
            self._save_cache()
        return data
```

- [ ] **Step 4: Run ALL existing tests to verify nothing broke**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py tests/test_sports_context_pipeline.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/odds_api.py tests/test_odds_bridge.py
git commit -m "refactor(odds): extract _api_request from _get — shared HTTP layer, no duplication"
```

---

### Task 5: `_get_fresh()` — TTL-Based Cache for Bridge

**Files:**
- Modify: `src/odds_api.py` (add `_get_fresh` + `_BRIDGE_CACHE_MAX_AGE` constant)
- Test: `tests/test_odds_bridge.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_odds_bridge.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestGetFresh -v`
Expected: FAIL — `_BRIDGE_CACHE_MAX_AGE` and `_get_fresh` don't exist

- [ ] **Step 3: Add `_BRIDGE_CACHE_MAX_AGE` constant and `_get_fresh` method**

In `src/odds_api.py`, add class attribute after `_CACHE_FILE` (line ~116):

```python
    _BRIDGE_CACHE_MAX_AGE = 10800  # 3h — bridge events refresh independently of boundaries
```

Add `_get_fresh` method after `_get` method:

```python
    def _get_fresh(self, endpoint: str, params: dict) -> Optional[dict | list]:
        """Make API call with TTL-based caching — bypasses refresh-boundary.

        Used by bridge to ensure fresh events. Uses _api_request() for the
        actual HTTP call (shared auth, quota tracking, backup key logic).
        """
        if not self.available:
            return None

        cache_key = f"bridge_raw:{endpoint}:{sorted(params.items())}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.time() - ts < self._BRIDGE_CACHE_MAX_AGE:
                return data

        data = self._api_request(endpoint, params)
        if data is not None:
            self._cache[cache_key] = (data, time.time())
        return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestGetFresh -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/odds_api.py tests/test_odds_bridge.py
git commit -m "feat(odds): _get_fresh with TTL-based cache for bridge — bypasses refresh boundaries"
```

---

### Task 6: Bridge Sport Key Lists + `refresh_bridge_events()`

**Files:**
- Modify: `src/odds_api.py` (add class attributes + method)
- Test: `tests/test_odds_bridge.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_odds_bridge.py`:

```python
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
            mock_dt.now.return_value = MagicMock(month=3)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            client.refresh_bridge_events()

        # Check NFL was NOT fetched (no bridge:americanfootball_nfl in cache)
        nfl_keys = [k for k in client._cache if "americanfootball_nfl" in k and k.startswith("bridge:")]
        assert len(nfl_keys) == 0, "NFL should be skipped in March"

    def test_refresh_returns_zero_without_api_key(self):
        """No API key → return 0, don't crash."""
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestRefreshBridgeEvents -v`
Expected: FAIL — `refresh_bridge_events` doesn't exist

- [ ] **Step 3: Add sport key lists and `refresh_bridge_events`**

In `src/odds_api.py`, add class attributes after `_BRIDGE_CACHE_MAX_AGE`:

```python
    # All sport keys to scan when building the bridge event pool.
    _BRIDGE_SPORT_KEYS_ALWAYS = [
        "basketball_nba",
        "baseball_mlb",
        "icehockey_nhl",
        "mma_mixed_martial_arts", "boxing_boxing",
        "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a",
        "soccer_germany_bundesliga", "soccer_france_ligue_one",
        "soccer_uefa_champs_league", "soccer_uefa_europa_league",
        "soccer_usa_mls",
        "cricket_ipl", "cricket_international_t20",
        "rugbyleague_nrl",
    ]
    _BRIDGE_SPORT_KEYS_SEASONAL = {
        "americanfootball_nfl": (8, 9, 10, 11, 12, 1, 2),
        "americanfootball_ncaaf": (8, 9, 10, 11, 12, 1),
        "basketball_ncaab": (11, 12, 1, 2, 3, 4),
        "basketball_wncaab": (11, 12, 1, 2, 3, 4),
    }
```

Add `refresh_bridge_events` method at the END of the class (before `get_live_scores`):

```python
    # ------------------------------------------------------------------
    # Odds API Bridge — match Polymarket markets against Odds API events
    # to extract clean standardized team names for ESPN/PandaScore lookups
    # ------------------------------------------------------------------

    def refresh_bridge_events(self, force: bool = False) -> int:
        """Fetch events for all sports + active tennis into bridge cache.

        Called once per entry_gate analysis cycle. Uses _get_fresh() to bypass
        refresh-boundary caching so bridge always has current events.

        Returns total number of events in the bridge pool.
        """
        if not self.available:
            return 0

        total = 0
        sport_keys = list(self._BRIDGE_SPORT_KEYS_ALWAYS)

        current_month = datetime.now(timezone.utc).month
        for sk, active_months in self._BRIDGE_SPORT_KEYS_SEASONAL.items():
            if current_month in active_months:
                sport_keys.append(sk)

        for gender in ("atp", "wta"):
            sport_keys.extend(self._get_active_tennis_keys(gender))

        for sport_key in sport_keys:
            cache_key = f"bridge:{sport_key}"
            cached = self._cache.get(cache_key)
            if cached and not force:
                data, ts = cached
                if time.time() - ts < self._BRIDGE_CACHE_MAX_AGE:
                    total += len(data) if isinstance(data, list) else 0
                    continue

            events = self._get_fresh(f"/sports/{sport_key}/odds", {
                "regions": "us",
                "markets": "h2h",
                "oddsFormat": "decimal",
            })
            if events and isinstance(events, list):
                self._cache[cache_key] = (events, time.time())
                # Cross-populate regular cache so get_bookmaker_odds benefits
                regular_key = f"/sports/{sport_key}/odds:{sorted({'regions': 'us', 'markets': 'h2h', 'oddsFormat': 'decimal'}.items())}"
                self._cache[regular_key] = (events, time.time())
                total += len(events)
                logger.debug("Bridge cache refreshed: %s -> %d events", sport_key, len(events))
            elif events is None and cached:
                total += len(cached[0]) if isinstance(cached[0], list) else 0

        self._save_cache()
        logger.info("Bridge event pool: %d total events across %d sport keys", total, len(sport_keys))
        return total
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestRefreshBridgeEvents -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/odds_api.py tests/test_odds_bridge.py
git commit -m "feat(odds): refresh_bridge_events — populate event pool for bridge matching"
```

---

### Task 7: `_get_bridge_events()` + `bridge_match()` Core Methods

**Files:**
- Modify: `src/odds_api.py` (add 2 methods after `refresh_bridge_events`)
- Test: `tests/test_odds_bridge.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_odds_bridge.py`:

```python
class TestBridgeMatch:
    def test_bridge_match_targeted(self):
        """Bridge should match using targeted sport key detection."""
        client = _make_client()
        # Pre-populate bridge cache with NBA events
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
        # Put MLB events in bridge cache — but slug has no prefix
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
        client._cache["other:key"] = ({"x": 1}, time.time())  # Should be excluded

        results = client._get_bridge_events()
        sport_keys = [sk for sk, _ in results]
        assert "basketball_nba" in sport_keys
        assert "baseball_mlb" in sport_keys
        assert len(results) == 2  # 'other:key' excluded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestBridgeMatch -v`
Expected: FAIL — `bridge_match` and `_get_bridge_events` don't exist

- [ ] **Step 3: Add `_get_bridge_events` and `bridge_match` methods**

In `src/odds_api.py`, add after `refresh_bridge_events`:

```python
    def _get_bridge_events(self) -> List[Tuple[str, list]]:
        """Return all cached bridge events as (sport_key, events) pairs."""
        results = []
        for cache_key, (data, ts) in self._cache.items():
            if not cache_key.startswith("bridge:"):
                continue
            sport_key = cache_key[len("bridge:"):]
            if isinstance(data, list) and data:
                results.append((sport_key, data))
        return results

    def bridge_match(
        self, question: str, slug: str, tags: List[str],
    ) -> Optional[Dict]:
        """Match a Polymarket market against cached Odds API events.

        Returns dict with home_team, away_team, sport_key, confidence, event_id
        or None if no match found.
        """
        team_a, team_b = self._extract_teams(question)
        if not team_a or not team_b:
            return None

        # Strategy 1: Targeted — detect sport key, search only that sport
        sport_keys = self._detect_all_sport_keys(question, slug, tags)
        if sport_keys:
            for sk in sport_keys:
                cache_key = f"bridge:{sk}"
                cached = self._cache.get(cache_key)
                if not cached:
                    # Try regular odds cache (populated by get_bookmaker_odds)
                    odds_key = f"/sports/{sk}/odds:{sorted({'regions': 'us', 'markets': 'h2h', 'oddsFormat': 'decimal'}.items())}"
                    cached = self._cache.get(odds_key)
                if not cached:
                    continue
                events = cached[0]
                if not isinstance(events, list):
                    continue
                result = find_best_event_match(team_a, team_b, events, min_confidence=0.80)
                if result:
                    event, conf = result
                    return {
                        "home_team": event.get("home_team", ""),
                        "away_team": event.get("away_team", ""),
                        "sport_key": sk,
                        "confidence": conf,
                        "event_id": event.get("id", ""),
                    }

        # Strategy 2: Exhaustive — scan ALL bridge cache entries
        best_result = None
        best_conf = 0.0
        for sport_key, events in self._get_bridge_events():
            result = find_best_event_match(team_a, team_b, events, min_confidence=0.80)
            if result:
                event, conf = result
                if conf > best_conf:
                    best_conf = conf
                    best_result = {
                        "home_team": event.get("home_team", ""),
                        "away_team": event.get("away_team", ""),
                        "sport_key": sport_key,
                        "confidence": conf,
                        "event_id": event.get("id", ""),
                    }

        if best_result:
            logger.info("Bridge match (exhaustive): '%s' -> %s vs %s [%.0f%%]",
                        question[:50], best_result["home_team"],
                        best_result["away_team"], best_result["confidence"] * 100)
        return best_result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestBridgeMatch -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/odds_api.py tests/test_odds_bridge.py
git commit -m "feat(odds): bridge_match + _get_bridge_events — core bridge matching logic"
```

---

### Task 8: Cross-Populate Bridge Cache from `get_bookmaker_odds()`

**Files:**
- Modify: `src/odds_api.py:309-316` (add 3 lines after events fetch)
- Test: `tests/test_odds_bridge.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_odds_bridge.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestCrossPopulate -v`
Expected: FAIL — `bridge:basketball_nba` key not in cache

- [ ] **Step 3: Add cross-population to `get_bookmaker_odds`**

In `src/odds_api.py`, in `get_bookmaker_odds` method, after `if not events: return None` (line ~316), add:

```python
        # Side-effect: populate bridge cache with this sport's events (free — same data)
        if isinstance(events, list):
            bridge_key = f"bridge:{sport_key}"
            self._cache[bridge_key] = (events, time.time())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestCrossPopulate -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/odds_api.py tests/test_odds_bridge.py
git commit -m "feat(odds): cross-populate bridge cache from get_bookmaker_odds — zero extra API calls"
```

---

### Task 9: Entry Gate Bridge Integration

**Files:**
- Modify: `src/entry_gate.py:304-325` (replace sports context section)
- Test: `tests/test_sports_context_pipeline.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_sports_context_pipeline.py`, add a new test (keep existing tests intact):

```python
def test_bridge_injects_clean_names_into_espn():
    """When bridge matches, ESPN should receive clean team names."""
    sports_mock = MagicMock()
    # ESPN should succeed when given clean names
    sports_mock.get_match_context = MagicMock(return_value="ESPN context: Lakers vs Celtics")

    gate = _make_gate(sports=sports_mock)

    # Configure odds_api with bridge capability
    gate.odds_api.available = True
    gate.odds_api.refresh_bridge_events = MagicMock(return_value=50)
    gate.odds_api.bridge_match = MagicMock(return_value={
        "home_team": "Los Angeles Lakers",
        "away_team": "Boston Celtics",
        "sport_key": "basketball_nba",
        "confidence": 0.95,
        "event_id": "e1",
    })

    m = _make_market(
        cid="cid-bridge-1",
        slug="nba-lakers-celtics",
        question="NBA: Lakers vs Celtics",
    )
    markets, estimates = gate._analyze_batch([m], cycle_count=1)

    # Verify bridge_match was called
    gate.odds_api.bridge_match.assert_called_once()

    # Verify ESPN received the clean bridge name, not the raw question
    calls = sports_mock.get_match_context.call_args_list
    assert any("Los Angeles Lakers vs Boston Celtics" in str(c) for c in calls), \
        f"ESPN should receive clean bridge names. Calls: {calls}"


def test_bridge_fallback_to_original_path():
    """When bridge returns None, original ESPN path should run."""
    sports_mock = MagicMock()
    sports_mock.get_match_context = MagicMock(return_value="ESPN fallback context")

    gate = _make_gate(sports=sports_mock)
    gate.odds_api.available = True
    gate.odds_api.refresh_bridge_events = MagicMock(return_value=50)
    gate.odds_api.bridge_match = MagicMock(return_value=None)  # Bridge fails

    m = _make_market(
        cid="cid-fallback-1",
        slug="nba-knicks-hornets",
        question="NBA: Knicks vs Hornets",
    )
    markets, estimates = gate._analyze_batch([m], cycle_count=1)

    # ESPN should still be called with the original question
    calls = sports_mock.get_match_context.call_args_list
    assert any("Knicks vs Hornets" in str(c) for c in calls), \
        f"Fallback should use original question. Calls: {calls}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_sports_context_pipeline.py::test_bridge_injects_clean_names_into_espn -v`
Expected: FAIL — bridge methods not called, ESPN receives original question

- [ ] **Step 3: Modify entry_gate.py — replace lines 304-325**

In `src/entry_gate.py`, replace the sports context section (lines 304-325) with:

```python
        # Odds API Bridge: match Polymarket markets to Odds API events for clean team names
        _bridge_names: dict[str, dict] = {}
        if self.odds_api and self.odds_api.available:
            try:
                pool_size = self.odds_api.refresh_bridge_events()
                if pool_size > 0:
                    for _m in prioritized:
                        if _m.condition_id in esports_contexts:
                            continue
                        if is_esports_slug(_m.slug or ""):
                            continue
                        _br = self.odds_api.bridge_match(
                            getattr(_m, "question", ""), _m.slug or "",
                            getattr(_m, "tags", []),
                        )
                        if _br:
                            _bridge_names[_m.condition_id] = _br
                    if _bridge_names:
                        logger.info("Bridge matched %d/%d non-esports markets",
                                    len(_bridge_names), len(prioritized))
            except Exception as exc:
                logger.warning("Bridge refresh failed: %s", exc)

        # Traditional sports context: Bridge→ESPN → Original→ESPN → TheSportsDB
        if self.sports:
            for _m in prioritized:
                if _m.condition_id in esports_contexts:
                    continue
                _is_esports_mkt = is_esports_slug(_m.slug or "")
                if _is_esports_mkt:
                    continue
                try:
                    _ctx = None
                    _source = ""
                    _bridge_info = _bridge_names.get(_m.condition_id)

                    # Kademe 1: Bridge clean names → ESPN
                    if _bridge_info:
                        _clean_q = f"{_bridge_info['home_team']} vs {_bridge_info['away_team']}"
                        _ctx = self.sports.get_match_context(_clean_q, _m.slug or "", [])
                        if _ctx:
                            _source = "Bridge->ESPN"

                    # Kademe 2: Original question → ESPN
                    if not _ctx:
                        _ctx = self.sports.get_match_context(
                            getattr(_m, "question", ""), _m.slug or "", []
                        )
                        if _ctx:
                            _source = "ESPN"

                    # Kademe 3: TheSportsDB fallback (try bridge names first, then original)
                    if not _ctx:
                        if _bridge_info:
                            _clean_q = f"{_bridge_info['home_team']} vs {_bridge_info['away_team']}"
                            _ctx = self.tsdb.get_match_context(_clean_q)
                        if not _ctx:
                            _ctx = self.tsdb.get_match_context(getattr(_m, "question", ""))
                        if _ctx:
                            _source = "TheSportsDB"

                    if _ctx:
                        esports_contexts[_m.condition_id] = _ctx
                        logger.info("Sports context fetched (%s): %s", _source, _m.slug[:40])
                except Exception as _exc:
                    logger.debug("Sports context fetch error for %s: %s", _m.slug[:40], _exc)
```

- [ ] **Step 4: Run ALL tests to verify nothing broke**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py tests/test_sports_context_pipeline.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/entry_gate.py tests/test_sports_context_pipeline.py
git commit -m "feat(entry): integrate Odds API bridge — 3-tier fallback (Bridge→ESPN → ESPN → TheSportsDB)"
```

---

### Task 10: Full Integration Smoke Test + Final Verification

**Files:**
- Test: `tests/test_odds_bridge.py` (add integration test)
- All files: run full test suite

- [ ] **Step 1: Write integration smoke test**

Append to `tests/test_odds_bridge.py`:

```python
class TestBridgeIntegration:
    """End-to-end smoke tests: bridge_match → clean names → correct result."""

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
```

- [ ] **Step 2: Run the integration smoke tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_odds_bridge.py::TestBridgeIntegration -v`
Expected: ALL PASS

- [ ] **Step 3: Run the FULL test suite**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v --tb=short 2>&1 | tail -40`
Expected: All existing tests PASS, no regressions

- [ ] **Step 4: Final commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add tests/test_odds_bridge.py
git commit -m "test(odds): integration smoke tests — verify production failure cases are fixed"
```
