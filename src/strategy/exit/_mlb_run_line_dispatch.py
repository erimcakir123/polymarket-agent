"""MLB run line exit dispatch: ESPN score_info + Position → MLBSignal | None.

v1 simplification: cover_probability_fn uses WE lookup as proxy for cover.
v2 candidate: explicit margin-coverage probability with remaining innings.

monitor.py import YOK (circular import önlemi).
Strategy katmanı: I/O yok, ESPN dict caller tarafından dolu gelir.
"""
from __future__ import annotations

from src.domain.math.mlb_win_expectancy import encode_base_state, lookup_win_expectancy
from src.models.position import Position
from src.strategy.exit._mlb_exit_mapping import MLBSignal, map_mlb_run_line_decision
from src.strategy.exit.mlb_run_line_exit import (
    MLBRunLineExitConfig,
    decide_mlb_run_line_exit,
)


def check_mlb_run_line_exit(
    pos: Position,
    score_info: dict,
    rl_exit_cfg: MLBRunLineExitConfig,
) -> MLBSignal | None:
    """Decide MLB Run Line exit signal from score_info. Returns None → HOLD."""
    inning = score_info.get("period_number") or score_info.get("inning")
    if not isinstance(inning, int) or inning <= 0:
        return None

    outs = score_info.get("outs", 0)
    on_first = score_info.get("on_first", False)
    on_second = score_info.get("on_second", False)
    on_third = score_info.get("on_third", False)
    home_score = score_info.get("home_score")
    away_score = score_info.get("away_score")
    if home_score is None or away_score is None:
        return None

    base_state = encode_base_state(on_first, on_second, on_third)
    run_diff = home_score - away_score
    is_home = bool(score_info.get("is_home_position", True))

    def _cover_fn(period: int, _abs_diff: int, outs_param: int) -> tuple[float, str]:
        we = lookup_win_expectancy(period, outs_param, base_state, run_diff, is_home=is_home)
        return (we, "table" if we != 0.5 else "fallback")

    decision = decide_mlb_run_line_exit(
        cfg=rl_exit_cfg,
        entry_price=pos.entry_price,
        current_bid=pos.bid_price,
        current_price=pos.current_price,
        scaled_out_50=pos.scaled_out_50,
        inning=inning,
        outs=outs,
        base_state=base_state,
        run_diff=run_diff,
        is_home_position=is_home,
        cover_probability_fn=_cover_fn,
    )
    return map_mlb_run_line_decision(decision)
