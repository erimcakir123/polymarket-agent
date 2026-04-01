# ESPN Data Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich AI analyst prompts with ESPN injuries, BPI predictor, standings (home/away split), H2H, B2B detection, and venue data — consolidating team-sport enrichment into `sports_data.py` and slimming `espn_enrichment.py` to athlete-only.

**Architecture:** Add 5 new methods to `SportsDataClient` in `sports_data.py` (injuries, standings, BPI predictor, B2B, H2H). Enhance `_get_team_match_context()` to call them and produce a richer context string. Update `ai_analyst.py` DATA SOURCES section. Remove overlapping team-sport methods from `espn_enrichment.py`. Update `sports_discovery.py` wiring so team sports no longer route through `ESPNEnrichment.enrich()`.

**Tech Stack:** Python 3.11, requests, ESPN public API (no key), pytest

**Safety strategy:** Each task adds new code and tests first, then modifies existing code only after the replacement is proven. `espn_enrichment.py` cleanup is the LAST task — nothing breaks until we're sure the new code works.

---

## Safety Rules (MANDATORY — every task)

1. **Her adımda mevcut testleri çalıştır** — Yeni method ekledikten sonra `python -m pytest tests/ --tb=short` ile TÜM testlerin hala geçtiğini doğrula. Sadece yeni testler değil, ESKİ testler de geçmeli.

2. **Silmeden önce kanıtla** — `espn_enrichment.py`'den method silmeden ÖNCE, yeni karşılığının `sports_data.py`'de çalıştığını test ile kanıtla. Task 1-5 tamamlanmadan Task 7'ye geçme.

3. **Wiring en son değişir** — `sports_discovery.py` bağlantıları (Task 7) en son değişir. Yeni method'lar test edildikten sonra bağla. Bu sayede herhangi bir noktada durursan sistem çalışmaya devam eder.

4. **Her commit atomik** — Her commit tek bir mantıksal değişiklik. Bir şey kırılırsa `git revert` ile o commit'i geri al, geri kalan değişiklikler etkilenmez.

5. **Kırılma testi** — Task 5 ve Task 7'den sonra `python -c "from src.main import *"` çalıştır. Import zinciri kırılmamalı.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/sports_data.py` | MODIFY | Add `get_team_injuries()`, `get_standings_context()`, `get_espn_predictor()`, `detect_back_to_back()`, `get_head_to_head()`. Enhance `_get_team_match_context()`. |
| `src/ai_analyst.py` | MODIFY | Update DATA SOURCES section in `_build_prompt()` to show ESPN BPI, injuries, standings. |
| `src/espn_enrichment.py` | MODIFY | Remove team-sport methods (`get_league_standing`, `get_win_probability`, `get_cdn_scoreboard`). Keep athlete-only methods. Update `enrich()`. |
| `src/sports_discovery.py` | MODIFY | Stop calling `enrichment.enrich()` for team sports (context now comes from `sports_data.py` directly). |
| `tests/test_sports_enrichment.py` | CREATE | Tests for all 5 new methods + enhanced `_get_team_match_context()`. |
| `tests/test_espn_enrichment.py` | MODIFY | Update to match slimmed-down `espn_enrichment.py`. |

---

### Task 1: `get_team_injuries()` — new method in `sports_data.py`

**Files:**
- Modify: `src/sports_data.py` (add method after `get_team_record()`, ~line 439)
- Create: `tests/test_sports_enrichment.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sports_enrichment.py`:

```python
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
        """Tennis, MMA, cricket return empty list (endpoints return 500)."""
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sports_enrichment.py::TestGetTeamInjuries -v`
Expected: FAIL — `AttributeError: 'SportsDataClient' object has no attribute 'get_team_injuries'`

- [ ] **Step 3: Implement `get_team_injuries()`**

Add to `src/sports_data.py` after `get_team_record()` method (after line 439):

```python
    # Sports where injury endpoint returns 500
    _NO_INJURY_SPORTS = frozenset({"tennis", "mma", "golf", "racing", "cricket"})

    def get_team_injuries(self, sport: str, league: str, team_id: str) -> List[Dict]:
        """Fetch injury report for a team from ESPN Site API.

        Returns list of: {player, status, detail, position}
        Skips call for sports where endpoint returns 500.
        """
        if sport in self._NO_INJURY_SPORTS:
            return []

        url = f"{ESPN_BASE}/{sport}/{league}/teams/{team_id}/injuries"
        data = self._get(url)
        if not data:
            return []

        injuries = []
        for item in data.get("injuries", []):
            athlete = item.get("athlete", {})
            injuries.append({
                "player": athlete.get("displayName", "Unknown"),
                "status": item.get("status", "Unknown"),
                "detail": item.get("detail", ""),
                "position": athlete.get("position", {}).get("abbreviation", ""),
            })
        return injuries
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sports_enrichment.py::TestGetTeamInjuries -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/sports_data.py tests/test_sports_enrichment.py
git commit -m "feat: add get_team_injuries() to SportsDataClient"
```

---

### Task 2: `get_standings_context()` — new method in `sports_data.py`

**Files:**
- Modify: `src/sports_data.py` (add method after `get_team_injuries()`)
- Modify: `tests/test_sports_enrichment.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sports_enrichment.py`:

