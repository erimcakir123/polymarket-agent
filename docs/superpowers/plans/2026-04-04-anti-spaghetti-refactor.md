# Anti-Spaghetti Refactoring Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate all CLAUDE.md rule violations — functions >80 lines, duplicated logic, misplaced business logic — without changing any runtime behavior.

**Architecture:** Pure refactoring. Extract helpers from large functions, deduplicate reentry pool logic, unify time-to-match calculations. Every change must be behavior-preserving — no new features, no threshold changes, no logic alterations.

**Tech Stack:** Python 3.11, no new dependencies. All changes are internal restructuring.

**Critical Rule:** Bot must NOT be running during refactoring. Kill before starting.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/time_utils.py` | Shared hours-to-match/start calculation |
| Modify | `src/exit_executor.py` | Extract `_add_to_reentry_pool()` helper |
| Modify | `src/agent.py` | Extract `_drain_exits()` helper |
| Modify | `src/entry_gate.py` | Split `_evaluate_candidates()` into sub-functions |
| Modify | `src/entry_gate.py` | Split `_analyze_batch()` into sub-functions |
| Modify | `src/upset_hunter.py` | Use shared `time_utils.hours_to_event()` |

---

## Phase 1: Low-Hanging Fruit (DRY violations + small helpers)

### Task 1: Extract shared `hours_to_event()` into `src/time_utils.py`

**Files:**
- Create: `src/time_utils.py`
- Modify: `src/entry_gate.py:1012-1035` — replace `_hours_to_start()` with import
- Modify: `src/upset_hunter.py:185-195` — replace `_hours_to_match()` with import
- Test: `tests/test_time_utils.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_time_utils.py
from datetime import datetime, timezone, timedelta
from src.time_utils import hours_to_event


def test_future_event():
    future = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    result = hours_to_event(future)
    assert 4.9 < result < 5.1


def test_past_event():
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    result = hours_to_event(past)
    assert -2.1 < result < -1.9


def test_none_input():
    assert hours_to_event(None) is None
    assert hours_to_event("") is None


def test_z_suffix():
    future = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = hours_to_event(future)
    assert 2.9 < result < 3.1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_time_utils.py -v`
Expected: FAIL with "No module named 'src.time_utils'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/time_utils.py
"""Shared time utilities for hours-to-event calculations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def hours_to_event(iso_str: Optional[str]) -> Optional[float]:
    """Hours until an event. Negative = already started. None = unparseable.

    Handles both '+00:00' and 'Z' suffixed ISO strings.
    """
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (dt - now).total_seconds() / 3600
    except (ValueError, TypeError):
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_time_utils.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Wire into entry_gate.py — replace `_hours_to_start()`**

In `src/entry_gate.py`, replace the standalone `_hours_to_start()` function (lines 1012-1035) with a wrapper that uses `hours_to_event`:

```python
# At top of entry_gate.py, add import:
from src.time_utils import hours_to_event

# Replace _hours_to_start function body (keep the function name for backward compat):
def _hours_to_start(market) -> float:
    """Hours until match starts. Wrapper around shared hours_to_event()."""
    start_iso = getattr(market, "match_start_iso", "") or ""
    if start_iso:
        result = hours_to_event(start_iso)
        if result is not None:
            return result
    end_iso = getattr(market, "end_date_iso", "") or ""
    result = hours_to_event(end_iso)
    return result if result is not None else 999.0
```

- [ ] **Step 6: Wire into upset_hunter.py — replace `_hours_to_match()`**

In `src/upset_hunter.py`, replace `_hours_to_match()` (lines 185-195):

```python
# At top of upset_hunter.py, add import:
from src.time_utils import hours_to_event

# Replace _hours_to_match:
def _hours_to_match(end_date_iso: str) -> Optional[float]:
    """Hours until match/resolution. Negative = already started."""
    return hours_to_event(end_date_iso)
```

- [ ] **Step 7: Verify full import chain works**

Run: `python -c "from src.entry_gate import _hours_to_start; from src.upset_hunter import _hours_to_match; print('OK')"`
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add src/time_utils.py tests/test_time_utils.py src/entry_gate.py src/upset_hunter.py
git commit -m "refactor: extract shared hours_to_event() into time_utils.py (DRY)"
```

