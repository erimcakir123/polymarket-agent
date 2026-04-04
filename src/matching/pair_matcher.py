"""Team pair matching — compare two team names with 4-layer confidence.

Replaces src/team_matcher.py. Used by:
- matching pipeline (market <-> scout)
- odds_api.py (market <-> Odds API event)
- sports_data.py, esports_data.py (team lookup)
"""
from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Optional

from rapidfuzz import fuzz

from src.matching.team_resolver import normalize, _STATIC_ALIASES, _STATIC_ABBREVS

logger = logging.getLogger(__name__)


def _canonicalize(name: str) -> str:
    """Resolve through aliases/abbrevs to canonical name."""
    n = normalize(name)
    if n in _STATIC_ALIASES:
        return _STATIC_ALIASES[n]
    if n in _STATIC_ABBREVS:
        return _STATIC_ABBREVS[n]
    return n


def match_team(query: str, candidate: str) -> tuple[bool, float, str]:
    """Match two team names. Returns (is_match, confidence, method).

    L1: Exact / alias (1.0)
    L2: Token overlap (0.85-0.90)
    L3: Fuzzy SequenceMatcher >= 0.80
    """
    q = normalize(query)
    c = normalize(candidate)

    # L1: Exact canonical
    if _canonicalize(query) == _canonicalize(candidate):
        return True, 1.0, "exact_alias"

    # L2: Token overlap
    q_tokens = set(q.split())
    c_tokens = set(c.split())
    noise = {"team", "the", "of", "de", "fc", "sc", "city", "united"}

    if len(q_tokens) == 1:
        q_word = list(q_tokens)[0]
        if q_word not in noise and (q_word in c_tokens or any(q_word in ct for ct in c_tokens)):
            return True, 0.90, "token_substring"

    if len(q_tokens) > 1 and len(c_tokens) > 1:
        overlap = q_tokens & c_tokens
        meaningful = overlap - noise
        if meaningful and len(overlap) / min(len(q_tokens), len(c_tokens)) >= 0.5:
            return True, 0.85, "token_overlap"

    # L3: Fuzzy — high threshold only
    score = SequenceMatcher(None, q, c).ratio()
    if score >= 0.80:
        return True, score, "fuzzy"

    # L3b: rapidfuzz token_sort for longer names
    if len(q) >= 4 and len(c) >= 4:
        rf_score = fuzz.token_sort_ratio(q, c) / 100.0
        if rf_score >= 0.85:
            return True, rf_score, "fuzzy_token_sort"

    # L3c: rapidfuzz partial_ratio — catches abbreviations like "man" matching "manchester"
    if len(q) >= 4 and len(c) >= 4:
        partial_score = fuzz.partial_ratio(q, c) / 100.0
        # Require overlap of non-noise tokens too for safety
        overlap = q_tokens & c_tokens
        if partial_score >= 0.80 and overlap:
            return True, partial_score, "fuzzy_partial"

    return False, max(score, 0.0), "no_match"


def match_pair(
    market_names: tuple[str, str],
    entry_names: tuple[str, str],
) -> tuple[bool, float]:
    """Match two team pairs. Both must match. Tries normal + swapped order."""
    # Normal order
    ma, ca, _ = match_team(market_names[0], entry_names[0])
    mb, cb, _ = match_team(market_names[1], entry_names[1])
    if ma and mb:
        return True, min(ca, cb)

    # Swapped
    ma2, ca2, _ = match_team(market_names[0], entry_names[1])
    mb2, cb2, _ = match_team(market_names[1], entry_names[0])
    if ma2 and mb2:
        return True, min(ca2, cb2)

    return False, 0.0


def find_best_event_match(
    team_a: str,
    team_b: str,
    events: list[dict],
    home_key: str = "home_team",
    away_key: str = "away_team",
    min_confidence: float = 0.80,
) -> Optional[tuple[dict, float]]:
    """Find best matching event for a team pair (used by odds_api.py)."""
    best_event = None
    best_conf = 0.0

    for event in events:
        home = event.get(home_key, "")
        away = event.get(away_key, "")
        if not home or not away:
            continue
        is_match, conf = match_pair((team_a, team_b), (home, away))
        if is_match and conf > best_conf:
            best_conf = conf
            best_event = event

    if best_event and best_conf >= min_confidence:
        return best_event, best_conf
    return None


def find_best_single_team_match(
    team: str,
    events: list[dict],
    home_key: str = "home_team",
    away_key: str = "away_team",
    min_confidence: float = 0.80,
) -> Optional[tuple[dict, float, bool]]:
    """Find best matching event for a SINGLE team name.

    Returns (event, confidence, team_is_home) or None.
    Used when Polymarket question has only one team (e.g. "Will Ajax win?").
    """
    best_event = None
    best_conf = 0.0
    best_is_home = True

    for event in events:
        home = event.get(home_key, "")
        away = event.get(away_key, "")
        if not home or not away:
            continue

        is_match_h, conf_h, _ = match_team(team, home)
        if is_match_h and conf_h > best_conf:
            best_conf = conf_h
            best_event = event
            best_is_home = True

        is_match_a, conf_a, _ = match_team(team, away)
        if is_match_a and conf_a > best_conf:
            best_conf = conf_a
            best_event = event
            best_is_home = False

    if best_event and best_conf >= min_confidence:
        return best_event, best_conf, best_is_home
    return None
