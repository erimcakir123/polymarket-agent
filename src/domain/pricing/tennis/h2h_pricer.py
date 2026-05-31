"""H2H (match winner) pricer — Glicko + serve % blend.

Glicko %73 doğruluk veriyor (PLOS One 2022). Serve % match dynamics ekliyor.
Blend: glicko_weight * Glicko + (1-glicko_weight) * Markov. Ağırlık entegrasyon
sırasında config.yaml'dan geçirilir; domain'de default 0.6.
"""
from __future__ import annotations

from src.domain.pricing.tennis.glicko import Rating, win_probability
from src.domain.pricing.tennis.markov import match_win_prob, set_win_prob
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats, point_win_on_serve


def price_h2h(
    a_rating: Rating,
    b_rating: Rating,
    a_serve: PlayerServeStats,
    b_serve: PlayerServeStats,
    best_of: int,
    glicko_weight: float = 0.6,
) -> float:
    """P(A beats B). Returns P(YES) for the "A wins" market."""
    glicko_p = win_probability(a_rating, b_rating)

    p_a = point_win_on_serve(a_serve, b_serve)
    p_b = point_win_on_serve(b_serve, a_serve)
    set_p = set_win_prob(p_a, p_b)
    serve_p = match_win_prob(set_p, best_of=best_of)

    return glicko_weight * glicko_p + (1.0 - glicko_weight) * serve_p
