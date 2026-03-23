# Match-Aware Exit System — Design Spec v2

**Date:** 2026-03-22
**Status:** Approved — reviewed by Gemini, Perplexity, Claude Opus. Feedback integrated.
**v2 Errata (2026-03-23):** BUY_NO direction bugs found during v2 spec review — all price comparisons use raw YES prices, breaking Layers 1-4 for BUY_NO. Fixes documented in v2 spec section 9. Additional fixes: 80% force-exit gap, flat SL override, momentum guard loophole.
**Scope:** Replace flat stop-loss with a multi-layered exit system that uses match timing, price trajectory, profit history, and live score data to make smarter exit decisions.

---

## Problem Statement

The bot's biggest losses come from positions held to resolution that go to -99%. The current exit system uses a flat stop-loss (-40% for normal, -50% for esports) that does not account for match progress, whether the position ever saw profit, or how the match is going. This leads to two failure modes:

1. **Hold-to-resolve disaster**: Position gradually drops (-10%, -20%, -30%) but stays above stop-loss threshold. Match resolves, position goes to -99%. Example: xCrew match resolved in 20 minutes, price went from 41.5¢ to 0.
2. **Premature exit**: Stop-loss triggers on a temporary dip during a match that the team could still win. The position recovers after we exit.

---

## Current Exit Mechanisms (as-is)

These are the existing rules in `src/portfolio.py` and `src/main.py` that this design will modify or extend:

### 1. Stop Loss (`check_stop_losses()`)
- **Normal positions**: -40% of entry price
- **Esports**: -50% (BO5 gets extra +10% = -60%)
- **Volatility Swing**: -50%
- **Ultra-low entry (<9¢)**: No stop-loss (bet size IS the risk)
- **Low entry (9-20¢)**: Graduated 60%→40%
- **Medium_low confidence (B-)**: Tighter -30%
- **O/U and spread markets**: Exempt (hold to resolution)

### 2. Trailing Stop (`check_trailing_stops()`)
- Graduated tiers: peak 35%+ → 50% drop, peak 50%+ → 35% drop, peak 75%+ → 25% drop
- **Favorite exemption**: AI ≥65% for our side + high/medium_high confidence → skip trailing stop entirely (hold to resolve)
- **In-loss protection**: If position is currently in loss (negative PnL), trailing stop does NOT trigger — defers to stop_loss instead
- Only triggers when position is still in profit

### 3. Take Profit (`check_take_profits()`)
- **Favorite (AI ≥65%, high/med_high conf)**: Hold to resolve, only emergency exit on >50% gain ("spike exit")
- **Underdog/edge trade**: Exit at 85% of AI target price (if also >10% profit)
- **Confidence-based TP**: low/med_low=40%, med_high=80%, high=140%
- **VS positions**: Dynamic TP based on entry price (cheap=high TP, expensive=low TP)

### 4. Esports Halftime Exit (`check_esports_halftime_exits()`)
- BO3: After 62 minutes, if losing → exit
- BO5: After 87 minutes, if losing → exit
- If in profit → exempt (let it ride)
- **REPLACED BY**: Layer 2 + Layer 3 (graduated stop loss + never-in-profit guard)
- **CLEANUP:** This function is dead code in `portfolio.py` — should be removed.

### 5. Pre-Match Exit (`check_pre_match_exits()`)
- 30 minutes before end_date, exit non-high-confidence positions
- High/med_high confidence exempt (hold to resolve)
- **REPLACED BY**: Layer 2 (graduated stop loss covers this more intelligently)
- **CLEANUP:** This function is dead code in `portfolio.py` — should be removed.

### 6. VS Mandatory Exit (`check_volatility_swing_exits()`)
- 15 minutes before resolution → mandatory exit for all VS positions
- **UNCHANGED** — VS positions have their own exit system

### 7. Scouted Hold-to-Resolve Guard (in `main.py`)
- Scouted positions require B+ (medium_high) or higher confidence AND >60% AI certainty
- If not met → `is_scouted = False` (downgraded to normal position)
- **UNCHANGED at entry** — but Layer 4 now adds in-match revocation + restore

---

## Available Data Points

These fields are already populated on each Position object and can be used by the new exit system:

