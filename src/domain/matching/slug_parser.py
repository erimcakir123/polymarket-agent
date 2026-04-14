"""Polymarket market slug'ını sport code + team abbreviation token'larına ayırır.

Standart format: '{sport}-{abbrev_a}-{abbrev_b}-{YYYY}-{MM}-{DD}'
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.matching.sport_classifier import _SLUG_TO_CATEGORY

_NOISE_TOKENS: frozenset[str] = frozenset({"will", "win", "beat", "vs", "the", "over", "against"})


@dataclass
class SlugParts:
    sport: str | None = None
    team_tokens: list[str] = field(default_factory=list)
    raw_tokens: list[str] = field(default_factory=list)


def parse_slug(slug: str) -> SlugParts:
    """Slug'dan sport + team token'ları çıkar."""
    if not slug:
        return SlugParts()
    parts = slug.lower().split("-")
    if not parts:
        return SlugParts()

    # Sondan tarih token'larını (YYYY, MM, DD) sıyır
    i = len(parts) - 1
    date_count = 0
    while i >= 0 and parts[i].isdigit() and date_count < 3:
        i -= 1
        date_count += 1
    clean = parts[:i + 1]
    if not clean:
        return SlugParts()

    # İlk token sport code mu?
    sport: str | None = None
    team_start = 0
    if clean[0] in _SLUG_TO_CATEGORY:
        sport = clean[0]
        team_start = 1

    team_tokens = [
        t for t in clean[team_start:]
        if len(t) >= 2 and t not in _NOISE_TOKENS
    ]
    return SlugParts(sport=sport, team_tokens=team_tokens, raw_tokens=clean)


def extract_slug_tokens(slug: str) -> set[str]:
    """Slug'daki anlamlı token'ları çıkar (abbreviation match için)."""
    return {
        p for p in slug.lower().split("-")
        if len(p) >= 2 and not p.isdigit()
    }
