"""NBA spread exit — Bill James cover math + empirical key numbers."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.math.safe_lead import is_spread_dead
from src.models.enums import ExitReason


@dataclass
class NbaSpreadCheckResult:
    reason: ExitReason
    detail: str
    sell_pct: float = 1.0
    partial: bool = False


def check(
    score_info: dict,
    spread_line: float,
    direction: str,
    bid_price: float = 0.0,
    entry_price: float = 0.0,
    bill_james_multiplier: float = 0.861,
    structural_damage_ratio: float = 0.30,
    ot_seconds: int = 60,
    ot_margin: int = 8,
    q4_late_seconds: int = 360,
    q4_late_margin: int = 7,
    q4_final_seconds: int = 180,
    q4_final_margin: int = 4,
    q4_endgame_seconds: int = 60,
    q4_endgame_margin: int = 3,
) -> NbaSpreadCheckResult | None:
    """NBA spread cover exit kararı.

    Near-resolve ve scale-out monitor.py'de önce çalışır — burada yok.
    Return None → HOLD. Return NbaSpreadCheckResult → exit.

    BUY_YES (favorite covers): margin_to_cover = spread_line - (our_score - opp_score)
    BUY_NO  (underdog covers): margin_to_cover = -(our_score - opp_score) - spread_line
    """
    if not score_info.get("available"):
        return None

    period: int = score_info.get("period_number") or 0
    clock: int = score_info.get("clock_seconds") or 0
    our_score: int = score_info.get("our_score") or 0
    opp_score: int = score_info.get("opp_score") or 0

    actual_diff = our_score - opp_score

    if direction == "BUY_YES":
        margin_to_cover = spread_line - actual_diff
    else:
        margin_to_cover = -actual_diff - spread_line

    is_ot = period > 4

    # Q1-Q3: hold
    if not is_ot and period < 4:
        return None

    # OT exit
    if is_ot and clock <= ot_seconds and margin_to_cover >= ot_margin:
        return NbaSpreadCheckResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"OT_DEAD period={period} clock={clock}s margin={margin_to_cover:.1f}",
        )

    if period == 4:
        # 1. Structural damage — fiyat çöküşü + math dead
        if (
            entry_price > 0
            and bid_price > 0
            and (bid_price / entry_price) < structural_damage_ratio
            and is_spread_dead(margin_to_cover, clock, bill_james_multiplier)
        ):
            return NbaSpreadCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"STRUCTURAL_DAMAGE price_ratio={bid_price/entry_price:.2f} margin={margin_to_cover:.1f}",
            )

        # 2. Bill James spread dead
        if is_spread_dead(margin_to_cover, clock, bill_james_multiplier):
            return NbaSpreadCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"SPREAD_MATH_DEAD margin={margin_to_cover:.1f} clock={clock}s",
            )

        # 3. Empirical key numbers (NBA spread: 3 ve 7 kritik)
        if _empirical_spread_dead(
            clock, margin_to_cover,
            q4_late_seconds, q4_late_margin,
            q4_final_seconds, q4_final_margin,
            q4_endgame_seconds, q4_endgame_margin,
        ):
            return NbaSpreadCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"EMPIRICAL_DEAD margin={margin_to_cover:.1f} clock={clock}s",
            )

    return None


def _empirical_spread_dead(
    clock: int,
    margin: float,
    late_sec: int,
    late_mar: int,
    final_sec: int,
    final_mar: int,
    endgame_sec: int,
    endgame_mar: int,
) -> bool:
    return (
        (clock <= late_sec and margin >= late_mar)
        or (clock <= final_sec and margin >= final_mar)
        or (clock <= endgame_sec and margin >= endgame_mar)
    )
