"""Geriye uyumluluk shim — yeni location: src/domain/calibration/curve.py.

Plan 1.D refactor (2026-06-01): calibration spor-bağımsız hale getirildi.
Mevcut tennis import'ları bu shim üzerinden çalışmaya devam eder.
"""
from src.domain.calibration.curve import (
    CalibrationCurve,
    apply_calibration,
    fit_calibration,
    identity_curve,
)

__all__ = [
    "CalibrationCurve",
    "identity_curve",
    "fit_calibration",
    "apply_calibration",
]
