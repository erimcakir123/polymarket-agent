# src/liquidity_check.py
"""Check CLOB order book depth before placing sell orders.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #18
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def check_exit_liquidity(
    token_id: str,
    shares_to_sell: float,
    min_fill_ratio: float = 0.80,
    mock_book: dict | None = None,
) -> dict:
    """Check order book depth. mock_book for testing, else calls CLOB API."""
    try:
        if shares_to_sell <= 0:
            return {"fillable": True, "strategy": "market", "reason": "Nothing to sell"}

        if mock_book is not None:
            book = mock_book
        else:
            from src.executor import fetch_order_book
            book = fetch_order_book(token_id)

        bids = book.get("bids", [])
        if not bids:
            return {"fillable": False, "strategy": "skip", "reason": "No bids"}

        best_bid = float(bids[0]["price"])
        floor_price = best_bid * 0.95

        available = 0.0
        for bid in bids:
            price = float(bid["price"])
            if price < floor_price:
                break
            available += float(bid["size"])

        fill_ratio = available / shares_to_sell
        if fill_ratio >= 1.0:
            return {"fillable": True, "strategy": "market",
                    "recommended_price": best_bid, "available_depth": available}
        elif fill_ratio >= min_fill_ratio:
            return {"fillable": True, "strategy": "limit",
                    "recommended_price": best_bid, "available_depth": available}
        else:
            return {"fillable": False, "strategy": "split",
                    "recommended_price": best_bid, "available_depth": available,
                    "partially_fillable": True,
                    "note": f"Only {fill_ratio:.0%} fillable — split across cycles"}
    except Exception as e:
        logger.warning("Exit liquidity check failed: %s — blocking sell to prevent slippage", e)
        return {"fillable": False, "strategy": "skip", "reason": "Book check failed — skipping to prevent slippage"}


def check_entry_liquidity(
    token_id: str,
    size_usdc: float,
    min_depth: float = 100.0,
    mock_book: dict | None = None,
) -> dict:
    """Check order book depth before entry. Returns fillability info.

    Rules:
    - Skip if total ask depth < $min_depth (illiquid market)
    - If order > 20% of book depth, halve the size
    - Returns recommended_size (may be smaller than requested)
    """
    try:
        if size_usdc <= 0:
            return {"ok": True, "recommended_size": size_usdc, "reason": "Nothing to buy"}

        if mock_book is not None:
            book = mock_book
        else:
            from src.executor import fetch_order_book
            book = fetch_order_book(token_id)

        asks = book.get("asks", [])
        if not asks:
            return {"ok": False, "recommended_size": 0, "reason": "No asks — market dead"}

        # Calculate total ask-side depth in USDC
        total_depth = 0.0
        for ask in asks:
            price = float(ask["price"])
            size = float(ask["size"])
            total_depth += price * size

        if total_depth < max(min_depth, 1.0):
            logger.info("Entry blocked: ask depth $%.0f < min $%.0f for %s",
                        total_depth, min_depth, token_id[:16])
            return {"ok": False, "recommended_size": 0, "depth": total_depth,
                    "reason": f"Ask depth ${total_depth:.0f} < ${min_depth:.0f}"}

        # If our order is > 20% of book, halve size to reduce slippage
        recommended = size_usdc
        impact_ratio = size_usdc / total_depth  # safe: total_depth >= 1.0
        if impact_ratio > 0.20:
            recommended = size_usdc / 2
            logger.info("Entry size halved: $%.2f → $%.2f (%.0f%% of $%.0f book) for %s",
                        size_usdc, recommended, impact_ratio * 100, total_depth, token_id[:16])

        return {"ok": True, "recommended_size": recommended, "depth": total_depth,
                "impact_ratio": impact_ratio}
    except Exception as e:
        logger.warning("Entry liquidity check failed: %s — blocking entry to prevent slippage", e)
        return {"ok": False, "recommended_size": 0, "reason": "Book check failed — skipping to prevent slippage"}
