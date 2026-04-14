"""FAV (favored) promote/demote (TDD §6.13) — pure state transition.

Holding sırasında dinamik durum değişikliği. favored=True olan pozisyonlar
A-conf hold mantığına tabi olur (graduated SL'den muaf, market_flip elapsed gate'li).

v1 verisi: 5 favored trade = +$42.90, %100 WR. Kural korunacak.
"""
from __future__ import annotations

from src.models.position import Position, effective_price

DEFAULT_PROMOTE_EFF_PRICE = 0.65
DEFAULT_DEMOTE_EFF_PRICE = 0.65
DEFAULT_CONF_REQUIRED: frozenset[str] = frozenset({"A", "B"})


def should_promote(
    pos: Position,
    promote_threshold: float = DEFAULT_PROMOTE_EFF_PRICE,
    conf_required: frozenset[str] = DEFAULT_CONF_REQUIRED,
) -> bool:
    """Pozisyon favored'a promote edilmeli mi?

    Koşul: favored=False AND volatility_swing=False AND effective_current >= threshold
           AND confidence ∈ {A, B}
    """
    if pos.favored or pos.volatility_swing:
        return False
    if pos.confidence not in conf_required:
        return False
    eff = effective_price(pos.current_price, pos.direction)
    return eff >= promote_threshold


def should_demote(
    pos: Position,
    demote_threshold: float = DEFAULT_DEMOTE_EFF_PRICE,
) -> bool:
    """Favored pozisyon demote edilmeli mi?

    Koşul: favored=True AND effective_current < threshold
    """
    if not pos.favored:
        return False
    eff = effective_price(pos.current_price, pos.direction)
    return eff < demote_threshold
