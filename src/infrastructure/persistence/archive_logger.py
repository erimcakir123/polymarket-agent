"""Retrospective rule analysis arsivi (SPEC-009) — append-only JSONL.

3 ayri dosya:
  - exits.jsonl        — her exit'in tam snapshot'i + skor
  - score_events.jsonl — mac icindeki her skor degisikligi
  - match_results.jsonl — mac final result

Reboot/reload DOKUNMAZ: bu dosyalar sifirlanmaz.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ArchiveExitRecord(BaseModel):
    """Bir exit anindaki tam snapshot — trade detayi + skor."""
    model_config = ConfigDict(extra="ignore")

    # Trade kimligi
    slug: str
    condition_id: str
    event_id: str
    token_id: str
    sport_tag: str
    question: str

    # Entry
    direction: str
    entry_price: float
    entry_timestamp: str
    size_usdc: float
    shares: float
    confidence: str
    anchor_probability: float
    entry_reason: str

    # Exit
    exit_price: float
    exit_pnl_usdc: float
    exit_reason: str
    exit_timestamp: str
    partial_exits: list[dict] = []

    # Skor snapshot (exit aninda)
    score_at_exit: str = ""
    period_at_exit: str = ""
    elapsed_pct_at_exit: float = -1.0


class ArchiveScoreEvent(BaseModel):
    """Bir mac icindeki tek bir skor degisikligi."""
    model_config = ConfigDict(extra="ignore")

    event_id: str
    slug: str
    sport_tag: str
    timestamp: str
    prev_score: str
    new_score: str
    period: str = ""


class ArchiveMatchResult(BaseModel):
    """Mac final result — mac tamamlandiginda yazilir."""
    model_config = ConfigDict(extra="ignore")

    event_id: str
    slug: str
    sport_tag: str
    final_score: str
    winner_home: bool | None
    completed_timestamp: str
    source: str = "espn"


class ArchiveLogger:
    """3 ayri append-only JSONL'e yazar. Retrospektif analiz icin."""

    _EXITS_FILE = "exits.jsonl"
    _SCORE_EVENTS_FILE = "score_events.jsonl"
    _MATCH_RESULTS_FILE = "match_results.jsonl"

    def __init__(self, archive_dir: str) -> None:
        self.dir = Path(archive_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def log_exit(self, record: ArchiveExitRecord) -> None:
        self._append(self._EXITS_FILE, record)

    def log_score_event(self, event: ArchiveScoreEvent) -> None:
        self._append(self._SCORE_EVENTS_FILE, event)

    def log_match_result(self, result: ArchiveMatchResult) -> None:
        self._append(self._MATCH_RESULTS_FILE, result)

    def load_logged_match_event_ids(self) -> set[str]:
        """Startup'ta cagrilir — daha once yazilmis match_result'larin
        event_id set'ini dondur. Duplicate yazim engellemesi icin."""
        path = self.dir / self._MATCH_RESULTS_FILE
        if not path.exists():
            return set()
        ids: set[str] = set()
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event_id = data.get("event_id", "")
                    if event_id:
                        ids.add(event_id)
                except json.JSONDecodeError:
                    continue
        return ids

    def _append(self, filename: str, record: BaseModel) -> None:
        with open(self.dir / filename, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
