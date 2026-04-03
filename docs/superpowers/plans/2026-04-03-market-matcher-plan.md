# Market Matcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken `match_markets_batch` string-in-string matching with a 3-layer abbreviation-aware matcher that bridges Polymarket ↔ ESPN ↔ PandaScore, raising match rate from ~20% to ~85%.

**Architecture:** New `src/market_matcher.py` (~300-350 lines) containing `AliasStore` class (builds/caches team abbreviation lookups from 3 APIs) and `match_batch()` function (3-layer matching: exact abbreviation → normalized short name → fuzzy). Drop-in replacement for `scout_scheduler.match_markets_batch` — same return format, zero changes to downstream modules. Also fixes CS2 PandaScore slug bug and pagination params.

**Tech Stack:** Python 3.11+, rapidfuzz, requests, existing `src/team_matcher.py` (reused for fuzzy layer)

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| **Create** | `src/market_matcher.py` | AliasStore + match_batch — the new matching engine |
| **Modify** | `src/scout_scheduler.py:107` | Fix `cs2` → `csgo` in `_ESPORT_GAMES` |
| **Modify** | `src/scout_scheduler.py:617-619` | Fix PandaScore pagination params |
| **Modify** | `src/scout_scheduler.py:567-592` | Add `abbrev_a`/`abbrev_b`/`espn_event_id` to ESPN entries |
| **Modify** | `src/scout_scheduler.py:629-664` | Add `abbrev_a`/`abbrev_b`/`pandascore_match_id` to PandaScore entries |
| **Modify** | `src/entry_gate.py:335` | Replace `match_markets_batch` call with `market_matcher.match_batch` |
| **Create** | `tests/test_market_matcher.py` | Unit tests for AliasStore + match_batch |

No other files are touched. Return format is identical — entry_gate, enrichment pipeline, AI pipeline all unaffected.

---

### Task 1: Install rapidfuzz dependency

**Files:**
- Modify: `requirements.txt` (add rapidfuzz)

- [ ] **Step 1: Add rapidfuzz to requirements.txt**

```bash
pip install rapidfuzz
```

Then add to requirements.txt:

```
rapidfuzz>=3.0.0
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from rapidfuzz import fuzz; print(fuzz.ratio('test', 'test'))"`
Expected: `100.0`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add rapidfuzz for team name matching"
```

---

### Task 2: Fix CS2 slug + PandaScore pagination in scout_scheduler.py

**Files:**
- Modify: `src/scout_scheduler.py:107` — `cs2` → `csgo`
- Modify: `src/scout_scheduler.py:617-619` — pagination params

**IMPORTANT — "Önce Neyi Bozar?" check:**
- `_ESPORT_GAMES` is used ONLY in `_fetch_esports_upcoming()` (line 610). No other consumer.
- Pagination params are used ONLY in the same function (line 617-619). No other consumer.
- Changing `cs2` → `csgo` means the URL changes from `https://api.pandascore.co/cs2/matches/upcoming` (returns 404/empty) to `https://api.pandascore.co/csgo/matches/upcoming` (returns real CS2 matches). This is a pure fix, no breakage.

- [ ] **Step 1: Write test for CS2 slug fix**

Create `tests/test_scout_cs2_fix.py`:

```python
"""Verify CS2 slug fix — PandaScore uses 'csgo' not 'cs2'."""
import pytest


def test_esport_games_uses_csgo_slug():
    """_ESPORT_GAMES must use 'csgo' (PandaScore's slug), not 'cs2'."""
    from src.scout_scheduler import _ESPORT_GAMES

    assert "csgo" in _ESPORT_GAMES, "CS2 must use 'csgo' slug for PandaScore API"
    assert "cs2" not in _ESPORT_GAMES, "'cs2' is not a valid PandaScore game slug"


def test_esport_games_contains_all_games():
    """All four main esports games must be present."""
    from src.scout_scheduler import _ESPORT_GAMES

    expected = {"csgo", "lol", "dota2", "valorant"}
    assert set(_ESPORT_GAMES) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scout_cs2_fix.py -v`
Expected: FAIL — `assert "csgo" in ["cs2", "lol", "dota2", "valorant"]`

- [ ] **Step 3: Fix the slug in scout_scheduler.py**

In `src/scout_scheduler.py` line 107, change:

```python
# OLD:
_ESPORT_GAMES = ["cs2", "lol", "dota2", "valorant"]

# NEW:
_ESPORT_GAMES = ["csgo", "lol", "dota2", "valorant"]
```

- [ ] **Step 4: Fix PandaScore pagination params**

In `src/scout_scheduler.py` lines 617-619, change:

```python
# OLD:
                    resp = requests.get(
                        url,
                        params={"per_page": 100, "sort": "begin_at", "page": page},
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10,
                    )

# NEW:
                    resp = requests.get(
                        url,
                        params={"page[size]": 100, "sort": "begin_at", "page[number]": page},
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10,
                    )
```

Also fix the pagination check on line 667:

```python
# OLD:
                    if len(page_results) >= 100:
                        page += 1

# NEW:
                    if len(page_results) >= 100:
                        page += 1
```

