"""Calibration curve — bin-based reliability + apply (spor-bağımsız).

Pure domain. Reliability diagram methodology:
- Tahminleri n_bins'e ayır (örn 10 bin → [0,0.1), [0.1,0.2), ...)
- Her bin için gözlemlenen frekansı hesapla
- Apply: tahmin bin midpoint → observed frequency linear interpolation

Boş bin → identity fallback (data noksanı).

Plan 1.D: tenis için yazılmıştı, basket de aynı altyapıyı kullanır.
"""
from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_BINS = 10


@dataclass(frozen=True)
class CalibrationCurve:
    """Reliability bins: each bin maps a midpoint prediction to observed freq."""
    bin_midpoints: tuple[float, ...]
    bin_observed: tuple[float, ...]
    n_bins: int


def identity_curve(n_bins: int = _DEFAULT_BINS) -> CalibrationCurve:
    """No-op calibration: observed = predicted at each bin midpoint."""
    edges = [i / n_bins for i in range(n_bins + 1)]
    mids = tuple((edges[i] + edges[i + 1]) / 2 for i in range(n_bins))
    return CalibrationCurve(bin_midpoints=mids, bin_observed=mids, n_bins=n_bins)


def fit_calibration(
    predictions: list[float],
    outcomes: list[int],
    n_bins: int = _DEFAULT_BINS,
) -> CalibrationCurve:
    """Fit reliability curve. Empty bins fall back to bin midpoint."""
    edges = [i / n_bins for i in range(n_bins + 1)]
    mids = tuple((edges[i] + edges[i + 1]) / 2 for i in range(n_bins))
    sums = [0.0] * n_bins
    counts = [0] * n_bins
    for p, o in zip(predictions, outcomes):
        idx = min(int(p * n_bins), n_bins - 1)
        sums[idx] += o
        counts[idx] += 1
    observed = tuple(
        sums[i] / counts[i] if counts[i] > 0 else mids[i]
        for i in range(n_bins)
    )
    return CalibrationCurve(bin_midpoints=mids, bin_observed=observed, n_bins=n_bins)


def apply_calibration(raw_prob: float, curve: CalibrationCurve) -> float:
    """Linear interpolation between bin midpoints. Clamp to [0,1]."""
    p = max(0.0, min(1.0, raw_prob))
    mids = curve.bin_midpoints
    obs = curve.bin_observed
    if p <= mids[0]:
        return obs[0]
    if p >= mids[-1]:
        return obs[-1]
    for i in range(len(mids) - 1):
        if mids[i] <= p <= mids[i + 1]:
            t = (p - mids[i]) / (mids[i + 1] - mids[i])
            return obs[i] + t * (obs[i + 1] - obs[i])
    return p
