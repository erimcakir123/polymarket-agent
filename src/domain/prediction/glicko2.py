"""Glicko-2 rating system — pure math, no I/O.

Reference: http://www.glicko.net/glicko/glicko2.pdf (M. Glickman, 2013)

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §4
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Glickman scale factor (rating ↔ mu transform)
_SCALE = 173.7178


@dataclass(frozen=True)
class Glicko2Rating:
    """Player rating with uncertainty.

    rating: skill estimate (1500 = average)
    rd: rating deviation (lower = more certain)
    volatility: how erratic recent performance is
    """

    rating: float
    rd: float
    volatility: float


def expected_score(player: Glicko2Rating, opponent: Glicko2Rating) -> float:
    """Probability that player beats opponent. Returns in [0, 1]."""
    mu_p = (player.rating - 1500) / _SCALE
    mu_o = (opponent.rating - 1500) / _SCALE
    phi_o = opponent.rd / _SCALE
    g_phi = 1.0 / math.sqrt(1.0 + 3.0 * phi_o * phi_o / (math.pi**2))
    return 1.0 / (1.0 + math.exp(-g_phi * (mu_p - mu_o)))


def update_rating(
    player: Glicko2Rating,
    results: list[tuple[Glicko2Rating, float]],
    tau: float = 0.5,
) -> Glicko2Rating:
    """Update player rating after a series of matches.

    Args:
        player: current rating
        results: list of (opponent_rating, score) where score in {0.0, 0.5, 1.0}
        tau: system constant controls volatility change (0.3-1.2)

    Returns:
        new Glicko2Rating
    """
    if not results:
        # No matches — increase RD due to inactivity
        phi = player.rd / _SCALE
        sigma = player.volatility
        new_phi = math.sqrt(phi * phi + sigma * sigma)
        return Glicko2Rating(
            rating=player.rating,
            rd=min(new_phi * _SCALE, 350.0),
            volatility=sigma,
        )

    # Step 2: convert to Glicko-2 scale
    mu = (player.rating - 1500) / _SCALE
    phi = player.rd / _SCALE
    sigma = player.volatility

    # Step 3: compute v (estimated variance)
    v_inv = 0.0
    for opp_rating, _score in results:
        mu_j = (opp_rating.rating - 1500) / _SCALE
        phi_j = opp_rating.rd / _SCALE
        g_j = 1.0 / math.sqrt(1.0 + 3.0 * phi_j * phi_j / (math.pi**2))
        E_j = 1.0 / (1.0 + math.exp(-g_j * (mu - mu_j)))
        v_inv += (g_j * g_j) * E_j * (1.0 - E_j)
    v = 1.0 / v_inv

    # Step 4: compute delta
    delta_sum = 0.0
    for opp_rating, score in results:
        mu_j = (opp_rating.rating - 1500) / _SCALE
        phi_j = opp_rating.rd / _SCALE
        g_j = 1.0 / math.sqrt(1.0 + 3.0 * phi_j * phi_j / (math.pi**2))
        E_j = 1.0 / (1.0 + math.exp(-g_j * (mu - mu_j)))
        delta_sum += g_j * (score - E_j)
    delta = v * delta_sum

    # Step 5: compute new volatility (iterative Illinois algorithm)
    a = math.log(sigma * sigma)

    def _f(x: float) -> float:
        e_x = math.exp(x)
        num = e_x * (delta * delta - phi * phi - v - e_x)
        den = 2.0 * (phi * phi + v + e_x) ** 2
        return num / den - (x - a) / (tau * tau)

    eps = 1e-6
    A = a
    if delta * delta > phi * phi + v:
        B = math.log(delta * delta - phi * phi - v)
    else:
        k = 1
        while _f(a - k * tau) < 0:
            k += 1
        B = a - k * tau

    fA = _f(A)
    fB = _f(B)
    while abs(B - A) > eps:
        C = A + (A - B) * fA / (fB - fA)
        fC = _f(C)
        if fC * fB <= 0:
            A = B
            fA = fB
        else:
            fA = fA / 2.0
        B = C
        fB = fC

    new_sigma = math.exp(A / 2.0)

    # Step 6: pre-rating period RD
    phi_star = math.sqrt(phi * phi + new_sigma * new_sigma)

    # Step 7: new RD and rating
    new_phi = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / v)
    new_mu = mu + new_phi * new_phi * delta_sum

    return Glicko2Rating(
        rating=new_mu * _SCALE + 1500,
        rd=new_phi * _SCALE,
        volatility=new_sigma,
    )
