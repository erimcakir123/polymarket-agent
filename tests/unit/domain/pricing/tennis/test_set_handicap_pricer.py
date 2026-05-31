"""Set handicap — multiclass set-score distribution."""
from src.domain.pricing.tennis.set_handicap_pricer import (
    price_set_handicap,
    set_score_distribution,
)


def test_distribution_sums_to_one_bo3():
    dist = set_score_distribution(set_prob=0.65, best_of=3)
    assert abs(sum(dist.values()) - 1.0) < 1e-6
    assert dist[(2, 0)] + dist[(2, 1)] > dist[(1, 2)] + dist[(0, 2)]


def test_distribution_sums_to_one_bo5():
    dist = set_score_distribution(set_prob=0.60, best_of=5)
    assert abs(sum(dist.values()) - 1.0) < 1e-6


def test_minus_15_handicap_bo3():
    # A favori p=0.65, A -1.5 → must win 2-0 → P = 0.65^2 = 0.4225
    p = price_set_handicap(set_prob=0.65, best_of=3, handicap=-1.5)
    assert abs(p - 0.4225) < 1e-6


def test_plus_15_handicap_bo3():
    # B underdog p=0.35, +1.5 handicap from B's perspective:
    # B kapsar → B wins or A wins by 1
    # dist[(0,2)] + dist[(1,2)] + dist[(2,1)] kapsar
    # but +1.5 means B's effective = B + 1.5 > A
    p = price_set_handicap(set_prob=0.35, best_of=3, handicap=1.5)
    assert p > 0.5
