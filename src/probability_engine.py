"""Bookmaker Probability Engine.

Pure bookmaker-derived probability. No AI blend — bookmaker consensus is the
sole anchor for trade decisions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from src.confidence import derive_confidence

logger = logging.getLogger(__name__)


@dataclass
class BookmakerProbability:
    """Result of bookmaker probability calculation."""
    probability: float          # Final probability [0.05, 0.95]
    confidence: str             # "A" / "B" / "C"
    bookmaker_prob: float       # Raw bookmaker probability
    num_bookmakers: float       # Total bookmaker weight
    has_sharp: bool             # Pinnacle/Betfair Exchange present


def calculate_bookmaker_probability(
    bookmaker_prob: Optional[float] = None,
    num_bookmakers: float = 0,
    has_sharp: bool = False,
) -> BookmakerProbability:
    """Calculate probability from bookmaker data only.

    Args:
        bookmaker_prob: Average bookmaker implied probability (None if unavailable)
        num_bookmakers: Total bookmaker weight (sum of individual weights)
        has_sharp: Whether a sharp book (Pinnacle/Betfair Exchange) is present

    Returns:
        BookmakerProbability with final probability and metadata
    """
    confidence = derive_confidence(num_bookmakers, has_sharp)

    if bookmaker_prob is None or bookmaker_prob <= 0 or num_bookmakers < 1:
        return BookmakerProbability(
            probability=0.5,
            confidence=confidence,
            bookmaker_prob=0.0,
            num_bookmakers=num_bookmakers,
            has_sharp=has_sharp,
        )

    clamped = max(0.05, min(0.95, bookmaker_prob))

    return BookmakerProbability(
        probability=round(clamped, 4),
        confidence=confidence,
        bookmaker_prob=round(bookmaker_prob, 4),
        num_bookmakers=num_bookmakers,
        has_sharp=has_sharp,
    )
