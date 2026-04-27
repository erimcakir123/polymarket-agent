"""NHL exit dispatch: score_info + Position → NHLSignal | None.

monitor.py import YOK (circular import önlemi).
Strategy katmanı: tablo dışarıdan inject edilir, I/O yok.
"""
from __future__ import annotations

from src.domain.math.nhl_win_probability import (
    leading_team_win_probability,
    trailing_team_win_probability,
)
from src.models.position import Position
from src.strategy.exit._nhl_exit_mapping import NHLSignal, map_nhl_decision
from src.strategy.exit.nhl_score_exit import NHLExitConfig, decide_nhl_exit


def check_nhl_exit(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,  # şimdilik kullanılmıyor ama imza gelecek için
    nhl_exit_cfg: NHLExitConfig,
    nhl_wp_table: dict,
) -> NHLSignal | None:
    """Decide NHL exit signal from score_info. Returns None → HOLD."""
    period = score_info.get("period") or score_info.get("period_number")
    clock_seconds = score_info.get("clock_seconds")
    our_score = score_info.get("our_score")
    opp_score = score_info.get("opp_score")
    is_shootout = score_info.get("is_shootout", False)

    if any(v is None for v in (period, clock_seconds, our_score, opp_score)):
        return None

    abs_score_diff = abs(our_score - opp_score)
    we_are_leader = our_score > opp_score  # tie → False (trailing fn, deficit=0)

    def _wp_fn(p: int, v: int, s: int) -> tuple[float, str]:
        if we_are_leader:
            return leading_team_win_probability(p, v, s, table=nhl_wp_table)
        return trailing_team_win_probability(p, v, s, table=nhl_wp_table)

    decision = decide_nhl_exit(
        cfg=nhl_exit_cfg,
        entry_price=pos.entry_price,
        current_bid=pos.bid_price,
        current_price=pos.current_price,
        scaled_out_50=pos.scaled_out_50,
        period=period,
        seconds_remaining=clock_seconds,
        abs_score_diff=abs_score_diff,
        we_are_leader=we_are_leader,
        is_shootout=is_shootout,
        win_probability_fn=_wp_fn,
    )
    return map_nhl_decision(decision)
