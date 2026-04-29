"""Tests for tennis exit logic — Phase 1 v1 set-bazlı tablo (BO3 only).

Spec: docs/superpowers/specs/2026-04-29-tennis-magnus-live-system-design.md §6
DECISIONS.md tennis section.

Direction handling:
- BUY_YES → we bet on player A (home team in Polymarket convention)
- BUY_NO  → we bet on player B (away team)
For BUY_NO bets, "Set 1 lost" means player A won set 1.

Set-bazlı tablo (BO3):
- pre-match (no sets): HOLD
- 1-0 sets (won): HOLD (profit_lock at bid>=0.80)
- 0-1 sets, close loss (4-6 / 5-7 / 6-7): HOLD
- 0-1 sets, decisive (1-6 / 2-6 / 3-6): SELL_50 SET_LOSS_DECISIVE
- 0-1 sets, bagel (0-6): SELL_75 SET_LOSS_BAGEL
- 1-1 sets: HOLD
- 0-2 sets: SELL_ALL MATEMATICAL_DEATH
- bid >= 0.95 anytime: SELL_ALL NEAR_RESOLVE (overrides)
- bid >= 0.80 (and not yet locked): SELL_50 PROFIT_LOCK
- price/entry <= 0.30: SELL_ALL STRUCTURAL_DAMAGE
"""
from __future__ import annotations

import pytest

from src.strategy.exit._tennis_exit_dispatch import (
    ExitAction,
    ExitReason,
    TennisExitConfig,
    TennisExitDecision,
    decide_tennis_exit,
)


def _decide(**overrides):
    """Helper. Defaults to mid-match BUY_YES, neutral state, BO3."""
    defaults = dict(
        cfg=TennisExitConfig(),
        entry_price=0.50,
        current_bid=0.50,
        current_price=0.50,
        sets_won_home=0,
        sets_won_away=0,
        games_home=0,
        games_away=0,
        current_set=1,
        is_bo5=False,
        direction="BUY_YES",
    )
    defaults.update(overrides)
    return decide_tennis_exit(**defaults)


# ─────────────────────────── Pre-match / Empty state ────────────────────────


class TestPreMatch:
    def test_pre_match_no_sets_no_games_holds(self):
        d = _decide(sets_won_home=0, sets_won_away=0,
                    games_home=0, games_away=0, current_set=1)
        assert d.action == ExitAction.HOLD
        assert d.reason == ExitReason.HOLD


# ─────────────────────────── Set state — BUY_YES (we are A) ─────────────────


class TestBuyYesSetWon:
    def test_one_set_won_no_profit_lock_holds(self):
        # 1-0 sets, bid moderate → HOLD
        d = _decide(sets_won_home=1, sets_won_away=0, current_set=2,
                    current_bid=0.60)
        assert d.action == ExitAction.HOLD
        assert d.reason == ExitReason.HOLD

    def test_one_set_won_with_profit_lock_triggers_sell_50(self):
        # 1-0 sets, bid >= 0.80 → PROFIT_LOCK
        d = _decide(sets_won_home=1, sets_won_away=0, current_set=2,
                    current_bid=0.82)
        assert d.action == ExitAction.SELL_50
        assert d.reason == ExitReason.PROFIT_LOCK


class TestBuyYesSetLostClose:
    """0-1 sets, close set loss (we lost as A) → HOLD."""

    @pytest.mark.parametrize("ours,theirs", [(4, 6), (5, 7), (6, 7)])
    def test_close_loss_holds(self, ours, theirs):
        d = _decide(sets_won_home=0, sets_won_away=1, current_set=2,
                    last_completed_set_home=ours,
                    last_completed_set_away=theirs)
        assert d.action == ExitAction.HOLD


class TestBuyYesSetLostDecisive:
    """0-1 sets, decisive set loss → SELL_50."""

    @pytest.mark.parametrize("ours,theirs", [(1, 6), (2, 6), (3, 6)])
    def test_decisive_loss_sells_50(self, ours, theirs):
        d = _decide(sets_won_home=0, sets_won_away=1, current_set=2,
                    last_completed_set_home=ours,
                    last_completed_set_away=theirs)
        assert d.action == ExitAction.SELL_50
        assert d.reason == ExitReason.SET_LOSS_DECISIVE


class TestBuyYesSetLostBagel:
    """0-1 sets, 0-6 bagel → SELL_75."""

    def test_bagel_sells_75(self):
        d = _decide(sets_won_home=0, sets_won_away=1, current_set=2,
                    last_completed_set_home=0,
                    last_completed_set_away=6)
        assert d.action == ExitAction.SELL_75
        assert d.reason == ExitReason.SET_LOSS_BAGEL


class TestBuyYesEvenSets:
    def test_one_one_holds(self):
        d = _decide(sets_won_home=1, sets_won_away=1, current_set=3)
        assert d.action == ExitAction.HOLD


