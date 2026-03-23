# Polymarket Bot — Complete Exit & Re-Entry Rule System

> **Purpose:** This document describes the FULL exit and re-entry system currently running in the bot.
> Use this as context when proposing improvements. Any new feature MUST NOT conflict with these rules.

---

## Part 1: Exit System Overview

The bot has TWO exit systems running in parallel:

### A. Legacy Flat Exit System (portfolio.py)
Still active, runs AFTER the match-aware system. Acts as a safety net.

| Check | Logic | Trigger |
|-------|-------|---------|
| **Stop Loss** | `unrealized_pnl_pct < -SL%` | SL varies: 40% default, 30% for medium_low, 50% for VS, ultra-low (<9¢) exempt |
| **Take Profit** | Confidence-based thresholds | low/medium_low=40%, medium/medium_high=80%, high=140% |
| **Trailing Stop** | Peak-based: 10%+ peak→50% drop, 20%+→35%, 40%+→25% | Tightest matching tier wins |
| **Favorite Hold** | AI≥65% + high/medium_high conf → hold to resolve | Only exits on >50% spike overshoot |
| **Underdog Edge TP** | Exit when price reaches AI_target × 85% AND price > entry×1.10 | Closes at 85% of AI's fair value |
| **VS Take Profit** | Dynamic: cheap (3¢)→200% TP, expensive (30¢)→50% TP | Linear interpolation |
| **VS Time Exit** | Volatility swings exit 15min before resolution | Must exit — holding VS to resolve = guaranteed loss |

### B. Match-Aware Exit System (match_exit.py) — NEW
Runs BEFORE the legacy system. 4-layer graduated exit using match timing, score, and profit history.

#### Layer 0: Score Terminal
```
if is_already_lost → EXIT immediately
if is_already_won  → HOLD to resolve (don't sell winner)

Score parsing: "2-1|Bo3" → direction-aware (BUY_YES=first team, BUY_NO=second team)
wins_needed = (BO // 2) + 1
  BO1: 1 win needed
  BO3: 2 wins needed
  BO5: 3 wins needed
```

**Important limitation:** By the time score shows match lost (e.g., 0-2 in BO3), price has usually already crashed to 1-3¢. L0's real value is preventing early sale of WINNING positions.

#### Layer 1: Catastrophic Floor
```
if entry_price >= 0.25 AND current_price < entry_price × 0.50 → EXIT
```
Fires regardless of score, timing, or any other factor. Absolute safety net.

#### Layer 2: Graduated Stop Loss (primary protector)
```
max_loss = base_tier × entry_price_multiplier × score_adjustment

Base tiers (by elapsed_pct of estimated match duration):
  0% - 40%  → 40% max loss (early match, wide)
  40% - 65% → 30% max loss (mid match)
  65% - 85% → 20% max loss (late match)
  85% - 100% → 15% max loss (final phase, tight)
  100%+     → 5% max loss (overtime, very tight)

Entry price multiplier (adjusts for bet type):
  <20¢ (heavy underdog) → 1.50× (wider, more room)
  <35¢ (underdog)       → 1.25×
  ≤50¢ (coin flip)      → 1.00×
  <70¢ (slight favorite)→ 0.85×
  ≥70¢ (heavy favorite) → 0.70× (tighter, less room)

Score adjustment:
  Ahead (map_diff > 0) → 1.25× (loosen — we're winning)
  Even  (map_diff = 0) → 1.00×
  Behind (map_diff < 0) → 0.75× (tighten — we're losing)

Momentum tightening:
  3+ consecutive down cycles AND 5¢+ cumulative drop → tighten by 25% (max_loss × 0.75)

Final: clamp result to [0.05, 0.70]
If unrealized_pnl_pct < -max_loss → EXIT
```

**Example:** Entry 72¢, BO3 LoL, 85% elapsed, score 1-1
```
base=0.15 × price_mult=0.70 × score_adj=1.0 = 0.105
Exit if PnL < -10.5% (i.e., price drops to ~64¢)
Old system would wait until -40% (43¢). New system saves 30% of loss.
```

