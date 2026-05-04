"""Polymarket MLB question parser.

Extracts market intent from Polymarket MLB question text + outcome label.

Supported market types:
- MONEYLINE — "Will X beat Y?" / "X vs Y" with outcome=team name
- RUN_LINE — "Will X -1.5 cover?" / "X +1.5 cover?"
- TOTALS — "X vs Y Over/Under N runs?"

Returns MLBMarketIntent or None on parse failure / team resolution failure.

Note: home/away order comes from slug (caller responsibility), not question.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.domain.sports.mlb_team_aliases import resolve_mlb_team


class MLBMarketType(str, Enum):
    MONEYLINE = "MONEYLINE"
    RUN_LINE = "RUN_LINE"
    TOTALS = "TOTALS"


@dataclass(frozen=True)
class MLBMarketIntent:
    market_type: MLBMarketType
    team_a: str  # canonical abbr
    team_b: str  # canonical abbr
    side_team: str | None  # ML/RL: which team this market sides with
    line: float | None  # RL: 1.5; Totals: 8.5; ML: None
    is_favorite_side: bool | None  # RL only: True if -1.5, False if +1.5
    totals_side: str | None  # Totals only: "OVER" / "UNDER"


# Patterns (evaluated in priority order — most specific first)
_TOTALS_PATTERN = re.compile(
    r"(?P<a>[A-Za-z][A-Za-z\.\s]+?)\s+vs\.?\s+(?P<b>[A-Za-z][A-Za-z\.\s]+?)\s+"
    r"(?P<side>Over|Under)\s+(?P<line>\d+\.\d+)\s+runs?\??$",
    re.IGNORECASE,
)

_RL_PATTERN = re.compile(
    r"^(?:Will\s+(?:the\s+)?)?(?P<team>[A-Za-z][A-Za-z\.\s]+?)\s+"
    r"(?P<sign>[+-])(?P<line>\d+\.\d+)\s+cover\??$",
    re.IGNORECASE,
)

_ML_WILL_PATTERN = re.compile(
    r"^Will\s+(?:the\s+)?(?P<a>.+?)\s+(?:beat|win\s+against)\s+(?:the\s+)?(?P<b>.+?)\??$",
    re.IGNORECASE,
)

_ML_VS_PATTERN = re.compile(
    r"^(?:MLB(?:\s+Playoffs?)?:\s*)?(?P<a>[A-Za-z][A-Za-z\.\s]+?)\s+vs\.?\s+(?P<b>[A-Za-z][A-Za-z\.\s]+?)$",
    re.IGNORECASE,
)


def parse_mlb_question(
    question: str | None,
    outcome: str | None = None,
) -> Optional[MLBMarketIntent]:
    """Parse Polymarket MLB question + outcome label into market intent.

    Args:
        question: raw Polymarket market question text
        outcome: the outcome label selected (e.g. "Braves", "Yes", "Over")

    Returns:
        MLBMarketIntent or None if parse fails or any team cannot be resolved.
    """
    if not question or not isinstance(question, str):
        return None
    text = question.strip()
    if not text:
        return None

    # 1. TOTALS — most specific, requires "runs?" suffix
    m = _TOTALS_PATTERN.match(text)
    if m:
        a = resolve_mlb_team(m.group("a").strip())
        b = resolve_mlb_team(m.group("b").strip())
        if a and b and a != b:
            return MLBMarketIntent(
                market_type=MLBMarketType.TOTALS,
                team_a=a,
                team_b=b,
                side_team=None,
                line=float(m.group("line")),
                is_favorite_side=None,
                totals_side=m.group("side").upper(),
            )

    # 2. RUN_LINE — "Will X -1.5 cover?" / "X +1.5 cover?"
    m = _RL_PATTERN.match(text)
    if m:
        team = resolve_mlb_team(m.group("team").strip())
        if team:
            sign = m.group("sign")
            return MLBMarketIntent(
                market_type=MLBMarketType.RUN_LINE,
                team_a=team,
                team_b="",
                side_team=team,
                line=float(m.group("line")),
                is_favorite_side=(sign == "-"),
                totals_side=None,
            )

    # 3. MONEYLINE — "Will X beat Y?"
    m = _ML_WILL_PATTERN.match(text)
    if m:
        a = resolve_mlb_team(m.group("a").strip())
        b = resolve_mlb_team(m.group("b").strip())
        if a and b and a != b:
            return MLBMarketIntent(
                market_type=MLBMarketType.MONEYLINE,
                team_a=a,
                team_b=b,
                side_team=a,
                line=None,
                is_favorite_side=None,
                totals_side=None,
            )

    # 4. MONEYLINE — "X vs. Y" / "MLB: X vs. Y"
    m = _ML_VS_PATTERN.match(text)
    if m:
        a = resolve_mlb_team(m.group("a").strip())
        b = resolve_mlb_team(m.group("b").strip())
        if a and b and a != b:
            side = resolve_mlb_team(outcome) if outcome else a
            return MLBMarketIntent(
                market_type=MLBMarketType.MONEYLINE,
                team_a=a,
                team_b=b,
                side_team=side,
                line=None,
                is_favorite_side=None,
                totals_side=None,
            )

    return None
