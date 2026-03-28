# Dynamic Sports Discovery Layer — Design Spec

## Goal

Replace all hardcoded slug/keyword→league mappings with dynamic API-based discovery. Remove redundant data sources (football-data.org, TheSportsDB). Clean up the bridge system. Result: zero dead code, zero hardcoded sport mappings, every market finds its data source dynamically.

## Problem

The bot currently has ~200+ hardcoded slug/keyword mappings spread across 6 files. When a Polymarket market uses an unmapped slug (e.g., `eng3-`, `league-one-`), the bot can't find sports data → gets confidence C → skips the market. This caused 15+ markets to be skipped in a single cycle. Adding new leagues requires manual code changes.

## Architecture

### Data Flow (Current → New)

**Current (5-tier cascade with hardcoded lookups):**
```
Market → Bridge→ESPN → ESPN → football-data.org → CricketData → TheSportsDB
         ↑ hardcoded     ↑ hardcoded    ↑ hardcoded      ↑ hardcoded    ↑ dynamic but unreliable
```

**New (dynamic discovery, no hardcoded mappings):**
```
Market → SportsDiscovery.resolve()
           ├── is_esports? → PandaScore (search[name] endpoint)
           ├── is_cricket? → CricketData (currentMatches + fuzzy match)
           └── everything else → ESPN (team search endpoint)
         Then: Odds API (dynamic sport key from /sports + /events) → bookmaker odds
```

### Routing Logic

Route detection stays **lightweight** — it's categorization (4 categories), not discovery:

| Signal | Route |
|--------|-------|
| Tags contain "esports" OR slug starts with cs2/lol/dota2/valorant | → PandaScore |
| Tags/question contain "cricket" OR slug starts with ipl/t20/psl/cric | → CricketData |
| Everything else (soccer, basketball, MMA, tennis, etc.) | → ESPN |

This is intentionally simple — ESPN covers 56+ sports/leagues, so the default route handles nearly everything.

## Components

### 1. New File: `src/sports_discovery.py`

Single entry point for all sports data resolution. Thin orchestrator — no business logic, just routing + result packaging.

```python
@dataclass
class DiscoveryResult:
    context: str          # Sports context string for AI analyst
    source: str           # "ESPN", "PandaScore", "CricketData"
    confidence: str       # "A" (reliable), "C" (no data)

class SportsDiscovery:
    def __init__(self, espn: SportsDataClient, pandascore: EsportsDataClient,
                 cricket: CricketDataClient, odds_api: OddsAPIClient)

    def resolve(self, question: str, slug: str, tags: list[str]) -> DiscoveryResult | None:
        """Route market to correct API, return context or None."""

    def _detect_route(self, question: str, slug: str, tags: list[str]) -> str:
        """Return 'esports', 'cricket', or 'espn'."""
```

**Key behaviors:**
- Returns `None` if no data source finds the market (equivalent to current "no reliable data" skip)
- All returned results are reliable — no TheSportsDB "unreliable" tier
- ESPN search failures don't crash — they return None gracefully
- Odds API bookmaker odds fetched separately (not part of discovery)

### 2. ESPN Refactor: `src/sports_data.py`

**Remove:** `_SPORT_LEAGUES` dict (68 entries), `_QUESTION_KEYWORDS` dict (43 entries)

**Add:** `search_team(team_name: str) -> tuple[str, str] | None` method

Uses ESPN's free search endpoint:
```
GET https://site.web.api.espn.com/apis/common/v3/search
    ?query=TeamName&type=team&sport=soccer
```

Returns `(sport, league)` tuple (e.g., `("soccer", "eng.3")`) dynamically. Then existing `get_match_context()` works with the discovered sport/league — no changes needed to context-building logic.

**Fallback chain within ESPN:**
1. Try search endpoint with team name
2. If search returns multiple results, pick the one whose league has upcoming events
3. Cache search results (30 min TTL) to avoid repeat lookups

**Keep intact:** `get_team_record()`, `get_match_context()`, `get_upcoming_match_info()`, `_extract_teams()`. These work fine once sport+league is known.

**Rename `detect_sport()` → `_detect_sport()`** (internal only, no external callers after refactor).

### 3. PandaScore Refactor: `src/esports_data.py`

**Remove:** `_GAME_SLUGS` dict (9 hardcoded entries)

**Add:** `search_match(team_name: str) -> dict | None` method

Uses PandaScore search endpoint:
```
GET /matches/upcoming?search[name]=TeamName&per_page=5
```

Returns match data with game slug discovered dynamically.

