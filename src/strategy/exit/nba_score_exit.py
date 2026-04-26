"""NBA score exit — Bill James formülü + empirical Q4 eşikleri."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.math.safe_lead import is_mathematically_dead, predictive_exit_decision_ml
from src.models.enums import ExitReason


@dataclass
class NbaCheckResult:
    reason: ExitReason
    detail: str
    sell_pct: float = 1.0
    partial: bool = False


def check(
    score_info: dict,
    elapsed_pct: float,
    sport_tag: str,
    bid_price: float = 0.0,
    entry_price: float = 0.0,
    bill_james_multiplier: float = 0.861,
    structural_damage_ratio: float = 0.30,
    ot_seconds: int = 60,
    ot_deficit: int = 8,
    q4_blowout_seconds: int = 720,
    q4_blowout_deficit: int = 20,
    q4_late_seconds: int = 360,
    q4_late_deficit: int = 15,
    q4_final_seconds: int = 180,
    q4_final_deficit: int = 10,
    q4_endgame_seconds: int = 60,
    q4_endgame_deficit: int = 6,
    predictive_enabled: bool = True,
    predictive_safety_margin: float = 0.03,
    predictive_hold_threshold: float = 0.20,
) -> NbaCheckResult | None:
    """NBA score-based exit kararı.

    Near-resolve (94c) ve scale-out (85c) monitor.py'de önce çalışır — burada yok.
    Return None → HOLD. Return NbaCheckResult → exit.
    """
    if not score_info.get("available"):
        return None

    period: int = score_info.get("period_number") or 0
    clock: int = score_info.get("clock_seconds") or 0
    deficit: int = score_info.get("deficit", 0)
    is_ot = period > 4

    # Q1-Q3: hiç tetiklenme (comeback ihtimali %5-13)
    if not is_ot and period < 4:
        return None

    # OT exit
    if is_ot and clock <= ot_seconds and deficit >= ot_deficit:
        return NbaCheckResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"OT_DEAD period={period} clock={clock}s deficit={deficit}",
        )

    # Q4 çıkışları (period == 4)
    if period == 4:
        # 1. Structural damage — fiyat çöküşü + matematiksel ölüm (önce kontrol)
        if (
            entry_price > 0
            and bid_price > 0
            and (bid_price / entry_price) < structural_damage_ratio
            and is_mathematically_dead(deficit, clock, bill_james_multiplier)
        ):
            return NbaCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"STRUCTURAL_DAMAGE price_ratio={bid_price/entry_price:.2f}",
            )

        # 2. Bill James mathematical dead
        if is_mathematically_dead(deficit, clock, bill_james_multiplier):
            return NbaCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"MATH_DEAD deficit={deficit} clock={clock}s",
            )

        # 3. Predictive dead (EV bazlı — math_dead tetiklemediyse)
        if predictive_enabled and predictive_exit_decision_ml(
            deficit=deficit,
            seconds=clock,
            current_bid=bid_price,
            safety_margin=predictive_safety_margin,
            hold_threshold=predictive_hold_threshold,
        ):
            return NbaCheckResult(
                reason=ExitReason.PREDICTIVE_DEAD,
                detail=f"PREDICTIVE_DEAD deficit={deficit} clock={clock}s bid={bid_price:.3f}",
            )

        # 4. Empirical backup (14-yıl NBA verisi)
        if _empirical_dead(
            clock, deficit,
            q4_blowout_seconds, q4_blowout_deficit,
            q4_late_seconds, q4_late_deficit,
            q4_final_seconds, q4_final_deficit,
            q4_endgame_seconds, q4_endgame_deficit,
        ):
            return NbaCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"EMPIRICAL_DEAD deficit={deficit} clock={clock}s",
            )

    return None


def _empirical_dead(
    clock: int,
    deficit: int,
    blowout_sec: int,
    blowout_def: int,
    late_sec: int,
    late_def: int,
    final_sec: int,
    final_def: int,
    endgame_sec: int,
    endgame_def: int,
) -> bool:
    """14-yıl NBA geri dönüş verisi — ~%1-3 ihtimal altı eşikler."""
    return (
        (clock <= blowout_sec and deficit >= blowout_def)
        or (clock <= late_sec and deficit >= late_def)
        or (clock <= final_sec and deficit >= final_def)
        or (clock <= endgame_sec and deficit >= endgame_def)
    )
