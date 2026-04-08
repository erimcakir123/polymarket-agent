# 6 Bug Fix Design — Exit System + Dashboard

## 1. Edge Decay — Underdog Only
**File**: `src/match_exit.py` line ~434
**Change**: Add `effective_entry < 0.50` condition. Edge decay only fires for underdog positions (entry <50¢). Favorite positions (≥50¢) skip edge decay — scale-out + graduated SL handle them.
```python
# Current:
if ai_probability > 0 and not result.get("exit") and not a_conf_hold:
# New:
if ai_probability > 0 and not result.get("exit") and not a_conf_hold and effective_entry < 0.50:
```

## 2. WS Scale-Out Force Execute
**Files**: `src/exit_monitor.py`, `src/exit_executor.py`

When WS detects scale-out trigger, set force flag on position:
```python
# exit_monitor.py _ws_check_exits, after scale-out detected:
pos._force_scale_out_tier = so["tier"]  # "tier1_risk_free" or "tier2_profit_lock"
```

In process_scale_outs, check force flag before current price:
```python
# exit_executor.py process_scale_outs:
for cid, pos in positions:
    force_tier = getattr(pos, '_force_scale_out_tier', None)
    if force_tier:
        # Execute without current price check
        tier_name = force_tier
        sell_pct = 0.40 if "tier1" in tier_name else 0.50
        # ... execute partial sell ...
        pos._force_scale_out_tier = None  # Clear flag
    else:
        # Normal: check current price via check_scale_out()
```

## 3. Pre-Match Guard
Already fixed (gameStartTime + retroactive update). No additional changes.

## 4. Dashboard NRM Slot Count
**File**: `templates/dashboard.html`
**Change**: Fix JS fallback values to match config (max_positions=20, reserved_slots=3):
- `s.normal?.max || 20` → `s.normal?.max || 17`
- `s.vs?.max || 5` → `s.vs?.max || 3`
- Total gauge: `(s.normal?.max || 17) + (s.vs?.max || 3)` = 20

## 5. Dashboard Realized PnL — Direct Read
**File**: `src/dashboard.py`
**Change**: New endpoint `/api/realized` reads `logs/realized_pnl.json` directly.
**File**: `templates/dashboard.html`
**Change**: ALL dashboard data fetches consolidated to 1 second interval. fetchData (positions, trades, portfolio, slots, stock, performance, budget) + fetchBotStatus + realized PnL — hepsi 1 saniyede bir. Localhost'tan JSON okumak microsaniye, yük yok.

## 6b. Near-Resolve Exit — %94+ Çıkış
**File**: `src/exit_monitor.py` (_ws_check_exits ve _common_exit_checks)
**Change**: Bizim taraf effective price ≥ 0.94 → EXIT. Resolve beklemeye gerek yok, 6¢ risk almaya değmez. Tüm confidence seviyelerinde (A, B+) geçerli. A-conf hold-to-resolve'u da override eder.
```python
# After price update, before any other exit check:
if effective_current >= 0.94:
    exit("near_resolve_profit")  # Lock ~94¢+ profit
```

## 6c. WTA Tennis
No fix needed. Odds API dynamic discovery (`_get_active_tennis_keys("wta")`) will auto-detect when WTA tournament starts. Currently no active WTA tournament on Odds API.

## Verification
1. Edge decay: Favorite position (+%15) should NOT trigger edge decay exit
2. Scale-out: Position at +%30 → force flag set → partial sell executes in next light cycle
3. Dashboard NRM: Shows 15/17 not 15/25
4. Dashboard Realized: Updates within 5 seconds of exit, not waiting for cycle
5. No cycle errors in bot.log
