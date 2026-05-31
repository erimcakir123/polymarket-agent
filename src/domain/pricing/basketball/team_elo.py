"""Klasik Elo rating system — takim gucu, home advantage dahil.

Domain layer — saf math, hicbir I/O yok. FiveThirtyEight pattern'i:
  E_home = 1 / (1 + 10^((R_away - R_home - H) / 400))
  R'_home = R_home + K * (S_home - E_home)

S_home in {0, 1} (loss/win). K-factor lig-basina config'den verilir
(genellikle 20). H = home advantage (NBA ~100, WNBA ~95, NCAAB ~130).
"""
from __future__ import annotations

from dataclasses import dataclass, replace

DEFAULT_RATING = 1500.0
_ELO_DIVISOR = 400.0


@dataclass(frozen=True)
class EloRating:
    rating: float = DEFAULT_RATING
    games: int = 0


def expected_win_prob(
    home: EloRating, away: EloRating, home_advantage: float,
) -> float:
    """P(home wins) — klasik Elo logistic, home_advantage rating puani olarak eklenir."""
    diff = away.rating - home.rating - home_advantage
    return 1.0 / (1.0 + 10.0 ** (diff / _ELO_DIVISOR))


def update_elo(
    home: EloRating, away: EloRating,
    home_won: bool, k_factor: float, home_advantage: float,
) -> tuple[EloRating, EloRating]:
    """Mac sonucundan yeni Elo'lar uret. Sum-zero (toplam puan korunur)."""
    e_home = expected_win_prob(home, away, home_advantage)
    s_home = 1.0 if home_won else 0.0
    delta = k_factor * (s_home - e_home)
    new_home = replace(home, rating=home.rating + delta, games=home.games + 1)
    new_away = replace(away, rating=away.rating - delta, games=away.games + 1)
    return new_home, new_away
