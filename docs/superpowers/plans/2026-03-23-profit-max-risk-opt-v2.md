# Profit Maximization & Risk Optimization v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 18 risk/exit/re-entry improvements + fix BUY_NO direction bugs across the Polymarket prediction bot.

**Architecture:** 6 phases — Phase 0 fixes critical BUY_NO bugs in existing code, Phases 1-5 add new features. Each phase produces working, testable software. New logic lives in dedicated modules; existing files get surgical modifications.

**Tech Stack:** Python 3.14, Pydantic BaseModel, pytest, Polymarket CLOB API

**Spec:** `docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md`
**v1 Spec:** `docs/superpowers/specs/2026-03-22-match-aware-exit-system-design.md`

---

## File Structure

```
src/
├── match_exit.py          # MODIFY: BUY_NO direction fixes, momentum v2, re-entry floor, score_terminal split, elapsed_pct in result
├── circuit_breaker.py     # CREATE: Portfolio-level loss limits
├── edge_decay.py          # CREATE: AI signal freshness
├── scale_out.py           # CREATE: 3-tier partial exit
├── trailing_sigma.py      # CREATE: σ-based trailing stop
├── vs_spike.py            # CREATE: Velocity-based VS spike detection
├── reentry.py             # CREATE: Re-entry eligibility, blacklist, snowball, grace period
├── correlation.py         # CREATE: Match-level exposure tracking
├── models.py              # MODIFY: +new Position fields, +PartialExit model
├── portfolio.py           # MODIFY: +scale_out check, +σ-trailing, +buffer population, +skip flat SL
├── risk_manager.py        # MODIFY: +adaptive kelly adjustments
├── config.py              # MODIFY: +new config sections
├── main.py                # MODIFY: integration of all systems, _exit_position extension, blacklist replacement

tests/
├── test_match_exit.py     # MODIFY: +BUY_NO direction tests, +momentum v2, +re-entry floor
├── test_circuit_breaker.py # CREATE
├── test_edge_decay.py     # CREATE
├── test_scale_out.py      # CREATE
├── test_trailing_sigma.py # CREATE
├── test_vs_spike.py       # CREATE
├── test_reentry.py        # CREATE
├── test_correlation.py    # CREATE
├── test_scale_in.py       # CREATE
├── test_integration.py    # CREATE: Multi-module integration tests
```

---

## Phase 0: BUY_NO Direction Fixes in match_exit.py

### Task 1: Add effective price conversion + fix catastrophic floor

**Context:** ALL price comparisons in `match_exit.py` use raw YES token prices. For BUY_NO positions, this means every layer is broken. See v2 spec section 9a-9f.

**Files:**
- Modify: `src/match_exit.py:185-330`
- Modify: `tests/test_match_exit.py`

- [ ] **Step 1: Write BUY_NO catastrophic floor test**

```python
# tests/test_match_exit.py — add to existing file

class TestBuyNoDirection:
    """BUY_NO positions must use effective prices (1 - YES price)."""

    def _make_data(self, **overrides):
        base = {
            "entry_price": 0.65,  # YES price — effective entry for BUY_NO = 0.35
            "current_price": 0.65,
            "direction": "BUY_NO",
            "number_of_games": 3,
            "slug": "cs2-test-match",
            "match_score": "",
            "match_start_iso": (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat(),
            "ever_in_profit": False,
            "peak_pnl_pct": 0.0,
            "scouted": False,
            "confidence": "medium",
            "ai_probability": 0.5,
            "consecutive_down_cycles": 0,
            "cumulative_drop": 0.0,
            "hold_revoked_at": None,
            "hold_was_original": False,
            "volatility_swing": False,
            "unrealized_pnl_pct": 0.0,
            "entry_reason": "",
            "cycles_held": 0,
        }
        base.update(overrides)
        return base

    def test_catastrophic_floor_buy_no_triggers_on_adverse_move(self):
        """BUY_NO at YES=0.35 (eff=0.65). YES rises to 0.85 (eff=0.15).
        Eff 0.15 < eff_entry 0.65 * 0.50 = 0.325 → should EXIT."""
        from src.match_exit import check_match_exit
        data = self._make_data(entry_price=0.35, current_price=0.85)
        result = check_match_exit(data)
        assert result["exit"] is True
        assert result["layer"] == "catastrophic_floor"

    def test_catastrophic_floor_buy_no_no_false_trigger(self):
        """BUY_NO at YES=0.65 (eff=0.35). YES drops to 0.50 (eff=0.50).
        Eff 0.50 > eff_entry 0.35 * 0.50 = 0.175 → should NOT exit (we're profiting)."""
        from src.match_exit import check_match_exit
        data = self._make_data(entry_price=0.65, current_price=0.50)
        result = check_match_exit(data)
        assert result["exit"] is False or result["layer"] != "catastrophic_floor"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::TestBuyNoDirection -v`
Expected: FAIL (current code uses raw prices)

- [ ] **Step 3: Implement effective price conversion in check_match_exit()**

In `src/match_exit.py`, modify `check_match_exit()` starting at line 185:

```python
def check_match_exit(data: dict) -> dict:
    result = {"exit": False, "layer": "", "reason": "",
              "revoke_hold": False, "restore_hold": False, "momentum_tighten": False,
              "elapsed_pct": -1.0}  # NEW: return elapsed_pct for tiered blacklist

    entry_price = data["entry_price"]
    current_price = data["current_price"]
    direction = data.get("direction", "BUY_YES")

    # NEW: Direction-aware effective prices
    effective_entry = entry_price if direction == "BUY_YES" else (1 - entry_price)
    effective_current = current_price if direction == "BUY_YES" else (1 - current_price)

    # ... existing field extraction unchanged ...
```

Then replace ALL price comparisons:

**Catastrophic floor (line ~240):**
```python
    # OLD: if entry_price >= 0.25 and current_price < entry_price * 0.50:
    # NEW:
    is_reentry = data.get("entry_reason", "").startswith("re_entry") or data.get("entry_reason") == "scale_in"
    cat_floor_mult = 0.75 if is_reentry else 0.50
    if effective_entry >= 0.25 and effective_current < effective_entry * cat_floor_mult:
        return {**result, "exit": True, "layer": "catastrophic_floor",
                "reason": f"Price eff:{effective_current:.3f} < eff_entry*{cat_floor_mult:.0%} ({effective_entry*cat_floor_mult:.3f})"}
```

**Ultra-low guard (line ~263):**
```python
    # OLD: if entry_price < 0.09 and elapsed_pct >= 0.90 and current_price < 0.05:
    # NEW:
    if effective_entry < 0.09 and elapsed_pct >= 0.90 and effective_current < 0.05:
```

**Graduated SL (line ~268):**
```python
    # OLD: max_loss = get_graduated_max_loss(elapsed_pct, entry_price, score_info)
    # NEW:
    max_loss = get_graduated_max_loss(elapsed_pct, effective_entry, score_info)
```

**Never-in-profit (line ~281-289):**
```python
    # Replace current_price with effective_current, entry_price with effective_entry:
    if not ever_in_profit and peak_pnl_pct <= 0.01 and elapsed_pct >= 0.70:
        score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
        if score_ahead:
            pass
        elif effective_current >= effective_entry * 0.90:
            pass
        elif effective_current < effective_entry * 0.75:
            return {**result, "exit": True, "layer": "never_in_profit",
                    "reason": f"Never profited + 70%+ done + eff_price {effective_current:.3f} < eff_entry*75%"}
```

**Hold revocation (line ~302-328):**
```python
    # Replace all current_price/entry_price with effective_current/effective_entry
    if is_hold_candidate:
        dip_is_temporary = (consecutive_down < 3 or cumulative_drop < 0.05)

        if ever_in_profit and effective_current < effective_entry * 0.70 and elapsed_pct > 0.60:
            score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
            if not score_ahead and not dip_is_temporary:
                result["revoke_hold"] = True
                result["reason"] = f"Hold revoked: eff_price {effective_current:.3f} < eff_entry*70%"

        if not ever_in_profit and effective_current < effective_entry * 0.75 and elapsed_pct > 0.70:
            score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
            if not score_ahead and not dip_is_temporary:
                result["revoke_hold"] = True
                result["exit"] = True
                result["layer"] = "hold_revoked"
                result["reason"] = f"Hold revoked + exit: eff_price {effective_current:.3f} < eff_entry*75%"

    # Restore check:
    if hold_was_original and not scouted and hold_revoked_at:
        # ...existing parse logic...
        if minutes_since >= 10 and effective_current > effective_entry * 0.85:
            score_behind = score_info.get("available") and score_info.get("map_diff", 0) < 0
            if not score_behind:
                result["restore_hold"] = True
```

Also add `elapsed_pct` to the result dict at the end:
```python
    result["elapsed_pct"] = elapsed_pct
    return result
```

- [ ] **Step 4: Run BUY_NO tests + all existing tests**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py -v`
Expected: ALL PASS (new BUY_NO tests + existing tests unchanged)

- [ ] **Step 5: Add score_terminal split**

In `check_match_exit()`, change score terminal returns:
```python
    # OLD: return {"exit": True, "layer": "score_terminal", ...}
    # NEW:
    if score_info.get("is_already_lost"):
        return {**result, "exit": True, "layer": "score_terminal_loss",
                "reason": f"Match already lost (score: {match_score})"}
    if score_info.get("is_already_won"):
        return {**result, "exit": False, "layer": "score_terminal_win",
                "reason": f"Match already won — hold to resolve (score: {match_score})"}
