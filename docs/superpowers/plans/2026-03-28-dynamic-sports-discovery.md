# Dynamic Sports Discovery Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all hardcoded slug/keyword→league mappings with dynamic API-based discovery, remove redundant data sources, clean up bridge system.

**Architecture:** New `SportsDiscovery` class routes markets to ESPN/PandaScore/CricketData based on lightweight categorization. Each data client uses its API's search/list endpoints instead of hardcoded mappings. Odds API uses `/sports` + `/events` endpoints (FREE) for dynamic sport key resolution.

**Tech Stack:** Python 3.11+, requests, Pydantic, pytest

---

### Task 1: Fix `_check_live_dip()` Crash Bug

**Files:**
- Modify: `src/agent.py:928`

This is a standalone bug fix that prevents the bot from crashing on Cycle #2. Must be done first.

- [ ] **Step 1: Fix the clamp**

In `src/agent.py`, find line 928 inside `_check_live_dip()`:

```python
# BEFORE (line 928):
                ai_probability=pre_match,

# AFTER:
                ai_probability=max(0.01, min(0.99, pre_match)),
```

- [ ] **Step 2: Run existing tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -x -q`
Expected: All existing tests pass (this is a runtime fix, no test coverage exists for this path yet).

- [ ] **Step 3: Commit**

```bash
git add src/agent.py
git commit -m "fix: clamp ai_probability in _check_live_dip to [0.01, 0.99]"
```

---

### Task 2: Create `sports_discovery.py` — Unified Discovery Layer

**Files:**
- Create: `src/sports_discovery.py`
- Create: `tests/test_sports_discovery.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for SportsDiscovery routing and resolution."""
from unittest.mock import MagicMock
import pytest

from src.sports_discovery import SportsDiscovery, DiscoveryResult


def _make_discovery(espn_ctx=None, panda_ctx=None, cricket_ctx=None):
    espn = MagicMock()
    espn.get_match_context = MagicMock(return_value=espn_ctx)
    espn.search_team = MagicMock(return_value=("soccer", "eng.3") if espn_ctx else None)

    panda = MagicMock()
    panda.available = True
    panda.get_match_context = MagicMock(return_value=panda_ctx)

    cricket = MagicMock()
    cricket.available = True
    cricket.get_match_context = MagicMock(return_value=cricket_ctx)

    odds = MagicMock()
    odds.available = False

    return SportsDiscovery(espn=espn, pandascore=panda, cricket=cricket, odds_api=odds)


def test_route_esports_by_tag():
    d = _make_discovery()
    route = d._detect_route("Fnatic vs G2", "cs2-fnatic-g2", ["esports", "cs2"])
    assert route == "esports"


def test_route_esports_by_slug():
    d = _make_discovery()
    route = d._detect_route("Fnatic vs G2", "cs2-fnatic-g2", [])
    assert route == "esports"


def test_route_cricket_by_tag():
    d = _make_discovery()
    route = d._detect_route("India vs Pakistan", "ipl-ind-pak", ["cricket"])
    assert route == "cricket"


def test_route_cricket_by_slug():
    d = _make_discovery()
    route = d._detect_route("India vs Pakistan", "ipl-ind-pak", [])
    assert route == "cricket"


def test_route_default_espn():
    d = _make_discovery()
    route = d._detect_route("Lakers vs Celtics", "nba-lakers-celtics", ["sports"])
    assert route == "espn"


def test_resolve_espn_returns_context():
    d = _make_discovery(espn_ctx="=== ESPN DATA ===")
    result = d.resolve("Lakers vs Celtics", "nba-lakers-celtics", ["sports"])
    assert result is not None
    assert result.context == "=== ESPN DATA ==="
    assert result.source == "ESPN"


def test_resolve_cricket_returns_context():
    d = _make_discovery(cricket_ctx="=== CRICKET DATA ===")
    result = d.resolve("India vs Pakistan", "ipl-ind-pak", ["cricket"])
    assert result is not None
    assert result.context == "=== CRICKET DATA ==="
    assert result.source == "CricketData"


def test_resolve_returns_none_when_no_data():
    d = _make_discovery()  # all return None
    result = d.resolve("Unknown vs Team", "xyz-unk-team", ["sports"])
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_sports_discovery.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.sports_discovery'`

- [ ] **Step 3: Write the implementation**

Create `src/sports_discovery.py`:

```python
"""Unified sports data discovery — routes markets to the correct API dynamically.

Replaces the old 5-tier cascade (Bridge→ESPN→football-data→CricketData→TheSportsDB)
with a simple 3-way router: esports → PandaScore, cricket → CricketData, else → ESPN.
No hardcoded slug/keyword mappings — each API uses its own search endpoints.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.sports_data import SportsDataClient
    from src.esports_data import EsportsDataClient
    from src.cricket_data import CricketDataClient
    from src.odds_api import OddsAPIClient

logger = logging.getLogger(__name__)

