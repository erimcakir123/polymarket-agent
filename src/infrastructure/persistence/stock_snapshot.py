"""Stock snapshot — StockQueue'nun persistent durumunu disk'e yazar.

Her heavy cycle sonunda overwrite (append değil). Atomic write via JsonStore.
Restart'ta StockQueue.load() burayı okur; MarketData round-trip edilir.
Dashboard da Stock sekmesini bu dosyadan besleyebilir.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.infrastructure.persistence.json_store import JsonStore
from src.models.market import MarketData

if TYPE_CHECKING:
    from src.orchestration.stock_queue import StockEntry


class StockSnapshot:
    """Atomic JSON snapshot for StockQueue."""

    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self._store = JsonStore(self.path)

    def dump(self, entries: list[StockEntry]) -> None:
        payload = [
            {
                "first_seen_iso": e.first_seen_iso,
                "last_eval_iso": e.last_eval_iso,
                "last_skip_reason": e.last_skip_reason,
                "stale_attempts": e.stale_attempts,
                "market": e.market.model_dump(mode="json"),
            }
            for e in entries
        ]
        self._store.save(payload)

    def load(self) -> list[StockEntry]:
        from src.orchestration.stock_queue import StockEntry  # avoid cycle

        raw = self._store.load([])
        if not isinstance(raw, list):
            return []
        out: list[StockEntry] = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            market_raw = row.get("market")
            if not isinstance(market_raw, dict):
                continue
            try:
                market = MarketData(**market_raw)
            except (TypeError, ValueError):
                continue
            out.append(StockEntry(
                market=market,
                first_seen_iso=row.get("first_seen_iso", ""),
                last_eval_iso=row.get("last_eval_iso", ""),
                last_skip_reason=row.get("last_skip_reason", ""),
                stale_attempts=int(row.get("stale_attempts", 0) or 0),
            ))
        return out

    def load_raw(self) -> list[dict[str, Any]]:
        """Dashboard'un Stock tab'ı için raw JSON — MarketData parse etmeden."""
        raw = self._store.load([])
        return raw if isinstance(raw, list) else []
