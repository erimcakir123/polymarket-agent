# Matcher Layer 0: Polymarket /teams Abbreviation Matching

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise the market-to-scout match rate from 14% to 95%+ by using Polymarket's own `/teams` endpoint to resolve slug abbreviations to team names, then matching those names against scout entries. Existing fuzzy layers 1-5 stay as fallback.

**Architecture:** New Layer 0 sits before all existing fuzzy layers. Parses slug tokens (e.g. `nhl-nj-mon` → `["nj", "mon"]`), looks them up in a cached copy of Polymarket's `/teams` API (which returns `{abbreviation: "nj", name: "Devils", alias: "Devils", league: "nhl"}`), then checks if both resolved names appear in the scout entry's `team_a`/`team_b` fields. This is a deterministic dict lookup — no fuzzy matching, no false positives.

**Tech Stack:** Python 3.11, requests, json file cache, pytest.

**What is NOT touched:** ESPN API, PandaScore API, Odds API, `pair_matcher.py`, `team_resolver.py`, exit logic, dashboard, WebSocket feed. Zero existing behaviour changes.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `src/matching/polymarket_teams.py` | **CREATE** | Fetch `/teams` endpoint, cache to disk, provide `resolve_abbreviation(abbr, league) -> name` |
| `src/matching/__init__.py` | **MODIFY** (~15 lines added before Layer 1) | Import teams resolver, run Layer 0 before fuzzy layers |
| `src/market_scanner.py` | **MODIFY** (~2 lines in `_parse_market`) | Extract `sportsMarketType` from raw market data, store on MarketData |
| `src/models.py` | **MODIFY** (1 line in MarketData) | Add `sports_market_type: str = ""` field |
| `tests/test_matcher_layer0.py` | **CREATE** | Unit tests for teams resolver + Layer 0 matching |

---

## Invariants

