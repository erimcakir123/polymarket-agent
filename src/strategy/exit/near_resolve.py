"""Near-resolve profit lock — bid_price >= threshold → sell all."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NearResolveResult:
    sell_pct: float = 1.0
    reason: str = ""


def check(bid_price: float, threshold: float = 0.94) -> NearResolveResult | None:
    """bid_price >= threshold → NEAR_RESOLVE. None → hold."""
    if bid_price >= threshold:
        return NearResolveResult(sell_pct=1.0, reason=f"bid {bid_price:.3f} >= {threshold:.2f}")
    return None
