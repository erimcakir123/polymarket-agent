"""NHL puck line (-1.5) exit logic — priority-chain pure function."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


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
class NHLPuckLineExitDecision:
    action: ExitAction
    reason: ExitReason
    p_cover: float | None
    p_cover_source: str
    note: str


@dataclass(frozen=True)
class NHLPuckLineExitConfig:
    near_resolve_threshold: float = 0.94
    scale_out_threshold: float = 0.85
    structural_damage_ratio: float = 0.30
    predictive_safety_margin: float = 0.03


def decide_nhl_puck_line_exit(
    *,
    cfg: NHLPuckLineExitConfig,
    entry_price: float,
    current_bid: float,
    current_price: float,
    scaled_out_50: bool,
    period: int,
    seconds_remaining: int,
    current_margin: int,
    p_cover_fn: Callable[[int, int, int], tuple[float, str]],
) -> NHLPuckLineExitDecision:
    """NHL puck line (-1.5) exit kararı — priority chain.

    p_cover_fn signature: (period, current_margin, seconds_remaining) -> (p, source)
    Exception → p_cover=None, PREDICTIVE_DEAD skip.
    """
    # 1. NEAR_RESOLVE
    if current_bid >= cfg.near_resolve_threshold:
        return NHLPuckLineExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.NEAR_RESOLVE,
            p_cover=1.0,
            p_cover_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # 2. SCALE_OUT
    if not scaled_out_50 and current_bid >= cfg.scale_out_threshold:
        return NHLPuckLineExitDecision(
            action=ExitAction.SELL_50,
            reason=ExitReason.SCALE_OUT,
            p_cover=current_bid,
            p_cover_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # 3. PREDICTIVE_DEAD
    try:
        p_cover, p_cover_source = p_cover_fn(period, current_margin, seconds_remaining)
    except Exception:
        p_cover = None
        p_cover_source = "error"

    # PREDICTIVE_DEAD: NBA'nın "Q4 only" pattern'ı paraleli — sadece P3+ aktif.
    # P1/P2'de skor henüz "geri dönülemez" değil; empirical bile baz değer
    # üretir → false trigger riski. Ek olarak source=='empirical' şartı:
    # Skellam fallback NHL -1.5'i under-estimate ediyor (low-scoring + OT/SO
    # modifier yok). NEAR_RESOLVE/SCALE_OUT/STRUCTURAL_DAMAGE + dolar SL
    # erken oyunda da çalışmaya devam eder.
    if (
        period >= 3
        and p_cover is not None
        and p_cover_source == "empirical"
        and p_cover < (current_bid + cfg.predictive_safety_margin)
    ):
        return NHLPuckLineExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.PREDICTIVE_DEAD,
            p_cover=p_cover,
            p_cover_source=p_cover_source,
            note=f"p_cover={p_cover:.3f} bid={current_bid:.3f}",
        )

    # 4. STRUCTURAL_DAMAGE
    if entry_price > 0 and (current_price / entry_price) < cfg.structural_damage_ratio:
        return NHLPuckLineExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.STRUCTURAL_DAMAGE,
            p_cover=p_cover,
            p_cover_source=p_cover_source,
            note=f"ratio={current_price / entry_price:.2f}",
        )

    # 5. HOLD
    return NHLPuckLineExitDecision(
        action=ExitAction.HOLD,
        reason=ExitReason.HOLD,
        p_cover=p_cover,
        p_cover_source=p_cover_source,
        note="",
    )
