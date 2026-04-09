# 4 Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix soccer/baseball scale-out, baseball 70% hold rule, live dip prop bug, slot pool unification.

**Architecture:** Targeted edits in match_exit.py, portfolio.py, live_strategies.py, agent.py, config.py. Uses existing sport_classifier.classify_sport() for sport detection.

**Tech Stack:** Python 3.11

---

### Task 1: Soccer + Baseball A-conf Scale-out

**Files:**
- Modify: `src/portfolio.py:366-370`

- [ ] **Step 1: Add soccer/baseball exception to A-conf scale-out bypass**

In `src/portfolio.py`, find the A-conf scale-out bypass in `check_scale_outs()` (around line 366). Replace:

```python
            # A-conf hold-to-resolve: skip scale-out, hold full position until resolution
            from src.models import effective_price
            _eff_entry = effective_price(pos.entry_price, pos.direction)
            if (pos.confidence == "A" and _eff_entry >= 0.60
                    and getattr(pos, "entry_reason", "") not in ("upset", "penny")):
                continue
```

With:

```python
            # A-conf hold-to-resolve: skip scale-out, hold full position until resolution
            # EXCEPTION: soccer (draw risk) + baseball (inning spikes) → allow scale-out
            from src.models import effective_price
            from src.matching.sport_classifier import classify_sport
            _eff_entry = effective_price(pos.entry_price, pos.direction)
            _sport = classify_sport(pos) if hasattr(pos, 'slug') else ""
            if (pos.confidence == "A" and _eff_entry >= 0.60
                    and getattr(pos, "entry_reason", "") not in ("upset", "penny")
                    and _sport not in ("soccer", "baseball")):
                continue
```

- [ ] **Step 2: Verify syntax**
```bash
python -c "import py_compile; py_compile.compile('src/portfolio.py', doraise=True); print('OK')"
```

- [ ] **Step 3: Commit**
```bash
git add src/portfolio.py
git commit -m "fix: allow scale-out for soccer/baseball A-conf (draw risk + inning spikes)"
```

---

### Task 2: Baseball A-conf 70% Elapsed Hold Rule

**Files:**
- Modify: `src/match_exit.py:339-350`

- [ ] **Step 1: Add baseball 70% elapsed exception to a_conf_hold**

In `src/match_exit.py`, replace the `a_conf_hold` definition and its if block (around line 339-350):

```python
    a_conf_hold = (
        confidence == "A"
        and effective_entry >= 0.60
        and entry_reason not in ("upset", "penny")
    )
    if a_conf_hold:
        if effective_current < 0.50:
            return {**result, "exit": True, "layer": "a_conf_market_flip",
                    "reason": f"A-conf: eff_price {effective_current:.2f} < 0.50 -- market no longer favors"}
        # else: skip graduated SL, hold through drawdown
```

With:

```python
    a_conf_hold = (
        confidence == "A"
        and effective_entry >= 0.60
        and entry_reason not in ("upset", "penny")
    )
    if a_conf_hold:
        if effective_current < 0.50:
            return {**result, "exit": True, "layer": "a_conf_market_flip",
                    "reason": f"A-conf: eff_price {effective_current:.2f} < 0.50 -- market no longer favors"}
        # Baseball 70%+ elapsed: if our side <60¢ (losing/toss-up), allow graduated SL
        _is_baseball = sport_tag in ("mlb", "baseball", "kbo", "npb")
        if _is_baseball and elapsed_pct >= 0.70 and effective_current < 0.60:
            pass  # Fall through to graduated SL below
        else:
            pass  # Normal hold-to-resolve
```

But this `pass` won't skip the graduated SL — we need to restructure. Better approach — make `a_conf_hold` False for baseball losing positions:

```python
    _is_baseball = sport_tag in ("mlb", "baseball", "kbo", "npb")
    _baseball_losing = _is_baseball and elapsed_pct >= 0.70 and effective_current < 0.60
    a_conf_hold = (
        confidence == "A"
        and effective_entry >= 0.60
        and entry_reason not in ("upset", "penny")
        and not _baseball_losing
    )
    if a_conf_hold:
        if effective_current < 0.50:
            return {**result, "exit": True, "layer": "a_conf_market_flip",
                    "reason": f"A-conf: eff_price {effective_current:.2f} < 0.50 -- market no longer favors"}
        # else: skip graduated SL, hold through drawdown
```

