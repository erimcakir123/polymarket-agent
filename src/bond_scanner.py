"""Bond Farming Scanner — near-certain events for low-risk profit.

Scans Polymarket for events with YES tokens priced $0.90-0.97.
These are near-certain outcomes where buying YES and waiting for
resolution at $1.00 yields 3-7% profit with minimal risk.

No AI analysis needed — purely programmatic check:
    1. Is the event near resolution? (< 7 days)
    2. Is there high volume? (market efficiency signal)
    3. Is liquidity sufficient for exit?
    4. Are multiple indicators confirming the outcome?

Also detects "live blowout" bonds: matches where score is lopsided
and time is running out (e.g., NBA team up 20 with 5 min left).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from src.models import MarketData

logger = logging.getLogger(__name__)

# Bond criteria — percentage of bankroll, not fixed amounts
MIN_YES_PRICE = 0.90           # At least 90% implied probability
MAX_YES_PRICE = 0.97           # Above 97% = not enough edge
MIN_VOLUME_24H = 50_000        # High volume = market is pricing correctly
MIN_LIQUIDITY = 5_000          # Need to be able to exit
MAX_RESOLUTION_DAYS = 7        # Resolve within 1 week

# Position sizing as % of bankroll
BOND_BET_PCT = 0.15            # Up to 15% bankroll per bond (low risk allows larger size)
MAX_TOTAL_BOND_PCT = 0.35      # Max 35% bankroll across all bonds
MAX_CONCURRENT_BONDS = 3       # Max 3 bond positions at once


@dataclass
class BondCandidate:
    """A near-certain market suitable for bond farming."""
    condition_id: str
    question: str
    slug: str
    yes_price: float
    volume_24h: float
    liquidity: float
    days_to_resolution: float
    expected_profit_pct: float    # (1.00 - yes_price) / yes_price
    bond_type: str                # "time_decay" | "live_blowout" | "resolved_pending"
    confidence_signals: List[str]  # Why we think this is near-certain


def scan_bond_candidates(
    markets: List[MarketData],
    max_resolution_days: float = MAX_RESOLUTION_DAYS,
    min_yes_price: float = MIN_YES_PRICE,
    max_yes_price: float = MAX_YES_PRICE,
    min_volume: float = MIN_VOLUME_24H,
    min_liquidity: float = MIN_LIQUIDITY,
) -> List[BondCandidate]:
    """Scan markets for bond farming opportunities.

    Args:
        markets: List of MarketData from Gamma API
        max_resolution_days: Only markets resolving within this window
        min_yes_price: Minimum YES price (probability floor)
        max_yes_price: Maximum YES price (ceiling for edge)
        min_volume: Minimum 24h volume
        min_liquidity: Minimum CLOB liquidity

    Returns:
        List of BondCandidate sorted by expected profit (highest first)
    """
    candidates = []

    for m in markets:
        # Basic filters
        if m.yes_price < min_yes_price or m.yes_price > max_yes_price:
            continue
        if m.volume_24h < min_volume:
            continue
        if m.liquidity < min_liquidity:
            continue

        # Calculate days to resolution
        days_left = _days_to_resolution(m.end_date_iso)
        if days_left is None or days_left > max_resolution_days or days_left < 0:
            continue

        # Expected profit
        expected_profit = (1.0 - m.yes_price) / m.yes_price

        # Determine bond type and confidence signals
        bond_type, signals = _classify_bond(m, days_left)

        if not signals:
            continue  # No confidence signals = skip

        candidates.append(BondCandidate(
            condition_id=m.condition_id,
            question=m.question,
            slug=m.slug or "",
            yes_price=m.yes_price,
            volume_24h=m.volume_24h,
            liquidity=m.liquidity,
            days_to_resolution=days_left,
            expected_profit_pct=round(expected_profit, 4),
            bond_type=bond_type,
            confidence_signals=signals,
        ))

    # Sort by expected profit (highest first)
    candidates.sort(key=lambda c: c.expected_profit_pct, reverse=True)

    logger.info("Bond scanner found %d candidates from %d markets", len(candidates), len(markets))
    return candidates


def size_bond_position(
    bankroll: float,
    candidate: BondCandidate,
    current_bond_exposure: float = 0.0,
    current_bond_count: int = 0,
    bet_pct: float = BOND_BET_PCT,
    max_total_pct: float = MAX_TOTAL_BOND_PCT,
    max_concurrent: int = MAX_CONCURRENT_BONDS,
) -> float:
    """Calculate bond position size as percentage of bankroll.

    Returns USDC size (0.0 if not eligible).
    """
    if current_bond_count >= max_concurrent:
        return 0.0

    remaining_allocation = (bankroll * max_total_pct) - current_bond_exposure
    if remaining_allocation <= 0:
        return 0.0

    size = min(
        bankroll * bet_pct,          # Per-bond limit
        remaining_allocation,        # Total bond allocation remaining
    )

    return max(0.0, size)


def _classify_bond(m: MarketData, days_left: float) -> tuple:
    """Classify bond type and gather confidence signals."""
    signals = []
    bond_type = "time_decay"

    # Signal: High volume indicates market consensus
    if m.volume_24h > 100_000:
        signals.append(f"Very high volume (${m.volume_24h:,.0f})")
    elif m.volume_24h > 50_000:
        signals.append(f"High volume (${m.volume_24h:,.0f})")

    # Signal: Very close to resolution
    if days_left < 1:
        signals.append(f"Resolves in <24h ({days_left:.1f} days)")
        bond_type = "resolved_pending"
    elif days_left < 3:
        signals.append(f"Resolves in {days_left:.1f} days")

    # Signal: Event already happened (match ended, result known)
    if m.event_ended:
        signals.append("Event already ended — awaiting resolution")
        bond_type = "resolved_pending"

    # Signal: Live blowout (match in progress, dominant lead)
    if m.event_live and m.match_score:
        blowout = _detect_blowout(m.match_score, m.sport_tag)
        if blowout:
            signals.append(f"Live blowout: {m.match_score}")
            bond_type = "live_blowout"

    # Signal: Price stability (high price + high volume = consensus)
    if m.yes_price >= 0.93 and m.volume_24h > 75_000:
        signals.append("Strong price consensus (>93¢ + high volume)")

    return bond_type, signals


def _detect_blowout(score: str, sport_tag: str) -> bool:
    """Detect if a live match score indicates a blowout."""
    try:
        # Parse common score formats: "3-0|Bo3", "102-78", "3-0"
        clean = score.split("|")[0].strip()
        parts = clean.split("-")
        if len(parts) != 2:
            return False
        a, b = int(parts[0]), int(parts[1])
        diff = abs(a - b)

        # Sport-specific blowout thresholds
        if sport_tag in ("nba", "basketball"):
            return diff >= 15  # 15+ point lead
        elif sport_tag in ("nfl", "football"):
            return diff >= 14  # 2+ touchdown lead
        elif sport_tag in ("mlb", "baseball"):
            return diff >= 5   # 5+ run lead
        elif sport_tag in ("cs2", "val", "valorant"):
            return diff >= 2 and max(a, b) >= 2  # 2-0 in BO3
        elif sport_tag in ("lol", "dota2"):
            return diff >= 2 and max(a, b) >= 2  # 2-0 in BO3
        elif sport_tag in ("soccer", "epl", "ucl", "laliga"):
            return diff >= 2   # 2+ goal lead
        elif sport_tag in ("tennis", "atp", "wta"):
            return diff >= 2   # 2 sets up in BO3
        else:
            return diff >= 2   # Generic: 2+ lead
    except (ValueError, IndexError):
        return False


def _days_to_resolution(end_date_iso: str) -> Optional[float]:
    """Calculate days until market resolution."""
    if not end_date_iso:
        return None
    try:
        from datetime import datetime, timezone
        end = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = (end - now).total_seconds() / 86400
        return delta
    except (ValueError, TypeError):
        return None
