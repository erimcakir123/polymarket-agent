"""Order execution: dry_run, paper, live modes with hybrid limit/market orders."""
from __future__ import annotations
import logging
import uuid
from typing import Any, List, Optional

import requests

from src.config import Mode

logger = logging.getLogger(__name__)

# Liquidity threshold — above this use market order, below use limit
LIQUID_DEPTH_USDC = 500.0
# Limit order offset — place limit this many cents better than market
LIMIT_OFFSET_CENTS = 0.01


def fetch_order_book(token_id: str) -> dict:
    """Fetch CLOB order book from Polymarket. Returns {bids: [...], asks: [...]}."""
    try:
        resp = requests.get(
            "https://clob.polymarket.com/book",
            params={"token_id": token_id},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Order book fetch failed for %s: %s", token_id[:16], e)
        return {"bids": [], "asks": []}


def _book_depth_usdc(levels: List[dict]) -> float:
    """Calculate total USDC depth from order book levels."""
    total = 0.0
    for level in levels:
        price = float(level.get("price", 0))
        size = float(level.get("size", 0))
        total += price * size
    return total


def choose_order_strategy(
    token_id: str,
    side: str,
    price: float,
    size_usdc: float,
    liquid_threshold: float = LIQUID_DEPTH_USDC,
) -> dict:
    """Choose between market order and limit order based on book depth.

    Returns dict with: strategy ("market"|"limit"), price, order_type
    """
    book = fetch_order_book(token_id)

    if side == "BUY":
        asks = book.get("asks", [])
        depth = _book_depth_usdc(asks)
        if depth >= liquid_threshold and size_usdc < depth * 0.20:
            # Liquid market, small order relative to book → market order
            return {"strategy": "market", "price": price, "order_type": "FOK"}
        else:
            # Illiquid → limit order slightly below best ask
            best_ask = float(asks[0]["price"]) if asks else price
            limit_price = round(max(0.01, best_ask - LIMIT_OFFSET_CENTS), 2)
            logger.info("Illiquid book (depth=$%.0f) → limit order @ $%.2f (best ask $%.2f)",
                        depth, limit_price, best_ask)
            return {"strategy": "limit", "price": limit_price, "order_type": "GTC"}
    else:
        bids = book.get("bids", [])
        depth = _book_depth_usdc(bids)
        if depth >= liquid_threshold and size_usdc < depth * 0.20:
            return {"strategy": "market", "price": price, "order_type": "FOK"}
        else:
            best_bid = float(bids[0]["price"]) if bids else price
            limit_price = round(min(0.99, best_bid + LIMIT_OFFSET_CENTS), 2)
            logger.info("Illiquid book (depth=$%.0f) → limit sell @ $%.2f (best bid $%.2f)",
                        depth, limit_price, best_bid)
            return {"strategy": "limit", "price": limit_price, "order_type": "GTC"}


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
        use_hybrid: bool = True,
    ) -> dict:
        # Hybrid mode: choose strategy based on book depth
        if use_hybrid and self.mode == Mode.LIVE:
            strategy = choose_order_strategy(token_id, side, price, size_usdc)
            price = strategy["price"]
            order_type = strategy["order_type"]
            logger.info("Hybrid order: %s strategy, price=$%.2f, type=%s",
                        strategy["strategy"], price, order_type)

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

    def exit_position(self, pos, reason: str = "", mode: "Mode | None" = None) -> dict:
        """Execute a position exit. Called by agent._exit_position().

        Args:
            pos: Position object with token_id, shares, slug attributes.
            reason: Exit reason string for audit trail.
            mode: Override mode (uses self.mode if None).
        """
        _mode = mode or self.mode
        logger.info("EXIT_POSITION: %s | reason=%s | mode=%s | shares=%.2f",
                     pos.slug[:40] if hasattr(pos, 'slug') else pos.token_id[:16],
                     reason, _mode.value, pos.shares)

        if _mode in (Mode.DRY_RUN, Mode.PAPER):
            order_id = f"sim_exit_{uuid.uuid4().hex[:8]}"
            logger.info("[%s] Simulated exit: %s | reason=%s",
                        _mode.value, pos.slug[:40] if hasattr(pos, 'slug') else "?", reason)
            return {
                "order_id": order_id,
                "status": "simulated",
                "mode": _mode.value,
                "reason": reason,
            }

        # Live mode — delegate to existing exit logic
        return self._execute_live_exit(pos.token_id, pos.shares)

    def _execute_live(
        self, token_id: str, side: str, price: float, size_usdc: float, order_type: str
    ) -> dict:
        from py_clob_client.clob_types import OrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY, SELL

        clob_side = BUY if side == "BUY" else SELL
        if price <= 0:
            logger.error("Cannot execute order with price <= 0")
            return {"order_id": "", "status": "error", "mode": "live", "reason": "invalid price"}
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
