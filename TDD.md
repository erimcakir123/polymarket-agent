# TDD — Technical Design Document
> Polymarket Agent 2.0 | v2.0 | 2026-04-13 | APPROVED

---

## Index — When to Read

| §     | Title                       | Required when                          |
|-------|-----------------------------|----------------------------------------|
| 0     | Core Principles             | **ALWAYS**                             |
| 6.1   | Bookmaker Probability       | prob / edge work                       |
| 6.2   | Confidence Grading          | confidence work                        |
| 6.3   | Directional Entry (SPEC-017)| entry gate / directional strategy      |
| 6.4   | Three-Way Entry (SPEC-015)  | 3-way entry gate                       |
| 6.5   | Position Sizing             | sizing                                 |
| 6.6   | Scale-Out (1-tier)          | exit / scale                           |
| 6.7   | Flat Stop-Loss (removed)    | —                                      |
| 6.9   | Market Flip Exit            | exit (market flip)                     |
| 6.10  | Never-in-Profit Guard       | exit                                   |
| 6.11  | Near-Resolve Profit Exit    | exit                                   |
| 6.12  | Ultra-Low Guard             | exit                                   |
| 6.13  | FAV Promotion               | position mgmt                          |
| 6.14  | Hold Revocation             | position mgmt                          |
| 6.15  | Circuit Breaker             | risk                                   |
| 6.16  | Manipulation Guard          | entry / risk                           |
| 6.17  | Liquidity Check             | entry                                  |
| 7     | Sport Rules                 | sport-specific / sport tag work        |
| 13    | Open Items                  | reference                              |

**Safety net:** §6.x cluster — always scan neighbors (sizing ↔ confidence ↔ directional entry). Arch questions → ARCHITECTURE_GUARD.md. Iron rule questions → PRD.md §2.

---

### Stock Queue (F1.5)

Persistent eligible pool between scanner and gate. Prevents Odds API credit waste + missed opportunities.

- Gate pushes rejected markets (exposure_cap / max_positions / stale / no_bookmaker_data) to stock.
- Each heavy cycle: Gamma scan → stock refresh (MarketData updated, delisted dropped) → TTL eviction.
- **JIT batch:** `empty_slots × jit_batch_multiplier` (default 3) items match_start ASC → enrich + gate. Remaining slots: fresh-only batch.
- **TTL evict:** first_seen + 24h | match_start − 30min | event has open position | stale_attempts ≥ 3.
- **Persistent:** `logs/stock_queue.json` — restored on restart.

Rationale: 3 × empty_slots enrich instead of 300. 4 empty slots = 12 nearest markets. ~70% credit savings.

---

## 0. Core Principles (Invariants)

1. **Data source = bookmaker.** Odds API consensus from 20+ books.
2. **3-layer cycle:** WebSocket (instant) + Light (5s) + Heavy (30min).
3. **Position size ∝ confidence:** A=5%, B=4%, C=blocked.
4. **Profit taking = scale-out** (1-tier).
5. **MVP scope = 2-way sports.** Deferred: `TODO.md`.
6. **P(YES) always anchor** — direction-adjusted never stored.
7. **Event-level guard:** same event_id → two positions impossible.

---

## 5. Dashboard & Observability

### 5.7 Dashboard Display Rules

Source: `presentation/dashboard/computed.py` + `static/js/*`

#### 5.7.1 Treemap Branch Grouping

Key = **sport category** (baseball, hockey, tennis, …). Lig → sport map:
```python
_LEAGUE_TO_SPORT = {
    "mlb": "baseball",
    "nhl": "hockey", "ahl": "hockey", "khl": "hockey",
    "nba": "basketball", "wnba": "basketball",
    "nfl": "football", "cfl": "football",
    "epl": "soccer", "ucl": "soccer", "mls": "soccer", "seriea": "soccer",
    "wta": "tennis", "atp": "tennis",
    "pga": "golf", "lpga": "golf", "rbc": "golf",
}
```
Priority: `sport_category` field → `sport_tag` split → lig map → sport_tag as-is → `unknown`.

Partial scale-out: both full-close and partial scale-out counted as separate trade events. Per partial: `invested = sell_pct × original_size_usdc`, `pnl = realized_pnl_usdc`.

Source: `computed.py::sport_roi_treemap` iterates `partial_exits`.

#### 5.7.2 Direction-Adjusted Odds Display

Storage invariant (ARCH Rule 7): `anchor_probability = P(YES)`; `entry_price`/`current_price` = token-native.

Display:
- Active card `Odds X%`: `direction == "BUY_NO" ? 1 − anchor : anchor`
- Entry/Now prices: already token-native → no conversion
- YES/NO badge: BUY_YES → first team in slug, BUY_NO → second. Fallback: `"YES"` / `"NO"`

Source: `static/js/feed.js::_activeCard` + `static/js/dashboard.js::FMT.sideCode`

#### 5.7.3 Feed Sort

