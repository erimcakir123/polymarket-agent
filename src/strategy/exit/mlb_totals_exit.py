# src/strategy/exit/mlb_totals_exit.py
"""MLB Totals exit logic — priority-chain pure function.

Mirrors NHL totals exit pattern. MLB-specific:
- NO M1/M2/M3 (totals doesn't care about score deficit, only total runs)
- PREDICTIVE_DEAD via p_over_remaining (Poisson on innings remaining)
- PREDICTIVE_DEAD margin 0.04 (MLB variance)
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
    PREDICTIVE_DEAD = "PREDICTIVE_DEAD"
    STRUCTURAL_DAMAGE = "STRUCTURAL_DAMAGE"
    HOLD = "HOLD"


@dataclass(frozen=True)
class MLBTotalsExitDecision:
    action: ExitAction
    reason: ExitReason
    p_over_remaining: float | None
    p_over_source: str
    note: str


@dataclass(frozen=True)
class MLBTotalsExitConfig:
    near_resolve_threshold: float
    scale_out_threshold: float
    structural_damage_ratio: float
    predictive_safety_margin: float


_PREDICTIVE_INNING_FLOOR: int = 6


def decide_mlb_totals_exit(
    *,
    cfg: MLBTotalsExitConfig,
    entry_price: float,
    current_bid: float,
    current_price: float,
    scaled_out_50: bool,
    inning: int,
    outs: int,
    current_total: int,
    is_over_position: bool,
    over_probability_fn: Callable[[int, int, int], tuple[float, str]],
) -> MLBTotalsExitDecision:
    """MLB Totals exit decision."""
    if current_bid >= cfg.near_resolve_threshold:
        return MLBTotalsExitDecision(
            ExitAction.SELL_ALL, ExitReason.NEAR_RESOLVE,
            1.0, "price", f"bid={current_bid:.3f}",
        )

    if not scaled_out_50 and current_bid >= cfg.scale_out_threshold:
        return MLBTotalsExitDecision(
            ExitAction.SELL_50, ExitReason.SCALE_OUT,
            current_bid, "price", f"bid={current_bid:.3f}",
        )

    try:
        p_over, p_over_source = over_probability_fn(inning, current_total, outs)
    except Exception:
        logger.warning(
            "over_probability_fn raised inning=%s total=%s outs=%s",
            inning, current_total, outs, exc_info=True,
        )
        p_over = None
        p_over_source = "error"

    # Direction-adjust: if we backed UNDER, our success is 1 - p_over
    if p_over is not None:
        p_position = p_over if is_over_position else (1.0 - p_over)
    else:
        p_position = None

    if (
        inning >= _PREDICTIVE_INNING_FLOOR
        and p_position is not None
        and p_over_source == "table"
        and p_position < (current_bid + cfg.predictive_safety_margin)
    ):
        return MLBTotalsExitDecision(
            ExitAction.SELL_ALL, ExitReason.PREDICTIVE_DEAD,
            p_over, p_over_source, f"p={p_position:.3f} bid={current_bid:.3f}",
        )

    if entry_price > 0 and (current_price / entry_price) < cfg.structural_damage_ratio:
        return MLBTotalsExitDecision(
            ExitAction.SELL_ALL, ExitReason.STRUCTURAL_DAMAGE,
            p_over, p_over_source, f"ratio={current_price / entry_price:.2f}",
        )

    return MLBTotalsExitDecision(
        ExitAction.HOLD, ExitReason.HOLD,
        p_over, p_over_source, "",
    )
