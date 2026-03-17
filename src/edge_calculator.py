"""Edge detection: AI probability vs market price."""
from __future__ import annotations
from src.models import Direction

CONFIDENCE_MULTIPLIERS = {"low": 1.5, "medium": 1.0, "high": 0.75}


def calculate_edge(
    ai_prob: float,
    market_yes_price: float,
    min_edge: float = 0.06,
    confidence: str = "medium",
) -> tuple[Direction, float]:
    multiplier = CONFIDENCE_MULTIPLIERS.get(confidence, 1.0)
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