All tabs (Active/Exited/Skipped/Stock): `match_start_iso` ASC. Nulls last.

Source: `static/js/feed.js::FEED.render`

#### 5.7.4 CSS Palette

Hex literals **only** in `static/css/dashboard.css:root`. All other CSS/JS: `var(--)` only.

Variables: `--green`, `--red`, `--blue`, `--orange` + `-dim`/`-dark`/`-hover`/`-strong` variants; `--bg`, `--panel*`, `--text`, `--muted*`, `--border-soft`.

JS chart colors: `getComputedStyle(document.documentElement).getPropertyValue("--green")`

#### 5.7.5 Scanner Filter Suite (h2h scope)

Filter order (`_passes_filters`):
1. `closed` / `resolved` / `not accepting_orders` → drop
2. `yes_price >= resolved_price_threshold` (0.98) or `<= 1−threshold` → drop (price-based resolved detection; flag lag bypass)
3. `sports_market_type == "moneyline"` strict (empty string = PGA Top-N props → drop)
4. Sport whitelist: `config.scanner.allowed_sport_tags` (wildcard)
5. Min liquidity: `min_liquidity` (default $1000)
6. Max duration: `end_date ≤ max_duration_days` (default 14d)
7. Odds API window: `match_start ≤ max_hours_to_start` (default 24h)
8. Stale match_start: started 8+ hours ago → drop

Source: `orchestration/scanner.py::MarketScanner._passes_filters`. Config: `config.yaml scanner:`

#### 5.7.6 Enrichment Layer — Tennis Matching

Two fixes:
1. **Tournament prefix strip** (`question_parser.py::extract_teams`): "Porsche Tennis Grand Prix: Eva Lys vs Elina Svitolina" → strip everything before last ":" in team_a.
2. **Slug priority sport_key resolve** (`sport_key_resolver.py::resolve_sport_key`): slug prefix checked BEFORE question text. Prevents wta-* falling into ATP branch.

Note: Odds API tennis ~3 major tournaments/week; Challenger tour = structural gap.

#### 5.7.8 match_start_iso Source + Date-Aware Matching

**Single source: Gamma API `event.startTime`** (per-match accurate). Odds API `commence_time` never overrides — UFC card time 3-4h off, MLB series wrong-day risk.

**Date-aware matching** (`pair_matcher.find_best_event_match`): multiple events for same team pair (MLB/KBO series) → pick closest `commence_time` to `expected_start` from Gamma.

**Immediate persist** (`entry_processor._execute_entry`): `positions.json` written immediately after `add_position()`, BEFORE `trade_logger.log()`. Ensures event_guard consistency on crash+restart.

#### 5.7.7 Total Equity Chart

Formula: `initial_bankroll + Σ exit_pnl_usdc` (cumulative over trade history). **Unrealized excluded.**

Source: `/api/trades` (`computed.exit_events`) — full-close + partial scale-out events. Client builds chronological cumsum.

**Period tabs + adaptive bucketing (PLAN-009):**

| Tab | Granularity | Each point | Typical max |
|-----|------------|------------|-------------|
| 24h | Event      | each exit = 1 step | ~50 |
| 7d  | Hourly     | hour-end cumulative | ~168 |
| 30d | Daily      | day-end cumulative | 30 |
| 1y  | Weekly ISO | week-end cumulative | 52 |

Default: `30d`. No "All" tab (lifetime PnL on Balance card instead). Dense slices (24h/7d): `overflow-x: auto` scroll.

Rendering: `stepped: "before"`, `tension: 0`.

Identity (per period): last point = `initial + Σ exit_pnl_usdc` for that slice.

**Tab-level PnL summary** (Total Equity card only): `<strong>±$XX.XX</strong> · N trades`. Positive green, negative red; `tabular-nums`.

**Per Trade PnL chart:** same 4 tabs, period filter applied, NO bucketing — each bar = 1 exit event. `waterfallMaxBars = 40` + CSS scroll.

**Sticky y-axis:** `scales.y.ticks.display: false`, `afterFit: s.width = 0`. External `.chart-y-axis` DOM element; `externalYAxis` Chart.js plugin writes scale ticks on `afterUpdate`. `$`-prefix + kilo notation (`$1.00k`, `$20`) tabular-nums. Color: `--axis-label`.

**Hitbox accuracy:** set `parent .chart-canvas-wrap style.width`, not `canvas.style.minWidth`. ResizeObserver tracks parent → correct tooltip hit-detection.

Sources:
- `static/js/trade_filter.js::FILTER.cumulativeByResolution`, `.periodLabel`
- `static/js/dashboard.js::CHARTS.setEquity(trades, initialBankroll)`
- `static/js/chart_tabs.js` — `stickyScrollRight`, `externalYAxis` plugins

### 5.8 Restart Protocols

Both modes cover bot (`src.main`) + dashboard (`src.presentation.dashboard.app`).