#### Ultra-Low Guard
```
if entry < 9¢ AND elapsed ≥ 90% AND current_price < 5¢ → EXIT
```
Ultra-cheap entries are normally exempt from SL, but if match is almost over and price is dead, exit.

#### Layer 3: Never-in-Profit Guard
```
if ever_in_profit=False AND peak_pnl ≤ 1% AND elapsed ≥ 70%:
  if score_ahead → STAY (winning despite no profit, price may catch up)
  if price ≥ entry × 0.90 → STAY (close to entry, not urgent)
  if price < entry × 0.75 → EXIT
  Between 0.75-0.90 → Layer 2 handles via graduated SL
```

#### Layer 4: Hold-to-Resolve Decision Matrix
Applies to positions that qualify for hold-to-resolve (scouted OR AI≥65% + high/medium_high conf).

**Revocation conditions:**
```
If ever_in_profit AND price < entry×0.70 AND elapsed > 60%:
  if NOT score_ahead AND NOT temporary_dip → REVOKE hold

If NOT ever_in_profit AND price < entry×0.75 AND elapsed > 70%:
  if NOT score_ahead AND NOT temporary_dip → REVOKE hold + EXIT

Temporary dip = consecutive_down < 3 OR cumulative_drop < 5¢
```

**Restoration conditions:**
```
If hold_was_original AND previously_revoked AND 10+ min since revocation:
  if price > entry × 0.85 AND NOT score_behind → RESTORE hold
```

#### Game Duration Estimates (for elapsed_pct calculation)
```
CS2:  BO1=40min, BO3=130min, BO5=200min
Val:  BO1=50min, BO3=140min, BO5=220min
LoL:  BO1=35min, BO3=100min, BO5=160min
Dota2: BO1=45min, BO3=130min, BO5=210min
Football (EPL, UCL, etc.): 95min
NBA: 150min, MLB: 180min, NHL: 150min
Generic esports fallback: BO1=40, BO3=120, BO5=180
Absolute fallback: 90min
```

---

## Part 2: Position Tracking Fields

Each position tracks these fields for the exit system:

```python
ever_in_profit: bool          # True once peak_pnl_pct > 1% (never resets)
consecutive_down_cycles: int  # Consecutive cycles where price dropped
cumulative_drop: float        # Total price drop during current down streak
previous_cycle_price: float   # Price at last cycle (for momentum tracking)
hold_revoked_at: datetime     # When hold-to-resolve was revoked (None if not)
hold_was_original: bool       # Was this originally a hold-to-resolve position
peak_pnl_pct: float          # Highest unrealized PnL % ever seen
scouted: bool                 # Pre-game scouted entry → hold to resolve
volatility_swing: bool        # Bought cheap underdog for in-game spike → tight TP/SL
```

---

## Part 3: Current Re-Entry System

The bot already has TWO re-entry mechanisms:

### A. Spike Re-Entry (_check_spike_reentry)
**Trigger:** Position exited via `spike_exit` (>50% gain on favorite)

```
Saved data: AI probability, confidence, direction, exit_price, entry_price
Expiry: 10 cycles after exit
Re-entry conditions:
  - current_price < exit_price (price dropped back)
  - edge (|ai_prob - current_price|) > min_edge
  - Position slot available
  - No AI call — uses saved analysis
Size: Full Kelly calculation
```

### B. Scouted Re-Entry (_check_scouted_reentry)
**Trigger:** Scouted position exited via `take_profit` or `trailing_stop`

```
Saved data: Same as spike + match_start_iso
Expiry: 15 cycles after exit (longer horizon for scouted)
Re-entry conditions:
  - Price dropped ≥ 15% from exit_price
  - edge > min_edge
  - Match hasn't ended (end_date_iso check)
  - Position slot available
  - No AI call — uses saved analysis
  - Re-enters with scouted=True (continues hold-to-resolve)
Size: Full Kelly calculation
```

