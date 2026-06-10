"""Glicko-2 rating system (Glickman 2013).

Domain layer — saf math, hiçbir I/O yok. Tennis maç tahmini için
PLOS One 2022 sport-bağımsız %73 doğruluk kanıtladı.

State variables:
- mu: oyuncu yeteneği (1500 = ortalama, log-scale)
- phi: rating deviation (350 = belirsiz, 30 = stabil)
- sigma: volatility (0.06 default, rating drift hızı)

Tüm hesaplar internal Glicko-2 scale (mu/173.7178) üzerinden yapılır.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

DEFAULT_RATING = 1500.0
DEFAULT_RD = 350.0
DEFAULT_VOL = 0.06
_SCALE = 173.7178
_TAU = 0.5
_EPSILON = 1e-6


@dataclass(frozen=True)
class Rating:
    mu: float = DEFAULT_RATING
    phi: float = DEFAULT_RD
    sigma: float = DEFAULT_VOL


def _g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / (math.pi * math.pi))


def _expected(mu: float, mu_j: float, phi_j: float) -> float:
    return 1.0 / (1.0 + math.exp(-_g(phi_j) * (mu - mu_j)))


def win_probability(player: Rating, opponent: Rating) -> float:
    """P(player beats opponent) — Glicko-2 internal scale."""
    mu_p = (player.mu - DEFAULT_RATING) / _SCALE
    mu_o = (opponent.mu - DEFAULT_RATING) / _SCALE
    phi_o = opponent.phi / _SCALE
    return _expected(mu_p, mu_o, phi_o)


def _new_volatility(sigma: float, phi: float, v: float, delta: float, tau: float) -> float:
    """Glickman illinois algorithm for new volatility."""
    a = math.log(sigma * sigma)
    delta_sq = delta * delta
    phi_sq = phi * phi

    def f(x: float) -> float:
        ex = math.exp(x)
        num = ex * (delta_sq - phi_sq - v - ex)
        den = 2.0 * (phi_sq + v + ex) ** 2
        return num / den - (x - a) / (tau * tau)

    A = a
    if delta_sq > phi_sq + v:
        B = math.log(delta_sq - phi_sq - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        B = a - k * tau

    fa = f(A)
    fb = f(B)
    while abs(B - A) > _EPSILON:
        C = A + (A - B) * fa / (fb - fa)
        fc = f(C)
        if fc * fb <= 0:
            A = B
            fa = fb
        else:
            fa = fa / 2.0
        B = C
        fb = fc
    return math.exp(A / 2.0)


def update_rating(
    rating: Rating,
    opponents: list[Rating],
    outcomes: list[float],
    tau: float = _TAU,
) -> Rating:
    """One Glicko-2 update with N games.

    outcomes: 1.0=win, 0.0=loss. No games → only RD drifts upward.
    """
    mu = (rating.mu - DEFAULT_RATING) / _SCALE
    phi = rating.phi / _SCALE
    sigma = rating.sigma

    if not opponents:
        phi_star = math.sqrt(phi * phi + sigma * sigma)
        return replace(rating, phi=phi_star * _SCALE)

    opp_mu = [(o.mu - DEFAULT_RATING) / _SCALE for o in opponents]
    opp_phi = [o.phi / _SCALE for o in opponents]
    g_vals = [_g(p) for p in opp_phi]
    e_vals = [_expected(mu, opp_mu[i], opp_phi[i]) for i in range(len(opponents))]

    v = 1.0 / sum(g_vals[i] ** 2 * e_vals[i] * (1.0 - e_vals[i]) for i in range(len(opponents)))
    delta = v * sum(g_vals[i] * (outcomes[i] - e_vals[i]) for i in range(len(opponents)))

    new_sigma = _new_volatility(sigma, phi, v, delta, tau)
    phi_star = math.sqrt(phi * phi + new_sigma * new_sigma)
    new_phi = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / v)
    new_mu = mu + new_phi * new_phi * sum(
        g_vals[i] * (outcomes[i] - e_vals[i]) for i in range(len(opponents))
    )

    return Rating(
        mu=new_mu * _SCALE + DEFAULT_RATING,
        phi=new_phi * _SCALE,
        sigma=new_sigma,
    )


def fit_ratings(results: list[tuple[str, str]]) -> dict[str, Rating]:
    """Kronolojik (kazanan, kaybeden) çiftlerinden Glicko fit (PLAN-DATA1 DRY).

    build_tennis_ratings + sim/araştırma scriptlerinin ortak döngüsü — saf fonksiyon.
    Çiftler ÇAĞIRAN tarafından tarihe göre sıralanmış olmalı.
    """
    ratings: dict[str, Rating] = {}
    for winner, loser in results:
        w = ratings.get(winner, Rating())
        loser_r = ratings.get(loser, Rating())
        ratings[winner] = update_rating(w, [loser_r], [1.0])
        ratings[loser] = update_rating(loser_r, [w], [0.0])
    return ratings
