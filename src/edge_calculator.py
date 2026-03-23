"""Edge detection: AI probability vs market price."""
from __future__ import annotations
from typing import Dict, Optional
from src.models import Direction

DEFAULT_CONFIDENCE_MULTIPLIERS = {"low": 1.5, "medium": 1.0, "high": 0.75}


def calculate_edge(
    ai_prob: float,
    market_yes_price: float,
    min_edge: float = 0.06,
    confidence: str = "medium",
    confidence_multipliers: Optional[Dict[str, float]] = None,
) -> tuple[Direction, float]:
    multipliers = confidence_multipliers or DEFAULT_CONFIDENCE_MULTIPLIERS
    multiplier = multipliers.get(confidence, 1.0)
    threshold = min_edge * multiplier
    raw = ai_prob - market_yes_price

    if raw > threshold:
        return Direction.BUY_YES, raw
    elif raw < -threshold:
        return Direction.BUY_NO, abs(raw)
    else:
        return Direction.HOLD, abs(raw)


def calculate_edge_with_whale(
    ai_prob: float,
    market_price: float,
    min_edge: float = 0.06,
    confidence: str = "medium",
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


_CONFIDENCE_LEVELS = ["low", "medium", "high"]


def boost_confidence(current: str, delta: int) -> str:
    """Shift confidence level up (+1) or down (-1), clamped to valid range."""
    try:
        idx = _CONFIDENCE_LEVELS.index(current)
    except ValueError:
        return current
    new_idx = max(0, min(len(_CONFIDENCE_LEVELS) - 1, idx + delta))
    return _CONFIDENCE_LEVELS[new_idx]
