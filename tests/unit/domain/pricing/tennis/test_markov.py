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


def test_tiebreak_extreme_serves_converge():
    """Hem A hem B %100 servis kazanıyorsa balance'a düşülmez, ilk break belirler.

    Edge case: closed-form deuce p_a_block=p_b_block=0 olabilir → guard test.
    """
    # A %100 serve, B %50 serve → A neredeyse kesin kazanır
    p = tiebreak_win_prob(1.0, 0.5)
    assert p > 0.9


def test_set_outcome_distribution_sums_to_one():
    """set_outcome_distribution (DRY single-source) tam dağılım vermeli."""
    from src.domain.pricing.tennis.markov import set_outcome_distribution
    dist = set_outcome_distribution(0.65, 0.60)
    total = sum(p for _, _, p in dist)
    assert abs(total - 1.0) < 1e-6


def test_set_outcome_distribution_matches_set_win_prob():
    """A skorları (a>b) toplamı set_win_prob ile aynı (DRY regression)."""
    from src.domain.pricing.tennis.markov import set_outcome_distribution
    dist = set_outcome_distribution(0.65, 0.55)
    a_wins = sum(p for a, b, p in dist if a > b)
    assert abs(a_wins - set_win_prob(0.65, 0.55)) < 1e-6


def test_game_extreme_inputs_clamped():
    """game_win_prob p<=0 → 0, p>=1 → 1 (defensive guard)."""
    assert game_win_prob(0.0) == 0.0
    assert game_win_prob(1.0) == 1.0
    assert game_win_prob(-0.5) == 0.0
    assert game_win_prob(1.5) == 1.0


def test_match_invalid_best_of_raises():
    """BO≠3,5 → ValueError (sessiz default değil)."""
    import pytest
    with pytest.raises(ValueError):
        match_win_prob(set_prob=0.6, best_of=7)