#### Reload (data preserved)

1. Kill bot + dashboard PIDs → `taskkill`
2. Delete `process.lock`
3. `pytest -q` → FAIL → **STOP**
4. `python -m src.main --mode dry_run &`
5. `python -m src.presentation.dashboard.app &`
6. Verify `bot_status.json` + dashboard access

Preserved: `positions.json`, `trade_history.jsonl`, `circuit_breaker_state.json`, `stock_queue.json`, `equity_history.jsonl`, `skipped_trades.jsonl`

#### Reboot (full reset)

**Requires user confirmation.** Warning: open positions deleted, trade history archived, circuit breaker reset. Irreversible.

1. Kill PIDs + delete `process.lock`
2. Archive: `trade_history.jsonl` → `.bak` (timestamped), `equity_history.jsonl` → `.bak`
3. Reset: `positions.json` → `{"positions":{}, "realized_pnl":0.0, "high_water_mark":0.0}`; delete `circuit_breaker_state.json` / `stock_queue.json` / `skipped_trades.jsonl`
4. `pytest -q` → FAIL → **STOP**
5. Start bot + dashboard; verify

**Archive protection (SPEC-009):** Reboot NEVER touches:
- `logs/archive/exits.jsonl`
- `logs/archive/score_events.jsonl`
- `logs/archive/match_results.jsonl`

---

## 6. Critical Algorithms

### 6.1 Bookmaker Probability

Inputs: `bookmaker_prob` (no-vig, 0–1), `num_bookmakers` (weighted), `has_sharp` (Pinnacle/Betfair Exchange/Smarkets/Matchbook present)

Rules:
- Invalid: `bookmaker_prob` None or ≤ 0, or `num_bookmakers < 1` → `probability = 0.5` fallback
- Valid: `probability = clamp(bookmaker_prob, 0.05, 0.95)`, round 4 decimal

Returns: `BookmakerProbability(probability, confidence, bookmaker_prob_raw, num_bookmakers, has_sharp)`

Confidence derivation → §6.2

### 6.2 Confidence Grading

| Confidence | Condition |
|---|---|
| **A** | `has_sharp = True` (Pinnacle / Betfair Exchange / Matchbook / Smarkets) AND `bm_weight ≥ 5` |
| **B** | `bm_weight ≥ 5`, no sharp |
| **C** | `bm_weight` None OR < 5 — entry blocked |

**Exchange vig-free rule:** Betfair Exchange, Matchbook, Smarkets: no vig → `skip_vig_normalize` in `odds_enricher._parse_bookmaker_markets`. Traditional books: 4-8% overround → normalize required.

**Bookmaker tiers** (`bookmaker_weights.py`):
| Tier | Weight | Bookmakers |
|---|---|---|
| Sharp | 3.0× | Pinnacle, Betfair Exchange (EU/UK/AU), Matchbook, Smarkets |
| Reputable | 1.5× | Bet365, William Hill, Unibet, Betclic, Marathon |
| Standard | 1.0× | All others |

### 6.3 Directional Entry (SPEC-017)

Single strategy. Steps:

1. **Direction from anchor:**
   - `anchor >= 0.50` → BUY_YES, `win_prob = anchor`
   - `anchor < 0.50` → BUY_NO, `win_prob = 1 − anchor`

2. **Favorite filter:** `win_prob >= min_favorite_probability` (default 0.60). Toss-ups blocked.

3. **Price cap (upper outlier):** `effective_entry_price <= max_entry_price` (default 0.80)
   - `effective = BUY_YES ? yes_price : 1 − yes_price`
   - **No lower floor** (post-tuning): bookmaker says 60%+ favorite but Polymarket prices 30¢ = undervalue = positive edge. Floor removed.

4. **Other guards** (event, liquidity, manipulation, exposure cap): unchanged.

5. **Stake (SPEC-016):** `bankroll × bet_pct × win_prob`

Config: `entry.min_favorite_probability`, `entry.max_entry_price`

### 6.4 ThreeWayEntry (SPEC-015)

Soccer/rugby/AFL/handball: 3 markets (Home/Draw/Away) grouped by `EventGrouper` on event_id.

`three_way.evaluate()` logic:
1. Pick favorite = highest bookmaker probability across 3 outcomes
2. Tie-break: equal → SKIP
3. Absolute threshold: `favorite_prob >= 0.40` (3-way calibrated; 2-way equivalent = ~0.55)
4. Relative margin: `favorite − second_highest >= 0.07` (eliminates toss-ups)
5. Price cap: `favorite_market yes_price <= max_entry_price (0.80)` — no lower floor

No live direction switch. No underdog/draw value bet (favorites only).

Scanner `sum_filter`: `sum(3 × yes_price) ∈ [0.95, 1.05]` — eliminates double-chance/handicap/specials.

### 6.5 Position Sizing (SPEC-010 + SPEC-016)

