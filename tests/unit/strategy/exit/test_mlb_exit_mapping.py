"""Unit tests for _mlb_exit_mapping.py — MLBSignal mapping."""
import pytest

from src.models.enums import ExitReason
from src.strategy.exit._mlb_exit_mapping import (
    MLBSignal,
    map_mlb_decision,
    map_mlb_run_line_decision,
    map_mlb_totals_decision,
)
from src.strategy.exit.mlb_score_exit import (
    ExitAction,
    ExitReason as MLBR,
    MLBExitDecision,
)
from src.strategy.exit.mlb_run_line_exit import (
    ExitAction as RLA,
    ExitReason as RLR,
    MLBRunLineExitDecision,
)
from src.strategy.exit.mlb_totals_exit import (
    ExitAction as TA,
    ExitReason as TR,
    MLBTotalsExitDecision,
)


def test_hold_returns_none():
    d = MLBExitDecision(ExitAction.HOLD, MLBR.HOLD, None, "", "")
    assert map_mlb_decision(d) is None


def test_sell_all_maps_to_signal():
    d = MLBExitDecision(ExitAction.SELL_ALL, MLBR.NEAR_RESOLVE, 0.99, "price", "bid=0.99")
    sig = map_mlb_decision(d)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_NEAR_RESOLVE
    assert sig.partial is False
    assert sig.sell_pct == 1.00


def test_sell_50_maps_to_partial():
    d = MLBExitDecision(ExitAction.SELL_50, MLBR.SCALE_OUT, 0.86, "price", "bid=0.86")
    sig = map_mlb_decision(d)
    assert sig is not None
    assert sig.partial is True
    assert sig.sell_pct == 0.50


def test_m1_reason_maps_correctly():
    d = MLBExitDecision(ExitAction.SELL_ALL, MLBR.M1_SEVENTH_DEFICIT_5, None, "rule", "inning=7")
    sig = map_mlb_decision(d)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_M1_SEVENTH_DEFICIT_5


def test_m2_reason_maps_correctly():
    d = MLBExitDecision(ExitAction.SELL_ALL, MLBR.M2_EIGHTH_DEFICIT_3, None, "rule", "inning=8")
    sig = map_mlb_decision(d)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_M2_EIGHTH_DEFICIT_3


def test_m3_reason_maps_correctly():
    d = MLBExitDecision(ExitAction.SELL_ALL, MLBR.M3_NINTH_DEFICIT_1, None, "rule", "inning=9")
    sig = map_mlb_decision(d)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_M3_NINTH_DEFICIT_1


def test_detail_includes_p_win():
    d = MLBExitDecision(ExitAction.SELL_ALL, MLBR.PREDICTIVE_DEAD, 0.123, "table", "p=0.123")
    sig = map_mlb_decision(d)
    assert sig is not None
    assert "p_win=0.123" in sig.detail
    assert "(table)" in sig.detail


def test_run_line_hold_returns_none():
    d = MLBRunLineExitDecision(RLA.HOLD, RLR.HOLD, None, "", "")
    assert map_mlb_run_line_decision(d) is None


def test_run_line_mapping():
    d = MLBRunLineExitDecision(RLA.SELL_ALL, RLR.M1_SEVENTH_DEFICIT_5, None, "rule", "")
    sig = map_mlb_run_line_decision(d)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_M1_SEVENTH_DEFICIT_5


def test_run_line_near_resolve_maps():
    d = MLBRunLineExitDecision(RLA.SELL_ALL, RLR.NEAR_RESOLVE, 1.0, "price", "bid=0.96")
    sig = map_mlb_run_line_decision(d)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_RUN_LINE_NEAR_RESOLVE
    assert sig.partial is False


def test_run_line_predictive_dead_maps():
    d = MLBRunLineExitDecision(RLA.SELL_ALL, RLR.PREDICTIVE_DEAD, 0.05, "table", "p=0.05")
    sig = map_mlb_run_line_decision(d)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_RUN_LINE_PREDICTIVE_DEAD
    assert "p_cover=0.050" in sig.detail


def test_totals_mapping():
    d = MLBTotalsExitDecision(TA.SELL_ALL, TR.PREDICTIVE_DEAD, 0.05, "table", "p=0.05")
    sig = map_mlb_totals_decision(d)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_TOTALS_PREDICTIVE_DEAD


def test_totals_hold_returns_none():
    d = MLBTotalsExitDecision(TA.HOLD, TR.HOLD, None, "", "")
    assert map_mlb_totals_decision(d) is None


def test_totals_near_resolve_maps():
    d = MLBTotalsExitDecision(TA.SELL_ALL, TR.NEAR_RESOLVE, 1.0, "price", "bid=0.96")
    sig = map_mlb_totals_decision(d)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_TOTALS_NEAR_RESOLVE


def test_totals_detail_includes_p_over():
    d = MLBTotalsExitDecision(TA.SELL_ALL, TR.STRUCTURAL_DAMAGE, 0.88, "table", "ratio=0.25")
    sig = map_mlb_totals_decision(d)
    assert sig is not None
    assert "p_over=0.880" in sig.detail
    assert "(table)" in sig.detail
