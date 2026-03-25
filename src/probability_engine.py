"""Bookmaker-Anchored Probability Engine.

Combines AI probability with bookmaker implied probability for more robust estimates.
AI never decides alone — bookmaker consensus serves as the anchor.

Formula:
    anchored = BOOK_WEIGHT × bookmaker_prob + AI_WEIGHT × ai_prob

When bookmaker data unavailable, applies overconfidence shrinkage:
    shrunk = ai_prob × (1 - SHRINKAGE) + 0.50 × SHRINKAGE
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Default weights — bookmaker gets majority vote
BOOK_WEIGHT = 0.55
AI_WEIGHT = 0.45

# Shrinkage toward 50% when no bookmaker data (LLMs are overconfident)
SHRINKAGE_FACTOR = 0.10
SHRINKAGE_TARGET = 0.50

# If AI and bookmaker diverge by more than this, flag as high-divergence
HIGH_DIVERGENCE_THRESHOLD = 0.15


@dataclass
class AnchoredProbability:
    """Result of bookmaker-anchored probability calculation."""
    probability: float          # Final anchored probability [0.05, 0.95]
    method: str                 # "anchored" | "shrunk_no_bookmaker"
    ai_prob: float              # Raw AI probability
    bookmaker_prob: float       # Bookmaker probability (0.0 if unavailable)
    divergence: float           # |AI - bookmaker| (0.0 if no bookmaker)
    high_divergence: bool       # True if divergence > threshold
    num_bookmakers: int         # Number of bookmaker sources


def calculate_anchored_probability(
    ai_prob: float,
    bookmaker_prob: Optional[float] = None,
    num_bookmakers: int = 0,
    book_weight: float = BOOK_WEIGHT,
    ai_weight: float = AI_WEIGHT,
    shrinkage: float = SHRINKAGE_FACTOR,
    divergence_threshold: float = HIGH_DIVERGENCE_THRESHOLD,
) -> AnchoredProbability:
    """Calculate bookmaker-anchored probability.

    Args:
        ai_prob: AI's estimated probability (0.0-1.0)
        bookmaker_prob: Average bookmaker implied probability (None if unavailable)
        num_bookmakers: Number of bookmaker sources used
        book_weight: Weight for bookmaker probability (default 0.55)
        ai_weight: Weight for AI probability (default 0.45)
        shrinkage: Shrinkage factor toward 50% when no bookmaker (default 0.10)
        divergence_threshold: Max acceptable AI-bookmaker divergence (default 0.15)

    Returns:
        AnchoredProbability with final probability and metadata
    """
    ai_prob = max(0.01, min(0.99, ai_prob))

    if bookmaker_prob is not None and bookmaker_prob > 0 and num_bookmakers >= 1:
        bookmaker_prob = max(0.01, min(0.99, bookmaker_prob))

        # Anchored formula
        final = book_weight * bookmaker_prob + ai_weight * ai_prob

        divergence = abs(ai_prob - bookmaker_prob)
        high_div = divergence > divergence_threshold

        if high_div:
            logger.warning(
                "HIGH DIVERGENCE: AI=%.2f vs Book=%.2f (diff=%.2f, threshold=%.2f)",
                ai_prob, bookmaker_prob, divergence, divergence_threshold,
            )

        final = max(0.05, min(0.95, final))

        return AnchoredProbability(
            probability=round(final, 4),
            method="anchored",
            ai_prob=ai_prob,
            bookmaker_prob=bookmaker_prob,
            divergence=round(divergence, 4),
            high_divergence=high_div,
            num_bookmakers=num_bookmakers,
        )

    else:
        # No bookmaker data — apply overconfidence shrinkage
        # Pulls AI estimate toward 50% by shrinkage factor
        shrunk = ai_prob * (1 - shrinkage) + SHRINKAGE_TARGET * shrinkage
        shrunk = max(0.05, min(0.95, shrunk))

        logger.info(
            "SHRINK_DEBUG: AI=%.3f → shrunk=%.3f (formula: %.3f * %.2f + %.2f * %.2f)",
            ai_prob, shrunk, ai_prob, 1 - shrinkage, SHRINKAGE_TARGET, shrinkage,
        )

        return AnchoredProbability(
            probability=round(shrunk, 4),
            method="shrunk_no_bookmaker",
            ai_prob=ai_prob,
            bookmaker_prob=0.0,
            divergence=0.0,
            high_divergence=False,
            num_bookmakers=0,
        )


def get_edge_threshold_adjustment(anchored: AnchoredProbability) -> float:
    """Return additional edge threshold based on probability quality.

    High-divergence signals require higher edge to trade.
    No-bookmaker signals get a small penalty.

    Returns:
        Additional edge to add to min_edge (0.0 = no adjustment)
    """
    if anchored.high_divergence:
        # AI and bookmaker strongly disagree — need much higher edge
        return 0.04  # +4% additional edge required
    if anchored.method == "shrunk_no_bookmaker":
        # No bookmaker validation — small penalty
        return 0.02  # +2% additional edge required
    return 0.0