```
stake = bankroll × confidence_bet_pct × win_prob    (SPEC-016)
      capped by: max_single_bet_usdc ($75)
      capped by: bankroll × max_bet_pct (5%)
      floored by: Polymarket $5 min-order → return 0 if below
```

`win_prob` = direction-adjusted:
- `BUY_YES` → `anchor_probability`
- `BUY_NO` → `1 − anchor_probability`

P(YES) always stored as anchor (ARCH_GUARD Rule 8). Direction-adjustment only via `effective_win_prob(anchor, direction)` at sizing time.

Config flag: `risk.probability_weighted: true` (false → base-only formula, rollback)

**Base sizing (`confidence_bet_pct` from config.yaml):**
| Confidence | Pct | Application |
|---|---|---|
| A | 5% | bankroll × 0.05 |
| B | 4% | bankroll × 0.04 |
| C | — | 0 (entry blocked) |

**Multipliers (applied on bet_pct):**
| Condition | Multiplier |
|---|---|
| Lossy reentry — `is_reentry = True` | × 0.80 |

**Entry price cap:** `effective_entry >= 0.88` → gate rejects (`entry_price_cap`). Reason: max payout `0.99 − entry ≤ 0.11`; on $25 position max ~$2.75 gain vs ~$7.50 SL loss. R/R broken.

**Caps:**
- `max_bet_pct` = 5% bankroll (single cap; from config.yaml)
- Bankroll sanity upper bound
- Polymarket minimum: $5 — reject if below

### 6.6 Scale-Out (Midpoint-to-Resolution) — SPEC-013

Config-driven tier list. Per tier: `threshold` (fraction of distance from entry to 0.99) + `sell_pct`.

**Trigger formula** (pure, `scale_out.py`):
```
max_distance = 0.99 − entry_price
current_distance = current_price − entry_price
distance_fraction = current_distance / max_distance
if distance_fraction >= tier.threshold AND not yet triggered: SELL
```

**Example** (default threshold 0.50, 40% sell):
| Entry | Trigger | Locked PnL ($45 stake) |
|---|---|---|
| 0.30 | 0.645 | ≈$14 |
| 0.43 | 0.71  | ≈$11 |
| 0.70 | 0.845 | ≈$8  |
| 0.80 | 0.895 | ≈$4  |

Transition: tier 0 → 1. After tier 1 triggered, remaining position goes to near-resolve or SL.

**Direction-aware:** `entry_price` and `current_price` = effective prices (BUY_YES: yes_price, BUY_NO: no_price). Stored correctly in `src/models/position.py`.

Config: `config.yaml scale_out.tiers` (list, N-tier capable). Near-resolve (§6.11, 94¢) has priority — tier threshold must stay below near-resolve to avoid bypass on price spikes.

### 6.7 Flat Stop-Loss (removed in A3)

Removed: 7-layer flat SL + graduated SL + catastrophic watch. See git history + `docs/superpowers/specs/2026-04-20-*-score-only-exits-*`.

### 6.9 Market Flip Exit

Post A3 spec: A-conf hold branching + `is_a_conf_hold` removed. All positions follow same chain. Score-based exit active for all confidence classes.

**Market flip condition (all sports except tennis):**
- `elapsed_pct >= 0.85` AND `effective_price(pos.current_price, pos.direction) < 0.50`
- → `exit("market_flip")`

**Tennis immune:** Set structure causes 40-50% price swings naturally → false positive risk. Tennis: T1/T2/SFM score exit only.

**SPEC-004 K5 catastrophic_watch:** Removed in A3 (2026-04-20). Score-based exit is a more reliable signal than price alone.

#### 6.9a Score-Based Exit — Hockey Family (SPEC-004, SPEC-014)

Active all confidence classes post-A3.

| Rule | Condition | Config key |
|---|---|---|
| K1 Heavy deficit | deficit ≥ `period_exit_deficit` (3) | sport_rules |
| K2 Late disadvantage | deficit ≥ `late_deficit` (2) + elapsed ≥ `late_elapsed_gate` (0.67) | sport_rules |
| K3 Score + price | deficit ≥ `late_deficit` (2) + price < `score_price_confirm` (0.35) | sport_rules |
| K4 Final minute | deficit ≥ 1 + elapsed ≥ `final_elapsed_gate` (0.92) | sport_rules |

Backtest (9 hockey trades): −$23.24 → +$3.70 (+$26.94). Winning trades ($76.84): untouched.

**NHL/AHL Family (SPEC-014):** `SPORT_RULES["ahl"]` shares NHL thresholds; only `espn_league` differs. `hockey_score_exit._is_hockey_family` checks single set `{"nhl", "ahl"}`. Threshold drift impossible: AHL auto-follows NHL changes.

#### 6.9c Score Polling Infrastructure (SPEC-005)

**Primary:** ESPN public API (`site.api.espn.com`) — free, no API key. Covers hockey (goals), tennis (set+game), MLB (runs), NBA (score).

