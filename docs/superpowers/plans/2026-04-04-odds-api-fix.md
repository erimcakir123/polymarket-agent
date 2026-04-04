# Odds API Sport Key Resolution Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 bugs in `src/odds_api.py` so that soccer markets (and all other sports) correctly resolve to Odds API sport keys and fetch bookmaker odds — including single-team Polymarket questions like "Will Ajax win?"

**Architecture:** Create a new mapping module `src/matching/odds_sport_keys.py` that maps Polymarket slug prefixes and Gamma tags to Odds API sport keys (reusing the same pattern as `_SPORT_LEAGUES` in `sports_data.py`). Fix `_discover_sport_key()` to require both-team match and prioritize by sport group. Fix `_extract_teams()` and `get_bookmaker_odds()` to support single-team questions. Existing `_match_tennis_key()` stays untouched.

**Tech Stack:** Python 3.11, requests, existing `src/matching/pair_matcher.py`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/matching/odds_sport_keys.py` | **Create** | Polymarket slug/tag → Odds API sport key mapping (single source of truth) |
| `src/odds_api.py` | **Modify** | Import from new module, fix `_detect_sport_key()`, `_discover_sport_key()`, `_extract_teams()`, `get_bookmaker_odds()` |
| `tests/test_odds_sport_keys.py` | **Create** | Unit tests for mapping module |
| `tests/test_odds_api_bugs.py` | **Create** | Regression tests for all 4 bugs |

---

### Task 1: Create `odds_sport_keys.py` mapping module

**Files:**
- Create: `src/matching/odds_sport_keys.py`
- Test: `tests/test_odds_sport_keys.py`

This module maps Polymarket slug prefixes AND Gamma series tags to The Odds API sport keys. It consolidates what was empty `_SPORT_KEYS` and `_QUESTION_SPORT_KEYS` dicts in `odds_api.py`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_odds_sport_keys.py`:

```python
"""Tests for Polymarket -> Odds API sport key mapping."""
import pytest


def test_slug_prefix_to_odds_key_soccer():
    from src.matching.odds_sport_keys import slug_to_odds_key
    # Polymarket slug prefixes for major soccer leagues
    assert slug_to_odds_key("epl") == "soccer_epl"
    assert slug_to_odds_key("lal") == "soccer_spain_la_liga"
    assert slug_to_odds_key("bun") == "soccer_germany_bundesliga"
    assert slug_to_odds_key("sea") == "soccer_italy_serie_a"
    assert slug_to_odds_key("fl1") == "soccer_france_ligue_one"
    assert slug_to_odds_key("ere") == "soccer_netherlands_eredivisie"
    assert slug_to_odds_key("mls") == "soccer_usa_mls"
    assert slug_to_odds_key("ucl") == "soccer_uefa_champs_league"
    assert slug_to_odds_key("spl") == "soccer_saudi_arabia_pro_league"
    assert slug_to_odds_key("arg") == "soccer_argentina_primera_division"


def test_slug_prefix_to_odds_key_american():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("mlb") == "baseball_mlb"
    assert slug_to_odds_key("nba") == "basketball_nba"
    assert slug_to_odds_key("nhl") == "icehockey_nhl"
    assert slug_to_odds_key("nfl") == "americanfootball_nfl"


def test_slug_prefix_to_odds_key_mma():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("ufc") == "mma_mixed_martial_arts"


def test_slug_prefix_unknown_returns_none():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("xyz999") is None
    assert slug_to_odds_key("") is None


def test_tag_to_odds_key_soccer():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("premier-league") == "soccer_epl"
    assert tag_to_odds_key("la-liga") == "soccer_spain_la_liga"
    assert tag_to_odds_key("serie-a") == "soccer_italy_serie_a"
    assert tag_to_odds_key("bundesliga") == "soccer_germany_bundesliga"
    assert tag_to_odds_key("ligue-1") == "soccer_france_ligue_one"
    assert tag_to_odds_key("eredivisie") == "soccer_netherlands_eredivisie"
    assert tag_to_odds_key("champions-league") == "soccer_uefa_champs_league"
    assert tag_to_odds_key("saudi-professional-league") == "soccer_saudi_arabia_pro_league"


def test_tag_to_odds_key_strips_year_suffix():
    from src.matching.odds_sport_keys import tag_to_odds_key
    # Polymarket tags often have year suffixes like "serie-a-2025"
    assert tag_to_odds_key("serie-a-2025") == "soccer_italy_serie_a"
    assert tag_to_odds_key("la-liga-2025") == "soccer_spain_la_liga"
    assert tag_to_odds_key("ligue-1-2025") == "soccer_france_ligue_one"


def test_tag_unknown_returns_none():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("unknown-league-xyz") is None
    assert tag_to_odds_key("") is None


def test_resolve_odds_key_prefers_slug():
    from src.matching.odds_sport_keys import resolve_odds_key
    # slug prefix match takes priority over tags
    result = resolve_odds_key(slug="epl-ars-che-2026-04-04", tags=["premier-league"])
    assert result == "soccer_epl"


def test_resolve_odds_key_falls_back_to_tags():
    from src.matching.odds_sport_keys import resolve_odds_key
    # Unknown slug prefix -> fall back to tag
    result = resolve_odds_key(slug="xxx-ars-che-2026-04-04", tags=["premier-league"])
    assert result == "soccer_epl"


def test_resolve_odds_key_no_match():
    from src.matching.odds_sport_keys import resolve_odds_key
    result = resolve_odds_key(slug="xxx-yyy", tags=["unknown-tag"])
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_odds_sport_keys.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.matching.odds_sport_keys'`

