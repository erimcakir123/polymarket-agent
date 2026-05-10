"""NBA spread exit — 5-katman pipeline (SPEC-J §Spread exit pipeline).

Pre-rollback'ten mantık migrate (kod taze yazıldı):
  1. OT_DEAD          — period > 4, son 60s, margin ≥ 8.
  2. STRUCTURAL_DAMAGE — Q4, bid/entry < 0.30, Bill James math dead.
  3. SPREAD_MATH_DEAD — Q4, Bill James 0.861 multiplier.
  4. PREDICTIVE_DEAD  — Q4, EV bazlı (comeback < hold ve bid + safety > comeback).
  5. EMPIRICAL_DEAD   — Q4, key numbers (7/4/3) ile son-dakika.

Strategy katmanı: I/O yok, log yok, saf karar.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.math.safe_lead import is_spread_dead, predictive_exit_decision_spread
from src.models.enums import Direction, ExitReason
from src.strategy.exit._nba_score_mapper import map_our_opp_scores


@dataclass
class NbaSpreadCheckResult:
    reason: ExitReason
    detail: str
    sell_pct: float = 1.0
    partial: bool = False


def check(
    score_info: dict,
    spread_line: float,
    direction: str,            # Direction.BUY_YES.value | BUY_NO.value
    spread_side: str,          # "home" | "away"
    bid_price: float,
    entry_price: float,
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
    predictive_enabled: bool = True,
    predictive_safety_margin: float = 0.03,
    predictive_hold_threshold: float = 0.20,
) -> NbaSpreadCheckResult | None:
    """NBA spread cover exit kararı. None → HOLD; sonuç → EXIT.

    Near-resolve / scale-out monitor.py'da önce çalışır — burada yok.

    Margin formülü (pre-rollback'ten birebir, kanıtlanmış):
      BUY_YES: margin_to_cover = spread_line - actual_diff
      BUY_NO:  margin_to_cover = -actual_diff - spread_line
    actual_diff = our_score - opp_score (mapper our/opp swap'ı yapar).
    """
    if not score_info.get("available"):
        return None

    period: int = score_info.get("period_number", 0) or 0
    clock: int = score_info.get("clock_seconds", 0) or 0
    home_score: int = score_info.get("home_score", 0) or 0
    away_score: int = score_info.get("away_score", 0) or 0

    our_score, opp_score = map_our_opp_scores(
        home_score=home_score,
        away_score=away_score,
        direction=direction,
        spread_side=spread_side,
    )
    actual_diff = our_score - opp_score

    if direction == Direction.BUY_YES.value:
        margin_to_cover = spread_line - actual_diff
    else:
        margin_to_cover = -actual_diff - spread_line

    is_ot = period > 4

    # Q1-Q3 → HOLD (pipeline sadece Q4 ve OT'de çalışır).
    if not is_ot and period < 4:
        return None

    # Layer 1 — OT_DEAD
    if is_ot and clock <= ot_seconds and margin_to_cover >= ot_margin:
        return NbaSpreadCheckResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"OT_DEAD period={period} clock={clock}s margin={margin_to_cover:.1f}",
        )

    # Layer 2-5 sadece Q4'te (OT kendi layer'ında üstte ele alındı).
    if period == 4:
        # Layer 2 — STRUCTURAL_DAMAGE (fiyat çöküşü + math dead).
        if (
            entry_price > 0
            and bid_price > 0
            and (bid_price / entry_price) < structural_damage_ratio
            and is_spread_dead(margin_to_cover, clock, bill_james_multiplier)
        ):
            return NbaSpreadCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=(
                    f"STRUCTURAL_DAMAGE price_ratio={bid_price / entry_price:.2f} "
                    f"margin={margin_to_cover:.1f}"
                ),
            )

        # Layer 3 — SPREAD_MATH_DEAD (Bill James %99).
        if is_spread_dead(margin_to_cover, clock, bill_james_multiplier):
            return NbaSpreadCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"SPREAD_MATH_DEAD margin={margin_to_cover:.1f} clock={clock}s",
            )

        # Layer 4 — PREDICTIVE_DEAD (EV bazlı).
        if predictive_enabled and predictive_exit_decision_spread(
            margin_to_cover=margin_to_cover,
            seconds=clock,
            current_bid=bid_price,
            safety_margin=predictive_safety_margin,
            hold_threshold=predictive_hold_threshold,
        ):
            return NbaSpreadCheckResult(
                reason=ExitReason.PREDICTIVE_DEAD,
                detail=(
                    f"PREDICTIVE_DEAD margin={margin_to_cover:.1f} clock={clock}s "
                    f"bid={bid_price:.3f}"
                ),
            )

        # Layer 5 — EMPIRICAL_DEAD (key numbers).
        if (
            (clock <= q4_late_seconds and margin_to_cover >= q4_late_margin)
            or (clock <= q4_final_seconds and margin_to_cover >= q4_final_margin)
            or (clock <= q4_endgame_seconds and margin_to_cover >= q4_endgame_margin)
        ):
            return NbaSpreadCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"EMPIRICAL_DEAD margin={margin_to_cover:.1f} clock={clock}s",
            )

    return None
