# src/correlation.py
"""Correlation-aware exposure tracking -- limit total USD exposure per match.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #17
"""
from __future__ import annotations
import re


_STRIP_SUFFIXES = re.compile(
    r"-(map|game)-?\d+$|-(winner|over|under|total|to-win|handicap|spread|moneyline)$|-(first-.+)$"
)


def extract_match_key(slug: str) -> str:
    """Strip map/game/market-type suffixes to get the base match identifier."""
    return _STRIP_SUFFIXES.sub("", slug)


def get_match_exposure(match_key: str, positions: list[dict]) -> float:
    """Net USD exposure for a match key. BUY_YES=positive, BUY_NO=negative."""
    total = 0.0
    for pos in positions:
        if extract_match_key(pos["slug"]) == match_key:
            size = pos.get("size_usdc", 0.0)
            total += size if pos.get("direction") == "BUY_YES" else -size
    return abs(total)


MAX_MATCH_EXPOSURE_PCT = 0.15  # 15% of bankroll


def apply_correlation_cap(
    proposed_size: float,
    match_key: str,
    existing_positions: list[dict],
    bankroll: float,
    max_match_pct: float = MAX_MATCH_EXPOSURE_PCT,
) -> float:
    """Cap proposed_size so total match exposure stays within bankroll limit.
    Returns the capped size (may be 0 if limit already reached).
    NOTE: Intentionally conservative -- treats all new positions as additive
    regardless of direction. A BUY_NO on a BUY_YES-heavy match would technically
    reduce net exposure, but we cap conservatively for a real-money bot.
    Over-capping is safer than under-capping."""
    max_exposure = bankroll * max_match_pct
    current_net = get_match_exposure(match_key, existing_positions)
    remaining = max(0.0, max_exposure - current_net)
    return min(proposed_size, remaining)
