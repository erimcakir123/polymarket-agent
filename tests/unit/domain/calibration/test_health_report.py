"""compute_health — per-sport accuracy + Brier unit testleri."""
from __future__ import annotations

from src.domain.calibration.health_report import compute_health


def test_compute_health_groups_by_sport():
    trades = (
        [{"sport_tag": "nba", "anchor_probability": 0.7, "resolved_outcome": 1}] * 10
        + [{"sport_tag": "tennis", "anchor_probability": 0.8, "resolved_outcome": 1}] * 10
    )
    out = compute_health(trades)
    assert "nba" in out
    assert "tennis" in out
    assert out["nba"]["n_trades"] == 10
    assert out["tennis"]["n_trades"] == 10


def test_compute_health_skips_sports_below_minimum_samples():
    trades = [
        {"sport_tag": "nba", "anchor_probability": 0.7, "resolved_outcome": 1},
    ] * 5
    out = compute_health(trades)
    assert "nba" not in out


def test_compute_health_accuracy_correct():
    trades = [
        {"sport_tag": "nba", "anchor_probability": 0.7, "resolved_outcome": 1},
    ] * 10
    out = compute_health(trades)
    assert out["nba"]["accuracy"] == 1.0


def test_compute_health_brier_zero_for_perfect_predictions():
    trades = [
        {"sport_tag": "nba", "anchor_probability": 1.0, "resolved_outcome": 1},
    ] * 10
    out = compute_health(trades)
    assert abs(out["nba"]["brier"]) < 1e-9


def test_compute_health_skips_missing_fields():
    trades = (
        [{"sport_tag": "nba", "anchor_probability": 0.7, "resolved_outcome": 1}] * 10
        + [{"sport_tag": "nba", "anchor_probability": None, "resolved_outcome": 1}] * 5
        + [{"sport_tag": "nba", "anchor_probability": 0.5}] * 5  # missing outcome
    )
    out = compute_health(trades)
    assert out["nba"]["n_trades"] == 10
