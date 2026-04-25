"""NBA totals exit — Poisson-based scoring pace + empirical backup."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.math.safe_lead import is_total_dead
from src.models.enums import ExitReason


@dataclass
class NbaTotalsCheckResult:
    reason: ExitReason
    detail: str
    sell_pct: float = 1.0
    partial: bool = False


def check(
    score_info: dict,
    target_total: float,
    side: str,
    bid_price: float = 0.0,
    entry_price: float = 0.0,
    totals_multiplier: float = 1.218,
    structural_damage_ratio: float = 0.30,
    ot_over_scale_pct: float = 0.75,
    q4_late_seconds: int = 360,
    q4_late_gap: int = 20,
    q4_final_seconds: int = 180,
    q4_final_gap: int = 12,
    q4_endgame_seconds: int = 60,
    q4_endgame_gap: int = 6,
) -> NbaTotalsCheckResult | None:
    """NBA totals exit kararı.

    Near-resolve ve scale-out monitor.py'de önce çalışır — burada yok.
    side: "over" (YES=over konvansiyonu) veya "under" (BUY_NO=under).
    Return None → HOLD. Return NbaTotalsCheckResult → exit.
    """
    if not score_info.get("available"):
        return None

    period: int = score_info.get("period_number") or 0
    clock: int = score_info.get("clock_seconds") or 0
    our_score: int = score_info.get("our_score") or 0
    opp_score: int = score_info.get("opp_score") or 0
    current_total = our_score + opp_score

    is_ot = period > 4

    # Q1-Q3: hold
    if not is_ot and period < 4:
        return None

    # OT — totals için özel
    if is_ot:
        if side == "over":
            return NbaTotalsCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"OT_OVER_WINDFALL period={period} current={current_total} target={target_total}",
                sell_pct=ot_over_scale_pct,
                partial=True,
            )
        else:
            return NbaTotalsCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"OT_UNDER_DEAD period={period} current={current_total} target={target_total}",
            )

    if period == 4:
        # 1. Structural damage
        if (
            entry_price > 0
            and bid_price > 0
            and (bid_price / entry_price) < structural_damage_ratio
            and is_total_dead(target_total, current_total, clock, side, totals_multiplier)
        ):
            return NbaTotalsCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"STRUCTURAL_DAMAGE price_ratio={bid_price/entry_price:.2f}",
            )

        # 2. Math dead
        if is_total_dead(target_total, current_total, clock, side, totals_multiplier):
            return NbaTotalsCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"TOTALS_MATH_DEAD current={current_total} target={target_total} clock={clock}s side={side}",
            )

        # 3. Empirical backup
        if _empirical_totals_dead(
            clock, current_total, target_total, side,
            q4_late_seconds, q4_late_gap,
            q4_final_seconds, q4_final_gap,
            q4_endgame_seconds, q4_endgame_gap,
        ):
            return NbaTotalsCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"EMPIRICAL_DEAD current={current_total} target={target_total} clock={clock}s side={side}",
            )

    return None


def _empirical_totals_dead(
    clock: int,
    current_total: int,
    target_total: float,
    side: str,
    late_sec: int,
    late_gap: int,
    final_sec: int,
    final_gap: int,
    endgame_sec: int,
    endgame_gap: int,
) -> bool:
    if side == "over":
        points_needed = target_total - current_total
        return (
            (clock <= late_sec and points_needed >= late_gap)
            or (clock <= final_sec and points_needed >= final_gap)
            or (clock <= endgame_sec and points_needed >= endgame_gap)
        )
    else:  # under
        excess = current_total - target_total
        return (
            (clock <= late_sec and excess >= late_gap)
            or (clock <= endgame_sec and excess >= endgame_gap)
        )