**Fallback:** Odds API `/scores` — hockey/MLB/NBA. No tennis score.

**Adaptive polling:** normal 60s; price ≤ 35¢ → 30s. Config: `config.yaml score`.

**Kill switch:** `score.enabled: false` → all score polling stops.

**Archive score_at_exit (SPEC-014):** `score_enricher._match_cached` writes `pos.match_score` + `pos.match_period` on match. `exit_processor._log_exit_to_archive` reads `pos.match_score or ""`. Pre-SPEC-014: all 13/13 archive records empty. Now populated for retrospective score-exit analysis.

#### 6.9d Tennis Score-Based Exit (SPEC-006)

ESPN set/game score. BO3 only. Active all confidence classes post-A3.

**T1 — Straight set loss:** 0-1 sets + current set deficit ≥ 3 + games_total ≥ 7 (or deficit ≥ 4).
Tiebreak buffer: 1st set narrow loss (our ≥ 5 games, e.g. 6-7) → deficit threshold +1 (3→4). Blowout (our < 5, e.g. 2-6) → no buffer.

**T2 — Decider set loss:** 1-1 sets + 3rd set deficit ≥ 3 + games_total ≥ 7 (or deficit ≥ 4). No tiebreak buffer (decider — no tolerance).

Config: `sport_rules.py → tennis → set_exit_*`. Comeback rate: 3-8%.

**Serve-for-match (SFM):** In deciding set (T1: set 2 when 0-1; T2: set 3 when 1-1) opponent ≥ 5 games + we're behind → exit. Config: `set_exit_serve_for_match_games`. Deficit + games_total checks skipped — opponent 1 game from close, comeback 8-15%.

#### 6.9e Baseball Score Exit (SPEC-010)

FORCED exit. Sport tags: `mlb`, `kbo`, `npb`, `baseball`. `deficit = opp_score − our_score`.

| Rule | Condition | Rationale |
|---|---|---|
| M1 | `inning >= 7 AND deficit >= 5` | Blowout — unrecoverable |
| M2 | `inning >= 8 AND deficit >= 3` | Late large deficit |
| M3 | `inning >= 9 AND deficit >= 1` | Final inning, any deficit |

Config (`sport_rules.py`): `score_exit_m1_inning`, `score_exit_m1_deficit`, `score_exit_m2_inning`, `score_exit_m2_deficit`, `score_exit_m3_inning`, `score_exit_m3_deficit`

Returns: `ExitReason.SCORE_EXIT`

**Inning source (SPEC-014):** ESPN `status.period` (int 1-9+, 0=pregame). `status.type.description` unreliable (text format variable). Pre-SPEC-014: `_parse_inning` regex was never triggering M1/M2/M3 (audit: 0 score-exits in 13 records). Fix: `ESPNMatchScore.inning: int | None`; dead code `_parse_inning` + `_INNING_RE` removed.

#### 6.9f Cricket Score Exit (SPEC-011)

FORCED exit. 2nd innings (chase) + `our_chasing = True` only. C1/C2/C3 skipped if defending (our_chasing=False — chase collapse benefits us).

| Rule | Condition |
|---|---|
| C1 | `balls_remaining < c1_balls AND required_rate > c1_rate` (impossible chase) |
| C2 | `wickets_lost >= c2_wickets AND runs_remaining > c2_runs` (too many wickets) |
| C3 | `balls_remaining < c3_balls AND runs_remaining > c3_runs` (final over gap) |

Config (`sport_rules.py`):
- T20 default: `c1_balls=30, c1_rate=18, c2_wickets=8, c2_runs=20, c3_balls=6, c3_runs=10`
- ODI relaxed: `c1_balls=60, c1_rate=12, c2_wickets=8, c2_runs=40, c3_balls=30, c3_runs=30`

Score source: CricAPI free tier (100 hits/day; ESPN has no cricket). Limit hit → entry gate `cricapi_unavailable` skip.

#### 6.9g Soccer Score Exit (SPEC-015)

FORCED exit. Uses `SOCCER_CONFIG` (DRY — same function works for rugby/AFL/handball, different config).

**HOME/AWAY position:**
- 0-65': HOLD (comeback potential)
- 65'+: 2 goals down → EXIT
- 75'+: 1 goal down → EXIT

**DRAW position:**
- 0-70', 0-0: HOLD (draw value peak)
- 75'+: any goal → EXIT (draw cliff)
- Knockout + 90+stoppage → AUTO-EXIT (extra time + penalties end draw value)

Design: No red card special exit — ESPN reliability unclear + market flip from goals already catches it. First-half lock 0-65%: soccer comeback rate from 0-1 HT ~25-30%, exiting early destroys EV.

Knockout flag: from `position.tags` or question text ("Cup", "Champions League", "Final", etc.).

### 6.10 Never-in-Profit Guard