---

### Task 2: Extract `_add_to_reentry_pool()` in `exit_executor.py`

**Files:**
- Modify: `src/exit_executor.py:31-203` — extract helper, call from 2 places

The `reentry_pool.add(...)` call with 16 identical kwargs appears at lines 69-87 and lines 105-125. Extract into a single helper.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exit_executor_helper.py
"""Test that _add_to_reentry_pool helper exists and is callable."""

def test_helper_exists():
    from src.exit_executor import ExitExecutor
    assert hasattr(ExitExecutor, '_add_to_reentry_pool')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_exit_executor_helper.py -v`
Expected: FAIL with "AssertionError"

- [ ] **Step 3: Add the helper method to ExitExecutor**

Add this method to the `ExitExecutor` class (before `exit_position`):

```python
def _add_to_reentry_pool(self, pos, condition_id: str, realized_pnl: float,
                          exit_reason: str = "", sl_reentry_count: int | None = None) -> None:
    """Add position to reentry pool — shared by profitable exits and lossy SL exits."""
    existing_pool = self.ctx.reentry_pool.get(condition_id)
    original_entry = existing_pool.original_entry_price if existing_pool else pos.entry_price
    kwargs = dict(
        condition_id=condition_id,
        event_id=getattr(pos, "event_id", "") or "",
        slug=pos.slug,
        question=getattr(pos, "question", ""),
        direction=pos.direction,
        token_id=pos.token_id,
        ai_probability=pos.ai_probability,
        confidence=pos.confidence,
        original_entry_price=original_entry,
        exit_price=pos.current_price,
        exit_cycle=self.ctx.cycle_count,
        end_date_iso=getattr(pos, "end_date_iso", ""),
        match_start_iso=getattr(pos, "match_start_iso", ""),
        sport_tag=getattr(pos, "sport_tag", ""),
        number_of_games=getattr(pos, "number_of_games", 0),
        was_scouted=getattr(pos, "scouted", False),
        realized_pnl=realized_pnl,
    )
    if exit_reason:
        kwargs["exit_reason"] = exit_reason
    if sl_reentry_count is not None:
        kwargs["sl_reentry_count"] = sl_reentry_count
    self.ctx.reentry_pool.add(**kwargs)
```

- [ ] **Step 4: Replace the two inline blocks with helper calls**

Replace lines 67-87 (profitable exit block):
```python
# Before (20 lines):
existing_pool = self.ctx.reentry_pool.get(condition_id)
original_entry = ...
self.ctx.reentry_pool.add(condition_id=..., ...)

# After (1 line):
self._add_to_reentry_pool(pos, condition_id, realized_pnl)
```

Replace lines 103-125 (SL lossy reentry block):
```python
# Before (21 lines):
existing_pool = self.ctx.reentry_pool.get(condition_id)
original_entry = ...
self.ctx.reentry_pool.add(condition_id=..., ...)

# After (1 line):
self._add_to_reentry_pool(pos, condition_id, realized_pnl,
                           exit_reason="stop_loss", sl_reentry_count=0)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_exit_executor_helper.py -v`
Expected: PASS

- [ ] **Step 6: Verify full import chain**

Run: `python -c "from src.exit_executor import ExitExecutor; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add src/exit_executor.py tests/test_exit_executor_helper.py
git commit -m "refactor: extract _add_to_reentry_pool() helper (DRY — was duplicated 2x)"
```

---

### Task 3: Extract `_drain_exits()` in `agent.py`

**Files:**
- Modify: `src/agent.py` — extract 3-line pattern into helper, replace 3 call sites

The pattern `for cid, reason in self.exit_monitor.drain(): if cid in ... exit_position(...)` appears 3 times (lines 332-334, 496-498, 625-627).

- [ ] **Step 1: Add helper method to Agent class**

```python
def _drain_exits(self) -> int:
    """Drain exit queue and execute pending exits. Returns count executed."""
    count = 0
    for cid, reason in self.exit_monitor.drain():
        if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
            self.exit_executor.exit_position(cid, reason)
            count += 1
    return count
