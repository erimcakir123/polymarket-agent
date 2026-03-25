"""Penny Alpha Scanner — find $0.01-$0.02 tokens with 5-10x upside potential.

Strategy: Buy tokens priced at $0.01-$0.02 (extreme longshots) and hold for
multiplier exits. No AI analysis needed — pure price + catalyst detection.

Entry criteria:
    - YES token price $0.01-$0.02
    - Market has reasonable volume (not dead)
    - Event has a plausible catalyst (upcoming match, election, etc.)
    - Not already resolved or expired

Exit targets:
    - $0.01 entry → 5x target ($0.05)
    - $0.02 entry → 2x target ($0.04)
    - Hard stop: price drops to $0.00 (total loss accepted — position is small)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

# Penny alpha thresholds
PENNY_MAX_PRICE = 0.02
PENNY_MIN_VOLUME = 500  # Minimum 24h volume to ensure some activity
PENNY_BET_PCT = 0.05  # 5% bankroll per penny bet
MAX_CONCURRENT_PENNIES = 3

# Target multipliers by entry price
PENNY_TARGETS = {
    0.01: 5.0,  # $0.01 → target $0.05 (5x)
    0.02: 2.0,  # $0.02 → target $0.04 (2x)
}


@dataclass
class PennyCandidate:
    """A penny alpha candidate."""
    condition_id: str
    question: str
    slug: str
    yes_price: float
    no_price: float
    volume_24h: float
    target_price: float
    target_multiplier: float
    days_to_resolution: float
    token_side: str  # "YES" or "NO" — whichever is the penny token


def scan_penny_candidates(
    markets: list,
    max_candidates: int = 10,
    min_volume: float = PENNY_MIN_VOLUME,
    max_price: float = PENNY_MAX_PRICE,
) -> List[PennyCandidate]:
    """Scan markets for penny alpha opportunities.

    Looks for both YES and NO tokens priced at $0.01-$0.02.
    A YES token at $0.01 means market thinks outcome is ~1% likely.
    A NO token at $0.01 means market thinks outcome is ~99% likely (buy NO = bet against).

    Args:
        markets: List of MarketData objects from scanner
        max_candidates: Maximum candidates to return
        min_volume: Minimum 24h volume filter
        max_price: Maximum token price for penny alpha

    Returns:
        List of PennyCandidate sorted by volume (most liquid first)
    """
    candidates: List[PennyCandidate] = []

    for m in markets:
        # Skip dead or very illiquid markets
        if m.volume_24h < min_volume:
            continue

        # Check days to resolution
        days_to_res = 999.0
        if m.end_date_iso:
            try:
                end_dt = datetime.fromisoformat(m.end_date_iso.replace("Z", "+00:00"))
                delta = end_dt - datetime.now(timezone.utc)
                days_to_res = max(0, delta.total_seconds() / 86400)
            except (ValueError, TypeError):
                pass

        # Skip if already resolved
        if days_to_res < 0:
            continue

        # Only head-to-head matchups (X vs Y) — never tournament/season winners
        q_lower = m.question.lower()
        has_vs = " vs " in q_lower or " vs. " in q_lower
        if not has_vs:
            continue

        # Check YES side penny
        if 0.01 <= m.yes_price <= max_price:
            entry_price = m.yes_price
            # Round to nearest cent for target lookup
            key = round(entry_price, 2)
            multiplier = PENNY_TARGETS.get(key, 2.0)
            candidates.append(PennyCandidate(
                condition_id=m.condition_id,
                question=m.question,
                slug=m.slug,
                yes_price=m.yes_price,
                no_price=m.no_price,
                volume_24h=m.volume_24h,
                target_price=round(entry_price * multiplier, 2),
                target_multiplier=multiplier,
                days_to_resolution=round(days_to_res, 1),
                token_side="YES",
            ))

        # Check NO side penny — use actual no_price from order book when available
        no_price = getattr(m, "no_price", 0.0) or (1.0 - m.yes_price)
        if 0.01 <= no_price <= max_price:
            entry_price = no_price
            key = round(entry_price, 2)
            multiplier = PENNY_TARGETS.get(key, 2.0)
            candidates.append(PennyCandidate(
                condition_id=m.condition_id,
                question=m.question,
                slug=m.slug,
                yes_price=m.yes_price,
                no_price=no_price,
                volume_24h=m.volume_24h,
                target_price=round(entry_price * multiplier, 2),
                target_multiplier=multiplier,
                days_to_resolution=round(days_to_res, 1),
                token_side="NO",
            ))

    # Sort by volume (most liquid first)
    candidates.sort(key=lambda c: c.volume_24h, reverse=True)
    return candidates[:max_candidates]


def size_penny_position(
    bankroll: float,
    bet_pct: float = PENNY_BET_PCT,
    max_concurrent: int = MAX_CONCURRENT_PENNIES,
    current_penny_count: int = 0,
) -> float:
    """Calculate position size for a penny alpha trade.

    Returns 0 if max concurrent pennies reached.
    """
    if current_penny_count >= max_concurrent:
        return 0.0
    return round(bankroll * bet_pct, 2)


def check_penny_exit(
    entry_price: float,
    current_price: float,
    target_multiplier: float,
) -> dict:
    """Check if penny position should exit.

    Returns:
        {"exit": bool, "reason": str, "profit_pct": float}
    """
    if entry_price <= 0:
        return {"exit": False, "reason": "invalid_entry", "profit_pct": 0.0}

    profit_pct = (current_price - entry_price) / entry_price
    target_price = entry_price * target_multiplier

    if current_price >= target_price:
        return {
            "exit": True,
            "reason": f"penny_target_{target_multiplier:.0f}x",
            "profit_pct": round(profit_pct, 3),
        }

    # No stop-loss for pennies — accept total loss as cost of strategy
    return {"exit": False, "reason": "holding", "profit_pct": round(profit_pct, 3)}