```

Update existing tests that check `layer == "score_terminal"` to use the new values.

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/match_exit.py tests/test_match_exit.py
git commit -m "fix: BUY_NO direction in match_exit + score_terminal split + elapsed_pct in result"
```

---

### Task 2: Momentum Tightening v2

**Files:**
- Modify: `src/match_exit.py:270-275`
- Modify: `tests/test_match_exit.py`

- [ ] **Step 1: Write momentum v2 tests**

```python
# tests/test_match_exit.py — add to TestBuyNoDirection or new class

class TestMomentumTighteningV2:
    def _make_data(self, **overrides):
        base = {
            "entry_price": 0.50, "current_price": 0.35, "direction": "BUY_YES",
            "number_of_games": 3, "slug": "cs2-test",
            "match_score": "", "match_start_iso": (datetime.now(timezone.utc) - timedelta(minutes=80)).isoformat(),
            "ever_in_profit": False, "peak_pnl_pct": 0.0, "scouted": False,
            "confidence": "medium", "ai_probability": 0.5,
            "consecutive_down_cycles": 0, "cumulative_drop": 0.0,
            "hold_revoked_at": None, "hold_was_original": False,
            "volatility_swing": False, "unrealized_pnl_pct": -0.30,
            "entry_reason": "", "cycles_held": 10,
        }
        base.update(overrides)
        return base

    def test_deeper_tier_fires_at_5_cycles_10c(self):
        """5+ consecutive down, 10c+ drop → ×0.60 (not ×0.75)."""
        from src.match_exit import check_match_exit
        data = self._make_data(consecutive_down_cycles=6, cumulative_drop=0.12)
        result = check_match_exit(data)
        assert result["momentum_tighten"] is True
        assert result["momentum_multiplier"] == 0.60  # Deeper tier

    def test_moderate_tier_fires_at_3_cycles_5c(self):
        """3 consecutive down, 5c drop → ×0.75."""
        from src.match_exit import check_match_exit
        data = self._make_data(consecutive_down_cycles=3, cumulative_drop=0.06)
        result = check_match_exit(data)
        assert result["momentum_tighten"] is True
        assert result["momentum_multiplier"] == 0.75  # Moderate tier

    def test_deeper_tier_not_reachable_at_3_cycles(self):
        """3 cycles, 12c drop → moderate tier (×0.75) not deeper."""
        from src.match_exit import check_match_exit
        data = self._make_data(consecutive_down_cycles=3, cumulative_drop=0.12)
        # Should fire moderate, not deeper (need 5+ cycles for deeper)
        result = check_match_exit(data)
        assert result["momentum_tighten"] is True
        assert result["momentum_multiplier"] == 0.75  # Only moderate — need 5+ cycles for 0.60
```

- [ ] **Step 2: Run to verify behavior**

Run: `python -m pytest tests/test_match_exit.py::TestMomentumTighteningV2 -v`

- [ ] **Step 3: Implement deeper tier (swap if/elif order)**

In `src/match_exit.py`, replace the momentum tightening block (around line 271-274):

```python
    # Check DEEPER tier first (5+ is subset of 3+, must come first):
    if consecutive_down >= 5 and cumulative_drop >= 0.10:
        result["momentum_tighten"] = True
        result["momentum_multiplier"] = 0.60
        max_loss = max(0.05, max_loss * 0.60)
    elif consecutive_down >= 3 and cumulative_drop >= 0.05:
        result["momentum_tighten"] = True
        result["momentum_multiplier"] = 0.75
        max_loss = max(0.05, max_loss * 0.75)
```

- [ ] **Step 4: Run all match_exit tests**

Run: `python -m pytest tests/test_match_exit.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/match_exit.py tests/test_match_exit.py
git commit -m "feat: momentum tightening v2 — deeper tier at 5+cycles/10c+"
```

---

## Phase 1: Risk Foundation

### Task 3: Circuit Breaker (#14)

**Files:**
- Create: `src/circuit_breaker.py`
- Create: `tests/test_circuit_breaker.py`

- [ ] **Step 1: Write circuit breaker tests**

```python
# tests/test_circuit_breaker.py
import pytest
from datetime import datetime, timezone, timedelta


class TestCircuitBreaker:
    def _make_breaker(self):
        from src.circuit_breaker import CircuitBreaker
        return CircuitBreaker()

    def test_no_halt_initially(self):
        cb = self._make_breaker()
        halt, reason = cb.should_halt_entries()
        assert halt is False

    def test_daily_limit_triggers(self):
        cb = self._make_breaker()
        # Simulate -9% daily loss
        cb.record_exit(-90.0, 1000.0)  # -9%
        halt, reason = cb.should_halt_entries()
        assert halt is True
        assert "Daily" in reason or "daily" in reason

    def test_hourly_limit_triggers(self):
        cb = self._make_breaker()
        cb.record_exit(-60.0, 1000.0)  # -6% in one hour
        halt, reason = cb.should_halt_entries()
        assert halt is True

    def test_consecutive_losses_trigger(self):
        cb = self._make_breaker()
        for _ in range(4):
            cb.record_exit(-5.0, 1000.0)
        halt, reason = cb.should_halt_entries()
        assert halt is True
        assert "consecutive" in reason.lower()

    def test_winning_exit_resets_consecutive(self):
        cb = self._make_breaker()
        cb.record_exit(-5.0, 1000.0)
        cb.record_exit(-5.0, 1000.0)
        cb.record_exit(10.0, 1000.0)  # Win resets
        cb.record_exit(-5.0, 1000.0)
        halt, _ = cb.should_halt_entries()
        assert halt is False  # Only 1 consecutive loss

    def test_soft_block_at_3pct(self):
        cb = self._make_breaker()
        # -35.0 on 1000 = -3.5% daily. Below soft block -3% but above hourly -5%.
        # No internal state manipulation needed — this naturally hits soft block only.
        cb.record_exit(-35.0, 1000.0)
        halt, reason = cb.should_halt_entries()
        assert halt is True
        assert "soft" in reason.lower() or "limit" in reason.lower()

    def test_below_soft_block_no_halt(self):
        cb = self._make_breaker()
        # -25.0 on 1000 = -2.5%. Below soft block -3% threshold.
        cb.record_exit(-25.0, 1000.0)
        halt, _ = cb.should_halt_entries()
        assert halt is False  # -2.5% > -3%, no soft block

    def test_hourly_reset(self):
        cb = self._make_breaker()
        cb.record_exit(-60.0, 1000.0)
        # Simulate 61 minutes passing
        cb.last_hourly_reset = datetime.now(timezone.utc) - timedelta(minutes=61)
        cb.reset_if_needed()
        assert cb.hourly_realized_pnl_pct == 0.0

    def test_never_halts_exits(self):
        """Circuit breaker should return halt status, but callers must never use it to block exits."""
        cb = self._make_breaker()
        cb.record_exit(-90.0, 1000.0)
        halt, _ = cb.should_halt_entries()
        assert halt is True  # Entries halted, but exits are caller's responsibility

    def test_persistence_fields(self):
        cb = self._make_breaker()
        state = cb.to_dict()
        assert "daily_realized_pnl_pct" in state
        assert "last_daily_reset" in state

        from src.circuit_breaker import CircuitBreaker
        cb2 = CircuitBreaker.from_dict(state)
        assert cb2.daily_realized_pnl_pct == cb.daily_realized_pnl_pct
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_circuit_breaker.py -v`
Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Implement circuit_breaker.py**

