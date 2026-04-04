# Odds API Maximum Coverage & Sharp Weighting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand Odds API usage to fetch multi-region/multi-market bookmaker data with adaptive throttling, sharp-bookmaker quality weighting (system-wide), soccer 3-way draw parsing, and a 24h time window — without breaking existing consumers.

**Architecture:** A new `bookmaker_weights.py` module provides per-bookmaker quality weights used by both `odds_api.py` and `sports_data.py`. `odds_api.py` gains a params builder keyed on sport type (soccer vs non-soccer), an adaptive throttle driven by Odds API response headers, Polymarket bookmaker filtering, and 3-way market parsing. `sports_data.py` reuses the same weighting module for ESPN odds averaging. `entry_gate.py` consumes the new `total_weight` field instead of `num_bookmakers`.

**Tech Stack:** Python 3.11, `requests`, `pytest`, `rapidfuzz` (existing), no new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-04-odds-api-maximum-coverage-design.md`

---

## File Map

| File | Role | Status |
|---|---|---|
| `src/matching/bookmaker_weights.py` | Single source of truth for bookmaker quality tiers + `get_bookmaker_weight()` | CREATE |
| `tests/test_bookmaker_weights.py` | Unit tests for weight tiers | CREATE |
| `src/matching/odds_sport_keys.py` | Add `is_soccer_key()` helper | MODIFY |
| `tests/test_odds_sport_keys.py` | Extend with `is_soccer_key()` tests | MODIFY |
| `src/odds_api.py` | Params builder, adaptive throttle, Polymarket filter, 3-way parsing, sharp weighting, small cleanups | MODIFY |
| `tests/test_odds_api_bugs.py` | Extend with new behavior tests | MODIFY |
| `src/sports_data.py` | Apply sharp weighting to ESPN odds averaging | MODIFY |
| `src/entry_gate.py` | One-line change: use `total_weight` instead of `num_bookmakers` | MODIFY |

---

## Task 1: Create `bookmaker_weights` module

**Files:**
- Create: `src/matching/bookmaker_weights.py`
- Test: `tests/test_bookmaker_weights.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bookmaker_weights.py`:

```python
"""Tests for bookmaker quality weight tiers."""


def test_sharp_bookmakers_get_weight_3():
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("pinnacle") == 3.0
    assert get_bookmaker_weight("betfair_ex_eu") == 3.0
    assert get_bookmaker_weight("betfair_ex_uk") == 3.0
    assert get_bookmaker_weight("matchbook") == 3.0


def test_reputable_bookmakers_get_weight_1_5():
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("bet365") == 1.5
    assert get_bookmaker_weight("williamhill") == 1.5
    assert get_bookmaker_weight("unibet_eu") == 1.5
    assert get_bookmaker_weight("unibet_uk") == 1.5
    assert get_bookmaker_weight("betclic") == 1.5
    assert get_bookmaker_weight("marathonbet") == 1.5


def test_standard_bookmakers_get_weight_1():
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("draftkings") == 1.0
    assert get_bookmaker_weight("fanduel") == 1.0
    assert get_bookmaker_weight("betmgm") == 1.0
    assert get_bookmaker_weight("caesars") == 1.0


def test_unknown_bookmaker_defaults_to_1():
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("some_random_book") == 1.0
    assert get_bookmaker_weight("") == 1.0


def test_case_insensitive():
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("Pinnacle") == 3.0
    assert get_bookmaker_weight("BET365") == 1.5
    assert get_bookmaker_weight("DraftKings") == 1.0


def test_display_name_normalization():
    """ESPN returns display names like 'Bet365' or 'William Hill' — handle these too."""
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("William Hill") == 1.5
    assert get_bookmaker_weight("Bet 365") == 1.5


def test_is_sharp_helper():
    from src.matching.bookmaker_weights import is_sharp
    assert is_sharp("pinnacle") is True
    assert is_sharp("betfair_ex_eu") is True
    assert is_sharp("bet365") is False
    assert is_sharp("draftkings") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bookmaker_weights.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'src.matching.bookmaker_weights'`

- [ ] **Step 3: Create the module**

Create `src/matching/bookmaker_weights.py`:

```python
"""Bookmaker quality weights — single source of truth.

Used by src/odds_api.py and src/sports_data.py to apply quality-weighted
averaging when combining bookmaker probabilities. Sharp bookmakers
(Pinnacle, Betfair Exchange) get 3x the weight of standard soft books.

Tier rationale:
- Tier 1 (3.0): Sharp books that don't restrict winning customers. Their
  closing lines are the industry benchmark for "true" probability.
- Tier 2 (1.5): Reputable European books with high limits and decent lines.
- Tier 3 (1.0): All other bookmakers (default).
"""
from __future__ import annotations

# Tier 1: Sharp bookmakers (professional-grade)
_SHARP: frozenset[str] = frozenset({
    "pinnacle",
    "betfair_ex_eu",
    "betfair_ex_uk",
    "matchbook",
})

# Tier 2: Reputable bookmakers (high limits, European)
_REPUTABLE: frozenset[str] = frozenset({
    "bet365",
    "williamhill",
    "unibet_eu",
    "unibet_uk",
    "betclic",
    "marathonbet",
})

