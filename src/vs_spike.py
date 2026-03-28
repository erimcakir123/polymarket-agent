# src/vs_spike.py
"""VS spike detection and resolution-aware TP.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #5, #2
"""
from __future__ import annotations


def detect_vs_spike(
    price_history: list[float],
    entry_price: float,
) -> dict:
    """Velocity-based spike detection for volatility swing positions."""
    if len(price_history) < 3:
        return {"spike": False}

    # 2-cycle velocity
    if price_history[-3] <= 0:
        return {"spike": False}
    velocity_2 = (price_history[-1] - price_history[-3]) / price_history[-3]

    # 1-cycle velocity (acceleration)
    if price_history[-2] <= 0:
        return {"spike": False}
    velocity_1 = (price_history[-1] - price_history[-2]) / price_history[-2]

    # Strong spike: +15% in 2 cycles and still accelerating
    if velocity_2 > 0.15 and velocity_1 > 0.05:
        return {
            "spike": True,
            "velocity": velocity_2,
            "action": "EXIT_NOW",
            "reason": f"VS spike: +{velocity_2:.0%} in 2 cycles, accelerating",
        }

    # Weakening spike: +10% in 2 cycles but momentum fading
    prev_velocity = (price_history[-2] - price_history[-3]) / price_history[-3] if price_history[-3] > 0 else 0
    if velocity_2 > 0.10 and velocity_1 < prev_velocity:
        return {
            "spike": True,
            "velocity": velocity_2,
            "action": "EXIT_NOW",
            "reason": f"VS spike peaking: +{velocity_2:.0%}, momentum fading",
        }

    return {"spike": False}


def should_hold_for_resolution(
    effective_price: float,
    effective_ai: float,
    scale_out_tier: int,
    score_behind: bool,
    is_already_won: bool,
) -> tuple[bool, str]:
    """Decide whether to hold for resolution instead of taking profit.
    Spec: #2 Resolution-Aware TP.
    ALL prices must be effective (direction-adjusted by caller)."""
    if is_already_won:
        return True, "Match already won -- hold to resolution"
    if scale_out_tier < 1:
        return False, f"Scale-out tier {scale_out_tier} < 1"
    if effective_price < 0.80:
        return False, f"Effective price {effective_price:.2f} < 0.80"
    if effective_ai < 0.70:
        return False, f"Effective AI {effective_ai:.2f} < 0.70"
    if score_behind:
        return False, "Score behind -- don't hold"
    return True, f"Hold for resolution: eff_price={effective_price:.2f}, eff_ai={effective_ai:.2f}"
