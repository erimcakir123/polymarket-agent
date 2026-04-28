"""Guard helper'ları — monitor.py'dan extract (satır limit koruma).

Pure: pos + elapsed + score_info + cfg → bool. I/O yok.
"""
from __future__ import annotations

from src.config.settings import ExitMonitorConfig
from src.models.position import Position

_DEFAULT_MONITOR_CFG = ExitMonitorConfig()


def never_in_profit_exit_check(
    pos: Position,
    elapsed_pct: float,
    score_info: dict,
    cfg: ExitMonitorConfig = _DEFAULT_MONITOR_CFG,
) -> bool:
    """Never-in-profit guard (TDD §6.10).

    pos hiç kâra geçmedi + maç ≥ elapsed_gate + fiyat çok düştü → True.
    """
    if pos.ever_in_profit or pos.peak_pnl_pct > 0.01:
        return False
    if elapsed_pct < cfg.never_in_profit_elapsed_gate:
        return False
    eff_entry = pos.entry_price
    eff_current = pos.bid_price
    score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
    if score_ahead:
        return False
    if eff_current >= eff_entry * cfg.never_in_profit_recovery_ratio:
        return False
    if eff_current < eff_entry * cfg.never_in_profit_drop_ratio:
        return True
    return False  # recovery_ratio ~ drop_ratio aralığı: bekle
