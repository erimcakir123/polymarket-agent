"""Entry point and main agent loop."""
from __future__ import annotations
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.config import AppConfig, Mode, load_config
from src.market_scanner import MarketScanner
from src.ai_analyst import AIAnalyst
from src.edge_calculator import calculate_edge_with_whale
from src.risk_manager import RiskManager
from src.portfolio import Portfolio
from src.executor import Executor
from src.order_manager import OrderManager
from src.orderbook_analyzer import OrderBookAnalyzer
from src.news_scanner import NewsScanner
from src.whale_tracker import WhaleTracker
from src.event_cluster import EventCluster
from src.cycle_timer import CycleTimer
from src.liquidity_provider import LiquidityProvider
from src.performance_tracker import PerformanceTracker
from src.trade_logger import TradeLogger
from src.notifier import TelegramNotifier
from src.models import Signal, Direction

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.running = True
        self.consecutive_api_failures = 0

        # Core modules
        self.scanner = MarketScanner(config.scanner)
        self.ai = AIAnalyst(config.ai)
        self.risk = RiskManager(config.risk)
        self.portfolio = Portfolio()
        self.order_manager = OrderManager()
        self.ob_analyzer = OrderBookAnalyzer(
            wall_threshold_usd=config.orderbook.wall_threshold_usd,
            max_slippage_pct=config.orderbook.max_slippage_pct,
        )

        # Signal enhancers
        self.news_scanner = NewsScanner()
        self.whale_tracker = WhaleTracker(config.whale)
        self.event_cluster = EventCluster()
        self.cycle_timer = CycleTimer(config.cycle)
        self.lp = LiquidityProvider(config.liquidity_provider)
        self.perf = PerformanceTracker()

        # Logging & notifications
        self.trade_log = TradeLogger(config.logging.trades_file)
        self.portfolio_log = TradeLogger(config.logging.portfolio_file)
        self.notifier = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        )

        # Wallet & executor
        self.wallet = None
        self.executor = Executor(mode=Mode(config.mode), clob_client=None)

    def shutdown(self) -> None:
        self.running = False
        logger.info("Shutdown requested — finishing current cycle")

    def run_cycle(self) -> None:
        logger.info("=== Cycle start ===")

        # 1. Check bankroll
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.portfolio.update_bankroll(bankroll)

        # Drawdown check
        if self.portfolio.is_drawdown_breaker_active(self.config.risk.drawdown_halt_pct):
            msg = self.notifier.alert_drawdown(bankroll, self.portfolio.high_water_mark)
            self.notifier.send(msg)
            logger.critical("DRAWDOWN BREAKER — halting")
            self.running = False
            return

        # 2. Check stop-losses and take-profits
        for cid in self.portfolio.check_stop_losses(self.config.risk.stop_loss_pct):
            self._exit_position(cid, "stop_loss")
        for cid in self.portfolio.check_take_profits(self.config.risk.take_profit_pct):
            self._exit_position(cid, "take_profit")

        # 3. Order manager tick
        self.order_manager.tick_cycle()
        self.order_manager.cancel_stale(self.executor)

        # 4. Fetch news
        headlines = self.news_scanner.fetch_headlines()

        # 5. Scan markets
        markets = self.scanner.fetch()
        if not markets:
            self._try_liquidity_providing(bankroll)
            self._log_cycle_summary(bankroll, "no qualifying markets")
            return

        # 6. Cluster and analyze
        clusters = self.event_cluster.group(markets)
        news_context = self.news_scanner.build_news_context(headlines)

        # Check for breaking news and adjust cycle timer
        market_keywords = {m.condition_id: m.question.lower().split()[:5] for m in markets}
        news_matches = self.news_scanner.match_headlines(headlines, market_keywords)
        has_breaking = any(
            any(h.get("is_breaking") for h in hs)
            for hs in news_matches.values()
        )
        if has_breaking:
            self.cycle_timer.signal_breaking_news()
            # Invalidate AI cache for affected markets
            for cid in news_matches:
                self.ai.invalidate_cache(cid)

        estimates = self.ai.analyze_batch(markets[:self.config.ai.batch_size], news_context)

        # 7. Generate signals
        signals_generated = False
        for market, estimate in zip(markets, estimates):
            whale_positions = self.whale_tracker.check_market(market.condition_id)
            whale_prob = self.whale_tracker.compute_signal(whale_positions)

            direction, edge = calculate_edge_with_whale(
                ai_prob=estimate.ai_probability,
                market_price=market.yes_price,
                min_edge=self.config.edge.min_edge,
                confidence=estimate.confidence,
                whale_prob=whale_prob,
                whale_weight=self.config.whale.signal_weight,
            )

            if direction == Direction.HOLD:
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": edge, "mode": self.config.mode,
                })
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
                    "edge": edge, "rejected": decision.reason, "mode": self.config.mode,
                })
                continue

            # Execute
            token_id = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
            price = market.yes_price if direction == Direction.BUY_YES else market.no_price
            result = self.executor.place_order(token_id, "BUY", price, decision.size_usdc)

            # Track
            shares = decision.size_usdc / price if price > 0 else 0
            self.portfolio.add_position(
                market.condition_id, token_id, direction.value,
                price, decision.size_usdc, shares, market.slug,
                market.tags[0] if market.tags else "",
            )
            self.trade_log.log({
                "market": market.slug, "action": direction.value,
                "size": decision.size_usdc, "price": price,
                "edge": edge, "confidence": estimate.confidence,
                "mode": self.config.mode, "status": result["status"],
            })
            self.notifier.send(self.notifier.format_trade(
                market.question, direction.value, decision.size_usdc, price, edge
            ))

        if not signals_generated:
            self._try_liquidity_providing(bankroll)

        self._log_cycle_summary(bankroll, "complete")

    def _exit_position(self, condition_id: str, reason: str) -> None:
        pos = self.portfolio.remove_position(condition_id)
        if not pos:
            return
        result = self.executor.place_exit_order(pos.token_id, pos.shares)
        self.risk.record_outcome(win=pos.unrealized_pnl_usdc > 0)
        self.perf.record_trade(
            pos.category, won=pos.unrealized_pnl_usdc > 0, edge=0
        )
        self.trade_log.log({
            "market": pos.slug, "action": "EXIT",
            "reason": reason, "pnl": pos.unrealized_pnl_usdc,
            "mode": self.config.mode, "status": result.get("status", ""),
        })
        self.notifier.send(self.notifier.format_exit(
            pos.slug, reason, pos.unrealized_pnl_usdc
        ))

    def _try_liquidity_providing(self, bankroll: float) -> None:
        if not self.config.liquidity_provider.enabled:
            return
        logger.info("No edge signals — trying LP mode")

    def _log_cycle_summary(self, bankroll: float, status: str) -> None:
        self.portfolio_log.log({
            "bankroll": bankroll,
            "positions": len(self.portfolio.positions),
            "unrealized_pnl": self.portfolio.total_unrealized_pnl(),
            "hwm": self.portfolio.high_water_mark,
            "status": status,
        })

    def run(self) -> None:
        logger.info("Agent starting in %s mode", self.config.mode)
        signal.signal(signal.SIGINT, lambda *_: self.shutdown())

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

            interval = self.cycle_timer.get_interval()
            self.cycle_timer.tick()

            # Night mode check
            current_hour = datetime.now().hour
            self.cycle_timer.signal_night_mode(current_hour)

            # Near stop-loss check
            for pos in self.portfolio.positions.values():
                if pos.unrealized_pnl_pct < -(self.config.risk.stop_loss_pct * 0.83):
                    self.cycle_timer.signal_near_stop_loss()
                    break

            logger.info("Next cycle in %d min", interval)
            for _ in range(interval * 60):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Agent stopped")


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = load_config()

    # Iron Rule 6: User must explicitly confirm before live trading
    if config.mode == "live":
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
