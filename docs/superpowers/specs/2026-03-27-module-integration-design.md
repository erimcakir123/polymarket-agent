# Module Integration Design — 5 Orphan Modules into Agent Pipeline

## Goal

Integrate 5 standalone modules into `agent.py` as separate scan passes, each with its own sizing and execution logic, sharing the common infrastructure (executor, portfolio, trade_log, notifier, blacklist, slot limits).

## Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Live dip trigger | WS price tick (no ESPN) | Faster, zero API cost, pure market price |
| Bond thresholds | Config-compatible ($5K vol, $100 liq) | More candidates, $0.90-0.97 price filter is enough |
| Pipeline approach | Separate passes in agent.py | Each module has its own sizing; entry_gate untouched |

## Architecture

### run_cycle() Extension

```
run_cycle():
  ├─ [existing] Scout + bankroll + drawdown
  ├─ [existing] Exit detection + execution
  ├─ [existing] entry_gate.run()
  ├─ [existing] entry_gate.drain_stock()
  ├─ [existing] _check_farming_reentry()
  │
  ├─ [NEW] _check_bond_farming(fresh_markets, bankroll)
  ├─ [NEW] _check_penny_alpha(fresh_markets, bankroll)
  ├─ [NEW] _check_live_dip(bankroll)
  ├─ [NEW] _check_live_momentum(bankroll, match_states)
  │
  └─ [existing] _log_cycle_summary()
```

### _exit_position() Extension

```
_exit_position():
  ├─ [existing] remove + execute + pnl + reentry/blacklist + log
  │
  └─ [NEW] price_history.save_price_history(...)  ← fire-and-forget
```

## Module Specifications

### 1. Bond Scanner (`_check_bond_farming`)

**Source:** `src/bond_scanner.py` (existing, no changes needed)

**Integration in agent.py:**
- Receives `fresh_markets` (already fetched by scanner)
- Calls `scan_bond_candidates(markets)` with config-derived thresholds
- Sizing: `size_bond_position(bankroll, candidate, current_bond_exposure, current_bond_count)`
- Thresholds from config: `config.bond_farming.min_yes_price` (0.90), `config.bond_farming.max_yes_price` (0.97)
- Volume/liquidity: uses `config.scanner.min_volume_24h` and `config.scanner.min_liquidity`
- Max concurrent: `config.bond_farming.max_concurrent` (3)
- Max total allocation: `config.bond_farming.max_total_bond_pct` (20%)
- Bet size: `config.bond_farming.bet_pct` (8%)
- Entry reason: `"bond"`
- Exit: wait for resolution at $1.00 (existing trailing TP / resolution logic handles this)

**Guard rails:**
- Slot check: `portfolio.active_position_count < max_positions`
- Duplicate: `cid not in portfolio.positions`
- Blacklist: `not blacklist.is_blocked(cid)`
- Exited: `cid not in _exited_markets`
- Min bet: `size >= 5.0`

### 2. Penny Alpha (`_check_penny_alpha`)

**Source:** `src/penny_alpha.py` (existing, no changes needed)

**Integration in agent.py:**
- Receives `fresh_markets`
- Calls `scan_penny_candidates(markets)`
- Sizing: `size_penny_position(bankroll, config.penny_alpha.bet_pct, config.penny_alpha.max_concurrent, current_penny_count)`
- Entry reason: `"penny"`
- Exit: custom penny exit check added to exit_monitor — `check_penny_exit(entry_price, current_price, target_multiplier)` returns `{"exit": True}` when target hit (5x for $0.01, 2x for $0.02)

**Penny exit integration in exit_monitor.py:**
- In `check_exits()`, after trailing TP section, add penny exit check
- Only for positions with `entry_reason == "penny"`
- No stop-loss for pennies (accept total loss — position is small)

**Guard rails:** Same as bond (slot, duplicate, blacklist, exited, min bet)

### 3. Live Dip (`_check_live_dip`)

**Source:** `src/live_dip_entry.py` (needs modification — remove ESPN dependency)