```python
# src/circuit_breaker.py
"""Portfolio-level circuit breaker — halts new entries on excessive losses.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #14
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DAILY_MAX_LOSS_PCT = -0.08
HOURLY_MAX_LOSS_PCT = -0.05
CONSECUTIVE_LOSS_LIMIT = 4
COOLDOWN_AFTER_DAILY = 120
COOLDOWN_AFTER_HOURLY = 60
COOLDOWN_AFTER_CONSECUTIVE = 60
ENTRY_BLOCK_THRESHOLD = -0.03  # Soft block at -3% daily (fires before hourly -5% hard limit)
STATE_FILE = Path("logs/circuit_breaker_state.json")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CircuitBreaker:
    def __init__(self):
        self.daily_realized_pnl_pct: float = 0.0
        self.hourly_realized_pnl_pct: float = 0.0
        self.consecutive_losses: int = 0
        self.breaker_active_until: datetime | None = None
        self.last_daily_reset: datetime = _now()
        self.last_hourly_reset: datetime = _now()

    def record_exit(self, pnl_usd: float, portfolio_value: float) -> None:
        pnl_pct = pnl_usd / portfolio_value if portfolio_value > 0 else 0
        self.daily_realized_pnl_pct += pnl_pct
        self.hourly_realized_pnl_pct += pnl_pct
        if pnl_usd < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def reset_if_needed(self) -> None:
        now = _now()
        if (now - self.last_daily_reset).total_seconds() >= 86400:
            self.daily_realized_pnl_pct = 0.0
            self.last_daily_reset = now
        if (now - self.last_hourly_reset).total_seconds() >= 3600:
            self.hourly_realized_pnl_pct = 0.0
            self.last_hourly_reset = now

    def should_halt_entries(self) -> tuple[bool, str]:
        """Returns (halt, reason). Never halts exits — only entry decisions."""
        self.reset_if_needed()
        now = _now()

        if self.breaker_active_until and now < self.breaker_active_until:
            remaining = int((self.breaker_active_until - now).total_seconds() // 60)
            return True, f"Circuit breaker cooldown ({remaining}min remaining)"

        if self.daily_realized_pnl_pct <= DAILY_MAX_LOSS_PCT:
            self.breaker_active_until = now + timedelta(minutes=COOLDOWN_AFTER_DAILY)
            logger.warning("Circuit breaker: daily loss %.1f%% hit %.0f%% limit",
                           self.daily_realized_pnl_pct * 100, DAILY_MAX_LOSS_PCT * 100)
            return True, f"Daily loss {self.daily_realized_pnl_pct:.1%} hit {DAILY_MAX_LOSS_PCT:.0%} limit"

        if self.hourly_realized_pnl_pct <= HOURLY_MAX_LOSS_PCT:
            self.breaker_active_until = now + timedelta(minutes=COOLDOWN_AFTER_HOURLY)
            return True, f"Hourly loss {self.hourly_realized_pnl_pct:.1%} hit {HOURLY_MAX_LOSS_PCT:.0%} limit"

        if self.consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
            self.breaker_active_until = now + timedelta(minutes=COOLDOWN_AFTER_CONSECUTIVE)
            self.consecutive_losses = 0
            return True, f"{CONSECUTIVE_LOSS_LIMIT} consecutive losses"

        if self.daily_realized_pnl_pct <= ENTRY_BLOCK_THRESHOLD:
            return True, f"Daily loss {self.daily_realized_pnl_pct:.1%} exceeded soft limit {ENTRY_BLOCK_THRESHOLD:.0%}"

        return False, ""

    def to_dict(self) -> dict:
        return {
            "daily_realized_pnl_pct": self.daily_realized_pnl_pct,
            "hourly_realized_pnl_pct": self.hourly_realized_pnl_pct,
            "consecutive_losses": self.consecutive_losses,
            "breaker_active_until": self.breaker_active_until.isoformat() if self.breaker_active_until else None,
            "last_daily_reset": self.last_daily_reset.isoformat(),
            "last_hourly_reset": self.last_hourly_reset.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> CircuitBreaker:
        cb = cls()
        cb.daily_realized_pnl_pct = d.get("daily_realized_pnl_pct", 0.0)
        cb.hourly_realized_pnl_pct = d.get("hourly_realized_pnl_pct", 0.0)
        cb.consecutive_losses = d.get("consecutive_losses", 0)
        raw = d.get("breaker_active_until")
        cb.breaker_active_until = datetime.fromisoformat(raw) if raw else None
        cb.last_daily_reset = datetime.fromisoformat(d["last_daily_reset"])
        cb.last_hourly_reset = datetime.fromisoformat(d["last_hourly_reset"])
        return cb

    def save(self) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls) -> CircuitBreaker:
        if STATE_FILE.exists():
            try:
                return cls.from_dict(json.loads(STATE_FILE.read_text()))
            except Exception:
                pass
        return cls()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_circuit_breaker.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/circuit_breaker.py tests/test_circuit_breaker.py
git commit -m "feat: circuit breaker — portfolio-level loss limits (#14)"
```

---

### Task 4: Adaptive Kelly Enhancement (#15)

**Files:**
- Create: `src/adaptive_kelly.py`
- Modify: `tests/test_risk_manager.py`

- [ ] **Step 1: Write adaptive kelly tests**

```python
# tests/test_adaptive_kelly.py
import pytest


class TestAdaptiveKelly:
    def test_high_confidence_base(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        frac = get_adaptive_kelly_fraction("high", 0.70, "esports",
                                            config_kelly_by_conf={"high": 0.25, "medium_high": 0.20, "medium_low": 0.12, "low": 0.08})
        # high=0.25 * esports_discount=0.90 = 0.225
        assert 0.20 <= frac <= 0.25

    def test_strong_ai_bonus(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        frac = get_adaptive_kelly_fraction("high", 0.85, "sports",
                                            config_kelly_by_conf={"high": 0.25})
        # 0.25 + 0.05 (AI>0.80) = 0.30
        assert frac == 0.30

    def test_reentry_discount(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        frac = get_adaptive_kelly_fraction("medium_high", 0.70, "esports", is_reentry=True,
                                            config_kelly_by_conf={"medium_high": 0.20})
        # 0.20 * 0.90 (esports) * 0.80 (re-entry) = 0.144
        assert 0.13 <= frac <= 0.16

    def test_low_confidence_floor(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        frac = get_adaptive_kelly_fraction("low", 0.55, "esports", is_reentry=True,
                                            config_kelly_by_conf={"low": 0.08})
        # 0.08 * 0.90 (esports) * 0.80 (re-entry) = 0.0576, above 0.05 floor
        assert abs(frac - 0.058) < 0.005

    def test_missing_confidence_uses_default(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        frac = get_adaptive_kelly_fraction("unknown", 0.65, "sports",
                                            config_kelly_by_conf={"high": 0.25})
        # Fallback 0.15
        assert frac == 0.15
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_adaptive_kelly.py -v`

- [ ] **Step 3: Implement adaptive_kelly.py**

```python
# src/adaptive_kelly.py
"""Adaptive Kelly fraction — enhances config.risk.kelly_by_confidence with dynamic adjustments.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #15
"""


def get_adaptive_kelly_fraction(
    confidence: str,
    ai_probability: float,
    category: str,
    is_reentry: bool = False,
    config_kelly_by_conf: dict | None = None,
) -> float:
    base = (config_kelly_by_conf or {}).get(confidence, 0.15)

    if ai_probability > 0.80:
        base = min(0.30, base + 0.05)

    if category == "esports":
        base *= 0.90

    if is_reentry:
        base *= 0.80

    return max(0.05, min(0.30, base))
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_adaptive_kelly.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/adaptive_kelly.py tests/test_adaptive_kelly.py
git commit -m "feat: adaptive kelly — confidence/AI/category/re-entry adjustments (#15)"
```

---

### Task 5: Edge Decay (#4)

**Files:**
- Create: `src/edge_decay.py`
- Create: `tests/test_edge_decay.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_edge_decay.py
import pytest


class TestEdgeDecay:
    def test_full_strength_early(self):
        from src.edge_decay import get_edge_decay_factor
        assert get_edge_decay_factor(0.10) == 1.0

    def test_quarter_strength_late(self):
        from src.edge_decay import get_edge_decay_factor
        assert get_edge_decay_factor(0.90) == 0.25

    def test_decayed_target_early_match(self):
        from src.edge_decay import get_decayed_ai_target
        # At 10% elapsed, decay=1.0, target = current + (ai - current) * 1.0 = ai
        target = get_decayed_ai_target(0.70, 0.50, 0.10)
        assert abs(target - 0.70) < 0.01

    def test_decayed_target_late_match(self):
        from src.edge_decay import get_decayed_ai_target
        # At 90% elapsed, decay=0.25, target = 0.50 + (0.70 - 0.50) * 0.25 = 0.55
        target = get_decayed_ai_target(0.70, 0.50, 0.90)
        assert abs(target - 0.55) < 0.01
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_edge_decay.py -v`

- [ ] **Step 3: Implement edge_decay.py**

```python
# src/edge_decay.py
"""AI signal freshness — decay AI target toward market price as match progresses.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #4
"""


def get_edge_decay_factor(elapsed_pct: float) -> float:
    if elapsed_pct < 0.30:
        return 1.0
    elif elapsed_pct < 0.60:
        return 0.75
    elif elapsed_pct < 0.85:
        return 0.50
    else:
        return 0.25


def get_decayed_ai_target(ai_prob: float, current_price: float, elapsed_pct: float) -> float:
    """Blend AI target toward current price. Output is in raw YES-probability frame.
    Callers handle direction conversion when computing edge."""
    decay = get_edge_decay_factor(elapsed_pct)
    return current_price + (ai_prob - current_price) * decay
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_edge_decay.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/edge_decay.py tests/test_edge_decay.py
git commit -m "feat: edge decay — AI signal freshness degradation (#4)"
```

---

### Task 6: Liquidity Check (#18)

**Files:**
- Create: `src/liquidity_check.py`
- Create: `tests/test_liquidity_check.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_liquidity_check.py
import pytest


class TestLiquidityCheck:
    def test_nothing_to_sell(self):
        from src.liquidity_check import check_exit_liquidity
        result = check_exit_liquidity("token123", 0, mock_book={"bids": []})
        assert result["fillable"] is True
        assert result["strategy"] == "market"

    def test_no_bids(self):
        from src.liquidity_check import check_exit_liquidity
        result = check_exit_liquidity("token123", 100, mock_book={"bids": []})
        assert result["fillable"] is False
        assert result["strategy"] == "skip"

    def test_full_depth(self):
        from src.liquidity_check import check_exit_liquidity
        book = {"bids": [{"price": "0.50", "size": "200"}]}
        result = check_exit_liquidity("token123", 100, mock_book=book)
        assert result["fillable"] is True
        assert result["strategy"] == "market"

    def test_partial_depth(self):
        from src.liquidity_check import check_exit_liquidity
        book = {"bids": [{"price": "0.50", "size": "50"}]}
        result = check_exit_liquidity("token123", 100, mock_book=book)
        assert result["fillable"] is False
        assert result["strategy"] == "split"
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_liquidity_check.py -v`

- [ ] **Step 3: Implement liquidity_check.py**

