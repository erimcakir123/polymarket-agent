# src/edge_decay.py
"""AI signal freshness -- decay AI target toward market price as match progresses.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #4
"""


def get_edge_decay_factor(elapsed_pct: float) -> float:
    if elapsed_pct < 0.30:
        return 1.0
    elif elapsed_pct < 0.60:
        return 0.75
    elif elapsed_pct < 0.85:
        return 0.50
    else:
        return 0.25


def get_decayed_ai_target(ai_prob: float, current_price: float, elapsed_pct: float) -> float:
    """Blend AI target toward current price. Output is in raw YES-probability frame.
    Callers handle direction conversion when computing edge."""
    decay = get_edge_decay_factor(elapsed_pct)
    return current_price + (ai_prob - current_price) * decay