# Lightweight route detection — categorization, not discovery
_ESPORTS_SLUGS = frozenset({"cs2", "csgo", "lol", "dota2", "valorant"})
_CRICKET_SLUGS = frozenset({"ipl", "psl", "t20", "crint", "cricpakt20cup", "criclcl"})


@dataclass
class DiscoveryResult:
    """Result from sports data discovery."""
    context: str      # Sports context string for AI analyst
    source: str       # "ESPN", "PandaScore", "CricketData"
    confidence: str   # Always "A" — all sources are reliable


class SportsDiscovery:
    """Single entry point for all sports data resolution.

    Thin orchestrator — routes markets to the correct API based on
    lightweight categorization (esports/cricket/everything else).
    """

    def __init__(
        self,
        espn: "SportsDataClient",
        pandascore: "EsportsDataClient",
        cricket: "CricketDataClient",
        odds_api: "OddsAPIClient",
    ) -> None:
        self.espn = espn
        self.pandascore = pandascore
        self.cricket = cricket
        self.odds_api = odds_api

    def resolve(
        self, question: str, slug: str, tags: list[str],
    ) -> Optional[DiscoveryResult]:
        """Route market to correct API, return context or None."""
        route = self._detect_route(question, slug, tags)

        try:
            if route == "esports":
                ctx = self.pandascore.get_match_context(question, tags)
                if ctx:
                    return DiscoveryResult(context=ctx, source="PandaScore", confidence="A")

            elif route == "cricket":
                ctx = self.cricket.get_match_context(question, slug, tags)
                if ctx:
                    return DiscoveryResult(context=ctx, source="CricketData", confidence="A")

            else:  # espn
                ctx = self.espn.get_match_context(question, slug, tags)
                if ctx:
                    return DiscoveryResult(context=ctx, source="ESPN", confidence="A")

        except Exception as exc:
            logger.warning("Discovery error (%s) for '%s': %s", route, slug[:40], exc)

        return None

    def _detect_route(self, question: str, slug: str, tags: list[str]) -> str:
        """Lightweight categorization: 'esports', 'cricket', or 'espn'."""
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        tags_lower = {t.lower() for t in tags}

        # Esports: tag or slug prefix
        if "esports" in tags_lower or slug_prefix in _ESPORTS_SLUGS:
            return "esports"
        if any(game in tags_lower for game in _ESPORTS_SLUGS):
            return "esports"

        # Cricket: tag, slug, or question keyword
        if "cricket" in tags_lower or slug_prefix in _CRICKET_SLUGS:
            return "cricket"
        if "cricket" in question.lower():
            return "cricket"

        # Everything else → ESPN
        return "espn"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_sports_discovery.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sports_discovery.py tests/test_sports_discovery.py
git commit -m "feat: add SportsDiscovery unified routing layer"
```

---

### Task 3: Refactor ESPN — Remove Hardcoded Mappings, Add Search

**Files:**
- Modify: `src/sports_data.py`

The ESPN client currently has 68 + 43 = 111 hardcoded entries. We remove them and add a `search_team()` method that uses ESPN's free search API. The existing `get_match_context()` still needs `detect_sport()` internally (for when sport/league is already known from the question), but we make the hardcoded dicts empty and rely on search as primary discovery.

- [ ] **Step 1: Remove hardcoded `_SPORT_LEAGUES` and `_QUESTION_KEYWORDS` dicts**

Replace the entire `_SPORT_LEAGUES` dict (lines 17-86) with an empty dict:

```python
# Dynamic discovery replaces hardcoded mappings.
# ESPN search endpoint finds sport/league for any team name.
_SPORT_LEAGUES: dict = {}
```

Replace the entire `_QUESTION_KEYWORDS` dict (lines 88-143) with an empty dict:

```python
# Dynamic discovery replaces hardcoded keyword mappings.
_QUESTION_KEYWORDS: dict = {}
```

- [ ] **Step 2: Add `search_team()` method to `SportsDataClient`**

Add after the `_get()` method (after line 180):

```python
    # ESPN search endpoint — free, no API key needed
    _SEARCH_URL = "https://site.web.api.espn.com/apis/common/v3/search"

    def search_team(self, team_name: str) -> Optional[Tuple[str, str]]:
        """Search ESPN for a team by name. Returns (sport, league) or None.

        Uses ESPN's free search endpoint to dynamically discover which
        sport/league a team belongs to, eliminating hardcoded mappings.
        """
        if not team_name or len(team_name) < 2:
            return None

        cache_key = f"search:{team_name.lower().strip()}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        self._rate_limit()
        try:
            resp = requests.get(
                self._SEARCH_URL,
                params={"query": team_name, "limit": "5", "type": "team"},
                timeout=10,
            )
            resp.raise_for_status()
            record_call("espn")
            results = resp.json()

            for item in results.get("results", []):
                entities = item.get("entities", [])
                for entity in entities:
                    link = entity.get("link", "")
                    # Link format: /sport/league/team/id/name
                    # e.g. /soccer/eng.3/team/123/team-name
                    parts = link.strip("/").split("/")
                    if len(parts) >= 3 and parts[0] != "athlete":
                        sport = parts[0]
                        league = parts[1]
                        result = (sport, league)
                        self._cache[cache_key] = (result, time.monotonic())
                        logger.info("ESPN search: '%s' → %s/%s", team_name, sport, league)
                        return result

            # No results found
            self._cache[cache_key] = (None, time.monotonic())
            return None

        except requests.RequestException as e:
            logger.debug("ESPN search failed for '%s': %s", team_name, e)
            return None
