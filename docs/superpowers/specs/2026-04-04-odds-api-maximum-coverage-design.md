# Odds API Maximum Coverage & Sharp Weighting — Design Spec

**Date:** 2026-04-04
**Goal:** Get maximum odds coverage from The Odds API's 20K monthly credits, minimize "no odds data" responses, and weight sharp bookmakers (Pinnacle, Betfair Exchange) higher across the entire anchor probability system.

**Status:** Approved for implementation

---

## Problem Statement

Current `odds_api.py` implementation is too conservative:

1. **Only `us` region** — misses UK/EU bookmakers, which are critical for soccer coverage and contain the sharpest bookmaker in the world (Pinnacle, EU region)
2. **Only `h2h` market** — for soccer this is wrong because it hides draw probability, inflating win probabilities
3. **No `commenceTime` filter** — fetches all upcoming events, most of which are >24h away and irrelevant
4. **Fixed 2h refresh** — no budget-awareness, risks running out of credits mid-month
5. **Democratic bookmaker averaging** — treats Pinnacle (sharpest bookmaker on earth) the same as DraftKings (soft, retail-focused)
6. **No Polymarket filter** — the `us` region does not contain Polymarket today, but the `us_ex` region does, and this creates a circular-data risk if ever expanded
7. **Dead code** — unused `_hist_cache_ttl` field, inline imports

**Consequence:** Low bookmaker coverage, biased averages from soft bookmakers, inflated soccer probabilities, wasted response payload, and no safety rails on credit usage.

---

## Goals

- Use full 20K monthly Odds API budget intentionally, never exceed it
- Maximize bookmaker diversity per match (target: 10-15 bookmakers average, including at least one sharp)
- Eliminate "no bookmaker odds" responses for markets with active Odds API coverage
- Weight sharp bookmakers (Pinnacle, Betfair Exchange, Bookmaker.eu) 3× higher in all probability averaging (Odds API + ESPN odds)
- Weight reputable bookmakers (Bet365, William Hill, Unibet) 1.5× higher than standard soft books
- Get accurate soccer win probabilities by reading the 3-way market (home/draw/away)
- Do not break any existing consumer (`entry_gate.py`, `live_strategies.py`, `upset_hunter.py`, `agent.py`)
- Zero dead code, zero spaghetti, backward compatible return formats

---

## Architecture

### Files Changed

| File | Role | Change Type |
|---|---|---|
| `src/matching/bookmaker_weights.py` | NEW — single source of truth for bookmaker quality weights | Create |
| `src/matching/odds_sport_keys.py` | Add `is_soccer_key()` helper | Modify |
| `src/odds_api.py` | Core rewrites for fetch strategy, throttling, 3-way parsing, sharp weighting | Modify |
| `src/sports_data.py` | Apply sharp weighting to ESPN bookmaker averaging | Modify |
| `src/entry_gate.py` | Use `total_weight` instead of `num_bookmakers` when combining Odds API + ESPN anchors | Modify (single line) |

### Files NOT Changed (Important)

- `src/live_strategies.py` — still reads `bookmaker_prob_a` field (unchanged)
- `src/upset_hunter.py` — still reads `odds_api_implied_prob` from market model (unchanged)
- `src/agent.py` — only wires `OddsAPIClient` into the pipeline (unchanged)
- `src/models.py` — `Market.odds_api_implied_prob` field unchanged (still single float)
- Tests in `tests/test_odds_sport_keys.py`, `tests/test_odds_api_bugs.py` — extended with new cases, existing cases stay green

---

## Design Decisions

### 1. Bookmaker Weight Tiers

**Tier 1: Sharp (weight 3.0)** — These bookmakers do not restrict winning customers, adjust lines based on where smart money moves, and publish the most accurate probabilities in the market.

- `pinnacle` (EU)
- `betfair_ex_eu` (EU)
- `betfair_ex_uk` (UK)
- `matchbook` (UK, peer-to-peer exchange)

**Tier 2: Reputable (weight 1.5)** — Large, established European books with decent lines but some retail bias.

- `bet365` (UK)
- `williamhill` (UK)
- `unibet_eu` (EU)
- `unibet_uk` (UK)
- `betclic` (FR/EU)
- `marathonbet` (UK/EU)

