"""Position cycle-bazlı state güncellemeleri — pure (TDD §6.8 momentum + §6.10 ever_in_profit).

Her light cycle'da Position üzerinde:
  - peak_pnl_pct + peak_price (§6.6 scale-out, §6.10 never-in-profit)
  - ever_in_profit (§6.10)
  - consecutive_down_cycles + cumulative_drop (§6.8 graduated SL momentum)
  - previous_cycle_price + cycles_held
"""
from __future__ import annotations

from src.models.position import Position

_PROFIT_FLAG_THRESHOLD = 0.01  # +1% PnL → ever_in_profit


def tick_position_state(pos: Position) -> None:
    """Cycle-bazlı state mutate. Çağıran light cycle / agent."""
    pnl_pct = pos.unrealized_pnl_pct
    if pnl_pct > pos.peak_pnl_pct:
        pos.peak_pnl_pct = pnl_pct
        pos.peak_price = pos.current_price
    if pnl_pct > _PROFIT_FLAG_THRESHOLD and not pos.ever_in_profit:
        pos.ever_in_profit = True

    # Momentum tracking (graduated SL için)
    prev = pos.previous_cycle_price or pos.entry_price
    if pos.current_price < prev:
        pos.consecutive_down_cycles += 1
        pos.cumulative_drop += (prev - pos.current_price)
    else:
        pos.consecutive_down_cycles = 0
        pos.cumulative_drop = 0.0

    pos.previous_cycle_price = pos.current_price
    pos.cycles_held += 1
