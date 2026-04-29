"""Tests for NHL moneyline exit logic."""
from __future__ import annotations

import dataclasses

import pytest

from src.strategy.exit.nhl_score_exit import (
    ExitAction,
    ExitReason,
    NHLExitConfig,
    NHLExitDecision,
    decide_nhl_exit,
)


def _decide(**overrides):
    defaults = dict(
        cfg=NHLExitConfig(),
        entry_price=0.45,
        current_bid=0.50,
        current_price=0.52,
        scaled_out_50=False,
        period=3,
        seconds_remaining=600,
        abs_score_diff=1,
        we_are_leader=False,
        is_shootout=False,
        win_probability_fn=lambda p, v, s: (0.60, "default"),
    )
    defaults.update(overrides)
    return decide_nhl_exit(**defaults)


class TestNearResolve:
    def test_near_resolve_fires_at_threshold(self):
        d = _decide(current_bid=0.94)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.NEAR_RESOLVE

    def test_near_resolve_fires_above_threshold(self):
        d = _decide(current_bid=0.97)
        assert d.reason == ExitReason.NEAR_RESOLVE

    def test_near_resolve_does_not_fire_below_threshold(self):
        d = _decide(current_bid=0.93)
        assert d.reason != ExitReason.NEAR_RESOLVE

    def test_near_resolve_custom_threshold_fires_sell_all(self):
        cfg = NHLExitConfig(near_resolve_threshold=0.90)
        d = _decide(cfg=cfg, current_bid=0.91)
        assert d.reason == ExitReason.NEAR_RESOLVE

    def test_near_resolve_priority_beats_scale_out(self):
        d = _decide(current_bid=0.95, scaled_out_50=False)
        assert d.reason == ExitReason.NEAR_RESOLVE


class TestScaleOut:
    def test_scale_out_fires_at_threshold(self):
        d = _decide(current_bid=0.85, scaled_out_50=False)
        assert d.action == ExitAction.SELL_50
        assert d.reason == ExitReason.SCALE_OUT

    def test_scale_out_fires_above_threshold(self):
        d = _decide(current_bid=0.87, scaled_out_50=False)
        assert d.reason == ExitReason.SCALE_OUT

    def test_scale_out_skipped_if_already_scaled(self):
        d = _decide(current_bid=0.87, scaled_out_50=True)
        assert d.reason != ExitReason.SCALE_OUT

    def test_scale_out_does_not_fire_below_threshold(self):
        d = _decide(current_bid=0.84, scaled_out_50=False)
        assert d.reason != ExitReason.SCALE_OUT


class TestShootout:
    def test_shootout_profit_fires_when_favored(self):
        d = _decide(is_shootout=True, current_bid=0.54)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.SHOOTOUT_PROFIT

    def test_shootout_profit_does_not_fire_when_underdog(self):
        d = _decide(is_shootout=True, current_bid=0.48)
        assert d.reason != ExitReason.SHOOTOUT_PROFIT

    def test_shootout_profit_not_fired_outside_shootout(self):
        d = _decide(is_shootout=False, current_bid=0.55)
        assert d.reason != ExitReason.SHOOTOUT_PROFIT


class TestPredictiveDead:
    def test_predictive_dead_fires_when_p_win_low(self):
        d = _decide(
            win_probability_fn=lambda p, v, s: (0.12, "empirical"),
            current_bid=0.15,
        )
        assert d.reason == ExitReason.PREDICTIVE_DEAD
        assert d.p_win == pytest.approx(0.12)
        assert d.p_win_source == "empirical"

    def test_predictive_dead_skipped_when_source_not_empirical(self):
        """Skellam fallback NHL ML'i bid'e yakın tahmin edebilir → false trigger.
        Empirical kalibrasyon yokken PREDICTIVE_DEAD kapalı."""
        d = _decide(
            win_probability_fn=lambda p, v, s: (0.12, "skellam_fallback"),
            current_bid=0.15,
        )
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_predictive_dead_skipped_in_period_1(self):
        """NBA Q4-only paraleli: P1'de PREDICTIVE_DEAD pasif."""
        d = _decide(
            period=1,
            win_probability_fn=lambda p, v, s: (0.12, "empirical"),
            current_bid=0.15,
        )
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_predictive_dead_skipped_in_period_2(self):
        """NBA Q4-only paraleli: P2'de PREDICTIVE_DEAD pasif."""
        d = _decide(
            period=2,
            win_probability_fn=lambda p, v, s: (0.12, "empirical"),
            current_bid=0.15,
        )
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_predictive_dead_does_not_fire_when_p_win_high(self):
        d = _decide(
            win_probability_fn=lambda p, v, s: (0.40, "skellam"),
            current_bid=0.30,
        )
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_predictive_dead_boundary_is_exclusive(self):
        d = _decide(
            win_probability_fn=lambda p, v, s: (0.17, "skellam"),
            current_bid=0.14,
        )
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_predictive_dead_skipped_when_fn_raises(self):
        def _raising_fn(p, v, s):
            raise RuntimeError("ESPN down")

        d = _decide(win_probability_fn=_raising_fn)
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_predictive_dead_uses_bid_not_price(self):
        d = _decide(
            win_probability_fn=lambda p, v, s: (0.26, "sk"),
            current_bid=0.20,
            current_price=0.30,
        )
        assert d.reason != ExitReason.PREDICTIVE_DEAD