**Tier 3: Standard (weight 1.0)** — All other bookmakers. Soft, retail-focused, higher vig, biased toward popular teams.

Default weight if bookmaker key not found in any tier: `1.0`.

**Why these tiers:** Pinnacle's reputation as the sharpest book is well-documented in sports betting literature and reflected in professional workflows (pros use Pinnacle closing lines as the benchmark for "true probability"). Betfair Exchange is a peer-to-peer market, so its prices emerge from actual betting volume rather than a bookmaker's opinion — structurally sharp. Bet365 and William Hill are historically the "grown-up" European books with large limits. Retail US books like DraftKings, FanDuel, BetMGM are soft because their business model kicks winners off the platform.

### 2. Fetch Strategy by Sport

**Soccer (any `soccer_*` sport key):**
```
regions = us,uk,eu
markets = h2h,h2h_3_way
commenceTimeFrom = now (rounded down to hour)
commenceTimeTo = now + 24h (rounded down to hour)
```
Cost: `2 markets × 3 regions = 6 credits per call`

**Non-soccer (baseball, basketball, hockey, MMA, tennis, etc.):**
```
regions = us,uk,eu
markets = h2h
commenceTimeFrom = now (rounded to hour)
commenceTimeTo = now + 24h (rounded to hour)
```
Cost: `1 market × 3 regions = 3 credits per call`

**Hour rounding rationale:** `commenceTimeFrom`/`commenceTimeTo` are part of the cache key. If they change every second, the cache never hits. Rounding to the top of the hour means all requests within the same clock hour share one cache entry.

### 3. Adaptive Throttle

Read `x-requests-used` and `x-requests-remaining` headers on every API response. Calculate usage percentage:

```
usage_pct = used / (used + remaining)
```

Apply refresh interval by tier:

| Usage % | Refresh Interval |
|---|---|
| 0% – 70% | 2 hours |
| 70% – 90% | 3 hours |
| 90%+ | 4 hours |

This replaces the fixed `_REFRESH_INTERVAL_HOURS = 2` constant with a dynamic `_current_refresh_hours()` method that reads the last known usage and returns the appropriate interval.

**Bootstrap:** Before the first API call of a session, `_last_remaining` and `_last_total` are `None`. Default to 2h refresh during bootstrap, since we have no usage information yet.

### 4. Polymarket Bookmaker Filter

Inside `get_bookmaker_odds()`, after extracting bookmakers from the matched event, skip any bookmaker whose key is `polymarket`:

```python
for bookmaker in best_event.get("bookmakers", []):
    if bookmaker.get("key") == "polymarket":
        continue
    ...
```

This is defensive: the current `us` region does not include Polymarket (only `us_ex` does). But the filter costs one line and prevents circular data forever.

### 5. Soccer 3-Way Parsing

In the bookmaker loop, for each bookmaker, check available markets:

1. If `h2h_3_way` market exists → use it. Extract home/draw/away outcomes. Normalize by `home + draw + away` to remove vig. Keep draw probability separately.
2. Else if `h2h` market exists → fall back to 2-way parsing (existing logic).
3. Else → skip bookmaker.

When computing "Will X win?" probability, use the 3-way home or away probability directly (do not redistribute draw). The draw probability is returned separately in the result dict as `bookmaker_prob_draw`.

For non-soccer markets, `h2h_3_way` does not exist and `h2h` is 2-way — existing logic applies, `bookmaker_prob_draw` stays `None`.

### 6. Return Format (Backward Compatible)

Current return from `get_bookmaker_odds()`:
```python
{
    "team_a": ..., "team_b": ...,
    "bookmaker_prob_a": ..., "bookmaker_prob_b": ...,
    "num_bookmakers": ...,
    "bookmakers": [...],
}
```

New return:
```python
{
    "team_a": ..., "team_b": ...,
    "bookmaker_prob_a": ..., "bookmaker_prob_b": ...,
    "bookmaker_prob_draw": ...,  # NEW: float for soccer 3-way, None otherwise
    "num_bookmakers": ...,        # KEPT: count of contributing bookmakers (backward compat)
    "total_weight": ...,          # NEW: sum of bookmaker quality weights (float)
    "has_sharp": ...,             # NEW: bool, true if at least one tier-1 book contributed
    "bookmakers": [...],
}
```

