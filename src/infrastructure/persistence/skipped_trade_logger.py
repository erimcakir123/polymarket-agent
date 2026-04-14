"""Skipped trade logger — gate skip'lerini dashboard için persist eder.

ARCH_GUARD Kural 1: strategy/ infrastructure/ import edemez. Bu logger
orchestration katmanından (agent.py) çağrılır. Gate sadece SkipReason
döndürür; orchestration logger'a yazar.

Append-only JSONL; her satır bir SkippedTradeRecord.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.infrastructure.persistence.jsonl_tail import read_jsonl_tail

_BYTES_PER_LINE = 512


class SkippedTradeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: str           # ISO 8601 UTC
    slug: str
    sport_tag: str
    event_id: str = ""
    direction: str = ""      # BUY_YES / BUY_NO / "" (skip karar öncesi)
    entry_price: float = 0.0
    anchor_probability: float = 0.0
    confidence: str = ""
    skip_reason: str         # slot_full | exposure_cap | event_guard_duplicate | no_edge | low_liquidity | manipulation | cb_active | ...
    skip_detail: str = ""    # Opsiyonel ek not


class SkippedTradeLogger:
    """Append-only JSONL writer/reader for skip kayıtları."""

    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: SkippedTradeRecord) -> None:
        line = record.model_dump_json() + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_recent(self, n: int = 100) -> list[dict[str, Any]]:
        return read_jsonl_tail(self.path, n, _BYTES_PER_LINE)
