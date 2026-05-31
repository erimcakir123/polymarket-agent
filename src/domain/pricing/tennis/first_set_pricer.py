"""First set winner — set win probability (format-agnostic)."""
from __future__ import annotations

from src.domain.pricing.tennis.markov import set_win_prob


def price_first_set_winner(p_a: float, p_b: float) -> float:
    """P(A wins first set). Sadece set_win_prob — match-level bağımsız."""
    return set_win_prob(p_a, p_b)