All existing consumers still work because they only read `bookmaker_prob_a`. Only `entry_gate.py` is updated to use `total_weight` instead of `num_bookmakers` in the anchor combination loop.

### 7. ESPN Odds Sharp Weighting

`src/sports_data.py` has its own bookmaker averaging loop for ESPN's `/odds` endpoint. ESPN typically returns DraftKings and Bet365. Apply the same `bookmaker_weights.get_bookmaker_weight()` function there, so that the ESPN result also reports `total_weight` instead of raw bookmaker count. The return format gains the same new fields (`total_weight`, `has_sharp`).

### 8. Entry Gate Combination

Current code (`entry_gate.py` ~678):
```python
for prob, weight in _odds_probs:  # weight = num_bookmakers
    ...
total_weight = sum(w for _, w in _odds_probs)
_anchor_book_prob = sum(p * w for p, w in _odds_probs) / total_weight
```

New code:
```python
# _odds_probs is now list of (prob, total_weight) tuples
# where total_weight is the sum of quality weights, not bookmaker count
for prob, weight in _odds_probs:  # weight = total_weight
    ...
total_weight = sum(w for _, w in _odds_probs)
_anchor_book_prob = sum(p * w for p, w in _odds_probs) / total_weight
```

Only the semantics change — the math is identical. We're feeding in quality-weighted totals instead of raw counts.

---

## Data Flow

```
Market discovered in agent cycle
    ↓
entry_gate.evaluate_market()
    ↓
odds_api.get_bookmaker_odds(question, slug, tags)
    ↓
    _detect_sport_key() → sport_key (e.g. "soccer_epl")
    ↓
    is_soccer_key(sport_key) → True/False
    ↓
    _build_odds_params(sport_key) → {regions, markets, commenceTime*}
    ↓
    _get("/sports/.../odds", params)  [cached per sport_key + hour]
    ↓
    Match event by team names (pair_matcher)
    ↓
    For each bookmaker in event:
        - Skip if key == "polymarket"
        - Get quality weight from bookmaker_weights
        - Parse h2h_3_way if soccer, else h2h
        - Apply weight × prob, accumulate
    ↓
    Return dict with weighted averages + total_weight + has_sharp
    ↓
entry_gate combines with ESPN odds (same format, same weighting)
    ↓
calculate_anchored_probability(ai_prob, anchor_prob, total_weight)
```

---

## Budget Math

**Assumptions:**
- 12 unique active sport keys at peak (mix of soccer + American + MMA + tennis)
- Of those, ~7 are soccer (EPL, La Liga, Serie A, Bundesliga, Champions League, etc.)
- Bot runs 24/7

**Full speed (2h refresh, 12 calls/day):**
- Soccer: 7 keys × 6 credits × 12 calls = 504 credits/day
- Non-soccer: 5 keys × 3 credits × 12 calls = 180 credits/day
- Total: 684 credits/day → ~20,520/month ⚠ at the edge

**Adaptive kicks in at 70% (~14,000 credits):**
- Switches to 3h refresh (8 calls/day)
- Soccer: 7 × 6 × 8 = 336/day
- Non-soccer: 5 × 3 × 8 = 120/day
- Total: 456/day → 13,680/month remaining-run rate

**Emergency throttle at 90% (~18,000 credits):**
- 4h refresh (6 calls/day)
- Total: 342/day

**Monthly projection:** ~18,000 – 19,500 credits used, safely under 20K. Ay sonunda bile odds verisi gelmeye devam eder.

---

## Error Handling

- **API 429 (rate limit):** Existing backup-key switch logic unchanged.
- **Empty response for a sport key:** Cached as empty list for the refresh interval. No retry storm.
- **Bookmaker has no `h2h_3_way` AND no `h2h`:** Skip that bookmaker, continue with others.
- **All bookmakers filtered out:** Return `None` (same as "no match found" today).
- **Unknown bookmaker key:** Default weight 1.0 (treated as standard). Log at debug level for monitoring.
- **`commenceTimeFrom`/`commenceTimeTo` in wrong format:** The Odds API returns 400. We let it bubble as RequestException and fall back to no-time-filter on retry? **Decision: no fallback.** If our time formatting is wrong, that's a bug we fix in code, not at runtime. The ISO format is deterministic from `datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")`.

