"""Match outcome logger -- records every position exit for AI calibration.

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
    anchor_probability: float,
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
    bookmaker_prob: float = 0.0,
    # Post-exit outcome tracker fields (allow self_improve to ingest these)
    yes_won_override: bool | None = None,    # outcome_tracker provides this directly
    actual_pnl: float | None = None,         # what we actually realized at exit
    hypothetical_pnl: float | None = None,   # what we'd have made if held to resolve
    pnl_left_on_table: float | None = None,  # hypothetical - actual (positive = we exited too early)
    exit_was_correct: bool | None = None,    # exit decision was right (True if pnl>0 OR we'd have lost)
) -> None:
    """Append one outcome record to the JSONL log.

    A market is considered RESOLVED for self_improve / calibration purposes if:
      1. exit_reason starts with 'resolved_' (sync exit at oracle resolution), OR
      2. exit_reason starts with 'post_exit_' (outcome_tracker observed final result
         after our early exit -- yes_won_override, actual_pnl, hypothetical_pnl
         must be provided by the caller in this case).
    """
    is_resolved = (
        exit_reason.startswith("resolved_") or
        exit_reason.startswith("post_exit_")
    )
    is_win = exit_reason == "resolved_win"

    # Anchor said YES has this probability
    anchor_yes_prob = anchor_probability

    # Did YES actually win? Three sources, in priority order:
    #   1. yes_won_override (outcome_tracker post-exit knows the final result)
    #   2. exit_reason == 'resolved_win' for BUY_YES side
    #   3. None (unknown)
    if yes_won_override is not None:
        yes_won = yes_won_override
    elif exit_reason.startswith("resolved_"):
        yes_won = is_win if direction == "BUY_YES" else (not is_win)
    else:
        yes_won = None

    # AI was correct if: predicted >50% YES and YES won, or <50% YES and NO won
    anchor_correct = None
    if is_resolved and yes_won is not None:
        anchor_favored_yes = anchor_yes_prob > 0.5
        anchor_correct = (anchor_favored_yes and yes_won) or (not anchor_favored_yes and not yes_won)

    # "Bet correct" semantics differ for sync vs post-exit:
    #   - sync resolved_*: pnl > 0 means we made money on this exit
    #   - post_exit_*: hypothetical_pnl > 0 means our SIDE was right
    #     (independent of whether our actual exit captured profit)
    if is_resolved:
        if hypothetical_pnl is not None:
            bet_correct = hypothetical_pnl > 0
        else:
            bet_correct = pnl > 0
    else:
        bet_correct = None

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "slug": slug,
        "question": question,
        "direction": direction,
        "anchor_probability": round(anchor_yes_prob, 4),
        "confidence": confidence,
        "entry_price": round(entry_price, 4),
        "exit_price": round(exit_price, 4),
        "exit_reason": exit_reason,
        "resolved": is_resolved,
        "yes_won": yes_won,
        "anchor_correct": anchor_correct,
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
        "bookmaker_prob": round(bookmaker_prob, 4) if bookmaker_prob else 0.0,
        # Post-exit outcome tracker analytics (None for sync resolved_* exits).
        # These power the deeper self_improve breakdowns: hold-vs-exit, exit
        # timing accuracy, match-flip recovery rate, money left on the table.
        "actual_pnl": round(actual_pnl, 2) if actual_pnl is not None else None,
        "hypothetical_pnl": round(hypothetical_pnl, 2) if hypothetical_pnl is not None else None,
        "pnl_left_on_table": round(pnl_left_on_table, 2) if pnl_left_on_table is not None else None,
        "exit_was_correct": exit_was_correct,
    }

    try:
        OUTCOMES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTCOMES_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        logger.info(
            "Outcome logged: %s | %s | AI=%.0f%% | %s | PnL=$%.2f",
            slug[:35], exit_reason, anchor_yes_prob * 100,
            "correct" if anchor_correct else ("wrong" if anchor_correct is False else "n/a"),
            pnl,
        )
    except OSError as e:
        logger.warning("Failed to log outcome: %s", e)
