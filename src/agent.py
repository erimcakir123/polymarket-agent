"""agent.py -- Thin agent loop. Coordinates EntryGate and ExitMonitor.

Responsibilities:
  - Initialize all modules (entry_gate, exit_monitor, portfolio, executor, etc.)
  - run_cycle(): heavy cycle -- scanning, AI analysis, upset/early/penny entries
  - run_light_cycle(): fast cycle (5s) -- exits, live_dip, momentum, farming re-entry,
    scale-outs (with per-strategy cooldowns to avoid spamming)
  - run(): main loop
  Delegates to: ExitExecutor, LiveStrategies, PriceUpdater, CycleHelpers
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone, date
from pathlib import Path

from src.config import AppConfig, Mode
from src.portfolio import Portfolio
from src.executor import Executor
from src.ai_analyst import AIAnalyst
from src.market_scanner import MarketScanner
from src.risk_manager import RiskManager
from src.odds_api import OddsAPIClient
from src.esports_data import EsportsDataClient
from src.sports_data import SportsDataClient
from src.sports_discovery import SportsDiscovery
from src.news_scanner import NewsScanner
from src.manipulation_guard import ManipulationGuard
from src.trade_logger import TradeLogger
from src.notifier import TelegramNotifier
from src.websocket_feed import WebSocketFeed
from src.circuit_breaker import CircuitBreaker
from src.reentry_farming import ReentryPool
from src.reentry import Blacklist
from src.outcome_tracker import OutcomeTracker
from src.cycle_timer import CycleTimer
from src.scout_scheduler import ScoutScheduler
from src.entry_gate import EntryGate
from src.exit_monitor import ExitMonitor
from src.exit_executor import ExitExecutor
from src.live_strategies import LiveStrategies
from src.price_updater import PriceUpdater
from src.cycle_logic import CycleHelpers

logger = logging.getLogger(__name__)


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

        # Extracted modules
        self.exit_executor = ExitExecutor(self)
        self.live_strategies = LiveStrategies(self)
        self.price_updater = PriceUpdater(self)
        self.cycle_helpers = CycleHelpers(self)

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
                        _consecutive_dry = 0  # Track consecutive refills with no new entries
                        while True:
                            current_vs = sum(1 for p in self.portfolio.positions.values() if p.volatility_swing)
                            current_normal = self.portfolio.active_position_count - current_vs
                            open_slots = self.config.risk.max_positions - vs_reserved - current_normal
                            if open_slots <= 0:
                                logger.info("All slots filled -- refill complete")
                                break
                            # Also stop refilling if exposure cap reached
                            from src.risk_manager import exceeds_exposure_limit
                            if exceeds_exposure_limit(
                                self.portfolio.positions, 0.0,
                                self.portfolio.bankroll, self.config.risk.max_exposure_pct,
                            ):
                                logger.info("Exposure cap reached -- refill complete")
                                break
                            _refill_round += 1
                            positions_before = len(self.portfolio.positions)
                            logger.info("Pool not full (%d open slots) -- refill cycle %d",
                                        open_slots, _refill_round)
                            self.entry_gate.reset_seen_markets()  # R3: fresh scan each refill
                            self.run_cycle()
                            last_full_cycle_time = time.time()
                            positions_after = len(self.portfolio.positions)
                            new_entries = positions_after - positions_before
                            if new_entries > 0:
                                logger.info("Refill cycle %d added %d positions", _refill_round, new_entries)
                                _consecutive_dry = 0
                            else:
                                _consecutive_dry += 1
                                logger.info("Refill cycle %d -- no new entries (dry streak: %d)",
                                            _refill_round, _consecutive_dry)
                            # Two consecutive dry refills = pool exhausted
                            if _consecutive_dry >= 2:
                                logger.info("Eligible pool exhausted -- 2 dry refills. Done.")
                                break
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
                    if pos.unrealized_pnl_pct < -(self.config.risk.stop_loss_pct * self.config.risk.near_stop_loss_multiplier):
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

                self.cycle_helpers.write_status("waiting", "Waiting")

                # Sleep between iterations
                # Light cycles: 5s (fast exit detection via WS prices)
                # After full cycle: 60s (next full gated by cycle_timer anyway)
                time.sleep(5 if has_positions and not run_full else 60)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.cycle_helpers.write_status("offline", "Stopped")
            self.ws_feed.stop()
            logger.info("Agent stopped")

    def run_light_cycle(self) -> None:
        """Price-only cycle: update prices + check exits. No scan, no AI."""
        cycle_start = time.monotonic()
        self.cycle_helpers.write_status("running", "Light cycle")
        if self._is_paused():
            return
        logger.info("=== Light cycle ===")

        # Process WS ticks first (main thread)
        t0 = time.monotonic()
        self.exit_monitor.process_ws_ticks()

        # Drain WS exits
        for cid, reason in self.exit_monitor.drain():
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self.exit_executor.exit_position(cid, reason)
        logger.info("Phase [ws_ticks+drain] took %.1fs", time.monotonic() - t0)

        # Update prices
        t0 = time.monotonic()
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.portfolio.update_bankroll(bankroll)
        if not self.ws_feed.connected:
            self.last_cycle_has_live_clob = self.price_updater.update_position_prices()
        self.price_updater.sync_ws_subscriptions()
        logger.info("Phase [price_update] took %.1fs", time.monotonic() - t0)

        # Fetch live match states
        t0 = time.monotonic()
        match_states = self.price_updater.fetch_match_states()
        logger.info("Phase [match_states] took %.1fs", time.monotonic() - t0)

        # Light exit checks
        t0 = time.monotonic()
        for cid, reason in self.exit_monitor.check_exits_light():
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self.exit_executor.exit_position(cid, reason)

        # Handle hold-revoke/restore (match_exit meta -- mutates pos directly)
        self.exit_executor.handle_hold_revokes()
        logger.info("Phase [exit_checks] took %.1fs", time.monotonic() - t0)

        self.light_cycle_count += 1

        # --- Light cycle action strategies (with per-strategy cooldowns) ---
        t0 = time.monotonic()
        held_events = self.live_strategies.get_held_event_ids()

        # Fetch fresh market data once for all strategies that need it
        _need_markets = (
            self.live_strategies.light_cooldown_ready("live_dip")
            or self.live_strategies.light_cooldown_ready("momentum")
        )
        light_fresh_markets = self.scanner.fetch() if _need_markets else []

        # Cache pre-match prices from fresh scan (first-seen only).
        # NOTE: _pre_match_prices is populated by both heavy and light cycles.
        # All writes are first-seen-only (idempotent). Light cycle strategies
        # only READ existing entries for dip/momentum detection.
        for m in light_fresh_markets:
            if m.condition_id not in self._pre_match_prices and m.yes_price > 0:
                self._pre_match_prices[m.condition_id] = m.yes_price

        if self.live_strategies.light_cooldown_ready("scale_out"):
            self.exit_executor.process_scale_outs()
            self.live_strategies.set_light_cooldown("scale_out")

        if self.live_strategies.light_cooldown_ready("farming_reentry"):
            entered = self.live_strategies.check_farming_reentry()
            if entered:
                self.live_strategies.set_light_cooldown("farming_reentry")

        if self.live_strategies.light_cooldown_ready("live_dip"):
            entered = self.live_strategies.check_live_dip(held_events, light_fresh_markets)
            if entered:
                self.live_strategies.set_light_cooldown("live_dip")

        if self.live_strategies.light_cooldown_ready("momentum"):
            entered = self.live_strategies.check_live_momentum(held_events, light_fresh_markets, match_states)
            if entered:
                self.live_strategies.set_light_cooldown("momentum")
        logger.info("Phase [strategies] took %.1fs", time.monotonic() - t0)

        # Persist portfolio snapshot so dashboard sees real-time PnL
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.cycle_helpers.log_cycle_summary(bankroll, "light")
        logger.info("Full light cycle took %.1fs", time.monotonic() - cycle_start)

    def run_cycle(self) -> None:
        """Heavy cycle: exit checks + market scan + AI + entry decisions."""
        cycle_start = time.monotonic()
        self.cycle_helpers.write_status("running", "Hard cycle")
        if self._is_paused():
            return
        self.cycle_count += 1
        self.risk.new_cycle()
        logger.info("=== Cycle #%d start ===", self.cycle_count)

        # Self-reflection
        t0 = time.monotonic()
        self.cycle_helpers.maybe_run_reflection()
        logger.info("Phase [reflection] took %.1fs", time.monotonic() - t0)

        # Bankroll + drawdown
        t0 = time.monotonic()
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.portfolio.update_bankroll(bankroll)
        dd_level = self.portfolio.get_drawdown_level()
        if dd_level == "hard":
            self.notifier.send("🚨 HARD HALT: equity < 35% HWM -- closing all positions")
            for cid in list(self.portfolio.positions.keys()):
                if not self.exit_monitor.is_exiting(cid):
                    self.exit_executor.exit_position(cid, "hard_halt_drawdown")
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
        logger.info("Phase [bankroll+drawdown+cb] took %.1fs", time.monotonic() - t0)

        # Check resolved markets
        t0 = time.monotonic()
        self.cycle_helpers.write_status("running", "Checking exits")
        self.price_updater.check_resolved_markets()

        # Update prices
        self.last_cycle_has_live_clob = self.price_updater.update_position_prices()
        self.price_updater.check_price_drift_reanalysis()
        logger.info("Phase [price_update+resolved] took %.1fs", time.monotonic() - t0)

        # Process WS ticks first (main thread)
        t0 = time.monotonic()
        self.exit_monitor.process_ws_ticks()

        # Exit detection + execution
        for cid, reason in self.exit_monitor.drain():
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self.exit_executor.exit_position(cid, reason)

        match_states = self.price_updater.fetch_match_states()
        for cid, reason in self.exit_monitor.check_exits(self.cycle_count):
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self.exit_executor.exit_position(cid, reason)
        self.exit_executor.handle_hold_revokes()
        # NOTE: _process_scale_outs() moved to light cycle with cooldown
        self.price_updater.sync_ws_subscriptions()
        logger.info("Phase [exit_detection] took %.1fs", time.monotonic() - t0)

        self._quick_exit_check(bankroll)  # between exits and scan

        # Scout + Entry: fresh scan (analyze=True)
        t0 = time.monotonic()
        # Daily listing runs UNCONDITIONALLY (R4) — it's just data gathering, no entries
        if self.scout.is_daily_listing_time() and self.scout.should_run_scout():
            self.cycle_helpers.write_status("running", "Daily match listing")
            new_listed = self.scout.run_daily_listing()
            if new_listed:
                self.notifier.send(f"📋 DAILY LISTING: {new_listed} matches catalogued")
        elif self.scout.should_run_scout():
            # 06/12/18 UTC refresh — catches late additions
            self.cycle_helpers.write_status("running", "Refreshing match list")
            new_scouted = self.scout.run_scout()
            if new_scouted:
                self.notifier.send(f"🔍 SCOUT REFRESH: {new_scouted} new matches")

        self.cycle_helpers.write_status("running", "Scanning markets")
        fresh_markets = self.scanner.fetch()
        self._last_candidate_count = len(fresh_markets)

        # Cache pre-match prices (first-seen only) for live_dip/momentum in light cycle
        for m in fresh_markets:
            if m.condition_id not in self._pre_match_prices and m.yes_price > 0:
                self._pre_match_prices[m.condition_id] = m.yes_price
        logger.info("Phase [scout+scan] took %.1fs", time.monotonic() - t0)

        # Skip expensive AI analysis if exposure cap already reached
        from src.risk_manager import exceeds_exposure_limit
        _exposure_full = exceeds_exposure_limit(
            self.portfolio.positions, 0.0,
            self.portfolio.bankroll, self.config.risk.max_exposure_pct,
        )
        if _exposure_full and entries_allowed:
            logger.info("Exposure cap reached (%.0f%%) -- skipping AI analysis, drain stock only",
                        self.config.risk.max_exposure_pct * 100)
            entries_allowed = False

        t0 = time.monotonic()
        self.entry_gate.run(
            fresh_markets, entries_allowed=entries_allowed, analyze=True,
            bankroll=bankroll, cycle_count=self.cycle_count,
            blacklist=self.blacklist, exited_markets=self._exited_markets,
        )
        logger.info("Phase [entry_gate_ai] took %.1fs", time.monotonic() - t0)

        self._quick_exit_check(bankroll)  # between AI entries and stock drain

        # Breaking news detected -> shorten cycle interval
        if self.entry_gate._breaking_news_detected:
            self.entry_gate._breaking_news_detected = False
            self.cycle_timer.signal_breaking_news()
            logger.info("Breaking news detected -- cycle shortened to %d min", self.config.cycle.breaking_news_interval_min)

        t0 = time.monotonic()
        self.cycle_helpers.write_status("running", "Evaluating entries")
        # Entry: stock queue drain (analyze=False -- no AI cost)
        self.entry_gate.drain_stock(
            entries_allowed=entries_allowed, bankroll=bankroll,
            cycle_count=self.cycle_count, blacklist=self.blacklist,
            exited_markets=self._exited_markets,
        )
        logger.info("Phase [stock_drain] took %.1fs", time.monotonic() - t0)

        self._quick_exit_check(bankroll)  # between stock drain and upset hunter

        # NOTE: farming_reentry, live_dip, live_momentum, scale_outs moved to light cycle
        # Upset hunter stays in heavy cycle (needs fresh scan data + AI analysis)
        t0 = time.monotonic()
        if entries_allowed:
            self.live_strategies.check_upset_hunter(fresh_markets, bankroll)
        logger.info("Phase [upset_hunter] took %.1fs", time.monotonic() - t0)

        self._quick_exit_check(bankroll)  # after upset, before summary

        # Check outcomes + log
        self.price_updater.check_tracked_outcomes()
        self.cycle_helpers.log_cycle_summary(bankroll, "ok")
        logger.info("Full heavy cycle #%d took %.1fs", self.cycle_count, time.monotonic() - cycle_start)

    # (Light-cycle strategies moved to src/live_strategies.py)

    # ── Interleaved exit check (runs between heavy cycle phases) ────────

    def _quick_exit_check(self, bankroll: float) -> None:
        """Lightweight exit sweep inserted between heavy cycle phases.

        Drains WS ticks, runs light exit checks, processes scale-outs,
        and writes a portfolio snapshot so the dashboard stays fresh.
        """
        self.exit_monitor.process_ws_ticks()
        for cid, reason in self.exit_monitor.drain():
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self.exit_executor.exit_position(cid, reason)
        for cid, reason in self.exit_monitor.check_exits_light():
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self.exit_executor.exit_position(cid, reason)
        self.exit_executor.process_scale_outs()
        self.cycle_helpers.log_cycle_summary(bankroll, "interleaved")

    # ── Utilities ─────────────────────────────────────────────────────────

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

    # (Price/market methods moved to src/price_updater.py)

