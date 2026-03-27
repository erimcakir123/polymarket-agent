# Bot Fixes & Strategy Rewrite — Design Spec

## Goal

Fix 6 issues discovered during bridge production test: executor crash, wrong trade direction, low bridge match rate, PandaScore instability, dashboard offline status, and silent Telegram notifications.

## Priority Order

1. Executor crash (blocks all exits)
2. Strategy rewrite (wrong trade direction)
3. Bridge lazy fetch (API waste)
4. PandaScore retry (intermittent failures)
5. Dashboard offline (missing status file)
6. Telegram fix (silent notifications)

---

## 1. Executor Crash — `exit_position` Missing

### Problem

`agent.py:427` calls `self.executor.exit_position(pos, reason, mode)` but this method does not exist in `executor.py`. Only `place_exit_order(token_id, shares)` exists. Bot crashes with `AttributeError` on every exit attempt, entering an infinite light-cycle loop.

### Fix

Add `exit_position(pos, reason, mode)` method to `src/executor.py`:
- In `dry_run` mode: simulate exit, log reason + PnL
- In `live` mode: call existing `place_exit_order(pos.token_id, pos.shares)`
- Log the exit with reason and mode for audit trail

### Files Changed

- `src/executor.py` — add method

### Breaking Impact

None — new method, no existing code changes.

---

## 2. Strategy Rewrite — Trade Direction Fix

### Problem

Bot uses AI probability to pick direction (whoever AI gives >50%). Shrinkage formula (`AI * 0.90 + 0.50 * 0.10`) pulls everything toward 50%, causing:
- AI=75% → shrunk=67.5% (still correct direction)
- AI=55% → shrunk=54.5% (fragile, small margin)
- AI=42% → shrunk=42.8% → picks NO side → bets on underdog

User's rule: **Bet on whoever AI thinks will win. If AI and market agree on favorite, no edge requirement — the edge IS the 99¢ payout.**

### New Logic

```
1. Get raw AI probability (before shrinkage)
2. Determine market favorite: yes_price > 0.50 → YES favorite
3. Determine AI favorite: ai_p > 0.50 → YES favorite

CASE A: AI and market agree (both favor same side)
  → Direction = favorite side
  → Edge = 0.99 - entry_price (payout potential)
  → Shrinkage SKIPPED (market already confirms)
  → ai_probability used raw for mode classification

CASE B: AI and market disagree
  → Current shrinkage + edge logic preserved
  → More cautious entry (AI contradicts market)

MODE classification (on direction_prob):
  < 55%  → SKIP (too uncertain, don't trade)
  55-65% → DEADZONE (low confidence, pre-match exit)
  ≥ 65%  → WINNER (hold-to-resolve)
```

### Files Changed

- `src/entry_gate.py` — lines 485-510: direction/edge/mode logic
- `src/probability_engine.py` — add bypass flag for market-AI agreement

### Breaking Impact (3 items — all must be fixed)

**1. sanity_check.py will block valid trades:**
- Current: `if edge > 0.25` → blocks as "data error"
- New edge = 99¢ - 70¢ = 29% → BLOCKED
- Fix: When AI+market agree (consensus mode), skip the edge>0.25 check or raise threshold to 0.50

**2. predictions.jsonl cache mismatch:**
- Old HOLD entries use 0.65 threshold for consensus detection
- New logic uses 0.55
- Fix: Clear predictions.jsonl on bot restart (already done during reset)

**3. test_entry_modes.py assertions break:**
- Threshold changes from <65% DEADZONE to <55% SKIP + 55-65% DEADZONE
- Fix: Update test assertions to match new thresholds, add tests for 54%/55%/65% boundaries

### Unchanged

- FAV promotion logic (uses market price, not direction_prob)
- Kelly sizing (uses ai_prob + market_price directly, sizing_edge is dead code)
- Exit logic (reads mode string, names stay WINNER/DEADZONE)
- Trailing TP (independent of entry logic)

