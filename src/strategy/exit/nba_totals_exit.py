"""NBA totals exit — 4-katman pipeline (SPEC-J §Totals exit pipeline).

Pre-rollback'ten mantık migrate (kod taze yazıldı):
  1. STRUCTURAL_DAMAGE — Q4, bid/entry < 0.30, total dead.
  2. TOTALS_MATH_DEAD — Q4, Poisson 1.218 (= 0.861 × √2).
  3. PREDICTIVE_DEAD  — Q4, EV bazlı (comeback < hold ve bid + safety > comeback).
  4. EMPIRICAL_DEAD   — Q4, side-aware gap (OVER: needed > gap; UNDER: excess > gap).

Strategy katmanı: I/O yok, log yok, saf karar.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.math.safe_lead import is_total_dead, predictive_exit_decision_totals
from src.models.enums import ExitReason, TotalSide


@dataclass
class NbaTotalsCheckResult:
    reason: ExitReason
    detail: str
    sell_pct: float = 1.0
    partial: bool = False


def check(
    score_info: dict,
    target_total: float,
    side: str,                        # TotalSide.OVER.value | UNDER.value
    bid_price: float,
    entry_price: float,
    totals_multiplier: float = 1.218,
    structural_damage_ratio: float = 0.30,
    # _ot_over_scale_pct: pre-rollback OT-aware adjustment, currently unused per SPEC-J YAGNI
    _ot_over_scale_pct: float = 0.5,
    q4_late_seconds: int = 360,
    q4_late_gap: float = 7,
    q4_final_seconds: int = 180,
    q4_final_gap: float = 4,
    q4_endgame_seconds: int = 60,
    q4_endgame_gap: float = 3,
    predictive_enabled: bool = True,
    predictive_safety_margin: float = 0.03,
    predictive_hold_threshold: float = 0.20,
) -> NbaTotalsCheckResult | None:
    """NBA totals exit kararı. None → HOLD; sonuç → EXIT.

    Near-resolve / scale-out monitor.py'da önce çalışır — burada yok.
    side="invalid" → safe_lead.is_total_dead ValueError fırlatır (propagate).

    `_ot_over_scale_pct` MVP'de kullanılmıyor; ileride OT'de over windfall partial-sell
    kalibrasyonu için ayrı SPEC açılırsa kullanılacak (config interface stable).
    Underscore prefix → "intentionally unused, kept for signature compat".
    """
    if not score_info.get("available"):
        return None

    period: int = score_info.get("period_number", 0) or 0
    clock: int = score_info.get("clock_seconds", 0) or 0
    home_score: int = score_info.get("home_score", 0) or 0
    away_score: int = score_info.get("away_score", 0) or 0
    current_total = home_score + away_score
    points_diff = target_total - current_total  # >0: hedef henüz aşılmadı

    # Q1-Q3 ve OT (period > 4) → HOLD; layer 1-4 sadece Q4'te.
    if period != 4:
        return None

    # Layer 1 — STRUCTURAL_DAMAGE (fiyat çöküşü + math dead).
    if (
        entry_price > 0
        and bid_price > 0
        and (bid_price / entry_price) < structural_damage_ratio
        and is_total_dead(target_total, current_total, clock, side, totals_multiplier)
    ):
        return NbaTotalsCheckResult(
            reason=ExitReason.SCORE_EXIT,
            detail=(
                f"STRUCTURAL_DAMAGE price_ratio={bid_price / entry_price:.2f} "
                f"current={current_total} target={target_total} side={side}"
            ),
        )

    # Layer 2 — TOTALS_MATH_DEAD (Poisson 1.218).
    if is_total_dead(target_total, current_total, clock, side, totals_multiplier):
        return NbaTotalsCheckResult(
            reason=ExitReason.SCORE_EXIT,
            detail=(
                f"TOTALS_MATH_DEAD current={current_total} target={target_total} "
                f"clock={clock}s side={side}"
            ),
        )

    # Layer 3 — PREDICTIVE_DEAD (EV bazlı).
    if predictive_enabled and predictive_exit_decision_totals(
        target_total=target_total,
        current_total=current_total,
        seconds=clock,
        side=side,
        current_bid=bid_price,
        safety_margin=predictive_safety_margin,
        hold_threshold=predictive_hold_threshold,
    ):
        return NbaTotalsCheckResult(
            reason=ExitReason.PREDICTIVE_DEAD,
            detail=(
                f"PREDICTIVE_DEAD current={current_total} target={target_total} "
                f"clock={clock}s side={side} bid={bid_price:.3f}"
            ),
        )

    # Layer 4 — EMPIRICAL_DEAD (side-aware gap).
    if _empirical_total_dead(
        clock=clock,
        points_diff=points_diff,
        side=side,
        late_seconds=q4_late_seconds,
        late_gap=q4_late_gap,
        final_seconds=q4_final_seconds,
        final_gap=q4_final_gap,
        endgame_seconds=q4_endgame_seconds,
        endgame_gap=q4_endgame_gap,
    ):
        return NbaTotalsCheckResult(
            reason=ExitReason.SCORE_EXIT,
            detail=(
                f"EMPIRICAL_DEAD current={current_total} target={target_total} "
                f"clock={clock}s side={side}"
            ),
        )

    return None


def _empirical_total_dead(
    *,
    clock: int,
    points_diff: float,
    side: str,
    late_seconds: int,
    late_gap: float,
    final_seconds: int,
    final_gap: float,
    endgame_seconds: int,
    endgame_gap: float,
) -> bool:
    """Side-aware empirical gap kontrolü.

    OVER: target'a çok puan kaldı → too far away → DEAD (points_diff > gap).
    UNDER: current target'ı geçmiş → over busted → DEAD (-points_diff > gap).
    """
    if side == TotalSide.OVER.value:
        magnitude = points_diff
    elif side == TotalSide.UNDER.value:
        magnitude = -points_diff
    else:
        # is_total_dead yukarıda zaten ValueError fırlattı; defensive guard.
        return False

    return (
        (clock <= late_seconds and magnitude > late_gap)
        or (clock <= final_seconds and magnitude > final_gap)
        or (clock <= endgame_seconds and magnitude > endgame_gap)
    )