```python
# src/liquidity_check.py
"""Check CLOB order book depth before placing sell orders.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #18
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def check_exit_liquidity(
    token_id: str,
    shares_to_sell: float,
    min_fill_ratio: float = 0.80,
    mock_book: dict | None = None,
) -> dict:
    """Check order book depth. mock_book for testing, else calls CLOB API."""
    try:
        if shares_to_sell <= 0:
            return {"fillable": True, "strategy": "market", "reason": "Nothing to sell"}

        if mock_book is not None:
            book = mock_book
        else:
            from src.executor import fetch_order_book
            book = fetch_order_book(token_id)

        bids = book.get("bids", [])
        if not bids:
            return {"fillable": False, "strategy": "skip", "reason": "No bids"}

        best_bid = float(bids[0]["price"])
        floor_price = best_bid * 0.95

        available = 0.0
        for bid in bids:
            price = float(bid["price"])
            if price < floor_price:
                break
            available += float(bid["size"])

        fill_ratio = available / shares_to_sell
        if fill_ratio >= 1.0:
            return {"fillable": True, "strategy": "market",
                    "recommended_price": best_bid, "available_depth": available}
        elif fill_ratio >= min_fill_ratio:
            return {"fillable": True, "strategy": "limit",
                    "recommended_price": best_bid, "available_depth": available}
        else:
            return {"fillable": False, "strategy": "split",
                    "recommended_price": best_bid, "available_depth": available,
                    "partially_fillable": True,
                    "note": f"Only {fill_ratio:.0%} fillable — split across cycles"}
    except Exception:
        return {"fillable": True, "strategy": "market", "reason": "Book check failed, proceeding anyway"}
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_liquidity_check.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/liquidity_check.py tests/test_liquidity_check.py
git commit -m "feat: liquidity check before exit (#18)"
```

---

## Phase 2: Re-Entry Foundation

### Task 7: Re-Entry System + Tiered Blacklist (#6, #8, #10)

These three are tightly coupled — the re-entry function checks blacklist, and the catastrophic floor is already in Task 1. Building them together.

**Files:**
- Create: `src/reentry.py`
- Create: `tests/test_reentry.py`

- [ ] **Step 1: Write re-entry and blacklist tests**

```python
# tests/test_reentry.py
import pytest
from datetime import datetime, timezone


class TestCanReenter:
    def test_profitable_exit_allowed(self):
        from src.reentry import can_reenter
        ok, reason = can_reenter(
            exit_reason="take_profit", exit_price=0.60, current_price=0.50,
            ai_prob=0.70, direction="BUY_YES",
            score_info={"available": False}, elapsed_pct=0.30,
            slug="cs2-test", number_of_games=3,
            minutes_since_exit=10, daily_reentry_count=0, market_reentry_count=0,
        )
        assert ok is True

    def test_loss_exit_rejected(self):
        from src.reentry import can_reenter
        ok, reason = can_reenter(
            exit_reason="stop_loss", exit_price=0.60, current_price=0.50,
            ai_prob=0.70, direction="BUY_YES",
            score_info={"available": False}, elapsed_pct=0.30,
            slug="cs2-test", number_of_games=3,
            minutes_since_exit=10, daily_reentry_count=0, market_reentry_count=0,
        )
        assert ok is False

    def test_buy_no_effective_prices(self):
        """BUY_NO at YES exit=0.25 (eff=0.75). YES now=0.35 (eff=0.65).
        Effective drop = (0.75-0.65)/0.75 = 13.3% > 5% min → allowed."""
        from src.reentry import can_reenter
        ok, reason = can_reenter(
            exit_reason="take_profit", exit_price=0.25, current_price=0.35,
            ai_prob=0.30, direction="BUY_NO",  # effective_ai = 0.70
            score_info={"available": False}, elapsed_pct=0.30,
            slug="cs2-test", number_of_games=3,
            minutes_since_exit=10, daily_reentry_count=0, market_reentry_count=0,
        )
        assert ok is True

    def test_buy_no_low_ai_rejected(self):
        """BUY_NO with ai_prob=0.50 → effective_ai=0.50 < 0.60 → rejected."""
        from src.reentry import can_reenter
        ok, reason = can_reenter(
            exit_reason="take_profit", exit_price=0.25, current_price=0.35,
            ai_prob=0.50, direction="BUY_NO",
            score_info={"available": False}, elapsed_pct=0.30,
            slug="cs2-test", number_of_games=3,
            minutes_since_exit=10, daily_reentry_count=0, market_reentry_count=0,
        )
        assert ok is False

    def test_too_late_rejected(self):
        from src.reentry import can_reenter
        ok, _ = can_reenter(
            exit_reason="take_profit", exit_price=0.60, current_price=0.50,
            ai_prob=0.70, direction="BUY_YES",
            score_info={"available": False}, elapsed_pct=0.90,
            slug="lol-test", number_of_games=1,
            minutes_since_exit=10, daily_reentry_count=0, market_reentry_count=0,
        )
        assert ok is False  # LoL BO1 max_elapsed = 0.40


class TestBlacklistRules:
    def test_take_profit_is_reentry_type(self):
        from src.reentry import get_blacklist_rule
        btype, duration = get_blacklist_rule("take_profit", elapsed_pct=0.5)
        assert btype == "reentry"
        assert duration == 5

    def test_catastrophic_is_permanent(self):
        from src.reentry import get_blacklist_rule
        btype, duration = get_blacklist_rule("catastrophic_floor", elapsed_pct=0.5)
        assert btype == "permanent"

    def test_graduated_sl_dynamic_duration(self):
        from src.reentry import get_blacklist_rule
        btype, duration_early = get_blacklist_rule("graduated_sl", elapsed_pct=0.30)
        btype, duration_late = get_blacklist_rule("graduated_sl", elapsed_pct=0.90)
        assert duration_early < duration_late  # Early = shorter cooldown


class TestReentryDynamicParams:
    def test_moba_tight_elapsed(self):
        from src.reentry import get_reentry_max_elapsed
        assert get_reentry_max_elapsed("lol-test", 1) == 0.40

    def test_cs2_bo3_wider(self):
        from src.reentry import get_reentry_max_elapsed
        assert get_reentry_max_elapsed("cs2-test", 3) == 0.70

    def test_min_drop_cheap(self):
        from src.reentry import get_min_reentry_drop
        assert get_min_reentry_drop(0.20) == 0.15

    def test_min_drop_expensive(self):
        from src.reentry import get_min_reentry_drop
        assert get_min_reentry_drop(0.80) == 0.05

    def test_size_multiplier_high_ai(self):
        from src.reentry import get_reentry_size_multiplier
        mult = get_reentry_size_multiplier(0.20, "BUY_NO", {"available": False}, 0.40)
        # effective_ai = 0.80 → +0.25 bonus
        assert mult >= 0.70
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_reentry.py -v`

- [ ] **Step 3: Implement reentry.py**

Create `src/reentry.py` with all functions from v2 spec sections 3 (#6, #8, #10). Include:
- `get_reentry_max_elapsed(slug, number_of_games)` — game-type specific thresholds
- `get_min_reentry_drop(effective_exit_price)` — dynamic min price drop
- `get_reentry_size_multiplier(ai_prob, direction, score_info, original_pnl_pct)` — dynamic size
- `can_reenter(...)` — full re-entry eligibility with direction-aware prices
- `get_blacklist_rule(exit_reason, elapsed_pct)` — tiered blacklist duration lookup
- `BlacklistEntry` dataclass
- `Blacklist` class with `add()`, `is_blocked()`, `get_entry()`, `cleanup()`, `save()`, `load()`

Full code follows the spec exactly. All functions use effective prices for BUY_NO.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_reentry.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/reentry.py tests/test_reentry.py
git commit -m "feat: re-entry system + tiered blacklist + dynamic params (#6, #8, #10)"
```

---

## Phase 3: Exit System Overhaul

### Task 8: Scale Out (#1)

**Files:**
- Create: `src/scale_out.py`
- Create: `tests/test_scale_out.py`
- Modify: `src/models.py` — add PartialExit, scale_out fields

- [ ] **Step 1: Add new fields to Position model**

In `src/models.py`, add after existing fields (around line 66):
```python
    # Scale Out fields (v2)
    original_shares: float | None = None
    original_size_usdc: float | None = None
    partial_exits: list[dict] = []
    scale_out_tier: int = 0
    # Scale-In fields (v2)
    intended_size_usdc: float = 0.0
    scale_in_complete: bool = False
    # σ-Trailing fields (v2)
    price_history_buffer: list[float] = []
    peak_price: float = 0.0
    # Grace period (v2)
    cycles_held: int = 0
```

- [ ] **Step 2: Write scale out tests**

```python
# tests/test_scale_out.py
import pytest


class TestCheckScaleOut:
    def test_tier1_at_25pct(self):
        from src.scale_out import check_scale_out
        result = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.26, volatility_swing=False)
        assert result is not None
        assert result["tier"] == "tier1_risk_free"
        assert result["sell_pct"] == 0.40

    def test_no_trigger_below_threshold(self):
        from src.scale_out import check_scale_out
        result = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.20, volatility_swing=False)
        assert result is None

    def test_tier2_at_50pct(self):
        from src.scale_out import check_scale_out
        result = check_scale_out(scale_out_tier=1, unrealized_pnl_pct=0.55, volatility_swing=False)
        assert result is not None
        assert result["tier"] == "tier2_profit_lock"

    def test_vs_positions_skipped(self):
        from src.scale_out import check_scale_out
        result = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50, volatility_swing=True)
        assert result is None


