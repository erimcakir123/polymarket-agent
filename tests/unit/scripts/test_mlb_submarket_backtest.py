"""Unit tests for mlb_submarket_backtest script.

SPEC-R Plan 4 T4. Smoke-tests evaluate_backtest_pick and summarize_backtest.
"""
from __future__ import annotations

import pytest
from scripts.mlb_submarket_backtest import (
    evaluate_backtest_pick,
    summarize_backtest,
)


def test_totals_model_picks_over_correctly() -> None:
    """Model thinks over is 62% likely; market at 55%. Actual = over. Model correct."""
    result = evaluate_backtest_pick(
        model_p=0.62, market_p=0.55,
        actual_outcome="over", market_type="totals",
    )
    assert result["model_pick"] == "over"
    assert result["correct"] is True
    assert abs(result["edge"] - 0.07) < 1e-9


def test_totals_model_picks_under_when_low_prob() -> None:
    """Model thinks over is 40%; market at 55%. Model picks UNDER (1-0.40 = 0.60 prob)."""
    result = evaluate_backtest_pick(
        model_p=0.40, market_p=0.55,
        actual_outcome="under", market_type="totals",
    )
    assert result["model_pick"] == "under"
    assert result["correct"] is True


def test_run_line_model_picks_home() -> None:
    result = evaluate_backtest_pick(
        model_p=0.60, market_p=0.50,
        actual_outcome="home_covers", market_type="run_line",
    )
    assert result["model_pick"] == "home_covers"
    assert result["correct"] is True


def test_run_line_model_picks_away_when_low_prob() -> None:
    result = evaluate_backtest_pick(
        model_p=0.30, market_p=0.50,
        actual_outcome="away_covers", market_type="run_line",
    )
    assert result["model_pick"] == "away_covers"
    assert result["correct"] is True


def test_model_wrong() -> None:
    result = evaluate_backtest_pick(
        model_p=0.62, market_p=0.55,
        actual_outcome="under", market_type="totals",
    )
    assert result["model_pick"] == "over"
    assert result["correct"] is False


def test_summarize_basic() -> None:
    picks = [
        {"correct": True, "edge": 0.07},
        {"correct": True, "edge": 0.06},
        {"correct": False, "edge": -0.08},
        {"correct": True, "edge": 0.10},
    ]
    summary = summarize_backtest(picks)
    assert summary["n_markets"] == 4
    assert summary["n_correct"] == 3
    assert abs(summary["accuracy"] - 0.75) < 1e-9
    # Mean edge = (0.07 + 0.06 + -0.08 + 0.10) / 4 = 0.0375
    assert abs(summary["mean_edge"] - 0.0375) < 1e-9


def test_summarize_empty_returns_zeros() -> None:
    summary = summarize_backtest([])
    assert summary["n_markets"] == 0
    assert summary["accuracy"] == 0.0


def test_summarize_high_edge_accuracy() -> None:
    """Picks with |edge| >= 0.07 should be tracked separately."""
    picks = [
        {"correct": True, "edge": 0.10},    # high edge
        {"correct": True, "edge": 0.08},    # high edge
        {"correct": False, "edge": -0.08},  # high edge
        {"correct": True, "edge": 0.05},    # low edge (excluded)
        {"correct": False, "edge": 0.04},   # low edge (excluded)
    ]
    summary = summarize_backtest(picks)
    # high-edge: 2/3 correct = 0.6667
    assert abs(summary["accuracy_high_edge"] - 2 / 3) < 1e-9