- [ ] **Step 3: Write the mapping module**

Create `src/matching/odds_sport_keys.py`:

```python
"""Polymarket slug/tag -> The Odds API sport key mapping.

Single source of truth for resolving Polymarket market identifiers
to Odds API sport keys. Used by odds_api.py for sport detection.

Odds API sport keys from: https://the-odds-api.com/sports-odds-data/sports-apis.html
Polymarket slug prefixes from: src/matching/sport_classifier.py
Polymarket Gamma tags from: src/sports_data.py _SERIES_TO_ESPN
"""
from __future__ import annotations

import re
from typing import Optional

# ── Polymarket slug prefix -> Odds API sport key ─────────────────────────
# Slug prefix = first segment of slug before first "-"
# e.g. "epl-ars-che-2026-04-04" -> prefix "epl"
_SLUG_TO_ODDS: dict[str, str] = {
    # American sports
    "mlb": "baseball_mlb",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
    "nfl": "americanfootball_nfl",
    "cfb": "americanfootball_ncaaf",
    "cbb": "basketball_nba",  # college -> NBA key as fallback (events won't match but safe)
    # MMA
    "ufc": "mma_mixed_martial_arts",
    # Soccer — England
    "epl": "soccer_epl",
    "efa": "soccer_fa_cup",
    "efl": "soccer_efl_champ",
    # Soccer — Spain
    "lal": "soccer_spain_la_liga",
    "cde": "soccer_spain_copa_del_rey",
    "cdr": "soccer_spain_copa_del_rey",
    # Soccer — Germany
    "bun": "soccer_germany_bundesliga",
    "bl2": "soccer_germany_bundesliga2",
    "dfb": "soccer_germany_dfb_pokal",
    # Soccer — Italy
    "sea": "soccer_italy_serie_a",
    "ser": "soccer_italy_serie_a",
    "itc": "soccer_italy_coppa_italia",
    # Soccer — France
    "fl1": "soccer_france_ligue_one",
    "fr2": "soccer_france_ligue_two",
    "cof": "soccer_france_coupe_de_france",
    # Soccer — Other Europe
    "ere": "soccer_netherlands_eredivisie",
    "por": "soccer_portugal_primeira_liga",
    "tur": "soccer_turkey_super_league",
    "sco": "soccer_spl",
    "bel": "soccer_belgium_first_div",
    "den": "soccer_denmark_superliga",
    "nor": "soccer_norway_eliteserien",
    "swe": "soccer_sweden_allsvenskan",
    "rus": "soccer_russia_premier_league",
    "gre": "soccer_greece_super_league",
    "aut": "soccer_austria_bundesliga",
    # Soccer — Americas
    "mls": "soccer_usa_mls",
    "nwsl": "soccer_usa_mls",  # fallback
    "arg": "soccer_argentina_primera_division",
    "bra": "soccer_brazil_campeonato",
    "bra2": "soccer_brazil_serie_b",
    "mex": "soccer_mexico_ligamx",
    "col": "soccer_chile_campeonato",  # Colombia has no Odds API key; Chile as fallback
    "col1": "soccer_chile_campeonato",
    "chi": "soccer_chile_campeonato",
    "chi1": "soccer_chile_campeonato",
    # Soccer — Asia/Middle East
    "spl": "soccer_saudi_arabia_pro_league",
    "kor": "soccer_korea_kleague1",
    "jpn": "soccer_japan_j_league",
    # Soccer — Cups/International
    "ucl": "soccer_uefa_champs_league",
    "uel": "soccer_uefa_europa_league",
    "uecl": "soccer_uefa_europa_conference_league",
    "lib": "soccer_conmebol_copa_libertadores",
    "sud": "soccer_conmebol_copa_sudamericana",
    "fif": "soccer_fifa_world_cup",
    "euro": "soccer_uefa_european_championship",
    "con": "soccer_conmebol_copa_libertadores",
    "gold": "soccer_concacaf_gold_cup",
    # Soccer — Australia
    "aus": "soccer_australia_aleague",
}

# ── Polymarket Gamma series tag -> Odds API sport key ────────────────────
# Tags come from Polymarket Gamma API "series" field as slugified strings.
# Year suffixes (e.g. "serie-a-2025") are stripped before lookup.
_TAG_TO_ODDS: dict[str, str] = {
    # Soccer
    "premier-league": "soccer_epl",
    "la-liga": "soccer_spain_la_liga",
    "la-liga-2": "soccer_spain_segunda_division",
    "bundesliga": "soccer_germany_bundesliga",
    "serie-a": "soccer_italy_serie_a",
    "ligue-1": "soccer_france_ligue_one",
    "eredivisie": "soccer_netherlands_eredivisie",
    "primeira-liga": "soccer_portugal_primeira_liga",
    "super-lig": "soccer_turkey_super_league",
    "scottish-premiership": "soccer_spl",
    "belgian-pro-league": "soccer_belgium_first_div",
    "danish-superliga": "soccer_denmark_superliga",
    "eliteserien": "soccer_norway_eliteserien",
    "allsvenskan": "soccer_sweden_allsvenskan",
    "greek-super-league": "soccer_greece_super_league",
    "austrian-bundesliga": "soccer_austria_bundesliga",
    "russian-premier-league": "soccer_russia_premier_league",
    "saudi-professional-league": "soccer_saudi_arabia_pro_league",
    "k-league": "soccer_korea_kleague1",
    "j1-league": "soccer_japan_j_league",
    "a-league": "soccer_australia_aleague",
    "liga-mx": "soccer_mexico_ligamx",
    "liga-betplay": "soccer_chile_campeonato",  # no direct Odds API key
    "brasileirao": "soccer_brazil_campeonato",
    "brazil-serie-b": "soccer_brazil_serie_b",
    "mls": "soccer_usa_mls",
    # Soccer — Cups
    "champions-league": "soccer_uefa_champs_league",
    "europa-league": "soccer_uefa_europa_league",
    "conference-league": "soccer_uefa_europa_conference_league",
    "copa-libertadores": "soccer_conmebol_copa_libertadores",
    "copa-sudamericana": "soccer_conmebol_copa_sudamericana",
    "fa-cup": "soccer_fa_cup",
    "efl-cup": "soccer_england_efl_cup",
    "dfb-pokal": "soccer_germany_dfb_pokal",
    "copa-del-rey": "soccer_spain_copa_del_rey",
    "coppa-italia": "soccer_italy_coppa_italia",
    "coupe-de-france": "soccer_france_coupe_de_france",
    # Non-soccer (tag fallbacks)
    "mlb": "baseball_mlb",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
    "nfl": "americanfootball_nfl",
}


def slug_to_odds_key(slug_prefix: str) -> Optional[str]:
    """Map a Polymarket slug prefix to an Odds API sport key.

    Args:
        slug_prefix: First segment of slug (e.g. "epl" from "epl-ars-che-2026-04-04")

    Returns:
        Odds API sport key or None if no mapping exists.
    """
    return _SLUG_TO_ODDS.get(slug_prefix.lower().strip()) if slug_prefix else None


def tag_to_odds_key(tag: str) -> Optional[str]:
    """Map a Polymarket Gamma series tag to an Odds API sport key.

    Strips year suffixes (e.g. "serie-a-2025" -> "serie-a") before lookup.

    Args:
        tag: Gamma series tag string.

    Returns:
        Odds API sport key or None if no mapping exists.
    """
    if not tag:
        return None
    tag_lower = tag.lower().strip()
    # Direct match first
    if tag_lower in _TAG_TO_ODDS:
        return _TAG_TO_ODDS[tag_lower]
    # Strip year suffix and retry
    stripped = re.sub(r"-\d{4}$", "", tag_lower)
    if stripped != tag_lower and stripped in _TAG_TO_ODDS:
        return _TAG_TO_ODDS[stripped]
    return None


def resolve_odds_key(slug: str, tags: list[str]) -> Optional[str]:
    """Resolve Odds API sport key from slug + tags. Slug wins, tags are fallback.

    Args:
        slug: Full Polymarket slug (e.g. "epl-ars-che-2026-04-04")
        tags: List of Gamma series tags

    Returns:
        Odds API sport key or None.
    """
    # 1. Slug prefix
    prefix = slug.split("-")[0].lower() if slug else ""
    result = slug_to_odds_key(prefix)
    if result:
        return result

    # 2. Tags (try each)
    for tag in (tags or []):
        result = tag_to_odds_key(tag)
        if result:
            return result

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_odds_sport_keys.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/matching/odds_sport_keys.py tests/test_odds_sport_keys.py
git commit -m "feat: add Polymarket -> Odds API sport key mapping module"
```

