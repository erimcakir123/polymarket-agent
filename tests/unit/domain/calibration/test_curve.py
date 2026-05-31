"""Generic calibration curve — sport-agnostic."""
from __future__ import annotations

from src.domain.calibration.curve import (
    CalibrationCurve,
    apply_calibration,
    fit_calibration,
    identity_curve,
)


def test_identity_curve_returns_input():
    c = identity_curve(n_bins=10)
    assert abs(apply_calibration(0.5, c) - 0.5) < 0.05


def test_fit_calibration_overconfident_model_pulled_down():
    """Model %70 dediğinde gerçekte %60 → eğri %70'i %60'a yaklaştırmalı."""
    preds = [0.7] * 100
    outs = [1] * 60 + [0] * 40
    c = fit_calibration(preds, outs, n_bins=10)
    calibrated = apply_calibration(0.7, c)
    assert calibrated < 0.7
    assert calibrated > 0.5  # %60 civarı


def test_fit_calibration_empty_bins_fallback_to_midpoint():
    """Veri olmayan bin → identity."""
    preds = [0.5]
    outs = [1]
    c = fit_calibration(preds, outs, n_bins=10)
    # 0.9 binine veri yok → 0.9 dön
    p = apply_calibration(0.95, c)
    assert 0.8 < p < 1.0


def test_apply_calibration_clamps_input():
    c = identity_curve(n_bins=10)
    # 1.5 → 1.0 clamp → eğrinin son midpoint'i
    assert apply_calibration(1.5, c) <= 1.0
    assert apply_calibration(-0.5, c) >= 0.0
