"""Calibration curve — reliability bin + apply."""
from src.domain.pricing.tennis.calibration import (
    apply_calibration,
    fit_calibration,
    identity_curve,
)


def test_identity_curve_returns_input():
    curve = identity_curve()
    for p in (0.1, 0.5, 0.78, 0.95):
        assert abs(apply_calibration(p, curve) - p) < 1e-6


def test_fit_with_perfect_predictions_close_to_identity():
    # 100 predictions perfectly calibrated: 0.5 → half win
    preds = [0.5] * 100
    outcomes = [1] * 50 + [0] * 50
    curve = fit_calibration(preds, outcomes, n_bins=10)
    assert abs(apply_calibration(0.5, curve) - 0.5) < 0.05


def test_fit_with_overconfident_predictions():
    # bin 8 (0.80-0.90, mid 0.85) → predictions 0.85, observed 0.60
    preds = [0.85] * 100
    outcomes = [1] * 60 + [0] * 40
    curve = fit_calibration(preds, outcomes, n_bins=10)
    calibrated = apply_calibration(0.85, curve)
    assert 0.55 < calibrated < 0.65


def test_fit_with_underconfident_predictions():
    # bin 6 (0.60-0.70, mid 0.65) → predictions 0.65, observed 0.80
    preds = [0.65] * 100
    outcomes = [1] * 80 + [0] * 20
    curve = fit_calibration(preds, outcomes, n_bins=10)
    calibrated = apply_calibration(0.65, curve)
    assert 0.75 < calibrated < 0.85


def test_extreme_probability_clamped():
    curve = identity_curve()
    assert apply_calibration(-0.1, curve) >= 0.0
    assert apply_calibration(1.5, curve) <= 1.0


def test_empty_bin_falls_back_to_midpoint():
    # No data in bin (0.9-1.0) → returns bin midpoint (identity fallback)
    preds = [0.5] * 100
    outcomes = [1] * 50 + [0] * 50
    curve = fit_calibration(preds, outcomes, n_bins=10)
    # 0.95 → no observation → falls back to mid (0.95)
    assert abs(apply_calibration(0.95, curve) - 0.95) < 0.1
