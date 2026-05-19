"""Diagnose CLI — group-by surface/tier/feature analysis."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from scripts.diagnose import (
    DiagnosticRecord,
    group_by_feature,
    group_by_surface,
    group_by_tier,
    load_diagnostic_records,
)


@pytest.fixture
def diag_dir(tmp_path):
    d = tmp_path / "diag"
    d.mkdir()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    # 4 trades: 2 wins, 2 losses; mixed surface + tier
    records = [
        {
            "trade_id": "t1", "timestamp": "2026-05-19T10:00:00Z",
            "match": {"surface": "clay", "tournament_tier": "ATP 250"},
            "market": {"type": "first_set_winner"},
            "prediction": {"model_prob": 0.62, "edge": 0.07, "confidence_tier": "A"},
            "features": {"p1_form_data_age_days": 45, "h2h_matches_total": 2},
            "outcome": None,
        },
        {"trade_id": "t1", "outcome": "WIN", "realized_pnl_usdc": 5.0},
        {
            "trade_id": "t2", "timestamp": "2026-05-19T11:00:00Z",
            "match": {"surface": "clay", "tournament_tier": "ATP 1000"},
            "market": {"type": "set_handicap"},
            "prediction": {"model_prob": 0.40, "edge": -0.08, "confidence_tier": "A"},
            "features": {"p1_form_data_age_days": 80, "h2h_matches_total": 0},
            "outcome": None,
        },
        {"trade_id": "t2", "outcome": "LOSS", "realized_pnl_usdc": -10.0},
        {
            "trade_id": "t3", "timestamp": "2026-05-19T12:00:00Z",
            "match": {"surface": "hard", "tournament_tier": "ATP 500"},
            "market": {"type": "first_set_winner"},
            "prediction": {"model_prob": 0.70, "edge": 0.10, "confidence_tier": "B"},
            "features": {"p1_form_data_age_days": 50, "h2h_matches_total": 1},
            "outcome": None,
        },
        {"trade_id": "t3", "outcome": "WIN", "realized_pnl_usdc": 8.0},
        {
            "trade_id": "t4", "timestamp": "2026-05-19T13:00:00Z",
            "match": {"surface": "hard", "tournament_tier": "ATP 250"},
            "market": {"type": "total_sets"},
            "prediction": {"model_prob": 0.55, "edge": 0.05, "confidence_tier": "B"},
            "features": {"p1_form_data_age_days": 70, "h2h_matches_total": 0},
            "outcome": None,
        },
        {"trade_id": "t4", "outcome": "LOSS", "realized_pnl_usdc": -5.0},
    ]
    log_file = d / f"{today}.jsonl"
    with open(log_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return d


def test_load_records_merges_prediction_and_outcome(diag_dir):
    recs = load_diagnostic_records(diag_dir, days=7)
    assert len(recs) == 4
    by_id = {r.trade_id: r for r in recs}
    assert by_id["t1"].outcome == "WIN"
    assert by_id["t2"].outcome == "LOSS"


def test_group_by_surface(diag_dir):
    recs = load_diagnostic_records(diag_dir, days=7)
    groups = group_by_surface(recs)
    assert "clay" in groups
    assert "hard" in groups
    assert groups["clay"]["wins"] == 1
    assert groups["clay"]["losses"] == 1
    assert groups["clay"]["net_pnl"] == -5.0


def test_group_by_tier(diag_dir):
    recs = load_diagnostic_records(diag_dir, days=7)
    groups = group_by_tier(recs)
    assert groups["A"]["wins"] == 1
    assert groups["A"]["losses"] == 1
    assert groups["B"]["wins"] == 1
    assert groups["B"]["losses"] == 1


def test_group_by_feature_h2h_zero(diag_dir):
    recs = load_diagnostic_records(diag_dir, days=7)
    groups = group_by_feature(recs)
    # h2h_matches_total=0 → 2 trades (t2 LOSS, t4 LOSS)
    assert groups["h2h_matches_total=0"]["losses"] == 2
    assert groups["h2h_matches_total=0"]["wins"] == 0
