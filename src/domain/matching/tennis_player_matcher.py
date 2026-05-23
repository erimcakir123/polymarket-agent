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

# Max token-count difference between input and target for a fuzzy match to be
# considered. Guards against prefix-substring false positives where the input
# is a strict prefix of a longer real name (e.g., Polymarket "Juan Martin"
# matching "Juan Martin del Potro" via partial_ratio=100). Typos within ±1
# token (e.g., "Sinnerr" vs "Jannik Sinner", "Carlos Alcaraz" vs "Carlos
# Alcaraz Garfia") remain reachable.
_MAX_FUZZY_TOKEN_DIFF: int = 1


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
    tour: str = "atp",
) -> tuple[dict[str, PlayerRating], dict[str, list[PlayerRating]]]:
    """Build (by_normalized_full, by_last_name) lookup dicts filtered to one tour.

    Only players whose `tour` field matches the argument are included. Prevents
    cross-tour name collisions (e.g. "Williams" exists in both ATP and WTA).

    Args:
        ratings: dict keyed by player_id → PlayerRating.
        tour: "atp" or "wta" — only players with matching `tour` are indexed.

    Returns:
        (by_full, by_last) — pre-built lookup dicts for fast matching.
    """
    by_full: dict[str, PlayerRating] = {}
    by_last: dict[str, list[PlayerRating]] = {}
    for pr in ratings.values():
        if pr.tour != tour:
            continue
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
    tour: str = "atp",
) -> Optional[PlayerRating]:
    """Fuzzy match Polymarket player name → PlayerRating, scoped to one tour.

    Try:
    1. Exact match (case-insensitive, accent-stripped)
    2. Last-name-first match ("Mannarino" matches "Adrian Mannarino")
    3. rapidfuzz partial_ratio > 85 (if available)

    All tiers operate ONLY on players where `tour` matches the argument. The
    `by_full` / `by_last` indexes are already tour-filtered (built via
    `build_match_index(ratings, tour=...)`); the compound + fuzzy scans over
    `ratings.values()` are filtered inline to keep symmetry.

    Args:
        name: Polymarket question player name (may be surname only or full).
        ratings: Full ratings dict (player_id → PlayerRating).
        by_full: Optional pre-built full-name index (avoids rebuilding each call).
        by_last: Optional pre-built last-name index.
        tour: "atp" or "wta" — scopes lookup; default "atp" preserves legacy callers.

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
        by_full, by_last = build_match_index(ratings, tour=tour)

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
            if pr.tour == tour and norm in _normalize(pr.player_name).split()
        ]
        if len(partial_matches) == 1:
            return partial_matches[0]

    # Tier 3: rapidfuzz partial_ratio (graceful fallback if not installed)
    try:
        from rapidfuzz import fuzz as _fuzz  # noqa: PLC0415

        input_tokens = norm.split()
        best: Optional[PlayerRating] = None
        best_score = 0.0
        for pr in ratings.values():
            if pr.tour != tour:
                continue
            target_norm = _normalize(pr.player_name)
            target_tokens = target_norm.split()
            # Guard 1: reject prefix-substring collisions (e.g. "Juan Martin"
            # vs "Juan Martin del Potro"). Token count must be close.
            if abs(len(input_tokens) - len(target_tokens)) > _MAX_FUZZY_TOKEN_DIFF:
                continue
            # Guard 2: each input token must have a strong match somewhere
            # in target tokens (e.g. "Juan Martin" vs "Dan Martin" fails on
            # "juan" → none of {dan, martin} reach threshold).
            if not all(
                max(
                    (float(_fuzz.ratio(it, tt)) for tt in target_tokens),
                    default=0.0,
                )
                >= _FUZZY_THRESHOLD
                for it in input_tokens
            ):
                continue
            score = float(_fuzz.partial_ratio(norm, target_norm))
            if score > best_score and score >= _FUZZY_THRESHOLD:
                best_score = score
                best = pr
        return best
    except ImportError:
        return None
