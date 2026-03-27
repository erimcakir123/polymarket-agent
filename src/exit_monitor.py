"""exit_monitor.py — Exit detection for all active positions.

Responsibilities:
  - Register WebSocket price-update callback (via ws_feed.set_on_price_update)
  - Drain WS exit queue at start of each cycle
  - Run all portfolio.check_*() exit detectors
  - Return (condition_id, reason) pairs — agent.py calls _exit_position()

Does NOT call executor or modify portfolio directly.
Does NOT execute exits — detection only.

Data flow:
   WS price tick → _on_ws_price_update() → _ws_tick_queue (SimpleQueue, thread-safe)
   agent.process_ws_ticks() ← drains tick queue on main thread, fills _ws_exit_queue
   agent.drain()  ← returns list of (cid, reason) to execute
   agent.check_exits() ← calls portfolio.check_*() methods, returns list
"""
from __future__ import annotations

import logging
import queue
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from src.portfolio import Portfolio
    from src.websocket_feed import WebSocketFeed
    from src.config import AppConfig
    from src.models import Position

logger = logging.getLogger(__name__)


class ExitMonitor:
    """Detect exits. Return (cid, reason) pairs. Never calls executor."""

    def __init__(
        self,
        portfolio: "Portfolio",
        ws_feed: "WebSocketFeed",
        config: "AppConfig",
    ) -> None:
        self.portfolio = portfolio
        self.config = config
        self._ws_tick_queue: queue.SimpleQueue[tuple[str, float, float]] = queue.SimpleQueue()
        self._ws_exit_queue: deque[tuple[str, str]] = deque()
        self._ws_exit_queued_set: set[str] = set()
        self._exiting_set: set[str] = set()  # Double-exit guard

        # Register our callback with the WS feed
        ws_feed.set_on_price_update(self._on_ws_price_update)

    # ── WebSocket ──────────────────────────────────────────────────────────

    def _on_ws_price_update(self, token_id: str, price: float, ts: float) -> None:
        """Called from WS thread — only enqueues, never mutates shared state."""
        self._ws_tick_queue.put_nowait((token_id, price, ts))

    def process_ws_ticks(self) -> None:
        """Process all pending WS price ticks. Must be called from the main thread."""
        while not self._ws_tick_queue.empty():
            try:
                token_id, price, ts = self._ws_tick_queue.get_nowait()
            except queue.Empty:
                break

            # Find matching position by token_id
            cid_found: str | None = None
            pos_found = None
            for cid, pos in self.portfolio.positions.items():
                if pos.token_id == token_id:
                    pos.current_price = price
                    cid_found = cid
                    pos_found = pos
                    break
            if cid_found is None or pos_found is None:
                continue

            cid: str = cast(str, cid_found)  # guarded by None-check above

            # Skip if already in exit queue or actively exiting
            if cid in self._exiting_set:
                continue
            if cid in self._ws_exit_queued_set:
                continue

            self._ws_check_exits(cid, pos_found)

    def _ws_check_exits(self, cid: str, pos: "Position") -> None:
        """Lightweight exit checks triggered by WebSocket price update.

        Only checks stop-loss and trailing TP (pure math, no I/O).
        Queues (cid, reason) into _ws_exit_queue for drain() to return.
        """
        from src.trailing_tp import calculate_trailing_tp

        direction = pos.direction
        entry = pos.entry_price
        current = pos.current_price

        # Effective prices for BUY_NO (track NO-side value)
        if direction == "BUY_NO":
            effective_entry = 1.0 - entry
            effective_current = 1.0 - current
        else:
            effective_entry = entry
            effective_current = current

        pnl_pct = (effective_current - effective_entry) / effective_entry if effective_entry > 0 else 0

        # 1. Stop-loss check — same for all sports
        sl_pct = self.config.risk.stop_loss_pct
        if pnl_pct <= -abs(sl_pct):
            self._ws_exit_queue.append((cid, "stop_loss"))
            self._ws_exit_queued_set.add(cid)
            logger.info(
                "WS_EXIT queued [stop_loss]: %s | pnl=%.1f%% <= -%.0f%%",
                pos.slug[:35], pnl_pct * 100, abs(sl_pct) * 100,
            )
            return

        # 2. Trailing TP check (non-VS positions only)
        ttp_cfg = self.config.trailing_tp
        if ttp_cfg.enabled and not pos.volatility_swing:
            # Update peak tracking — always in effective space
            # BUY_YES: effective = YES price (higher = better)
            # BUY_NO:  effective = NO value = 1 - YES price (higher = better)
            if direction == "BUY_NO":
                eff_current = 1.0 - current
            else:
                eff_current = current
            if eff_current > pos.peak_price or pos.peak_price == 0:
                pos.peak_price = eff_current

            # Calculate peak P&L (peak_price is in effective space)
            if direction == "BUY_NO":
                no_cost = 1.0 - entry
                peak_pnl = (pos.peak_price - no_cost) / no_cost if no_cost > 0 else 0
            else:
                peak_pnl = (pos.peak_price - entry) / entry if entry > 0 else 0
            pos.peak_pnl_pct = max(pos.peak_pnl_pct, peak_pnl)

            if pos.peak_pnl_pct >= ttp_cfg.activation_pct:
                ttp_result = calculate_trailing_tp(
                    entry_price=entry,
                    current_price=current,
                    direction=direction,
                    peak_price=pos.peak_price,
                    trailing_active=True,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=ttp_cfg.trail_distance,
                )
                if ttp_result["action"] == "EXIT":
                    self._ws_exit_queue.append((cid, f"trailing_tp: {ttp_result['reason']}"))
                    self._ws_exit_queued_set.add(cid)
                    logger.info(
                        "WS_EXIT queued [trailing_tp]: %s | %s",
                        pos.slug[:35], ttp_result["reason"],
                    )
                    return

    def drain(self) -> list[tuple[str, str]]:
        """Pop all WS-triggered exits and return them.

        Call at top of each cycle. agent.py calls _exit_position(cid, reason) for each.
        Applies the _exiting_set guard before returning.
        """
        exits: list[tuple[str, str]] = []
        while self._ws_exit_queue:
            cid, reason = self._ws_exit_queue.popleft()
            if cid in self._exiting_set:
                continue  # Already being exited — double-exit guard
            exits.append((cid, reason))
        self._ws_exit_queued_set.clear()
        return exits

    # ── Cycle exit checks ─────────────────────────────────────────────────

    def check_exits(
        self,
        match_states: dict,
        cycle_count: int,
    ) -> list[tuple[str, str]]:
        """Run all exit detectors. Return (cid, reason) list.

        Agent calls _exit_position(cid, reason) for each returned pair.
        Called once per heavy cycle.
        """
        from src.trailing_tp import calculate_trailing_tp

        result: list[tuple[str, str]] = []
        cfg = self.config
        seen_cids: set[str] = set()

        def _add(cid: str, reason: str) -> None:
            if cid not in seen_cids and cid not in self._exiting_set:
                result.append((cid, reason))
                seen_cids.add(cid)

        # 1. Match-aware exits (4 layers: score/time/halftime/pre-match)
        match_exit_results = self.portfolio.check_match_aware_exits()
        for mexr in match_exit_results:
            cid = mexr["condition_id"]
            if mexr.get("exit") and cid in self.portfolio.positions:
                _add(cid, f"match_exit_{mexr['layer']}")

        # 2. Stop-losses
        vs_cfg = cfg.volatility_swing
        for cid in self.portfolio.check_stop_losses(
            cfg.risk.stop_loss_pct,
            vs_stop_loss_pct=vs_cfg.stop_loss_pct,
        ):
            _add(cid, "stop_loss")

        # 3. Trailing take-profit (non-VS positions)
        ttp_cfg = cfg.trailing_tp
        if ttp_cfg.enabled:
            for cid, pos in list(self.portfolio.positions.items()):
                if pos.volatility_swing:
                    continue
                if cid in seen_cids:
                    continue
                ttp_result = calculate_trailing_tp(
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    direction=pos.direction,
                    peak_price=pos.peak_price,
                    trailing_active=pos.peak_pnl_pct >= ttp_cfg.activation_pct,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=ttp_cfg.trail_distance,
                )
                if ttp_result["peak_price"] > pos.peak_price:
                    pos.peak_price = ttp_result["peak_price"]
                if ttp_result["action"] == "EXIT":
                    _add(cid, f"trailing_tp: {ttp_result['reason']}")

        # 4. VS trailing stop (tighten near resolution)
        if ttp_cfg.enabled:
            for cid, pos in list(self.portfolio.positions.items()):
                if not pos.volatility_swing:
                    continue
                if cid in seen_cids:
                    continue
                if pos.peak_pnl_pct < ttp_cfg.activation_pct:
                    continue
                trail = 0.04 if _hours_to_resolution(pos) <= 0.5 else ttp_cfg.trail_distance
                ttp_result = calculate_trailing_tp(
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    direction=pos.direction,
                    peak_price=pos.peak_price,
                    trailing_active=True,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=trail,
                )
                if ttp_result["peak_price"] > pos.peak_price:
                    pos.peak_price = ttp_result["peak_price"]
                if ttp_result["action"] == "EXIT":
                    _add(cid, f"trailing_tp: {ttp_result['reason']}")

        # 5. Pre-match exits (mandatory exit before match starts)
        for cid in self.portfolio.check_pre_match_exits(minutes_before=30):
            _add(cid, "pre_match_exit")

        return result

    def check_exits_light(self, match_states: dict) -> list[tuple[str, str]]:
        """Subset of exit checks for light cycles (price-only, no AI).

        Light cycles run every 2 minutes. Runs match-aware, stop-loss, trailing TP.
        """
        from src.trailing_tp import calculate_trailing_tp

        result: list[tuple[str, str]] = []
        cfg = self.config
        seen_cids: set[str] = set()

        def _add(cid: str, reason: str) -> None:
            if cid not in seen_cids and cid not in self._exiting_set:
                result.append((cid, reason))
                seen_cids.add(cid)

        # Match-aware exits
        match_exit_results = self.portfolio.check_match_aware_exits()
        for mexr in match_exit_results:
            cid = mexr["condition_id"]
            if mexr.get("exit") and cid in self.portfolio.positions:
                _add(cid, f"match_exit_{mexr['layer']}")

        # Stop-losses
        vs_cfg = cfg.volatility_swing
        for cid in self.portfolio.check_stop_losses(
            cfg.risk.stop_loss_pct,
            vs_stop_loss_pct=vs_cfg.stop_loss_pct,
        ):
            _add(cid, "stop_loss")

        # Trailing TP
        ttp_cfg = cfg.trailing_tp
        if ttp_cfg.enabled:
            for cid, pos in list(self.portfolio.positions.items()):
                if cid in seen_cids:
                    continue
                ttp_result = calculate_trailing_tp(
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    direction=pos.direction,
                    peak_price=pos.peak_price,
                    trailing_active=pos.peak_pnl_pct >= ttp_cfg.activation_pct,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=ttp_cfg.trail_distance,
                )
                if ttp_result["peak_price"] > pos.peak_price:
                    pos.peak_price = ttp_result["peak_price"]
                if ttp_result["action"] == "EXIT":
                    _add(cid, f"trailing_tp: {ttp_result['reason']}")

        return result

    # ── Double-exit guard ─────────────────────────────────────────────────

    def mark_exiting(self, cid: str) -> None:
        """Called by agent before executing _exit_position. Prevents double-exit."""
        self._exiting_set.add(cid)

    def unmark_exiting(self, cid: str) -> None:
        """Called by agent after _exit_position completes."""
        self._exiting_set.discard(cid)

    def is_exiting(self, cid: str) -> bool:
        """Returns True if position is currently being exited."""
        return cid in self._exiting_set

    def match_exit_hold_revokes(self) -> list[dict]:
        """Return match_exit results that need hold-revoke/restore.

        Agent handles these separately (requires direct position mutation).
        """
        return [
            r for r in self.portfolio.check_match_aware_exits()
            if r.get("revoke_hold") or r.get("restore_hold")
        ]


# ── Module-level helpers ───────────────────────────────────────────────────

def _hours_to_resolution(pos) -> float:
    """Hours until position's end_date. Returns 99.0 if unknown."""
    end_iso = getattr(pos, "end_date_iso", "")
    if not end_iso:
        return 99.0
    try:
        end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        return max(0.0, (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600)
    except (ValueError, TypeError):
        return 99.0
