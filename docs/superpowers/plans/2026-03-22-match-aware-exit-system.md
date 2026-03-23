# Match-Aware Exit System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace flat stop-loss with a 4-layer exit system that uses match timing, entry price, live score, and profit history to make smarter exit decisions.

**Architecture:** New `src/match_exit.py` module with pure functions for all exit logic. Portfolio calls `check_match_aware_exits()` which delegates to this module. Existing `check_stop_losses()` and `check_esports_halftime_exits()` and `check_pre_match_exits()` are replaced; `check_trailing_stops()`, `check_take_profits()`, `check_volatility_swing_exits()` remain unchanged.

**Tech Stack:** Python 3.11+, Pydantic models, pytest

**Spec:** `docs/superpowers/specs/2026-03-22-match-aware-exit-system-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/match_exit.py` | **CREATE** | All match-aware exit logic: score parsing, duration lookup, graduated stop loss calculation, 4-layer check |
| `src/models.py` | **MODIFY** | Add 6 new Position fields |
| `src/portfolio.py` | **MODIFY** | Add `check_match_aware_exits()`, update `update_price()` for `ever_in_profit` tracking |
| `src/main.py` | **MODIFY** | Wire new exit system, replace old halftime/pre-match exits |
| `tests/test_match_exit.py` | **CREATE** | All unit tests for match exit logic |
| `tests/test_portfolio.py` | **MODIFY** | Add integration test for new exit flow |

---

### Task 1: New Position Fields

**Files:**
- Modify: `src/models.py` (Position class)
- Test: `tests/test_models.py`

- [ ] **Step 1: Write failing test for new fields**

```python
# tests/test_models.py — append to file

def test_position_match_exit_fields():
    """New fields for match-aware exit system."""
    from src.models import Position
    pos = Position(
        condition_id="0xtest", token_id="tok", direction="BUY_YES",
        entry_price=0.55, size_usdc=20.0, shares=36.36, current_price=0.55,
    )
    assert pos.ever_in_profit is False
    assert pos.consecutive_down_cycles == 0
    assert pos.cumulative_drop == 0.0
    assert pos.previous_cycle_price == 0.0
    assert pos.hold_revoked_at is None
    assert pos.hold_was_original is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_models.py::test_position_match_exit_fields -v`
Expected: FAIL — `ever_in_profit` not a field

- [ ] **Step 3: Add fields to Position model**

Add to `src/models.py` Position class, after `pending_resolution`:

```python
    # Match-aware exit system fields
    ever_in_profit: bool = False           # True once peak_pnl_pct > 0.01 (never resets)
    consecutive_down_cycles: int = 0       # Consecutive cycles where price dropped
    cumulative_drop: float = 0.0           # Total price drop during current down streak
    previous_cycle_price: float = 0.0      # Price at last cycle (for momentum tracking)
    hold_revoked_at: datetime | None = None  # When hold-to-resolve was revoked
    hold_was_original: bool = False          # Was this originally a hold-to-resolve position
```

Ensure `from datetime import datetime` is already imported (it should be).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_models.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/models.py tests/test_models.py
git commit -m "feat: add Position fields for match-aware exit system"
```

---

### Task 2: Score Parsing

**Files:**
- Create: `src/match_exit.py`
- Test: `tests/test_match_exit.py`

- [ ] **Step 1: Write failing tests for score parsing**

Create `tests/test_match_exit.py`:

```python
"""Tests for match-aware exit system."""
import pytest