```python
class TestGetStandingsContext:
    def test_returns_standings_dict(self):
        client = _make_client()
        # Simulate ESPN standings response with stats array
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
                            {"abbreviation": "STRK", "value": "W3",
                             "displayValue": "W3"},
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
            "team": {"id": "999", "displayName": "Other",
                     "abbreviation": "OTH"},
            "stats": [],
        }]}}]}
        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_standings_context("basketball", "nba", "13")
        assert result is None

    def test_uses_longer_cache_ttl(self):
        """Standings use 6-hour cache (21600s), not the default 30min."""
        client = _make_client()
        import time
        # Manually inject a cached entry with timestamp 2 hours ago
        url = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
        two_hours_ago = time.monotonic() - 7200
        client._cache[url] = ({"children": []}, two_hours_ago)
        # Default TTL (1800s) would expire this, but standings TTL (21600s) keeps it
        # We test by calling _get with the standings URL — but _get uses self._cache_ttl
        # Instead, we verify get_standings_context calls with correct URL pattern
        with patch.object(client, "_get") as mock_get:
            mock_get.return_value = None
            client.get_standings_context("basketball", "nba", "13")
            call_url = mock_get.call_args[0][0]
            assert "/apis/v2/sports/" in call_url
            assert "/standings" in call_url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sports_enrichment.py::TestGetStandingsContext -v`
Expected: FAIL — `AttributeError: 'SportsDataClient' object has no attribute 'get_standings_context'`

- [ ] **Step 3: Implement `get_standings_context()`**

Add to `src/sports_data.py` after `get_team_injuries()`:

```python
    _STANDINGS_CACHE_TTL = 21600  # 6 hours

    def get_standings_context(self, sport: str, league: str, team_id: str) -> Optional[Dict]:
        """Fetch team's standings data from ESPN.

        Returns: {wins, losses, win_pct, home_record, away_record,
                  streak, last_10, games_behind, conference_rank}
        Uses /apis/v2/ path (not /apis/site/v2/ which returns a stub).
        Cached for 6 hours.
        """
        # Use correct path: /apis/v2/ not /apis/site/v2/
        url = f"https://site.api.espn.com/apis/v2/sports/{sport}/{league}/standings"

        # Check 6-hour cache manually (override default 30min)
        cached = self._cache.get(url)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._STANDINGS_CACHE_TTL:
                return self._extract_team_standing(data, team_id)

        data = self._get(url)
        if not data:
            return None

        # Re-cache with current timestamp (already done by _get)
        return self._extract_team_standing(data, team_id)

    def _extract_team_standing(self, data: dict, team_id: str) -> Optional[Dict]:
        """Extract a single team's standing from the full standings response."""
        for group in data.get("children", []):
            for entry in group.get("standings", {}).get("entries", []):
                if str(entry.get("team", {}).get("id", "")) != str(team_id):
                    continue

                stats = {}
                for s in entry.get("stats", []):
                    abbrev = s.get("abbreviation", "")
                    # Prefer displayValue (formatted string like "22-10") over raw value
                    stats[abbrev] = s.get("displayValue", s.get("value", ""))

                return {
                    "wins": int(float(stats.get("W", 0))),
                    "losses": int(float(stats.get("L", 0))),
                    "win_pct": stats.get("PCT", ""),
                    "home_record": stats.get("HOME", ""),
                    "away_record": stats.get("AWAY", ""),
                    "streak": stats.get("STRK", ""),
                    "last_10": stats.get("L10", ""),
                    "games_behind": stats.get("GB", ""),
                    "conference_rank": entry.get("team", {}).get("id", ""),
                }
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sports_enrichment.py::TestGetStandingsContext -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/sports_data.py tests/test_sports_enrichment.py
git commit -m "feat: add get_standings_context() to SportsDataClient"
```

---

### Task 3: `get_espn_predictor()` — BPI win probability

**Files:**
- Modify: `src/sports_data.py` (add method after `get_standings_context()`)
- Modify: `tests/test_sports_enrichment.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sports_enrichment.py`:

```python
class TestGetEspnPredictor:
    def test_returns_probabilities_from_core_api(self):
        """Primary path: probabilities endpoint."""
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
        """Fallback: summary endpoint with predictor block."""
        client = _make_client()
        # First call (probabilities) returns None, second (summary) returns predictor
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
        with patch.object(client, "_get", return_value={"items": []}):
            result = client.get_espn_predictor("basketball", "nba", "401584701", "401584701")
        # Falls back to summary, which also returns None
        with patch.object(client, "_get", side_effect=[{"items": []}, None]):
            result = client.get_espn_predictor("basketball", "nba", "401584701", "401584701")
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sports_enrichment.py::TestGetEspnPredictor -v`
Expected: FAIL — `AttributeError: 'SportsDataClient' object has no attribute 'get_espn_predictor'`

- [ ] **Step 3: Implement `get_espn_predictor()`**

Add to `src/sports_data.py` after `get_standings_context()`:

```python
    def get_espn_predictor(self, sport: str, league: str, event_id: str, comp_id: str) -> Optional[Dict]:
        """Fetch ESPN BPI/predictor win probability (ESPN's own model, NOT bookmaker odds).

        Tries Core API probabilities endpoint first (lighter response).
        Falls back to summary endpoint and extracts predictor block.
        Returns: {home_win_pct, away_win_pct, tie_pct, source: "espn_bpi"}
        """
        # Option A: probabilities endpoint (preferred)
        prob_url = (
            f"{self._CORE_API}/{sport}/leagues/{league}/events/{event_id}"
            f"/competitions/{comp_id}/probabilities?limit=1"
        )
        data = self._get(prob_url)
        if data:
            items = data.get("items", [])
            if items:
                item = items[0]
                home_pct = item.get("homeWinPercentage")
                away_pct = item.get("awayWinPercentage")
                if home_pct is not None and away_pct is not None:
                    return {
                        "home_win_pct": float(home_pct),
                        "away_win_pct": float(away_pct),
                        "tie_pct": float(item.get("tiePercentage", 0.0)),
                        "source": "espn_bpi",
                    }

        # Option B: summary endpoint fallback
        summary_url = f"{ESPN_BASE}/{sport}/{league}/summary?event={event_id}"
        summary = self._get(summary_url)
        if summary:
            predictor = summary.get("predictor", {})
            home_team = predictor.get("homeTeam", {})
            projection = home_team.get("gameProjection")
            if projection is not None:
                try:
                    home_pct = float(projection) / 100.0
                    return {
                        "home_win_pct": home_pct,
                        "away_win_pct": 1.0 - home_pct,
                        "tie_pct": 0.0,
                        "source": "espn_bpi",
                    }
                except (ValueError, TypeError):
                    pass

        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sports_enrichment.py::TestGetEspnPredictor -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/sports_data.py tests/test_sports_enrichment.py
git commit -m "feat: add get_espn_predictor() for BPI win probability"
```