---

## 3. Bridge Lazy Fetch

### Problem

`refresh_bridge_events()` pre-fetches 20 sport keys (20 API calls) at cycle start, but most events are unused. Only 1/20 markets matched. API waste with no benefit.

### New Logic

- Remove `refresh_bridge_events()` pre-fetch
- `bridge_match()` becomes lazy: when a market arrives, detect sport from slug → fetch that sport key on-demand → cache as `bridge:{sport_key}` with 3h TTL
- Second market in same sport → served from `bridge:{sport_key}` cache, no API call
- Cross-populate from `get_bookmaker_odds()` stays as-is

### Files Changed

- `src/odds_api.py` — refactor `bridge_match()` to lazy fetch, remove `refresh_bridge_events()`
- `src/entry_gate.py` — remove `refresh_bridge_events()` call
- `tests/test_odds_bridge.py` — update `TestRefreshBridgeEvents` tests

### Breaking Impact

- `refresh_bridge_events()` called in entry_gate.py → remove call
- Tests asserting pre-fetch behavior → rewrite for lazy behavior
- Cross-populate in `get_bookmaker_odds` → unchanged (writes to same cache keys)

---

## 4. PandaScore Retry + Connection Pooling

### Problem

PandaScore API returns intermittent 500 errors and connection timeouts. Token is valid and active, but free-tier servers are unreliable. Bot gets no esports context data when this happens.

### Fix

- Reduce timeout: 10s → 5s (fail fast)
- Add 1x retry with 2s backoff on 500/timeout
- Use `requests.Session()` for TCP connection reuse
- Log retry attempts at INFO level

### Files Changed

- `src/esports_data.py` — `_api_request()` method (both instances at lines 68-80 and 304-316)

### Breaking Impact

None — transport layer only, same data returned. No consumers affected.

---

## 5. Dashboard Offline — Missing Status File

### Problem

Dashboard reads `logs/bot_status.json` for cycle status. Agent never writes this file. Dashboard always shows "Hard cycle: Offline" and "Light cycle: Offline".

### Fix

Add `_write_status(state, step, **kwargs)` method to `src/agent.py`:
- Hard cycle start: `{"state": "running", "step": "Hard cycle", "ts": "<iso>", "has_positions": true}`
- Light cycle: `{"state": "running", "step": "Light cycle", "light_ts": "<iso>", "has_positions": true}`
- Waiting: `{"state": "waiting", "step": "Waiting (15min)"}`
- Write atomically (write to tmp, rename)

### Files Changed

- `src/agent.py` — add `_write_status()`, call at cycle transitions

### Breaking Impact

None — dashboard already expects this format, file just didn't exist.

---

## 6. Telegram Fix — Silent Notifications

### Problem

No Telegram log entries in bot.log — not even startup flush. Token is in .env, config says enabled. Possible causes: invalid/revoked token, silent exception swallowing.

### Fix

- At startup: call `getMe` API to validate token, log result at INFO level
- On success: `"Telegram connected: @BotName (chat_id: 5102852678)"`
- On failure: `"Telegram FAILED: <error>"`  → set `self.enabled = False`
- In `send()`: log response body on non-200 status (currently only logs exceptions)

### Files Changed

- `src/notifier.py` — add `_validate_token()` at init, improve `send()` logging

### Breaking Impact

None — only logging changes.

---

## Execution Order

1. Executor fix (unblocks exits)
2. Strategy rewrite + 3 breaking fixes (sanity_check, cache, tests)
3. Bridge lazy fetch
4. PandaScore retry
5. Dashboard status
6. Telegram validation

Items 4-6 are independent and can be done in any order after 1-3.

---

## Out of Scope

- Batch size increase (currently 10-20 markets per cycle) — separate discussion
- PandaScore server reliability (their infrastructure, can't control)
- Bridge match rate improvement beyond lazy fetch (team name matching improvements — future work)
- Correlation risk system (user explicitly does not want this)