```

- [ ] **Step 3: Update `detect_sport()` to use search as fallback**

Replace the `detect_sport()` method (lines 182-202) with:

```python
    def detect_sport(self, question: str, slug: str, tags: List[str]) -> Optional[Tuple[str, str]]:
        """Detect sport/league from market data. Returns (sport, league) or None.

        Primary: ESPN search endpoint (dynamic discovery).
        Fallback: slug prefix or question keyword lookup (if any mappings exist).
        """
        # Try hardcoded lookups first (fast path — empty by default after refactor)
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        if slug_prefix in _SPORT_LEAGUES:
            sport, league, _ = _SPORT_LEAGUES[slug_prefix]
            return (sport, league)

        q_lower = question.lower()
        for keyword, (sport, league) in _QUESTION_KEYWORDS.items():
            if keyword in q_lower:
                return (sport, league)

        # Dynamic discovery via ESPN search
        team_a, team_b = self._extract_teams_from_question(question)
        if not team_a and not team_b:
            team_a, team_b = self._extract_teams_from_slug(slug)

        # Search with first team name
        for name in [team_a, team_b]:
            if name:
                result = self.search_team(name)
                if result:
                    return result

        return None
```

- [ ] **Step 4: Update `get_match_context()` to not depend on `_SPORT_LEAGUES` for league name**

Replace lines 402-407 in `get_match_context()`:

```python
        # BEFORE:
        league_name = ""
        for prefix, (s, l, name) in _SPORT_LEAGUES.items():
            if s == sport and l == league:
                league_name = name
                break

        # AFTER:
        league_name = league  # Use league slug as display name (e.g. "eng.1", "nba")
```

- [ ] **Step 5: Run all tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -x -q`
Expected: All pass (some tests may need adjusting if they depend on `_SPORT_LEAGUES` content).

- [ ] **Step 6: Commit**

```bash
git add src/sports_data.py
git commit -m "refactor: remove 111 hardcoded ESPN mappings, add search_team() discovery"
```

---

### Task 4: Refactor PandaScore — Remove Hardcoded Game Slugs

**Files:**
- Modify: `src/esports_data.py`

- [ ] **Step 1: Replace `_GAME_SLUGS` with minimal categorization**

Replace lines 19-30:

```python
# BEFORE:
_GAME_SLUGS = {
    "counter-strike": "csgo",
    "cs2": "csgo",
    "cs:go": "csgo",
    "csgo": "csgo",
    "league-of-legends": "lol",
    "lol": "lol",
    "dota": "dota2",
    "dota2": "dota2",
    "valorant": "valorant",
}

# AFTER — minimal categorization for API routing (4 games, no aliases):
_GAME_SLUGS = {
    "cs2": "csgo", "csgo": "csgo",
    "lol": "lol",
    "dota2": "dota2",
    "valorant": "valorant",
}
```

- [ ] **Step 2: Update `detect_game()` to search PandaScore when slug lookup fails**

Replace the `detect_game()` method (lines 95-111):

```python
    def detect_game(self, question: str, tags: List[str]) -> Optional[str]:
        """Detect which esports game a market is about. Returns PandaScore slug."""
        q_lower = question.lower()
        tags_lower = [t.lower() for t in tags]

        # Check tags first (fast path)
        for tag in tags_lower:
            for keyword, slug in _GAME_SLUGS.items():
                if keyword in tag:
                    return slug

        # Check question text
        for keyword, slug in _GAME_SLUGS.items():
            if keyword in q_lower:
                return slug

        # Dynamic: search PandaScore for team name
        team_a, _ = self._extract_team_names(question)
        if team_a:
            match = self.search_match(team_a)
            if match:
                videogame = match.get("videogame", {})
                slug = videogame.get("slug", "")
                if slug:
                    logger.info("PandaScore search: '%s' → game=%s", team_a, slug)
                    return slug

        return None
```

- [ ] **Step 3: Add `search_match()` method**

Add after `detect_game()`:

```python
    def search_match(self, team_name: str) -> Optional[dict]:
        """Search PandaScore for an upcoming match by team name.

        Uses the search[name] parameter on /matches/upcoming endpoint.
        Returns the first matching match dict, or None.
        """
        if not self.available or not team_name:
            return None

        cache_key = f"search_match:{team_name.lower().strip()}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        matches = self._get("/matches/upcoming", {
            "search[name]": team_name,
            "per_page": 5,
            "sort": "begin_at",
        })

        if matches and isinstance(matches, list) and len(matches) > 0:
            result = matches[0]
            self._cache[cache_key] = (result, time.monotonic())
            return result

        self._cache[cache_key] = (None, time.monotonic())
        return None
```

- [ ] **Step 4: Run tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_esports_data.py tests/test_sports_discovery.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/esports_data.py
git commit -m "refactor: simplify PandaScore game slugs, add search_match() discovery"
```

---

### Task 5: Refactor CricketData — Remove Hardcoded Series Mappings

**Files:**
- Modify: `src/cricket_data.py`

- [ ] **Step 1: Remove hardcoded dicts and simplify `get_match_context()`**

Replace lines 21-38 (the two hardcoded dicts):

```python
# Dynamic discovery — no hardcoded series mappings needed.
# get_match_context() fetches all current matches and fuzzy-matches team names.
```

Replace the `get_match_context()` method (lines 139-220) with:

```python
    def get_match_context(self, question: str, slug: str, tags: list[str]) -> Optional[str]:
        """Build context string for AI analyst — same interface as other data clients.

        Dynamic discovery: fetches all current matches and fuzzy-matches
        team names from the question. No hardcoded series mappings.
        """
        if not self.available:
            return None

        # Check if this is a cricket market (by tag, slug, or question)
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        _cricket_slugs = {"ipl", "psl", "t20", "crint", "cricpakt20cup", "criclcl"}
        tags_lower = " ".join(t.lower() for t in tags)
        is_cricket = (
            slug_prefix in _cricket_slugs
            or "cricket" in tags_lower
            or "cricket" in question.lower()
        )
        if not is_cricket:
            return None

        # Extract team names
        team_a, team_b = self._extract_teams(question)
        if not team_a or not team_b:
            return None

        logger.info("Fetching CricketData: %s vs %s", team_a, team_b)

        # Get current matches and find the relevant one
        current = self.get_current_matches()
        matched_match = None
        team_a_lower = team_a.lower()
        team_b_lower = team_b.lower()

        for m in current:
            teams_lower = [t.lower() for t in m["teams"]]
            shortnames_lower = {k.lower(): v.lower() for k, v in m["shortnames"].items()}

            # Check if both teams are in this match
            a_found = any(
                team_a_lower in t or t in team_a_lower
                for t in teams_lower
            ) or any(
                team_a_lower in sn or sn in team_a_lower
                for sn in shortnames_lower.values()
            )
            b_found = any(
                team_b_lower in t or t in team_b_lower
                for t in teams_lower
            ) or any(
                team_b_lower in sn or sn in team_b_lower
                for sn in shortnames_lower.values()
            )

            if a_found and b_found:
                matched_match = m
                break

        parts = ["=== SPORTS DATA (CricketData) ==="]

        if matched_match:
            parts.append(f"\nMatch: {matched_match['name']}")
            parts.append(f"Type: {matched_match['match_type'].upper()}")
            parts.append(f"Venue: {matched_match['venue']}")
            parts.append(f"Status: {matched_match['status']}")
            if matched_match["score"]:
                parts.append(f"Score: {matched_match['score']}")
            if matched_match["started"] and not matched_match["ended"]:
                parts.append("State: LIVE")
            elif matched_match["ended"]:
                parts.append("State: COMPLETED")
            else:
                parts.append("State: UPCOMING")
        else:
            parts.append(f"\n{team_a} vs {team_b}")
            parts.append("No live/recent match data found for this fixture.")

        parts.append("\nUse match status, score, and format to inform your estimate.")
        return "\n".join(parts)
```

- [ ] **Step 2: Run tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -x -q`
Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add src/cricket_data.py
git commit -m "refactor: remove 11 hardcoded cricket series mappings, use dynamic match discovery"
```

---

### Task 6: Refactor Odds API — Remove Bridge, Hardcoded Keys, Change Refresh

**Files:**
- Modify: `src/odds_api.py`

This is the largest refactor. We remove ~136 hardcoded entries, the bridge system, and change refresh from 4x/day to every 2 hours.

- [ ] **Step 1: Remove `_SPORT_KEYS` dict (lines 34-97)**

Replace with:

```python
# Dynamic sport key discovery replaces hardcoded mappings.
# _detect_sport_key() uses /v4/sports (FREE) to find active keys,
# then /v4/sports/{key}/events (FREE) to match teams.
_SPORT_KEYS: dict = {}
```

- [ ] **Step 2: Remove `_QUESTION_SPORT_KEYS` dict (lines 99-156)**

Replace with:

```python
# Dynamic discovery replaces hardcoded keyword mappings.
_QUESTION_SPORT_KEYS: dict = {}
```

- [ ] **Step 3: Change refresh schedule**

Replace line 177:

```python
# BEFORE:
    _REFRESH_HOURS_UTC = [7, 12, 19, 23]  # 4x/day (was 8x — credit savings)