SHARP_WEIGHT = 3.0
REPUTABLE_WEIGHT = 1.5
STANDARD_WEIGHT = 1.0


def _normalize(name: str) -> str:
    """Normalize a bookmaker key or display name to match our tier keys.

    Handles both Odds API keys ('bet365', 'betfair_ex_eu') and ESPN display
    names ('Bet365', 'William Hill', 'Bet 365') by lowercasing and stripping spaces.
    """
    if not name:
        return ""
    return name.lower().replace(" ", "")


def get_bookmaker_weight(name: str) -> float:
    """Return the quality weight for a bookmaker key or display name.

    Unknown bookmakers default to STANDARD_WEIGHT (1.0).
    """
    key = _normalize(name)
    if key in _SHARP:
        return SHARP_WEIGHT
    if key in _REPUTABLE:
        return REPUTABLE_WEIGHT
    return STANDARD_WEIGHT


def is_sharp(name: str) -> bool:
    """Return True if the bookmaker is in the sharp tier."""
    return _normalize(name) in _SHARP
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_bookmaker_weights.py -v`

Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/matching/bookmaker_weights.py tests/test_bookmaker_weights.py
git commit -m "feat(matching): add bookmaker_weights module with sharp/reputable/standard tiers"
```

---

## Task 2: Add `is_soccer_key` helper to odds_sport_keys

**Files:**
- Modify: `src/matching/odds_sport_keys.py`
- Test: `tests/test_odds_sport_keys.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_odds_sport_keys.py`:

```python
def test_is_soccer_key_true():
    from src.matching.odds_sport_keys import is_soccer_key
    assert is_soccer_key("soccer_epl") is True
    assert is_soccer_key("soccer_italy_serie_a") is True
    assert is_soccer_key("soccer_uefa_champs_league") is True


def test_is_soccer_key_false():
    from src.matching.odds_sport_keys import is_soccer_key
    assert is_soccer_key("baseball_mlb") is False
    assert is_soccer_key("basketball_nba") is False
    assert is_soccer_key("tennis_atp_miami_open") is False
    assert is_soccer_key("mma_mixed_martial_arts") is False


def test_is_soccer_key_empty_or_none():
    from src.matching.odds_sport_keys import is_soccer_key
    assert is_soccer_key("") is False
    assert is_soccer_key(None) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_odds_sport_keys.py -v -k is_soccer`

Expected: FAIL — `ImportError: cannot import name 'is_soccer_key'`

- [ ] **Step 3: Add the helper to `src/matching/odds_sport_keys.py`**

Append this function at the end of the file (after `resolve_odds_key`):

```python
def is_soccer_key(sport_key: Optional[str]) -> bool:
    """Return True if the Odds API sport key is a soccer league."""
    if not sport_key:
        return False
    return sport_key.startswith("soccer_")
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_odds_sport_keys.py -v`

Expected: PASS (original 10 tests + 3 new = 13 total)

- [ ] **Step 5: Commit**

```bash
git add src/matching/odds_sport_keys.py tests/test_odds_sport_keys.py
git commit -m "feat(matching): add is_soccer_key helper to odds_sport_keys"
```

---

## Task 3: Odds API params builder (regions, markets, commenceTime)

**Files:**
- Modify: `src/odds_api.py`
- Test: `tests/test_odds_api_bugs.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_odds_api_bugs.py`:

```python
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
    # Format: YYYY-MM-DDTHH:00:00Z
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_odds_api_bugs.py -v -k build_odds_params`

Expected: FAIL — `AttributeError: 'OddsAPIClient' object has no attribute '_build_odds_params'`

- [ ] **Step 3: Add the params builder method to `src/odds_api.py`**

In `src/odds_api.py`, add this import at the top near the existing `odds_sport_keys` import:

```python
from src.matching.odds_sport_keys import is_soccer_key, resolve_odds_key
```

(Replace the existing `from src.matching.odds_sport_keys import resolve_odds_key` line.)

Update the `datetime` import at the top of `src/odds_api.py`. Change:

```python
from datetime import datetime, timezone
```
to:
```python
from datetime import datetime, timedelta, timezone
```

Then add this method to the `OddsAPIClient` class, placing it right after `_match_tennis_key` (around line 199):

```python
def _build_odds_params(self, sport_key: str) -> dict:
    """Build query params for GET /sports/{key}/odds based on sport type.

    Soccer: 3 regions × 2 markets (h2h + h2h_3_way) = 6 credits per call
    Non-soccer: 3 regions × 1 market (h2h) = 3 credits per call

    commenceTimeFrom/To are rounded to the top of the hour so the cache key
    stays stable within each clock hour (otherwise cache would never hit).
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    time_from = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_to = (now + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

    markets = "h2h,h2h_3_way" if is_soccer_key(sport_key) else "h2h"

    return {
        "regions": "us,uk,eu",
        "markets": markets,
        "oddsFormat": "decimal",
        "commenceTimeFrom": time_from,
        "commenceTimeTo": time_to,
    }
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_odds_api_bugs.py -v -k build_odds_params`

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/odds_api.py tests/test_odds_api_bugs.py
git commit -m "feat(odds_api): add sport-aware params builder with 24h time window"
```

---

## Task 4: Odds API adaptive throttle

**Files:**
- Modify: `src/odds_api.py`
- Test: `tests/test_odds_api_bugs.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_odds_api_bugs.py`:

```python
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
    # 15000 / 20000 = 75%
    assert client._current_refresh_hours() == 3.0


