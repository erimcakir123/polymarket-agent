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
    except Exception:
        return {"fillable": True, "strategy": "market", "reason": "Book check failed, proceeding anyway"}