**Keep minimal game categorization** — only 4 values (cs2, lol, dota2, valorant) for the route detector. This is categorization, not discovery.

**Refactor `detect_game()`:** Instead of hardcoded `_GAME_SLUGS`, try search endpoint. If team is found in any game's upcoming matches, return that game slug.

### 4. CricketData Refactor: `src/cricket_data.py`

**Remove:** `_SLUG_TO_SERIES` (6 entries), `_KEYWORD_TO_SERIES` (5 entries)

**Refactor `get_match_context()`:** Instead of series detection via hardcoded mappings:
1. Call `get_current_matches()` (returns all active matches across all series)
2. Fuzzy-match team names from question against match teams
3. Build context from matched game — series name comes from the API response, not our mapping

This is simpler and covers ALL cricket series, not just the 6 we hardcoded.

### 5. Odds API Cleanup: `src/odds_api.py`

**Remove:**
- `_SPORT_KEYS` dict (80+ slug→key entries)
- `_QUESTION_SPORT_KEYS` dict (56+ keyword→key entries)
- `bridge_match()` method
- `_get_bridge_events()` method
- `_detect_all_sport_keys()` method
- `_BRIDGE_CACHE_MAX_AGE` constant

**Refactor `_detect_sport_key()`:** Use dynamic sport key discovery instead of hardcoded mappings.

New flow:
1. Call `/v4/sports?all=false` (FREE, 0 credits) → get all active sport keys
2. Cache result (1h TTL, already has `_ACTIVE_SPORTS_CACHE_TTL`)
3. For each active sport key, scan `/v4/sports/{key}/events` (FREE) for team name match
4. Cache events per sport key (2h TTL)
5. Return matched sport key

**Tennis handling stays:** `_get_active_tennis_keys()`, `_match_tennis_key()`, `_is_wta_market()` already use dynamic discovery. Keep as-is.

**Change refresh schedule:**
- Current: `_REFRESH_HOURS_UTC = [7, 12, 19, 23]` (4x/day)
- New: Every 2 hours (12x/day)
- Budget: 360 calls/day × 30 = 10,800/month (54% of 20K)
- Implementation: Replace `_REFRESH_HOURS_UTC` list with `_REFRESH_INTERVAL_HOURS = 2`

**Keep intact:** `get_bookmaker_odds()`, `get_line_movement()`, `get_historical_odds()`, `build_line_movement_context()`, `get_live_scores()`, `_extract_teams()`, all caching/persistence logic.

### 6. entry_gate.py Simplification

**Remove:**
- `from src.thesportsdb import TheSportsDBClient` import + `self.tsdb` instantiation
- `from src.football_data import FootballDataClient` import + `self.football_data` instantiation
- The entire 5-tier cascade (lines 314-400)
- `_reliable_source_cids` tracking (all sources are now reliable)
- Bridge match logic (lines 315-333)

**Add:**
- `from src.sports_discovery import SportsDiscovery` (passed in constructor)
- Single discovery call replacing the cascade

**New `__init__` signature:** Replace `sports` parameter with `discovery: SportsDiscovery`. Remove `football_data` and `tsdb` internal instantiation. Keep `cricket_data` instantiation inside SportsDiscovery.

**New sports context fetch (replaces lines 314-400):**
```python
# Sports context via unified discovery
if self.discovery:
    for _m in prioritized:
        if _m.condition_id in esports_contexts:
            continue  # PandaScore/Scout already has context
        if is_esports_slug(_m.slug or ""):
            continue
        try:
            result = self.discovery.resolve(
                getattr(_m, "question", ""), _m.slug or "",
                getattr(_m, "tags", []),
            )
            if result:
                esports_contexts[_m.condition_id] = result.context
        except Exception as _exc:
            logger.debug("Discovery error for %s: %s", _m.slug[:40], _exc)
```

**Reliability filter simplification:** Remove `_reliable_source_cids` tracking entirely. Discovery only returns results from reliable sources (ESPN, PandaScore, CricketData). If discovery returns None, the market has no data — same as current "unreliable skip" behavior, but cleaner.

The existing esports context fetch (lines 282-295) stays — PandaScore `get_match_context()` is called directly for esports markets detected by the esports tag/slug check.

### 7. scout_scheduler.py Updates

**Remove:**
- `from src.football_data import FootballDataClient` import + `self.football_data` instantiation
- `from src.sports_data import _SPORT_LEAGUES` import
- `_LEAGUE_TO_PREFIX` reverse lookup dict
- `_fetch_football_data_upcoming()` method (Copa Libertadores — ESPN covers it)
- football-data.org fallback in `run_scout()` context fetch