**Modified approach:**
- Does NOT use ESPN scoreboard (user decision: pure market price)
- Tracks pre-match prices from scanner results (cache YES price at first scan)
- On each cycle, compares current price vs cached pre-match price
- If favorite dropped 10%+: enter position
- Favorite = pre-match YES price > 0.65 or NO price > 0.65

**New state in agent.py:**
- `_pre_match_prices: dict[str, float]` — caches first-seen YES price per condition_id
- Updated each cycle from scanner results (only set once, never overwritten)

**Sizing:** `confidence_position_size(confidence="B-", bankroll, ...)` — uses existing system
- Entry reason: `"live_dip"`
- Max concurrent: `config.live_momentum.max_concurrent` (2)

**Guard rails:** Same as bond + max concurrent live_dip check

### 4. Live Momentum (`_check_live_momentum`)

**Source:** `src/live_momentum.py` (existing, no changes needed)

**Integration in agent.py:**
- Uses `_match_states` (already fetched every cycle via `_fetch_match_states()`)
- Two modes:

**Mode A — New entry:**
- For markets in `_match_states` that are NOT in portfolio
- Calls `detect_momentum_opportunity(cid, ai_prob, market_price, match_state, sport_tag)`
- If edge >= 6%: enter with `confidence_position_size(confidence="B-", ...)`
- Needs AI probability — uses entry_gate's cached estimates if available, else skips
- Entry reason: `"momentum"`

**Mode B — Existing position update:**
- For markets in `_match_states` that ARE in portfolio
- Calls `calculate_score_adjusted_probability(pre_match_prob, match_state, sport_tag, direction)`
- Updates `pos.ai_probability` with adjusted value (informational, for trailing TP decisions)
- Does NOT force exit — exit_monitor handles that

**Guard rails:** Same as bond + edge >= 6% threshold

### 5. Price History (`_exit_position` post-hook)

**Source:** `src/price_history.py` (existing, no changes needed)

**Integration:**
- 5 lines added at end of `_exit_position()`, after logging
- Fire-and-forget: wrapped in try/except, failure doesn't block exit
- Passes: slug, token_id, entry_price, exit_price, reason, match metadata

```python
# Post-exit: save CLOB price history for calibration
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

## Shared Guard Rails (All Modules)

Every new entry pass checks these before placing an order:

1. `portfolio.active_position_count < config.risk.max_positions` — global slot limit
2. `cid not in portfolio.positions` — no duplicates
3. `not blacklist.is_blocked(cid, cycle_count)` — respect blacklist
4. `cid not in _exited_markets` — respect permanent exits
5. `size >= 5.0` — Polymarket minimum order
6. `entries_allowed` — respect drawdown halt, circuit breaker, manual pause

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `src/agent.py` | Modify | Add 4 new methods + price_history hook in _exit_position |
| `src/exit_monitor.py` | Modify | Add penny exit check in check_exits() |
| `src/live_dip_entry.py` | Modify | Remove ESPN dependency, pure price-based |
| `src/bond_scanner.py` | No change | Used as-is |
| `src/live_momentum.py` | No change | Used as-is |
| `src/penny_alpha.py` | No change | Used as-is |
| `src/price_history.py` | No change | Used as-is |

## What Does NOT Change

- `src/entry_gate.py` — untouched, unified AI pipeline stays as-is
- `src/risk_manager.py` — untouched, confidence-based sizing stays
- `src/trailing_tp.py` — untouched
- `src/config.py` — untouched (existing config sections already have all needed fields)
- `config.yaml` — untouched (existing sections already configured)

## Conflict Analysis

| Module A | Module B | Can conflict? | Resolution |
|----------|----------|---------------|------------|
| entry_gate | bond_scanner | No | Different price ranges ($0.90-0.97 vs normal) |
| entry_gate | penny_alpha | No | Different price ranges ($0.01-0.02 vs normal) |
| entry_gate | live_dip | Yes — same market | `cid in portfolio.positions` check prevents double entry |
| entry_gate | live_momentum | Yes — same market | `cid in portfolio.positions` check prevents double entry |
| bond_scanner | penny_alpha | No | Opposite price ranges |
| live_dip | live_momentum | Yes — same live market | live_dip enters first (runs before momentum); momentum updates existing |
| Any module | max_positions | All check | Global slot limit enforced by every module |
