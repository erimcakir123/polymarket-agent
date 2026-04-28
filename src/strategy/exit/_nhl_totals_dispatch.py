"""NHL totals dispatch: score_info + Position → NHLSignal | None.

monitor.py import YOK (circular safe).
Strategy katmanı, I/O yok.
"""
from __future__ import annotations

from src.domain.math.nhl_totals_probability import p_over_hybrid
from src.models.position import Position
from src.strategy.exit._nhl_exit_mapping import NHLSignal, map_nhl_totals_decision
from src.strategy.exit.nhl_totals_exit import NHLTotalsExitConfig, decide_nhl_totals_exit


def check_nhl_totals_exit(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,
    nhl_totals_cfg: NHLTotalsExitConfig,
    nhl_totals_table: dict,
) -> NHLSignal | None:
    """Decide NHL totals exit signal. Returns None → HOLD."""
    period = score_info.get("period") or score_info.get("period_number")
    clock_seconds = score_info.get("clock_seconds")
    our_score = score_info.get("our_score")
    opp_score = score_info.get("opp_score")

    target_total = getattr(pos, "total_line", None)
    side = getattr(pos, "total_side", None) or "over"

    if any(v is None for v in (period, clock_seconds, our_score, opp_score, target_total)):
        return None

    current_total = int(our_score + opp_score)

    def _p_fn(p: int, c: int, s: int, t: float) -> tuple[float, str]:
        return p_over_hybrid(p, c, s, t, table=nhl_totals_table)

    decision = decide_nhl_totals_exit(
        cfg=nhl_totals_cfg,
        entry_price=pos.entry_price,
        current_bid=pos.bid_price,
        current_price=pos.current_price,
        scaled_out_50=pos.scaled_out_50,
        period=period,
        seconds_remaining=clock_seconds,
        current_total=current_total,
        target_total=float(target_total),
        side=side,
        p_over_fn=_p_fn,
    )
    return map_nhl_totals_decision(decision)