- Existing fuzzy layers 1-5 remain intact and run as fallback when Layer 0 doesn't match.
- `match_markets()` return format is unchanged: `[{"market": m, "scout_entry": e, "scout_key": k}]`.
- No changes to any file outside `src/matching/`, `src/market_scanner.py`, `src/models.py`, and tests.
- `/teams` endpoint is FREE (no auth needed, standard Gamma API).
- Cache refreshes once per day at most (teams don't change mid-day).

---

### Task 1: Polymarket Teams Fetcher + Cache

**Files:**
- Create: `src/matching/polymarket_teams.py`
- Test: `tests/test_matcher_layer0.py` (new file)

- [ ] **Step 1: Write the failing test**

Create `tests/test_matcher_layer0.py`:

```python
"""Tests for Polymarket /teams-based matcher Layer 0."""
from __future__ import annotations


class TestPolymarketTeamsCache:
    def test_resolve_known_abbreviation(self):
        from src.matching.polymarket_teams import PolymarketTeamsCache

        # Inject fake data to avoid live API call in tests
        cache = PolymarketTeamsCache()
        cache._abbr_to_name = {
            "nj": "Devils",
            "mon": "Canadiens",
            "bos": "Bruins",
            "pain": "paiN",
        }

        assert cache.resolve("nj") == "Devils"
        assert cache.resolve("mon") == "Canadiens"
        assert cache.resolve("pain") == "paiN"

    def test_resolve_unknown_returns_none(self):
        from src.matching.polymarket_teams import PolymarketTeamsCache

        cache = PolymarketTeamsCache()
        cache._abbr_to_name = {"nj": "Devils"}

        assert cache.resolve("xyz") is None
        assert cache.resolve("") is None

    def test_resolve_case_insensitive(self):
        from src.matching.polymarket_teams import PolymarketTeamsCache

        cache = PolymarketTeamsCache()
        cache._abbr_to_name = {"nj": "Devils"}

        assert cache.resolve("NJ") == "Devils"
        assert cache.resolve("Nj") == "Devils"

    def test_load_from_api_response(self):
        from src.matching.polymarket_teams import PolymarketTeamsCache

        fake_response = [
            {"id": 100630, "name": "Devils", "abbreviation": "nj", "alias": "Devils", "league": "nhl"},
            {"id": 100628, "name": "Canadiens", "abbreviation": "mon", "alias": "Canadiens", "league": "nhl"},
            {"id": 177234, "name": "paiN", "abbreviation": "pain", "alias": "paiN", "league": "csgo"},
        ]
        cache = PolymarketTeamsCache()
        cache._ingest_teams(fake_response)

        assert cache.resolve("nj") == "Devils"
        assert cache.resolve("mon") == "Canadiens"
        assert cache.resolve("pain") == "paiN"
        assert len(cache._abbr_to_name) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_matcher_layer0.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.matching.polymarket_teams'`

- [ ] **Step 3: Implement the teams fetcher**

Create `src/matching/polymarket_teams.py`:

```python
"""Polymarket /teams cache — resolves slug abbreviations to team names.

Polymarket's GET /teams endpoint returns all registered teams (sports + esports)
with {id, name, abbreviation, alias, league}. The `abbreviation` field matches
the slug tokens used in market slugs (e.g. "nj" in "nhl-nj-mon-2026-04-05").

Usage:
    cache = PolymarketTeamsCache()
    cache.refresh()  # fetches from API, caches to disk
    name = cache.resolve("nj")  # → "Devils"

The cache is refreshed at most once per day. Between refreshes, the disk cache
is read on bot startup so there's no cold-start API call.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GAMMA_TEAMS_URL = "https://gamma-api.polymarket.com/teams"
CACHE_FILE = Path("logs/polymarket_teams_cache.json")
REFRESH_INTERVAL = 24 * 3600  # 24 hours


class PolymarketTeamsCache:
    """Abbreviation → team name resolver backed by Polymarket /teams API."""

    def __init__(self) -> None:
        # abbreviation (lowercase) → name (original casing from API)
        self._abbr_to_name: dict[str, str] = {}
        self._last_refresh: float = 0.0
        self._load_disk_cache()

    def resolve(self, abbreviation: str) -> Optional[str]:
        """Return team name for a slug abbreviation, or None if unknown."""
        if not abbreviation:
            return None
        return self._abbr_to_name.get(abbreviation.lower())

    def refresh_if_stale(self) -> None:
        """Fetch fresh teams from API if cache is older than REFRESH_INTERVAL."""
        if time.time() - self._last_refresh < REFRESH_INTERVAL:
            return
        self._fetch_all_teams()

    def _ingest_teams(self, teams: list[dict]) -> None:
        """Load a list of team dicts into the lookup table."""
        for team in teams:
            abbr = (team.get("abbreviation") or "").lower().strip()
            name = team.get("name") or team.get("alias") or ""
            if abbr and name:
                self._abbr_to_name[abbr] = name

    def _fetch_all_teams(self) -> None:
        """Paginate through /teams endpoint and ingest all teams."""
        all_teams: list[dict] = []
        offset = 0
        page_size = 500  # API max per request

        while True:
            try:
                resp = requests.get(
                    GAMMA_TEAMS_URL,
                    params={"limit": page_size, "offset": offset},
                    timeout=15,
                )
                resp.raise_for_status()
                page = resp.json()
            except Exception as exc:
                logger.warning("Polymarket /teams fetch failed (offset=%d): %s", offset, exc)
                break

            if not page:
                break
            all_teams.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        if all_teams:
            self._abbr_to_name.clear()
            self._ingest_teams(all_teams)
            self._last_refresh = time.time()
            self._save_disk_cache(all_teams)
            logger.info("Polymarket teams cache refreshed: %d teams, %d abbreviations",
                        len(all_teams), len(self._abbr_to_name))

    def _load_disk_cache(self) -> None:
        """Load previously saved cache from disk (survives bot restarts)."""
        try:
            if not CACHE_FILE.exists():
                return
            raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            teams = raw.get("teams", [])
            ts = raw.get("timestamp", 0)
            if teams:
                self._ingest_teams(teams)
                self._last_refresh = ts
                logger.info("Polymarket teams loaded from disk: %d abbreviations", len(self._abbr_to_name))
        except Exception as exc:
            logger.debug("Could not load teams cache: %s", exc)

    def _save_disk_cache(self, teams: list[dict]) -> None:
        """Persist teams to disk for cold-start on next boot."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = CACHE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps({
                "teams": teams,
                "timestamp": time.time(),
                "count": len(teams),
            }), encoding="utf-8")
            tmp.replace(CACHE_FILE)
        except Exception as exc:
            logger.debug("Could not save teams cache: %s", exc)
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests/test_matcher_layer0.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/matching/polymarket_teams.py tests/test_matcher_layer0.py
git commit -m "feat(matching): Polymarket /teams cache for abbreviation resolution"
```

---

### Task 2: Layer 0 in matcher pipeline

**Files:**
- Modify: `src/matching/__init__.py` (add Layer 0 before existing Layer 1)
- Test: `tests/test_matcher_layer0.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_matcher_layer0.py`:

```python
class TestLayer0Matching:
    """Layer 0: slug abbreviation → /teams name → scout entry team_a/team_b."""

    def _make_market(self, slug="nhl-nj-mon-2026-04-05", question="Devils vs. Canadiens"):
        from src.models import MarketData
        return MarketData(
            condition_id="0x123", question=question,
            yes_price=0.5, no_price=0.5,
            yes_token_id="1", no_token_id="2",
            slug=slug, sport_tag="nhl",
        )

    def test_layer0_matches_nhl_by_abbreviation(self):
        from src.matching import match_markets
        from src.matching.polymarket_teams import PolymarketTeamsCache
        import src.matching as matcher_mod

        # Inject a fake teams cache
        fake_cache = PolymarketTeamsCache()
        fake_cache._abbr_to_name = {
            "nj": "Devils", "mon": "Canadiens",
        }
        matcher_mod._teams_cache = fake_cache

        market = self._make_market()
        scout_queue = {
            "hockey_nhl_New Jersey Devils_Montreal Canadiens_20260405": {
                "team_a": "New Jersey Devils",
                "team_b": "Montreal Canadiens",
                "sport": "hockey",
                "match_time": "2026-04-05T23:00:00Z",
            }
        }

        result = match_markets([market], scout_queue)
        assert len(result) == 1
        assert result[0]["market"].slug == "nhl-nj-mon-2026-04-05"
        assert result[0]["scout_entry"]["team_a"] == "New Jersey Devils"

    def test_layer0_matches_esports_csgo(self):
        from src.matching import match_markets
        from src.matching.polymarket_teams import PolymarketTeamsCache
        import src.matching as matcher_mod

        fake_cache = PolymarketTeamsCache()
        fake_cache._abbr_to_name = {
            "pain": "paiN", "gl1": "GamerLegion",
        }
        matcher_mod._teams_cache = fake_cache

        market = self._make_market(
            slug="cs2-pain-gl1-2026-04-06",
            question="Counter-Strike: paiN vs GamerLegion (BO3)",
        )
        scout_queue = {
            "csgo_paiN_GamerLegion_20260406": {
                "team_a": "paiN",
                "team_b": "GamerLegion",
                "sport": "",
                "match_time": "2026-04-06T15:00:00Z",
            }
        }

        result = match_markets([market], scout_queue)
        assert len(result) == 1

    def test_layer0_falls_through_to_fuzzy_if_no_teams_match(self):
        """If Layer 0 can't resolve abbreviations, old fuzzy layers should
        still attempt to match (fallback)."""
        from src.matching import match_markets
        from src.matching.polymarket_teams import PolymarketTeamsCache
        import src.matching as matcher_mod

        # Empty teams cache — Layer 0 will produce no match
        fake_cache = PolymarketTeamsCache()
        fake_cache._abbr_to_name = {}
        matcher_mod._teams_cache = fake_cache

        market = self._make_market(
            slug="nhl-nj-mon-2026-04-05",
            question="New Jersey Devils vs Montreal Canadiens",
        )
        scout_queue = {
            "hockey_nhl_New Jersey Devils_Montreal Canadiens_20260405": {
                "team_a": "New Jersey Devils",
                "team_b": "Montreal Canadiens",
                "abbrev_a": "",
                "abbrev_b": "",
                "short_a": "devils",
                "short_b": "canadiens",
                "sport": "hockey",
                "match_time": "2026-04-05T23:00:00Z",
            }
        }

        # Layer 0 fails (no abbreviation data), but Layer 3/4 (short name / full name
        # in question) should still match since question contains both full names.
        result = match_markets([market], scout_queue)
        assert len(result) == 1  # Fuzzy fallback caught it
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_matcher_layer0.py::TestLayer0Matching -v`
Expected: FAIL — `_teams_cache` attribute does not exist on module yet.

- [ ] **Step 3: Add Layer 0 to `match_markets()`**

In `src/matching/__init__.py`, add the import and module-level cache singleton after the existing `_resolver` singleton:

```python
from src.matching.polymarket_teams import PolymarketTeamsCache

# Module-level singletons (created on first call)
_resolver: Optional[TeamResolver] = None
_teams_cache: Optional[PolymarketTeamsCache] = None


def _get_teams_cache() -> PolymarketTeamsCache:
    global _teams_cache
    if _teams_cache is None:
        _teams_cache = PolymarketTeamsCache()
    return _teams_cache
```

Then inside `match_markets()`, right after the existing `slug_parts` and `slug_tokens` lines and before the `for key, entry in scout_queue.items():` loop, add the Layer 0 block:

```python
        # ── Layer 0: Polymarket /teams abbreviation lookup (deterministic) ──
        # Resolve slug tokens via Polymarket's own /teams endpoint. If both
        # tokens resolve to team names that appear in a scout entry's team_a
        # or team_b, it's a guaranteed match (confidence=1.0). This is the
        # fastest and most reliable matching path — no fuzzy logic involved.
        teams = _get_teams_cache()
        if len(slug_parts.team_tokens) >= 2:
            t0_name = teams.resolve(slug_parts.team_tokens[0])
            t1_name = teams.resolve(slug_parts.team_tokens[1])
            if t0_name and t1_name:
                t0_low = t0_name.lower()
                t1_low = t1_name.lower()
                for key, entry in scout_queue.items():
                    if entry.get("entered") or key in used_keys:
                        continue
                    ea = (entry.get("team_a") or "").lower()
                    eb = (entry.get("team_b") or "").lower()
                    if not ea or not eb:
                        continue
                    # Check if both resolved names appear in either team field
                    # (order-independent: "Devils" in "New Jersey Devils" → True)
                    a_in = (t0_low in ea or t0_low in eb)
                    b_in = (t1_low in ea or t1_low in eb)
                    if a_in and b_in:
                        entry_copy = dict(entry)
                        entry_copy["matched"] = True
                        entry_copy["match_confidence"] = 1.0
                        matched.append({
                            "market": market,
                            "scout_entry": entry_copy,
                            "scout_key": key,
                        })
                        used_keys.add(key)
                        _diag["matched"] += 1
                        logger.debug("L0 matched [1.00]: %s -> %s vs %s (via /teams)",
                                     slug[:40], t0_name, t1_name)
                        break  # matched, skip fuzzy layers for this market
                else:
                    pass  # No Layer 0 match — fall through to fuzzy layers below
                if key in used_keys and matched and matched[-1]["market"] is market:
                    continue  # This market matched via Layer 0, next market
```

Wait — the `continue` at the bottom is wrong because we're inside a `for market in markets:` loop but the Layer 0 code needs to skip the *rest of the fuzzy processing* for this market. Let me restructure cleanly.

Actually, looking at the existing code structure, the entire fuzzy block (layers 1-5 + doubleheader + threshold) runs inside the `for market in markets:` outer loop. The cleanest approach is to wrap the existing layers 1-5 in an `if not already_matched:` guard. Here's the complete modification:

At the top of the `for market in markets:` loop body (after `slug_tokens = ...`), insert:

```python
        # ── Layer 0: Polymarket /teams abbreviation lookup (deterministic) ──
        teams = _get_teams_cache()
        layer0_matched = False
        if len(slug_parts.team_tokens) >= 2:
            t0_name = teams.resolve(slug_parts.team_tokens[0])
            t1_name = teams.resolve(slug_parts.team_tokens[1])
            if t0_name and t1_name:
                t0_low = t0_name.lower()
                t1_low = t1_name.lower()
                for key, entry in scout_queue.items():
                    if entry.get("entered") or key in used_keys:
                        continue
                    ea = (entry.get("team_a") or "").lower()
                    eb = (entry.get("team_b") or "").lower()
                    if not ea or not eb:
                        continue
                    if (t0_low in ea or t0_low in eb) and (t1_low in ea or t1_low in eb):
                        entry_copy = dict(entry)
                        entry_copy["matched"] = True
                        entry_copy["match_confidence"] = 1.0
                        matched.append({
                            "market": market,
                            "scout_entry": entry_copy,
                            "scout_key": key,
                        })
                        used_keys.add(key)
                        _diag["matched"] += 1
                        logger.debug("L0 matched [1.00]: %s -> %s vs %s (via /teams)",
                                     slug[:40], t0_name, t1_name)
                        layer0_matched = True
                        break
        if layer0_matched:
            continue  # Skip fuzzy layers for this market
```

This `continue` cleanly skips all fuzzy processing and the diagnostics `else` block for this market, moving to the next market in the outer loop.

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests/test_matcher_layer0.py -v`
Expected: all 7 tests PASS (4 from Task 1 + 3 from Task 2).

- [ ] **Step 5: Run the full existing test suite**

Run: `python -m pytest tests/test_match_exit.py tests/test_odds_api_bugs.py tests/test_reentry.py tests/test_bid_mtm.py tests/test_matcher_layer0.py -q`
Expected: 165 passed (158 existing + 7 new).

- [ ] **Step 6: Commit**

```bash
git add src/matching/__init__.py tests/test_matcher_layer0.py
git commit -m "feat(matching): Layer 0 — /teams abbreviation lookup before fuzzy"
```

---

### Task 3: Extract sportsMarketType from scanner + add to MarketData

**Files:**
- Modify: `src/models.py` (1 line — add field to MarketData)
- Modify: `src/market_scanner.py` (2 lines — extract from raw, pass to MarketData)

- [ ] **Step 1: Add field to MarketData**

In `src/models.py`, inside `class MarketData`, after `accepting_orders`:

```python
    sports_market_type: str = ""  # "moneyline", "totals", "spreads" — from Gamma sportsMarketType
```

- [ ] **Step 2: Extract from raw data in scanner**

In `src/market_scanner.py` `_parse_market()`, add to the MarketData constructor (after `accepting_orders`):

```python
                sports_market_type=raw.get("sportsMarketType", ""),
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_match_exit.py tests/test_odds_api_bugs.py tests/test_reentry.py tests/test_bid_mtm.py tests/test_matcher_layer0.py -q`
Expected: 165 passed. No regressions.

- [ ] **Step 4: Commit**

```bash
git add src/models.py src/market_scanner.py
git commit -m "feat(scanner): extract sportsMarketType from Gamma markets"
```

---

### Task 4: Trigger teams cache refresh on scout run

**Files:**
- Modify: `src/matching/__init__.py` (1 line — call `refresh_if_stale` inside `match_markets`)

- [ ] **Step 1: Add refresh call**

At the very top of `match_markets()`, before the `for market in markets:` loop, add:

```python
    # Refresh Polymarket teams cache daily (free API, no auth needed)
    _get_teams_cache().refresh_if_stale()
```

This ensures the cache is populated on first call and refreshed once per day. The `refresh_if_stale()` method is a no-op if the cache is younger than 24 hours.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_matcher_layer0.py tests/test_match_exit.py tests/test_odds_api_bugs.py tests/test_reentry.py tests/test_bid_mtm.py -q`
Expected: 165 passed.

- [ ] **Step 3: Commit**

```bash
git add src/matching/__init__.py
git commit -m "feat(matching): auto-refresh Polymarket teams cache daily"
```

---

### Task 5: Audit + push

- [ ] **Step 1: Single audit agent (round 1)**

Per CLAUDE.md: 1 agent, 2 consecutive clean rounds. Dispatch agent with prompt covering:
- `src/matching/polymarket_teams.py` — no dead code, correct caching, correct resolve
- `src/matching/__init__.py` — Layer 0 before fuzzy, `continue` skips fuzzy correctly, diagnostics still work for non-Layer-0 markets
- `src/models.py` — `sports_market_type` field added, no clash
- `src/market_scanner.py` — `sportsMarketType` extracted from raw
- No exit-logic files touched (grep `bid_price` / `current_price` in match_exit/stop_loss/trailing_tp unchanged)
- All tests pass (165)
- Zero dead code, zero spaghetti

- [ ] **Step 2: Fix bugs if found, re-audit until clean**

- [ ] **Step 3: Audit round 2 (different agent)**

Same scope, fresh eyes.

- [ ] **Step 4: Push**

```bash
git push origin master
```

---

### Task 6: Live verification

- [ ] **Step 1: Restart bot**

Kill existing bot → `python scripts/reset_bot.py --no-archive` → `python -m src.main` + `python start_dashboard.py`

- [ ] **Step 2: Check first cycle matcher diagnostics**

After Cycle #1 completes, check log for:
```
matching: N/M markets matched
matcher diag: below_thresh=X | no_candidates=Y | no_teams_in_slug=Z
```

`N` should be significantly higher than the pre-fix 3-5 range. Target: 15-20+ in 2h window.

Also look for `L0 matched` debug lines to confirm Layer 0 is firing.

- [ ] **Step 3: Run diagnostic script to compare**

```bash
python scripts/diagnose_matcher.py
```

Compare the new report against the pre-fix report (`docs/superpowers/analysis/2026-04-06-matcher-diagnostic.md`). The `fuzzy_name_mismatch_candidate` count should drop from 19 to near zero.
