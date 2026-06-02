"""Tennis model anchor — Polymarket market_type → pricer dispatch.

Strategy layer. Anchor source override (sport_rules.submarket_anchor="model").
Eksik veride None (caller bookmaker'a düşer veya skip eder).
"""
from __future__ import annotations

from src.domain.pricing.tennis.first_set_pricer import price_first_set_winner
from src.domain.pricing.tennis.h2h_pricer import price_h2h
from src.domain.pricing.tennis.markov import set_win_prob
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats, point_win_on_serve
from src.domain.pricing.tennis.set_handicap_pricer import price_set_handicap
from src.domain.pricing.tennis.set_totals_pricer import price_set_total_over
from src.domain.pricing.tennis.totals_pricer import price_total_over


def _resolve_serve_with_fallback(
    serve_by_surface: dict[str, PlayerServeStats],
    surface: str,
) -> PlayerServeStats | None:
    """Hedef surface yoksa diger surface'lerden n_points-agirlikli ortalama.

    Sackmann CSV'lerinde Grass %89, Clay %34, Hard %20 oyuncuda surface-spesifik
    serve verisi eksik (cogu oyuncu sadece Hard veya Clay maclar oynamis). Surface
    eksikse modeli pas etmek yerine, oyuncunun diger surface'lerdeki ortalamasini
    kullan — Glicko rating zaten "overall fallback" yapiyor; serve icin paralel.
    """
    direct = serve_by_surface.get(surface)
    if direct is not None and direct.n_points > 0:
        return direct
    others = [s for k, s in serve_by_surface.items() if k != surface and s.n_points > 0]
    if not others:
        return direct  # ya None ya da 0-point entry
    total_n = sum(s.n_points for s in others)
    return PlayerServeStats(
        serve_pts_won_pct=sum(s.serve_pts_won_pct * s.n_points for s in others) / total_n,
        return_pts_won_pct=sum(s.return_pts_won_pct * s.n_points for s in others) / total_n,
        n_points=total_n,
    )


def compute_model_anchor(
    market_type: str,
    a_snapshot: PlayerSnapshot,
    b_snapshot: PlayerSnapshot,
    surface: str,
    best_of: int,
    line: float | None = None,
    handicap: float | None = None,
    glicko_weight: float = 0.6,
) -> float | None:
    """P(YES) from model. Eksik veri (surface yok, market_type bilinmiyor) → None."""
    a_serve = _resolve_serve_with_fallback(a_snapshot.serve_by_surface, surface)
    b_serve = _resolve_serve_with_fallback(b_snapshot.serve_by_surface, surface)
    if a_serve is None or b_serve is None:
        return None
    p_a = point_win_on_serve(a_serve, b_serve)
    p_b = point_win_on_serve(b_serve, a_serve)

    mt = market_type.lower()
    if mt in ("moneyline", "h2h"):
        return price_h2h(
            a_snapshot.rating, b_snapshot.rating, a_serve, b_serve,
            best_of=best_of, glicko_weight=glicko_weight,
        )
    if mt == "tennis_set_handicap" and handicap is not None:
        set_p = set_win_prob(p_a, p_b)
        return price_set_handicap(set_p, best_of, handicap)
    if mt in ("tennis_match_totals", "tennis_first_set_totals") and line is not None:
        return price_total_over(p_a, p_b, best_of, line)
    if mt == "tennis_first_set_winner":
        return price_first_set_winner(p_a, p_b)
    if mt == "tennis_set_totals" and line is not None:
        set_p = set_win_prob(p_a, p_b)
        return price_set_total_over(set_p, best_of, line)
    return None