def test_current_refresh_hours_high_usage():
    """Usage >= 90% -> 4h refresh."""
    client = _make_client()
    client._last_used = 19000
    client._last_remaining = 1000
    # 19000 / 20000 = 95%
    assert client._current_refresh_hours() == 4.0


def test_past_refresh_boundary_uses_dynamic_interval():
    """_past_refresh_boundary should respect _current_refresh_hours()."""
    import time
    client = _make_client()
    # Simulate 90% usage -> 4h refresh
    client._last_used = 18000
    client._last_remaining = 2000
    # Cache entry 3 hours old -> should NOT be past boundary (needs 4h)
    three_hours_ago = time.time() - (3 * 3600)
    assert client._past_refresh_boundary(three_hours_ago) is False
    # Cache entry 5 hours old -> should be past boundary
    five_hours_ago = time.time() - (5 * 3600)
    assert client._past_refresh_boundary(five_hours_ago) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_odds_api_bugs.py -v -k refresh_hours`

Expected: FAIL — `AttributeError: '_last_used'` or `_current_refresh_hours`

- [ ] **Step 3: Add throttle fields and methods to `src/odds_api.py`**

In `__init__` (around line 52-63), add two new instance variables after `self._requests_used = 0`:

```python
self._requests_used = 0
self._last_used: Optional[int] = None        # from x-requests-used header
self._last_remaining: Optional[int] = None   # from x-requests-remaining header
```

Add this method to the `OddsAPIClient` class, placing it right before `_past_refresh_boundary`:

```python
def _current_refresh_hours(self) -> float:
    """Return the refresh interval in hours based on current quota usage.

    Adaptive throttle:
    - 0-70% used: 2h refresh (fastest, freshest data)
    - 70-90% used: 3h refresh (slow down)
    - 90%+ used: 4h refresh (emergency preservation)

    Before the first API call, defaults to 2h (bootstrap).
    """
    if self._last_used is None or self._last_remaining is None:
        return 2.0
    total = self._last_used + self._last_remaining
    if total <= 0:
        return 2.0
    usage_pct = self._last_used / total
    if usage_pct >= 0.90:
        return 4.0
    if usage_pct >= 0.70:
        return 3.0
    return 2.0
```

Then replace the existing `_past_refresh_boundary` method (around line 278-283):

Find:
```python
def _past_refresh_boundary(self, cached_wall_ts: float) -> bool:
    """Check if enough time has passed since last fetch.

    Uses a simple interval (every 2h) instead of fixed UTC hours.
    """
    return (time.time() - cached_wall_ts) >= self._REFRESH_INTERVAL_HOURS * 3600
```

Replace with:
```python
def _past_refresh_boundary(self, cached_wall_ts: float) -> bool:
    """Check if enough time has passed since last fetch.

    Uses the adaptive refresh interval from _current_refresh_hours()
    so the bot slows down when the monthly budget is running low.
    """
    return (time.time() - cached_wall_ts) >= self._current_refresh_hours() * 3600
```

Inside `_api_request` (around line 300-303), update the header-reading block to also populate the new fields. Find:

```python
# Track remaining quota from headers
remaining_str = resp.headers.get("x-requests-remaining", "?")
used = resp.headers.get("x-requests-used", "?")
logger.info("Odds API quota: %s used, %s remaining", used, remaining_str)
self._requests_used += 1
record_call("odds_api")
```

Replace with:
```python
# Track remaining quota from headers (used by adaptive throttle)
remaining_str = resp.headers.get("x-requests-remaining", "?")
used_str = resp.headers.get("x-requests-used", "?")
logger.info("Odds API quota: %s used, %s remaining", used_str, remaining_str)
try:
    self._last_used = int(used_str)
except (ValueError, TypeError):
    pass
try:
    self._last_remaining = int(remaining_str)
except (ValueError, TypeError):
    pass
self._requests_used += 1
record_call("odds_api")
```

Also update the downstream reference `remaining_str` in the quota notification block (around line 307-323) — it already uses `remaining_str`, so just replace the `remaining` local with the new `self._last_remaining`:

Find:
```python
# Quota threshold notifications
remaining = int(remaining_str) if remaining_str != "?" else -1
if remaining >= 0:
    total = remaining + self._requests_used
```

Replace with:
```python
# Quota threshold notifications (use authoritative header values)
if self._last_used is not None and self._last_remaining is not None:
    total = self._last_used + self._last_remaining
```

And update the rest of the block — find:
```python
    if total > 0:
        usage_pct = self._requests_used / total
```

Replace with:
```python
    if total > 0:
        usage_pct = self._last_used / total
```

Finally, remove the now-unused `_REFRESH_INTERVAL_HOURS = 2` class attribute (around line 44) — but ONLY after verifying no other code references it. Run:

```bash
grep -rn "_REFRESH_INTERVAL_HOURS" "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent/src"
```

If `_discover_sport_key` (around line 239) still references it — keep the class attribute for now AND leave that line alone. The discover path uses it as a cache TTL, which is a separate concern from `_past_refresh_boundary`.

Actually, `_discover_sport_key` references `self._REFRESH_INTERVAL_HOURS * 3600` for events cache TTL. Keep that reference working by KEEPING the class attribute. Do NOT delete it.

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_odds_api_bugs.py -v`

