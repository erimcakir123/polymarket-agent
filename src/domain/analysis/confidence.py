"""Bookmaker-derived confidence tiers A / B / C (TDD §6.2).

A = sharp book present (Pinnacle / Betfair Exchange)
B = bookmaker weight >= 5, standard book
C = insufficient data → entry blocked
"""
from __future__ import annotations


def derive_confidence(bm_weight: float | None, has_sharp: bool) -> str:
    """Bookmaker sinyal gücünden confidence tier çıkar."""
    if bm_weight is None or bm_weight < 5:
        return "C"
    if has_sharp:
        return "A"
    return "B"
