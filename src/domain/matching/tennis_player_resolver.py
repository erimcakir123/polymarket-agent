"""Tennis player name resolver - pure domain, no I/O.

Reconciles names across Polymarket (slug surnames), ESPN (full names with
diacritics), and Sackmann (canonical full names). Uses normalize/fuzzy.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Iterable

from rapidfuzz import fuzz


_FUZZY_TOKEN_SORT_THRESHOLD = 0.85


@dataclass(frozen=True)
class PlayerRecord:
    sackmann_id: str
    first: str
    last: str
    hand: str
    country: str

    @property
    def full_name(self) -> str:
        return f"{self.first} {self.last}"


@dataclass(frozen=True)
class ResolutionFailure:
    """Returned when resolution is ambiguous (multiple matches)."""
    query: str
    candidates: list[str]


@dataclass
class PlayerRegistry:
    """In-memory registry built from PlayerRecord list. Indexed for fast lookup."""
    records: list[PlayerRecord]
    by_normalized_full: dict[str, PlayerRecord]
    by_normalized_last: dict[str, list[PlayerRecord]]


def _strip_accents(text: str) -> str:
    """Decompose then strip combining marks. e-acute->e, sh->s, dotless-i kept as i."""
    text = text.replace("ı", "i")  # Turkish dotless i
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    if not name:
        return ""
    n = _strip_accents(name).lower().strip()
    return " ".join(n.split())


def build_registry(records: Iterable[PlayerRecord]) -> PlayerRegistry:
    """Build indexed registry from records."""
    records_list = list(records)
    by_full: dict[str, PlayerRecord] = {}
    by_last: dict[str, list[PlayerRecord]] = {}
    for r in records_list:
        full_norm = _normalize(r.full_name)
        last_norm = _normalize(r.last)
        by_full[full_norm] = r
        by_last.setdefault(last_norm, []).append(r)
    return PlayerRegistry(
        records=records_list,
        by_normalized_full=by_full,
        by_normalized_last=by_last,
    )


def _try_first_initial_match(query: str, registry: PlayerRegistry) -> PlayerRecord | None:
    """Match 'D. Medvedev' against registry by first letter + surname."""
    parts = [p.strip(".") for p in query.split() if p.strip()]
    if len(parts) < 2:
        return None
    first_token = parts[0]
    if len(first_token) > 2:  # not initial-like
        return None
    first_letter = _normalize(first_token)[:1]
    surname = _normalize(" ".join(parts[1:]))
    candidates = registry.by_normalized_last.get(surname, [])
    matches = [r for r in candidates if _normalize(r.first)[:1] == first_letter]
    if len(matches) == 1:
        return matches[0]
    return None


def _try_surname_only(query: str, registry: PlayerRegistry) -> PlayerRecord | None:
    """Match plain 'Medvedev' against registry - only if unique."""
    norm = _normalize(query)
    candidates = registry.by_normalized_last.get(norm, [])
    if len(candidates) == 1:
        return candidates[0]

    # Try compound surname (e.g., 'Alcaraz Garfia' vs query 'Alcaraz')
    if len(norm.split()) == 1:
        partial_matches = [
            r for r in registry.records
            if norm in _normalize(r.last).split()
        ]
        if len(partial_matches) == 1:
            return partial_matches[0]

    return None


def _try_fuzzy(query: str, registry: PlayerRegistry) -> PlayerRecord | None:
    """Fuzzy fallback for full names (handles minor typos)."""
    norm = _normalize(query)
    if len(norm) < 4:
        return None
    best_record: PlayerRecord | None = None
    best_score = 0.0
    for r in registry.records:
        score = fuzz.token_sort_ratio(norm, _normalize(r.full_name)) / 100.0
        if score > best_score and score >= _FUZZY_TOKEN_SORT_THRESHOLD:
            best_score = score
            best_record = r
    return best_record


def resolve_player(query: str, registry: PlayerRegistry) -> PlayerRecord | None:
    """Return PlayerRecord for query, or None if not confidently resolved."""
    if not query:
        return None
    norm = _normalize(query)

    # Layer 1: Exact normalized full name
    exact = registry.by_normalized_full.get(norm)
    if exact is not None:
        return exact

    # Layer 2: First initial + surname pattern
    initial_match = _try_first_initial_match(query, registry)
    if initial_match is not None:
        return initial_match

    # Layer 3: Surname only (must be unique)
    surname_match = _try_surname_only(query, registry)
    if surname_match is not None:
        return surname_match

    # Layer 4: Fuzzy fallback (full name)
    fuzzy_match = _try_fuzzy(query, registry)
    if fuzzy_match is not None:
        return fuzzy_match

    return None
