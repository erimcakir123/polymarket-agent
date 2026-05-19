"""Bill James %99 safe-lead + EV-bazlı predictive exit math (basketbol).

Kaynaklar (DECISIONS §6 / §7):
- Bill James: deficit ≥ 0.861 × √seconds → matematiksel olarak kapatılamaz
  (NBA için kalibre, %99 güven aralığı).
- Totals variance ≈ √2 × spread variance → multiplier 1.218 (= 0.861 × √2).
- ML score-diff σ/√s = 0.3727; totals σ/√s = 0.5270 (NBA empirik).
- EV bazlı predictive_dead: comeback < hold_threshold ve
  (current_bid + safety_margin) > comeback → şimdi sat.

Domain katmanı saf math: I/O / log / global state YOK.
"""
from __future__ import annotations

from math import erf, sqrt


# ── Variance sabitleri (NBA empirik kalibrasyon) ─────────────────────────────

ML_SCORE_DIFF_STD_PER_SQRT_SEC: float = 0.3727
TOTALS_STD_PER_SQRT_SEC: float = 0.5270


# ── Bill James matematiksel ölü kontrolü ─────────────────────────────────────


def is_total_dead(
    target_total: float,
    current_total: int,
    seconds_remaining: int,
    side: str,
    multiplier: float = 1.218,
) -> bool:
    """Totals için Poisson-bazlı ölü kontrolü.

    multiplier 1.218 = 0.861 × √2 (toplam = iki takım, variance daha yüksek).
    side="over": target'a yetişmek imkansızsa → True.
    side="under": target'ı geçmek kaçınılmazsa → True.
    """
    if side not in ("over", "under"):
        raise ValueError(f"side must be 'over' or 'under', got {side!r}")

    points_needed = target_total - current_total

    if seconds_remaining <= 0:
        if side == "over":
            return points_needed > 0
        # under loses on push (total exactly hits line) — align with predictive_exit_decision_totals.
        return points_needed <= 0

    threshold = multiplier * sqrt(seconds_remaining)

    if side == "over":
        return points_needed > threshold
    return -points_needed > threshold


# ── Comeback rate (standart normal CDF) ──────────────────────────────────────


def estimate_comeback_rate_ml(deficit: int, seconds_remaining: int) -> float:
    """Moneyline comeback olasılığı.

    deficit > 0: bizim takım geride.
    deficit ≤ 0: zaten ileride/eşit → 1.0.
    seconds ≤ 0 + deficit > 0 → 0.0.

    Returns: 0.0 ≤ rate ≤ 1.0 (clamp).
    """
    if seconds_remaining <= 0:
        return 1.0 if deficit <= 0 else 0.0
    if deficit <= 0:
        return 1.0

    z = deficit / (ML_SCORE_DIFF_STD_PER_SQRT_SEC * sqrt(seconds_remaining))
    rate = 0.5 * (1 - erf(z / sqrt(2)))
    return max(0.0, min(1.0, rate))


def estimate_comeback_rate_totals(
    points_diff: float,
    seconds_remaining: int,
    side: str,
) -> float:
    """Totals comeback rate.

    points_diff = target_total - current_total (her zaman aynı).
    Pozitif → hedef henüz aşılmadı.
    Negatif/sıfır → hedef aşıldı (over kazandı, under kaybetti).

    side="over":  hedefe yetişme olasılığı.
    side="under": hedefin altında kalma olasılığı.
    """
    if side not in ("over", "under"):
        raise ValueError(f"side must be 'over' or 'under', got {side!r}")

    if points_diff <= 0:
        return 1.0 if side == "over" else 0.0

    if seconds_remaining <= 0:
        return 0.0 if side == "over" else 1.0

    z = points_diff / (TOTALS_STD_PER_SQRT_SEC * sqrt(seconds_remaining))

    if side == "over":
        return 0.5 * (1 - erf(z / sqrt(2)))
    return 0.5 * (1 + erf(z / sqrt(2)))


# ── EV bazlı predictive exit kararları ──────────────────────────────────────


def predictive_exit_decision_totals(
    target_total: float,
    current_total: int,
    seconds: int,
    side: str,
    current_bid: float,
    safety_margin: float = 0.03,
    hold_threshold: float = 0.20,
) -> bool:
    """Totals için EV bazlı predictive exit (True = EXIT, False = HOLD).

    1. seconds ≤ 0 → over: hedef aşılmadıysa EXIT, under: aşıldıysa EXIT.
    2. points_until_decision ≤ 0:
         over → kazandık, HOLD.
         under → kaybettik, EXIT.
    3. comeback ≥ hold_threshold → HOLD.
    4. (current_bid + safety_margin) > comeback → EXIT.
    """
    if side not in ("over", "under"):
        raise ValueError(f"side must be 'over' or 'under', got {side!r}")

    if seconds <= 0:
        if side == "over":
            return current_total < target_total
        return current_total >= target_total

    points_until_decision = target_total - current_total

    if points_until_decision <= 0:
        return side == "under"

    comeback = estimate_comeback_rate_totals(points_until_decision, seconds, side)
    if comeback >= hold_threshold:
        return False
    return (current_bid + safety_margin) > comeback
