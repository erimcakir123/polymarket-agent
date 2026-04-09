"""Startup cleanup: resolve stale positions from previous sessions.

When the bot is offline during match resolution, positions are "stuck" in the
portfolio. Without this cleanup, the next startup silently removes them as
"stale" with $0 PnL -- losing real winnings or recording phantom money.

This module runs ONCE at agent startup, BEFORE the first cycle:
  1. Scan loaded positions for stale candidates (match likely ended + buffer)
  2. For each candidate, try to determine the actual outcome via:
     a) Gamma API slug query (market closed + extreme prices)
     b) CLOB price history (last tick at >=0.99 or <=0.01)
  3. If outcome determined: close with REAL PnL via exit_executor
  4. If uncertain: mark position with stale_unknown=True, keep in portfolio,
     notify user for manual review

Exit reasons written to trade_log:
  - stale_cleanup_win / stale_cleanup_loss (resolved via Gamma or CLOB)
  - stale_cleanup_unknown (flagged for manual review, position kept)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Stale candidate threshold: match must have ended at least this long ago
STALE_BUFFER_HOURS = 2.0

# CLOB resolution thresholds (strict — avoid false positives)
CLOB_WIN_THRESHOLD = 0.99
CLOB_LOSS_THRESHOLD = 0.01


@dataclass
class ResolutionResult:
    """Outcome of a stale position resolution attempt."""
    source: str               # "gamma" | "clob_history"
    yes_won: bool             # True if YES outcome won
    exit_price: float         # Token YES price at resolution (1.0 or 0.0)


class StartupCleanup:
    """Resolves stale positions carried over from previous sessions.

    Called once from Agent.run() before the main loop starts.
    """

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def run(self) -> dict:
        """Execute cleanup. Returns stats dict: checked/resolved/unknown."""
        stats = {"checked": 0, "resolved": 0, "unknown": 0}
        now = datetime.now(timezone.utc)

        candidates = self._find_stale_candidates(now)
        stats["checked"] = len(candidates)

        if not candidates:
            logger.info("Startup cleanup: no stale candidates")
            return stats

        logger.info(
            "Startup cleanup: %d stale candidates found, attempting resolution",
            len(candidates),
        )

        for cid, pos in candidates:
            result = (
                self._try_gamma_resolution(pos)
                or self._try_clob_history_resolution(pos)
            )

            if result is not None:
                self._resolve_with_pnl(cid, pos, result)
                stats["resolved"] += 1
            else:
                self._mark_unknown(cid, pos)
                stats["unknown"] += 1

        logger.info(
            "Startup cleanup complete: checked=%d resolved=%d unknown=%d",
            stats["checked"], stats["resolved"], stats["unknown"],
        )

        if stats["resolved"] or stats["unknown"]:
            try:
                self.ctx.notifier.send(
                    f"\U0001f9f9 *STARTUP CLEANUP*\n\n"
                    f"Checked: {stats['checked']}\n"
                    f"Resolved: {stats['resolved']}\n"
                    f"Unknown: {stats['unknown']}"
                    + (" (manual review recommended)" if stats["unknown"] else "")
                )
            except Exception as e:
                logger.debug("Startup cleanup notifier failed: %s", e)

        return stats

    # ── Candidate detection ────────────────────────────────────────────────

    def _find_stale_candidates(self, now: datetime) -> list[tuple[str, "Position"]]:
        """Return positions whose match should have ended (beyond duration + buffer).

        Skips positions that are already marked pending_resolution or stale_unknown.
        """
        candidates: list[tuple[str, "Position"]] = []
        for cid, pos in list(self.ctx.portfolio.positions.items()):
            # Skip already-flagged positions (pending oracle or previously marked unknown)
            if getattr(pos, "pending_resolution", False):
                continue
            if getattr(pos, "stale_unknown", False):
                continue

            ms_iso = getattr(pos, "match_start_iso", "") or ""
            if not ms_iso:
                continue  # can't determine staleness without match time

            try:
                start_dt = datetime.fromisoformat(ms_iso.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            duration_h = self._estimate_duration(pos)
            expected_end = start_dt + timedelta(hours=duration_h + STALE_BUFFER_HOURS)

            if now > expected_end:
                candidates.append((cid, pos))

        return candidates

    def _estimate_duration(self, pos) -> float:
        """Estimate match duration in hours. Reuses PriceUpdater.match_duration."""
        try:
            from src.price_updater import PriceUpdater
            return PriceUpdater.match_duration(
                pos.slug or "",
                getattr(pos, "question", "") or "",
            )
        except Exception:
            return 3.0  # safe default

    # ── Resolution strategies ──────────────────────────────────────────────

    def _try_gamma_resolution(self, pos) -> Optional[ResolutionResult]:
        """Query Gamma API for market state. Return result if closed+resolved."""
        if not pos.slug:
            return None
        try:
            resp = requests.get(
                "https://gamma-api.polymarket.com/markets",
                params={"slug": pos.slug},
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None  # market delisted — try CLOB history next

            market = data[0] if isinstance(data, list) else data
            if not market.get("closed", False):
                return None  # still open — not yet resolved

            prices = json.loads(market.get("outcomePrices", '["0.5","0.5"]'))
            yes_price = float(prices[0])
            no_price = float(prices[1]) if len(prices) > 1 else 1.0 - yes_price

            if yes_price >= 0.95:
                return ResolutionResult("gamma", True, 1.0)
            if no_price >= 0.95:
                return ResolutionResult("gamma", False, 0.0)
            return None  # closed but prices mid-range — uncertain
        except Exception as e:
            logger.debug(
                "Gamma resolution failed for %s: %s", pos.slug[:30], e
            )
            return None

    def _try_clob_history_resolution(self, pos) -> Optional[ResolutionResult]:
        """Query CLOB price history endpoint. Return result if last tick is extreme."""
        if not pos.token_id:
            return None
        try:
            resp = requests.get(
                "https://clob.polymarket.com/prices-history",
                params={
                    "market": pos.token_id,
                    "interval": "1d",
                    "fidelity": 60,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            history = data.get("history") or []
            if not history:
                return None

            last_price = float(history[-1].get("p", 0.5))
            # YES token price at resolution
            if last_price >= CLOB_WIN_THRESHOLD:
                return ResolutionResult("clob_history", True, 1.0)
            if last_price <= CLOB_LOSS_THRESHOLD:
                return ResolutionResult("clob_history", False, 0.0)
            return None
        except Exception as e:
            logger.debug(
                "CLOB history resolution failed for %s: %s", pos.slug[:30], e
            )
            return None

    # ── Outcome application ───────────────────────────────────────────────

    def _resolve_with_pnl(self, cid: str, pos, result: ResolutionResult) -> None:
        """Close position with real PnL via exit_executor (same path as normal resolve)."""
        # Update current_price so unrealized_pnl calculation is correct
        self.ctx.portfolio.update_price(cid, result.exit_price)

        our_side_won = (
            (pos.direction == "BUY_YES" and result.yes_won)
            or (pos.direction == "BUY_NO" and not result.yes_won)
        )
        reason = (
            f"stale_cleanup_win_{result.source}"
            if our_side_won
            else f"stale_cleanup_loss_{result.source}"
        )

        logger.info(
            "Startup cleanup RESOLVED: %s | %s | source=%s",
            pos.slug[:40],
            "WIN" if our_side_won else "LOSS",
            result.source,
        )

        # Delegate to exit_executor for consistent PnL recording + trade log + notification
        self.ctx.exit_executor.exit_position(cid, reason)

    def _mark_unknown(self, cid: str, pos) -> None:
        """Flag position as stale_unknown: keep in portfolio, free slot, log warning.

        The position is NOT removed. User must manually verify and resolve it
        via Telegram command or direct portfolio edit.
        """
        pos.stale_unknown = True
        # pending_resolution=True frees the slot in active_position_count
        pos.pending_resolution = True

        try:
            self.ctx.portfolio._save_positions()
        except Exception as e:
            logger.debug("Failed to save portfolio after mark_unknown: %s", e)

        self.ctx.trade_log.log({
            "market": pos.slug,
            "action": "FLAGGED",
            "reason": "stale_cleanup_unknown",
            "mode": self.ctx.config.mode.value,
            "note": "Match likely ended but outcome could not be determined. Manual review required.",
        })

        logger.warning(
            "Startup cleanup UNKNOWN: %s — flagged stale_unknown=True, pending_resolution=True, manual review required",
            pos.slug[:40],
        )
