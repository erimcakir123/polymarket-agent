"""Total games over/under pricer."""
from src.domain.pricing.tennis.totals_pricer import (
    expected_total_games,
    price_total_over,
)


def test_high_hold_more_games():
    high = expected_total_games(p_a=0.70, p_b=0.70, best_of=3)
    low = expected_total_games(p_a=0.50, p_b=0.50, best_of=3)
    assert high > low


def test_over_under_complement():
    p_over = price_total_over(p_a=0.65, p_b=0.60, best_of=3, line=22.5)
    p_under = price_total_over(p_a=0.65, p_b=0.60, best_of=3, line=22.5, side="under")
    assert abs(p_over + p_under - 1.0) < 1e-6


def test_bo5_has_more_games():
    bo3 = expected_total_games(p_a=0.65, p_b=0.60, best_of=3)
    bo5 = expected_total_games(p_a=0.65, p_b=0.60, best_of=5)
    assert bo5 > bo3


def test_extreme_dominance_low_total():
    # A çok güçlü (p=0.80), B zayıf (p=0.40) → maç çabuk biter
    total = expected_total_games(p_a=0.80, p_b=0.40, best_of=3)
    assert total < 23
