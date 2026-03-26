"""Entry point and main agent loop."""
from __future__ import annotations
import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path

import re
import requests

from dotenv import load_dotenv

from src.config import AppConfig, Mode, load_config
from src.market_scanner import MarketScanner
from src.ai_analyst import AIAnalyst, AIEstimate
from src.edge_calculator import calculate_edge, scale_min_edge, boost_confidence
from src.risk_manager import RiskManager, kelly_position_size
from src.portfolio import Portfolio
from src.executor import Executor
from src.news_scanner import NewsScanner
from src.manipulation_guard import ManipulationGuard
from src.cycle_timer import CycleTimer
from src.trade_logger import TradeLogger
from src.notifier import TelegramNotifier
from src.models import MarketData, Signal, Direction
from src.pre_filter import filter_impossible_markets
from src.sanity_check import check_bet_sanity
from src.esports_data import EsportsDataClient
from src.sports_data import SportsDataClient
from src.odds_api import OddsAPIClient
from src.vlr_data import VLRDataClient
from src.hltv_data import HLTVDataClient
from src.scout_scheduler import ScoutScheduler
from src.process_lock import acquire_lock
from src.dashboard import create_app as create_dashboard
from src.live_dip_entry import find_live_dip_candidates
from src.circuit_breaker import CircuitBreaker
from src.reentry_farming import ReentryPool, check_reentry
from src.websocket_feed import WebSocketFeed
from src.reentry import Blacklist, can_reenter, get_blacklist_rule, is_snowball_banned, qualifies_for_score_reversal_reentry, passes_confidence_momentum, get_reentry_size_multiplier
from src.edge_decay import get_decayed_ai_target
from src.correlation import apply_correlation_cap, extract_match_key
from src.liquidity_check import check_exit_liquidity, check_entry_liquidity
from src.adaptive_kelly import get_adaptive_kelly_fraction
from src.outcome_tracker import OutcomeTracker
from src.probability_engine import calculate_anchored_probability, get_edge_threshold_adjustment
from src.trailing_tp import calculate_trailing_tp
from src.trade_logger import EdgeSourceTracker
from src.bond_scanner import scan_bond_candidates, size_bond_position
from src.live_momentum import detect_momentum_opportunity
from src.penny_alpha import scan_penny_candidates, size_penny_position, check_penny_exit

logger = logging.getLogger(__name__)


PAUSE_FILE = Path("logs/AWAITING_APPROVAL")
STATUS_FILE = Path("logs/bot_status.json")
BETS_PER_APPROVAL = 10

# Exit reasons that can NEVER go back to stock (market closed or no spread)
_NEVER_STOCK_EXITS = frozenset({"far_penny", "stop_loss", "esports_halftime"})
_NEVER_STOCK_PREFIXES = ("resolved_", "far_penny_", "match_exit_")
def _load_test_start_date() -> date:
    """Load test start date from file, or default to today."""
    p = Path("logs/test_start_date.txt")
    if p.exists():
        try:
            return datetime.strptime(p.read_text().strip(), "%Y-%m-%d").date()
        except Exception:
            pass
    today = datetime.now(timezone.utc).date()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(today.isoformat())
    return today

TEST_START_DATE = _load_test_start_date()

# Testing plan milestones — (day, message)
_MILESTONES = [
    (1, "Day 1 — Bot started (dry_run). Collecting data."),
    (3, "Day 3 — CHECKPOINT 1: First data. ~350 predictions expected.\n"
        "Run self-improve: win rate, Brier score, worst 5 errors, category analysis."),
    (5, "Day 5 — CHECKPOINT 2: Baseline complete. ~700 predictions.\n"
        "BOT WILL PAUSE. Run /self-improve for first optimization."),
    (8, "Day 8 — CHECKPOINT 3: Post-optimization check.\n"
        "Did win rate improve? Were filtered categories correct?"),
    (11, "Day 11 — CHECKPOINT 4: Second comparison.\n"
         "Phase 1 vs Phase 2. Run PnL simulation.\n"
         "BOT WILL PAUSE. Run /self-improve for second optimization."),
    (15, "Day 15 — CHECKPOINT 5: Validation.\n"
         "Last 3 checkpoint trends, overfitting check, simulated PnL."),
    (19, "Day 19 — CHECKPOINT 6: DECISION POINT.\n"
         "Win rate >57% → go live ($100-200)\n"
         "Win rate 53-57% → one more iteration\n"
         "Win rate <53% → fundamental changes needed"),
    (21, "Day 21 — Live transition (if approved)."),
    (28, "Day 28 — CHECKPOINT 8: First week live results.\n"
         "Live PnL vs dry_run comparison."),
]


