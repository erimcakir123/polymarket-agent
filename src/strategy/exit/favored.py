"""FAV (favored) promote/demote (TDD §6.13) — pure state transition.

Holding sırasında dinamik durum değişikliği. favored=True olan pozisyonlar
A-conf hold mantığına tabi olur (graduated SL'den muaf, market_flip elapsed gate'li).

v1 verisi: 5 favored trade = +$42.90, %100 WR. Kural korunacak.
"""
from __future__ import annotations

from src.models.position import Position

DEFAULT_PROMOTE_EFF_PRICE = 0.65
DEFAULT_DEMOTE_EFF_PRICE = 0.65
DEFAULT_CONF_REQUIRED: frozenset[str] = frozenset({"A", "B"})


def should_promote(
    pos: Position,
    promote_threshold: float = DEFAULT_PROMOTE_EFF_PRICE,
    conf_required: frozenset[str] = DEFAULT_CONF_REQUIRED,
) -> bool:
    """Pozisyon favored'a promote edilmeli mi?

    Koşul: favored=False AND effective_current >= threshold AND confidence ∈ {A, B}
    """
    if pos.favored:
        return False
    if pos.confidence not in conf_required:
        return False
    # current_price zaten token-native.
    return pos.current_price >= promote_threshold


def should_demote(
    pos: Position,
    demote_threshold: float = DEFAULT_DEMOTE_EFF_PRICE,
) -> bool:
    """Favored pozisyon demote edilmeli mi?

    Koşul: favored=True AND effective_current < threshold
    """
    if not pos.favored:
        return False
    # current_price zaten token-native.
    return pos.current_price < demote_threshold
