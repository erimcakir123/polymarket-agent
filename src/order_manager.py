"""Pending order tracking and stale order cancellation."""
from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class OrderManager:
    def __init__(self, stale_after_cycles: int = 2) -> None:
        self.stale_after_cycles = stale_after_cycles
        self.pending_orders: Dict[str, dict] = {}

    def add_pending(
        self, order_id: str, condition_id: str, direction: str, price: float, size: float
    ) -> None:
        self.pending_orders[order_id] = {
            "order_id": order_id,
            "condition_id": condition_id,
            "direction": direction,
            "price": price,
            "size": size,
            "cycles_waiting": 0,
        }

    def tick_cycle(self) -> None:
        for order in self.pending_orders.values():
            order["cycles_waiting"] += 1

    def get_stale_orders(self) -> List[dict]:
        return [o for o in self.pending_orders.values()
                if o["cycles_waiting"] >= self.stale_after_cycles]

    def remove_order(self, order_id: str) -> None:
        self.pending_orders.pop(order_id, None)

    def cancel_stale(self, executor: Any) -> List[str]:
        cancelled = []
        for order in self.get_stale_orders():
            oid = order["order_id"]
            logger.info("Cancelling stale order: %s", oid)
            self.remove_order(oid)
            cancelled.append(oid)
        return cancelled
