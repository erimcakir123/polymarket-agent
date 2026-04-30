"""NHL totals (over/under) exit logic — priority chain pure function."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Literal

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
class NHLTotalsExitDecision:
    action: ExitAction
    reason: ExitReason
    p_side: float | None
    p_source: str
    note: str


@dataclass(frozen=True)
class NHLTotalsExitConfig:
    near_resolve_threshold: float = 0.94
    scale_out_threshold: float = 0.85
    structural_damage_ratio: float = 0.30
    predictive_safety_margin: float = 0.03


def decide_nhl_totals_exit(
    *,
    cfg: NHLTotalsExitConfig,
    entry_price: float,
    current_bid: float,
    current_price: float,
    scaled_out_50: bool,
    period: int,
    seconds_remaining: int,
    current_total: int,
    target_total: float,
    side: Literal["over", "under"],
    p_over_fn: Callable[[int, int, int, float], tuple[float, str]],
) -> NHLTotalsExitDecision:
    """NHL totals over/under exit — priority chain.

    side: "over" (BUY_YES) veya "under" (BUY_NO).
    p_over_fn: (period, current_total, seconds_remaining, target_total) -> (p_over, source)
    Under için p_side = 1 - p_over.
    """
    # 1. NEAR_RESOLVE
    if current_bid >= cfg.near_resolve_threshold:
        return NHLTotalsExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.NEAR_RESOLVE,
            p_side=1.0, p_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # 2. SCALE_OUT
    if not scaled_out_50 and current_bid >= cfg.scale_out_threshold:
        return NHLTotalsExitDecision(
            action=ExitAction.SELL_50,
            reason=ExitReason.SCALE_OUT,
            p_side=current_bid, p_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # 3. PREDICTIVE_DEAD
    try:
        p_over, p_source = p_over_fn(period, current_total, seconds_remaining, target_total)
    except Exception:
        logger.warning(
            "p_over_fn raised; skipping PREDICTIVE_DEAD (period=%s total=%s sec=%s target=%s)",
            period, current_total, seconds_remaining, target_total, exc_info=True,
        )
        p_over = None
        p_source = "error"

    p_side: float | None = None
    if p_over is not None:
        p_side = p_over if side == "over" else (1.0 - p_over)

    # PREDICTIVE_DEAD: NBA'nın "Q4 only" pattern'ı paraleli — sadece P3+ aktif.
    # P1/P2'de over/under henüz kesinleşmedi; empirical bile baz değer üretir
    # → false trigger riski. source=='empirical' şartı: Skellam fallback
    # totals'da da bid'e yakın çıkıp false trigger üretebilir.
    if (
        period >= 3
        and p_side is not None
        and p_source == "empirical"
        and p_side < (current_bid + cfg.predictive_safety_margin)
    ):
        return NHLTotalsExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.PREDICTIVE_DEAD,
            p_side=p_side, p_source=p_source,
            note=f"p_{side}={p_side:.3f} bid={current_bid:.3f}",
        )

    # 4. STRUCTURAL_DAMAGE
    if entry_price > 0 and (current_price / entry_price) < cfg.structural_damage_ratio:
        return NHLTotalsExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.STRUCTURAL_DAMAGE,
            p_side=p_side, p_source=p_source,
            note=f"ratio={current_price/entry_price:.2f}",
        )

    # 5. HOLD
    return NHLTotalsExitDecision(
        action=ExitAction.HOLD,
        reason=ExitReason.HOLD,
        p_side=p_side, p_source=p_source,
        note="",
    )
