"""Per-sport model isabet + Brier rapor mantığı — saf domain.

Trade history'den son N maç için accuracy + Brier hesabı.
I/O yok — trade listesi parametre olarak verilir.
Çağıran script (scripts/calibration_health_report.py) JSON I/O yapar.
"""
from __future__ import annotations

from typing import Iterable

_LOOKBACK_TRADES = 50
_MIN_SAMPLES_FOR_REPORT = 10


def compute_health(trades: Iterable[dict]) -> dict[str, dict]:
    """Trade listesinden per-sport accuracy + Brier.

    trade dict'inin beklediği alanlar:
      - sport_tag: str (örn 'nba', 'tennis')
      - anchor_probability: float (model_p kayıt edilmiş)
      - resolved_outcome: int (1=YES kazandı, 0=NO)

    Çıktı: {sport: {accuracy, brier, n_trades}}.
    Minimum threshold altındaki sporlar atlanır.
    """
    by_sport: dict[str, list[tuple[float, int]]] = {}
    for t in trades:
        sport = str(t.get("sport_tag", "")).lower()
        model_p = t.get("anchor_probability")
        outcome = t.get("resolved_outcome")
        if sport and model_p is not None and outcome is not None:
            by_sport.setdefault(sport, []).append((float(model_p), int(outcome)))
    out: dict[str, dict] = {}
    for sport, samples in by_sport.items():
        if len(samples) < _MIN_SAMPLES_FOR_REPORT:
            continue
        last = samples[-_LOOKBACK_TRADES:]
        correct = sum(1 for p, o in last if (p > 0.5) == (o == 1))
        brier = sum((p - o) ** 2 for p, o in last) / len(last)
        out[sport] = {
            "accuracy": correct / len(last),
            "brier": brier,
            "n_trades": len(last),
        }
    return out
