"""Bookmaker quality weights — single source of truth.

Used by src/odds_api.py and src/sports_data.py to apply quality-weighted
averaging when combining bookmaker probabilities. Sharp bookmakers
(Pinnacle, Betfair Exchange) get 3x the weight of standard soft books.

Tier rationale:
- Tier 1 (3.0): Sharp books that don't restrict winning customers. Their
  closing lines are the industry benchmark for "true" probability.
- Tier 2 (1.5): Reputable European books with high limits and decent lines.
- Tier 3 (1.0): All other bookmakers (default).
"""
from __future__ import annotations

# Tier 1: Sharp bookmakers (professional-grade)
_SHARP: frozenset[str] = frozenset({
    "pinnacle",
    "betfair_ex_eu",
    "betfair_ex_uk",
    "matchbook",
})

# Tier 2: Reputable bookmakers (high limits, European)
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
    """Normalize a bookmaker key or display name to match our tier keys.

    Handles both Odds API keys ('bet365', 'betfair_ex_eu') and ESPN display
    names ('Bet365', 'William Hill', 'Bet 365') by lowercasing and stripping spaces.
    """
    if not name:
        return ""
    return name.lower().replace(" ", "")


def get_bookmaker_weight(name: str) -> float:
    """Return the quality weight for a bookmaker key or display name.

    Unknown bookmakers default to STANDARD_WEIGHT (1.0).
    """
    key = _normalize(name)
    if key in _SHARP:
        return SHARP_WEIGHT
    if key in _REPUTABLE:
        return REPUTABLE_WEIGHT
    return STANDARD_WEIGHT


def is_sharp(name: str) -> bool:
    """Return True if the bookmaker is in the sharp tier."""
    return _normalize(name) in _SHARP
