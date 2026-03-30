# Daily Pre-Scan System Design

## Problem

The bot currently discovers markets via Gamma API (volume-sorted, 120 over-scan limit), then enriches them with ESPN/PandaScore data. This creates two problems:

1. **Over-scan ceiling**: Only 120 of 1,490+ filtered markets get scanned per cycle. Many valid matches (e.g., Saudi Arabia vs Serbia, NHL games) never reach enrichment because they sort below the 120 cutoff.
2. **Volume bias**: Volume-sorted scan favors popular markets, missing less-traded but profitable opportunities that start soon.

## Solution

Extend the existing `ScoutScheduler` to run a **full daily match listing** at 00:01 UTC (no enrichment, just team names + match times), then have the entry gate consume that list **chronologically** instead of by volume. Enrichment (ESPN/PandaScore — free) happens at cycle time for the 1-2 hour window ahead. AI analysis stays capped at 20 per batch.

## Design Decisions (Confirmed)

| Decision | Choice | Reason |
|---|---|---|
| Module approach | Extend `scout_scheduler.py` | No new module, less code to maintain |
| 00:01 scan depth | List only (no enrichment) | Fast, covers all matches, enrichment deferred |
| Refresh schedule | 00:01 full scan + 6h light refreshes (06, 12, 18 UTC) | Catches late additions without full re-scan |
| Expired entry cleanup | Existing `match_time + 4h` pruning | Already works, no change needed |
| Market selection order | Chronological (soonest first) | Matches starting soon = highest value |
| Selection window | Start with 1-2h ahead, expand to 3, 4, 5h if not enough | Prioritizes imminent matches, expands as needed |
| Enrichment cost | Unlimited — ESPN/PandaScore are free | No budget impact |
| AI batch cap | Max 20 per call | Claude API is the expensive part |
| Odds API timing | Post-AI only | No cost concern, current behavior preserved |
| Auto-refill | Consecutive heavy cycles until slots full | Existing mechanism, no change |
| Interleaved exits | 4 call sites preserved in agent.py (477, 516, 534, 543) | Verified working |

## Architecture

### Current Flow (Before)

```
Heavy Cycle:
  1. scout.should_run_scout() → runs at 00/06/12/18 UTC, pre-fetches ESPN/PandaScore context
  2. scanner.fetch() → Gamma API volume-sorted, returns ~1490 markets
  3. entry_gate._analyze_batch() → takes top 120 (over-scan), enriches, filters to 20 for AI
```

### New Flow (After)

```
Heavy Cycle:
  1. scout.should_run_scout() → 00:01 UTC full listing (all matches, no enrichment)
     + 06/12/18 UTC light refresh (new matches only)
  2. scanner.fetch() → Gamma API (unchanged, still fetches current markets)
  3. entry_gate._analyze_batch() → NEW SELECTION:
     a. Get scout queue sorted by match_time (soonest first)
     b. Window: 1-2h ahead initially, expand to 3/4/5h if <20 qualified
     c. Match scout entries to Gamma markets (team name matching)
     d. Enrich matched markets (ESPN/PandaScore — free, unlimited)
     e. Filter by thin data gate (unchanged)
     f. AI batch: top 20 qualified (unchanged cap)
     g. Fallback: if scout queue yields <5 matches, use current volume-sorted scan
```

### Components Changed

**1. `scout_scheduler.py` — Extended**

- New method: `run_daily_listing()` — 00:01 UTC full scan, ESPN + PandaScore upcoming matches for next 24h, NO enrichment, just saves team names + match times + sport/league to queue
- Modified: `should_run_scout()` — recognizes 00:01 as daily listing trigger (separate from 06/12/18 refresh)
- Modified: `run_scout()` at 06/12/18 — light refresh mode, only adds NEW matches not already in queue, no re-enrichment
- New method: `get_chronological_queue()` — returns unmatched/unentered entries sorted by `match_time` ascending
- New method: `get_window(hours_ahead: float)` — returns entries within N hours from now, sorted chronologically
- Existing pruning (`match_time + 4h`) unchanged

**2. `entry_gate.py` — Modified selection logic**

- Modified: `_analyze_batch()` — replaces volume-sorted over-scan with scout-driven chronological selection
- New step before current enrichment: query `scout.get_window(2)` for 1-2h window, expand if too few
- Match scout entries to Gamma markets using existing `scout.match_market()` (team name matching)
- Enrichment loop unchanged (ESPN/PandaScore/discovery — all free)
- AI batch cap at 20 unchanged
- Fallback: if chronological selection yields <5, fall back to current volume-sorted behavior

**3. `agent.py` — Minimal change**

- Modified: heavy cycle scout section — call `run_daily_listing()` at 00:01, `run_scout()` at 06/12/18
- All 4 interleaved exit check call sites preserved (lines 477, 516, 534, 543)
- Auto-refill loop unchanged