class TestStructuralDamage:
    def test_structural_damage_fires_when_price_collapsed(self):
        d = _decide(entry_price=0.60, current_price=0.10, current_bid=0.50)
        assert d.reason == ExitReason.STRUCTURAL_DAMAGE
        assert d.action == ExitAction.SELL_ALL

    def test_structural_damage_does_not_fire_above_ratio(self):
        d = _decide(entry_price=0.60, current_price=0.25, current_bid=0.50)
        assert d.reason != ExitReason.STRUCTURAL_DAMAGE

    def test_structural_damage_boundary_is_exclusive(self):
        d = _decide(entry_price=0.60, current_price=0.18, current_bid=0.50)
        assert d.reason != ExitReason.STRUCTURAL_DAMAGE

    def test_structural_damage_uses_price_not_bid(self):
        d = _decide(
            entry_price=0.45,
            current_price=0.20,
            current_bid=0.08,
        )
        assert d.reason != ExitReason.STRUCTURAL_DAMAGE


class TestPriorityOrder:
    def test_near_resolve_beats_scale_out(self):
        d = _decide(current_bid=0.95, scaled_out_50=False)
        assert d.reason == ExitReason.NEAR_RESOLVE

    def test_scale_out_beats_shootout(self):
        d = _decide(current_bid=0.87, scaled_out_50=False, is_shootout=True)
        assert d.reason == ExitReason.SCALE_OUT

    def test_shootout_beats_predictive_dead(self):
        d = _decide(
            win_probability_fn=lambda p, v, s: (0.10, "sk"),
            is_shootout=True,
            current_bid=0.55,
        )
        assert d.reason == ExitReason.SHOOTOUT_PROFIT

    def test_priority_structural_damage_over_hold_fires_sell_all(self):
        d = _decide(entry_price=0.60, current_price=0.10)
        assert d.reason != ExitReason.HOLD


class TestHold:
    def test_hold_when_no_conditions_met(self):
        d = _decide(
            win_probability_fn=lambda p, v, s: (0.60, "sk"),
            entry_price=0.50,
            current_bid=0.50,
            current_price=0.52,
        )
        assert d.reason == ExitReason.HOLD

    def test_hold_returns_correct_action(self):
        d = _decide()
        assert d.action == ExitAction.HOLD

    def test_hold_default_note_is_empty_string(self):
        d = _decide()
        assert d.note == ""


class TestEdgeCases:
    def test_entry_price_zero_does_not_crash(self):
        d = _decide(entry_price=0.0)
        assert d.reason == ExitReason.HOLD

    def test_frozen_decision_is_immutable(self):
        d = _decide()
        with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
            d.action = ExitAction.SELL_ALL

    def test_custom_config_thresholds(self):
        cfg = NHLExitConfig(near_resolve_threshold=0.90, scale_out_threshold=0.75)
        d_scale = _decide(cfg=cfg, current_bid=0.76)
        assert d_scale.reason == ExitReason.SCALE_OUT

        d_nr = _decide(cfg=cfg, current_bid=0.91)
        assert d_nr.reason == ExitReason.NEAR_RESOLVE

    def test_we_are_leader_does_not_affect_output(self):
        # we_are_leader is accepted but direction is handled by win_probability_fn closure
        d_trailing = _decide(we_are_leader=False)
        d_leading = _decide(we_are_leader=True)
        assert d_trailing.action == d_leading.action
        assert d_trailing.reason == d_leading.reason