---

## Testing Strategy

### Unit Tests

**`tests/test_bookmaker_weights.py` (NEW):**
- `get_bookmaker_weight("pinnacle")` returns 3.0
- `get_bookmaker_weight("betfair_ex_eu")` returns 3.0
- `get_bookmaker_weight("bet365")` returns 1.5
- `get_bookmaker_weight("draftkings")` returns 1.0
- `get_bookmaker_weight("unknown_book")` returns 1.0
- `get_bookmaker_weight("")` returns 1.0
- Case insensitive: `get_bookmaker_weight("Pinnacle")` returns 3.0

**`tests/test_odds_sport_keys.py` (EXTEND):**
- `is_soccer_key("soccer_epl")` returns True
- `is_soccer_key("soccer_italy_serie_a")` returns True
- `is_soccer_key("baseball_mlb")` returns False
- `is_soccer_key("")` returns False
- `is_soccer_key(None)` returns False

**`tests/test_odds_api_bugs.py` (EXTEND):**
- `_build_odds_params("soccer_epl")` includes `markets=h2h,h2h_3_way`, `regions=us,uk,eu`
- `_build_odds_params("baseball_mlb")` includes `markets=h2h`, `regions=us,uk,eu`
- `_build_odds_params` includes `commenceTimeFrom` and `commenceTimeTo`, rounded to hour
- `_current_refresh_hours()` returns 2 when bootstrap (no usage data)
- `_current_refresh_hours()` returns 2 when usage 50%
- `_current_refresh_hours()` returns 3 when usage 75%
- `_current_refresh_hours()` returns 4 when usage 95%
- `get_bookmaker_odds()` filters out bookmaker with key "polymarket"
- `get_bookmaker_odds()` with soccer + h2h_3_way response returns `bookmaker_prob_draw`
- `get_bookmaker_odds()` with non-soccer returns `bookmaker_prob_draw = None`
- `get_bookmaker_odds()` weighted result: mock 2 bookmakers (pinnacle 0.64, draftkings 0.70), expect weighted average = (0.64×3 + 0.70×1) / 4 = 0.655
- `get_bookmaker_odds()` return dict contains `total_weight` and `has_sharp` fields

### Integration Test

- Full import chain: `from src.agent import Agent` succeeds, bot boots in dry-run mode, first cycle runs without errors.

### Regression Coverage

All existing tests in `test_odds_sport_keys.py` and `test_odds_api_bugs.py` must stay green after changes.

---

## Non-Goals (Explicit YAGNI)

- No historical odds usage (expensive, not needed for live betting)
- No `spreads` or `totals` markets (we only bet moneyline / series winner)
- No `/event/{id}/odds` endpoint (batch `/odds` is cheaper)
- No player props
- No futures/outrights
- No new data persisted to logs beyond existing cache file
- No changes to `Market` model schema
- No new config toggles — these are hard-coded strategy decisions, changing them is a code change

---

## Rollback Plan

All changes are contained in 5 files. If something breaks in production:

1. Revert the commit(s) for this feature
2. Old cache file is still compatible (same schema)
3. No database migrations, no schema changes, no external config

Bot restart is sufficient to return to previous state.

---

## Success Criteria

1. **Bookmaker coverage:** Soccer markets show ≥8 bookmakers per anchor (was 1-3). Non-soccer ≥5 (was 1-3).
2. **Sharp representation:** `has_sharp = True` in ≥70% of soccer anchors, ≥40% of non-soccer anchors (depends on Pinnacle coverage per sport).
3. **Budget safety:** Monthly credit usage stays under 19,500.
4. **No regressions:** All existing tests pass; all four Odds API bug fixes from the previous iteration remain green.
5. **No consumer breakage:** `entry_gate.py`, `live_strategies.py`, `upset_hunter.py` continue to function without modification beyond the one-line change in `entry_gate.py`.
6. **Soccer probability accuracy:** For soccer markets, the anchor probability now correctly separates draw from win, so "Will X win?" evaluations use the true win probability instead of a draw-inflated number.

---

## Open Questions

None. Tüm kararlar brainstorming oturumu sırasında kesinleşti.