### Data Flow

```
00:01 UTC:
  ScoutScheduler.run_daily_listing()
    → ESPN: loop _SCOUT_LEAGUES, fetch scoreboard, extract team names + match times
    → PandaScore: loop _ESPORT_GAMES, fetch upcoming, extract team names + match times
    → Save all to scout_queue.json (no enrichment, no AI)
    → ~200-400 matches/day typical

06/12/18 UTC:
  ScoutScheduler.run_scout()
    → Same ESPN/PandaScore fetch, but skip entries already in queue
    → Catches late-announced matches
    → Existing pruning removes expired entries (match_time + 4h)

Each Heavy Cycle:
  EntryGate._analyze_batch()
    → scout.get_window(2) → matches starting in 0-2h (chronological)
    → If <20: expand to get_window(3), then 4, then 5
    → Match each scout entry to Gamma market via team name matching
    → Unmatched scout entries = no Polymarket bet yet, skip
    → Matched: enrich with ESPN/PandaScore (free, unlimited)
    → Filter by thin data gate
    → Cap at 20 for AI analysis
    → Fallback: if <5 from scout, supplement with volume-sorted (current behavior)
```

### Scout Queue Entry (Schema)

No schema change from current. Existing fields:

```json
{
  "scout_key": "soccer_eng.1_Arsenal_Chelsea_20260330",
  "team_a": "Arsenal",
  "team_b": "Chelsea",
  "question": "Arsenal vs Chelsea: Who will win?",
  "match_time": "2026-03-30T15:00:00+00:00",
  "sport": "soccer",
  "league": "eng.1",
  "league_name": "Premier League",
  "is_esports": false,
  "slug_hint": "soc-arse-chel",
  "tags": ["sports", "premier league"],
  "sports_context": "",
  "scouted_at": "2026-03-30T00:01:00+00:00",
  "matched": false,
  "entered": false
}
```

Key difference: `sports_context` is empty at 00:01 listing time. Enrichment fills it during the heavy cycle when the entry gate processes the market.

## Risks and Mitigations

### Spec-Created Risks (MUST fix during implementation)

| # | Risk | Mitigation |
|---|---|---|
| R1 | **agent.py dispatch unclear** — `should_run_scout()` returns True for both 00:01 and 06/12/18, agent doesn't know which method to call | Add `scout.is_daily_listing_time() -> bool` (True only at hour=0). Agent checks this first: if True → `run_daily_listing()`, else → `run_scout()` |
| R2 | **Enrichment ownership scattered** — currently 4 places populate `sports_context`: scout enrichment (scout_scheduler:200-213), scout inject (entry_gate:302-316), discovery.resolve (entry_gate:319-338), + new chronological enrichment | **Single owner: `entry_gate._analyze_batch()`** via `discovery.resolve()`. Remove enrichment from `scout_scheduler.run_scout()` and `run_daily_listing()`. Remove separate scout inject block (entry_gate:302-316) — fold into chronological selection path |
| R3 | **`_seen_market_ids` kills refill** — chronological window has 20-30 markets, all marked "seen" after 1st cycle → refill finds 0 unseen → slots stay empty | **Reset `_seen_market_ids` before each heavy cycle in auto-refill loop**, not just at first cycle. Or: don't add chronological-window markets to `_seen_market_ids` (they should be re-eligible each cycle) |
| R4 | **`entries_allowed` gates daily listing** — if circuit breaker / soft halt active at 00:01, daily listing never runs → entire day has no chronological data until 06:00 refresh | **Decouple daily listing from `entries_allowed`**. Listing is just data gathering (no entries, no AI). Run it unconditionally: `if scout.is_daily_listing_time(): scout.run_daily_listing()` before the `entries_allowed` check |
| R5 | **Two selection paradigms in one method** — volume-sorted (current) + chronological (new) both live in `_analyze_batch()` | **Extract current prioritization (lines 237-256) into `_volume_sorted_selection(markets, scan_size)`**. New chronological path is the default. Fallback calls `_volume_sorted_selection()` when scout yields <5 |

### Pre-Existing Bugs (fix alongside implementation)