(Pagination check stays the same — the logic is correct, only the param names change.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_scout_cs2_fix.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/scout_scheduler.py tests/test_scout_cs2_fix.py
git commit -m "fix: CS2 PandaScore slug cs2→csgo + pagination params"
```

---

### Task 3: Add abbreviation fields to scout entries

**Files:**
- Modify: `src/scout_scheduler.py:567-592` — ESPN standard entries: add `abbrev_a`, `abbrev_b`, `espn_event_id`
- Modify: `src/scout_scheduler.py:498-534` — ESPN tennis entries: add `abbrev_a`, `abbrev_b`
- Modify: `src/scout_scheduler.py:538-564` — ESPN MMA entries: add `abbrev_a`, `abbrev_b`
- Modify: `src/scout_scheduler.py:629-664` — PandaScore entries: add `abbrev_a`, `abbrev_b`, `pandascore_match_id`

**IMPORTANT — "Önce Neyi Bozar?" check:**
- Scout entries are plain dicts. Adding new keys does NOT break any consumer.
- `match_markets_batch` only reads `team_a`, `team_b`, `entered`, `matched` keys. New keys are ignored.
- `entry_gate.py` reads `scout_entry.get("match_time")`, `scout_entry.get("scout_key")`. New keys are ignored.
- All new fields use `.get()` with default — no KeyError risk.

- [ ] **Step 1: Write test for abbreviation fields**

Add to `tests/test_scout_cs2_fix.py`:

```python
def test_espn_entry_has_abbreviation_fields():
    """ESPN scout entries must include abbreviation fields."""
    # Simulate what _fetch_espn_upcoming produces for a standard entry
    entry = {
        "scout_key": "basketball_nba_Los Angeles Lakers_Boston Celtics_20260405",
        "team_a": "Los Angeles Lakers",
        "team_b": "Boston Celtics",
        "abbrev_a": "LAL",
        "abbrev_b": "BOS",
        "espn_event_id": "401654321",
        "match_time": "2026-04-05T00:00:00+00:00",
        "sport": "basketball",
        "league": "nba",
    }
    assert "abbrev_a" in entry
    assert "abbrev_b" in entry
    assert "espn_event_id" in entry
    assert len(entry["abbrev_a"]) >= 2
    assert len(entry["abbrev_b"]) >= 2


def test_pandascore_entry_has_abbreviation_fields():
    """PandaScore scout entries must include abbreviation fields."""
    entry = {
        "scout_key": "esports_csgo_Fnatic_Team Liquid_20260405",
        "team_a": "Fnatic",
        "team_b": "Team Liquid",
        "abbrev_a": "FNC",
        "abbrev_b": "TL",
        "pandascore_match_id": 98765,
        "match_time": "2026-04-05T18:00:00+00:00",
        "is_esports": True,
    }
    assert "abbrev_a" in entry
    assert "abbrev_b" in entry
    assert "pandascore_match_id" in entry
```

- [ ] **Step 2: Add abbreviation fields to ESPN standard entries**

In `src/scout_scheduler.py` around lines 567-592, change the entry construction:

```python
                        # STANDARD (soccer, basketball, football, baseball, hockey):
                        # flat competitions[] with team.displayName
                        competitors = event.get("competitions", [{}])[0].get("competitors", [])
                        if len(competitors) != 2:
                            continue

                        team_a = competitors[0].get("team", {}).get("displayName", "")
                        team_b = competitors[1].get("team", {}).get("displayName", "")
                        if not team_a or not team_b:
                            continue

                        abbrev_a = competitors[0].get("team", {}).get("abbreviation", "")
                        abbrev_b = competitors[1].get("team", {}).get("abbreviation", "")
                        short_a = competitors[0].get("team", {}).get("shortDisplayName", "")
                        short_b = competitors[1].get("team", {}).get("shortDisplayName", "")

                        slug_hint = f"{sport[:3]}-{team_a[:4].lower()}-{team_b[:4].lower()}"
                        scout_key = f"{sport}_{league}_{team_a}_{team_b}_{date_str}"
                        matches.append({
                            "scout_key": scout_key,
                            "team_a": team_a,
                            "team_b": team_b,
                            "abbrev_a": abbrev_a,
                            "abbrev_b": abbrev_b,
                            "short_a": short_a,
                            "short_b": short_b,
                            "espn_event_id": event.get("id", ""),
                            "question": f"{team_a} vs {team_b}: Who will win?",
                            "match_time": event_dt.isoformat(),
                            "sport": sport,
                            "league": league,
                            "league_name": display_name,
                            "slug_hint": slug_hint,
                            "tags": ["sports", display_name.lower()],
                            "is_esports": False,
                        })
```

- [ ] **Step 3: Add abbreviation fields to ESPN tennis entries**

In `src/scout_scheduler.py` around lines 498-534, tennis entries use `athlete` not `team`. Add abbreviation from athlete data:

```python
                                    # Inside tennis parser, after extracting player_a/player_b:
                                    abbrev_a = competitors[0].get("athlete", {}).get("shortName", player_a)
                                    abbrev_b = competitors[1].get("athlete", {}).get("shortName", player_b)
```

Add to the dict: `"abbrev_a": abbrev_a, "abbrev_b": abbrev_b, "espn_event_id": event.get("id", ""),`

- [ ] **Step 4: Add abbreviation fields to ESPN MMA entries**

In `src/scout_scheduler.py` around lines 538-564, MMA entries also use `athlete`:

```python
                                    abbrev_a = competitors[0].get("athlete", {}).get("shortName", fighter_a)
                                    abbrev_b = competitors[1].get("athlete", {}).get("shortName", fighter_b)
```

Add to the dict: `"abbrev_a": abbrev_a, "abbrev_b": abbrev_b, "espn_event_id": event.get("id", ""),`

- [ ] **Step 5: Add abbreviation fields to PandaScore entries**

In `src/scout_scheduler.py` around lines 629-664, change:

```python
                        opponents = match.get("opponents", [])
                        if len(opponents) != 2:
                            continue

                        team_a = opponents[0].get("opponent", {}).get("name", "")
                        team_b = opponents[1].get("opponent", {}).get("name", "")
                        if not team_a or not team_b:
                            continue

                        abbrev_a = opponents[0].get("opponent", {}).get("acronym", "") or ""
                        abbrev_b = opponents[1].get("opponent", {}).get("acronym", "") or ""

                        scout_key = f"esports_{game}_{team_a}_{team_b}_{match_dt.strftime('%Y%m%d')}"
                        matches.append({
                            "scout_key": scout_key,
                            "team_a": team_a,
                            "team_b": team_b,
                            "abbrev_a": abbrev_a,
                            "abbrev_b": abbrev_b,
                            "pandascore_match_id": match.get("id"),
                            "question": f"{team_a} vs {team_b}: Who will win? ({game.upper()})",
                            "match_time": match_dt.isoformat(),
                            "sport": "",
                            "league": "",
                            "league_name": game.upper(),
                            "slug_hint": f"{game}-{team_a[:4].lower()}-{team_b[:4].lower()}",
                            "tags": ["esports", game],
                            "is_esports": True,
                        })
```

- [ ] **Step 6: Verify no existing tests break**

Run: `python -m pytest tests/ -v --tb=short 2>&1 | head -50`
Expected: All existing tests pass (new fields don't break anything).

- [ ] **Step 7: Commit**

```bash
git add src/scout_scheduler.py tests/test_scout_cs2_fix.py
git commit -m "feat: add abbreviation fields to ESPN/PandaScore scout entries"
```

---

### Task 4: Create market_matcher.py — AliasStore class

**Files:**
- Create: `src/market_matcher.py`
- Create: `tests/test_market_matcher.py`

This task creates the `AliasStore` class that builds and caches team abbreviation lookup tables from Polymarket, ESPN, and PandaScore APIs. The store persists to `logs/alias_cache.json` and refreshes in a background thread every 24h.

- [ ] **Step 1: Write tests for AliasStore**

Create `tests/test_market_matcher.py`:

```python
"""Tests for market_matcher.py — AliasStore + match_batch."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.market_matcher import AliasStore, STATIC_ABBREVS


class TestAliasStore:
    """AliasStore loads from cache, falls back to static dict."""

    def test_static_fallback_has_entries(self):
        """Static abbreviation dict must not be empty."""
        assert len(STATIC_ABBREVS) > 0
        # Must have key esports abbreviations
        assert "fnc" in STATIC_ABBREVS or "FNC" in STATIC_ABBREVS

    def test_load_from_cache_file(self, tmp_path):
        """AliasStore loads from existing cache JSON."""
        cache_file = tmp_path / "alias_cache.json"
        cache_data = {
            "_meta": {"updated_at": "2026-04-03T00:00:00Z"},
            "abbrevs": {"lal": "los angeles lakers", "bos": "boston celtics"},
        }
        cache_file.write_text(json.dumps(cache_data))

        store = AliasStore(cache_path=cache_file, auto_refresh=False)
        assert store.resolve("LAL") == "los angeles lakers"
        assert store.resolve("BOS") == "boston celtics"

    def test_fallback_to_static_when_no_cache(self, tmp_path):
        """AliasStore uses static dict when cache file doesn't exist."""
        cache_file = tmp_path / "nonexistent.json"
        store = AliasStore(cache_path=cache_file, auto_refresh=False)
        # Static dict should be loaded
        assert store._abbrevs  # not empty

    def test_resolve_case_insensitive(self, tmp_path):
        """Resolve works regardless of case."""
        cache_file = tmp_path / "alias_cache.json"
        cache_data = {
            "_meta": {"updated_at": "2026-04-03T00:00:00Z"},
            "abbrevs": {"fnc": "fnatic", "tl": "team liquid"},
        }
        cache_file.write_text(json.dumps(cache_data))

        store = AliasStore(cache_path=cache_file, auto_refresh=False)
        assert store.resolve("FNC") == "fnatic"
        assert store.resolve("fnc") == "fnatic"
        assert store.resolve("Fnc") == "fnatic"

    def test_resolve_unknown_returns_input(self, tmp_path):
        """Unknown abbreviation returns the input lowered."""
        cache_file = tmp_path / "nonexistent.json"
        store = AliasStore(cache_path=cache_file, auto_refresh=False)
        assert store.resolve("ZZZZZ") == "zzzzz"

    def test_corrupted_cache_falls_back_to_static(self, tmp_path):
        """Corrupted JSON cache falls back to static dict."""
        cache_file = tmp_path / "alias_cache.json"
        cache_file.write_text("{broken json!!!")
        store = AliasStore(cache_path=cache_file, auto_refresh=False)
        assert store._abbrevs  # static fallback loaded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_market_matcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.market_matcher'`

- [ ] **Step 3: Implement AliasStore**

Create `src/market_matcher.py`:

```python
"""Market matcher — bridges Polymarket markets to ESPN/PandaScore scout entries.

Drop-in replacement for scout_scheduler.match_markets_batch().
Uses 3-layer matching: exact abbreviation → normalized short name → fuzzy.
AliasStore caches team abbreviation lookups to logs/alias_cache.json.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from rapidfuzz import fuzz

from src.team_matcher import match_team, _normalize, TEAM_ALIASES

logger = logging.getLogger(__name__)

ALIAS_CACHE_PATH = Path("logs/alias_cache.json")
CACHE_TTL_HOURS = 24

# ── Static fallback abbreviations ────────────────────────────────────────────
# Used when cache file doesn't exist or is corrupted.
# Key = lowercase abbreviation, Value = lowercase canonical name.
STATIC_ABBREVS: dict[str, str] = {
    # NBA
    "lal": "los angeles lakers", "bos": "boston celtics", "gsw": "golden state warriors",
    "bkn": "brooklyn nets", "nyk": "new york knicks", "phi": "philadelphia 76ers",
    "mil": "milwaukee bucks", "mia": "miami heat", "chi": "chicago bulls",
    "phx": "phoenix suns", "dal": "dallas mavericks", "den": "denver nuggets",
    "min": "minnesota timberwolves", "okc": "oklahoma city thunder",
    "cle": "cleveland cavaliers", "lac": "la clippers", "hou": "houston rockets",
    "mem": "memphis grizzlies", "nop": "new orleans pelicans", "atl": "atlanta hawks",
    "ind": "indiana pacers", "orl": "orlando magic", "tor": "toronto raptors",
    "wsh": "washington wizards", "det": "detroit pistons", "cha": "charlotte hornets",
    "sac": "sacramento kings", "por": "portland trail blazers", "uta": "utah jazz",
    "sas": "san antonio spurs",
    # NFL
    "kc": "kansas city chiefs", "buf": "buffalo bills", "bal": "baltimore ravens",
    "sf": "san francisco 49ers", "gb": "green bay packers", "tb": "tampa bay buccaneers",
    "ne": "new england patriots", "sea": "seattle seahawks", "pit": "pittsburgh steelers",
    "cin": "cincinnati bengals", "jax": "jacksonville jaguars", "ten": "tennessee titans",
    "lar": "los angeles rams", "nyg": "new york giants", "nyj": "new york jets",
    "car": "carolina panthers", "no": "new orleans saints", "lv": "las vegas raiders",
    "ari": "arizona cardinals",
    # MLB
    "nyy": "new york yankees", "bos": "boston red sox", "lad": "los angeles dodgers",
    "nym": "new york mets", "chc": "chicago cubs", "cws": "chicago white sox",
    "sd": "san diego padres", "tex": "texas rangers", "stl": "st. louis cardinals",
    # NHL
    "tor": "toronto maple leafs", "mtl": "montreal canadiens", "bos": "boston bruins",
    "nyr": "new york rangers", "pit": "pittsburgh penguins", "wsh": "washington capitals",
    "edm": "edmonton oilers", "cgy": "calgary flames", "van": "vancouver canucks",
    "col": "colorado avalanche",
    # Esports
    "fnc": "fnatic", "tl": "team liquid", "g2": "g2 esports", "c9": "cloud9",
    "t1": "t1", "geng": "gen.g", "drx": "drx", "sen": "sentinels",
    "100t": "100 thieves", "eg": "evil geniuses", "navi": "natus vincere",
    "faze": "faze clan", "vit": "team vitality", "spirit": "team spirit",
    "mouz": "mouz", "hero": "heroic", "col": "complexity gaming",
    "loud": "loud", "furia": "furia", "mibr": "mibr",
    "kcorp": "karmine corp", "kc": "karmine corp",
    "blg": "bilibili gaming", "tes": "top esports", "jdg": "jd gaming",
    "weibo": "weibo gaming", "lng": "lng esports", "rng": "royal never give up",
    "edg": "edward gaming", "fpx": "funplus phoenix",
}


class AliasStore:
    """Team abbreviation → canonical name lookup.

    Loads from logs/alias_cache.json on init (instant).
    Refreshes from APIs in background thread every 24h.
    Falls back to STATIC_ABBREVS if cache is missing/corrupted.
    """

    def __init__(
        self,
        cache_path: Path = ALIAS_CACHE_PATH,
        auto_refresh: bool = True,
    ) -> None:
        self._cache_path = cache_path
        self._abbrevs: dict[str, str] = {}
        self._lock = threading.Lock()

        # Load from cache or static fallback
        if not self._load_cache():
            self._abbrevs = dict(STATIC_ABBREVS)
            logger.info("AliasStore: loaded %d static abbreviations", len(self._abbrevs))

        # Background refresh if enabled
        if auto_refresh:
            t = threading.Thread(target=self._background_refresh, daemon=True)
            t.start()

    def resolve(self, abbreviation: str) -> str:
        """Resolve abbreviation to canonical team name. Case-insensitive.

        Returns lowercase canonical name, or input lowered if not found.
        """
        key = abbreviation.lower().strip()
        with self._lock:
            return self._abbrevs.get(key, key)

    def has(self, abbreviation: str) -> bool:
        """Check if abbreviation is known."""
        key = abbreviation.lower().strip()
        with self._lock:
            return key in self._abbrevs

    def _load_cache(self) -> bool:
        """Load abbreviations from JSON cache. Returns True if successful."""
        try:
            if not self._cache_path.exists():
                return False
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            abbrevs = data.get("abbrevs", {})
            if not abbrevs:
                return False
            # Check TTL
            updated = data.get("_meta", {}).get("updated_at", "")
            if updated:
                try:
                    updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    age_hours = (datetime.now(timezone.utc) - updated_dt).total_seconds() / 3600
                    if age_hours > CACHE_TTL_HOURS * 2:
                        logger.info("AliasStore: cache too old (%.1fh), will refresh", age_hours)
                except (ValueError, TypeError):
                    pass
            with self._lock:
                self._abbrevs = {k.lower(): v.lower() for k, v in abbrevs.items()}
            logger.info("AliasStore: loaded %d abbreviations from cache", len(self._abbrevs))
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("AliasStore: cache load failed (%s), using static fallback", e)
            return False

    def _save_cache(self) -> None:
        """Persist current abbreviations to JSON."""
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                data = {
                    "_meta": {"updated_at": datetime.now(timezone.utc).isoformat()},
                    "abbrevs": dict(self._abbrevs),
                }
            self._cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("AliasStore: saved %d abbreviations to cache", len(self._abbrevs))
        except OSError as e:
            logger.warning("AliasStore: cache save failed: %s", e)

    def _background_refresh(self) -> None:
        """Refresh abbreviations from APIs in background thread."""
        try:
            new_abbrevs: dict[str, str] = dict(STATIC_ABBREVS)

            # 1. Polymarket /sports/teams
            self._fetch_polymarket_teams(new_abbrevs)

            # 2. ESPN /teams for all leagues
            self._fetch_espn_teams(new_abbrevs)

            # 3. PandaScore /teams for all games
            self._fetch_pandascore_teams(new_abbrevs)

            with self._lock:
                self._abbrevs = {k.lower(): v.lower() for k, v in new_abbrevs.items()}

            self._save_cache()
            logger.info("AliasStore: background refresh complete — %d abbreviations", len(self._abbrevs))
        except Exception as e:
            logger.warning("AliasStore: background refresh failed: %s", e)

    def _fetch_polymarket_teams(self, abbrevs: dict[str, str]) -> None:
        """Fetch team abbreviations from Polymarket Gamma API."""
        try:
            resp = requests.get(
                "https://gamma-api.polymarket.com/sports/teams",
                timeout=15,
            )
            if resp.status_code != 200:
                logger.debug("Polymarket /sports/teams returned %d", resp.status_code)
                return
            teams = resp.json()
            count = 0
            if isinstance(teams, list):
                for team in teams:
                    abbr = (team.get("abbreviation") or "").strip()
                    name = (team.get("name") or "").strip()
                    if abbr and name and len(abbr) >= 2:
                        abbrevs[abbr.lower()] = name.lower()
                        count += 1
                    # Also add alias if present
                    alias = (team.get("alias") or "").strip()
                    if alias and name:
                        abbrevs[alias.lower()] = name.lower()
            logger.debug("Polymarket teams: %d abbreviations", count)
        except Exception as e:
            logger.debug("Polymarket teams fetch failed: %s", e)

    def _fetch_espn_teams(self, abbrevs: dict[str, str]) -> None:
        """Fetch team abbreviations from ESPN /teams endpoints."""
        from src.scout_scheduler import _SCOUT_LEAGUES

        count = 0
        for sport, league, _ in _SCOUT_LEAGUES:
            # Skip tournament sports (tennis, golf) — they use athletes, not teams
            if sport in ("tennis", "golf", "mma"):
                continue
            try:
                url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for sport_data in data.get("sports", []):
                    for league_data in sport_data.get("leagues", []):
                        for team_entry in league_data.get("teams", []):
                            t = team_entry.get("team", {})
                            abbr = (t.get("abbreviation") or "").strip()
                            display = (t.get("displayName") or "").strip()
                            short = (t.get("shortDisplayName") or "").strip()
                            if abbr and display:
                                abbrevs[abbr.lower()] = display.lower()
                                count += 1
                            if short and display:
                                abbrevs[short.lower()] = display.lower()
                time.sleep(0.3)  # ESPN rate limit
            except Exception as e:
                logger.debug("ESPN teams fetch failed for %s/%s: %s", sport, league, e)
        logger.debug("ESPN teams: %d abbreviations", count)

    def _fetch_pandascore_teams(self, abbrevs: dict[str, str]) -> None:
        """Fetch team acronyms from PandaScore /teams endpoints."""
        import os
        api_key = os.getenv("PANDASCORE_API_KEY", "")
        if not api_key:
            logger.debug("PandaScore API key not set, skipping team fetch")
            return

        count = 0
        for game in ["csgo", "lol", "dota2", "valorant"]:
            try:
                resp = requests.get(
                    f"https://api.pandascore.co/{game}/teams",
                    params={"page[size]": 100, "page[number]": 1},
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10,
                )
                if resp.status_code != 200:
                    continue
                for team in resp.json():
                    acronym = (team.get("acronym") or "").strip()
                    name = (team.get("name") or "").strip()
                    slug = (team.get("slug") or "").strip()
                    if acronym and name:
                        abbrevs[acronym.lower()] = name.lower()
                        count += 1
                    if slug and name:
                        abbrevs[slug.lower()] = name.lower()
                time.sleep(0.5)  # PandaScore rate limit
            except Exception as e:
                logger.debug("PandaScore teams fetch failed for %s: %s", game, e)
        logger.debug("PandaScore teams: %d abbreviations", count)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_market_matcher.py::TestAliasStore -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/market_matcher.py tests/test_market_matcher.py
git commit -m "feat: add AliasStore with 3-API background refresh + JSON cache"
```

---

### Task 5: Create market_matcher.py — match_batch function

**Files:**
- Modify: `src/market_matcher.py` — add `match_batch()` function
- Modify: `tests/test_market_matcher.py` — add match_batch tests

This is the core matching engine. 3 layers:
1. **Exact abbreviation**: scout entry `abbrev_a`/`abbrev_b` found in Polymarket slug tokens → confidence 1.0
2. **Normalized short name**: `team_matcher._normalize()` applied to both sides, then substring check in question/slug → confidence 0.9
3. **Fuzzy (rapidfuzz)**: `fuzz.token_sort_ratio` ≥ 80, minimum 4 chars → confidence 0.7-0.9

League context filter runs BEFORE matching to prevent cross-sport false positives (PHI = 76ers vs Eagles vs Phillies).

- [ ] **Step 1: Write tests for match_batch**

Add to `tests/test_market_matcher.py`:

```python
from dataclasses import dataclass


@dataclass
class FakeMarket:
    """Minimal market object for testing."""
    condition_id: str = "cond_123"
    question: str = ""
    slug: str = ""
    sport_tag: str = ""


class TestMatchBatch:
    """match_batch returns same format as scout_scheduler.match_markets_batch."""

    def test_exact_abbreviation_match(self):
        """Layer 1: abbreviation in slug matches scout entry abbreviation."""
        from src.market_matcher import match_batch, AliasStore

        store = AliasStore(cache_path=Path("/nonexistent"), auto_refresh=False)

        market = FakeMarket(
            question="Los Angeles Lakers vs Boston Celtics",
            slug="nba-lal-bos-2026-04-05",
            sport_tag="NBA",
        )
        entries = {
            "basketball_nba_LAL_BOS_20260405": {
                "scout_key": "basketball_nba_LAL_BOS_20260405",
                "team_a": "Los Angeles Lakers",
                "team_b": "Boston Celtics",
                "abbrev_a": "LAL",
                "abbrev_b": "BOS",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball",
                "league": "nba",
                "is_esports": False,
            }
        }

        results = match_batch([market], entries, store)
        assert len(results) == 1
        assert results[0]["market"] is market
        assert results[0]["scout_key"] == "basketball_nba_LAL_BOS_20260405"

    def test_esports_acronym_match(self):
        """Layer 1: PandaScore acronym matches esports slug."""
        from src.market_matcher import match_batch, AliasStore

        store = AliasStore(cache_path=Path("/nonexistent"), auto_refresh=False)

        market = FakeMarket(
            question="Fnatic vs Team Liquid - Winner",
            slug="val-fnc-tl-2026-04-05",
            sport_tag="valorant",
        )
        entries = {
            "esports_valorant_Fnatic_Team Liquid_20260405": {
                "scout_key": "esports_valorant_Fnatic_Team Liquid_20260405",
                "team_a": "Fnatic",
                "team_b": "Team Liquid",
                "abbrev_a": "FNC",
                "abbrev_b": "TL",
                "match_time": "2026-04-05T18:00:00+00:00",
                "sport": "",
                "league": "",
                "is_esports": True,
            }
        }

        results = match_batch([market], entries, store)
        assert len(results) == 1

    def test_no_cross_sport_match(self):
        """PHI abbreviation must NOT match across sports."""
        from src.market_matcher import match_batch, AliasStore

        store = AliasStore(cache_path=Path("/nonexistent"), auto_refresh=False)

        # NBA market
        market = FakeMarket(
            question="Philadelphia 76ers vs Miami Heat",
            slug="nba-phi-mia-2026-04-05",
            sport_tag="NBA",
        )
        # NFL entry — should NOT match
        entries = {
            "football_nfl_Philadelphia Eagles_Dallas Cowboys_20260405": {
                "scout_key": "football_nfl_PHI_DAL_20260405",
                "team_a": "Philadelphia Eagles",
                "team_b": "Dallas Cowboys",
                "abbrev_a": "PHI",
                "abbrev_b": "DAL",
                "match_time": "2026-04-05T20:00:00+00:00",
                "sport": "football",
                "league": "nfl",
                "is_esports": False,
            }
        }

        results = match_batch([market], entries, store)
        assert len(results) == 0  # Must NOT match cross-sport

    def test_normalized_short_name_match(self):
        """Layer 2: short name from question matches entry."""
        from src.market_matcher import match_batch, AliasStore

        store = AliasStore(cache_path=Path("/nonexistent"), auto_refresh=False)

        market = FakeMarket(
            question="Will the Lakers beat the Celtics?",
            slug="will-lakers-beat-celtics",
        )
        entries = {
            "basketball_nba_LAL_BOS_20260405": {
                "scout_key": "basketball_nba_LAL_BOS_20260405",
                "team_a": "Los Angeles Lakers",
                "team_b": "Boston Celtics",
                "abbrev_a": "LAL",
                "abbrev_b": "BOS",
                "short_a": "Lakers",
                "short_b": "Celtics",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball",
                "league": "nba",
                "is_esports": False,
            }
        }

        results = match_batch([market], entries, store)
        assert len(results) == 1

    def test_doubleheader_picks_one(self):
        """Ambiguous doubleheader: same teams, 2 entries → only 1 matched."""
        from src.market_matcher import match_batch, AliasStore

        store = AliasStore(cache_path=Path("/nonexistent"), auto_refresh=False)

        market = FakeMarket(
            question="New York Yankees vs Boston Red Sox",
            slug="mlb-nyy-bos-2026-04-05",
            sport_tag="MLB",
        )
        entries = {
            "game1": {
                "scout_key": "game1",
                "team_a": "New York Yankees", "team_b": "Boston Red Sox",
                "abbrev_a": "NYY", "abbrev_b": "BOS",
                "match_time": "2026-04-05T17:00:00+00:00",
                "sport": "baseball", "league": "mlb", "is_esports": False,
            },
            "game2": {
                "scout_key": "game2",
                "team_a": "New York Yankees", "team_b": "Boston Red Sox",
                "abbrev_a": "NYY", "abbrev_b": "BOS",
                "match_time": "2026-04-05T22:00:00+00:00",
                "sport": "baseball", "league": "mlb", "is_esports": False,
            },
        }

        results = match_batch([market], entries, store)
        assert len(results) == 1  # Only first match, not both

    def test_return_format_matches_old_api(self):
        """Return format must be [{"market": m, "scout_entry": e, "scout_key": k}]."""
        from src.market_matcher import match_batch, AliasStore

        store = AliasStore(cache_path=Path("/nonexistent"), auto_refresh=False)

        market = FakeMarket(
            slug="val-fnc-tl-2026-04-05",
            question="Fnatic vs Team Liquid",
        )
        entries = {
            "key1": {
                "scout_key": "key1",
                "team_a": "Fnatic", "team_b": "Team Liquid",
                "abbrev_a": "FNC", "abbrev_b": "TL",
                "match_time": "2026-04-05T18:00:00+00:00",
                "is_esports": True, "sport": "", "league": "",
            }
        }

        results = match_batch([market], entries, store)
        assert len(results) == 1
        r = results[0]
        assert "market" in r
        assert "scout_entry" in r
        assert "scout_key" in r
        assert r["market"] is market
        assert r["scout_entry"]["team_a"] == "Fnatic"
        assert r["scout_key"] == "key1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_market_matcher.py::TestMatchBatch -v`
Expected: FAIL — `ImportError: cannot import name 'match_batch'`

- [ ] **Step 3: Implement match_batch and helper functions**

Add to `src/market_matcher.py` (after the AliasStore class):

```python
# ── Sport context detection from Polymarket slug/tags ────────────────────────

# Slug prefix → expected sport in scout entry
_SLUG_SPORT_HINTS: dict[str, str] = {
    "nba": "basketball", "wnba": "basketball", "cbb": "basketball",
    "nfl": "football", "cfb": "football",
    "mlb": "baseball", "nhl": "hockey",
    "soc": "soccer", "epl": "soccer", "ucl": "soccer",
    "ufc": "mma", "mma": "mma",
    "ten": "tennis", "atp": "tennis", "wta": "tennis",
    "gol": "golf", "pga": "golf",
    # Esports prefixes
    "cs": "esports", "csgo": "esports", "cs2": "esports",
    "val": "esports", "lol": "esports", "dota": "esports",
}

# Tag/sport_tag → expected sport
_TAG_SPORT_HINTS: dict[str, str] = {
    "nba": "basketball", "nfl": "football", "mlb": "baseball",
    "nhl": "hockey", "mls": "soccer", "epl": "soccer",
    "premier league": "soccer", "la liga": "soccer",
    "champions league": "soccer", "bundesliga": "soccer",
    "serie a": "soccer", "ligue 1": "soccer",
    "ufc": "mma",
    "counter-strike": "esports", "csgo": "esports", "cs2": "esports",
    "valorant": "esports", "league-of-legends": "esports",
    "lol": "esports", "dota-2": "esports", "dota2": "esports",
}


def _detect_sport_context(market) -> Optional[str]:
    """Detect sport context from market slug prefix or tags.

    Returns: sport string (e.g. "basketball", "esports") or None.
    """
    slug = (getattr(market, "slug", "") or "").lower()
    sport_tag = (getattr(market, "sport_tag", "") or "").lower()

    # 1. Check slug prefix (first token before first hyphen)
    prefix = slug.split("-")[0] if slug else ""
    if prefix in _SLUG_SPORT_HINTS:
        return _SLUG_SPORT_HINTS[prefix]

    # 2. Check sport_tag
    if sport_tag in _TAG_SPORT_HINTS:
        return _TAG_SPORT_HINTS[sport_tag]

    # 3. Check common keywords in slug
    for key, sport in _SLUG_SPORT_HINTS.items():
        if key in slug:
            return sport

    return None


def _entry_sport(entry: dict) -> str:
    """Get sport context from a scout entry."""
    if entry.get("is_esports"):
        return "esports"
    return entry.get("sport", "")


def _sports_compatible(market_sport: Optional[str], entry_sport: str) -> bool:
    """Check if market and entry are in the same sport domain.

    Prevents cross-sport matches (PHI = 76ers vs Eagles vs Phillies).
    If market sport is unknown, allow match (permissive fallback).
    """
    if market_sport is None:
        return True  # Unknown → allow
    if market_sport == "esports" and entry_sport == "esports":
        return True
    if market_sport == "esports" or entry_sport == "esports":
        return market_sport == entry_sport  # Don't cross esports/traditional
    # Traditional sports: must match
    if market_sport and entry_sport:
        return market_sport == entry_sport
    return True  # Unknown on either side → allow


def _extract_slug_tokens(slug: str) -> set[str]:
    """Extract meaningful tokens from Polymarket slug.

    'nba-lal-bos-2026-04-05' → {'nba', 'lal', 'bos'}
    Filters out date parts and very short tokens.
    """
    parts = slug.lower().split("-")
    tokens = set()
    for p in parts:
        # Skip date-like parts (4 digits or 1-2 digits)
        if p.isdigit():
            continue
        if len(p) >= 2:
            tokens.add(p)
    return tokens


def match_batch(
    markets: list,
    scout_queue: dict,
    alias_store: AliasStore,
) -> list[dict]:
    """Match Polymarket markets to scout entries. Drop-in replacement.

    3-layer matching:
        Layer 1: Exact abbreviation in slug tokens (confidence 1.0)
        Layer 2: Normalized short name in question/slug (confidence 0.9)
        Layer 3: Fuzzy rapidfuzz token_sort_ratio ≥ 80 (confidence 0.7-0.9)

    Args:
        markets: List of Gamma market objects (must have .question, .slug, .sport_tag)
        scout_queue: Dict of scout_key → entry dict (from ScoutScheduler._queue)
        alias_store: AliasStore instance for abbreviation resolution

    Returns:
        List of {"market": m, "scout_entry": entry, "scout_key": key}
        Same format as scout_scheduler.match_markets_batch().
    """
    matched: list[dict] = []
    used_keys: set[str] = set()

    for market in markets:
        question = (getattr(market, "question", "") or "").lower()
        slug = (getattr(market, "slug", "") or "").lower()
        slug_tokens = _extract_slug_tokens(slug)
        market_sport = _detect_sport_context(market)

        best_match: Optional[dict] = None
        best_confidence: float = 0.0
        best_key: str = ""
        # Track candidates for doubleheader detection
        candidates: list[tuple[str, dict, float]] = []

        for key, entry in scout_queue.items():
            if entry.get("entered") or key in used_keys:
                continue

            # ── Sport context filter ──
            e_sport = _entry_sport(entry)
            if not _sports_compatible(market_sport, e_sport):
                continue

            abbrev_a = (entry.get("abbrev_a") or "").lower()
            abbrev_b = (entry.get("abbrev_b") or "").lower()
            team_a = entry.get("team_a", "")
            team_b = entry.get("team_b", "")
            short_a = (entry.get("short_a") or "").lower()
            short_b = (entry.get("short_b") or "").lower()

            confidence = 0.0

            # ── Layer 1: Exact abbreviation in slug tokens ──
            if abbrev_a and abbrev_b:
                a_in_slug = abbrev_a in slug_tokens
                b_in_slug = abbrev_b in slug_tokens
                if a_in_slug and b_in_slug:
                    confidence = 1.0

            # ── Layer 2: Normalized short name in question/slug ──
            if confidence < 0.9:
                # Try short display names first (ESPN: "Lakers", "Celtics")
                if short_a and short_b:
                    a_found = short_a in question or short_a in slug
                    b_found = short_b in question or short_b in slug
                    if a_found and b_found:
                        confidence = max(confidence, 0.9)

                # Try team_matcher normalized names
                if confidence < 0.9:
                    norm_a = _normalize(team_a)
                    norm_b = _normalize(team_b)
                    if norm_a and norm_b:
                        a_found = norm_a in question or norm_a in slug
                        b_found = norm_b in question or norm_b in slug
                        if a_found and b_found:
                            confidence = max(confidence, 0.85)

            # ── Layer 3: Fuzzy matching (rapidfuzz) ──
            if confidence < 0.7:
                norm_a = _normalize(team_a)
                norm_b = _normalize(team_b)
                # Only fuzzy if names are long enough
                if len(norm_a) >= 4 and len(norm_b) >= 4:
                    # Check both orders (home/away might be swapped)
                    # Extract team-like tokens from question
                    best_fuzzy = 0.0

                    # Try abbreviation resolved names against question
                    resolved_a = alias_store.resolve(abbrev_a) if abbrev_a else norm_a
                    resolved_b = alias_store.resolve(abbrev_b) if abbrev_b else norm_b

                    score_a = max(
                        fuzz.token_sort_ratio(norm_a, question),
                        fuzz.partial_ratio(norm_a, question),
                        fuzz.token_sort_ratio(resolved_a, question) if resolved_a != norm_a else 0,
                    )
                    score_b = max(
                        fuzz.token_sort_ratio(norm_b, question),
                        fuzz.partial_ratio(norm_b, question),
                        fuzz.token_sort_ratio(resolved_b, question) if resolved_b != norm_b else 0,
                    )

                    # Both teams must have reasonable scores
                    if score_a >= 60 and score_b >= 60:
                        best_fuzzy = min(score_a, score_b) / 100.0
                        if best_fuzzy >= 0.70:
                            confidence = max(confidence, best_fuzzy)

            if confidence > 0.0:
                candidates.append((key, entry, confidence))

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = entry
                best_key = key

        # ── Doubleheader check ──
        if len(candidates) > 1 and best_confidence >= 0.6:
            # Check if multiple entries have same team pair
            team_pair = None
            if best_match:
                team_pair = frozenset([
                    best_match.get("team_a", "").lower(),
                    best_match.get("team_b", "").lower()
                ])
            same_pair = [
                (k, e, c) for k, e, c in candidates
                if frozenset([e.get("team_a", "").lower(), e.get("team_b", "").lower()]) == team_pair
            ]
            if len(same_pair) > 1:
                # Doubleheader: pick earliest match time
                same_pair.sort(key=lambda x: x[1].get("match_time", ""))
                best_key, best_match, best_confidence = same_pair[0]
                logger.debug(
                    "Doubleheader detected: %s — picking earliest (%s)",
                    team_pair, best_match.get("match_time", "")[:16]
                )

        # ── Threshold check ──
        if best_match and best_confidence >= 0.6:
            entry_copy = dict(best_match)
            entry_copy["matched"] = True
            entry_copy["match_confidence"] = best_confidence
            matched.append({
                "market": market,
                "scout_entry": entry_copy,
                "scout_key": best_key,
            })
            used_keys.add(best_key)
            logger.debug(
                "Matched [%.2f]: %s → %s vs %s",
                best_confidence, slug[:40],
                best_match.get("team_a", ""), best_match.get("team_b", "")
            )

    if matched:
        logger.info("market_matcher: %d/%d markets matched", len(matched), len(markets))

    return matched
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_market_matcher.py -v`
Expected: All tests PASS (both AliasStore and match_batch)

- [ ] **Step 5: Commit**

```bash
git add src/market_matcher.py tests/test_market_matcher.py
git commit -m "feat: add match_batch with 3-layer matching engine"
```

---

### Task 6: Wire market_matcher into entry_gate.py

**Files:**
- Modify: `src/entry_gate.py:335` — replace `match_markets_batch` with `market_matcher.match_batch`
- Modify: `src/entry_gate.py` (imports) — add market_matcher import

**IMPORTANT — "Önce Neyi Bozar?" check:**
- Line 335: `matched_markets = self.scout.match_markets_batch(markets)` — this is the ONLY call site.
- Return format is identical: `[{"market": m, "scout_entry": e, "scout_key": k}]`
- Lines 336-348 consume the result: `.sort(key=...)`, `mm["market"]`, `mm["scout_key"]` — all same keys.
- Enrichment pipeline (lines 389-449) doesn't use match data, only market objects.
- **Zero downstream breakage.**

- [ ] **Step 1: Write integration test**

Create `tests/test_entry_gate_matcher_integration.py`:

```python
"""Verify entry_gate uses market_matcher instead of match_markets_batch."""
import pytest
from unittest.mock import MagicMock, patch


def test_entry_gate_imports_market_matcher():
    """entry_gate must import from market_matcher, not use match_markets_batch directly."""
    import src.entry_gate as eg
    source = open(eg.__file__).read()
    assert "market_matcher" in source or "match_batch" in source, \
        "entry_gate should use market_matcher.match_batch"
```

- [ ] **Step 2: Add market_matcher import to entry_gate.py**

At the top of `src/entry_gate.py`, after existing imports, add:

```python
from src.market_matcher import match_batch as matcher_match_batch, AliasStore
```

- [ ] **Step 3: Initialize AliasStore in EntryGate.__init__**

Find the `__init__` method of the EntryGate class in `src/entry_gate.py` and add:

```python
        # Market matcher alias store (background refresh, JSON cache)
        self._alias_store = AliasStore()
```

- [ ] **Step 4: Replace match_markets_batch call**

In `src/entry_gate.py` line 335, change:

```python
# OLD:
            matched_markets = self.scout.match_markets_batch(markets)

# NEW:
            matched_markets = matcher_match_batch(
                markets, self.scout._queue, self._alias_store
            )
```

- [ ] **Step 5: Verify syntax and imports**

Run: `python -c "from src.entry_gate import EntryGate; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Run all tests**

Run: `python -m pytest tests/ -v --tb=short 2>&1 | head -60`
Expected: All tests pass, including new and existing tests.

- [ ] **Step 7: Commit**

```bash
git add src/entry_gate.py tests/test_entry_gate_matcher_integration.py
git commit -m "feat: wire market_matcher into entry_gate — drop-in replacement"
```

---

### Task 7: Update price_updater.py matching (bonus — same bug)

**Files:**
- Modify: `src/price_updater.py:100-111` — use team_matcher instead of primitive string matching

**IMPORTANT — "Önce Neyi Bozar?" check:**
- `price_updater.py` lines 100-111 has the SAME primitive matching as the old `match_markets_batch`.
- This is used for match time lookup, not market selection — lower risk.
- But same bug: "Los Angeles Lakers" not found in slug.

- [ ] **Step 1: Read full context of the matching code**

Read `src/price_updater.py` lines 85-115 to understand the function fully.

- [ ] **Step 2: Replace with team_matcher-based matching**

In `src/price_updater.py`, replace the matching block (lines ~96-111):

```python
# OLD:
            team_a = entry.get("team_a", "").lower()
            team_b = entry.get("team_b", "").lower()
            if not team_a or not team_b:
                continue
            # Match by team names in slug or question
            a_in = team_a in q_lower or team_a in s_lower
            b_in = team_b in q_lower or team_b in s_lower
            if a_in and b_in:
                return mt
            # 6-char abbreviated match (same as scout_scheduler.match_markets_batch)
            if len(team_a) >= 6 and len(team_b) >= 6:
                if team_a[:6] in s_lower and team_b[:6] in s_lower:
                    return mt

# NEW:
            team_a = entry.get("team_a", "").lower()
            team_b = entry.get("team_b", "").lower()
            abbrev_a = (entry.get("abbrev_a") or "").lower()
            abbrev_b = (entry.get("abbrev_b") or "").lower()
            if not team_a or not team_b:
                continue
            # Layer 1: Abbreviation in slug
            slug_tokens = set(s_lower.split("-"))
            if abbrev_a and abbrev_b and abbrev_a in slug_tokens and abbrev_b in slug_tokens:
                return mt
            # Layer 2: Full/short name in question or slug
            a_in = team_a in q_lower or team_a in s_lower
            b_in = team_b in q_lower or team_b in s_lower
            if a_in and b_in:
                return mt
            # Layer 3: Short name
            short_a = (entry.get("short_a") or "").lower()
            short_b = (entry.get("short_b") or "").lower()
            if short_a and short_b:
                if (short_a in q_lower or short_a in s_lower) and (short_b in q_lower or short_b in s_lower):
                    return mt
```

- [ ] **Step 3: Verify no breakage**

Run: `python -c "from src.price_updater import PriceUpdater; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/price_updater.py
git commit -m "fix: price_updater matching uses abbreviations (same fix as market_matcher)"
```

---

### Task 8: End-to-end smoke test

**Files:**
- No new files — run existing bot in dry_run mode to verify integration

- [ ] **Step 1: Verify all imports chain works**

```bash
python -c "
from src.market_matcher import AliasStore, match_batch
from src.entry_gate import EntryGate
from src.scout_scheduler import ScoutScheduler, _ESPORT_GAMES
assert 'csgo' in _ESPORT_GAMES
assert 'cs2' not in _ESPORT_GAMES
print('All imports OK')
print('AliasStore static abbrevs:', len(AliasStore(auto_refresh=False)._abbrevs))
"
```

Expected:
```
All imports OK
AliasStore static abbrevs: <number > 50>
```

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: All tests pass, 0 failures.

- [ ] **Step 3: Commit final state**

```bash
git add -A
git commit -m "test: end-to-end smoke test for market_matcher integration"
```

---

## Rollback Plan

If anything breaks in production:

1. In `src/entry_gate.py` line 335, revert to:
   ```python
   matched_markets = self.scout.match_markets_batch(markets)
   ```
2. Remove `from src.market_matcher import ...` from entry_gate.py imports
3. Remove `self._alias_store = AliasStore()` from `__init__`

This is a 3-line revert. Bot returns to old behavior instantly.

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Match rate | ~20% (6/30 markets) | ~85% (25/30 markets) |
| CS2 coverage | 0% | ~85% |
| ESPN coverage | ~30% | ~80% |
| New files | — | 1 (market_matcher.py) |
| Modified files | — | 3 (scout_scheduler, entry_gate, price_updater) |
| New dependency | — | rapidfuzz |
