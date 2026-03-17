"""Order book depth analysis and slippage estimation."""
from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class OrderBookAnalyzer:
    def __init__(self, wall_threshold_usd: float = 5000, max_slippage_pct: float = 0.015) -> None:
        self.wall_threshold = wall_threshold_usd
        self.max_slippage = max_slippage_pct

    def analyze(self, book: Dict[str, Any], side: str, size_usdc: float) -> Dict[str, Any]:
        levels = book.get("asks" if side == "BUY" else "bids", [])
        if not levels:
            return {"estimated_avg_price": 0, "slippage_pct": 1.0, "executable": False}

        remaining = size_usdc
        total_shares = 0.0
        total_cost = 0.0

        for level in levels:
            price = float(level["price"])
            shares_available = float(level["size"])
            level_cost = shares_available * price

            if remaining <= level_cost:
                shares_bought = remaining / price
                total_shares += shares_bought
                total_cost += remaining
                remaining = 0
                break
            else:
                total_shares += shares_available
                total_cost += level_cost
                remaining -= level_cost

        if total_shares == 0:
            return {"estimated_avg_price": 0, "slippage_pct": 1.0, "executable": False}

        avg_price = total_cost / total_shares
        best_price = float(levels[0]["price"])
        slippage = abs(avg_price - best_price) / best_price if best_price > 0 else 0

        return {
            "estimated_avg_price": round(avg_price, 4),
            "slippage_pct": round(slippage, 4),
            "executable": remaining == 0 and slippage <= self.max_slippage,
            "unfilled_usdc": round(remaining, 2),
        }

    def detect_walls(self, book: Dict[str, Any]) -> Dict[str, List[dict]]:
        result: Dict[str, List[dict]] = {"bid_walls": [], "ask_walls": []}
        for side_key, wall_key in [("bids", "bid_walls"), ("asks", "ask_walls")]:
            for level in book.get(side_key, []):
                price = float(level["price"])
                size = float(level["size"])
                value = price * size
                if value >= self.wall_threshold:
                    result[wall_key].append({"price": price, "size": size, "value_usd": round(value, 2)})
        return result
