"""Newton-Keller tennis formulas — Wikipedia ve O'Malley 2008 referans değerleri."""
from src.domain.pricing.tennis.markov import (
    game_win_prob,
    match_win_prob,
    set_win_prob,
    tiebreak_win_prob,
)


def test_game_at_equal_serve_is_half():
    assert abs(game_win_prob(0.5) - 0.5) < 1e-6


def test_game_at_high_serve():
    p = game_win_prob(0.65)
    assert 0.82 < p < 0.85


def test_game_at_low_serve():
    p = game_win_prob(0.35)
    assert 0.15 < p < 0.18


def test_set_win_prob_high_serve_pair():
    # A serve 0.65 (game win ~0.83), B serve 0.55 (game win ~0.62) → A dominantes
    p = set_win_prob(p_a_serve=0.65, p_b_serve=0.55)
    assert 0.70 < p < 0.90


def test_match_bo3_win_prob():
    # set prob 0.70 → match (BO3) ~ 0.784 (literature)
    p = match_win_prob(set_prob=0.70, best_of=3)
    assert 0.78 < p < 0.79


def test_match_bo5_win_prob():
    # set prob 0.70 → match (BO5) ~ 0.837
    p = match_win_prob(set_prob=0.70, best_of=5)
    assert 0.83 < p < 0.84


def test_match_bo5_higher_than_bo3():
    set_p = 0.65
    assert match_win_prob(set_p, 5) > match_win_prob(set_p, 3)


def test_tiebreak_equal_is_half():
    assert abs(tiebreak_win_prob(0.5, 0.5) - 0.5) < 1e-6