| # | Bug | Location | Fix |
|---|---|---|---|
| P1 | `mark_entered()` never called — `entered` flag always False → `signal_scout_approaching()` fires for already-traded markets → permanent 5-min cycles | `scout_scheduler.py:291` is dead code, never called from entry_gate or agent | Wire up: call `scout.mark_entered(scout_key)` from `entry_gate._execute_entries()` when a position is opened via scout match |
| P2 | `_candidate_stock` never pruned — grows unbounded, stale candidates attempted repeatedly | `entry_gate.py:112` — list only grows, never shrinks | Add TTL eviction: remove stock entries older than 2 hours, or cap at 20 entries with FIFO |
| P3 | `_confidence_c_attempts` never reset — markets getting C on Day 1 permanently blocked even if data improves by Day 5 | `entry_gate.py:108` — dict grows forever | Reset daily (clear at 00:01 with the daily listing) or evict entries older than 24h |
| P4 | `_pre_match_prices` never evicted — stale prices from days ago cause false `live_dip` signals | `agent.py:366,492` — dict grows forever | Evict entries for resolved/exited markets. Prune entries older than 48h |
| P5 | `match_market()` saves to disk on every single match — 50-100 disk writes per cycle if many matches | `scout_scheduler.py:275` — `_save_queue()` per match | Add `match_markets_batch(markets)` that matches all, saves once at end |
| P6 | `_seen_market_ids` hardcoded threshold 5 conflicts with sport-aware thresholds (tennis=2, mma=2) — tennis markets analyzed once but blocked from refill | `entry_gate.py:434-436` — uses `< 5` instead of sport-aware `_THIN_DATA_THRESHOLDS` | Use the same sport-aware threshold lookup from `_THIN_DATA_THRESHOLDS` |
| P7 | PandaScore `per_page: 100` with no pagination — drops matches when >100 upcoming per game (busy tournament days) | `scout_scheduler.py:468` | Add pagination loop: fetch page 1, if 100 results → fetch page 2, etc. |
| P8 | ESPN rate limiting: 60 leagues × 3 days = 180 requests with only inter-league sleep (0.5s), no per-request sleep | `scout_scheduler.py:320,448` — sleep is outside inner day loop | Add `time.sleep(0.2)` between day requests within a league, or reduce to 2-day fetch (today + tomorrow) |
| P9 | Dashboard `trades.jsonl` reads entire file on every page load — 72K+ lines after 30 days | `dashboard.py` `read_all()` | Add pagination to API endpoint, or read only last N entries (e.g., 500) |
| P10 | `_espn_odds_cache` and `_exited_markets` grow without eviction | `entry_gate.py:107`, `agent.py:70` | Low priority — no functional bug, just memory. Evict resolved markets periodically |
| P11 | Dashboard `read_all()` reads entire `trades.jsonl` into memory on every `/api/trades` call — unbounded file growth (72K+ lines/month) slows dashboard | `dashboard.py` + `trade_logger.py` | Read only last N lines (tail read), or add `?limit=500&offset=0` pagination to the API endpoint |

## Edge Cases

1. **No scout data yet (first boot)**: Fallback to `_volume_sorted_selection()`. Bot works without scout queue.
2. **00:01 scan misses a match**: 06/12/18 refresh catches late additions. If all miss, volume-sorted fallback still works.
3. **Scout entry doesn't match any Gamma market**: Normal — match hasn't been listed on Polymarket yet. Entry skipped, pruned after `match_time + 4h`.
4. **Queue grows large**: Pruning at `match_time + 4h` keeps it bounded. Typical: 200-400 entries, pruned within hours.
5. **ESPN rate limiting**: Sleep between leagues + between day requests. 00:01 scan takes ~60-90 seconds for all leagues.
6. **Multiple heavy cycles (auto-refill)**: `_seen_market_ids` reset before each refill cycle (R3 mitigation). Each reads `get_window()` fresh.
7. **Bot starts mid-day (e.g., 03:00 UTC)**: No daily listing exists. `should_run_scout()` returns False until 06:00. Volume-sorted fallback handles the gap.
8. **Bot halted at midnight**: Daily listing runs unconditionally (R4 mitigation). When entries resume, chronological data is ready.
9. **match_market() false positives (e.g., "Real Madrid" vs "Real Betis")**: Abbreviated matching (4-char prefix) can collide. Mitigation: increase prefix to 6 chars, or require full team_a match (not abbreviated) when team name is <8 chars.

## What Does NOT Change

- Light cycle logic (5s loop, per-strategy cooldowns)
- Exit monitoring (interleaved checks at 4 points)
- AI batch cap (20 markets max)
- Thin data gate thresholds (sport-aware values preserved)
- Odds API usage (post-AI only)
- Risk manager / position sizing
- Upset hunter (stays in heavy cycle)
- WebSocket subscriptions

## Success Criteria

1. Bot discovers matches from ALL leagues in `_SCOUT_LEAGUES`, not just top-120 by volume
2. Markets processed chronologically (soonest-starting first)
3. No increase in AI API spend (batch cap stays at 20)
4. No increase in Odds API spend (post-AI only)
5. Fallback to volume-sorted scan works when scout queue is empty
6. All existing interleaved exit checks preserved
7. Auto-refill still runs consecutive heavy cycles until slots full
8. All R1-R5 spec risks mitigated — no dead code, no spaghetti, single enrichment owner
9. All P1-P11 pre-existing bugs fixed — no stale caches, no unbounded growth, no dead code
