"""Portfolio state manager — pure, no I/O.

Pozisyon ekleme/silme, bankroll, realized PnL izleme, event-level duplicate guard
(ARCH Kural 8). Persistence orkestrasyonda (JsonStore kullanılır).

Snapshot serialization → `domain/portfolio/snapshot.py` (free functions).
Bankroll formülü → `domain/portfolio/bankroll.py`.
Position cycle-state tick → `domain/portfolio/lifecycle.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.portfolio.bankroll import compute_bankroll
from src.models.position import Position


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

    def recalculate_bankroll(self, initial_bankroll: float) -> None:
        """Bankroll'u baştan türet: initial + realized − açık pozisyonların toplam size'ı.

        Crash recovery sonrası state düzeltmeleri için kullanılır.
        """
        invested = sum(p.size_usdc for p in self.positions.values())
        self.bankroll = compute_bankroll(initial_bankroll, self.realized_pnl, invested)
        self.high_water_mark = max(self.high_water_mark, self.bankroll)

    # ── Event-level guard (ARCH Kural 8) ──

    def has_event(self, event_id: str) -> bool:
        """Aynı event_id'ye sahip bir pozisyon var mı?"""
        if not event_id:
            return False
        return any(p.event_id == event_id for p in self.positions.values())

    # ── Mutations ──

    def add_position(self, pos: Position) -> bool:
        """Pozisyon ekle. Event/condition duplicate'te False döner (ARCH Kural 8).

        Defensive duplicate guard — gate.py'de event_already_held normal akışta
        zaten reddediyor; buraya gelirse caller'ın loglaması beklenir.
        """
        if pos.event_id and self.has_event(pos.event_id):
            return False
        if pos.condition_id in self.positions:
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
        state'i cycle-bazlı → `lifecycle.tick_position_state` ile güncellenir.
        """
        if not token_id or yes_price <= 0:
            return False
        for pos in self.positions.values():
            if pos.token_id == token_id:
                pos.current_price = yes_price
                pos.bid_price = bid_price
                return True
        return False
