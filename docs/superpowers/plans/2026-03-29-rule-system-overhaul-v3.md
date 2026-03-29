# Rule System Overhaul v3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 critical bugs (P0), 4 high-risk issues (P1), and restructure the cycle architecture so exits and re-entries happen in seconds instead of 30 minutes.

**Architecture:** 3-tier cycle model (WebSocket → Light 5s → Heavy 30min). Light cycle handles ALL actions (exits, re-entries, entries). Heavy cycle handles only scanning and AI. Entry/exit rules updated for upset protection, bidirectional upset hunting, lossy re-entry, and exposure safety.

**Tech Stack:** Python 3.11+, Pydantic config, existing module structure. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-03-29-rule-system-overhaul-v3-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/config.py` | Modify | `FarConfig` → `EarlyEntryConfig`, add `max_entry_price`, `RiskConfig` + `max_exposure_pct`, VS `reserved_slots: 3` |
| `src/match_exit.py` | Modify | Upset exempt graduated SL, upset forced exit price filter, never-in-profit upset/penny exempt, catastrophic floor 20¢ |
| `src/exit_monitor.py` | Modify | Remove pre-match exit call, upset trailing TP skip below 35¢, exit detailed logging |
| `src/agent.py` | Modify | Light cycle architecture, cooldown system, light_cycle_count, lossy re-entry, event dedup, penny timing, `far_penny_` → `early_penny_` prefix, `"is_far"` dict key |
| `src/upset_hunter.py` | Modify | YES+NO direction support in UpsetCandidate and pre_filter |
| `src/entry_gate.py` | Modify | `is_far` → `is_early`, `_far_market_ids` → `_early_market_ids`, `_far_stock` → `_early_stock`, global filter 5-95%, exposure guard |
| `src/reentry_farming.py` | Modify | Accept lossy exits, 40% recovery filter, SL counter tracking |
| `src/adaptive_kelly.py` | Modify | `is_far` → `is_early` rename |
| `src/portfolio.py` | Modify | Remove `check_pre_match_exits()`, `_SPECIAL_ENTRY_REASONS` "far" → "early", `entry_reason == "far"` → "early" |
| `src/reentry.py` | Modify | `"far_penny"` → `"early_penny"` exit reason mapping |
| `src/sport_rules.py` | Modify | Remove `pre_match_mandatory_exit_min` from all 15 sport definitions (dead config) |
| `src/models.py` | Modify | Add `is_early` field (rename from `is_far`) |
| `config.yaml` | Modify | `far:` section → `early:` (lines 62-77) |
| `tests/test_match_exit.py` | Modify | Update graduated SL tests for upset exemption, catastrophic floor 20¢ |
| `tests/test_entry_modes.py` | Modify | `gate._far_market_ids` → `gate._early_market_ids` |
| `tests/test_sports_context_pipeline.py` | Modify | `gate._far_market_ids` → `gate._early_market_ids`, `gate._far_stock` → `gate._early_stock` |
| `tests/test_scale_out.py` | No change | Already config-driven |

---

### Task 1: P0 — Catastrophic Floor Threshold 25¢ → 20¢

**Files:**
- Modify: `src/match_exit.py:282`
- Modify: `tests/test_match_exit.py:223-262`

- [ ] **Step 1: Write the failing test**

In `tests/test_match_exit.py`, add a test for the new 20¢ threshold:

```python
def test_catastrophic_floor_triggers_at_20c_entry(self):
    """Catastrophic floor should trigger for entries as low as 20¢."""
    result = check_match_exit(
        entry_reason="winner",
        effective_entry=0.20,
        effective_current=0.09,  # Below 50% of 20¢
        elapsed_pct=0.50,
        ever_in_profit=False,
        peak_pnl_pct=0.0,
        consecutive_down_cycles=0,
        cumulative_drop=0.0,
        hold_candidate=False,
        is_reentry=False,
    )
    assert result is not None
    assert result[1] == "match_exit_catastrophic_floor"


def test_catastrophic_floor_skips_below_20c_entry(self):
    """Catastrophic floor should NOT trigger for entries below 20¢ (penny/upset territory)."""
    result = check_match_exit(
        entry_reason="winner",
        effective_entry=0.19,
        effective_current=0.08,
        elapsed_pct=0.50,
        ever_in_profit=False,
        peak_pnl_pct=0.0,
        consecutive_down_cycles=0,
        cumulative_drop=0.0,
        hold_candidate=False,
        is_reentry=False,
    )
    # Should not trigger catastrophic floor for sub-20¢ entries
    assert result is None or result[1] != "match_exit_catastrophic_floor"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::TestLayer1CatastrophicFloor::test_catastrophic_floor_triggers_at_20c_entry -v`
Expected: FAIL (current threshold is 0.25, so 0.20 entry won't trigger)

- [ ] **Step 3: Change threshold in match_exit.py**

In `src/match_exit.py` line 282, change:
```python
# OLD
if effective_entry >= 0.25 and effective_current < effective_entry * cat_floor_mult:
# NEW
if effective_entry >= 0.20 and effective_current < effective_entry * cat_floor_mult:
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/match_exit.py tests/test_match_exit.py
git commit -m "fix(P0): lower catastrophic floor threshold from 25¢ to 20¢"
```

---

### Task 2: P0 — VS Reserved Slots 5 → 3

**Files:**
- Modify: `src/config.py:99`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py (create if not exists)
from src.config import AppConfig

def test_vs_reserved_slots_default_is_3():
    cfg = AppConfig()
    assert cfg.volatility_swing.reserved_slots == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_config.py::test_vs_reserved_slots_default_is_3 -v`
