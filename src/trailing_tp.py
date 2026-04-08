"""Trailing Take-Profit System.

Replaces fixed TP entirely. Once a position reaches activation threshold,
a trailing floor tracks the peak price upward. When price drops below
the floor, the position is closed -- locking in profit.

Logic:
    1. Position profit < ACTIVATION_PCT -> no action (let it run)
    2. Profit >= ACTIVATION_PCT -> trailing ACTIVE, track peak
    3. Peak updates on every price tick (via WebSocket or polling)
    4. Floor = peak × (1 - TRAIL_DISTANCE)
    5. Current price < floor -> EXIT (profit locked)

No fixed TP means:
    - A position at +30% won't be sold if it's still climbing
    - A position at +80% will be sold when it starts dropping (e.g., drops to +72%)
    - Maximum upside capture with downside protection
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from src.models import effective_price as eff_price_fn

logger = logging.getLogger(__name__)

# Default parameters (can be overridden via config)
DEFAULT_ACTIVATION_PCT = 0.20   # Activate trailing at +20% profit
DEFAULT_TRAIL_DISTANCE = 0.15   # Sell when price drops 15% from peak


@dataclass
class TrailingTPState:
    """Trailing TP state for a single position."""
    active: bool = False
    peak_price: float = 0.0
    floor_price: float = 0.0
    activation_price: float = 0.0   # Price at which trailing was activated
    activated_at: float = 0.0       # Timestamp when activated


def calculate_trailing_tp(
    entry_price: float,
    current_price: float,
    direction: str,
    peak_price: float = 0.0,
    trailing_active: bool = False,
    activation_pct: float = DEFAULT_ACTIVATION_PCT,
    trail_distance: float = DEFAULT_TRAIL_DISTANCE,
) -> dict:
    """Calculate trailing take-profit decision.

    Args:
        entry_price: Position entry price
        current_price: Current market price
        direction: "BUY_YES" or "BUY_NO"
        peak_price: Highest price seen since activation (0.0 if not active)
        trailing_active: Whether trailing is currently active
        activation_pct: Profit % to activate trailing (default 20%)
        trail_distance: Distance from peak to trigger exit (default 15%)

    Returns:
        dict with:
            - action: "HOLD" | "EXIT"
            - trailing_active: bool (new state)
            - peak_price: float (updated peak)
            - floor_price: float (current floor, 0.0 if inactive)
            - profit_pct: float (current profit %)
            - reason: str (explanation)
    """
    if entry_price <= 0 or current_price <= 0:
        return _hold(0.0, trailing_active, peak_price, 0.0)

    # Calculate profit based on direction
    if direction == "BUY_YES":
        profit_pct = (current_price - entry_price) / entry_price
        effective_price = eff_price_fn(current_price, direction)
    elif direction == "BUY_NO":
        # BUY_NO: cost basis is (1 - entry_yes_price), value is (1 - current_yes_price)
        no_cost = eff_price_fn(entry_price, direction)
        no_value = eff_price_fn(current_price, direction)
        profit_pct = (no_value - no_cost) / no_cost if no_cost > 0 else 0.0
        # For trailing, track the NO token price (higher = better for BUY_NO)
        effective_price = no_value
    else:
        return _hold(0.0, False, 0.0, 0.0)

    # Entry effective price = minimum floor (never exit at or below entry)
    if direction == "BUY_YES":
        _entry_eff = entry_price
    else:
        _entry_eff = eff_price_fn(entry_price, direction)

    # Step 1: Check if trailing should activate
    if not trailing_active:
        if profit_pct >= activation_pct:
            # ACTIVATE trailing TP
            new_peak = effective_price
            floor = max(new_peak * (1.0 - trail_distance), _entry_eff * 1.01)  # At least 1% above entry
            logger.info(
                "Trailing TP ACTIVATED: profit=%.1f%%, peak=$%.3f, floor=$%.3f",
                profit_pct * 100, new_peak, floor,
            )
            return {
                "action": "HOLD",
                "trailing_active": True,
                "peak_price": new_peak,
                "floor_price": floor,
                "profit_pct": profit_pct,
                "reason": f"Trailing activated at +{profit_pct:.1%} profit",
            }
        else:
            # Not yet profitable enough
            return _hold(profit_pct, False, 0.0, 0.0)

    # Step 2: Trailing is active -- update peak and check floor
    if effective_price > peak_price:
        # New high -- update peak and floor
        peak_price = effective_price
        floor = max(peak_price * (1.0 - trail_distance), _entry_eff * 1.01)
        logger.debug(
            "Trailing TP new peak: $%.3f, floor=$%.3f, profit=%.1f%%",
            peak_price, floor, profit_pct * 100,
        )
        return {
            "action": "HOLD",
            "trailing_active": True,
            "peak_price": peak_price,
            "floor_price": floor,
            "profit_pct": profit_pct,
            "reason": f"New peak ${peak_price:.3f}, floor ${floor:.3f}",
        }

    # Price is below peak -- check if it hit the floor
    floor = max(peak_price * (1.0 - trail_distance), _entry_eff * 1.01)

    if effective_price <= floor:
        # TRAIL HIT -- EXIT
        locked_profit_pct = _calc_locked_profit(entry_price, floor, direction)
        logger.info(
            "Trailing TP EXIT: price=$%.3f hit floor=$%.3f (peak=$%.3f). "
            "Locked profit: %.1f%% (vs peak %.1f%%)",
            effective_price, floor, peak_price,
            locked_profit_pct * 100, profit_pct * 100,
        )
        return {
            "action": "EXIT",
            "trailing_active": True,
            "peak_price": peak_price,
            "floor_price": floor,
            "profit_pct": profit_pct,
            "reason": (
                f"Trailing TP hit: price ${effective_price:.3f} <= floor ${floor:.3f} "
                f"(peak ${peak_price:.3f}, locked ~{locked_profit_pct:.1%})"
            ),
        }

    # Between peak and floor -- hold
    distance_to_floor = (effective_price - floor) / effective_price if effective_price > 0 else 0
    return {
        "action": "HOLD",
        "trailing_active": True,
        "peak_price": peak_price,
        "floor_price": floor,
        "profit_pct": profit_pct,
        "reason": f"Trailing active: {distance_to_floor:.1%} above floor",
    }


def _hold(profit_pct: float, active: bool, peak: float, floor: float) -> dict:
    return {
        "action": "HOLD",
        "trailing_active": active,
        "peak_price": peak,
        "floor_price": floor,
        "profit_pct": profit_pct,
        "reason": "Below activation threshold" if not active else "Holding",
    }


def _calc_locked_profit(entry: float, floor: float, direction: str) -> float:
    """Approximate locked profit percentage at the floor price."""
    cost = eff_price_fn(entry, direction)
    return (floor - cost) / cost if cost > 0 else 0.0
