# Upset Hunter Module — Design Spec

## Summary

Replace bond farming (90-97¢ YES tokens, inverted risk/reward) with upset hunter (5-15¢ underdog YES tokens, asymmetric upside). Bond farming lost money: 2W/2L = -$15.98, single upset wiped 13+ wins. Upset hunter flips the asymmetry — small frequent losses, rare large wins.

## Motivation

**Bond farming problem:**
- Buy YES at 90-97¢, resolve at $1.00 for 3-7% profit
- Kelly math: need 93%+ win rate at 93¢ to break even — too narrow
- One loss ($80) wipes 13 wins ($6 each)
- Live results confirmed: net negative after 4 trades

**Upset hunter thesis:**
- Favourite-longshot bias: markets systematically overprice favorites, underprice underdogs
- At 10¢, only need 11% win rate to break even
- One win ($150+) covers 8+ losses ($20 each)
- Risk/reward correctly aligned: small bets, huge upside

## Architecture

**Approach:** Bağımsız modül — new `upset_hunter.py` replaces `bond_scanner.py`. Same call point in agent.py, completely different logic.

### Files Changed

| Action | File | What |
|--------|------|------|
| **DELETE** | `src/bond_scanner.py` | Entire file removed |
| **CREATE** | `src/upset_hunter.py` | Pre-filter + candidate scoring |
| **MODIFY** | `src/config.py` | Remove `BondFarmingConfig`, add `UpsetHunterConfig` |
| **MODIFY** | `src/agent.py` | `_check_bond_farming()` → `_check_upset_hunter()` |
| **MODIFY** | `src/exit_monitor.py` | Add upset-specific exit params (SL, trailing TP) |
| **MODIFY** | `src/match_exit.py` | Add forced exit at last 10% of match |
| **MODIFY** | `src/ai_analyst.py` | Add underdog-specific prompt template |
| **MODIFY** | `src/scale_out.py` | Add upset-specific 3-tier config |
| **MODIFY** | `src/trade_logger.py` | Replace "bond_farming" edge source with "upset_hunter" |
| **MODIFY** | `analyze_pnl.py` | Add "UPSET_ENTRY" to action filter |

### Files NOT Changed

- `portfolio.py` — uses generic `entry_reason` string, no changes needed
- `risk_manager.py` — existing limits apply, upset uses normal position slots
- `trailing_tp.py` — pure function, caller passes params
- `models.py` — `Position.entry_reason` is generic string
- `reentry_farming.py` — works with any entry_reason

## Confirmed Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Price zone | 5-15¢ | Favourite-longshot bias zone |
| Per-position size | 2% bankroll ($20) | Small bets, frequent losses expected |
| Stop-loss | 50% | 10¢→5¢ triggers exit, max loss $10 |
| Max concurrent | 3 positions | 3×$20=$60 max risk, under circuit breaker |
| Position slots | Shared with core (from max 20) | No separate pool needed |
| Exposure cap | +5% on top of core's 30% = 35% total | Separate upset allocation |
| Promotion threshold | 35¢ | Above 35¢ → switch to core exit rules |
| Forced match exit | Last 10% of match | No holding to resolution |
| AI model | Claude Sonnet | Accuracy over cost savings |
| Confidence minimum | B- (same as core) | Existing tier system applies |
| Kelly fraction | 0.20 (same as core) | Already conservative |
| Daily circuit breaker | -8% (shared with core) | Same trigger for everything |

## Module Design

### 1. Pre-Filter (Before AI — Cheap Elimination)

Runs during heavy cycle. Eliminates ~80-90% of candidates before expensive Sonnet call.

**Filter 1 — Price Zone:**
- `5¢ <= yes_price <= 15¢`
- Outside range → skip

**Filter 2 — Odds API Divergence:**
- Compare Polymarket price vs Odds API implied probability
- Minimum 5 percentage point divergence required
- Example: Polymarket 8¢, Odds API implies 14% → 6pt divergence → pass
- Example: Polymarket 10¢, Odds API implies 12% → 2pt divergence → skip (below 5pt minimum)
- If no Odds API data available (esports, niche sports) → skip this filter, pass to AI with note "no bookmaker cross-reference"

