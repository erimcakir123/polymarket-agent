# Sports WebSocket + ESPN Enrichment + Entry Guards — Design Spec

**Date:** 2026-03-31
**Status:** Approved
**Scope:** 6 changes, 2 new files, 8 modified files

---

## Problem Statement

Bot testing on 2026-03-30 revealed 6 critical issues:

1. **Entered a RESOLVED match** (val-rose-evi) → instant -$20 loss. Gamma API returns resolved markets as `active=true`. No guard in entry pipeline.
2. **Entered matches past halfway** — no elapsed-time guard in EntryGate or UpsetHunter (UpsetHunter had 75% threshold with hardcoded 120min duration).
3. **No real-time match state** — bot polls Gamma API every 30s+, no live/ended/score awareness at entry time.
4. **ESPN enrichment data not reaching AI** — odds cached in entry_gate but never passed to AI analyst. Single data source → B- confidence on all entries.
5. **ESPN endpoints underutilized** — only 5 of 12+ useful endpoints used. Missing: win probability, standings, H2H, rankings, athlete overview, splits, CDN scoreboard.
6. **Scout doesn't run on cold start** — only triggers at UTC 0/6/12/18, no first-run mechanism.

---

## Changes

### A. Polymarket Sports WebSocket — `src/sports_ws.py` (NEW, ~120 lines)

**Purpose:** Real-time match state from Polymarket's sports feed.

**Connection:** `wss://sports-api.polymarket.com/ws`
- No subscription message needed — connect and receive all active events
- Server sends ping every 5s, client must respond with pong within 10s
- Auto-reconnect with exponential backoff (2s-60s)

**Message schema (from Polymarket docs):**
```json
{
  "gameId": 12345,
  "leagueAbbreviation": "NBA",
  "slug": "nba-cha-bkn",
  "homeTeam": "Hornets",
  "awayTeam": "Nets",
  "status": "InProgress",
  "score": "98-102",
  "period": "4Q",
  "live": true,
  "ended": false,
  "elapsed": "42:18",
  "finished_timestamp": null
}
```

**Class interface:**
```python
class SportsWebSocket:
    def __init__(self) -> None: ...
    def start_background(self) -> None: ...  # Daemon thread, same pattern as WebSocketFeed
    def stop(self) -> None: ...
    def get_match_state(self, slug: str) -> dict | None: ...
    def is_ended(self, slug: str) -> bool: ...
    def is_live(self, slug: str) -> bool: ...
    @property
    def connected(self) -> bool: ...
```

**Internal state:** `_states: dict[str, dict]` protected by `threading.Lock`. Keyed by WS slug (e.g., `"nba-cha-bkn"`).

**Slug matching:** WS slugs (e.g., `"nba-cha-bkn"`) may differ from Gamma market slugs (e.g., `"will-charlotte-hornets-beat-nets"`). `get_match_state(slug)` must normalize: try exact match first, then check if any WS slug is a prefix of the market slug, or if the market slug contains the WS slug's team abbreviations. Implementation will use the abbreviated slug format that positions already store (e.g., `"nba-cha-bkn-2026-03-30"` → strip date suffix → match WS slug).

**Integration:**
- `agent.py` __init__: create `SportsWebSocket()`, call `start_background()`
- Pass to `entry_gate` and `price_updater` as constructor argument
- `agent.py` shutdown: call `stop()`

**Does NOT touch:** `WebSocketFeed` (CLOB) — zero changes to existing WebSocket code.

---

### B. Gamma API Field Parsing — `models.py` + `market_scanner.py`

**New fields on MarketData (`models.py`):**
```python
closed: bool = False           # Gamma raw "closed"
resolved: bool = False         # Gamma raw "resolved"
accepting_orders: bool = True  # Gamma raw "acceptingOrders"
```

**Parsing in `market_scanner.py` `_parse_market()`:**
```python
closed=raw.get("closed", False),
resolved=raw.get("resolved", False),
accepting_orders=raw.get("acceptingOrders", True),
```

**Entry guard in `entry_gate.py` `_evaluate_candidates()`:**
```python
if market.closed or market.resolved or not market.accepting_orders:
    logger.info("SKIP resolved/closed: %s", market.slug[:40])
    continue
```

**Files changed:** `models.py` (+3 lines), `market_scanner.py` (+3 lines), `entry_gate.py` (+4 lines).

---

### C. Entry Elapsed Guard (50%) + UpsetHunter DRY Fix

**Rule:** All entry pipelines — if match is past 50%, do not enter. No exceptions.

**EntryGate `_evaluate_candidates()` — new guard:**

