"""NHL totals (over/under) exit decision tests — TDD."""
from __future__ import annotations

import pytest

from src.strategy.exit.nhl_totals_exit import (
    ExitAction,
    ExitReason,
    NHLTotalsExitConfig,
    NHLTotalsExitDecision,
    decide_nhl_totals_exit,
)


def _decide(**overrides):
    defaults = dict(
        cfg=NHLTotalsExitConfig(),
        entry_price=0.45,
        current_bid=0.50,
        current_price=0.52,
        scaled_out_50=False,
        period=3,
        seconds_remaining=600,
        current_total=4,
        target_total=5.5,
        side="over",
        p_over_fn=lambda p, c, s, t: (0.45, "empirical"),
    )
    defaults.update(overrides)
    return decide_nhl_totals_exit(**defaults)


class TestNearResolve:
    def test_bid_at_or_above_threshold_triggers_sell_all(self):
        d = _decide(current_bid=0.95)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.NEAR_RESOLVE
        assert d.p_side == 1.0
        assert d.p_source == "price"


class TestScaleOut:
    def test_bid_at_scale_threshold_not_yet_scaled_triggers_sell_50(self):
        d = _decide(current_bid=0.86, scaled_out_50=False)
        assert d.action == ExitAction.SELL_50
        assert d.reason == ExitReason.SCALE_OUT
        assert d.p_source == "price"


class TestPredictiveDeadOver:
    def test_p_over_below_bid_minus_margin_triggers_sell(self):
        # bid=0.60, margin=0.03 → trigger if p_over < 0.63
        d = _decide(
            current_bid=0.60,
            p_over_fn=lambda p, c, s, t: (0.50, "empirical"),
            side="over",
        )
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.PREDICTIVE_DEAD
        assert d.p_side == 0.50
        assert d.p_source == "empirical"

    def test_p_over_above_bid_plus_margin_no_trigger(self):
        # bid=0.50 → only triggers if p_over < 0.53; here 0.70 → HOLD
        d = _decide(
            current_bid=0.50,
            entry_price=0.50,
            current_price=0.52,
            p_over_fn=lambda p, c, s, t: (0.70, "empirical"),
            side="over",
        )
        assert d.action == ExitAction.HOLD


class TestPredictiveDeadUnder:
    def test_under_p_side_inverse_of_p_over_triggers(self):
        # side=under, p_over=0.80 → p_side=0.20, bid=0.50, margin=0.03 → 0.20 < 0.53 trigger
        d = _decide(
            current_bid=0.50,
            p_over_fn=lambda p, c, s, t: (0.80, "empirical"),
            side="under",
        )
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.PREDICTIVE_DEAD
        assert d.p_side == pytest.approx(0.20)
        assert d.p_source == "empirical"

    def test_under_with_low_p_over_no_trigger(self):
        # side=under, p_over=0.20 → p_side=0.80, bid=0.50 → 0.80 >= 0.53, no trigger
        d = _decide(
            current_bid=0.50,
            entry_price=0.50,
            current_price=0.52,
            p_over_fn=lambda p, c, s, t: (0.20, "empirical"),
            side="under",
        )
        assert d.action == ExitAction.HOLD


class TestStructuralDamage:
    def test_price_collapsed_below_ratio_triggers_sell(self):
        # entry=0.50, current=0.10 → ratio=0.20 < 0.30 trigger
        d = _decide(
            entry_price=0.50,
            current_price=0.10,
            current_bid=0.10,
            p_over_fn=lambda p, c, s, t: (0.90, "empirical"),  # avoid PREDICTIVE_DEAD
            side="over",
        )
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.STRUCTURAL_DAMAGE


class TestHold:
    def test_no_condition_met_holds(self):
        d = _decide(
            entry_price=0.50,
            current_price=0.52,
            current_bid=0.52,
            scaled_out_50=False,
            p_over_fn=lambda p, c, s, t: (0.70, "empirical"),
            side="over",
        )
        assert d.action == ExitAction.HOLD
        assert d.reason == ExitReason.HOLD


class TestEdgeCases:
    def test_p_over_fn_exception_skips_predictive_dead(self):
        def boom(p, c, s, t):
            raise RuntimeError("boom")

        d = _decide(
            current_bid=0.50,
            entry_price=0.50,
            current_price=0.52,
            p_over_fn=boom,
        )
        # exception → p_side None → PREDICTIVE_DEAD skip → HOLD
        assert d.action == ExitAction.HOLD
        assert d.p_side is None
        assert d.p_source == "error"

    def test_decision_is_frozen_immutable(self):
        d = _decide()
        with pytest.raises(Exception):
            d.action = ExitAction.SELL_ALL  # type: ignore[misc]

    def test_predictive_dead_skipped_when_source_not_empirical(self):
        """Skellam fallback NHL totals'da bid'e yakın çıkıp false trigger
        üretebilir. Empirical kalibrasyon yokken PREDICTIVE_DEAD kapalı."""
        d = _decide(
            current_bid=0.40,
            p_over_fn=lambda p, c, s, t: (0.10, "skellam_fallback"),
        )
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_predictive_dead_skipped_in_period_1(self):
        """NBA Q4-only paraleli: P1'de PREDICTIVE_DEAD pasif."""
        d = _decide(
            period=1,
            current_bid=0.40,
            p_over_fn=lambda p, c, s, t: (0.10, "empirical"),
        )
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_predictive_dead_skipped_in_period_2(self):
        """NBA Q4-only paraleli: P2'de PREDICTIVE_DEAD pasif."""
        d = _decide(
            period=2,
            current_bid=0.40,
            p_over_fn=lambda p, c, s, t: (0.10, "empirical"),
        )
        assert d.reason != ExitReason.PREDICTIVE_DEAD
