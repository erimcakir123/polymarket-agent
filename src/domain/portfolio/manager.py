"""Portfolio state manager — pure, no I/O.

Pozisyon ekleme/silme, bankroll, realized PnL izleme, event-level duplicate guard
(ARCH Kural 8). Persistence orkestrasyonda (JsonStore kullanılır).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.models.position import Position

logger = logging.getLogger(__name__)


@dataclass
class PortfolioManager:
    """Mevcut pozisyonlar + bankroll + realized PnL. I/O YOK."""
    initial_bankroll: float = 1000.0
    bankroll: float = field(init=False)
    realized_pnl: float = 0.0
    high_water_mark: float = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.bankroll = self.initial_bankroll
        self.high_water_mark = self.initial_bankroll

    # ── Snapshot I/O (to/from dict; gerçek dosya orkestrasyonda) ──

    def to_snapshot(self) -> dict:
        """State snapshot — JsonStore ile persist edilmek üzere."""
        return {
            "realized_pnl": self.realized_pnl,
            "high_water_mark": self.high_water_mark,
            "positions": {cid: p.model_dump(mode="json") for cid, p in self.positions.items()},
        }

    @classmethod
    def from_snapshot(cls, data: dict, initial_bankroll: float = 1000.0) -> "PortfolioManager":
        mgr = cls(initial_bankroll=initial_bankroll)
        mgr.realized_pnl = data.get("realized_pnl", 0.0)
        for cid, pos_data in data.get("positions", {}).items():
            mgr.positions[cid] = Position(**pos_data)
        mgr.high_water_mark = data.get("high_water_mark", initial_bankroll)
        mgr.recalculate_bankroll(initial_bankroll)
        return mgr

    def recalculate_bankroll(self, initial_bankroll: float) -> None:
        """Bankroll'u baştan türet: initial + realized − açık pozisyonların toplam size'ı.

        Crash recovery sonrası state düzeltmeleri için kullanılır.
        """
        invested = sum(p.size_usdc for p in self.positions.values())
        self.bankroll = self.compute_bankroll(initial_bankroll, self.realized_pnl, invested)
        self.high_water_mark = max(self.high_water_mark, self.bankroll)

    @staticmethod
    def compute_bankroll(initial_bankroll: float, realized_pnl: float,
                         total_invested: float) -> float:
        """Bankroll formülü — tek yerde tutulur (DRY).

        bankroll = initial + realized − açık pozisyon size'larının toplamı.
        Hem PortfolioManager.recalculate_bankroll hem presentation katmanları kullanır.
        """
        return initial_bankroll + realized_pnl - total_invested

    # ── Event-level guard (ARCH Kural 8) ──

    def has_event(self, event_id: str) -> bool:
        """Aynı event_id'ye sahip bir pozisyon var mı?"""
        if not event_id:
            return False
        return any(p.event_id == event_id for p in self.positions.values())

    # ── Mutations ──

    def add_position(self, pos: Position) -> bool:
        """Pozisyon ekle. Event/condition duplicate'te False döner (ARCH Kural 8)."""
        if pos.event_id and self.has_event(pos.event_id):
            logger.warning(
                "BLOCKED: same event already held — existing %s, attempted %s, event_id=%s",
                next((p.slug[:35] for p in self.positions.values() if p.event_id == pos.event_id), "?"),
                pos.slug[:35], pos.event_id,
            )
            return False
        if pos.condition_id in self.positions:
            logger.warning("BLOCKED duplicate add_position: %s already held", pos.slug[:35])
            return False
        self.positions[pos.condition_id] = pos
        self.bankroll -= pos.size_usdc
        return True

    def remove_position(self, condition_id: str, realized_pnl_usdc: float = 0.0) -> Position | None:
        """Pozisyon kapat. Realized PnL güncelle, bankroll geri bırak."""
        pos = self.positions.pop(condition_id, None)
        if pos is None:
            return None
        self.bankroll += pos.size_usdc + realized_pnl_usdc
        self.realized_pnl += realized_pnl_usdc
        self.high_water_mark = max(self.high_water_mark, self.bankroll)
        return pos

    def apply_partial_exit(self, condition_id: str, realized_usdc: float) -> None:
        """Scale-out: partial exit realize et (bankroll güncellenir, pozisyon silinmez)."""
        if condition_id not in self.positions:
            return
        self.bankroll += realized_usdc
        self.realized_pnl += realized_usdc

    # ── Queries ──

    def count(self) -> int:
        return len(self.positions)

    def total_invested(self) -> float:
        return sum(p.size_usdc for p in self.positions.values())

    def get(self, condition_id: str) -> Position | None:
        return self.positions.get(condition_id)

    # ── WS price update (her tick) + cycle state tick (her light cycle) ──

    def update_position_price(self, token_id: str, yes_price: float, bid_price: float) -> bool:
        """WS tick ile token fiyatı güncelle. Returns True → pozisyon bulundu & güncellendi.

        SADECE anlık fiyat (current_price, bid_price). Peak/momentum/ever_in_profit
        state'i cycle-bazlı → `tick_position_state` ile güncellenir.
        """
        if not token_id or yes_price <= 0:
            return False
        for pos in self.positions.values():
            if pos.token_id == token_id:
                pos.current_price = yes_price
                pos.bid_price = bid_price
                return True
        return False

    def tick_position_state(self, condition_id: str) -> None:
        """Her light cycle'da pozisyon için cycle-bazlı state güncelle.

        Günceller: peak_pnl_pct, peak_price, ever_in_profit,
        consecutive_down_cycles, cumulative_drop, previous_cycle_price, cycles_held.
        """
        pos = self.positions.get(condition_id)
        if pos is None:
            return

        pnl_pct = pos.unrealized_pnl_pct
        if pnl_pct > pos.peak_pnl_pct:
            pos.peak_pnl_pct = pnl_pct
            pos.peak_price = pos.current_price
        if pnl_pct > 0.01 and not pos.ever_in_profit:
            pos.ever_in_profit = True

        # Momentum tracking (graduated SL için)
        prev = pos.previous_cycle_price or pos.entry_price
        if pos.current_price < prev:
            pos.consecutive_down_cycles += 1
            pos.cumulative_drop += (prev - pos.current_price)
        else:
            pos.consecutive_down_cycles = 0
            pos.cumulative_drop = 0.0

        pos.previous_cycle_price = pos.current_price
        pos.cycles_held += 1
