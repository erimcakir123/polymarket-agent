"""Map MLB exit decisions → MLBSignal (intermediate transport, no monitor.py import)."""
from __future__ import annotations

from dataclasses import dataclass

from src.models.enums import ExitReason
from src.strategy.exit.mlb_score_exit import (
    ExitAction,
    ExitReason as MLBExitReason,
    MLBExitDecision,
)
from src.strategy.exit.mlb_run_line_exit import (
    ExitAction as RLExitAction,
    ExitReason as RLExitReason,
    MLBRunLineExitDecision,
)
from src.strategy.exit.mlb_totals_exit import (
    ExitAction as TExitAction,
    ExitReason as TExitReason,
    MLBTotalsExitDecision,
)

_REASON_MAP: dict[MLBExitReason, ExitReason] = {
    MLBExitReason.NEAR_RESOLVE: ExitReason.MLB_NEAR_RESOLVE,
    MLBExitReason.SCALE_OUT: ExitReason.MLB_SCALE_OUT,
    MLBExitReason.M1_SEVENTH_DEFICIT_5: ExitReason.MLB_M1_SEVENTH_DEFICIT_5,
    MLBExitReason.M2_EIGHTH_DEFICIT_3: ExitReason.MLB_M2_EIGHTH_DEFICIT_3,
    MLBExitReason.M3_NINTH_DEFICIT_1: ExitReason.MLB_M3_NINTH_DEFICIT_1,
    MLBExitReason.PREDICTIVE_DEAD: ExitReason.MLB_PREDICTIVE_DEAD,
    MLBExitReason.STRUCTURAL_DAMAGE: ExitReason.MLB_STRUCTURAL_DAMAGE,
}

_RUN_LINE_REASON_MAP: dict[RLExitReason, ExitReason] = {
    RLExitReason.NEAR_RESOLVE: ExitReason.MLB_RUN_LINE_NEAR_RESOLVE,
    RLExitReason.SCALE_OUT: ExitReason.MLB_RUN_LINE_SCALE_OUT,
    RLExitReason.M1_SEVENTH_DEFICIT_5: ExitReason.MLB_M1_SEVENTH_DEFICIT_5,
    RLExitReason.M2_EIGHTH_DEFICIT_3: ExitReason.MLB_M2_EIGHTH_DEFICIT_3,
    RLExitReason.M3_NINTH_DEFICIT_1: ExitReason.MLB_M3_NINTH_DEFICIT_1,
    RLExitReason.PREDICTIVE_DEAD: ExitReason.MLB_RUN_LINE_PREDICTIVE_DEAD,
    RLExitReason.STRUCTURAL_DAMAGE: ExitReason.MLB_RUN_LINE_STRUCTURAL_DAMAGE,
}

_TOTALS_REASON_MAP: dict[TExitReason, ExitReason] = {
    TExitReason.NEAR_RESOLVE: ExitReason.MLB_TOTALS_NEAR_RESOLVE,
    TExitReason.SCALE_OUT: ExitReason.MLB_TOTALS_SCALE_OUT,
    TExitReason.PREDICTIVE_DEAD: ExitReason.MLB_TOTALS_PREDICTIVE_DEAD,
    TExitReason.STRUCTURAL_DAMAGE: ExitReason.MLB_TOTALS_STRUCTURAL_DAMAGE,
}


@dataclass(frozen=True)
class MLBSignal:
    reason: ExitReason
    partial: bool
    sell_pct: float
    detail: str


def map_mlb_decision(decision: MLBExitDecision) -> MLBSignal | None:
    """MLBExitDecision → MLBSignal. HOLD → None."""
    if decision.action == ExitAction.HOLD:
        return None
    reason = _REASON_MAP.get(decision.reason, ExitReason.SCORE_EXIT)
    detail = decision.note
    if decision.p_win is not None:
        detail += f" | p_win={decision.p_win:.3f} ({decision.p_win_source})"
    partial = decision.action == ExitAction.SELL_50
    return MLBSignal(
        reason=reason, partial=partial,
        sell_pct=0.50 if partial else 1.00, detail=detail,
    )


def map_mlb_run_line_decision(decision: MLBRunLineExitDecision) -> MLBSignal | None:
    """MLBRunLineExitDecision → MLBSignal. HOLD → None."""
    if decision.action == RLExitAction.HOLD:
        return None
    reason = _RUN_LINE_REASON_MAP.get(decision.reason, ExitReason.SCORE_EXIT)
    detail = decision.note
    if decision.p_cover is not None:
        detail += f" | p_cover={decision.p_cover:.3f} ({decision.p_cover_source})"
    partial = decision.action == RLExitAction.SELL_50
    return MLBSignal(
        reason=reason, partial=partial,
        sell_pct=0.50 if partial else 1.00, detail=detail,
    )


def map_mlb_totals_decision(decision: MLBTotalsExitDecision) -> MLBSignal | None:
    """MLBTotalsExitDecision → MLBSignal. HOLD → None."""
    if decision.action == TExitAction.HOLD:
        return None
    reason = _TOTALS_REASON_MAP.get(decision.reason, ExitReason.SCORE_EXIT)
    detail = decision.note
    if decision.p_over_remaining is not None:
        detail += f" | p_over={decision.p_over_remaining:.3f} ({decision.p_over_source})"
    partial = decision.action == TExitAction.SELL_50
    return MLBSignal(
        reason=reason, partial=partial,
        sell_pct=0.50 if partial else 1.00, detail=detail,
    )
