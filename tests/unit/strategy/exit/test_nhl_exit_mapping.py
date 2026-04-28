"""Unit tests for _nhl_exit_mapping — puck line decision → NHLSignal."""
from __future__ import annotations


class TestPuckLineMapping:
    def test_hold_returns_none(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_puck_line_decision
        from src.strategy.exit.nhl_puck_line_exit import (
            NHLPuckLineExitDecision, ExitAction, ExitReason,
        )
        d = NHLPuckLineExitDecision(
            action=ExitAction.HOLD, reason=ExitReason.HOLD,
            p_cover=0.5, p_cover_source="empirical", note="",
        )
        assert map_nhl_puck_line_decision(d) is None

    def test_near_resolve_maps_to_nhl_puck_line_reason(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_puck_line_decision
        from src.strategy.exit.nhl_puck_line_exit import (
            NHLPuckLineExitDecision, ExitAction, ExitReason,
        )
        from src.models.enums import ExitReason as GExitReason
        d = NHLPuckLineExitDecision(
            action=ExitAction.SELL_ALL, reason=ExitReason.NEAR_RESOLVE,
            p_cover=1.0, p_cover_source="price", note="bid=0.95",
        )
        sig = map_nhl_puck_line_decision(d)
        assert sig is not None
        assert sig.reason == GExitReason.NHL_PUCK_LINE_NEAR_RESOLVE
        assert sig.partial is False
        assert sig.sell_pct == 1.00

    def test_scale_out_partial_50(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_puck_line_decision
        from src.strategy.exit.nhl_puck_line_exit import (
            NHLPuckLineExitDecision, ExitAction, ExitReason,
        )
        d = NHLPuckLineExitDecision(
            action=ExitAction.SELL_50, reason=ExitReason.SCALE_OUT,
            p_cover=0.85, p_cover_source="price", note="bid=0.85",
        )
        sig = map_nhl_puck_line_decision(d)
        assert sig.partial is True
        assert sig.sell_pct == 0.50

    def test_predictive_dead_with_p_cover_in_detail(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_puck_line_decision
        from src.strategy.exit.nhl_puck_line_exit import (
            NHLPuckLineExitDecision, ExitAction, ExitReason,
        )
        from src.models.enums import ExitReason as GExitReason
        d = NHLPuckLineExitDecision(
            action=ExitAction.SELL_ALL, reason=ExitReason.PREDICTIVE_DEAD,
            p_cover=0.10, p_cover_source="empirical", note="p_cover=0.10",
        )
        sig = map_nhl_puck_line_decision(d)
        assert sig.reason == GExitReason.NHL_PUCK_LINE_PREDICTIVE_DEAD
        assert "p_cover=0.100" in sig.detail
        assert "empirical" in sig.detail


class TestTotalsMapping:
    def test_hold_returns_none(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_totals_decision
        from src.strategy.exit.nhl_totals_exit import (
            NHLTotalsExitDecision, ExitAction, ExitReason,
        )
        d = NHLTotalsExitDecision(
            action=ExitAction.HOLD, reason=ExitReason.HOLD,
            p_side=0.5, p_source="x", note="",
        )
        assert map_nhl_totals_decision(d) is None

    def test_predictive_dead_maps_to_nhl_totals_reason(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_totals_decision
        from src.strategy.exit.nhl_totals_exit import (
            NHLTotalsExitDecision, ExitAction, ExitReason,
        )
        from src.models.enums import ExitReason as GExitReason
        d = NHLTotalsExitDecision(
            action=ExitAction.SELL_ALL, reason=ExitReason.PREDICTIVE_DEAD,
            p_side=0.10, p_source="empirical", note="p_over=0.10",
        )
        sig = map_nhl_totals_decision(d)
        assert sig.reason == GExitReason.NHL_TOTALS_PREDICTIVE_DEAD
        assert sig.partial is False

    def test_scale_out_partial_50(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_totals_decision
        from src.strategy.exit.nhl_totals_exit import (
            NHLTotalsExitDecision, ExitAction, ExitReason,
        )
        d = NHLTotalsExitDecision(
            action=ExitAction.SELL_50, reason=ExitReason.SCALE_OUT,
            p_side=0.85, p_source="price", note="bid=0.85",
        )
        sig = map_nhl_totals_decision(d)
        assert sig.partial is True
        assert sig.sell_pct == 0.50
