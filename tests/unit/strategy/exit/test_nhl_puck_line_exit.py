"""Tests for NHL puck line (-1.5) exit logic."""
from __future__ import annotations

import dataclasses

import pytest

from src.strategy.exit.nhl_puck_line_exit import (
    ExitAction,
    ExitReason,
    NHLPuckLineExitConfig,
    NHLPuckLineExitDecision,
    decide_nhl_puck_line_exit,
)


def _decide(**overrides):
    defaults = dict(
        cfg=NHLPuckLineExitConfig(),
        entry_price=0.45,
        current_bid=0.50,
        current_price=0.52,
        scaled_out_50=False,
        period=3,
        seconds_remaining=600,
        current_margin=1,
        p_cover_fn=lambda p, m, s: (0.55, "empirical"),
    )
    defaults.update(overrides)
    return decide_nhl_puck_line_exit(**defaults)


class TestNearResolve:
    def test_near_resolve_fires_at_threshold(self):
        d = _decide(current_bid=0.94)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.NEAR_RESOLVE
        assert d.p_cover == 1.0
        assert d.p_cover_source == "price"

    def test_near_resolve_does_not_fire_below_threshold(self):
        d = _decide(current_bid=0.93)
        assert d.reason != ExitReason.NEAR_RESOLVE


class TestScaleOut:
    def test_scale_out_fires_at_threshold_when_not_scaled(self):
        d = _decide(current_bid=0.85, scaled_out_50=False)
        assert d.action == ExitAction.SELL_50
        assert d.reason == ExitReason.SCALE_OUT
        assert d.p_cover == 0.85
        assert d.p_cover_source == "price"

    def test_scale_out_does_not_fire_when_already_scaled(self):
        d = _decide(current_bid=0.86, scaled_out_50=True)
        assert d.reason != ExitReason.SCALE_OUT


class TestPredictiveDead:
    def test_predictive_dead_fires_when_p_cover_low(self):
        # bid=0.50, p_cover=0.40, margin=0.03 → 0.40 < 0.53 → fires
        d = _decide(
            current_bid=0.50,
            p_cover_fn=lambda p, m, s: (0.40, "empirical"),
        )
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.PREDICTIVE_DEAD
        assert d.p_cover == 0.40
        assert d.p_cover_source == "empirical"

    def test_predictive_dead_no_fire_when_p_cover_high(self):
        # bid=0.50, p_cover=0.60 → 0.60 >= 0.53 → no fire
        d = _decide(
            current_bid=0.50,
            p_cover_fn=lambda p, m, s: (0.60, "empirical"),
        )
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_predictive_dead_skipped_when_fn_raises(self):
        def boom(p, m, s):
            raise RuntimeError("table miss")

        d = _decide(
            current_bid=0.50,
            p_cover_fn=boom,
        )
        # Should not fire PREDICTIVE_DEAD; falls through to HOLD (or STRUCTURAL_DAMAGE if applicable)
        assert d.reason != ExitReason.PREDICTIVE_DEAD
        assert d.p_cover is None
        assert d.p_cover_source == "error"


class TestStructuralDamage:
    def test_structural_damage_fires_when_ratio_below_threshold(self):
        # entry=0.50, current=0.10 → ratio=0.20 < 0.30 → fires
        d = _decide(
            entry_price=0.50,
            current_price=0.10,
            current_bid=0.10,  # avoid NEAR_RESOLVE/SCALE_OUT
            p_cover_fn=lambda p, m, s: (0.95, "empirical"),  # avoid PREDICTIVE_DEAD
        )
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.STRUCTURAL_DAMAGE

    def test_structural_damage_no_fire_when_ratio_above_threshold(self):
        # entry=0.50, current=0.40 → ratio=0.80 → no fire
        d = _decide(
            entry_price=0.50,
            current_price=0.40,
            current_bid=0.40,
            p_cover_fn=lambda p, m, s: (0.95, "empirical"),
        )
        assert d.reason != ExitReason.STRUCTURAL_DAMAGE


class TestHold:
    def test_hold_when_no_condition_fires(self):
        d = _decide(
            current_bid=0.50,
            current_price=0.52,
            entry_price=0.45,
            p_cover_fn=lambda p, m, s: (0.70, "empirical"),
        )
        assert d.action == ExitAction.HOLD
        assert d.reason == ExitReason.HOLD


class TestPriorityOrder:
    def test_near_resolve_beats_scale_out(self):
        d = _decide(current_bid=0.95, scaled_out_50=False)
        assert d.reason == ExitReason.NEAR_RESOLVE

    def test_scale_out_beats_predictive_dead(self):
        # bid=0.85 triggers SCALE_OUT; p_cover would also trigger PREDICTIVE_DEAD if reached
        d = _decide(
            current_bid=0.85,
            scaled_out_50=False,
            p_cover_fn=lambda p, m, s: (0.10, "empirical"),
        )
        assert d.reason == ExitReason.SCALE_OUT


class TestEdgeCases:
    def test_zero_entry_price_does_not_trigger_structural_damage(self):
        # entry_price=0 → division guard, must not fire STRUCTURAL_DAMAGE
        d = _decide(
            entry_price=0.0,
            current_price=0.01,
            current_bid=0.10,
            p_cover_fn=lambda p, m, s: (0.95, "empirical"),
        )
        assert d.reason != ExitReason.STRUCTURAL_DAMAGE

    def test_decision_is_frozen_immutable(self):
        d = _decide()
        with pytest.raises(dataclasses.FrozenInstanceError):
            d.action = ExitAction.SELL_ALL  # type: ignore[misc]