**Refactor:**
- Replace `_SPORT_LEAGUES` usage in slug_hint generation with inline logic
- Keep `_SCOUT_LEAGUES` hardcoded list — this is a curated list of what to scout, not a discovery mapping. It's intentional curation, not a limitation.
- Replace football-data.org context fallback with ESPN (which covers all the same leagues)

### 8. agent.py Updates

**Refactor constructor:** Currently creates `SportsDataClient()` and passes it to `EntryGate(sports=sports)`. After refactor:
1. Create `SportsDataClient()`, `CricketDataClient()` as before
2. Create `SportsDiscovery(espn=sports, pandascore=esports, cricket=cricket, odds_api=odds_api)`
3. Pass `discovery=discovery` to `EntryGate` instead of `sports=sports`
4. Remove `FootballDataClient` instantiation if present

**Bug fix:** In `_check_live_dip()` line 928, clamp `pre_match`:
```python
ai_probability=max(0.01, min(0.99, pre_match)),
```

### 9. Files to Delete

| File | Lines | Reason |
|------|-------|--------|
| `src/football_data.py` | 333 | ESPN covers all 12 free-tier leagues + more |
| `src/thesportsdb.py` | 166 | Data quality too low, marked unreliable by existing code |

### 10. Test Files to Update/Delete

| File | Action | Reason |
|------|--------|--------|
| `tests/test_thesportsdb.py` | DELETE | Module removed |
| `tests/test_odds_bridge.py` | DELETE | Bridge system removed |
| `tests/test_sports_context_pipeline.py` | UPDATE | Remove football-data + TheSportsDB references, add discovery mock |

## Bug Fix: `_check_live_dip()` Crash

**File:** `src/agent.py`, line 928
**Bug:** `ai_probability=pre_match` passes the YES market price as ai_probability. For strong NO favorites (YES price = 0.0045), this violates the Position validator `[0.01, 0.99]`.
**Fix:** Clamp pre_match to `[0.01, 0.99]` before passing to `add_position()`:
```python
ai_probability=max(0.01, min(0.99, pre_match)),
```

## Cost Impact

| Item | Before | After | Delta |
|------|--------|-------|-------|
| ESPN API calls | Same | Same | 0 (free) |
| ESPN search calls | 0 | ~20/cycle | 0 (free) |
| PandaScore calls | Same | Same | 0 (included in plan) |
| CricketData calls | Same | Same | 0 (free tier) |
| Odds API credits/month | ~5,400 (4x/day) | ~10,800 (12x/day) | +5,400 (within 20K budget) |
| football-data.org calls | ~50/day | 0 | Eliminated |
| AI tokens saved | — | ~15 markets/cycle no longer get conf=C | Saves ~$0.50/day |

## Files Changed Summary

| File | Action | What Changes |
|------|--------|-------------|
| `src/sports_discovery.py` | **CREATE** | Unified discovery orchestrator (~120 lines) |
| `src/sports_data.py` | REFACTOR | Remove 111 hardcoded entries, add `search_team()` |
| `src/esports_data.py` | REFACTOR | Remove 9 hardcoded entries, add `search_match()` |
| `src/cricket_data.py` | REFACTOR | Remove 11 hardcoded entries, use fuzzy match on currentMatches |
| `src/odds_api.py` | REFACTOR | Remove 136+ entries + bridge system, dynamic sport keys, 2h refresh |
| `src/entry_gate.py` | REFACTOR | Replace 5-tier cascade with single discovery call |
| `src/scout_scheduler.py` | REFACTOR | Remove football-data refs, simplify context fetch |
| `src/agent.py` | REFACTOR + FIX | Create `SportsDiscovery` instance, pass to `EntryGate`; clamp ai_probability in `_check_live_dip()` |
| `src/football_data.py` | **DELETE** | Fully redundant with ESPN |
| `src/thesportsdb.py` | **DELETE** | Unreliable, fully redundant |
| `tests/test_thesportsdb.py` | **DELETE** | Module removed |
| `tests/test_odds_bridge.py` | **DELETE** | Bridge removed |
| `tests/test_sports_context_pipeline.py` | UPDATE | Remove dead refs, add discovery mock |

## Constraints

- No breaking changes to AI analyst interface — `esports_contexts` dict format stays identical
- No changes to position management, risk, or execution logic
- Odds API bookmaker odds flow unchanged — only discovery/routing changes
- Scout scheduler keeps curated `_SCOUT_LEAGUES` list (intentional curation ≠ hardcoded limitation)
- `team_matcher.py` stays — still used by Odds API `get_bookmaker_odds()` for event matching