Expected: FAIL (current default is 5)

- [ ] **Step 3: Change default in config.py**

In `src/config.py` line 99, change:
```python
# OLD
reserved_slots: int = 5
# NEW
reserved_slots: int = 3
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_config.py::test_vs_reserved_slots_default_is_3 -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/config.py tests/test_config.py
git commit -m "fix(P0): reduce VS reserved slots from 5 to 3"
```

---

### Task 3: P0 — Exposure Guard

**Files:**
- Modify: `src/config.py:59-91` (RiskConfig)
- Modify: `src/agent.py` (entry gate check before all entries)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exposure_guard.py
def test_exposure_guard_blocks_when_over_limit():
    """Entry should be blocked when total_invested + candidate_size > 35% of bankroll."""
    bankroll = 1000.0
    total_invested = 300.0  # 30% already
    candidate_size = 100.0   # Would push to 40%
    max_exposure_pct = 0.35

    over_limit = (total_invested + candidate_size) / bankroll > max_exposure_pct
    assert over_limit is True


def test_exposure_guard_allows_when_under_limit():
    """Entry should be allowed when total_invested + candidate_size <= 35% of bankroll."""
    bankroll = 1000.0
    total_invested = 200.0  # 20% already
    candidate_size = 100.0   # Would push to 30%
    max_exposure_pct = 0.35

    over_limit = (total_invested + candidate_size) / bankroll > max_exposure_pct
    assert over_limit is False
```

- [ ] **Step 2: Run test to verify it passes (logic test)**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_exposure_guard.py -v`
Expected: PASS (pure logic test)

- [ ] **Step 3: Add max_exposure_pct to RiskConfig**

In `src/config.py`, add to `RiskConfig` class (after line 77):
```python
max_exposure_pct: float = 0.35
```

- [ ] **Step 4: Add exposure check to agent.py**

In `src/agent.py`, create a helper method in the Agent class:

```python
def _check_exposure_limit(self, candidate_size: float) -> bool:
    """Return True if adding candidate_size would exceed exposure limit."""
    total_invested = sum(p.size_usdc for p in self.portfolio.positions.values())
    bankroll = self.portfolio.bankroll
    if bankroll <= 0:
        return True
    return (total_invested + candidate_size) / bankroll > self.config.risk.max_exposure_pct
```

Then add this check before every entry execution call. In each entry method (`_check_live_dip`, `_check_live_momentum`, `_check_upset_hunter`, `_check_penny_alpha`, and the heavy cycle entry paths), add before the `_execute_entry()` or `_place_order()` call:

```python
if self._check_exposure_limit(size_usdc):
    logger.info("SKIP exposure cap: %.0f%% > %.0f%%",
                (total_invested + size_usdc) / bankroll * 100,
                self.config.risk.max_exposure_pct * 100)
    return
```

