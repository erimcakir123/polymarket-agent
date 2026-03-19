"""Pre-filter: skip logically impossible markets before spending AI tokens.

Content-based, not time-based. A sports match 2h away is still worth analyzing.
But "Will Iran war end by March?" with 2h left is obviously NO — skip it.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import List

from src.models import MarketData

logger = logging.getLogger(__name__)

# Patterns that indicate large-scale events unlikely to resolve in hours
_LARGE_EVENT_PATTERNS = re.compile(
    r"\b(war|conflict|invasion|peace deal|ceasefire|treaty|annex|"
    r"recession|depression|collapse|default|"
    r"impeach|remove from office|convicted|sentenced|"
    r"cure|eradicate|pandemic end|"
    r"reunif|independence|secede|"
    r"nuclear|world war|martial law)\b",
    re.IGNORECASE,
)

# Patterns for events that CAN resolve quickly (hours/days)
_QUICK_RESOLVE_PATTERNS = re.compile(
    r"\b(win|beat|score|goal|match|game|fight|bout|"
    r"announce|sign|tweet|post|say|"
    r"vote|pass|approve|reject|"
    r"rate decision|cut rate|hike rate|"
    r"land|launch|arrive|release|drop)\b",
    re.IGNORECASE,
)


def filter_impossible_markets(
    markets: List[MarketData],
    hours_threshold: float = 6.0,
) -> List[MarketData]:
    """Remove markets where the outcome is logically impossible given time remaining.

    Rules:
    - Large-scale events (war, recession, etc.) with <6h remaining → skip
    - Quick-resolve events (matches, votes, announcements) → keep regardless
    - No end_date → keep (can't judge)
    """
    filtered = []
    for market in markets:
        result = check_market(market, hours_threshold)
        if result == "skip":
            logger.info("Pre-filter SKIP (impossible): %s", market.question[:60])
            continue
        filtered.append(market)
    return filtered


def check_market(
    market: MarketData,
    hours_threshold: float = 6.0,
) -> str:
    """Check if a market's outcome is logically possible.

    Returns: "keep" or "skip"
    """
    # No end date → can't judge → keep
    if not market.end_date_iso:
        return "keep"

    # Parse end date
    try:
        end_dt = datetime.fromisoformat(market.end_date_iso.replace("Z", "+00:00"))
        hours_left = (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600
    except (ValueError, TypeError):
        return "keep"

    # Already expired → skip
    if hours_left <= 0:
        return "skip"

    # Plenty of time → keep
    if hours_left > hours_threshold:
        return "keep"

    # Short time remaining — check content
    question = market.question.lower()
    description = (market.description or "").lower()
    text = question + " " + description

    # Quick-resolve events (matches, votes, announcements) → keep even with short time
    if _QUICK_RESOLVE_PATTERNS.search(text):
        return "keep"

    # Large-scale events with short time → impossible → skip
    if _LARGE_EVENT_PATTERNS.search(text):
        return "skip"

    # Default: keep (don't over-filter)
    return "keep"
