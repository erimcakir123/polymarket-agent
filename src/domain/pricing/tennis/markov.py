"""Newton-Keller (2005) + O'Malley (2008) closed-form tennis formulas.

Bir oyuncunun serve point % (p) verilince:
- game_win_prob(p): standart oyun (deuce dahil)
- tiebreak_win_prob(p_a, p_b): 7-puan tiebreak
- set_win_prob: 6-game set (tiebreak dahil)
- match_win_prob: BO3 veya BO5

Tüm formüller saf math (domain), I/O yok. State DP @lru_cache ile.
"""
from __future__ import annotations

from functools import lru_cache
from math import comb


def game_win_prob(p: float) -> float:
    """Standart oyun (4 puan, deuce dahil) — O'Malley closed-form."""
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    q = 1.0 - p
    p4_0 = p ** 4
    p4_1 = 4 * p ** 4 * q
    p4_2 = 10 * p ** 4 * q * q
    deuce_reach = 20 * (p ** 3) * (q ** 3)
    p_deuce_win = p * p / (p * p + q * q)
    return p4_0 + p4_1 + p4_2 + deuce_reach * p_deuce_win


@lru_cache(maxsize=4096)
def _tiebreak_dp(p_a: float, p_b: float) -> float:
    """Tiebreak via memoized recursion. State: (A score, B score, point idx).

    ITF serve order: A serves point 1, B serves 2-3, A serves 4-5, ...
    A=B=6 reach edilirse "deuce" closed-form (margin-2 geometric).
    """
    def serve_by(idx: int) -> str:
        if idx == 0:
            return "A"
        return "A" if ((idx - 1) // 2) % 2 == 1 else "B"

    # 6-6 sonrası serve sequence A,B,B,A,A,B,B... → her 2-point block'ta her
    # taraf 1 puan serve eder. Block'ta A 2 puan alma olasılığı = p_a*(1-p_b).
    # Block'ta B 2 puan alma = (1-p_a)*p_b. Diğer durumlar net sıfır.
    p_a_block = p_a * (1.0 - p_b)
    p_b_block = (1.0 - p_a) * p_b
    denom = p_a_block + p_b_block
    p_a_wins_from_balance = p_a_block / denom if denom > 0 else 0.5

    def recurse(a: int, b: int, point_idx: int) -> float:
        if a >= 7 and a - b >= 2:
            return 1.0
        if b >= 7 and b - a >= 2:
            return 0.0
        # Both at 6+ AND equal score → closed-form deuce
        if a >= 6 and b >= 6 and a == b:
            return p_a_wins_from_balance
        server = serve_by(point_idx)
        p_a_wins_pt = p_a if server == "A" else (1.0 - p_b)
        win = recurse(a + 1, b, point_idx + 1)
        lose = recurse(a, b + 1, point_idx + 1)
        return p_a_wins_pt * win + (1.0 - p_a_wins_pt) * lose

    return recurse(0, 0, 0)


def tiebreak_win_prob(p_a: float, p_b: float) -> float:
    """7-puan tiebreak — O'Malley 2008."""
    return _tiebreak_dp(p_a, p_b)


@lru_cache(maxsize=4096)
def set_outcome_distribution(
    p_a_serve: float,
    p_b_serve: float,
) -> tuple[tuple[int, int, float], ...]:
    """Tek bir setin (a_games, b_games, probability) terminal dağılımı.

    Single source of truth — set_win_prob, totals_pricer ve totals_pricer
    içindeki _set_game_distribution buradan türer (DRY).

    Tiebreak 6-6: setin sonucu A 7-6 veya B 6-7. Tiebreak içi P(A) tiebreak_dp.
    """
    g_a = game_win_prob(p_a_serve)
    g_b = game_win_prob(p_b_serve)
    tb_p_a = _tiebreak_dp(p_a_serve, p_b_serve)

    outcomes: dict[tuple[int, int], float] = {}

    def recurse(a: int, b: int, server_idx: int, prob: float) -> None:
        if a == 6 and b <= 4:
            outcomes[(a, b)] = outcomes.get((a, b), 0.0) + prob
            return
        if b == 6 and a <= 4:
            outcomes[(a, b)] = outcomes.get((a, b), 0.0) + prob
            return
        if a == 7 and b == 5:
            outcomes[(7, 5)] = outcomes.get((7, 5), 0.0) + prob
            return
        if b == 7 and a == 5:
            outcomes[(5, 7)] = outcomes.get((5, 7), 0.0) + prob
            return
        if a == 6 and b == 6:
            outcomes[(7, 6)] = outcomes.get((7, 6), 0.0) + prob * tb_p_a
            outcomes[(6, 7)] = outcomes.get((6, 7), 0.0) + prob * (1.0 - tb_p_a)
            return
        a_serves = server_idx % 2 == 0
        p_a_wins_game = g_a if a_serves else (1.0 - g_b)
        recurse(a + 1, b, server_idx + 1, prob * p_a_wins_game)
        recurse(a, b + 1, server_idx + 1, prob * (1.0 - p_a_wins_game))

    recurse(0, 0, 0, 1.0)
    return tuple((a, b, p) for (a, b), p in sorted(outcomes.items()))


def set_win_prob(p_a_serve: float, p_b_serve: float) -> float:
    """6-game set — A ve B alterne serve. Tiebreak 6-6'da."""
    return sum(p for a, b, p in set_outcome_distribution(p_a_serve, p_b_serve) if a > b)


def match_win_prob(set_prob: float, best_of: int) -> float:
    """Best-of-N match probability from set probability (negative binomial)."""
    if best_of == 3:
        sets_to_win = 2
    elif best_of == 5:
        sets_to_win = 3
    else:
        raise ValueError(f"best_of must be 3 or 5, got {best_of}")
    p = set_prob
    q = 1.0 - p
    total = 0.0
    for n_losses in range(sets_to_win):
        total += comb(sets_to_win - 1 + n_losses, n_losses) * (p ** sets_to_win) * (q ** n_losses)
    return total