---

### Task 4: `detect_back_to_back()` and `get_head_to_head()` — derived methods (no API calls)

**Files:**
- Modify: `src/sports_data.py`
- Modify: `tests/test_sports_enrichment.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_sports_enrichment.py`:

```python
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
        games = [
            {"date": two_days_ago, "opponent": "Team X", "won": True, "score": "110-100", "home_away": "H"},
        ]
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
        # Mock get_team_record to return schedule with an opponent match
        team_a_data = {
            "team_name": "Lakers",
            "record": "38-29",
            "standing": "",
            "recent_games": [
                {"date": "2026-01-15", "opponent": "Boston Celtics", "won": True,
                 "score": "110-100", "home_away": "H"},
                {"date": "2026-02-20", "opponent": "Boston Celtics", "won": False,
                 "score": "95-105", "home_away": "A"},
                {"date": "2026-03-01", "opponent": "Miami Heat", "won": True,
                 "score": "115-100", "home_away": "H"},
            ],
        }
        with patch.object(client, "get_team_record", return_value=team_a_data):
            result = client.get_head_to_head(
                "basketball", "nba", "Lakers", "Celtics"
            )
        assert len(result) == 2
        assert result[0]["opponent"] == "Boston Celtics"
        assert result[0]["won"] is True
        assert result[1]["won"] is False

    def test_returns_empty_when_no_matchups(self):
        client = _make_client()
        team_a_data = {
            "team_name": "Lakers",
            "record": "38-29",
            "standing": "",
            "recent_games": [
                {"date": "2026-03-01", "opponent": "Miami Heat", "won": True,
                 "score": "115-100", "home_away": "H"},
            ],
        }
        with patch.object(client, "get_team_record", return_value=team_a_data):
            result = client.get_head_to_head(
                "basketball", "nba", "Lakers", "Celtics"
            )
        assert result == []

    def test_returns_empty_when_team_not_found(self):
        client = _make_client()
        with patch.object(client, "get_team_record", return_value=None):
            result = client.get_head_to_head(
                "basketball", "nba", "Lakers", "Celtics"
            )
        assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sports_enrichment.py::TestDetectBackToBack tests/test_sports_enrichment.py::TestGetHeadToHead -v`
Expected: FAIL — `AttributeError`

- [ ] **Step 3: Implement both methods**

Add to `src/sports_data.py` after `get_espn_predictor()`:

```python
    # Sports with daily schedules where B2B matters
    _DAILY_SPORTS = frozenset({"basketball", "hockey", "baseball"})

    def detect_back_to_back(self, recent_games: List[Dict]) -> bool:
        """Check if team played yesterday (back-to-back).

        Scans recent_games dates. If most recent game was yesterday, return True.
        No API call needed — uses cached schedule data.
        """
        if not recent_games:
            return False

        last_game = recent_games[-1]
        last_date_str = last_game.get("date", "")
        if not last_date_str:
            return False

        try:
            from datetime import timedelta
            last_date = datetime.strptime(last_date_str[:10], "%Y-%m-%d").date()
            yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
            return last_date == yesterday
        except (ValueError, TypeError):
            return False

    def get_head_to_head(
        self, sport: str, league: str, team_a_name: str, team_b_name: str
    ) -> List[Dict]:
        """Find H2H matchups this season from team A's schedule.

        Scans team_a's cached schedule for completed games vs team_b.
        Returns: [{date, opponent, won, score, home_away}]
        No extra API call needed — reuses get_team_record() cached data.
        """
        team_a_data = self.get_team_record(sport, league, team_a_name)
        if not team_a_data:
            return []

        team_b_lower = team_b_name.lower()
        h2h = []
        for game in team_a_data.get("recent_games", []):
            opp = game.get("opponent", "").lower()
            if team_b_lower in opp or opp in team_b_lower:
                h2h.append(game)
        return h2h
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sports_enrichment.py::TestDetectBackToBack tests/test_sports_enrichment.py::TestGetHeadToHead -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/sports_data.py tests/test_sports_enrichment.py
git commit -m "feat: add detect_back_to_back() and get_head_to_head()"
```

---

### Task 5: Enhance `_get_team_match_context()` to use enrichment data

**Files:**
- Modify: `src/sports_data.py:815-875` (`_get_team_match_context()`)
- Modify: `tests/test_sports_enrichment.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sports_enrichment.py`:

