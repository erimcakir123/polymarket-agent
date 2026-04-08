# 6 Bug Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 6 bugs in exit system + dashboard: edge decay underdog-only, WS scale-out force execute, dashboard NRM count, realized PnL direct read, near-resolve %94 exit, 1s refresh.

**Architecture:** Targeted fixes across match_exit.py, exit_monitor.py, exit_executor.py, dashboard.py, dashboard.html. No new files. Each fix is independent.

**Tech Stack:** Python 3.11, Flask, vanilla JS

---

### Task 1: Edge Decay — Underdog Only

**Files:**
- Modify: `src/match_exit.py:434`

- [ ] **Step 1: Add underdog condition to edge decay**

In `src/match_exit.py` line 434, change:
```python
# Current:
if ai_probability > 0 and not result.get("exit") and not a_conf_hold:

# New:
if ai_probability > 0 and not result.get("exit") and not a_conf_hold and effective_entry < 0.50:
```

- [ ] **Step 2: Verify syntax**
```bash
python -c "import py_compile; py_compile.compile('src/match_exit.py', doraise=True); print('OK')"
```

- [ ] **Step 3: Commit**
```bash
git add src/match_exit.py
git commit -m "fix: edge decay only for underdog positions (<50¢ entry)"
```

---

### Task 2: WS Scale-Out Force Execute

**Files:**
- Modify: `src/exit_monitor.py:234-243`
- Modify: `src/exit_executor.py:263-330`

- [ ] **Step 1: Set force flag in WS path**

In `src/exit_monitor.py`, after scale-out is detected and queued (line 243), add force flag:
```python
                if cid not in self._ws_scale_out_queued_set:
                    self._ws_scale_out_queue.append((cid, so))
                    self._ws_scale_out_queued_set.add(cid)
                    # Force flag so process_scale_outs executes even if price drops back
                    pos._force_scale_out_tier = so["tier"]
                    logger.info("WS_SCALE_OUT queued: %s | tier=%s pnl=%.1f%%",
                                pos.slug[:35], so["tier"], pnl_pct * 100)
```

- [ ] **Step 2: Handle force flag in process_scale_outs**

In `src/exit_executor.py`, at the start of `process_scale_outs()` (line 267), add force-execute block BEFORE normal check:
```python
    def process_scale_outs(self) -> None:
        """Check and execute partial scale-out exits for all positions."""
        from src.scale_out import apply_partial_exit, SCALE_OUT_TIERS

        # Force-execute WS-triggered scale-outs (price may have dropped back)
        for cid, pos in list(self.ctx.portfolio.positions.items()):
            force_tier = getattr(pos, '_force_scale_out_tier', None)
            if not force_tier:
                continue
            pos._force_scale_out_tier = None  # Clear flag immediately
            if self.ctx.exit_monitor.is_exiting(cid):
                continue
            tier_info = SCALE_OUT_TIERS.get(force_tier)
            if not tier_info:
                continue
            sell_pct = tier_info["sell_pct"]
            shares_to_sell = pos.shares * sell_pct
            if shares_to_sell < 1.0:
                continue

            eff_sell_price = effective_price(pos.current_price, pos.direction)
            result = self.ctx.executor.place_order(
                pos.token_id, "SELL", eff_sell_price,
                shares_to_sell * eff_sell_price, use_hybrid=False,
            )
            if not result or result.get("status") == "error":
                logger.warning("WS force scale-out failed: %s | %s", pos.slug[:35], result)
                continue

            _sell_fill = result.get("price", eff_sell_price)
            fill_price = _sell_fill if pos.direction == "BUY_YES" else (1.0 - _sell_fill)
            partial = apply_partial_exit(
                shares=pos.shares, size_usdc=pos.size_usdc,
                entry_price=pos.entry_price, direction=pos.direction,
                shares_sold=shares_to_sell, fill_price=fill_price,
                tier=force_tier,
                original_shares=getattr(pos, "original_shares", None),
                original_size_usdc=getattr(pos, "original_size_usdc", None),
                scale_out_tier=pos.scale_out_tier,
            )
            pos.shares = partial["remaining_shares"]
            pos.size_usdc = partial["remaining_size_usdc"]
            pos.scale_out_tier = partial["new_scale_out_tier"]
            if pos.original_shares is None:
                pos.original_shares = partial["original_shares"]
            if pos.original_size_usdc is None:
                pos.original_size_usdc = partial["original_size_usdc"]
            self.ctx.portfolio.record_realized(partial["realized_pnl"])
            pos.scale_out_realized_usdc += partial["realized_pnl"]
            logger.info("WS FORCE SCALE-OUT: %s | %s | sold %.0f shares | pnl=$%.2f",
                        pos.slug[:35], force_tier, shares_to_sell, partial["realized_pnl"])

        # Normal scale-out check (current price based)
        scale_outs = self.ctx.portfolio.check_scale_outs()
```

