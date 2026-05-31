"""H2H pricer — Glicko + Markov blend."""
from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.h2h_pricer import price_h2h
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats


def test_strong_vs_weak_high_prob():
    strong = Rating(mu=1800, phi=50)
    weak = Rating(mu=1500, phi=50)
    s_serve = PlayerServeStats(0.68, 0.42, 5000)
    w_serve = PlayerServeStats(0.58, 0.34, 5000)
    p = price_h2h(strong, weak, s_serve, w_serve, best_of=3)
    assert p > 0.70


def test_equal_players_half():
    r = Rating(mu=1600, phi=80)
    serve = PlayerServeStats(0.62, 0.38, 5000)
    p = price_h2h(r, r, serve, serve, best_of=3)
    assert abs(p - 0.5) < 1e-3


def test_bo5_extends_favorite():
    a = Rating(mu=1700, phi=80)
    b = Rating(mu=1550, phi=80)
    sa = PlayerServeStats(0.65, 0.40, 5000)
    sb = PlayerServeStats(0.60, 0.35, 5000)
    p_bo3 = price_h2h(a, b, sa, sb, best_of=3)
    p_bo5 = price_h2h(a, b, sa, sb, best_of=5)
    assert p_bo5 > p_bo3
