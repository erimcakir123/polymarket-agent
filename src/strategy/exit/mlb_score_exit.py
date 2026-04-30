# src/strategy/exit/mlb_score_exit.py
"""MLB moneyline exit logic — priority-chain pure function.

Mirrors NHL score exit pattern. MLB-specific:
- M1/M2/M3 deficit rules from DECISIONS.md SPEC-014
- PREDICTIVE_DEAD margin 0.04 (vs NHL 0.03; MLB variance higher)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class ExitAction(str, Enum):
    HOLD = "HOLD"
    SELL_50 = "SELL_50"
    SELL_ALL = "SELL_ALL"


class ExitReason(str, Enum):
    NEAR_RESOLVE = "NEAR_RESOLVE"
    SCALE_OUT = "SCALE_OUT"
    M1_SEVENTH_DEFICIT_5 = "M1_SEVENTH_DEFICIT_5"
    M2_EIGHTH_DEFICIT_3 = "M2_EIGHTH_DEFICIT_3"
    M3_NINTH_DEFICIT_1 = "M3_NINTH_DEFICIT_1"
    PREDICTIVE_DEAD = "PREDICTIVE_DEAD"
    STRUCTURAL_DAMAGE = "STRUCTURAL_DAMAGE"
    HOLD = "HOLD"


@dataclass(frozen=True)
class MLBExitDecision:
    action: ExitAction
    reason: ExitReason
    p_win: float | None
    p_win_source: str
    note: str


@dataclass(frozen=True)
class MLBExitConfig:
    near_resolve_threshold: float
    scale_out_threshold: float
    structural_damage_ratio: float
    predictive_safety_margin: float


_M1_INNING_THRESHOLD: int = 7
_M1_DEFICIT_THRESHOLD: int = 5
_M2_INNING_THRESHOLD: int = 8
_M2_DEFICIT_THRESHOLD: int = 3
_M3_INNING_THRESHOLD: int = 9
_M3_DEFICIT_THRESHOLD: int = 1
_PREDICTIVE_INNING_FLOOR: int = 6


def decide_mlb_score_exit(
    *,
    cfg: MLBExitConfig,
    entry_price: float,
    current_bid: float,
    current_price: float,
    scaled_out_50: bool,
    inning: int,
    outs: int,
    base_state: int,
    run_diff: int,
    is_home_position: bool,
    win_probability_fn: Callable[[int, int, int], tuple[float, str]],
) -> MLBExitDecision:
    """MLB moneyline exit decision."""
    if current_bid >= cfg.near_resolve_threshold:
        return MLBExitDecision(
            ExitAction.SELL_ALL, ExitReason.NEAR_RESOLVE,
            1.0, "price", f"bid={current_bid:.3f}",
        )

    if not scaled_out_50 and current_bid >= cfg.scale_out_threshold:
        return MLBExitDecision(
            ExitAction.SELL_50, ExitReason.SCALE_OUT,
            current_bid, "price", f"bid={current_bid:.3f}",
        )

    deficit = -run_diff if is_home_position else run_diff

    if inning >= _M3_INNING_THRESHOLD and deficit >= _M3_DEFICIT_THRESHOLD:
        return MLBExitDecision(
            ExitAction.SELL_ALL, ExitReason.M3_NINTH_DEFICIT_1,
            None, "rule", f"inning={inning} def={deficit}",
        )
    if inning >= _M2_INNING_THRESHOLD and deficit >= _M2_DEFICIT_THRESHOLD:
        return MLBExitDecision(
            ExitAction.SELL_ALL, ExitReason.M2_EIGHTH_DEFICIT_3,
            None, "rule", f"inning={inning} def={deficit}",
        )
    if inning >= _M1_INNING_THRESHOLD and deficit >= _M1_DEFICIT_THRESHOLD:
        return MLBExitDecision(
            ExitAction.SELL_ALL, ExitReason.M1_SEVENTH_DEFICIT_5,
            None, "rule", f"inning={inning} def={deficit}",
        )

    try:
        p_win, p_win_source = win_probability_fn(inning, abs(run_diff), outs)
    except Exception:
        logger.warning(
            "win_probability_fn raised inning=%s diff=%s outs=%s",
            inning, run_diff, outs, exc_info=True,
        )
        p_win = None
        p_win_source = "error"

    if (
        inning >= _PREDICTIVE_INNING_FLOOR
        and p_win is not None
        and p_win_source == "table"
        and p_win < (current_bid + cfg.predictive_safety_margin)
    ):
        return MLBExitDecision(
            ExitAction.SELL_ALL, ExitReason.PREDICTIVE_DEAD,
            p_win, p_win_source, f"p={p_win:.3f} bid={current_bid:.3f}",
        )

    if entry_price > 0 and (current_price / entry_price) < cfg.structural_damage_ratio:
        return MLBExitDecision(
            ExitAction.SELL_ALL, ExitReason.STRUCTURAL_DAMAGE,
            p_win, p_win_source, f"ratio={current_price / entry_price:.2f}",
        )

    return MLBExitDecision(
        ExitAction.HOLD, ExitReason.HOLD,
        p_win, p_win_source, "",
    )
