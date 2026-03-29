"""Upset Hunter -- contrarian underdog strategy.

Buys YES tokens at 5-15¢ where favourite-longshot bias
creates systematic mispricing. Small bets, huge upside on wins.

Pre-filter pipeline (cheap, no AI):
    1. Price zone: 5-15¢
    2. Odds API divergence: min 5pt
    3. Liquidity: min $5,000
    4. Timing: max 48h before match, not past 75% if live
    5. Moneyline only (no draw/spread/total)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from src.models import MarketData

logger = logging.getLogger(__name__)

_ALT_SLUG = ("-draw", "-1h-", "-first-half-", "-total-", "-spread-", "-btts")


@dataclass
class UpsetCandidate:
    """A pre-filtered underdog market ready for AI evaluation."""
    condition_id: str
    question: str
    slug: str
    yes_price: float
    yes_token_id: str
    no_price: float
    no_token_id: str
    direction: str  # "BUY_YES" or "BUY_NO"
    volume_24h: float
    liquidity: float
    odds_api_implied: Optional[float]
    divergence: Optional[float]
    hours_to_match: Optional[float]
    upset_type: str
    event_id: str


def pre_filter(
    markets: List[MarketData],
    min_price: float = 0.05,
    max_price: float = 0.15,
    min_liquidity: float = 5_000,
    min_odds_divergence: float = 0.05,
    max_hours_before: float = 48,
) -> List[UpsetCandidate]:
    """Pre-filter markets for upset hunting candidates.

    Returns candidates sorted by divergence (highest first).
    No AI calls -- purely programmatic cheap filters.
    """
    candidates = []

    for m in markets:
        # Determine which sides are in the price zone
        yes_in_zone = min_price <= m.yes_price <= max_price
        no_price = getattr(m, "no_price", 1 - m.yes_price)
        no_in_zone = min_price <= no_price <= max_price

        # Skip if neither side is in the upset zone
        if not yes_in_zone and not no_in_zone:
            continue

        # Filter 5: Moneyline only (check early to skip fast)
        if any(t in (m.slug or "").lower() for t in _ALT_SLUG):
            continue

        # Filter 3: Minimum liquidity
        if m.liquidity < min_liquidity:
            continue

        # Filter 4: Timing window
        hours_left = _hours_to_match(m.end_date_iso)
        if hours_left is not None:
            if hours_left > max_hours_before:
                continue
            if hours_left < 0:
                elapsed_pct = _estimate_elapsed_pct(m)
                if elapsed_pct is not None and elapsed_pct > 0.75:
                    continue

        # Filter 2: Odds API divergence (direction-aware)
        odds_implied = getattr(m, "odds_api_implied_prob", None)
        # YES-side divergence: bookmaker_yes_prob - market_yes_price
        yes_divergence = None
        # NO-side divergence: bookmaker_no_prob - market_no_price
        no_divergence = None
        if odds_implied is not None and odds_implied > 0:
            yes_divergence = odds_implied - m.yes_price
            no_divergence = (1 - odds_implied) - no_price

        # Determine upset type
        if hours_left is not None and hours_left < 0:
            upset_type = "early_live"
        else:
            upset_type = "pre_match"

        no_token_id = getattr(m, "no_token_id", "") or ""

        # Emit candidate for each qualifying side (with per-side divergence gate)
        if yes_in_zone:
            # Gate: if odds data exists, YES divergence must meet threshold
            if yes_divergence is not None and yes_divergence < min_odds_divergence:
                pass  # skip YES side
            else:
                candidates.append(UpsetCandidate(
                    condition_id=m.condition_id,
                    question=m.question,
                    slug=m.slug or "",
                    yes_price=m.yes_price,
                    yes_token_id=m.yes_token_id,
                    no_price=no_price,
                    no_token_id=no_token_id,
                    direction="BUY_YES",
                    volume_24h=m.volume_24h,
                    liquidity=m.liquidity,
                    odds_api_implied=odds_implied,
                    divergence=yes_divergence,
                    hours_to_match=hours_left,
                    upset_type=upset_type,
                    event_id=getattr(m, "event_id", "") or "",
                ))

        if no_in_zone:
            # Gate: if odds data exists, NO divergence must meet threshold
            if no_divergence is not None and no_divergence < min_odds_divergence:
                pass  # skip NO side
            else:
                candidates.append(UpsetCandidate(
                    condition_id=m.condition_id,
                    question=m.question,
                    slug=m.slug or "",
                    yes_price=m.yes_price,
                    yes_token_id=m.yes_token_id,
                    no_price=no_price,
                    no_token_id=no_token_id,
                    direction="BUY_NO",
                    volume_24h=m.volume_24h,
                    liquidity=m.liquidity,
                    odds_api_implied=odds_implied,
                    divergence=no_divergence,
                    hours_to_match=hours_left,
                    upset_type=upset_type,
                    event_id=getattr(m, "event_id", "") or "",
                ))

    candidates.sort(key=lambda c: c.divergence if c.divergence is not None else -1, reverse=True)
    logger.info("Upset hunter pre-filter: %d candidates from %d markets", len(candidates), len(markets))
    return candidates


def size_upset_position(
    bankroll: float,
    bet_pct: float = 0.02,
    current_upset_count: int = 0,
    max_concurrent: int = 3,
) -> float:
    """Calculate upset position size. Returns USDC amount (0.0 if not eligible)."""
    if current_upset_count >= max_concurrent:
        return 0.0
    return max(0.0, bankroll * bet_pct)


def _hours_to_match(end_date_iso: str) -> Optional[float]:
    """Hours until match/resolution. Negative = already started."""
    if not end_date_iso:
        return None
    try:
        from datetime import datetime, timezone
        end = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (end - now).total_seconds() / 3600
    except (ValueError, TypeError):
        return None


def _estimate_elapsed_pct(m: MarketData) -> Optional[float]:
    """Rough estimate of match elapsed percentage from available data."""
    if getattr(m, "match_start_iso", None):
        try:
            from datetime import datetime, timezone
            start = datetime.fromisoformat(m.match_start_iso.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            elapsed_min = (now - start).total_seconds() / 60
            return min(elapsed_min / 120, 1.0)
        except (ValueError, TypeError):
            pass
    return None
