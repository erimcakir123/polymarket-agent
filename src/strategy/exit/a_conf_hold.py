"""A-conf strong-entry hold-to-resolve davranışı (TDD §6.9).

Koşul: pos.confidence == 'A' AND effective_entry ≥ 60¢.

A-conf hold pozisyonları:
  - Graduated SL atlanır (erken/orta maçta)
  - Never-in-profit guard atlanır
  - Hold revocation atlanır
  - SADECE scale-out + near-resolve + market-flip (elapsed ≥ %85) aktif

Market flip rule (elapsed ≥ 85%):
  effective_current < 0.50 → çık (market artık tarafımızda değil)

v1 verisi: 25 A-conf resolved trade → market_flip kural $110.78 tasarruf etti.
Elapsed gate eklenmesi early-match false positive'leri elediği için zorunlu.
"""
from __future__ import annotations

from src.models.position import Position, effective_price

DEFAULT_MIN_ENTRY_PRICE = 0.60
DEFAULT_MARKET_FLIP_THRESHOLD = 0.50
DEFAULT_MARKET_FLIP_ELAPSED_GATE = 0.85


def is_a_conf_hold(pos: Position, min_entry_price: float = DEFAULT_MIN_ENTRY_PRICE) -> bool:
    """Pozisyon A-conf strong-entry hold'a tabi mi?"""
    eff_entry = effective_price(pos.entry_price, pos.direction)
    return pos.confidence == "A" and eff_entry >= min_entry_price


def market_flip_exit(
    pos: Position,
    elapsed_pct: float,
    flip_threshold: float = DEFAULT_MARKET_FLIP_THRESHOLD,
    elapsed_gate: float = DEFAULT_MARKET_FLIP_ELAPSED_GATE,
) -> bool:
    """Market flip exit tetiklendi mi? (A-conf hold pozisyonları için).

    Sadece elapsed ≥ gate AND effective_current < threshold durumunda aktif.
    Erken/orta maçta tetiklenmez (false positive elenir).
    """
    if elapsed_pct < elapsed_gate:
        return False
    eff_current = effective_price(pos.current_price, pos.direction)
    return eff_current < flip_threshold
