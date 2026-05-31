"""Set totals (kaç set oynanır) pricer."""
from __future__ import annotations

from src.domain.pricing.tennis.set_handicap_pricer import set_score_distribution


def set_count_distribution(set_prob: float, best_of: int) -> dict[int, float]:
    """Dağılım: {set_count: probability}."""
    score_dist = set_score_distribution(set_prob, best_of)
    counts: dict[int, float] = {}
    for (a, b), p in score_dist.items():
        n = a + b
        counts[n] = counts.get(n, 0.0) + p
    return counts


def price_set_total_over(set_prob: float, best_of: int, line: float) -> float:
    """P(set count > line)."""
    dist = set_count_distribution(set_prob, best_of)
    return sum(p for n, p in dist.items() if n > line)