**Filter 3 — Minimum Liquidity:**
- $5,000 minimum CLOB liquidity
- Below → skip (can't exit position)

**Filter 4 — Timing Window:**
- Max 48 hours before match start → pass
- More than 48 hours → skip (price too unstable)
- Match already started AND past 75% → skip (too late for entry)

**Filter 5 — Moneyline Only:**
- Block: draw, spread, total, BTTS, first-half, props markets
- Allow: match winner / moneyline only
- Slug filter: reject if contains `-draw`, `-spread-`, `-total-`, `-btts`, `-1h-`, `-first-half-`

### 2. AI Analysis (Underdog-Specific Prompt)

Candidates passing pre-filter go to Claude Sonnet with a different analytical lens:

**Core question:** "Is this team MORE likely to win than {market_price}% implies?"

**Prompt focus areas:**
- Favorite's vulnerabilities (form drop, injuries, motivation, fatigue, travel)
- Underdog's hidden strengths (recent form trajectory, style matchup, home advantage)
- Historical upset frequency for this matchup type
- Match conditions (tennis surface, esports map pool, soccer away form)

**Output:** Same JSON schema as core strategy — `probability`, `confidence_grade`, `edge`, `key_factors`, `recommendation`

**Entry decision:**
- AI probability > market price + 5% edge minimum
- Confidence grade >= B-
- If both pass → enter

**Esports calibration note in prompt:** "Historical data shows esports underdog probability is systematically underestimated. In BO1 formats, upset frequency is significantly higher than implied odds suggest. Weight this accordingly."

### 3. Entry Flow

```
Heavy Cycle
  → market_scanner returns markets in 5-15¢ range
  → upset_hunter.pre_filter(markets)
      → Filter 1-5 eliminate ~80-90%
  → Remaining candidates → ai_analyst with underdog prompt
  → AI returns probability + confidence
  → If confidence >= B- AND edge >= 5%:
      → risk_manager.check_entry() (existing limits)
      → executor.place_order(token_id, "BUY", price, size)
      → portfolio.add_position(entry_reason="upset")
      → trade_logger.log(action="UPSET_ENTRY")
      → notifier.send("UPSET ENTRY: ...")
```

### 4. Exit System (5 Layers, Priority Order)

**Layer 1 — Forced Match Exit (HIGHEST PRIORITY):**
- When `elapsed_pct >= 0.90` (last 10% of match)
- Exit regardless of P&L
- Reason: holding underdog to resolution = 85-90% chance of $0
- Implementation: new check in `match_exit.py`, gated by `entry_reason == "upset"`

**Layer 2 — Stop-Loss 50%:**
- Token drops from entry to 50% loss (e.g., 10¢ → 5¢)
- Max loss per position: $10 (on $20 bet)
- Implementation: `exit_monitor.py` reads SL from `UpsetHunterConfig.stop_loss_pct` when `entry_reason == "upset"`

**Layer 3 — 3-Tier Scale-Out:**
- Tier 1: price reaches 25¢ (2.5x entry) → sell 30% of position
- Tier 2: price reaches 35¢ (3.5x entry) → sell 30% more
- Tier 3: remaining 40% → automatically promoted to core exit rules (since Tier 2 triggers at 35¢ = promotion price)
- Implementation: `scale_out.py` gets `entry_reason` parameter, uses upset-specific tiers
- Note: Tier 2 and promotion share the 35¢ threshold — Tier 2 sells 30%, then remaining 40% immediately enters promotion

**Layer 4 — Promotion to Core Exit Rules:**
- When remaining position price >= 35¢
- Position switches from upset exit rules to core exit rules
- Core trailing TP: +20% activation, 8% trail distance
- Deadzone (40-60¢) only blocks entry, not exit — no conflict

**Layer 5 — Underdog Trailing TP (pre-promotion):**
- Activation: +100% (price must double from entry)
- Trail distance: 25% from peak
- Wider than core because underdog prices are volatile
- Implementation: `exit_monitor.py` passes upset-specific params to `calculate_trailing_tp()`

### 5. Position Lifecycle

```
ENTRY (5-15¢)
  │
  ├─ Price drops to 50% of entry → SL exit (Layer 2)
  │
  ├─ Match reaches 90%+ elapsed → Forced exit (Layer 1)
  │
  ├─ Price rises to 25¢ → Scale-out Tier 1: sell 30%
  │     │
  │     ├─ Price rises to 35¢ → Scale-out Tier 2: sell 30%
  │     │     │
  │     │     └─ Remaining 40% promoted to core exit rules
  │     │           │
  │     │           ├─ Core trailing TP (+20%/8%)
  │     │           └─ Core graduated SL
  │     │
  │     └─ Price drops → Underdog trailing TP (100%/25%)
  │
  └─ Price doubles → Underdog trailing TP activates (Layer 5)
```

### 6. Reentry Handling

- Upset positions that exit profitably (trailing_stop, take_profit, scale_out_final) → added to reentry pool
- Reentry uses standard reentry_farming logic (existing)
- Reentry entry_reason = `"re_entry_t1"` (NOT "upset") — prevents recursive upset hunting on same market
- Upset positions that exit at loss → blacklisted (standard behavior)

## Config

```python
class UpsetHunterConfig(BaseModel):
    enabled: bool = True
    min_price: float = 0.05
    max_price: float = 0.15
    bet_pct: float = 0.02
    max_concurrent: int = 3
    stop_loss_pct: float = 0.50
    min_liquidity: float = 5_000
    min_odds_divergence: float = 0.05
    max_hours_before_match: float = 48
    late_match_exit_pct: float = 0.10
    promotion_price: float = 0.35
    scale_out_tier1_price: float = 0.25
    scale_out_tier1_sell_pct: float = 0.30
    scale_out_tier2_price: float = 0.35
    scale_out_tier2_sell_pct: float = 0.30
    trailing_activation: float = 1.00
    trailing_distance: float = 0.25
    max_hold_hours: float = 3.0
```

## Bond Farming Removal — Complete Cleanup

Every bond reference in the codebase (14 points identified):

| File | What to Do |
|------|-----------|
| `bond_scanner.py` | Delete entire file |
| `config.py:127-137` | Delete `BondFarmingConfig` class |
| `config.py:202` | Delete `bond_farming: BondFarmingConfig` from AppConfig |
| `agent.py:1092` | Change import from `bond_scanner` to `upset_hunter` |
| `agent.py:1088-1171` | Replace `_check_bond_farming()` with `_check_upset_hunter()` |
| `agent.py:444` | Change call from `_check_bond_farming` to `_check_upset_hunter` |
| `agent.py:1095-1098` | Change `entry_reason == "bond"` to `entry_reason == "upset"` |
| `agent.py:1100` | Change `self.config.bond_farming` to `self.config.upset_hunter` |
| `agent.py:1147,1149` | Change `entry_reason="bond"` to `entry_reason="upset"` |
| `agent.py:1156` | Change `"BOND_ENTRY"` to `"UPSET_ENTRY"` |
| `agent.py:1158,1164,1168` | Change `bond_type` references to `upset_type` |
| `trade_logger.py:74` | Change `"bond_farming"` to `"upset_hunter"` in edge sources |
| `analyze_pnl.py:75` | Add `"UPSET_ENTRY"` to action filter (keep `"BOND_ENTRY"` for historical logs) |

Zero dead code after migration. No bond references remain in active code.

## Edge Cases

**1. Core + Upset same match:**
Already handled. `event_id` check in entry_gate.py (line 659-678) prevents entering any market from same event. If core holds a position, upset can't enter same match and vice versa.

**2. Match timing unavailable:**
If `match_start_iso` is missing, `elapsed_pct = -1.0`. Forced match exit won't trigger. Fallback: if position held > `max_hold_hours` (default 3.0, configurable in UpsetHunterConfig) with no match timing data AND position is at a loss, exit. If position is in profit with no timing data, let trailing TP handle the exit instead.

**3. Odds API data unavailable:**
Pre-filter divergence check is skipped. AI evaluates with lower confidence (no cross-reference). Confidence tier system naturally handles this — AI gives B- or lower without data.

**4. Price gap through scale-out tiers:**
Token jumps from 15¢ to 40¢ in one update (skips 25¢ and 35¢ tiers). Scale-out catches up: execute both Tier 1 and Tier 2 in same cycle, then promote remaining to core.

**5. Reentry as upset:**
Prevented. Reentry uses `entry_reason="re_entry_tX"`, not `"upset"`. Upset hunter only enters fresh candidates from market scanner, never from reentry pool.

## Performance Evaluation

**Expected baseline (if strategy works):**
- Win rate: 10-20%
- Average win: 5-10x entry price
- Average loss: 50-100% of small position
- Net positive after 50+ bets

**Kill switch:**
- After 50 bets: if win rate < 5% AND cumulative ROI < -30% → auto-disable
- After 30 bets: if win rate = 0% → auto-disable immediately

**Tracking:** Log every upset bet with `action="UPSET_ENTRY"`, track via existing edge source system as `"upset_hunter"`.
