"""Branş kartı isabet sub-line için pure derivation — Plan 1.D Task 4.

`computed.py` 400-satır limiti yaklaştığı için ayrı modül. Aynı katman
(presentation/dashboard), aynı tek-sorumluluk kuralı: dashboard JSON
payload için ham model_health.json blob'unu UI-friendly forma çevirir.

I/O YOK — dosya okuma `readers.read_model_health()` içinde.
"""
from __future__ import annotations

from typing import Any

# Branş kartı isabet alarm eşiği. accuracy < bu değer → kart kırmızı +
# (script tarafında) Telegram bildirim. config.yaml'a taşıma TODO.
_ACCURACY_ALARM_THRESHOLD = 0.55


def compute_sport_health_for_dashboard(
    health_blob: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """model_health.json blob → {sport: {accuracy, n_trades, alarm}}.

    Bozuk/eksik blob → {} (graceful). alarm = accuracy < eşik.
    """
    sports = (health_blob or {}).get("sports") or {}
    out: dict[str, dict[str, Any]] = {}
    for sport, stats in sports.items():
        if not isinstance(stats, dict) or "accuracy" not in stats:
            continue
        accuracy = float(stats.get("accuracy", 0.0))
        out[str(sport).lower()] = {
            "accuracy": round(accuracy, 4),
            "n_trades": int(stats.get("n_trades", 0)),
            "alarm": accuracy < _ACCURACY_ALARM_THRESHOLD,
        }
    return out