Expected: PASS — all existing tests + 5 new throttle tests

- [ ] **Step 5: Commit**

```bash
git add src/odds_api.py tests/test_odds_api_bugs.py
git commit -m "feat(odds_api): adaptive refresh throttle based on monthly usage"
```

---

## Task 5: Odds API — Polymarket filter + sharp weighting + 3-way parsing

**Files:**
- Modify: `src/odds_api.py`
- Test: `tests/test_odds_api_bugs.py`

This is the core task. It rewrites the bookmaker extraction loop inside `get_bookmaker_odds()` to:
1. Skip `polymarket` bookmaker key
2. Apply sharp/reputable weights via `bookmaker_weights.get_bookmaker_weight()`
3. Prefer `h2h_3_way` market when present, fall back to `h2h`
4. Return new fields: `bookmaker_prob_draw`, `total_weight`, `has_sharp`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_odds_api_bugs.py`:

```python
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
    assert result["num_bookmakers"] == 1  # Only DraftKings counted
    assert "polymarket" not in [b.lower() for b in result["bookmakers"]]


def test_get_bookmaker_odds_sharp_weighted_average(monkeypatch):
    """Pinnacle (weight 3) should pull the average toward its value."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient(api_key="test")
    monkeypatch.setattr(client, "_detect_sport_key", lambda q, s, t: "basketball_nba")

    # Pinnacle says 64% home, DraftKings says 70% home
    # Weighted: (0.64 * 3 + 0.70 * 1) / 4 = 2.62/4 = 0.655
    # Unweighted would be 0.67 — this proves weighting is applied
    fake_events = [{
        "home_team": "Los Angeles Lakers",
        "away_team": "Boston Celtics",
        "bookmakers": [
            {"key": "pinnacle", "title": "Pinnacle", "markets": [{
                "key": "h2h", "outcomes": [
                    {"name": "Los Angeles Lakers", "price": 1.5625},  # ~64% implied
                    {"name": "Boston Celtics", "price": 2.7778},       # ~36% implied
                ]}]},
            {"key": "draftkings", "title": "DraftKings", "markets": [{
                "key": "h2h", "outcomes": [
                    {"name": "Los Angeles Lakers", "price": 1.4286},  # ~70% implied
                    {"name": "Boston Celtics", "price": 3.3333},       # ~30% implied
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
    # Weighted average should be closer to Pinnacle (0.64) than unweighted (0.67)
    assert 0.64 <= result["bookmaker_prob_a"] <= 0.67
    assert result["total_weight"] == 4.0  # 3 (pinnacle) + 1 (draftkings)
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

    # Real probabilities: home 48%, draw 27%, away 25%
    # Decimal odds: home 1/0.48=2.083, draw 1/0.27=3.704, away 1/0.25=4.00
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
    # Manchester City (home) win probability should be ~0.48 (not ~0.66)
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_odds_api_bugs.py -v -k "polymarket or sharp or draw or 3_way"`

Expected: FAIL — new fields don't exist, polymarket not filtered

- [ ] **Step 3: Add the import and rewrite the bookmaker loop**

In `src/odds_api.py`, add this import near the top (after the `odds_sport_keys` import):

```python
from src.matching.bookmaker_weights import get_bookmaker_weight, is_sharp
```

Also add at the top of the file (after other imports):

```python
from src.matching.pair_matcher import find_best_event_match, find_best_single_team_match, match_team
```

(This replaces the existing partial `pair_matcher` import and hoists `find_best_single_team_match` out of the function body.)

Remove the now-redundant inline import inside `get_bookmaker_odds` (around line 394):

```python
# DELETE this line:
from src.matching.pair_matcher import find_best_single_team_match
```

Also hoist the `import re` from inside `_extract_teams` (line 465) to the top of the file:

```python
import json
import logging
import os
import re
import time
```

Remove the local `import re` inside `_extract_teams`.

Now replace the entire `get_bookmaker_odds` method. Find the current implementation starting at `def get_bookmaker_odds(` (around line 356) and ending at the final `return { ... }` block (around line 461).

Replace with:

```python
def get_bookmaker_odds(
    self, question: str, slug: str, tags: List[str]
) -> Optional[Dict]:
    """Get bookmaker implied probability for a sports match.

    Applies quality-weighted averaging (sharp books 3x, reputable 1.5x, others 1x).
    For soccer, prefers h2h_3_way market and returns draw probability separately.
    Filters out `polymarket` bookmaker to prevent circular data.

    Returns dict with:
        team_a, team_b,
        bookmaker_prob_a, bookmaker_prob_b,
        bookmaker_prob_draw (float for soccer, None otherwise),
        num_bookmakers (int count, backward compat),
        total_weight (float, sum of quality weights),
        has_sharp (bool, true if Pinnacle/Betfair Exchange contributed),
        bookmakers (list of display names, first 5)
    Or None if not a sports market / no data.
    """
    sport_key = self._detect_sport_key(question, slug, tags)
    if not sport_key:
        return None

    params = self._build_odds_params(sport_key)
    events = self._get(f"/sports/{sport_key}/odds", params)
    if not events:
        return None

    team_a_name, team_b_name = self._extract_teams(question)
    if not team_a_name:
        return None

    if team_b_name:
        match_result = find_best_event_match(team_a_name, team_b_name, events)
        if not match_result:
            event_names = [(e.get("home_team", "?"), e.get("away_team", "?")) for e in events[:5]]
            logger.info("No Odds API match for '%s vs %s' in %d events. Sample: %s",
                        team_a_name, team_b_name, len(events), event_names)
            return None
        best_event, _ = match_result
        home_is_a, _, _ = match_team(team_a_name, best_event.get("home_team", ""))
    else:
        single_result = find_best_single_team_match(team_a_name, events)
        if not single_result:
            logger.info("No Odds API single-team match for '%s' in %d events",
                        team_a_name, len(events))
            return None
        best_event, _, team_a_is_home_flag = single_result
        home_is_a = team_a_is_home_flag
        if home_is_a:
            team_b_name = best_event.get("away_team", "")
        else:
            team_b_name = best_event.get("home_team", "")

    home_team = best_event.get("home_team", "")
    away_team = best_event.get("away_team", "")

    # Accumulators for quality-weighted average
    weighted_prob_a_sum = 0.0
    weighted_prob_b_sum = 0.0
    weighted_prob_draw_sum = 0.0
    draw_weight_total = 0.0
    total_weight = 0.0
    bookmaker_names: list[str] = []
    has_sharp_flag = False

    for bookmaker in best_event.get("bookmakers", []):
        bm_key = bookmaker.get("key", "")
        if bm_key == "polymarket":
            continue  # Prevent circular data — we read Polymarket directly

        parsed = self._parse_bookmaker_markets(
            bookmaker.get("markets", []), home_team, away_team
        )
        if parsed is None:
            continue

        home_prob, away_prob, draw_prob = parsed
        weight = get_bookmaker_weight(bm_key)

        if home_is_a:
            weighted_prob_a_sum += home_prob * weight
            weighted_prob_b_sum += away_prob * weight
        else:
            weighted_prob_a_sum += away_prob * weight
            weighted_prob_b_sum += home_prob * weight

        if draw_prob is not None:
            weighted_prob_draw_sum += draw_prob * weight
            draw_weight_total += weight

        total_weight += weight
        bookmaker_names.append(bookmaker.get("title", bm_key))
        if is_sharp(bm_key):
            has_sharp_flag = True

    if total_weight <= 0:
        return None

    avg_a = weighted_prob_a_sum / total_weight
    avg_b = weighted_prob_b_sum / total_weight
    avg_draw = (weighted_prob_draw_sum / draw_weight_total) if draw_weight_total > 0 else None

    return {
        "team_a": team_a_name,
        "team_b": team_b_name,
        "bookmaker_prob_a": round(avg_a, 3),
        "bookmaker_prob_b": round(avg_b, 3),
        "bookmaker_prob_draw": round(avg_draw, 3) if avg_draw is not None else None,
        "num_bookmakers": len(bookmaker_names),
        "total_weight": round(total_weight, 2),
        "has_sharp": has_sharp_flag,
        "bookmakers": bookmaker_names[:5],
    }
```

Now add the helper method `_parse_bookmaker_markets` right above `get_bookmaker_odds`:

```python
def _parse_bookmaker_markets(
    self, markets: list, home_team: str, away_team: str
) -> Optional[Tuple[float, float, Optional[float]]]:
    """Parse a bookmaker's markets list into (home_prob, away_prob, draw_prob).

    Prefers h2h_3_way (soccer, gives real draw probability) over h2h (2-way).
    Normalizes by summing outcomes to remove the vig.

    Returns None if no usable market/outcomes found.
    """
    # Prefer 3-way for soccer
    for market in markets:
        if market.get("key") != "h2h_3_way":
            continue
        home_odds = away_odds = draw_odds = None
        for outcome in market.get("outcomes", []):
            name = outcome.get("name", "")
            price = outcome.get("price", 0) or 0
            if name == home_team:
                home_odds = price
            elif name == away_team:
                away_odds = price
            elif name.lower() == "draw":
                draw_odds = price
        if home_odds and away_odds and draw_odds and home_odds > 1 and away_odds > 1 and draw_odds > 1:
            home_raw = 1.0 / home_odds
            away_raw = 1.0 / away_odds
            draw_raw = 1.0 / draw_odds
            total = home_raw + away_raw + draw_raw
            return (home_raw / total, away_raw / total, draw_raw / total)

    # Fall back to 2-way h2h
    for market in markets:
        if market.get("key") != "h2h":
            continue
        home_odds = away_odds = None
        for outcome in market.get("outcomes", []):
            name = outcome.get("name", "")
            price = outcome.get("price", 0) or 0
            if name == home_team:
                home_odds = price
            elif name == away_team:
                away_odds = price
        if home_odds and away_odds and home_odds > 1 and away_odds > 1:
            home_raw = 1.0 / home_odds
            away_raw = 1.0 / away_odds
            total = home_raw + away_raw
            return (home_raw / total, away_raw / total, None)

    return None
```

- [ ] **Step 4: Run all odds_api tests**

Run: `python -m pytest tests/test_odds_api_bugs.py -v`

Expected: PASS — all existing tests (15+) plus 5 new tests (20 total)

Also run existing mapping tests to ensure nothing broke:
Run: `python -m pytest tests/test_odds_sport_keys.py tests/test_bookmaker_weights.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/odds_api.py tests/test_odds_api_bugs.py
git commit -m "feat(odds_api): sharp weighting, 3-way draw parsing, Polymarket filter"
```

---

## Task 6: Odds API small cleanups (dead code removal)

**Files:**
- Modify: `src/odds_api.py`

- [ ] **Step 1: Verify `_hist_cache_ttl` is dead code**

Run:
```bash
grep -n "_hist_cache_ttl" "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent/src/odds_api.py"
```

Expected output: Only 1 match (the assignment itself in `__init__`). If there's more than 1 match, STOP and investigate — it may be used elsewhere.

Also check the project root:
```bash
grep -rn "_hist_cache_ttl" "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent/src" "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent/tests"
```

Expected: Only 1 match (the assignment). Safe to remove.

- [ ] **Step 2: Remove the dead line**

In `src/odds_api.py`, find in `__init__` (around line 58):

```python
self._cache_ttl = 28800  # 8h fallback TTL (tennis keys, etc.)
self._hist_cache_ttl = 28800  # 8 hour cache for historical
```

Delete only the second line:

```python
self._cache_ttl = 28800  # 8h fallback TTL (tennis keys, etc.)
```

- [ ] **Step 3: Run full odds_api test suite to verify nothing broke**

Run: `python -m pytest tests/test_odds_api_bugs.py tests/test_odds_sport_keys.py tests/test_bookmaker_weights.py -v`

Expected: PASS (all tests)

- [ ] **Step 4: Commit**

```bash
git add src/odds_api.py
git commit -m "chore(odds_api): remove unused _hist_cache_ttl field"
```

---

## Task 7: ESPN odds sharp weighting

**Files:**
- Modify: `src/sports_data.py`
- Test: `tests/test_sports_data_weighting.py` (CREATE)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sports_data_weighting.py`:

```python
"""Tests for ESPN odds sharp bookmaker weighting in sports_data.py."""
from unittest.mock import MagicMock, patch


def _make_odds_response(providers_odds: list) -> dict:
    """Build a fake ESPN odds API response from a list of (provider_name, home_odds, away_odds)."""
    return {
        "items": [
            {
                "provider": {"name": name},
                "homeTeamOdds": {"current": {"moneyLine": {"decimal": h}}},
                "awayTeamOdds": {"current": {"moneyLine": {"decimal": a}}},
            }
            for name, h, a in providers_odds
        ]
    }


def test_espn_odds_applies_sharp_weight(monkeypatch):
    """Pinnacle should be weighted 3x higher than DraftKings in ESPN averaging.

    ESPN actually returns DraftKings/Bet365 in most cases, but we test with
    hypothetical providers to verify the weighting logic.
    """
    from src.sports_data import ESPNClient

    client = ESPNClient()

    # DraftKings 70% home, Bet365 68% home
    # Weighted: (0.70*1 + 0.68*1.5) / 2.5 = 1.72/2.5 = 0.688
    # Unweighted: (0.70 + 0.68) / 2 = 0.69
    # These are close — but the total_weight field will differ
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = _make_odds_response([
        ("DraftKings", 1.4286, 3.3333),  # ~70% home
        ("Bet365", 1.4706, 3.125),        # ~68% home
    ])

    monkeypatch.setattr(client, "_find_espn_event", lambda *a, **k: (
        "evt1", "comp1", "Lakers", "Celtics", True
    ))
    monkeypatch.setattr("src.sports_data.requests.get", lambda *a, **k: fake_resp)
    monkeypatch.setattr(client, "_rate_limit", lambda: None)

    result = client.get_espn_odds("basketball", "nba", "Lakers", "Celtics")
    assert result is not None
    # total_weight = 1 (draftkings) + 1.5 (bet365) = 2.5
    assert result["total_weight"] == 2.5
    assert result["num_bookmakers"] == 2
    # Bet365 should pull the average slightly toward its value (0.68)
    # vs unweighted 0.69
    assert 0.685 <= result["bookmaker_prob_a"] <= 0.695


def test_espn_odds_has_sharp_false_for_retail_only(monkeypatch):
    """has_sharp should be False when no sharp book is in the ESPN response."""
    from src.sports_data import ESPNClient

    client = ESPNClient()

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = _make_odds_response([
        ("DraftKings", 1.90, 2.00),
    ])

    monkeypatch.setattr(client, "_find_espn_event", lambda *a, **k: (
        "evt1", "comp1", "Yankees", "Red Sox", True
    ))
    monkeypatch.setattr("src.sports_data.requests.get", lambda *a, **k: fake_resp)
    monkeypatch.setattr(client, "_rate_limit", lambda: None)

    result = client.get_espn_odds("baseball", "mlb", "Yankees", "Red Sox")
    assert result is not None
    assert result["has_sharp"] is False
    assert result["total_weight"] == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sports_data_weighting.py -v`

Expected: FAIL — `total_weight` / `has_sharp` not in return dict

- [ ] **Step 3: Modify `get_espn_odds` in `src/sports_data.py`**

Add the import near the top of `sports_data.py` (after `from src.matching.pair_matcher import match_team`):

```python
from src.matching.bookmaker_weights import get_bookmaker_weight, is_sharp
```

Now modify the bookmaker loop inside `get_espn_odds`. Find this block (around line 1253-1315):

```python
# Parse odds from all providers
probs_a: list[float] = []
probs_b: list[float] = []
provider_names: list[str] = []

for item in odds_data.get("items", []):
    provider_name = item.get("provider", {}).get("name", "ESPN")
    home_odds = away_odds = None
    # ... [existing parsing logic] ...

    if team_a_is_home:
        probs_a.append(home_prob)
        probs_b.append(away_prob)
    else:
        probs_a.append(away_prob)
        probs_b.append(home_prob)
    provider_names.append(provider_name)

if not probs_a:
    return None

avg_a = sum(probs_a) / len(probs_a)
avg_b = sum(probs_b) / len(probs_b)

logger.info("ESPN odds: %s %.0f%% vs %s %.0f%% (%d providers: %s)",
             team_a_name, avg_a * 100, team_b_name, avg_b * 100,
             len(probs_a), ", ".join(provider_names))

return {
    "team_a": team_a_name,
    "team_b": team_b_name,
    "bookmaker_prob_a": round(avg_a, 3),
    "bookmaker_prob_b": round(avg_b, 3),
    "num_bookmakers": len(probs_a),
    "bookmakers": provider_names[:5],
    "source": "espn",
}
```

Replace with:

```python
# Parse odds from all providers with quality-weighted averaging
weighted_a_sum = 0.0
weighted_b_sum = 0.0
total_weight = 0.0
num_providers = 0
provider_names: list[str] = []
has_sharp_flag = False

for item in odds_data.get("items", []):
    provider_name = item.get("provider", {}).get("name", "ESPN")
    home_odds = away_odds = None

    # Try DraftKings-style structure (current.moneyLine.decimal)
    home_block = item.get("homeTeamOdds", {})
    away_block = item.get("awayTeamOdds", {})

    current_home = home_block.get("current", {}).get("moneyLine", {})
    current_away = away_block.get("current", {}).get("moneyLine", {})

    if current_home.get("decimal") and current_away.get("decimal"):
        home_odds = float(current_home["decimal"])
        away_odds = float(current_away["decimal"])
    else:
        # Bet365-style: odds.value in awayTeamOdds/homeTeamOdds
        h_odds_block = home_block.get("odds", {})
        a_odds_block = away_block.get("odds", {})
        if h_odds_block.get("value") and a_odds_block.get("value"):
            home_odds = float(h_odds_block["value"])
            away_odds = float(a_odds_block["value"])

    if not home_odds or not away_odds or home_odds <= 1.0 or away_odds <= 1.0:
        continue

    # Convert decimal odds to implied probability (remove vig)
    home_prob = 1.0 / home_odds
    away_prob = 1.0 / away_odds
    total = home_prob + away_prob
    home_prob /= total
    away_prob /= total

    weight = get_bookmaker_weight(provider_name)

    if team_a_is_home:
        weighted_a_sum += home_prob * weight
        weighted_b_sum += away_prob * weight
    else:
        weighted_a_sum += away_prob * weight
        weighted_b_sum += home_prob * weight

    total_weight += weight
    num_providers += 1
    provider_names.append(provider_name)
    if is_sharp(provider_name):
        has_sharp_flag = True

if total_weight <= 0:
    return None

avg_a = weighted_a_sum / total_weight
avg_b = weighted_b_sum / total_weight

logger.info("ESPN odds: %s %.0f%% vs %s %.0f%% (%d providers, weight=%.1f: %s)",
             team_a_name, avg_a * 100, team_b_name, avg_b * 100,
             num_providers, total_weight, ", ".join(provider_names))

return {
    "team_a": team_a_name,
    "team_b": team_b_name,
    "bookmaker_prob_a": round(avg_a, 3),
    "bookmaker_prob_b": round(avg_b, 3),
    "num_bookmakers": num_providers,
    "total_weight": round(total_weight, 2),
    "has_sharp": has_sharp_flag,
    "bookmakers": provider_names[:5],
    "source": "espn",
}
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_sports_data_weighting.py -v`

Expected: PASS (2 tests)

Also run a quick sanity check — does `sports_data.py` still import cleanly?

Run: `python -c "from src.sports_data import ESPNClient; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/sports_data.py tests/test_sports_data_weighting.py
git commit -m "feat(sports_data): apply sharp bookmaker weighting to ESPN odds averaging"
```

---

## Task 8: Entry gate — use total_weight when combining anchors

**Files:**
- Modify: `src/entry_gate.py`

- [ ] **Step 1: Read the current block**

Open `src/entry_gate.py` and locate the block around line 656-685 where Odds API + ESPN results are combined into `_odds_probs`.

Current code (approximate):

```python
# Source 1: Odds API (paid, multi-bookmaker average)
if not _is_esports_mkt and self.odds_api.available:
    try:
        _mkt_odds = self.odds_api.get_bookmaker_odds(
            market.question, market.slug or "", market.tags or []
        )
        if _mkt_odds and _mkt_odds.get("bookmaker_prob_a") is not None:
            _odds_probs.append((
                _mkt_odds["bookmaker_prob_a"],
                _mkt_odds.get("num_bookmakers", 1),
            ))
    except Exception:
        pass

# Source 2: ESPN odds (free, cached from discovery phase -- no extra API call)
_espn_odds = self._espn_odds_cache.get(cid)
if _espn_odds and _espn_odds.get("bookmaker_prob_a") is not None:
    _odds_probs.append((
        _espn_odds["bookmaker_prob_a"],
        _espn_odds.get("num_bookmakers", 1),
    ))
```

- [ ] **Step 2: Update both appends to use total_weight**

Replace both append calls. Change `num_bookmakers` to `total_weight` (with `num_bookmakers` as fallback for backward compat if total_weight is missing):

```python
# Source 1: Odds API (paid, multi-bookmaker average)
if not _is_esports_mkt and self.odds_api.available:
    try:
        _mkt_odds = self.odds_api.get_bookmaker_odds(
            market.question, market.slug or "", market.tags or []
        )
        if _mkt_odds and _mkt_odds.get("bookmaker_prob_a") is not None:
            _odds_probs.append((
                _mkt_odds["bookmaker_prob_a"],
                _mkt_odds.get("total_weight") or _mkt_odds.get("num_bookmakers", 1),
            ))
    except Exception:
        pass

# Source 2: ESPN odds (free, cached from discovery phase -- no extra API call)
_espn_odds = self._espn_odds_cache.get(cid)
if _espn_odds and _espn_odds.get("bookmaker_prob_a") is not None:
    _odds_probs.append((
        _espn_odds["bookmaker_prob_a"],
        _espn_odds.get("total_weight") or _espn_odds.get("num_bookmakers", 1),
    ))
```

The `or` fallback ensures that if an unexpected code path provides an old-format dict (no `total_weight`), we gracefully degrade to the old count-based weighting instead of crashing.

- [ ] **Step 3: Verify import chain**

Run: `python -c "from src.agent import Agent; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest tests/test_odds_api_bugs.py tests/test_odds_sport_keys.py tests/test_bookmaker_weights.py tests/test_sports_data_weighting.py -v`

Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/entry_gate.py
git commit -m "feat(entry_gate): use total_weight for bookmaker anchor combination"
```

---

## Task 9: Final integration verification

**Files:** None (verification only)

- [ ] **Step 1: Full test sweep**

Run: `python -m pytest tests/ -v --tb=short`

Expected: All tests pass. Any pre-existing failures unrelated to odds/bookmaker are acceptable but must be noted.

- [ ] **Step 2: Full import sweep**

Run each of these to ensure no import cycles or syntax errors:

```bash
python -c "from src.agent import Agent; print('agent OK')"
python -c "from src.odds_api import OddsAPIClient; print('odds_api OK')"
python -c "from src.sports_data import ESPNClient; print('sports_data OK')"
python -c "from src.entry_gate import EntryGate; print('entry_gate OK')"
python -c "from src.matching.bookmaker_weights import get_bookmaker_weight, is_sharp; print('weights OK')"
python -c "from src.matching.odds_sport_keys import is_soccer_key, resolve_odds_key; print('sport_keys OK')"
```

Expected: All print their OK lines with no errors.

- [ ] **Step 3: Budget math sanity check**

Manually walk through:

1. `_build_odds_params("soccer_epl")` → `markets=h2h,h2h_3_way`, `regions=us,uk,eu` → 6 credits
2. `_build_odds_params("baseball_mlb")` → `markets=h2h`, `regions=us,uk,eu` → 3 credits
3. `_current_refresh_hours()` with `_last_used=0, _last_remaining=None` → returns 2.0 (bootstrap)
4. `_current_refresh_hours()` with `_last_used=14000, _last_remaining=6000` → returns 3.0 (70%)
5. `_current_refresh_hours()` with `_last_used=19000, _last_remaining=1000` → returns 4.0 (95%)

All must match expected values — these are already covered by tests but double-check manually.

- [ ] **Step 4: Verify zero dead code**

Run:

```bash
grep -rn "_hist_cache_ttl" "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent/src"
grep -rn "_SPORT_KEYS\s*=\s*{}" "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent/src"
grep -rn "_QUESTION_SPORT_KEYS\s*=\s*{}" "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent/src"
```

Expected: No matches for any of these (all dead code removed).

- [ ] **Step 5: Commit any final cleanup**

If the above steps revealed no issues, no commit needed. If anything showed up, address and commit:

```bash
git add -A
git commit -m "chore: post-implementation cleanup from integration sweep"
```

---

## Summary

After all 9 tasks complete, the system will have:

- Multi-region (us/uk/eu) Odds API coverage for all sport keys
- Soccer `h2h_3_way` market giving correct win/draw/loss probabilities
- Adaptive 2h/3h/4h throttle keeping monthly credits under 20K
- 24h `commenceTime` window trimming irrelevant events
- Polymarket bookmaker filtered out of averages (no circular data)
- Quality-weighted averaging: Pinnacle 3x, Bet365 1.5x, others 1x
- ESPN odds using the same weighting as Odds API
- `entry_gate.py` combining Odds API + ESPN by total_weight
- Zero dead code (`_hist_cache_ttl` removed)
- Zero inline imports (`re`, `find_best_single_team_match` hoisted)
- ~20 new unit tests covering all new behavior
- All existing tests still passing
