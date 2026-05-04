"""Bookmaker quality weights — tek kaynak (TDD §6.1).

Tier 1 (Sharp, 3.0×): Pinnacle, Betfair Exchange, Matchbook — profesyonel kesim.
Tier 2 (Reputable, 1.5×): Bet365, William Hill, Unibet, Betclic, Marathon.
Tier 3 (Standard, 1.0×): Diğer hepsi.
"""
from __future__ import annotations

# Tier 1 — sharp bookmakers
_SHARP: frozenset[str] = frozenset({
    "pinnacle",
    "betfair_ex_eu",
    "betfair_ex_uk",
    "betfair_ex_au",
    "matchbook",
    "smarkets",
})

# Tier 2 — reputable bookmakers (yüksek limit, Avrupa)
_REPUTABLE: frozenset[str] = frozenset({
    "bet365",
    "williamhill",
    "unibet_eu",
    "unibet_uk",
    "betclic",
    "marathonbet",
})

SHARP_WEIGHT = 3.0
REPUTABLE_WEIGHT = 1.5
STANDARD_WEIGHT = 1.0


def _normalize(name: str) -> str:
    """Odds API key veya display name → tier key ('bet365', 'betfair_ex_eu')."""
    if not name:
        return ""
    return name.lower().replace(" ", "")


def get_bookmaker_weight(name: str) -> float:
    """Bookmaker için quality weight. Bilinmeyen → STANDARD (1.0)."""
    key = _normalize(name)
    if key in _SHARP:
        return SHARP_WEIGHT
    if key in _REPUTABLE:
        return REPUTABLE_WEIGHT
    return STANDARD_WEIGHT


# Exchange bookmaker'lar — vig yok, 1/price ≈ gerçek olasılık.
# Vig normalize uygulanmamalı (TDD §6.1).
_EXCHANGE: frozenset[str] = frozenset({
    "betfair_ex_eu",
    "betfair_ex_uk",
    "betfair_ex_au",
    "matchbook",
    "smarkets",
})


def is_sharp(name: str) -> bool:
    """Sharp tier (Pinnacle / Betfair Ex / Matchbook) mi?"""
    return _normalize(name) in _SHARP


def is_exchange(name: str) -> bool:
    """Exchange bookmaker mı? (vig yok, normalize atlanmalı)."""
    return _normalize(name) in _EXCHANGE
