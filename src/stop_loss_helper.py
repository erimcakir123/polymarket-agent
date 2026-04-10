"""
stop_loss_helper.py -- Unified stop-loss percentage computation.

Single source of truth for all stop-loss rules. Called by both:
- exit_monitor._ws_check_exits() (WebSocket real-time path)
- portfolio.check_stop_losses() (cycle-based path)

Rules (in priority order):
1. Stale price skip (current_price ~0 and != entry) -> None
2. Totals/spread -> None (hold to resolution)
3. Volatility swing -> vs_sl_pct
4. Ultra-low entries (eff_entry < 9¢) -> 50% wide SL
5. Low-entry graduated (9-20¢) -> linear 60%->40%
6. B- confidence -> 30% tighter SL
7. Sport-specific SL (from sport_rules)
8. Esports BO5+ bonus (+10%, capped at 50%)
9. Lossy re-entry multiplier (75% of computed)
"""
from __future__ import annotations

import logging

from src.models import effective_price
from src.sport_rules import get_stop_loss

logger = logging.getLogger(__name__)


def compute_stop_loss_pct(
    pos,
    base_sl_pct: float = 0.30,
    vs_sl_pct: float = 0.20,
) -> float | None:
    """Compute the correct stop-loss percentage for a position.

    Returns:
        float: The SL percentage (e.g. 0.30 for 30%), OR
        None: If this position should SKIP stop-loss entirely.
    """
    # 1. Stale price skip (price never updated -> fake -100% PnL)
    if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
        return None

    # 2. Totals/spread: hold to resolution, no SL
    q = (getattr(pos, 'question', '') or '').lower()
    slug = (getattr(pos, 'slug', '') or '').lower()
    if any(k in q or k in slug for k in ('o/u', 'total', 'spread')):
        return None

    # 3. Volatility swing positions: their own SL
    if getattr(pos, 'volatility_swing', False):
        sl = vs_sl_pct
        # Lossy re-entry still applies to VS
        if getattr(pos, 'sl_reentry_count', 0) >= 1:
            sl *= 0.75
        return sl

    # Use effective entry price for BUY_NO (cost = 1 - yes_price)
    direction = getattr(pos, 'direction', 'BUY_YES')
    eff_entry = effective_price(pos.entry_price, direction)

    # 4. Ultra-low entries (eff_entry < 9¢): wide 50% SL
    if eff_entry < 0.09:
        sl = 0.50
    elif eff_entry < 0.20:
        # 5. Low-entry graduated (9-20¢): linear 60% -> 40%
        t = (eff_entry - 0.09) / (0.20 - 0.09)  # 0..1
        sl = 0.60 - t * 0.20  # 60% -> 40%
    elif getattr(pos, 'confidence', '') == 'B-':
        # 6. B- confidence: tighter 30% SL
        sl = 0.30
    else:
        # 7. Sport-specific SL
        sport_tag = getattr(pos, 'sport_tag', '') or ''
        sl = get_stop_loss(sport_tag)

        # 8. Esports BO5+ bonus
        category = getattr(pos, 'category', '') or ''
        num_games = getattr(pos, 'number_of_games', 0) or 0
        if category == 'esports' and num_games >= 5:
            sl += 0.10

    # 9. Lossy re-entry: tighter SL (75% of computed)
    if getattr(pos, 'sl_reentry_count', 0) >= 1:
        sl *= 0.75

    return sl
