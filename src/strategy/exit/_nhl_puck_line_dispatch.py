"""NHL puck line dispatch: score_info + Position → NHLSignal | None.

monitor.py import YOK (circular import önlemi).
Strategy katmanı: tablo dışarıdan inject edilir, I/O yok.
"""
from __future__ import annotations

from src.domain.math.nhl_puck_line_probability import p_favorite_covers_hybrid
from src.models.position import Position
from src.strategy.exit._nhl_exit_mapping import NHLSignal, map_nhl_puck_line_decision
from src.strategy.exit.nhl_puck_line_exit import (
    NHLPuckLineExitConfig,
    decide_nhl_puck_line_exit,
)


def check_nhl_puck_line_exit(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,  # şimdilik kullanılmıyor, signature uyum
    nhl_puck_line_cfg: NHLPuckLineExitConfig,
    nhl_puck_line_table: dict,
) -> NHLSignal | None:
    """Decide NHL puck line exit signal. Returns None → HOLD."""
    period = score_info.get("period") or score_info.get("period_number")
    clock_seconds = score_info.get("clock_seconds")
    our_score = score_info.get("our_score")
    opp_score = score_info.get("opp_score")

    if any(v is None for v in (period, clock_seconds, our_score, opp_score)):
        return None

    direction = getattr(pos, "direction", "BUY_YES")
    if direction == "BUY_YES":
        current_margin = our_score - opp_score
    else:
        current_margin = opp_score - our_score

    def _p_fn(p: int, m: int, s: int) -> tuple[float, str]:
        return p_favorite_covers_hybrid(p, m, s, table=nhl_puck_line_table)

    decision = decide_nhl_puck_line_exit(
        cfg=nhl_puck_line_cfg,
        entry_price=pos.entry_price,
        current_bid=pos.bid_price,
        current_price=pos.current_price,
        scaled_out_50=pos.scaled_out_50,
        period=period,
        seconds_remaining=clock_seconds,
        current_margin=current_margin,
        p_cover_fn=_p_fn,
    )
    return map_nhl_puck_line_decision(decision)