class TestParseMatchScore:
    def test_bo3_ahead(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("2-1|Bo3", number_of_games=3, direction="BUY_YES")
        assert result["available"] is True
        assert result["our_maps"] == 2
        assert result["opp_maps"] == 1
        assert result["map_diff"] == 1
        assert result["is_already_won"] is True  # 2 wins needed in BO3, we have 2

    def test_bo3_behind(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("0-2|Bo3", number_of_games=3, direction="BUY_YES")
        assert result["our_maps"] == 0
        assert result["opp_maps"] == 2
        assert result["map_diff"] == -2
        assert result["is_already_lost"] is True

    def test_bo5_mid_match(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("1-2|Bo5", number_of_games=5, direction="BUY_YES")
        assert result["our_maps"] == 1
        assert result["opp_maps"] == 2
        assert result["map_diff"] == -1
        assert result["is_already_lost"] is False  # Need 3 to win BO5
        assert result["is_already_won"] is False

    def test_buy_no_reverses_sides(self):
        from src.match_exit import parse_match_score
        # BUY_NO means we bet AGAINST the first team
        # Score "2-1" means first team has 2, second has 1
        # For BUY_NO: our side is the second team (opp of YES)
        result = parse_match_score("2-1|Bo3", number_of_games=3, direction="BUY_NO")
        assert result["our_maps"] == 1  # reversed
        assert result["opp_maps"] == 2  # reversed
        assert result["map_diff"] == -1

    def test_simple_score_no_format(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("1-0", number_of_games=3, direction="BUY_YES")
        assert result["our_maps"] == 1
        assert result["opp_maps"] == 0
        assert result["map_diff"] == 1

    def test_empty_score(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("", number_of_games=3, direction="BUY_YES")
        assert result["available"] is False

    def test_none_score(self):
        from src.match_exit import parse_match_score
        result = parse_match_score(None, number_of_games=3, direction="BUY_YES")
        assert result["available"] is False

    def test_unparseable_score(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("Live", number_of_games=3, direction="BUY_YES")
        assert result["available"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::TestParseMatchScore -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement score parsing**

Create `src/match_exit.py`:

```python
"""Match-aware exit system — 4-layer exit logic using match timing, score, and profit history.

Spec: docs/superpowers/specs/2026-03-22-match-aware-exit-system-design.md
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def parse_match_score(
    score_str: str | None,
    number_of_games: int,
    direction: str,
) -> dict:
    """Parse match_score into structured data, direction-aware.

    Args:
        score_str: Raw score string from Gamma API (e.g. "2-1|Bo3", "1-0")
        number_of_games: BO format (1, 3, 5). 0 = unknown, treated as BO3.
        direction: "BUY_YES" or "BUY_NO" — determines which side is "ours"

    Returns:
        dict with keys: available, our_maps, opp_maps, map_diff,
                        is_already_lost, is_already_won
    """
    empty = {"available": False}

    if not score_str or not isinstance(score_str, str):
        return empty

    try:
        # Split format suffix: "2-1|Bo3" → "2-1", "Bo3"
        parts = score_str.split("|")
        scores = parts[0].strip().split("-")
        if len(scores) != 2:
            return empty

        first_score = int(scores[0].strip())
        second_score = int(scores[1].strip())
    except (ValueError, IndexError):
        return empty

    # Direction-aware: BUY_YES = we want first team to win
    #                  BUY_NO  = we want first team to lose (second team wins)
    if direction == "BUY_NO":
        our_maps = second_score
        opp_maps = first_score
    else:
        our_maps = first_score
        opp_maps = second_score

    bo = number_of_games if number_of_games > 0 else 3
    wins_needed = (bo // 2) + 1

    return {
        "available": True,
        "our_maps": our_maps,
        "opp_maps": opp_maps,
        "map_diff": our_maps - opp_maps,
        "is_already_lost": opp_maps >= wins_needed,
        "is_already_won": our_maps >= wins_needed,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::TestParseMatchScore -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/match_exit.py tests/test_match_exit.py
git commit -m "feat: add score parsing for match-aware exit system"
```

---

### Task 3: Game-Specific Duration Lookup

**Files:**
- Modify: `src/match_exit.py`
- Test: `tests/test_match_exit.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_match_exit.py`:

```python
class TestGameDuration:
    def test_cs2_bo3(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("cs2-nrg-furia-2026-03-22", 3) == 130

    def test_cs2_bo1(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("cs2-nrg-furia-2026-03-22", 1) == 40

    def test_valorant_bo5(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("val-lse-s8ul-2026-03-22", 5) == 220

    def test_dota2_bo3(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("dota2-tundra-bb4-2026-03-22", 3) == 130

    def test_lol_bo3(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("lol-g2-blg-2026-03-22", 3) == 100

    def test_football(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("epl-ast-wes-2026-03-22-total-2pt5", 0) == 95

    def test_nba(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("nba-por-den-2026-03-22-total-241pt5", 0) == 150

    def test_mlb(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("mlb-atl-min-2026-03-22", 0) == 180

    def test_nhl(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("nhl-car-pit-2026-03-22", 0) == 150

    def test_college_basketball(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("cbb-ucla-uconn-2026-03-22", 0) == 120

    def test_unknown_fallback(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("some-unknown-market", 0) == 90

    def test_generic_esports_bo3(self):
        from src.match_exit import get_game_duration
        # Unknown esports game but has BO format → generic esports
        assert get_game_duration("hok-team1-team2-2026", 3) == 120
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::TestGameDuration -v`
Expected: FAIL — function not found

- [ ] **Step 3: Implement duration lookup**

Add to `src/match_exit.py`:

```python
# Game-specific duration estimates (minutes)
# Key: (game_prefix, number_of_games) → duration in minutes
_DURATION_TABLE: dict[tuple[str, int], int] = {
    ("cs2", 1): 40,   ("cs2", 3): 130,  ("cs2", 5): 200,
    ("val", 1): 50,    ("val", 3): 140,  ("val", 5): 220,
    ("lol", 1): 35,    ("lol", 3): 100,  ("lol", 5): 160,
    ("dota2", 1): 45,  ("dota2", 3): 130, ("dota2", 5): 210,
}

# Sport detection from slug prefix
_SPORT_DURATION: dict[str, int] = {
    "epl": 95, "laliga": 95, "ucl": 95, "seriea": 95, "bundesliga": 95, "ligue1": 95,
    "nba": 150,
    "cbb": 120,
    "mlb": 180,
    "nhl": 150,
}

# Generic esports fallback (when game is unknown but BO format exists)
_GENERIC_ESPORTS: dict[int, int] = {1: 40, 3: 120, 5: 180}


def get_game_duration(slug: str, number_of_games: int) -> int:
    """Return estimated match duration in minutes.

    Uses game-specific lookup from slug prefix + BO format.
    Falls back to sport-specific, then generic esports, then 90 min default.
    """
    slug_lower = slug.lower()

    # Try game-specific esports lookup
    for prefix in ("cs2", "val", "lol", "dota2"):
        if slug_lower.startswith(f"{prefix}-"):
            bo = number_of_games if number_of_games > 0 else 3
            return _DURATION_TABLE.get((prefix, bo), _DURATION_TABLE.get((prefix, 3), 120))

    # Try sport-specific lookup
    for prefix, duration in _SPORT_DURATION.items():
        if slug_lower.startswith(f"{prefix}-"):
            return duration

    # If BO format is specified, assume generic esports
    if number_of_games in (1, 3, 5):
        return _GENERIC_ESPORTS[number_of_games]

    # Absolute fallback
    return 90
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::TestGameDuration -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/match_exit.py tests/test_match_exit.py
git commit -m "feat: add game-specific duration lookup table"
```

---

### Task 4: Entry-Price Multiplier & Graduated Stop Loss Calculation

**Files:**
- Modify: `src/match_exit.py`
- Test: `tests/test_match_exit.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_match_exit.py`:

```python
class TestEntryPriceMultiplier:
    def test_heavy_underdog(self):
        from src.match_exit import get_entry_price_multiplier
        assert get_entry_price_multiplier(0.15) == 1.50

    def test_underdog(self):
        from src.match_exit import get_entry_price_multiplier
        assert get_entry_price_multiplier(0.25) == 1.25

    def test_coin_flip(self):
        from src.match_exit import get_entry_price_multiplier
        assert get_entry_price_multiplier(0.45) == 1.00

    def test_favorite(self):
        from src.match_exit import get_entry_price_multiplier
        assert get_entry_price_multiplier(0.60) == 0.85

    def test_heavy_favorite(self):
        from src.match_exit import get_entry_price_multiplier
        assert get_entry_price_multiplier(0.80) == 0.70


class TestGraduatedMaxLoss:
    def test_early_match_coin_flip(self):
        from src.match_exit import get_graduated_max_loss
        # 30% progress, 45¢ entry, no score
        loss = get_graduated_max_loss(0.30, 0.45, {"available": False})
        assert loss == pytest.approx(0.40, abs=0.01)  # -40% × 1.0 × 1.0

    def test_mid_match_favorite(self):
        from src.match_exit import get_graduated_max_loss
        # 50% progress, 65¢ entry, no score
        loss = get_graduated_max_loss(0.50, 0.65, {"available": False})
        assert loss == pytest.approx(0.255, abs=0.01)  # -30% × 0.85

    def test_late_match_underdog_ahead(self):
        from src.match_exit import get_graduated_max_loss
        # 75% progress, 25¢ entry, score ahead
        score = {"available": True, "map_diff": 1, "is_already_lost": False, "is_already_won": False}
        loss = get_graduated_max_loss(0.75, 0.25, score)
        # -20% × 1.25 × 1.25 = -31.25%
        assert loss == pytest.approx(0.3125, abs=0.01)

    def test_final_phase_favorite_behind(self):
        from src.match_exit import get_graduated_max_loss
        # 90% progress, 70¢ entry, score behind
        score = {"available": True, "map_diff": -1, "is_already_lost": False, "is_already_won": False}
        loss = get_graduated_max_loss(0.90, 0.70, score)
        # -15% × 0.70 × 0.75 = -7.875%
        assert loss == pytest.approx(0.07875, abs=0.01)

    def test_overtime(self):
        from src.match_exit import get_graduated_max_loss
        loss = get_graduated_max_loss(1.10, 0.50, {"available": False})
        assert loss == pytest.approx(0.05, abs=0.01)  # -5% × 1.0

    def test_pre_match(self):
        from src.match_exit import get_graduated_max_loss
        loss = get_graduated_max_loss(-0.5, 0.50, {"available": False})
        assert loss == pytest.approx(0.40, abs=0.01)  # Pre-match default

    def test_clamp_max(self):
        from src.match_exit import get_graduated_max_loss
        # Heavy underdog early: -40% × 1.50 × 1.25 (ahead) = -75% → clamped to -70%
        score = {"available": True, "map_diff": 1, "is_already_lost": False, "is_already_won": False}
        loss = get_graduated_max_loss(0.30, 0.10, score)
        assert loss <= 0.70

    def test_clamp_min(self):
        from src.match_exit import get_graduated_max_loss
        # Overtime heavy favorite behind: -5% × 0.70 × 0.75 = -2.625% → clamped to -5%
        score = {"available": True, "map_diff": -2, "is_already_lost": False, "is_already_won": False}
        loss = get_graduated_max_loss(1.10, 0.80, score)
        assert loss >= 0.05
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::TestEntryPriceMultiplier tests/test_match_exit.py::TestGraduatedMaxLoss -v`
Expected: FAIL

- [ ] **Step 3: Implement multiplier and graduated calculation**

Add to `src/match_exit.py`:

```python
def get_entry_price_multiplier(entry_price: float) -> float:
    """Return stop loss width multiplier based on entry price.

    Low entry (underdog) → wider tolerance (1.50)
    High entry (favorite) → tighter tolerance (0.70)
    """
    if entry_price < 0.20:
        return 1.50
    elif entry_price < 0.35:
        return 1.25
    elif entry_price < 0.50:
        return 1.00
    elif entry_price < 0.70:
        return 0.85
    else:
        return 0.70


# Base tiers: (elapsed_pct_threshold, max_loss)
# The tier that matches the HIGHEST threshold <= elapsed_pct is used.
_BASE_TIERS = [
    (1.00, 0.05),   # Overtime
    (0.85, 0.15),   # Final phase
    (0.65, 0.20),   # Late match
    (0.40, 0.30),   # Mid match
    (0.00, 0.40),   # Early match
]


def get_graduated_max_loss(
    elapsed_pct: float,
    entry_price: float,
    score_info: dict,
) -> float:
    """Calculate max allowed loss: base_tier × price_mult × score_adj.

    Returns a float in [0.05, 0.70] representing the max loss fraction.
    E.g. 0.30 means position is exited if unrealized_pnl_pct < -0.30.
    """
    # Pre-match: use base -40%
    if elapsed_pct < 0:
        base = 0.40
    else:
        # Find matching tier (sorted descending, first match wins)
        base = 0.40  # default
        for threshold, loss in _BASE_TIERS:
            if elapsed_pct >= threshold:
                base = loss
                break

    # Entry price multiplier
    price_mult = get_entry_price_multiplier(entry_price)

    # Score adjustment
    score_adj = 1.0
    if score_info.get("available"):
        md = score_info.get("map_diff", 0)
        if md > 0:
            score_adj = 1.25  # ahead: loosen
        elif md < 0:
            score_adj = 0.75  # behind: tighten

    result = base * price_mult * score_adj

    # Clamp to [0.05, 0.70]
    return max(0.05, min(0.70, result))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::TestEntryPriceMultiplier tests/test_match_exit.py::TestGraduatedMaxLoss -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/match_exit.py tests/test_match_exit.py
git commit -m "feat: add entry-price-adjusted graduated stop loss calculation"
```

---

### Task 5: 4-Layer Exit Check (Core Logic)

**Files:**
- Modify: `src/match_exit.py`
- Test: `tests/test_match_exit.py`

This is the main function that implements all 4 layers. It takes position data as input and returns exit decisions.

- [ ] **Step 1: Write failing tests for Layer 1 (Catastrophic Floor)**

Append to `tests/test_match_exit.py`:

```python
from datetime import datetime, timezone, timedelta


def _make_pos_data(
    entry_price=0.55, current_price=0.55, peak_pnl_pct=0.0,
    ever_in_profit=False, match_start_iso="", number_of_games=3,
    slug="cs2-test-match", match_score="", direction="BUY_YES",
    scouted=False, confidence="medium_high", ai_probability=0.70,
    consecutive_down_cycles=0, cumulative_drop=0.0,
    hold_revoked_at=None, hold_was_original=False,
    volatility_swing=False, category="esports",
):
    """Helper to build position-like data dict for check_match_exit()."""
    return {
        "entry_price": entry_price,
        "current_price": current_price,
        "peak_pnl_pct": peak_pnl_pct,
        "ever_in_profit": ever_in_profit,
        "match_start_iso": match_start_iso,
        "number_of_games": number_of_games,
        "slug": slug,
        "match_score": match_score,
        "direction": direction,
        "scouted": scouted,
        "confidence": confidence,
        "ai_probability": ai_probability,
        "consecutive_down_cycles": consecutive_down_cycles,
        "cumulative_drop": cumulative_drop,
        "hold_revoked_at": hold_revoked_at,
        "hold_was_original": hold_was_original,
        "volatility_swing": volatility_swing,
        "category": category,
        "unrealized_pnl_pct": (current_price - entry_price) / entry_price if entry_price > 0 else 0,
    }


class TestLayer1CatastrophicFloor:
    def test_favorite_halved_exits(self):
        from src.match_exit import check_match_exit
        data = _make_pos_data(entry_price=0.70, current_price=0.34)
        result = check_match_exit(data)
        assert result["exit"] is True
        assert result["layer"] == "catastrophic_floor"

    def test_underdog_exempt(self):
        from src.match_exit import check_match_exit
        # Entry <25¢ is exempt from catastrophic floor
        data = _make_pos_data(entry_price=0.20, current_price=0.09)
        result = check_match_exit(data)
        # Should NOT exit via catastrophic (Layer 2 might exit but not Layer 1)
        assert result.get("layer") != "catastrophic_floor"

    def test_above_25_not_exempt(self):
        from src.match_exit import check_match_exit
        data = _make_pos_data(entry_price=0.30, current_price=0.14)
        result = check_match_exit(data)
        assert result["exit"] is True
        assert result["layer"] == "catastrophic_floor"

    def test_price_above_half_no_exit(self):
        from src.match_exit import check_match_exit
        data = _make_pos_data(entry_price=0.70, current_price=0.40)
        result = check_match_exit(data)
        assert result.get("layer") != "catastrophic_floor"

    def test_score_already_lost_exits(self):
        from src.match_exit import check_match_exit
        # Even if price hasn't halved, score 0-2 in BO3 = lost
        data = _make_pos_data(
            entry_price=0.50, current_price=0.40,
            match_score="0-2|Bo3", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result["exit"] is True
        assert result["layer"] == "score_terminal"
```

- [ ] **Step 2: Write failing tests for Layer 3 (Never-in-Profit)**

Append to `tests/test_match_exit.py`:

```python
class TestLayer3NeverInProfit:
    def _match_started_ago(self, minutes: int) -> str:
        """Return ISO timestamp for a match that started N minutes ago."""
        return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()

    def test_before_70_pct_no_exit(self):
        from src.match_exit import check_match_exit
        # CS2 BO3 = 130 min. 50 min elapsed = 38% progress. Never in profit, price dropped.
        data = _make_pos_data(
            entry_price=0.60, current_price=0.45,
            match_start_iso=self._match_started_ago(50),
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        # Should NOT exit via never-in-profit (too early)
        assert result.get("layer") != "never_in_profit"

    def test_at_70_pct_price_close_to_entry_stay(self):
        from src.match_exit import check_match_exit
        # 91 min elapsed / 130 = 70%. Price at entry×0.92 → STAY
        data = _make_pos_data(
            entry_price=0.60, current_price=0.55,  # 55/60 = 0.917 > 0.90
            match_start_iso=self._match_started_ago(91),
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result["exit"] is False

    def test_at_70_pct_price_dropped_exit(self):
        from src.match_exit import check_match_exit
        # 91 min / 130 = 70%. Price at entry×0.70 < 0.75 → EXIT
        data = _make_pos_data(
            entry_price=0.60, current_price=0.42,  # 42/60 = 0.70 < 0.75
            match_start_iso=self._match_started_ago(91),
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result["exit"] is True
        assert result["layer"] == "never_in_profit"

    def test_at_70_pct_score_ahead_stay(self):
        from src.match_exit import check_match_exit
        # Even if price dropped below entry×0.75, score ahead → STAY
        data = _make_pos_data(
            entry_price=0.60, current_price=0.42,
            match_start_iso=self._match_started_ago(91),
            slug="cs2-test", number_of_games=3,
            match_score="1-0|Bo3",
        )
        result = check_match_exit(data)
        assert result["exit"] is False

    def test_saw_profit_not_applicable(self):
        from src.match_exit import check_match_exit
        # ever_in_profit=True → Layer 3 doesn't apply
        data = _make_pos_data(
            entry_price=0.60, current_price=0.42,
            ever_in_profit=True, peak_pnl_pct=0.10,
            match_start_iso=self._match_started_ago(91),
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result.get("layer") != "never_in_profit"
```

- [ ] **Step 3: Write failing tests for Layer 4 (Hold-to-Resolve)**

Append to `tests/test_match_exit.py`:

```python
class TestLayer4HoldToResolve:
    def _match_started_ago(self, minutes: int) -> str:
        return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()

    def test_scouted_in_profit_hold(self):
        from src.match_exit import check_match_exit
        data = _make_pos_data(
            entry_price=0.55, current_price=0.65,
            ever_in_profit=True, peak_pnl_pct=0.18,
            scouted=True, confidence="high", ai_probability=0.80,
            match_start_iso=self._match_started_ago(60),
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result["exit"] is False
        assert result.get("revoke_hold") is not True

    def test_scouted_significant_loss_revoke(self):
        from src.match_exit import check_match_exit
        data = _make_pos_data(
            entry_price=0.60, current_price=0.40,  # below entry×0.70
            ever_in_profit=True, peak_pnl_pct=0.15,
            scouted=True, confidence="high", ai_probability=0.80,
            match_start_iso=self._match_started_ago(85),  # 65% progress
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result.get("revoke_hold") is True

    def test_restore_after_recovery(self):
        from src.match_exit import check_match_exit
        data = _make_pos_data(
            entry_price=0.60, current_price=0.52,  # entry×0.867 > 0.85
            ever_in_profit=True, peak_pnl_pct=0.15,
            scouted=False,  # was revoked
            hold_was_original=True,
            hold_revoked_at=datetime.now(timezone.utc) - timedelta(minutes=15),
            confidence="high", ai_probability=0.80,
            match_start_iso=self._match_started_ago(60),
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result.get("restore_hold") is True
```

- [ ] **Step 4: Run all new tests to verify they fail**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py -v -k "Layer1 or Layer3 or Layer4"`
Expected: FAIL — `check_match_exit` not found

- [ ] **Step 5: Implement `check_match_exit()` function**

Add to `src/match_exit.py`:

```python
from datetime import datetime, timezone


def check_match_exit(data: dict) -> dict:
    """Run 4-layer match-aware exit check on a position.

    Args:
        data: Dict with position fields (see _make_pos_data in tests for schema)

    Returns:
        dict with keys:
            exit: bool — should this position be exited?
            layer: str — which layer triggered (if exit=True)
            reason: str — human-readable reason
            revoke_hold: bool — should hold-to-resolve be revoked?
            restore_hold: bool — should hold-to-resolve be restored?
            momentum_tighten: bool — should graduated SL be tightened next cycle?
    """
    result = {"exit": False, "layer": "", "reason": "",
              "revoke_hold": False, "restore_hold": False, "momentum_tighten": False}

    entry_price = data["entry_price"]
    current_price = data["current_price"]
    direction = data.get("direction", "BUY_YES")
    number_of_games = data.get("number_of_games", 0)
    slug = data.get("slug", "")
    match_score = data.get("match_score", "")
    match_start_iso = data.get("match_start_iso", "")
    ever_in_profit = data.get("ever_in_profit", False)
    peak_pnl_pct = data.get("peak_pnl_pct", 0.0)
    scouted = data.get("scouted", False)
    confidence = data.get("confidence", "medium")
    ai_probability = data.get("ai_probability", 0.5)
    consecutive_down = data.get("consecutive_down_cycles", 0)
    cumulative_drop = data.get("cumulative_drop", 0.0)
    hold_revoked_at = data.get("hold_revoked_at")
    hold_was_original = data.get("hold_was_original", False)
    volatility_swing = data.get("volatility_swing", False)
    pnl_pct = data.get("unrealized_pnl_pct", 0.0)

    # VS positions use their own exit system
    if volatility_swing:
        return result

    # --- Step 0: Parse score ---
    score_info = parse_match_score(match_score, number_of_games, direction)

    # --- Step 0a: Score terminal checks ---
    if score_info.get("is_already_lost"):
        return {"exit": True, "layer": "score_terminal",
                "reason": f"Match already lost (score: {match_score})",
                "revoke_hold": False, "restore_hold": False, "momentum_tighten": False}
    if score_info.get("is_already_won"):
        return {"exit": False, "layer": "score_terminal",
                "reason": f"Match already won — hold to resolve (score: {match_score})",
                "revoke_hold": False, "restore_hold": False, "momentum_tighten": False}

    # --- Step 1: Catastrophic Floor (Layer 1) ---
    if entry_price >= 0.25 and current_price < entry_price * 0.50:
        return {"exit": True, "layer": "catastrophic_floor",
                "reason": f"Price {current_price:.3f} < entry×50% ({entry_price*0.50:.3f})",
                "revoke_hold": False, "restore_hold": False, "momentum_tighten": False}

    # --- Step 2: Calculate elapsed_pct ---
    elapsed_pct = -1.0
    if match_start_iso:
        try:
            start_dt = datetime.fromisoformat(match_start_iso.replace("Z", "+00:00"))
            elapsed_min = (datetime.now(timezone.utc) - start_dt).total_seconds() / 60
            duration = get_game_duration(slug, number_of_games)
            elapsed_pct = elapsed_min / duration if duration > 0 else 0
        except (ValueError, TypeError):
            pass

    if elapsed_pct < 0:
        # No match timing → can't do graduated/never-in-profit checks
        # Return no exit, let existing flat stop loss handle
        return result

    # --- Step 3: Graduated Stop Loss (Layer 2) ---
    max_loss = get_graduated_max_loss(elapsed_pct, entry_price, score_info)

    # Momentum tightening: if 3+ consecutive down cycles with 5¢+ drop, tighten one tier
    if consecutive_down >= 3 and cumulative_drop >= 0.05:
        result["momentum_tighten"] = True
        # Tighten by moving to next tier's value
        max_loss = max(0.05, max_loss * 0.75)  # Reduce tolerance by 25%

    if pnl_pct < -max_loss:
        return {**result, "exit": True, "layer": "graduated_sl",
                "reason": f"PnL {pnl_pct:.1%} < -{max_loss:.1%} (elapsed {elapsed_pct:.0%})"}

    # --- Step 4: Never-in-Profit Guard (Layer 3) ---
    if not ever_in_profit and peak_pnl_pct <= 0.01 and elapsed_pct >= 0.70:
        # Score ahead → STAY regardless
        if score_info.get("available") and score_info.get("map_diff", 0) > 0:
            pass  # Stay — winning despite no profit
        elif current_price >= entry_price * 0.90:
            pass  # Stay — close to entry, right side
        elif current_price < entry_price * 0.75:
            return {**result, "exit": True, "layer": "never_in_profit",
                    "reason": f"Never profited + 70%+ done + price {current_price:.3f} < entry×75% ({entry_price*0.75:.3f})"}
        # Between 0.75 and 0.90: Layer 2 handles via graduated SL

        # Force exit at 80%+ if price < entry×0.75 and score not ahead
        if elapsed_pct >= 0.80 and current_price < entry_price * 0.75:
            score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
            if not score_ahead:
                return {**result, "exit": True, "layer": "never_in_profit",
                        "reason": f"Force exit at 80%+ — never profited, price {current_price:.3f}"}

    # --- Step 5: Hold-to-Resolve Check (Layer 4) ---
    is_hold_candidate = scouted or (
        ai_probability >= 0.65 and confidence in ("high", "medium_high")
    )

    if is_hold_candidate:
        # Check revocation
        # Momentum guard: dips shorter than 3 cycles or smaller than 5¢ are temporary → keep hold
        dip_is_temporary = (consecutive_down < 3 or cumulative_drop < 0.05)

        if ever_in_profit and current_price < entry_price * 0.70 and elapsed_pct > 0.60:
            score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
            if not score_ahead and not dip_is_temporary:
                result["revoke_hold"] = True
                result["reason"] = f"Hold revoked: saw profit but now at {current_price:.3f} < entry×70%"

        if not ever_in_profit and current_price < entry_price * 0.75 and elapsed_pct > 0.70:
            score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
            if not score_ahead and not dip_is_temporary:
                result["revoke_hold"] = True
                result["exit"] = True
                result["layer"] = "hold_revoked"
                result["reason"] = f"Hold revoked + exit: never profited, {current_price:.3f} < entry×75% at {elapsed_pct:.0%}"

    # Check restore (if previously revoked)
    if hold_was_original and not scouted and hold_revoked_at:
        try:
            revoked_dt = hold_revoked_at if isinstance(hold_revoked_at, datetime) else \
                datetime.fromisoformat(str(hold_revoked_at).replace("Z", "+00:00"))
            minutes_since = (datetime.now(timezone.utc) - revoked_dt).total_seconds() / 60
            if minutes_since >= 10 and current_price > entry_price * 0.85:
                score_behind = score_info.get("available") and score_info.get("map_diff", 0) < 0
                if not score_behind:
                    result["restore_hold"] = True
                    result["reason"] = f"Hold restored: price recovered to {current_price:.3f} > entry×85%"
        except (ValueError, TypeError):
            pass

    return result
```

- [ ] **Step 6: Run all tests**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/match_exit.py tests/test_match_exit.py
git commit -m "feat: implement 4-layer check_match_exit() core logic"
```

---

### Task 6: Portfolio Integration

**Files:**
- Modify: `src/portfolio.py`
- Test: `tests/test_portfolio.py`

- [ ] **Step 1: Write failing integration test**

Append to `tests/test_portfolio.py`:

```python
def test_match_aware_exit_catastrophic():
    """Integration: catastrophic floor exits via check_match_aware_exits."""
    from src.portfolio import Portfolio
    pf = Portfolio()
    pf.add_position("0xcat", "tok", "BUY_YES", 0.70, 20.0, 28.57, "cs2-test-match",
                     category="esports", number_of_games=3)
    pf.update_price("0xcat", 0.34)  # Below entry×50%
    exits = pf.check_match_aware_exits()
    assert "0xcat" in [e["condition_id"] for e in exits]
    assert any(e["layer"] == "catastrophic_floor" for e in exits)


def test_ever_in_profit_tracking():
    """update_price sets ever_in_profit when peak exceeds 1%."""
    from src.portfolio import Portfolio
    pf = Portfolio()
    pf.add_position("0xeip", "tok", "BUY_YES", 0.50, 20.0, 40.0, "test")
    assert pf.positions["0xeip"].ever_in_profit is False
    pf.update_price("0xeip", 0.52)  # +4% profit
    assert pf.positions["0xeip"].ever_in_profit is True
    pf.update_price("0xeip", 0.45)  # Back to loss
    assert pf.positions["0xeip"].ever_in_profit is True  # Never resets
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_portfolio.py::test_match_aware_exit_catastrophic tests/test_portfolio.py::test_ever_in_profit_tracking -v`
Expected: FAIL

- [ ] **Step 3: Update `update_price()` in `src/portfolio.py`**

In `src/portfolio.py`, modify `update_price()` (around line 175):

```python
    def update_price(self, condition_id: str, new_price: float) -> None:
        if condition_id in self.positions:
            pos = self.positions[condition_id]
            # Momentum tracking
            pos.previous_cycle_price = pos.current_price
            pos.current_price = new_price
            # Track peak PnL for trailing stop
            if pos.unrealized_pnl_pct > pos.peak_pnl_pct:
                pos.peak_pnl_pct = pos.unrealized_pnl_pct
            # Track ever_in_profit (never resets)
            if not pos.ever_in_profit and pos.peak_pnl_pct > 0.01:
                pos.ever_in_profit = True
            # Track consecutive down cycles for momentum alert
            if pos.previous_cycle_price > 0 and new_price < pos.previous_cycle_price:
                pos.consecutive_down_cycles += 1
                pos.cumulative_drop += (pos.previous_cycle_price - new_price)
            else:
                pos.consecutive_down_cycles = 0
                pos.cumulative_drop = 0.0
```

- [ ] **Step 4: Add `check_match_aware_exits()` to Portfolio**

Add new method to `src/portfolio.py` (after `check_esports_halftime_exits`):

```python
    def check_match_aware_exits(self) -> list[dict]:
        """Run 4-layer match-aware exit check on all positions.

        Returns list of dicts with: condition_id, layer, reason, exit, revoke_hold, restore_hold
        """
        from src.match_exit import check_match_exit

        results = []
        for cid, pos in self.positions.items():
            # Skip stale prices
            if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
                continue
            # O/U and spread markets: hold to resolution
            if self._is_totals_or_spread(pos):
                continue

            data = {
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "peak_pnl_pct": pos.peak_pnl_pct,
                "ever_in_profit": pos.ever_in_profit,
                "match_start_iso": pos.match_start_iso,
                "number_of_games": pos.number_of_games,
                "slug": pos.slug,
                "match_score": pos.match_score,
                "direction": pos.direction,
                "scouted": pos.scouted,
                "confidence": pos.confidence,
                "ai_probability": pos.ai_probability,
                "consecutive_down_cycles": pos.consecutive_down_cycles,
                "cumulative_drop": pos.cumulative_drop,
                "hold_revoked_at": pos.hold_revoked_at,
                "hold_was_original": pos.hold_was_original,
                "volatility_swing": pos.volatility_swing,
                "category": pos.category,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
            }

            check = check_match_exit(data)
            if check["exit"] or check["revoke_hold"] or check["restore_hold"]:
                results.append({"condition_id": cid, **check})

        return results
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_portfolio.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/portfolio.py tests/test_portfolio.py
git commit -m "feat: integrate match-aware exits into Portfolio"
```

---

### Task 7: Main Loop Wiring

**Files:**
- Modify: `src/main.py`

This task wires the new exit system into the main loop, replacing the old halftime and pre-match exits.

- [ ] **Step 1: Find both exit check blocks in `src/main.py`**

There are TWO blocks (pre-match cycle ~line 383 and in-match cycle ~line 485) that call:
- `check_stop_losses()`
- `check_take_profits()`
- `check_trailing_stops()`
- `check_volatility_swing_exits()`
- `check_pre_match_exits()`
- `check_esports_halftime_exits()`

- [ ] **Step 2: Add match-aware exit call BEFORE existing checks**

In BOTH blocks, add this code BEFORE the `check_stop_losses()` call:

```python
        # --- Match-aware exit system (4 layers) ---
        match_exit_results = self.portfolio.check_match_aware_exits()
        match_exited_cids = set()
        for mexr in match_exit_results:
            cid = mexr["condition_id"]
            if mexr.get("exit"):
                self._exit_position(cid, f"match_exit_{mexr['layer']}")
                match_exited_cids.add(cid)
                logger.info("Match-aware exit [%s]: %s — %s",
                            mexr["layer"], self.portfolio.positions.get(cid, {}).slug if cid in self.portfolio.positions else cid[:10],
                            mexr.get("reason", ""))
            if mexr.get("revoke_hold") and cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                if pos.scouted:
                    pos.hold_was_original = True
                    pos.scouted = False
                    pos.hold_revoked_at = datetime.now(timezone.utc)
                    logger.info("Hold-to-resolve REVOKED: %s — %s", pos.slug[:40], mexr.get("reason", ""))
            if mexr.get("restore_hold") and cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                pos.scouted = True
                pos.hold_revoked_at = None
                logger.info("Hold-to-resolve RESTORED: %s — %s", pos.slug[:40], mexr.get("reason", ""))
```

- [ ] **Step 3: Skip already-exited positions in existing checks**

After the match-aware block, the existing `check_stop_losses()` etc. should skip positions already exited. Since `_exit_position()` removes from `self.portfolio.positions`, this happens automatically.

- [ ] **Step 4: Remove old halftime and pre-match exit calls**

In BOTH blocks, remove or comment out:
```python
        # REMOVED — replaced by match-aware exit system Layer 2
        # for cid in self.portfolio.check_pre_match_exits(minutes_before=30):
        #     self._exit_position(cid, "pre_match_exit")
        # for cid in self.portfolio.check_esports_halftime_exits():
        #     self._exit_position(cid, "esports_halftime_loss")
```

Keep `check_stop_losses()` as fallback for positions without match timing data. Keep `check_trailing_stops()`, `check_take_profits()`, `check_volatility_swing_exits()` unchanged.

- [ ] **Step 5: Test manually**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v --ignore=tests/.venv -x`
Expected: ALL existing tests pass

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/main.py
git commit -m "feat: wire match-aware exit system into main loop, replace halftime/pre-match exits"
```

---

### Task 8: Ultra-Low Guard & Pending Resolution Fix

**Files:**
- Modify: `src/match_exit.py`
- Test: `tests/test_match_exit.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_match_exit.py`:

```python
class TestUltraLowGuard:
    def _match_started_ago(self, minutes: int) -> str:
        return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()

    def test_ultra_low_late_match_exit(self):
        from src.match_exit import check_match_exit
        # Entry <9¢, price <5¢, elapsed >90% → should exit
        data = _make_pos_data(
            entry_price=0.07, current_price=0.03,
            match_start_iso=self._match_started_ago(120),  # 120/130 = 92%
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result["exit"] is True
        assert result["layer"] == "ultra_low_guard"

    def test_ultra_low_early_match_no_exit(self):
        from src.match_exit import check_match_exit
        # Entry <9¢, price <5¢, but elapsed only 30% → don't exit
        data = _make_pos_data(
            entry_price=0.07, current_price=0.03,
            match_start_iso=self._match_started_ago(39),  # 39/130 = 30%
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result["exit"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py::TestUltraLowGuard -v`

- [ ] **Step 3: Add ultra-low guard to `check_match_exit()`**

In `src/match_exit.py`, in `check_match_exit()`, add AFTER the elapsed_pct calculation and BEFORE graduated stop loss:

```python
    # Ultra-low entry (<9¢) guard: normally exempt from stop loss, but
    # if match is >90% done and price <5¢, exit (position is dead)
    if entry_price < 0.09 and elapsed_pct >= 0.90 and current_price < 0.05:
        return {**result, "exit": True, "layer": "ultra_low_guard",
                "reason": f"Ultra-low {entry_price:.0f}¢ at {elapsed_pct:.0%} done, price {current_price:.0f}¢ < 5¢"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/match_exit.py tests/test_match_exit.py
git commit -m "feat: add ultra-low guard and pending resolution handling"
```

---

### Task 9: Price History Collection

**Files:**
- Create: `src/price_history.py`
- Modify: `src/main.py` (in `_exit_position`)

- [ ] **Step 1: Create price history collector**

Create `src/price_history.py`:

```python
"""Collect CLOB price history on position close for future calibration."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

PRICE_HISTORY_DIR = Path("logs/price_history")


def save_price_history(
    slug: str,
    token_id: str,
    entry_price: float,
    exit_price: float,
    exit_reason: str,
    exit_layer: str,
    match_start_iso: str,
    number_of_games: int,
    ever_in_profit: bool,
    peak_pnl_pct: float,
    match_score: str,
) -> None:
    """Fetch CLOB price history and save to disk."""
    try:
        resp = requests.get(
            "https://clob.polymarket.com/prices-history",
            params={"market": token_id, "interval": "max", "fidelity": "60"},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("Price history fetch failed for %s: %d", slug[:30], resp.status_code)
            return

        history = resp.json().get("history", [])

        record = {
            "slug": slug,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "exit_layer": exit_layer,
            "match_start_iso": match_start_iso,
            "number_of_games": number_of_games,
            "ever_in_profit": ever_in_profit,
            "peak_pnl_pct": peak_pnl_pct,
            "match_score": match_score,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "price_history": history,
        }

        PRICE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        safe_slug = slug.replace("/", "_")[:80]
        path = PRICE_HISTORY_DIR / f"{safe_slug}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        logger.info("Saved price history: %s (%d points)", slug[:30], len(history))

    except Exception as e:
        logger.warning("Price history save failed for %s: %s", slug[:30], e)
```

- [ ] **Step 2: Wire into `_exit_position()` in `src/main.py`**

At the end of `_exit_position()`, after the notifier.send() call, add:

```python
        # Collect price history for future calibration
        try:
            from src.price_history import save_price_history
            save_price_history(
                slug=pos.slug,
                token_id=pos.token_id,
                entry_price=pos.entry_price,
                exit_price=pos.current_price,
                exit_reason=reason,
                exit_layer=reason.replace("match_exit_", "") if reason.startswith("match_exit_") else "",
                match_start_iso=getattr(pos, "match_start_iso", ""),
                number_of_games=getattr(pos, "number_of_games", 0),
                ever_in_profit=getattr(pos, "ever_in_profit", False),
                peak_pnl_pct=getattr(pos, "peak_pnl_pct", 0.0),
                match_score=getattr(pos, "match_score", ""),
            )
        except Exception as e:
            logger.debug("Price history collection skipped: %s", e)
```

- [ ] **Step 3: Test manually**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v --ignore=tests/.venv -x`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/price_history.py src/main.py
git commit -m "feat: add CLOB price history collection on position close"
```

---

### Task 10: Full Integration Test

**Files:**
- Test: `tests/test_match_exit.py`

- [ ] **Step 1: Write scenario tests from spec success criteria**

Append to `tests/test_match_exit.py`:

```python
class TestSuccessCriteria:
    """Tests from spec success criteria — validates real-world scenarios."""

    def _match_started_ago(self, minutes: int) -> str:
        return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()

    def test_xcrew_scenario_prevented(self):
        """Entry 70¢, drops to 35¢ → catastrophic floor exits instead of -99%."""
        from src.match_exit import check_match_exit
        data = _make_pos_data(entry_price=0.70, current_price=0.35)
        result = check_match_exit(data)
        assert result["exit"] is True
        assert result["layer"] == "catastrophic_floor"

    def test_liverpool_scenario_preserved(self):
        """Entry 70¢ (AI 85%), price 66¢, team winning → no exit."""
        from src.match_exit import check_match_exit
        data = _make_pos_data(
            entry_price=0.70, current_price=0.66,
            ai_probability=0.85, confidence="high", scouted=True,
            match_start_iso=self._match_started_ago(60),
            slug="epl-test", number_of_games=0,
        )
        result = check_match_exit(data)
        assert result["exit"] is False

    def test_panic_dip_survived(self):
        """Entry 60¢, spiked to 75¢, dropped to 55¢ on goal against → no exit."""
        from src.match_exit import check_match_exit
        data = _make_pos_data(
            entry_price=0.60, current_price=0.55,
            ever_in_profit=True, peak_pnl_pct=0.25,  # Saw 75¢
            match_start_iso=self._match_started_ago(45),
            slug="epl-test", number_of_games=0,
        )
        result = check_match_exit(data)
        assert result["exit"] is False

    def test_never_in_profit_caught(self):
        """Entry 65¢, never profits, 70% done, price 48¢ → exit."""
        from src.match_exit import check_match_exit
        data = _make_pos_data(
            entry_price=0.65, current_price=0.48,  # 48/65 = 0.738 < 0.75
            match_start_iso=self._match_started_ago(91),  # 91/130 = 70%
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result["exit"] is True
        assert result["layer"] == "never_in_profit"

    def test_bo3_score_02_immediate_exit(self):
        """BO3 score 0-2 → immediate exit."""
        from src.match_exit import check_match_exit
        data = _make_pos_data(
            entry_price=0.50, current_price=0.40,
            match_score="0-2|Bo3", number_of_games=3,
        )
        result = check_match_exit(data)
        assert result["exit"] is True
        assert result["layer"] == "score_terminal"

    def test_bo3_score_10_no_exit(self):
        """BO3 score 1-0, never in profit, price dipped → STAY (score ahead)."""
        from src.match_exit import check_match_exit
        data = _make_pos_data(
            entry_price=0.60, current_price=0.42,
            match_start_iso=self._match_started_ago(91),
            slug="cs2-test", number_of_games=3,
            match_score="1-0|Bo3",
        )
        result = check_match_exit(data)
        assert result["exit"] is False

    def test_underdog_protection(self):
        """Entry 20¢, drops to 12¢ → no catastrophic (exempt), graduated handles."""
        from src.match_exit import check_match_exit
        data = _make_pos_data(entry_price=0.20, current_price=0.12)
        result = check_match_exit(data)
        assert result.get("layer") != "catastrophic_floor"

    def test_favorite_early_catch(self):
        """Entry 75¢, mid-match, price 58¢ → graduated SL catches earlier than flat -40%."""
        from src.match_exit import check_match_exit
        data = _make_pos_data(
            entry_price=0.75, current_price=0.58,  # PnL = -22.7%
            match_start_iso=self._match_started_ago(65),  # 65/130 = 50% (mid-match)
            slug="cs2-test", number_of_games=3,
        )
        result = check_match_exit(data)
        # -30% base × 0.70 mult (>70¢ entry) = -21%. PnL is -22.7% > -21% → EXIT
        assert result["exit"] is True
        assert result["layer"] == "graduated_sl"
```

- [ ] **Step 2: Run all tests**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_match_exit.py -v`
Expected: ALL PASS

- [ ] **Step 3: Run full test suite**

Run: `cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v --ignore=.venv -x`
Expected: ALL PASS

- [ ] **Step 4: Final commit**

```bash
cd "C:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add tests/test_match_exit.py
git commit -m "test: add success criteria scenario tests for match-aware exit system"
```

---

## Summary

| Task | What | Files | Est. Time |
|---|---|---|---|
| 1 | Position model fields | models.py | 2 min |
| 2 | Score parsing | match_exit.py | 5 min |
| 3 | Duration lookup | match_exit.py | 3 min |
| 4 | Graduated stop loss calc | match_exit.py | 5 min |
| 5 | 4-layer core logic | match_exit.py | 10 min |
| 6 | Portfolio integration | portfolio.py | 5 min |
| 7 | Main loop wiring | main.py | 5 min |
| 8 | Ultra-low guard | match_exit.py | 3 min |
| 9 | Price history collection | price_history.py, main.py | 5 min |
| 10 | Integration tests | test_match_exit.py | 5 min |
