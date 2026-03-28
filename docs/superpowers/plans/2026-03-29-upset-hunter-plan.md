# Upset Hunter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace bond farming with upset hunter — buy underdog YES tokens at 5-15¢ where favourite-longshot bias creates mispricing.

**Architecture:** Delete `bond_scanner.py`, create `upset_hunter.py` with pre-filter logic, wire into agent.py at the same call point. Add upset-specific exit rules to exit_monitor and match_exit. Add underdog prompt to ai_analyst.

**Tech Stack:** Python, Pydantic config, Claude Sonnet API, Polymarket CLOB

**Spec:** `docs/superpowers/specs/2026-03-29-upset-hunter-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| DELETE | `src/bond_scanner.py` | Removed entirely |
| CREATE | `src/upset_hunter.py` | Pre-filter candidates, build upset context for AI |
| MODIFY | `src/config.py` | Remove BondFarmingConfig, add UpsetHunterConfig |
| MODIFY | `src/agent.py` | Replace _check_bond_farming with _check_upset_hunter |
| MODIFY | `src/exit_monitor.py` | Upset-specific SL and trailing TP params |
| MODIFY | `src/match_exit.py` | Forced exit at last 10% of match for upset positions |
| MODIFY | `src/scale_out.py` | Upset-specific 3-tier scale-out |
| MODIFY | `src/ai_analyst.py` | Underdog-specific prompt template |
| MODIFY | `src/trade_logger.py` | Replace "bond_farming" edge source with "upset_hunter" |
| MODIFY | `analyze_pnl.py` | Add "UPSET_ENTRY" to action filter |

---

### Task 1: Config — Remove BondFarmingConfig, Add UpsetHunterConfig

**Files:**
- Modify: `src/config.py:127-137` (delete BondFarmingConfig)
- Modify: `src/config.py:202` (delete bond_farming from AppConfig)
- Modify: `src/config.py` (add UpsetHunterConfig + AppConfig field)

- [ ] **Step 1: Delete BondFarmingConfig class**

In `src/config.py`, delete lines 127-137:
```python
# DELETE THIS ENTIRE BLOCK:
class BondFarmingConfig(BaseModel):
    enabled: bool = True
    min_yes_price: float = 0.90
    max_yes_price: float = 0.97
    bet_pct: float = 0.08
    max_total_bond_pct: float = 0.20
    max_concurrent: int = 3
    min_volume_24h: float = 5_000
    min_liquidity: float = 5_000
    max_days_to_resolution: float = 0.25
```

- [ ] **Step 2: Add UpsetHunterConfig class**

In `src/config.py`, at the same location (after PennyAlphaConfig, before LiveMomentumConfig), add:
```python
class UpsetHunterConfig(BaseModel):
    enabled: bool = True
    min_price: float = 0.05            # 5¢ minimum
    max_price: float = 0.15            # 15¢ maximum
    bet_pct: float = 0.02              # 2% bankroll per position
    max_concurrent: int = 3            # Max 3 upset positions
    stop_loss_pct: float = 0.50        # 50% SL (10¢ → 5¢)
    min_liquidity: float = 5_000       # Min CLOB liquidity
    min_odds_divergence: float = 0.05  # 5pt min divergence from Odds API
    max_hours_before_match: float = 48 # Max 48h before match
    late_match_exit_pct: float = 0.10  # Force exit at last 10%
    promotion_price: float = 0.35      # 35¢ → core exit rules
    scale_out_tier1_price: float = 0.25  # Tier 1 at 25¢
    scale_out_tier1_sell_pct: float = 0.30
    scale_out_tier2_price: float = 0.35  # Tier 2 at 35¢
    scale_out_tier2_sell_pct: float = 0.30
    trailing_activation: float = 1.00  # +100% to activate
    trailing_distance: float = 0.25    # 25% trail from peak
    max_hold_hours: float = 3.0        # Fallback exit if no match timing
```

- [ ] **Step 3: Update AppConfig**

In `src/config.py` line 202, replace:
```python
    bond_farming: BondFarmingConfig = BondFarmingConfig()
