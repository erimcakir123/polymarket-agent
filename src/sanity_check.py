"""Post-AI sanity check: catch absurd bets before execution.

Runs after AI analysis, before placing the bet. Catches cases where
the AI made an obviously wrong assessment.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SanityResult:
    ok: bool
    suspicious: bool
    reason: str


def check_bet_sanity(
    question: str,
    direction: str,
    ai_probability: float,
    market_price: float,
    edge: float,
    confidence: str,
    bookmaker_count: int = 0,
    bookmaker_agrees_with_market: bool = False,
) -> SanityResult:
    """Validate that a bet makes basic sense.

    Returns SanityResult:
      - ok=True, suspicious=False → proceed normally
      - ok=True, suspicious=True → proceed but notify user (Telegram approval)
      - ok=False → block the bet entirely
    """
    # 1. Absurd edge — likely AI hallucination or data error
    if edge > 0.40:
        return SanityResult(
            ok=False, suspicious=True,
            reason=f"Edge too high ({edge:.0%}) — likely AI error or stale data",
        )

    # 2. Extreme AI probability — AI is very confident, usually wrong
    if ai_probability > 0.95 or ai_probability < 0.05:
        return SanityResult(
            ok=False, suspicious=True,
            reason=f"AI probability extreme ({ai_probability:.0%}) — overconfidence likely",
        )

    # 3. Large edge with low confidence — contradictory signals
    if edge > 0.20 and confidence == "C":
        return SanityResult(
            ok=True, suspicious=True,
            reason=f"Large edge ({edge:.0%}) but low confidence — contradictory",
        )

    # 4. AI and market strongly disagree (>25% gap)
    gap = abs(ai_probability - market_price)
    if gap > 0.25:
        return SanityResult(
            ok=True, suspicious=True,
            reason=f"AI vs market gap too large ({gap:.0%}) — verify manually",
        )

    return SanityResult(ok=True, suspicious=False, reason="")
