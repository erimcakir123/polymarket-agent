"""Portfolio snapshot serialization — pure dict round-trip.

Dosya I/O orchestration/persistence katmanında. Bu modül sadece dict↔state
dönüşümü yapar.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.position import Position

if TYPE_CHECKING:
    from src.domain.portfolio.manager import PortfolioManager


def to_dict(mgr: "PortfolioManager") -> dict:
    """PortfolioManager state → JSON-serializable dict."""
    return {
        "realized_pnl": mgr.realized_pnl,
        "high_water_mark": mgr.high_water_mark,
        "positions": {cid: p.model_dump(mode="json") for cid, p in mgr.positions.items()},
    }


def from_dict(data: dict, initial_bankroll: float = 1000.0) -> "PortfolioManager":
    """Dict → PortfolioManager. recalculate_bankroll çağrılır (positions toplamı)."""
    from src.domain.portfolio.manager import PortfolioManager  # avoid cycle

    mgr = PortfolioManager(initial_bankroll=initial_bankroll)
    mgr.realized_pnl = data.get("realized_pnl", 0.0)
    for cid, pos_data in data.get("positions", {}).items():
        mgr.positions[cid] = Position(**pos_data)
    mgr.high_water_mark = data.get("high_water_mark", initial_bankroll)
    mgr.recalculate_bankroll(initial_bankroll)
    return mgr