```

- [ ] **Step 2: Replace all 3 call sites**

Line 332-334 → `self._drain_exits()`
Line 496-498 → `self._drain_exits()`
Line 625-627 → `self._drain_exits()`

- [ ] **Step 3: Verify import chain**

Run: `python -c "from src.agent import Agent; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/agent.py
git commit -m "refactor: extract _drain_exits() helper (DRY — was duplicated 3x)"
```

---

## Phase 2: Large Function Splits (>150 line functions)

### Task 4: Split `exit_position()` in `exit_executor.py` (173 lines → 4 helpers)

**Files:**
- Modify: `src/exit_executor.py:31-203`

The function has 4 distinct sections. Extract each as a private method:

- [ ] **Step 1: Extract `_route_post_exit()` — lines 61-163**

This is the routing logic (profitable → reentry, SL → lossy reentry or blacklist, else → stock/blacklist).

```python
def _route_post_exit(self, pos, condition_id: str, reason: str, realized_pnl: float) -> None:
    """Route exited position: reentry pool, blacklist, or stock demotion."""
    profitable_reasons = {
        "take_profit", "trailing_tp", "spike_exit",
        "edge_tp", "scale_out_final", "vs_take_profit",
    }
    if any(reason.startswith(r) for r in profitable_reasons) and realized_pnl > 0:
        self._add_to_reentry_pool(pos, condition_id, realized_pnl)
    elif reason == "stop_loss":
        self._handle_stop_loss_exit(pos, condition_id, realized_pnl)
    else:
        self._handle_unprofitable_exit(pos, condition_id, reason)
```

- [ ] **Step 2: Extract `_handle_stop_loss_exit()` — lines 88-138**

```python
def _handle_stop_loss_exit(self, pos, condition_id: str, realized_pnl: float) -> None:
    """Handle stop-loss exit: 2nd SL → blacklist, high AI → lossy reentry, else → blacklist."""
    _sl_count = getattr(pos, 'sl_reentry_count', 0)
    if _sl_count >= 1:
        self.ctx.blacklist.add(
            condition_id, exit_reason="stop_loss_2nd",
            blacklist_type="permanent", expires_at_cycle=None,
            exit_data={"slug": pos.slug},
        )
        logger.info("BLACKLIST: 2nd SL after lossy re-entry, permanent ban: %s", pos.slug[:40])
    elif pos.ai_probability >= 0.65:
        self._add_to_reentry_pool(pos, condition_id, realized_pnl,
                                   exit_reason="stop_loss", sl_reentry_count=0)
        logger.info("REENTRY_POOL: SL exit added (AI=%.0f%%): %s",
                    pos.ai_probability * 100, pos.slug[:40])
    else:
        btype, duration = get_blacklist_rule("stop_loss")
        if btype and duration:
            self.ctx.blacklist.add(
                condition_id, exit_reason="stop_loss",
                blacklist_type=btype,
                expires_at_cycle=self.ctx.cycle_count + duration if duration else None,
                exit_data={"slug": pos.slug},
            )
```

- [ ] **Step 3: Extract `_handle_unprofitable_exit()` — lines 139-163**

```python
def _handle_unprofitable_exit(self, pos, condition_id: str, reason: str) -> None:
    """Handle non-profitable exit: try stock demotion, else blacklist."""
    _is_never_stock = (
        reason in _NEVER_STOCK_EXITS
        or any(reason.startswith(p) for p in _NEVER_STOCK_PREFIXES)
    )
    demoted = False
    if not _is_never_stock:
        demoted = self.try_demote_to_stock(pos, reason)
    if not demoted:
        bl_reason = reason
        for prefix in ("match_exit_", "early_penny_", "SLOT_UPGRADE", "election_reeval"):
            if bl_reason.startswith(prefix):
                bl_reason = prefix.rstrip("_")
                break
        btype, duration = get_blacklist_rule(bl_reason)
        if btype and duration:
            self.ctx.blacklist.add(
                condition_id, exit_reason=reason,
                blacklist_type=btype,
                expires_at_cycle=self.ctx.cycle_count + duration if duration else None,
                exit_data={"slug": pos.slug},
            )