**All conditions together:**
- `not ever_in_profit`
- AND `peak_pnl_pct <= 0.01`
- AND `elapsed_pct >= 0.70`

| State | Action |
|---|---|
| Score ahead (`map_diff > 0`, available) | **Stay** |
| `effective_current >= effective_entry × 0.90` | **Stay** (near entry) |
| `effective_current < effective_entry × 0.75` | **Exit** (`never_in_profit`) |
| Between (0.75 ≤ ratio < 0.90) | Flat SL (§6.7) takes over |

### 6.11 Near-Resolve Profit Exit

**Trigger:** `pos.current_price >= 0.94` (token-native, owned side)

Critical: `current_price` is already owned-token price (BUY_YES → YES token, BUY_NO → NO token). Do NOT apply `effective_price()` — double flip. Exit modules use `pos.current_price` and `pos.entry_price` directly. `effective_price()` only for market-side YES input (gate.py).

**Sanity guards (WS spike protection):**
| Condition | Action |
|---|---|
| Pre-match (not started) | Reject |
| `mins_since_start < 10.0` | Reject (opening spike — 0.00/1.00 possible) |
| Otherwise | **Exit** (`near_resolve_profit`) |

Data: 27 near-resolve exits = **+$140.31 (93% WR)** — largest profit source.

### 6.12 Ultra-Low Guard

**All conditions together:**
- `effective_entry < 0.09`
- AND `elapsed_pct >= 0.75`
- AND `effective_current < 0.05`

→ **Exit** (`ultra_low_guard`)

### 6.13 FAV Promotion

Evaluated on `effective_price(current_price, direction)`.

**PROMOTE (all conditions):**
- `not favored`
- AND `effective_price >= 0.65`
- AND `confidence ∈ {A, B}`
→ `favored = True`

**DEMOTE:**
- `favored = True`
- AND `effective_price < 0.65`
→ `favored = False`

`favored = True` positions managed via market_flip + score_exit chain (§6.9). State tracking for FAV promotion/demotion — not a separate exit branch (A-conf hold removed in A3).

Data: 5 favored trades = **+$42.90, 100% WR** — preserved.

### 6.14 Hold Revocation

Non-favored positions only. A-conf hold branch removed in A3.

**Hold candidate:** `favored` OR (`anchor_probability >= 0.65` AND `confidence ∈ {A, B}`)

