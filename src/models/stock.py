"""StockEntry domain modeli — StockQueue (orchestration) ve StockSnapshot (infrastructure) ortak kullanır."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.models.market import MarketData


def _parse_iso(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


@dataclass
class StockEntry:
    """Tek market için stock state. MarketData canlı tutulur — her refresh'te
    yeni fiyat + liquidity ile güncellenir.
    """
    market: MarketData
    first_seen_iso: str
    last_eval_iso: str
    last_skip_reason: str
    stale_attempts: int = 0

    @property
    def condition_id(self) -> str:
        return self.market.condition_id

    @property
    def match_start_dt(self) -> datetime | None:
        return _parse_iso(self.market.match_start_iso)
