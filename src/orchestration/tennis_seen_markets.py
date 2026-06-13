"""Loglardan görülen tenis marketlerini topla (hasat girdisi).

Append-only skip + trade loglarından tenis condition_id + question + timestamp
toplar, condition_id ile dedupe eder. ITF/Challenger dahil tam değerlendirme evreni.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_TENNIS_TAGS = frozenset({"tennis", "atp", "wta"})


def collect_seen_tennis_markets(
    log_paths: list[Path], since_yyyymmdd: str | None = None
) -> list[dict]:
    """[{condition_id, question, ts}] — tenis, condition_id ile dedupe.

    since_yyyymmdd verilirse ts'i bu tarihten eski kayıtlar elenir (backfill penceresi).
    """
    by_cid: dict[str, dict] = {}
    for path in log_paths:
        p = Path(path)
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (d.get("sport_tag") or "").lower() not in _TENNIS_TAGS:
                continue
            cid = d.get("condition_id")
            q = d.get("question")
            if not cid or not q:
                continue
            ts = d.get("timestamp") or d.get("entry_timestamp") or ""
            if since_yyyymmdd and ts:
                ts_ymd = ts[:10].replace("-", "")
                if ts_ymd and ts_ymd < since_yyyymmdd:
                    continue
            if cid not in by_cid:
                by_cid[cid] = {"condition_id": cid, "question": q, "ts": ts}
    return list(by_cid.values())