```

- [ ] **Step 4: Extract `_log_and_notify_exit()` — lines 165-183**

```python
def _log_and_notify_exit(self, pos, reason: str, realized_pnl: float) -> None:
    """Log exit to trade log and send Telegram notification."""
    self.ctx.trade_log.log({
        "market": pos.slug, "action": "EXIT",
        "reason": reason, "pnl": realized_pnl,
        "price": pos.entry_price, "exit_price": pos.current_price,
        "size": pos.size_usdc, "direction": pos.direction,
    })
    logger.info(
        "EXIT: %s | reason=%s | pnl=$%.2f | entry=%.2f exit=%.2f",
        pos.slug[:40], reason, realized_pnl, pos.entry_price, pos.current_price,
    )
    _pnl_emoji = "🟢" if realized_pnl >= 0 else "🔴"
    self.ctx.notifier.send(
        f"{_pnl_emoji} *EXIT*: {pos.slug[:40]}\n\n"
        f"📋 Reason: {reason}\n"
        f"💵 PnL: ${realized_pnl:+.2f}\n"
        f"📊 Entry: {pos.entry_price:.2f} -> Exit: {pos.current_price:.2f}"
    )
```

- [ ] **Step 5: Rewrite `exit_position()` as thin orchestrator**

```python
def exit_position(self, condition_id: str, reason: str, cooldown_cycles: int = 1) -> None:
    """Execute exit: sell, route to reentry/blacklist/stock, log."""
    self.ctx.exit_monitor.mark_exiting(condition_id)
    try:
        pos = self.ctx.portfolio.remove_position(condition_id)
    finally:
        self.ctx.exit_monitor.unmark_exiting(condition_id)
    if not pos:
        return

    self.ctx._exit_cooldowns[condition_id] = self.ctx.cycle_count + cooldown_cycles

    sell_result = self.ctx.executor.exit_position(pos, reason=reason, mode=self.ctx.config.mode)
    if sell_result.get("status") == "error":
        logger.error("EXIT SELL FAILED for %s — restoring: %s",
                     pos.slug[:35], sell_result.get("reason", "unknown"))
        self.ctx.portfolio.positions[condition_id] = pos
        self.ctx.portfolio.bankroll -= pos.size_usdc
        self.ctx.portfolio._save_positions()
        return

    realized_pnl = pos.unrealized_pnl_usdc
    self.ctx.portfolio.record_realized(realized_pnl)

    self._route_post_exit(pos, condition_id, reason, realized_pnl)
    self._log_and_notify_exit(pos, reason, realized_pnl)

    if reason in ("resolved", "near_resolve"):
        self.save_exited_market(condition_id)

    try:
        from src.price_history import save_price_history
        save_price_history(
            slug=pos.slug, token_id=pos.token_id,
            entry_price=pos.entry_price, exit_price=pos.current_price,
            exit_reason=reason, exit_layer="agent",
            match_start_iso=getattr(pos, "match_start_iso", ""),
            number_of_games=getattr(pos, "number_of_games", 0),
            ever_in_profit=pos.peak_pnl_pct > 0,
            peak_pnl_pct=pos.peak_pnl_pct,
            match_score=getattr(pos, "match_score", ""),
        )
    except Exception:
        pass
