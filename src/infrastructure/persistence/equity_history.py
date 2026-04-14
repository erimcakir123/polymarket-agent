"""Equity snapshot logger — her heavy cycle sonunda bankroll durumunu yazar.

Dashboard Total Equity grafiği bu dosyadan son N snapshot'ı okuyarak çizer.
Append-only JSONL; her satır bir EquitySnapshot.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.infrastructure.persistence.jsonl_tail import read_jsonl_tail

_BYTES_PER_LINE = 256


class EquitySnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: str           # ISO 8601 UTC
    bankroll: float          # Mevcut cash (realized dahil)
    realized_pnl: float      # Kümülatif gerçekleşmiş PnL
    unrealized_pnl: float    # Açık pozisyonların anlık PnL'i
    invested: float          # Açık pozisyonlara kilitli USDC
    open_positions: int      # Açık pozisyon sayısı


class EquityHistoryLogger:
    """Append-only JSONL writer/reader for equity snapshots."""

    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, snapshot: EquitySnapshot) -> None:
        line = snapshot.model_dump_json() + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_recent(self, n: int = 100) -> list[dict[str, Any]]:
        return read_jsonl_tail(self.path, n, _BYTES_PER_LINE)
