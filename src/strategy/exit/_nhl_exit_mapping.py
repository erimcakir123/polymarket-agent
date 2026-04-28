"""Map NHLExitDecision → NHLSignal (intermediate transport, no monitor.py import)."""
from __future__ import annotations

from dataclasses import dataclass

from src.strategy.exit.nhl_score_exit import ExitAction
from src.strategy.exit.nhl_score_exit import ExitReason as NHLExitReason
from src.strategy.exit.nhl_score_exit import NHLExitDecision
from src.strategy.exit.nhl_puck_line_exit import (
    NHLPuckLineExitDecision,
    ExitAction as PLExitAction,
    ExitReason as PLExitReason,
)
from src.models.enums import ExitReason

_REASON_MAP: dict[NHLExitReason, ExitReason] = {
    NHLExitReason.NEAR_RESOLVE: ExitReason.NHL_NEAR_RESOLVE,
    NHLExitReason.SCALE_OUT: ExitReason.NHL_SCALE_OUT,
    NHLExitReason.SHOOTOUT_PROFIT: ExitReason.NHL_SHOOTOUT_PROFIT,
    NHLExitReason.PREDICTIVE_DEAD: ExitReason.NHL_PREDICTIVE_DEAD,
    NHLExitReason.STRUCTURAL_DAMAGE: ExitReason.NHL_STRUCTURAL_DAMAGE,
}

_PUCK_LINE_REASON_MAP: dict[PLExitReason, ExitReason] = {
    PLExitReason.NEAR_RESOLVE: ExitReason.NHL_PUCK_LINE_NEAR_RESOLVE,
    PLExitReason.SCALE_OUT: ExitReason.NHL_PUCK_LINE_SCALE_OUT,
    PLExitReason.PREDICTIVE_DEAD: ExitReason.NHL_PUCK_LINE_PREDICTIVE_DEAD,
    PLExitReason.STRUCTURAL_DAMAGE: ExitReason.NHL_PUCK_LINE_STRUCTURAL_DAMAGE,
}


@dataclass(frozen=True)
class NHLSignal:
    reason: ExitReason
    partial: bool
    sell_pct: float
    detail: str


def map_nhl_decision(decision: NHLExitDecision) -> NHLSignal | None:
    """NHLExitDecision → NHLSignal. HOLD → None."""
    if decision.action == ExitAction.HOLD:
        return None
    reason = _REASON_MAP.get(decision.reason, ExitReason.SCORE_EXIT)
    detail = decision.note
    if decision.p_win is not None:
        detail += f" | p_win={decision.p_win:.3f} ({decision.p_win_source})"
    partial = decision.action == ExitAction.SELL_50
    return NHLSignal(
        reason=reason,
        partial=partial,
        sell_pct=0.50 if partial else 1.00,
        detail=detail,
    )


def map_nhl_puck_line_decision(decision: NHLPuckLineExitDecision) -> NHLSignal | None:
    """NHLPuckLineExitDecision -> NHLSignal. HOLD action → None."""
    if decision.action == PLExitAction.HOLD:
        return None
    reason = _PUCK_LINE_REASON_MAP.get(decision.reason, ExitReason.SCORE_EXIT)
    detail = decision.note
    if decision.p_cover is not None:
        detail += f" | p_cover={decision.p_cover:.3f} ({decision.p_cover_source})"
    partial = decision.action == PLExitAction.SELL_50
    return NHLSignal(
        reason=reason,
        partial=partial,
        sell_pct=0.50 if partial else 1.00,
        detail=detail,
    )