- [ ] **Step 5: Run all tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/config.py src/agent.py tests/test_exposure_guard.py
git commit -m "fix(P0): add exposure guard — block entries when >35% bankroll invested"
```

---

### Task 4: Match Exit — Upset Exempt from Graduated SL

**Files:**
- Modify: `src/match_exit.py:321-336`
- Modify: `tests/test_match_exit.py:136-187`

- [ ] **Step 1: Write the failing test**

```python
# In tests/test_match_exit.py
def test_upset_exempt_from_graduated_sl():
    """Upset positions should never trigger graduated SL."""
    result = check_match_exit(
        entry_reason="upset",
        effective_entry=0.10,
        effective_current=0.06,  # Would normally trigger graduated SL
        elapsed_pct=0.85,
        ever_in_profit=False,
        peak_pnl_pct=0.0,
        consecutive_down_cycles=6,
        cumulative_drop=0.04,
        hold_candidate=False,
        is_reentry=False,
    )
    # Upset should NOT get graduated SL exit
    assert result is None or "graduated" not in result[1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::test_upset_exempt_from_graduated_sl -v`
Expected: FAIL (upset currently goes through graduated SL)

- [ ] **Step 3: Add upset exemption before graduated SL block**

In `src/match_exit.py`, before the graduated SL block (line ~321), add:

```python
# Upset positions use their own SL (50%) and forced exit at 90%
# Skip graduated SL — it kills upsets at exactly the wrong time
if entry_reason == "upset":
    pass  # Skip to next layer
else:
    # ... existing graduated SL logic (lines 321-336) ...
```

Wrap the existing graduated SL code in the `else` branch.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/match_exit.py tests/test_match_exit.py
git commit -m "fix(P1): exempt upset positions from graduated SL"
```

---

### Task 5: Match Exit — Upset Forced Exit with Price Filter

**Files:**
- Modify: `src/match_exit.py:297-308`

- [ ] **Step 1: Write the failing tests**

```python
# In tests/test_match_exit.py
def test_upset_forced_exit_holds_above_60c():
    """Upset at 90%+ elapsed but price >= 60¢ should HOLD (became favorite)."""
    result = check_match_exit(
        entry_reason="upset",
        effective_entry=0.10,
        effective_current=0.65,
        elapsed_pct=0.92,
        ever_in_profit=True,
        peak_pnl_pct=5.50,
        consecutive_down_cycles=0,
        cumulative_drop=0.0,
        hold_candidate=False,
        is_reentry=False,
    )
    assert result is None  # Should HOLD


def test_upset_forced_exit_takes_profit_50_to_60c():
    """Upset at 90%+ elapsed with price 50-60¢ should take profit."""
    result = check_match_exit(
        entry_reason="upset",
        effective_entry=0.10,
        effective_current=0.55,
        elapsed_pct=0.92,
        ever_in_profit=True,
        peak_pnl_pct=4.50,
        consecutive_down_cycles=0,
        cumulative_drop=0.0,
        hold_candidate=False,
        is_reentry=False,
    )
    assert result is not None
    assert result[1] == "upset_take_profit"


def test_upset_forced_exit_below_50c():
    """Upset at 90%+ elapsed with price < 50¢ should force exit."""
    result = check_match_exit(
        entry_reason="upset",
        effective_entry=0.10,
        effective_current=0.12,
        elapsed_pct=0.92,
        ever_in_profit=False,
        peak_pnl_pct=0.20,
        consecutive_down_cycles=0,
        cumulative_drop=0.0,
        hold_candidate=False,
        is_reentry=False,
    )
    assert result is not None
    assert result[1] == "upset_forced_exit"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::test_upset_forced_exit_holds_above_60c tests/test_match_exit.py::test_upset_forced_exit_takes_profit_50_to_60c tests/test_match_exit.py::test_upset_forced_exit_below_50c -v`
Expected: FAIL (current code exits blindly at 90%)

- [ ] **Step 3: Replace blind forced exit with price-aware logic**

In `src/match_exit.py`, replace the upset forced exit block (lines ~297-308) with:

```python
# --- Upset forced exit (price-aware) ---
if entry_reason == "upset" and elapsed_pct is not None and elapsed_pct >= 0.90:
    if effective_current >= 0.60:
        pass  # HOLD — became favorite, let it resolve
    elif effective_current >= 0.50:
        return (True, "upset_take_profit")  # Risky zone, take profit
    else:
        return (True, "upset_forced_exit")  # Still underdog, exit

# Fallback for upset without timing data
if entry_reason == "upset" and elapsed_pct is None:
    # Keep existing 3h max hold + PnL < 0 check (lines 304-308)
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/match_exit.py tests/test_match_exit.py
git commit -m "feat: upset forced exit with 3-tier price filter (hold/TP/exit)"
```

---

### Task 6: Match Exit — Never-in-Profit Guard: Upset + Penny Exempt

**Files:**
- Modify: `src/match_exit.py:344-354`
- Modify: `tests/test_match_exit.py:264-335`

- [ ] **Step 1: Write the failing test**

```python
def test_upset_exempt_from_never_in_profit():
    """Upset positions should not be killed by never-in-profit guard."""
    result = check_match_exit(
        entry_reason="upset",
        effective_entry=0.10,
        effective_current=0.09,
        elapsed_pct=0.75,
        ever_in_profit=False,
        peak_pnl_pct=0.0,
        consecutive_down_cycles=0,
        cumulative_drop=0.01,
        hold_candidate=False,
        is_reentry=False,
    )
    assert result is None or "never_in_profit" not in result[1]


def test_penny_exempt_from_never_in_profit():
    """Penny positions should not be killed by never-in-profit guard."""
    result = check_match_exit(
        entry_reason="penny",
        effective_entry=0.02,
        effective_current=0.015,
        elapsed_pct=0.75,
        ever_in_profit=False,
        peak_pnl_pct=0.0,
        consecutive_down_cycles=0,
        cumulative_drop=0.005,
        hold_candidate=False,
        is_reentry=False,
    )
    assert result is None or "never_in_profit" not in result[1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::test_upset_exempt_from_never_in_profit tests/test_match_exit.py::test_penny_exempt_from_never_in_profit -v`
Expected: FAIL

- [ ] **Step 3: Add exemption before never-in-profit check**

In `src/match_exit.py`, before the never-in-profit guard (line ~344), add:

```python
if entry_reason in ("upset", "penny"):
    pass  # Skip never-in-profit — these are designed to stay out of profit until late
else:
    # ... existing never-in-profit logic (lines 344-354) ...
```

- [ ] **Step 4: Run tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/match_exit.py tests/test_match_exit.py
git commit -m "fix(P1): exempt upset and penny from never-in-profit guard"
```

---

### Task 7: Exit Monitor — Trailing TP Skip Below 35¢ for Upsets

**Files:**
- Modify: `src/exit_monitor.py:147-162`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exit_monitor.py (add to existing or create)
def test_upset_trailing_tp_skipped_below_35c():
    """Upset positions below promotion price (35¢) should not trigger trailing TP."""
    # When effective_current < 0.35 and entry_reason == "upset":
    # trailing TP should be completely skipped
    # (Only scale-out tiers and hold-to-resolve apply)
    entry_reason = "upset"
    effective_current = 0.30
    promotion_price = 0.35

    should_skip_trailing = entry_reason == "upset" and effective_current < promotion_price
    assert should_skip_trailing is True


def test_upset_trailing_tp_active_above_35c():
    """Upset positions above 35¢ should use core trailing TP params."""
    entry_reason = "upset"
    effective_current = 0.40
    promotion_price = 0.35

    should_skip_trailing = entry_reason == "upset" and effective_current < promotion_price
    assert should_skip_trailing is False
```

- [ ] **Step 2: Run test**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_exit_monitor.py -v`
Expected: PASS (logic test)

- [ ] **Step 3: Add explicit skip in exit_monitor.py**

In `src/exit_monitor.py`, in the trailing TP section for upset positions (lines ~147-162), add before the trailing TP calculation:

```python
# Upset below promotion price: skip trailing TP entirely
# Only scale-out (25¢/35¢ tiers) and hold-to-resolve apply
if entry_reason == "upset" and effective_current < self.config.upset_hunter.promotion_price:
    continue  # or skip this position for trailing TP
```

If price >= promotion_price, use core trailing TP params (activation 20%, trail 8%) instead of the upset-specific params (100% activation, 25% trail).

- [ ] **Step 4: Run all exit monitor tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_exit_monitor.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/exit_monitor.py tests/test_exit_monitor.py
git commit -m "fix(P1): skip trailing TP for upset positions below 35¢"
```

---

### Task 8: Exit Monitor — Remove Pre-Match Exit + Dead Config Cleanup + Detailed Logging

**Files:**
- Modify: `src/exit_monitor.py:299` (remove pre-match exit call)
- Modify: `src/exit_monitor.py:216-219, 315-318` (detailed logging)
- Modify: `src/portfolio.py:579-607` (remove method)
- Modify: `src/agent.py:51-55` (remove from _NEVER_STOCK_EXITS)
- Modify: `src/sport_rules.py` (remove `pre_match_mandatory_exit_min` from all 15 sport definitions)

- [ ] **Step 1: Remove pre-match exit call from exit_monitor.py**

In `src/exit_monitor.py`, delete line 299:
```python
# DELETE this block:
for cid in self.portfolio.check_pre_match_exits(minutes_before=30):
    _add(cid, "pre_match_exit")
```

- [ ] **Step 2: Remove check_pre_match_exits from portfolio.py**

In `src/portfolio.py`, delete the `check_pre_match_exits()` method (lines 579-607).

- [ ] **Step 3: Remove "pre_match_exit" from _NEVER_STOCK_EXITS**

In `src/agent.py` line 53, remove `"pre_match_exit"` from the frozenset:
```python
# OLD
_NEVER_STOCK_EXITS = frozenset({
    "hard_halt_drawdown", "hard_halt", "stop_loss", "esports_halftime",
    "pre_match_exit", "resolved", "near_resolve",
})
# NEW
_NEVER_STOCK_EXITS = frozenset({
    "hard_halt_drawdown", "hard_halt", "stop_loss", "esports_halftime",
    "resolved", "near_resolve",
})
```

- [ ] **Step 4: Add exit detailed logging to _add helpers**

In `src/exit_monitor.py`, modify both `_add` helpers (lines 216-219 and 315-318):

```python
_all_triggered: dict[str, list[str]] = {}

def _add(cid: str, reason: str) -> None:
    _all_triggered.setdefault(cid, []).append(reason)
    if cid not in seen_cids and cid not in self._exiting_set:
        result.append((cid, reason))
        seen_cids.add(cid)
```

At end of both `check_exits()` and `check_exits_light()`:

```python
for cid, rules in _all_triggered.items():
    if len(rules) > 1:
        winner = rules[0]
        logger.info("EXIT_DETAIL: %s | fired=%s | also_triggered=%s",
                     cid[:20], winner, rules[1:])
```

- [ ] **Step 5: Remove `pre_match_mandatory_exit_min` from sport_rules.py**

In `src/sport_rules.py`, remove the `"pre_match_mandatory_exit_min": <int>` key from all 15 sport definition dicts (lines 32, 49, 67, 86, 102, 121, 144, 163, 179, 195, 211, 229, 245, 264, 332). This config is dead after removing the feature.

**Do NOT touch** these unrelated `pre_match` patterns (they are NOT about the exit feature):
- `upset_hunter.py:93` — `upset_type = "pre_match"` (candidate classification)
- `live_momentum.py:84` — `pre_match_prob` (probability baseline)
- `live_dip_entry.py:51` — `pre_match_price` (price baseline)

- [ ] **Step 6: Grep for any other references to check_pre_match_exits or pre_match_exit**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && grep -rn "pre_match_exit\|check_pre_match\|pre_match_mandatory_exit" src/ tests/`
Expected: No remaining references (clean removal). `pre_match_prob`, `pre_match_price`, `upset_type = "pre_match"` are OK — they are unrelated.

- [ ] **Step 7: Run all tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/exit_monitor.py src/portfolio.py src/agent.py src/sport_rules.py
git commit -m "feat: remove pre-match exit + dead config, add exit detailed logging"
```

---

### Task 9: Config Rename — FarConfig → EarlyEntryConfig (Atomic, All Files)

**Files (COMPLETE list from audit):**
- Modify: `src/config.py:108-125, 210` (class + field)
- Modify: `src/entry_gate.py:58, 94, 107, 260, 643, 744` (`_far_market_ids`, `_far_stock`, `is_far` dict keys)
- Modify: `src/adaptive_kelly.py:11, 25` (function param + logic)
- Modify: `src/agent.py:55, 519, 719` (`far_penny_` prefixes → `early_penny_`, `is_far` dict key)
- Modify: `src/portfolio.py:167, 171, 451` (`_SPECIAL_ENTRY_REASONS`, `entry_reason == "far"`)
- Modify: `src/reentry.py:179` (`"far_penny"` → `"early_penny"`)
- Modify: `src/models.py` (if `is_far` field exists on Position)
- Modify: `config.yaml:62-77` (`far:` section → `early:`)
- Modify: `tests/test_entry_modes.py:51` (`gate._far_market_ids`)
- Modify: `tests/test_sports_context_pipeline.py:29, 36` (`gate._far_market_ids`, `gate._far_stock`)

**DO NOT TOUCH:** `src/market_scanner.py` — `far_future` variable is a date sorting helper, unrelated to FAR strategy.

- [ ] **Step 1: Grep all is_far, FarConfig, far_penny, _far_ references**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && grep -rn "is_far\|FarConfig\|far_penny\|_far_market\|_far_stock\|\.far\b\|entry_reason.*\"far\"\|\"far\".*entry_reason" src/ tests/ config.yaml`
Capture all locations. Verify against the list above — if any new locations appear, add them.

- [ ] **Step 2: Rename in config.py**

```python
# OLD (line 108)
class FarConfig(BaseModel):
# NEW
class EarlyEntryConfig(BaseModel):
```

Add `max_entry_price: float = 0.70` to the class.

```python
# OLD (line 210)
far: FarConfig = FarConfig()
# NEW
early: EarlyEntryConfig = EarlyEntryConfig()
```

- [ ] **Step 3: Rename in config.yaml**

```yaml
# OLD (line 62)
far:
  enabled: true
  max_slots: 4
  ...
# NEW
early:
  enabled: true
  max_slots: 4
  ...
```

- [ ] **Step 4: Rename in adaptive_kelly.py**

```python
# OLD (line 11)
is_far: bool = False,
# NEW
is_early: bool = False,

# OLD (line 25)
if is_far:
# NEW
if is_early:
```

- [ ] **Step 5: Rename in entry_gate.py (6 locations)**

```python
# Line 94: self._far_market_ids → self._early_market_ids
# Line 107: self._far_stock → self._early_stock
# Line 260: self._far_market_ids = {...} → self._early_market_ids = {...}
# Line 643: "is_far": cid in self._far_market_ids → "is_early": cid in self._early_market_ids
# Line 744: "is_far": c["is_far"] → "is_early": c["is_early"]
# All self.config.far → self.config.early
```

- [ ] **Step 6: Rename in agent.py (3 locations)**

```python
# Line 55: "far_penny_" → "early_penny_" in _NEVER_STOCK_PREFIXES
# Line 519: "far_penny_" → "early_penny_" in prefix tuple
# Line 719: "is_far": False → "is_early": False
# All config.far → config.early, entry_reason="far" → entry_reason="early"
```

- [ ] **Step 7: Rename in portfolio.py (3 locations)**

```python
# Line 167: _SPECIAL_ENTRY_REASONS = {"live_dip", "fav_time_gate", "far"} → {"live_dip", "fav_time_gate", "early"}
# Line 171: comment mentioning "far" → "early"
# Line 451: if pos.entry_reason == "far" → if pos.entry_reason == "early"
```

- [ ] **Step 8: Rename in reentry.py (1 location)**

```python
# Line 179: "far_penny": ("none", 0) → "early_penny": ("none", 0)
```

- [ ] **Step 9: Rename in models.py (if applicable)**

If Position has `is_far: bool`, rename to `is_early: bool`.

- [ ] **Step 10: Rename in test files (3 locations)**

```python
# tests/test_entry_modes.py line 51: gate._far_market_ids → gate._early_market_ids
# tests/test_sports_context_pipeline.py line 29: gate._far_market_ids → gate._early_market_ids
# tests/test_sports_context_pipeline.py line 36: gate._far_stock → gate._early_stock
```

- [ ] **Step 11: Run all tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 12: Verify ZERO remaining far references**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && grep -rn "is_far\|FarConfig\|far_penny\|_far_market\|_far_stock\|\"far\"" src/ tests/ config.yaml`
Expected: No matches. `far_future` in `market_scanner.py` is OK (unrelated).

- [ ] **Step 13: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/config.py src/adaptive_kelly.py src/entry_gate.py src/agent.py src/portfolio.py src/reentry.py src/models.py config.yaml tests/test_entry_modes.py tests/test_sports_context_pipeline.py
git commit -m "refactor: rename FarConfig → EarlyEntryConfig, is_far → is_early, far_penny → early_penny"
```

---

### Task 10: Upset Hunter — Bidirectional (YES + NO)

**Files:**
- Modify: `src/upset_hunter.py:26-40, 43-112`
- Modify: `src/agent.py:1280` (hardcoded BUY_YES)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_upset_hunter.py
from src.upset_hunter import UpsetCandidate, pre_filter

def test_upset_candidate_has_direction_fields():
    """UpsetCandidate should have no_price, no_token_id, direction fields."""
    c = UpsetCandidate(
        condition_id="cid1",
        question="Team A vs Team B",
        slug="team-a-vs-team-b",
        yes_price=0.90,
        yes_token_id="tok_yes",
        no_price=0.10,
        no_token_id="tok_no",
        direction="BUY_NO",
        volume_24h=50000,
        liquidity=10000,
        odds_api_implied=None,
        divergence=None,
        hours_to_match=2.0,
        upset_type="underdog",
        event_id="evt1",
    )
    assert c.direction == "BUY_NO"
    assert c.no_price == 0.10
    assert c.no_token_id == "tok_no"


def test_pre_filter_produces_no_side_candidate():
    """When NO price is in 5-15¢ zone, pre_filter should produce BUY_NO candidate."""
    # Market where YES=92¢, NO=8¢ — NO side is the upset
    markets = [{
        "condition_id": "cid1",
        "question": "Will Team A win?",
        "slug": "team-a-win",
        "tokens": [
            {"token_id": "tok_yes", "outcome": "Yes", "price": 0.92},
            {"token_id": "tok_no", "outcome": "No", "price": 0.08},
        ],
        "volume_24h": 50000,
        "liquidity": 10000,
        "event_id": "evt1",
    }]
    # pre_filter should find NO side at 8¢ is in upset zone
    candidates = pre_filter(markets, min_price=0.05, max_price=0.15)
    assert any(c.direction == "BUY_NO" for c in candidates)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_upset_hunter.py -v`
Expected: FAIL (UpsetCandidate doesn't have direction/no_price/no_token_id fields)

- [ ] **Step 3: Add direction fields to UpsetCandidate**

In `src/upset_hunter.py` lines 26-40, add fields:

```python
@dataclass
class UpsetCandidate:
    condition_id: str
    question: str
    slug: str
    yes_price: float
    yes_token_id: str
    no_price: float        # NEW
    no_token_id: str       # NEW
    direction: str         # NEW: "BUY_YES" or "BUY_NO"
    volume_24h: float
    liquidity: float
    odds_api_implied: Optional[float]
    divergence: Optional[float]
    hours_to_match: Optional[float]
    upset_type: str
    event_id: str
```

- [ ] **Step 4: Update pre_filter to check both YES and NO sides**

In `src/upset_hunter.py` `pre_filter()` (lines 43-112), modify the price zone filter:

```python
# Check YES price: if 5-15¢ → candidate with direction="BUY_YES"
# Check NO price (= 1 - yes_price): if 5-15¢ → candidate with direction="BUY_NO"
# Same market can produce TWO candidates (one per side)

candidates = []
for market in markets:
    yes_price = get_yes_price(market)
    no_price = 1 - yes_price
    yes_token_id = get_token_id(market, "Yes")
    no_token_id = get_token_id(market, "No")

    if min_price <= yes_price <= max_price:
        candidates.append(UpsetCandidate(
            ...,
            yes_price=yes_price,
            no_price=no_price,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            direction="BUY_YES",
        ))

    if min_price <= no_price <= max_price:
        candidates.append(UpsetCandidate(
            ...,
            yes_price=yes_price,
            no_price=no_price,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            direction="BUY_NO",
        ))
```

- [ ] **Step 5: Update agent.py to use candidate.direction**

In `src/agent.py` line ~1280, replace hardcoded `"BUY_YES"`:

```python
# OLD
direction = "BUY_YES"
token_id = candidate.yes_token_id
# NEW
direction = candidate.direction
token_id = candidate.yes_token_id if direction == "BUY_YES" else candidate.no_token_id
```

- [ ] **Step 6: Update all pre_filter callers to pass new fields**

Grep for `UpsetCandidate(` and update all construction sites to include the new fields.

- [ ] **Step 7: Run all tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/upset_hunter.py src/agent.py tests/test_upset_hunter.py
git commit -m "feat: upset hunter bidirectional — evaluate both YES and NO sides"
```

---

### Task 11: Penny Alpha — Timing Filter

**Files:**
- Modify: `src/agent.py:1313-1400` (`_check_penny_alpha`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_penny_timing.py
def test_penny_skipped_past_first_half():
    """Penny entry should be skipped if match is past 50% elapsed."""
    elapsed_pct = 0.55
    should_skip = elapsed_pct > 0.50
    assert should_skip is True


def test_penny_allowed_first_half():
    """Penny entry allowed in first half."""
    elapsed_pct = 0.40
    should_skip = elapsed_pct > 0.50
    assert should_skip is False


def test_penny_allowed_no_timing_data():
    """Penny entry allowed when no timing data (pre-match assumed)."""
    elapsed_pct = None
    should_skip = elapsed_pct is not None and elapsed_pct > 0.50
    assert should_skip is False
```

- [ ] **Step 2: Run test**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_penny_timing.py -v`
Expected: PASS (logic test)

- [ ] **Step 3: Add elapsed check to _check_penny_alpha**

In `src/agent.py` `_check_penny_alpha()` method, before entry execution, add:

```python
# Timing filter: skip penny if match past first half
if match_start_iso:
    elapsed_pct = _calc_elapsed_pct(match_start_iso, end_date_iso)
    if elapsed_pct is not None and elapsed_pct > 0.50:
        logger.info("PENNY skip: match %.0f%% elapsed (>50%%)", elapsed_pct * 100)
        continue  # or return
```

- [ ] **Step 4: Run all tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/agent.py tests/test_penny_timing.py
git commit -m "feat: penny alpha timing filter — skip entries past first half"
```

---

### Task 12: Global Price Filter — 5-95%

**Files:**
- Modify: `src/entry_gate.py` (0.02/0.98 → 0.05/0.95)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_global_price_filter.py
def test_price_filter_rejects_4_percent():
    """Price at 4¢ should be rejected by 5-95% filter."""
    price = 0.04
    in_range = 0.05 <= price <= 0.95
    assert in_range is False


def test_price_filter_accepts_5_percent():
    """Price at 5¢ should be accepted."""
    price = 0.05
    in_range = 0.05 <= price <= 0.95
    assert in_range is True


def test_price_filter_rejects_96_percent():
    """Price at 96¢ should be rejected."""
    price = 0.96
    in_range = 0.05 <= price <= 0.95
    assert in_range is False
```

- [ ] **Step 2: Run test**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_global_price_filter.py -v`
Expected: PASS (logic test)

- [ ] **Step 3: Update entry_gate.py**

Find and replace `0.02` / `0.98` extreme price guards with `0.05` / `0.95`. The resolution detection at `agent.py:1789` stays at 2-98%.

Important: Upset and Penny strategies bypass this filter (they use their own pre-filters). Verify that upset/penny entries go through their own path, not through this global filter.

- [ ] **Step 4: Verify resolution detection unchanged**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && grep -n "0.02\|0.98" src/agent.py`
Expected: Resolution detection lines still use 0.02/0.98

- [ ] **Step 5: Run all tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/entry_gate.py tests/test_global_price_filter.py
git commit -m "feat: tighten global price filter from 2-98% to 5-95%"
```

---

### Task 13: Lossy Exit Re-entry

**Files:**
- Modify: `src/reentry_farming.py:78-101` (ReentryCandidate)
- Modify: `src/agent.py:480-506` (_exit_position pool acceptance)
- Modify: `src/agent.py` (_check_farming_reentry for recovery trigger)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lossy_reentry.py
def test_sl_exit_added_to_reentry_pool():
    """Stop-loss exit with AI prob ≥ 65% should be added to reentry pool."""
    exit_reason = "stop_loss"
    ai_probability = 0.70
    sl_reentry_count = 0

    should_add = (
        exit_reason == "stop_loss"
        and ai_probability >= 0.65
        and sl_reentry_count == 0
    )
    assert should_add is True


def test_sl_exit_rejected_if_already_reentered():
    """Stop-loss exit should NOT be re-added if already re-entered once."""
    exit_reason = "stop_loss"
    ai_probability = 0.70
    sl_reentry_count = 1  # Already re-entered

    should_add = (
        exit_reason == "stop_loss"
        and ai_probability >= 0.65
        and sl_reentry_count == 0
    )
    assert should_add is False


def test_lossy_reentry_recovery_trigger():
    """Re-entry triggers when price recovers 40% of the drop."""
    original_entry = 0.70
    exit_price = 0.58
    drop = original_entry - exit_price  # 0.12
    recovery_needed = drop * 0.40  # 0.048
    trigger_price = exit_price + recovery_needed  # 0.628

    current_price = 0.63
    should_trigger = current_price >= trigger_price
    assert should_trigger is True


def test_lossy_reentry_tighter_sl():
    """Lossy re-entry should use 75% of original SL."""
    original_sl_pct = 0.15  # 15% stop loss
    lossy_sl_pct = original_sl_pct * 0.75  # 11.25%
    assert lossy_sl_pct == 0.15 * 0.75


def test_second_sl_triggers_permanent_blacklist():
    """Second SL after lossy re-entry = permanent blacklist."""
    sl_reentry_count = 1
    exit_reason = "stop_loss"
    should_blacklist = exit_reason == "stop_loss" and sl_reentry_count >= 1
    assert should_blacklist is True
```

- [ ] **Step 2: Run test**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_lossy_reentry.py -v`
Expected: PASS (logic tests)

- [ ] **Step 3: Add sl_reentry_count to ReentryCandidate**

In `src/reentry_farming.py`, add to `ReentryCandidate`:
```python
sl_reentry_count: int = 0
exit_reason: str = ""  # Track if this was a lossy exit
```

- [ ] **Step 4: Expand pool acceptance in agent._exit_position**

In `src/agent.py` `_exit_position()` (lines 480-506), expand the reentry pool acceptance:

```python
# Existing: add to pool for profitable exits
# NEW: also add for stop_loss exits with high AI probability
if exit_reason == "stop_loss":
    cached_ai = self._ai_cache.get(position.condition_id)
    if cached_ai and cached_ai.probability >= 0.65:
        if getattr(position, 'sl_reentry_count', 0) == 0:
            self.reentry_farming.add_candidate(
                position,
                exit_price=fill_price,
                exit_reason="stop_loss",
                sl_reentry_count=0,
            )
            logger.info("REENTRY_POOL: SL exit added (AI=%.0f%%)", cached_ai.probability * 100)
```

- [ ] **Step 5: Add 40% recovery trigger for lossy re-entries**

In the farming re-entry check method, add recovery condition for SL candidates:

```python
if candidate.exit_reason == "stop_loss":
    drop = candidate.original_entry_price - candidate.last_exit_price
    recovery_needed = drop * 0.40
    trigger_price = candidate.last_exit_price + recovery_needed
    if effective_current < trigger_price:
        continue  # Not enough recovery yet
```

- [ ] **Step 6: Handle 2nd SL = permanent blacklist**

In `_exit_position()`, when exit_reason is "stop_loss" AND position has `sl_reentry_count >= 1`:
```python
if exit_reason == "stop_loss" and getattr(position, 'sl_reentry_count', 0) >= 1:
    self.reentry_farming.blacklist(position.condition_id)
    logger.info("BLACKLIST: 2nd SL after lossy re-entry, permanent ban")
```

- [ ] **Step 7: Apply tighter SL for lossy re-entries**

When creating position from lossy re-entry, set SL to `original_sl * 0.75`.

- [ ] **Step 8: Run all tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/reentry_farming.py src/agent.py tests/test_lossy_reentry.py
git commit -m "feat: lossy exit re-entry — SL exits rejoin pool with 40% recovery trigger"
```

---

### Task 14: Cycle Architecture — Light Cycle Takes Over Actions

**Files:**
- Modify: `src/agent.py` (run_light_cycle, __init__, cooldown system)

This is the largest task. It restructures which cycle handles which actions.

- [ ] **Step 1: Add light_cycle_count to __init__**

In `src/agent.py` `__init__`, add:
```python
self.light_cycle_count: int = 0
self._light_cooldowns: dict[str, int] = {}  # strategy_name → expires_at_light_tick
```

- [ ] **Step 2: Define cooldown constants**

```python
_LIGHT_COOLDOWNS = {
    "live_dip": 60,        # 5 min
    "momentum": 36,        # 3 min
    "farming_reentry": 24, # 2 min
    "scale_out": 12,       # 1 min
}
```

- [ ] **Step 3: Add cooldown helper**

```python
def _light_cooldown_ready(self, strategy: str) -> bool:
    """Check if strategy is off cooldown in light cycle."""
    return self.light_cycle_count >= self._light_cooldowns.get(strategy, 0)

def _set_light_cooldown(self, strategy: str) -> None:
    """Set cooldown for strategy after action."""
    ticks = _LIGHT_COOLDOWNS.get(strategy, 0)
    self._light_cooldowns[strategy] = self.light_cycle_count + ticks
```

- [ ] **Step 4: Add _get_held_event_ids helper**

```python
def _get_held_event_ids(self) -> set[str]:
    """Get event IDs of all currently held positions. Prevents same-event dual-side."""
    return {p.event_id for p in self.portfolio.positions.values()}
```

- [ ] **Step 5: Move live_dip, momentum, scale-out, farming re-entry to run_light_cycle**

In `run_light_cycle()` (lines ~298-337), add after exit processing:

```python
self.light_cycle_count += 1

# --- Light cycle entries (with cooldowns) ---
held_events = self._get_held_event_ids()

if self._light_cooldown_ready("live_dip"):
    entered = self._check_live_dip(held_events)
    if entered:
        self._set_light_cooldown("live_dip")

if self._light_cooldown_ready("momentum"):
    entered = self._check_live_momentum(held_events)
    if entered:
        self._set_light_cooldown("momentum")

if self._light_cooldown_ready("farming_reentry"):
    entered = self._check_farming_reentry()
    if entered:
        self._set_light_cooldown("farming_reentry")

if self._light_cooldown_ready("scale_out"):
    self._process_scale_outs()
    self._set_light_cooldown("scale_out")
```

- [ ] **Step 6: Remove live_dip, momentum, farming_reentry, scale_out from heavy cycle**

In the heavy cycle, remove these calls that are now handled exclusively by light cycle:
- Line ~448: `self._check_live_dip(fresh_markets, bankroll)` — REMOVE
- Line ~449: `self._check_live_momentum(fresh_markets, bankroll, match_states)` — REMOVE
- Line ~443: `self._check_farming_reentry()` — REMOVE (already called from light at line 333, now with cooldown)
- Line ~410: `self._process_scale_outs()` — REMOVE (already called from light at line 330, now with cooldown)

Keep in heavy cycle: Winner, Early, Upset, Penny (these need fresh scan data + AI analysis).

- [ ] **Step 7: Update _check_live_dip and _check_live_momentum signatures**

Add `held_events: set[str]` parameter. Before entry, check:
```python
if candidate_event_id in held_events:
    logger.info("SKIP same-event dedup: %s", candidate_event_id)
    continue
```

- [ ] **Step 8: Ensure _pre_match_prices safety**

Verify that light cycle methods only READ `_pre_match_prices`, never write. Add a comment:
```python
# NOTE: _pre_match_prices is populated by heavy cycle only.
# Light cycle reads this dict — NEVER writes.
```

- [ ] **Step 9: Run all tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 10: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/agent.py
git commit -m "feat: 3-tier cycle architecture — light cycle handles all actions with cooldowns"
```

---

### Task 15: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Grep for dead code**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
grep -rn "is_far\|FarConfig\|far_penny\|_far_market\|_far_stock\|pre_match_exit\|check_pre_match\|pre_match_mandatory_exit" src/ tests/ config.yaml
```
Expected: No matches (except `far_future` in `market_scanner.py` which is unrelated)

- [ ] **Step 3: Grep for hardcoded BUY_YES in upset paths**

```bash
grep -n "BUY_YES" src/agent.py src/upset_hunter.py
```
Expected: No hardcoded BUY_YES in upset entry path (only in non-upset paths where it's correct)

- [ ] **Step 4: Verify spec coverage**

Check each spec section against implementation:
- §1 Cycle Architecture ✓ (Task 14)
- §2a Early Entry ✓ (Task 9)
- §2b Upset Bidirectional ✓ (Task 10)
- §2c Penny Timing ✓ (Task 11)
- §2d Global Price Filter ✓ (Task 12)
- §2e Lossy Re-entry ✓ (Task 13)
- §3a Upset Exempt Graduated SL ✓ (Task 4)
- §3b Upset Forced Exit Price Filter ✓ (Task 5)
- §3c Never-in-Profit Exempt ✓ (Task 6)
- §3d Trailing TP Skip ✓ (Task 7)
- §3e Pre-Match Exit Remove ✓ (Task 8)
- §3f Exit Detailed Logging ✓ (Task 8)
- §4a Exposure Guard ✓ (Task 3)
- §4b VS Slots 3 ✓ (Task 2)
- §4c Catastrophic Floor 20¢ ✓ (Task 1)

- [ ] **Step 5: Commit final state**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add -A
git status
# If any remaining changes, commit:
git commit -m "chore: final verification — rule system overhaul v3 complete"
```
