"""Bill James %99 safe lead formülü — NBA için kalibre."""
from __future__ import annotations

from math import erf, sqrt


def is_mathematically_dead(
    deficit: int,
    clock_seconds: int,
    multiplier: float,
) -> bool:
    """Geri dönüşü matematiksel olarak imkânsız mı?

    deficit >= multiplier * sqrt(clock_seconds) → evet.
    deficit negatifse (biz öndeyiz) → False.
    """
    if deficit <= 0:
        return False
    if clock_seconds <= 0:
        return deficit > 0
    return deficit >= multiplier * sqrt(clock_seconds)


def is_spread_dead(
    margin_to_cover: float,
    seconds_remaining: int,
    multiplier: float = 0.861,
) -> bool:
    """NBA spread cover için Bill James %99 confidence.

    margin_to_cover: spread'i kapatmak için gereken puan.
    Pozitif = cover edemiyoruz. Negatif veya sıfır = zaten cover'dayız.
    """
    if margin_to_cover <= 0:
        return False
    if seconds_remaining <= 0:
        return margin_to_cover > 0
    return margin_to_cover >= multiplier * sqrt(seconds_remaining)


def is_total_dead(
    target_total: float,
    current_total: int,
    seconds_remaining: int,
    side: str,
    multiplier: float = 1.218,
) -> bool:
    """NBA totals için Poisson-based dead check.

    multiplier 1.218 = 0.861 × sqrt(2) — toplam variance daha yüksek.
    side="over": target'a yetişemeyeceksek dead.
    side="under": target'ı kesinlikle geçeceksek dead.
    """
    if side not in ("over", "under"):
        raise ValueError(f"side must be 'over' or 'under', got {side!r}")

    points_needed = target_total - current_total

    if seconds_remaining <= 0:
        if side == "over":
            return points_needed > 0
        else:
            return points_needed < 0

    threshold = multiplier * sqrt(seconds_remaining)

    if side == "over":
        return points_needed > threshold
    else:
        return -points_needed > threshold


# ── Comeback rate (EV bazlı predictive exit için) ──────────────────────────

# NBA scoring model — iki takım score farkı ve toplam için σ/√s
ML_SCORE_DIFF_STD_PER_SQRT_SEC: float = 0.3727
TOTALS_STD_PER_SQRT_SEC: float = 0.5270


def estimate_comeback_rate_ml(deficit: int, seconds_remaining: int) -> float:
    """Moneyline için comeback olasılığı (standart normal CDF).

    deficit > 0: bizim takım geride.
    deficit ≤ 0: zaten ileride veya berabere.
    Returns: 0.0 ≤ rate ≤ 1.0
    """
    if seconds_remaining <= 0:
        return 1.0 if deficit <= 0 else 0.0
    if deficit <= 0:
        return 1.0

    z = deficit / (ML_SCORE_DIFF_STD_PER_SQRT_SEC * sqrt(seconds_remaining))
    comeback_rate = 0.5 * (1 - erf(z / sqrt(2)))
    return max(0.0, min(1.0, comeback_rate))


def estimate_comeback_rate_spread(margin_to_cover: float, seconds_remaining: int) -> float:
    """Spread için margin_to_cover bazlı comeback rate."""
    if margin_to_cover <= 0:
        return 1.0
    return estimate_comeback_rate_ml(int(round(margin_to_cover)), seconds_remaining)


def estimate_comeback_rate_totals(
    points_diff: float,
    seconds_remaining: int,
    side: str,
) -> float:
    """Totals için comeback rate.

    points_diff = target_total - current_total (her zaman, her iki side için aynı).
    Pozitif → hedef henüz aşılmadı. Negatif/sıfır → hedef aşıldı (over kazandı, under kaybetti).

    side="over":  P(remaining scoring ≥ points_diff) → ne kadar puanın gelmesi lazım.
    side="under": P(remaining scoring < points_diff) → under hâlâ güvende mi.
    """
    if side not in ("over", "under"):
        raise ValueError(f"side must be 'over' or 'under', got {side!r}")

    if points_diff <= 0:
        # Hedef aşıldı / tam eşit: over kazandı, under kaybetti
        return 1.0 if side == "over" else 0.0

    if seconds_remaining <= 0:
        # Süre bitti, hedef henüz aşılmamış: over kaybetti, under kazandı
        return 0.0 if side == "over" else 1.0

    z = points_diff / (TOTALS_STD_PER_SQRT_SEC * sqrt(seconds_remaining))

    if side == "over":
        return 0.5 * (1 - erf(z / sqrt(2)))
    else:
        return 0.5 * (1 + erf(z / sqrt(2)))


# ── EV bazlı karar fonksiyonları ─────────────────────────────────────────────


def predictive_exit_decision_ml(
    deficit: int,
    seconds: int,
    current_bid: float,
    safety_margin: float = 0.03,
    hold_threshold: float = 0.20,
) -> bool:
    """EV bazlı predictive exit — moneyline.

    Returns True → EXIT, False → HOLD.
    Logic:
      1. Comeback >= hold_threshold → HOLD
      2. ev_sell + safety_margin > ev_hold (comeback × $1) → EXIT
      3. Otherwise → HOLD
    """
    if seconds <= 0:
        return deficit > 0
    if deficit <= 0:
        return False

    comeback = estimate_comeback_rate_ml(deficit, seconds)

    if comeback >= hold_threshold:
        return False

    ev_hold = comeback
    return (current_bid + safety_margin) > ev_hold


def predictive_exit_decision_spread(
    margin_to_cover: float,
    seconds: int,
    current_bid: float,
    safety_margin: float = 0.03,
    hold_threshold: float = 0.20,
) -> bool:
    """EV bazlı predictive exit — spread."""
    if seconds <= 0:
        return margin_to_cover > 0
    if margin_to_cover <= 0:
        return False

    comeback = estimate_comeback_rate_spread(margin_to_cover, seconds)
    if comeback >= hold_threshold:
        return False

    return (current_bid + safety_margin) > comeback


def predictive_exit_decision_totals(
    target_total: float,
    current_total: int,
    seconds: int,
    side: str,
    current_bid: float,
    safety_margin: float = 0.03,
    hold_threshold: float = 0.20,
) -> bool:
    """EV bazlı predictive exit — totals.

    points_until_decision = target - current (her zaman).
    ≤ 0: over → kazandık (HOLD), under → kaybettik (EXIT).
    """
    if side not in ("over", "under"):
        raise ValueError(f"side must be 'over' or 'under', got {side!r}")

    if seconds <= 0:
        if side == "over":
            return current_total < target_total   # hedef aşılmadı → over kaybetti
        else:
            return current_total >= target_total  # hedef aşıldı → under kaybetti

    points_until_decision = target_total - current_total  # her zaman target - current

    if points_until_decision <= 0:
        if side == "over":
            return False  # zaten kazandık, çıkma
        else:
            return True   # under kaybetti, hemen çık

    comeback = estimate_comeback_rate_totals(points_until_decision, seconds, side)
    if comeback >= hold_threshold:
        return False

    return (current_bid + safety_margin) > comeback
