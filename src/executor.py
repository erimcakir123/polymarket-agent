"""Order execution: dry_run, paper, live modes."""
from __future__ import annotations
import logging
import uuid
from typing import Any, Optional

from src.config import Mode

logger = logging.getLogger(__name__)


class Executor:
    def __init__(self, mode: Mode, clob_client: Any = None) -> None:
        self.mode = mode
        self.client = clob_client
        if mode == Mode.LIVE and clob_client is None:
            raise ValueError("CLOB client required for live mode")

    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size_usdc: float,
        order_type: str = "GTC",
    ) -> dict:
        if self.mode in (Mode.DRY_RUN, Mode.PAPER):
            order_id = f"sim_{uuid.uuid4().hex[:8]}"
            logger.info("[%s] Simulated %s %s @ $%.2f, size=$%.2f",
                        self.mode.value, side, token_id[:8], price, size_usdc)
            return {
                "order_id": order_id,
                "status": "simulated",
                "mode": self.mode.value,
                "token_id": token_id,
                "side": side,
                "price": price,
                "size_usdc": size_usdc,
            }

        # Live mode
        return self._execute_live(token_id, side, price, size_usdc, order_type)

    def place_exit_order(self, token_id: str, shares: float) -> dict:
        if self.mode in (Mode.DRY_RUN, Mode.PAPER):
            return {
                "order_id": f"sim_exit_{uuid.uuid4().hex[:8]}",
                "status": "simulated",
                "mode": self.mode.value,
            }
        return self._execute_live_exit(token_id, shares)

    def _execute_live(
        self, token_id: str, side: str, price: float, size_usdc: float, order_type: str
    ) -> dict:
        from py_clob_client.clob_types import OrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY, SELL

        clob_side = BUY if side == "BUY" else SELL
        shares = size_usdc / price
        order_args = OrderArgs(token_id=token_id, price=price, size=shares, side=clob_side)
        signed = self.client.create_order(order_args)
        ot = {"GTC": OrderType.GTC, "FOK": OrderType.FOK}.get(order_type, OrderType.GTC)
        resp = self.client.post_order(signed, ot)
        logger.info("Live order placed: %s", resp)
        return {"order_id": resp.get("orderID", ""), "status": "placed", "mode": "live", "response": resp}

    def _execute_live_exit(self, token_id: str, shares: float) -> dict:
        from py_clob_client.clob_types import MarketOrderArgs, OrderType
        from py_clob_client.order_builder.constants import SELL

        mo = MarketOrderArgs(token_id=token_id, amount=shares, side=SELL)
        signed = self.client.create_market_order(mo)
        resp = self.client.post_order(signed, OrderType.FOK)
        return {"order_id": resp.get("orderID", ""), "status": "placed", "mode": "live", "response": resp}