| Field | Source | Description |
|---|---|---|
| `entry_price` | Entry time | Price we paid |
| `current_price` | Gamma API (slug query) | Current market price |
| `unrealized_pnl_pct` | Calculated | Current profit/loss as percentage |
| `peak_pnl_pct` | Updated each cycle | Highest profit % ever seen for this position |
| `match_start_iso` | Gamma API event.startDate | When the match starts/started |
| `match_live` | Gamma API event.live | Whether match is currently live |
| `match_ended` | Gamma API event.ended | Whether match has ended |
| `match_score` | Gamma API event.score | Current score (e.g. "2-1\|Bo3") |
| `match_period` | Gamma API event.period | Current period (e.g. "2/3") |
| `number_of_games` | PandaScore / slug parsing | BO format (1, 3, 5, or 0=unknown) |
| `confidence` | AI analysis | Confidence level (low, medium_low, medium_high, high) |
| `ai_probability` | AI analysis | AI's predicted probability |
| `scouted` | Entry logic | Whether this was a pre-game scouted entry |
| `volatility_swing` | Entry logic | Whether this is a VS (underdog spike) position |
| `live_on_clob` | Gamma API | Whether the market is actively trading |
| `category` | Market metadata | "esports", "sports", etc. |
| `entry_timestamp` | Entry time | When we entered the position |
| `end_date_iso` | Market metadata | Market resolution deadline |
| `pending_resolution` | Price check | True when price ≥0.95 or ≤0.05 |

### Derived Values (to be calculated in the new system)

| Value | Formula | Description |
|---|---|---|
| `elapsed_pct` | `(now - match_start) / estimated_duration` | How far through the match we are (0.0 to 1.0+) |
| `estimated_duration` | Game-specific lookup table (see below) | Sport and game-specific match duration estimate |
| `ever_in_profit` | `peak_pnl_pct > 0.01` | Whether the position ever saw meaningful profit (>1%) |
| `price_vs_entry_ratio` | `current_price / entry_price` | How current price compares to entry (0.5 = halved) |
| `effective_ai_price` | Direction-adjusted AI probability | AI's predicted fair price for our side |
| `score_info` | Parsed from `match_score` | Structured score data (our_maps, opp_maps, map_diff, is_already_lost, etc.) |

---

## New System: 4-Layer Match-Aware Exit + Score Integration

The new system adds 4 layers that work together. Each layer is checked every cycle. **First matching layer wins** — if Catastrophic Floor triggers, nothing else matters. **Score data adjusts thresholds across all layers.**

### Score Integration (applies to all layers)

`match_score` is parsed every cycle into structured data. Score adjusts thresholds in Layer 2, decisions in Layer 3, and revocation in Layer 4.

**Score parsing:**
```
Input: "2-1|Bo3"  →  our_maps=2, opp_maps=1, map_diff=+1, format=3
Input: "0-2|Bo3"  →  our_maps=0, opp_maps=2, map_diff=-2, is_already_lost=True
Input: "1-0"      →  our_maps=1, opp_maps=0, map_diff=+1
Input: ""          →  available=False (no score data)
```

**NOTE:** "Our side" is determined by the bet direction. If we bet BUY_YES on Team A, then the first score number is Team A's. If we bet BUY_NO, the first score number is the opponent's (we want them to lose). The score parsing must be direction-aware.

**Score adjustments:**
| Score State | Effect on Thresholds |
|---|---|
| Ahead (map_diff > 0) | Loosen graduated stop loss by 25% (more room for dips) |
| Behind (map_diff < 0) | Tighten graduated stop loss by 25% (less patience) |
| Even (map_diff == 0) | No adjustment |
| Already lost (e.g. 0-2 in BO3) | Immediate exit regardless of other layers |
| Already won (e.g. 2-0 in BO3) | Hold to resolve, disable all stop losses |
| Score unavailable | No adjustment, use base thresholds |

### Layer 1: Catastrophic Floor (always active, highest priority)

**Rule:** If `current_price < entry_price * 0.50` → **immediate exit**.

> **⚠ BUY_NO ERRATA:** All price comparisons must use effective prices (direction-adjusted). For BUY_NO: `effective_price = 1 - YES_price`. Without this, Layer 1 never triggers for BUY_NO positions because rising YES price (bad for us) doesn't satisfy `current < entry * 0.50`. Fix: `effective_entry = entry_price if BUY_YES else (1 - entry_price)`, same for current. See v2 spec section 9b-9f for all fixes.

**Underdog exemption (from Gemini review):** If `entry_price < 0.25` (underdog position), Layer 1 is **disabled**. Rationale: a 20¢ underdog dropping to 12¢ is normal volatility, not catastrophic. These positions are protected by bet size (small Kelly allocation) and Layer 2's entry-price-adjusted tiers instead.

**Score override:** If score data shows `is_already_lost=True` → exit immediately even if price hasn't hit catastrophic floor.

**Rationale:** If the price has halved from our entry, the market is saying our side is in serious trouble. No match progress, no "wait and see" — this is a hard floor.

**Examples:**
- Entry 70¢, now 34¢ → EXIT (favori takım underdog olmuş)
- Entry 55¢, now 27¢ → EXIT
- Entry 20¢, now 12¢ → **NO EXIT** (underdog exemption, Layer 2 handles)
- Entry 30¢, now 14¢ → EXIT (above 25¢ threshold, catastrophic applies)

**Why entry×50% and not a fixed threshold?**
- A fixed threshold (e.g. "below 30¢") would wrongly exit a 31¢→29¢ underdog position (normal fluctuation)
- The 50% ratio means the same rule works for favorites (70¢→35¢) and mid-range (50¢→25¢)
- 50% represents a fundamental regime change: the market no longer believes what it believed when we entered