class TestApplyPartialExit:
    def test_buy_yes_pnl_correct(self):
        from src.scale_out import apply_partial_exit
        # Entry: 100 shares at 0.45, size_usdc=45. Sell 40 shares at 0.65.
        result = apply_partial_exit(
            shares=100, size_usdc=45.0, entry_price=0.45, direction="BUY_YES",
            shares_sold=40, fill_price=0.65, tier="tier1_risk_free",
            original_shares=None, original_size_usdc=None, scale_out_tier=0,
        )
        assert result["status"] == "OK"
        assert result["remaining_shares"] == 60
        assert abs(result["remaining_size_usdc"] - 27.0) < 0.01  # 45 * (1 - 40/100)
        assert result["realized_pnl"] > 0  # 40*0.65 - 45*(40/100) = 26 - 18 = 8

    def test_buy_no_pnl_correct(self):
        from src.scale_out import apply_partial_exit
        # BUY_NO: 100 shares at YES=0.65 (eff=0.35), size_usdc=35. Sell 40 at YES=0.30.
        result = apply_partial_exit(
            shares=100, size_usdc=35.0, entry_price=0.65, direction="BUY_NO",
            shares_sold=40, fill_price=0.30, tier="tier1_risk_free",
            original_shares=None, original_size_usdc=None, scale_out_tier=0,
        )
        # proceeds = 40 * (1 - 0.30) = 28. cost_basis_sold = 35 * (40/100) = 14. pnl = 14.
        assert result["realized_pnl"] == 14.0

    def test_dust_closes_remainder(self):
        from src.scale_out import apply_partial_exit
        result = apply_partial_exit(
            shares=2, size_usdc=1.0, entry_price=0.50, direction="BUY_YES",
            shares_sold=1.5, fill_price=0.60, tier="tier2_profit_lock",
            original_shares=10, original_size_usdc=5.0, scale_out_tier=1,
        )
        assert result["status"] == "CLOSE_REMAINDER"
```

- [ ] **Step 3: Implement scale_out.py**

Create `src/scale_out.py` with `check_scale_out()` and `apply_partial_exit()` following spec exactly. Use pure functions (no Position object dependency — accept/return primitives for testability). Important: `check_scale_out()` skips VS (volatility_swing) positions but scouted "hold to resolve" positions intentionally participate in scale-out — add a comment documenting this per spec Section 9j.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_scale_out.py tests/test_models.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/scale_out.py tests/test_scale_out.py src/models.py
git commit -m "feat: scale out 3-tier partial exit (#1) + new Position fields"
```

---

### Task 9: σ-based Trailing Stop (#3)

**Files:**
- Create: `src/trailing_sigma.py`
- Create: `tests/test_trailing_sigma.py`

- [ ] **Step 1: Write sigma trailing tests**

```python
# tests/test_trailing_sigma.py
import pytest


class TestSigmaTrailing:
    def test_inactive_below_5pct_peak(self):
        from src.trailing_sigma import calculate_sigma_trailing_stop
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.03, price_history=[0.50, 0.51, 0.50, 0.49, 0.50],
            current_price=0.50, peak_price=0.51, entry_price=0.48,
        )
        assert result["active"] is False

    def test_inactive_short_history(self):
        from src.trailing_sigma import calculate_sigma_trailing_stop
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.20, price_history=[0.50, 0.51],
            current_price=0.50, peak_price=0.55, entry_price=0.45,
        )
        assert result["active"] is False

    def test_wide_stop_low_peak(self):
        from src.trailing_sigma import calculate_sigma_trailing_stop
        # Low peak (8%) → z=3.0 → wide stop
        history = [0.50, 0.51, 0.52, 0.51, 0.50, 0.52, 0.53, 0.54]
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.08, price_history=history,
            current_price=0.52, peak_price=0.54, entry_price=0.50,
        )
        assert result["active"] is True
        assert result["z_score"] == 3.0
        assert result["triggered"] is False  # Wide stop, not triggered

    def test_tight_stop_high_peak(self):
        from src.trailing_sigma import calculate_sigma_trailing_stop
        # High peak (60%) → z=1.5 → tight stop
        history = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.75, 0.70]
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.60, price_history=history,
            current_price=0.65, peak_price=0.80, entry_price=0.50,
        )
        assert result["active"] is True
        assert result["z_score"] == 1.5

    def test_entry_price_floor(self):
        """Stop never goes below entry price."""
        from src.trailing_sigma import calculate_sigma_trailing_stop
        # Very volatile → large sigma → stop would be below entry
        history = [0.50, 0.60, 0.50, 0.70, 0.50, 0.60]
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.40, price_history=history,
            current_price=0.55, peak_price=0.70, entry_price=0.50,
        )
        assert result["stop_price"] >= 0.50

    def test_all_params_are_effective_prices(self):
        """For BUY_NO: caller passes effective prices. Function works identically."""
        from src.trailing_sigma import calculate_sigma_trailing_stop
        # BUY_NO: YES entry=0.65, effective_entry=0.35. Peak effective=0.60.
        history = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.58, 0.55]
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.70, price_history=history,
            current_price=0.55, peak_price=0.60, entry_price=0.35,
        )
        assert result["active"] is True
        assert result["stop_price"] >= 0.35  # Floor at effective entry
```

- [ ] **Step 2: Implement trailing_sigma.py**

```python
# src/trailing_sigma.py
"""σ-based trailing stop — volatility-adjusted trailing using rolling standard deviation.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #3

ALL price parameters must be effective (direction-adjusted) prices.
Caller converts: BUY_YES=raw, BUY_NO=1-raw.
"""


def calculate_sigma_trailing_stop(
    peak_pnl_pct: float,
    price_history: list[float],
    current_price: float,
    peak_price: float,
    entry_price: float,
) -> dict:
    if peak_pnl_pct < 0.05 or len(price_history) < 5:
        return {"active": False}

    changes = [price_history[i] - price_history[i - 1] for i in range(1, len(price_history))]
    if not changes:
        return {"active": False}

    mean_change = sum(changes) / len(changes)
    sigma = (sum((c - mean_change) ** 2 for c in changes) / len(changes)) ** 0.5

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
        "reason": f"σ-trail: {current_price:.3f} {'<' if triggered else '>='} stop {stop_price:.3f}",
    }
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_trailing_sigma.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add src/trailing_sigma.py tests/test_trailing_sigma.py
git commit -m "feat: σ-based trailing stop (#3)"
```

---

### Task 10: Resolution-Aware TP (#2) + VS Spike Detection (#5)

**Files:**
- Create: `src/vs_spike.py`
- Create: `tests/test_vs_spike.py`
- The resolution-aware TP logic will be integrated in portfolio.py in the integration task

- [ ] **Step 1: Write VS spike tests**

```python
# tests/test_vs_spike.py
import pytest


class TestVsSpike:
    def test_strong_spike_detected(self):
        from src.vs_spike import detect_vs_spike
        # +30% in 2 cycles and still accelerating
        history = [0.10, 0.11, 0.12, 0.10, 0.11, 0.13]  # 0.10→0.13 = +30% in 2 cycles
        result = detect_vs_spike(history, entry_price=0.08)
        assert result["spike"] is True

    def test_no_spike_stable(self):
        from src.vs_spike import detect_vs_spike
        history = [0.10, 0.10, 0.11, 0.10, 0.11, 0.10]
        result = detect_vs_spike(history, entry_price=0.08)
        assert result["spike"] is False

    def test_short_history_no_spike(self):
        from src.vs_spike import detect_vs_spike
        result = detect_vs_spike([0.10, 0.12], entry_price=0.08)
        assert result["spike"] is False
```

- [ ] **Step 2: Implement vs_spike.py**

Copy from v2 spec #5 exactly.

- [ ] **Step 3: Write resolution-aware TP tests**

```python
# tests/test_vs_spike.py — add to same file

class TestShouldHoldForResolution:
    def test_hold_buy_yes_high_price_high_ai(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.75,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is True

    def test_hold_buy_no_where_yes_low(self):
        """BUY_NO where YES=0.15 → effective=0.85 → hold."""
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.80,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is True

    def test_reject_low_scale_out_tier(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.75,
            scale_out_tier=0, score_behind=False, is_already_won=False,
        )
        assert hold is False  # Need scale_out_tier >= 1

    def test_reject_low_ai(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.55,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is False  # AI < 0.70

    def test_reject_score_behind(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.75,
            scale_out_tier=2, score_behind=True, is_already_won=False,
        )
        assert hold is False  # Score behind

    def test_already_won_always_holds(self):
        """score_terminal_win overrides all other conditions."""
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.50, effective_ai=0.40,
            scale_out_tier=0, score_behind=True, is_already_won=True,
        )
        assert hold is True  # Already won overrides everything

    def test_effective_price_below_80c_rejected(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.75, effective_ai=0.80,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is False  # effective_price < 0.80
```

- [ ] **Step 4: Implement should_hold_for_resolution() in vs_spike.py**

```python
# In src/vs_spike.py — add:

def should_hold_for_resolution(
    effective_price: float,
    effective_ai: float,
    scale_out_tier: int,
    score_behind: bool,
    is_already_won: bool,
) -> tuple[bool, str]:
    """Decide whether to hold for resolution instead of taking profit.
    Spec: #2 Resolution-Aware TP.
    ALL prices must be effective (direction-adjusted by caller)."""
    if is_already_won:
        return True, "Match already won — hold to resolution"
    if scale_out_tier < 1:
        return False, f"Scale-out tier {scale_out_tier} < 1"
    if effective_price < 0.80:
        return False, f"Effective price {effective_price:.2f} < 0.80"
    if effective_ai < 0.70:
        return False, f"Effective AI {effective_ai:.2f} < 0.70"
    if score_behind:
        return False, "Score behind — don't hold"
    return True, f"Hold for resolution: eff_price={effective_price:.2f}, eff_ai={effective_ai:.2f}"
```

- [ ] **Step 5: Run tests + commit**

```bash
python -m pytest tests/test_vs_spike.py -v
git add src/vs_spike.py tests/test_vs_spike.py
git commit -m "feat: VS spike detection (#5) + resolution-aware TP (#2)"
```

---

## Phase 4: Re-Entry Extensions