```python
from src.match_exit import get_game_duration

# Prefer Sports WebSocket elapsed data (real-time)
elapsed_pct = 0.0  # Default: match not started
ws_state = self.sports_ws.get_match_state(slug) if self.sports_ws else None
if ws_state and ws_state.get("ended"):
    skip  # Match finished

if ws_state and ws_state.get("elapsed"):
    # Parse "MM:SS" → minutes, compute pct against sport duration
    _parts = ws_state["elapsed"].split(":")
    _elapsed_min = int(_parts[0]) + int(_parts[1]) / 60 if len(_parts) == 2 else 0
    duration_min = get_game_duration(slug, number_of_games, sport_tag)
    elapsed_pct = _elapsed_min / max(duration_min, 1)
elif match_start_iso:
    # Fallback: calculate from match_start_iso + sport duration
    elapsed_min = (now - start_dt).total_seconds() / 60
    duration_min = get_game_duration(slug, number_of_games, sport_tag)
    elapsed_pct = elapsed_min / max(duration_min, 1)

if elapsed_pct > 0.50:
    logger.info("SKIP half-elapsed: %s | %.0f%% through", slug[:35], elapsed_pct * 100)
    skip
```

**UpsetHunter `_estimate_elapsed_pct()` — DRY fix:**

Replace hardcoded 120min with `get_game_duration()`:
```python
# Old (line 195):
return min(elapsed_min / 120, 1.0)

# New:
duration = get_game_duration(m.slug or "", getattr(m, "number_of_games", 0), getattr(m, "sport_tag", ""))
return min(elapsed_min / max(duration, 1), 1.0)
```

Change UpsetHunter threshold from 75% to 50% (line 86):
```python
# Old:
if elapsed_pct > 0.75:
# New:
if elapsed_pct > 0.50:
```

**Files changed:** `entry_gate.py` (+10 lines), `upset_hunter.py` (3 lines changed).
**Files NOT changed:** `match_exit.py` (only imported, not modified).

---

### D. ESPN Enrichment Endpoints — `src/espn_enrichment.py` (NEW, ~200 lines)

**Purpose:** Additional ESPN data sources for richer AI context.

**New endpoints (7 methods):**

| Method | ESPN Endpoint | Returns |
|--------|--------------|---------|
| `get_win_probability(sport, league, event_id, comp_id)` | `sports.core.api.espn.com/v2/.../odds` (probabilities field) | `{home_prob, away_prob}` |
| `get_league_standing(sport, league, team_name)` | `site.api.espn.com/apis/v2/sports/.../standings` | `{rank, wins, losses, points, streak}` |
| `get_athlete_overview(sport, league, athlete_id)` | `site.web.api.espn.com/apis/common/v3/.../athletes/{id}/overview` | `{ranking, injury_status, news, next_match}` |
| `get_athlete_splits(sport, league, athlete_id)` | `site.api.espn.com/.../athletes/{id}/splits` | `{home_record, away_record, surface_stats}` |
| `get_rankings(sport, league)` | `sports.core.api.espn.com/v2/.../rankings` | `[{name, rank, points}]` |
| `get_cdn_scoreboard(sport)` | `cdn.espn.com/core/{sport}/scoreboard?xhr=1` | Lightweight live scoreboard |
| `get_h2h(sport, league, athlete_id_a, athlete_id_b)` | `site.api.espn.com/.../athletes/{id}/vsathlete/{opp_id}` | `{wins_a, wins_b, last_results}` |

**Error handling:** Each method returns `None` on failure (network error, 404, timeout). No exceptions propagated. Logged at WARNING level.

**Caching:** Simple TTL dict cache (5 min for standings/rankings, no cache for live data).

**Dependency:** Receives `SportsDataClient` instance via constructor. Uses public methods only: `detect_sport()`, ESPN search endpoint, scoreboard fetch. For event_id/athlete_id discovery, `enrich()` calls the scoreboard endpoint directly (same URL pattern as `sports_data.py` but independent call) rather than relying on private `_find_espn_event()`. No circular imports — `espn_enrichment` imports nothing at module level from `src/`, receives client via DI.

**Does NOT modify:** `sports_data.py` — only calls existing public methods.

---

### D2. ESPN Enrichment Integration — `sports_discovery.py`

**`resolve()` method updated to call both modules:**

