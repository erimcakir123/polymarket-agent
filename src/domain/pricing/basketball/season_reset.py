"""Sezon başı rating mean-reversion — FiveThirtyEight paterni.

Yeni sezonda takım roster'ı önemli ölçüde değişebilir (trade, sakatlık,
emeklilik, draft). Tarihsel rating'leri tam carry-over yapmak yanlış
tahminlere yol açar. Çözüm: %25 ortalamaya çekiş.

  post = pre × (1 - 0.25) + DEFAULT_RATING × 0.25

Domain layer — saf math, I/O yok.
"""
from __future__ import annotations

from dataclasses import replace

from src.domain.pricing.basketball.team_elo import DEFAULT_RATING, EloRating

REVERT_FRACTION = 0.25


def revert_to_mean(rating: EloRating) -> EloRating:
    """Sezon başında rating'i %25 ortalamaya çek (games sayacı korunur)."""
    new_rating = rating.rating * (1 - REVERT_FRACTION) + DEFAULT_RATING * REVERT_FRACTION
    return replace(rating, rating=new_rating)
