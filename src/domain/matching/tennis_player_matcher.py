"""Tennis player name matcher — Polymarket name → PlayerRating. Pure domain, no I/O.

Bridges Polymarket question player names (e.g. "Mannarino") to the
PlayerRating objects stored in TennisRatingsStore (keyed by player_name).

Strategy:
  1. Exact match (case-insensitive, normalized)
  2. Last-name-only match (unique surname in ratings)
  3. rapidfuzz partial_ratio > _FUZZY_THRESHOLD (if available)

All three tiers use _normalize() to handle diacritics/accents.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §5.2
"""
from __future__ import annotations

import unicodedata
from typing import Optional

from src.infrastructure.data.tennis_ratings_store import PlayerRating

# Fuzzy match threshold — same calibration reference as tennis_player_resolver.py:18
_FUZZY_THRESHOLD: float = 85.0


def _strip_accents(text: str) -> str:
    """Decompose then drop combining marks. Turkish dotless-i kept as i."""
    text = text.replace("ı", "i")  # Turkish ı → i
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    if not name:
        return ""
    return " ".join(_strip_accents(name).lower().split())


def _last_name(full_name: str) -> str:
    """Return the last space-separated token of a full name (normalized)."""
    parts = _normalize(full_name).split()
    return parts[-1] if parts else ""


def build_match_index(
    ratings: dict[str, PlayerRating],
) -> tuple[dict[str, PlayerRating], dict[str, list[PlayerRating]]]:
    """Build (by_normalized_full, by_last_name) lookup dicts from ratings.

    Args:
        ratings: dict keyed by player_id → PlayerRating.

    Returns:
        (by_full, by_last) — pre-built lookup dicts for fast matching.
    """
    by_full: dict[str, PlayerRating] = {}
    by_last: dict[str, list[PlayerRating]] = {}
    for pr in ratings.values():
        full_norm = _normalize(pr.player_name)
        last_norm = _last_name(pr.player_name)
        by_full[full_norm] = pr
        by_last.setdefault(last_norm, []).append(pr)
    return by_full, by_last


def match_player(
    name: str,
    ratings: dict[str, PlayerRating],
    *,
    by_full: dict[str, PlayerRating] | None = None,
    by_last: dict[str, list[PlayerRating]] | None = None,
) -> Optional[PlayerRating]:
    """Fuzzy match Polymarket player name → PlayerRating.

    Try:
    1. Exact match (case-insensitive, accent-stripped)
    2. Last-name-first match ("Mannarino" matches "Adrian Mannarino")
    3. rapidfuzz partial_ratio > 85 (if available)

    Args:
        name: Polymarket question player name (may be surname only or full).
        ratings: Full ratings dict (player_id → PlayerRating).
        by_full: Optional pre-built full-name index (avoids rebuilding each call).
        by_last: Optional pre-built last-name index.

    Returns:
        Matched PlayerRating or None.
    """
    if not name or not ratings:
        return None
    norm = _normalize(name)
    if not norm:
        return None

    # Build indexes lazily if not provided
    if by_full is None or by_last is None:
        by_full, by_last = build_match_index(ratings)

    # Tier 1: exact normalized full name
    exact = by_full.get(norm)
    if exact is not None:
        return exact

    # Tier 2: surname-only (must be unique)
    by_last_norm = by_last.get(norm, [])
    if len(by_last_norm) == 1:
        return by_last_norm[0]

    # Also handle compound last name ("Alcaraz" matching "Carlos Alcaraz Garfia")
    if len(norm.split()) == 1:
        partial_matches = [
            pr for pr in ratings.values()
            if norm in _normalize(pr.player_name).split()
        ]
        if len(partial_matches) == 1:
            return partial_matches[0]

    # Tier 3: rapidfuzz partial_ratio (graceful fallback if not installed)
    try:
        from rapidfuzz import fuzz as _fuzz  # noqa: PLC0415

        best: Optional[PlayerRating] = None
        best_score = 0.0
        for pr in ratings.values():
            score = float(_fuzz.partial_ratio(norm, _normalize(pr.player_name)))
            if score > best_score and score >= _FUZZY_THRESHOLD:
                best_score = score
                best = pr
        return best
    except ImportError:
        return None
