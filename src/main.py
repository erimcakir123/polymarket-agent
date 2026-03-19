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
from src.edge_calculator import calculate_edge
from src.risk_manager import RiskManager
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
from src.scout_scheduler import ScoutScheduler
from src.process_lock import acquire_lock
from src.dashboard import create_app as create_dashboard

logger = logging.getLogger(__name__)


PAUSE_FILE = Path("logs/AWAITING_APPROVAL")
STATUS_FILE = Path("logs/bot_status.json")
BETS_PER_APPROVAL = 10
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
        self.bets_since_approval = 0
        self.cycle_count = 0
        self._exit_cooldowns: dict[str, int] = {}  # condition_id -> cycle when cooldown expires
        self._exited_markets: set[str] = self._load_exited_markets()  # Never re-enter these
        self._seen_market_ids: set[str] = set()  # Track markets across cycles for new-market detection
        self._last_resolved_count = self._count_resolved()

        # Core modules
        self.scanner = MarketScanner(config.scanner)
        self.ai = AIAnalyst(config.ai)
        self.risk = RiskManager(config.risk)
        self.portfolio = Portfolio(initial_bankroll=config.initial_bankroll)

        # Signal enhancers
        self.esports = EsportsDataClient()
        self.sports = SportsDataClient()
        self.odds_api = OddsAPIClient()
        self.news_scanner = NewsScanner()
        self.manip_guard = ManipulationGuard()
        self.cycle_timer = CycleTimer(config.cycle)
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

    def shutdown(self) -> None:
        self.running = False
        logger.info("Shutdown requested — finishing current cycle")

    def _set_status(self, state: str, step: str = "") -> None:
        """Write current bot status to disk for dashboard polling."""
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = STATUS_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps({
                "state": state,
                "step": step,
                "cycle": self.cycle_count,
                "ts": datetime.now(timezone.utc).isoformat(),
            }), encoding="utf-8")
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
        """After N bets, pause and ask for approval."""
        if self.bets_since_approval >= BETS_PER_APPROVAL:
            PAUSE_FILE.parent.mkdir(parents=True, exist_ok=True)
            PAUSE_FILE.write_text(
                f"Paused after {self.bets_since_approval} bets. Delete this file to resume.",
                encoding="utf-8",
            )
            self.notifier.send(
                f"\u23f8 *PAUSED*\n\n"
                f"{self.bets_since_approval} bets completed.\n"
                f"Send /resume to continue."
            )
            logger.warning("Bet limit reached (%d). Paused for approval.", self.bets_since_approval)
            self.bets_since_approval = 0

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

    def run_cycle(self) -> None:
        # Skip cycle if paused
        if self._is_paused():
            return
        self.cycle_count += 1
        logger.info("=== Cycle #%d start ===", self.cycle_count)
        self._set_status("running", "Starting cycle")

        # 0. Daily milestone reminder + self-reflection
        self._maybe_send_milestone_reminder()
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

        # Drawdown check
        if self.portfolio.is_drawdown_breaker_active(self.config.risk.drawdown_halt_pct):
            msg = self.notifier.alert_drawdown(bankroll, self.portfolio.high_water_mark)
            self.notifier.send(msg)
            logger.critical("DRAWDOWN BREAKER — halting")
            self.running = False
            return

        # 2. Check resolved markets for calibration
        self._set_status("running", "Checking resolved markets")
        self._check_resolved_markets()

        # 3. Update position prices from current market data
        self._set_status("running", "Updating prices")
        self._update_position_prices()

        # 4. Check stop-losses and take-profits
        self._set_status("running", "Checking stop-losses")
        for cid in self.portfolio.check_stop_losses(self.config.risk.stop_loss_pct):
            self._exit_position(cid, "stop_loss")
        for cid in self.portfolio.check_take_profits(self.config.risk.take_profit_pct):
            self._exit_position(cid, "take_profit")
        for cid in self.portfolio.check_trailing_stops(trailing_drop_pct=0.40):
            self._exit_position(cid, "trailing_stop")

        # 4b. Re-evaluate election positions — swing trade on opinion shift
        self._reevaluate_election_positions(bankroll)

        # 5. Scan markets
        self._set_status("running", "Scanning markets")
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
                # Invalidate cache for new markets — analyze with fresh data
                for m in new_markets_list:
                    self.ai.invalidate_cache(m.condition_id)
                # New markets first, then old markets fill remaining batch slots
                markets = new_markets_list + old_markets_list
                for m in new_markets_list[:5]:
                    logger.info("  NEW: %s (%.0f%%) vol=$%.0f",
                                m.question[:60], m.yes_price * 100, m.volume_24h)
        self._seen_market_ids = current_ids

        # 7. Select markets for analysis (whale pre-filter disabled — Data API requires wallet address)
        prioritized = markets[:self.config.ai.batch_size]

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

        # Build combined news context for AI
        all_articles = []
        for cid, articles in news_by_market.items():
            all_articles.extend(articles)
        news_context = self.news_scanner.build_news_context(all_articles)

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

        # 9. Skip markets already in portfolio or on exit cooldown
        new_markets = [
            m for m in prioritized
            if m.condition_id not in self.portfolio.positions
            and m.condition_id not in self._exited_markets
            and self._exit_cooldowns.get(m.condition_id, 0) <= self.cycle_count
        ]
        skipped_portfolio = sum(1 for m in prioritized if m.condition_id in self.portfolio.positions)
        skipped_cooldown = sum(
            1 for m in prioritized
            if m.condition_id not in self.portfolio.positions
            and self._exit_cooldowns.get(m.condition_id, 0) > self.cycle_count
        )
        if skipped_portfolio or skipped_cooldown:
            logger.info("Skipped %d in portfolio, %d on cooldown (saved API calls)",
                        skipped_portfolio, skipped_cooldown)
        prioritized = new_markets

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

            # Add bookmaker odds to AI context (uses quota sparingly — cached 1hr)
            if self.odds_api.available and (espn_ctx or parts):
                odds = self.odds_api.get_bookmaker_odds(m.question, m.slug, m.tags)
                if odds:
                    parts.append(self.odds_api.build_odds_context(odds))
                    sources.append("odds_api")
                    logger.info("Bookmaker odds loaded: %s (%.0f%% vs %.0f%%, %d books)",
                                m.slug[:30], odds["bookmaker_prob_a"] * 100,
                                odds["bookmaker_prob_b"] * 100, odds["num_bookmakers"])

            if parts:
                esports_contexts[m.condition_id] = "\n".join(parts)
            data_sources_by_market[m.condition_id] = sources
        if esports_contexts:
            logger.info("Sports data fetched for %d/%d markets", len(esports_contexts), len(prioritized))

        # 10. Analyze ALL markets with AI (scout only pre-fetches sports data, not AI)
        self._set_status("running", f"Warren analyzing {len(prioritized)} markets")
        estimates = self.ai.analyze_batch(prioritized, news_context, esports_contexts)

        # 10a. Check budget alerts
        for alert in self.ai.check_budget_alerts():
            self.notifier.send(alert)
            logger.warning("Budget alert sent: %s", alert[:60])

        # 11. Generate signals
        self._set_status("running", "Evaluating signals")
        signals_generated = False
        for market, estimate in zip(prioritized, estimates):
            # Hard stop: budget exhausted → skip all remaining markets
            if estimate.reasoning_pro == "BUDGET_EXHAUSTED":
                logger.warning("Budget exhausted — skipping remaining markets")
                break
            # API error → skip this market (0.5 would cause false edge on extreme-priced markets)
            if estimate.reasoning_pro == "API_ERROR":
                logger.warning("API error for %s — skipping", market.slug[:40])
                continue

            # Log ALL AI predictions for calibration (including future HOLDs)
            self._log_prediction(market, estimate)

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

            # Track data sources for this market
            mkt_sources = list(data_sources_by_market.get(market.condition_id, []))
            if news_by_market.get(market.condition_id):
                mkt_sources.append("news")
            mkt_sources.append("claude_sonnet")

            # Edge calculation (pure AI probability first)
            direction, edge = calculate_edge(
                ai_prob=estimate.ai_probability,
                market_yes_price=market.yes_price,
                min_edge=self.config.edge.min_edge,
                confidence=estimate.confidence,
                confidence_multipliers=self.config.edge.confidence_multipliers,
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

            # Ignorance edge guard: confidence-proportional edge cap
            # If AI isn't confident, large edge is likely fake (AI defaulting to ~50%)
            # High confidence = no cap (AI genuinely sees mispricing)
            _MAX_EDGE_BY_CONFIDENCE = {"low": 0.15, "medium": 0.25}
            ulti_used = False
            original_ai_prob = estimate.ai_probability

            max_edge = _MAX_EDGE_BY_CONFIDENCE.get(estimate.confidence)
            blocked_by_ignorance = max_edge is not None and edge > max_edge

            if blocked_by_ignorance:
                # ULTI rescue: AI wasn't confident enough, try bookmaker odds
                logger.info("Ignorance edge blocked: %s | edge=%.1f%% conf=%s cap=%.0f%% — trying ULTI",
                            market.slug[:40], edge * 100, estimate.confidence, max_edge * 100)
                if estimate.confidence in ("low", "medium") and self.odds_api.available:
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
                        estimate.confidence = "medium"
                        ulti_used = True
                        # Recalculate edge with blended probability
                        direction, edge = calculate_edge(
                            ai_prob=estimate.ai_probability,
                            market_yes_price=market.yes_price,
                            min_edge=self.config.edge.min_edge,
                            confidence=estimate.confidence,
                            confidence_multipliers=self.config.edge.confidence_multipliers,
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
                        # Re-check ignorance with new edge
                        max_edge = _MAX_EDGE_BY_CONFIDENCE.get(estimate.confidence)
                        blocked_by_ignorance = max_edge is not None and edge > max_edge

                if blocked_by_ignorance:
                    self.trade_log.log({
                        "market": market.slug, "action": "HOLD",
                        "question": market.question,
                        "ai_prob": estimate.ai_probability, "price": market.yes_price,
                        "edge": edge, "mode": self.config.mode.value,
                        "rejected": f"IGNORANCE_EDGE: {estimate.confidence} confidence with "
                                    f"edge {edge:.1%} > cap {max_edge:.0%} — crowd likely knows more"
                                    + (" (ULTI tried)" if ulti_used else ""),
                        "data_sources": mkt_sources,
                    })
                    logger.info("Ignorance edge blocked: %s | edge=%.1f%% conf=%s cap=%.0f%%%s",
                                market.slug[:40], edge * 100, estimate.confidence, max_edge * 100,
                                " (ULTI tried)" if ulti_used else "")
                    continue

            signals_generated = True
            signal = Signal(
                condition_id=market.condition_id,
                direction=direction,
                ai_probability=estimate.ai_probability,
                market_price=market.yes_price,
                edge=edge,
                confidence=estimate.confidence,
            )

            # Risk check
            corr_exposure = self.portfolio.correlated_exposure(
                market.tags[0] if market.tags else ""
            )
            decision = self.risk.evaluate(
                signal, bankroll, self.portfolio.positions, corr_exposure
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
                continue

            # Adjust position size for medium-risk markets
            adjusted_size = self.manip_guard.adjust_position_size(
                decision.size_usdc, manip_check
            )
            if adjusted_size < 5.0:
                self.trade_log.log({
                    "market": market.slug, "action": direction.value,
                    "edge": edge, "rejected": f"Manipulation risk reduced size below minimum: {manip_check.recommendation}",
                    "mode": self.config.mode.value,
                    "data_sources": mkt_sources,
                })
                continue

            # Sanity check: catch absurd bets before execution
            sanity = check_bet_sanity(
                question=market.question,
                direction=direction.value,
                ai_probability=estimate.ai_probability,
                market_price=market.yes_price,
                edge=edge,
                confidence=estimate.confidence,
            )
            if not sanity.ok:
                # ULTI rescue for sanity block (only if not already tried)
                if not ulti_used and estimate.confidence in ("low", "medium") and self.odds_api.available:
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
                        estimate.confidence = "medium"
                        ulti_used = True
                        # Recalculate edge
                        direction, edge = calculate_edge(
                            ai_prob=estimate.ai_probability,
                            market_yes_price=market.yes_price,
                            min_edge=self.config.edge.min_edge,
                            confidence=estimate.confidence,
                            confidence_multipliers=self.config.edge.confidence_multipliers,
                        )
                        # Re-check sanity with blended probability
                        sanity = check_bet_sanity(
                            question=market.question,
                            direction=direction.value,
                            ai_probability=estimate.ai_probability,
                            market_price=market.yes_price,
                            edge=edge,
                            confidence=estimate.confidence,
                        )
                        if sanity.ok:
                            logger.info("ULTI RESCUED sanity: %s — proceeding", market.slug[:40])
                            # Fall through to execution below

                if not sanity.ok:
                    self.trade_log.log({
                        "market": market.slug, "action": direction.value,
                        "edge": edge, "rejected": f"SANITY: {sanity.reason}"
                                                   + (" (ULTI tried)" if ulti_used else ""),
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

            # Execute
            token_id = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
            price = market.yes_price if direction == Direction.BUY_YES else market.no_price
            result = self.executor.place_order(token_id, "BUY", price, adjusted_size)

            # Track — always store YES price for consistent P&L calculation
            shares = adjusted_size / price if price > 0 else 0
            is_scouted = market.condition_id in scouted_markets
            self.portfolio.add_position(
                market.condition_id, token_id, direction.value,
                market.yes_price, adjusted_size, shares, market.slug,
                market.tags[0] if market.tags else "",
                confidence=estimate.confidence,
                ai_probability=estimate.ai_probability,
                scouted=is_scouted,
                question=market.question,
                end_date_iso=market.end_date_iso,
            )
            # Note: bankroll deduction happens inside add_position()
            # Mark scout entry as used
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
                "market_yes_price": market.yes_price,
                "end_date": market.end_date_iso,
                "data_sources": mkt_sources,
            })
            # Write human-readable reasoning log
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
            # Bet counter — pause after N bets for approval
            self.bets_since_approval += 1
            self._check_bet_limit()

        self._log_cycle_summary(bankroll, "complete")

        # Check if enough data for self-improvement
        self._check_self_improve_ready()

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

    def _exit_position(self, condition_id: str, reason: str, cooldown_cycles: int = 3) -> None:
        pos = self.portfolio.remove_position(condition_id)
        if not pos:
            return
        # Set cooldown — don't re-enter this market for N cycles (let dust settle)
        self._exit_cooldowns[condition_id] = self.cycle_count + cooldown_cycles
        # Persist to disk so we never re-enter after restart
        self._save_exited_market(condition_id)
        result = self.executor.place_exit_order(pos.token_id, pos.shares)
        realized_pnl = pos.unrealized_pnl_usdc
        self.portfolio.record_realized(realized_pnl)
        self.risk.record_outcome(win=realized_pnl > 0)
        # Dry-run bankroll: return position value (investment + profit/loss)
        if not self.wallet:
            self.portfolio.update_bankroll(self.portfolio.bankroll + pos.current_value)
        self.trade_log.log({
            "market": pos.slug, "action": "EXIT",
            "reason": reason, "pnl": realized_pnl,
            "mode": self.config.mode.value, "status": result.get("status", ""),
        })
        pnl_sign = "+" if realized_pnl >= 0 else ""
        self.notifier.send(
            f"\U0001f6aa *EXIT* — Cycle #{self.cycle_count}\n\n"
            f"{pos.slug}\n"
            f"Reason: {reason}\n"
            f"PnL: `{pnl_sign}${realized_pnl:.2f}`"
        )

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

    def _update_position_prices(self) -> None:
        """Fetch current YES prices for all open positions from Gamma API."""
        if not self.portfolio.positions:
            return
        stale_cids = []
        for cid, pos in list(self.portfolio.positions.items()):
            try:
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"conditionId": cid}, timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                if data:
                    market_data = data[0]
                    prices = json.loads(market_data.get("outcomePrices", '["0.5","0.5"]'))
                    new_yes_price = float(prices[0])
                    is_closed = market_data.get("closed", False)

                    if is_closed:
                        # Market resolved — determine outcome
                        # Gamma returns ["1","0"] (YES won) or ["0","1"] (NO won)
                        no_price = float(prices[1]) if len(prices) > 1 else 1 - new_yes_price

                        if new_yes_price >= 0.95:
                            yes_won = True  # YES clearly won
                        elif no_price >= 0.95:
                            yes_won = False  # NO clearly won
                        else:
                            # Gamma returned ambiguous prices (e.g. ["0","0"])
                            # Market closed but not fully resolved yet — wait
                            logger.info(
                                "Closed but not resolved yet: %s (prices=[%.2f, %.2f]) — waiting",
                                pos.slug, new_yes_price, no_price,
                            )
                            continue

                        won = (pos.direction == "BUY_YES" and yes_won) or \
                              (pos.direction == "BUY_NO" and not yes_won)

                        # Update current_price to resolution value BEFORE exit
                        # so unrealized_pnl_usdc calculates correctly
                        resolution_price = 1.0 if yes_won else 0.0
                        self.portfolio.update_price(cid, resolution_price)

                        pnl = pos.shares - pos.size_usdc if won else -pos.size_usdc
                        logger.info("RESOLVED: %s | %s | %s | PnL=$%.2f",
                                    pos.slug, pos.direction, "WIN" if won else "LOSS", pnl)
                        self._exit_position(cid, f"resolved_{'win' if won else 'loss'}")
                    else:
                        self.portfolio.update_price(cid, new_yes_price)
                else:
                    logger.warning("Market not found on Gamma: %s (%s..)", pos.slug, cid[:16])
                    stale_cids.append(cid)
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
                if not market.get("closed", False):
                    unresolved.append(line)
                    continue

                # Market resolved — log calibration result
                outcome_prices = json.loads(market.get("outcomePrices", '["0.5","0.5"]'))
                resolved_yes = float(outcome_prices[0]) > 0.95  # YES won
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
        wins = sum(1 for l in lines if l.get("outcome") == 1)
        losses = sum(1 for l in lines if l.get("outcome") == 0)
        total = wins + losses
        if total == 0:
            return
        brier = sum((l.get("probability", 0) - l.get("outcome", 0)) ** 2 for l in lines) / len(lines)
        # Best category by win rate
        cat_wins: dict[str, int] = {}
        cat_total: dict[str, int] = {}
        for l in lines:
            market = l.get("market", "")
            cat_match = re.match(r"^(nba|nhl|cbb|nfl|mlb|cs2|lol|dota2|valorant)", market, re.IGNORECASE)
            cat = cat_match.group(1).upper() if cat_match else "Other"
            cat_total[cat] = cat_total.get(cat, 0) + 1
            if l.get("outcome") == 1:
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

        while self.running:
            try:
                self.run_cycle()
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

            # Night mode — only if no active breaking news override
            current_hour = datetime.now(timezone.utc).hour
            if not (self.cycle_timer._override and self.cycle_timer._override_cycles > 0):
                self.cycle_timer.signal_night_mode(current_hour)

            # Near stop-loss check
            for pos in self.portfolio.positions.values():
                if pos.unrealized_pnl_pct < -(self.config.risk.stop_loss_pct * 0.83):
                    self.cycle_timer.signal_near_stop_loss()
                    break

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
            for tick in range(interval * 60):
                if not self.running:
                    break
                # Poll Telegram commands every 5 seconds
                if tick % 5 == 0:
                    self.notifier.handle_commands(self)
                time.sleep(1)

        self._set_status("offline", "Bot stopped")
        self.notifier.send(
            f"\U0001f534 *OFFLINE*\n\n"
            f"Cycles: {self.cycle_count}\n"
            f"Balance: `${self.portfolio.bankroll:.2f}`\n"
            f"Positions: {len(self.portfolio.positions)}"
        )
        logger.info("Agent stopped")


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

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