# AFTER:
    _REFRESH_INTERVAL_HOURS = 2  # Every 2h (12x/day). Budget: 10,800/month of 20K.
```

- [ ] **Step 4: Update `_past_refresh_boundary()` to use interval**

Replace the `_past_refresh_boundary()` method (find it with `def _past_refresh_boundary`):

```python
    def _past_refresh_boundary(self, cached_wall_ts: float) -> bool:
        """Check if enough time has passed since last fetch.

        Uses a simple interval (every 2h) instead of fixed UTC hours.
        """
        return (time.time() - cached_wall_ts) >= self._REFRESH_INTERVAL_HOURS * 3600
```

- [ ] **Step 5: Add dynamic sport key discovery method**

Add a new method `_discover_sport_key()` after `_match_tennis_key()`:

```python
    def _discover_sport_key(self, team_a: str, team_b: str) -> Optional[str]:
        """Dynamically find the sport key for a team pair using FREE endpoints.

        1. GET /v4/sports?all=false → all active sport keys (FREE, 0 credits)
        2. For each sport key, GET /v4/sports/{key}/events → match team names (FREE)
        """
        if not team_a and not team_b:
            return None

        # Get active sports (cached 1h)
        cache_key = "_active_sports"
        cached = self._cache.get(cache_key)
        active_keys = None
        if cached:
            data, ts = cached
            if time.time() - ts < self._ACTIVE_SPORTS_CACHE_TTL:
                active_keys = data

        if active_keys is None:
            sports_data = self._get("/sports", {"all": "false"})
            if not sports_data:
                return None
            active_keys = [s["key"] for s in sports_data
                          if isinstance(s, dict) and s.get("key") and s.get("active")]
            self._cache[cache_key] = (active_keys, time.time())

        # Search through cached events for each sport
        team_a_lower = team_a.lower() if team_a else ""
        team_b_lower = team_b.lower() if team_b else ""

        for sk in active_keys:
            events_cache_key = f"events:{sk}"
            cached_events = self._cache.get(events_cache_key)
            events = None
            if cached_events:
                data, ts = cached_events
                if time.time() - ts < self._REFRESH_INTERVAL_HOURS * 3600:
                    events = data

            if events is None:
                events = self._get(f"/sports/{sk}/events", {})
                if events and isinstance(events, list):
                    self._cache[events_cache_key] = (events, time.time())
                else:
                    continue

            # Check if any event matches our teams
            for event in events:
                home = (event.get("home_team") or "").lower()
                away = (event.get("away_team") or "").lower()
                if not home or not away:
                    continue
                # Check if team names match (substring)
                a_match = (team_a_lower in home or home in team_a_lower or
                           team_a_lower in away or away in team_a_lower)
                b_match = (team_b_lower in home or home in team_b_lower or
                           team_b_lower in away or away in team_b_lower)
                if a_match or b_match:
                    logger.info("Odds API discovery: '%s/%s' → %s", team_a, team_b, sk)
                    return sk

        return None