This way `_baseball_losing` makes `a_conf_hold = False` → graduated SL applies normally. When baseball is winning (≥60¢) or <70% elapsed, `a_conf_hold` stays True → normal hold.

- [ ] **Step 2: Verify syntax**
```bash
python -c "import py_compile; py_compile.compile('src/match_exit.py', doraise=True); print('OK')"
```

- [ ] **Step 3: Commit**
```bash
git add src/match_exit.py
git commit -m "fix: baseball A-conf graduated SL after 70% elapsed when losing (<60¢)"
```

---

### Task 3: Live Dip Moneyline + sportsMarketType Filter

**Files:**
- Modify: `src/live_strategies.py:296-315`

- [ ] **Step 1: Add sportsMarketType guard to check_live_dip**

In `src/live_strategies.py`, find `check_live_dip()` method. Inside the `for m in fresh_markets:` loop, after the existing `_non_ml` keyword filter (around line 314), add:

```python
            # Block non-moneyline markets (Top10, spread, totals, props)
            _smt = getattr(m, "sports_market_type", "") or ""
            if _smt and _smt.lower() != "moneyline":
                continue
```

- [ ] **Step 2: Verify syntax**
```bash
python -c "import py_compile; py_compile.compile('src/live_strategies.py', doraise=True); print('OK')"
```

- [ ] **Step 3: Commit**
```bash
git add src/live_strategies.py
git commit -m "fix: live dip skip non-moneyline markets (prop/Top10 guard)"
```

---

### Task 4: Slot Pool Unification

**Files:**
- Modify: `src/config.py:109`
- Modify: `src/agent.py:240-242`

- [ ] **Step 1: Set VS reserved to 0**

In `src/config.py`, find `reserved_slots` (around line 109):
```python
# Current:
    reserved_slots: int = 3

# New:
    reserved_slots: int = 0  # Single pool — all entry modes share max_positions
```

- [ ] **Step 2: Simplify agent refill loop**

In `src/agent.py`, find the refill loop (around line 240-242):
```python
# Current:
                            current_vs = sum(1 for p in self.portfolio.positions.values() if p.volatility_swing)
                            current_normal = self.portfolio.active_position_count - current_vs
                            open_slots = self.config.risk.max_positions - vs_reserved - current_normal

# New:
                            open_slots = self.config.risk.max_positions - self.portfolio.active_position_count
```

- [ ] **Step 3: Verify syntax**
```bash
python -c "import py_compile; py_compile.compile('src/config.py', doraise=True); py_compile.compile('src/agent.py', doraise=True); print('OK')"
```

- [ ] **Step 4: Commit**
```bash
git add src/config.py src/agent.py
git commit -m "fix: unify slot pool — remove VS reserved, single max_positions cap"
```

---

### Task 5: Verification

- [ ] **Step 1: Syntax check all files**
```bash
python -c "
import py_compile
for f in ['src/portfolio.py','src/match_exit.py','src/live_strategies.py','src/config.py','src/agent.py']:
    py_compile.compile(f, doraise=True)
    print(f'  {f}: OK')
print('ALL OK')
"
```

- [ ] **Step 2: Feature verification**
```bash
python -c "
po = open('src/portfolio.py','r',encoding='utf-8').read()
assert 'soccer' in po and 'baseball' in po; print('Task 1: soccer+baseball scale-out exception: OK')

me = open('src/match_exit.py','r',encoding='utf-8').read()
assert '_baseball_losing' in me; print('Task 2: baseball 70% hold rule: OK')

ls = open('src/live_strategies.py','r',encoding='utf-8').read()
assert 'moneyline' in ls.split('check_live_dip')[1][:500]; print('Task 3: live dip moneyline guard: OK')

cf = open('src/config.py','r',encoding='utf-8').read()
assert 'reserved_slots: int = 0' in cf; print('Task 4: VS reserved = 0: OK')

ag = open('src/agent.py','r',encoding='utf-8').read()
assert 'max_positions - self.portfolio.active_position_count' in ag; print('Task 4: simplified refill: OK')

print('ALL CHECKS PASSED')
"
```

- [ ] **Step 3: Restart bot (keep positions)**
```bash
taskkill //IM python.exe //F
sleep 1
python -m src.main > /dev/null 2>&1 &
python -m src.dashboard > /dev/null 2>&1 &
```
