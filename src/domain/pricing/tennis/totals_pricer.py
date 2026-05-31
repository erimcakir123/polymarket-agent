"""Total games over/under — Markov game/set DP ile beklenen + dağılım.

Bir set kaç oyun sürer? p_a ve p_b'e bağlı. Düşük hold → çok break → kısa setler.
Yüksek hold → uzun setler + tiebreak. Normal approx ile over/under fiyatı.
"""
from __future__ import annotations

import math
from functools import lru_cache
from math import comb

from src.domain.pricing.tennis.markov import game_win_prob, set_win_prob


@lru_cache(maxsize=4096)
def _set_game_distribution(p_a: float, p_b: float) -> tuple[tuple[int, float], ...]:
    """Bir setin toplam oyun dağılımı (frozen tuple for hashability)."""
    g_a = game_win_prob(p_a)
    g_b = game_win_prob(p_b)
    dist: dict[int, float] = {}

    def recurse(a: int, b: int, server_idx: int, prob: float) -> None:
        if a == 6 and b <= 4:
            total = a + b
            dist[total] = dist.get(total, 0.0) + prob
            return
        if b == 6 and a <= 4:
            total = a + b
            dist[total] = dist.get(total, 0.0) + prob
            return
        if a == 7 and b == 5:
            dist[12] = dist.get(12, 0.0) + prob
            return
        if b == 7 and a == 5:
            dist[12] = dist.get(12, 0.0) + prob
            return
        if a == 6 and b == 6:
            # Tiebreak counted as one extra "game" → 13 total
            dist[13] = dist.get(13, 0.0) + prob
            return
        a_serves = server_idx % 2 == 0
        p_a_wins_game = g_a if a_serves else (1.0 - g_b)
        recurse(a + 1, b, server_idx + 1, prob * p_a_wins_game)
        recurse(a, b + 1, server_idx + 1, prob * (1.0 - p_a_wins_game))

    recurse(0, 0, 0, 1.0)
    return tuple(sorted(dist.items()))


def _expected_games_per_set(p_a: float, p_b: float) -> float:
    dist = _set_game_distribution(p_a, p_b)
    return sum(g * pr for g, pr in dist)


def _variance_games_per_set(p_a: float, p_b: float, mean: float) -> float:
    dist = _set_game_distribution(p_a, p_b)
    return sum((g - mean) ** 2 * pr for g, pr in dist)


def _expected_sets(p_a: float, p_b: float, best_of: int) -> float:
    sp = set_win_prob(p_a, p_b)
    if best_of == 3:
        e_sets = 2 * (sp ** 2 + (1 - sp) ** 2) + 3 * (
            2 * sp ** 2 * (1 - sp) + 2 * sp * (1 - sp) ** 2
        )
    elif best_of == 5:
        e_sets = 0.0
        for k in range(3):
            n = 3 + k
            p_a_path = comb(n - 1, k) * sp ** 3 * (1 - sp) ** k
            p_b_path = comb(n - 1, k) * (1 - sp) ** 3 * sp ** k
            e_sets += n * (p_a_path + p_b_path)
    else:
        raise ValueError(f"best_of must be 3 or 5, got {best_of}")
    return e_sets


def expected_total_games(p_a: float, p_b: float, best_of: int) -> float:
    """E[total games] = E[sets] * E[games per set]."""
    return _expected_sets(p_a, p_b, best_of) * _expected_games_per_set(p_a, p_b)


def price_total_over(
    p_a: float,
    p_b: float,
    best_of: int,
    line: float,
    side: str = "over",
) -> float:
    """P(total games > line) — normal approximation (mean + variance)."""
    mean_per_set = _expected_games_per_set(p_a, p_b)
    var_per_set = _variance_games_per_set(p_a, p_b, mean_per_set)
    e_sets = _expected_sets(p_a, p_b, best_of)
    total_mean = e_sets * mean_per_set
    total_std = math.sqrt(e_sets * var_per_set)
    if total_std < 1e-6:
        p_over = 1.0 if total_mean > line else 0.0
    else:
        z = (line - total_mean) / total_std
        p_over = 0.5 * math.erfc(z / math.sqrt(2.0))
    if side == "under":
        return 1.0 - p_over
    return p_over