class TestBuyYesMathDeath:
    def test_zero_two_sets_bo3_sells_all(self):
        # 0-2 in BO3 → mathematical death (cannot win)
        d = _decide(sets_won_home=0, sets_won_away=2, current_set=3,
                    is_bo5=False)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.MATEMATICAL_DEATH


class TestBuyYesNearResolve:
    def test_two_zero_sets_bid_high_near_resolve(self):
        # 2-0 sets in BO3 → bid would be >= 0.95 typically → NEAR_RESOLVE
        d = _decide(sets_won_home=2, sets_won_away=0, current_set=3,
                    current_bid=0.96)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.NEAR_RESOLVE


# ─────────────────────────── Direction handling — BUY_NO ────────────────────


class TestBuyNoDirection:
    """For BUY_NO, we are betting on player B (away). 'Our' set = away_set."""

    def test_buy_no_a_won_set_treated_as_loss(self):
        # Sets 1-0 (home/A won 1, away/B won 0) but we're BUY_NO (we = B).
        # So this is a SET LOSS for us. With decisive 6-2 → SELL_50.
        d = _decide(sets_won_home=1, sets_won_away=0, current_set=2,
                    last_completed_set_home=6,
                    last_completed_set_away=2,
                    direction="BUY_NO")
        assert d.action == ExitAction.SELL_50
        assert d.reason == ExitReason.SET_LOSS_DECISIVE

    def test_buy_no_a_won_bagel_sells_75(self):
        d = _decide(sets_won_home=1, sets_won_away=0, current_set=2,
                    last_completed_set_home=6,
                    last_completed_set_away=0,
                    direction="BUY_NO")
        assert d.action == ExitAction.SELL_75
        assert d.reason == ExitReason.SET_LOSS_BAGEL

    def test_buy_no_b_won_set_holds(self):
        # 0-1 sets (B won 1) → from B's perspective, B is winning → HOLD
        d = _decide(sets_won_home=0, sets_won_away=1, current_set=2,
                    direction="BUY_NO")
        assert d.action == ExitAction.HOLD

    def test_buy_no_two_zero_sets_buy_no_math_death(self):
        # 2-0 sets (A won 2) → from B's perspective, B is dead → SELL_ALL
        d = _decide(sets_won_home=2, sets_won_away=0, current_set=3,
                    direction="BUY_NO", is_bo5=False)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.MATEMATICAL_DEATH


# ─────────────────────────── Override layer — bid filters ───────────────────


class TestNearResolveOverride:
    def test_near_resolve_fires_regardless_of_set_state(self):
        # Pre-match style state but bid spike >= 0.95 → NEAR_RESOLVE
        d = _decide(sets_won_home=0, sets_won_away=0, current_set=1,
                    current_bid=0.95)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.NEAR_RESOLVE

    def test_near_resolve_priority_over_set_loss(self):
        # 0-1 decisive set loss BUT bid still 0.95 → NEAR_RESOLVE wins
        d = _decide(sets_won_home=0, sets_won_away=1, current_set=2,
                    last_completed_set_home=2, last_completed_set_away=6,
                    current_bid=0.96)
        assert d.reason == ExitReason.NEAR_RESOLVE
        assert d.action == ExitAction.SELL_ALL


class TestProfitLock:
    def test_profit_lock_at_threshold_sells_50(self):
        d = _decide(current_bid=0.80)
        assert d.action == ExitAction.SELL_50
        assert d.reason == ExitReason.PROFIT_LOCK

    def test_profit_lock_below_threshold_no_trigger(self):
        d = _decide(current_bid=0.79)
        assert d.reason != ExitReason.PROFIT_LOCK


class TestStructuralDamage:
    def test_price_collapsed_below_ratio_sells_all(self):
        # entry 0.50, current 0.10 → ratio 0.20 < 0.30 → SELL_ALL
        d = _decide(entry_price=0.50, current_price=0.10, current_bid=0.10)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.STRUCTURAL_DAMAGE

    def test_price_at_ratio_no_trigger(self):
        d = _decide(entry_price=0.50, current_price=0.16, current_bid=0.16)
        # ratio = 0.32 → no trigger
        assert d.reason != ExitReason.STRUCTURAL_DAMAGE

    def test_zero_entry_price_no_division(self):
        d = _decide(entry_price=0.0, current_price=0.10, current_bid=0.10)
        # Should not crash, no STRUCTURAL_DAMAGE fire
        assert d.reason != ExitReason.STRUCTURAL_DAMAGE


# ─────────────────────────── BO5 handling (Phase 2 deferred) ────────────────