**Dip temporary?**
- `consecutive_down < 3` OR `cumulative_drop < 0.05` → TEMPORARY (don't revoke)
- Otherwise → PERMANENT

**Revoke conditions (hold candidates):**
| State | Condition | Action |
|---|---|---|
| `ever_in_profit = True` | `current < entry × 0.70` AND `elapsed > 0.60` AND NOT score_ahead AND NOT dip_temporary | Revoke hold (return to normal rules) |
| `ever_in_profit = False` | `current < entry × 0.75` AND `elapsed > 0.70` AND NOT score_ahead AND NOT dip_temporary | Revoke + **Exit** (`hold_revoked`) |

### 6.15 Circuit Breaker

**Entry halt only** — never affects exits.

**NET PnL tracking:** Daily/hourly PnL accumulated in **USD** (wins + losses net). At check time: divide by current `portfolio_value` for percentage. Partial exit profits included. All realized PnL counted.

Reason for USD accumulation: old approach summed percentages at different portfolio values → false triggers on net-profitable days.

**Thresholds:**
| Parameter | Value | Effect |
|---|---|---|
| Daily max NET loss (hard halt) | -8% | Halt + 120min cooldown |
| Hourly max NET loss (hard halt) | -5% | Halt + 60min cooldown |
| Consecutive loss limit | 4 trades | Halt + 60min cooldown |
| Daily entry soft block | -3% | Soft block (entries suspended, not hard halt) |

**`should_halt_entries(portfolio_value)` check order:**
1. Cooldown active? → halt (show remaining min)
2. Daily NET loss ≤ -8% → halt 120min ("Daily limit hit")
3. Hourly NET loss ≤ -5% → halt 60min ("Hourly limit hit")
4. Consecutive losses ≥ 4 → halt 60min ("Consecutive loss limit")
5. Daily NET loss ≤ -3% → soft block ("Soft block (-3%)")
6. Otherwise → continue

**Exposure Cap (entry block):**

```
exposure = (total_invested + candidate_size) / total_portfolio_value
total_portfolio_value = portfolio.bankroll (cash) + portfolio.total_invested()
```

`max_exposure_pct` (config `risk.max_exposure_pct`, default 0.50) = **soft cap**. Gate/agent clip size rather than full reject:

- `soft_cap = portfolio × max_exposure_pct` (50%)
- `hard_cap = portfolio × (max_exposure_pct + hard_cap_overflow_pct)` (52%)
- `available = max(0, hard_cap − total_invested)`
- `min_size = bankroll × min_entry_size_pct` (1.5%)

Flow:
1. `available <= 0` → skip (`exposure_cap_reached`)
2. `available < min_size` → skip (tx-cost floor; micro-position unprofitable after fees)
3. Otherwise → `entry_size = min(kelly, available)`

**Match-start ASC priority:** approved signals sorted `match_start ASC, volume_24h DESC`. Earlier matches claim cap capacity first.

**Critical invariant:** denominator = TOTAL portfolio value (cash + invested). Using only `portfolio.bankroll` as denominator shrinks as positions open → cap triggers prematurely.

**Pure function:** `domain/portfolio/exposure.py::available_under_cap`
**Callers:** `strategy/entry/gate.py` + `orchestration/agent.py` — both compute `pm.bankroll + pm.total_invested()`
**Tests:** `tests/unit/domain/portfolio/test_exposure.py` (5), `tests/unit/strategy/entry/test_gate.py` (clip tests), `tests/unit/orchestration/test_agent.py` (priority tests)

### 6.16 Manipulation Guard

**Self-resolving subjects** (16): `trump, biden, elon, musk, putin, zelensky, xi jinping, desantis, vance, newsom, harris, netanyahu, modi, zuckerberg, bezos, altman`

**Self-resolving verbs** (regex, case-insensitive, word boundary): `say, tweet, post, announce, sign, veto, pardon, fire, hire, appoint, endorse, resign, visit, meet with, call, respond, comment, declare`

**Risk score:**
| Check | Condition | Score |
|---|---|---|
| Self-resolving | Subject AND verb in question + description | +3 |
| Low liquidity | `liquidity < 10_000` | +1 (+2 if `liquidity <= 0`) |

**Risk level → behavior:**
| Score | Level | Action |
|---|---|---|
| ≥ 3 | high | **SKIP** |
| = 2 | medium | Size × 0.5 |
| < 2 | low | OK (full size) |

Default `min_liquidity_usd`: `10000` (config.yaml `manipulation.min_liquidity_usd`)

### 6.17 Liquidity Check

**Entry check:**

`total_ask_depth = sum(ask.price × ask.size)` across all ask levels.

| Condition | Action |
|---|---|
| `total_ask_depth < $100` | **Reject** (`ok=False`, reason: "Depth < $100") |
| `size_usdc / total_ask_depth > 0.20` | Halve size (`recommended_size = size / 2`) |
| Otherwise | Accept, original size |

Default `min_depth`: `100.0`

**Exit check:**

`floor_price = best_bid × 0.95`
`available = sum(bid.size for bid in book.bids if bid.price >= floor_price)`
`fill_ratio = available / shares_to_sell`

| `fill_ratio` | Strategy |
|---|---|
| ≥ 1.0 | `market` (single order) |
| `min_fill_ratio` ≤ ratio < 1.0 | `limit` (at floor_price) |
| < `min_fill_ratio` | `split` (chunk over time) |

Default `min_fill_ratio`: `0.80`

---

## 7. Sport Rules (MVP)

### 7.1 Scope

**Active (2-way):**
- Baseball: MLB, MiLB, NPB, KBO, NCAA
- Basketball: NBA, WNBA, NCAAB, WNCAAB, Euroleague, NBL, NBA Summer
- Ice Hockey: NHL, AHL, Liiga, Mestis, SHL, Allsvenskan
- American Football: NFL, NCAAF, CFL, UFL
- Tennis: All ATP/WTA (dynamic matching)

**SPEC-015 MVP additions (3-way):** Soccer (all leagues), rugby, AFL, handball — via `threeway_enricher.py`.

**MVP excluded:** Cricket (test match) — long draw probability, separate modeling needed.

MMA: TODO-002. Golf: TODO-003.

### 7.2 Sport Rules Summary

| Sport | match_duration_hours | Score exit |
|---|---|---|
| NBA | 2.5 | N1/N2/N3 (elapsed + deficit + period/clock — A3 + A4) |
| NFL | 3.25 | N1/N2/N3 (elapsed + deficit + period/clock — A3 + A4) |
| NCAAF/CFL/UFL | 3.25 | late-game deficit exit |
| NHL (AHL/Liiga/…) | 2.5 | K1-K4 (deficit/elapsed/price) |
| MLB (+MiLB/NPB/KBO/NCAA) | 3.0 | M1-M3 (inning+deficit — SPEC-010) |
| Tennis ATP/WTA | 1.75-3.5 (BO3/BO5) | T1/T2 set-game + market_flip DISABLED |
| cricket_ipl | 3.5 | C1/C2/C3 (T20) |
| cricket_odi | 8.0 | C1/C2/C3 (ODI, relaxed) |
| cricket_international_t20 | 3.5 | C1/C2/C3 (T20) |
| cricket_psl | 3.5 | C1/C2/C3 (T20) |
| cricket_big_bash | 3.5 | C1/C2/C3 (T20) |
| cricket_caribbean_premier_league | 3.5 | C1/C2/C3 (T20) |
| cricket_t20_blast | 3.5 | C1/C2/C3 (T20) |
| soccer | 2.0 | HOME/AWAY 65'+ + DRAW 70'+ (SPEC-015) |
| rugby_union | 1.75 | blowout 50'+ 14pt, late 70'+ 7pt |
| afl | 2.0 | blowout 60'+ 30pt, late 75'+ 15pt |
| handball | 1.5 | blowout 45'+ 8goals, late 55'+ 4goals |
| DEFAULT | 2.0 | — |

Detailed `sport_rules` tables: `src/config/sport_rules.py`. Deferred: `TODO.md` TODO-001.

#### 7.2.1 NBA Score Exit (A3 + SPEC-A4)

- **N1:** elapsed ≥ 0.75 + deficit ≥ **18** (Q3 end + heavy gap; 17pt comeback = 2-3%)
- **N2:** elapsed ≥ 0.92 + deficit ≥ **8** (last 4min + meaningful gap; still 8-10% safe)
- **N3 (SPEC-A4):** period_number == 4 AND clock_seconds ≤ 120 AND deficit ≥ 5 (last 2min, one-score+; comeback 3-5%)

Priority: N3 > N2 > N1. Thresholds from `sport_rules.py`.

#### 7.2.2 NFL Score Exit (A3 + SPEC-A4)

- **N1:** elapsed ≥ 0.75 + deficit ≥ **17** (Q3 end + 2.5-score; σ-model 99% confidence)
- **N2:** elapsed ≥ 0.92 + deficit ≥ **9** (last 5min + 2-possession; 3-4% safe)
- **N3 (SPEC-A4):** period_number == 4 AND clock_seconds ≤ 150 AND deficit ≥ 4 (last 2.5min, one-score; possession ambiguous zone)

Priority: N3 > N2 > N1. Thresholds from `sport_rules.py`.

#### 7.2.3 Period + Clock Infrastructure (SPEC-A4)

NBA/NFL exits use `score_info["period_number"]` (int 1-4, 5+=OT) + `score_info["clock_seconds"]` (ESPN displayClock "M:SS" parse). Parse fail → `clock_seconds = None` → N3 doesn't fire (fail-safe); N1/N2 continue via elapsed_pct (backward compat).

Other sports (Hockey, Baseball, Tennis, Cricket, Soccer): still use `elapsed_pct`. Full period/clock refactor deferred to SPEC-A5 after NBA/NFL live observation.

### 7.3 Sport Tag Validation (Slug-Based Override)

Gamma API event tags unreliable: events can carry multiple tags; wrong tag can come first. Broken tag → wrong exit rules, wrong treemap category, wrong sport_rules.

**Defense** (`gamma_client._parse_market`): Market slug prefix checked against `_SLUG_PREFIX_SPORT` lookup. Slug prefix overrides event tag with WARNING logged.

```
Priority: slug prefix (most reliable) > event tag (Gamma API order-dependent)
```

**Lookup table** (`infrastructure/apis/gamma_client.py` — aligned with `config.scanner.allowed_sport_tags`):

| Slug prefix | Correct sport_tag | Note |
|---|---|---|
| atp, wta | tennis | generic `tennis` + `atp*`/`wta*` wildcard in whitelist |
| nhl, ahl, liiga, mestis, shl, allsvenskan | (prefix = self) | specific league; `hockey` generic removed (SPEC-003, no KHL) |
| nba, wnba, ncaab, wncaab, cbb, euroleague, nbl | (prefix = self) | specific league; `basketball` generic removed (SPEC-003) |
| mlb, milb, npb, kbo | baseball | generic `baseball` in whitelist |
| ncaaf, cfl, ufl, nfl | (prefix = self) | `football` generic not in whitelist; NFL scanner-dropped (TODO-001) |
| ufc, mma | mma | generic `mma` in whitelist |
| boxing | boxing | `boxing` in whitelist |
| lpga, liv, pga | (prefix = self) | `lpga*`/`liv*`/`pga*` wildcard in whitelist |

Root cause (2026-04-17): `atp-medjedo-borges` arrived with `ncaab` tag. Root cause (2026-04-19): Gamma sends NBA events with team tags (`raptors`, `magic`) → old table mapped `nba → basketball` (not in whitelist) → NBA/NHL/NFL silently filtered. Aligning values with config whitelist fixes this.

---

## 13. Open Items

1. **Golf outright futures:** H2H only (`golf_lpga_tour`, `golf_liv_tour`) in MVP. Outright winner markets scope-out.
2. **Tennis dynamic matching:** `odds_client.py::_get_active_tennis_keys` + `_match_tennis_key` migration pending.
3. **Baseball preseason:** `baseball_mlb_preseason` active but motivation factor low — potential `allow_preseason: false` flag.
4. **Draw-possible sports:** Soccer/rugby/AFL/handball added (SPEC-015). Remaining: Cricket Test, Boxing, NFL draw — TODO-001.
