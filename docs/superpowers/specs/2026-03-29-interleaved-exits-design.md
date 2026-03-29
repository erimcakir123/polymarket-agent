# Interleaved Exit Checks + Upset Profit Fix

**Date:** 2026-03-29
**Status:** Approved

## Problem

Three linked issues from the same root cause:

1. **Heavy cycle blocks exits** — 10+ min with zero exit checks. Profitable positions can't close.
2. **Upset exit uses absolute cents, not %** — A position at +110% profit (15¢→31¢) doesn't trigger scale-out or trailing TP because thresholds are `25¢` and `35¢` absolute, not profit-based. YES/NO is just Team A/Team B — has nothing to do with underdog/favorite.
3. **Dashboard stale** — `portfolio.jsonl` only written at cycle end, so realized P&L doesn't update until heavy cycle finishes.

## Design

### 1. `_quick_exit_check()` — Interleaved During Heavy Cycle

A lightweight exit sweep inserted between heavy cycle phases:

```
run_cycle():
    bankroll/drawdown check
    → _quick_exit_check()
    resolved markets + price update + exit detection
    → _quick_exit_check()          # after exits, before scan
    scan markets
    → _quick_exit_check()          # after scan, before AI
    entry_gate.run() (AI analysis)
    → _quick_exit_check()          # after AI, before upset
    upset_hunter
    → _quick_exit_check()          # after upset, before summary
    log_cycle_summary
```

**`_quick_exit_check()` does:**
1. `exit_monitor.process_ws_ticks()` — drain WebSocket price updates
2. `exit_monitor.drain()` → execute exits
3. `exit_monitor.check_exits_light()` → execute exits
4. `exit_executor.process_scale_outs()` — partial profit-taking
5. `cycle_helpers.log_cycle_summary(bankroll, "interleaved")` — update dashboard

**Does NOT do:** Market scan, AI calls, live strategies, WS sync. Pure exit + snapshot.

**Location:** Method on Agent class, ~15 lines. Not a separate file.

### 2. Upset Exit: % Based (Same as Standard)

Remove all absolute-cent logic for upset positions. Use the same PnL% system as standard positions:

**scale_out.py changes:**
- Remove the `if entry_reason == "upset"` branch entirely (lines 41-56)
- Upset positions use the standard PnL% tiers:
  - Tier 1: `unrealized_pnl_pct >= 25%` → sell 40%
  - Tier 2: `unrealized_pnl_pct >= 50%` → sell 50%

**exit_monitor.py changes:**
- Remove `if pos.entry_reason == "upset"` blocks that skip trailing TP (lines 143-150 in WS handler, lines 243-247 in check_exits_light, similar in check_exits)
- Upset positions use standard trailing TP: activation at +20%, trail 8% from peak
- No `promotion_price` concept needed anymore

**config.py changes:**
- Remove from UpsetHunterConfig: `promotion_price`, `scale_out_tier1_price`, `scale_out_tier1_sell_pct`, `scale_out_tier2_price`, `scale_out_tier2_sell_pct`, `trailing_activation`, `trailing_distance`
- Keep: `enabled`, `min_price`, `max_price`, `bet_pct`, `max_concurrent`, `stop_loss_pct`, `min_liquidity`, `min_odds_divergence`, `max_hours_before_match`, `late_match_exit_pct`, `max_hold_hours`

### 3. Dashboard Freshness

Solved by `_quick_exit_check()` calling `log_cycle_summary()` after every exit sweep. Dashboard polls `/api/portfolio` which reads last line of `portfolio.jsonl` — will now update every 1-2 minutes during heavy cycle instead of only at cycle end.

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `src/agent.py` | Add `_quick_exit_check()`, call it 5x in `run_cycle()` | +20 |
| `src/scale_out.py` | Remove upset-specific branch | -16 |
| `src/exit_monitor.py` | Remove upset trailing TP skip blocks (3 places) | -15 |
| `src/config.py` | Remove 7 upset config fields | -7 |

**Net:** ~-18 lines. Removes complexity, doesn't add it.

## What NOT to Change

- `live_strategies.py` upset entry logic — unchanged
- `match_exit.py` — unchanged (already uses effective_price correctly)
- `trailing_tp.py` — unchanged (already handles BUY_NO correctly)
- Light cycle structure — unchanged
- No new files, no new classes, no new abstractions