### Layer 2: Progress-Based Graduated Stop Loss (Entry-Price-Adjusted)

**Applies to:** All positions where match has started (`match_start_iso` exists and `elapsed_pct > 0`).

**Replaces:** The flat -40%/-50% stop loss for positions where match timing is available.

**Key change from v1 (from Opus review):** Stop loss tiers are no longer flat percentages. They are **adjusted by entry price** — low entry (underdog) gets wider tolerance, high entry (favorite) gets tighter tolerance. This prevents killing underdog positions on normal volatility while catching favorite losses earlier.

**Base tiers (before adjustment):**

| Match Progress (`elapsed_pct`) | Base Max Loss |
|---|---|
| Pre-match (elapsed < 0) | -40% |
| 0% – 40% (early match) | -40% |
| 40% – 65% (mid match) | -30% |
| 65% – 85% (late match) | -20% |
| 85% – 100% (final phase) | -15% |
| >100% (overtime / should have ended) | -5% |

**NOTE:** Final phase is -15% (not -10% as in v1). Changed based on Gemini review: "desperation variance" in the last phase of matches causes wild price swings (tactical fouls in basketball, all-in plays in esports, stoppage time goals in football). -10% would cause too many false exits. -15% gives enough room for legitimate last-minute volatility while still protecting against real losses.

**Entry-price multiplier (from Opus review):**

> **⚠ BUY_NO ERRATA:** Entry price ranges below refer to **effective entry price** (direction-adjusted). A BUY_NO at YES=70¢ has effective_entry=30¢ → underdog multiplier (1.25), NOT favorite (0.70). See v2 spec section 9d.

| Effective Entry Price Range | Multiplier | Effect | Rationale |
|---|---|---|---|
| <20¢ (heavy underdog) | 1.50 | Base×1.5 → wider tolerance | High natural volatility, bet size is the risk |
| 20-35¢ (underdog) | 1.25 | Base×1.25 → somewhat wider | Moderate volatility expected |
| 35-50¢ (coin flip) | 1.00 | No adjustment | Base tiers as-is |
| 50-70¢ (favorite) | 0.85 | Base×0.85 → tighter | Drops are more significant signals |
| >70¢ (heavy favorite) | 0.70 | Base×0.70 → much tighter | Any drop is a strong negative signal |

**Score adjustment (applied AFTER entry-price multiplier):**
- Score ahead (map_diff > 0): multiply final tolerance by 1.25 (loosen)
- Score behind (map_diff < 0): multiply final tolerance by 0.75 (tighten)
- Score even or unavailable: no change

**Resulting max loss = base_tier × entry_price_multiplier × score_adjustment**

**Example calculations:**

| Entry | Progress | Base | ×Price Mult | ×Score Adj | Final Max Loss | Exit Price |
|---|---|---|---|---|---|---|
| 15¢ underdog | 40-65% | -30% | ×1.50=-45% | even: ×1.0 | -45% | 8.25¢ |
| 15¢ underdog | 40-65% | -30% | ×1.50=-45% | behind: ×0.75 | -33.75% | 9.94¢ |
| 50¢ coin flip | 40-65% | -30% | ×1.00=-30% | even: ×1.0 | -30% | 35¢ |
| 70¢ favorite | 40-65% | -30% | ×0.85=-25.5% | even: ×1.0 | -25.5% | 52.15¢ |
| 70¢ favorite | 65-85% | -20% | ×0.85=-17% | behind: ×0.75 | -12.75% | 61.08¢ |
| 85¢ premium | 40-65% | -30% | ×0.70=-21% | ahead: ×1.25 | -26.25% | 62.69¢ |

**Hard limits:** Final max loss is clamped to range [5%, 70%] (as a positive number). Exit triggers when `unrealized_pnl_pct < -max_loss`. Never wider than 70% (even underdog), never tighter than 5% (overtime). Implementation: `max(0.05, min(0.70, result))`.

**Game-specific estimated duration (from Opus review):**

| Game | BO1 | BO3 | BO5 | Notes |
|---|---|---|---|---|
| CS2 | 40 min | 130 min | 200 min | Overtime possible in BO1 |
| Valorant | 50 min | 140 min | 220 min | Longer maps than CS2 |
| League of Legends | 35 min | 100 min | 160 min | Faster resolution |
| Dota 2 | 45 min | 130 min | 210 min | Games can run long |
| Generic esports | 40 min | 120 min | 180 min | Fallback for unknown game |
| Football/Soccer | 95 min | — | — | 90 min + stoppage |
| Basketball (NBA) | 150 min | — | — | 48 min game + stoppages |
| College Basketball | 120 min | — | — | 40 min game + stoppages |
| Baseball (MLB) | 180 min | — | — | 9 innings, variable |
| Hockey (NHL) | 150 min | — | — | 60 min game + stoppages |
| Tennis | 120 min | — | — | Highly variable |
| Unknown/Other | 90 min | — | — | Conservative default |

