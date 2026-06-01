"""Calibration (model dogruluk karnesi) raporu — dashboard icin.

ARCH_GUARD §3 (computed.py 400 limit) icin ayri modul.
4-bin sezgisel kova: underdog / hafif / net / ezici favori.
Yetersiz veri (< 10) icin "pending" doner.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# Display order: heavy favorite at top, descending to underdog (high prob -> low prob).
_BINS: list[tuple[str, float, float, str]] = [
    ("ezici_favori", 0.80, 1.01, "Heavy favorite"),
    ("net_favori",   0.65, 0.80, "Clear favorite"),
    ("hafif_favori", 0.45, 0.65, "Slight favorite"),
    ("underdog",     0.30, 0.45, "Underdog call"),
]
_MIN_TRADES_PER_BIN = 10
_GREEN_DELTA = 0.05    # |predicted - actual| <= 5pp -> dogru
_YELLOW_DELTA = 0.12   # 5-12pp -> hafif sapma; > 12pp -> kirmizi
_CALIBRATION_PATH = Path("data/calibration_curves.json")


def _classify(delta: float) -> tuple[str, str]:
    abs_delta = abs(delta)
    direction = "iyimser" if delta > 0 else "temkinli"
    if abs_delta <= _GREEN_DELTA:
        return "green", "Dogru tahmin"
    if abs_delta <= _YELLOW_DELTA:
        return "yellow", f"{int(abs_delta*100)} puan {direction}"
    return "red", f"{int(abs_delta*100)} puan {direction} — buyuk sapma"


def calibration_report(trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Model dogruluk karnesi.

    Her bin icin: avg prediction, gercek win-rate, n, status (green/yellow/red).
    Bot perspektifi: tahmin = direction'a gore model_for_side.
    """
    last_updated_ts = (
        _CALIBRATION_PATH.stat().st_mtime if _CALIBRATION_PATH.exists() else None
    )

    bins: dict[str, list[tuple[float, int]]] = {b[0]: [] for b in _BINS}
    for t in trades:
        if t.get("exit_price") is None or t.get("exit_pnl_usdc") is None:
            continue
        anchor = t.get("anchor_probability")
        direction = t.get("direction", "")
        if anchor is None or not direction:
            continue
        try:
            anchor_f = float(anchor)
        except (TypeError, ValueError):
            continue
        prob_for_side = anchor_f if direction == "BUY_YES" else 1.0 - anchor_f
        outcome = 1 if float(t.get("exit_pnl_usdc") or 0.0) > 0 else 0
        for key, lo, hi, _ in _BINS:
            if lo <= prob_for_side < hi:
                bins[key].append((prob_for_side, outcome))
                break

    report = []
    total_trades = 0
    weighted_score = 0.0
    for key, lo, hi, label in _BINS:
        samples = bins[key]
        n = len(samples)
        if n < _MIN_TRADES_PER_BIN:
            report.append({
                "bin": key, "label": label,
                "range_pct": f"{int(lo*100)}-{int(hi*100)}",
                "n": n, "status": "pending",
                "predicted_pct": None, "actual_pct": None, "delta": None,
                "note": f"Henuz veri yok ({n}/{_MIN_TRADES_PER_BIN})",
            })
            continue
        predicted = sum(p for p, _ in samples) / n
        actual = sum(o for _, o in samples) / n
        delta = predicted - actual
        status, note = _classify(delta)
        report.append({
            "bin": key, "label": label,
            "range_pct": f"{int(lo*100)}-{int(hi*100)}",
            "n": n, "status": status,
            "predicted_pct": round(predicted * 100, 1),
            "actual_pct": round(actual * 100, 1),
            "delta": round(delta * 100, 1),
            "note": note,
        })
        total_trades += n
        weighted_score += (1.0 - abs(delta)) * n

    overall = (
        round((weighted_score / total_trades) * 100, 1) if total_trades else None
    )
    return {
        "bins": report,
        "total_trades": total_trades,
        "overall_score_pct": overall,
        "last_updated_ts": last_updated_ts,
        "min_trades_per_bin": _MIN_TRADES_PER_BIN,
    }