```python
def resolve(self, question, slug, tags):
    route = self._detect_route(question, slug, tags)  # unchanged

    if route == "esports":
        # ... existing PandaScore path, unchanged ...
    elif route == "cricket":
        # ... existing CricketData path, unchanged ...
    else:  # espn — MODIFIED below
        context = self.espn.get_match_context(question, slug, tags)
        if not context:
            return None  # No base context → skip (unchanged behavior)

        odds = self.espn.get_espn_odds(question, slug, tags)

        # NEW: additional enrichment from ESPN endpoints
        enrichment = self.enrichment.enrich(question, slug, tags)

        # Combine into single context string:
        parts = [context]
        if odds:
            parts.append(f"\n=== BOOKMAKER ODDS (ESPN) ===\n"
                         f"{odds.get('team_a','?')} {odds.get('bookmaker_prob_a',0):.0%} vs "
                         f"{odds.get('team_b','?')} {odds.get('bookmaker_prob_b',0):.0%} "
                         f"({odds.get('num_bookmakers',0)} bookmakers)")
        if enrichment:
            parts.append(enrichment)
        full_context = "\n".join(parts)
        return DiscoveryResult(context=full_context, source="ESPN",
                               confidence="A", espn_odds=odds)
```

**`enrich()` method logic (in espn_enrichment.py):**
- Team sports (baseball, basketball, football, hockey, soccer): standings + win probability + CDN scoreboard
- Athlete sports (tennis, mma, golf): athlete overview + splits + rankings + H2H
- All sports: odds included in context string → AI sees "bookmaker" → confidence upgrade

**Golf support:**
- `sports_data.py`: add `"golf"` to `_ATHLETE_SPORTS` (1 line)
- `scout_scheduler.py`: add golf leagues to `_SCOUT_LEAGUES` (`"pga"`, `"lpga"`) (+2 lines)
- Golf H2H markets matched via athlete name extraction, tournament-winner markets filtered by moneyline-only rule in entry_gate

**Files changed:** `sports_discovery.py` (+15 lines), `sports_data.py` (+1 line), `scout_scheduler.py` (+2 lines).

---

### E. ESPN Odds → AI Context

**No separate change needed.** Bölüm D2 solves this — `sports_discovery.resolve()` now includes odds in the combined context string. `ai_analyst._build_prompt()` already detects "bookmaker" keyword in context and sets `has_odds = True`. No changes to `ai_analyst.py`.

---

### F. Scout Cold-Start + Discovery Error Logging

**Scout cold-start (`scout_scheduler.py` `should_run_scout()`):**
```python
# Add at top of method, before hour check:
if not self._queue:
    return True  # Cold start — never scouted, run immediately
```

**Discovery error logging (`entry_gate.py` line 402):**
```python
# Old:
logger.debug("Discovery error for %s: %s", ...)
# New:
logger.warning("Discovery error for %s: %s", ...)
```

**Files changed:** `scout_scheduler.py` (+2 lines), `entry_gate.py` (1 line changed).

---

## File Change Summary

| File | Change Type | Lines |
|------|-------------|-------|
| `src/sports_ws.py` | **NEW** | ~120 |
| `src/espn_enrichment.py` | **NEW** | ~200 |
| `src/models.py` | +3 fields | +3 |
| `src/market_scanner.py` | +3 parse lines | +3 |
| `src/entry_gate.py` | +resolved guard, +elapsed guard, +1 log level | +15 |
| `src/upset_hunter.py` | DRY fix + threshold change | ~3 changed |
| `src/sports_discovery.py` | enrichment integration + __init__ update | +20 |
| `src/sports_data.py` | +golf to _ATHLETE_SPORTS | +1 |
| `src/scout_scheduler.py` | cold-start + golf leagues | +4 |
| `src/agent.py` | init SportsWebSocket + ESPNEnrichment, pass to modules | +8 |

**Total new code:** ~320 lines (2 new files)
**Total modified:** ~57 lines across 8 existing files
**Dead code created:** 0
**Files deleted:** 0

---

## What Does NOT Change

- `src/websocket_feed.py` — CLOB WebSocket untouched
- `src/ai_analyst.py` — already detects bookmaker keyword, no changes
- `src/risk_manager.py` — no changes
- `src/match_exit.py` — only imported, not modified
- `src/portfolio.py` — no changes
- `src/exit_monitor.py` — no changes
- `src/config.py` — no new config flags needed (ESPN is free, no API key)
- All test files — existing tests unaffected, new tests added

---

## Anti-Spaghetti Verification

After implementation, verify:
1. `python -m pytest tests/ -v --tb=short` → all pass
2. `grep -rn "120" src/upset_hunter.py` → no hardcoded duration
3. `grep -rn "def.*unused\|# removed\|# old" src/` → no dead code markers
4. `grep -rn "from src.sports_ws import" src/` → only agent.py, entry_gate.py, price_updater.py
5. `grep -rn "from src.espn_enrichment import" src/` → only sports_discovery.py
6. No circular imports: `sports_ws.py` imports nothing from `src/`. `espn_enrichment.py` uses `SportsDataClient` via DI (no module-level src imports)