**Game detection from slug:**
```
slug contains "cs2-" → CS2
slug contains "val-" → Valorant
slug contains "lol-" → League of Legends
slug contains "dota2-" → Dota 2
slug contains "epl-", "laliga-", "ucl-" → Football
slug contains "nba-" → Basketball (NBA)
slug contains "cbb-" → College Basketball
slug contains "mlb-" → Baseball
slug contains "nhl-" → Hockey
otherwise → Unknown/Other
```

**How `elapsed_pct` is calculated:**
```
match_start = parse(pos.match_start_iso)
elapsed_minutes = (now - match_start).total_seconds() / 60
estimated_duration = get_game_specific_duration(pos.slug, pos.number_of_games)
elapsed_pct = elapsed_minutes / estimated_duration
```

**If `match_start_iso` is not available:** Fall back to the current flat stop loss (-40%/-50%). Do NOT guess match start.

**Interaction with existing stop loss rules:**
- This REPLACES the flat stop loss for positions with match timing data
- Ultra-low entry (<9¢) exemption still applies (no stop loss at all)
- O/U and spread market exemption still applies (hold to resolution)
- VS positions still use their own stop loss (-50%)

> **⚠ FLAT SL OVERRIDE BUG:** In `portfolio.py`, the legacy flat SL (`check_stop_losses()`) runs AFTER `check_match_aware_exits()`. If match-aware exits don't trigger (e.g., graduated SL gives an underdog a wider -45% tolerance), but the flat SL is -40%, the flat SL triggers first and overrides the graduated system's intent. Fix: when `check_match_exit()` returns a result (even non-exit), skip flat SL for that position. Implemented in v2.

### Layer 3: Never-in-Profit Guard (Relative Thresholds)

**Applies to:** Positions where `peak_pnl_pct <= 0.01` (never saw meaningful profit) AND match has started.

**Rationale:** If the AI predicted our side would win but the market NEVER agreed (price never went above entry even briefly), the AI was likely wrong. However, we don't exit immediately — we give the match time to develop, because fans and bettors who are watching the match are pricing performance in real-time. Their collective judgment needs time to form.

**Key change from v1 (from Gemini + Perplexity review):** Thresholds are **relative to entry price**, not fixed at 65¢/55¢. Fixed thresholds are wrong for underdog positions (a 35¢ entry at 25¢ is not the same as a 70¢ entry at 55¢).

**Rule:**

1. **Before 70% match progress:** Do nothing extra. The match is still open. Let the graduated stop loss (Layer 2) handle extreme drops.

2. **At 70% match progress:** Check current price RELATIVE TO ENTRY:
   - If `current_price > entry_price × 0.90` → **STAY**. Price is within 10% of entry. We're on the right side, just entered at a bad price. The team will likely win. (Liverpool scenario: entered 70¢, now 66¢ → 66/70 = 0.94 > 0.90 → STAY)
   - If `current_price < entry_price × 0.75` → **EXIT**. Price dropped more than 25% from entry and we never saw profit — AI was wrong. (xCrew scenario: entered 70¢, now 50¢ → 50/70 = 0.71 < 0.75 → EXIT)
   - If `current_price` is between entry×0.75 and entry×0.90 → **Layer 2 decides**. The graduated stop loss thresholds apply normally.

3. **Score override at 70%+:**
   - If score shows we're ahead (map_diff > 0) → **STAY** regardless of price. We're winning the match even if price dipped.
   - If score shows we're behind AND price < entry×0.75 → **EXIT** immediately.

4. **At 80% match progress:** If never-in-profit AND price < entry×0.75 AND score is not ahead → **force exit**. Must be out by 80%.

> **⚠ BUY_NO ERRATA:** All `current_price` vs `entry_price` comparisons in Layer 3 must use effective prices. See v2 spec section 9e.

> **⚠ IMPLEMENTATION GAP:** The 80% force-exit (point 4) is NOT explicitly implemented in `match_exit.py`. Layer 3 at line 281 checks `elapsed_pct >= 0.70` but does not differentiate 70% vs 80%. In practice, Layer 2's tighter graduated SL at 85%+ (-15%) usually catches these positions, but the explicit 80% force-exit should be added. Fix in v2 spec: add `if elapsed_pct >= 0.80 and not ever_in_profit and effective_current < effective_entry * 0.75 and not score_ahead: EXIT`.

**Why relative thresholds?**
- Entry 70¢, now 63¢ → 63/70 = 0.90 → STAY (within 10%, normal variance)
- Entry 35¢ underdog, now 25¢ → 25/35 = 0.71 → EXIT (dropped 29%, AI was wrong)
- Entry 35¢ underdog, now 32¢ → 32/35 = 0.91 → STAY (still close to entry)
- The same logic works for all price levels without hardcoded 65¢/55¢ breakpoints

