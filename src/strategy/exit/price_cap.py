"""PLAN-014: Dolar-bazlı stop-loss (price_cap).

Koşul: token fiyatı eşiğin altına düştüğünde VE gerçekleşmemiş zarar
max_loss_usd'yi aştığında pozisyonu kapat.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.position import Position


@dataclass
class SLParams:
    enabled: bool
    price_below: float
    max_loss_usd: float
    min_elapsed_pct: float = field(default=0.75)  # mac %75 tamamlanmadan SL calismaz


def check(pos: "Position", sl: SLParams, elapsed_pct: float) -> bool:
    """True döndürürse SL tetiklenir ve pozisyon kapatılır."""
    if not sl.enabled:
        return False
    if elapsed_pct < sl.min_elapsed_pct:
        return False
    if pos.current_price >= sl.price_below:
        return False
    loss_usd = -pos.unrealized_pnl_usdc
    return loss_usd >= sl.max_loss_usd
