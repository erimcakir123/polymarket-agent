"""Match outcome logger — records every position exit for AI calibration.

Writes to logs/match_outcomes.jsonl (append-only, one JSON object per line).
Used to measure: AI accuracy, confidence calibration, edge vs actual PnL.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

OUTCOMES_FILE = Path("logs/match_outcomes.jsonl")


def log_outcome(
    slug: str,
    question: str,
    direction: str,
    ai_probability: float,
    confidence: str,
    entry_price: float,
    exit_price: float,
    exit_reason: str,
    pnl: float,
    size: float,
    sport_tag: str = "",
    entry_reason: str = "",
    scouted: bool = False,
    peak_pnl_pct: float = 0.0,
    match_score: str = "",
    price_history: list[float] | None = None,
    cycles_held: int = 0,
) -> None:
    """Append one outcome record to the JSONL log."""
    is_resolved = exit_reason.startswith("resolved_")
    is_win = exit_reason == "resolved_win"
    is_loss = exit_reason == "resolved_loss"

    # AI said YES has this probability
    ai_yes_prob = ai_probability
    # Did YES actually win? (only known for resolved markets)
    yes_won = is_win if direction == "BUY_YES" else (not is_win if direction == "BUY_NO" else None)

    # AI was correct if: predicted >50% YES and YES won, or <50% YES and NO won
    ai_correct = None
    if is_resolved and yes_won is not None:
        ai_favored_yes = ai_yes_prob > 0.5
        ai_correct = (ai_favored_yes and yes_won) or (not ai_favored_yes and not yes_won)

    # Bet was correct if we made money
    bet_correct = pnl > 0 if is_resolved else None

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "slug": slug,
        "question": question,
        "direction": direction,
        "ai_probability": round(ai_yes_prob, 4),
        "confidence": confidence,
        "entry_price": round(entry_price, 4),
        "exit_price": round(exit_price, 4),
        "exit_reason": exit_reason,
        "resolved": is_resolved,
        "yes_won": yes_won,
        "ai_correct": ai_correct,
        "bet_correct": bet_correct,
        "pnl": round(pnl, 2),
        "size": round(size, 2),
        "pnl_pct": round(pnl / size * 100, 1) if size > 0 else 0.0,
        "peak_pnl_pct": round(peak_pnl_pct * 100, 1),
        "sport_tag": sport_tag,
        "entry_reason": entry_reason,
        "scouted": scouted,
        "match_score": match_score,
        "cycles_held": cycles_held,
        "price_history": [round(p, 4) for p in (price_history or [])],
    }

    try:
        OUTCOMES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTCOMES_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        logger.info(
            "Outcome logged: %s | %s | AI=%.0f%% | %s | PnL=$%.2f",
            slug[:35], exit_reason, ai_yes_prob * 100,
            "correct" if ai_correct else ("wrong" if ai_correct is False else "n/a"),
            pnl,
        )
    except OSError as e:
        logger.warning("Failed to log outcome: %s", e)