**Why 70% and not earlier?**
- At 50% match progress, a team at 50¢ has genuine comeback potential
- Esports: 0-1 down in BO3 at halftime → 50% of matches still winnable
- Football: 0-1 down at 60th minute → goals in 60-90 range are common
- By 70%, enough match data exists for the market to have a reliable opinion
- By 80%, exit should be complete

### Layer 4: Hold-to-Resolve Decision Matrix (with Restore)

**Applies to:** Positions that are candidates for holding to resolution (scouted, high confidence, favorites).

**Current rule (unchanged at entry):** Scouted positions require B+ (medium_high) or higher confidence AND >60% AI certainty. If not met, `is_scouted = False`.

**New: In-match revocation — Hold-to-resolve should be REVOKED during the match if conditions deteriorate:**

| Saw Profit? | Current Price | Match Progress | Score | Decision |
|---|---|---|---|---|
| Yes, still in profit | Above entry | Any | Any | **HOLD TO RESOLVE** — everything is going right |
| Yes, saw profit 1-2 times | Near entry (±10%) | <80% | Even or ahead | **HOLD** — dip is likely panic, team showed strength earlier |
| Yes, saw profit but now significant loss | Below entry×70% | >60% | Behind or even | **REVOKE** — profit window closed, apply trailing stop |
| Yes, saw profit but now catastrophic | Below entry×50% | Any | Any | **EXIT via Layer 1** — catastrophic floor overrides |
| No, never in profit | Above entry×90% | Any | Ahead | **HOLD** — right side, score confirms |
| No, never in profit | Above entry×90% | Any | Even/behind | **HOLD** — still close to entry, give time |
| No, never in profit | entry×75% to entry×90% | <70% | Any | **WAIT** — let match develop, Layer 2 guards |
| No, never in profit | Below entry×75% | >70% | Not ahead | **REVOKE + EXIT** — AI was wrong |
| No, never in profit | Below entry×50% | Any | Any | **EXIT via Layer 1** — catastrophic floor |

**New: Hold-to-resolve RESTORE (from Opus review)**

Currently, once hold-to-resolve is revoked it's permanent. This is wrong — if the position recovers, hold should be restored.

**Restore conditions (ALL must be true):**
1. Hold-to-resolve was revoked (not never-had-it)
2. At least 10 minutes have passed since revocation
3. `current_price > entry_price × 0.85` (price recovered to within 15% of entry)
4. Score is not behind (map_diff >= 0), OR score unavailable

**New Position fields for restore:**
```python
hold_revoked_at: datetime | None = None    # When hold-to-resolve was revoked
hold_was_original: bool = False            # Was this originally a hold-to-resolve position
```

When restored: `pos.scouted = pos.hold_was_original`, `pos.hold_revoked_at = None`. Log: "Hold-to-resolve RESTORED for {slug}: price recovered to {price}"

**Distinguishing panic dips from real trend changes:**
- **Panic dip:** Sharp drop (1-2 cycles) then stabilization. Score doesn't reflect the drop (e.g. 1-1 draw causes panic for the favorite side). Recovery likely.
- **Real trend change:** Sustained drop over 3+ cycles AND 5¢+ total drop (see Momentum section). Score confirms the other side is winning. No recovery expected.

> **⚠ BUY_NO ERRATA:** All price comparisons in Layer 4 (entry×0.70, entry×0.75, entry×0.85, entry×0.90) must use effective prices. See v2 spec section 9f.

> **⚠ MOMENTUM GUARD LOOPHOLE:** The `consecutive_down_cycles < 3 OR cumulative_drop < 0.05` check uses OR and resets on any uptick. A position slowly bleeding with intermittent 1¢ bounces (70¢→68¢→69¢→66¢→66.5¢→...) never builds 3 consecutive down cycles, so revocation is permanently blocked even if total loss reaches 25%+. The Layer 2 graduated SL usually catches this, but hold-to-resolve positions may survive to resolution loss. Fix in v2: Momentum Tightening v2 adds deeper tier (5+ cycles, 10¢+), and Layer 4 revocation now uses effective prices which correctly detect adverse moves.

---

## Momentum Alert (Enhanced)

**Original idea:** Exit if price drops sharply in 2 consecutive cycles.

**Problem identified during brainstorming:** In esports, a single map loss causes a sharp price drop that stabilizes. This is NOT a signal to exit — the team can win the next map. See Leosun vs S8UL chart: price dropped sharply mid-match then recovered completely.

**Key change from v1 (from Gemini review):** Added minimum delta requirement. In thin markets, 3 consecutive cycles of 1¢ drops could be microstructure noise (spread widening, small bot selling), not real momentum. Require both cycle count AND meaningful price drop.

