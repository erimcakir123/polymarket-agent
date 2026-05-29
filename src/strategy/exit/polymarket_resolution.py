"""Polymarket resolution exit signal — pure decision (I/O caller'da).

Polymarket gamma'da market closed=true + umaResolutionStatus=resolved oldugunda
owned-side payout (0 veya 1) hesaplanir; ExitProcessor bu sinyali alip
_finalize_full_exit ile pozisyonu kapatir.

Owned-side payout:
- BUY_YES: outcomePrices[0] (YES token resolution price)
- BUY_NO : outcomePrices[1] (NO  token resolution price)

prices=['1','0'] -> YES won (1.0) / NO lost (0.0)
prices=['0','1'] -> NO  won (1.0) / YES lost (0.0)

Hicbir kosul saglanmazsa (market None / closed degil / uma resolved degil /
bozuk prices) -> None.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from src.models.position import Position

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedSignal:
    """Polymarket resolution detected. exit_price = owned-side payout (0.0 veya 1.0)."""
    exit_price: float


def check_resolution(pos: Position, market: dict | None) -> ResolvedSignal | None:
    """Market resolved ise ResolvedSignal don, degilse None.

    Args:
        pos: open position (direction hangi outcome owned belirler).
        market: gamma.fetch_closed_market_by_condition response, or None.

    Returns:
        ResolvedSignal(exit_price=owned_payout) ya da None.
    """
    if market is None:
        return None
    if not market.get("closed"):
        return None
    if market.get("umaResolutionStatus") != "resolved":
        return None

    prices = market.get("outcomePrices", "[]")
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except json.JSONDecodeError:
            logger.warning(
                "Gamma resolved market %s: outcomePrices not parseable",
                pos.slug[:30],
            )
            return None
    if not isinstance(prices, list) or len(prices) < 2:
        return None

    try:
        yes_payout = float(prices[0])
        no_payout = float(prices[1])
    except (ValueError, TypeError):
        return None

    payout = yes_payout if pos.direction == "BUY_YES" else no_payout
    return ResolvedSignal(exit_price=payout)
