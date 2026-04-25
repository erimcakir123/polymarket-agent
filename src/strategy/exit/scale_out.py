"""Scale-out (kısmi exit) — bid_price >= threshold → sell 50%."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScaleOutResult:
    sell_pct: float = 0.50
    tier: int = 1
    reason: str = ""


def check(bid_price: float, already_scaled: bool, threshold: float = 0.85) -> ScaleOutResult | None:
    """bid_price >= threshold ve henüz scale edilmediyse → SCALE_OUT. None → hold."""
    if already_scaled:
        return None
    if bid_price >= threshold:
        return ScaleOutResult(sell_pct=0.50, tier=1, reason=f"bid {bid_price:.3f} >= {threshold:.2f}")
    return None
