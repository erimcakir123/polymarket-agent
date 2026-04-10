"""exit_monitor.py -- Exit detection for all active positions.

Responsibilities:
  - Register WebSocket price-update callback (via ws_feed.set_on_price_update)
  - Drain WS exit queue at start of each cycle
  - Run all portfolio.check_*() exit detectors
  - Return (condition_id, reason) pairs -- agent.py calls _exit_position()

Does NOT call executor or modify portfolio directly.
Does NOT execute exits -- detection only.

Data flow:
   WS price tick → _on_ws_price_update() → _ws_tick_queue (SimpleQueue, thread-safe)
   agent.process_ws_ticks() ← drains tick queue on main thread, fills _ws_exit_queue
   agent.drain()  ← returns list of (cid, reason) to execute
   agent.check_exits() ← calls portfolio.check_*() methods, returns list
"""
from __future__ import annotations

import logging
import queue
import threading
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

from src.models import effective_price
from src.stop_loss_helper import compute_stop_loss_pct

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
        # (token_id, yes_price_ask, bid_price, timestamp)
        self._ws_tick_queue: queue.SimpleQueue[tuple[str, float, float, float]] = queue.SimpleQueue()
        self._ws_exit_queue: deque[tuple[str, str]] = deque()
        self._ws_exit_queued_set: set[str] = set()
        self._exiting_set: set[str] = set()  # Double-exit guard
        self._ws_scale_out_queue: list[tuple[str, dict]] = []
        self._ws_scale_out_queued_set: set[str] = set()
        self._last_ws_save_ts: float = 0.0   # Throttle positions.json writes from WS ticks
        # Lock for process_ws_ticks so main thread and background pulse thread
        # can't concurrently drain the queue (avoids race on _ws_exit_queued_set
        # and position.current_price mutations).
        self._ws_tick_lock: threading.Lock = threading.Lock()
        # Background pulse thread (started by start_ws_pulse_thread) drains
        # queued WS ticks every 2s so positions.json stays fresh for the
        # dashboard even when the main thread is blocked in a long AI batch.
        self._pulse_thread: threading.Thread | None = None
        self._pulse_stop_event: threading.Event = threading.Event()

        # Register our callback with the WS feed
        ws_feed.set_on_price_update(self._on_ws_price_update)

    # ── WebSocket ──────────────────────────────────────────────────────────

    def _on_ws_price_update(self, token_id: str, price: float, bid_price: float, ts: float) -> None:
        """Called from WS thread -- only enqueues, never mutates shared state.

        `price` is the token-side best-ask (fill price); `bid_price` is the
        token-side best-bid (realizable close value). Both are enqueued so
        the main thread can store them on the Position atomically.
        """
        self._ws_tick_queue.put_nowait((token_id, price, bid_price, ts))

    def process_ws_ticks(self) -> None:
        """Process all pending WS price ticks.

        Callable from either the main thread or the background pulse thread
        (_ws_pulse_loop); a lock serializes the two callers so queue drain,
        position mutation, and positions.json save are atomic w.r.t. each other.
        """
        with self._ws_tick_lock:
            _ticks_processed = 0
            while not self._ws_tick_queue.empty():
                try:
                    token_id, price, bid_price, ts = self._ws_tick_queue.get_nowait()
                except queue.Empty:
                    break

                # Find matching position by token_id
                # Snapshot positions to avoid RuntimeError if the main thread
                # adds/removes a position concurrently during entry/exit.
                cid_found: str | None = None
                pos_found = None
                for cid, pos in list(self.portfolio.positions.items()):
                    if pos.token_id == token_id:
                        # WS sends token-side prices; convert BUY_NO to YES-side
                        # so all downstream code (PnL, SL, TP) sees consistent prices.
                        # current_price stays ASK-side (drives exit logic);
                        # bid_price is stored so the dashboard can display the
                        # realizable close value without spread-wide false losses.
                        if pos.direction == "BUY_NO":
                            pos.current_price = 1.0 - price
                            # For BUY_NO the NO-token's bid maps to (1 - bid) on the
                            # YES-side. Dashboard re-applies effective_price(),
                            # so we store YES-side consistently with current_price.
                            pos.bid_price = 1.0 - bid_price if bid_price > 0 else 0.0
                        else:
                            pos.current_price = price
                            pos.bid_price = bid_price
                        cid_found = cid
                        pos_found = pos
                        _ticks_processed += 1
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

            # Throttled persistence: if we mutated any position current_price
            # from WS ticks, persist positions.json at most once every 2 seconds
            # so the dashboard sees near-real-time prices without disk I/O storms.
            if _ticks_processed > 0:
                import time as _time
                now_ts = _time.time()
                if now_ts - self._last_ws_save_ts >= 2.0:
                    try:
                        self.portfolio.save_prices_to_disk()
                        self._last_ws_save_ts = now_ts
                    except Exception as exc:
                        logger.debug("WS tick save failed: %s", exc)

    def start_ws_pulse_thread(self, interval_sec: float = 2.0) -> None:
        """Start a background daemon that drains WS ticks every interval_sec.

        This keeps positions.json and in-memory prices fresh during long hard
        cycle phases (e.g. a 3-5 min AI batch) when the main thread is blocked
        inside a single blocking call and can't call process_ws_ticks itself.
        """
        if self._pulse_thread and self._pulse_thread.is_alive():
            return
        self._pulse_stop_event.clear()

        def _loop() -> None:
            while not self._pulse_stop_event.is_set():
                try:
                    self.process_ws_ticks()
                except Exception as exc:
                    logger.debug("WS pulse iteration failed: %s", exc)
                # Sleep in small slices so stop_event wakes us promptly
                self._pulse_stop_event.wait(timeout=interval_sec)

        self._pulse_thread = threading.Thread(
            target=_loop, name="ws-pulse", daemon=True,
        )
        self._pulse_thread.start()
        logger.info("WS pulse thread started (interval=%.1fs)", interval_sec)

    def stop_ws_pulse_thread(self) -> None:
        """Signal the pulse thread to exit and wait briefly for it."""
        self._pulse_stop_event.set()
        if self._pulse_thread:
            self._pulse_thread.join(timeout=3)

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
        effective_entry = effective_price(entry, direction)
        effective_current = effective_price(current, direction)

        pnl_pct = (effective_current - effective_entry) / effective_entry if effective_entry > 0 else 0

        # Pre-match guard: don't exit before match starts (result unknown, price noise)
        # Moved up so near_resolve can use it.
        _match_start = getattr(pos, "match_start_iso", "") or ""
        _pre_match = False
        _mins_since_start = None
        if _match_start:
            try:
                from datetime import datetime, timezone
                _start_dt = datetime.fromisoformat(_match_start.replace("Z", "+00:00"))
                _now = datetime.now(timezone.utc)
                _pre_match = _now < _start_dt
                _mins_since_start = (_now - _start_dt).total_seconds() / 60
            except (ValueError, TypeError):
                pass

        # Near-resolve: our side ≥94¢ → exit, don't risk 6¢ for resolve
        # SANITY: reject if match hasn't started or just started (<5min).
        # WebSocket sometimes delivers spike prices (0.00 or 1.00) at open/first tick,
        # which falsely trigger near_resolve. A real 94% means the match is essentially
        # decided, which cannot happen in the first 5 minutes.
        if effective_current >= 0.94:
            if _pre_match:
                logger.warning("WS near_resolve REJECTED [pre_match]: %s | eff=%.0f%% (match not started)",
                               pos.slug[:35], effective_current * 100)
                return
            if _mins_since_start is not None and _mins_since_start < 5.0:
                logger.warning("WS near_resolve REJECTED [just_started]: %s | eff=%.0f%% (%.1fmin in)",
                               pos.slug[:35], effective_current * 100, _mins_since_start)
                return
            self._ws_exit_queue.append((cid, "near_resolve_profit"))
            self._ws_exit_queued_set.add(cid)
            logger.info("WS_EXIT queued [near_resolve]: %s | eff=%.0f%%", pos.slug[:35], effective_current * 100)
            return

        # A-conf hold-to-resolve check (reused by SL and TP)
        _a_conf_hold = (pos.confidence == "A"
                        and effective_entry >= 0.60)

        # 1. Stop-loss check -- unified rules via helper
        # A-conf hold-to-resolve: skip flat SL, only catastrophic floor + market flip apply
        # Pre-match: skip SL/TP (match hasn't started, price noise not actionable)
        if not _a_conf_hold and not _pre_match:
            sl_pct = compute_stop_loss_pct(pos, base_sl_pct=self.config.risk.stop_loss_pct)
            if sl_pct is not None and pnl_pct <= -abs(sl_pct):
                self._ws_exit_queue.append((cid, "stop_loss"))
                self._ws_exit_queued_set.add(cid)
                logger.info(
                    "WS_EXIT queued [stop_loss]: %s | pnl=%.1f%% <= -%.0f%%",
                    pos.slug[:35], pnl_pct * 100, abs(sl_pct) * 100,
                )
                return

        # 2a. Scale-out check (WS path — catches fast spikes that light cycle misses)
        if not pos.volatility_swing and not _a_conf_hold:
            from src.scale_out import check_scale_out
            so = check_scale_out(
                scale_out_tier=pos.scale_out_tier,
                unrealized_pnl_pct=pnl_pct,
                volatility_swing=pos.volatility_swing,
            )
            if so is not None:
                if not hasattr(self, '_ws_scale_out_queue'):
                    self._ws_scale_out_queue = []
                if not hasattr(self, '_ws_scale_out_queued_set'):
                    self._ws_scale_out_queued_set = set()
                if cid not in self._ws_scale_out_queued_set:
                    self._ws_scale_out_queue.append((cid, so))
                    self._ws_scale_out_queued_set.add(cid)
                    # Force flag so process_scale_outs executes even if price drops back
                    pos.force_scale_out_tier = so["tier"]
                    logger.info("WS_SCALE_OUT queued: %s | tier=%s pnl=%.1f%%",
                                pos.slug[:35], so["tier"], pnl_pct * 100)

        # 2b. Trailing TP check (non-VS, non-A-conf-hold, post-match-start only)
        ttp_cfg = self.config.trailing_tp
        if ttp_cfg.enabled and not pos.volatility_swing and not _a_conf_hold and not _pre_match:
            # Update peak tracking -- always in effective space
            # BUY_YES: effective = YES price (higher = better)
            # BUY_NO:  effective = NO value = 1 - YES price (higher = better)
            eff_current = effective_price(current, direction)
            if eff_current > pos.peak_price or pos.peak_price == 0:
                pos.peak_price = eff_current

            # Calculate peak P&L (peak_price is in effective space)
            eff_entry = effective_price(entry, direction)
            peak_pnl = (pos.peak_price - eff_entry) / eff_entry if eff_entry > 0 else 0
            pos.peak_pnl_pct = max(pos.peak_pnl_pct, peak_pnl)

            act_pct = ttp_cfg.activation_pct
            trail_dist = ttp_cfg.trail_distance

            if pos.peak_pnl_pct >= act_pct:
                ttp_result = calculate_trailing_tp(
                    entry_price=entry,
                    current_price=current,
                    direction=direction,
                    peak_price=pos.peak_price,
                    trailing_active=True,
                    activation_pct=act_pct,
                    trail_distance=trail_dist,
                )
                if ttp_result["action"] == "EXIT":
                    self._ws_exit_queue.append((cid, f"trailing_tp: {ttp_result['reason']}"))
                    self._ws_exit_queued_set.add(cid)
                    logger.info(
                        "WS_EXIT queued [trailing_tp]: %s | %s",
                        pos.slug[:35], ttp_result["reason"],
                    )
                    return

    def drain_scale_outs(self) -> list[tuple[str, dict]]:
        """Pop WS-triggered scale-out signals. Called by agent before process_scale_outs."""
        if not hasattr(self, '_ws_scale_out_queue'):
            return []
        result = list(self._ws_scale_out_queue)
        self._ws_scale_out_queue.clear()
        if hasattr(self, '_ws_scale_out_queued_set'):
            self._ws_scale_out_queued_set.clear()
        return result

    def drain(self) -> list[tuple[str, str]]:
        """Pop all WS-triggered exits and return them.

        Call at top of each cycle. agent.py calls _exit_position(cid, reason) for each.
        Applies the _exiting_set guard before returning.
        """
        exits: list[tuple[str, str]] = []
        while self._ws_exit_queue:
            cid, reason = self._ws_exit_queue.popleft()
            if cid in self._exiting_set:
                continue  # Already being exited -- double-exit guard
            exits.append((cid, reason))
        self._ws_exit_queued_set.clear()
        return exits

    # ── Cycle exit checks ─────────────────────────────────────────────────

    def _common_exit_checks(self) -> tuple[list[tuple[str, str]], set[str], dict[str, list[str]]]:
        """Shared exit logic for both heavy and light cycles.

        Returns (result_list, seen_cids, all_triggered) for callers to extend.
        Runs: match-aware exits, stop-losses, consensus thesis, trailing TP (non-VS).
        """
        from src.trailing_tp import calculate_trailing_tp

        result: list[tuple[str, str]] = []
        cfg = self.config
        seen_cids: set[str] = set()
        _all_triggered: dict[str, list[str]] = {}

        def _add(cid: str, reason: str) -> None:
            _all_triggered.setdefault(cid, []).append(reason)
            if cid not in seen_cids and cid not in self._exiting_set:
                result.append((cid, reason))
                seen_cids.add(cid)

        # 0. Near-resolve profit: our side ≥94¢ → exit immediately
        # SANITY: reject if match hasn't started or just started (<5min) — WS spikes
        # at match open falsely trigger this. Real 94% cannot happen in first 5min.
        from datetime import datetime, timezone
        _now_ts = datetime.now(timezone.utc)
        for cid, pos in list(self.portfolio.positions.items()):
            _eff = effective_price(pos.current_price, pos.direction)
            if _eff >= 0.94:
                _ms = getattr(pos, "match_start_iso", "") or ""
                if _ms:
                    try:
                        _sd = datetime.fromisoformat(_ms.replace("Z", "+00:00"))
                        _mins = (_now_ts - _sd).total_seconds() / 60
                        if _mins < 5.0:
                            logger.warning(
                                "near_resolve REJECTED [%s]: %s | eff=%.0f%% (%.1fmin in)",
                                "pre_match" if _mins < 0 else "just_started",
                                pos.slug[:35], _eff * 100, _mins,
                            )
                            continue
                    except (ValueError, TypeError):
                        pass
                _add(cid, "near_resolve_profit")

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

        # 2b. Consensus thesis invalidation (eff price < 55% = thesis broken)
        for cid in self.portfolio.check_consensus_thesis():
            _add(cid, "consensus_thesis_invalidated")

        # 3. Trailing take-profit (non-VS, non-A-conf-hold positions)
        ttp_cfg = cfg.trailing_tp
        if ttp_cfg.enabled:
            for cid, pos in list(self.portfolio.positions.items()):
                if pos.volatility_swing:
                    continue
                if cid in seen_cids:
                    continue
                # A-conf hold-to-resolve: skip trailing TP, hold until resolution
                _eff_entry = effective_price(pos.entry_price, pos.direction)
                if pos.confidence == "A" and _eff_entry >= 0.60:
                    continue
                act_pct = ttp_cfg.activation_pct
                trail_dist = ttp_cfg.trail_distance
                ttp_result = calculate_trailing_tp(
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    direction=pos.direction,
                    peak_price=pos.peak_price,
                    trailing_active=pos.peak_pnl_pct >= act_pct,
                    activation_pct=act_pct,
                    trail_distance=trail_dist,
                )
                if ttp_result["peak_price"] > pos.peak_price:
                    pos.peak_price = ttp_result["peak_price"]
                if ttp_result["action"] == "EXIT":
                    _add(cid, f"trailing_tp: {ttp_result['reason']}")

        return result, seen_cids, _all_triggered

    @staticmethod
    def _log_exit_details(_all_triggered: dict[str, list[str]]) -> None:
        for cid, rules in _all_triggered.items():
            if len(rules) > 1:
                logger.info("EXIT_DETAIL: %s | fired=%s | also_triggered=%s",
                             cid[:20], rules[0], rules[1:])

    def check_exits(
        self,
        cycle_count: int,
    ) -> list[tuple[str, str]]:
        """Run all exit detectors. Return (cid, reason) list.

        Agent calls _exit_position(cid, reason) for each returned pair.
        Called once per heavy cycle. Includes VS trailing stop (not in light cycle).
        """
        from src.trailing_tp import calculate_trailing_tp

        result, seen_cids, _all_triggered = self._common_exit_checks()
        cfg = self.config

        def _add(cid: str, reason: str) -> None:
            _all_triggered.setdefault(cid, []).append(reason)
            if cid not in seen_cids and cid not in self._exiting_set:
                result.append((cid, reason))
                seen_cids.add(cid)

        # 4. VS trailing stop (heavy cycle only — tighten near resolution)
        ttp_cfg = cfg.trailing_tp
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

        self._log_exit_details(_all_triggered)
        return result

    def check_exits_light(self) -> list[tuple[str, str]]:
        """Subset of exit checks for light cycles (price-only, no AI).

        Light cycles run every 2 minutes. Includes VS trailing TP for
        real-time protection of fast-moving volatility swing positions.
        """
        from src.trailing_tp import calculate_trailing_tp

        result, seen_cids, _all_triggered = self._common_exit_checks()
        cfg = self.config

        def _add(cid: str, reason: str) -> None:
            _all_triggered.setdefault(cid, []).append(reason)
            if cid not in seen_cids and cid not in self._exiting_set:
                result.append((cid, reason))
                seen_cids.add(cid)

        # VS trailing stop (same logic as heavy cycle)
        ttp_cfg = cfg.trailing_tp
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

        self._log_exit_details(_all_triggered)
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
