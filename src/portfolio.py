"""Position tracking, PnL, stop-loss, take-profit, drawdown breaker."""
from __future__ import annotations
import logging
from typing import Dict, List

from src.models import Position

logger = logging.getLogger(__name__)


class Portfolio:
    def __init__(self, initial_bankroll: float = 0.0) -> None:
        self.positions: Dict[str, Position] = {}
        self.bankroll: float = initial_bankroll
        self.high_water_mark: float = initial_bankroll

    def add_position(
        self,
        condition_id: str,
        token_id: str,
        direction: str,
        entry_price: float,
        size_usdc: float,
        shares: float,
        slug: str = "",
        category: str = "",
    ) -> None:
        self.positions[condition_id] = Position(
            condition_id=condition_id,
            token_id=token_id,
            direction=direction,
            entry_price=entry_price,
            size_usdc=size_usdc,
            shares=shares,
            current_price=entry_price,
            slug=slug,
            category=category,
        )

    def remove_position(self, condition_id: str) -> Position | None:
        return self.positions.pop(condition_id, None)

    def update_price(self, condition_id: str, new_price: float) -> None:
        if condition_id in self.positions:
            self.positions[condition_id].current_price = new_price

    def update_bankroll(self, new_bankroll: float) -> None:
        self.bankroll = new_bankroll
        if new_bankroll > self.high_water_mark:
            self.high_water_mark = new_bankroll

    def check_stop_losses(self, stop_loss_pct: float = 0.30) -> List[str]:
        triggered = []
        for cid, pos in self.positions.items():
            if pos.unrealized_pnl_pct < -stop_loss_pct:
                triggered.append(cid)
                logger.warning("Stop-loss triggered for %s: %.1f%%", pos.slug, pos.unrealized_pnl_pct * 100)
        return triggered

    def check_take_profits(self, take_profit_pct: float = 0.40) -> List[str]:
        triggered = []
        for cid, pos in self.positions.items():
            if pos.unrealized_pnl_pct > take_profit_pct:
                triggered.append(cid)
                logger.info("Take-profit triggered for %s: %.1f%%", pos.slug, pos.unrealized_pnl_pct * 100)
        return triggered

    def is_drawdown_breaker_active(self, halt_pct: float = 0.50) -> bool:
        if self.high_water_mark <= 0:
            return False
        return self.bankroll < self.high_water_mark * (1 - halt_pct)

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl_usdc for p in self.positions.values())

    def correlated_exposure(self, category: str) -> float:
        if self.bankroll <= 0:
            return 0.0
        cat_total = sum(p.size_usdc for p in self.positions.values() if p.category == category)
        return cat_total / self.bankroll