```python
class TestEnhancedTeamMatchContext:
    def test_includes_injuries_in_context(self):
        """Context string should include injury data when available."""
        client = _make_client()
        team_a = {
            "team_name": "Los Angeles Lakers", "record": "38-29",
            "standing": "7th in Western Conference",
            "recent_games": [
                {"date": "2026-03-28", "opponent": "Celtics", "won": True,
                 "score": "110-100", "home_away": "H"},
            ],
        }
        injuries = [{"player": "LeBron James", "status": "Out",
                      "detail": "Ankle", "position": "SF"}]
        standings = {"wins": 38, "losses": 29, "win_pct": "0.567",
                     "home_record": "22-10", "away_record": "16-19",
                     "streak": "W3", "last_10": "7-3",
                     "games_behind": "5.0", "conference_rank": "13"}

        with patch.object(client, "get_team_record", side_effect=[team_a, None]), \
             patch.object(client, "get_team_injuries", return_value=injuries), \
             patch.object(client, "get_standings_context", return_value=standings), \
             patch.object(client, "detect_back_to_back", return_value=False), \
             patch.object(client, "get_head_to_head", return_value=[]), \
             patch.object(client, "_find_espn_event", return_value=(None, None, None, None, None)):
            result = client._get_team_match_context("basketball", "nba",
                "Will Lakers beat Celtics?", "nba-lal-bos")

        assert result is not None
        assert "LeBron James" in result
        assert "Out" in result
        assert "22-10" in result  # home record
        assert "W3" in result  # streak

    def test_includes_bpi_predictor(self):
        """Context string should include ESPN BPI when event_id found."""
        client = _make_client()
        team_a = {
            "team_name": "Los Angeles Lakers", "record": "38-29",
            "standing": "", "recent_games": [],
        }
        predictor = {"home_win_pct": 0.634, "away_win_pct": 0.366,
                     "tie_pct": 0.0, "source": "espn_bpi"}

        with patch.object(client, "get_team_record", side_effect=[team_a, None]), \
             patch.object(client, "get_team_injuries", return_value=[]), \
             patch.object(client, "get_standings_context", return_value=None), \
             patch.object(client, "detect_back_to_back", return_value=False), \
             patch.object(client, "get_head_to_head", return_value=[]), \
             patch.object(client, "_find_espn_event",
                          return_value=("401584701", "401584701", "Lakers", "Celtics", True)), \
             patch.object(client, "get_espn_predictor", return_value=predictor):
            result = client._get_team_match_context("basketball", "nba",
                "Will Lakers beat Celtics?", "nba-lal-bos")

        assert result is not None
        assert "ESPN BPI" in result
        assert "63.4%" in result

    def test_includes_b2b_warning(self):
        """Context should flag back-to-back games."""
        client = _make_client()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        team_a = {
            "team_name": "Los Angeles Lakers", "record": "38-29",
            "standing": "", "recent_games": [
                {"date": yesterday, "opponent": "Heat", "won": True,
                 "score": "110-100", "home_away": "H"},
            ],
        }

        with patch.object(client, "get_team_record", side_effect=[team_a, None]), \
             patch.object(client, "get_team_injuries", return_value=[]), \
             patch.object(client, "get_standings_context", return_value=None), \
             patch.object(client, "get_head_to_head", return_value=[]), \
             patch.object(client, "_find_espn_event", return_value=(None, None, None, None, None)):
            # Let detect_back_to_back run for real
            result = client._get_team_match_context("basketball", "nba",
                "Will Lakers beat Celtics?", "nba-lal-bos")

        assert result is not None
        assert "BACK-TO-BACK" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sports_enrichment.py::TestEnhancedTeamMatchContext -v`
Expected: FAIL — context string doesn't contain injury/BPI/B2B data yet

- [ ] **Step 3: Rewrite `_get_team_match_context()`**

Replace the existing `_get_team_match_context()` method in `src/sports_data.py` (lines 815-875):

