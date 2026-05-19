"""Tennis diagnostic logger — per-trade feature snapshot."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.domain.prediction.feature_extractor import FeatureSnapshot
from src.domain.prediction.tennis_predictor import MarketPrediction
from src.orchestration.tennis_diagnostic_logger import TennisDiagnosticLogger


def _snap() -> FeatureSnapshot:
    return FeatureSnapshot(
        p1_name="Djere", p2_name="Cerundolo", surface="clay",
        p1_match_count_12mo=87, p1_surface_count=23,
        p1_form_w_pct_60d=0.55, p1_form_data_age_days=45,
        p2_match_count_12mo=42, p2_surface_count=9,
        p2_form_w_pct_60d=0.50, p2_form_data_age_days=67,
        h2h_matches_total=2, h2h_matches_same_surface=1,
        h2h_p1_wins=1, h2h_last_meeting_days_ago=380,
    )


def _pred() -> MarketPrediction:
    return MarketPrediction(
        market_type="first_set_winner",
        probability=0.62, raw_probability=0.60, notes="form_adj=+0.02",
    )


def test_log_creates_file_with_record(tmp_path):
    logger = TennisDiagnosticLogger(log_dir=tmp_path)
    logger.log_prediction(
        trade_id="abc-123",
        tournament="Geneva Open", tournament_tier="ATP 250",
        slug="atp-djere-cerund-2026", format_="BO3",
        match_start_iso="2026-05-20T17:45:00Z",
        market_polymarket_price=0.55, direction="BUY_YES",
        prediction=_pred(), features=_snap(),
        confidence_tier="A", edge=0.07,
    )
    # File created
    today = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = tmp_path / f"{today}.jsonl"
    assert log_file.exists()
    # Single record
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["trade_id"] == "abc-123"
    assert record["match"]["surface"] == "clay"
    assert record["market"]["type"] == "first_set_winner"
    assert record["prediction"]["model_prob"] == 0.62
    assert record["features"]["p1_match_count_12mo"] == 87
    assert record["features"]["h2h_p1_wins"] == 1
    assert record["outcome"] is None


def test_update_outcome(tmp_path):
    logger = TennisDiagnosticLogger(log_dir=tmp_path)
    logger.log_prediction(
        trade_id="abc-123", tournament="Test", tournament_tier="ATP 250",
        slug="atp-test-2026", format_="BO3",
        match_start_iso="2026-05-20T17:45:00Z",
        market_polymarket_price=0.55, direction="BUY_YES",
        prediction=_pred(), features=_snap(),
        confidence_tier="A", edge=0.07,
    )
    logger.update_outcome(trade_id="abc-123", outcome="WIN", exit_price=0.94, realized_pnl=4.50)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = tmp_path / f"{today}.jsonl"
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    # Append-style update: 2 lines
    assert len(lines) == 2
    update_record = json.loads(lines[1])
    assert update_record["trade_id"] == "abc-123"
    assert update_record["outcome"] == "WIN"
    assert update_record["exit_price"] == 0.94
    assert update_record["realized_pnl_usdc"] == 4.50