---

### Task 2: Wire mapping into `_detect_sport_key()` and fix `_discover_sport_key()`

**Files:**
- Modify: `src/odds_api.py:33-39` (imports), `src/odds_api.py:137-164` (`_detect_sport_key`), `src/odds_api.py:210-270` (`_discover_sport_key`)
- Test: `tests/test_odds_api_bugs.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_odds_api_bugs.py`:

```python
"""Regression tests for odds_api.py bugs (2026-04-04)."""
import pytest
from unittest.mock import patch, MagicMock

# ── Bug 1+2: Sport key detection ────────────────────────────────────────

def _make_client():
    """Create OddsAPIClient with no real API key (won't make live calls)."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient(api_key="")
    return client


def test_detect_sport_key_epl_from_slug():
    """Bug 1: _SPORT_KEYS was empty — EPL slug should resolve without API call."""
    client = _make_client()
    result = client._detect_sport_key(
        question="Will Arsenal beat Chelsea?",
        slug="epl-ars-che-2026-04-04",
        tags=["premier-league"],
    )
    assert result == "soccer_epl"


def test_detect_sport_key_serie_a_from_tag():
    """Bug 1: Tags should resolve when slug prefix is ambiguous."""
    client = _make_client()
    result = client._detect_sport_key(
        question="Will SS Lazio win on 2026-04-04?",
        slug="sea-laz-par-2026-04-04-laz",
        tags=["serie-a-2025"],
    )
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
    """Bug 2: Discovery should require BOTH teams to match, not just one."""
    client = _make_client()
    # Mock cached events with a Japanese baseball team that partially matches "Stars"
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
    # Should find NHL (both teams match), NOT NPB (only "Stars" partially matches)
    assert result == "icehockey_nhl"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_odds_api_bugs.py::test_detect_sport_key_epl_from_slug tests/test_odds_api_bugs.py::test_discover_sport_key_requires_both_teams -v`
