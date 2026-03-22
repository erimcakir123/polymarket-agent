# Profit Maximization & Risk Optimization v2 — Design Spec

> **Builds on:** Match-Aware Exit System v1 (2026-03-22)
> **Scope:** 18 actions across exit optimization, re-entry system, and portfolio risk management
> **Principle:** Maximize expected value, minimize drawdown, never break v1

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Phase 1: Risk Foundation](#2-phase-1-risk-foundation)
3. [Phase 2: Re-Entry Foundation](#3-phase-2-re-entry-foundation)
4. [Phase 3: Exit System Overhaul](#4-phase-3-exit-system-overhaul)
5. [Phase 4: Re-Entry Extensions](#5-phase-4-re-entry-extensions)
6. [Phase 5: Advanced Features](#6-phase-5-advanced-features)
7. [Conflict Resolutions](#7-conflict-resolutions)
8. [Position Model Changes](#8-position-model-changes)
9. [v1 BUY_NO Direction Fixes in match_exit.py](#9-v1-buy_no-direction-fixes-in-match_exitpy)
10. [File Structure](#10-file-structure)
11. [Testing Strategy](#11-testing-strategy)

---

## 1. Architecture Overview

### What v1 Solved (Don't Touch)
- 4-layer match-aware exit (score terminal, catastrophic floor, graduated SL, never-in-profit, hold-to-resolve)
- Legacy flat exit (SL/TP/trailing) as safety net
- Spike re-entry and Scouted re-entry mechanisms
- Position model with 15+ tracking fields
- Price history collection on exit

### What v2 Adds

```
v2 LAYER CAKE (bottom = highest priority)
═══════════════════════════════════════════

PORTFOLIO LEVEL (new)
├── Circuit Breaker (#14) — daily/hourly loss limits, halt new entries
├── Adaptive Kelly (#15) — confidence-based position sizing
├── Correlation-Aware Exposure (#17) — net match exposure tracking
└── Liquidity Check (#18) — order book depth before exit

POSITION EXIT (enhanced)
├── Scale Out (#1) — 3-tier partial exit
├── Resolution-Aware TP (#2) — hold final tier for 100¢
├── σ-based Trailing Stop (#3) — volatility-adjusted trailing
├── Edge Decay (#4) — AI signal freshness degradation
├── VS Spike Detection (#5) — velocity-based spike exit
└── Momentum Tightening v2 (#16) — deeper tightening tier

POSITION ENTRY (new)
├── Re-entry Params Fix (#6) — dynamic thresholds
├── Scale-In (#7) — gradual entry (50% + 50%)
├── Tiered Blacklist (#8) — exit-reason-based durations
├── Layer 3 Grace Period (#9) — re-entry immunity
├── Re-entry Catastrophic Floor (#10) — tighter floor
├── Snowball Ban (#11) — MOBA re-entry block
├── AI Confidence Momentum (#12) — rising confidence filter
└── Score Reversal Exception (#13) — blacklist override
```

### Implementation Order & Dependencies

```
PHASE 1 — RISK FOUNDATION (no dependencies, protect capital first)
  #14 Circuit Breaker
  #15 Adaptive Kelly
  #16 Momentum Tightening v2
  #18 Liquidity Check

PHASE 2 — RE-ENTRY FOUNDATION (fix broken re-entry before building on it)
  #6 Re-entry Params Fix
  #10 Re-entry Catastrophic Floor
  #8 Tiered Blacklist
  #4 Edge Decay

PHASE 3 — EXIT OVERHAUL (biggest structural change)
  #1 Scale Out
  #2 Resolution-Aware TP
  #3 σ-based Trailing Stop

PHASE 4 — RE-ENTRY EXTENSIONS (build on Phase 2 foundation)
  #11 Snowball Ban
  #12 AI Confidence Momentum
  #9 Layer 3 Grace Period
  #13 Score Reversal Exception

PHASE 5 — ADVANCED (highest complexity, most interactions)
  #7 Scale-In
  #5 VS Spike Detection
  #17 Correlation-Aware Exposure
```

---

## 2. Phase 1: Risk Foundation

### #14 Circuit Breaker

**Purpose:** Portfolio-level loss limit. Halts new entries when daily or hourly losses exceed thresholds. Prevents catastrophic days from compounding.

**Constants:**
```python
DAILY_MAX_LOSS_PCT = -0.08      # -8% of portfolio value
HOURLY_MAX_LOSS_PCT = -0.05     # -5% of portfolio value
CONSECUTIVE_LOSS_LIMIT = 4       # 4 back-to-back SL hits → halt
COOLDOWN_AFTER_DAILY = 120       # minutes to wait after daily limit hit
COOLDOWN_AFTER_HOURLY = 60       # minutes to wait after hourly limit hit
COOLDOWN_AFTER_CONSECUTIVE = 60  # minutes after consecutive losses
ENTRY_BLOCK_THRESHOLD = -0.03   # soft block at -3% daily (fires before hourly -5% hard limit)
```

**Logic:**
```python
class CircuitBreaker:
    def __init__(self):
        self.daily_realized_pnl_pct = 0.0
        self.hourly_realized_pnl_pct = 0.0
        self.consecutive_losses = 0
        self.breaker_active_until: datetime | None = None
        self.last_daily_reset: datetime = now_utc()
        self.last_hourly_reset: datetime = now_utc()

    def record_exit(self, pnl_usd: float, portfolio_value: float):
        pnl_pct = pnl_usd / portfolio_value if portfolio_value > 0 else 0
        self.daily_realized_pnl_pct += pnl_pct
        self.hourly_realized_pnl_pct += pnl_pct
        if pnl_usd < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def reset_if_needed(self):
        now = now_utc()
        if (now - self.last_daily_reset).total_seconds() >= 86400:
            self.daily_realized_pnl_pct = 0.0
            self.last_daily_reset = now
        if (now - self.last_hourly_reset).total_seconds() >= 3600:
            self.hourly_realized_pnl_pct = 0.0
            self.last_hourly_reset = now

    def should_halt_entries(self) -> tuple[bool, str]:
        """Returns (halt, reason). Never halts exits."""
        self.reset_if_needed()

        if self.breaker_active_until and now_utc() < self.breaker_active_until:
            remaining = (self.breaker_active_until - now_utc()).seconds // 60
            return True, f"Circuit breaker cooldown ({remaining}min remaining)"

        if self.daily_realized_pnl_pct <= DAILY_MAX_LOSS_PCT:
            self.breaker_active_until = now_utc() + timedelta(minutes=COOLDOWN_AFTER_DAILY)
            return True, f"Daily loss {self.daily_realized_pnl_pct:.1%} hit {DAILY_MAX_LOSS_PCT:.0%} limit"

        if self.hourly_realized_pnl_pct <= HOURLY_MAX_LOSS_PCT:
            self.breaker_active_until = now_utc() + timedelta(minutes=COOLDOWN_AFTER_HOURLY)
            return True, f"Hourly loss {self.hourly_realized_pnl_pct:.1%} hit {HOURLY_MAX_LOSS_PCT:.0%} limit"

        if self.consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
            self.breaker_active_until = now_utc() + timedelta(minutes=COOLDOWN_AFTER_CONSECUTIVE)
            self.consecutive_losses = 0
            return True, f"{CONSECUTIVE_LOSS_LIMIT} consecutive losses"

        # Soft block: nearing daily limit
        if self.daily_realized_pnl_pct <= ENTRY_BLOCK_THRESHOLD:
            return True, f"Daily loss {self.daily_realized_pnl_pct:.1%} exceeded soft limit {ENTRY_BLOCK_THRESHOLD:.0%}, new entries blocked"

        return False, ""
```

**Integration points:**
- Called in main loop BEFORE any entry logic (AI analysis, scouted entry, re-entry)
- `record_exit()` called from `_exit_position()` after realized PnL is calculated
- NEVER blocks exits — only entry decisions
- Circuit breaker state persisted to `logs/circuit_breaker_state.json` for restart recovery. Fields saved: `daily_realized_pnl_pct`, `hourly_realized_pnl_pct`, `consecutive_losses`, `breaker_active_until`, `last_daily_reset`, `last_hourly_reset`
- Telegram notification when breaker activates/deactivates

**Critical rule:** Resolution-hold positions (#2) are NEVER force-exited by circuit breaker.

**Note on daily limit re-trigger:** Once daily loss hits -8%, the cooldown (120min) expires but `daily_realized_pnl_pct` is NOT reset until 24h. This means the breaker will immediately re-trigger, effectively halting entries for the rest of the day. This is intended behavior — a -8% day should stop all new entries. The cooldown mechanism is mainly for the hourly and consecutive-loss triggers which reset more frequently.

---

### #15 Adaptive Kelly

**Purpose:** Enhance the existing `kelly_by_confidence` system with AI probability bonus, esports discount, and re-entry discount.

**Existing system in config.py:**
```python
# Already exists — DO NOT duplicate:
kelly_fraction: float = 0.25                    # Default
kelly_by_confidence: Dict[str, float] = {
    "high": 0.25, "medium_high": 0.20, "medium_low": 0.12, "low": 0.08
}
```

**Enhancement:** Wrap existing config with adaptive adjustments:
```python
def get_adaptive_kelly_fraction(
    confidence: str,
    ai_probability: float,
    category: str,
    is_reentry: bool = False,
    config_kelly_by_conf: dict = None,  # Pass config.risk.kelly_by_confidence
) -> float:
    # Use existing config as base (DO NOT override with hardcoded values)
    base = (config_kelly_by_conf or {}).get(confidence, 0.15)

    # Strong AI conviction bonus (+0.05)
    if ai_probability > 0.80:
        base = min(0.30, base + 0.05)

    # Esports volatility discount (10% smaller)
    if category == "esports":
        base *= 0.90

    # Re-entry discount (20% smaller — second chance = more conservative)
    if is_reentry:
        base *= 0.80

    # Absolute bounds — never exceed current max (0.25), never below 0.05
    return max(0.05, min(0.30, base))
```

**Key difference from original proposal:** Fractions calibrated against actual baseline (0.08-0.25), not assumed 0.50. The `high` confidence at 0.25 Kelly is already aggressive for the bot's bankroll — the bonus only adds +0.05 for very strong AI conviction.

**Integration:** In `risk_manager.py` (NOT `risk.py` — file doesn't exist), wrap the existing `kelly_by_confidence` lookup with `get_adaptive_kelly_fraction()`. Config values remain the base, adaptive adjustments layer on top.

---

### #16 Momentum Tightening v2

**Purpose:** Add a deeper tightening tier to the existing momentum system. Currently: 3+ cycles AND 5¢+ → ×0.75. Add: 5+ cycles AND 10¢+ → ×0.60.

**Change in `match_exit.py` (after line 274):**
```python
# Check DEEPER tier first (5+ is subset of 3+, must come first in elif chain):
if consecutive_down >= 5 and cumulative_drop >= 0.10:
    result["momentum_tighten"] = True
    max_loss = max(0.05, max_loss * 0.60)  # Severe momentum: ×0.60
elif consecutive_down >= 3 and cumulative_drop >= 0.05:
    result["momentum_tighten"] = True
    max_loss = max(0.05, max_loss * 0.75)  # Moderate momentum: ×0.75
```

**Note:** Deeper tier checked FIRST because 5+/10¢+ is a subset of 3+/5¢+. If 3+ were checked first, the elif for 5+ would be dead code.

---

### #18 Liquidity Check Before Exit

**Purpose:** Check CLOB order book depth before placing sell orders. Prevent slippage on illiquid markets.

**Logic:**
```python
def check_exit_liquidity(token_id: str, shares_to_sell: float, min_fill_ratio: float = 0.80) -> dict:
    """
    Check if order book has enough depth to absorb our sell.

    Returns dict with guaranteed keys:
        fillable: bool — can we sell at acceptable price?
        strategy: str — "market" | "limit" | "split" | "skip"
    Optional keys (present when fillable=True or partially_fillable=True):
        recommended_price: float — best achievable price
        available_depth: float — total shares biddable within 5% of midpoint
        partially_fillable: bool — True when strategy="split"
        reason: str — human-readable explanation
        note: str — additional context
    """
    try:
        if shares_to_sell <= 0:
            return {"fillable": True, "strategy": "market", "reason": "Nothing to sell"}

        book = fetch_order_book(token_id)  # CLOB API call
        bids = book.get("bids", [])

        # Calculate available depth within 5% of best bid
        if not bids:
            return {"fillable": False, "strategy": "skip", "reason": "No bids"}

        best_bid = float(bids[0]["price"])
        floor_price = best_bid * 0.95  # Accept up to 5% slippage

        available = 0.0
        for bid in bids:
            price = float(bid["price"])
            if price < floor_price:
                break
            available += float(bid["size"])

        fill_ratio = available / shares_to_sell if shares_to_sell > 0 else 0

        if fill_ratio >= 1.0:
            return {"fillable": True, "strategy": "market", "recommended_price": best_bid, "available_depth": available}
        elif fill_ratio >= min_fill_ratio:
            return {"fillable": True, "strategy": "limit", "recommended_price": best_bid, "available_depth": available}
        else:
            return {"fillable": False, "partially_fillable": True, "strategy": "split",
                    "recommended_price": best_bid, "available_depth": available,
                    "note": f"Only {fill_ratio:.0%} fillable — split across cycles"}
    except Exception:
        # On error, proceed with exit (don't block exits on API failure)
        return {"fillable": True, "strategy": "market", "reason": "Book check failed, proceeding anyway"}
```

**Integration:**
- Called from `_exit_position()` BEFORE `executor.place_exit_order()`
- If `strategy == "split"`: sell available depth now, remaining next cycle
- If `strategy == "skip"`: log warning, retry next cycle (but NEVER skip catastrophic floor exits)
- Match-aware exit layer exits (L0 score_terminal, L1 catastrophic_floor) **always execute regardless** of liquidity

---

## 3. Phase 2: Re-Entry Foundation

### #6 Re-Entry Parameters Fix

**Purpose:** Replace fixed re-entry thresholds with dynamic, game-aware values.

**A. Dynamic Elapsed Threshold (replaces fixed `elapsed_pct < 0.40`):**
```python
RE_ENTRY_MAX_ELAPSED = {
    # Esports — game-type specific
    "cs2_bo1": 0.55,    # BO1 short, 45% remaining is enough
    "cs2_bo3": 0.70,    # BO3 can reverse with 1 map left
    "cs2_bo5": 0.75,    # BO5 even more reversal potential
    "val_bo1": 0.55,
    "val_bo3": 0.70,
    "val_bo5": 0.75,
    "lol_bo1": 0.40,    # MOBA BO1: snowball, tighter window
    "lol_bo3": 0.55,    # MOBA BO3: snowball but more maps
    "lol_bo5": 0.65,
    "dota2_bo1": 0.40,
    "dota2_bo3": 0.55,
    "dota2_bo5": 0.65,
    # Sports
    "football": 0.70,   # 70th minute still viable
    "basketball": 0.75, # NBA last quarter comebacks frequent
    "default": 0.65,
}

def get_reentry_max_elapsed(slug: str, number_of_games: int) -> float:
    slug_lower = slug.lower()
    for prefix in ("cs2", "val", "lol", "dota2"):
        if slug_lower.startswith(f"{prefix}-"):
            bo = number_of_games if number_of_games > 0 else 3
            key = f"{prefix}_bo{bo}"
            return RE_ENTRY_MAX_ELAPSED.get(key, RE_ENTRY_MAX_ELAPSED["default"])
    for sport in ("epl", "laliga", "ucl", "seriea", "bundesliga", "ligue1"):
        if slug_lower.startswith(f"{sport}-"):
            return RE_ENTRY_MAX_ELAPSED["football"]
    for sport in ("nba", "cbb"):
        if slug_lower.startswith(f"{sport}-"):
            return RE_ENTRY_MAX_ELAPSED["basketball"]
    return RE_ENTRY_MAX_ELAPSED["default"]
```

**B. Dynamic Minimum Price Drop (replaces fixed 5%):**
```python
def get_min_reentry_drop(exit_price: float) -> float:
    """
    Higher exit price → smaller drop needed (each cent matters more).
    Lower exit price → larger drop needed (more noise).
    """
    if exit_price < 0.25:
        return 0.15   # 15% drop for cheap positions
    elif exit_price < 0.50:
        return 0.10   # 10% for mid-range
    elif exit_price < 0.75:
        return 0.08   # 8% for moderately priced
    else:
        return 0.05   # 5% for expensive (favorites)
```

**C. Dynamic Re-Entry Size (replaces fixed 75%):**
```python
def get_reentry_size_multiplier(
    ai_prob: float,
    direction: str,
    score_info: dict,
    original_pnl_pct: float,
) -> float:
    """
    Size = original_size × multiplier.
    Stronger signal → bigger re-entry.
    All AI prob comparisons use effective (direction-adjusted) probability.
    """
    effective_ai = ai_prob if direction == "BUY_YES" else (1 - ai_prob)
    base = 0.50  # Start conservative

    # AI probability bonus (using effective AI)
    if effective_ai >= 0.75:
        base += 0.25  # Strong conviction → 75%
    elif effective_ai >= 0.65:
        base += 0.15  # Medium conviction → 65%

    # Score bonus
    if score_info.get("available") and score_info.get("map_diff", 0) > 0:
        base += 0.15  # Ahead → more aggressive

    # Previous profit bonus
    if original_pnl_pct > 0.30:
        base += 0.10  # Made 30%+ profit last time → 10% bonus

    return min(1.0, base)
```

**D. Updated Re-Entry Conditions (ALL must be true):**
```python
def can_reenter(
    exit_reason: str,
    exit_price: float,        # Raw YES token price at exit
    current_price: float,     # Raw YES token price now
    ai_prob: float,           # Raw AI probability (YES side)
    direction: str,           # "BUY_YES" or "BUY_NO"
    score_info: dict,
    elapsed_pct: float,
    slug: str,
    number_of_games: int,
    minutes_since_exit: float,
    daily_reentry_count: int,
    market_reentry_count: int,
) -> tuple[bool, str]:
    # Direction-aware conversions (all comparisons use effective prices)
    effective_ai = ai_prob if direction == "BUY_YES" else (1 - ai_prob)
    effective_exit = exit_price if direction == "BUY_YES" else (1 - exit_price)
    effective_current = current_price if direction == "BUY_YES" else (1 - current_price)

    # Only profitable exits
    if exit_reason not in ("take_profit", "trailing_stop", "edge_tp", "spike_exit", "scale_out_final"):
        return False, "Non-profit exit"

    # Game-type specific elapsed limit
    max_elapsed = get_reentry_max_elapsed(slug, number_of_games)
    if elapsed_pct > max_elapsed:
        return False, f"Too late: {elapsed_pct:.0%} > {max_elapsed:.0%}"

    # Dynamic price drop (using effective prices)
    min_drop = get_min_reentry_drop(effective_exit)
    actual_drop = (effective_exit - effective_current) / effective_exit if effective_exit > 0 else 0
    if actual_drop < min_drop:
        return False, f"Drop {actual_drop:.0%} < required {min_drop:.0%}"

    # AI still favorable (using effective AI)
    if effective_ai < 0.60:
        return False, f"AI prob {effective_ai:.0%} < 60%"

    # Not losing
    if score_info.get("available") and score_info.get("map_diff", 0) < 0:
        return False, "Score behind"

    # Cooldown
    if minutes_since_exit < 5:
        return False, f"Cooldown: {minutes_since_exit:.0f}min < 5min"

    # Daily limits
    if daily_reentry_count >= 5:
        return False, "Daily re-entry limit (5) reached"
    if market_reentry_count >= 2:
        return False, "Market re-entry limit (2) reached"

    return True, "OK"
```

---

### #10 Re-Entry Catastrophic Floor

**Purpose:** Tighter catastrophic floor for re-entry positions: `entry × 0.75` instead of `entry × 0.50`.

**Change in `match_exit.py` catastrophic floor layer:**
```python
# Current (unchanged for normal positions):
# if entry_price >= 0.25 and current_price < entry_price * 0.50 → EXIT

# NEW: Add re-entry check
is_reentry = data.get("entry_reason", "").startswith("re_entry") or data.get("entry_reason") == "scale_in"
cat_floor_mult = 0.75 if is_reentry else 0.50

if entry_price >= 0.25 and current_price < entry_price * cat_floor_mult:
    return {"exit": True, "layer": "catastrophic_floor",
            "reason": f"Price {current_price:.3f} < entry*{cat_floor_mult:.0%} ({entry_price*cat_floor_mult:.3f})"
                      f"{' [re-entry tighter floor]' if is_reentry else ''}",
            "revoke_hold": False, "restore_hold": False, "momentum_tighten": False}
```

---

### #8 Tiered Blacklist

**Purpose:** Replace permanent blacklist with exit-reason-based durations. Profitable exits get short cooldown (re-entry eligible). Loss exits get longer cooldowns. Only catastrophic failures get permanent ban.

**Blacklist Rules:**
```python
BLACKLIST_RULES = {
    # Permanent — catastrophic failure, this market is not for us
    "catastrophic_floor": ("permanent", None),
    "hold_revoked": ("permanent", None),

    # Long cooldown — serious loss but market may still be viable
    # graduated_sl duration is set dynamically via get_graduated_sl_cooldown(elapsed_pct)
    "graduated_sl": ("timed", None),  # None = call get_graduated_sl_cooldown()
    "never_in_profit": ("timed", 20),
    "stop_loss": ("timed", 25),
    "ultra_low_guard": ("timed", 15),

    # Short cooldown — normal exit, re-entry eligible
    "take_profit": ("reentry", 5),
    "trailing_stop": ("reentry", 5),
    "edge_tp": ("reentry", 5),
    "spike_exit": ("reentry", 3),
    "scale_out_final": ("reentry", 5),

    # Score terminal — depends on outcome
    # NOTE: Requires match_exit.py modification: check_match_exit() must return
    # layer="score_terminal_loss" for is_already_lost and "score_terminal_win" for is_already_won
    # (currently returns "score_terminal" for both)
    "score_terminal_loss": ("permanent", None),
    "score_terminal_win": ("none", 0),  # Won → no blacklist
}

def get_graduated_sl_cooldown(elapsed_pct: float) -> int:
    """Earlier SL exits → shorter cooldown (market still has time)."""
    if elapsed_pct < 0.40:
        return 10   # Early match SL
    elif elapsed_pct < 0.65:
        return 15   # Mid match SL
    elif elapsed_pct < 0.85:
        return 20   # Late match SL
    else:
        return 30   # Final phase SL — very late, long cooldown
```

**Data structure:**
```python
class BlacklistEntry:
    condition_id: str
    exit_reason: str
    blacklist_type: str  # "permanent" | "timed" | "reentry" | "none"
    expires_at_cycle: int | None  # None = permanent
    exit_data: dict  # Saved AI prob, confidence, direction, prices for re-entry
```

**Blacklist creation for graduated_sl:**
```python
# In _exit_position(), when exit_reason == "graduated_sl":
# NOTE: elapsed_pct must be passed to _exit_position() as an additional parameter.
# check_match_exit() must return elapsed_pct in its result dict for this purpose.
duration = get_graduated_sl_cooldown(elapsed_pct)
blacklist.add(condition_id, "graduated_sl", "timed", current_cycle + duration, exit_data)
```

**Integration:** Replaces `_exited_markets` set and `_save_exited_market()`. Persisted to `logs/blacklist.json`.

---

### #4 Edge Decay

**Purpose:** AI analysis done at entry time becomes stale as the match progresses. Market absorbs information and becomes more efficient. Decay the AI target over time.

```python
def get_edge_decay_factor(elapsed_pct: float) -> float:
    """
    AI signal freshness. 1.0 = fully fresh, 0.25 = mostly stale.
    Used to blend AI target toward current market price.
    """
    if elapsed_pct < 0.30:
        return 1.0   # Edge at full strength
    elif elapsed_pct < 0.60:
        return 0.75  # 25% decayed
    elif elapsed_pct < 0.85:
        return 0.50  # Half decayed
    else:
        return 0.25  # Edge minimal — market price likely correct

def get_decayed_ai_target(ai_prob: float, current_price: float, elapsed_pct: float) -> float:
    """
    Blend AI target toward current price as match progresses.
    Early match: trust AI. Late match: trust market.
    """
    decay = get_edge_decay_factor(elapsed_pct)
    return current_price + (ai_prob - current_price) * decay
```

**Usage:**
- In `check_take_profits()`: use decayed target instead of raw `ai_probability` for edge TP calculation
- In re-entry decisions: edge = |decayed_ai_target - current_price| (not raw AI prob)
- **NOT used in `check_match_exit()`** — exit system uses raw thresholds, not AI targets
- **NOT used for Kelly sizing** — Kelly uses raw probability (sizing is a pre-entry decision)

**Important:** AI Confidence Momentum filter (#12) compares RAW (un-decayed) values, not decayed ones.

---

## 4. Phase 3: Exit System Overhaul

### #1 Scale Out (3-Tier Partial Exit)

**Purpose:** Replace binary exit (all-or-nothing) with graduated profit-taking. Sell portions at milestones, let the rest ride for resolution or trailing stop.

**Position Model Addition:**
```python
class PartialExit(BaseModel):
    timestamp: datetime
    tier: str           # "tier1_risk_free" | "tier2_profit_lock" | "tier3_final"
    shares_sold: float
    fill_price: float
    realized_pnl: float
    pct_of_original: float

# Added to Position:
original_shares: float | None = None        # Snapshot on first partial exit
original_size_usdc: float | None = None     # Snapshot on first partial exit
partial_exits: list[PartialExit] = []       # History of partial exits
scale_out_tier: int = 0                     # 0=none, 1=tier1 done, 2=tier2 done
```

**Tier Configuration:**
```python
SCALE_OUT_TIERS = {
    "tier1_risk_free": {
        "trigger_pnl_pct": 0.25,    # +25% unrealized PnL
        "sell_pct": 0.40,           # Sell 40% of position
    },
    "tier2_profit_lock": {
        "trigger_pnl_pct": 0.50,    # +50% unrealized PnL
        "sell_pct": 0.50,           # Sell 50% of REMAINING (= 30% of original)
    },
    "tier3_final": {
        "trigger": "resolution_or_trailing_or_exit_system",
        "sell_pct": 1.0,            # Sell everything remaining (~30% of original)
    },
}
```

**Scale Out Check (runs every cycle, BEFORE legacy TP check):**
```python
def check_scale_out(pos: Position) -> dict | None:
    """Check if position qualifies for next scale-out tier."""
    # Skip VS positions (they have their own TP)
    if pos.volatility_swing:
        return None

    # Skip if not enough unrealized profit
    pnl_pct = pos.unrealized_pnl_pct

    if pos.scale_out_tier == 0 and pnl_pct >= 0.25:
        return {
            "action": "scale_out",
            "tier": "tier1_risk_free",
            "sell_pct": 0.40,
            "reason": f"Tier 1: Risk-free at +{pnl_pct:.0%}"
        }

    if pos.scale_out_tier == 1 and pnl_pct >= 0.50:
        return {
            "action": "scale_out",
            "tier": "tier2_profit_lock",
            "sell_pct": 0.50,  # 50% of remaining
            "reason": f"Tier 2: Profit lock at +{pnl_pct:.0%}"
        }

    return None
```

**Mutation After Confirmed Partial Fill:**
```python
def apply_partial_exit(pos: Position, shares_sold: float, fill_price: float, tier: str) -> str:
    # fill_price is always the YES token price from the order book, regardless of direction.
    # Direction conversion is handled internally (proceeds calculation below).
    # Snapshot originals on first partial
    if pos.original_shares is None:
        pos.original_shares = pos.shares
        pos.original_size_usdc = pos.size_usdc

    # Compute realized PnL (direction-safe: use proportional cost from size_usdc)
    cost_basis_sold = pos.size_usdc * (shares_sold / pos.shares)
    if pos.direction == "BUY_NO":
        proceeds = shares_sold * (1 - fill_price)
    else:
        proceeds = shares_sold * fill_price
    realized_pnl = proceeds - cost_basis_sold

    # Record
    pos.partial_exits.append(PartialExit(
        timestamp=datetime.now(timezone.utc),
        tier=tier,
        shares_sold=shares_sold,
        fill_price=fill_price,
        realized_pnl=realized_pnl,
        pct_of_original=shares_sold / pos.original_shares if pos.original_shares else 0,
    ))

    # Mutate proportionally
    reduction_ratio = shares_sold / pos.shares
    pos.shares -= shares_sold
    pos.size_usdc *= (1 - reduction_ratio)
    pos.scale_out_tier += 1

    # Note: After partial exit, unrealized_pnl_pct on the remaining position is identical
    # to before the partial exit. This holds for BOTH BUY_YES and BUY_NO because shares
    # is the only variable reduced in both value and cost calculations (proportional reduction).
    # Tier 2 trigger (+50%) is measured against the same cost basis per share.

    # Dust check — close entirely if remainder trivial
    if pos.size_usdc < 0.50 or pos.shares < 1.0:
        return "CLOSE_REMAINDER"
    return "OK"
```

**Interaction with existing exits:**
- When scale_out_tier > 0, **disable legacy TP logic** for this position (Scale Out manages profit-taking)
- Match-aware exits (L0-L4) still apply to remaining shares — if catastrophic floor triggers, sell everything remaining
- Trailing stop applies to remaining shares after scale-out tiers
- `_exit_position()` for tier3 (final exit) works as before: remove position, place sell order for remaining shares
- When tier 3 exits via trailing stop, resolution, or exit system, `exit_reason` is set to `"scale_out_final"` for blacklist/re-entry classification
- **Tier 3 final exit MUST go through `_exit_position()`** to save `exit_data` (AI prob, confidence, direction, prices) into `BlacklistEntry` for re-entry eligibility

---

### #2 Resolution-Aware TP

**Purpose:** When price is high (≥80¢), AI is confident, and score is favorable — don't TP. Hold remaining shares for 100¢ resolution. Prediction markets resolve binary: 0¢ or 100¢.

```python
def should_hold_for_resolution(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,
) -> tuple[bool, str]:
    """
    Decide if remaining position (after scale-out tiers) should be held for resolution.
    Only applies to tier 2+ positions (already took partial profits).
    """
    if pos.scale_out_tier < 1:
        return False, "No tiers exited yet"

    current = pos.current_price
    ai_prob = pos.ai_probability

    # Effective AI prob for our direction
    effective_ai = ai_prob if pos.direction == "BUY_YES" else (1 - ai_prob)

    # Direction-aware price: for BUY_NO, "our" price is (1 - YES price)
    effective_price = current if pos.direction == "BUY_YES" else (1 - current)

    # Conditions for resolution hold
    price_high = effective_price >= 0.80
    ai_confident = effective_ai >= 0.70
    not_behind = not (score_info.get("available") and score_info.get("map_diff", 0) < 0)

    if price_high and ai_confident and not_behind:
        return True, f"Resolution hold: effective_price {effective_price:.0%}, AI {effective_ai:.0%}, not behind"

    # Already won → definitely hold
    if score_info.get("is_already_won"):
        return True, f"Already won — hold for 100¢ resolution"

    return False, ""
```

**Interaction with Graduated SL:** When `resolution_hold = True`, graduated SL is bypassed unless price drops catastrophically:
```python
# In graduated SL calculation:
if resolution_hold:
    # Don't let graduated SL kill a near-certain winner
    # Direction-aware: effective_price = current_price for BUY_YES, (1 - current_price) for BUY_NO
    effective_price = current_price if direction == "BUY_YES" else (1 - current_price)
    # Only exit if effective price drops below 65¢ (catastrophic reversal from 80¢+)
    if effective_price >= 0.65:
        pass  # Skip graduated SL entirely — hold for resolution
    # If effective price dropped below 65¢, resolution thesis is broken, let graduated SL handle it
```

---

### #3 σ-based Trailing Stop

**Purpose:** Replace fixed-tier trailing stop with continuous, volatility-adjusted trailing. More responsive to actual market conditions.

```python
def calculate_sigma_trailing_stop(
    peak_pnl_pct: float,
    price_history: list[float],  # Last 20 prices
    current_price: float,
    peak_price: float,
    entry_price: float,
) -> dict:
    """
    Trailing stop based on price volatility (σ).

    Wide in volatile markets, tight in calm markets.
    Tightens as peak PnL increases (protect larger gains).

    IMPORTANT: ALL price parameters must be effective (direction-adjusted) prices.
    The caller converts before passing:
      BUY_YES: effective = raw YES price
      BUY_NO:  effective = 1 - raw YES price
    This includes price_history, current_price, peak_price, AND entry_price.
    """
    if peak_pnl_pct < 0.05 or len(price_history) < 5:
        return {"active": False}

    # Calculate rolling σ (true standard deviation of price changes, mean-subtracted)
    changes = [price_history[i] - price_history[i-1] for i in range(1, len(price_history))]
    if not changes:
        return {"active": False}

    mean_change = sum(changes) / len(changes)
    sigma = (sum((c - mean_change)**2 for c in changes) / len(changes)) ** 0.5

    # Z-score multiplier: tightens with higher peak
    # Low peak (5-15%) → z=3.0 (wide, let it breathe)
    # High peak (40%+) → z=1.5 (tight, protect gains)
    if peak_pnl_pct < 0.15:
        z = 3.0
    elif peak_pnl_pct < 0.30:
        z = 2.5
    elif peak_pnl_pct < 0.50:
        z = 2.0
    else:
        z = 1.5

    trail_distance = z * sigma
    stop_price = peak_price - trail_distance

    # Never let stop go below entry (once in profit, stay in profit zone)
    stop_price = max(stop_price, entry_price)

    triggered = current_price <= stop_price and stop_price > 0

    return {
        "active": True,
        "sigma": sigma,
        "z_score": z,
        "trail_distance": trail_distance,
        "stop_price": stop_price,
        "peak_price": peak_price,
        "triggered": triggered,
        "reason": f"σ-trail: price {current_price:.3f} {'<' if triggered else '>='} stop {stop_price:.3f} (peak {peak_price:.3f} - {z}×{sigma:.4f})"
    }
```

**Position model addition:**
```python
# Added to Position:
price_history_buffer: list[float] = []  # Rolling buffer of last 20 prices
peak_price: float = 0.0                 # Highest price seen (for trailing)
```

**Integration:** Replaces `check_trailing_stops()` in portfolio.py. The old tier-based trailing is removed.

**Direction handling:** All σ-trailing operates on **effective prices** (direction-adjusted):
- `BUY_YES`: effective_price = current_price, peak tracks highest price
- `BUY_NO`: effective_price = 1 - current_price, peak tracks highest effective price (lowest YES price)

The caller converts before passing to `calculate_sigma_trailing_stop()`. This ensures the function works identically for both directions.

**Buffer population** (in `portfolio.py::update_price()`):
```python
# After updating current_price:
# Store effective price (direction-adjusted) in buffer
effective_price = pos.current_price if pos.direction == "BUY_YES" else (1 - pos.current_price)
pos.price_history_buffer.append(effective_price)
if len(pos.price_history_buffer) > 20:
    pos.price_history_buffer = pos.price_history_buffer[-20:]  # Keep last 20
if effective_price > pos.peak_price:
    pos.peak_price = effective_price
```

**Interaction with VS positions:** VS positions keep their own exit logic. σ-trailing does NOT apply to `volatility_swing=True` positions.

**Interaction with Scale Out:** σ-trailing applies to remaining shares after scale-out tiers. If tier 1 and tier 2 are done, the remaining ~30% rides with σ-trailing until resolution or stop.

---

## 5. Phase 4: Re-Entry Extensions

### #11 Snowball Ban

**Purpose:** MOBA games (LoL, Dota 2) have snowball mechanics — gold/XP advantages compound exponentially. If behind after 30% of match, comeback is statistically very unlikely. Ban re-entry.

```python
SNOWBALL_GAMES = {"lol", "dota2"}

def is_snowball_banned(
    slug: str,
    elapsed_pct: float,
    score_info: dict,
) -> tuple[bool, str]:
    slug_lower = slug.lower()
    is_moba = any(slug_lower.startswith(f"{g}-") for g in SNOWBALL_GAMES)

    if not is_moba:
        return False, ""

    if elapsed_pct > 0.30 and score_info.get("available") and score_info.get("map_diff", 0) < 0:
        return True, f"MOBA snowball ban: {elapsed_pct:.0%} elapsed, score behind"

    return False, ""
```

**Exception:** Score Reversal (#13) can override this ONLY if `map_diff >= 2` (convincing lead, not just +1).

---

### #12 AI Confidence Momentum Filter

**Purpose:** Re-entry only if AI confidence is rising (new assessment > saved assessment × 1.05). Prevents re-entering on stale or declining signals.

```python
def passes_confidence_momentum(
    saved_ai_prob: float,
    current_ai_prob: float,
    direction: str,
    threshold: float = 1.05,
) -> tuple[bool, str]:
    """
    Compare RAW (un-decayed) AI probabilities, direction-adjusted.
    Current effective prob must be at least 5% higher than saved effective prob.
    For BUY_NO, effective = 1 - raw (so rising NO confidence = falling YES prob).
    """
    saved_eff = saved_ai_prob if direction == "BUY_YES" else (1 - saved_ai_prob)
    current_eff = current_ai_prob if direction == "BUY_YES" else (1 - current_ai_prob)

    if saved_eff < 0.10:
        return True, "Saved effective prob too low to compare meaningfully"

    ratio = current_eff / saved_eff
    if ratio >= threshold:
        return True, f"Confidence rising: {saved_eff:.0%} → {current_eff:.0%} (×{ratio:.2f})"
    else:
        return False, f"Confidence not rising: {saved_eff:.0%} → {current_eff:.0%} (×{ratio:.2f} < ×{threshold})"
```

**Note:** This requires a fresh AI call for re-entry decisions (unlike current spike/scouted re-entry which uses saved analysis). Cost: 1 API call per re-entry candidate. Benefit: much better signal quality.

**Decision:** For the initial implementation, AI Confidence Momentum is OPTIONAL — if the bot has API budget, call AI; if not, skip this filter and use saved probability. Config flag: `reentry_fresh_ai_call: bool = False`.

---

### #9 Layer 3 Grace Period

**Purpose:** Re-entry positions get conditional immunity from Never-in-Profit guard. Without this, Layer 3 would immediately flag a re-entry as "never profited, 70%+ done" because the match is already well underway.

```python
# Grace period: conditional, not blanket
REENTRY_GRACE_CYCLES = 5
REENTRY_GRACE_MAX_DROP = 0.03  # 3¢

def is_grace_period_active(data: dict) -> bool:
    """Re-entry positions get limited immunity from Layer 3.

    Accepts the same data dict passed to check_match_exit().
    Requires 'entry_reason' and 'cycles_held' fields in the dict.
    """
    entry_reason = data.get("entry_reason", "")
    if not entry_reason.startswith("re_entry") and entry_reason != "scale_in":
        return False

    cycles_held = data.get("cycles_held", 999)  # Default high = no grace
    if cycles_held > REENTRY_GRACE_CYCLES:
        return False  # Grace expired

    # Grace revoked if effective price drops too much (direction-aware)
    entry_p = data.get("entry_price", 0)
    current_p = data.get("current_price", 0)
    direction = data.get("direction", "BUY_YES")
    if direction == "BUY_NO":
        # For BUY_NO: effective price = 1 - YES price. Drop = effective_entry - effective_current
        drop_since_entry = (1 - entry_p) - (1 - current_p)  # = current_p - entry_p
    else:
        drop_since_entry = entry_p - current_p
    if drop_since_entry > REENTRY_GRACE_MAX_DROP:
        return False  # Bad re-entry, revoke grace

    return True
```

**Integration in `check_match_exit()` Layer 3:**
```python
# Before never-in-profit check:
if is_grace_period_active(data):
    pass  # Skip Layer 3 for this cycle
```

**Data dict additions** (in `check_match_aware_exits()` in portfolio.py):
```python
data = {
    ...existing fields...,
    "entry_reason": pos.entry_reason,
    "cycles_held": pos.cycles_held,
}
```

**Position model addition:**
```python
cycles_held: int = 0  # Incremented every update_price() cycle
```

---

### #13 Score Reversal Blacklist Exception

**Purpose:** Override timed/permanent blacklist if score has completely reversed in our favor. Narrowly scoped — requires convincing lead.

```python
def qualifies_for_score_reversal_reentry(
    blacklist_entry: BlacklistEntry,
    score_info: dict,
    elapsed_pct: float,
    current_cycle: int,
) -> tuple[bool, str]:
    """
    Override blacklist if score dramatically reversed.
    Very narrow conditions to prevent abuse.
    """
    # Must have score data
    if not score_info.get("available"):
        return False, "No score data"

    # Must be convincingly ahead (not just +1)
    map_diff = score_info.get("map_diff", 0)
    if map_diff < 2:
        return False, f"map_diff {map_diff} < 2 (need convincing lead)"

    # Must not be too late
    if elapsed_pct > 0.70:
        return False, f"Too late: {elapsed_pct:.0%} > 70%"

    # Only override timed blacklists with >10 cycles remaining
    if blacklist_entry.blacklist_type == "permanent":
        return False, "Cannot override permanent blacklist"
    if blacklist_entry.blacklist_type == "timed":
        remaining = (blacklist_entry.expires_at_cycle or 0) - current_cycle
        if remaining <= 10:
            return False, f"Only {remaining} cycles left, let it expire naturally"

    # MOBA snowball override requires map_diff >= 2 (already checked above)

    return True, f"Score reversal: map_diff={map_diff}, elapsed={elapsed_pct:.0%}"
```

**Size for score reversal re-entry:** Kelly / 4 (very conservative — this is opportunistic).

---

## 6. Phase 5: Advanced Features

### #7 Scale-In (Gradual Entry)

**Purpose:** Enter 50% of position initially. Add remaining 50% when confirmed (score ahead or price rising). Reduces loss on bad entries.

```python
SCALE_IN_INITIAL_PCT = 0.50
SCALE_IN_CONFIRMATION_CYCLES = 3  # Wait at least 3 cycles before adding

def should_scale_in(pos: Position, score_info: dict) -> tuple[bool, str]:
    """Check if position qualifies for second tranche."""
    if pos.scale_in_complete:
        return False, "Already scaled in"
    if pos.cycles_held < SCALE_IN_CONFIRMATION_CYCLES:
        return False, f"Too early: {pos.cycles_held} < {SCALE_IN_CONFIRMATION_CYCLES} cycles"

    # Confirmation signals (need at least 1)
    # Use PnL-based confirmation instead of raw price (direction-safe)
    # unrealized_pnl_pct is already direction-aware (computed from current_value vs size_usdc)
    pnl_positive = pos.unrealized_pnl_pct > 0.02  # +2% PnL (works for both BUY_YES and BUY_NO)
    score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
    # price_rising replaced by pnl_positive — raw price comparison is direction-broken

    if pnl_positive or score_ahead:
        return True, f"Confirmed: pnl+={pnl_positive}, score_ahead={score_ahead}"

    return False, "No confirmation signal yet"
```

**Second tranche sizing:**
```python
def get_scale_in_size(pos: Position, bankroll: float, config) -> float:
    """
    Second tranche = min(original_intended_remaining, Kelly_now - current_exposure).
    Re-runs Kelly to avoid over-sizing if conditions changed.
    """
    current_kelly = kelly_position_size(
        pos.ai_probability, pos.current_price, bankroll,
        kelly_fraction=get_adaptive_kelly_fraction(pos.confidence, pos.ai_probability, pos.category),
        max_bet_usdc=config.risk.max_single_bet_usdc,
        max_bet_pct=config.risk.max_bet_pct,
        direction=pos.direction,
    )
    remaining_intended = pos.intended_size_usdc - pos.size_usdc
    return max(0, min(remaining_intended, current_kelly - pos.size_usdc))
```

**Position model additions:**
```python
intended_size_usdc: float = 0.0    # Full Kelly size at entry (before scale-in split)
                                    # Legacy positions with intended_size_usdc=0 are automatically excluded from scale-in
scale_in_complete: bool = False     # True after second tranche
```

**Entry-time setup:** When scale-in is active for a new position:
```python
full_kelly_size = kelly_position_size(...)
pos.intended_size_usdc = full_kelly_size
pos.size_usdc = full_kelly_size * SCALE_IN_INITIAL_PCT  # 50%
pos.shares = ... # Shares for the 50% position
```
Legacy positions with `intended_size_usdc=0` are automatically excluded (remaining_intended = 0 - size_usdc < 0 → returns 0).

**Interaction with Circuit Breaker:** If circuit breaker is active, second tranche is blocked. Position stays at 50%.

---

### #5 VS Spike Detection

**Purpose:** Detect rapid price spikes in VS positions using velocity (rate of change). Exit immediately during spike peak.

```python
def detect_vs_spike(
    price_history: list[float],
    entry_price: float,
) -> dict:
    """
    Velocity-based spike detection for volatility swing positions.
    Spike = rapid price increase that's likely to reverse.
    """
    if len(price_history) < 3:
        return {"spike": False}

    # 2-cycle velocity
    if price_history[-3] <= 0:
        return {"spike": False}
    velocity_2 = (price_history[-1] - price_history[-3]) / price_history[-3]

    # 1-cycle velocity (acceleration)
    if price_history[-2] <= 0:
        return {"spike": False}
    velocity_1 = (price_history[-1] - price_history[-2]) / price_history[-2]

    # Strong spike: +15% in 2 cycles and still accelerating
    if velocity_2 > 0.15 and velocity_1 > 0.05:
        return {
            "spike": True,
            "velocity": velocity_2,
            "action": "EXIT_NOW",
            "reason": f"VS spike: +{velocity_2:.0%} in 2 cycles, accelerating"
        }

    # Weakening spike: +10% in 2 cycles but momentum fading
    prev_velocity = (price_history[-2] - price_history[-3]) / price_history[-3] if price_history[-3] > 0 else 0
    if velocity_2 > 0.10 and velocity_1 < prev_velocity:
        return {
            "spike": True,
            "velocity": velocity_2,
            "action": "EXIT_NOW",
            "reason": f"VS spike peaking: +{velocity_2:.0%}, momentum fading"
        }

    return {"spike": False}
```

**Integration:** Added to `check_volatility_swing_exits()`. Spike detection runs BEFORE normal VS TP. If spike detected, exit immediately without waiting for TP threshold.

**Interaction with σ-trailing:** VS positions do NOT use σ-trailing. They keep their own exit logic (VS TP + VS time exit + spike detection).

---

### #17 Correlation-Aware Exposure

**Purpose:** Detect when multiple positions bet on the same match outcome. Calculate net exposure instead of gross.

```python
def calculate_net_exposure(positions: dict[str, Position]) -> dict[str, float]:
    """
    Group positions by match (using slug prefix).
    Calculate net exposure per match.

    Example: "cs2-navi-vs-faze" YES $50 + "cs2-navi-vs-faze" NO $30 = net $20 YES exposure
    """
    match_groups: dict[str, list[Position]] = {}
    for pos in positions.values():
        # Extract match identifier from slug (remove outcome suffix)
        match_key = _extract_match_key(pos.slug)
        if match_key:
            match_groups.setdefault(match_key, []).append(pos)

    exposures = {}
    for match_key, group in match_groups.items():
        yes_exposure = sum(p.size_usdc for p in group if p.direction == "BUY_YES")
        no_exposure = sum(p.size_usdc for p in group if p.direction == "BUY_NO")
        net = abs(yes_exposure - no_exposure)
        gross = yes_exposure + no_exposure
        exposures[match_key] = {
            "net": net,
            "gross": gross,
            "yes": yes_exposure,
            "no": no_exposure,
            "hedged": min(yes_exposure, no_exposure),
        }
    return exposures

def _extract_match_key(slug: str) -> str | None:
    """
    Extract match identifier. E.g.:
    "cs2-navi-vs-faze-winner" → "cs2-navi-vs-faze"
    "cs2-navi-vs-faze-map1" → "cs2-navi-vs-faze"
    """
    slug_lower = slug.lower()
    # Remove common suffixes
    # Best-effort heuristic — add new suffixes as discovered in production
    import re
    match = re.match(r"(.*-vs-.*?)(?:-(?:winner|map\d+|over|under|total|to-win|handicap|first-\w+|spread|moneyline))?$", slug_lower)
    if match:
        return match.group(1)
    return slug_lower
```

**Integration with Kelly:** Pipeline is: `Kelly(confidence) → Correlation cap → Final size`. Correlation can only reduce, never increase.

```python
MAX_MATCH_EXPOSURE_PCT = 0.15  # Max 15% of bankroll on one match

def apply_correlation_cap(
    proposed_size: float,
    match_key: str,
    current_exposures: dict,
    bankroll: float,
) -> float:
    max_exposure = bankroll * MAX_MATCH_EXPOSURE_PCT
    current = current_exposures.get(match_key, {}).get("net", 0)
    remaining = max(0, max_exposure - current)
    return min(proposed_size, remaining)
```

---

## 7. Conflict Resolutions

All identified conflicts and their resolutions:

| ID | Conflict | Resolution |
|----|----------|------------|
| C1 | Scale Out vs 4-Layer Exit | Exit layers operate on remaining shares. Catastrophic floor and score terminal exit ALL remaining. Graduated SL and never-in-profit on remaining only. |
| C2 | Resolution-Aware TP vs Graduated SL | When resolution_hold=True, SL floor widens to 65¢ minimum. Only catastrophic reversal triggers exit. |
| C3 | σ-Trailing vs VS Spike | Separate σ windows: trailing=20-cycle, spike=5-cycle ratio. VS positions excluded from σ-trailing entirely. |
| C4 | Tiered Blacklist vs Score Reversal Exception | #13 only overrides blacklists with >10 cycles remaining. Short-duration blacklists expire naturally. |
| C5 | Scale-In vs Adaptive Kelly | Tranche 2 re-runs Kelly. Size = min(intended_remaining, Kelly_now - current_size). |
| C6 | Layer 3 Grace vs Never-in-Profit | Grace is conditional: revoked if price drops >3¢ within 5 cycles. Not blanket immunity. |
| C7 | Circuit Breaker vs Resolution Hold | Breaker NEVER force-exits resolution-hold positions. Only blocks new entries and scale-in tranches. |
| C8 | Correlation vs Kelly | Pipeline: Kelly → Correlation cap → Final size. Cap only reduces, never increases. |
| C9 | Edge Decay vs AI Momentum | #12 compares RAW probabilities. #4 decay applies only to position management and TP targets. |
| C10 | Snowball Ban vs Score Reversal | #13 overrides #11 only if map_diff ≥ 2. Single-map lead in MOBA not enough. |
| C11 | Scale-In vs Re-entry Cat. Floor | Scale-in (`entry_reason="scale_in"`) uses the tighter 0.75 floor intentionally. Scale-in is a second tranche that was NOT in the original entry — it was added after confirmation. If the confirmation was wrong, tighter protection is warranted. Normal first-tranche positions (`entry_reason="ai"`) use standard 0.50 floor. |

---

## 8. Position Model Changes

New fields added to `Position` class in `models.py`:

```python
# Scale Out fields
original_shares: float | None = None
original_size_usdc: float | None = None
partial_exits: list[dict] = []    # List of PartialExit dicts (serializable)
scale_out_tier: int = 0           # 0=none, 1=tier1, 2=tier2

# Scale-In fields
intended_size_usdc: float = 0.0   # Full Kelly size before scale-in split
scale_in_complete: bool = False

# σ-Trailing fields
price_history_buffer: list[float] = []  # Rolling 20-price buffer
peak_price: float = 0.0                # Highest effective price seen (YES for BUY_YES, 1-YES for BUY_NO)

# Grace period
cycles_held: int = 0                   # Incremented each update cycle

# Entry reason (already exists but now used by more systems)
entry_reason: str = ""                 # "ai", "scouted", "re_entry_after_profit", "scale_in", etc.
```

**Backward compatibility:** All new fields have defaults. Existing positions loaded from disk will work with defaults (scale_out_tier=0, partial_exits=[], etc.).

---

## 9. v1 BUY_NO Direction Fixes in match_exit.py

**Context:** While modifying `match_exit.py` for v2 features, we found that ALL price comparisons in the v1 code use raw YES token prices. For BUY_NO positions, this means catastrophic floor, never-in-profit guard, hold revocation, and graduated SL width multiplier are all broken. Since we're already modifying this file, include these fixes.

### 9a. Effective Price Helper

Add at top of `check_match_exit()`, after parsing direction:
```python
# Direction-aware effective prices: for BUY_NO, our value = 1 - YES price
effective_entry = entry_price if direction == "BUY_YES" else (1 - entry_price)
effective_current = current_price if direction == "BUY_YES" else (1 - current_price)
```

### 9b. Catastrophic Floor (Layer 1) — use effective prices

```python
# BEFORE (broken for BUY_NO):
# if entry_price >= 0.25 and current_price < entry_price * 0.50:

# AFTER:
is_reentry = data.get("entry_reason", "").startswith("re_entry") or data.get("entry_reason") == "scale_in"
cat_floor_mult = 0.75 if is_reentry else 0.50
if effective_entry >= 0.25 and effective_current < effective_entry * cat_floor_mult:
    return {"exit": True, "layer": "catastrophic_floor", ...}
```

### 9c. Ultra-Low Guard — use effective prices

```python
# BEFORE: if entry_price < 0.09 and ... current_price < 0.05
# AFTER:
if effective_entry < 0.09 and elapsed_pct >= 0.90 and effective_current < 0.05:
```

### 9d. Graduated SL Width — use effective entry for multiplier

```python
# BEFORE: max_loss = get_graduated_max_loss(elapsed_pct, entry_price, score_info)
# AFTER:
max_loss = get_graduated_max_loss(elapsed_pct, effective_entry, score_info)
```

This makes `get_entry_price_multiplier()` receive the correct effective price:
- BUY_YES at YES=0.65 → 0.65 (favorite, tight stop) ✓
- BUY_NO at YES=0.65 → effective 0.35 (underdog, wide stop) ✓

### 9e. Never-in-Profit Guard (Layer 3) — use effective prices

```python
# BEFORE:
# elif current_price >= entry_price * 0.90: pass
# elif current_price < entry_price * 0.75: EXIT

# AFTER:
elif effective_current >= effective_entry * 0.90:
    pass  # Close to entry
elif effective_current < effective_entry * 0.75:
    return ... exit
```

### 9f. Hold-to-Resolve Revocation (Layer 4) — use effective prices

```python
# BEFORE:
# if ever_in_profit and current_price < entry_price * 0.70 ...

# AFTER:
if ever_in_profit and effective_current < effective_entry * 0.70 and elapsed_pct > 0.60:
    ...
if not ever_in_profit and effective_current < effective_entry * 0.75 and elapsed_pct > 0.70:
    ...

# Hold restore:
if ... current_price > entry_price * 0.85:
# becomes:
if ... effective_current > effective_entry * 0.85:
```

### 9g. score_terminal Layer Split

`check_match_exit()` must return differentiated layer values for the tiered blacklist:
```python
# BEFORE:
if score_info.get("is_already_lost"):
    return {"exit": True, "layer": "score_terminal", ...}
if score_info.get("is_already_won"):
    return {"exit": False, "layer": "score_terminal", ...}

# AFTER:
if score_info.get("is_already_lost"):
    return {"exit": True, "layer": "score_terminal_loss", ...}
if score_info.get("is_already_won"):
    return {"exit": False, "layer": "score_terminal_win", ...}
```

### 9h. check_match_exit Result Dict — add elapsed_pct

For tiered blacklist's `get_graduated_sl_cooldown()`, add `elapsed_pct` to the return dict:
```python
result = {"exit": False, "layer": "", "reason": "",
          "revoke_hold": False, "restore_hold": False,
          "momentum_tighten": False, "elapsed_pct": elapsed_pct}
```

### 9i. Edge Decay — document raw-frame contract

`get_decayed_ai_target()` operates in raw YES-probability frame. Callers must handle direction conversion:
```python
# Usage in check_take_profits():
decayed_target = get_decayed_ai_target(pos.ai_probability, pos.current_price, elapsed_pct)
# For BUY_NO, the target is already in YES frame — convert when computing edge:
if pos.direction == "BUY_NO":
    edge = pos.current_price - decayed_target  # Edge = YES price minus target (lower is better for NO)
else:
    edge = decayed_target - pos.current_price  # Edge = target minus YES price
```

### 9j. Scale Out + Scouted Positions

Scouted "hold to resolve" positions participate in scale-out. This is intentional:
- v1 held 100% to resolve — high variance, binary outcome
- v2 takes partial profits (40% at +25%, 30% at +50%), then holds remaining ~30% for resolution
- This reduces variance while preserving resolution upside on the remaining shares
- Add comment in `check_scale_out()` documenting this design decision

---

## 10. File Structure

```
src/
├── match_exit.py          # MODIFIED: +re-entry floor, +momentum v2, +BUY_NO direction fixes, +score_terminal split
├── scale_out.py           # NEW: Scale out logic, partial exit mutation
├── reentry.py             # NEW: Re-entry eligibility, dynamic thresholds, blacklist
├── circuit_breaker.py     # NEW: Portfolio-level loss limits
├── edge_decay.py          # NEW: AI signal freshness
├── trailing_sigma.py      # NEW: σ-based trailing stop
├── vs_spike.py            # NEW: Volatility swing spike detection
├── correlation.py         # NEW: Match-level exposure tracking
├── portfolio.py           # MODIFIED: +scale_out check, +σ-trailing, +new fields
├── models.py              # MODIFIED: +new Position fields
├── main.py                # MODIFIED: integration of all new systems
├── config.py              # MODIFIED: +new config sections
└── risk_manager.py        # MODIFIED: +adaptive kelly

tests/
├── test_match_exit.py     # MODIFIED: +re-entry floor, +momentum v2, +BUY_NO direction tests
├── test_scale_out.py      # NEW
├── test_reentry.py        # NEW
├── test_circuit_breaker.py # NEW
├── test_edge_decay.py     # NEW
├── test_trailing_sigma.py # NEW
├── test_vs_spike.py       # NEW
├── test_correlation.py    # NEW
└── test_scale_in.py       # NEW
```

---

## 11. Testing Strategy

### Unit Tests (per module)
Each new module gets its own test file with:
- Happy path tests
- Edge cases (zero values, None inputs, extreme ranges)
- Boundary tests (exactly at thresholds)

### BUY_NO Direction Tests (CRITICAL)
Every function that uses prices or AI probability must have **paired BUY_YES and BUY_NO tests**:
- `check_match_exit()`: catastrophic floor, graduated SL, never-in-profit, hold revocation — all with BUY_NO
- `can_reenter()`: price drop detection, AI prob threshold — BUY_NO effective conversions
- `calculate_sigma_trailing_stop()`: effective price buffer, peak tracking — BUY_NO
- `should_hold_for_resolution()`: effective price ≥80¢ — BUY_NO where YES<20¢
- `passes_confidence_momentum()`: ratio inversion — BUY_NO where falling YES = good
- `is_grace_period_active()`: drop direction — BUY_NO where YES rising = bad
- `should_scale_in()`: PnL-based confirmation (not raw price) — BUY_NO

### Integration Tests
- Scale Out + Match-Aware Exit: verify catastrophic floor exits all remaining tiers
- Circuit Breaker + Re-entry: verify breaker blocks re-entries
- σ-Trailing + Scale Out: verify trailing applies to remaining shares
- Tiered Blacklist + Score Reversal: verify override logic
- Layer 3 Grace + Re-entry: verify grace revocation on price drop
- Adaptive Kelly + Correlation: verify pipeline sizing

### Regression Tests
- All existing `test_match_exit.py` tests must pass unchanged
- Existing position PnL calculations must produce same results for non-partial positions
- BUY_NO regression: existing BUY_NO test scenarios may need updating to reflect direction fixes

### Success Criteria
1. No existing test breaks
2. All new modules have >90% branch coverage
3. Scale Out PnL math verified with 5+ scenarios (both BUY_YES and BUY_NO)
4. Circuit Breaker halts entries but never exits
5. Re-entry parameters produce reasonable values for all game types
6. σ-trailing produces tighter stops than old tier system at high peaks, wider at low peaks
7. Every function with price/AI comparisons has paired BUY_YES and BUY_NO tests