- [ ] **Step 3: Verify syntax**
```bash
python -c "import py_compile; py_compile.compile('src/exit_monitor.py', doraise=True); py_compile.compile('src/exit_executor.py', doraise=True); print('OK')"
```

- [ ] **Step 4: Commit**
```bash
git add src/exit_monitor.py src/exit_executor.py
git commit -m "fix: WS scale-out force execute via position flag"
```

---

### Task 3: Near-Resolve Exit (%94+)

**Files:**
- Modify: `src/exit_monitor.py:192-194`

- [ ] **Step 1: Add %94+ exit check in WS path**

In `src/exit_monitor.py`, after `effective_current` is calculated (line 192) and before the A-conf check (line 196), add:
```python
        effective_current = effective_price(current, direction)

        pnl_pct = (effective_current - effective_entry) / effective_entry if effective_entry > 0 else 0

        # Near-resolve: our side ≥94¢ → exit, don't risk 6¢ for resolve
        if effective_current >= 0.94:
            self._ws_exit_queue.append((cid, "near_resolve_profit"))
            self._ws_exit_queued_set.add(cid)
            logger.info("WS_EXIT queued [near_resolve]: %s | eff=%.0f%%", pos.slug[:35], effective_current * 100)
            return

        # A-conf hold-to-resolve check (reused by SL and TP)
```

- [ ] **Step 2: Add same check in heavy cycle**

In `src/exit_monitor.py` `_common_exit_checks()`, add near-resolve check before match-aware exits. Find the line `# 1. Match-aware exits` and add before it:
```python
        # 0. Near-resolve profit: our side ≥94¢ → exit immediately
        for cid, pos in list(self.portfolio.positions.items()):
            _eff = effective_price(pos.current_price, pos.direction)
            if _eff >= 0.94:
                _add(cid, "near_resolve_profit")
```

- [ ] **Step 3: Verify syntax**
```bash
python -c "import py_compile; py_compile.compile('src/exit_monitor.py', doraise=True); print('OK')"
```

- [ ] **Step 4: Commit**
```bash
git add src/exit_monitor.py
git commit -m "feat: near-resolve exit at 94%+ (don't wait for oracle)"
```

---

### Task 4: Dashboard NRM Slot Count

**Files:**
- Modify: `templates/dashboard.html:1753`

- [ ] **Step 1: Fix JS fallback values**

In `templates/dashboard.html` line 1753, change:
```javascript
// Current:
const maxPos = s.max_total || ((s.normal?.max || 20) + (s.vs?.max || 5));
// New:
const maxPos = s.max_total || ((s.normal?.max || 17) + (s.vs?.max || 3));
```

- [ ] **Step 2: Commit**
```bash
git add templates/dashboard.html
git commit -m "fix: dashboard NRM slot count fallback 20+5→17+3"
```

---

### Task 5: Dashboard Realized PnL + 1s Refresh

**Files:**
- Modify: `src/dashboard.py`
- Modify: `templates/dashboard.html`

