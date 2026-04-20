"""Market-flip exit (A3 sonrasi sadelesmis).

Market flip rule (elapsed ≥ 85%):
  effective_current < 0.50 → çık (market artık tarafımızda değil)

v1 verisi: 25 A-conf resolved trade → market_flip kural $110.78 tasarruf etti.
Elapsed gate eklenmesi early-match false positive'leri elediği için zorunlu.
"""
from __future__ import annotations

from src.models.position import Position

DEFAULT_MARKET_FLIP_THRESHOLD = 0.50
DEFAULT_MARKET_FLIP_ELAPSED_GATE = 0.85


def market_flip_exit(
    pos: Position,
    elapsed_pct: float,
    flip_threshold: float = DEFAULT_MARKET_FLIP_THRESHOLD,
    elapsed_gate: float = DEFAULT_MARKET_FLIP_ELAPSED_GATE,
) -> bool:
    """Market flip exit tetiklendi mi?

    Sadece elapsed ≥ gate AND effective_current < threshold durumunda aktif.
    Erken/orta maçta tetiklenmez (false positive elenir).
    """
    if elapsed_pct < elapsed_gate:
        return False
    # current_price zaten token-native. Owned side threshold altına düştüyse flip.
    return pos.current_price < flip_threshold