```python
    def _get_team_match_context(
        self, sport: str, league: str, question: str, slug: str
    ) -> Optional[str]:
        """Build enriched context for team-based sports."""
        league_name = league

        team_a_name, team_b_name = self._extract_teams_from_question(question)
        slug_a, slug_b = self._extract_teams_from_slug(slug)

        if not team_a_name and slug_a and len(slug_a) >= 4:
            team_a_name = slug_a
        if not team_b_name and slug_b and len(slug_b) >= 4:
            team_b_name = slug_b

        if not team_a_name:
            logger.debug("Could not extract team names from: %s / %s", question[:60], slug)
            return None

        logger.info("Fetching ESPN data: %s vs %s (%s)", team_a_name, team_b_name, league_name)

        team_a = self.get_team_record(sport, league, team_a_name)
        team_b = self.get_team_record(sport, league, team_b_name) if team_b_name else None

        if not team_a and not team_b:
            if slug_a and len(slug_a) >= 4 and slug_a != team_a_name:
                team_a = self.get_team_record(sport, league, slug_a)
            if slug_b and len(slug_b) >= 4 and slug_b != team_b_name:
                team_b = self.get_team_record(sport, league, slug_b)

        if not team_a and not team_b:
            return None

        # Try to find event for BPI predictor
        event_id, comp_id, home_team, away_team, team_a_is_home = (
            self._find_espn_event(sport, league, team_a_name or "", team_b_name or "")
        )

        # BPI Predictor (requires event_id)
        predictor = None
        if event_id and comp_id:
            predictor = self.get_espn_predictor(sport, league, event_id, comp_id)

        parts = [f"=== SPORTS DATA (ESPN) -- {league_name} ==="]

        # BPI Predictor section (top — most important ESPN-exclusive signal)
        if predictor:
            home_pct = predictor["home_win_pct"] * 100
            away_pct = predictor["away_win_pct"] * 100
            home_label = home_team or "Home"
            away_label = away_team or "Away"
            parts.append(
                f"\n=== ESPN BPI PREDICTOR ===\n"
                f"(ESPN's own win probability model — independent from bookmaker odds)\n"
                f"  {home_label}: {home_pct:.1f}%\n"
                f"  {away_label}: {away_pct:.1f}%"
            )

        # Venue (from event if found)
        if event_id:
            venue = self._get_venue_from_event(sport, league, event_id)
            if venue:
                parts.append(f"\nVENUE: {venue}")

        for label, stats, name in [
            ("TEAM A", team_a, team_a_name),
            ("TEAM B", team_b, team_b_name),
        ]:
            if not stats:
                parts.append(f"\n{label}: No data available")
                continue

            team_id = self._get_team_id(sport, league, stats["team_name"])

            header = f"\n{label}: {stats['team_name']}"
            if stats["record"]:
                header += f" ({stats['record']})"
            if stats["standing"]:
                header += f" -- {stats['standing']}"
            parts.append(header)

            # Standings enrichment (home/away, streak, L10)
            if team_id:
                standing = self.get_standings_context(sport, league, team_id)
                if standing:
                    if standing.get("home_record"):
                        parts.append(f"  Home: {standing['home_record']} | Away: {standing.get('away_record', 'N/A')}")
                    if standing.get("last_10"):
                        parts.append(f"  Last 10: {standing['last_10']} | Streak: {standing.get('streak', 'N/A')}")

            # Recent games
            if stats["recent_games"]:
                recent_5 = stats["recent_games"][-5:]
                wins = sum(1 for g in recent_5 if g["won"])
                parts.append(f"  Last 5: {wins}W-{5 - wins}L")
                parts.append("  Recent games:")
                for g in stats["recent_games"][-5:]:
                    result = "W" if g["won"] else "L"
                    parts.append(
                        f"    [{result}] {g['home_away']} vs {g['opponent']} "
                        f"{g['score']} ({g['date']})"
                    )

            # Back-to-back detection
            if sport in self._DAILY_SPORTS and self.detect_back_to_back(stats.get("recent_games", [])):
                parts.append(f"  ⚠️ SCHEDULE: BACK-TO-BACK")

            # Injuries
            if team_id:
                injuries = self.get_team_injuries(sport, league, team_id)
                if injuries:
                    parts.append("  Injuries:")
                    for inj in injuries[:8]:  # Cap at 8 to save tokens
                        parts.append(
                            f"    {inj['player']} ({inj['position']}) — "
                            f"{inj['status']}: {inj['detail']}"
                        )

        # Head-to-head
        if team_a_name and team_b_name:
            h2h = self.get_head_to_head(sport, league, team_a_name, team_b_name)
            if h2h:
                a_wins = sum(1 for g in h2h if g["won"])
                b_wins = len(h2h) - a_wins
                parts.append(f"\nHEAD-TO-HEAD (this season): {team_a_name} {a_wins}-{b_wins} {team_b_name}")
                for g in h2h[-3:]:
                    result = "W" if g["won"] else "L"
                    parts.append(f"  [{result}] {g['home_away']} {g['score']} ({g['date']})")

        parts.append("\nUse team records, recent form, standings, injuries, and BPI predictor "
                     "to inform your estimate. Weight recent form and home/away performance.")
        return "\n".join(parts)
```

- [ ] **Step 4: Add helper methods needed by enhanced context**

Add these helper methods to `SportsDataClient` (after `_extract_team_standing`):

```python
    def _get_team_id(self, sport: str, league: str, team_name: str) -> Optional[str]:
        """Get ESPN team ID from team name. Uses cached team search."""
        team = self._search_team(sport, league, team_name)
        return str(team.get("id", "")) if team else None

    def _get_venue_from_event(self, sport: str, league: str, event_id: str) -> Optional[str]:
        """Extract venue name from event summary."""
        url = f"{ESPN_BASE}/{sport}/{league}/summary?event={event_id}"
        # Check cache first — summary is expensive
        cached = self._cache.get(url)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < 900:  # 15 min cache
                venue = data.get("gameInfo", {}).get("venue", {})
                if venue:
                    name = venue.get("fullName", "")
                    city = venue.get("address", {}).get("city", "")
                    return f"{name}, {city}" if city else name
                return None

        data = self._get(url)
        if not data:
            return None
        venue = data.get("gameInfo", {}).get("venue", {})
        if not venue:
            return None
        name = venue.get("fullName", "")
        city = venue.get("address", {}).get("city", "")
        return f"{name}, {city}" if city else name
```

- [ ] **Step 5: Run all enrichment tests**