### Task 11: Snowball Ban (#11) + Layer 3 Grace (#9) + Score Reversal (#13)

**Files:**
- Modify: `src/reentry.py` — add snowball, grace, score reversal functions

- [ ] **Step 1: Write tests for all three**

```python
# tests/test_reentry.py — add to existing file

class TestSnowballBan:
    def test_moba_behind_banned(self):
        from src.reentry import is_snowball_banned
        banned, _ = is_snowball_banned("lol-test", 0.40, {"available": True, "map_diff": -1})
        assert banned is True

    def test_cs2_behind_not_banned(self):
        from src.reentry import is_snowball_banned
        banned, _ = is_snowball_banned("cs2-test", 0.40, {"available": True, "map_diff": -1})
        assert banned is False

    def test_moba_early_not_banned(self):
        from src.reentry import is_snowball_banned
        banned, _ = is_snowball_banned("lol-test", 0.20, {"available": True, "map_diff": -1})
        assert banned is False


class TestGracePeriod:
    def test_reentry_gets_grace(self):
        from src.reentry import is_grace_period_active
        assert is_grace_period_active({
            "entry_reason": "re_entry_after_profit", "cycles_held": 3,
            "entry_price": 0.50, "current_price": 0.49, "direction": "BUY_YES",
        }) is True

    def test_grace_expired(self):
        from src.reentry import is_grace_period_active
        assert is_grace_period_active({
            "entry_reason": "re_entry_after_profit", "cycles_held": 10,
            "entry_price": 0.50, "current_price": 0.49, "direction": "BUY_YES",
        }) is False

    def test_grace_revoked_on_drop(self):
        from src.reentry import is_grace_period_active
        assert is_grace_period_active({
            "entry_reason": "re_entry_after_profit", "cycles_held": 2,
            "entry_price": 0.50, "current_price": 0.46, "direction": "BUY_YES",
        }) is False  # 4c drop > 3c max

    def test_buy_no_grace_direction(self):
        """BUY_NO: YES price rising = bad for us = should revoke grace."""
        from src.reentry import is_grace_period_active
        assert is_grace_period_active({
            "entry_reason": "re_entry_after_profit", "cycles_held": 2,
            "entry_price": 0.60, "current_price": 0.64, "direction": "BUY_NO",
        }) is False  # eff drop = (0.64-0.60) = 4c > 3c


class TestScoreReversal:
    def test_convincing_lead_overrides(self):
        from src.reentry import qualifies_for_score_reversal_reentry, BlacklistEntry
        entry = BlacklistEntry("cid1", "graduated_sl", "timed", 100, {})
        ok, _ = qualifies_for_score_reversal_reentry(
            entry, {"available": True, "map_diff": 2}, elapsed_pct=0.50, current_cycle=50,
        )
        assert ok is True

    def test_single_map_lead_not_enough(self):
        from src.reentry import qualifies_for_score_reversal_reentry, BlacklistEntry
        entry = BlacklistEntry("cid1", "graduated_sl", "timed", 100, {})
        ok, _ = qualifies_for_score_reversal_reentry(
            entry, {"available": True, "map_diff": 1}, elapsed_pct=0.50, current_cycle=50,
        )
        assert ok is False

    def test_permanent_blacklist_not_overrideable(self):
        from src.reentry import qualifies_for_score_reversal_reentry, BlacklistEntry
        entry = BlacklistEntry("cid1", "catastrophic_floor", "permanent", None, {})
        ok, _ = qualifies_for_score_reversal_reentry(
            entry, {"available": True, "map_diff": 3}, elapsed_pct=0.50, current_cycle=50,
        )
        assert ok is False
```

- [ ] **Step 2: Implement in reentry.py**

Add `is_snowball_banned()`, `is_grace_period_active()`, `qualifies_for_score_reversal_reentry()` to `src/reentry.py`. All following spec exactly.

- [ ] **Step 3: Run tests + commit**

```bash
python -m pytest tests/test_reentry.py -v
git add src/reentry.py tests/test_reentry.py
git commit -m "feat: snowball ban + L3 grace + score reversal exception (#11, #9, #13)"
```

---

### Task 12: AI Confidence Momentum (#12)

- [ ] **Step 1: Add passes_confidence_momentum() to reentry.py**

```python
# In src/reentry.py — add:
def passes_confidence_momentum(
    saved_ai_prob: float,
    current_ai_prob: float,
    direction: str,
    threshold: float = 1.05,
) -> tuple[bool, str]:
    saved_eff = saved_ai_prob if direction == "BUY_YES" else (1 - saved_ai_prob)
    current_eff = current_ai_prob if direction == "BUY_YES" else (1 - current_ai_prob)
    if saved_eff < 0.10:
        return True, "Saved effective prob too low"
    ratio = current_eff / saved_eff
    if ratio >= threshold:
        return True, f"Confidence rising: {saved_eff:.0%} → {current_eff:.0%}"
    return False, f"Confidence not rising: ratio {ratio:.2f} < {threshold}"
```

- [ ] **Step 2: Write confidence momentum tests**

```python
# tests/test_reentry.py — add to existing file

class TestConfidenceMomentum:
    def test_rising_confidence_passes(self):
        from src.reentry import passes_confidence_momentum
        ok, _ = passes_confidence_momentum(0.60, 0.65, "BUY_YES")
        assert ok is True  # 0.65/0.60 = 1.083 >= 1.05

    def test_flat_confidence_fails(self):
        from src.reentry import passes_confidence_momentum
        ok, _ = passes_confidence_momentum(0.60, 0.61, "BUY_YES")
        assert ok is False  # 0.61/0.60 = 1.017 < 1.05

    def test_buy_no_direction_conversion(self):
        """BUY_NO: saved_ai=0.30 (eff=0.70), current_ai=0.25 (eff=0.75).
        Ratio = 0.75/0.70 = 1.071 >= 1.05 → passes."""
        from src.reentry import passes_confidence_momentum
        ok, _ = passes_confidence_momentum(0.30, 0.25, "BUY_NO")
        assert ok is True

    def test_buy_no_wrong_direction_fails(self):
        """BUY_NO: saved_ai=0.30 (eff=0.70), current_ai=0.35 (eff=0.65).
        Ratio = 0.65/0.70 = 0.929 < 1.05 → fails."""
        from src.reentry import passes_confidence_momentum
        ok, _ = passes_confidence_momentum(0.30, 0.35, "BUY_NO")
        assert ok is False

    def test_low_saved_passes_trivially(self):
        from src.reentry import passes_confidence_momentum
        ok, _ = passes_confidence_momentum(0.05, 0.04, "BUY_YES")
        assert ok is True  # saved_eff < 0.10 → auto-pass
```

- [ ] **Step 3: Run tests + commit**

```bash
python -m pytest tests/test_reentry.py -v
git add src/reentry.py tests/test_reentry.py
git commit -m "feat: AI confidence momentum filter (#12)"
```

---

## Phase 5: Advanced Features

### Task 13: Scale-In (#7)

**Files:**
- Create: `tests/test_scale_in.py`
- The scale-in logic is added to `src/scale_out.py` (same module — position sizing)

- [ ] **Step 1: Write scale-in tests**

```python
# tests/test_scale_in.py
import pytest


class TestShouldScaleIn:
    def test_scale_in_when_profitable(self):
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=0.05, cycles_held=4,
            scale_in_complete=False, intended_size_usdc=100.0,
            current_size_usdc=50.0, score_ahead=False,
        )
        assert ok is True  # 5% profit > 2% threshold, 4 cycles, room to scale

    def test_scale_in_via_score_ahead(self):
        """Score-ahead can confirm even if PnL is marginal (but still positive)."""
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=0.01, cycles_held=4,
            scale_in_complete=False, intended_size_usdc=100.0,
            current_size_usdc=50.0, score_ahead=True,
        )
        assert ok is True  # PnL > 0 + score_ahead → confirmed

    def test_no_scale_in_losing(self):
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=-0.05, cycles_held=4,
            scale_in_complete=False, intended_size_usdc=100.0,
            current_size_usdc=50.0, score_ahead=True,
        )
        assert ok is False  # Losing position, don't add even with score ahead

    def test_no_scale_in_too_early(self):
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=0.08, cycles_held=1,
            scale_in_complete=False, intended_size_usdc=100.0,
            current_size_usdc=50.0, score_ahead=False,
        )
        assert ok is False  # Need min 3 cycles

    def test_no_scale_in_already_complete(self):
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=0.15, cycles_held=10,
            scale_in_complete=True, intended_size_usdc=100.0,
            current_size_usdc=100.0, score_ahead=False,
        )
        assert ok is False  # Already at full size

    def test_marginal_pnl_no_score_rejected(self):
        """PnL between 0-2% without score_ahead → not confirmed."""
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=0.01, cycles_held=4,
            scale_in_complete=False, intended_size_usdc=100.0,
            current_size_usdc=50.0, score_ahead=False,
        )
        assert ok is False


class TestGetScaleInSize:
    def test_kelly_based_sizing(self):
        from src.scale_out import get_scale_in_size
        size = get_scale_in_size(
            intended_size_usdc=100.0, current_size_usdc=50.0,
            kelly_size_now=80.0,
        )
        # min(remaining=50, kelly_now - current=30) = 30
        assert abs(size - 30.0) < 0.01

    def test_kelly_larger_than_remaining(self):
        from src.scale_out import get_scale_in_size
        size = get_scale_in_size(
            intended_size_usdc=100.0, current_size_usdc=90.0,
            kelly_size_now=200.0,
        )
        # min(remaining=10, kelly_now - current=110) = 10
        assert abs(size - 10.0) < 0.01

    def test_kelly_smaller_than_current(self):
        """If Kelly now says less than current position, don't add."""
        from src.scale_out import get_scale_in_size
        size = get_scale_in_size(
            intended_size_usdc=100.0, current_size_usdc=50.0,
            kelly_size_now=40.0,
        )
        assert size == 0.0  # Kelly says we're already overexposed
```

