"""Edge detection: AI probability vs market price with slippage awareness."""
from __future__ import annotations
import logging
from typing import Dict, List, Optional
from src.models import Direction

logger = logging.getLogger(__name__)

DEFAULT_CONFIDENCE_MULTIPLIERS = {"C": 1.5, "B-": 1.0, "B+": 0.85, "A": 0.75}


def estimate_slippage(
    order_size_usdc: float,
    order_book_side: List[dict],
    max_slippage_pct: float = 0.02,
) -> float:
    """Estimate slippage from order book depth.

    Args:
        order_size_usdc: Size of the order in USDC
        order_book_side: List of {price, size} from relevant side (asks for buy, bids for sell)
        max_slippage_pct: Maximum acceptable slippage (default 2%)

    Returns:
        Estimated slippage as absolute price impact (e.g., 0.015 = 1.5 cents)
    """
    if not order_book_side or order_size_usdc <= 0:
        return 0.0

    total_filled = 0.0
    weighted_price = 0.0
    best_price = float(order_book_side[0].get("price", 0)) if order_book_side else 0.0

    for level in order_book_side:
        price = float(level.get("price", 0))
        size = float(level.get("size", 0))
        if price <= 0 or size <= 0:
            continue

        level_usdc = price * size
        remaining = order_size_usdc - total_filled

        if remaining <= 0:
            break

        fill_at_level = min(level_usdc, remaining)
        weighted_price += price * fill_at_level
        total_filled += fill_at_level

    if total_filled <= 0 or best_price <= 0:
        return 0.0

    avg_fill_price = weighted_price / total_filled
    slippage = abs(avg_fill_price - best_price)

    # Cap at max slippage
    if best_price > 0 and slippage / best_price > max_slippage_pct:
        capped = best_price * max_slippage_pct
        logger.warning(
            "Slippage %.4f (%.1f%%) exceeds max %.1f%% -- capped to %.4f",
            slippage, (slippage / best_price) * 100, max_slippage_pct * 100, capped,
        )
        slippage = capped

    return slippage


def calculate_edge(
    ai_prob: float,
    market_yes_price: float,
    min_edge: float = 0.06,
    confidence: str = "B-",
    confidence_multipliers: Optional[Dict[str, float]] = None,
    spread: float = 0.0,
    slippage: float = 0.0,
    edge_threshold_adjustment: float = 0.0,
) -> tuple[Direction, float]:
    """Calculate edge between AI probability and market price.

    Args:
        ai_prob: Anchored probability (bookmaker-weighted or shrunk)
        market_yes_price: Current YES token price
        min_edge: Base minimum edge threshold
        confidence: AI confidence grade
        confidence_multipliers: Grade-to-multiplier mapping
        spread: Bid-ask spread to account for
        slippage: Estimated slippage from order book
        edge_threshold_adjustment: Additional edge required (from probability engine)

    Returns:
        (Direction, effective_edge) tuple
    """
    # ai_prob is ALWAYS P(YES wins). raw > 0 -> BUY_YES, raw < 0 -> BUY_NO.
    multipliers = confidence_multipliers or DEFAULT_CONFIDENCE_MULTIPLIERS
    multiplier = multipliers.get(confidence, 1.0)
    threshold = (min_edge + edge_threshold_adjustment) * multiplier
    raw = ai_prob - market_yes_price

    # Effective edge = raw edge minus costs (spread + slippage)
    cost = spread + slippage
    effective_yes = raw - cost
    effective_no = abs(raw) - cost

    if raw > 0 and effective_yes > threshold:
        return Direction.BUY_YES, effective_yes
    elif raw < 0 and effective_no > threshold:
        return Direction.BUY_NO, effective_no
    else:
        return Direction.HOLD, abs(raw)


def calculate_edge_with_whale(
    ai_prob: float,
    market_price: float,
    min_edge: float = 0.06,
    confidence: str = "B-",
    whale_prob: float | None = None,
    whale_weight: float = 0.15,
) -> tuple[Direction, float]:
    if whale_prob is not None:
        blended = ai_prob * (1 - whale_weight) + whale_prob * whale_weight
    else:
        blended = ai_prob
    return calculate_edge(blended, market_price, min_edge, confidence)


def scale_min_edge(
    base_min_edge: float,
    fill_ratio: float,
    aggressive_threshold: float = 0.3,
    selective_threshold: float = 0.7,
) -> float:
    """Scale min_edge based on portfolio fill ratio.

    When portfolio is empty (<aggressive), lower the bar to find trades.
    When portfolio is full (>selective), raise the bar to be pickier.
    """
    if fill_ratio < aggressive_threshold:
        return base_min_edge * 0.8
    elif fill_ratio > selective_threshold:
        return base_min_edge * 1.3
    return base_min_edge


_CONFIDENCE_LEVELS = ["C", "B-", "B+", "A"]


def boost_confidence(current: str, delta: int) -> str:
    """Shift confidence level up (+1) or down (-1), clamped to valid range."""
    try:
        idx = _CONFIDENCE_LEVELS.index(current)
    except ValueError:
        return current
    new_idx = max(0, min(len(_CONFIDENCE_LEVELS) - 1, idx + delta))
    return _CONFIDENCE_LEVELS[new_idx]
