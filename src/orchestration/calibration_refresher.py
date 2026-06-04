"""Günlük kalibrasyon eğrisi update orchestrator (Plan 1.D Task 6).

Sackmann refresh paralel: bot başlangıçta stale check → stale ise
event log'dan fit_calibration → calibration_store'a yaz.

Stale: dosya son 24 saatten eski (2026-06-02: 7 gün → 1 gün, kullanıcı kararı).
Bozulma/yokluk → graceful skip + log.

SPEC-Z17 (2026-06-04): kaynak artık trade_events.jsonl event log; entry event'ler
calibration bucketing icin doğrudan kullanılır (sport_tag + anchor_probability +
market_type + resolved_outcome). market_type/resolved_outcome alanları gelecekte
event log'a eklenecek metadata — şu an placeholder.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from src.domain.calibration.curve import fit_calibration
from src.infrastructure.data.calibration_store import save_calibration

REFRESH_INTERVAL_DAYS = 1
_MIN_TRADES_PER_BUCKET = 30

logger = logging.getLogger(__name__)


def is_calibration_stale(path: Path) -> bool:
    """Calibration eğrisi son 7 günden eski mi?"""
    if not path.exists():
        return True
    age_days = (time.time() - path.stat().st_mtime) / 86400.0
    return age_days > REFRESH_INTERVAL_DAYS


def _read_trades(path: Path) -> list[dict]:
    """Trade event log JSONL'den ham entry event'leri oku — bozuk satırları atla.

    SPEC-Z17 sonrası tek truth = trade_events.jsonl. Calibration buckets entry
    event'ler üzerinde çalışır; sadece kind="entry" event'leri filtrelenir.
    """
    if not path.exists():
        return []
    trades: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Z17 event log → "entry" event'leri trade-record yerine geçer.
            # Eski raw record formatı (kind alanı yok) backwards-compat kabul edilir.
            kind = obj.get("kind")
            if kind in (None, "entry"):
                trades.append(obj)
    return trades


def _fit_curves_per_bucket(trades: list[dict]) -> dict:
    """{sport}:{market_type} grup başına fit_calibration."""
    buckets: dict[str, list[tuple[float, int]]] = {}
    for t in trades:
        sport = str(t.get("sport_tag", "")).lower()
        mt = str(t.get("market_type", "")).lower()
        p = t.get("anchor_probability")
        o = t.get("resolved_outcome")
        if sport and mt and p is not None and o is not None:
            buckets.setdefault(f"{sport}:{mt}", []).append((float(p), int(o)))
    curves = {}
    for key, samples in buckets.items():
        if len(samples) < _MIN_TRADES_PER_BUCKET:
            continue
        preds = [p for p, _ in samples]
        outs = [o for _, o in samples]
        curves[key] = fit_calibration(preds, outs)
    return curves


def refresh_calibration_if_stale(
    calibration_path: Path,
    trades_path: Path,
) -> bool:
    """Stale ise fit + save. Returns True if refresh ran."""
    if not is_calibration_stale(calibration_path):
        logger.info("calibration fresh — skip refresh")
        return False
    trades = _read_trades(trades_path)
    if not trades:
        logger.warning("calibration refresh: trade history empty/missing")
        return False
    curves = _fit_curves_per_bucket(trades)
    if not curves:
        logger.info(
            "calibration refresh: no bucket reached min %d trades",
            _MIN_TRADES_PER_BUCKET,
        )
        return False
    save_calibration(curves, calibration_path)
    logger.info(
        "calibration refresh: fit %d bucket(s) from %d trade(s)",
        len(curves), len(trades),
    )
    return True
