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

## Edge Cases

1. **No scout data yet (first boot)**: Fallback to current volume-sorted scan. Bot works without scout queue.
2. **00:01 scan misses a match**: 06/12/18 refresh catches late additions. If all miss, volume-sorted fallback still works.
3. **Scout entry doesn't match any Gamma market**: Normal — match hasn't been listed on Polymarket yet. Entry skipped, pruned after `match_time + 4h`.
4. **Queue grows large**: Pruning at `match_time + 4h` keeps it bounded. Typical: 200-400 entries, pruned within hours.
5. **ESPN rate limiting**: Existing `time.sleep(0.5)` between league fetches. 00:01 scan takes ~45-50 seconds for all leagues.
6. **Multiple heavy cycles**: Auto-refill runs consecutive heavy cycles. Each one re-reads `get_window()` fresh — no stale data.

## What Does NOT Change

- Light cycle logic (5s loop, per-strategy cooldowns)
- Exit monitoring (interleaved checks at 4 points)
- AI batch cap (20 markets max)
- Thin data gate thresholds
- Odds API usage (post-AI only)
- Risk manager / position sizing
- Upset hunter (stays in heavy cycle)
- WebSocket subscriptions
- Dashboard / trade logger

## Success Criteria

1. Bot discovers matches from ALL leagues in `_SCOUT_LEAGUES`, not just top-120 by volume
2. Markets processed chronologically (soonest-starting first)
3. No increase in AI API spend (batch cap stays at 20)
4. No increase in Odds API spend (post-AI only)
5. Fallback to volume-sorted scan works when scout queue is empty
6. All existing interleaved exit checks preserved
7. Auto-refill still runs consecutive heavy cycles until slots full