```
With:
```python
    upset_hunter: UpsetHunterConfig = UpsetHunterConfig()
```

- [ ] **Step 4: Verify config loads**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -c "from src.config import AppConfig; c = AppConfig(); print(c.upset_hunter); print('OK')"`
Expected: UpsetHunterConfig fields printed, "OK"

- [ ] **Step 5: Commit**

```bash
git add src/config.py
git commit -m "feat: replace BondFarmingConfig with UpsetHunterConfig"
```

---

### Task 2: Create upset_hunter.py — Pre-Filter Module

**Files:**
- Create: `src/upset_hunter.py`
- Delete: `src/bond_scanner.py`

- [ ] **Step 1: Delete bond_scanner.py**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
rm src/bond_scanner.py
```

- [ ] **Step 2: Create upset_hunter.py**

Create `src/upset_hunter.py`:
```python
"""Upset Hunter -- contrarian underdog strategy.

Buys YES tokens at 5-15¢ where favourite-longshot bias
creates systematic mispricing. Small bets, huge upside on wins.

Pre-filter pipeline (cheap, no AI):
    1. Price zone: 5-15¢
    2. Odds API divergence: min 5pt
    3. Liquidity: min $5,000
    4. Timing: max 48h before match, not past 75% if live
    5. Moneyline only (no draw/spread/total)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from src.models import MarketData

logger = logging.getLogger(__name__)

_ALT_SLUG = ("-draw", "-1h-", "-first-half-", "-total-", "-spread-", "-btts")


@dataclass
class UpsetCandidate:
    """A pre-filtered underdog market ready for AI evaluation."""
    condition_id: str
    question: str
    slug: str
    yes_price: float
    yes_token_id: str
    volume_24h: float
    liquidity: float
    odds_api_implied: Optional[float]  # Bookmaker implied prob, None if unavailable
    divergence: Optional[float]        # odds_api_implied - yes_price, None if no data
    hours_to_match: Optional[float]
    upset_type: str                    # "pre_match" | "early_live"
    event_id: str


def pre_filter(
    markets: List[MarketData],
    min_price: float = 0.05,
    max_price: float = 0.15,
    min_liquidity: float = 5_000,
    min_odds_divergence: float = 0.05,
    max_hours_before: float = 48,
) -> List[UpsetCandidate]:
    """Pre-filter markets for upset hunting candidates.

    Returns candidates sorted by divergence (highest first).
    No AI calls — purely programmatic cheap filters.
    """
    candidates = []

    for m in markets:
        # Filter 1: Price zone
        if m.yes_price < min_price or m.yes_price > max_price:
            continue

        # Filter 5: Moneyline only (check early to skip fast)
        if any(t in (m.slug or "").lower() for t in _ALT_SLUG):
            continue

        # Filter 3: Minimum liquidity
        if m.liquidity < min_liquidity:
            continue

        # Filter 4: Timing window
        hours_left = _hours_to_match(m.end_date_iso)
        if hours_left is not None:
            if hours_left > max_hours_before:
                continue  # Too far out
            if hours_left < 0:
                # Match started — check if past 75%
                elapsed_pct = _estimate_elapsed_pct(m)
                if elapsed_pct is not None and elapsed_pct > 0.75:
                    continue  # Too late for entry

        # Filter 2: Odds API divergence
        odds_implied = getattr(m, "odds_api_implied_prob", None)
        divergence = None
        if odds_implied is not None and odds_implied > 0:
            divergence = odds_implied - m.yes_price
            if divergence < min_odds_divergence:
                continue  # Not enough divergence
        # If no Odds API data, skip this filter (pass to AI with note)

        # Determine upset type
        if hours_left is not None and hours_left < 0:
            upset_type = "early_live"
        else:
            upset_type = "pre_match"

        candidates.append(UpsetCandidate(
            condition_id=m.condition_id,
            question=m.question,
            slug=m.slug or "",
            yes_price=m.yes_price,
            yes_token_id=m.yes_token_id,
            volume_24h=m.volume_24h,
            liquidity=m.liquidity,
            odds_api_implied=odds_implied,
            divergence=divergence,
            hours_to_match=hours_left,
            upset_type=upset_type,
            event_id=getattr(m, "event_id", "") or "",
        ))

    # Sort by divergence (highest first), None-divergence last
    candidates.sort(key=lambda c: c.divergence if c.divergence is not None else -1, reverse=True)
    logger.info("Upset hunter pre-filter: %d candidates from %d markets", len(candidates), len(markets))
    return candidates


def size_upset_position(
    bankroll: float,
    bet_pct: float = 0.02,
    current_upset_count: int = 0,
    max_concurrent: int = 3,
) -> float:
    """Calculate upset position size. Returns USDC amount (0.0 if not eligible)."""
    if current_upset_count >= max_concurrent:
        return 0.0
    return max(0.0, bankroll * bet_pct)


def _hours_to_match(end_date_iso: str) -> Optional[float]:
    """Hours until match/resolution. Negative = already started."""
    if not end_date_iso:
        return None
    try:
        from datetime import datetime, timezone
        end = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (end - now).total_seconds() / 3600
    except (ValueError, TypeError):
        return None


def _estimate_elapsed_pct(m: MarketData) -> Optional[float]:
    """Rough estimate of match elapsed percentage from available data."""
    if getattr(m, "match_start_iso", None):
        try:
            from datetime import datetime, timezone
            start = datetime.fromisoformat(m.match_start_iso.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            elapsed_min = (now - start).total_seconds() / 60
            # Use 120 min as default match duration estimate
            return min(elapsed_min / 120, 1.0)
        except (ValueError, TypeError):
            pass
    return None
```

- [ ] **Step 3: Verify module imports**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -c "from src.upset_hunter import pre_filter, size_upset_position, UpsetCandidate; print('OK')"`
Expected: "OK"

- [ ] **Step 4: Commit**

```bash
git add src/upset_hunter.py
git rm src/bond_scanner.py
git commit -m "feat: add upset_hunter.py, delete bond_scanner.py"
```

---

### Task 3: Agent.py — Replace _check_bond_farming with _check_upset_hunter

**Files:**
- Modify: `src/agent.py:442-444` (call site)
- Modify: `src/agent.py:1086-1171` (method replacement)

- [ ] **Step 1: Update call site**

In `src/agent.py`, replace lines 442-444:
```python
        # Bond farming, live dip, live momentum -- all skip when entries paused
        if entries_allowed:
            self._check_bond_farming(fresh_markets, bankroll)
```
With:
```python
        # Upset hunter, live dip, live momentum -- all skip when entries paused
        if entries_allowed:
            self._check_upset_hunter(fresh_markets, bankroll)
```

- [ ] **Step 2: Replace the method**

In `src/agent.py`, delete the entire `_check_bond_farming` method (lines 1086-1171) and replace with:
```python
    # ── Upset Hunter & Penny scanners ─────────────────────────────────────

    def _check_upset_hunter(self, fresh_markets: list, bankroll: float) -> None:
        """Scan for upset hunting opportunities -- underdog YES tokens $0.05-0.15."""
        if not fresh_markets:
            return
        from src.upset_hunter import pre_filter, size_upset_position

        cfg = self.config.upset_hunter
        if not cfg.enabled:
            return

        # Count current upset positions
        upset_count = sum(1 for p in self.portfolio.positions.values()
                          if getattr(p, "entry_reason", "") == "upset")

        candidates = pre_filter(
            fresh_markets,
            min_price=cfg.min_price,
            max_price=cfg.max_price,
            min_liquidity=cfg.min_liquidity,
            min_odds_divergence=cfg.min_odds_divergence,
            max_hours_before=cfg.max_hours_before_match,
        )

        for c in candidates:
            if upset_count >= cfg.max_concurrent:
                break
            if self.portfolio.active_position_count >= self.config.risk.max_positions:
                break
            if c.condition_id in self.portfolio.positions:
                continue
            if self.blacklist.is_blocked(c.condition_id, self.cycle_count):
                continue
            if c.condition_id in self._exited_markets:
                continue

            size = size_upset_position(
                bankroll, bet_pct=cfg.bet_pct,
                current_upset_count=upset_count,
                max_concurrent=cfg.max_concurrent,
            )
            if size < 5.0:
                continue

            # AI analysis with underdog prompt
            if self.ai_analyst:
                odds_note = ""
                if c.divergence is not None:
                    odds_note = f"Odds API implied: {c.odds_api_implied:.0%}, Polymarket: {c.yes_price:.0%}, divergence: {c.divergence:.0%}"
                else:
                    odds_note = "No bookmaker cross-reference available for this market."

                from src.models import MarketData as MD
                # Find the original MarketData for AI analysis
                market_data = None
                for m in fresh_markets:
                    if m.condition_id == c.condition_id:
                        market_data = m
                        break
                if not market_data:
                    continue

                estimate = self.ai_analyst.analyze_market(
                    market_data,
                    esports_context=odds_note,
                    upset_mode=True,
                )

                # Check AI confidence and edge
                if estimate.confidence in ("C", "D"):
                    continue
                ai_edge = estimate.ai_probability - c.yes_price
                if ai_edge < cfg.min_odds_divergence:  # Use same 5% min edge
                    continue

            # Execute order
            token_id = c.yes_token_id
            if not token_id:
                for m in fresh_markets:
                    if m.condition_id == c.condition_id:
                        token_id = m.yes_token_id
                        break
            if not token_id:
                continue

            result = self.executor.place_order(token_id, "BUY", c.yes_price, size)
            if not result or result.get("status") == "error":
                continue

            shares = size / c.yes_price if c.yes_price > 0 else 0
            self.portfolio.add_position(
                c.condition_id, token_id, "BUY_YES",
                c.yes_price, size, shares, c.slug,
                "", confidence=estimate.confidence if self.ai_analyst else "B-",
                ai_probability=estimate.ai_probability if self.ai_analyst else c.yes_price,
                entry_reason="upset",
                end_date_iso="",
            )
            upset_count += 1

            self.trade_log.log({
                "market": c.slug, "action": "UPSET_ENTRY",
                "size": size, "price": c.yes_price,
                "upset_type": c.upset_type,
                "odds_divergence": c.divergence,
                "ai_probability": estimate.ai_probability if self.ai_analyst else None,
                "mode": self.config.mode.value,
            })
            logger.info(
                "UPSET ENTRY: %s | type=%s | price=%.2f | div=%s | size=$%.0f",
                c.slug[:40], c.upset_type, c.yes_price,
                f"{c.divergence:.0%}" if c.divergence else "N/A", size,
            )
            self.notifier.send(
                f"🎯 *UPSET ENTRY*: {c.slug[:40]}\n\n"
                f"🏷 Type: {c.upset_type}\n"
                f"📊 Price: {c.yes_price:.2f} | Div: {c.divergence:.0%}" if c.divergence else f"📊 Price: {c.yes_price:.2f}" + "\n"
                f"💰 Size: ${size:.0f}"
            )
```

- [ ] **Step 3: Verify no bond references remain in agent.py**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && grep -n "bond" src/agent.py`
Expected: No matches (or only in comments that should be cleaned)

- [ ] **Step 4: Commit**

```bash
git add src/agent.py
git commit -m "feat: replace _check_bond_farming with _check_upset_hunter in agent"
```

---

### Task 4: AI Analyst — Add Underdog Prompt Mode

**Files:**
- Modify: `src/ai_analyst.py:351-379` (analyze_market signature)
- Modify: `src/ai_analyst.py:426-475` (_build_prompt method)

- [ ] **Step 1: Add upset_mode parameter to analyze_market**

In `src/ai_analyst.py`, change line 351-353:
```python
    def analyze_market(
        self, market: MarketData, news_context: str = "",
        esports_context: str = "",
    ) -> AIEstimate:
```
To:
```python
    def analyze_market(
        self, market: MarketData, news_context: str = "",
        esports_context: str = "",
        upset_mode: bool = False,
    ) -> AIEstimate:
```

- [ ] **Step 2: Pass upset_mode to _build_prompt**

In `src/ai_analyst.py`, change line 379:
```python
        prompt = self._build_prompt(market, news_context, esports_context)
```
To:
```python
        prompt = self._build_prompt(market, news_context, esports_context, upset_mode=upset_mode)
```

- [ ] **Step 3: Add upset_mode to _build_prompt and inject underdog lens**

In `src/ai_analyst.py`, change line 426-427:
```python
    def _build_prompt(
        self, market: MarketData, news_context: str, esports_context: str = ""
    ) -> str:
```
To:
```python
    def _build_prompt(
        self, market: MarketData, news_context: str, esports_context: str = "",
        upset_mode: bool = False,
    ) -> str:
```

Then, after the `parts` list is built (after line 438), add the underdog analytical lens:
```python
        if upset_mode:
            parts.append("""
