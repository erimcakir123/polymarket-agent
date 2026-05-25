"""Distance-based partial profit-taking (scale-out).

Tier fires when price has covered `threshold` fraction of distance from entry
to $1.00 resolution:

    progress = (current_price - entry_price) / (1.0 - entry_price)

Scale-invariant across entry prices — a 19¢ entry and a 80¢ entry both fire
their tier 1 at ~40% of their respective journeys, locking substantial $ each
time. Replaces profit-percentage thresholds which locked $1-2 on cheap entries
and never fired on expensive entries.

Boundary equality uses math.isclose to absorb IEEE-754 rounding (e.g.
(0.52-0.20)/(1-0.20) == 0.39999999999999997 instead of 0.40 exactly), so a
price at the precise tier-trigger crossover still fires the tier.

Spec: docs/superpowers/plans/2026-05-25-distance-based-scale-out.md
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.config.settings import ScaleOutTier


@dataclass(frozen=True)
class ScaleOutDecision:
    tier: int           # 1-indexed: 1 = tier1 fired, 2 = tier2
    sell_pct: float     # of remaining shares to sell


def check_scale_out(
    *,
    scale_out_tier: int,
    entry_price: float,
    current_price: float,
    tiers: list[ScaleOutTier],
) -> ScaleOutDecision | None:
    """Return the next scale-out decision, or None if no tier fires.

    scale_out_tier: already-fired count (0=none, 1=tier1 done, etc.)
    entry_price:   original fill price (0 < entry < 1)
    current_price: latest market price
    tiers:         ordered list of ScaleOutTier (config.scale_out.tiers)
    """
    distance_to_resolution = 1.0 - entry_price
    if distance_to_resolution <= 0.0:
        return None

    progress = (current_price - entry_price) / distance_to_resolution

    next_tier_idx = scale_out_tier
    if next_tier_idx >= len(tiers):
        return None

    tier_cfg = tiers[next_tier_idx]
    if progress >= tier_cfg.threshold or math.isclose(progress, tier_cfg.threshold):
        return ScaleOutDecision(
            tier=next_tier_idx + 1,
            sell_pct=tier_cfg.sell_pct,
        )
    return None
