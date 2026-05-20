"""Tennis question parser — extract players + market type from Polymarket. Pure, no I/O.

Parses Polymarket market question text to extract:
- p1_name, p2_name  (player names, may be surnames or full names)
- market_type       (derived from sports_market_type field, not text)
- surface guess     (from tournament name keyword in slug or question)

Market type mapping (uses sports_market_type, not regex):
  tennis_first_set_winner  → "first_set_winner"
  tennis_set_handicap      → "set_handicap_minus_1_5"
  tennis_set_totals        → "total_sets_under_2_5"

Skipped market types (no model for these):
  tennis_match_totals, tennis_first_set_totals, tennis_completed_match, etc.

Surface keyword → surface (fallback "hard"):
  Tournament name keywords extracted from slug and question text.

WTA filter (2026-05-20): predictor uses ATP-only Sackmann data. Any `wta-*`
slug is rejected at parse time to avoid (a) silent skips from missing ratings
or (b) coincidental ATP name collisions yielding garbage predictions.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §5.3
"""
from __future__ import annotations

import logging
import re
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# WTA prefix filter: predictor model uses ATP-only Sackmann historical data.
# Any market whose slug indicates WTA is unparseable → return None.
_WTA_SLUG_PREFIX = "wta-"
_wta_skipped_count = 0

# Mapping from Polymarket sports_market_type → internal market_type.
# Only the 3 types the predictor handles are included; others → None (skip).
_MARKET_TYPE_MAP: dict[str, str] = {
    "tennis_first_set_winner": "first_set_winner",
    "tennis_set_handicap": "set_handicap_minus_1_5",
    "tennis_set_totals": "total_sets_under_2_5",
}

# Tournament keyword → surface. Order matters: check longer/more-specific keys first.
# Keywords are lowercased; matched against slug + question corpus (lowercased).
_TOURNAMENT_SURFACE: list[tuple[str, str]] = [
    # Clay
    ("roland-garros", "clay"), ("roland garros", "clay"),
    ("french-open", "clay"), ("french open", "clay"),
    ("monte-carlo", "clay"), ("monte carlo", "clay"),
    ("barcelona", "clay"),
    ("madrid", "clay"),
    ("rome", "clay"), ("roma", "clay"),
    ("hamburg", "clay"),
    ("geneva", "clay"),
    ("lyon", "clay"),
    ("munich", "clay"),
    ("estoril", "clay"),
    ("cervia", "clay"),
    # Grass
    ("wimbledon", "grass"),
    ("queens", "grass"), ("queen's", "grass"),
    ("halle", "grass"),
    ("stuttgart", "grass"),
    ("eastbourne", "grass"),
    # Hard — specific (before generic)
    ("australian-open", "hard"), ("australian open", "hard"),
    ("us-open", "hard"), ("us open", "hard"),
    ("indian-wells", "hard"), ("indian wells", "hard"),
    ("miami", "hard"),
    ("cincinnati", "hard"),
    ("washington", "hard"),
    ("atlanta", "hard"),
    ("toronto", "hard"),
    ("montreal", "hard"),
    ("beijing", "hard"),
    ("shanghai", "hard"),
    ("paris", "hard"),
    ("vienna", "hard"),
    ("basel", "hard"),
]

# Regex to extract player names from question.
# Handles: "P1 vs P2", "Set 1 Winner: P1 vs P2", "P1 vs. P2: O/U 8.5"
_VS_PATTERN = re.compile(
    r"(?:^|\:\s*)([A-Za-z\-'. ]{2,30?})\s+vs\.?\s+([A-Za-z\-'. ]{2,30?})"
    r"(?:\s*[\:\(]|$)",
    re.IGNORECASE,
)

# "Set Handicap: Samsonova (-1.5) vs Siegemund (+1.5)" — handicap format
_HANDICAP_PATTERN = re.compile(
    r"([A-Za-z\-'. ]{2,25})\s*\([+-]?\d+\.\d+\)\s+vs\.?\s+([A-Za-z\-'. ]{2,25})",
    re.IGNORECASE,
)