**Revised rule:** Momentum is an ALERT, not an auto-exit:
- `consecutive_down_cycles >= 3` AND `total_drop >= 0.05` (5¢) → **tighten** graduated stop loss by 25% (e.g. if currently at -30% tolerance, move to -22.5%). Note: spec said "one tier" but implementation uses ×0.75 multiplier which is more granular. v2 adds deeper tier: 5+ cycles AND 10¢+ → ×0.60.
- Single sharp drop that stabilizes → do nothing, this is normal match volatility
- Implementation: count `consecutive_down_cycles` per position AND track `cumulative_drop` (entry_price at start of streak minus current_price). Reset both to 0 when price goes up.

**Why 5¢ minimum?** In a $500-$1000 liquidity pool, a $50 market sell can move price by 2-3¢. Three such random sells = 6-9¢ drop that looks like momentum but is just noise. 5¢ is a compromise — catches real moves, filters noise.

---

## BO1/BO3/BO5 Format Considerations

Match format affects everything because it determines how much "comeback potential" exists:

| Format | Typical Duration | Comeback Potential | Key Insight |
|---|---|---|---|
| **BO1** | 35-50 min | Very low — one map, if behind at 70% it's almost over | Entire graduated stop loss plays out in ~40 min. Fast decisions needed. |
| **BO3** | 100-140 min | Medium — can lose map 1 and win maps 2-3 (e.g. 0-1 → 2-1) | Most common format. Score data most valuable here. |
| **BO5** | 160-220 min | High — can lose 2 maps and still win 3 (e.g. 0-2 → 3-2) | Longest format. Patient graduation. Score extremely important. |

**The graduated stop loss handles format differences** because it uses `elapsed_pct`, not absolute time. A BO5 at 40% progress = ~72 minutes in (only 2 maps), while a BO1 at 40% = ~16 minutes in (already mid-map). The same tolerance at 40% progress means different things in different formats, which is correct.

**BO1 special consideration (CS2 example, 40 min estimate):**
- 0-16 min: -40% × price_mult tolerance (early)
- 16-26 min: -30% × price_mult tolerance (mid)
- 26-34 min: -20% × price_mult tolerance (late)
- 34-40 min: -15% × price_mult tolerance (final)
- This is aggressive but appropriate — BO1 has almost no comeback potential

**BO5 Dota 2 example (210 min estimate):**
- 0-84 min: -40% × price_mult tolerance (first 2 maps)
- 84-136 min: -30% × price_mult tolerance (maps 2-3)
- 136-178 min: -20% × price_mult tolerance (maps 3-4)
- 178-210 min: -15% × price_mult tolerance (map 5)
- Much more patient — appropriate for format with high comeback potential

---

## Price History Collection (Future Calibration)

**Goal:** Collect price movement data to calibrate thresholds over time.

**Implementation:**
1. When a position is closed (any exit reason), call CLOB API: `GET /prices-history?market={tokenID}&interval=max&fidelity=60`
2. Save response to `logs/price_history/{slug}.json` with metadata:
   ```json
   {
     "slug": "cs2-nrg-furia-2026-03-22",
     "entry_price": 0.55,
     "exit_price": 0.38,
     "exit_reason": "graduated_sl_mid",
     "exit_layer": "layer2",
     "match_start_iso": "2026-03-22T14:00:00Z",
     "match_end_iso": "2026-03-22T16:15:00Z",
     "game": "cs2",
     "format": 3,
     "entry_price_mult": 0.85,
     "score_at_exit": "0-1|Bo3",
     "ever_in_profit": false,
     "peak_pnl_pct": -0.02,
     "resolution_price": 0.0,
     "price_history": [{"t": 1711108800, "p": 0.55}, ...]
   }
   ```
3. Over time, analyze patterns:
   - "After a favorite drops 20%, what % recover?" → calibrate catastrophic floor
   - "After never-in-profit at 70% progress, what % of positions recover?" → calibrate the 70% threshold
   - "BO3 comeback rate after 0-1 down?" → validate format-specific assumptions
   - "What's the average price swing in esports last 15% of match?" → validate final phase tolerance

**Not blocking for v1:** Start with the fixed thresholds above, collect data, refine later.

---

## What This System Does NOT Change

- **O/U and spread markets**: Still exempt from all stop loss (hold to resolution)
- **Volatility Swing positions**: Still use their own exit system (VS stop loss, VS TP, mandatory pre-resolution exit)
- **Take profit logic**: Unchanged — confidence-based TP, edge TP at 85% AI target, favorite spike exit at >50%
- **Scouted re-entry logic**: Unchanged
- **Spike re-entry logic**: Unchanged
- **Entry logic**: Unchanged — edge thresholds, Kelly sizing, confidence filters all stay

---

## Implementation Notes

