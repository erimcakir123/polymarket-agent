"""Calibration store — JSON round-trip + missing file."""
from src.domain.pricing.tennis.calibration import CalibrationCurve
from src.infrastructure.data.calibration_store import (
    load_calibration,
    save_calibration,
)


def test_round_trip(tmp_path):
    curve = CalibrationCurve(
        bin_midpoints=(0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95),
        bin_observed=(0.04, 0.13, 0.28, 0.32, 0.50, 0.58, 0.69, 0.78, 0.81, 0.92),
        n_bins=10,
    )
    path = tmp_path / "calib.json"
    save_calibration({"moneyline": curve}, path)
    loaded = load_calibration(path)
    assert "moneyline" in loaded
    assert loaded["moneyline"].n_bins == 10
    assert abs(loaded["moneyline"].bin_observed[5] - 0.58) < 1e-6


def test_load_missing_returns_empty(tmp_path):
    assert load_calibration(tmp_path / "nope.json") == {}