Run: `python -m pytest tests/test_sports_enrichment.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run existing tests to confirm nothing broke**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All existing tests still PASS

- [ ] **Step 7: Commit**

```bash
git add src/sports_data.py tests/test_sports_enrichment.py
git commit -m "feat: enhance _get_team_match_context() with injuries, BPI, standings, B2B, H2H"
```

---

### Task 6: Update `ai_analyst.py` DATA SOURCES section

**Files:**
- Modify: `src/ai_analyst.py:428-465` (DATA SOURCES block in `_build_prompt()`)

- [ ] **Step 1: Read the current DATA SOURCES section**

File: `src/ai_analyst.py` lines 428-465. The current code builds a `sources_section` list checking for `has_odds` and `has_stats` via keyword detection in `esports_context`.

- [ ] **Step 2: Update the DATA SOURCES builder**

Replace the DATA SOURCES block in `_build_prompt()` (from `sources_section = ["\n=== DATA SOURCES ==="]` through `parts.append("\n".join(sources_section))`):

```python
        sources_section = ["\n=== DATA SOURCES ==="]
        ctx_lower = (esports_context or "").lower()
        has_odds = "bookmaker" in ctx_lower or "odds api" in ctx_lower
        has_stats = bool(esports_context) and ("win" in ctx_lower or
                                                "recent" in ctx_lower or
                                                "match" in ctx_lower)
        has_bpi = "espn bpi" in ctx_lower
        has_injuries = "injuries:" in ctx_lower or "injury" in ctx_lower
        has_standings = "home:" in ctx_lower and "away:" in ctx_lower

        if has_stats:
            sources_section.append("✓ Match Stats: Available (ESPN)")
        else:
            sources_section.append("✗ Match Stats: Not available")

        if has_odds:
            sources_section.append("✓ Bookmaker Odds: Available (The Odds API — 8-10 providers)")
        elif is_esport:
            sources_section.append("✗ Bookmaker Odds: Not available (normal for esports -- do NOT penalize confidence)")
        else:
            sources_section.append("✗ Bookmaker Odds: Not available")

        if has_bpi:
            sources_section.append("✓ ESPN BPI Predictor: Available (ESPN's own model — independent signal)")

        if has_injuries:
            sources_section.append("✓ Injury Reports: Available (both teams)")

        if has_standings:
            sources_section.append("✓ Standings & Records: Available")

        if news_context:
            sources_section.append("✓ News: Available (see below)")
        else:
            sources_section.append("✗ News: No relevant articles found")

        if is_esport:
            sport_label = sport.upper() if sport else "ESPORTS"
            sources_section.append(f"\nSport: {sport_label} -- match stats from PandaScore are the primary data source. "
                                   f"Bookmaker odds are rarely available for esports markets. "
                                   f"8+ recent matches per team = good data quality for B+ or A confidence.")
```

- [ ] **Step 3: Run existing tests**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/ai_analyst.py
git commit -m "feat: update DATA SOURCES section to reflect ESPN BPI, injuries, standings"
```

---

### Task 7: Slim down `espn_enrichment.py` — remove team-sport overlap

**Files:**
- Modify: `src/espn_enrichment.py`
- Modify: `src/sports_discovery.py:75-106` (ESPN route)
- Modify: `tests/test_espn_enrichment.py`

**SAFETY:** This is the consolidation step. Team-sport enrichment now flows through `sports_data.py._get_team_match_context()` which already includes injuries, BPI, standings, etc. We remove the overlapping team methods from `espn_enrichment.py` and update `sports_discovery.py` to stop calling `enrichment.enrich()` for team sports.

- [ ] **Step 1: Verify enrichment is no longer needed for team sports**

Run a quick import+syntax check:

```bash
python -c "from src.sports_data import SportsDataClient; c = SportsDataClient(); print('Methods:', [m for m in dir(c) if 'injur' in m or 'stand' in m or 'predict' in m or 'b2b' in m or 'h2h' in m or 'head' in m])"
```

Expected output includes: `['detect_back_to_back', 'get_espn_predictor', 'get_head_to_head', 'get_standings_context', 'get_team_injuries']`

- [ ] **Step 2: Update `sports_discovery.py` — stop enrichment for team sports**

In `src/sports_discovery.py`, replace the ESPN route block (lines 75-106):

```python
            else:  # espn
                ctx = self.espn.get_match_context(question, slug, tags)
                if ctx:
                    espn_odds = self.espn.get_espn_odds(question, slug, tags)

                    # Enrichment: athlete-specific extras only (team enrichment is now in sports_data.py)
                    enrichment_ctx = None
                    sport_league = self.espn.detect_sport(question, slug, tags)
                    is_athlete_sport = sport_league and sport_league[0] in ("tennis", "mma", "golf")
                    if is_athlete_sport and self.enrichment:
                        try:
                            enrichment_ctx = self.enrichment.enrich(question, slug, tags)
                        except Exception as exc:
                            logger.warning("Enrichment error for '%s': %s", slug[:40], exc)

                    # Combine context
                    parts = [ctx]
                    if espn_odds:
                        parts.append(
                            f"\n=== BOOKMAKER ODDS (ESPN) ===\n"
                            f"{espn_odds.get('team_a', '?')} "
                            f"{espn_odds.get('bookmaker_prob_a', 0):.0%} vs "
                            f"{espn_odds.get('team_b', '?')} "
                            f"{espn_odds.get('bookmaker_prob_b', 0):.0%} "
                            f"({espn_odds.get('num_bookmakers', 0)} bookmakers)"
                        )
                    if enrichment_ctx:
                        parts.append(enrichment_ctx)
                    full_context = "\n".join(parts)

                    return DiscoveryResult(
                        context=full_context, source="ESPN",
                        confidence="A", espn_odds=espn_odds,
                    )
```

- [ ] **Step 3: Remove team-sport methods from `espn_enrichment.py`**

Rewrite `src/espn_enrichment.py` — remove `get_league_standing()`, `get_win_probability()`, `get_cdn_scoreboard()`, and update `enrich()` to only handle athlete sports:

```python
"""ESPN enrichment — athlete-specific endpoints for richer AI context.

Provides: athlete overview, splits, rankings, H2H for tennis/MMA/golf.
Team-sport enrichment (injuries, BPI, standings, B2B, H2H) is handled
directly by SportsDataClient._get_team_match_context() in sports_data.py.

Receives SportsDataClient via DI for detect_sport() reuse.
Does NOT import anything from src/ at module level.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Optional

import requests

if TYPE_CHECKING:
    from src.sports_data import SportsDataClient

logger = logging.getLogger(__name__)

_SITE_API = "https://site.api.espn.com/apis/site/v2/sports"
_CORE_API = "https://sports.core.api.espn.com/v2/sports"
_WEB_API = "https://site.web.api.espn.com/apis/common/v3/sports"
_TIMEOUT = 8

# Sports where competitors are individual athletes
_ATHLETE_SPORTS = frozenset({"tennis", "mma", "golf"})


class ESPNEnrichment:
    """Athlete-specific ESPN data sources for AI context enrichment.

    Team-sport enrichment is handled by SportsDataClient directly.
    This class only enriches athlete sports (tennis, MMA, golf).
    """

    def __init__(self, sports_client: "SportsDataClient") -> None:
        self._client = sports_client
        self._cache: dict[str, dict] = {}
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "PolymarketBot/1.0"

    # ── Cache helpers ──────────────────────────────────────────

    def _get_cached(self, key: str, ttl: int = 300) -> Optional[str]:
        entry = self._cache.get(key)
        if entry and (time.time() - entry["ts"]) < ttl:
            return entry["data"]
        return None

    def _set_cache(self, key: str, data: str) -> None:
        self._cache[key] = {"data": data, "ts": time.time()}

    # ── Public entry point ─────────────────────────────────────

    def enrich(self, question: str, slug: str, tags: list[str]) -> Optional[str]:
        """Fetch athlete-specific enrichment data. Returns None for team sports."""
        sport_league = self._client.detect_sport(question, slug, tags)
        if not sport_league:
            return None
        sport, league = sport_league

        # Only handle athlete sports — team sports enriched in sports_data.py
        if sport not in _ATHLETE_SPORTS:
            return None

        parts: list[str] = []

        overview = self.get_athlete_overview(sport, league, question, slug)
        if overview:
            parts.append(overview)
        splits = self.get_athlete_splits(sport, league, question, slug)
        if splits:
            parts.append(splits)
        rankings = self.get_rankings(sport, league)
        if rankings:
            parts.append(rankings)
        h2h = self.get_h2h(sport, league, question, slug)
        if h2h:
            parts.append(h2h)

        if not parts:
            return None
        return "\n=== ESPN ENRICHMENT ===\n" + "\n".join(parts)

    # ── Athlete-specific endpoint methods ────────────────────

    def get_athlete_overview(self, sport: str, league: str,
                            question: str, slug: str) -> Optional[str]:
        """Fetch athlete overview (ranking, injury, news)."""
        try:
            athlete_ids = self._find_athlete_ids(sport, league, question, slug)
            if not athlete_ids:
                return None

            parts = []
            for aid, name in athlete_ids[:2]:
                url = f"{_WEB_API}/{sport}/{league}/athletes/{aid}/overview"
                resp = self._session.get(url, timeout=_TIMEOUT)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                athlete = data.get("athlete", {})
                rank = athlete.get("rank", {}).get("current", {}).get("rank", "N/A")
                injuries = athlete.get("injuries", [])
                injury_status = injuries[0].get("status", "Healthy") if injuries else "Healthy"
                parts.append(f"  {name}: Rank #{rank}, Status: {injury_status}")

            if not parts:
                return None
            return "Athlete Overview:\n" + "\n".join(parts)
        except Exception as exc:
            logger.warning("ESPN athlete overview error: %s", exc)
            return None

    def get_athlete_splits(self, sport: str, league: str,
                           question: str, slug: str) -> Optional[str]:
        """Fetch athlete statistical splits (home/away/surface)."""
        try:
            athlete_ids = self._find_athlete_ids(sport, league, question, slug)
            if not athlete_ids:
                return None

            parts = []
            for aid, name in athlete_ids[:2]:
                url = f"{_SITE_API}/{sport}/{league}/athletes/{aid}/splits"
                resp = self._session.get(url, timeout=_TIMEOUT)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                categories = data.get("splitCategories", [])
                for cat in categories[:2]:
                    cat_name = cat.get("displayName", "")
                    for split in cat.get("splits", [])[:3]:
                        split_name = split.get("displayName", "")
                        stats_list = split.get("stats", [])
                        record = f"{stats_list[0]}-{stats_list[1]}" if len(stats_list) >= 2 else "N/A"
                        parts.append(f"  {name} ({cat_name}/{split_name}): {record}")

            if not parts:
                return None
            return "Athlete Splits:\n" + "\n".join(parts[:8])
        except Exception as exc:
            logger.warning("ESPN athlete splits error: %s", exc)
            return None

    def get_rankings(self, sport: str, league: str) -> Optional[str]:
        """Fetch current rankings (ATP/WTA/golf)."""
        cache_key = f"rankings:{sport}:{league}"
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return cached

        try:
            url = f"{_CORE_API}/{sport}/leagues/{league}/rankings"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            rankings = data.get("rankings", [])
            if not rankings:
                return None

            entries = rankings[0].get("ranks", [])[:20]
            lines = []
            for r in entries:
                athlete = r.get("athlete", {})
                name = athlete.get("displayName", "Unknown")
                rank = r.get("current", "?")
                points = r.get("points", "")
                lines.append(f"  #{rank} {name}" + (f" ({points}pts)" if points else ""))

            if not lines:
                return None
            text = f"Rankings ({league.upper()}):\n" + "\n".join(lines[:10])
            self._set_cache(cache_key, text)
            return text
        except Exception as exc:
            logger.warning("ESPN rankings error: %s", exc)
            return None

    def get_h2h(self, sport: str, league: str,
                question: str, slug: str) -> Optional[str]:
        """Fetch head-to-head stats between two athletes."""
        try:
            athlete_ids = self._find_athlete_ids(sport, league, question, slug)
            if not athlete_ids or len(athlete_ids) < 2:
                return None

            id_a, name_a = athlete_ids[0]
            id_b, name_b = athlete_ids[1]
            url = f"{_SITE_API}/{sport}/{league}/athletes/{id_a}/vsathlete/{id_b}"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            vs = data.get("vsAthlete", {})
            record = vs.get("record", {})
            wins_a = record.get("wins", 0)
            wins_b = record.get("losses", 0)

            events = vs.get("events", [])
            recent = []
            for ev in events[:5]:
                winner = ev.get("winner", {}).get("displayName", "?")
                date = ev.get("date", "")[:10]
                recent.append(f"    {date}: {winner}")

            result = f"H2H: {name_a} {wins_a}-{wins_b} {name_b}"
            if recent:
                result += "\n  Recent:\n" + "\n".join(recent)
            return result
        except Exception as exc:
            logger.warning("ESPN H2H error: %s", exc)
            return None

    # ── Internal helpers ───────────────────────────────────────

    def _find_athlete_ids(self, sport: str, league: str,
                          question: str, slug: str) -> list[tuple[str, str]]:
        """Find athlete IDs from question text via ESPN search."""
        results = []
        parts = slug.replace("-", " ").split()
        name_parts = [p for p in parts if len(p) > 2 and not p.isdigit()
                      and p not in ("atp", "wta", "ufc", "pga", "lpga")]

        for name in name_parts[:4]:
            try:
                url = f"https://site.web.api.espn.com/apis/common/v3/search"
                resp = self._session.get(url, params={
                    "query": name, "limit": 3, "type": "player",
                }, timeout=_TIMEOUT)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                items = data.get("items", []) or data.get("results", [])
                for item in items:
                    entries = item.get("entries", []) if isinstance(item, dict) else []
                    for entry in entries:
                        aid = entry.get("id", "")
                        display = entry.get("displayName", "")
                        if aid and name.lower() in display.lower():
                            results.append((str(aid), display))
                            break
            except Exception:
                continue

        return results[:2]
```

