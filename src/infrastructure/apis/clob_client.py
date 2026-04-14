"""Polymarket CLOB order placement istemcisi (live mode — TDD §8).

py-clob-client sarmalayıcı. Hybrid strategy: likit book → FOK market,
illikit → GTC limit (LIMIT_OFFSET_CENTS üstünde).

Executor dry_run/paper'da bu modülü kullanmaz; sadece Mode.LIVE'da wire'lanır.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Likit book eşiği (USDC). Altında → limit order.
LIQUID_DEPTH_USDC = 500.0
# Limit price offset (cents). Best ask/bid'in bu kadar dışına yerleş.
LIMIT_OFFSET_CENTS = 0.01


def build_client(
    host: str,
    chain_id: int,
    private_key: str,
) -> Any:
    """py-clob-client ClobClient oluştur. Runtime import (test ortamında stub'lanabilir)."""
    from py_clob_client.client import ClobClient
    return ClobClient(host=host, chain_id=chain_id, key=private_key)


def _book_depth_usdc(levels: list[dict]) -> float:
    """Orderbook level listesinden toplam USDC derinliği."""
    total = 0.0
    for lvl in levels:
        try:
            total += float(lvl.get("price", 0)) * float(lvl.get("size", 0))
        except (TypeError, ValueError, KeyError):
            continue
    return total


def choose_order_strategy(
    book: dict,
    side: str,
    price: float,
    size_usdc: float,
    liquid_threshold: float = LIQUID_DEPTH_USDC,
) -> dict:
    """Likit → market (FOK); illikit → limit (GTC) best ± offset.

    Returns: {"strategy": "market"|"limit", "price", "order_type"}
    """
    levels = book.get("asks" if side == "BUY" else "bids", [])
    depth = _book_depth_usdc(levels)

    if depth >= liquid_threshold and size_usdc < depth * 0.20:
        return {"strategy": "market", "price": price, "order_type": "FOK"}

    if side == "BUY":
        # Best ask = asks[-1] (Polymarket DESC sort)
        try:
            best = float(levels[-1]["price"]) if levels else price
        except (TypeError, ValueError, KeyError):
            best = price
        limit = round(max(0.01, best - LIMIT_OFFSET_CENTS), 2)
    else:
        try:
            best = float(levels[-1]["price"]) if levels else price
        except (TypeError, ValueError, KeyError):
            best = price
        limit = round(min(0.99, best + LIMIT_OFFSET_CENTS), 2)

    return {"strategy": "limit", "price": limit, "order_type": "GTC"}


class ClobOrderClient:
    """Live CLOB order placement (py-clob-client wrapper)."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size_usdc: float,
        order_type: str = "GTC",
    ) -> dict:
        """Live buy/sell order. Runtime import (py_clob_client)."""
        from py_clob_client.clob_types import OrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY, SELL

        if price <= 0:
            return {"order_id": "", "status": "error", "reason": "invalid price"}

        clob_side = BUY if side == "BUY" else SELL
        shares = size_usdc / price
        order_args = OrderArgs(token_id=token_id, price=price, size=shares, side=clob_side)
        signed = self._client.create_order(order_args)
        ot = {"GTC": OrderType.GTC, "FOK": OrderType.FOK}.get(order_type, OrderType.GTC)
        resp = self._client.post_order(signed, ot)
        logger.info("Live order placed: %s", resp)
        return {"order_id": resp.get("orderID", ""), "status": "placed", "response": resp}

    def place_market_sell(self, token_id: str, shares: float) -> dict:
        """FOK market sell (exit için)."""
        from py_clob_client.clob_types import MarketOrderArgs, OrderType
        from py_clob_client.order_builder.constants import SELL

        try:
            mo = MarketOrderArgs(token_id=token_id, amount=shares, side=SELL)
            signed = self._client.create_market_order(mo)
            resp = self._client.post_order(signed, OrderType.FOK)
            if not resp.get("orderID"):
                return {"order_id": "", "status": "error", "reason": "no orderID"}
            return {"order_id": resp.get("orderID", ""), "status": "placed", "response": resp}
        except Exception as e:
            logger.error("Live exit failed: %s", e)
            return {"order_id": "", "status": "error", "reason": str(e)}
