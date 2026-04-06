# Stock Queue Persistence + Overflow Routing Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two bugs: (1) stock queue is never persisted to disk so dashboard STOCK tab is always empty and bot restart loses stock, (2) when slots are full the ranker silently discards remaining high-score candidates instead of routing them to stock.

**Architecture:** Two surgical edits in `src/entry_gate.py`. (a) After the slot-full `break` in `_execute_candidates`, push remaining candidates to `_candidate_stock` (mirrors the existing EXPOSURE_CAP path 5 lines below). (b) Add a `_save_candidate_stock()` method that atomically writes `_candidate_stock` to `logs/candidate_stock.json`, called at the end of `run()`. Dashboard already reads this file via `/api/stock`.

**Tech Stack:** Python, json, pathlib (atomic write pattern already used throughout codebase).

---

## File Structure

| File | Change | Lines |
|---|---|---|
| `src/entry_gate.py` | MODIFY | ~15 lines added |

No new files. No other files touched.

---

### Task 1: Route overflow candidates to stock on slot-full break

**Files:**
- Modify: `src/entry_gate.py:891-894`

- [ ] **Step 1: Change the slot-full break to save remaining candidates**

In `src/entry_gate.py` `_execute_candidates()`, find lines 891-894:

```python
            # Slot check
            open_slots = cfg.risk.max_positions - self.portfolio.active_position_count
            if open_slots <= 0:
                break
```

Replace with:

```python
            # Slot check — if full, save remaining candidates to stock queue
            # so they can be drained when a slot opens (via exit or resolution).
            # Without this, high-score candidates (e.g. A-conf score=1.76) are
            # silently discarded when all 15 slots are occupied.
            open_slots = cfg.risk.max_positions - self.portfolio.active_position_count
            if open_slots <= 0:
                remaining_idx = candidates.index(c)
                overflow = candidates[remaining_idx:]
                for rc in overflow:
                    rc["added_at"] = datetime.now(timezone.utc).isoformat()
                    self._candidate_stock.append(rc)
                if overflow:
                    logger.info("Slots full — saved %d candidates to stock queue", len(overflow))
                break
```

- [ ] **Step 2: Run existing tests**

Run: `python -m pytest tests/test_match_exit.py tests/test_odds_api_bugs.py tests/test_reentry.py tests/test_bid_mtm.py tests/test_matcher_layer0.py -q`
Expected: 165 passed.

- [ ] **Step 3: Commit**

```bash
git add src/entry_gate.py
git commit -m "fix(entry_gate): route overflow candidates to stock when slots full"
```

---

### Task 2: Persist stock queue to disk

**Files:**
- Modify: `src/entry_gate.py` (add `_save_candidate_stock` method + call it from `run()`)

- [ ] **Step 1: Add the save method**

In `src/entry_gate.py`, after the existing `_prune_candidate_stock()` method (around line 258), add:

```python
    def _save_candidate_stock(self) -> None:
        """Persist candidate stock to disk so dashboard can display it.

        Uses atomic write (tmp + replace) consistent with portfolio.py.
        Dashboard reads this file via /api/stock endpoint.
        """
        stock_path = Path("logs/candidate_stock.json")
        try:
            stock_path.parent.mkdir(parents=True, exist_ok=True)
            serializable = []
            for c in self._candidate_stock:
                entry = {}
                market = c.get("market")
                if market:
                    entry["condition_id"] = getattr(market, "condition_id", "")
                    entry["slug"] = getattr(market, "slug", "")
                    entry["question"] = getattr(market, "question", "")
                    entry["yes_price"] = getattr(market, "yes_price", 0)
                    entry["sport_tag"] = getattr(market, "sport_tag", "")
                entry["score"] = c.get("score", 0)
                entry["confidence"] = c.get("estimate", {})
                if hasattr(entry["confidence"], "confidence"):
                    entry["confidence"] = entry["confidence"].confidence
                elif isinstance(entry["confidence"], dict):
                    entry["confidence"] = entry["confidence"].get("confidence", "")
                entry["edge"] = c.get("edge", 0)
                entry["added_at"] = c.get("added_at", "")
                entry["entry_reason"] = c.get("entry_reason", "")
                serializable.append(entry)
            tmp = stock_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(serializable, default=str), encoding="utf-8")
            tmp.replace(stock_path)
        except Exception as exc:
            logger.debug("Could not save candidate stock: %s", exc)
```

- [ ] **Step 2: Call it at the end of `run()`**

In `src/entry_gate.py` `run()` method, find line 224-225:

```python
        # Execute top N
        entered = self._execute_candidates(candidates, bankroll, cycle_count)
        return entered
```

Replace with:

```python
        # Execute top N
        entered = self._execute_candidates(candidates, bankroll, cycle_count)
        # Persist stock queue to disk so dashboard STOCK tab reflects reality
        self._save_candidate_stock()
        return entered
```

- [ ] **Step 3: Add `Path` import if not already present**

Check the imports at the top of `entry_gate.py`. `Path` should already be imported from `pathlib` (used elsewhere in the file). If not, add:

```python
from pathlib import Path
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_match_exit.py tests/test_odds_api_bugs.py tests/test_reentry.py tests/test_bid_mtm.py tests/test_matcher_layer0.py -q`
Expected: 165 passed.

- [ ] **Step 5: Import smoke test**

Run: `python -c "from src.entry_gate import EntryGate; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add src/entry_gate.py
git commit -m "feat(entry_gate): persist candidate stock to disk for dashboard"
```

---

### Task 3: Audit + push

- [ ] **Step 1: Single audit agent**

Audit scope:
- `_execute_candidates` overflow routing (no regression in entry logic)
- `_save_candidate_stock` serialization (handles missing market, Pydantic objects)
- `run()` calls save after execute
- No exit logic touched
- No dashboard HTML touched (it already reads the file)
- 165 tests pass

- [ ] **Step 2: Second audit if first is clean**

- [ ] **Step 3: Push**

```bash
git push origin master
```
