"""
Polymarket NHL question parser.

Extracts the two team abbreviations from a Polymarket NHL market question.
Does NOT determine home/away order — that comes from the slug, which is the
canonical source.

Supported patterns (real Polymarket samples):
- "Bruins vs. Sabres"                      (mascot only, common)
- "Bruins vs Sabres"                       (no period after vs)
- "NHL: Lightning vs. Canadiens"           (NHL prefix)
- "NHL Playoffs: Oilers vs. Ducks"         (Playoffs prefix)
- "Boston Bruins vs. Buffalo Sabres"       (full name)
- "Will the Bruins win against the Sabres?" (question form)
- "Will the Oilers beat the Ducks?"        (alt verb)

Returns:
    (team_a_abbr, team_b_abbr) | None

Note: team_a is always the team mentioned first in the question text.
Polymarket convention is typically away-vs-home but THIS IS NOT GUARANTEED.
Slug parser is the source of truth for home/away resolution.

References:
- Polymarket NHL market question samples (manually collected during planning)
- src/domain/sports/nhl_team_aliases.resolve_nhl_team
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from src.domain.sports.nhl_team_aliases import resolve_nhl_team


# Compiled patterns (priority order). First match wins.
_QUESTION_PATTERNS = [
    # "Will the X win/beat (against) Y?"
    re.compile(
        r"^Will\s+(?:the\s+)?(?P<a>.+?)\s+(?:win|beat)\s+"
        r"(?:against\s+)?(?:the\s+)?(?P<b>.+?)\??$",
        re.IGNORECASE,
    ),
    # "NHL Playoffs: X vs. Y" / "NHL Playoff: X vs. Y" / "NHL: X vs. Y"
    re.compile(
        r"^NHL(?:\s+Playoffs?)?:\s*(?P<a>.+?)\s+vs\.?\s+(?P<b>.+?)$",
        re.IGNORECASE,
    ),
    # "X vs. Y" (most common)
    re.compile(
        r"^(?P<a>[A-Za-z][A-Za-z\.\s]+?)\s+vs\.?\s+(?P<b>[A-Za-z][A-Za-z\.\s]+?)$",
        re.IGNORECASE,
    ),
]


def parse_nhl_question(question: str) -> Optional[Tuple[str, str]]:
    """
    Parse a Polymarket NHL question into a pair of canonical ESPN abbreviations.

    Args:
        question: raw market question text

    Returns:
        (team_a_abbr, team_b_abbr) where team_a is mentioned first in the
        question, or None if parse fails or either team can't be resolved.

    Order is text-order, NOT home/away. Use slug parser for that.
    """
    if not question or not isinstance(question, str):
        return None

    text = question.strip()
    if not text:
        return None

    for pattern in _QUESTION_PATTERNS:
        match = pattern.match(text)
        if not match:
            continue
        a_raw = match.group("a").strip()
        b_raw = match.group("b").strip()
        if not a_raw or not b_raw:
            continue

        a_abbr = resolve_nhl_team(a_raw)
        b_abbr = resolve_nhl_team(b_raw)
        if a_abbr and b_abbr and a_abbr != b_abbr:
            return (a_abbr, b_abbr)

    return None


def is_nhl_question(question: str) -> bool:
    """Heuristic: is this question likely an NHL market?"""
    if not question or not isinstance(question, str):
        return False
    return parse_nhl_question(question) is not None