Expected: FAIL — `test_detect_sport_key_epl_from_slug` returns None (empty dict), `test_discover_sport_key_requires_both_teams` returns `baseball_npb_japan` (wrong)

- [ ] **Step 3: Implement the fix in `odds_api.py`**

**3a. Replace empty dicts with imports (lines 33-39):**

Replace:
```python
# Dynamic sport key discovery replaces hardcoded mappings.
# _detect_sport_key() uses /v4/sports (FREE) to find active keys,
# then /v4/sports/{key}/events (FREE) to match teams.
_SPORT_KEYS: dict = {}

# Dynamic discovery replaces hardcoded keyword mappings.
_QUESTION_SPORT_KEYS: dict = {}
```

With:
```python
from src.matching.odds_sport_keys import resolve_odds_key
```

**3b. Rewrite `_detect_sport_key()` (lines 137-164):**

Replace the entire method with:
```python
    def _detect_sport_key(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Detect The Odds API sport key from market data.

        Priority: static mapping (fast) -> tennis dynamic -> discovery fallback.
        """
        # 1. Static mapping from slug prefix + tags (covers 95% of markets)
        static = resolve_odds_key(slug, tags)
        if static:
            return static

        # 2. Tennis: dynamic tournament key matching
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        q_lower = question.lower()
        if slug_prefix in ("atp", "tennis"):
            return self._match_tennis_key("atp", q_lower, slug)
        if slug_prefix == "wta":
            return self._match_tennis_key("wta", q_lower, slug)
        if "wta" in q_lower or "women" in q_lower:
            return self._match_tennis_key("wta", q_lower, slug)
        if "atp" in q_lower or "tennis" in q_lower:
            return self._match_tennis_key("atp", q_lower, slug)

        # 3. Dynamic discovery (expensive — last resort)
        team_a, team_b = self._extract_teams(question)
        return self._discover_sport_key(team_a, team_b)
```