- [ ] **Step 1: Add /api/realized endpoint**

In `src/dashboard.py`, after the existing routes, add:
```python
    @app.route("/api/realized")
    def api_realized():
        """Direct read from realized_pnl.json — no cycle snapshot dependency."""
        rpath = Path("logs/realized_pnl.json")
        if not rpath.exists():
            return jsonify({"total": 0, "wins": 0, "losses": 0, "hwm": 0})
        try:
            return jsonify(json.loads(rpath.read_text(encoding="utf-8")))
        except Exception:
            return jsonify({"total": 0, "wins": 0, "losses": 0, "hwm": 0})
```

Add `import json` at top if not present. Add `from pathlib import Path` if not imported.

- [ ] **Step 2: Update dashboard JS — fetch realized + 1s intervals**

In `templates/dashboard.html`, replace the interval block at the end:
```javascript
// Current:
fetchData();
fetchBotStatus();
setInterval(fetchData, 10000);
setInterval(fetchBotStatus, 5000);
setInterval(renderBotStatus, 1000);

// New:
fetchData();
fetchBotStatus();
fetchRealized();
setInterval(fetchData, 1000);
setInterval(fetchBotStatus, 1000);
setInterval(fetchRealized, 1000);
setInterval(renderBotStatus, 1000);
```

Add `fetchRealized` function before the interval block:
```javascript
function fetchRealized() {
    fetch('/api/realized?_=' + Date.now(), {cache: 'no-store'})
        .then(r => r.json())
        .then(data => {
            const pnl = data.total || 0;
            const wins = data.wins || 0;
            const losses = data.losses || 0;
            const el = document.getElementById('realizedPnl');
            if (Math.abs(pnl) < 0.005) {
                el.innerHTML = '$0.00';
                el.className = 'card-value up';
            } else {
                el.innerHTML = (pnl >= 0 ? '+$' : '-$') + Math.abs(pnl).toFixed(2);
                el.className = 'card-value ' + (pnl >= 0 ? 'up' : 'down');
            }
            document.getElementById('realizedWL').textContent = wins + 'W / ' + losses + 'L';
        })
        .catch(() => {});
}
```

- [ ] **Step 3: Verify syntax**
```bash
python -c "import py_compile; py_compile.compile('src/dashboard.py', doraise=True); print('OK')"
```

- [ ] **Step 4: Commit**
```bash
git add src/dashboard.py templates/dashboard.html
git commit -m "feat: dashboard realized PnL direct read + 1s refresh all"
```

---

### Task 6: Verification

- [ ] **Step 1: Syntax check all modified files**
```bash
python -c "
import py_compile
for f in ['src/match_exit.py','src/exit_monitor.py','src/exit_executor.py','src/dashboard.py']:
    py_compile.compile(f, doraise=True)
    print(f'  {f}: OK')
print('ALL OK')
"
```

- [ ] **Step 2: Feature check**
```bash
python -c "
me = open('src/match_exit.py','r',encoding='utf-8').read()
assert 'effective_entry < 0.50' in me; print('Edge decay underdog: OK')

em = open('src/exit_monitor.py','r',encoding='utf-8').read()
assert 'near_resolve_profit' in em; print('Near-resolve exit: OK')
assert '_force_scale_out_tier' in em; print('WS force flag: OK')

ee = open('src/exit_executor.py','r',encoding='utf-8').read()
assert 'WS FORCE SCALE-OUT' in ee; print('Force execute: OK')
assert 'SCALE_OUT_TIERS' in ee; print('Tier lookup: OK')

dh = open('templates/dashboard.html','r',encoding='utf-8').read()
assert '17' in dh.split('normal?.max')[1][:20]; print('NRM fallback: OK')
assert 'fetchRealized' in dh; print('Realized fetch: OK')
assert 'setInterval(fetchData, 1000)' in dh; print('1s refresh: OK')

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
