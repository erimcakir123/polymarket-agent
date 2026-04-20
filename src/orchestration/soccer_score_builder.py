"""Soccer-specific score_info enrichment helpers (SPEC-015).

score_enricher.py 400-satır limitine yakın — soccer-specific logic ayrı modülde.
Pure functions, no I/O.
"""
from __future__ import annotations

_DRAW_KEYWORDS = ("end in a draw", "draw", "level", "tie")

_KNOCKOUT_KEYWORDS = (
    "cup", "final", "champions league", "europa league", "conference league",
    "knockout", "round of 16", "quarter-final", "semi-final", "playoff",
    "elimination",
)


def determine_our_outcome(pos) -> str:
    """Position → 'home' | 'draw' | 'away'.

    Heuristic:
    - Question 'draw' keyword → 'draw'
    - BUY_YES → 'home' (Polymarket convention: first team in question = home)
    - BUY_NO → 'away' (NO on home = away wins implied)
    NOT: 3-way market'te genelde her outcome ayrı market olduğundan
    bu heuristic 2-way fallback. Soccer 3-way için EventGrouper.classify_outcomes()
    kullanılır (caller karar verir, bu sadece fallback).
    """
    question = (getattr(pos, "question", "") or "").lower()
    direction = getattr(pos, "direction", "BUY_YES")

    if any(kw in question for kw in _DRAW_KEYWORDS):
        return "draw"
    return "home" if direction == "BUY_YES" else "away"


def is_knockout_competition(pos) -> bool:
    """pos.tags veya question'dan knockout/cup tespiti."""
    tags = getattr(pos, "tags", []) or []
    question = (getattr(pos, "question", "") or "").lower()
    raw = " ".join(t.lower() for t in tags if isinstance(t, str)) + " " + question
    text = raw.replace("-", " ")
    return any(kw in text for kw in _KNOCKOUT_KEYWORDS)
