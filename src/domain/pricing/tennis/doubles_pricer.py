"""Doubles match pricer — partner rating birleştirme + singles pricer paralel.

Domain layer — saf math, I/O yok. Singles glicko.py pattern'ini taklit eder.
Doubles'da takım = 2 oyuncu birleşimi. Rating birleştirme:
  mu_team = (mu_p1 + mu_p2) / 2
  phi_team = sqrt(phi_p1^2 + phi_p2^2) / 2  (combined uncertainty)

Bu basit blend Sackmann doubles datasını anlamak için yeterli. Daha
gelişmiş modelleme (oyuncu × partner sinerji) ileri faz.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.domain.pricing.tennis.glicko import Rating, win_probability


@dataclass(frozen=True)
class DoublesTeam:
    """Doubles takımı — combined rating."""
    rating: Rating


def combine_partner_ratings(p1: Rating, p2: Rating) -> Rating:
    """İki oyuncudan takım rating üret. mu=average, phi=combined uncertainty."""
    mu = (p1.mu + p2.mu) / 2.0
    # Combined std (independent uncertainty): sqrt(phi1^2 + phi2^2) / 2
    phi = math.sqrt(p1.phi * p1.phi + p2.phi * p2.phi) / 2.0
    sigma = (p1.sigma + p2.sigma) / 2.0
    return Rating(mu=mu, phi=phi, sigma=sigma)


def price_doubles_h2h(team_a: DoublesTeam, team_b: DoublesTeam) -> float:
    """P(team_a wins). Singles glicko.win_probability ile aynı."""
    return win_probability(team_a.rating, team_b.rating)
