"""Post-exit outcome tracker -- follows markets after we exit to record final results.

When we exit a position (TP, SL, etc.), we don't know the final match result yet.
This tracker keeps watching those markets via Gamma API and records the actual
outcome once the market resolves.

This gives us critical data:
- "We took profit at 70¢ but the team won (resolved at $1) -- left money on table"
- "We stop-lossed and the team actually won -- premature exit"
- "We stop-lossed and the team lost -- good exit"

Data is written to logs/match_outcomes.jsonl with resolved=True and actual result.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from src.models import effective_price

logger = logging.getLogger(__name__)

TRACKER_FILE = Path("logs/outcome_tracker.json")

# Stop tracking after 24 hours (market should resolve by then)
MAX_TRACK_SECONDS = 86400


@dataclass
class TrackedMarket:
    """A market we exited but still want to know the final outcome."""
    condition_id: str
    token_id: str
    slug: str
    question: str
    direction: str
    anchor_probability: float
    confidence: str
    entry_price: float
    exit_price: float
    exit_reason: str
    pnl: float
    size: float
    sport_tag: str
    entry_reason: str
    scouted: bool
    peak_pnl_pct: float
    match_score: str
    cycles_held: int
    bookmaker_prob: float  # Bookmaker implied probability at entry (0 = not available)
    exit_timestamp: float  # time.time() when exited


class OutcomeTracker:
    """Tracks exited markets until they resolve, then logs the final outcome."""

    def __init__(self) -> None:
        self._tracked: dict[str, TrackedMarket] = {}
        self._load()

    def track(
        self,
        condition_id: str,
        token_id: str,
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
        cycles_held: int = 0,
        bookmaker_prob: float = 0.0,
    ) -> None:
        """Start tracking a market after exit."""
        # Don't track resolved exits -- we already know the outcome
        if exit_reason.startswith("resolved_"):
            return

        self._tracked[condition_id] = TrackedMarket(
            condition_id=condition_id,
            token_id=token_id,
            slug=slug,
            question=question,
            direction=direction,
            anchor_probability=anchor_probability,
            confidence=confidence,
            entry_price=entry_price,
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl=pnl,
            size=size,
            sport_tag=sport_tag,
            entry_reason=entry_reason,
            scouted=scouted,
            peak_pnl_pct=peak_pnl_pct,
            match_score=match_score,
            cycles_held=cycles_held,
            bookmaker_prob=bookmaker_prob,
            exit_timestamp=time.time(),
        )
        self._save()
        logger.info("Outcome tracker: watching %s after %s exit", slug[:35], exit_reason)

    def check_resolutions(self, gamma_events: dict[str, dict]) -> list[dict]:
        """Check tracked markets for resolution using already-fetched Gamma data.

        Args:
            gamma_events: dict of condition_id -> event data from Gamma API
                          (same data already fetched in _update_position_prices)

        Returns:
            List of resolved outcome dicts for logging.
        """
        resolved = []
        expired = []
        now = time.time()

        for cid, tm in list(self._tracked.items()):
            # Expire old entries
            if now - tm.exit_timestamp > MAX_TRACK_SECONDS:
                expired.append(cid)
                logger.info("Outcome tracker: expired %s (>24h, no resolution)", tm.slug[:35])
                continue

            event = gamma_events.get(cid)
            if not event:
                continue

            # Check if market has resolved
            yes_price = event.get("yes_price")
            is_closed = event.get("closed", False)
            is_ended = event.get("ended", False)

            if not (is_closed or is_ended):
                continue

            if yes_price is None:
                continue

            # Determine outcome
            if yes_price >= 0.95:
                yes_won = True
            elif yes_price <= 0.05:
                yes_won = False
            else:
                continue  # Not fully resolved yet

            # Calculate what would have happened if we held
            our_side_won = (tm.direction == "BUY_YES" and yes_won) or \
                           (tm.direction == "BUY_NO" and not yes_won)

            # Hypothetical PnL: what we'd have earned/lost if we held to resolution
            # Calculate hypothetical PnL if we held to resolution
            eff_cost = effective_price(tm.entry_price, tm.direction)
            shares = tm.size / eff_cost if eff_cost > 0 else 0
            if tm.direction == "BUY_YES":
                token_resolve = 1.0 if yes_won else 0.0
            else:
                token_resolve = 0.0 if yes_won else 1.0  # NO token value
            hypothetical_pnl = shares * token_resolve - tm.size

            outcome = {
                "condition_id": cid,
                "slug": tm.slug,
                "question": tm.question,
                "direction": tm.direction,
                "anchor_probability": tm.anchor_probability,
                "confidence": tm.confidence,
                "entry_price": tm.entry_price,
                "exit_price": tm.exit_price,
                "exit_reason": tm.exit_reason,
                "actual_pnl": tm.pnl,
                "hypothetical_pnl": round(hypothetical_pnl, 2),
                "pnl_left_on_table": round(hypothetical_pnl - tm.pnl, 2) if our_side_won else 0.0,
                "size": tm.size,
                "yes_won": yes_won,
                "our_side_won": our_side_won,
                "sport_tag": tm.sport_tag,
                "entry_reason": tm.entry_reason,
                "scouted": tm.scouted,
                "peak_pnl_pct": tm.peak_pnl_pct,
                "match_score": tm.match_score,
                "cycles_held": tm.cycles_held,
                "exit_was_correct": (tm.pnl > 0) or (not our_side_won),
                "bookmaker_prob": tm.bookmaker_prob,
            }

            resolved.append(outcome)
            logger.info(
                "Outcome RESOLVED: %s | %s | exit=%s actual=%s | PnL=$%.2f (held=$%.2f)",
                tm.slug[:30], tm.exit_reason,
                "win" if tm.pnl > 0 else "loss",
                "WIN" if our_side_won else "LOSS",
                tm.pnl, hypothetical_pnl,
            )

        # Remove resolved and expired
        for cid in [r["condition_id"] for r in resolved] + expired:
            self._tracked.pop(cid, None)

        if resolved or expired:
            self._save()

        return resolved

    @property
    def tracked_count(self) -> int:
        return len(self._tracked)

    @property
    def tracked_condition_ids(self) -> set[str]:
        return set(self._tracked.keys())

    def _save(self) -> None:
        TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {cid: asdict(tm) for cid, tm in self._tracked.items()}
        TRACKER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not TRACKER_FILE.exists():
            return
        try:
            data = json.loads(TRACKER_FILE.read_text())
            for cid, d in data.items():
                d.setdefault("bookmaker_prob", 0.0)  # backward compat
                self._tracked[cid] = TrackedMarket(**d)
            if self._tracked:
                logger.info("Outcome tracker: loaded %d markets to watch", len(self._tracked))
        except Exception as e:
            logger.warning("Failed to load outcome tracker: %s", e)
