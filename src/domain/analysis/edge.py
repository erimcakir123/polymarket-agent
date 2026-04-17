"""Edge hesabı (TDD §6.3) — anchor P(YES) vs market price.

Confidence multipliers: A=0.67 (sharp data güvenilir → düşük eşik %4),
B=1.00 (baz %6). C girmez. Mantık: A-conf'ta Pinnacle/Betfair var →
olasılık tahmini daha doğru → daha küçük edge kabul edilebilir.
"""
from __future__ import annotations

from src.models.enums import Direction

DEFAULT_CONFIDENCE_MULTIPLIERS: dict[str, float] = {"A": 0.67, "B": 1.00}


def calculate_edge(
    anchor_prob: float,
    market_yes_price: float,
    min_edge: float = 0.06,
    confidence: str = "B",
    confidence_multipliers: dict[str, float] | None = None,
    spread: float = 0.0,
    slippage: float = 0.0,
) -> tuple[Direction, float]:
    """Effective edge = raw edge − maliyet (spread + slippage).

    raw = anchor_prob − market_yes_price.
    raw > 0 ve threshold aşıldıysa → BUY_YES, edge döner.
    raw < 0 ve |raw| − maliyet threshold aşıldıysa → BUY_NO.
    Aksi halde → HOLD, edge=0.
    """
    multipliers = confidence_multipliers or DEFAULT_CONFIDENCE_MULTIPLIERS
    multiplier = multipliers.get(confidence, 1.0)
    threshold = min_edge * multiplier

    raw = anchor_prob - market_yes_price
    cost = spread + slippage
    effective_yes = raw - cost
    effective_no = abs(raw) - cost

    if raw > 0 and effective_yes > threshold:
        return Direction.BUY_YES, effective_yes
    if raw < 0 and effective_no > threshold:
        return Direction.BUY_NO, effective_no
    return Direction.SKIP, 0.0
