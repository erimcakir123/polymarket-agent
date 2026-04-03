"""Parse Polymarket market slugs into sport code + team abbreviation tokens."""
from __future__ import annotations
from dataclasses import dataclass, field

from src.matching.sport_classifier import _SLUG_TO_CATEGORY


@dataclass
class SlugParts:
    sport: str | None = None
    team_tokens: list[str] = field(default_factory=list)
    raw_tokens: list[str] = field(default_factory=list)


def parse_slug(slug: str) -> SlugParts:
    """Parse a Polymarket slug into sport code and team abbreviation tokens.

    Standard format: "{sport}-{abbrev_a}-{abbrev_b}-{YYYY}-{MM}-{DD}"
    Returns SlugParts with sport code (if recognized) and team tokens.
    """
    if not slug:
        return SlugParts()

    parts = slug.lower().split("-")
    if not parts:
        return SlugParts()

    # Strip date tokens from the end (YYYY, MM, DD pattern)
    i = len(parts) - 1
    date_count = 0
    while i >= 0 and parts[i].isdigit() and date_count < 3:
        i -= 1
        date_count += 1
    clean = parts[:i + 1]

    if not clean:
        return SlugParts()

    # First token: sport code?
    sport = None
    team_start = 0
    if clean[0] in _SLUG_TO_CATEGORY:
        sport = clean[0]
        team_start = 1

    # Team tokens: everything after sport code, excluding noise
    _NOISE = {"will", "win", "beat", "vs", "the", "over", "against"}
    team_tokens = [
        t for t in clean[team_start:]
        if len(t) >= 2 and t not in _NOISE
    ]

    return SlugParts(
        sport=sport,
        team_tokens=team_tokens,
        raw_tokens=clean,
    )


def extract_slug_tokens(slug: str) -> set[str]:
    """Extract all meaningful tokens from slug (for abbreviation matching).

    Excludes: single-char tokens, pure digits.
    """
    return {
        p for p in slug.lower().split("-")
        if len(p) >= 2 and not p.isdigit()
    }