```

- [ ] **Step 6: Update `_detect_sport_key()` to use dynamic discovery as fallback**

Replace the `_detect_sport_key()` method (lines 289-312):

```python
    def _detect_sport_key(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Detect The Odds API sport key from market data.

        Priority: hardcoded lookup (fast) → tennis dynamic → full dynamic discovery.
        """
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        if slug_prefix in _SPORT_KEYS:
            return _SPORT_KEYS[slug_prefix]

        q_lower = question.lower()
        for keyword, sport_key in _QUESTION_SPORT_KEYS.items():
            if keyword in q_lower:
                if sport_key == "_tennis_atp":
                    gender = "wta" if self._is_wta_market(q_lower, slug) else "atp"
                    return self._match_tennis_key(gender, q_lower, slug)
                if sport_key == "_tennis_wta":
                    return self._match_tennis_key("wta", q_lower, slug)
                return sport_key

        # Tennis slug prefixes
        if slug_prefix in ("atp", "tennis"):
            return self._match_tennis_key("atp", q_lower, slug)
        if slug_prefix == "wta":
            return self._match_tennis_key("wta", q_lower, slug)

        # Dynamic discovery: extract teams, search through active sports
        team_a, team_b = self._extract_teams(question)
        return self._discover_sport_key(team_a, team_b)
```

- [ ] **Step 7: Remove bridge system methods**

Delete these methods entirely:
- `_get_bridge_events()` (lines ~780-789)
- `bridge_match()` (lines ~791-870)
- `_detect_all_sport_keys()` (lines ~358-366)

Also remove the `_BRIDGE_CACHE_MAX_AGE` constant (line ~180).

- [ ] **Step 8: Run tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -x -q --ignore=tests/test_odds_bridge.py`
Expected: All pass (ignoring bridge tests which will be deleted in Task 9).

- [ ] **Step 9: Commit**

```bash
git add src/odds_api.py
git commit -m "refactor: remove 136 hardcoded odds mappings + bridge, add dynamic discovery, 2h refresh"
```

---

### Task 7: Refactor `entry_gate.py` — Replace Cascade with Discovery

**Files:**
- Modify: `src/entry_gate.py`

- [ ] **Step 1: Update imports and constructor**

Replace lines 92-97:

```python
        # BEFORE:
        from src.thesportsdb import TheSportsDBClient
        self.tsdb = TheSportsDBClient()
        from src.football_data import FootballDataClient
        self.football_data = FootballDataClient()
        from src.cricket_data import CricketDataClient
        self.cricket_data = CricketDataClient()

        # AFTER — remove entirely (no replacement needed here)
```

Add `discovery` parameter to `__init__` signature — replace the `sports` parameter (line 75):

```python
        # BEFORE:
        sports: "SportsDataClient | None" = None,

        # AFTER:
        discovery: "SportsDiscovery | None" = None,
```

Update the TYPE_CHECKING import block (line 46):

```python
        # BEFORE:
    from src.sports_data import SportsDataClient

        # AFTER:
    from src.sports_discovery import SportsDiscovery
```

Update the attribute assignment (line 90):

```python
        # BEFORE:
        self.sports = sports

        # AFTER:
        self.discovery = discovery
```

- [ ] **Step 2: Replace the 5-tier cascade with discovery call**

Replace lines 314-400 (the entire bridge + cascade section) with:

```python
        # Sports context via unified discovery
        if self.discovery:
            for _m in prioritized:
                if _m.condition_id in esports_contexts:
                    continue  # PandaScore/Scout already has context
                _is_esports_mkt = is_esports_slug(_m.slug or "")
                if _is_esports_mkt:
                    continue
                try:
                    result = self.discovery.resolve(
                        getattr(_m, "question", ""),
                        _m.slug or "",
                        getattr(_m, "tags", []),
                    )
                    if result:
                        esports_contexts[_m.condition_id] = result.context
                        logger.info("Sports context (%s): %s", result.source, (_m.slug or "")[:40])
                except Exception as _exc:
                    logger.debug("Discovery error for %s: %s", (_m.slug or "")[:40], _exc)
```

- [ ] **Step 3: Remove `_reliable_source_cids` tracking**

Remove lines 337 (`_reliable_source_cids: set[str] = set()`) and all references to it:

Replace lines 431-447 (the reliability filter):

```python
        # BEFORE:
        _has_data: list = []
        _no_reliable_skipped = 0
        for m in prioritized:
            if m.condition_id in _reliable_source_cids:
                _has_data.append(m)
            else:
                _no_reliable_skipped += 1
        ...

        # AFTER — all discovery sources are reliable, filter by having context:
        _has_data: list = []
        _no_data_skipped = 0
        for m in prioritized:
            if m.condition_id in esports_contexts:
                _has_data.append(m)
            else:
                _no_data_skipped += 1
        if _no_data_skipped:
            logger.info("Skipped %d markets without sports data (saves AI tokens)", _no_data_skipped)
```

- [ ] **Step 4: Remove bridge match section**

Delete lines 314-333 (the bridge match section):

```python
        # REMOVE THIS ENTIRE BLOCK:
        # Odds API Bridge: match Polymarket markets to Odds API events for clean team names
        _bridge_names: dict[str, dict] = {}
        if self.odds_api and self.odds_api.available:
            ...
```

- [ ] **Step 5: Run tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -x -q --ignore=tests/test_odds_bridge.py --ignore=tests/test_thesportsdb.py`
Expected: Some test failures in `test_sports_context_pipeline.py` (will fix in Task 9).

- [ ] **Step 6: Commit**

```bash
git add src/entry_gate.py
git commit -m "refactor: replace 5-tier sports cascade with single discovery call"
```

---

### Task 8: Wire `SportsDiscovery` in `agent.py` and `scout_scheduler.py`

**Files:**
- Modify: `src/agent.py`
- Modify: `src/scout_scheduler.py`

- [ ] **Step 1: Update `agent.py` constructor**

In `src/agent.py`, add the import (after line 32):

```python
from src.sports_discovery import SportsDiscovery
```

Replace lines 92-99 and 139-154 — update how EntryGate is constructed:

After line 93 (`odds_api = OddsAPIClient()`), add:

```python
        from src.cricket_data import CricketDataClient
        cricket = CricketDataClient()
        discovery = SportsDiscovery(
            espn=sports, pandascore=self.esports,
            cricket=cricket, odds_api=odds_api,
        )
```

In the `EntryGate(...)` call (lines 139-154), replace:

```python
            # BEFORE:
            sports=sports,

            # AFTER:
            discovery=discovery,
```

- [ ] **Step 2: Update `scout_scheduler.py`**

Remove dead imports (lines 18, 21-22):

```python
# REMOVE:
from src.sports_data import SportsDataClient, _SPORT_LEAGUES
from src.football_data import FootballDataClient
from src.cricket_data import CricketDataClient
```

Replace with:

```python
from src.sports_data import SportsDataClient
```

Remove from `__init__` (lines 83-84):

```python
# REMOVE:
        self.football_data = FootballDataClient()
        self.cricket_data = CricketDataClient()
```

Remove `_LEAGUE_TO_PREFIX` dict (line 74):

```python
# REMOVE:
_LEAGUE_TO_PREFIX = {(s, l): prefix for prefix, (s, l, _) in _SPORT_LEAGUES.items()}
```

Update `_fetch_espn_upcoming()` — replace the slug_hint line (line 353):

```python
                        # BEFORE:
                        league_prefix = _LEAGUE_TO_PREFIX.get((sport, league), sport[:3])
                        slug_hint = f"{league_prefix}-{team_a[:4].lower()}-{team_b[:4].lower()}"

                        # AFTER:
                        slug_hint = f"{sport[:3]}-{team_a[:4].lower()}-{team_b[:4].lower()}"
```

Delete `_fetch_football_data_upcoming()` method entirely (lines 445-481).

Update `run_scout()` — remove the football-data.org call (lines 165-167 and 173):

```python
        # REMOVE these lines:
        # 3. Fetch football-data.org matches (Copa Libertadores + ESPN gaps)
        fd_matches = self._fetch_football_data_upcoming()
        logger.info("football-data.org: found %d upcoming matches", len(fd_matches))

        # UPDATE this line:
        # BEFORE:
        all_matches = sports_matches + esports_matches + fd_matches + cricket_matches
        # AFTER:
        all_matches = sports_matches + esports_matches + cricket_matches
```

Also remove the football-data.org context fallback in the scout context fetch (lines 192-198):

```python
                # REMOVE this block:
                # football-data.org fallback (soccer only, covers Copa Libertadores)
                if not context_parts and self.football_data.available:
                    fd_ctx = self.football_data.get_match_context(
                        match["question"], match.get("slug_hint", ""), []
                    )
                    if fd_ctx:
                        context_parts.append(fd_ctx)
```

And remove the cricket_data fallback that uses `self.cricket_data` (lines 199-205) since scout_scheduler no longer instantiates it:

```python
                # REMOVE this block:
                # CricketData fallback
                if not context_parts and self.cricket_data.available:
                    cr_ctx = self.cricket_data.get_match_context(
                        match["question"], match.get("slug_hint", ""), []
                    )
                    if cr_ctx:
                        context_parts.append(cr_ctx)
```

- [ ] **Step 3: Run tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -x -q --ignore=tests/test_odds_bridge.py --ignore=tests/test_thesportsdb.py --ignore=tests/test_sports_context_pipeline.py`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add src/agent.py src/scout_scheduler.py
git commit -m "refactor: wire SportsDiscovery in agent and scout_scheduler, remove dead imports"
```

---

### Task 9: Delete Dead Files and Fix Tests

**Files:**
- Delete: `src/football_data.py`
- Delete: `src/thesportsdb.py`
- Delete: `tests/test_thesportsdb.py`
- Delete: `tests/test_odds_bridge.py`
- Modify: `tests/test_sports_context_pipeline.py`

- [ ] **Step 1: Delete dead source files**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git rm src/football_data.py src/thesportsdb.py
```

- [ ] **Step 2: Delete dead test files**

```bash
git rm tests/test_thesportsdb.py tests/test_odds_bridge.py
```

- [ ] **Step 3: Rewrite `test_sports_context_pipeline.py`**

Replace the entire file:

```python
"""Test that SportsDiscovery context is fetched for non-esports markets."""
from unittest.mock import MagicMock, patch


def _make_gate(discovery=None):
    from src.entry_gate import EntryGate
    cfg = MagicMock()
    cfg.edge.min_edge = 0.06
    cfg.edge.fill_ratio_scaling = False
    cfg.ai.batch_size = 10
    cfg.risk.max_positions = 10
    gate = EntryGate.__new__(EntryGate)
    gate.config = cfg
    gate.portfolio = MagicMock()
    gate.portfolio.active_position_count = 0
    gate.odds_api = MagicMock()
    gate.odds_api.available = False
    gate.esports = MagicMock()
    gate.esports.get_match_context = MagicMock(return_value=None)
    gate.news_scanner = MagicMock()
    gate.news_scanner.search_for_markets = MagicMock(return_value={})
    gate.news_scanner.build_news_context = MagicMock(return_value="")
    gate.ai = MagicMock()
    gate.ai.analyze_batch = MagicMock(return_value=[])
    gate.trade_log = MagicMock()
    gate.discovery = discovery or MagicMock()
    gate.scout = None
    gate._far_market_ids = set()
    gate._analyzed_market_ids = {}
    gate._seen_market_ids = set()
    gate._breaking_news_detected = False
    gate._candidate_stock = []
    gate._fav_stock = []
    gate._far_stock = []
    gate._eligible_cache = []
    gate._eligible_pointer = 0
    gate._eligible_cache_ts = 0.0
    gate._confidence_c_cids = set()
    return gate


def _make_market(cid="cid-001", slug="mlb-nyy-bos", question="Will NY Yankees beat Boston?", sport_tag=""):
    m = MagicMock()
    m.condition_id = cid
    m.slug = slug
    m.question = question
    m.sport_tag = sport_tag
    m.yes_price = 0.60
    m.end_date_iso = "2026-04-01T00:00:00Z"
    m.match_start_iso = None
    m.tags = []
    return m


def test_discovery_called_for_sports_market():
    """SportsDiscovery.resolve() should be called for non-esports markets."""
    from src.sports_discovery import DiscoveryResult
    mock_discovery = MagicMock()
    mock_discovery.resolve = MagicMock(return_value=DiscoveryResult(
        context="=== SPORTS DATA (ESPN) ===\nTeam A: 15-10",
        source="ESPN",
        confidence="A",
    ))
    gate = _make_gate(discovery=mock_discovery)

    market = _make_market()
    with patch("src.entry_gate.is_esports_slug", return_value=False):
        gate._analyze_batch([market], cycle_count=0)

    mock_discovery.resolve.assert_called_once()


def test_discovery_skipped_for_esports():
    """SportsDiscovery should NOT be called for esports markets (PandaScore handles them)."""
    mock_discovery = MagicMock()
    gate = _make_gate(discovery=mock_discovery)
    gate.esports.get_match_context = MagicMock(return_value="=== ESPORTS DATA ===")

    market = _make_market(slug="cs2-team-a-vs-b", sport_tag="cs2")
    with patch("src.entry_gate.is_esports_slug", return_value=True):
        gate._analyze_batch([market], cycle_count=0)

    mock_discovery.resolve.assert_not_called()


def test_no_data_markets_skipped():
    """Markets without any sports context should be skipped (not sent to AI)."""
    mock_discovery = MagicMock()
    mock_discovery.resolve = MagicMock(return_value=None)  # No data
    gate = _make_gate(discovery=mock_discovery)

    market = _make_market(slug="unknown-xyz-abc", question="Unknown Sport: X vs Y")
    with patch("src.entry_gate.is_esports_slug", return_value=False):
        result = gate._analyze_batch([market], cycle_count=0)

    # Should return empty — no markets with data
    assert result == ([], {})
```

- [ ] **Step 4: Run ALL tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "cleanup: delete football_data.py, thesportsdb.py, bridge tests, update pipeline tests"
```

---

### Task 10: Full Audit — Verify No Broken References

**Files:**
- All project files

- [ ] **Step 1: Search for any remaining references to deleted modules**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
grep -rn "football_data\|FootballDataClient\|thesportsdb\|TheSportsDBClient\|bridge_match\|_get_bridge_events\|_detect_all_sport_keys\|_BRIDGE_CACHE_MAX_AGE" src/ tests/ --include="*.py"
```

Expected: Zero matches. If any remain, fix them.

- [ ] **Step 2: Search for references to removed dicts**

```bash
grep -rn "_SPORT_LEAGUES\[" src/ tests/ --include="*.py"
grep -rn "_QUESTION_SPORT_KEYS\[" src/ tests/ --include="*.py"
grep -rn "_SLUG_TO_SERIES\[" src/ tests/ --include="*.py"
grep -rn "_KEYWORD_TO_SERIES\[" src/ tests/ --include="*.py"
grep -rn "_SLUG_TO_COMPETITION\[" src/ tests/ --include="*.py"
grep -rn "_KEYWORD_TO_COMPETITION\[" src/ tests/ --include="*.py"
```

Expected: Zero matches for all.

- [ ] **Step 3: Run full test suite**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v --tb=short`
Expected: All pass, zero failures.

- [ ] **Step 4: Verify imports work**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
python -c "from src.sports_discovery import SportsDiscovery, DiscoveryResult; print('OK')"
python -c "from src.entry_gate import EntryGate; print('OK')"
python -c "from src.agent import Agent; print('OK')"
python -c "from src.odds_api import OddsAPIClient; print('OK')"
python -c "from src.sports_data import SportsDataClient; print('OK')"
python -c "from src.esports_data import EsportsDataClient; print('OK')"
python -c "from src.cricket_data import CricketDataClient; print('OK')"
```

Expected: All print "OK".

- [ ] **Step 5: Commit audit results (if any fixes needed)**

```bash
git add -A
git commit -m "audit: verify no broken references after dynamic discovery refactor"
```