### C. Permanent Blacklist
**Trigger:** Any exit EXCEPT spike_exit and scouted TP/trailing

```
All other exits (stop_loss, match_exit, hold_revoked, etc.):
  → condition_id added to _exited_markets set
  → Persisted to logs/exited_markets.json
  → NEVER re-enter this market
```

### D. Temporary Cooldown
```
Every exit sets: _exit_cooldowns[cid] = current_cycle + 3
Market is skipped for 3 cycles regardless of exit reason
```

---

## Part 4: What's Missing (Proposed New Feature)

### Re-Entry After Normal Take-Profit

**Gap:** When a NON-scouted, NON-spike position exits via normal take-profit, it goes to permanent blacklist. There's no mechanism to re-enter even if:
- The team is clearly going to win
- Price dropped back to a better entry point
- Match still has 60%+ remaining

**Proposed: "Re-Entry After Profit" system**

Entry criteria (ALL must be true):
| Criterion | Value | Rationale |
|-----------|-------|-----------|
| Previous exit reason | `take_profit` or `trailing_stop` or `edge_tp` | Only profitable exits |
| Match timing | `elapsed_pct < 0.40` | At least 60% of match remaining |
| New price vs old entry | `new_price ≤ old_entry × 0.95` | Better price than before |
| AI probability | `≥ 0.60` | Still favors our side |
| Score | `map_diff ≥ 0` | Not losing |
| Cooldown | `≥ 5 minutes` since exit | Whipsaw protection |
| Daily limit | Max 1 re-entry per market | No overtrading |

Position settings for re-entry:
```
entry_reason: "re_entry_after_profit"
scouted: False
hold_to_resolve: True only if AI prob ≥ 0.70 AND score ahead
size: 75% of original position (reduced risk on second entry)
```

Safety rails:
- Max 3 re-entries per day (all markets combined)
- SL/match_exit exits → permanent blacklist (no re-entry after loss)
- If re-entry position hits SL → permanent blacklist
- Re-entry uses normal budget, no extra allocation

---

## Part 5: How Exit + Re-Entry Interact

```
                    ┌──────────────────┐
                    │   POSITION OPEN   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Match-Aware Exit │ (every 2-5 min cycle)
                    │  (4 layers)       │
                    └────────┬─────────┘
                             │
              No exit ───────┤──────── Exit triggered
                             │              │
                    ┌────────▼─────────┐    │
                    │  Legacy Exit      │    │
                    │  (SL/TP/trailing) │    │
                    └────────┬─────────┘    │
                             │              │
              No exit ───────┤              │
                             │              │
                    Position stays     ┌────▼──────────────┐
                                       │  What was the      │
                                       │  exit reason?       │
                                       └────┬──────────────┘
                                            │
                    ┌───────────────────┬────┴────────────────┐
                    │                   │                      │
              spike_exit          TP/trailing              Everything else
                    │            (scouted only)            (SL, match_exit,
                    │                   │                   hold_revoked...)
                    ▼                   ▼                      │
            Spike Re-Entry      Scouted Re-Entry               ▼
            (10 cycle window)   (15 cycle window)        Permanent Blacklist
                                                         (never re-enter)
                    │                   │
                    │    ┌──────────────┤
                    │    │              │
                    │  NEW: Normal TP   │
                    │  Re-Entry         │
                    │  (proposed)       │
                    ▼                   ▼
              Same exit system applies to re-entered positions
              (match-aware + legacy, full protection)
```

---

## Part 6: Questions for AI Review

1. Are the re-entry criteria too conservative or too aggressive?
2. Should the `elapsed_pct < 0.40` threshold be different for different game types?
3. Is 75% position size right for re-entry, or should it vary by confidence?
4. Should we require a minimum price drop (like scouted re-entry's 15%)?
5. Are there profit-maximizing strategies we're missing beyond re-entry?
6. Should the graduated SL be even tighter for re-entry positions (they already proved vulnerable)?
7. Any conflicts between the proposed re-entry and existing match-aware exit layers?
