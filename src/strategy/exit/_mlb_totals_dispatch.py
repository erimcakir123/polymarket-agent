"""MLB totals exit dispatch: ESPN score_info + Position → MLBSignal | None.

v1 simplification: over_probability_fn uses simple linear extrapolation.
v2 candidate: full Poisson on remaining innings.

monitor.py import YOK (circular import önlemi).
Strategy katmanı: I/O yok, ESPN dict caller tarafından dolu gelir.
"""
from __future__ import annotations

from src.models.position import Position
from src.strategy.exit._mlb_exit_mapping import MLBSignal, map_mlb_totals_decision
from src.strategy.exit.mlb_totals_exit import (
    MLBTotalsExitConfig,
    decide_mlb_totals_exit,
)

_INNINGS_TOTAL: int = 9


def check_mlb_totals_exit(
    pos: Position,
    score_info: dict,
    totals_exit_cfg: MLBTotalsExitConfig,
    over_under_line: float,
) -> MLBSignal | None:
    """Decide MLB Totals exit signal from score_info. Returns None → HOLD."""
    inning = score_info.get("period_number") or score_info.get("inning")
    if not isinstance(inning, int) or inning <= 0:
        return None

    outs = score_info.get("outs", 0)
    home_score = score_info.get("home_score")
    away_score = score_info.get("away_score")
    if home_score is None or away_score is None:
        return None

    current_total = home_score + away_score
    is_over_position = bool(score_info.get("is_over_position", True))

    def _over_fn(inning_param: int, total_param: int, _outs: int) -> tuple[float, str]:
        # v1 linear proxy: P(over) based on projected final total vs line
        innings_remaining = max(0, _INNINGS_TOTAL - inning_param + 1)
        if innings_remaining <= 0:
            # Game ending — over only if total_param > line
            return (1.0 if total_param > over_under_line else 0.0, "table")
        if inning_param > 0:
            projected_final = total_param * (_INNINGS_TOTAL / inning_param)
        else:
            projected_final = total_param * 2  # ratio fallback
        # Crude probability bucket
        if projected_final > over_under_line + 1:
            return (0.85, "table")
        if projected_final < over_under_line - 1:
            return (0.15, "table")
        return (0.5, "fallback")

    decision = decide_mlb_totals_exit(
        cfg=totals_exit_cfg,
        entry_price=pos.entry_price,
        current_bid=pos.bid_price,
        current_price=pos.current_price,
        scaled_out_50=pos.scaled_out_50,
        inning=inning,
        outs=outs,
        current_total=current_total,
        is_over_position=is_over_position,
        over_probability_fn=_over_fn,
    )
    return map_mlb_totals_decision(decision)
