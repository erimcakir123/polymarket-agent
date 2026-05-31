"""Calibration curves persistence — per market_type calibration.

Atomic write, missing file → empty dict (Kural 12 — infra default safe).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.domain.pricing.tennis.calibration import CalibrationCurve

logger = logging.getLogger(__name__)


def save_calibration(curves: dict[str, CalibrationCurve], path: Path) -> None:
    payload = {
        market_type: {
            "n_bins": c.n_bins,
            "bin_midpoints": list(c.bin_midpoints),
            "bin_observed": list(c.bin_observed),
        }
        for market_type, c in curves.items()
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(target) + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(target)


def load_calibration(path: Path) -> dict[str, CalibrationCurve]:
    target = Path(path)
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("calibration store okunamadı: %s", exc)
        return {}
    out: dict[str, CalibrationCurve] = {}
    for market_type, payload in data.items():
        out[market_type] = CalibrationCurve(
            bin_midpoints=tuple(payload["bin_midpoints"]),
            bin_observed=tuple(payload["bin_observed"]),
            n_bins=int(payload["n_bins"]),
        )
    return out
