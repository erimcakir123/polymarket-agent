"""Set totals (kaç set oynanır) pricer."""
from src.domain.pricing.tennis.set_totals_pricer import (
    price_set_total_over,
    set_count_distribution,
)


def test_bo3_distribution_sums_one():
    dist = set_count_distribution(set_prob=0.60, best_of=3)
    assert abs(sum(dist.values()) - 1.0) < 1e-6


def test_bo5_distribution_sums_one():
    dist = set_count_distribution(set_prob=0.55, best_of=5)
    assert abs(sum(dist.values()) - 1.0) < 1e-6


def test_close_match_more_sets():
    close = set_count_distribution(set_prob=0.50, best_of=3)
    dom = set_count_distribution(set_prob=0.80, best_of=3)
    assert close[3] > dom[3]


def test_over_25_bo3():
    p = price_set_total_over(set_prob=0.55, best_of=3, line=2.5)
    expected = 2 * 0.55 * 0.45
    assert abs(p - expected) < 1e-6