=== UNDERDOG ANALYSIS MODE ===
This market has a YES token priced at 5-15¢ (heavy underdog).
Your task is NOT "will this team win?" but "is this team MORE likely to win than the market implies?"

Focus on:
- Favorite's vulnerabilities: form drop, injuries, motivation, fatigue, travel schedule
- Underdog's hidden strengths: recent form trajectory, style/matchup advantage, home court/field
- Historical upset frequency for this type of matchup
- Match conditions that favor the underdog (tennis surface, esports map pool, weather)

CALIBRATION NOTE: Markets systematically overprice favorites and underprice underdogs
(favourite-longshot bias). A team priced at 10¢ often has a true probability of 13-18%.
For esports BO1 formats, upset frequency is 25-35% — significantly higher than implied odds suggest.
Do NOT anchor to the low market price. Form your own estimate independently.""")
```

- [ ] **Step 4: Verify ai_analyst still imports**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -c "from src.ai_analyst import AIAnalyst; print('OK')"`
Expected: "OK"

- [ ] **Step 5: Commit**

```bash
git add src/ai_analyst.py
git commit -m "feat: add upset_mode underdog prompt to AI analyst"
```

---

### Task 5: Exit Monitor — Upset-Specific SL and Trailing TP

**Files:**
- Modify: `src/exit_monitor.py:112-121` (stop-loss check)
- Modify: `src/exit_monitor.py:123-153` (trailing TP check)

- [ ] **Step 1: Upset-specific stop-loss**

In `src/exit_monitor.py`, replace lines 112-113:
```python
        # 1. Stop-loss check -- same for all sports
        sl_pct = self.config.risk.stop_loss_pct
```
With:
```python
        # 1. Stop-loss check -- upset positions use wider SL
        if pos.entry_reason == "upset":
            sl_pct = self.config.upset_hunter.stop_loss_pct  # 50%
        else:
            sl_pct = self.config.risk.stop_loss_pct  # 30%
```

- [ ] **Step 2: Upset-specific trailing TP parameters**

In `src/exit_monitor.py`, after line 125 (`if ttp_cfg.enabled and not pos.volatility_swing:`), add upset-specific parameter override. Replace lines 144-152:
```python
            if pos.peak_pnl_pct >= ttp_cfg.activation_pct:
                ttp_result = calculate_trailing_tp(
                    entry_price=entry,
                    current_price=current,
                    direction=direction,
                    peak_price=pos.peak_price,
                    trailing_active=True,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=ttp_cfg.trail_distance,
                )
```
With:
```python
            # Upset positions: wider activation (+100%) and trail (25%)
            if pos.entry_reason == "upset":
                upset_cfg = self.config.upset_hunter
                act_pct = upset_cfg.trailing_activation  # 1.00 (+100%)
                trail_dist = upset_cfg.trailing_distance  # 0.25
                # Check promotion: if price >= promotion threshold, switch to core params
                if effective_current >= upset_cfg.promotion_price:
                    act_pct = ttp_cfg.activation_pct    # Core: 0.20
                    trail_dist = ttp_cfg.trail_distance  # Core: 0.08
            else:
                act_pct = ttp_cfg.activation_pct
                trail_dist = ttp_cfg.trail_distance

            if pos.peak_pnl_pct >= act_pct:
                ttp_result = calculate_trailing_tp(
                    entry_price=entry,
                    current_price=current,
                    direction=direction,
                    peak_price=pos.peak_price,
                    trailing_active=True,
                    activation_pct=act_pct,
                    trail_distance=trail_dist,
                )
```

- [ ] **Step 3: Verify exit_monitor imports**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -c "from src.exit_monitor import ExitMonitor; print('OK')"`
Expected: "OK"

- [ ] **Step 4: Commit**

```bash
git add src/exit_monitor.py
git commit -m "feat: upset-specific SL (50%) and trailing TP (100%/25%) in exit monitor"
```

---

### Task 6: Match Exit — Forced Exit at Last 10%

**Files:**
- Modify: `src/match_exit.py:297-300` (after elapsed_pct calculation)

- [ ] **Step 1: Add forced upset exit**

In `src/match_exit.py`, after line 296 (the elapsed_pct calculation try/except), before the `if elapsed_pct < 0:` check at line 297, add:

```python
    # --- Upset Hunter: forced exit at last 10% of match ---
    entry_reason = data.get("entry_reason", "")
    if entry_reason == "upset" and elapsed_pct >= 0.90:
        return {**result, "exit": True, "layer": "upset_forced_exit",
                "reason": f"Upset hunter: match {elapsed_pct:.0%} done, forced exit"}
    if entry_reason == "upset" and elapsed_pct < 0 and data.get("hold_hours", 0) >= 3.0:
        # Fallback: no match timing, held too long, check if losing
        if pnl_pct < 0:
            return {**result, "exit": True, "layer": "upset_max_hold",
                    "reason": f"Upset hunter: held {data.get('hold_hours', 0):.1f}h with no timing, PnL {pnl_pct:.1%}"}
```

Note: `pnl_pct` must be calculated before this block. Check that it exists at this point in the function — it should be available from the effective_entry/effective_current calculation earlier in the function.

- [ ] **Step 2: Verify match_exit imports**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -c "from src.match_exit import check_match_exit; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```bash
git add src/match_exit.py
git commit -m "feat: forced exit at last 10% of match for upset positions"
```

---

### Task 7: Scale-Out — Upset-Specific 3-Tier

**Files:**
- Modify: `src/scale_out.py:21-44` (check_scale_out function)

- [ ] **Step 1: Add entry_reason parameter and upset tiers**

In `src/scale_out.py`, replace lines 21-44:
```python
def check_scale_out(
    scale_out_tier: int, unrealized_pnl_pct: float, volatility_swing: bool
) -> dict | None:
    """Check if position qualifies for next scale-out tier. Pure function."""
    if volatility_swing:
        return None

    if scale_out_tier == 0 and unrealized_pnl_pct >= 0.25:
        return {
            "action": "scale_out",
            "tier": "tier1_risk_free",
            "sell_pct": 0.40,
            "reason": f"Tier 1: Risk-free at +{unrealized_pnl_pct:.0%}",
        }

    if scale_out_tier == 1 and unrealized_pnl_pct >= 0.50:
        return {
            "action": "scale_out",
            "tier": "tier2_profit_lock",
            "sell_pct": 0.50,
            "reason": f"Tier 2: Profit lock at +{unrealized_pnl_pct:.0%}",
        }

    return None
```
With:
```python
def check_scale_out(
    scale_out_tier: int, unrealized_pnl_pct: float, volatility_swing: bool,
    entry_reason: str = "", current_price: float = 0.0,
    upset_tier1_price: float = 0.25, upset_tier2_price: float = 0.35,
    upset_tier1_sell: float = 0.30, upset_tier2_sell: float = 0.30,
) -> dict | None:
    """Check if position qualifies for next scale-out tier. Pure function."""
    if volatility_swing:
        return None

    # Upset positions: scale out by absolute price, not PnL percentage
    if entry_reason == "upset":
        if scale_out_tier == 0 and current_price >= upset_tier1_price:
            return {
                "action": "scale_out",
                "tier": "upset_tier1",
                "sell_pct": upset_tier1_sell,
                "reason": f"Upset Tier 1: price {current_price:.2f} >= {upset_tier1_price:.2f}",
            }
        if scale_out_tier == 1 and current_price >= upset_tier2_price:
            return {
                "action": "scale_out",
                "tier": "upset_tier2",
                "sell_pct": upset_tier2_sell,
                "reason": f"Upset Tier 2: price {current_price:.2f} >= {upset_tier2_price:.2f}, remaining promoted to core",
            }
        return None

    # Standard positions: PnL-based tiers
    if scale_out_tier == 0 and unrealized_pnl_pct >= 0.25:
        return {
            "action": "scale_out",
            "tier": "tier1_risk_free",
            "sell_pct": 0.40,
            "reason": f"Tier 1: Risk-free at +{unrealized_pnl_pct:.0%}",
        }

    if scale_out_tier == 1 and unrealized_pnl_pct >= 0.50:
        return {
            "action": "scale_out",
            "tier": "tier2_profit_lock",
            "sell_pct": 0.50,
            "reason": f"Tier 2: Profit lock at +{unrealized_pnl_pct:.0%}",
        }

    return None
```

- [ ] **Step 2: Find and update all callers of check_scale_out**

Search for all calls to `check_scale_out` and add the new parameters:

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && grep -rn "check_scale_out" src/`

For each caller, add `entry_reason=pos.entry_reason, current_price=current_price` to the call. The new params have defaults so existing callers won't break, but they should be updated for upset positions to work correctly.

- [ ] **Step 3: Verify scale_out imports**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -c "from src.scale_out import check_scale_out; print(check_scale_out(0, 0.30, False)); print('OK')"`
Expected: Standard tier1 result dict, "OK"

- [ ] **Step 4: Commit**

```bash
git add src/scale_out.py
git commit -m "feat: upset-specific 3-tier scale-out by absolute price (25¢/35¢)"
```

---

### Task 8: Trade Logger & analyze_pnl — Update Edge Sources

**Files:**
- Modify: `src/trade_logger.py:74-75` (edge source comment)
- Modify: `analyze_pnl.py:75` (action filter)

- [ ] **Step 1: Update edge source documentation**

In `src/trade_logger.py`, replace lines 74-75:
```python
    Edge sources: "ai_standard", "ai_anchored", "bond_farming", "live_momentum",
                  "penny_alpha", "fav_time_gate", "volatility_swing", "farming_reentry"
```
With:
```python
    Edge sources: "ai_standard", "ai_anchored", "upset_hunter", "live_momentum",
                  "penny_alpha", "fav_time_gate", "volatility_swing", "farming_reentry"
```

- [ ] **Step 2: Update analyze_pnl.py action filter**

In `analyze_pnl.py`, replace line 75:
```python
    if action in ("BUY", "LIVE_DIP_BUY_YES", "LIVE_DIP_BUY_NO", "BOND_ENTRY"):
```
With:
```python
    if action in ("BUY", "LIVE_DIP_BUY_YES", "LIVE_DIP_BUY_NO", "BOND_ENTRY", "UPSET_ENTRY"):
```

Note: `BOND_ENTRY` kept for historical log compatibility.

- [ ] **Step 3: Commit**

```bash
git add src/trade_logger.py analyze_pnl.py
git commit -m "feat: update edge sources and PnL analyzer for upset_hunter"
```

---

### Task 9: Final Verification — Zero Bond References

- [ ] **Step 1: Search for any remaining bond references**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && grep -rn -i "bond" src/ --include="*.py" | grep -v "__pycache__"`
Expected: No matches in active source code (only in docs/ or historical trade logs)

- [ ] **Step 2: Verify full import chain**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -c "from src.agent import Agent; print('Agent imports OK')"`
Expected: "Agent imports OK"

- [ ] **Step 3: Verify config round-trip**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -c "
from src.config import AppConfig
c = AppConfig()
assert not hasattr(c, 'bond_farming'), 'bond_farming still exists!'
assert hasattr(c, 'upset_hunter'), 'upset_hunter missing!'
print('Config clean:', c.upset_hunter.model_dump())
"`
Expected: UpsetHunterConfig dict printed

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: verify zero bond references, upset hunter migration complete"
```