class TestBo5SafeFallback:
    def test_bo5_with_zero_two_does_not_math_death(self):
        # In BO5, 0-2 is recoverable. Phase 1 returns HOLD safely.
        d = _decide(sets_won_home=0, sets_won_away=2, current_set=3,
                    is_bo5=True)
        # Should NOT be MATEMATICAL_DEATH
        assert d.reason != ExitReason.MATEMATICAL_DEATH

    def test_bo5_zero_three_sets_math_death(self):
        # In BO5, 0-3 IS mathematical death
        d = _decide(sets_won_home=0, sets_won_away=3, current_set=4,
                    is_bo5=True)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.MATEMATICAL_DEATH

    def test_bo5_set_loss_does_not_fire_phase1(self):
        # Phase 1 v1: BO5 set loss does NOT trigger SELL_50/75 (deferred Phase 2).
        # Bayesian model needed for BO5. Safe default: HOLD on set loss.
        d = _decide(sets_won_home=0, sets_won_away=1, current_set=2,
                    last_completed_set_home=2, last_completed_set_away=6,
                    is_bo5=True)
        assert d.action == ExitAction.HOLD


# ─────────────────────────── Decision is immutable ──────────────────────────


class TestDecisionShape:
    def test_decision_is_frozen(self):
        d = _decide()
        with pytest.raises(Exception):
            d.action = ExitAction.SELL_ALL  # type: ignore

    def test_decision_carries_note(self):
        d = _decide(current_bid=0.95)
        assert "0.95" in d.note or "bid" in d.note


# ─────────────────────────── Wrapper test (check function) ──────────────────


class TestCheckWrapper:
    """tennis_score_exit.check() — thin adapter for monitor.py legacy call."""

    def test_check_returns_none_for_hold(self):
        from src.strategy.exit import tennis_score_exit
        score_info = {
            "available": True,
            "sets_won_home": 0,
            "sets_won_away": 0,
            "games_home": 0,
            "games_away": 0,
            "current_set": 1,
            "linescores": [],
            "our_is_home": True,
        }
        result = tennis_score_exit.check(
            score_info=score_info,
            current_price=0.50,
            sport_tag="tennis",
            entry_price=0.50,
            direction="BUY_YES",
        )
        assert result is None

    def test_check_returns_signal_for_math_death(self):
        from src.strategy.exit import tennis_score_exit
        score_info = {
            "available": True,
            "sets_won_home": 0,
            "sets_won_away": 2,
            "games_home": 0,
            "games_away": 0,
            "current_set": 3,
            "linescores": [[2, 6], [4, 6]],
            "our_is_home": True,
        }
        result = tennis_score_exit.check(
            score_info=score_info,
            current_price=0.20,
            sport_tag="tennis",
            entry_price=0.50,
            direction="BUY_YES",
        )
        assert result is not None
        assert result.sell_pct == 1.0
        assert result.partial is False

    def test_check_returns_partial_for_profit_lock(self):
        from src.strategy.exit import tennis_score_exit
        score_info = {
            "available": True,
            "sets_won_home": 1,
            "sets_won_away": 0,
            "games_home": 0,
            "games_away": 0,
            "current_set": 2,
            "linescores": [[6, 3]],
            "our_is_home": True,
        }
        result = tennis_score_exit.check(
            score_info=score_info,
            current_price=0.85,
            sport_tag="tennis",
            entry_price=0.50,
            direction="BUY_YES",
        )
        assert result is not None
        assert result.partial is True
        assert result.sell_pct == 0.50

    def test_check_returns_partial_75_for_bagel(self):
        from src.strategy.exit import tennis_score_exit
        score_info = {
            "available": True,
            "sets_won_home": 0,
            "sets_won_away": 1,
            "games_home": 0,
            "games_away": 0,
            "current_set": 2,
            "linescores": [[0, 6]],
            "our_is_home": True,
        }
        result = tennis_score_exit.check(
            score_info=score_info,
            current_price=0.30,
            sport_tag="tennis",
            entry_price=0.50,
            direction="BUY_YES",
        )
        assert result is not None
        assert result.partial is True
        assert result.sell_pct == 0.75

    def test_check_buy_no_inverts_perspective(self):
        from src.strategy.exit import tennis_score_exit
        # BUY_NO + home (A) bagel'd away (B) 6-0 → from B's perspective bagel
        score_info = {
            "available": True,
            "sets_won_home": 1,
            "sets_won_away": 0,
            "games_home": 0,
            "games_away": 0,
            "current_set": 2,
            "linescores": [[6, 0]],
            "our_is_home": False,
        }
        result = tennis_score_exit.check(
            score_info=score_info,
            current_price=0.20,
            sport_tag="tennis",
            entry_price=0.50,
            direction="BUY_NO",
        )
        assert result is not None
        assert result.sell_pct == 0.75

    def test_check_score_unavailable_returns_none(self):
        from src.strategy.exit import tennis_score_exit
        result = tennis_score_exit.check(
            score_info={"available": False},
            current_price=0.50,
            sport_tag="tennis",
            entry_price=0.50,
            direction="BUY_YES",
        )
        assert result is None

    def test_check_missing_keys_returns_none_safely(self):
        from src.strategy.exit import tennis_score_exit
        # No sport_tag mismatch — missing keys should still be safe
        result = tennis_score_exit.check(
            score_info={"available": True},
            current_price=0.50,
            sport_tag="tennis",
            entry_price=0.50,
            direction="BUY_YES",
        )
        # Empty state → HOLD → None
        assert result is None
