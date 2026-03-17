"""Idle-mode spread earning via symmetric limit orders."""
from __future__ import annotations
import logging
from typing import List

from src.config import LPConfig

logger = logging.getLogger(__name__)


class LiquidityProvider:
    def __init__(self, config: LPConfig) -> None:
        self.config = config
        self.active_orders: List[dict] = []

    def generate_orders(
        self, token_id: str, midpoint: float, spread: float, bankroll: float
    ) -> List[dict]:
        if spread < self.config.min_spread_cents / 100:
            logger.debug("Spread too narrow (%.1f cents), skipping LP", spread * 100)
            return []

        max_size = bankroll * self.config.max_exposure_pct
        offset = self.config.spread_cents / 100

        bid_price = round(midpoint - offset, 2)
        ask_price = round(midpoint + offset, 2)

        if bid_price <= 0 or ask_price >= 1:
            return []

        orders = [
            {"token_id": token_id, "side": "BUY", "price": bid_price,
             "size_usdc": round(max_size, 2), "mode": "liquidity_provider"},
            {"token_id": token_id, "side": "SELL", "price": ask_price,
             "size_usdc": round(max_size, 2), "mode": "liquidity_provider"},
        ]
        return orders

    def should_cancel(self, midpoint: float, placement_midpoint: float) -> bool:
        move = abs(midpoint - placement_midpoint) / placement_midpoint if placement_midpoint > 0 else 0
        return move > self.config.price_move_cancel_pct
