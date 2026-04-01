# Interleaved Light Exit Checks Between Heavy Phases

**Date:** 2026-04-01
**Status:** Proposed
**Supersedes:** 2026-03-29-interleaved-exits-design.md (partially — refines the interleave concept)
**Files affected:** `src/agent.py` only

---

## 1. Problem

The heavy cycle takes ~25 minutes end-to-end. Current phase timings:

| Phase | Duration | Notes |
|-------|----------|-------|
| 1. reflection | ~0s | |
| 2. bankroll+drawdown+cb | ~0s | |
| 3. price_update+resolved | ~60s | |
| 4. exit_detection | ~0s (no positions) / seconds (with) | |
| 5. scout+scan | 237-285s | **HEAVY** |
| 6. entry_gate_ai | ~1530s | **HEAVY** (enrichment + AI) |
| 7. stock_drain | ~0s | |
| 8. upset_hunter | ~89s | |
| 9. sleep | configurable | |

Between phases 5-8, if a position's price moves significantly (stop-loss hit, take-profit opportunity), the bot is blind for ~25 minutes. A position could blow through its stop-loss and the bot wouldn't react until the next full exit detection pass.

**Current state:** `_quick_exit_check()` already exists (from 2026-03-29 spec) and runs at 4 interleave points. This spec proposes replacing it with a more focused `_light_exit_check()` that fetches fresh CLOB prices directly instead of relying solely on WebSocket tick drain.

---

## 2. Design

### 2.1 New Method: `_light_exit_check()`

A lightweight exit sweep that actively fetches current prices rather than passively draining WS ticks:

```python
def _light_exit_check(self) -> None:
    """Fast exit check between heavy phases. Fetches fresh CLOB prices
    and runs exit logic. No enrichment, no AI, no scanning.

    ~2-5s with active positions, instant (0s) with none.
    """
    positions = self.portfolio.positions
    if not positions:
        return  # no-op, 0s

    t0 = time.monotonic()
    n_positions = len(positions)

    # 1. Fetch current prices for all active positions (CLOB API, fast)
    for cid, pos in positions.items():
        try:
            price = self.executor.fetch_current_price(cid, pos.side)
            if price is not None:
                pos.current_price = price
        except Exception:
            pass  # stale price is acceptable, don't block

    # 2. Run exit logic with updated prices
    exits_triggered = 0
    for cid, reason in self.exit_monitor.check_exits_light():
        if cid in positions and not self.exit_monitor.is_exiting(cid):
            self.exit_executor.exit_position(cid, reason)
            exits_triggered += 1

    # 3. Process any pending scale-outs
    self.exit_executor.process_scale_outs()

    elapsed = time.monotonic() - t0
    logger.info("Light exit check: %d positions, %d exits triggered (%.1fs)",
                n_positions, exits_triggered, elapsed)
```

### 2.2 Insertion Points

```
Phase 4: exit_detection
Phase 5: scout+scan               ← HEAVY (237-285s)
  → _light_exit_check()
Phase 6: entry_gate_ai             ← HEAVY (1530s)
  → _light_exit_check()
Phase 7: stock_drain
Phase 8: upset_hunter
```

Two insertion points, after the two heaviest phases. This ensures:
- Max blind window drops from ~25 min to ~5 min (duration of longest single phase)
- Each check adds at most 5s to total cycle time

### 2.3 Key Differences from Current `_quick_exit_check()`

| Aspect | Current `_quick_exit_check()` | Proposed `_light_exit_check()` |
|--------|-------------------------------|-------------------------------|
| Price source | WS tick drain (passive) | CLOB API fetch (active) |
| No-position behavior | Still runs drain + summary | True no-op, returns immediately |
| Dashboard update | Writes portfolio snapshot every call | Does not write snapshot (avoids I/O) |
| Bankroll parameter | Required (passed for summary) | Not required |
| Exit count logging | No | Yes — logs positions checked and exits triggered |

The active price fetch is the critical difference. WebSocket ticks can be delayed or missed; a direct CLOB price fetch guarantees fresh data.

---

## 3. Constraints

- **Speed:** Must complete in <5s. Only price fetch + exit logic. No enrichment, no AI, no market scanning.
- **State safety:** Must not interfere with heavy phase state. `entry_gate` maintains `_seen_market_ids` and other stateful caches — light check does not touch these.
- **Thread safety:** Bot is single-threaded, so portfolio writes during light check have no race conditions.
- **Mode respect:** Exit execution uses the same `executor.py` path — dry_run/paper/live mode is honored.
- **No-position no-op:** If `portfolio.positions` is empty, return immediately (0s overhead).

---

## 4. Future Consideration

During the `entry_gate_ai` phase (~25 min), we could insert light checks between individual AI analysis calls (each takes ~30s). This would reduce the max blind window from ~25 min to ~30s. However, this is more invasive — `entry_gate.run()` would need to accept a callback or yield between analyses. Deferred to a follow-up spec.

---

## 5. Files Changed

| File | Change | Lines |
|------|--------|-------|
| `src/agent.py` | Add `_light_exit_check()` method, replace 2 of the 4 existing `_quick_exit_check()` calls with it | +25, -2 |

**Net:** ~+23 lines. Single file change, no new imports needed (executor and exit_monitor already available on `self`).

---

## 6. What NOT to Change

- `exit_monitor.py` — `check_exits_light()` already exists, no changes needed
- `executor.py` — `fetch_current_price()` or equivalent already exists
- `portfolio.py` — position price update is a simple attribute set
- `entry_gate.py` — not touched, stateful caches remain isolated
- Light cycle structure — unchanged
- No new files, no new classes, no new config parameters
