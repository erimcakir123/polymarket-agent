"""Eligible queue snapshot — scanner'ın in-memory queue'sunu disk'e yazar.

Dashboard Stock tab'ı bu dosyayı okur. Her heavy cycle sonunda overwrite
edilir (append değil — anlık durum). Atomic write (temp + replace).

Scanner/orchestration bu modülü çağırır. Snapshot içeriği dashboard'un
ihtiyacı kadar projeksiyondur — MarketData tamamı değil.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.infrastructure.persistence.json_store import JsonStore


class EligibleQueueEntry(BaseModel):
    """Dashboard'un Stock kartı için gereken minimal alanlar."""
    model_config = ConfigDict(extra="ignore")

    slug: str
    sport_tag: str
    question: str = ""
    yes_price: float = 0.0
    no_price: float = 0.0
    liquidity: float = 0.0
    volume_24h: float = 0.0
    match_start_iso: str = ""


class EligibleQueueSnapshot:
    """Atomic JSON snapshot (JsonStore delegate) — anlık durum, append yok."""

    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self._store = JsonStore(self.path)

    def dump(self, entries: list[EligibleQueueEntry]) -> None:
        self._store.save([e.model_dump(mode="json") for e in entries])

    def load(self) -> list[dict[str, Any]]:
        raw = self._store.load([])
        return raw if isinstance(raw, list) else []