- [ ] **Step 2: Implement should_scale_in() and get_scale_in_size() in scale_out.py**

```python
# In src/scale_out.py — add:

def should_scale_in(
    unrealized_pnl_pct: float,
    cycles_held: int,
    scale_in_complete: bool,
    intended_size_usdc: float,
    current_size_usdc: float,
    score_ahead: bool = False,
    min_pnl_pct: float = 0.02,
    min_cycles: int = 3,
) -> tuple[bool, str]:
    if scale_in_complete:
        return False, "Scale-in already complete"
    if current_size_usdc >= intended_size_usdc:
        return False, "Already at intended size"
    if cycles_held < min_cycles:
        return False, f"Need {min_cycles} cycles, have {cycles_held}"
    # Safety guard (stricter than spec — spec allows score_ahead alone even when losing,
    # but we block scale-in on actively losing positions as a risk improvement)
    if unrealized_pnl_pct < 0:
        return False, f"Position losing ({unrealized_pnl_pct:.1%}), no scale-in"
    # Confirmation: either PnL above threshold OR score advantage
    pnl_confirmed = unrealized_pnl_pct >= min_pnl_pct
    if not pnl_confirmed and not score_ahead:
        return False, f"PnL {unrealized_pnl_pct:.1%} < {min_pnl_pct:.0%} and no score advantage"
    return True, "Position confirmed — scale in"


def get_scale_in_size(
    intended_size_usdc: float,
    current_size_usdc: float,
    kelly_size_now: float,
) -> float:
    """Size based on Kelly re-evaluation. Returns min(remaining_intended, kelly_gap)."""
    remaining = intended_size_usdc - current_size_usdc
    if remaining <= 0:
        return 0.0
    kelly_gap = kelly_size_now - current_size_usdc
    if kelly_gap <= 0:
        return 0.0  # Kelly says we're already overexposed
    return min(remaining, kelly_gap)
```

- [ ] **Step 3: Run tests + commit**

```bash
python -m pytest tests/test_scale_in.py -v
git add src/scale_out.py tests/test_scale_in.py
git commit -m "feat: scale-in gradual entry (#7)"
```

---

### Task 14: Correlation-Aware Exposure (#17)

**Files:**
- Create: `src/correlation.py`
- Create: `tests/test_correlation.py`

- [ ] **Step 1: Write correlation tests**

```python
# tests/test_correlation.py
import pytest


class TestMatchKeyExtraction:
    def test_cs2_map_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("cs2-faze-vs-navi-map-1") == "cs2-faze-vs-navi"

    def test_no_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("lol-t1-vs-geng") == "lol-t1-vs-geng"

    def test_game_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("dota2-og-vs-spirit-game-2") == "dota2-og-vs-spirit"

    def test_winner_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("cs2-faze-vs-navi-winner") == "cs2-faze-vs-navi"

    def test_over_under_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("cs2-faze-vs-navi-over") == "cs2-faze-vs-navi"
        assert extract_match_key("cs2-faze-vs-navi-under") == "cs2-faze-vs-navi"

    def test_handicap_spread(self):
        from src.correlation import extract_match_key
        assert extract_match_key("lol-t1-vs-geng-handicap") == "lol-t1-vs-geng"
        assert extract_match_key("lol-t1-vs-geng-spread") == "lol-t1-vs-geng"

    def test_first_prefix_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("cs2-faze-vs-navi-first-blood") == "cs2-faze-vs-navi"


class TestNetExposure:
    def test_single_position(self):
        from src.correlation import get_match_exposure
        positions = [{"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 50.0, "direction": "BUY_YES"}]
        exposure = get_match_exposure("cs2-faze-vs-navi", positions)
        assert exposure == 50.0

    def test_opposing_positions_net(self):
        from src.correlation import get_match_exposure
        positions = [
            {"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 50.0, "direction": "BUY_YES"},
            {"slug": "cs2-faze-vs-navi-map-2", "size_usdc": 30.0, "direction": "BUY_NO"},
        ]
        exposure = get_match_exposure("cs2-faze-vs-navi", positions)
        assert exposure == 20.0  # 50 - 30

    def test_unrelated_match_excluded(self):
        from src.correlation import get_match_exposure
        positions = [
            {"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 50.0, "direction": "BUY_YES"},
            {"slug": "lol-t1-vs-geng", "size_usdc": 100.0, "direction": "BUY_YES"},
        ]
        exposure = get_match_exposure("cs2-faze-vs-navi", positions)
        assert exposure == 50.0


class TestCorrelationCap:
    def test_within_limit_returns_full_size(self):
        from src.correlation import apply_correlation_cap
        capped = apply_correlation_cap(
            proposed_size=30.0, match_key="cs2-faze-vs-navi",
            existing_positions=[], bankroll=1000.0,
        )
        assert capped == 30.0  # 30 < 150 (15% of 1000)

    def test_exceeds_limit_caps_size(self):
        from src.correlation import apply_correlation_cap
        positions = [{"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 130.0, "direction": "BUY_YES"}]
        capped = apply_correlation_cap(
            proposed_size=30.0, match_key="cs2-faze-vs-navi",
            existing_positions=positions, bankroll=1000.0,
        )
        assert capped == 20.0  # remaining = 150 - 130 = 20, min(30, 20) = 20

    def test_small_bankroll_tighter(self):
        from src.correlation import apply_correlation_cap
        capped = apply_correlation_cap(
            proposed_size=30.0, match_key="cs2-faze-vs-navi",
            existing_positions=[], bankroll=100.0,
        )
        assert capped == 15.0  # max_exposure = 15 (15% of 100), min(30, 15) = 15

    def test_at_limit_returns_zero(self):
        from src.correlation import apply_correlation_cap
        positions = [{"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 150.0, "direction": "BUY_YES"}]
        capped = apply_correlation_cap(
            proposed_size=30.0, match_key="cs2-faze-vs-navi",
            existing_positions=positions, bankroll=1000.0,
        )
        assert capped == 0.0  # already at limit
```

- [ ] **Step 2: Implement correlation.py**

```python
# src/correlation.py
"""Correlation-aware exposure tracking — limit total USD exposure per match.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #17
"""
from __future__ import annotations
import re


_STRIP_SUFFIXES = re.compile(
    r"-(map|game)-?\d+$|-(winner|over|under|total|to-win|handicap|spread|moneyline)$|-(first-.+)$"
)


def extract_match_key(slug: str) -> str:
    """Strip map/game/market-type suffixes to get the base match identifier."""
    return _STRIP_SUFFIXES.sub("", slug)


def get_match_exposure(match_key: str, positions: list[dict]) -> float:
    """Net USD exposure for a match key. BUY_YES=positive, BUY_NO=negative."""
    total = 0.0
    for pos in positions:
        if extract_match_key(pos["slug"]) == match_key:
            size = pos.get("size_usdc", 0.0)
            total += size if pos.get("direction") == "BUY_YES" else -size
    return abs(total)


MAX_MATCH_EXPOSURE_PCT = 0.15  # 15% of bankroll


def apply_correlation_cap(
    proposed_size: float,
    match_key: str,
    existing_positions: list[dict],
    bankroll: float,
    max_match_pct: float = MAX_MATCH_EXPOSURE_PCT,
) -> float:
    """Cap proposed_size so total match exposure stays within bankroll limit.
    Returns the capped size (may be 0 if limit already reached).
    NOTE: Intentionally conservative — treats all new positions as additive
    regardless of direction. A BUY_NO on a BUY_YES-heavy match would technically
    reduce net exposure, but we cap conservatively for a real-money bot.
    Over-capping is safer than under-capping."""
    max_exposure = bankroll * max_match_pct
    current_net = get_match_exposure(match_key, existing_positions)
    remaining = max(0.0, max_exposure - current_net)
    return min(proposed_size, remaining)
```

- [ ] **Step 3: Run tests + commit**

```bash
python -m pytest tests/test_correlation.py -v
git add src/correlation.py tests/test_correlation.py
git commit -m "feat: correlation-aware exposure tracking (#17)"
```

---

## Phase 6: Integration

### Task 15: Wire everything into portfolio.py

**Files:**
- Modify: `src/portfolio.py`

Key changes:
- [ ] **Step 1:** In `update_price()` (line 175): add `cycles_held += 1`, populate `price_history_buffer` with effective prices, update `peak_price`
- [ ] **Step 2:** In `check_match_aware_exits()` (line 498): pass `entry_reason` and `cycles_held` in data dict. Skip flat SL for positions processed by match-aware exits.
- [ ] **Step 3:** Add `check_scale_out()` call before `check_take_profits()`. When `scale_out_tier > 0`, skip legacy TP. Note: scouted positions intentionally participate in scale-out (spec Section 9j) — do NOT skip them.
- [ ] **Step 4:** Replace `check_trailing_stops()` with σ-trailing. Convert prices to effective before passing.
- [ ] **Step 5:** Wire `get_decayed_ai_target()` from `edge_decay.py` into `check_take_profits()` — replace raw `ai_probability` with decayed target when computing edge for TP decisions. This is the primary edge decay integration point (spec Section 9i).
- [ ] **Step 6:** Add resolution-aware TP check after scale-out tier 2. When `should_hold_for_resolution()` returns True, bypass graduated SL UNLESS `effective_price < 0.65`.
- [ ] **Step 7:** Run all portfolio tests: `python -m pytest tests/test_portfolio.py -v`
- [ ] **Step 8:** Commit

