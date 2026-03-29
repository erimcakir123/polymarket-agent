"""agent.py -- Thin agent loop. Coordinates EntryGate and ExitMonitor.

Responsibilities:
  - Initialize all modules (entry_gate, exit_monitor, portfolio, executor, etc.)
  - run_cycle(): heavy cycle -- scanning, AI analysis, upset/early/penny entries
  - run_light_cycle(): fast cycle (5s) -- exits, live_dip, momentum, farming re-entry,
    scale-outs (with per-strategy cooldowns to avoid spamming)
  - _exit_position(): execute position exit (reentry pool, blacklist, logging)
  - _check_farming_reentry(): reentry pool check (no AI cost)
  - run(): main loop
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone, date
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.config import AppConfig, load_config, Mode
from src.portfolio import Portfolio
from src.executor import Executor
from src.ai_analyst import AIAnalyst
from src.market_scanner import MarketScanner
from src.risk_manager import RiskManager, confidence_position_size
from src.odds_api import OddsAPIClient
from src.esports_data import EsportsDataClient
from src.sports_data import SportsDataClient
from src.sports_discovery import SportsDiscovery
from src.news_scanner import NewsScanner
from src.manipulation_guard import ManipulationGuard
from src.trade_logger import TradeLogger, EdgeSourceTracker
from src.notifier import TelegramNotifier
from src.websocket_feed import WebSocketFeed
from src.circuit_breaker import CircuitBreaker
from src.reentry_farming import ReentryPool, check_reentry
from src.reentry import Blacklist, get_blacklist_rule
from src.outcome_tracker import OutcomeTracker
from src.cycle_timer import CycleTimer
from src.scout_scheduler import ScoutScheduler
from src.entry_gate import EntryGate
from src.exit_monitor import ExitMonitor
from src.models import effective_price
from src.risk_manager import exceeds_exposure_limit

logger = logging.getLogger(__name__)

# Exits that should never be demoted to stock (permanent skip)
_NEVER_STOCK_EXITS = frozenset({
    "hard_halt_drawdown", "hard_halt", "stop_loss", "esports_halftime",
    "resolved", "near_resolve",
})
_NEVER_STOCK_PREFIXES = ("match_exit_", "election_reeval", "early_penny_")

# Light-cycle cooldowns: strategy_name → ticks before next run (1 tick = 5s)
_LIGHT_COOLDOWNS = {
    "live_dip": 60,        # 5 min (60 × 5s)
    "momentum": 36,        # 3 min (36 × 5s)
    "farming_reentry": 24, # 2 min (24 × 5s)
    "scale_out": 12,       # 1 min (12 × 5s)
}


class Agent:
    """Thin orchestrator. Delegates entry to EntryGate, exit detection to ExitMonitor."""

    STOP_FILE = Path("logs/stop_signal")

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.running = True
        self.cycle_count = 0
        self._soft_halt_active = False
        self._cb_was_active = False
        self.consecutive_api_failures = 0
        self.last_cycle_has_live_clob = False
        self._last_candidate_count = 0
        self.light_cycle_count: int = 0
        self._light_cooldowns: dict[str, int] = {}  # strategy_name → expires_at_light_tick

        # Exit infrastructure (owned by agent -- _exit_position needs these)
        self._exit_cooldowns: dict[str, int] = {}
        self._exited_markets: set[str] = self._load_exited_markets()
        self._match_states: dict[str, dict] = {}
        self._last_match_state_fetch: float = 0.0
        self._daily_reentry_count: int = 0
        self._last_reentry_reset_date: date = datetime.now(timezone.utc).date()
        self.bets_since_approval: int = 0
        self._pre_match_prices: dict[str, float] = {}  # Cache first-seen YES price per market

        # Core modules
        self.portfolio = Portfolio(initial_bankroll=config.initial_bankroll)
        self.circuit_breaker = CircuitBreaker()
        self.blacklist = Blacklist(path="logs/blacklist.json")
        self.reentry_pool = ReentryPool()
        self.outcome_tracker = OutcomeTracker()
        self.cycle_timer = CycleTimer(config.cycle)

        # Signal enhancers
        self.esports = EsportsDataClient()
        sports = SportsDataClient()
        odds_api = OddsAPIClient()
        self.odds_api = odds_api
        from src.cricket_data import CricketDataClient
        cricket = CricketDataClient()
        discovery = SportsDiscovery(
            espn=sports, pandascore=self.esports,
            cricket=cricket, odds_api=odds_api,
        )
        news_scanner = NewsScanner()
        manip_guard = ManipulationGuard()
        scanner = MarketScanner(config.scanner)
        self.ai = AIAnalyst(config.ai)
        risk = RiskManager(config.risk)
        self.scout = ScoutScheduler(sports, self.esports)
        self.edge_tracker = EdgeSourceTracker()
        self.risk = risk

        # Loggers & notifications
        self.trade_log = TradeLogger(config.logging.trades_file)
        self.portfolio_log = TradeLogger(config.logging.portfolio_file)
        self.perf_log = TradeLogger(config.logging.performance_file)
        self.notifier = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            enabled=config.notifications.telegram_enabled,
        )
        odds_api.set_notifier(self.notifier)

        # Wallet & executor
        self.wallet = None
        clob_client = None
        if config.mode == Mode.LIVE:
            from src.wallet import Wallet
            pk = os.getenv("POLYGON_PRIVATE_KEY", "")
            if pk:
                self.wallet = Wallet(private_key=pk)
                try:
                    from py_clob_client.client import ClobClient
                    clob_client = ClobClient(
                        "https://clob.polymarket.com", key=pk, chain_id=137,
                        signature_type=int(os.getenv("SIGNATURE_TYPE", "0")),
                        funder=os.getenv("PROXY_WALLET_ADDRESS", "") or None,
                    )
                    clob_client.set_api_creds(clob_client.create_or_derive_api_creds())
                except Exception as exc:
                    logger.error("CLOB init failed: %s", exc)
        self.executor = Executor(mode=config.mode, clob_client=clob_client)

        # WebSocket feed (exit_monitor registers callback below)
        ws_feed = WebSocketFeed(on_price_update=None)  # callback set by ExitMonitor

        # Composed modules
        self.exit_monitor = ExitMonitor(self.portfolio, ws_feed, config)
        self.entry_gate = EntryGate(
            config=config,
            portfolio=self.portfolio,
            executor=self.executor,
            ai=self.ai,
            scanner=scanner,
            risk=risk,
            odds_api=odds_api,
            esports=self.esports,
            news_scanner=news_scanner,
            manip_guard=manip_guard,
            trade_log=self.trade_log,
            notifier=self.notifier,
            discovery=discovery,
            scout=self.scout,
        )
        self.ws_feed = ws_feed
        self.scanner = scanner

    # ── Main loop ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """Main agent loop. Alternates heavy and light cycles."""
        import signal as _signal
        logger.info("Agent starting -- mode=%s", self.config.mode.value)
        self.consecutive_api_failures = 0
        last_full_cycle_time = 0.0
        try:
            try:
                _signal.signal(_signal.SIGTERM, lambda signum, frame: setattr(self, 'running', False))
            except (OSError, AttributeError):
                pass

            while self.running:
                self._check_stop_file()
                if not self.running:
                    break

                has_positions = len(self.portfolio.positions) > 0
                vs_near_match = False
                if has_positions:
                    vs_positions = [p for p in self.portfolio.positions.values() if p.volatility_swing]
                    if vs_positions:
                        now = datetime.now(timezone.utc)
                        for vp in vs_positions:
                            _vp_time = vp.match_start_iso or vp.end_date_iso
                            if _vp_time:
                                try:
                                    end_dt = datetime.fromisoformat(_vp_time.replace("Z", "+00:00"))
                                    hours_left = (end_dt - now).total_seconds() / 3600
                                    if hours_left <= 4.0:
                                        vs_near_match = True
                                        break
                                except (ValueError, TypeError):
                                    pass

                time_since_full = time.time() - last_full_cycle_time
                dynamic_interval = self.cycle_timer.get_interval()
                full_interval_sec = dynamic_interval * 60
                run_full = not has_positions or time_since_full >= full_interval_sec

                try:
                    if run_full:
                        self.entry_gate.reset_seen_markets()  # Fresh cycle -> scan from top
                        self.run_cycle()
                        last_full_cycle_time = time.time()
                        # Auto-refill: keep running hard cycles until slots full
                        # Each refill analyzes the NEXT batch (seen_market_ids tracks offset)
                        vs_reserved = self.config.volatility_swing.reserved_slots
                        _refill_round = 0
                        _prev_seen = len(self.entry_gate._seen_market_ids)
                        while True:
                            current_vs = sum(1 for p in self.portfolio.positions.values() if p.volatility_swing)
                            current_normal = self.portfolio.active_position_count - current_vs
                            open_slots = self.config.risk.max_positions - vs_reserved - current_normal
                            if open_slots <= 0:
                                logger.info("All slots filled -- refill complete")
                                break
                            _refill_round += 1
                            positions_before = len(self.portfolio.positions)
                            seen_count = len(self.entry_gate._seen_market_ids)
                            logger.info("Pool not full (%d open slots) -- refill cycle %d (seen %d markets)",
                                        open_slots, _refill_round, seen_count)
                            self.run_cycle()
                            last_full_cycle_time = time.time()
                            positions_after = len(self.portfolio.positions)
                            new_seen = len(self.entry_gate._seen_market_ids)
                            new_entries = positions_after - positions_before
                            if new_entries > 0:
                                logger.info("Refill cycle %d added %d positions", _refill_round, new_entries)
                            else:
                                logger.info("Refill cycle %d -- no new entries (seen %d markets so far)",
                                            _refill_round, new_seen)
                            # If no new markets were analyzed, eligible pool is exhausted
                            if new_seen == _prev_seen:
                                logger.info("Eligible pool exhausted -- no unseen markets left. Refill done.")
                                break
                            _prev_seen = new_seen
                    else:
                        self.run_light_cycle()
                    self.consecutive_api_failures = 0
                except Exception as exc:
                    self.consecutive_api_failures += 1
                    logger.error("Cycle error (%d): %s", self.consecutive_api_failures, exc, exc_info=True)
                    if self.consecutive_api_failures >= 3:
                        logger.warning("3 consecutive failures -- pausing 5 min")
                        time.sleep(300)
                        self.consecutive_api_failures = 0

                self.cycle_timer.tick()

                if not (self.cycle_timer._override and self.cycle_timer._override_cycles > 0):
                    active_count = getattr(self, '_last_candidate_count', 0)
                    self.cycle_timer.signal_market_aware(active_count, len(self.portfolio.positions))

                for pos in self.portfolio.positions.values():
                    if pos.unrealized_pnl_pct < -(self.config.risk.stop_loss_pct * 0.83):
                        self.cycle_timer.signal_near_stop_loss()
                        break

                if getattr(self, 'last_cycle_has_live_clob', False):
                    self.cycle_timer.signal_live_positions()

                if vs_near_match:
                    self.cycle_timer.signal_volatility_swing(
                        polling_min=self.config.volatility_swing.polling_interval_min)

                upcoming = self.scout.get_upcoming_match_times()
                if upcoming:
                    now_utc = datetime.now(timezone.utc)
                    for mt in upcoming:
                        hours_until = (mt - now_utc).total_seconds() / 3600
                        if 0 < hours_until < 3:
                            self.cycle_timer.signal_scout_approaching()
                            logger.info("Scouted match in %.1fh -- polling every 5 min", hours_until)
                            break

                self._write_status("waiting", "Waiting")

                # Sleep between iterations
                # Light cycles: 5s (fast exit detection via WS prices)
                # After full cycle: 60s (next full gated by cycle_timer anyway)
                time.sleep(5 if has_positions and not run_full else 60)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self._write_status("offline", "Stopped")
            self.ws_feed.stop()
            logger.info("Agent stopped")

    def run_light_cycle(self) -> None:
        """Price-only cycle: update prices + check exits. No scan, no AI."""
        self._write_status("running", "Light cycle")
        if self._is_paused():
            return
        logger.info("=== Light cycle ===")

        # Process WS ticks first (main thread)
        self.exit_monitor.process_ws_ticks()

        # Drain WS exits
        for cid, reason in self.exit_monitor.drain():
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self._exit_position(cid, reason)

        # Update prices
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.portfolio.update_bankroll(bankroll)
        if not self.ws_feed.connected:
            self._update_position_prices()
        self._sync_ws_subscriptions()

        # Fetch live match states
        match_states = self._fetch_match_states()

        # Light exit checks
        for cid, reason in self.exit_monitor.check_exits_light(match_states):
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self._exit_position(cid, reason)

        # Handle hold-revoke/restore (match_exit meta -- mutates pos directly)
        self._handle_hold_revokes()

        self.light_cycle_count += 1

        # --- Light cycle action strategies (with per-strategy cooldowns) ---
        held_events = self._get_held_event_ids()

        # Fetch fresh market data once for all strategies that need it
        _need_markets = (
            self._light_cooldown_ready("live_dip")
            or self._light_cooldown_ready("momentum")
        )
        light_fresh_markets = self.scanner.fetch() if _need_markets else []

        # Cache pre-match prices from fresh scan (first-seen only).
        # NOTE: _pre_match_prices is populated by both heavy and light cycles.
        # All writes are first-seen-only (idempotent). Light cycle strategies
        # only READ existing entries for dip/momentum detection.
        for m in light_fresh_markets:
            if m.condition_id not in self._pre_match_prices and m.yes_price > 0:
                self._pre_match_prices[m.condition_id] = m.yes_price

        if self._light_cooldown_ready("scale_out"):
            self._process_scale_outs()
            self._set_light_cooldown("scale_out")

        if self._light_cooldown_ready("farming_reentry"):
            entered = self._check_farming_reentry()
            if entered:
                self._set_light_cooldown("farming_reentry")

        if self._light_cooldown_ready("live_dip"):
            entered = self._check_live_dip(held_events, light_fresh_markets)
            if entered:
                self._set_light_cooldown("live_dip")

        if self._light_cooldown_ready("momentum"):
            entered = self._check_live_momentum(held_events, light_fresh_markets, match_states)
            if entered:
                self._set_light_cooldown("momentum")

        # Persist portfolio snapshot so dashboard sees real-time PnL
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self._log_cycle_summary(bankroll, "light")

    def run_cycle(self) -> None:
        """Heavy cycle: exit checks + market scan + AI + entry decisions."""
        self._write_status("running", "Hard cycle")
        if self._is_paused():
            return
        self.cycle_count += 1
        self.risk.new_cycle()
        logger.info("=== Cycle #%d start ===", self.cycle_count)

        # Self-reflection
        self._maybe_run_reflection()

        # Bankroll + drawdown
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.portfolio.update_bankroll(bankroll)
        dd_level = self.portfolio.get_drawdown_level()
        if dd_level == "hard":
            self.notifier.send("🚨 HARD HALT: equity < 35% HWM -- closing all positions")
            for cid in list(self.portfolio.positions.keys()):
                if not self.exit_monitor.is_exiting(cid):
                    self._exit_position(cid, "hard_halt_drawdown")
            self.running = False
            return
        elif dd_level == "soft":
            if not self._soft_halt_active:
                self.notifier.send("⚠️ SOFT HALT: equity < 50% HWM -- yeni entry durduruldu")
                self._soft_halt_active = True
        else:
            if self._soft_halt_active:
                self.notifier.send("✅ Drawdown recovered -- entries resumed")
                self._soft_halt_active = False

        # Circuit breaker
        halt, halt_reason = self.circuit_breaker.should_halt_entries()
        if halt and not self._cb_was_active:
            self.notifier.send(f"⚠️ Circuit breaker ACTIVATED: {halt_reason}")
            self._cb_was_active = True
        elif not halt and self._cb_was_active:
            self.notifier.send("✅ Circuit breaker deactivated -- entries resumed")
            self._cb_was_active = False
        if self._soft_halt_active:
            halt = True

        # Manual entry pause -- drop logs/no_new_entries to skip market scanning
        if Path("logs/no_new_entries").exists():
            halt = True
            logger.info("Entry pause active (logs/no_new_entries exists)")

        entries_allowed = not halt

        # Check resolved markets
        self._write_status("running", "Checking exits")
        self._check_resolved_markets()

        # Update prices
        self._update_position_prices()
        self._check_price_drift_reanalysis()

        # Process WS ticks first (main thread)
        self.exit_monitor.process_ws_ticks()

        # Exit detection + execution
        for cid, reason in self.exit_monitor.drain():
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self._exit_position(cid, reason)

        match_states = self._fetch_match_states()
        for cid, reason in self.exit_monitor.check_exits(match_states, self.cycle_count):
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self._exit_position(cid, reason)
        self._handle_hold_revokes()
        # NOTE: _process_scale_outs() moved to light cycle with cooldown
        self._sync_ws_subscriptions()

        # Scout + Entry: fresh scan (analyze=True)
        if entries_allowed and self.scout.should_run_scout():
            self._write_status("running", "Scouting matches")
            new_scouted = self.scout.run_scout()
            if new_scouted:
                self.notifier.send(f"🔍 SCOUT: {new_scouted} new matches")

        self._write_status("running", "Scanning markets")
        fresh_markets = self.scanner.fetch()

        # Cache pre-match prices (first-seen only) for live_dip/momentum in light cycle
        for m in fresh_markets:
            if m.condition_id not in self._pre_match_prices and m.yes_price > 0:
                self._pre_match_prices[m.condition_id] = m.yes_price

        self.entry_gate.run(
            fresh_markets, entries_allowed=entries_allowed, analyze=True,
            bankroll=bankroll, cycle_count=self.cycle_count,
            blacklist=self.blacklist, exited_markets=self._exited_markets,
        )

        # Breaking news detected -> shorten cycle interval
        if self.entry_gate._breaking_news_detected:
            self.entry_gate._breaking_news_detected = False
            self.cycle_timer.signal_breaking_news()
            logger.info("Breaking news detected -- cycle shortened to %d min", self.config.cycle.breaking_news_interval_min)

        self._write_status("running", "Evaluating entries")
        # Entry: stock queue drain (analyze=False -- no AI cost)
        self.entry_gate.drain_stock(
            entries_allowed=entries_allowed, bankroll=bankroll,
            cycle_count=self.cycle_count, blacklist=self.blacklist,
            exited_markets=self._exited_markets,
        )

        # NOTE: farming_reentry, live_dip, live_momentum, scale_outs moved to light cycle
        # Upset hunter stays in heavy cycle (needs fresh scan data + AI analysis)
        if entries_allowed:
            self._check_upset_hunter(fresh_markets, bankroll)

        # Check outcomes + log
        self._check_tracked_outcomes()
        self._log_cycle_summary(bankroll, "ok")

    # ── Exit execution ─────────────────────────────────────────────────────

    def _exit_position(self, condition_id: str, reason: str, cooldown_cycles: int = 1) -> None:
        """Execute exit: remove from portfolio, add to reentry pool or blacklist, log.

        This is the ONLY place that calls executor.exit(). ExitMonitor detects,
        Agent executes.
        """
        self.exit_monitor.mark_exiting(condition_id)
        try:
            pos = self.portfolio.remove_position(condition_id)
        finally:
            self.exit_monitor.unmark_exiting(condition_id)
        if not pos:
            return

        self._exit_cooldowns[condition_id] = self.cycle_count + cooldown_cycles

        # Execute via executor
        self.executor.exit_position(pos, reason=reason, mode=self.config.mode)

        # Record realized PnL
        realized_pnl = pos.unrealized_pnl_usdc
        self.portfolio.record_realized(realized_pnl)

        # Profitable exit -> add to farming re-entry pool
        profitable_reasons = {
            "take_profit", "trailing_stop", "spike_exit",
            "edge_tp", "scale_out_final", "vs_take_profit",
        }
        if reason in profitable_reasons and realized_pnl > 0:
            existing_pool = self.reentry_pool.get(condition_id)
            original_entry = existing_pool.original_entry_price if existing_pool else pos.entry_price
            self.reentry_pool.add(
                condition_id=condition_id,
                event_id=getattr(pos, "event_id", "") or "",
                slug=pos.slug,
                question=getattr(pos, "question", ""),
                direction=pos.direction,
                token_id=pos.token_id,
                ai_probability=pos.ai_probability,
                confidence=pos.confidence,
                original_entry_price=original_entry,
                exit_price=pos.current_price,
                exit_cycle=self.cycle_count,
                end_date_iso=getattr(pos, "end_date_iso", ""),
                match_start_iso=getattr(pos, "match_start_iso", ""),
                sport_tag=getattr(pos, "sport_tag", ""),
                number_of_games=getattr(pos, "number_of_games", 0),
                was_scouted=getattr(pos, "scouted", False),
                realized_pnl=realized_pnl,
            )
        elif reason == "stop_loss":
            # Lossy re-entry: SL exits can rejoin pool under strict conditions
            _sl_count = getattr(pos, 'sl_reentry_count', 0)
            if _sl_count >= 1:
                # 2nd SL after lossy re-entry = permanent blacklist
                self.blacklist.add(
                    condition_id,
                    exit_reason="stop_loss_2nd",
                    blacklist_type="permanent",
                    expires_at_cycle=None,
                    exit_data={"slug": pos.slug},
                )
                logger.info("BLACKLIST: 2nd SL after lossy re-entry, permanent ban: %s", pos.slug[:40])
            elif pos.ai_probability >= 0.65:
                # AI still believes in the market -- add to pool for potential recovery
                existing_pool = self.reentry_pool.get(condition_id)
                original_entry = existing_pool.original_entry_price if existing_pool else pos.entry_price
                self.reentry_pool.add(
                    condition_id=condition_id,
                    event_id=getattr(pos, "event_id", "") or "",
                    slug=pos.slug,
                    question=getattr(pos, "question", ""),
                    direction=pos.direction,
                    token_id=pos.token_id,
                    ai_probability=pos.ai_probability,
                    confidence=pos.confidence,
                    original_entry_price=original_entry,
                    exit_price=pos.current_price,
                    exit_cycle=self.cycle_count,
                    end_date_iso=getattr(pos, "end_date_iso", ""),
                    match_start_iso=getattr(pos, "match_start_iso", ""),
                    sport_tag=getattr(pos, "sport_tag", ""),
                    number_of_games=getattr(pos, "number_of_games", 0),
                    was_scouted=getattr(pos, "scouted", False),
                    realized_pnl=realized_pnl,
                    exit_reason="stop_loss",
                    sl_reentry_count=0,
                )
                logger.info("REENTRY_POOL: SL exit added (AI=%.0f%%): %s",
                            pos.ai_probability * 100, pos.slug[:40])
            else:
                # AI prob < 65% -- normal blacklist for SL
                btype, duration = get_blacklist_rule("stop_loss")
                if btype and duration:
                    self.blacklist.add(
                        condition_id,
                        exit_reason=reason,
                        blacklist_type=btype,
                        expires_at_cycle=self.cycle_count + duration if duration else None,
                        exit_data={"slug": pos.slug},
                    )
        else:
            # Non-profitable -> demote to stock or blacklist
            _is_never_stock = (
                reason in _NEVER_STOCK_EXITS
                or any(reason.startswith(p) for p in _NEVER_STOCK_PREFIXES)
            )
            demoted = False
            if not _is_never_stock:
                demoted = self._try_demote_to_stock(pos, reason)
            if not demoted:
                # Blacklist
                bl_reason = reason
                for prefix in ("match_exit_", "early_penny_", "SLOT_UPGRADE", "election_reeval"):
                    if bl_reason.startswith(prefix):
                        bl_reason = prefix.rstrip("_")
                        break
                btype, duration = get_blacklist_rule(bl_reason)
                if btype and duration:
                    self.blacklist.add(
                        condition_id,
                        exit_reason=reason,
                        blacklist_type=btype,
                        expires_at_cycle=self.cycle_count + duration if duration else None,
                        exit_data={"slug": pos.slug},
                    )

        # Log exit
        self.trade_log.log({
            "market": pos.slug, "action": "EXIT",
            "reason": reason, "pnl": realized_pnl,
            "price": pos.entry_price, "exit_price": pos.current_price,
            "size": pos.size_usdc,
            "direction": pos.direction,
        })
        logger.info(
            "EXIT: %s | reason=%s | pnl=$%.2f | entry=%.2f exit=%.2f",
            pos.slug[:40], reason, realized_pnl, pos.entry_price, pos.current_price,
        )
        _pnl_emoji = "🟢" if realized_pnl >= 0 else "🔴"
        self.notifier.send(
            f"{_pnl_emoji} *EXIT*: {pos.slug[:40]}\n\n"
            f"📋 Reason: {reason}\n"
            f"💵 PnL: ${realized_pnl:+.2f}\n"
            f"📊 Entry: {pos.entry_price:.2f} -> Exit: {pos.current_price:.2f}"
        )

        # Mark permanently exited if resolved
        if reason in ("resolved", "near_resolve"):
            self._save_exited_market(condition_id)

        # Post-exit: save CLOB price history for calibration
        try:
            from src.price_history import save_price_history
            save_price_history(
                slug=pos.slug, token_id=pos.token_id,
                entry_price=pos.entry_price, exit_price=pos.current_price,
                exit_reason=reason, exit_layer="agent",
                match_start_iso=getattr(pos, "match_start_iso", ""),
                number_of_games=getattr(pos, "number_of_games", 0),
                ever_in_profit=pos.peak_pnl_pct > 0,
                peak_pnl_pct=pos.peak_pnl_pct,
                match_score=getattr(pos, "match_score", ""),
            )
        except Exception:
            pass

    def _process_scale_outs(self) -> None:
        """Check and execute partial scale-out exits for all positions."""
        from src.scale_out import apply_partial_exit

        upset_cfg = self.config.upset_hunter
        scale_outs = self.portfolio.check_scale_outs(
            upset_tier1_price=upset_cfg.scale_out_tier1_price,
            upset_tier1_sell_pct=upset_cfg.scale_out_tier1_sell_pct,
            upset_tier2_price=upset_cfg.scale_out_tier2_price,
            upset_tier2_sell_pct=upset_cfg.scale_out_tier2_sell_pct,
        )
        for so in scale_outs:
            cid = so["condition_id"]
            pos = self.portfolio.positions.get(cid)
            if not pos or self.exit_monitor.is_exiting(cid):
                continue

            shares_to_sell = pos.shares * so["sell_pct"]
            if shares_to_sell < 1.0:
                continue

            # Execute partial sell (disable hybrid to preserve exact share count)
            result = self.executor.place_order(
                pos.token_id, "SELL", pos.current_price,
                shares_to_sell * pos.current_price, use_hybrid=False,
            )
            if not result or result.get("status") == "error":
                continue

            fill_price = pos.current_price
            partial = apply_partial_exit(
                shares=pos.shares,
                size_usdc=pos.size_usdc,
                entry_price=pos.entry_price,
                direction=pos.direction,
                shares_sold=shares_to_sell,
                fill_price=fill_price,
                tier=so["tier"],
                original_shares=getattr(pos, "original_shares", None),
                original_size_usdc=getattr(pos, "original_size_usdc", None),
                scale_out_tier=pos.scale_out_tier,
            )

            # Update position in-place
            pos.shares = partial["remaining_shares"]
            pos.size_usdc = partial["remaining_size_usdc"]
            pos.scale_out_tier = partial["new_scale_out_tier"]
            if not hasattr(pos, "original_shares") or pos.original_shares is None:
                pos.original_shares = partial["original_shares"]
            if not hasattr(pos, "original_size_usdc") or pos.original_size_usdc is None:
                pos.original_size_usdc = partial["original_size_usdc"]

            # Record proceeds and realized PnL
            self.portfolio.record_realized(partial["realized_pnl"])

            # Close dust remainder
            if partial["status"] == "CLOSE_REMAINDER":
                self._exit_position(cid, "scale_out_final")
                continue

            self.trade_log.log({
                "market": pos.slug, "action": "SCALE_OUT",
                "tier": so["tier"], "sell_pct": so["sell_pct"],
                "shares_sold": shares_to_sell,
                "realized_pnl": partial["realized_pnl"],
                "remaining_shares": partial["remaining_shares"],
            })
            logger.info(
                "SCALE_OUT: %s | %s | sold %.0f shares | pnl=$%.2f | remaining=%.0f",
                pos.slug[:35], so["tier"], shares_to_sell,
                partial["realized_pnl"], partial["remaining_shares"],
            )

        # Persist position changes to disk
        if scale_outs:
            self.portfolio._save_positions()

    def _try_demote_to_stock(self, pos, reason: str) -> bool:
        """Demote exited position back to candidate stock queue for re-entry.

        Accepts if stock has room (< 10) OR score beats the worst existing entry.
        Returns True if demoted, False if rejected (-> caller will blacklist instead).
        """
        from src.models import MarketData, effective_price
        from src.ai_analyst import AIEstimate

        _CONF_SCORE: dict[str, int] = {"A": 4, "B+": 3, "B-": 2, "C": 1}
        STOCK_MAX = 10

        # Calculate ranking score from saved position data
        pos_edge = max(0.0, abs(pos.ai_probability - pos.current_price))
        pos_score = pos_edge * _CONF_SCORE.get(getattr(pos, "confidence", "C"), 1)

        stock = self.entry_gate._candidate_stock

        # Decide whether to accept
        if len(stock) < STOCK_MAX:
            accept = True
        else:
            worst_score = min((c.get("score", 0.0) for c in stock), default=0.0)
            accept = pos_score > worst_score
            if accept:
                # Evict worst entry to make room
                worst_idx = min(range(len(stock)), key=lambda i: stock[i].get("score", 0.0))
                stock.pop(worst_idx)

        if not accept:
            return False

        # Reconstruct MarketData from position fields
        is_buy_yes = pos.direction == "BUY_YES"
        try:
            market = MarketData(
                condition_id=pos.condition_id,
                question=getattr(pos, "question", ""),
                yes_price=pos.current_price,
                no_price=round(1.0 - pos.current_price, 4),
                yes_token_id=pos.token_id if is_buy_yes else "",
                no_token_id=pos.token_id if not is_buy_yes else "",
                slug=pos.slug,
                sport_tag=getattr(pos, "sport_tag", "") or "",
                event_id=getattr(pos, "event_id", "") or "",
                end_date_iso=getattr(pos, "end_date_iso", "") or "",
                match_start_iso=getattr(pos, "match_start_iso", "") or "",
            )
        except Exception as exc:
            logger.warning("Could not reconstruct MarketData for stock demotion: %s", exc)
            return False

        estimate = AIEstimate(
            ai_probability=pos.ai_probability,
            confidence=getattr(pos, "confidence", "B-"),
            reasoning_pro="(demoted -- re-evaluate at entry)",
            reasoning_con="",
        )

        candidate = {
            "score": pos_score,
            "condition_id": pos.condition_id,
            "market": market,
            "estimate": estimate,
            "direction": pos.direction,
            "edge": pos_edge,
            "adjusted_size": 0.0,  # recalculated at execution time
            "entry_reason": "demoted",
            "is_consensus": False,
            "is_early": False,
            "sanity": None,
            "manip_check": None,
        }

        self.entry_gate.push_to_stock(candidate)
        logger.info(
            "DEMOTED to stock: %s | score=%.3f | reason=%s | stock_size=%d",
            pos.slug[:35], pos_score, reason, len(self.entry_gate._candidate_stock),
        )
        return True

    # ── Light-cycle cooldown helpers ──────────────────────────────────────

    def _light_cooldown_ready(self, strategy: str) -> bool:
        """Check if strategy is off cooldown in light cycle."""
        return self.light_cycle_count >= self._light_cooldowns.get(strategy, 0)

    def _set_light_cooldown(self, strategy: str) -> None:
        """Set cooldown for strategy after action."""
        ticks = _LIGHT_COOLDOWNS.get(strategy, 0)
        self._light_cooldowns[strategy] = self.light_cycle_count + ticks

    def _get_held_event_ids(self) -> set[str]:
        """Get event IDs of all currently held positions. Prevents same-event dual-side."""
        return {p.event_id for p in self.portfolio.positions.values()}

    # ── Exposure guard ─────────────────────────────────────────────────────

    def _check_exposure_limit(self, candidate_size: float) -> bool:
        """Return True if adding candidate_size would exceed exposure limit."""
        return exceeds_exposure_limit(
            self.portfolio.positions, candidate_size,
            self.portfolio.bankroll, self.config.risk.max_exposure_pct,
        )

    # ── Farming re-entry ──────────────────────────────────────────────────

    def _check_farming_reentry(self) -> bool:
        """Unified farming re-entry -- check pool for dip opportunities (no AI cost).

        Replaces old spike_reentry and scouted_reentry with a 3-tier system.
        Returns True if any re-entry was made.
        """
        self.reentry_pool.cleanup_expired(self.cycle_count)

        # Reset daily reentry count at midnight (UTC)
        now_utc = datetime.now(timezone.utc)
        if self._last_reentry_reset_date != now_utc.date():
            self._daily_reentry_count = 0
            self._last_reentry_reset_date = now_utc.date()

        if not self.reentry_pool.candidates:
            return False

        held_event_ids = {
            p.event_id for p in self.portfolio.positions.values()
            if p.event_id
        }

        # Check slot availability
        vs_reserved = self.config.volatility_swing.reserved_slots
        current_vs = sum(1 for p in self.portfolio.positions.values() if p.volatility_swing)
        current_normal = self.portfolio.active_position_count - current_vs

        entered = False
        for cid, candidate in list(self.reentry_pool.candidates.items()):
            # Cooldown check
            if self._exit_cooldowns.get(cid, 0) > self.cycle_count:
                continue

            # RE slot check -- max 3 concurrent re-entry positions
            RE_MAX_SLOTS = 3
            if self.portfolio.reentry_position_count >= RE_MAX_SLOTS:
                break  # No RE slots available

            # Fetch current price from Gamma
            try:
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"conditionId": cid}, timeout=10,
                )
                if resp.status_code != 200:
                    continue
                mkt_data = resp.json()
                if not mkt_data:
                    self.reentry_pool.remove(cid)
                    continue
                mkt = mkt_data[0] if isinstance(mkt_data, list) else mkt_data
                prices = json.loads(mkt.get("outcomePrices", '["0.5","0.5"]'))
                current_yes_price = float(prices[0])
            except (requests.RequestException, ValueError, IndexError, json.JSONDecodeError):
                continue

            # Update price history for stabilization tracking (use effective price for direction)
            eff_stab_price = effective_price(current_yes_price, candidate.direction)
            self.reentry_pool.update_price(cid, eff_stab_price)

            # Fetch match state for esports re-entry candidates
            re_match_state = self._match_states.get(cid)
            if not re_match_state and candidate.sport_tag.lower() in (
                "cs2", "csgo", "valorant", "lol", "dota2", "val"
            ):
                # Try to get live state from PandaScore for this candidate
                game_slug = self.esports.detect_game(candidate.question, [candidate.sport_tag])
                if game_slug:
                    team_a, team_b = self.esports._extract_team_names(candidate.question)
                    if team_a and team_b:
                        try:
                            re_match_state = self.esports.get_live_match_state(game_slug, team_a, team_b)
                        except Exception:
                            pass

            # Run decision logic
            decision = check_reentry(
                candidate=candidate,
                current_yes_price=current_yes_price,
                current_cycle=self.cycle_count,
                portfolio_positions=self.portfolio.positions,
                held_event_ids=held_event_ids,
                daily_reentry_count=self._daily_reentry_count,
                match_state=re_match_state,
            )

            if decision["action"] == "BLOCK":
                logger.debug("Farming re-entry BLOCK: %s | %s", candidate.slug[:35], decision["reason"])
                # All BLOCKs are permanent -> remove from pool
                self.reentry_pool.remove(cid)
                continue

            if decision["action"] == "WAIT":
                continue

            # --- ENTER ---
            direction = candidate.direction
            ai_prob = candidate.ai_probability
            size_mult = decision["size_mult"]

            # Calculate position size (confidence-based * tier multiplier)
            eff_price = effective_price(current_yes_price, direction)
            base_size = confidence_position_size(
                confidence=getattr(candidate, 'confidence', "B-"),
                bankroll=self.portfolio.bankroll,
                max_bet_usdc=self.config.risk.max_single_bet_usdc,
                max_bet_pct=self.config.risk.max_bet_pct,
                is_reentry=True,
            )
            size = base_size * size_mult

            if size < 5.0:
                continue  # Polymarket minimum

            # Profit protection cap
            if candidate.total_realized_profit > 0:
                max_risk = candidate.total_realized_profit * 0.50
                remaining_risk = max_risk - candidate.total_reentry_risk
                if remaining_risk <= 0:
                    logger.info("Farming skip (profit cap): %s", candidate.slug[:35])
                    continue
                size = min(size, remaining_risk)
                if size < 5.0:
                    continue

            token_id = candidate.token_id

            if self._check_exposure_limit(size):
                logger.info("SKIP exposure cap: would exceed %.0f%%", self.config.risk.max_exposure_pct * 100)
                continue

            result = self.executor.place_order(token_id, "BUY", eff_price, size)
            shares = size / eff_price if eff_price > 0 else 0
            yes_price_entry = current_yes_price

            tier_num = decision["tier"]
            reentry_num = candidate.reentry_count + 1
            _is_lossy = candidate.exit_reason == "stop_loss"
            entry_reason = f"re_entry_t{tier_num}_sl" if _is_lossy else f"re_entry_t{tier_num}"
            _sl_count = (candidate.sl_reentry_count + 1) if _is_lossy else 0

            self.portfolio.add_position(
                cid, token_id, direction,
                yes_price_entry, size, shares, candidate.slug,
                "", confidence=candidate.confidence,
                ai_probability=ai_prob,
                question=candidate.question,
                end_date_iso=candidate.end_date_iso,
                match_start_iso=candidate.match_start_iso,
                scouted=candidate.was_scouted,
                sport_tag=candidate.sport_tag,
                event_id=candidate.event_id,
                entry_reason=entry_reason,
                number_of_games=candidate.number_of_games,
                sl_reentry_count=_sl_count,
            )

            # Record in pool
            self.reentry_pool.record_reentry(cid, size)
            self._daily_reentry_count += 1
            current_normal += 1

            self.trade_log.log({
                "market": candidate.slug, "action": f"FARMING_REENTRY_{direction}",
                "size": size, "price": eff_price,
                "edge": decision["edge"],
                "confidence": candidate.confidence,
                "mode": self.config.mode.value,
                "status": result.get("status", ""),
                "ai_probability": ai_prob,
                "reentry_tier": tier_num,
                "reentry_count": reentry_num,
            })

            logger.info(
                "FARMING RE-ENTRY T%d (#%d): %s | %s @ %.0fc | edge=%.1f%% | size=$%.0f (%.0f%%) | no AI",
                tier_num, reentry_num, candidate.slug[:35], direction,
                eff_price * 100, decision["edge"] * 100, size, size_mult * 100,
            )
            self.notifier.send(
                f"\U0001f504 *FARMING RE-ENTRY* T{tier_num} (#{reentry_num}) -- Cycle #{self.cycle_count}\n\n"
                f"{candidate.question}\n"
                f"Exit: `{candidate.last_exit_price:.3f}` -> Re-entry: `{eff_price:.3f}`\n"
                f"Edge: `{decision['edge']:.1%}` | Size: `${size:.0f}` ({size_mult:.0%})\n"
                f"Profit so far: `${candidate.total_realized_profit:.2f}`\n"
                f"_No AI call -- using saved analysis_"
            )
            self.bets_since_approval += 1
            entered = True

        return entered

    # ── Live dip & momentum ─────────────────────────────────────────────

    def _check_live_dip(self, held_events: set[str] | None = None,
                        fresh_markets: list | None = None) -> bool:
        """Enter when favorite's market price drops 10%+ (no ESPN, pure price).

        Called from light cycle with cooldown. Uses cached _pre_match_prices.
        Accepts pre-fetched fresh_markets to avoid redundant scanner calls.
        Returns True if any entry was made.
        """
        if fresh_markets is None:
            fresh_markets = self.scanner.fetch()
        if not fresh_markets:
            return False

        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        cfg = self.config.live_momentum  # Uses live_momentum config for max_concurrent
        min_drop_pct = 0.10

        # Count current live_dip positions
        dip_count = sum(1 for p in self.portfolio.positions.values()
                        if getattr(p, "entry_reason", "") == "live_dip")
        if dip_count >= cfg.max_concurrent:
            return False

        # Use provided held_events or build from portfolio
        _dip_existing_eids = held_events if held_events is not None else (
            {getattr(p, "event_id", "") for p in self.portfolio.positions.values()} - {""}
        )

        entered = False
        for m in fresh_markets:
            if self.portfolio.active_position_count >= self.config.risk.max_positions:
                break
            if m.condition_id in self.portfolio.positions:
                continue
            if self.blacklist.is_blocked(m.condition_id, self.cycle_count):
                continue
            if m.condition_id in self._exited_markets:
                continue

            # Moneyline filter -- skip tournament/advance/qualify props
            _q = (getattr(m, "question", "") or "").lower()
            _slug = (m.slug or "").lower()
            _non_ml = ("advance", "qualify", "championship", "finalist",
                       "make the playoffs", "win the title", "win the tournament",
                       "win the cup", "win the league", "win the series",
                       "relegated", "promoted")
            if any(kw in _q or kw in _slug for kw in _non_ml):
                continue

            # Same-event dual-side check for live_dip (uses held_events from caller)
            _dip_eid = getattr(m, "event_id", "") or ""
            if _dip_eid and _dip_eid in _dip_existing_eids:
                logger.info("SKIP same-event dedup: %s", _dip_eid)
                continue

            pre_match = self._pre_match_prices.get(m.condition_id)
            if not pre_match:
                continue

            current_yes = m.yes_price
            if current_yes <= 0:
                continue

            # Check if favorite dropped 10%+
            direction = None
            drop_pct = 0.0

            if pre_match > 0.65:
                # YES was favorite, check if YES dropped
                drop = pre_match - current_yes
                drop_pct = drop / pre_match
                if drop_pct >= min_drop_pct:
                    direction = "BUY_YES"
            elif pre_match < 0.35:
                # NO was favorite, check if NO dropped (YES rose)
                no_pre = 1 - pre_match
                no_current = 1 - current_yes
                drop = no_pre - no_current
                drop_pct = drop / no_pre if no_pre > 0 else 0
                if drop_pct >= min_drop_pct:
                    direction = "BUY_NO"

            if not direction:
                continue

            # Size using confidence-based system
            from src.risk_manager import confidence_position_size
            size = confidence_position_size(
                confidence="B-", bankroll=bankroll,
                max_bet_usdc=self.config.risk.max_single_bet_usdc,
                max_bet_pct=self.config.risk.max_bet_pct,
            )
            if size < 5.0:
                continue

            # Get token_id
            if direction == "BUY_YES":
                token_id = m.yes_token_id
                price = current_yes
            else:
                token_id = m.no_token_id
                price = 1 - current_yes

            if not token_id:
                continue

            if self._check_exposure_limit(size):
                logger.info("SKIP exposure cap: would exceed %.0f%%", self.config.risk.max_exposure_pct * 100)
                continue

            result = self.executor.place_order(token_id, "BUY", price, size)
            if not result or result.get("status") == "error":
                continue

            shares = size / price if price > 0 else 0
            self.portfolio.add_position(
                m.condition_id, token_id, direction,
                m.yes_price, size, shares, m.slug,
                "", confidence="B-",
                ai_probability=max(0.01, min(0.99, pre_match)),
                entry_reason="live_dip",
                sport_tag=getattr(m, "sport_tag", "") or "",
                event_id=getattr(m, "event_id", "") or "",
                end_date_iso=getattr(m, "end_date_iso", "") or "",
            )
            dip_count += 1
            entered = True

            self.trade_log.log({
                "market": m.slug, "action": f"LIVE_DIP_{direction}",
                "size": size, "price": price,
                "pre_match_price": pre_match,
                "drop_pct": round(drop_pct, 3),
                "mode": self.config.mode.value,
            })
            logger.info(
                "LIVE DIP: %s | %s | pre=%.2f now=%.2f drop=%.0f%% | size=$%.0f",
                m.slug[:40], direction, pre_match, current_yes, drop_pct * 100, size,
            )
            self.notifier.send(
                f"📉 *LIVE DIP*: {m.slug[:40]}\n"
                f"Entry {direction} @ {price:.0%} | LIVE\n\n"
                f"📊 Pre-match: {pre_match:.0%} -> Now: {current_yes:.0%} (drop {drop_pct:.0%})\n"
                f"💰 Size: ${size:.0f}"
            )
        return entered

    def _check_live_momentum(self, held_events: set[str] | None = None,
                             fresh_markets: list | None = None,
                             match_states: dict | None = None) -> bool:
        """Score-based probability re-estimation for live matches.

        Called from light cycle with cooldown. Accepts pre-fetched fresh_markets
        to avoid redundant scanner calls.
        Returns True if any entry was made.
        """
        if not match_states:
            return False
        from src.live_momentum import detect_momentum_opportunity, calculate_score_adjusted_probability

        cfg = self.config.live_momentum
        if not cfg.enabled:
            return False

        # Use provided fresh_markets or fetch internally
        if fresh_markets is None:
            fresh_markets = self.scanner.fetch()
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll

        # Use provided held_events or build from portfolio
        _mom_held_eids = held_events if held_events is not None else (
            {getattr(p, "event_id", "") for p in self.portfolio.positions.values()} - {""}
        )

        momentum_count = sum(1 for p in self.portfolio.positions.values()
                             if getattr(p, "entry_reason", "") == "momentum")

        entered = False
        for cid, state in match_states.items():
            if not state:
                continue

            sport_tag = state.get("sport_tag", "")

            # Mode B: Update existing positions with score-adjusted probability
            if cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                adjusted = calculate_score_adjusted_probability(
                    pos.ai_probability, state, sport_tag, pos.direction,
                )
                if adjusted is not None:
                    pos.ai_probability = adjusted
                continue

            # Mode A: New entry if edge >= 6%
            if self.portfolio.active_position_count >= self.config.risk.max_positions:
                continue
            if momentum_count >= cfg.max_concurrent:
                continue
            if self.blacklist.is_blocked(cid, self.cycle_count):
                continue
            if cid in self._exited_markets:
                continue

            # Need pre-match price as probability baseline
            pre_match = self._pre_match_prices.get(cid)
            if not pre_match:
                continue

            # Find market in fresh_markets
            market = None
            if fresh_markets:
                for m in fresh_markets:
                    if m.condition_id == cid:
                        market = m
                        break
            if not market:
                continue

            # Same-event dual-side dedup
            _mom_eid = getattr(market, "event_id", "") or ""
            if _mom_eid and _mom_eid in _mom_held_eids:
                logger.info("SKIP same-event dedup: %s", _mom_eid)
                continue

            # Try both directions
            for direction in ("BUY_YES", "BUY_NO"):
                signal = detect_momentum_opportunity(
                    cid, pre_match, market.yes_price,
                    state, sport_tag, direction, min_edge=cfg.min_edge,
                )
                if not signal:
                    continue

                from src.risk_manager import confidence_position_size
                size = confidence_position_size(
                    confidence="B-", bankroll=bankroll,
                    max_bet_usdc=self.config.risk.max_single_bet_usdc,
                    max_bet_pct=cfg.bet_pct,
                )
                if size < 5.0:
                    continue

                if direction == "BUY_YES":
                    token_id = market.yes_token_id
                    price = market.yes_price
                else:
                    token_id = market.no_token_id
                    price = 1 - market.yes_price

                if not token_id:
                    continue

                if self._check_exposure_limit(size):
                    logger.info("SKIP exposure cap: would exceed %.0f%%", self.config.risk.max_exposure_pct * 100)
                    continue

                result = self.executor.place_order(token_id, "BUY", price, size)
                if not result or result.get("status") == "error":
                    continue

                shares = size / price if price > 0 else 0
                self.portfolio.add_position(
                    cid, token_id, direction,
                    market.yes_price, size, shares, market.slug,
                    "", confidence="B-",
                    ai_probability=signal.adjusted_prob,
                    entry_reason="momentum",
                    sport_tag=sport_tag,
                    event_id=getattr(market, "event_id", ""),
                    end_date_iso=getattr(market, "end_date_iso", ""),
                )
                momentum_count += 1
                entered = True

                self.trade_log.log({
                    "market": market.slug, "action": f"MOMENTUM_{direction}",
                    "size": size, "price": price,
                    "adjusted_prob": signal.adjusted_prob,
                    "edge": signal.edge,
                    "score_diff": signal.score_diff,
                    "mode": self.config.mode.value,
                })
                logger.info(
                    "MOMENTUM: %s | %s | edge=%.1f%% | adj_prob=%.1f%% | size=$%.0f",
                    market.slug[:40], direction, signal.edge * 100, signal.adjusted_prob * 100, size,
                )
                self.notifier.send(
                    f"⚡ *MOMENTUM*: {market.slug[:40]}\n"
                    f"Entry {direction} @ {price:.0%} | LIVE\n\n"
                    f"📊 Edge: {signal.edge:.1%} | Score: {signal.score_diff}\n"
                    f"💰 Size: ${size:.0f}"
                )
                break  # Only one direction per market
        return entered

    # ── Upset Hunter & Penny scanners ─────────────────────────────────────

    def _check_upset_hunter(self, fresh_markets: list, bankroll: float) -> None:
        """Scan for upset hunting opportunities -- underdog YES tokens $0.05-0.15."""
        if not fresh_markets:
            return
        from src.upset_hunter import pre_filter, size_upset_position

        cfg = self.config.upset_hunter
        if not cfg.enabled:
            return

        # Count current upset positions
        upset_count = sum(1 for p in self.portfolio.positions.values()
                          if getattr(p, "entry_reason", "") == "upset")

        # Enrich markets with Odds API implied probabilities for divergence filter
        for m in fresh_markets:
            if m.odds_api_implied_prob is not None:
                continue  # already enriched
            no_price = m.no_price if m.no_price else (1 - m.yes_price)
            yes_in_zone = cfg.min_price <= m.yes_price <= cfg.max_price
            no_in_zone = cfg.min_price <= no_price <= cfg.max_price
            if not yes_in_zone and not no_in_zone:
                continue  # only enrich candidates in price zone (save API calls)
            try:
                odds = self.odds_api.get_bookmaker_odds(m.question, m.slug, m.tags)
                if odds and odds.get("bookmaker_prob_a"):
                    # Use team A prob as YES implied (market question asks about team A winning)
                    m.odds_api_implied_prob = odds["bookmaker_prob_a"]
            except Exception:
                pass  # Odds API unavailable -- filter will be skipped per spec

        candidates = pre_filter(
            fresh_markets,
            min_price=cfg.min_price,
            max_price=cfg.max_price,
            min_liquidity=cfg.min_liquidity,
            min_odds_divergence=cfg.min_odds_divergence,
            max_hours_before=cfg.max_hours_before_match,
        )

        for c in candidates:
            if upset_count >= cfg.max_concurrent:
                break
            if self.portfolio.active_position_count >= self.config.risk.max_positions:
                break
            if c.condition_id in self.portfolio.positions:
                continue
            if self.blacklist.is_blocked(c.condition_id, self.cycle_count):
                continue
            if c.condition_id in self._exited_markets:
                continue

            size = size_upset_position(
                bankroll, bet_pct=cfg.bet_pct,
                current_upset_count=upset_count,
                max_concurrent=cfg.max_concurrent,
            )
            if size < 5.0:
                continue

            # AI analysis with underdog prompt
            estimate = None
            if self.ai:
                odds_note = ""
                if c.divergence is not None:
                    odds_note = f"Odds API implied: {c.odds_api_implied:.0%}, Polymarket: {c.yes_price:.0%}, divergence: {c.divergence:.0%}"
                else:
                    odds_note = "No bookmaker cross-reference available for this market."

                # Find the original MarketData for AI analysis
                market_data = None
                for m in fresh_markets:
                    if m.condition_id == c.condition_id:
                        market_data = m
                        break
                if not market_data:
                    continue

                estimate = self.ai.analyze_market(
                    market_data,
                    esports_context=odds_note,
                    upset_mode=True,
                )

                # Check AI confidence and edge
                if estimate.confidence in ("C", "D"):
                    continue
                # ai_probability is P(YES). For BUY_NO, edge = P(NO) - no_price
                if c.direction == "BUY_NO":
                    ai_edge = effective_price(estimate.ai_probability, c.direction) - c.no_price
                else:
                    ai_edge = effective_price(estimate.ai_probability, c.direction) - c.yes_price
                if ai_edge < cfg.min_odds_divergence:
                    continue

            # Execute order — use candidate direction (BUY_YES or BUY_NO)
            direction = c.direction
            if direction == "BUY_NO":
                token_id = c.no_token_id
                order_price = c.no_price
            else:
                token_id = c.yes_token_id
                order_price = c.yes_price
            if not token_id:
                for m in fresh_markets:
                    if m.condition_id == c.condition_id:
                        token_id = m.no_token_id if direction == "BUY_NO" else m.yes_token_id
                        break
            if not token_id:
                continue

            if self._check_exposure_limit(size):
                logger.info("SKIP exposure cap: would exceed %.0f%%", self.config.risk.max_exposure_pct * 100)
                continue

            result = self.executor.place_order(token_id, "BUY", order_price, size)
            if not result or result.get("status") == "error":
                continue

            shares = size / order_price if order_price > 0 else 0
            ai_conf = estimate.confidence if estimate else "B-"
            ai_prob = estimate.ai_probability if estimate else (c.no_price if direction == "BUY_NO" else c.yes_price)
            # market_data may already be fetched for AI; fallback lookup if not
            if not market_data:
                for m in fresh_markets:
                    if m.condition_id == c.condition_id:
                        market_data = m
                        break
            self.portfolio.add_position(
                c.condition_id, token_id, direction,
                order_price, size, shares, c.slug,
                "", confidence=ai_conf,
                ai_probability=ai_prob,
                entry_reason="upset",
                end_date_iso=market_data.end_date_iso if market_data else "",
                match_start_iso=market_data.match_start_iso if market_data else "",
                sport_tag=market_data.sport_tag if market_data else "",
                event_id=c.event_id,
            )
            upset_count += 1

            self.trade_log.log({
                "market": c.slug, "action": "UPSET_ENTRY",
                "direction": direction,
                "size": size, "price": order_price,
                "upset_type": c.upset_type,
                "odds_divergence": c.divergence,
                "ai_probability": ai_prob,
                "mode": self.config.mode.value,
            })
            logger.info(
                "UPSET ENTRY: %s | dir=%s | type=%s | price=%.2f | div=%s | size=$%.0f",
                c.slug[:40], direction, c.upset_type, order_price,
                f"{c.divergence:.0%}" if c.divergence else "N/A", size,
            )
            div_str = f" | Div: {c.divergence:.0%}" if c.divergence else ""
            self.notifier.send(
                f"🎯 *UPSET ENTRY*: {c.slug[:40]}\n\n"
                f"🏷 Type: {c.upset_type} | Dir: {direction}\n"
                f"📊 Price: {order_price:.2f}{div_str}\n"
                f"💰 Size: ${size:.0f}"
            )

    def _check_penny_alpha(self, fresh_markets: list, bankroll: float) -> None:
        """Scan for penny alpha -- $0.01-0.02 tokens with 5-10x upside."""
        if not fresh_markets:
            return
        from src.penny_alpha import scan_penny_candidates, size_penny_position

        cfg = self.config.penny_alpha
        if not cfg.enabled:
            return

        penny_count = sum(1 for p in self.portfolio.positions.values()
                          if getattr(p, "entry_reason", "") == "penny")

        candidates = scan_penny_candidates(
            fresh_markets,
            max_candidates=10,
            min_volume=cfg.min_volume,
            max_price=cfg.max_price,
        )

        for c in candidates:
            if self.portfolio.active_position_count >= self.config.risk.max_positions:
                break
            if c.condition_id in self.portfolio.positions:
                continue
            if self.blacklist.is_blocked(c.condition_id, self.cycle_count):
                continue
            if c.condition_id in self._exited_markets:
                continue

            size = size_penny_position(bankroll, cfg.bet_pct, cfg.max_concurrent, penny_count)
            if size < 5.0:
                continue

            # Determine token and direction
            if c.token_side == "YES":
                direction = "BUY_YES"
                token_id = ""
                price = c.yes_price
                for m in fresh_markets:
                    if m.condition_id == c.condition_id:
                        token_id = m.yes_token_id
                        break
            else:
                direction = "BUY_NO"
                token_id = ""
                price = c.no_price
                for m in fresh_markets:
                    if m.condition_id == c.condition_id:
                        token_id = m.no_token_id
                        break

            if not token_id:
                continue

            if self._check_exposure_limit(size):
                logger.info("SKIP exposure cap: would exceed %.0f%%", self.config.risk.max_exposure_pct * 100)
                continue

            # Timing filter: skip penny if match past first half
            market_match = None
            for m in fresh_markets:
                if m.condition_id == c.condition_id:
                    market_match = m
                    break
            if market_match:
                _ms = getattr(market_match, "match_start_iso", "") or ""
                _ed = getattr(market_match, "end_date_iso", "") or ""
                if _ms and _ed:
                    try:
                        _start = datetime.fromisoformat(_ms.replace("Z", "+00:00").replace(" ", "T"))
                        _end = datetime.fromisoformat(_ed.replace("Z", "+00:00").replace(" ", "T"))
                        _now = datetime.now(timezone.utc)
                        _total = (_end - _start).total_seconds()
                        if _total > 0:
                            _elapsed_pct = (_now - _start).total_seconds() / _total
                            if _elapsed_pct > 0.50:
                                logger.info("PENNY skip: match %.0f%% elapsed (>50%%)", _elapsed_pct * 100)
                                continue
                    except (ValueError, TypeError):
                        pass

            result = self.executor.place_order(token_id, "BUY", price, size)
            if not result or result.get("status") == "error":
                continue

            shares = size / price if price > 0 else 0
            self.portfolio.add_position(
                c.condition_id, token_id, direction,
                c.yes_price, size, shares, c.slug,
                "", confidence="B-",
                ai_probability=price,
                entry_reason="penny",
                end_date_iso="",
            )
            penny_count += 1

            self.trade_log.log({
                "market": c.slug, "action": f"PENNY_ENTRY_{direction}",
                "size": size, "price": price,
                "target": c.target_price,
                "multiplier": c.target_multiplier,
                "token_side": c.token_side,
                "mode": self.config.mode.value,
            })
            logger.info(
                "PENNY ENTRY: %s | %s @ $%.2f | target=$%.2f (%dx) | size=$%.0f",
                c.slug[:40], c.token_side, price, c.target_price, int(c.target_multiplier), size,
            )
            self.notifier.send(
                f"🎰 *PENNY ENTRY*: {c.slug[:40]}\n\n"
                f"🏷 {c.token_side} @ ${price:.2f}\n"
                f"🎯 Target: ${c.target_price:.2f} ({c.target_multiplier:.0f}x)\n"
                f"💰 Size: ${size:.0f}"
            )

    # ── Utilities ─────────────────────────────────────────────────────────

    def _handle_hold_revokes(self) -> None:
        """Apply match_exit hold-revoke and hold-restore mutations to positions."""
        for mexr in self.exit_monitor.match_exit_hold_revokes():
            cid = mexr["condition_id"]
            if mexr.get("revoke_hold") and cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                if pos.scouted:
                    pos.hold_was_original = True
                    pos.scouted = False
                    pos.hold_revoked_at = datetime.now(timezone.utc)
                    logger.info("Hold REVOKED: %s -- %s", pos.slug[:40], mexr.get("reason", ""))
            if mexr.get("restore_hold") and cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                pos.scouted = True
                pos.hold_revoked_at = None
                logger.info("Hold RESTORED: %s", pos.slug[:40])

    def _check_stop_file(self) -> None:
        if self.STOP_FILE.exists():
            logger.info("Stop signal received")
            self.STOP_FILE.unlink(missing_ok=True)
            self.running = False

    def _is_paused(self) -> bool:
        return Path("logs/pause_signal").exists()

    def _load_exited_markets(self) -> set:
        try:
            path = Path("logs/exited_markets.json")
            if path.exists():
                return set(json.loads(path.read_text()))
        except Exception:
            pass
        return set()

    def _save_exited_market(self, cid: str) -> None:
        self._exited_markets.add(cid)
        try:
            Path("logs/exited_markets.json").write_text(json.dumps(list(self._exited_markets)), encoding="utf-8")
        except Exception:
            pass

    def _fetch_match_states(self) -> dict[str, dict]:
        """Fetch live match states for all esports positions from PandaScore.

        Returns dict of condition_id -> match_state dict.
        Rate-limited to once per 60 seconds.
        """
        now = time.time()
        if now - self._last_match_state_fetch < 30:
            return self._match_states  # Return cached

        if not self.esports.available:
            return {}

        states: dict[str, dict] = {}
        # Group esports positions by game slug
        esports_positions = [
            (cid, pos) for cid, pos in self.portfolio.positions.items()
            if pos.category == "esports" and pos.live_on_clob
        ]
        if not esports_positions:
            self._match_states = {}
            return {}

        # Also check reentry pool for esports candidates
        esports_games_checked: set[str] = set()

        for cid, pos in esports_positions:
            game_slug = self.esports.detect_game(pos.question, [pos.sport_tag])
            if not game_slug:
                continue

            team_a, team_b = self.esports._extract_team_names(pos.question)
            if not team_a or not team_b:
                continue

            cache_key = f"{game_slug}:{team_a}:{team_b}"
            if cache_key in esports_games_checked:
                continue
            esports_games_checked.add(cache_key)

            try:
                ms = self.esports.get_live_match_state(game_slug, team_a, team_b)
                if ms:
                    states[cid] = ms
                    # Update position fields
                    pos.match_score = ms.get("map_score", "")
                    pos.match_period = f"{ms.get('map_number', '?')}/{ms.get('total_maps', '?')}"
            except Exception as e:
                logger.debug("Match state fetch error for %s: %s", pos.slug[:30], e)

        self._match_states = states
        self._last_match_state_fetch = now
        if states:
            logger.info("Fetched %d live match states from PandaScore", len(states))
        return states

    def _update_position_prices(self) -> bool:
        """Fetch current YES prices for all open positions via slug query.

        Uses slug-based Gamma query which returns correct prices AND event data
        (startTime, live, score, period). conditionId queries return stale/wrong data.
        Returns True if any live positions found.
        """
        if not self.portfolio.positions:
            return False
        stale_cids = []
        reentry_resolve_exits = []
        pending_resolve_exits = []
        has_live_clob = False
        for cid, pos in list(self.portfolio.positions.items()):
            try:
                # Query by slug -- conditionId queries return wrong market data
                if not pos.slug:
                    logger.debug("No slug for position %s, skipping price update", cid[:16])
                    continue
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"slug": pos.slug}, timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    logger.warning("Market not found on Gamma: %s (%s..)", pos.slug, cid[:16])
                    stale_cids.append(cid)
                    continue

                market_data = data[0] if isinstance(data, list) else data
                prices = json.loads(market_data.get("outcomePrices", '["0.5","0.5"]'))
                new_yes_price = float(prices[0])
                no_price = float(prices[1]) if len(prices) > 1 else 1 - new_yes_price
                is_closed = market_data.get("closed", False)

                # Extract event data (startTime, live, score, period)
                events = market_data.get("events", [])
                if events:
                    ev = events[0]
                    ev_start = ev.get("startTime")
                    ev_live = ev.get("live")
                    ev_ended = ev.get("ended")
                    ev_score = ev.get("score") or ""
                    ev_period = ev.get("period") or ""

                    # Populate match_start_iso from event.startTime
                    if ev_start and not pos.match_start_iso:
                        pos.match_start_iso = ev_start
                        logger.info("Match start from Gamma event: %s -> %s",
                                    pos.slug[:35], ev_start)

                    # Update live/ended status directly from Gamma
                    if ev_live is not None:
                        pos.match_live = bool(ev_live)
                        pos.live_on_clob = bool(ev_live)
                        if ev_live:
                            has_live_clob = True
                    if ev_ended is not None:
                        pos.match_ended = bool(ev_ended)
                    if ev_score:
                        pos.match_score = ev_score
                    if ev_period:
                        pos.match_period = ev_period

                if is_closed:
                    # Market resolved -- determine outcome
                    if new_yes_price >= 0.95:
                        yes_won = True
                    elif no_price >= 0.95:
                        yes_won = False
                    elif 0.45 <= new_yes_price <= 0.55 and 0.45 <= no_price <= 0.55:
                        # Void / draw -- both sides refunded at ~50¢
                        logger.info("VOID/DRAW: %s | prices=[%.2f, %.2f] -- exiting as refund",
                                    pos.slug[:40], new_yes_price, no_price)
                        self.portfolio.update_price(cid, new_yes_price)
                        self._exit_position(cid, "resolved_void")
                        continue
                    elif new_yes_price <= 0.05 and no_price <= 0.05:
                        # Ambiguous [0,0] -- check if event says ended
                        if events and events[0].get("ended"):
                            # Event ended but prices ambiguous -- check CLOB as tiebreaker
                            clob_price = self._get_clob_midpoint(pos.token_id)
                            if clob_price is not None and clob_price > 0.01:
                                # CLOB still active despite event "ended"
                                if pos.direction == "BUY_NO":
                                    self.portfolio.update_price(cid, 1.0 - clob_price)
                                else:
                                    self.portfolio.update_price(cid, clob_price)
                                has_live_clob = True
                                continue
                        # Truly ambiguous -- awaiting oracle
                        if not pos.pending_resolution:
                            self.portfolio.mark_pending_resolution(cid)
                        logger.info("Closed and awaiting resolution: %s (prices=[%.2f, %.2f])",
                                    pos.slug, new_yes_price, no_price)
                        continue
                    else:
                        # Prices not at extremes but market closed
                        # Check if match likely ended (start time + estimated duration passed)
                        match_likely_ended = False
                        if pos.match_start_iso:
                            try:
                                start_dt = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
                                elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds() / 60
                                bo = pos.number_of_games or 0
                                est_duration = 180 if bo >= 5 else 120 if bo >= 3 else 90
                                if elapsed > est_duration:
                                    match_likely_ended = True
                            except (ValueError, TypeError):
                                pass

                        if match_likely_ended:
                            # Match likely over -- mark pending, awaiting oracle
                            self.portfolio.update_price(cid, new_yes_price)
                            if not pos.pending_resolution:
                                self.portfolio.mark_pending_resolution(cid)
                                logger.info("Match likely ended (elapsed > est duration): %s -- marking pending",
                                            pos.slug[:40])
                        else:
                            # Match not started or in progress -- treat as active
                            self.portfolio.update_price(cid, new_yes_price)
                        continue

                    won = (pos.direction == "BUY_YES" and yes_won) or \
                          (pos.direction == "BUY_NO" and not yes_won)
                    resolution_price = 1.0 if yes_won else 0.0
                    self.portfolio.update_price(cid, resolution_price)
                    pnl = pos.shares - pos.size_usdc if won else -pos.size_usdc
                    logger.info("RESOLVED: %s | %s | %s | PnL=$%.2f",
                                pos.slug, pos.direction, "WIN" if won else "LOSS", pnl)
                    self._exit_position(cid, f"resolved_{'win' if won else 'loss'}")
                else:
                    # Market still open -- update price
                    self.portfolio.update_price(cid, new_yes_price)
                    # Fallback live detection if event data missing
                    if not events or events[0].get("live") is None:
                        pos.live_on_clob = self._estimate_match_live(
                            pos.slug, pos.question, pos.end_date_iso,
                            match_start_iso=pos.match_start_iso)
                        if pos.live_on_clob:
                            has_live_clob = True
                    # Re-entry resolve guard: exit re-entry positions before they hit resolve
                    # to avoid 1¢/99¢ losses. Exit at 90¢ (winning) or 10¢ (losing side).
                    if getattr(pos, "entry_reason", "").startswith("re_entry"):
                        eff_p = effective_price(new_yes_price, pos.direction)
                        if eff_p >= 0.90:
                            logger.info("RE-ENTRY RESOLVE GUARD (WIN): %s @ %.0f%% -- exiting before resolve",
                                        pos.slug[:35], eff_p * 100)
                            reentry_resolve_exits.append((cid, "re_entry_resolve_win"))
                            continue
                        elif eff_p <= 0.10:
                            logger.info("RE-ENTRY RESOLVE GUARD (LOSS): %s @ %.0f%% -- exiting before resolve",
                                        pos.slug[:35], eff_p * 100)
                            reentry_resolve_exits.append((cid, "re_entry_resolve_loss"))
                            continue

                    # Mark as pending resolution ONLY when match ended + price at extremes
                    # Price extreme alone is NOT enough -- underdog markets sit at 2-5¢ while live
                    if not pos.pending_resolution and (new_yes_price >= 0.95 or new_yes_price <= 0.05):
                        match_ended = getattr(pos, 'match_ended', False)
                        event_ended = False
                        if events:
                            event_ended = bool(events[0].get("ended", False))
                        if match_ended or event_ended:
                            self.portfolio.mark_pending_resolution(cid)
                    # Un-mark false pending: if market is open and event not ended, undo pending
                    if pos.pending_resolution and not is_closed:
                        event_still_live = events and not events[0].get("ended", False)
                        if event_still_live or not events:
                            pos.pending_resolution = False
                            logger.info("Un-pending: %s -- market still open, event not ended", pos.slug[:40])
                    # Pending positions are no longer live
                    if pos.pending_resolution:
                        pos.live_on_clob = False
                        pos.match_live = False
                        # Immediately resolve pending positions with clear outcome
                        if new_yes_price >= 0.97 or new_yes_price <= 0.03:
                            _yes_won = new_yes_price >= 0.97
                            _won = (pos.direction == "BUY_YES" and _yes_won) or \
                                   (pos.direction == "BUY_NO" and not _yes_won)
                            _res_price = 1.0 if _yes_won else 0.0
                            self.portfolio.update_price(cid, _res_price)
                            _pnl = pos.shares - pos.size_usdc if _won else -pos.size_usdc
                            logger.info("RESOLVED (pending): %s | %s | %s | PnL=$%.2f",
                                        pos.slug[:40], pos.direction, "WIN" if _won else "LOSS", _pnl)
                            pending_resolve_exits.append((cid, f"resolved_{'win' if _won else 'loss'}"))
                            continue
            except Exception as e:
                logger.debug("Price update failed for %s: %s", pos.slug[:30], e)

        # Auto-remove positions whose markets no longer exist (stale/test data)
        for cid in stale_cids:
            pos = self.portfolio.remove_position(cid)
            if pos:
                logger.warning("Removed stale position: %s (not on Polymarket)", pos.slug)
                self.trade_log.log({
                    "market": pos.slug, "action": "REMOVED",
                    "reason": "stale: market not found on Gamma API",
                    "mode": self.config.mode.value,
                })
        # Process re-entry resolve guard exits (outside iteration loop)
        for cid, reason in reentry_resolve_exits:
            self._exit_position(cid, reason)
            self.reentry_pool.remove(cid)  # Don't let near-resolved markets re-enter
        # Process pending resolution exits (clear outcome, immediate realize)
        for cid, reason in pending_resolve_exits:
            self._exit_position(cid, reason)

        # Check outcome tracker -- resolve exited markets we're still watching
        if self.outcome_tracker.tracked_count > 0:
            self._check_tracked_outcomes()

        # Persist updated prices + live status to disk
        self.portfolio.save_prices_to_disk()
        return has_live_clob

    def _sync_ws_subscriptions(self) -> None:
        """Sync WebSocket subscriptions with active positions."""
        token_ids = [pos.token_id for pos in self.portfolio.positions.values()]
        self.ws_feed.sync_subscriptions(token_ids)

    def _check_price_drift_reanalysis(self) -> None:
        """Invalidate AI cache for positions whose price drifted significantly from entry."""
        threshold = self.config.risk.price_drift_reanalysis_pct
        for cid, pos in self.portfolio.positions.items():
            if pos.current_price <= 0.001:
                continue
            drift = abs(pos.current_price - pos.entry_price) / max(pos.entry_price, 0.01)
            if drift >= threshold:
                self.entry_gate.invalidate_cache(cid)
                logger.info(
                    "Price drift detected: %s | entry=%.0f¢ now=%.0f¢ drift=%.1f%%",
                    pos.slug, pos.entry_price * 100, pos.current_price * 100, drift * 100,
                )

    def _check_resolved_markets(self) -> None:
        """Check if any past predictions have resolved. Log outcome for calibration."""
        cal_path = Path("logs/calibration.jsonl")
        cal_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing predictions that haven't been resolved yet
        pred_path = Path("logs/predictions.jsonl")
        if not pred_path.exists():
            return

        unresolved = []
        try:
            lines = pred_path.read_text(encoding="utf-8").strip().split("\n")
        except Exception:
            return

        for line in lines:
            if not line.strip():
                continue
            try:
                pred = json.loads(line)
            except json.JSONDecodeError:
                continue

            cid = pred.get("condition_id", "")
            if not cid:
                continue

            # Check if market is resolved
            try:
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"conditionId": cid}, timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    unresolved.append(line)
                    continue

                market = data[0]
                # Must be truly resolved (not just closed for trading)
                # Gamma sets resolved=true only when outcome is final
                if not market.get("resolved", False):
                    unresolved.append(line)
                    continue

                # Market resolved -- log calibration result
                outcome_prices = json.loads(market.get("outcomePrices", '["0.5","0.5"]'))
                yes_price = float(outcome_prices[0])
                # Resolved markets have prices at exactly 1.0 or 0.0 (or very close)
                if 0.02 < yes_price < 0.98:
                    # Not truly resolved -- prices still mid-range
                    unresolved.append(line)
                    continue
                resolved_yes = yes_price > 0.50  # YES won
                ai_prob = pred.get("ai_probability", 0.5)
                ai_was_right = (ai_prob > 0.5 and resolved_yes) or (ai_prob <= 0.5 and not resolved_yes)
                error = abs(ai_prob - (1.0 if resolved_yes else 0.0))

                result = {
                    "condition_id": cid,
                    "question": pred.get("question", ""),
                    "ai_probability": ai_prob,
                    "market_price_at_trade": pred.get("market_price", 0),
                    "direction": pred.get("direction", ""),
                    "resolved_yes": resolved_yes,
                    "ai_correct": ai_was_right,
                    "prediction_error": round(error, 3),
                    "category": pred.get("category", ""),
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                }
                with open(cal_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result) + "\n")
                logger.info(
                    "Calibration: %s | AI=%.0f%% | Result=%s | %s",
                    pred.get("question", "")[:40],
                    ai_prob * 100,
                    "YES" if resolved_yes else "NO",
                    "CORRECT" if ai_was_right else "WRONG",
                )
            except Exception as e:
                logger.debug("Calibration check failed for %s: %s", cid[:20], e)
                unresolved.append(line)

        # Rewrite predictions file atomically (write to temp, then rename)
        if len(unresolved) < len(lines):
            tmp_path = pred_path.with_suffix(".tmp")
            tmp_path.write_text(
                "\n".join(unresolved) + "\n" if unresolved else "",
                encoding="utf-8",
            )
            tmp_path.replace(pred_path)

    def _check_tracked_outcomes(self) -> None:
        """Check exited markets for resolution -- no AI cost, just Gamma API."""
        from src.match_outcomes import log_outcome as _log_resolved
        tracked_cids = self.outcome_tracker.tracked_condition_ids
        if not tracked_cids:
            return

        gamma_events: dict[str, dict] = {}
        for cid in list(tracked_cids):
            tm = self.outcome_tracker._tracked.get(cid)
            if not tm:
                continue
            try:
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"slug": tm.slug}, timeout=10,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if not data:
                    continue
                md = data[0] if isinstance(data, list) else data
                prices = json.loads(md.get("outcomePrices", '["0.5","0.5"]'))
                gamma_events[cid] = {
                    "yes_price": float(prices[0]),
                    "closed": md.get("closed", False),
                    "ended": (md.get("events") or [{}])[0].get("ended", False),
                }
            except Exception:
                continue

        resolved = self.outcome_tracker.check_resolutions(gamma_events)
        for outcome in resolved:
            # Log resolved outcome to match_outcomes.jsonl
            try:
                _log_resolved(
                    slug=outcome["slug"],
                    question=outcome.get("question", ""),
                    direction=outcome["direction"],
                    ai_probability=outcome["ai_probability"],
                    confidence=outcome["confidence"],
                    entry_price=outcome["entry_price"],
                    exit_price=outcome["exit_price"],
                    exit_reason=f"post_exit_{outcome['exit_reason']}",
                    pnl=outcome["hypothetical_pnl"],
                    size=outcome["size"],
                    sport_tag=outcome.get("sport_tag", ""),
                    entry_reason=outcome.get("entry_reason", ""),
                    scouted=outcome.get("scouted", False),
                    peak_pnl_pct=outcome.get("peak_pnl_pct", 0.0),
                    match_score=outcome.get("match_score", ""),
                    cycles_held=outcome.get("cycles_held", 0),
                    bookmaker_prob=outcome.get("bookmaker_prob", 0.0),
                )
            except Exception:
                pass

            # Auto-calibration check (every 50 resolved outcomes)
            try:
                from src.self_improve import auto_calibrate
                cal_result = auto_calibrate(logger=logger)
                if cal_result:
                    weaknesses = cal_result.get("weaknesses", [])
                    self.notifier.send(
                        f"\U0001f4ca *AUTO-CALIBRATION* -- {cal_result['resolved_count']} resolved\n\n"
                        f"Win rate: `{cal_result['overall_win_rate']:.0%}`\n"
                        f"Brier: `{cal_result['overall_brier']:.3f}`\n"
                        + (f"Weaknesses: {len(weaknesses)}\n" if weaknesses else "No weaknesses found\n")
                        + (f"Top: {weaknesses[0]}" if weaknesses else "")
                    )
            except Exception as e:
                logger.debug("Auto-calibration skipped: %s", e)

            # Notify
            side = "WIN" if outcome["our_side_won"] else "LOSS"
            left = outcome.get("pnl_left_on_table", 0)
            self.notifier.send(
                f"\U0001f50d *POST-EXIT* -- {outcome['slug'][:40]}\n\n"
                f"Exited: `{outcome['exit_reason']}` PnL=`${outcome['actual_pnl']:.2f}`\n"
                f"Match result: `{side}`\n"
                f"If held: `${outcome['hypothetical_pnl']:.2f}`"
                + (f" (left `${left:.2f}` on table)" if left > 0.5 else "")
            )

    def _log_cycle_summary(self, bankroll: float, status: str) -> None:
        invested = sum(p.size_usdc for p in self.portfolio.positions.values())
        unrealized = self.portfolio.total_unrealized_pnl()
        # Equity = initial + realized + unrealized (always correct, no tracking drift)
        equity = self.portfolio._initial_bankroll + self.portfolio.realized_pnl + unrealized
        self.portfolio_log.log({
            "bankroll": self.portfolio.bankroll,
            "positions": len(self.portfolio.positions),
            "invested": round(invested, 2),
            "unrealized_pnl": unrealized,
            "realized_pnl": self.portfolio.realized_pnl,
            "realized_wins": self.portfolio.realized_wins,
            "realized_losses": self.portfolio.realized_losses,
            "hwm": self.portfolio.high_water_mark,
            "initial_bankroll": self.portfolio._initial_bankroll,
            "equity": round(equity, 2),
            "status": status,
        })
        self._log_performance()

    def _write_status(self, state: str, step: str, **kwargs) -> None:
        """Write bot status to logs/bot_status.json for dashboard consumption."""
        from datetime import datetime, timezone
        status = {
            "state": state,
            "step": step,
            "ts": datetime.now(timezone.utc).isoformat(),
            "has_positions": self.portfolio.active_position_count > 0,
            **kwargs,
        }
        try:
            status_path = Path("logs/bot_status.json")
            status_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = status_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(status), encoding="utf-8")
            tmp.replace(status_path)
        except Exception as e:
            logger.debug("Status file write error: %s", e)

    def _log_performance(self) -> None:
        """Write performance stats to performance.jsonl for the dashboard."""
        cal = Path("logs/calibration.jsonl")
        if not cal.exists():
            return
        try:
            lines = [json.loads(l) for l in cal.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
        except Exception:
            return
        if not lines:
            return
        # Calibration uses ai_correct (bool) and ai_probability fields
        wins = sum(1 for l in lines if l.get("ai_correct", False))
        losses = sum(1 for l in lines if not l.get("ai_correct", False))
        total = wins + losses
        if total == 0:
            return
        # Brier score: (predicted_prob - actual_outcome)^2
        brier_pairs = []
        for l in lines:
            prob = l.get("ai_probability", 0.5)
            outcome = 1 if l.get("resolved_yes", False) else 0
            brier_pairs.append((prob - outcome) ** 2)
        brier = sum(brier_pairs) / len(brier_pairs) if brier_pairs else 0.5
        # Best category by win rate
        cat_wins: dict[str, int] = {}
        cat_total: dict[str, int] = {}
        for l in lines:
            q = l.get("question", "")
            slug = l.get("condition_id", "")
            # Try category field first, then detect from question text
            cat = l.get("category", "")
            if not cat:
                cat_match = re.search(r"\b(NBA|NHL|CBB|NFL|MLB|CS2|CS:GO|LoL|EPL|UCL|UEL|Dota|Valorant)\b", q, re.IGNORECASE)
                cat = cat_match.group(1).upper() if cat_match else "Other"
            cat_total[cat] = cat_total.get(cat, 0) + 1
            if l.get("ai_correct", False):
                cat_wins[cat] = cat_wins.get(cat, 0) + 1
        best_cat = max(cat_total, key=lambda c: (cat_wins.get(c, 0) / cat_total[c], cat_total[c])) if cat_total else None
        self.perf_log.log({
            "win_rate": round(wins / total, 4),
            "wins": wins,
            "losses": losses,
            "resolved": total,
            "brier_score": round(brier, 4),
            "best_category": best_cat,
            "best_category_rate": round(cat_wins.get(best_cat, 0) / cat_total.get(best_cat, 1), 4) if best_cat else None,
        })

    def _maybe_run_reflection(self) -> None:
        """Every 3 days, analyze calibration results and generate lessons."""
        lessons_path = Path("logs/ai_lessons.md")
        cal_path = Path("logs/calibration.jsonl")

        # Check if it's time (every 3 days)
        marker_path = Path("logs/.last_reflection")
        if marker_path.exists():
            try:
                last = datetime.fromisoformat(marker_path.read_text().strip())
                if (datetime.now(timezone.utc) - last).days < 3:
                    return
            except (ValueError, OSError):
                pass

        if not cal_path.exists():
            return

        # Need at least 5 resolved predictions
        try:
            lines = [l for l in cal_path.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
        except Exception:
            return
        if len(lines) < 5:
            return

        # Build reflection prompt from calibration data
        results = []
        for line in lines[-20:]:  # Last 20 results max
            try:
                r = json.loads(line)
                results.append(
                    f"- Q: {r.get('question', '')[:80]} | "
                    f"AI: {r.get('ai_probability', 0):.0%} | "
                    f"Result: {'YES' if r.get('resolved_yes') else 'NO'} | "
                    f"{'CORRECT' if r.get('ai_correct') else 'WRONG'} | "
                    f"Error: {r.get('prediction_error', 0):.0%} | "
                    f"Category: {r.get('category', 'unknown')}"
                )
            except (json.JSONDecodeError, KeyError):
                continue

        if not results:
            return

        correct = 0
        for l in lines:
            try:
                correct += 1 if json.loads(l).get("ai_correct") else 0
            except (json.JSONDecodeError, AttributeError):
                pass
        total = len(lines)
        accuracy = correct / total if total > 0 else 0

        reflection_prompt = (
            f"You are reviewing your past prediction performance.\n"
            f"Overall accuracy: {correct}/{total} ({accuracy:.0%})\n\n"
            f"Recent results:\n" + "\n".join(results) + "\n\n"
            f"Analyze your mistakes. Write 3-5 SHORT, SPECIFIC rules for yourself. "
            f"Focus on: What reasoning patterns led to wrong predictions? "
            f"What should you do differently? Which categories are you weak in?\n"
            f"Keep it under 400 characters total. Be brutally honest."
        )

        try:
            # Estimate cost (~$0.01)
            if self.ai.budget_remaining_usd < 0.05:
                return

            result = self.ai._call_claude(
                "You are a prediction analyst reviewing your own performance. "
                "Output ONLY plain text rules, no JSON.",
                reflection_prompt,
                parse_json=False,
            )
            if not result or not isinstance(result, str):
                return
            lessons_text = result

            # Save lessons
            lessons_path.write_text(
                f"# AI Self-Reflection (updated {datetime.now(timezone.utc).strftime('%Y-%m-%d')})\n"
                f"Accuracy: {correct}/{total} ({accuracy:.0%})\n\n"
                f"{lessons_text}\n",
                encoding="utf-8",
            )
            marker_path.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
            logger.info("Self-reflection complete: %d/%d correct (%.0f%%)", correct, total, accuracy * 100)
        except Exception as e:
            logger.debug("Reflection failed: %s", e)

    # ── Internal helpers ───────────────────────────────────────────────────

    def _get_clob_midpoint(self, token_id: str) -> float | None:
        """Fetch midpoint price from CLOB API for a token. Returns None on failure."""
        try:
            resp = requests.get(
                "https://clob.polymarket.com/midpoint",
                params={"token_id": token_id}, timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            mid = float(data.get("mid", 0))
            return mid if mid > 0 else None
        except Exception as e:
            logger.debug("CLOB midpoint failed for %s: %s", token_id[:16], e)
            return None

    @staticmethod
    def _match_duration(slug: str, question: str) -> float:
        """Estimated match duration in hours based on sport/format."""
        text = (slug + " " + question).lower()
        if "bo5" in text or "best of 5" in text:
            if "dota" in text:
                return 3.25
            return 2.75
        if "bo1" in text:
            return 0.75
        if "bo3" in text or "best of 3" in text:
            if "dota" in text:
                return 2.0
            if any(k in text for k in ("lol:", "league")):
                return 1.5
            return 1.75
        if any(k in text for k in ("cs2", "cs:", "csgo", "counter-strike", "valorant")):
            return 1.75
        if any(k in text for k in ("lol:", "league")):
            return 1.5
        if "dota" in text:
            return 2.0
        if any(k in text for k in ("nba", "cbb", "ncaa basket")):
            return 2.25
        if any(k in text for k in ("nfl", "football")):
            return 3.25
        if any(k in text for k in ("nhl", "hockey")):
            return 2.33
        if any(k in text for k in ("epl", "ucl", "uel", "soccer", "fc ", "united")):
            return 2.0
        if any(k in text for k in ("mlb", "baseball")):
            return 2.75
        return 2.0

    @staticmethod
    def _estimate_match_live(slug: str, question: str, end_date_iso: str,
                             match_start_iso: str = "") -> bool:
        """Estimate if a match is currently in progress."""
        now = datetime.now(timezone.utc)

        # Best source: actual match start time
        if match_start_iso:
            try:
                start_dt = datetime.fromisoformat(
                    match_start_iso.replace("Z", "+00:00")
                    .replace(" ", "T")
                )
                if now < start_dt:
                    return False
                minutes_since_start = (now - start_dt).total_seconds() / 60
                if minutes_since_start <= 5:
                    return False
                return True
            except (ValueError, TypeError):
                pass

        # Fallback: estimate from endDate
        if not end_date_iso:
            return False
        try:
            end_dt = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
            hours_to_end = (end_dt - now).total_seconds() / 3600
        except (ValueError, TypeError):
            return False
        if hours_to_end <= 0:
            return True
        duration_h = Agent._match_duration(slug, question)
        return hours_to_end <= duration_h
