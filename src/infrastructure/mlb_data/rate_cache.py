"""Rate cache (JSONL persistence) for batter/pitcher PA outcome rates.

SPEC-R Plan 3 T4. Append-only log; latest entry wins. Malformed lines skipped.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class RateCache:
    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        cache_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_lines(self) -> list[dict]:
        if not self.cache_path.exists():
            return []
        entries: list[dict] = []
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning("RateCache malformed line skipped: %s", e)
        return entries

    def get(self, mlbam_id: int, season: int, role: str) -> dict[str, float] | None:
        latest: dict[str, float] | None = None
        latest_ts: str = ""
        for entry in self._read_lines():
            if (entry.get("mlbam_id") == mlbam_id and
                    entry.get("season") == season and
                    entry.get("role") == role):
                ts = entry.get("ts", "")
                if ts >= latest_ts:
                    latest_ts = ts
                    latest = entry.get("rates")
        if latest is None:
            return None
        return dict(latest)  # copy

    def put(self, mlbam_id: int, season: int, role: str, rates: dict[str, float]) -> None:
        record = {
            "mlbam_id": mlbam_id,
            "season": season,
            "role": role,
            "rates": rates,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        with self.cache_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def clear_expired(self, max_age_days: int = 7) -> None:
        if not self.cache_path.exists():
            return
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        cutoff_iso = cutoff.isoformat()
        kept: list[dict] = []
        for entry in self._read_lines():
            ts = entry.get("ts", "")
            if ts >= cutoff_iso:
                kept.append(entry)
        with self.cache_path.open("w", encoding="utf-8") as f:
            for entry in kept:
                f.write(json.dumps(entry) + "\n")