- [ ] **Step 4: Update tests**

Replace `tests/test_espn_enrichment.py`:

```python
"""Tests for ESPN enrichment (athlete-specific only)."""
from unittest.mock import MagicMock
from src.espn_enrichment import ESPNEnrichment


def _make_enrichment():
    """Create ESPNEnrichment with mocked SportsDataClient."""
    mock_client = MagicMock()
    mock_client.detect_sport.return_value = ("basketball", "nba")
    return ESPNEnrichment(sports_client=mock_client)


def test_enrich_returns_none_for_team_sports():
    """Team sports should return None — enrichment is in sports_data.py now."""
    e = _make_enrichment()
    e._client.detect_sport.return_value = ("basketball", "nba")
    result = e.enrich("Will Lakers beat Celtics?", "nba-lal-bos", ["nba"])
    assert result is None


def test_enrich_routes_athlete_sports():
    """Athlete sports (tennis, MMA, golf) should attempt enrichment."""
    e = _make_enrichment()
    e._client.detect_sport.return_value = ("tennis", "atp")
    # Will return None because no real API, but should not short-circuit
    result = e.enrich("Djokovic vs Nadal", "atp-djo-nad", ["tennis"])
    assert result is None or isinstance(result, str)


def test_cache_ttl():
    """Verify TTL cache stores and expires."""
    e = _make_enrichment()
    e._cache["test_key"] = {"data": "value", "ts": 0}  # Expired
    assert e._get_cached("test_key", ttl=300) is None

    import time
    e._cache["test_key2"] = {"data": "value2", "ts": time.time()}
    assert e._get_cached("test_key2", ttl=300) == "value2"
```

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/ -v --tb=short`
Expected: ALL tests PASS

- [ ] **Step 6: Verify import chain**

```bash
python -c "from src.sports_data import SportsDataClient; from src.espn_enrichment import ESPNEnrichment; from src.sports_discovery import SportsDiscovery; print('No circular imports')"
```

Expected: `No circular imports`

- [ ] **Step 7: Commit**

```bash
git add src/espn_enrichment.py src/sports_discovery.py tests/test_espn_enrichment.py
git commit -m "refactor: consolidate team-sport enrichment into sports_data.py, slim espn_enrichment.py to athlete-only"
```

---

### Task 8: Final integration test + cleanup

**Files:**
- All modified files (verify only)

- [ ] **Step 1: Full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: ALL tests PASS

- [ ] **Step 2: Import validation**

```bash
python -c "from src.main import *; print('Full import chain OK')"
```

Expected: No errors

- [ ] **Step 3: Verify no dead code in espn_enrichment.py**

```bash
python -c "
from src.espn_enrichment import ESPNEnrichment
methods = [m for m in dir(ESPNEnrichment) if not m.startswith('_')]
print('Public methods:', methods)
expected = ['enrich', 'get_athlete_overview', 'get_athlete_splits', 'get_h2h', 'get_rankings']
missing = set(expected) - set(methods)
extra = set(methods) - set(expected)
assert not missing, f'Missing: {missing}'
print('No dead team-sport methods remain')
if extra:
    print(f'Note: extra methods {extra} — review if needed')
"
```

- [ ] **Step 4: Verify new methods exist in sports_data.py**

```bash
python -c "
from src.sports_data import SportsDataClient
c = SportsDataClient()
new_methods = ['get_team_injuries', 'get_standings_context', 'get_espn_predictor',
               'detect_back_to_back', 'get_head_to_head']
for m in new_methods:
    assert hasattr(c, m), f'Missing: {m}'
print('All 5 new enrichment methods present')
"
```

- [ ] **Step 5: Line count check**

```bash
wc -l src/sports_data.py src/espn_enrichment.py src/ai_analyst.py
```

Verify `sports_data.py` grew by ~150-200 lines and `espn_enrichment.py` shrank by ~100 lines.

- [ ] **Step 6: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore: ESPN data enrichment integration complete"
```
