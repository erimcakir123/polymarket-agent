# Parallel Enrichment Design

## Problem

The entry gate enriches each market candidate sequentially -- first PandaScore for esports, then ESPN via discovery for traditional sports. With ~90 markets per heavy cycle and ~10s per API call (timeout + retry), this phase takes ~15 minutes. The bot sits idle waiting for I/O while all these calls are independent of each other.

## Solution

Wrap both enrichment loops in a single `concurrent.futures.ThreadPoolExecutor(max_workers=8)` to fetch all market contexts in parallel. Each market's enrichment is independent (unique `condition_id` key, no shared mutable state during fetch), so parallelism is safe without locks.

**Expected improvement:** 15 min --> ~2 min (8x parallelism, bounded by slowest batch of 8).

## Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Parallelism primitive | `concurrent.futures.ThreadPoolExecutor` | stdlib, simple, I/O-bound workload |
| max_workers | 8 | Conservative; PandaScore allows 1000 req/hr, ESPN has no hard limit |
| Scope | Single pool for both esports + sports | Simpler than two pools, total concurrency still capped at 8 |
| Dict writes | No lock needed | Each task writes to a unique `condition_id` key |
| Error handling | Per-future try/except (matches current behavior) | One market failure must not block others |
| Cache safety | No change needed | File-based cache with 30min TTL, already safe for concurrent reads |
| ESPN odds cache | Write `_espn_odds_cache[cid]` inside worker | Unique keys per market, no race condition |

## Architecture

### Current Flow (Sequential)

```
for market in prioritized:          # ~50 esports markets
    esports.get_match_context()     # ~10s each → ~500s total

for market in prioritized:          # ~40 sports markets
    discovery.resolve()             # ~10s each → ~400s total

Total: ~900s (15 min)
```

### New Flow (Parallel)

```
with ThreadPoolExecutor(max_workers=8):
    futures = {}
    for market in prioritized:
        if is_esports(market):
            futures[cid] = submit(_enrich_esports, market)
        else:
            futures[cid] = submit(_enrich_sports, market)

    for cid, future in futures.items():
        result = future.result(timeout=30)
        esports_contexts[cid] = result

Total: ~90 markets / 8 workers × 10s = ~112s (~2 min)
```

## Implementation Plan

### Step 1: Extract helper methods

Extract two private methods from the current inline loops:

- `_enrich_esports(market) -> Optional[dict]` -- wraps the PandaScore call
- `_enrich_sports(market) -> Optional[tuple[context, espn_odds]]` -- wraps the discovery call

### Step 2: Replace sequential loops with ThreadPoolExecutor

Replace lines 388-427 in `entry_gate.py` with:

1. Import `concurrent.futures` at module top
2. Build a dict of `{condition_id: future}` by submitting each market to the appropriate helper
3. Collect results with `future.result(timeout=30)` in a loop
4. Populate `esports_contexts` and `_espn_odds_cache` from results

### Step 3: Add timing log

Log total enrichment duration before and after, so improvement is measurable:

```python
t0 = time.time()
# ... parallel enrichment ...
logger.info("Enrichment completed: %d markets in %.1fs", len(esports_contexts), time.time() - t0)
```

## Files Affected

| File | Change |
|---|---|
| `src/entry_gate.py` | Add import, extract 2 helpers, replace loops with ThreadPoolExecutor |

No other files affected. No new modules, no config changes, no new dependencies.

## Rate Limit Analysis

| API | Limit | Current usage (90 markets) | With 8 workers | Safe? |
|---|---|---|---|---|
| PandaScore | 1000 req/hr | ~250 calls (5/market x 50) | Same total, higher burst | Yes (burst << 1000) |
| ESPN | No explicit limit | ~40 calls | Same total, 8 concurrent | Yes |

## Rollback

Revert to sequential loops by removing the ThreadPoolExecutor wrapper. The helper methods can stay as they improve readability regardless.
