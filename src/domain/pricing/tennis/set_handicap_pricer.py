"""Set handicap pricer — set sequence Markov.

Multiclass set-score distribution: her geçerli skor (BO3: 2-0/2-1/1-2/0-2;
BO5: 3-0/.../0-3) için marjinal olasılık. Handicap olasılığı bu dağılımdan
toplanır.

set_prob: ilgili oyuncunun tek set kazanma olasılığı (Markov'dan gelir).
"""
from __future__ import annotations


def set_score_distribution(set_prob: float, best_of: int) -> dict[tuple[int, int], float]:
    """Tüm (a_sets, b_sets) outcome'larının olasılığı."""
    p = set_prob
    q = 1.0 - p
    if best_of == 3:
        return {
            (2, 0): p * p,
            (2, 1): 2 * p * p * q,
            (1, 2): 2 * p * q * q,
            (0, 2): q * q,
        }
    if best_of == 5:
        return {
            (3, 0): p ** 3,
            (3, 1): 3 * p ** 3 * q,
            (3, 2): 6 * p ** 3 * q * q,
            (2, 3): 6 * p * p * q ** 3,
            (1, 3): 3 * p * q ** 3,
            (0, 3): q ** 3,
        }
    raise ValueError(f"best_of must be 3 or 5, got {best_of}")


def price_set_handicap(set_prob: float, best_of: int, handicap: float) -> float:
    """P(player'ın etkin set skoru rakipten yüksek). handicap A perspektifinden.

    handicap > 0 → A'ya verilir.
    handicap < 0 → A'dan alınır (favori, kesin margin gerekir).
    Örn: -1.5 → A 2 set farkla kazanmalı (2-0 veya 3-0/3-1).
    """
    dist = set_score_distribution(set_prob, best_of)
    total = 0.0
    for (a, b), prob in dist.items():
        if a + handicap > b:
            total += prob
    return total