```

- [ ] **Step 6: Verify**

Run: `python -c "from src.exit_executor import ExitExecutor; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add src/exit_executor.py
git commit -m "refactor: split exit_position() 173→35 lines (4 extracted helpers)"
```

---

### Task 5: Split `_evaluate_candidates()` in `entry_gate.py` (290 lines → sub-functions)

**Files:**
- Modify: `src/entry_gate.py:561-850`

This is the largest function. Split into 3 phases that map to its internal structure:

- [ ] **Step 1: Identify the 3 phases inside `_evaluate_candidates()`**

Read `src/entry_gate.py` lines 561-850. The function has:
1. **Sanity checks** (~lines 570-650): validate market fields, skip resolved, check blacklist
2. **AI estimate evaluation** (~lines 650-750): parse AI response, apply anchor/consensus logic
3. **Edge & sizing** (~lines 750-850): compute edge, apply sport-specific rules, size position

- [ ] **Step 2: Extract `_sanity_check_candidate()` — returns True if candidate passes**

Extract the early-return checks into a method that returns `(passed: bool, skip_reason: str)`.

- [ ] **Step 3: Extract `_apply_edge_rules()` — esports-specific edge adjustments**

Extract the esports number_of_games edge boost, anchor logic, and consensus logic.

- [ ] **Step 4: Rewrite `_evaluate_candidates()` as a loop calling sub-functions**

The main function becomes a for-loop: sanity_check → evaluate → edge_rules → append to results.

- [ ] **Step 5: Verify**

Run: `python -c "from src.entry_gate import EntryGate; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/entry_gate.py
git commit -m "refactor: split _evaluate_candidates() 290→3 sub-functions"
```

---

### Task 6: Split `_analyze_batch()` in `entry_gate.py` (257 lines → sub-functions)

**Files:**
- Modify: `src/entry_gate.py:301-557`

- [ ] **Step 1: Identify internal phases**

Read `src/entry_gate.py` lines 301-557. Phases:
1. **Prioritization** (~50 lines): sort markets by time window
2. **Data enrichment** (~80 lines): fetch sports/odds data per market
3. **AI routing** (~80 lines): build prompts, call Claude API
4. **Result parsing** (~50 lines): parse AI responses

- [ ] **Step 2: Extract `_enrich_market_data()` — fetches sports context + odds**

- [ ] **Step 3: Extract `_parse_ai_responses()` — parses Claude output into estimates**

- [ ] **Step 4: Rewrite `_analyze_batch()` as orchestrator**

- [ ] **Step 5: Verify and commit**

```bash
git add src/entry_gate.py
git commit -m "refactor: split _analyze_batch() 257→3 sub-functions"
```

---

## Phase 3: Agent.py Cleanup

### Task 7: Split `run_cycle()` in `agent.py` (164 lines → phase methods)

**Files:**
- Modify: `src/agent.py:425-588`

- [ ] **Step 1: Identify cycle phases**

The run_cycle has: banking → circuit breaker → market scan → exit check → entry gate → portfolio update. Each is a natural method.

- [ ] **Step 2: Extract `_phase_banking()`, `_phase_scan()`, `_phase_exits()`, `_phase_entries()`**

Each phase is 20-40 lines. `run_cycle()` becomes:

```python
def run_cycle(self):
    self._phase_banking()
    if self._phase_circuit_breaker():
        return
    markets = self._phase_scan()
    self._phase_exits()
    self._phase_entries(markets)
    self._phase_portfolio_update()
```

- [ ] **Step 3: Verify and commit**

```bash
git add src/agent.py
git commit -m "refactor: split run_cycle() 164→6 phase methods"
```

---

## Validation

After all tasks are complete:

- [ ] **Final validation: full import test**

```bash
python -c "
from src.main import main
from src.agent import Agent
from src.entry_gate import EntryGate
from src.exit_executor import ExitExecutor
from src.time_utils import hours_to_event
print('All imports OK')
"
```

- [ ] **Final validation: no runtime changes**

The bot behavior must be 100% identical. All changes are structural only — no thresholds, no logic, no new features.

---

## Out of Scope (Not in this plan)

These were identified in the audit but are larger refactors for a separate plan:

- `sports_data.py` (1331 lines) → split into 4 modules
- `entry_gate.py` `_execute_candidates()` (154 lines) → reasonable size, skip for now
- `live_strategies.py` long functions → separate plan
- `agent.__init__()` (115 lines) → module factory extraction
- Late imports (44 locations) → separate cleanup pass
- Global singleton in `matching/__init__.py` → needs DI refactor
- `dashboard.py` route extraction → not trading-critical
