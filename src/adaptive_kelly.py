"""Adaptive Kelly fraction -- enhances config.risk.kelly_by_confidence with dynamic adjustments.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #15
"""


def get_adaptive_kelly_fraction(
    confidence: str,
    ai_probability: float,
    category: str,
    is_reentry: bool = False,
    is_far: bool = False,
    config_kelly_by_conf: dict | None = None,
) -> float:
    base = (config_kelly_by_conf or {}).get(confidence, 0.15)

    if ai_probability > 0.80:
        base = min(0.30, base + 0.05)

    if category == "esports":
        base *= 0.90

    if is_reentry:
        base *= 0.80

    if is_far:
        base *= 0.70  # 30% discount -- capital locked longer in FAR slots

    return max(0.05, min(0.30, base))
