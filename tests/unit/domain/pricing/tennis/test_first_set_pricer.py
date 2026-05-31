"""First set winner pricer."""
from src.domain.pricing.tennis.first_set_pricer import price_first_set_winner


def test_equal_players_half():
    p = price_first_set_winner(p_a=0.60, p_b=0.60)
    assert abs(p - 0.5) < 1e-3


def test_strong_favorite_high_prob():
    p = price_first_set_winner(p_a=0.70, p_b=0.55)
    assert p > 0.7


def test_format_independent():
    p1 = price_first_set_winner(p_a=0.65, p_b=0.60)
    p2 = price_first_set_winner(p_a=0.65, p_b=0.60)
    assert p1 == p2