def _strip_market_suffix(name: str) -> str:
    """Remove trailing handicap, O/U suffix from player name fragment."""
    # E.g. "Siegemund (+1.5)" → "Siegemund"
    return re.sub(r"\s*\([+-]?[\d.]+\).*$", "", name).strip()


def _extract_player_names(question: str) -> tuple[Optional[str], Optional[str]]:
    """Extract (p1_name, p2_name) from question text. Returns (None, None) on failure."""
    if not question:
        return None, None

    # Try handicap pattern first (more specific)
    m = _HANDICAP_PATTERN.search(question)
    if m:
        p1 = _strip_market_suffix(m.group(1)).strip()
        p2 = _strip_market_suffix(m.group(2)).strip()
        if p1 and p2:
            return p1, p2

    # Try generic vs pattern
    m2 = _VS_PATTERN.search(question)
    if m2:
        p1 = _strip_market_suffix(m2.group(1)).strip()
        p2 = _strip_market_suffix(m2.group(2)).strip()
        if p1 and p2:
            return p1, p2

    # Fallback: plain " vs " anywhere in question
    low = question.lower()
    for sep in (" vs. ", " vs ", " versus "):
        if sep in low:
            idx = low.index(sep)
            left = question[:idx].strip()
            right = question[idx + len(sep):].strip()
            # Strip tournament prefix ("Set 1 Winner: Player1" → "Player1")
            if ":" in left:
                left = left.rsplit(":", 1)[-1].strip()
            # Strip O/U suffix from right
            if ":" in right:
                right = right.split(":", 1)[0].strip()
            right = right.rstrip("?").strip()
            left = _strip_market_suffix(left)
            right = _strip_market_suffix(right)
            if left and right:
                return left, right

    return None, None


def _detect_surface(slug: str, question: str) -> str:
    """Guess surface from tournament keyword in slug or question. Default: hard."""
    corpus = f"{slug} {question}".lower().replace("_", "-").replace(" ", "-")
    for keyword, surface in _TOURNAMENT_SURFACE:
        kw = keyword.replace(" ", "-")
        if kw in corpus:
            return surface
    return "hard"


def map_market_type(sports_market_type: str) -> Optional[str]:
    """Map Polymarket sports_market_type → internal market_type string.

    Returns None for market types we don't predict (skip signal).
    """
    return _MARKET_TYPE_MAP.get(sports_market_type)


def parse_tennis_question(
    question: str,
    sports_market_type: str,
    slug: str = "",
) -> Optional[dict]:
    """Parse one Polymarket tennis market into structured fields.

    Args:
        question: Market question text (e.g. "Set 1 Winner: Djokovic vs Alcaraz").
        sports_market_type: Polymarket type tag (e.g. "tennis_first_set_winner").
        slug: Market slug for surface detection (e.g. "atp-djokovic-alcaraz-roland-garros-2026").

    Returns:
        dict with keys: p1_name, p2_name, market_type, surface
        or None if market_type is not supported / player names unparseable
        / slug is WTA (predictor is ATP-only).
    """
    # WTA filter (2026-05-20): Sackmann historical data is ATP-only. WTA slugs
    # would either fail player lookup or hit coincidental ATP collisions.
    if slug and slug.lower().startswith(_WTA_SLUG_PREFIX):
        global _wta_skipped_count
        _wta_skipped_count += 1
        if _wta_skipped_count % 10 == 1:
            logger.info(
                "tennis_parser: WTA slug skipped (count=%d) — ATP-only predictor; example=%s",
                _wta_skipped_count, slug[:60],
            )
        return None

    market_type = map_market_type(sports_market_type)
    if market_type is None:
        return None

    p1_name, p2_name = _extract_player_names(question)
    if not p1_name or not p2_name:
        return None

    surface = _detect_surface(slug=slug, question=question)

    return {
        "p1_name": p1_name,
        "p2_name": p2_name,
        "market_type": market_type,
        "surface": surface,
    }