class Agent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.running = True
        self.consecutive_api_failures = 0
        self.last_cycle_has_live_clob = False
        self.bets_since_approval = 0
        self.cycle_count = 0
        self._exit_cooldowns: dict[str, int] = {}  # condition_id -> cycle when cooldown expires
        self._exited_markets: set[str] = self._load_exited_markets()  # Never re-enter these
        self._seen_market_ids: set[str] = set()  # Track markets across cycles for new-market detection
        self._analyzed_market_ids: dict[str, float] = self._load_recent_analyses()  # condition_id -> timestamp of last AI analysis
        self._far_market_ids: set[str] = set()  # Far markets in current batch (need higher edge)
        self._candidate_stock: list[dict] = []  # AI-analyzed candidates waiting for slots
        self._stock_stats = {"used": 0, "stale": 0, "expired": 0}  # Pipeline metrics
        self._fav_stock: list[dict] = []  # FAV_TIME_GATE candidates with own slots (max 3)
        self._FAV_MAX_SLOTS = 5  # Dedicated FAV slots (separate from normal 15)
        self._FAV_MIN_EDGE = 0.15  # Only stok favorites with ≥15% edge
        self._far_stock: list[dict] = []  # FAR candidates (swing trade + penny alpha)
        self._last_live_dip_check: float = 0  # Timestamp of last live-dip scan
        self._last_bond_scan: float = 0  # Timestamp of last bond scan
        self._last_penny_scan: float = 0  # Timestamp of last penny alpha scan
        self._spike_reentry: dict[str, dict] = {}  # LEGACY — kept for backward compat, drained to farming pool
        self._scouted_reentry: dict[str, dict] = {}  # LEGACY — kept for backward compat, drained to farming pool
        self.reentry_pool = ReentryPool()  # Unified farming re-entry pool
        self.outcome_tracker = OutcomeTracker()  # Track match results after exit
        self.ws_feed = WebSocketFeed(on_price_update=self._on_ws_price_update)
        self._ws_exit_queue: list[tuple[str, str]] = []  # (condition_id, reason) — filled by WS, drained by main
        self._exiting_set: set[str] = set()  # condition_ids currently being exited — prevents double-exit (#1a, #2a)
        self._toxic_markets: set = set()  # Markets where favorite is losing badly — block all entries
        self._match_states: dict[str, dict] = {}  # condition_id → live match state
        self._last_match_state_fetch: float = 0.0  # Rate limit match state queries
        self._daily_reentry_count: int = 0  # Re-entries today (reset each heavy cycle at midnight)
        self._last_reentry_reset_date = datetime.now(timezone.utc).date()
        self._cycle_ai_cost_start: float = 0.0  # Sprint cost at cycle start (for per-cycle tracking)
        self._eligible_cache: list = []  # Cached eligible markets from last Gamma scan
        self._eligible_pointer: int = 0  # Next index to analyze from cache
        self._eligible_cache_ts: float = 0  # When cache was last refreshed
        self._last_resolved_count = self._count_resolved()

        # V2: Circuit breaker and tiered blacklist
        self.circuit_breaker = CircuitBreaker()
        self.blacklist = Blacklist(path="logs/blacklist.json")
        self._soft_halt_active = False

        # V3 Maximus: Edge source tracker
        self.edge_tracker = EdgeSourceTracker()

        # Legacy migration disabled — exited markets are now managed by
        # graduated blacklist rules (timed/reentry cooldowns per exit reason).
        # Old permanent blacklists from exited_markets are NOT re-added on restart,
        # so previously exited markets can re-enter if price is still good.

        # Core modules
        self.scanner = MarketScanner(config.scanner)
        self.ai = AIAnalyst(config.ai)
        self.risk = RiskManager(config.risk)
        self.portfolio = Portfolio(initial_bankroll=config.initial_bankroll)

        # Signal enhancers
        self.esports = EsportsDataClient()
        self.sports = SportsDataClient()
        self.odds_api = OddsAPIClient()
        self.vlr = VLRDataClient()
        self.hltv = HLTVDataClient()
        self.news_scanner = NewsScanner()
        self.manip_guard = ManipulationGuard()
        self.cycle_timer = CycleTimer(config.cycle)
        self._last_candidate_count: int = 0
        self._last_light_ts: str = ""
        self.scout = ScoutScheduler(self.sports, self.esports)

        # Logging & notifications
        self.trade_log = TradeLogger(config.logging.trades_file)
        self.portfolio_log = TradeLogger(config.logging.portfolio_file)
        self.perf_log = TradeLogger(config.logging.performance_file)
        self.notifier = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            enabled=config.notifications.telegram_enabled,
        )
        self.odds_api.set_notifier(self.notifier)

        # Wallet & executor (initialized for live mode only)
        self.wallet = None
        clob_client = None
        if config.mode == Mode.LIVE:
            from src.wallet import Wallet
            pk = os.getenv("POLYGON_PRIVATE_KEY", "")
            if pk:
                self.wallet = Wallet(private_key=pk)
                # Initialize CLOB client for live order execution
                try:
                    from py_clob_client.client import ClobClient
                    host = "https://clob.polymarket.com"
                    chain_id = 137  # Polygon mainnet
                    clob_client = ClobClient(
                        host, key=pk, chain_id=chain_id,
                        signature_type=int(os.getenv("SIGNATURE_TYPE", "0")),
                        funder=os.getenv("PROXY_WALLET_ADDRESS", "") or None,
                    )
                    clob_client.set_api_creds(clob_client.create_or_derive_api_creds())
                    logger.info("CLOB client initialized for LIVE trading")
                except ImportError:
                    logger.error("py-clob-client not installed — run: pip install py-clob-client")
                except Exception as e:
                    logger.error("CLOB client init failed: %s", e)
            else:
                logger.error("LIVE mode requires POLYGON_PRIVATE_KEY in .env")
        self.executor = Executor(mode=config.mode, clob_client=clob_client)

    STOP_FILE = Path("logs/stop_signal")

    # ------ WebSocket price callback ------

    def _on_ws_price_update(self, token_id: str, price: float, ts: float) -> None:
        """Called by WebSocket feed on every price change.

        Updates current_price and runs fast exit checks (stop-loss, trailing TP).
        Exit decisions are queued — main thread drains the queue and executes exits.
        """
        # Find position with this token_id and update its current_price
        cid_found = None
        pos_found = None
        for cid, pos in self.portfolio.positions.items():
            if pos.token_id == token_id:
                pos.current_price = price
                cid_found = cid
                pos_found = pos
                break
        if not pos_found or not cid_found:
            return

        # --- Fast exit checks (no I/O, no API calls) ---
        try:
            self._ws_check_exits(cid_found, pos_found)
        except Exception:
            pass  # Never crash the WebSocket thread

    def _ws_check_exits(self, cid: str, pos) -> None:
        """Lightweight exit checks triggered by WebSocket price update.

        Queues exits to _ws_exit_queue — main thread processes them.
        Only checks stop-loss and trailing TP (pure math, no I/O).
        """
        # Skip if already queued or actively being exited
        if cid in self._exiting_set:
            return
        if any(q[0] == cid for q in self._ws_exit_queue):
            return

        direction = pos.direction
        entry = pos.entry_price
        current = pos.current_price

        # Calculate effective prices for BUY_NO
        if direction == "BUY_NO":
            effective_entry = 1.0 - entry
            effective_current = 1.0 - current
        else:
            effective_entry = entry
            effective_current = current

        pnl_pct = (effective_current - effective_entry) / effective_entry if effective_entry > 0 else 0

        # 1. Stop-loss check
        sl_pct = self.config.risk.esports_stop_loss_pct if getattr(pos, "sport_tag", "").startswith(("counter-strike", "dota", "league-of", "valorant")) else self.config.risk.stop_loss_pct
        if pnl_pct <= -abs(sl_pct):
            self._ws_exit_queue.append((cid, "stop_loss"))
            logger.info("WS_EXIT queued [stop_loss]: %s | pnl=%.1f%% <= -%.0f%%",
                        pos.slug[:35], pnl_pct * 100, abs(sl_pct) * 100)
            return

        # 2. Trailing TP check
        ttp_cfg = self.config.trailing_tp
        if ttp_cfg.enabled and not pos.volatility_swing:
            # Update peak tracking
            if direction == "BUY_NO":
                # For BUY_NO, peak_price tracks the lowest YES price (= highest NO value)
                if current < pos.peak_price or pos.peak_price == 0:
                    pos.peak_price = current
            else:
                if current > pos.peak_price:
                    pos.peak_price = current

            peak_pnl = (pos.peak_price - entry) / entry if entry > 0 else 0
            if direction == "BUY_NO":
                peak_pnl = ((1 - pos.peak_price) - (1 - entry)) / (1 - entry) if (1 - entry) > 0 else 0
            pos.peak_pnl_pct = max(pos.peak_pnl_pct, peak_pnl)

            if pos.peak_pnl_pct >= ttp_cfg.activation_pct:
                ttp_result = calculate_trailing_tp(
                    entry_price=entry, current_price=current,
                    direction=direction, peak_price=pos.peak_price,
                    trailing_active=True,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=ttp_cfg.trail_distance,
                )
                if ttp_result["action"] == "EXIT":
                    self._ws_exit_queue.append((cid, f"trailing_tp: {ttp_result['reason']}"))
                    logger.info("WS_EXIT queued [trailing_tp]: %s | %s",
                                pos.slug[:35], ttp_result["reason"])
                    return

        # 3. Esports "losing side" exit — if our side drops below 50%, cut losses
        _esports_tags = ("counter-strike", "dota-2", "league-of-legends", "valorant")
        sport_tag = getattr(pos, "sport_tag", "")
        if sport_tag in _esports_tags:
            if effective_current < 0.50:
                self._ws_exit_queue.append((cid, "esports_losing_side"))
                logger.info("WS_EXIT queued [esports_losing]: %s | eff_price=%.3f pnl=%.1f%%",
                            pos.slug[:35], effective_current, pnl_pct * 100)
                return

    # ------ Live match state ------

    def _fetch_match_states(self) -> dict[str, dict]:
        """Fetch live match states for all esports positions from PandaScore.

        Returns dict of condition_id → match_state dict.
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

    def _sync_ws_subscriptions(self) -> None:
        """Sync WebSocket subscriptions with active positions."""
        token_ids = [pos.token_id for pos in self.portfolio.positions.values()]
        self.ws_feed.sync_subscriptions(token_ids)

    def shutdown(self) -> None:
        self.running = False
        self.ws_feed.stop()
        logger.info("Shutdown requested — finishing current cycle")

    def _check_stop_file(self) -> None:
        """Poll for file-based stop signal (Windows-safe shutdown)."""
        if self.STOP_FILE.exists():
            logger.info("Stop file detected — shutting down gracefully")
            self.STOP_FILE.unlink(missing_ok=True)
            self.shutdown()

    def _set_status(self, state: str, step: str = "", light_ts: str = "") -> None:
        """Write current bot status to disk for dashboard polling."""
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = STATUS_FILE.with_suffix(".tmp")
            payload = {
                "state": state,
                "step": step,
                "cycle": self.cycle_count,
                "ts": datetime.now(timezone.utc).isoformat(),
                "has_positions": len(self.portfolio.positions) > 0,
                "max_positions": self.config.risk.max_positions,
            }
            if light_ts:
                payload["light_ts"] = light_ts
            elif hasattr(self, '_last_light_ts'):
                payload["light_ts"] = self._last_light_ts
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(STATUS_FILE)
        except OSError:
            pass

    def _is_paused(self) -> bool:
        """Check if bot is paused awaiting user approval."""
        if PAUSE_FILE.exists():
            logger.info("Paused — awaiting approval. Delete %s or send /resume to continue.", PAUSE_FILE)
            return True
        return False

    def _maybe_send_milestone_reminder(self) -> None:
        """Once per day, check if today matches a testing plan milestone."""
        marker = Path("logs/.last_milestone_reminder")
        today = datetime.now(timezone.utc).date()

        # Already reminded today?
        if marker.exists():
            try:
                last = marker.read_text(encoding="utf-8").strip()
                if last == str(today):
                    return
            except OSError:
                pass

        day_number = (today - TEST_START_DATE).days + 1  # Day 1 = start date

        # Find matching milestone
        for milestone_day, message in _MILESTONES:
            if day_number == milestone_day:
                self.notifier.send(f"*MILESTONE*\n\n{message}")
                logger.info("Milestone reminder sent: Day %d", day_number)
                break
        else:
            # No exact match — send daily status on non-milestone days
            if day_number > 0:
                self.notifier.send(
                    f"\U0001f4ca *DAILY* — Day {day_number}\n\n"
                    f"Balance: `${self.portfolio.bankroll:.2f}`\n"
                    f"Positions: `{len(self.portfolio.positions)}`\n"
                    f"API budget: `${self.ai.budget_remaining_usd:.2f}`"
                )

        # Mark today as done
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(today), encoding="utf-8")

    def _check_bet_limit(self) -> None:
        """Bet limit check — disabled (slots should fill freely)."""
        pass

    def _load_recent_analyses(self) -> dict[str, float]:
        """Restore recently analyzed market IDs from predictions.jsonl on restart.

        Cache logic:
        - In portfolio → cache (already held, skip AI)
        - BUY signal was given (any confidence with edge ≥5%) → DON'T cache,
          let pipeline re-check current price and re-enter if still good
        - HOLD/reject (low edge or C confidence) → cache (don't waste AI credits)
        """
        pred_path = Path("logs/predictions.jsonl")
        if not pred_path.exists():
            return {}
        cutoff = time.time() - 4 * 3600  # 4 hours
        # Load current portfolio to know what's already held
        pos_path = Path("logs/positions.json")
        held_ids: set[str] = set()
        if pos_path.exists():
            try:
                held_ids = set(json.loads(pos_path.read_text(encoding="utf-8")).keys())
            except Exception:
                pass

        restored: dict[str, float] = {}
        skipped_buy = 0
        try:
            for line in pred_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)
                ts_str = entry.get("timestamp", "")
                cid = entry.get("condition_id", "")
                if not ts_str or not cid:
                    continue
                try:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    ts = dt.timestamp()
                except (ValueError, TypeError):
                    continue
                if ts < cutoff:
                    continue

                # If already in portfolio, always cache (no need to re-analyze)
                if cid in held_ids:
                    restored[cid] = ts
                    continue

                # Check if this was a BUY-worthy signal
                ai_prob = entry.get("ai_probability", 0.5)
                mkt_price = entry.get("market_price", 0.5)
                conf = entry.get("confidence", "C")
                edge = abs(ai_prob - mkt_price)

                if edge >= 0.05 and conf in ("A", "B+", "B-"):
                    # BUY-worthy (any decent confidence) → don't cache,
                    # pipeline will re-check current price and re-enter if still viable
                    skipped_buy += 1
                    continue

                # Consensus candidates: AI and market both ≥65% same direction
                # Don't cache — price may shift and they deserve fresh re-evaluation
                _ce_min = 0.65
                _is_cyes = ai_prob >= _ce_min and mkt_price >= _ce_min
                _is_cno = (1 - ai_prob) >= _ce_min and (1 - mkt_price) >= _ce_min
                if (_is_cyes or _is_cno) and conf in ("A", "B+"):
                    skipped_buy += 1
                    continue

                restored[cid] = ts
        except Exception as e:
            logger.warning("Could not restore analyzed markets: %s", e)
            return {}
        if restored or skipped_buy:
            logger.info(
                "Analysis cache: %d HOLD cached (saved AI calls), %d BUY-worthy uncached (will re-evaluate)",
                len(restored), skipped_buy,
            )
        return restored

    def _load_exited_markets(self) -> set:
        """Load condition IDs of previously exited markets from disk."""
        p = Path("logs/exited_markets.json")
        if not p.exists():
            return set()
        try:
            return set(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            return set()

    def _save_exited_market(self, condition_id: str) -> None:
        """Persist an exited market so we never re-enter after restart."""
        self._exited_markets.add(condition_id)
        p = Path("logs/exited_markets.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(list(self._exited_markets)), encoding="utf-8")
        tmp.replace(p)

    def _count_resolved(self) -> int:
        """Count resolved predictions in calibration file."""
        cal = Path("logs/calibration.jsonl")
        if not cal.exists():
            return 0
        return sum(1 for line in cal.read_text(encoding="utf-8").strip().split("\n") if line.strip())

    def _load_last_resolved_count(self) -> int:
        """Load persisted resolved count to avoid duplicate notifications."""
        p = Path("logs/self_improve_state.json")
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return data.get("last_resolved_count", 0)
            except Exception:
                pass
        return 0

    def _save_last_resolved_count(self, count: int) -> None:
        """Persist resolved count so it survives restarts."""
        p = Path("logs/self_improve_state.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps({"last_resolved_count": count}), encoding="utf-8")
        tmp.replace(p)

    def _check_self_improve_ready(self) -> None:
        """Notify via Telegram when enough new data exists for self-improvement."""
        current = self._count_resolved()
        # Read from file to stay in sync across restarts and multiple processes
        persisted = self._load_last_resolved_count()
        last = max(self._last_resolved_count, persisted)
        new_resolved = current - last
        if new_resolved >= 15:
            self.notifier.send(
                f"\U0001f9ea *SELF-IMPROVE*\n\n"
                f"{new_resolved} new resolved predictions\n"
                f"{current} total resolved\n\n"
                f"Run `/self-improve` in Claude Code"
            )
            self._last_resolved_count = current
            self._save_last_resolved_count(current)
            logger.info("Self-improve readiness notification sent (%d new resolved)", new_resolved)

    def _drain_ws_exit_queue(self) -> int:
        """Process exits queued by WebSocket price callbacks. Returns count."""
        drained = 0
        while self._ws_exit_queue:
            cid, reason = self._ws_exit_queue.pop(0)
            if cid in self._exiting_set:
                continue  # Already being exited (#2a double-exit guard)
            if cid in self.portfolio.positions:
                logger.info("WS_EXIT executing: %s | reason=%s", self.portfolio.positions[cid].slug[:35], reason)
                self._exit_position(cid, reason)
                drained += 1
        return drained

    def run_light_cycle(self) -> None:
        """Price-only cycle: update prices + check exits. No scanning, no AI, no news."""
        if self._is_paused():
            return

        # First: drain any exits queued by WebSocket callbacks
        ws_exits = self._drain_ws_exit_queue()
        if ws_exits:
            logger.info("Drained %d WebSocket-triggered exits before light cycle", ws_exits)

        logger.info("=== Light cycle (price check only) ===")
        self._set_status("running", "Light cycle — price check")

        # Update bankroll
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.portfolio.update_bankroll(bankroll)

        # Update position prices: skip CLOB API when WebSocket is feeding prices
        if self.ws_feed.connected:
            logger.debug("WS connected — skipping CLOB price fetch (WS has fresh prices)")
            self.last_cycle_has_live_clob = bool(self.portfolio.positions)
        else:
            self.last_cycle_has_live_clob = self._update_position_prices()

        # Sync WebSocket subscriptions with active positions
        self._sync_ws_subscriptions()

        # Fetch live match states from PandaScore (rate-limited to 1/min)
        match_states = self._fetch_match_states()

        # Esports halftime exits — uses live score when available
        for cid in self.portfolio.check_esports_halftime_exits(match_states=match_states):
            self._exit_position(cid, "esports_halftime")

        # --- Match-aware exit system (4 layers) ---
        match_exit_results = self.portfolio.check_match_aware_exits()
        for mexr in match_exit_results:
            cid = mexr["condition_id"]
            if mexr.get("exit") and cid in self.portfolio.positions:
                slug = self.portfolio.positions[cid].slug[:40]
                logger.info("Match-aware exit [%s]: %s — %s", mexr["layer"], slug, mexr.get("reason", ""))
                self._exit_position(cid, f"match_exit_{mexr['layer']}")
            if mexr.get("revoke_hold") and cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                if pos.scouted:
                    pos.hold_was_original = True
                    pos.scouted = False
                    pos.hold_revoked_at = datetime.now(timezone.utc)
                    logger.info("Hold-to-resolve REVOKED: %s — %s", pos.slug[:40], mexr.get("reason", ""))
            if mexr.get("restore_hold") and cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                pos.scouted = True
                pos.hold_revoked_at = None
                logger.info("Hold-to-resolve RESTORED: %s — %s", pos.slug[:40], mexr.get("reason", ""))

        # Check stop-losses and take-profits
        vs_cfg = self.config.volatility_swing
        for cid in self.portfolio.check_stop_losses(
                self.config.risk.stop_loss_pct, vs_stop_loss_pct=vs_cfg.stop_loss_pct,
                esports_stop_loss_pct=self.config.risk.esports_stop_loss_pct):
            self._exit_position(cid, "stop_loss")

        # V3 Maximus: Trailing Take-Profit (replaces fixed TP for non-VS positions)
        ttp_cfg = self.config.trailing_tp
        if ttp_cfg.enabled:
            for cid, pos in list(self.portfolio.positions.items()):
                if pos.volatility_swing:
                    continue  # VS positions use their own TP logic
                ttp_result = calculate_trailing_tp(
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    direction=pos.direction,
                    peak_price=pos.peak_price,
                    trailing_active=pos.peak_pnl_pct >= ttp_cfg.activation_pct,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=ttp_cfg.trail_distance,
                )
                # Update peak tracking
                if ttp_result["peak_price"] > pos.peak_price:
                    pos.peak_price = ttp_result["peak_price"]
                if ttp_result["action"] == "EXIT":
                    logger.info("Trailing TP EXIT: %s — %s (profit %.1f%%)",
                                pos.slug[:40], ttp_result["reason"], ttp_result["profit_pct"] * 100)
                    self._exit_position(cid, f"trailing_tp: {ttp_result['reason']}")

        # VS positions: tighten trailing near resolution (30min → trail 4% instead of 8%)
        if ttp_cfg.enabled:
            for cid, pos in list(self.portfolio.positions.items()):
                if not pos.volatility_swing:
                    continue
                if pos.peak_pnl_pct < ttp_cfg.activation_pct:
                    continue  # Not yet activated
                # Calculate hours to resolution
                hours_left = 99.0
                if pos.end_date_iso:
                    try:
                        from datetime import datetime, timezone
                        end_dt = datetime.fromisoformat(pos.end_date_iso.replace("Z", "+00:00"))
                        hours_left = max(0, (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600)
                    except (ValueError, TypeError):
                        pass
                trail_dist = 0.04 if hours_left <= 0.5 else ttp_cfg.trail_distance
                ttp_result = calculate_trailing_tp(
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    direction=pos.direction,
                    peak_price=pos.peak_price,
                    trailing_active=True,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=trail_dist,
                )
                if ttp_result["peak_price"] > pos.peak_price:
                    pos.peak_price = ttp_result["peak_price"]
                if ttp_result["action"] == "EXIT":
                    logger.info("VS trailing TP EXIT: %s — trail=%.0f%% hours_left=%.1f",
                                pos.slug[:40], trail_dist * 100, hours_left)
                    self._exit_position(cid, f"vs_trailing_tp: trail={trail_dist:.0%}")

        # Fixed TP only for VS positions now
        for cid in self.portfolio.check_take_profits(
                self.config.risk.take_profit_pct, vs_take_profit_pct=vs_cfg.take_profit_pct,
                vs_tp_floor=vs_cfg.tp_floor, vs_tp_ceiling=vs_cfg.tp_ceiling):
            pos = self.portfolio.positions.get(cid)
            if pos and not pos.volatility_swing:
                continue  # Non-VS uses trailing TP now
            is_vs = pos and pos.volatility_swing
            is_spike = (pos and not is_vs and pos.confidence in ("A", "B+") and
                        max(pos.ai_probability, 1 - pos.ai_probability) > 0.60)
            reason = "vs_take_profit" if is_vs else ("spike_exit" if is_spike else "take_profit")
            cooldown = 0 if (is_vs or is_spike) else 3
            self._exit_position(cid, reason, cooldown_cycles=cooldown)
        trailing_tiers = [{"min_peak": t.min_peak, "drop_pct": t.drop_pct}
                          for t in self.config.risk.trailing_stop_tiers]
        for cid in self.portfolio.check_trailing_stops(trailing_tiers=trailing_tiers):
            self._exit_position(cid, "trailing_stop")
        for cid in self.portfolio.check_volatility_swing_exits():
            self._exit_position(cid, "vs_mandatory_exit", cooldown_cycles=0)

        # Esports losing side exit — if our side drops below 50%, cut losses
        _esports_tags_lc = ("counter-strike", "dota-2", "league-of-legends", "valorant")
        for cid, pos in list(self.portfolio.positions.items()):
            if getattr(pos, "sport_tag", "") not in _esports_tags_lc:
                continue
            if pos.direction == "BUY_NO":
                eff = 1.0 - pos.current_price
            else:
                eff = pos.current_price
            if eff < 0.50:
                logger.info("Esports losing side exit: %s | eff=%.3f", pos.slug[:35], eff)
                self._exit_position(cid, "esports_losing_side")

        # FAR penny exits — multiplier targets ($0.01→5x, $0.02→2x)
        self._check_far_penny_exits()

        # Unified farming re-entry — check pool for dip opportunities (no AI cost)
        self._check_farming_reentry()

        # Persist updated prices to disk so dashboard sees them
        self.portfolio.save_prices_to_disk()

        # Live dip check — every 5 min (ESPN rate limit)
        if time.time() - self._last_live_dip_check >= 300:
            self._check_live_dips()
            self._last_live_dip_check = time.time()

        # Momentum signal check — log-only, runs with every live dip check
        self._check_momentum_signals()

        # Bond scan — every 10 min (low-risk near-certain markets)
        if time.time() - self._last_bond_scan >= 600:
            self._check_bond_candidates()
            self._last_bond_scan = time.time()

        # Penny alpha scan — every 15 min (ultra-cheap asymmetric bets)
        if time.time() - self._last_penny_scan >= 900:
            self._check_penny_candidates()
            self._last_penny_scan = time.time()

        # Log portfolio snapshot so dashboard picks up realized PnL changes from exits
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self._log_cycle_summary(bankroll, "light_cycle")
        self._save_stock_to_disk()

        self._last_light_ts = datetime.now(timezone.utc).isoformat()
        self._set_status("idle", "Light cycle done")
        logger.info("Light cycle done — %d positions checked", len(self.portfolio.positions))

    def run_cycle(self) -> None:
        # Skip cycle if paused
        if self._is_paused():
            return
        self.cycle_count += 1
        self._cycle_ai_cost_start = self.ai._sprint_cost_usd  # Track per-cycle AI cost
        self.risk.new_cycle()  # Reset per-cycle flags (cooldown decrement)
        logger.info("=== Cycle #%d start ===", self.cycle_count)
        self._set_status("running", "Starting cycle")

        # 0. Daily milestone reminder + self-reflection
        # self._maybe_send_milestone_reminder()  # Disabled in V3
        self._maybe_run_reflection()

        # 0b. Scout run (twice daily: 06:00 + 18:00 UTC)
        self._set_status("running", "Scouting matches")
        if self.scout.should_run_scout():
            new_scouted = self.scout.run_scout()
            if new_scouted:
                self.notifier.send(
                    f"\U0001f50d *SCOUT*\n\n"
                    f"{new_scouted} new matches scouted\n"
                    f"{len(self.scout._queue)} total in queue"
                )

        # 1. Check bankroll
        self._set_status("running", "Checking bankroll")
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.portfolio.update_bankroll(bankroll)

        # Drawdown check — soft (no new entries) / hard (close all + halt)
        dd_level = self.portfolio.get_drawdown_level()
        if dd_level == "hard":
            msg = self.notifier.alert_drawdown(bankroll, self.portfolio.high_water_mark)
            self.notifier.send(msg)
            logger.critical("HARD HALT: equity < 35%% HWM — closing all positions")
            self._ws_exit_queue.clear()  # Stop WS from interfering during panic sell (#1a)
            for cid in list(self.portfolio.positions.keys()):
                if cid not in self._exiting_set:
                    self._exit_position(cid, "hard_halt_drawdown")
            self.running = False
            return
        elif dd_level == "soft":
            if not getattr(self, '_soft_halt_active', False):
                self.notifier.send("⚠️ SOFT HALT: equity < 50% HWM — yeni entry durduruldu")
                self._soft_halt_active = True
            logger.warning("SOFT HALT active: no new entries until equity recovers")
        else:
            if getattr(self, '_soft_halt_active', False):
                self.notifier.send("✅ Drawdown recovered — entries resumed")
                self._soft_halt_active = False

        # V2: Circuit breaker check
        halt, halt_reason = self.circuit_breaker.should_halt_entries()
        if halt:
            logger.warning("Circuit breaker active: %s", halt_reason)
        if halt and not getattr(self, '_cb_was_active', False):
            self.notifier.send(f"\u26a0\ufe0f Circuit breaker ACTIVATED: {halt_reason}")
            self._cb_was_active = True
        elif not halt and getattr(self, '_cb_was_active', False):
            self.notifier.send("\u2705 Circuit breaker deactivated \u2014 entries resumed")
            self._cb_was_active = False

        # Soft halt also blocks new entries
        if getattr(self, '_soft_halt_active', False):
            halt = True
            halt_reason = "Soft drawdown halt (equity < 50% HWM)"

        # 2. Check resolved markets for calibration
        self._set_status("running", "Checking resolved markets")
        self._check_resolved_markets()

        # 3. Update position prices from current market data
        self._set_status("running", "Updating prices")
        self.last_cycle_has_live_clob = self._update_position_prices()
        self._check_price_drift_reanalysis()

        # 4. Match-aware exit system + stop-losses/take-profits
        self._set_status("running", "Checking stop-losses")

        # --- Match-aware exit system (4 layers) ---
        match_exit_results = self.portfolio.check_match_aware_exits()
        for mexr in match_exit_results:
            cid = mexr["condition_id"]
            if mexr.get("exit") and cid in self.portfolio.positions:
                slug = self.portfolio.positions[cid].slug[:40]
                logger.info("Match-aware exit [%s]: %s — %s", mexr["layer"], slug, mexr.get("reason", ""))
                self._exit_position(cid, f"match_exit_{mexr['layer']}")
            if mexr.get("revoke_hold") and cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                if pos.scouted:
                    pos.hold_was_original = True
                    pos.scouted = False
                    pos.hold_revoked_at = datetime.now(timezone.utc)
                    logger.info("Hold-to-resolve REVOKED: %s — %s", pos.slug[:40], mexr.get("reason", ""))
            if mexr.get("restore_hold") and cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                pos.scouted = True
                pos.hold_revoked_at = None
                logger.info("Hold-to-resolve RESTORED: %s — %s", pos.slug[:40], mexr.get("reason", ""))

        vs_cfg = self.config.volatility_swing
        for cid in self.portfolio.check_stop_losses(
                self.config.risk.stop_loss_pct, vs_stop_loss_pct=vs_cfg.stop_loss_pct,
                esports_stop_loss_pct=self.config.risk.esports_stop_loss_pct):
            self._exit_position(cid, "stop_loss")
        for cid in self.portfolio.check_take_profits(
                self.config.risk.take_profit_pct, vs_take_profit_pct=vs_cfg.take_profit_pct,
                vs_tp_floor=vs_cfg.tp_floor, vs_tp_ceiling=vs_cfg.tp_ceiling):
            # Spike exits get 0 cooldown — re-evaluate immediately if price drops back
            pos = self.portfolio.positions.get(cid)
            is_vs = pos and pos.volatility_swing
            is_spike = (pos and not is_vs and pos.confidence in ("A", "B+") and
                        max(pos.ai_probability, 1 - pos.ai_probability) > 0.60)
            reason = "vs_take_profit" if is_vs else ("spike_exit" if is_spike else "take_profit")
            cooldown = 0 if (is_vs or is_spike) else 3  # spike/VS: immediate re-entry eligible
            self._exit_position(cid, reason, cooldown_cycles=cooldown)
        trailing_tiers = [{"min_peak": t.min_peak, "drop_pct": t.drop_pct}
                          for t in self.config.risk.trailing_stop_tiers]
        for cid in self.portfolio.check_trailing_stops(trailing_tiers=trailing_tiers):
            self._exit_position(cid, "trailing_stop")
        # Volatility swing mandatory exit (30 min before resolve)
        for cid in self.portfolio.check_volatility_swing_exits():
            self._exit_position(cid, "vs_mandatory_exit", cooldown_cycles=0)

        # Unified farming re-entry — check pool for dip opportunities (no AI cost)
        self._check_farming_reentry()

        # 4b. Re-evaluate election positions — swing trade on opinion shift
        self._reevaluate_election_positions(bankroll)

        # 4c. Fill from stock — use pre-analyzed candidates if slots opened
        self._fill_from_stock()

        # 4d. Fill from FAV stock — execute favorites in their dedicated slots
        self._fill_from_fav_stock()

        # 4e. Fill from FAR stock — execute swing/penny candidates in FAR slots
        self._fill_from_far_stock()

        # 5. Early slot check — skip scan + AI if ALL slot types are full
        vs_reserved = self.config.volatility_swing.reserved_slots
        normal_max = self.config.risk.max_positions - vs_reserved
        current_normal = self.portfolio.normal_position_count
        current_vs = sum(1 for p in self.portfolio.positions.values() if p.volatility_swing)
        fav_current = sum(1 for p in self.portfolio.positions.values()
                          if getattr(p, 'entry_reason', '') == 'fav_time_gate')
        far_current = sum(1 for p in self.portfolio.positions.values()
                          if getattr(p, 'entry_reason', '') == 'far')
        all_full = (current_normal >= normal_max and
                    current_vs >= vs_reserved and
                    fav_current >= self._FAV_MAX_SLOTS and
                    far_current >= self.config.far.max_slots)
        if all_full:
            logger.info("All slots full (NRM:%d/%d VS:%d/%d FAV:%d/%d FAR:%d/%d) — skipping scan + AI",
                        current_normal, normal_max, current_vs, vs_reserved,
                        fav_current, self._FAV_MAX_SLOTS, far_current, self.config.far.max_slots)
            self._log_cycle_summary(bankroll, "full_cycle")
            self._set_status("idle", "All slots full — waiting")
            return

        # 5b. Scan markets — use cached eligible list if available, else fresh scan
        self._set_status("running", "Scanning markets")
        ELIGIBLE_CACHE_TTL = 1800  # 30 min — refresh when slots are full or cache stale
        now_ts = time.time()
        cache_stale = (now_ts - self._eligible_cache_ts) > ELIGIBLE_CACHE_TTL
        cache_exhausted = self._eligible_pointer >= len(self._eligible_cache)

        if self._eligible_cache and not cache_stale and not cache_exhausted:
            # Reuse cached list — skip Gamma API call
            markets = self._eligible_cache
            logger.info("Using cached eligible list (%d markets, pointer=%d/%d)",
                        len(markets), self._eligible_pointer, len(markets))
        else:
            # Fresh scan from Gamma API
            if cache_stale and self._eligible_cache:
                logger.info("Eligible cache stale (%.0fs old) — refreshing from Gamma",
                            now_ts - self._eligible_cache_ts)
            markets = self.scanner.fetch()
            if not markets:
                self._log_cycle_summary(bankroll, "no qualifying markets")
                return

            # 5b. Pre-filter: remove logically impossible markets before spending AI tokens
            markets = filter_impossible_markets(markets)
            if not markets:
                self._log_cycle_summary(bankroll, "all markets filtered as impossible")
                return

            # 6. New market detection — prioritize freshly opened markets (edge erodes fast)
            current_ids = {m.condition_id for m in markets}
            if self._seen_market_ids:
                new_ids = current_ids - self._seen_market_ids
                if new_ids:
                    logger.info("NEW MARKETS DETECTED: %d new markets this cycle", len(new_ids))
                    new_markets_list = [m for m in markets if m.condition_id in new_ids]
                    old_markets_list = [m for m in markets if m.condition_id not in new_ids]
                    for m in new_markets_list:
                        self.ai.invalidate_cache(m.condition_id)
                    markets = new_markets_list + old_markets_list
                    for m in new_markets_list[:5]:
                        logger.info("  NEW: %s (%.0f%%) vol=$%.0f",
                                    m.question[:60], m.yes_price * 100, m.volume_24h)
            self._seen_market_ids = current_ids

            # Cache the full eligible list and reset pointer
            self._eligible_cache = markets
            self._eligible_pointer = 0
            self._eligible_cache_ts = now_ts
            logger.info("Cached %d eligible markets for batch processing", len(markets))

        # 7. Filter BEFORE batch cut — don't waste AI calls on known-skip markets
        # 7a. Remove markets already in portfolio or on exit cooldown
        skipped_portfolio = sum(1 for m in markets if m.condition_id in self.portfolio.positions)
        skipped_cooldown = sum(
            1 for m in markets
            if m.condition_id not in self.portfolio.positions
            and self._exit_cooldowns.get(m.condition_id, 0) > self.cycle_count
        )
        # Collect event_ids already held — block all outcomes of same event
        held_event_ids = {
            p.event_id for p in self.portfolio.positions.values()
            if p.event_id
        }
        markets = [
            m for m in markets
            if m.condition_id not in self.portfolio.positions
            and not (m.event_id and m.event_id in held_event_ids)
            and not self.blacklist.is_blocked(m.condition_id, self.cycle_count)
            and self._exit_cooldowns.get(m.condition_id, 0) <= self.cycle_count
        ]
        if skipped_portfolio or skipped_cooldown:
            logger.info("Skipped %d in portfolio, %d on cooldown (saved API calls)",
                        skipped_portfolio, skipped_cooldown)

        # 7b. Skip markets already analyzed recently (don't re-send to AI)
        # Clean up old entries (>4 hours = allow re-analysis)
        self._analyzed_market_ids = {
            cid: ts for cid, ts in self._analyzed_market_ids.items()
            if now_ts - ts < 4 * 3600
        }
        # Also skip markets already in candidate stock (already analyzed, waiting for slot)
        _stock_ids = {c["market"].condition_id for c in self._candidate_stock}
        already_analyzed = sum(1 for m in markets if m.condition_id in self._analyzed_market_ids or m.condition_id in _stock_ids)
        markets = [m for m in markets if m.condition_id not in self._analyzed_market_ids and m.condition_id not in _stock_ids]
        if already_analyzed:
            logger.info("Skipped %d already analyzed/in stock (saved AI calls)", already_analyzed)

        # 7c. Filter non-moneyline bet types (spread, totals, props — AI has no edge)
        _ALT_BET_KEYWORDS = {
            "spread", "handicap", "over", "under", "total points", "total goals",
            "total runs", "total maps", "o/u", "player props", "first blood",
            "first kill", "first to score", "first goal", "first touchdown",
            "most kills", "most assists", "exact score",
        }
        def _is_alt_bet(question: str) -> bool:
            q = question.lower()
            for kw in _ALT_BET_KEYWORDS:
                if kw in q:
                    return True
            # Spread pattern: "Team (-1.5)" or "Team (+3.5)"
            if re.search(r'\([+-]\d+\.?\d*\)', q):
                return True
            return False

        alt_skipped = sum(1 for m in markets if _is_alt_bet(m.question))
        markets = [m for m in markets if not _is_alt_bet(m.question)]
        if alt_skipped:
            logger.info("Skipped %d alt bets (spread/totals/props — moneyline only)", alt_skipped)

        # 7d. Pre-filter LIVE matches (don't waste AI calls on in-progress games)
        live_markets = []
        non_live = []
        now_live_check = datetime.now(timezone.utc)
        for m in markets:
            # If scout has actual start time → use it for definitive LIVE check
            scout_entry = self.scout.match_market(m.question, m.slug)
            if scout_entry and scout_entry.get("match_time"):
                try:
                    mt = datetime.fromisoformat(scout_entry["match_time"])
                    if mt > now_live_check:
                        non_live.append(m)
                        continue  # Confirmed future match, skip LIVE check
                    else:
                        live_markets.append(m)
                        logger.debug("LIVE skip (scout): %s started at %s", m.question[:60], mt.isoformat())
                        continue  # Match already started → LIVE
                except (ValueError, TypeError):
                    pass
            # Use Gamma event.live (definitive), fallback to heuristic
            is_live = m.event_live if hasattr(m, 'event_live') else self._estimate_match_live(m.slug, m.question, m.end_date_iso)
            if is_live:
                live_markets.append(m)
                logger.debug("LIVE skip: %s (event_live=%s)", m.question[:60], m.event_live if hasattr(m, 'event_live') else 'heuristic')
            else:
                non_live.append(m)
        if live_markets:
            logger.info("Skipped %d LIVE matches pre-batch (saved AI calls)", len(live_markets))
        markets = non_live

        # 7d. Near-first batch allocation
        # Fill batch with near matches (≤6h) first — faster capital turnover
        # Far matches (>6h) only fill remaining slots when near can't fill batch
        # Smart batch sizing: only analyze what we need to fill
        vs_reserved = self.config.volatility_swing.reserved_slots
        normal_max = self.config.risk.max_positions - vs_reserved  # 15 normal slots
        current_normal = self.portfolio.normal_position_count
        open_slots = max(0, normal_max - current_normal)
        stock_viable = len([c for c in self._candidate_stock
                           if time.time() - c.get("stocked_at", 0) < 3600])
        stock_max = 5
        stock_empty = max(0, stock_max - stock_viable)
        # Don't spend AI on stock when all position slots are full.
        # Stock gets filled naturally from: (1) demoted exits, (2) leftover candidates when slots open.
        if open_slots == 0:
            stock_empty = 0
        total_need = open_slots + stock_empty  # positions to fill + stock to fill

        if total_need == 0:
            # Everything full → skip AI entirely, only do exits/price checks
            logger.info("Pool full (%d positions) + stock full (%d) → skipping market scan (save API)",
                        self.portfolio.active_position_count, stock_viable)
            return
        else:
            # Analyze proportional to need: 2x multiplier for selection quality
            batch_size = min(self.config.ai.batch_size, max(5, total_need * 2))
            logger.info("Need %d (slots=%d + stock=%d) → batch_size=%d",
                        total_need, open_slots, stock_empty, batch_size)
        now_utc = datetime.now(timezone.utc)

        # Pre-match scout queue for actual start times (PandaScore/ESPN)
        # endDate from Gamma is a settlement buffer, NOT match end time
        _scout_match_times: dict[str, float] = {}  # condition_id -> hours_to_start
        for m in markets:
            scout_entry = self.scout.match_market(m.question, m.slug)
            if scout_entry and scout_entry.get("match_time"):
                try:
                    mt = datetime.fromisoformat(scout_entry["match_time"])
                    h = (mt - now_utc).total_seconds() / 3600
                    _scout_match_times[m.condition_id] = max(0, h)
                except (ValueError, TypeError):
                    pass

        def _hours_to_end(m: MarketData) -> float:
            if not m.end_date_iso:
                return 999.0
            try:
                end_dt = datetime.fromisoformat(m.end_date_iso.replace("Z", "+00:00"))
                return max(0, (end_dt - now_utc).total_seconds() / 3600)
            except (ValueError, TypeError):
                return 999.0

        def _hours_to_start(m: MarketData) -> float:
            """Hours until match STARTS. Uses actual start time from
            PandaScore (esports) or ESPN (sports) when available,
            then match_start_iso from Gamma event startTime.
            Falls back to endDate - duration estimate otherwise."""
            # Prefer actual start time from scout queue
            if m.condition_id in _scout_match_times:
                return _scout_match_times[m.condition_id]
            # Prefer match_start_iso from Gamma event startTime (if available on MarketData)
            _msi = getattr(m, 'match_start_iso', '')
            if _msi:
                try:
                    start_dt = datetime.fromisoformat(_msi.replace("Z", "+00:00"))
                    return max(0, (start_dt - now_utc).total_seconds() / 3600)
                except (ValueError, TypeError):
                    pass
            # Fallback: estimate from endDate (unreliable, but better than nothing)
            h_end = _hours_to_end(m)
            if h_end >= 999:
                return 999.0
            duration = self._match_duration(m.slug, m.question)
            return max(0, h_end - duration)

        if _scout_match_times:
            logger.info("Scout match times: %d/%d markets have actual start times",
                        len(_scout_match_times), len(markets))

        # Filter out live matches BEFORE AI analysis (save API cost)
        pre_live = len(markets)
        markets = [m for m in markets if not (m.event_live if hasattr(m, 'event_live') else self._estimate_match_live(m.slug, m.question, m.end_date_iso, match_start_iso=getattr(m, 'match_start_iso', '')))]
        if len(markets) < pre_live:
            logger.info("Pre-filtered %d live matches (saved API cost)", pre_live - len(markets))

        # Filter out effectively resolved markets — one side >96¢ means match is over
        pre_resolved = len(markets)
        markets = [m for m in markets if m.yes_price <= 0.96 and m.no_price <= 0.96]
        if len(markets) < pre_resolved:
            logger.info("Pre-filtered %d resolved/near-resolved markets (price >96¢)",
                        pre_resolved - len(markets))

        # Position-aware dynamic batch allocation:
        # Few positions open → explore distant markets (early entry = better odds)
        # Many positions open → focus on near markets (fast turnover = capital velocity)
        imminent = sorted([m for m in markets if _hours_to_start(m) <= 6], key=_hours_to_start)
        midrange = sorted([m for m in markets if 6 < _hours_to_start(m) <= 24], key=_hours_to_start)
        discovery = sorted([m for m in markets if _hours_to_start(m) > 24], key=_hours_to_start)

        pos_count = self.portfolio.active_position_count
        max_pos = self.config.risk.max_positions
        capacity_pct = pos_count / max(1, max_pos)  # 0.0 = empty, 1.0 = full

        # Imminent-first strategy:
        # 1. Always fill imminent slots first (0-6h = fast turnover)
        # 2. As imminent fills up, shift to mid/discovery for stock pipeline
        imm_available = len(imminent)
        if imm_available >= batch_size:
            # Plenty of imminent — fill batch with them, stock gets mid/disc later
            imm_slots = batch_size
            mid_slots = 0
            disc_slots = 0
        elif imm_available >= batch_size * 6 // 10:
            # Good imminent supply — take all, fill rest with mid
            imm_slots = imm_available
            mid_slots = batch_size - imm_slots
            disc_slots = 0
        else:
            # Imminent scarce — take all, fill with mid then discovery
            imm_slots = imm_available
            mid_slots = min(len(midrange), (batch_size - imm_slots) * 7 // 10)
            disc_slots = batch_size - imm_slots - mid_slots

        prioritized = imminent[:imm_slots]
        prioritized += midrange[:mid_slots]
        prioritized += discovery[:disc_slots]
        # If any bucket was underfilled, fill from others
        if len(prioritized) < batch_size:
            used_ids = {m.condition_id for m in prioritized}
            remaining = [m for m in imminent + midrange + discovery if m.condition_id not in used_ids]
            prioritized += remaining[:batch_size - len(prioritized)]

        far_used = sum(1 for m in prioritized if _hours_to_start(m) > 6)
        near_used = len(prioritized) - far_used

        # Track which markets are far (for higher edge threshold at evaluation)
        self._far_market_ids = {m.condition_id for m in prioritized if _hours_to_start(m) > 6}

        logger.info("Batch: %d markets (%d imminent + %d mid + %d disc, capacity=%.0f%%, %d eligible)",
                     len(prioritized), near_used,
                     sum(1 for m in prioritized if 6 < _hours_to_start(m) <= 24),
                     sum(1 for m in prioritized if _hours_to_start(m) > 24),
                     capacity_pct * 100, len(markets))

        # 8. Fetch news (multi-source: NewsAPI → GNews → RSS)
        self._set_status("running", f"Fetching news for {len(prioritized)} markets")
        _STOP_WORDS = {"will", "the", "a", "an", "is", "are", "was", "were", "be", "been",
                        "to", "of", "in", "on", "at", "by", "for", "or", "and", "not", "no",
                        "do", "does", "did", "has", "have", "had", "this", "that", "it",
                        "with", "from", "as", "but", "if", "than", "win", "before", "after",
                        "vs", "vs.", "over", "more", "most", "between",
                        "o/u", "under", "total", "spread", "moneyline", "ml"}
        market_keywords = {
            m.condition_id: [
                w for w in (
                    # Strip punctuation (colons, parens, etc.) before filtering
                    word.strip(".:;,!?()[]")
                    for word in m.question.lower().split()
                )
                if w and w not in _STOP_WORDS and not w.replace(".", "").isdigit()
            ][:5]
            for m in prioritized
        }
        news_by_market = self.news_scanner.search_for_markets(market_keywords)

        # Build per-market news context (each market gets only its own relevant news)
        news_context_by_market: dict[str, str] = {}
        for cid, articles in news_by_market.items():
            ctx = self.news_scanner.build_news_context(articles)
            if ctx:
                news_context_by_market[cid] = ctx

        # Check for breaking news and adjust cycle timer
        has_breaking = any(
            any(a.get("is_breaking") for a in articles)
            for articles in news_by_market.values()
        )
        if has_breaking:
            self.cycle_timer.signal_breaking_news()
            for cid in news_by_market:
                if any(a.get("is_breaking") for a in news_by_market[cid]):
                    self.ai.invalidate_cache(cid)
                    self.news_scanner.invalidate_cache(" ".join(market_keywords.get(cid, [])))

        # 9b. Check scout queue — inject pre-fetched sports data for matched markets
        scouted_markets = {}  # condition_id -> scout_entry (for marking as scouted after entry)
        esports_contexts = {}
        for m in prioritized:
            scout_entry = self.scout.match_market(m.question, m.slug)
            if scout_entry and scout_entry.get("sports_context"):
                scouted_markets[m.condition_id] = scout_entry
                esports_contexts[m.condition_id] = scout_entry["sports_context"]
                logger.info("Scout HIT: %s (pre-fetched sports data injected)", m.slug[:40])

        # 9c. Fetch sports/esports data for non-scouted markets
        data_sources_by_market: dict[str, list[str]] = {}  # condition_id -> list of source names
        odds_by_market: dict[str, dict] = {}  # condition_id -> odds dict (bookmaker_prob_a, etc.)
        line_movement_by_market: dict = {}
        for cid in scouted_markets:
            data_sources_by_market[cid] = ["scout", "espn"]

        for m in prioritized:
            if m.condition_id in esports_contexts:
                continue  # Already have pre-fetched data from scout
            parts = []
            sources: list[str] = []
            # Try ESPN first (traditional sports — free, no key)
            espn_ctx = self.sports.get_match_context(m.question, m.slug, m.tags)
            if espn_ctx:
                parts.append(espn_ctx)
                sources.append("espn")
                logger.info("ESPN data loaded for: %s", m.question[:50])
            else:
                # Try PandaScore (esports — needs API key)
                if self.esports.available:
                    panda_ctx = self.esports.get_match_context(m.question, m.tags)
                    if panda_ctx:
                        parts.append(panda_ctx)
                        sources.append("pandascore")
                        logger.info("Esports data loaded for: %s", m.question[:50])

                # Complementary sources: VLR (Valorant) + HLTV (CS2) run alongside PandaScore
                # Even if PandaScore returned data, these add ranking/tier info
                if self.vlr.available:
                    vlr_ctx = self.vlr.get_match_context(m.question, m.tags)
                    if vlr_ctx:
                        parts.append(vlr_ctx)
                        sources.append("vlr")
                        logger.info("VLR data loaded for: %s", m.question[:50])
                # HLTV disabled — Cloudflare blocks without proxy, PandaScore covers CS2
                # if self.hltv.available:
                #     hltv_ctx = self.hltv.get_match_context(m.question, m.tags)
                #     if hltv_ctx:
                #         parts.append(hltv_ctx)
                #         sources.append("hltv")
                #         logger.info("HLTV data loaded for: %s", m.question[:50])

            # Add bookmaker odds to AI context (uses quota sparingly — cached 1hr)
            # Skip Odds API for esports — no bookmaker coverage, wastes credits
            _esports_slugs = ("cs2", "csgo", "val", "valorant", "lol", "dota2", "rl", "cod")
            _slug_prefix = m.slug.split("-")[0].lower() if m.slug else ""
            _is_esports = _slug_prefix in _esports_slugs
            if self.odds_api.available and not _is_esports:
                odds = self.odds_api.get_bookmaker_odds(m.question, m.slug, m.tags)
                if odds:
                    parts.append(self.odds_api.build_odds_context(odds))
                    sources.append("odds_api")
                    odds_by_market[m.condition_id] = odds
                    logger.info("Bookmaker odds loaded: %s (%.0f%% vs %.0f%%, %d books)",
                                m.slug[:30], odds["bookmaker_prob_a"] * 100,
                                odds["bookmaker_prob_b"] * 100, odds["num_bookmakers"])
                    # Line movement disabled — costs 10 credits/call, minimal edge value

            if parts:
                esports_contexts[m.condition_id] = "\n".join(parts)
            data_sources_by_market[m.condition_id] = sources
        if esports_contexts:
            logger.info("Sports data fetched for %d/%d markets", len(esports_contexts), len(prioritized))

        # 9d. Data gate: skip AI for markets without SUFFICIENT data
        # Single source (just ESPN stats) rarely produces candidates — need 2+ sources
        # or at least news/odds which provide stronger signal than stats alone.
        _no_data_markets = []
        _has_data_markets = []
        _odds_available = self.odds_api.available
        _news_available = any(news_context_by_market.values())
        for m in prioritized:
            has_sports = m.condition_id in esports_contexts
            has_news = bool(news_context_by_market.get(m.condition_id))
            has_odds = m.condition_id in odds_by_market  # actual odds found for THIS market
            source_count = sum([has_sports, has_news, has_odds])
            # Must have odds OR sports data as primary source — news alone is not enough
            # News is a supporting factor (injuries, roster changes) not a standalone signal
            has_primary = has_odds or has_sports
            if has_primary:
                _has_data_markets.append(m)
            else:
                _no_data_markets.append(m)
                # Mark as analyzed so we don't retry next cycle
                self._analyzed_market_ids[m.condition_id] = time.time()

        if _no_data_markets:
            logger.info("Data gate: skipped %d markets with no data (saved AI calls)", len(_no_data_markets))
        _skipped_no_data = len(_no_data_markets)

        # Track which APIs are down for cycle report
        _dead_apis = []
        if not self.odds_api.available:
            _dead_apis.append("Odds API (quota exhausted)")
        try:
            _news_worked = any(news_context_by_market.values())
            if not _news_worked:
                if not self.news_scanner.tavily_key:
                    _dead_apis.append("Tavily (no key)")
                elif self.news_scanner._monthly_tavily >= 950:
                    _dead_apis.append("Tavily (monthly limit)")
                if self.news_scanner._daily_usage.get("newsapi", 0) >= 95:
                    _dead_apis.append("NewsAPI (daily limit)")
                if self.news_scanner._daily_usage.get("gnews", 0) >= 95:
                    _dead_apis.append("GNews (daily limit)")
                if not any([self.news_scanner.tavily_key,
                           self.news_scanner.newsapi_key,
                           self.news_scanner.gnews_key]):
                    _dead_apis.append("All news APIs (no keys)")
        except Exception:
            pass

        # 10. Analyze markets WITH data only
        prioritized = _has_data_markets
        self._set_status("running", f"Warren analyzing {len(prioritized)} markets")
        if prioritized:
            estimates = self.ai.analyze_batch(prioritized, "", esports_contexts,
                                              news_by_market=news_context_by_market)
        else:
            estimates = {}
            logger.info("No markets with data — skipping AI entirely")

        # 10a. Mark as analyzed (don't re-send to AI next cycle)
        for m in prioritized:
            self._analyzed_market_ids[m.condition_id] = time.time()
        # Advance eligible cache pointer so next cycle continues from where we left off
        self._eligible_pointer += len(prioritized)

        # 10b. Check budget alerts
        for alert in self.ai.check_budget_alerts():
            self.notifier.send(alert)
            logger.warning("Budget alert sent: %s", alert[:60])

        # 11. Evaluate all markets — collect candidates, then pick the best
        self._set_status("running", "Evaluating signals")
        signals_generated = False
        _CONF_SCORE = {"A": 4, "B+": 3, "B-": 2, "C": 1}
        _SKIP_CONFIDENCE = {"C", "", "?"}  # C confidence = skip
        _MAX_EDGE_BY_CONFIDENCE = {"C": 0.15, "B-": 0.35, "B+": 0.40}
        candidates = []  # List of (score, market, estimate, direction, edge, manip_check, mkt_sources, decision, adjusted_size, sanity)
        vs_candidates = []  # VS candidates collected from ignorance/sanity blocks

        # Fill-ratio scaling: adjust min_edge based on how full the portfolio is
        fill_ratio = self.portfolio.active_position_count / max(1, self.config.risk.max_positions)
        if self.config.edge.fill_ratio_scaling:
            effective_min_edge = scale_min_edge(
                self.config.edge.min_edge, fill_ratio,
                self.config.edge.fill_ratio_aggressive,
                self.config.edge.fill_ratio_selective)
        else:
            effective_min_edge = self.config.edge.min_edge

        for market, estimate in zip(prioritized, estimates):
            # Hard stop: budget exhausted → skip all remaining markets
            if estimate.reasoning_pro == "BUDGET_EXHAUSTED":
                logger.warning("Budget exhausted — skipping remaining markets")
                break
            # API error → skip this market
            if estimate.reasoning_pro == "API_ERROR":
                logger.warning("API error for %s — skipping", market.slug[:40])
                continue

            # Log ALL AI predictions for calibration
            self._log_prediction(market, estimate)

            # ESPN verification gate: confirm match status before entry
            # Polymarket endDate/event_live can be wrong — ESPN is ground truth
            _espn_info = self.sports.get_upcoming_match_info(
                market.question, market.slug, market.tags)
            if _espn_info:
                _espn_status = _espn_info.get("status", "")
                if _espn_status in ("in_progress", "completed"):
                    logger.info("ESPN says %s for %s — skipping entry",
                                _espn_status.upper(), market.slug[:40])
                    self.trade_log.log({
                        "market": market.slug, "action": "HOLD",
                        "question": market.question,
                        "ai_prob": estimate.ai_probability, "price": market.yes_price,
                        "edge": abs(estimate.ai_probability - market.yes_price),
                        "mode": self.config.mode.value,
                        "rejected": f"ESPN_{_espn_status.upper()}: match already {_espn_status} per ESPN",
                    })
                    continue
                # Backfill match_start_iso from ESPN if we got a better time
                if _espn_info.get("match_start_iso"):
                    if not getattr(market, 'match_start_iso', ''):
                        market.match_start_iso = _espn_info["match_start_iso"]

            # Skip live matches — our edge is pre-match analysis, not real-time reaction
            if (market.event_live if hasattr(market, 'event_live') else self._estimate_match_live(market.slug, market.question, market.end_date_iso)):
                logger.info("Skipping LIVE match (no pre-match edge): %s", market.slug[:40])
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "question": market.question,
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": abs(estimate.ai_probability - market.yes_price),
                    "mode": self.config.mode.value,
                    "rejected": "LIVE_MATCH: crowd reacts to live score, AI has no edge mid-match",
                })
                continue

            # Bookmaker confidence modifier: boost/drop confidence based on agreement
            if self.config.edge.bookmaker_confidence_boost:
                mkt_odds = odds_by_market.get(market.condition_id)
                if mkt_odds:
                    book_prob = mkt_odds["bookmaker_prob_a"]
                    ai_direction_yes = estimate.ai_probability > 0.5
                    book_direction_yes = book_prob > 0.5
                    if ai_direction_yes == book_direction_yes:
                        old_conf = estimate.confidence
                        estimate.confidence = boost_confidence(estimate.confidence, +1)
                        if estimate.confidence != old_conf:
                            logger.info("Bookmaker AGREES: %s | AI=%.0f%% Book=%.0f%% → confidence %s→%s",
                                        market.slug[:35], estimate.ai_probability * 100,
                                        book_prob * 100, old_conf, estimate.confidence)
                    else:
                        old_conf = estimate.confidence
                        estimate.confidence = boost_confidence(estimate.confidence, -1)
                        if estimate.confidence != old_conf:
                            logger.info("Bookmaker DISAGREES: %s | AI=%.0f%% Book=%.0f%% → confidence %s→%s",
                                        market.slug[:35], estimate.ai_probability * 100,
                                        book_prob * 100, old_conf, estimate.confidence)

            # Confidence gate: skip low (unreliable signals)
            if estimate.confidence in _SKIP_CONFIDENCE:
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "question": market.question,
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": abs(estimate.ai_probability - market.yes_price),
                    "mode": self.config.mode.value,
                    "rejected": f"LOW_CONFIDENCE: {estimate.confidence} — skipped",
                })
                continue

            # medium_low (B-) experiment: allow but require decent edge (≥10%)
            _is_medium_low = estimate.confidence == "B-"
            if _is_medium_low:
                raw_edge = abs(estimate.ai_probability - market.yes_price)
                if raw_edge < 0.10:
                    self.trade_log.log({
                        "market": market.slug, "action": "HOLD",
                        "question": market.question,
                        "ai_prob": estimate.ai_probability, "price": market.yes_price,
                        "edge": raw_edge, "mode": self.config.mode.value,
                        "rejected": f"MEDIUM_LOW_EDGE: {raw_edge:.1%} < 10% min for B- bets",
                    })
                    continue

            # Manipulation check
            market_articles = news_by_market.get(market.condition_id, [])
            news_source_count = self.manip_guard.count_unique_sources(market_articles)
            manip_check = self.manip_guard.check_market(
                question=market.question,
                description=market.description,
                liquidity=market.liquidity,
                news_source_count=news_source_count,
            )

            if not manip_check.safe:
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "question": market.question,
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": 0, "mode": self.config.mode.value,
                    "rejected": f"MANIPULATION: {manip_check.recommendation}",
                    "manip_flags": manip_check.flags,
                })
                continue

            # Track data sources
            mkt_sources = list(data_sources_by_market.get(market.condition_id, []))
            if news_by_market.get(market.condition_id):
                mkt_sources.append("news")
            mkt_sources.append("claude_sonnet")

            # Bookmaker-anchored probability (V3 Maximus)
            _mkt_odds_for_anchor = odds_by_market.get(market.condition_id)
            _anchor_book_prob = _mkt_odds_for_anchor.get("bookmaker_prob_a") if _mkt_odds_for_anchor else None
            _anchor_num_books = _mkt_odds_for_anchor.get("num_bookmakers", 0) if _mkt_odds_for_anchor else 0
            anchored = calculate_anchored_probability(
                ai_prob=estimate.ai_probability,
                bookmaker_prob=_anchor_book_prob,
                num_bookmakers=_anchor_num_books,
            )
            logger.info("ANCHOR_DEBUG: %s | ai_prob=%.3f book_prob=%s n_books=%d → anchored=%.3f method=%s",
                        market.slug[:35], estimate.ai_probability,
                        f"{_anchor_book_prob:.3f}" if _anchor_book_prob else "None",
                        _anchor_num_books, anchored.probability, anchored.method)
            _edge_threshold_adj = get_edge_threshold_adjustment(anchored)

            # Edge calculation — uses anchored probability + threshold adjustment
            direction, edge = calculate_edge(
                ai_prob=anchored.probability,
                market_yes_price=market.yes_price,
                min_edge=effective_min_edge,
                confidence=estimate.confidence,
                confidence_multipliers=self.config.edge.confidence_multipliers,
                spread=self.config.edge.default_spread,
                edge_threshold_adjustment=_edge_threshold_adj,
            )

            # Esports entry filter — two rules:
            # 1. AI > 65% → ALWAYS BUY_YES (override BUY_NO/HOLD). Exit rules protect us.
            # 2. AI < 50% + BUY_YES → block (don't bet on predicted loser)
            _esports_entry_tags = ("counter-strike", "dota-2", "league-of-legends", "valorant")
            _sport_tag = getattr(market, "sport_tag", "") or ""
            if _sport_tag in _esports_entry_tags:
                # Rule 1: AI confident winner → force BUY_YES regardless of edge direction
                if anchored.probability > 0.65 and direction in (Direction.BUY_NO, Direction.HOLD):
                    win_potential = 1.0 - market.yes_price  # profit if team wins
                    logger.info("ESPORTS_WINNER_OVERRIDE: %s | AI=%.0f%% > 65%% | mkt=%.0f¢ | win_pot=%.0f%% | was %s → BUY_YES",
                                market.slug[:40], anchored.probability * 100, market.yes_price * 100,
                                win_potential * 100, direction.value)
                    direction = Direction.BUY_YES
                    edge = win_potential  # use win potential as edge for sizing

                # Rule 2: AI says loser → don't buy YES
                elif direction == Direction.BUY_YES and anchored.probability < 0.50:
                    logger.info("Esports underdog skip: %s | AI=%.0f%% < 50%% — not betting on predicted loser",
                                market.slug[:40], anchored.probability * 100)
                    self.trade_log.log({
                        "market": market.slug, "action": "HOLD",
                        "question": market.question,
                        "ai_prob": estimate.ai_probability, "price": market.yes_price,
                        "edge": edge, "mode": self.config.mode.value,
                        "rejected": f"ESPORTS_UNDERDOG: AI={anchored.probability:.0%} < 50% — don't buy underdog YES",
                    })
                    continue

            # Consensus Entry: override HOLD if AI + market both ≥min_price same direction
            # Stop-loss asymmetry makes this EV+ even without market edge
            is_consensus = False
            entry_reason = ""
            if direction == Direction.HOLD:
                _ce = self.config.consensus_entry
                if _ce.enabled and estimate.confidence in ("A", "B+"):
                    _ai = estimate.ai_probability
                    _mp = market.yes_price
                    _cyes = _ai >= _ce.min_price and _mp >= _ce.min_price
                    _cno = (1 - _ai) >= _ce.min_price and (1 - _mp) >= _ce.min_price
                    _is_far_mkt = market.condition_id in self._far_market_ids
                    if (_cyes or _cno) and not _is_far_mkt:
                        _consensus_count = self.portfolio.count_by_entry_reason("consensus")
                        if _consensus_count < _ce.max_slots:
                            direction = Direction.BUY_YES if _cyes else Direction.BUY_NO
                            is_consensus = True
                            entry_reason = "consensus"
                            logger.info(
                                "CONSENSUS_OVERRIDE: %s | AI=%.0f%% mkt=%.0f%% conf=%s → %s (%d/%d slots)",
                                market.slug[:40], _ai * 100, _mp * 100,
                                estimate.confidence, direction.value,
                                _consensus_count + 1, _ce.max_slots,
                            )

            if direction == Direction.HOLD:
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "question": market.question,
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": edge, "mode": self.config.mode.value,
                    "manip_risk": manip_check.risk_level,
                    "data_sources": mkt_sources,
                })
                continue

            # Far markets need higher edge (8%+) — capital locked longer, must justify
            if market.condition_id in self._far_market_ids and edge < 0.08:
                logger.info("Far market edge too low (%.1f%% < 8%%): %s", edge * 100, market.slug[:40])
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "question": market.question,
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": edge, "mode": self.config.mode.value,
                    "rejected": f"FAR_LOW_EDGE: {edge*100:.1f}% < 8% threshold for >6h markets",
                    "data_sources": mkt_sources,
                })
                continue

            # Ignorance edge guard + ULTI rescue
            ulti_used = False
            original_ai_prob = estimate.ai_probability
            max_edge = _MAX_EDGE_BY_CONFIDENCE.get(estimate.confidence)
            blocked_by_ignorance = max_edge is not None and edge > max_edge

            if blocked_by_ignorance:
                logger.info("Ignorance edge blocked: %s | edge=%.1f%% conf=%s cap=%.0f%% — trying ULTI",
                            market.slug[:40], edge * 100, estimate.confidence, max_edge * 100)
                if estimate.confidence in ("C", "B-", "B+") and self.odds_api.available:
                    odds = self.odds_api.get_bookmaker_odds(market.question, market.slug, market.tags)
                    if odds:
                        book_prob = odds["bookmaker_prob_a"]
                        blended = 0.6 * book_prob + 0.4 * estimate.ai_probability
                        logger.info(
                            "ULTI RESCUE: %s | AI=%.0f%% Book=%.0f%% Blended=%.0f%% (%d bookmakers)",
                            market.slug[:35], estimate.ai_probability * 100, book_prob * 100,
                            blended * 100, odds["num_bookmakers"],
                        )
                        self.trade_log.log({
                            "market": market.slug, "action": "ULTI_RESCUE",
                            "trigger": "IGNORANCE_EDGE",
                            "ai_prob_original": original_ai_prob,
                            "bookmaker_prob": book_prob,
                            "blended_prob": blended,
                            "bookmakers": odds["num_bookmakers"],
                            "mode": self.config.mode.value,
                            "data_sources": mkt_sources,
                        })
                        estimate.ai_probability = round(blended, 3)
                        estimate.confidence = "B-"  # ULTI rescue = kurtarma, promotion değil
                        ulti_used = True
                        direction, edge = calculate_edge(
                            ai_prob=estimate.ai_probability,
                            market_yes_price=market.yes_price,
                            min_edge=effective_min_edge,
                            confidence=estimate.confidence,
                            confidence_multipliers=self.config.edge.confidence_multipliers,
                            spread=self.config.edge.default_spread,
                        )
                        if direction == Direction.HOLD:
                            self.trade_log.log({
                                "market": market.slug, "action": "HOLD",
                                "question": market.question,
                                "ai_prob": estimate.ai_probability, "price": market.yes_price,
                                "edge": edge, "mode": self.config.mode.value,
                                "rejected": "ULTI_RESCUE failed: still HOLD after blend",
                                "data_sources": mkt_sources,
                            })
                            continue
                        max_edge = _MAX_EDGE_BY_CONFIDENCE.get(estimate.confidence)
                        blocked_by_ignorance = max_edge is not None and edge > max_edge

                if blocked_by_ignorance:
                    block_msg = (f"IGNORANCE_EDGE: {estimate.confidence} confidence with "
                                 f"edge {edge:.1%} > cap {max_edge:.0%} — crowd likely knows more"
                                 + (" (ULTI tried)" if ulti_used else ""))
                    # Do NOT send to VS — ignorance edge means crowd knows more,
                    # buying cheap tokens as VS would repeat the same mistake
                    self.trade_log.log({
                        "market": market.slug, "action": "HOLD",
                        "question": market.question,
                        "ai_prob": estimate.ai_probability, "price": market.yes_price,
                        "edge": edge, "mode": self.config.mode.value,
                        "rejected": block_msg,
                        "data_sources": mkt_sources,
                    })
                    continue

            # Risk check
            signal = Signal(
                condition_id=market.condition_id,
                direction=direction,
                ai_probability=estimate.ai_probability,
                market_price=market.yes_price,
                edge=edge,
                confidence=estimate.confidence,
            )
            _cat = market.tags[0] if market.tags else ""
            _stag = market.sport_tag or ""
            corr_exposure = self.portfolio.correlated_exposure(_cat, sport_tag=_stag)
            league_count = self.portfolio.count_by_category(_cat, sport_tag=_stag)
            decision = self.risk.evaluate(
                signal, bankroll, self.portfolio.positions, corr_exposure,
                league_count=league_count, confidence=estimate.confidence,
            )

            if not decision.approved:
                self.trade_log.log({
                    "market": market.slug, "action": direction.value,
                    "edge": edge, "rejected": decision.reason, "mode": self.config.mode.value,
                    "reasoning_pro": estimate.reasoning_pro[:200],
                    "reasoning_con": estimate.reasoning_con[:200],
                    "question": market.question,
                    "data_sources": mkt_sources,
                })
                # If rejected due to full slots, save to stock for instant fill later
                if "max_positions" in decision.reason or "slot" in decision.reason.lower():
                    rank_score = edge * ({"A": 1.3, "B+": 1.1, "B-": 0.9}.get(estimate.confidence, 0.8))
                    self._candidate_stock.append({
                        "market": market, "estimate": estimate, "direction": direction,
                        "edge": edge, "manip_check": manip_check, "mkt_sources": mkt_sources,
                        "adjusted_size": decision.size_usdc or 25.0,
                        "score": rank_score, "stocked_at": time.time(),
                        "stocked_price": market.yes_price,
                    })
                    if len(self._candidate_stock) > 10:
                        self._candidate_stock.sort(key=lambda c: c["score"], reverse=True)
                        self._candidate_stock = self._candidate_stock[:10]
                    self._save_stock_to_disk()
                    logger.info("Slot-rejected → STOCKED: %s | edge=%.1f%% conf=%s",
                                market.slug[:40], edge * 100, estimate.confidence)
                continue

            # Adjust position size (medium_low capped at 1.5% of bankroll)
            adjusted_size = self.manip_guard.adjust_position_size(
                decision.size_usdc, manip_check
            )
            if _is_medium_low:
                adjusted_size = min(adjusted_size, self.portfolio.bankroll * 0.015)
            # Consensus: Kelly≈0 (no market edge), use fixed bet_pct instead
            if is_consensus:
                _ce = self.config.consensus_entry
                adjusted_size = min(_ce.bet_pct * bankroll, self.config.risk.max_single_bet_usdc)
            if adjusted_size < 5.0:
                self.trade_log.log({
                    "market": market.slug, "action": direction.value,
                    "edge": edge, "rejected": f"Manipulation risk reduced size below minimum: {manip_check.recommendation}",
                    "mode": self.config.mode.value,
                    "data_sources": mkt_sources,
                })
                continue

            # Sanity check + ULTI rescue
            # Determine if bookmakers side with market (against AI)
            mkt_odds = odds_by_market.get(market.condition_id)
            _book_count = mkt_odds["num_bookmakers"] if mkt_odds else 0
            _book_agrees_market = False
            if mkt_odds:
                book_fav_yes = mkt_odds["bookmaker_prob_a"] > 0.5
                market_fav_yes = market.yes_price > 0.5
                _book_agrees_market = (book_fav_yes == market_fav_yes)
            sanity = check_bet_sanity(
                question=market.question,
                direction=direction.value,
                ai_probability=estimate.ai_probability,
                market_price=market.yes_price,
                edge=edge,
                confidence=estimate.confidence,
                bookmaker_count=_book_count,
                bookmaker_agrees_with_market=_book_agrees_market,
            )
            if not sanity.ok:
                if not ulti_used and estimate.confidence in ("C", "B-", "B+") and self.odds_api.available:
                    logger.info("Sanity blocked: %s — %s — trying ULTI", market.slug[:40], sanity.reason)
                    odds = self.odds_api.get_bookmaker_odds(market.question, market.slug, market.tags)
                    if odds:
                        book_prob = odds["bookmaker_prob_a"]
                        blended = 0.6 * book_prob + 0.4 * original_ai_prob
                        logger.info(
                            "ULTI RESCUE: %s | AI=%.0f%% Book=%.0f%% Blended=%.0f%% (%d bookmakers)",
                            market.slug[:35], original_ai_prob * 100, book_prob * 100,
                            blended * 100, odds["num_bookmakers"],
                        )
                        self.trade_log.log({
                            "market": market.slug, "action": "ULTI_RESCUE",
                            "trigger": "SANITY",
                            "ai_prob_original": original_ai_prob,
                            "bookmaker_prob": book_prob,
                            "blended_prob": blended,
                            "bookmakers": odds["num_bookmakers"],
                            "mode": self.config.mode.value,
                            "data_sources": mkt_sources,
                        })
                        estimate.ai_probability = round(blended, 3)
                        estimate.confidence = "B-"  # ULTI rescue = kurtarma, promotion değil
                        ulti_used = True
                        direction, edge = calculate_edge(
                            ai_prob=estimate.ai_probability,
                            market_yes_price=market.yes_price,
                            min_edge=effective_min_edge,
                            confidence=estimate.confidence,
                            confidence_multipliers=self.config.edge.confidence_multipliers,
                            spread=self.config.edge.default_spread,
                        )
                        sanity = check_bet_sanity(
                            question=market.question,
                            direction=direction.value,
                            ai_probability=estimate.ai_probability,
                            market_price=market.yes_price,
                            edge=edge,
                            confidence=estimate.confidence,
                            bookmaker_count=_book_count,
                            bookmaker_agrees_with_market=_book_agrees_market,
                        )
                        if sanity.ok:
                            logger.info("ULTI RESCUED sanity: %s — proceeding", market.slug[:40])

                if not sanity.ok:
                    sanity_msg = f"SANITY: {sanity.reason}" + (" (ULTI tried)" if ulti_used else "")
                    # Collect VS candidate instead of executing immediately
                    vs_candidate = self._evaluate_vs_candidate(market, estimate, direction, mkt_sources, sanity_msg)
                    if vs_candidate:
                        vs_candidates.append(vs_candidate)
                        continue
                    self.trade_log.log({
                        "market": market.slug, "action": direction.value,
                        "edge": edge, "rejected": sanity_msg,
                        "mode": self.config.mode.value,
                        "data_sources": mkt_sources,
                    })
                    self.notifier.send(self.notifier.format_suspicious_bet(
                        market.question, direction.value, adjusted_size, edge, sanity.reason
                    ))
                    logger.warning("Sanity BLOCKED: %s — %s%s", market.slug[:40], sanity.reason,
                                   " (ULTI tried)" if ulti_used else "")
                    continue

            if sanity.suspicious:
                self.notifier.send(self.notifier.format_suspicious_bet(
                    market.question, direction.value, adjusted_size, edge, sanity.reason
                ))
                logger.info("Sanity WARNING (proceeding): %s — %s", market.slug[:40], sanity.reason)

            # Resolution proximity gate: don't enter if market resolves within 45 min
            # (30 min mandatory exit + 15 min buffer for execution)
            if market.end_date_iso:
                try:
                    _end = datetime.fromisoformat(market.end_date_iso.replace("Z", "+00:00"))
                    _mins_left = (_end - datetime.now(timezone.utc)).total_seconds() / 60
                    if 0 < _mins_left < 20:
                        logger.info("Skipped near-resolve entry (%.0f min left): %s", _mins_left, market.slug[:40])
                        self.trade_log.log({
                            "market": market.slug, "action": "HOLD",
                            "question": market.question, "edge": edge,
                            "rejected": f"NEAR_RESOLVE: {_mins_left:.0f} min left, min 20 min required",
                            "mode": self.config.mode.value,
                        })
                        continue
                except (ValueError, TypeError):
                    pass

            # ✓ Passed all checks — add to candidates
            # Time-weighted score: edge * confidence * (1 + time_bonus)
            # Nearby matches get a bonus but edge remains dominant factor
            remaining_hours = 168.0  # default 7 days if no end_date
            time_bonus = 0.0
            # Prefer match_start_iso (actual match time) over end_date_iso (settlement)
            _time_iso = getattr(market, 'match_start_iso', '') or market.end_date_iso
            if _time_iso:
                try:
                    end_dt = datetime.fromisoformat(_time_iso.replace("Z", "+00:00"))
                    delta_h = (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600
                    remaining_hours = max(1.0, min(168.0, delta_h))  # clamp 1h-168h
                    # Time bonus: closer matches get priority (capital turnover)
                    if delta_h <= 2:
                        time_bonus = 0.50
                    elif delta_h <= 6:
                        time_bonus = 0.25
                    elif delta_h <= 12:
                        time_bonus = 0.10
                except (ValueError, TypeError):
                    pass

            # Freshness bonus: newly listed markets have incomplete price discovery
            freshness_bonus = 0.0
            if market.accepting_orders_at:
                try:
                    opened = datetime.fromisoformat(market.accepting_orders_at.replace("Z", "+00:00"))
                    age_h = (datetime.now(timezone.utc) - opened).total_seconds() / 3600
                    if age_h <= 2:
                        freshness_bonus = 0.40  # brand new, crowd hasn't converged
                    elif age_h <= 12:
                        freshness_bonus = 0.20
                    elif age_h <= 24:
                        freshness_bonus = 0.10
                except (ValueError, TypeError):
                    pass

            # Price uncertainty bonus: prices near 0.50 have max edge potential
            # FAR/penny candidates exempt (they target extreme prices)
            price_mid = min(market.yes_price, market.no_price)  # closer to 0.50 = higher
            price_uncertainty_bonus = 0.0
            if price_mid >= 0.35:  # 0.35-0.50 range
                price_uncertainty_bonus = 0.15
            elif price_mid >= 0.20:  # 0.20-0.35 range
                price_uncertainty_bonus = 0.05

            # Favorite time gate: favorites lock capital until resolution — limit early entry.
            # Favorite = AI ≥ 65% AND confidence high/medium_high (hold-to-resolve).
            # Underdogs use edge TP so they can exit anytime, early entry is fine.
            # Time limits: price < 10¢ → 24h (cheap, high upside), otherwise → 12h.
            # If edge ≥ 15%, save to FAV stok (separate slots) instead of rejecting.
            effective_ai_for_side = estimate.ai_probability if direction == Direction.BUY_YES else (1 - estimate.ai_probability)
            entry_price = market.yes_price if direction == Direction.BUY_YES else market.no_price
            is_favorite = effective_ai_for_side >= 0.65 and estimate.confidence in ("A", "B+")
            if is_favorite:
                max_hours = 24 if entry_price < 0.10 else 12
                if remaining_hours > max_hours:
                    # Good edge → save to FAV stok (own slots, no AI cost later)
                    if edge >= self._FAV_MIN_EDGE:
                        fav_current = self.portfolio.count_by_entry_reason("fav_time_gate")
                        if fav_current < self._FAV_MAX_SLOTS:
                            fav_score = edge * _CONF_SCORE.get(estimate.confidence, 1)
                            fav_entry = {
                                "score": fav_score,
                                "remaining_hours": remaining_hours,
                                "market": market,
                                "estimate": estimate,
                                "direction": direction,
                                "edge": edge,
                                "manip_check": manip_check,
                                "mkt_sources": mkt_sources,
                                "stocked_at": time.time(),
                                "stocked_price": market.yes_price,
                            }
                            self._fav_stock.append(fav_entry)
                            logger.info("FAV_STOK: %s | AI=%.0f%% edge=%.0f%% hours=%.0f — saved to FAV stok (%d/%d)",
                                        market.slug[:40], effective_ai_for_side * 100, edge * 100,
                                        remaining_hours, fav_current + 1, self._FAV_MAX_SLOTS)
                            self.trade_log.log({
                                "market": market.slug, "action": "FAV_STOK",
                                "question": market.question,
                                "ai_prob": estimate.ai_probability, "price": market.yes_price,
                                "edge": edge, "mode": self.config.mode.value,
                                "rejected": f"FAV_STOK: AI={effective_ai_for_side:.0%} edge={edge:.0%} {remaining_hours:.0f}h away — saved to FAV slots",
                            })
                            continue
                    # Low edge or FAV slots full → normal reject
                    logger.info("FAV_TIME_GATE: %s | AI=%.0f%% conf=%s price=%.0f¢ hours=%.0f — favorite too far (max %dh)",
                                market.slug[:40], estimate.ai_probability * 100, estimate.confidence,
                                entry_price * 100, remaining_hours, max_hours)
                    self.trade_log.log({
                        "market": market.slug, "action": "HOLD",
                        "question": market.question,
                        "ai_prob": estimate.ai_probability, "price": market.yes_price,
                        "edge": edge, "mode": self.config.mode.value,
                        "rejected": f"FAV_TIME_GATE: favorite AI={effective_ai_for_side:.0%} conf={estimate.confidence} but {remaining_hours:.0f}h away (max {max_hours}h) edge={edge:.0%}<{self._FAV_MIN_EDGE:.0%}",
                    })
                    continue

            # Consensus: score by resolution edge (1 - entry_price) — lower price = higher upside
            _effective_edge = (1 - entry_price) if is_consensus else edge
            rank_score = _effective_edge * _CONF_SCORE.get(estimate.confidence, 1) * (1 + time_bonus + freshness_bonus + price_uncertainty_bonus)

            # FAR slot detection: far markets (>6h) with qualifying edge go to far_stock
            _is_far_market = market.condition_id in self._far_market_ids
            _is_penny = entry_price <= self.config.far.penny_max_price  # $0.01-$0.02
            _far_eligible = (
                self.config.far.enabled
                and (_is_far_market or _is_penny)
                and remaining_hours > self.config.far.min_hours_to_start
                and edge >= self.config.far.min_edge
                and effective_ai_for_side >= self.config.far.min_ai_probability
            )
            if _far_eligible:
                far_current = self.portfolio.count_by_entry_reason("far")
                if far_current < self.config.far.max_slots:
                    far_entry = {
                        "score": rank_score,
                        "remaining_hours": remaining_hours,
                        "market": market,
                        "estimate": estimate,
                        "direction": direction,
                        "edge": edge,
                        "manip_check": manip_check,
                        "mkt_sources": mkt_sources,
                        "decision": decision,
                        "adjusted_size": adjusted_size,
                        "sanity": sanity,
                        "stocked_at": time.time(),
                        "stocked_price": market.yes_price,
                        "is_penny": _is_penny,
                        "entry_price": entry_price,
                    }
                    self._far_stock.append(far_entry)
                    logger.info("FAR_CANDIDATE: %s | edge=%.0f%% AI=%.0f%% price=%.0f¢ hours=%.0f %s",
                                market.slug[:40], edge * 100, effective_ai_for_side * 100,
                                entry_price * 100, remaining_hours,
                                "PENNY" if _is_penny else "SWING")
                    self.trade_log.log({
                        "market": market.slug, "action": "FAR_CANDIDATE",
                        "question": market.question,
                        "ai_prob": estimate.ai_probability, "price": market.yes_price,
                        "edge": edge, "mode": self.config.mode.value,
                        "far_type": "penny" if _is_penny else "swing",
                        "entry_price_cents": round(entry_price * 100, 1),
                        "hours_to_start": round(remaining_hours, 1),
                    })
                    continue  # Don't add to normal candidates

            candidates.append({
                "score": rank_score,
                "remaining_hours": remaining_hours,
                "market": market,
                "estimate": estimate,
                "direction": direction,
                "edge": edge,
                "manip_check": manip_check,
                "mkt_sources": mkt_sources,
                "decision": decision,
                "adjusted_size": adjusted_size,
                "sanity": sanity,
                "entry_reason": entry_reason,
                "is_consensus": is_consensus,
            })
            logger.info("Candidate: %s | edge=%.1f%% conf=%s hours=%.0f tbonus=+%.0f%% score=%.4f",
                        market.slug[:40], edge * 100, estimate.confidence, remaining_hours, time_bonus * 100, rank_score)

        # 12. Rank candidates by score and execute the best ones
        vs_reserved = self.config.volatility_swing.reserved_slots
        normal_max = self.config.risk.max_positions - vs_reserved  # 15 normal slots
        current_normal_count = self.portfolio.normal_position_count
        normal_slots = max(0, normal_max - current_normal_count)
        available_slots = normal_slots
        # Sort: confidence tier first (A > B+ > B-), then score within tier
        _CONF_TIER = {"A": 3, "B+": 2, "B-": 1}
        candidates.sort(key=lambda c: (_CONF_TIER.get(c["estimate"].confidence, 0), c["score"]), reverse=True)
        self._last_candidate_count = len(candidates) + len(vs_candidates)

        if candidates:
            logger.info("Ranked %d candidates for %d normal slots (%d VS reserved)",
                        len(candidates), available_slots, vs_reserved)

        for c in candidates[:max(0, available_slots)]:
            market = c["market"]
            estimate = c["estimate"]
            direction = c["direction"]
            edge = c["edge"]
            manip_check = c["manip_check"]
            mkt_sources = c["mkt_sources"]
            adjusted_size = c["adjusted_size"]

            signals_generated = True

            # Devil's Advocate veto check for B- confidence trades (V3 Maximus)
            if estimate.confidence in ("B-",) and not self.ai.budget_exhausted:
                da_result = self.ai.devils_advocate(estimate, direction.value, market)
                if da_result.vetoed:
                    self.trade_log.log({
                        "market": market.slug, "action": "DA_VETO",
                        "question": market.question,
                        "ai_prob": estimate.ai_probability, "price": market.yes_price,
                        "edge": edge, "mode": self.config.mode.value,
                        "rejected": f"DEVILS_ADVOCATE_VETO: {'; '.join(da_result.counter_arguments[:2])}",
                        "da_cost": da_result.cost_usd,
                    })
                    logger.info("DA VETO: %s — %s", market.slug[:40], da_result.counter_arguments[0] if da_result.counter_arguments else "no reason")
                    continue

            # Determine edge source for tracking (V3 Maximus)
            _edge_source = "ai_anchored" if anchored.method == "anchored" else "ai_standard"
            if ulti_used:
                _edge_source = "ai_ulti_rescue"

            # Check if edge source is killed
            if self.edge_tracker.is_source_killed(_edge_source):
                logger.info("Edge source KILLED — skipping: %s (source=%s)", market.slug[:40], _edge_source)
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "question": market.question, "edge": edge,
                    "rejected": f"EDGE_SOURCE_KILLED: {_edge_source}",
                    "mode": self.config.mode.value,
                })
                continue

            # Execute
            token_id = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
            price = market.yes_price if direction == Direction.BUY_YES else market.no_price

            # CLOB orderbook depth check before entry
            liq_entry = check_entry_liquidity(token_id, adjusted_size)
            if not liq_entry["ok"]:
                logger.info("Entry BLOCKED by liquidity: %s — %s",
                            market.slug[:40], liq_entry.get("reason", ""))
                continue
            if liq_entry["recommended_size"] < adjusted_size:
                logger.info("Entry size reduced: $%.2f → $%.2f (liquidity impact) for %s",
                            adjusted_size, liq_entry["recommended_size"], market.slug[:40])
                adjusted_size = liq_entry["recommended_size"]

            result = self.executor.place_order(token_id, "BUY", price, adjusted_size)

            # Track
            shares = adjusted_size / price if price > 0 else 0
            is_scouted = market.condition_id in scouted_markets
            # Scouted hold-to-resolve guard:
            # 1. AI certainty must be ≥40% (underdog protection)
            # 2. Confidence must be B+ (medium_high) or higher
            # 3. AI certainty must be >60% for our side
            # B- or lower → don't hold to resolve, apply normal exit rules
            ai_certainty = max(estimate.ai_probability, 1 - estimate.ai_probability)
            if is_scouted and (ai_certainty < 0.40 or
                               estimate.confidence not in ("A", "B+") or
                               ai_certainty <= 0.60):
                logger.info("Scout downgraded: %s (AI=%.0f%%, conf=%s — needs B+ and >60%% certainty for hold-to-resolve)",
                            market.slug[:40], ai_certainty * 100, estimate.confidence)
                is_scouted = False
            # Get actual match start time from scout if available
            _scout_entry = self.scout.match_market(market.question, market.slug)
            _match_start = _scout_entry.get("match_time", "") if _scout_entry else ""
            # Fallback to Gamma event startTime if scout has no match time
            if not _match_start:
                _match_start = getattr(market, 'match_start_iso', '') or ""
            _num_games = _scout_entry.get("number_of_games", 0) if _scout_entry else 0
            _book_prob = 0.0
            _mkt_odds = odds_by_market.get(market.condition_id)
            if _mkt_odds:
                _book_prob = _mkt_odds.get("bookmaker_prob_a", 0.0)
            self.portfolio.add_position(
                market.condition_id, token_id, direction.value,
                market.yes_price, adjusted_size, shares, market.slug,
                market.tags[0] if market.tags else "",
                confidence=estimate.confidence,
                ai_probability=estimate.ai_probability,
                scouted=is_scouted,
                question=market.question,
                end_date_iso=market.end_date_iso,
                match_start_iso=_match_start,
                number_of_games=_num_games,
                sport_tag=market.sport_tag or "",
                event_id=market.event_id or "",
                bookmaker_prob=_book_prob,
                entry_reason=c.get("entry_reason", ""),
            )
            # Set live_on_clob immediately if match is already in progress
            pos = self.portfolio.positions.get(market.condition_id)
            if pos:
                pos.live_on_clob = self._estimate_match_live(
                    market.slug, market.question, market.end_date_iso,
                    match_start_iso=pos.match_start_iso)
                self.portfolio._save_positions()
            # Note: bankroll deduction happens inside add_position()
            self.last_cycle_has_live_clob = True  # Trigger fast polling immediately
            if is_scouted:
                scout_entry = scouted_markets[market.condition_id]
                self.scout.mark_entered(scout_entry["scout_key"])
                logger.info("Scout ENTERED: %s (pre-analyzed, hold-to-resolve)", market.slug[:40])
            self.trade_log.log({
                "market": market.slug, "action": direction.value,
                "size": adjusted_size, "price": price,
                "edge": edge, "confidence": estimate.confidence,
                "mode": self.config.mode.value, "status": result["status"],
                "manip_risk": manip_check.risk_level,
                "reasoning_pro": estimate.reasoning_pro[:200],
                "reasoning_con": estimate.reasoning_con[:200],
                "question": market.question,
                "ai_probability": estimate.ai_probability,
                "anchored_probability": anchored.probability,
                "anchor_method": anchored.method,
                "market_yes_price": market.yes_price,
                "end_date": market.end_date_iso,
                "data_sources": mkt_sources,
                "edge_source": _edge_source,
                "rank_score": c["score"],
                "sport_tag": market.sport_tag or "",
                "entry_reason": c.get("entry_reason", ""),
            })
            self._log_reasoning(
                market.question, direction.value, adjusted_size, price,
                edge, estimate, manip_check.risk_level,
            )
            self.notifier.send(
                f"\U0001f3af *TRADE* — Cycle #{self.cycle_count}\n\n"
                f"{market.question}\n"
                f"`{direction.value}` | `${adjusted_size:.0f}` @ `{price:.3f}`\n"
                f"Edge: `{edge:.1%}`"
            )
            self.bets_since_approval += 1
            self._check_bet_limit()

        # 13. Slot upgrade: swap weak positions for better candidates
        SPREAD_COST_PCT = 0.045  # 4.5% round-trip cost (realistic Polymarket spread + fees)
        UPGRADE_THRESHOLD = 2.0  # New candidate must score 2x better than weakest position
        min_edge_swap = self.config.edge.min_edge_swap  # 8.5% — must cover spread
        leftover = candidates[max(0, available_slots):]
        if leftover and self.portfolio.active_position_count >= self.config.risk.max_positions:
            # Filter leftover: candidate edge must exceed spread cost for swaps
            leftover = [c for c in leftover if c["edge"] >= min_edge_swap]

            # Score existing positions
            now = datetime.now(timezone.utc)
            swappable = []
            for cid, pos in self.portfolio.positions.items():
                # Never swap hold-to-resolve positions (AI >60% + high only)
                ai_certainty = max(pos.ai_probability, 1 - pos.ai_probability)
                if ai_certainty > 0.60 and pos.confidence == "A":
                    continue
                # Never swap positions at a loss — selling would realize unnecessary loss
                if pos.unrealized_pnl_pct < 0:
                    continue
                # Never swap positions with significant profit movement (let them play out)
                if pos.unrealized_pnl_pct > 0.05:
                    continue
                # Never swap positions resolving within 2 hours
                if pos.end_date_iso:
                    try:
                        end_dt = datetime.fromisoformat(pos.end_date_iso.replace("Z", "+00:00"))
                        if (end_dt - now).total_seconds() < 7200:
                            continue
                    except (ValueError, TypeError):
                        pass
                # Calculate position score using same time-weighted formula
                conf_score = _CONF_SCORE.get(pos.confidence, 1)
                pos_edge = abs(pos.ai_probability - pos.entry_price)
                pos_remaining_hours = 168.0
                if pos.end_date_iso:
                    try:
                        end_dt = datetime.fromisoformat(pos.end_date_iso.replace("Z", "+00:00"))
                        delta_h = (end_dt - now).total_seconds() / 3600
                        pos_remaining_hours = max(1.0, min(168.0, delta_h))
                    except (ValueError, TypeError):
                        pass
                pos_time_bonus = 0.0
                if pos_remaining_hours <= 2:
                    pos_time_bonus = 0.50
                elif pos_remaining_hours <= 6:
                    pos_time_bonus = 0.25
                elif pos_remaining_hours <= 12:
                    pos_time_bonus = 0.10
                pos_score = pos_edge * conf_score * (1 + pos_time_bonus)
                swappable.append((pos_score, cid, pos, pos_remaining_hours))

            if swappable:
                swappable.sort(key=lambda x: x[0])  # Weakest first
                for candidate in leftover[:]:
                    if not swappable:
                        break
                    weakest_score, weakest_cid, weakest_pos, weakest_hours = swappable[0]
                    # Time factor: penalize swapping near-resolution bets for distant ones
                    cand_hours = candidate["remaining_hours"]
                    time_ratio = weakest_hours / max(1.0, cand_hours)  # >1 if candidate resolves faster
                    adjusted_score = candidate["score"] * min(time_ratio, 2.0)  # Cap time bonus at 2x
                    # Only swap if candidate is significantly better (covers spread cost + time)
                    if adjusted_score >= weakest_score * UPGRADE_THRESHOLD:
                        # Exit the weak position (with spread cost simulation)
                        spread_loss = weakest_pos.size_usdc * SPREAD_COST_PCT
                        logger.info(
                            "SLOT UPGRADE: exit %s (score=%.3f) for %s (score=%.3f) | spread cost=$%.2f",
                            weakest_pos.slug[:30], weakest_score,
                            candidate["market"].slug[:30], candidate["score"], spread_loss,
                        )
                        # Apply spread cost to bankroll in dry-run
                        if not self.wallet:
                            self.portfolio.update_bankroll(
                                self.portfolio.bankroll - spread_loss
                            )
                        self._exit_position(weakest_cid, f"SLOT_UPGRADE: replaced by {candidate['market'].slug[:40]} (score {candidate['score']:.3f} vs {weakest_score:.3f})", cooldown_cycles=0)

                        # Enter the better candidate
                        market = candidate["market"]
                        estimate = candidate["estimate"]
                        direction = candidate["direction"]
                        edge = candidate["edge"]
                        adjusted_size = candidate["adjusted_size"]
                        manip_check = candidate["manip_check"]
                        mkt_sources = candidate["mkt_sources"]

                        token_id = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
                        price = market.yes_price if direction == Direction.BUY_YES else market.no_price
                        result = self.executor.place_order(token_id, "BUY", price, adjusted_size)

                        shares = adjusted_size / price if price > 0 else 0
                        is_scouted = market.condition_id in scouted_markets
                        # Apply same scouted guard: B+ or higher + >60% certainty required
                        if is_scouted:
                            _cert = max(estimate.ai_probability, 1 - estimate.ai_probability)
                            if (_cert < 0.40 or
                                    estimate.confidence not in ("A", "B+") or
                                    _cert <= 0.60):
                                is_scouted = False
                        self.portfolio.add_position(
                            market.condition_id, token_id, direction.value,
                            market.yes_price, adjusted_size, shares, market.slug,
                            market.tags[0] if market.tags else "",
                            confidence=estimate.confidence,
                            ai_probability=estimate.ai_probability,
                            scouted=is_scouted,
                            question=market.question,
                            end_date_iso=market.end_date_iso,
                            match_start_iso=getattr(market, 'match_start_iso', '') or "",
                            sport_tag=market.sport_tag or "",
                            event_id=market.event_id or "",
                        )
                        self.last_cycle_has_live_clob = True  # Trigger fast polling immediately
                        self.trade_log.log({
                            "market": market.slug, "action": direction.value,
                            "size": adjusted_size, "price": price,
                            "edge": edge, "confidence": estimate.confidence,
                            "mode": self.config.mode.value, "status": result["status"],
                            "manip_risk": manip_check.risk_level,
                            "question": market.question,
                            "ai_probability": estimate.ai_probability,
                            "slot_upgrade": True,
                            "replaced": weakest_pos.slug,
                            "spread_cost": round(spread_loss, 2),
                            "rank_score": candidate["score"],
                            "data_sources": mkt_sources,
                            "sport_tag": market.sport_tag or "",
                        })
                        self._log_reasoning(
                            market.question, direction.value, adjusted_size, price,
                            edge, estimate, manip_check.risk_level,
                        )
                        self.notifier.send(
                            f"\U0001f504 *SLOT UPGRADE* — Cycle #{self.cycle_count}\n\n"
                            f"OUT: {weakest_pos.slug[:40]}\n"
                            f"IN: {market.question}\n"
                            f"`{direction.value}` | `${adjusted_size:.0f}` @ `{price:.3f}`\n"
                            f"Edge: `{edge:.1%}` | Spread cost: `${spread_loss:.2f}`"
                        )
                        signals_generated = True
                        swappable.pop(0)
                        leftover.remove(candidate)
                        self.bets_since_approval += 1
                        self._check_bet_limit()
                    else:
                        break  # Remaining candidates are weaker (sorted by score desc)

        # 13b. Execute VS candidates (fill reserved VS slots)
        current_vs_count = sum(1 for p in self.portfolio.positions.values() if p.volatility_swing)
        vs_slots_available = vs_reserved - current_vs_count
        if vs_candidates and vs_slots_available > 0:
            vs_candidates.sort(key=lambda c: c["score"], reverse=True)
            for vc in vs_candidates[:vs_slots_available]:
                if self._execute_vs_entry(vc):
                    signals_generated = True

        # Save ranked-out candidates to stock (for instant fill when slots open)
        for c in leftover:
            c["stocked_at"] = time.time()
            c["stocked_price"] = c["market"].yes_price
            self._candidate_stock.append(c)
            self.trade_log.log({
                "market": c["market"].slug, "action": c["direction"].value,
                "edge": c["edge"], "rejected": f"STOCKED: score={c['score']:.3f}, waiting for slot",
                "confidence": c["estimate"].confidence,
                "mode": self.config.mode.value,
                "question": c["market"].question,
                "data_sources": c["mkt_sources"],
            })
            logger.info("Stocked: %s | score=%.3f (waiting for slot)", c["market"].slug[:40], c["score"])
        # Cap stock size (keep best 10, drop weakest)
        if len(self._candidate_stock) > 10:
            self._candidate_stock.sort(key=lambda c: c["score"], reverse=True)
            self._candidate_stock = self._candidate_stock[:10]

        # Persist stock to disk for dashboard
        self._save_stock_to_disk()

        self._log_cycle_summary(bankroll, "complete")

        # Telegram: hard cycle report
        pos_count = self.portfolio.active_position_count
        stock_count = len(self._candidate_stock) + len(self._fav_stock) + len(self._far_stock)
        vs_count = sum(1 for p in self.portfolio.positions.values() if p.volatility_swing)
        far_count = self.portfolio.count_by_entry_reason("far")
        fav_count = self.portfolio.count_by_entry_reason("fav_time_gate")
        normal_count = pos_count - vs_count - far_count - fav_count
        invested = sum(p.size_usdc for p in self.portfolio.positions.values())
        unrealized = self.portfolio.total_unrealized_pnl()
        pnl_sign = "+" if unrealized >= 0 else ""
        # Build dead API / data gate line for cycle report
        _data_gate_line = ""
        if _skipped_no_data > 0 or _dead_apis:
            parts = []
            if _skipped_no_data > 0:
                parts.append(f"Skipped `{_skipped_no_data}` markets (no data)")
            if _dead_apis:
                parts.append("Down: " + ", ".join(_dead_apis))
            _data_gate_line = "\n\u26a0\ufe0f " + " | ".join(parts) + "\n"

        self.notifier.send(
            f"\U0001f4ca *CYCLE #{self.cycle_count} REPORT*\n\n"
            f"Scanned: `{len(markets)}` markets\n"
            f"Candidates: `{len(candidates)}` | Stocked: `{len(leftover)}`\n"
            f"\n\U0001f3af Positions: `{pos_count}` (Normal:{normal_count} VS:{vs_count} FAR:{far_count} FAV:{fav_count})\n"
            f"Stock: `{stock_count}` (N:{len(self._candidate_stock)} FAV:{len(self._fav_stock)} FAR:{len(self._far_stock)})\n"
            f"\n\U0001f4b0 Invested: `${invested:.2f}` | PnL: `{pnl_sign}${unrealized:.2f}`\n"
            f"\U0001f4b8 AI: `${self.ai._sprint_cost_usd - self._cycle_ai_cost_start:.4f}` cycle | `${self.ai._sprint_cost_usd:.2f}` / `${self.ai.config.sprint_budget_usd:.2f}` sprint"
            f"{_data_gate_line}"
        )

        # Check if enough data for self-improvement
        self._check_self_improve_ready()

    def _is_match_too_far(self, market, max_elapsed: float = 0.30) -> bool:
        """Return True if match has progressed past max_elapsed (default 30%).

        Stock entries should only happen in the first 30% of a match.
        Returns False (allow entry) if no match timing data is available.
        """
        msi = getattr(market, 'match_start_iso', '')
        if not msi:
            return False
        try:
            from datetime import datetime, timezone
            from src.match_exit import get_game_duration
            start_dt = datetime.fromisoformat(msi.replace("Z", "+00:00"))
            elapsed_min = (datetime.now(timezone.utc) - start_dt).total_seconds() / 60
            duration = get_game_duration(market.slug, getattr(market, 'number_of_games', 0),
                                         getattr(market, 'sport_tag', ''))
            elapsed_pct = elapsed_min / duration if duration > 0 else 0
            if elapsed_pct > max_elapsed:
                logger.info("Stock SKIP (match %d%% done > %d%% max): %s",
                            int(elapsed_pct * 100), int(max_elapsed * 100), market.slug[:40])
                return True
        except (ValueError, TypeError):
            pass
        return False

    def _fill_from_stock(self) -> None:
        """Fill open slots from pre-analyzed candidate stock. No AI call needed."""
        if not self._candidate_stock:
            return

        vs_reserved = self.config.volatility_swing.reserved_slots
        normal_max = self.config.risk.max_positions - vs_reserved
        current_normal_count = self.portfolio.normal_position_count
        available_slots = max(0, normal_max - current_normal_count)
        if available_slots == 0:
            return

        now = time.time()
        used = []
        stale = []
        expired = []
        filled = 0

        # Sort stock by score (best first)
        self._candidate_stock.sort(key=lambda c: c["score"], reverse=True)

        for c in self._candidate_stock[:]:
            if filled >= available_slots:
                break

            market = c["market"]
            age_min = (now - c["stocked_at"]) / 60

            # Expired: >60 min old or market already in portfolio/exited
            if age_min > 60:
                expired.append(c)
                self._candidate_stock.remove(c)
                continue
            if market.condition_id in self.portfolio.positions:
                self._candidate_stock.remove(c)
                continue
            if self.blacklist.is_blocked(market.condition_id, self.cycle_count):
                self._candidate_stock.remove(c)
                continue
            if self._exit_cooldowns.get(market.condition_id, 0) > self.cycle_count:
                self._candidate_stock.remove(c)
                continue

            # Match progress guard: only enter in first 30% of match
            if self._is_match_too_far(market, max_elapsed=0.30):
                self._candidate_stock.remove(c)
                continue

            # Freshness check: get current price from CLOB
            current_price = self._get_current_price(market)
            if current_price is not None:
                price_move = abs(current_price - c["stocked_price"])
                if price_move > 0.05:
                    stale.append(c)
                    self._candidate_stock.remove(c)
                    # Remove from analyzed cache so AI re-evaluates next cycle
                    self._analyzed_market_ids.pop(market.condition_id, None)
                    logger.info("Stock STALE → re-queue: %s | price moved %.1f%% (%.3f→%.3f)",
                                market.slug[:40], price_move * 100,
                                c["stocked_price"], current_price)
                    continue
                # Update market price for execution
                market.yes_price = current_price
                market.no_price = 1 - current_price

                # Recalculate raw edge with current price (#8b)
                _ai_prob = c["estimate"].ai_probability
                _dir = c["direction"]
                _new_edge = _ai_prob - current_price if _dir == Direction.BUY_YES else current_price - _ai_prob
                _min_edge = self.config.risk.min_edge
                if _new_edge < _min_edge * 0.5:
                    stale.append(c)
                    self._candidate_stock.remove(c)
                    self._analyzed_market_ids.pop(market.condition_id, None)
                    logger.info("Stock edge degraded → removed: %s | edge=%.1f%% min=%.1f%%",
                                market.slug[:40], _new_edge * 100, _min_edge * 100)
                    continue
                c["edge"] = _new_edge  # Keep score current

            # Execute from stock
            direction = c["direction"]
            estimate = c["estimate"]
            edge = c["edge"]
            adjusted_size = c["adjusted_size"]
            manip_check = c["manip_check"]
            mkt_sources = c["mkt_sources"]

            token_id = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
            price = market.yes_price if direction == Direction.BUY_YES else market.no_price
            result = self.executor.place_order(token_id, "BUY", price, adjusted_size)

            shares = adjusted_size / price if price > 0 else 0
            self.portfolio.add_position(
                market.condition_id, token_id, direction.value,
                market.yes_price, adjusted_size, shares, market.slug,
                market.tags[0] if market.tags else "",
                confidence=estimate.confidence,
                ai_probability=estimate.ai_probability,
                question=market.question,
                end_date_iso=market.end_date_iso,
                match_start_iso=getattr(market, 'match_start_iso', '') or "",
                sport_tag=market.sport_tag or "",
                event_id=market.event_id or "",
            )
            self.trade_log.log({
                "market": market.slug, "action": direction.value,
                "size": adjusted_size, "price": price,
                "edge": edge, "confidence": estimate.confidence,
                "mode": self.config.mode.value, "status": result["status"],
                "question": market.question,
                "ai_probability": estimate.ai_probability,
                "from_stock": True, "stock_age_min": round(age_min, 1),
                "data_sources": mkt_sources,
            })
            self._log_reasoning(
                market.question, direction.value, adjusted_size, price,
                edge, estimate, manip_check.risk_level,
            )
            self.notifier.send(
                f"\U0001f4e6 *FROM STOCK* — no AI cost\n\n"
                f"{market.question}\n"
                f"`{direction.value}` | `${adjusted_size:.0f}` @ `{price:.3f}`\n"
                f"Edge: `{edge:.1%}` | Age: `{age_min:.0f}min`"
            )
            used.append(c)
            self._candidate_stock.remove(c)
            filled += 1
            self.bets_since_approval += 1

        # Update stats
        self._stock_stats["used"] += len(used)
        self._stock_stats["stale"] += len(stale)
        self._stock_stats["expired"] += len(expired)

        if used or stale or expired:
            logger.info("Stock: %d filled, %d stale, %d expired, %d remaining | totals: %s",
                        len(used), len(stale), len(expired),
                        len(self._candidate_stock), self._stock_stats)

    def _try_demote_to_stock(self, pos, reason: str) -> bool:
        """Demote an exited position back to candidate stock if its score beats the worst stock item.

        Returns True if demoted, False if discarded.
        Only called for exits that are NOT resolved_* or far_penny*.
        """
        # Mutex: don't stock if already in re-entry pool
        if pos.condition_id in self.reentry_pool.candidates:
            logger.info("Exit skip stock (already in re-entry pool): %s", pos.slug[:40])
            return False

        # Mutex: don't stock if already in stock
        if any(c["market"].condition_id == pos.condition_id for c in self._candidate_stock):
            return False

        # Compute score the same way as slot-rejected candidates
        edge = abs(pos.ai_probability - pos.current_price)
        conf_score = {"A": 1.3, "B+": 1.1, "B-": 0.9}.get(pos.confidence, 0.8)
        score = edge * conf_score

        # Build minimal MarketData from position fields
        is_yes = pos.direction == "BUY_YES"
        market = MarketData(
            condition_id=pos.condition_id,
            question=getattr(pos, "question", ""),
            yes_price=pos.current_price if is_yes else 1 - pos.current_price,
            no_price=1 - pos.current_price if is_yes else pos.current_price,
            yes_token_id=pos.token_id if is_yes else "",
            no_token_id=pos.token_id if not is_yes else "",
            slug=pos.slug,
            tags=[pos.category] if pos.category else [],
            end_date_iso=getattr(pos, "end_date_iso", ""),
            event_id=getattr(pos, "event_id", "") or "",
            sport_tag=getattr(pos, "sport_tag", ""),
            match_start_iso=getattr(pos, "match_start_iso", ""),
        )

        estimate = AIEstimate(
            ai_probability=pos.ai_probability,
            confidence=pos.confidence,
            reasoning_pro="demoted_from_position",
            reasoning_con="",
        )

        direction = Direction.BUY_YES if is_yes else Direction.BUY_NO

        # Stub manipulation check (already validated at entry)
        from src.manipulation_guard import ManipulationCheck
        manip_stub = ManipulationCheck(safe=True, risk_level="low", flags=[], recommendation="ok")

        stock_item = {
            "market": market, "estimate": estimate, "direction": direction,
            "edge": edge, "manip_check": manip_stub, "mkt_sources": [],
            "adjusted_size": min(25.0, self.portfolio.bankroll * 0.02),
            "score": score, "stocked_at": time.time(),
            "stocked_price": market.yes_price,
        }

        # Stock not full → just add
        if len(self._candidate_stock) < 10:
            self._candidate_stock.append(stock_item)
            self._save_stock_to_disk()
            logger.info("Exit DEMOTED to stock: %s | score=%.3f reason=%s",
                        pos.slug[:40], score, reason)
            return True

        # Stock full → compare with worst
        worst = min(self._candidate_stock, key=lambda c: c["score"])
        if score > worst["score"]:
            self._candidate_stock.remove(worst)
            self._candidate_stock.append(stock_item)
            self._save_stock_to_disk()
            logger.info("Exit DEMOTED to stock (replaced %s): %s | score=%.3f > %.3f",
                        worst["market"].slug[:30], pos.slug[:30], score, worst["score"])
            return True

        logger.info("Exit DISCARDED (score too low for stock): %s | score=%.3f < worst=%.3f",
                    pos.slug[:40], score, worst["score"])
        return False

    def _fill_from_fav_stock(self) -> None:
        """Execute FAV stok candidates into their dedicated slots (no AI cost)."""
        if not self._fav_stock:
            return

        fav_current = self.portfolio.count_by_entry_reason("fav_time_gate")
        available = self._FAV_MAX_SLOTS - fav_current
        if available <= 0:
            return

        now = time.time()
        self._fav_stock.sort(key=lambda c: c["score"], reverse=True)
        filled = 0

        for c in self._fav_stock[:]:
            if filled >= available:
                break

            market = c["market"]
            age_min = (now - c["stocked_at"]) / 60

            # Expire after 4 hours (FAV candidates are far-out, longer TTL than normal stock)
            if age_min > 240:
                self._fav_stock.remove(c)
                continue
            if market.condition_id in self.portfolio.positions:
                self._fav_stock.remove(c)
                continue
            if self.blacklist.is_blocked(market.condition_id, self.cycle_count):
                self._fav_stock.remove(c)
                continue

            # Match progress guard: only enter in first 30% of match
            if self._is_match_too_far(market, max_elapsed=0.30):
                self._fav_stock.remove(c)
                continue

            # Freshness: check current price hasn't moved too much
            current_price = self._get_current_price(market)
            if current_price is not None:
                price_move = abs(current_price - c["stocked_price"])
                if price_move > 0.08:  # 8% tolerance (wider than normal stock)
                    logger.info("FAV stok STALE: %s | price moved %.1f%%", market.slug[:40], price_move * 100)
                    self._fav_stock.remove(c)
                    continue
                market.yes_price = current_price
                market.no_price = 1 - current_price

            direction = c["direction"]
            estimate = c["estimate"]
            edge = c["edge"]
            manip_check = c["manip_check"]
            mkt_sources = c["mkt_sources"]

            # Position sizing: normal sizing (not B- reduced)
            adjusted_size = self.portfolio.bankroll * 0.05
            adjusted_size = min(adjusted_size, self.portfolio.bankroll * 0.10)

            token_id = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
            price = market.yes_price if direction == Direction.BUY_YES else market.no_price
            result = self.executor.place_order(token_id, "BUY", price, adjusted_size)

            shares = adjusted_size / price if price > 0 else 0
            self.portfolio.add_position(
                market.condition_id, token_id, direction.value,
                market.yes_price, adjusted_size, shares, market.slug,
                market.tags[0] if market.tags else "",
                confidence=estimate.confidence,
                ai_probability=estimate.ai_probability,
                question=market.question,
                end_date_iso=market.end_date_iso,
                match_start_iso=getattr(market, 'match_start_iso', '') or "",
                entry_reason="fav_time_gate",
                sport_tag=market.sport_tag or "",
                event_id=market.event_id or "",
            )
            self.trade_log.log({
                "market": market.slug, "action": direction.value,
                "size": adjusted_size, "price": price,
                "edge": edge, "confidence": estimate.confidence,
                "mode": self.config.mode.value, "status": result["status"],
                "question": market.question,
                "ai_probability": estimate.ai_probability,
                "from_fav_stock": True, "stock_age_min": round(age_min, 1),
                "data_sources": mkt_sources,
                "sport_tag": market.sport_tag or "",
            })
            self.notifier.send(
                f"\u2b50 *FAV EARLY ENTRY* \u2014 no AI cost\n\n"
                f"{market.question}\n"
                f"`{direction.value}` | `${adjusted_size:.0f}` @ `{price:.3f}`\n"
                f"Edge: `{edge:.1%}` | Conf: `{estimate.confidence}` | Age: `{age_min:.0f}min`"
            )
            logger.info("FAV ENTRY: %s | %s | edge=%.0f%% | conf=%s",
                        market.slug[:40], direction.value, edge * 100, estimate.confidence)

            self._fav_stock.remove(c)
            filled += 1

        # Cap FAV stock size
        if len(self._fav_stock) > 5:
            self._fav_stock.sort(key=lambda c: c["score"], reverse=True)
            self._fav_stock = self._fav_stock[:5]

    def _fill_from_far_stock(self) -> None:
        """Execute FAR stock candidates into dedicated FAR slots (swing trade + penny alpha)."""
        if not self._far_stock or not self.config.far.enabled:
            return

        far_current = self.portfolio.count_by_entry_reason("far")
        available = self.config.far.max_slots - far_current
        if available <= 0:
            return

        now = time.time()
        self._far_stock.sort(key=lambda c: c["score"], reverse=True)
        filled = 0

        for c in self._far_stock[:]:
            if filled >= available:
                break

            market = c["market"]
            age_min = (now - c["stocked_at"]) / 60

            # Expire after 6 hours (FAR candidates are distant, long TTL)
            if age_min > 360:
                self._far_stock.remove(c)
                continue
            if market.condition_id in self.portfolio.positions:
                self._far_stock.remove(c)
                continue
            if self.blacklist.is_blocked(market.condition_id, self.cycle_count):
                self._far_stock.remove(c)
                continue

            # Match progress guard: only enter in first 30% of match
            if self._is_match_too_far(market, max_elapsed=0.30):
                self._far_stock.remove(c)
                continue

            # Freshness: check current price
            current_price = self._get_current_price(market)
            if current_price is not None:
                price_move = abs(current_price - c["stocked_price"])
                if price_move > 0.10:  # 10% tolerance (wide — FAR markets are volatile)
                    logger.info("FAR stock STALE: %s | price moved %.1f%%", market.slug[:40], price_move * 100)
                    self._far_stock.remove(c)
                    continue
                market.yes_price = current_price
                market.no_price = 1 - current_price

            direction = c["direction"]
            estimate = c["estimate"]
            edge = c["edge"]
            is_penny = c.get("is_penny", False)
            entry_price = c.get("entry_price", market.yes_price if direction == Direction.BUY_YES else market.no_price)

            # Position sizing: penny gets penny_bet_pct, swing gets bet_pct
            if is_penny:
                adjusted_size = self.portfolio.bankroll * self.config.far.penny_bet_pct
            else:
                adjusted_size = self.portfolio.bankroll * self.config.far.bet_pct
            adjusted_size = min(adjusted_size, self.config.risk.max_single_bet_usdc)

            # Correlation cap
            match_key = extract_match_key(market.slug)
            adjusted_size = apply_correlation_cap(
                adjusted_size, match_key,
                [{"slug": p.slug, "size_usdc": p.size_usdc, "direction": p.direction}
                 for p in self.portfolio.positions.values()],
                self.portfolio.bankroll,
            )
            if adjusted_size < 2.0:
                self._far_stock.remove(c)
                continue

            token_id = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
            price = market.yes_price if direction == Direction.BUY_YES else market.no_price
            result = self.executor.place_order(token_id, "BUY", price, adjusted_size)

            shares = adjusted_size / price if price > 0 else 0
            far_type = "penny" if is_penny else "swing"
            self.portfolio.add_position(
                market.condition_id, token_id, direction.value,
                market.yes_price, adjusted_size, shares, market.slug,
                market.tags[0] if market.tags else "",
                confidence=estimate.confidence,
                ai_probability=estimate.ai_probability,
                question=market.question,
                end_date_iso=market.end_date_iso,
                match_start_iso=getattr(market, 'match_start_iso', '') or "",
                entry_reason="far",
                sport_tag=market.sport_tag or "",
                event_id=market.event_id or "",
            )
            self.trade_log.log({
                "market": market.slug, "action": direction.value,
                "size": adjusted_size, "price": price,
                "edge": edge, "confidence": estimate.confidence,
                "mode": self.config.mode.value, "status": result["status"],
                "question": market.question,
                "ai_probability": estimate.ai_probability,
                "far_type": far_type, "is_penny": is_penny,
                "entry_price_cents": round(entry_price * 100, 1),
                "from_far_stock": True, "stock_age_min": round(age_min, 1),
                "sport_tag": market.sport_tag or "",
            })
            emoji = "\U0001f4b0" if is_penny else "\U0001f30d"
            self.notifier.send(
                f"{emoji} *FAR {'PENNY' if is_penny else 'SWING'}* \u2014 Cycle #{self.cycle_count}\n\n"
                f"{market.question}\n"
                f"`{direction.value}` | `${adjusted_size:.0f}` @ `{price:.3f}`\n"
                f"Edge: `{edge:.1%}` | Entry: `{entry_price*100:.0f}\u00a2` | Type: `{far_type}`"
            )
            logger.info("FAR ENTRY [%s]: %s | %s | edge=%.0f%% @ %.0f\u00a2",
                        far_type, market.slug[:40], direction.value, edge * 100, entry_price * 100)

            self._far_stock.remove(c)
            filled += 1

        # Cap FAR stock
        if len(self._far_stock) > 5:
            self._far_stock.sort(key=lambda c: c["score"], reverse=True)
            self._far_stock = self._far_stock[:5]

    def _save_stock_to_disk(self) -> None:
        """Persist all stock pipelines to disk for dashboard visibility."""
        try:
            stock_data = []
            for stock_type, stock_list in [
                ("normal", self._candidate_stock),
                ("fav", self._fav_stock),
                ("far", self._far_stock),
            ]:
                for c in stock_list:
                    m = c.get("market")
                    estimate = c.get("estimate")
                    direction = c.get("direction", "")
                    stock_data.append({
                        "slug": getattr(m, "slug", "") if m else "",
                        "question": getattr(m, "question", "") if m else "",
                        "score": c.get("score", 0),
                        "edge": c.get("edge", 0),
                        "confidence": getattr(estimate, "confidence", "") if estimate else "",
                        "ai_probability": getattr(estimate, "ai_probability", 0) if estimate else 0,
                        "direction": direction.value if hasattr(direction, "value") else str(direction),
                        "stocked_at": c.get("stocked_at", 0),
                        "stocked_price": c.get("stocked_price", 0),
                        "stock_type": stock_type,
                    })
            Path("logs/candidate_stock.json").write_text(
                json.dumps(stock_data), encoding="utf-8"
            )
        except Exception as e:
            logger.debug("Failed to save stock: %s", e)

    def _check_live_dips(self) -> None:
        """Scan for live-dip entry opportunities (rule-based, no AI)."""
        try:
            markets = self.scanner.fetch()
            if not markets:
                return

            result = find_live_dip_candidates(
                markets=markets,
                portfolio_positions=self.portfolio.positions,
                exited_markets=self._exited_markets,
                get_clob_midpoint=self._get_clob_midpoint,
                max_concurrent=2,
                min_drop_pct=0.10,
            )
            candidates = result["candidates"]
            self._toxic_markets = result.get("toxic_markets", set())

            for c in candidates:
                # Fixed bet size — no Kelly (no AI probability)
                bet_size = min(25.0, self.portfolio.bankroll * 0.05)
                if bet_size < 5:
                    logger.info("Live dip skip: bankroll too low for %s", c.slug[:40])
                    continue

                # Find the matching market object for token IDs
                market = None
                for m in markets:
                    if m.condition_id == c.condition_id:
                        market = m
                        break
                if not market:
                    continue

                token_id = market.yes_token_id if c.direction == "BUY_YES" else market.no_token_id
                price = c.current_price if c.direction == "BUY_YES" else (1 - c.current_price)

                result = self.executor.place_order(token_id, "BUY", price, bet_size)
                if result.get("status") == "error":
                    logger.warning("Live dip order failed for %s: %s", market.slug[:40], result.get("reason", ""))
                    continue
                shares = bet_size / price if price > 0 else 0

                # Look up pre-match AI prediction from trade log
                prior_ai_prob = 0.0
                prior_conf = "B-"
                for prev in reversed(self.trade_log.read_recent(200)):
                    if prev.get("market") == market.slug and prev.get("ai_prob", 0) > 0:
                        prior_ai_prob = prev["ai_prob"]
                        prior_conf = prev.get("confidence", "B-")
                        logger.info("Live dip: reusing pre-match AI pred for %s: %.0f%% (%s)",
                                    market.slug[:35], prior_ai_prob * 100, prior_conf)
                        break

                self.portfolio.add_position(
                    market.condition_id, token_id, c.direction,
                    market.yes_price, bet_size, shares, market.slug,
                    market.tags[0] if market.tags else "",
                    confidence=prior_conf if prior_ai_prob > 0 else "C",
                    ai_probability=prior_ai_prob,
                    question=market.question,
                    end_date_iso=market.end_date_iso,
                    match_start_iso=getattr(market, 'match_start_iso', '') or "",
                    entry_reason="live_dip",
                    sport_tag=market.sport_tag or "",
                    event_id=market.event_id or "",
                )

                self.trade_log.log({
                    "market": market.slug, "action": c.direction,
                    "size": bet_size, "price": price,
                    "edge": 0, "confidence": "live_dip",
                    "mode": self.config.mode.value, "status": result["status"],
                    "question": market.question,
                    "live_dip": True,
                    "pre_match_price": c.pre_match_price,
                    "drop_pct": c.drop_pct,
                    "score_summary": c.score_summary,
                    "sport_tag": market.sport_tag or "",
                })

                self.notifier.send(
                    f"\U0001f4c9 *LIVE DIP ENTRY* — no AI cost\n\n"
                    f"{market.question}\n"
                    f"`{c.direction}` | `${bet_size:.0f}` @ `{price:.3f}`\n"
                    f"Drop: `{c.drop_pct:.0%}` from `{c.pre_match_price:.3f}`\n"
                    f"Score: {c.score_summary}"
                )

                logger.info("LIVE DIP ENTRY: %s | %s | drop=%.0f%% | %s",
                            market.slug[:40], c.direction, c.drop_pct * 100, c.score_summary)

        except Exception as e:
            logger.warning("Live dip check error: %s", e, exc_info=True)

    def _check_bond_candidates(self) -> None:
        """Scan for bond farming opportunities — near-certain markets (rule-based, no AI)."""
        try:
            markets = self.scanner.fetch()
            if not markets:
                return

            # Count active bond positions
            bond_count = sum(
                1 for p in self.portfolio.positions.values()
                if getattr(p, 'entry_reason', '') == 'bond'
            )
            bond_exposure = sum(
                p.size_usdc for p in self.portfolio.positions.values()
                if getattr(p, 'entry_reason', '') == 'bond'
            )

            bf = self.config.bond_farming
            candidates = scan_bond_candidates(
                markets,
                max_resolution_days=bf.max_days_to_resolution,
            )
            for bond in candidates:
                # Global position limit
                if len(self.portfolio.positions) >= self.config.risk.max_positions:
                    break
                # Skip if already in this market
                if bond.condition_id in self.portfolio.positions:
                    continue
                if self.blacklist.is_blocked(bond.condition_id, self.cycle_count):
                    continue

                bet_size = size_bond_position(
                    bankroll=self.portfolio.bankroll,
                    candidate=bond,
                    current_bond_exposure=bond_exposure,
                    current_bond_count=bond_count,
                    bet_pct=bf.bet_pct,
                    max_total_pct=bf.max_total_bond_pct,
                )
                if bet_size < 5:
                    continue

                # Correlation cap — bond dahil (strateji-agnostik)
                _stag = getattr(bond, 'sport_tag', '') or ''
                if not _stag:
                    # Try to find sport_tag from market list
                    _m = next((m for m in markets if m.condition_id == bond.condition_id), None)
                    _stag = getattr(_m, 'sport_tag', '') or '' if _m else ''
                if _stag:
                    corr_exp = self.portfolio.correlated_exposure("", sport_tag=_stag)
                    if corr_exp >= self.config.risk.correlation_cap_pct:
                        logger.info("Bond skip: correlation cap for %s (%.0f%%)", _stag, corr_exp * 100)
                        continue

                # Find market object for token IDs
                market = next((m for m in markets if m.condition_id == bond.condition_id), None)
                if not market:
                    continue

                token_id = market.yes_token_id  # Bonds are always BUY_YES (price near 1.0)
                price = bond.yes_price

                result = self.executor.place_order(token_id, "BUY", price, bet_size)
                if result.get("status") == "error":
                    logger.warning("Bond order failed for %s: %s", market.slug[:40], result.get("reason", ""))
                    continue
                shares = bet_size / price if price > 0 else 0

                self.portfolio.add_position(
                    market.condition_id, token_id, "BUY_YES",
                    price, bet_size, shares, market.slug,
                    market.tags[0] if market.tags else "",
                    confidence="A", ai_probability=bond.yes_price,
                    question=market.question, end_date_iso=market.end_date_iso,
                    match_start_iso=getattr(market, 'match_start_iso', '') or "",
                    entry_reason="bond", sport_tag=market.sport_tag or "",
                    event_id=market.event_id or "",
                )

                self.trade_log.log({
                    "market": market.slug, "action": "BUY_YES",
                    "size": bet_size, "price": price,
                    "edge": bond.expected_profit_pct, "confidence": "bond",
                    "mode": self.config.mode.value, "status": result["status"],
                    "question": market.question, "bond_type": bond.bond_type,
                    "sport_tag": market.sport_tag or "",
                })

                self.notifier.send(
                    f"\U0001f4b0 *BOND ENTRY* — low-risk farming\n\n"
                    f"{market.question}\n"
                    f"`BUY_YES` | `${bet_size:.0f}` @ `{price:.3f}`\n"
                    f"Type: `{bond.bond_type}` | Expected: `{bond.expected_profit_pct:.1%}`"
                )

                logger.info("BOND ENTRY: %s | $%.0f @ %.3f | type=%s | exp=%.1f%%",
                            market.slug[:40], bet_size, price, bond.bond_type,
                            bond.expected_profit_pct * 100)

                bond_count += 1
                bond_exposure += bet_size

        except Exception as e:
            logger.warning("Bond scan error: %s", e, exc_info=True)

    def _check_penny_candidates(self) -> None:
        """Scan for penny alpha opportunities — ultra-cheap asymmetric bets (rule-based, no AI)."""
        try:
            markets = self.scanner.fetch()
            if not markets:
                return

            penny_count = sum(
                1 for p in self.portfolio.positions.values()
                if getattr(p, 'entry_reason', '') == 'penny'
            )

            candidates = scan_penny_candidates(markets)
            for penny in candidates:
                # Global position limit
                if len(self.portfolio.positions) >= self.config.risk.max_positions:
                    break
                if penny.condition_id in self.portfolio.positions:
                    continue
                if self.blacklist.is_blocked(penny.condition_id, self.cycle_count):
                    continue

                # Penny time filter: only enter matches starting within 6 hours
                _penny_market = next((m for m in markets if m.condition_id == penny.condition_id), None)
                _penny_start = getattr(_penny_market, 'match_start_iso', '') if _penny_market else ''
                if _penny_start:
                    try:
                        from datetime import datetime as _dt, timezone as _tz
                        _start_dt = _dt.fromisoformat(_penny_start.replace("Z", "+00:00"))
                        _hours_until = (_start_dt - _dt.now(_tz.utc)).total_seconds() / 3600
                        if _hours_until > 6.0:
                            logger.info("Penny skip: match starts in %.1fh (>6h): %s",
                                        _hours_until, penny.slug[:40])
                            continue
                        if _hours_until < -2.0:
                            # Match already started >2h ago — skip
                            continue
                    except (ValueError, TypeError):
                        pass
                elif _penny_market and getattr(_penny_market, 'end_date_iso', ''):
                    # No match_start_iso — use end_date as fallback, require <12h
                    try:
                        from datetime import datetime as _dt, timezone as _tz
                        _end_dt = _dt.fromisoformat(_penny_market.end_date_iso.replace("Z", "+00:00"))
                        _hours_to_end = (_end_dt - _dt.now(_tz.utc)).total_seconds() / 3600
                        if _hours_to_end > 12.0:
                            logger.info("Penny skip: resolution in %.1fh (>12h, no start time): %s",
                                        _hours_to_end, penny.slug[:40])
                            continue
                    except (ValueError, TypeError):
                        pass

                bet_size = size_penny_position(
                    bankroll=self.portfolio.bankroll,
                    current_penny_count=penny_count,
                )
                if bet_size < 5:
                    continue

                # Correlation cap — penny dahil (strateji-agnostik)
                _stag = getattr(penny, 'sport_tag', '') or ''
                if not _stag:
                    _m = next((m for m in markets if m.condition_id == penny.condition_id), None)
                    _stag = getattr(_m, 'sport_tag', '') or '' if _m else ''
                if _stag:
                    corr_exp = self.portfolio.correlated_exposure("", sport_tag=_stag)
                    if corr_exp >= self.config.risk.correlation_cap_pct:
                        logger.info("Penny skip: correlation cap for %s (%.0f%%)", _stag, corr_exp * 100)
                        continue

                market = next((m for m in markets if m.condition_id == penny.condition_id), None)
                if not market:
                    continue

                # Penny bets buy the cheap side
                direction = "BUY_YES" if penny.yes_price <= 0.02 else "BUY_NO"
                token_id = market.yes_token_id if direction == "BUY_YES" else market.no_token_id
                price = penny.yes_price if direction == "BUY_YES" else penny.no_price

                result = self.executor.place_order(token_id, "BUY", price, bet_size)
                if result.get("status") == "error":
                    logger.warning("Penny order failed for %s: %s", market.slug[:40], result.get("reason", ""))
                    continue
                shares = bet_size / price if price > 0 else 0

                self.portfolio.add_position(
                    market.condition_id, token_id, direction,
                    market.yes_price, bet_size, shares, market.slug,
                    market.tags[0] if market.tags else "",
                    confidence="C", ai_probability=price,
                    question=market.question, end_date_iso=market.end_date_iso,
                    match_start_iso=getattr(market, 'match_start_iso', '') or "",
                    entry_reason="penny", sport_tag=market.sport_tag or "",
                    event_id=market.event_id or "",
                )

                self.trade_log.log({
                    "market": market.slug, "action": direction,
                    "size": bet_size, "price": price,
                    "edge": 0, "confidence": "penny",
                    "mode": self.config.mode.value, "status": result["status"],
                    "question": market.question,
                    "sport_tag": market.sport_tag or "",
                })

                self.notifier.send(
                    f"\U0001f3b0 *PENNY ENTRY* — asymmetric bet\n\n"
                    f"{market.question}\n"
                    f"`{direction}` | `${bet_size:.0f}` @ `{price:.3f}`\n"
                    f"Target: `{penny.target_multiplier:.0f}x`"
                )

                logger.info("PENNY ENTRY: %s | %s | $%.0f @ %.3f | target=%dx",
                            market.slug[:40], direction, bet_size, price,
                            penny.target_multiplier)

                penny_count += 1

        except Exception as e:
            logger.warning("Penny scan error: %s", e, exc_info=True)

    def _check_momentum_signals(self) -> None:
        """Check live positions for momentum edge from score changes (rule-based, no AI)."""
        try:
            for cid, pos in list(self.portfolio.positions.items()):
                if cid in self._toxic_markets:
                    continue  # match_is_toxic — momentum entry blocked
                match_state = self._match_states.get(cid)
                if not match_state or match_state.get("team_a_score") is None:
                    continue

                signal = detect_momentum_opportunity(
                    condition_id=cid,
                    pre_match_prob=pos.ai_probability,
                    market_price=pos.current_price,
                    match_state=match_state,
                    sport_tag=getattr(pos, 'sport_tag', ''),
                    direction=pos.direction,
                )

                if signal and signal.edge >= 0.06:
                    logger.info("MOMENTUM SIGNAL: %s | edge=%.1f%% | score_diff=%d | %s",
                                pos.slug[:40], signal.edge * 100, signal.score_diff, signal.reason)

        except Exception as e:
            logger.warning("Momentum check error: %s", e, exc_info=True)

    def _get_current_price(self, market) -> float | None:
        """Get current CLOB price for freshness check. Returns None if unavailable."""
        mid = self._get_clob_midpoint(market.yes_token_id)
        if mid and mid > 0:
            return mid
        return None

    def _log_prediction(self, market, estimate) -> None:
        """Log every AI prediction (BUY and HOLD) for calibration tracking."""
        pred_path = Path("logs/predictions.jsonl")
        pred_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pred_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "condition_id": market.condition_id,
                "question": market.question,
                "ai_probability": estimate.ai_probability,
                "confidence": estimate.confidence,
                "market_price": market.yes_price,
                "category": market.tags[0] if market.tags else "",
                "end_date": market.end_date_iso,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }) + "\n")

    _ELECTION_KEYWORDS = {
        "election", "vote", "referendum", "ballot", "polling",
        "president", "presidential", "prime minister", "governor",
        "parliament", "congressional", "senate", "mayor",
        "party", "candidate", "incumbent", "runoff",
    }

    def _is_election_position(self, pos) -> bool:
        """Check if a position is election-related by slug/category."""
        slug = (pos.slug or "").lower()
        cat = (pos.category or "").lower()
        return any(kw in slug or kw in cat for kw in self._ELECTION_KEYWORDS)

    def _reevaluate_election_positions(self, bankroll: float) -> None:
        """Re-analyze election positions every cycle. Exit if AI opinion shifted >10%.

        Elections are swing-tradeable: news moves odds, but markets overreact.
        Buy on calm analysis, sell on spike, re-enter when settled.
        """
        if not self.portfolio.positions:
            return

        election_positions = {
            cid: pos for cid, pos in self.portfolio.positions.items()
            if self._is_election_position(pos)
        }
        if not election_positions:
            return

        # Only re-evaluate every 3rd cycle to save API budget
        if self.cycle_count % 3 != 0:
            return

        logger.info("Re-evaluating %d election position(s)", len(election_positions))

        for cid, pos in election_positions.items():
            # Skip if we can't afford another API call
            if self.ai.budget_exhausted:
                break

            # Fetch current market data for re-analysis
            try:
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"conditionId": cid}, timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    continue
                market_raw = data[0]
                prices = json.loads(market_raw.get("outcomePrices", '["0.5","0.5"]'))
                tokens = json.loads(market_raw.get("clobTokenIds", '["",""]'))
                market = MarketData(
                    condition_id=cid,
                    question=market_raw.get("question", ""),
                    yes_price=float(prices[0]),
                    no_price=float(prices[1]),
                    yes_token_id=tokens[0],
                    no_token_id=tokens[1],
                    slug=market_raw.get("slug", ""),
                    description=market_raw.get("description", ""),
                    end_date_iso=market_raw.get("endDate", ""),
                )
            except Exception as e:
                logger.debug("Election re-eval fetch failed for %s: %s", pos.slug[:30], e)
                continue

            # Invalidate cache to force fresh analysis
            self.ai.invalidate_cache(cid)
            new_estimate = self.ai.analyze_market(market)

            if new_estimate.reasoning_pro in ("BUDGET_EXHAUSTED", "API_ERROR"):
                continue

            # Compare new AI probability with entry probability
            old_prob = pos.ai_probability
            new_prob = new_estimate.ai_probability
            prob_shift = abs(new_prob - old_prob)

            logger.info(
                "Election re-eval: %s | entry AI=%.0f%% → now AI=%.0f%% (shift=%.0f%%)",
                pos.slug[:35], old_prob * 100, new_prob * 100, prob_shift * 100,
            )

            # If AI opinion shifted >10%, exit — the thesis has changed
            if prob_shift >= 0.10:
                reason = (
                    f"election_reeval: AI shifted {old_prob:.0%}→{new_prob:.0%} "
                    f"({prob_shift:.0%} change)"
                )
                self.notifier.send(
                    f"\U0001f504 *RE-EVAL* — Cycle #{self.cycle_count}\n\n"
                    f"{pos.slug}\n"
                    f"AI: `{old_prob:.0%}` → `{new_prob:.0%}` "
                    f"(shift: `{prob_shift:.0%}`)\n\n"
                    f"Exiting — thesis changed"
                )
                self._exit_position(cid, reason)

    def _evaluate_vs_candidate(
        self, market: "MarketData", estimate: "AIEstimate",
        direction: "Direction", mkt_sources: list, block_reason: str,
    ) -> dict | None:
        """Evaluate a market as a volatility swing candidate without executing.

        Returns a candidate dict with score if eligible, None otherwise.
        Same checks as _try_volatility_swing but deferred execution.
        """
        vs_cfg = self.config.volatility_swing
        if not vs_cfg.enabled:
            return None

        # Already have a position in this market?
        if market.condition_id in self.portfolio.positions:
            return None

        # Cooldown check
        if market.condition_id in self._exit_cooldowns:
            if self.cycle_count < self._exit_cooldowns[market.condition_id]:
                return None

        # Token price must be in sweet spot
        underdog_price = min(market.yes_price, market.no_price)
        if underdog_price > vs_cfg.max_token_price or underdog_price < vs_cfg.min_token_price:
            return None

        # Match must start within max_hours_to_start
        # Prefer match_start_iso (actual match time) over end_date_iso (settlement)
        _vs_time = getattr(market, 'match_start_iso', '') or market.end_date_iso
        if not _vs_time:
            return None
        try:
            end_dt = datetime.fromisoformat(_vs_time.replace("Z", "+00:00"))
            hours_left = (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600
            if hours_left > vs_cfg.max_hours_to_start or hours_left < 0:
                return None
        except (ValueError, TypeError):
            return None

        # Determine direction: buy the underdog token
        if market.yes_price <= market.no_price:
            vs_direction = Direction.BUY_YES
            token_price = market.yes_price
            token_id = market.yes_token_id
        else:
            vs_direction = Direction.BUY_NO
            token_price = market.no_price
            token_id = market.no_token_id

        # Size check
        bankroll = self.portfolio.bankroll
        size = min(bankroll * vs_cfg.bet_pct, self.config.risk.max_single_bet_usdc)
        if size < 5.0:
            return None

        # Score: edge * inverse of token price (cheaper = higher upside)
        edge = abs(estimate.ai_probability - market.yes_price)
        score = edge / max(token_price, 0.01)

        return {
            "market": market,
            "estimate": estimate,
            "vs_direction": vs_direction,
            "token_price": token_price,
            "token_id": token_id,
            "size": size,
            "score": score,
            "block_reason": block_reason,
            "mkt_sources": mkt_sources,
        }

    def _execute_vs_entry(self, vc: dict) -> bool:
        """Execute a volatility swing entry from a candidate dict.

        Returns True if position was opened.
        """
        market = vc["market"]
        estimate = vc["estimate"]
        vs_direction = vc["vs_direction"]
        token_price = vc["token_price"]
        token_id = vc["token_id"]
        size = vc["size"]
        block_reason = vc["block_reason"]
        mkt_sources = vc["mkt_sources"]

        # Double-check we still don't have a position (may have been added during normal execution)
        if market.condition_id in self.portfolio.positions:
            return False

        # Re-check VS count (may have changed during normal execution)
        vs_count = sum(1 for p in self.portfolio.positions.values() if p.volatility_swing)
        if vs_count >= self.config.volatility_swing.max_concurrent:
            return False

        result = self.executor.place_order(token_id, "BUY", token_price, size)
        shares = size / token_price if token_price > 0 else 0

        self.portfolio.add_position(
            market.condition_id, token_id, vs_direction.value,
            market.yes_price, size, shares, market.slug,
            market.tags[0] if market.tags else "",
            confidence=estimate.confidence,
            ai_probability=estimate.ai_probability,
            scouted=False,
            question=market.question,
            end_date_iso=market.end_date_iso,
            match_start_iso=getattr(market, 'match_start_iso', '') or "",
            volatility_swing=True,
            sport_tag=market.sport_tag or "",
            event_id=market.event_id or "",
        )
        self.last_cycle_has_live_clob = True  # Trigger fast polling immediately

        self.trade_log.log({
            "market": market.slug, "action": f"VOLATILITY_SWING_{vs_direction.value}",
            "size": size, "price": token_price,
            "edge": abs(estimate.ai_probability - market.yes_price),
            "confidence": estimate.confidence,
            "mode": self.config.mode.value, "status": result["status"],
            "block_reason": block_reason,
            "question": market.question,
            "ai_probability": estimate.ai_probability,
            "data_sources": mkt_sources,
            "vs_slot_reserved": True,
            "sport_tag": market.sport_tag or "",
        })
        logger.info(
            "VOLATILITY SWING (reserved slot): %s | %s @ %.0fc | $%.0f | blocked by: %s",
            market.slug[:40], vs_direction.value, token_price * 100, size, block_reason,
        )
        self.notifier.send(
            f"\U0001f30a *VOLATILITY SWING* -- Cycle #{self.cycle_count}\n\n"
            f"{market.question}\n"
            f"`{vs_direction.value}` | `${size:.0f}` @ `{token_price:.3f}`\n"
            f"Target: `{token_price * 2:.3f}` (+100%) | Stop: `{token_price * 0.5:.3f}` (-50%)\n"
            f"Reason: {block_reason}"
        )
        self.bets_since_approval += 1
        return True

    def _exit_position(self, condition_id: str, reason: str, cooldown_cycles: int = 3) -> None:
        self._exiting_set.add(condition_id)  # Guard against double-exit (#1a, #2a)
        try:
            pos = self.portfolio.remove_position(condition_id)
        finally:
            self._exiting_set.discard(condition_id)
        if not pos:
            return
        # Set cooldown — don't re-enter this market for N cycles (let dust settle)
        self._exit_cooldowns[condition_id] = self.cycle_count + cooldown_cycles

        # Profitable exit → add to farming re-entry pool
        profitable_reasons = ("take_profit", "trailing_stop", "spike_exit", "edge_tp", "scale_out_final", "vs_take_profit")
        realized_pnl = pos.unrealized_pnl_usdc
        if reason in profitable_reasons and realized_pnl > 0:
            # Get original entry price (first ever entry, not re-entry price)
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
        else:
            # Non-profitable exit → try demotion to stock, else blacklist
            _is_never_stock = reason in _NEVER_STOCK_EXITS or reason.startswith(_NEVER_STOCK_PREFIXES)
            demoted = False
            if not _is_never_stock:
                demoted = self._try_demote_to_stock(pos, reason)

            if not demoted:
                # Blacklist as before
                exit_data = {
                    "ai_probability": pos.ai_probability,
                    "confidence": pos.confidence,
                    "direction": pos.direction,
                    "entry_price": pos.entry_price,
                    "exit_price": pos.current_price,
                    "slug": pos.slug,
                    "token_id": pos.token_id,
                }
                _exit_elapsed = 0.0
                _mstart = getattr(pos, "match_start_iso", "")
                _edate = getattr(pos, "end_date_iso", "")
                if _mstart and _edate:
                    try:
                        from datetime import datetime, timezone
                        _ms = datetime.fromisoformat(_mstart.replace("Z", "+00:00"))
                        _ed = datetime.fromisoformat(_edate.replace("Z", "+00:00"))
                        _now = datetime.now(timezone.utc)
                        _total = (_ed - _ms).total_seconds()
                        if _total > 0:
                            _exit_elapsed = min(1.0, max(0.0, (_now - _ms).total_seconds() / _total))
                    except (ValueError, TypeError):
                        pass
                bl_reason = reason
                if bl_reason.startswith("match_exit_"):
                    bl_reason = bl_reason[len("match_exit_"):]
                elif bl_reason.startswith("far_penny_"):
                    bl_reason = "far_penny"
                elif bl_reason.startswith("SLOT_UPGRADE"):
                    bl_reason = "slot_upgrade"
                elif bl_reason.startswith("election_reeval"):
                    bl_reason = "election_reeval"
                btype, duration = get_blacklist_rule(bl_reason, elapsed_pct=_exit_elapsed)
                if btype == "permanent":
                    self.blacklist.add(condition_id, reason, "permanent", None, exit_data)
                elif btype == "timed":
                    self.blacklist.add(condition_id, reason, "timed", self.cycle_count + duration, exit_data)
                elif btype == "reentry":
                    self.blacklist.add(condition_id, reason, "reentry", self.cycle_count + duration, exit_data)
                self._save_exited_market(condition_id)

        # V2: Check exit liquidity before selling
        liq = check_exit_liquidity(pos.token_id, pos.shares)
        if not liq["fillable"]:
            logger.warning("Low liquidity for %s: %s — %s", pos.slug[:30], liq["strategy"], liq.get("note", ""))

        result = self.executor.place_exit_order(pos.token_id, pos.shares)
        realized_pnl = pos.unrealized_pnl_usdc
        self.portfolio.record_realized(realized_pnl)
        self.risk.record_outcome(win=realized_pnl > 0)

        # V2: Record in circuit breaker
        bankroll_for_cb = self.portfolio.bankroll + sum(p.size_usdc for p in self.portfolio.positions.values())
        self.circuit_breaker.record_exit(realized_pnl, bankroll_for_cb)
        # Dry-run bankroll: return position value (investment + profit/loss)
        if not self.wallet:
            self.portfolio.update_bankroll(self.portfolio.bankroll + pos.current_value)
        self.trade_log.log({
            "market": pos.slug, "action": "EXIT",
            "reason": reason, "pnl": realized_pnl,
            "mode": self.config.mode.value, "status": result.get("status", ""),
        })
        # Remove from "already analyzed" list so AI can re-evaluate if needed
        self._analyzed_market_ids.pop(condition_id, None)

        pnl_sign = "+" if realized_pnl >= 0 else ""
        self.notifier.send(
            f"\U0001f6aa *EXIT* — Cycle #{self.cycle_count}\n\n"
            f"{pos.slug}\n"
            f"Reason: {reason}\n"
            f"PnL: `{pnl_sign}${realized_pnl:.2f}`"
        )

        # Collect price history for future calibration
        try:
            from src.price_history import save_price_history
            save_price_history(
                slug=pos.slug,
                token_id=pos.token_id,
                entry_price=pos.entry_price,
                exit_price=pos.current_price,
                exit_reason=reason,
                exit_layer=reason.replace("match_exit_", "") if reason.startswith("match_exit_") else "",
                match_start_iso=getattr(pos, "match_start_iso", ""),
                number_of_games=getattr(pos, "number_of_games", 0),
                ever_in_profit=getattr(pos, "ever_in_profit", False),
                peak_pnl_pct=getattr(pos, "peak_pnl_pct", 0.0),
                match_score=getattr(pos, "match_score", ""),
            )
        except Exception as e:
            logger.debug("Price history collection skipped: %s", e)

        # Log match outcome for AI calibration
        try:
            from src.match_outcomes import log_outcome
            log_outcome(
                slug=pos.slug,
                question=getattr(pos, "question", ""),
                direction=pos.direction,
                ai_probability=pos.ai_probability,
                confidence=pos.confidence,
                entry_price=pos.entry_price,
                exit_price=pos.current_price,
                exit_reason=reason,
                pnl=realized_pnl,
                size=pos.size_usdc,
                sport_tag=getattr(pos, "sport_tag", ""),
                entry_reason=getattr(pos, "entry_reason", ""),
                scouted=getattr(pos, "scouted", False),
                peak_pnl_pct=getattr(pos, "peak_pnl_pct", 0.0),
                match_score=getattr(pos, "match_score", ""),
                price_history=getattr(pos, "price_history_buffer", []),
                cycles_held=getattr(pos, "cycles_held", 0),
                bookmaker_prob=getattr(pos, "bookmaker_prob", 0.0),
            )
        except Exception as e:
            logger.debug("Match outcome logging skipped: %s", e)

        # Track market for post-exit resolution (what actually happened)
        try:
            self.outcome_tracker.track(
                condition_id=condition_id,
                token_id=pos.token_id,
                slug=pos.slug,
                question=getattr(pos, "question", ""),
                direction=pos.direction,
                ai_probability=pos.ai_probability,
                confidence=pos.confidence,
                entry_price=pos.entry_price,
                exit_price=pos.current_price,
                exit_reason=reason,
                pnl=realized_pnl,
                size=pos.size_usdc,
                sport_tag=getattr(pos, "sport_tag", ""),
                entry_reason=getattr(pos, "entry_reason", ""),
                scouted=getattr(pos, "scouted", False),
                peak_pnl_pct=getattr(pos, "peak_pnl_pct", 0.0),
                match_score=getattr(pos, "match_score", ""),
                cycles_held=getattr(pos, "cycles_held", 0),
                bookmaker_prob=getattr(pos, "bookmaker_prob", 0.0),
            )
        except Exception as e:
            logger.debug("Outcome tracking skipped: %s", e)

    def _check_far_penny_exits(self) -> None:
        """Check FAR and standalone penny positions for multiplier target exits.
        $0.01 entry → hold for 5x ($0.05), then trailing stop
        $0.02 entry → hold for 2x ($0.04), then trailing stop
        Swing FAR uses normal TP/SL (handled by portfolio.check_take_profits)."""
        far_cfg = self.config.far
        for cid, pos in list(self.portfolio.positions.items()):
            if pos.pending_resolution:
                continue
            # Include both FAR penny and standalone penny positions
            is_far_penny = pos.entry_reason == "far" and pos.entry_price <= far_cfg.penny_max_price
            is_standalone_penny = pos.entry_reason == "penny"
            if not is_far_penny and not is_standalone_penny:
                continue
            if pos.entry_reason == "far" and pos.entry_price > far_cfg.penny_max_price:
                continue  # Swing FAR — normal TP/SL applies

            # Penny position — check multiplier target
            entry_cents = round(pos.entry_price * 100)
            eff_price = (1 - pos.current_price) if pos.direction == "BUY_NO" else pos.current_price

            if entry_cents <= 1:
                target_price = pos.entry_price * far_cfg.penny_1c_target_multiplier  # 5x
                target_label = f"{far_cfg.penny_1c_target_multiplier:.0f}x"
            else:
                target_price = pos.entry_price * far_cfg.penny_2c_target_multiplier  # 2x
                target_label = f"{far_cfg.penny_2c_target_multiplier:.0f}x"

            if eff_price >= target_price:
                logger.info("PENNY TARGET HIT: %s | entry=%.0f¢ current=%.0f¢ target=%.0f¢ (%s)",
                            pos.slug[:40], pos.entry_price * 100, eff_price * 100,
                            target_price * 100, target_label)
                self._exit_position(cid, f"far_penny_{target_label}_target", cooldown_cycles=0)
                self.notifier.send(
                    f"\U0001f4b0 *PENNY TARGET* \u2014 {target_label}\n\n"
                    f"{pos.question}\n"
                    f"Entry: `{pos.entry_price*100:.0f}\u00a2` \u2192 Current: `{eff_price*100:.0f}\u00a2`\n"
                    f"PnL: `{pos.unrealized_pnl_pct:.0%}`"
                )

    def _check_farming_reentry(self) -> None:
        """Unified farming re-entry — check pool for dip opportunities (no AI cost).

        Replaces old spike_reentry and scouted_reentry with a 3-tier system.
        """
        self.reentry_pool.cleanup_expired(self.cycle_count)

        # Reset daily reentry count at midnight (UTC)
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        if not hasattr(self, '_last_reentry_reset_date') or self._last_reentry_reset_date != now_utc.date():
            self._daily_reentry_count = 0
            self._last_reentry_reset_date = now_utc.date()

        if not self.reentry_pool.candidates:
            return

        held_event_ids = {
            p.event_id for p in self.portfolio.positions.values()
            if p.event_id
        }

        # Check slot availability
        vs_reserved = self.config.volatility_swing.reserved_slots
        current_vs = sum(1 for p in self.portfolio.positions.values() if p.volatility_swing)
        current_normal = self.portfolio.active_position_count - current_vs

        for cid, candidate in list(self.reentry_pool.candidates.items()):
            # Cooldown check
            if self._exit_cooldowns.get(cid, 0) > self.cycle_count:
                continue

            # RE slot check — max 3 concurrent re-entry positions
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
            eff_stab_price = (1.0 - current_yes_price) if candidate.direction == "BUY_NO" else current_yes_price
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
                # Permanent blocks → remove from pool
                if "Max re-entries" in decision["reason"] or "Thesis broken" in decision["reason"]:
                    self.reentry_pool.remove(cid)
                continue

            if decision["action"] == "WAIT":
                continue

            # --- ENTER ---
            direction = candidate.direction
            ai_prob = candidate.ai_probability
            size_mult = decision["size_mult"]

            # Calculate position size (Kelly * tier multiplier)
            eff_price = current_yes_price if direction == "BUY_YES" else (1.0 - current_yes_price)
            # Pass raw YES values — kelly_position_size handles direction internally
            base_size = kelly_position_size(
                ai_prob, current_yes_price, self.portfolio.bankroll,
                kelly_fraction=self.config.risk.kelly_fraction,
                max_bet_usdc=self.config.risk.max_single_bet_usdc,
                max_bet_pct=self.config.risk.max_bet_pct,
                direction=direction,
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
            result = self.executor.place_order(token_id, "BUY", eff_price, size)
            shares = size / eff_price if eff_price > 0 else 0
            yes_price_entry = current_yes_price

            tier_num = decision["tier"]
            reentry_num = candidate.reentry_count + 1
            entry_reason = f"re_entry_t{tier_num}"

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
                f"\U0001f504 *FARMING RE-ENTRY* T{tier_num} (#{reentry_num}) — Cycle #{self.cycle_count}\n\n"
                f"{candidate.question}\n"
                f"Exit: `{candidate.last_exit_price:.3f}` → Re-entry: `{eff_price:.3f}`\n"
                f"Edge: `{decision['edge']:.1%}` | Size: `${size:.0f}` ({size_mult:.0%})\n"
                f"Profit so far: `${candidate.total_realized_profit:.2f}`\n"
                f"_No AI call — using saved analysis_"
            )
            self.bets_since_approval += 1

    def _log_reasoning(
        self, question: str, direction: str, size: float, price: float,
        edge: float, estimate, manip_risk: str,
    ) -> None:
        """Append a human-readable reasoning entry to logs/trade_reasoning.md."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        entry = (
            f"\n---\n"
            f"## {ts} — {direction}\n"
            f"**Market:** {question}\n\n"
            f"**Size:** ${size:.2f} @ {price:.4f} | **Edge:** {edge:.1%} | "
            f"**Confidence:** {estimate.confidence} | **Manip risk:** {manip_risk}\n\n"
            f"**AI probability:** {estimate.ai_probability:.1%} vs market {price:.1%}\n\n"
            f"**PRO reasoning:**\n> {estimate.reasoning_pro}\n\n"
            f"**CON reasoning:**\n> {estimate.reasoning_con}\n"
        )
        log_path = Path("logs/trade_reasoning.md")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if not log_path.exists():
            log_path.write_text("# Trade Reasoning Log\n", encoding="utf-8")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
        logger.info("Reasoning logged for: %s", question[:60])

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
        """Estimated match duration in hours based on sport/format.

        Data sources: HLTV (CS2), VLR.gg (Val), Oracle's Elixir (LoL), Datdota (Dota2).
        """
        text = (slug + " " + question).lower()

        # Esports — average durations
        # CS2: BO1~35m, BO3~1.5h, BO5~2.5h | Val: BO3~1.7h, BO5~2.75h
        # LoL: BO3~1.3h, BO5~2.25h | Dota2: BO3~2h, BO5~3.25h
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
            return 1.75  # CS2/Valorant BO3
        if any(k in text for k in ("cs2", "cs:", "csgo", "counter-strike", "valorant")):
            return 1.75
        if any(k in text for k in ("lol:", "league")):
            return 1.5
        if "dota" in text:
            return 2.0
        # Traditional sports — wall clock averages
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
        """Estimate if a match is currently in progress.

        Prefers match_start_iso (actual start time from ESPN/PandaScore).
        Falls back to end_date - match_duration estimate.
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # Best source: actual match start time
        if match_start_iso:
            try:
                start_dt = datetime.fromisoformat(
                    match_start_iso.replace("Z", "+00:00")
                    .replace(" ", "T")  # PandaScore format: "2026-03-22 12:00:00+00"
                )
                # Not live if match hasn't started yet
                if now < start_dt:
                    return False
                # Match started — but allow entry in first 5 min (pre-match odds still valid)
                minutes_since_start = (now - start_dt).total_seconds() / 60
                if minutes_since_start <= 5:
                    return False  # Just started, pre-match edge still valid
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
            return True  # Past end → finished or live
        duration_h = Agent._match_duration(slug, question)
        return hours_to_end <= duration_h

    def _backfill_match_start(self, pos, cid: str) -> None:
        """Backfill match_start_iso from PandaScore or ESPN if missing."""
        if pos.match_start_iso:
            return
        # Try PandaScore (esports)
        if self.esports.available:
            game_slug = self.esports.detect_game(pos.question, [])
            if game_slug:
                ta, tb = self.esports._extract_team_names(pos.question)
                if ta and tb:
                    minfo = self.esports.get_upcoming_match_info(game_slug, ta, tb)
                    if minfo and minfo.get("begin_at"):
                        candidate_start = minfo["begin_at"]
                        use_it = True
                        if pos.end_date_iso:
                            try:
                                from datetime import datetime, timezone
                                end_dt = datetime.fromisoformat(pos.end_date_iso.replace("Z", "+00:00"))
                                start_dt = datetime.fromisoformat(candidate_start.replace("Z", "+00:00"))
                                if (end_dt - start_dt).total_seconds() > 86400:
                                    logger.warning("Backfill rejected: %s start=%s too far from end=%s",
                                                   pos.slug[:30], candidate_start[:16], pos.end_date_iso[:16])
                                    use_it = False
                            except Exception:
                                pass
                        if use_it:
                            pos.match_start_iso = candidate_start
                            if not pos.number_of_games:
                                pos.number_of_games = minfo.get("number_of_games", 0)
                            self.portfolio._save_positions()
                            logger.info("Backfilled match_start_iso for %s: %s (PandaScore)",
                                        pos.slug[:35], pos.match_start_iso)
        # Try ESPN (traditional sports)
        if not pos.match_start_iso and hasattr(self, 'sports'):
            _tag = getattr(pos, 'category', '') or ''
            espn_info = self.sports.get_upcoming_match_info(
                pos.question, pos.slug, [_tag] if _tag else [])
            if espn_info and espn_info.get("match_start_iso"):
                pos.match_start_iso = espn_info["match_start_iso"]
                self.portfolio._save_positions()
                logger.info("Backfilled match_start_iso for %s: %s (ESPN)",
                            pos.slug[:35], pos.match_start_iso)

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
        has_live_clob = False
        for cid, pos in list(self.portfolio.positions.items()):
            try:
                # Query by slug — conditionId queries return wrong market data
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
                        logger.info("Match start from Gamma event: %s → %s",
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
                    # Market resolved — determine outcome
                    if new_yes_price >= 0.95:
                        yes_won = True
                    elif no_price >= 0.95:
                        yes_won = False
                    elif 0.45 <= new_yes_price <= 0.55 and 0.45 <= no_price <= 0.55:
                        # Void / draw — both sides refunded at ~50¢
                        logger.info("VOID/DRAW: %s | prices=[%.2f, %.2f] — exiting as refund",
                                    pos.slug[:40], new_yes_price, no_price)
                        self.portfolio.update_price(cid, new_yes_price)
                        self._exit_position(cid, "resolved_void")
                        continue
                    elif new_yes_price <= 0.05 and no_price <= 0.05:
                        # Ambiguous [0,0] — check if event says ended
                        if events and events[0].get("ended"):
                            # Event ended but prices ambiguous — check CLOB as tiebreaker
                            clob_price = self._get_clob_midpoint(pos.token_id)
                            if clob_price is not None and clob_price > 0.01:
                                # CLOB still active despite event "ended"
                                if pos.direction == "BUY_NO":
                                    self.portfolio.update_price(cid, 1.0 - clob_price)
                                else:
                                    self.portfolio.update_price(cid, clob_price)
                                has_live_clob = True
                                continue
                        # Truly ambiguous — awaiting oracle
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
                            # Match likely over — mark pending, awaiting oracle
                            self.portfolio.update_price(cid, new_yes_price)
                            if not pos.pending_resolution:
                                self.portfolio.mark_pending_resolution(cid)
                                logger.info("Match likely ended (elapsed > est duration): %s — marking pending",
                                            pos.slug[:40])
                        else:
                            # Match not started or in progress — treat as active
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
                    # Market still open — update price
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
                        eff_p = (1.0 - new_yes_price) if pos.direction == "BUY_NO" else new_yes_price
                        if eff_p >= 0.90:
                            logger.info("RE-ENTRY RESOLVE GUARD (WIN): %s @ %.0f%% — exiting before resolve",
                                        pos.slug[:35], eff_p * 100)
                            reentry_resolve_exits.append((cid, "re_entry_resolve_win"))
                            continue
                        elif eff_p <= 0.10:
                            logger.info("RE-ENTRY RESOLVE GUARD (LOSS): %s @ %.0f%% — exiting before resolve",
                                        pos.slug[:35], eff_p * 100)
                            reentry_resolve_exits.append((cid, "re_entry_resolve_loss"))
                            continue

                    # Mark as pending resolution ONLY when match ended + price at extremes
                    # Price extreme alone is NOT enough — underdog markets sit at 2-5¢ while live
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
                            logger.info("Un-pending: %s — market still open, event not ended", pos.slug[:40])
                    # Pending positions are no longer live
                    if pos.pending_resolution:
                        pos.live_on_clob = False
                        pos.match_live = False
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

        # Check outcome tracker — resolve exited markets we're still watching
        if self.outcome_tracker.tracked_count > 0:
            self._check_tracked_outcomes()

        # Persist updated prices + live status to disk
        self.portfolio.save_prices_to_disk()
        return has_live_clob

    def _check_tracked_outcomes(self) -> None:
        """Check exited markets for resolution — no AI cost, just Gamma API."""
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
                        f"\U0001f4ca *AUTO-CALIBRATION* — {cal_result['resolved_count']} resolved\n\n"
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
                f"\U0001f50d *POST-EXIT* — {outcome['slug'][:40]}\n\n"
                f"Exited: `{outcome['exit_reason']}` PnL=`${outcome['actual_pnl']:.2f}`\n"
                f"Match result: `{side}`\n"
                f"If held: `${outcome['hypothetical_pnl']:.2f}`"
                + (f" (left `${left:.2f}` on table)" if left > 0.5 else "")
            )

    def _check_price_drift_reanalysis(self) -> None:
        """Invalidate AI cache for positions whose price drifted significantly from entry."""
        threshold = self.config.risk.price_drift_reanalysis_pct
        for cid, pos in self.portfolio.positions.items():
            if pos.current_price <= 0.001:
                continue
            drift = abs(pos.current_price - pos.entry_price) / max(pos.entry_price, 0.01)
            if drift >= threshold:
                self.ai.invalidate_cache(cid)
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

                # Market resolved — log calibration result
                outcome_prices = json.loads(market.get("outcomePrices", '["0.5","0.5"]'))
                yes_price = float(outcome_prices[0])
                # Resolved markets have prices at exactly 1.0 or 0.0 (or very close)
                if 0.02 < yes_price < 0.98:
                    # Not truly resolved — prices still mid-range
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

    def _start_dashboard(self) -> None:
        """Start the web dashboard in a background thread."""
        try:
            app = create_dashboard()
            host = self.config.dashboard.host
            port = self.config.dashboard.port
            t = threading.Thread(
                target=app.run,
                kwargs={"host": host, "port": port, "debug": False, "use_reloader": False},
                daemon=True,
            )
            t.start()
            logger.info("Dashboard running at http://%s:%d", host, port)
        except Exception as e:
            logger.warning("Dashboard failed to start: %s", e)

    def run(self) -> None:
        logger.info("Agent starting in %s mode", self.config.mode)

        # Start dashboard in background
        self._start_dashboard()

        # Start WebSocket price feed in background
        if self.portfolio.positions:
            self._sync_ws_subscriptions()
        self.ws_feed.start_background()
        logger.info("WebSocket price feed started")

        pos_count = len(self.portfolio.positions)
        self.notifier.send(
            "\U0001f7e2 *ONLINE*\n\n"
            "Mode: `{mode}`\n"
            "Balance: `${bank:.2f}`\n"
            "Positions: `{pos}`\n"
            "API budget: `${api:.2f}`".format(
                mode=self.config.mode.value,
                bank=self.portfolio.bankroll,
                pos=pos_count,
                api=self.ai.budget_remaining_usd,
            )
        )
        signal.signal(signal.SIGINT, lambda *_: self.shutdown())
        try:
            signal.signal(signal.SIGTERM, lambda *_: self.shutdown())
        except (OSError, AttributeError):
            pass  # SIGTERM not available on Windows

        # Track when last full cycle ran (for interleaving light cycles)
        last_full_cycle_time = 0.0

        while self.running:
            # Determine if we should run a light cycle or full cycle
            # Light cycle = price update + exit checks only (no AI, no scan)
            has_positions = len(self.portfolio.positions) > 0
            vs_near_match = False
            if has_positions:
                vs_positions = [p for p in self.portfolio.positions.values() if p.volatility_swing]
                if vs_positions:
                    now = datetime.now(timezone.utc)
                    for vp in vs_positions:
                        # Prefer match_start_iso (actual match time) over end_date_iso (settlement)
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

            # Full cycle at normal interval, light cycles in between when positions are open
            time_since_full = time.time() - last_full_cycle_time
            # Use dynamic interval from cycle_timer (respects live positions, VS, scout signals)
            dynamic_interval = self.cycle_timer.get_interval()
            full_interval_sec = dynamic_interval * 60
            run_full = not has_positions or time_since_full >= full_interval_sec

            try:
                if run_full:
                    self.run_cycle()
                    last_full_cycle_time = time.time()

                    # Auto-refill: keep running cycles until pool is full
                    # Safety: stop if no new positions were added (no viable markets left)
                    vs_reserved = self.config.volatility_swing.reserved_slots
                    _refill_round = 0
                    while True:
                        current_vs = sum(1 for p in self.portfolio.positions.values() if p.volatility_swing)
                        current_normal = self.portfolio.active_position_count - current_vs
                        open_slots = self.config.risk.max_positions - vs_reserved - current_normal
                        if open_slots <= 0:
                            break
                        _refill_round += 1
                        positions_before = len(self.portfolio.positions)
                        logger.info("Pool not full (%d open slots) — refill cycle %d",
                                    open_slots, _refill_round)
                        self.run_cycle()
                        last_full_cycle_time = time.time()
                        positions_after = len(self.portfolio.positions)
                        if positions_after <= positions_before:
                            logger.info("Refill cycle added 0 positions — no more viable markets, stopping")
                            break
                else:
                    self.run_light_cycle()
                self.consecutive_api_failures = 0
            except Exception as e:
                self.consecutive_api_failures += 1
                logger.error("Cycle error (%d): %s", self.consecutive_api_failures, e)
                if self.consecutive_api_failures >= 3:
                    logger.warning("3 consecutive failures — pausing 5 min")
                    time.sleep(300)
                    self.consecutive_api_failures = 0

            # Tick first, then get interval (otherwise override lasts 1 extra cycle)
            self.cycle_timer.tick()

            # Market-aware cycle — adjust based on activity, not clock
            if not (self.cycle_timer._override and self.cycle_timer._override_cycles > 0):
                active_count = getattr(self, '_last_candidate_count', 0)
                self.cycle_timer.signal_market_aware(active_count, len(self.portfolio.positions))

            # Near stop-loss check
            for pos in self.portfolio.positions.values():
                if pos.unrealized_pnl_pct < -(self.config.risk.stop_loss_pct * 0.83):
                    self.cycle_timer.signal_near_stop_loss()
                    break

            # Live positions on CLOB — speed up polling to 5 min
            if self.last_cycle_has_live_clob:
                self.cycle_timer.signal_live_positions()

            # Volatility swing near match — speed up to 3 min with light cycles
            if vs_near_match:
                self.cycle_timer.signal_volatility_swing(
                    polling_min=self.config.volatility_swing.polling_interval_min)

            # Scout approaching check — speed up polling when scouted match within 3 hours
            upcoming = self.scout.get_upcoming_match_times()
            if upcoming:
                now_utc = datetime.now(timezone.utc)
                for mt in upcoming:
                    hours_until = (mt - now_utc).total_seconds() / 3600
                    if 0 < hours_until < 3:
                        self.cycle_timer.signal_scout_approaching()
                        logger.info("Scouted match in %.1fh — polling every 5 min", hours_until)
                        break

            interval = self.cycle_timer.get_interval()
            logger.info("Next cycle in %d min", interval)
            self._set_status("waiting", f"Next cycle in {interval}min")
            light_interval_sec = 30  # Light cycle every 30s when positions open
            _last_ws_pos_count = len(self.portfolio.positions)  # Track for instant WS sync
            for tick in range(interval * 60):
                if not self.running:
                    break
                # Check file-based stop signal every 5 seconds (Windows-safe)
                if tick % 5 == 0:
                    self._check_stop_file()
                # Poll Telegram commands every 5 seconds
                if tick % 5 == 0:
                    self.notifier.handle_commands(self)
                # Drain WebSocket exit queue every tick (1s) — zero API cost
                if self._ws_exit_queue:
                    self._drain_ws_exit_queue()
                # Instant WS sync: new position entered → subscribe within 1s (not 60s)
                _cur_pos_count = len(self.portfolio.positions)
                if _cur_pos_count != _last_ws_pos_count:
                    self._sync_ws_subscriptions()
                    _last_ws_pos_count = _cur_pos_count
                # Dashboard price sync: save positions every 10s so dashboard reflects WS prices
                if tick % 10 == 0 and self.portfolio.positions:
                    self.portfolio._save_positions()
                # Light cycle: exit checks + dashboard update every 60s
                if self.portfolio.positions and tick > 0 and tick % light_interval_sec == 0:
                    try:
                        self.run_light_cycle()
                        self._set_status("waiting", f"Next cycle in {interval}min")
                    except Exception as e:
                        logger.debug("Light cycle error: %s", e)
                time.sleep(1)

        self._set_status("offline", "Bot stopped")
        self.notifier.send(
            f"\U0001f534 *OFFLINE*\n\n"
            f"Cycles: {self.cycle_count}\n"
            f"Balance: `${self.portfolio.bankroll:.2f}`\n"
            f"Positions: {len(self.portfolio.positions)}"
        )
        logger.info("Agent stopped")


def _reset_simulation() -> None:
    """Wipe all simulation state for a clean $1000 start.

    Deletes positions, trades, portfolio logs, predictions cache,
    blacklist, reentry pool, scout queue, and price history.
    Trade reasoning and AI lessons are preserved for analysis.
    """
    import glob
    reset_files = [
        "logs/positions.json",
        "logs/portfolio.jsonl",
        "logs/trades.jsonl",
        "logs/performance.jsonl",
        "logs/predictions.jsonl",
        "logs/bot_status.json",
        "logs/candidate_stock.json",
        "logs/portfolio_state.json",
        "logs/realized_pnl.json",
        "logs/blacklist.json",
        "logs/reentry_pool.json",
        "logs/scout_queue.json",
        "logs/exited_markets.json",
        "logs/agent.pid",
    ]
    deleted = 0
    for f in reset_files:
        p = Path(f)
        if p.exists():
            p.unlink()
            deleted += 1
    # Clear price history
    for f in glob.glob("logs/price_history/*.json"):
        Path(f).unlink()
        deleted += 1
    print(f"[RESET] Deleted {deleted} files. Clean $1000 start.")


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Handle --reset flag
    if "--reset" in sys.argv:
        _reset_simulation()
        sys.argv.remove("--reset")

    # Prevent multiple instances from running simultaneously
    acquire_lock()

    config = load_config()

    # Iron Rule 6: User must explicitly confirm before live trading
    if config.mode == Mode.LIVE:
        print("\n*** WARNING: LIVE TRADING MODE ***")
        print("This will execute REAL orders with REAL money on Polymarket.")
        confirm = input("Type 'CONFIRM LIVE' to proceed: ")
        if confirm.strip() != "CONFIRM LIVE":
            print("Aborted. Set mode to 'dry_run' or 'paper' in config.yaml.")
            sys.exit(1)

    agent = Agent(config)
    agent.run()


if __name__ == "__main__":
    main()
