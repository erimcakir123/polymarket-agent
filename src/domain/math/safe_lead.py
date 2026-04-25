"""Bill James %99 safe lead formülü — NBA için kalibre."""
from __future__ import annotations

from math import sqrt


def is_mathematically_dead(
    deficit: int,
    clock_seconds: int,
    multiplier: float,
) -> bool:
    """Geri dönüşü matematiksel olarak imkânsız mı?

    deficit >= multiplier * sqrt(clock_seconds) → evet.
    deficit negatifse (biz öndeyiz) → False.
    """
    if deficit <= 0:
        return False
    if clock_seconds <= 0:
        return deficit > 0
    return deficit >= multiplier * sqrt(clock_seconds)


def is_spread_dead(
    margin_to_cover: float,
    seconds_remaining: int,
    multiplier: float = 0.861,
) -> bool:
    """NBA spread cover için Bill James %99 confidence.

    margin_to_cover: spread'i kapatmak için gereken puan.
    Pozitif = cover edemiyoruz. Negatif veya sıfır = zaten cover'dayız.
    """
    if margin_to_cover <= 0:
        return False
    if seconds_remaining <= 0:
        return margin_to_cover > 0
    return margin_to_cover >= multiplier * sqrt(seconds_remaining)


def is_total_dead(
    target_total: float,
    current_total: int,
    seconds_remaining: int,
    side: str,
    multiplier: float = 1.218,
) -> bool:
    """NBA totals için Poisson-based dead check.

    multiplier 1.218 = 0.861 × sqrt(2) — toplam variance daha yüksek.
    side="over": target'a yetişemeyeceksek dead.
    side="under": target'ı kesinlikle geçeceksek dead.
    """
    if side not in ("over", "under"):
        raise ValueError(f"side must be 'over' or 'under', got {side!r}")

    points_needed = target_total - current_total

    if seconds_remaining <= 0:
        if side == "over":
            return points_needed > 0
        else:
            return points_needed < 0

    threshold = multiplier * sqrt(seconds_remaining)

    if side == "over":
        return points_needed > threshold
    else:
        return -points_needed > threshold