**3c. Fix `_discover_sport_key()` (lines 210-270):**

Replace the event matching loop (lines 240-268) with:
```python
        # Search through cached events — require BOTH teams to match
        team_a_lower = team_a.lower() if team_a else ""
        team_b_lower = team_b.lower() if team_b else ""

        best_key = None
        best_match_count = 0  # 2 = both teams matched, 1 = only one

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

            for event in events:
                home = (event.get("home_team") or "").lower()
                away = (event.get("away_team") or "").lower()
                if not home or not away:
                    continue

                a_match = (team_a_lower and (
                    team_a_lower in home or home in team_a_lower or
                    team_a_lower in away or away in team_a_lower
                ))
                b_match = (team_b_lower and (
                    team_b_lower in home or home in team_b_lower or
                    team_b_lower in away or away in team_b_lower
                ))

                match_count = int(bool(a_match)) + int(bool(b_match))

                # Both teams match -> immediate return (best possible)
                if match_count == 2:
                    logger.info("Odds API discovery: '%s/%s' -> %s (both teams)", team_a, team_b, sk)
                    return sk

                # Single team match -> remember but keep looking for a 2-team match
                if match_count == 1 and match_count > best_match_count:
                    best_match_count = match_count
                    best_key = sk

        # Fallback: single team match (only if no 2-team match found anywhere)
        if best_key:
            logger.info("Odds API discovery: '%s/%s' -> %s (single team fallback)", team_a, team_b, best_key)
        return best_key
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_odds_api_bugs.py tests/test_odds_sport_keys.py -v`
Expected: ALL PASS

- [ ] **Step 5: Verify import works**

Run: `python -c "import src.odds_api; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/odds_api.py tests/test_odds_api_bugs.py
git commit -m "fix: wire sport key mapping into odds_api, fix discovery misclassification"
```

---

### Task 3: Support single-team questions in `get_bookmaker_odds()` and `_extract_teams()`