```bash
git commit -m "feat: integrate scale-out, σ-trailing, resolution TP into portfolio.py"
```

---

### Task 16: Wire everything into main.py

**Files:**
- Modify: `src/main.py`

Key changes:
- [ ] **Step 1:** Import and initialize `CircuitBreaker` in `Agent.__init__()`. Load from disk.
- [ ] **Step 2:** Add `circuit_breaker.should_halt_entries()` check before any entry logic in `run_cycle()`.
- [ ] **Step 3:** Extend `_exit_position()` signature: add `elapsed_pct` param. Call `circuit_breaker.record_exit()`. Use `get_blacklist_rule()` instead of `_exited_markets`.
- [ ] **Step 4:** Replace `_exited_markets` set with `Blacklist` class from `reentry.py`. Update all `condition_id not in self._exited_markets` checks to `not self.blacklist.is_blocked(cid, current_cycle)`.
- [ ] **Step 5:** Add new re-entry path: after spike/scouted re-entry checks, add `can_reenter()` check for tiered blacklist entries with type "reentry". Check snowball ban, score reversal exception. Wire `get_decayed_ai_target()` from `edge_decay.py` into re-entry edge calculation: `edge = |decayed_ai_target - effective_current_price|`.
- [ ] **Step 6:** In `risk_manager.py` (per spec #15), wrap the existing `kelly_by_confidence` lookup with `get_adaptive_kelly_fraction()`. Import from `adaptive_kelly.py` and replace the raw dict lookup so all callers automatically get the adjusted fraction.
- [ ] **Step 7:** Wire `apply_correlation_cap()` from `correlation.py` into entry sizing pipeline (spec C8: Kelly → Correlation cap → Final size). After `get_adaptive_kelly_fraction()` computes the kelly-sized amount, pass it through `apply_correlation_cap(kelly_size, match_key, current_positions, bankroll)` before placing entry order. This ensures per-match exposure limits are enforced.
- [ ] **Step 8:** Wire `check_exit_liquidity()` in `_exit_position()` before placing sell order.
- [ ] **Step 9:** Add Telegram notification when circuit breaker activates or deactivates. Use the existing `send_telegram_message()` helper from `src/notifications.py`. Message format: `"⚠️ Circuit breaker ACTIVATED: {reason} (daily: {daily_pnl:.1%}, hourly: {hourly_pnl:.1%})"` on activation, `"✅ Circuit breaker deactivated — entries resumed"` on deactivation.
- [ ] **Step 10:** Run full test suite: `python -m pytest tests/ -v`
- [ ] **Step 11:** Commit

```bash
git commit -m "feat: integrate circuit breaker, blacklist, re-entry, adaptive kelly, edge decay into main loop"
```

---

### Task 17: Config.py Updates

**Files:**
- Modify: `src/config.py`

- [ ] **Step 1: Add new config fields**

```python
# In src/config.py, add to RiskConfig or create new sections:

    # Re-entry (#6, #12)
    reentry_fresh_ai_call: bool = False  # If True, call AI again before re-entry
    max_daily_reentries: int = 5  # Spec: can_reenter() checks >= 5
    max_market_reentries: int = 2

    # Correlation (#17)
    max_match_exposure_pct: float = 0.15  # 15% of bankroll per match

    # Scale-In (#7)
    scale_in_min_pnl_pct: float = 0.02  # Spec: > 2% PnL or score_ahead
    scale_in_min_cycles: int = 3
    scale_in_num_tranches: int = 2  # Spec: 2-tranche system (50% + 50%)
```

- [ ] **Step 2: Run config tests + commit**

```bash
python -m pytest tests/ -v --tb=short
git add src/config.py
git commit -m "feat: add config fields for re-entry, correlation, scale-in"
```

---

### Task 18: Integration Tests

**Files:**
- Create: `tests/test_integration.py`

These cover the 6 integration scenarios from spec Section 11.

- [ ] **Step 1: Write integration tests**

```python
# tests/test_integration.py
"""Integration tests — verify multi-module interactions.
Spec Section 11: Testing Strategy.
"""
import pytest


class TestScaleOutPlusMatchAware:
    """Scale Out tier 1 fires, then match-aware exit should use reduced shares."""
    def test_tier1_then_match_exit(self):
        from src.scale_out import apply_partial_exit, check_scale_out
        from src.match_exit import check_match_exit

        # Position: 100 shares, 25% profit → tier 1 fires
        tier = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.26, volatility_swing=False)
        assert tier is not None

        # After partial exit: 60 shares remain
        result = apply_partial_exit(
            shares=100, size_usdc=50.0, entry_price=0.50, direction="BUY_YES",
            shares_sold=40, fill_price=0.63, tier="tier1_risk_free",
            original_shares=None, original_size_usdc=None, scale_out_tier=0,
        )
        assert result["remaining_shares"] == 60

        # Match-aware exit should still work on remaining position
        exit_result = check_match_exit({
            "entry_price": 0.50, "current_price": 0.20, "direction": "BUY_YES",
            "number_of_games": 3, "slug": "cs2-test", "match_score": "",
            "match_start_iso": "2026-01-01T00:00:00+00:00",
            "ever_in_profit": True, "peak_pnl_pct": 0.26, "scouted": False,
            "confidence": "medium", "ai_probability": 0.5,
            "consecutive_down_cycles": 0, "cumulative_drop": 0.0,
            "hold_revoked_at": None, "hold_was_original": False,
            "volatility_swing": False, "unrealized_pnl_pct": -0.60,
            "entry_reason": "", "cycles_held": 10,
        })
        assert exit_result["exit"] is True


class TestCircuitBreakerPlusReentry:
    """Circuit breaker halts entries, re-entry should be blocked."""
    def test_breaker_blocks_reentry(self):
        from src.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker()
        cb.record_exit(-90.0, 1000.0)  # -9% → daily limit
        halt, _ = cb.should_halt_entries()
        assert halt is True
        # Re-entry attempt should be blocked by the caller (main.py checks cb first)


class TestSigmaTrailingPlusScaleOut:
    """After scale-out tier 1, σ-trailing should use effective prices."""
    def test_sigma_uses_effective_after_scale_out(self):
        from src.trailing_sigma import calculate_sigma_trailing_stop
        # BUY_NO: effective prices passed by caller
        history = [0.35, 0.40, 0.45, 0.50, 0.55, 0.58, 0.56, 0.53]
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.65, price_history=history,
            current_price=0.53, peak_price=0.58, entry_price=0.35,
        )
        assert result["active"] is True
        assert result["stop_price"] >= 0.35


class TestEdgeDecayPlusReentry:
    """Edge decay should reduce effective edge for re-entry decisions."""
    def test_late_match_reentry_lower_edge(self):
        from src.edge_decay import get_decayed_ai_target
        # Early match: full AI target
        early_target = get_decayed_ai_target(0.70, 0.50, 0.10)
        # Late match: decayed target
        late_target = get_decayed_ai_target(0.70, 0.50, 0.90)
        # Late edge should be smaller
        early_edge = abs(early_target - 0.50)
        late_edge = abs(late_target - 0.50)
        assert late_edge < early_edge


class TestResolutionHoldPlusGraduatedSL:
    """When resolution_hold=True, graduated SL should be bypassed unless effective_price < 0.65."""
    def test_resolution_hold_bypasses_sl(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.75,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is True
        # When hold=True AND effective_price >= 0.65, graduated SL is bypassed
        # (portfolio.py will check this — we verify the hold decision here)

    def test_resolution_hold_revoked_on_crash(self):
        """If effective_price drops below 0.65, resolution hold should NOT apply."""
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.60, effective_ai=0.75,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is False  # effective_price < 0.80 → no hold, graduated SL runs normally


class TestAdaptiveKellyPlusCorrelation:
    """Kelly sizing respects correlation exposure limits (spec C8 pipeline)."""
    def test_kelly_then_correlation_cap(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        from src.correlation import apply_correlation_cap

        kelly = get_adaptive_kelly_fraction("high", 0.75, "esports",
                                             config_kelly_by_conf={"high": 0.25})
        bankroll = 500.0
        size_usdc = kelly * bankroll

        # Already have 90 USD on this match — exceeds 15% limit (75 USD)
        positions = [{"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 90.0, "direction": "BUY_YES"}]
        capped = apply_correlation_cap(size_usdc, "cs2-faze-vs-navi", positions, bankroll)
        # Max exposure = 500 * 0.15 = 75. Existing 90 already over → capped to 0
        assert capped == 0.0
```

- [ ] **Step 2: Run integration tests**

Run: `python -m pytest tests/test_integration.py -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration tests for multi-module interactions"
```

---

### Task 19: End-to-End Smoke Test

- [ ] **Step 1:** Run bot in dry_run mode for 1 cycle: `python -m src.main` (manual verification)
- [ ] **Step 2:** Verify no import errors, no crashes, positions load correctly with new default fields
- [ ] **Step 3:** Check logs for any warnings about missing fields or unexpected behavior
- [ ] **Step 4:** Final commit with any fixes

```bash
git commit -m "fix: end-to-end smoke test fixes"
```

---

## Execution Notes

- **Test command:** `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/<file> -v`
- **All tests:** `python -m pytest tests/ -v --tb=short`
- **Working directory:** `C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent`
- **Python:** `python` (3.14, user's local install)
- **Never start the bot live** without user explicit permission
- **Config:** `config.yaml` in project root — never modify risk limits without asking
