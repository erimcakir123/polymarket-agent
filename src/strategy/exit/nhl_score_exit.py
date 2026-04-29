"""NHL moneyline exit logic — priority-chain pure function."""
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
    SHOOTOUT_PROFIT = "SHOOTOUT_PROFIT"
    PREDICTIVE_DEAD = "PREDICTIVE_DEAD"
    STRUCTURAL_DAMAGE = "STRUCTURAL_DAMAGE"
    HOLD = "HOLD"


@dataclass(frozen=True)
class NHLExitDecision:
    action: ExitAction
    reason: ExitReason
    p_win: float | None  # None when win_probability_fn raised an exception
    p_win_source: str
    note: str


@dataclass(frozen=True)
class NHLExitConfig:
    near_resolve_threshold: float = 0.94
    scale_out_threshold: float = 0.85
    shootout_profit_threshold: float = 0.52
    structural_damage_ratio: float = 0.30
    predictive_safety_margin: float = 0.03


def decide_nhl_exit(
    *,
    cfg: NHLExitConfig,
    entry_price: float,
    current_bid: float,
    current_price: float,
    scaled_out_50: bool,
    period: int,
    seconds_remaining: int,
    abs_score_diff: int,
    we_are_leader: bool,  # direction handled by win_probability_fn closure (Task 3C)
    is_shootout: bool,
    win_probability_fn: Callable[[int, int, int], tuple[float, str]],  # MANDATORY — never None
) -> NHLExitDecision:
    """NHL moneyline exit decision via priority-chain pure function.

    Priority order:
    1. NEAR_RESOLVE  — bid >= near_resolve_threshold
    2. SCALE_OUT     — bid >= scale_out_threshold AND not yet scaled
    3. SHOOTOUT_PROFIT — is_shootout AND bid >= shootout_profit_threshold
    4. PREDICTIVE_DEAD — p_win < bid + predictive_safety_margin
    5. STRUCTURAL_DAMAGE — current_price / entry_price < structural_damage_ratio
    6. HOLD          — default
    """
    # --- 1. NEAR_RESOLVE ---
    if current_bid >= cfg.near_resolve_threshold:
        return NHLExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.NEAR_RESOLVE,
            p_win=1.0,
            p_win_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # --- 2. SCALE_OUT ---
    if not scaled_out_50 and current_bid >= cfg.scale_out_threshold:
        return NHLExitDecision(
            action=ExitAction.SELL_50,
            reason=ExitReason.SCALE_OUT,
            p_win=current_bid,
            p_win_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # --- 3. SHOOTOUT_PROFIT ---
    if is_shootout and current_bid >= cfg.shootout_profit_threshold:
        return NHLExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.SHOOTOUT_PROFIT,
            p_win=current_bid,
            p_win_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # --- 4. PREDICTIVE_DEAD ---
    try:
        p_win, p_win_source = win_probability_fn(period, abs_score_diff, seconds_remaining)
    except Exception:
        p_win = None
        p_win_source = "error"

    # PREDICTIVE_DEAD: NBA'nın "Q4 only" pattern'ı paraleli — sadece P3+ aktif.
    # P1/P2'de skor henüz "geri dönülemez" değil; empirical bile baz değer
    # üretir → false trigger riski. source=='empirical' şartı: empirical
    # wp_table yokken fallback wp bid'e yakın çıkıp false trigger üretebilir.
    if (
        period >= 3
        and p_win is not None
        and p_win_source == "empirical"
        and p_win < (current_bid + cfg.predictive_safety_margin)
    ):
        return NHLExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.PREDICTIVE_DEAD,
            p_win=p_win,
            p_win_source=p_win_source,
            note=f"p_win={p_win:.3f} bid={current_bid:.3f}",
        )

    # --- 5. STRUCTURAL_DAMAGE ---
    # Uses current_price (mid/last), NOT current_bid — bid can be artificially low in thin books
    if entry_price > 0 and (current_price / entry_price) < cfg.structural_damage_ratio:
        return NHLExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.STRUCTURAL_DAMAGE,
            p_win=p_win,
            p_win_source=p_win_source,
            note=f"ratio={current_price / entry_price:.2f}",
        )

    # --- 6. HOLD (default) ---
    return NHLExitDecision(
        action=ExitAction.HOLD,
        reason=ExitReason.HOLD,
        p_win=p_win,
        p_win_source=p_win_source,
        note="",
    )