**Files:**
- Modify: `src/odds_api.py:350-376` (`get_bookmaker_odds`), `src/odds_api.py:444-474` (`_extract_teams`)
- Modify: `src/matching/pair_matcher.py:103-127` (add `find_best_single_team_match`)
- Test: `tests/test_odds_api_bugs.py` (append new tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_odds_api_bugs.py`:

```python
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

    # Mock _detect_sport_key to return a known key
    monkeypatch.setattr(client, "_detect_sport_key", lambda q, s, t: "soccer_netherlands_eredivisie")

    # Mock _get to return fake events with odds
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_odds_api_bugs.py::test_extract_teams_single_team_win tests/test_odds_api_bugs.py::test_get_bookmaker_odds_single_team -v`
Expected: FAIL — `_extract_teams` returns `(None, None)` for single-team, `get_bookmaker_odds` returns None

- [ ] **Step 3: Fix `_extract_teams()` to handle single-team questions**

Replace `_extract_teams` method in `src/odds_api.py` (lines 444-474):

```python
    def _extract_teams(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract team names from question. Returns (team_a, team_b) or (team_a, None) for single-team."""
        import re
        q = question.strip()
        # Strip sport/tour prefixes common in Polymarket questions
        _PREFIXES = [
            "ATP:", "WTA:", "Counter-Strike:", "CS2:", "CS:GO:",
            "Valorant:", "VALORANT:", "Dota 2:", "LoL:", "League of Legends:",
            "MLB:", "NBA:", "NHL:", "NFL:", "MMA:", "UFC:", "Boxing:",
            "Cricket:", "Rugby:", "Will",
        ]
        for pfx in _PREFIXES:
            if q.startswith(pfx):
                q = q[len(pfx):].strip()
                break
            if q.lower().startswith(pfx.lower()):
                q = q[len(pfx):].strip()
                break

        # Two-team: "vs" split
        for sep in [" vs. ", " vs ", " versus "]:
            if sep in q.lower():
                idx = q.lower().index(sep)
                a = q[:idx].strip()
                b = q[idx + len(sep):].strip()
                for char in ["(", " -"]:
                    if char in a:
                        a = a[:a.index(char)].strip()
                    if char in b:
                        b = b[:b.index(char)].strip()
                if a.lower().startswith("will "):
                    a = a[5:].strip()
                return a, b

        # Single-team: "Will X win" / "Will X beat Y"
        beat_match = re.search(
            r'(?:will\s+)?(?:the\s+)?(.+?)\s+(?:beat|defeat|win against|win over)\s+(?:the\s+)?(.+?)[\s?]*$',
            q, re.IGNORECASE,
        )
        if beat_match:
            return beat_match.group(1).strip(), beat_match.group(2).rstrip("?").strip()

        win_match = re.search(r'(?:will\s+)?(?:the\s+)?(.+?)\s+win\b', q, re.IGNORECASE)
        if win_match:
            team = win_match.group(1).strip()
            if len(team) >= 3:
                return team, None

        return None, None
```

- [ ] **Step 4: Add `find_best_single_team_match` to `pair_matcher.py`**

Append to `src/matching/pair_matcher.py` after `find_best_event_match`:

```python
def find_best_single_team_match(
    team: str,
    events: list[dict],
    home_key: str = "home_team",
    away_key: str = "away_team",
    min_confidence: float = 0.80,
) -> Optional[tuple[dict, float, bool]]:
    """Find best matching event for a SINGLE team name.

    Returns (event, confidence, team_is_home) or None.
    Used when Polymarket question has only one team (e.g. "Will Ajax win?").
    """
    best_event = None
    best_conf = 0.0
    best_is_home = True

    for event in events:
        home = event.get(home_key, "")
        away = event.get(away_key, "")
        if not home or not away:
            continue

        # Try matching against home team
        is_match_h, conf_h, _ = match_team(team, home)
        if is_match_h and conf_h > best_conf:
            best_conf = conf_h
            best_event = event
            best_is_home = True

        # Try matching against away team
        is_match_a, conf_a, _ = match_team(team, away)
        if is_match_a and conf_a > best_conf:
            best_conf = conf_a
            best_event = event
            best_is_home = False

    if best_event and best_conf >= min_confidence:
        return best_event, best_conf, best_is_home
    return None
```

- [ ] **Step 5: Fix `get_bookmaker_odds()` to handle single-team**

Replace the team extraction and event matching block in `get_bookmaker_odds()` (lines 372-384):

```python
        # Extract team names from question
        team_a_name, team_b_name = self._extract_teams(question)
        if not team_a_name:
            return None

        if team_b_name:
            # Two-team: use existing pair matcher
            result = find_best_event_match(team_a_name, team_b_name, events)
            if not result:
                event_names = [(e.get("home_team", "?"), e.get("away_team", "?")) for e in events[:5]]
                logger.info("No Odds API match for '%s vs %s' in %d events. Sample: %s",
                            team_a_name, team_b_name, len(events), event_names)
                return None
            best_event, match_conf = result
        else:
            # Single-team: find event containing this team
            from src.matching.pair_matcher import find_best_single_team_match
            result = find_best_single_team_match(team_a_name, events)
            if not result:
                logger.info("No Odds API single-team match for '%s' in %d events",
                            team_a_name, len(events))
                return None
            best_event, match_conf, team_a_is_home_flag = result
```

Also update the `home_is_a` logic below (lines 389-393) to use `team_a_is_home_flag` when available:

```python
        # Figure out which Polymarket team maps to home/away
        home_team = best_event.get("home_team", "")
        away_team = best_event.get("away_team", "")

        if team_b_name:
            home_is_a, _, _ = match_team(team_a_name, home_team)
        else:
            home_is_a = team_a_is_home_flag
            # Fill in team_b from event for return value
            team_b_name = away_team if home_is_a else home_team
```

- [ ] **Step 6: Run all tests**

Run: `python -m pytest tests/test_odds_api_bugs.py tests/test_odds_sport_keys.py -v`
Expected: ALL PASS

- [ ] **Step 7: Verify full import chain**

Run: `python -c "import src.odds_api; import src.matching.pair_matcher; print('OK')"`
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add src/odds_api.py src/matching/pair_matcher.py tests/test_odds_api_bugs.py
git commit -m "fix: support single-team questions in Odds API odds fetching"
```

---

### Task 4: Clean up dead code and remove unused imports

**Files:**
- Modify: `src/odds_api.py:27` (import line), remove old `_SPORT_KEYS` and `_QUESTION_SPORT_KEYS` references

- [ ] **Step 1: Remove old empty dicts and unused imports**

In `src/odds_api.py`, the old empty dicts at lines 33-39 should already be replaced in Task 2. Verify no remaining references to `_SPORT_KEYS` or `_QUESTION_SPORT_KEYS` exist in the file.

Run: `grep -n "_SPORT_KEYS\|_QUESTION_SPORT_KEYS" src/odds_api.py`
Expected: No output (all references removed)

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short 2>&1 | head -60`
Expected: All tests pass, no import errors

- [ ] **Step 3: Verify bot imports cleanly**

Run: `python -c "from src.agent import Agent; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/odds_api.py
git commit -m "chore: remove dead code from odds_api.py"
```

---

## Summary of Changes

| Bug | Root Cause | Fix | Files |
|-----|-----------|-----|-------|
| 1. Empty `_SPORT_KEYS` | Hardcoded dicts deleted, never replaced | New `odds_sport_keys.py` module with 60+ mappings | `odds_sport_keys.py`, `odds_api.py` |
| 2. Discovery misclassification | `a_match OR b_match` + random sport iteration | Require both-team match, single-team only as fallback | `odds_api.py` |
| 3. Single-team questions fail | `_extract_teams` + `get_bookmaker_odds` require both teams | Add "Will X win" pattern + `find_best_single_team_match` | `odds_api.py`, `pair_matcher.py` |
| 4. No soccer key mapping | 67 Odds API soccer keys, 0 mapped | Full slug+tag→key mapping in new module | `odds_sport_keys.py` |