### New Position Fields Needed
```python
# Add to Position model in models.py
ever_in_profit: bool = False           # True once peak_pnl_pct > 0.01 (set during price update, never reset)
consecutive_down_cycles: int = 0       # Consecutive cycles where price dropped
cumulative_drop: float = 0.0           # Total price drop during current down streak (for momentum minimum delta)
previous_cycle_price: float = 0.0      # Price at last cycle (for momentum tracking)
hold_revoked_at: datetime | None = None  # When hold-to-resolve was revoked (for restore timer)
hold_was_original: bool = False          # Was this originally a hold-to-resolve position (for restore)
```

### New Method: `check_match_aware_exits()`
This will be a new method in `portfolio.py` that implements all 4 layers. It runs BEFORE the existing `check_stop_losses()` and `check_trailing_stops()`. If it triggers an exit, the other checks are skipped for that position.

### Helper Functions Needed
```python
def parse_match_score(score_str: str, number_of_games: int, direction: str) -> dict:
    """Parse match_score into structured data, direction-aware."""

def get_game_specific_duration(slug: str, number_of_games: int) -> int:
    """Return estimated match duration in minutes from game-specific lookup table."""

def get_entry_price_multiplier(entry_price: float) -> float:
    """Return stop loss multiplier based on entry price range."""

def get_graduated_max_loss(elapsed_pct: float, entry_price: float, score_info: dict) -> float:
    """Calculate final max loss: base_tier × price_mult × score_adj, clamped to [-70%, -5%]."""
```

### Priority Order (per cycle, per position)
1. **Score parse**: Parse match_score into score_info (used by all layers)
2. **Score terminal check**: If already_lost → EXIT immediately
3. **Score terminal check**: If already_won → HOLD, skip all exit checks
4. **Layer 1**: Catastrophic Floor (entry×50%, underdog <25¢ exempt) → if triggered, EXIT
5. **Layer 2**: Graduated Stop Loss (entry-price-adjusted, score-adjusted) → if triggered, EXIT
6. **Layer 3**: Never-in-Profit Guard (relative thresholds, score-aware) → if triggered, EXIT
7. **Layer 4**: Hold-to-Resolve check → may REVOKE or RESTORE hold status
8. **Momentum update**: Update consecutive_down_cycles and cumulative_drop
9. **Existing trailing stop** → if triggered, EXIT (for non-hold-to-resolve positions)
10. **Existing take profit** → if triggered, EXIT

### Fallback Behavior
- If `match_start_iso` is not available → use current flat stop loss (no graduated)
- If `number_of_games` is 0 (unknown format) → use 90 minutes as default duration
- If `elapsed_pct > 1.5` (match should have ended 50% ago) → likely stale data, mark pending
- If `match_score` is empty or unparseable → score_info.available = False, no score adjustment

---

## Success Criteria

1. **xCrew scenario prevented**: Entry at 70¢, price drops to 35¢ → Layer 1 exits at -50% instead of holding to -99%
2. **Liverpool scenario preserved**: Entry at 70¢ (AI 85%), price at 66¢ (entry×0.94), team winning → no exit, hold to resolve, profit at 100¢
3. **Panic dip survived**: Entry at 60¢, price spikes to 75¢ (profit), drops to 55¢ on a goal against, stabilizes → no exit, position recovers
4. **Never-in-profit caught**: Entry at 65¢, never profits, at 70% match progress price is 48¢ (entry×0.74 < ×0.75) → EXIT
5. **BO1 fast exit**: Entry in BO1, at 70% progress (28 min) with -25% loss → graduated stop loss triggers exit
6. **Underdog protection**: Entry at 20¢, drops to 12¢ → no catastrophic (underdog exempt), graduated stop loss with 1.5x multiplier handles normally (tolerance = -45% at mid-match)
7. **Score-aware exit**: BO3 score 0-2 → immediate exit regardless of price
8. **Score-aware hold**: BO3 score 1-0, never in profit, price at entry×0.88 → STAY (score ahead overrides)
9. **Hold-to-resolve restore**: Revoked at 55¢, price recovers to 62¢ (entry×0.89) after 10 min, score 1-1 → RESTORE hold status
10. **Favorite early catch**: Entry at 75¢ (favorite), price at 58¢ at mid-match → adjusted max loss = -30%×0.70 = -21%, 58¢ = -22.7% → EXIT (caught earlier than flat -40%)

---

## Interaction Summary Table

For any AI implementing this: here is the complete decision matrix showing how all layers interact:

