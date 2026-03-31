"""Edge detection: AI probability vs market price."""
from __future__ import annotations
import logging
from typing import Dict, Optional
from src.models import Direction

logger = logging.getLogger(__name__)

DEFAULT_CONFIDENCE_MULTIPLIERS = {"C": 1.5, "B-": 1.0, "B+": 0.85, "A": 0.75}


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
