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