```
FOR EACH POSITION, EACH CYCLE:

0. PARSE SCORE + DIRECTION
   Parse match_score → score_info {available, our_maps, opp_maps, map_diff, is_already_lost, is_already_won}
   Direction-aware: adjust "our" side based on BUY_YES vs BUY_NO
   ⚠ Compute effective prices: effective_entry = entry_price if BUY_YES else (1 - entry_price)
                                effective_current = current_price if BUY_YES else (1 - current_price)
   ALL subsequent price comparisons use effective_entry/effective_current, NOT raw prices.

0a. SCORE TERMINAL CHECKS
   Is is_already_lost? → FULL EXIT immediately (match is over, we lost)
   Is is_already_won? → HOLD to resolve (match is over, we won, wait for 100¢)

1. CATASTROPHIC FLOOR (Layer 1)
   Is effective_entry >= 0.25? (not underdog-exempt)
   → YES: Is effective_current < effective_entry × 0.50?
     → YES: FULL EXIT immediately
     → NO: Continue
   → NO (underdog <25¢): Skip Layer 1, continue to Layer 2

2. MATCH TIMING CHECK
   Is match_start_iso available AND match started (elapsed > 0)?
   → NO: Use existing flat stop loss (-40%/-50%). Skip to step 5.
   → YES: Calculate elapsed_pct using game-specific duration. Continue.

3. GRADUATED STOP LOSS (Layer 2)
   base_max_loss = tier_lookup(elapsed_pct)                    # -40%, -30%, -20%, -15%, or -5%
   price_mult = get_entry_price_multiplier(effective_entry)    # 1.50, 1.25, 1.00, 0.85, or 0.70
   score_adj = 1.25 if score_ahead, 0.75 if score_behind, 1.0 otherwise
   final_max_loss = clamp(base × price_mult × score_adj, 0.05, 0.70)  # positive value, e.g. 0.30

   Is unrealized_pnl_pct < -final_max_loss?  # e.g. pnl < -0.30
   → YES: EXIT (Layer 2: Graduated Stop Loss)
   → NO: Continue

4. NEVER-IN-PROFIT GUARD (Layer 3)
   Is peak_pnl_pct <= 0.01 AND elapsed_pct >= 0.70?
   → NO: Skip (either saw profit or too early)
   → YES:
     Score ahead (map_diff > 0)? → STAY (winning despite no profit)
     effective_current >= effective_entry × 0.90? → STAY (close to entry, right side)
     effective_current < effective_entry × 0.75? → EXIT (dropped >25% + never profited + 70%+ done)
     Between 0.75 and 0.90? → Layer 2 graduated stop loss handles

   At 80%+: If still here AND effective_current < effective_entry×0.75 AND score not ahead → FORCE EXIT

5. HOLD-TO-RESOLVE CHECK (Layer 4)
   Is position scouted or favorite (AI≥65%, high/med_high conf)?
   → NO: Skip (normal position, existing trailing/TP apply)
   → YES: Check revocation conditions:
     - ever_in_profit=True AND effective_current > effective_entry×0.70 → KEEP hold
     - ever_in_profit=True AND effective_current < effective_entry×0.70 AND elapsed>60% AND score not ahead → REVOKE
     - ever_in_profit=False AND effective_current > effective_entry×0.90 → KEEP hold
     - ever_in_profit=False AND effective_current < effective_entry×0.75 AND elapsed>70% AND score not ahead → REVOKE + EXIT
     - consecutive_down_cycles < 3 OR cumulative_drop < 0.05 → KEEP (dip is temporary)

   Check restore conditions (if previously revoked):
     - hold_revoked_at exists AND 10+ min passed AND effective_current > effective_entry×0.85 AND score not behind → RESTORE

6. MOMENTUM UPDATE
   Did price drop this cycle vs previous_cycle_price?
   → YES: consecutive_down_cycles += 1, cumulative_drop += (previous_price - current_price)
     Is consecutive_down_cycles >= 3 AND cumulative_drop >= 0.05?
     → YES: Tighten graduated stop loss by one tier for next cycle
   → NO: consecutive_down_cycles = 0, cumulative_drop = 0.0

   Update: previous_cycle_price = current_price
   Update: if peak_pnl_pct > 0.01 → ever_in_profit = True

7. EXISTING CHECKS (unchanged):
   - Trailing stop (for non-hold-to-resolve positions)
   - Take profit
   - VS mandatory exit
```

---

## Appendix: Changes from v1 to v2

| Area | v1 (Original Spec) | v2 (After Review) | Source |
|---|---|---|---|
| Layer 1 | entry×50% no exceptions | entry×50% but underdog <25¢ exempt | Gemini |
| Layer 2 tiers | Flat percentages for all entries | Entry-price-adjusted multipliers (0.70-1.50) | Opus |
| Layer 2 final phase | -10% tolerance | -15% tolerance (desperation variance) | Gemini |
| Layer 2 duration | Generic sport durations | Game-specific (CS2/Val/LoL/Dota2 × BO format) | Opus |
| Layer 3 thresholds | Fixed 65¢/55¢ | Relative entry×0.90/entry×0.75 | Gemini + Perplexity |
| Layer 3 score | No score awareness | Score ahead → STAY, score behind → faster exit | Opus |
| Layer 4 | Revocation only (permanent) | Revocation + Restore (reversible after 10min recovery) | Opus |
| Momentum | 3 consecutive cycles → tighten | 3 consecutive cycles + 5¢ minimum delta → tighten | Gemini |
| Score integration | Listed as data but unused | Used in all 4 layers + terminal checks | All 3 reviewers |
