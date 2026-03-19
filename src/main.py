"""Entry point and main agent loop."""
from __future__ import annotations
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from dotenv import load_dotenv

from src.config import AppConfig, Mode, load_config
from src.market_scanner import MarketScanner
from src.ai_analyst import AIAnalyst
from src.edge_calculator import calculate_edge
from src.risk_manager import RiskManager
from src.portfolio import Portfolio
from src.executor import Executor
from src.news_scanner import NewsScanner
from src.manipulation_guard import ManipulationGuard
from src.cycle_timer import CycleTimer
from src.trade_logger import TradeLogger
from src.notifier import TelegramNotifier
from src.models import Signal, Direction
from src.pre_filter import filter_impossible_markets
from src.sanity_check import check_bet_sanity

logger = logging.getLogger(__name__)


PAUSE_FILE = Path("logs/AWAITING_APPROVAL")
BETS_PER_APPROVAL = 10
TEST_START_DATE = datetime(2026, 3, 19, tzinfo=timezone.utc).date()

# Testing plan milestones — (day, message)
_MILESTONES = [
    (1, "Gün 1 — Bot başladı (dry_run). Veri toplamaya başlıyoruz."),
    (3, "Gün 3 — CHECKPOINT 1: İlk veri. ~350 prediction olmalı.\n"
        "Claude'u çağır: win rate, Brier score, en kötü 5 hata, kategori analizi."),
    (5, "Gün 5 — CHECKPOINT 2: Baseline tamamlandı. ~700 prediction.\n"
        "BOT DURACAK. Claude çağrılacak → ilk optimizasyon yapılacak."),
    (8, "Gün 8 — CHECKPOINT 3: Optimizasyon sonrası ilk kontrol.\n"
        "Win rate iyileşti mi? Filtrelenen kategoriler doğru muydu?"),
    (11, "Gün 11 — CHECKPOINT 4: İkinci karşılaştırma.\n"
         "Faz 1 vs Faz 2. PnL simülasyonu yapılacak.\n"
         "BOT DURACAK. Claude çağrılacak → ikinci optimizasyon."),
    (15, "Gün 15 — CHECKPOINT 5: Doğrulama.\n"
         "Son 3 checkpoint trendi, overfitting kontrolü, simüle PnL."),
    (19, "Gün 19 — CHECKPOINT 6: KARAR NOKTASI.\n"
         "Win rate >%57 → gerçek para ($100-200)\n"
         "Win rate %53-57 → 1 iterasyon daha\n"
         "Win rate <%53 → temel değişiklik gerek"),
    (21, "Gün 21 — Gerçek para fazına geçiş (eğer onaylandıysa)."),
    (28, "Gün 28 — CHECKPOINT 8: İlk hafta gerçek trade sonuçları.\n"
         "Gerçek PnL vs dry_run karşılaştırması."),
]


class Agent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.running = True
        self.consecutive_api_failures = 0
        self.bets_since_approval = 0
        self.cycle_count = 0
        self._last_resolved_count = self._count_resolved()

        # Core modules
        self.scanner = MarketScanner(config.scanner)
        self.ai = AIAnalyst(config.ai)
        self.risk = RiskManager(config.risk)
        self.portfolio = Portfolio(initial_bankroll=config.initial_bankroll)

        # Signal enhancers
        self.news_scanner = NewsScanner()
        self.manip_guard = ManipulationGuard()
        self.cycle_timer = CycleTimer(config.cycle)

        # Logging & notifications
        self.trade_log = TradeLogger(config.logging.trades_file)
        self.portfolio_log = TradeLogger(config.logging.portfolio_file)
        self.notifier = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            enabled=config.notifications.telegram_enabled,
        )

        # Wallet & executor (initialized for live mode only)
        self.wallet = None
        if config.mode == Mode.LIVE:
            from src.wallet import Wallet
            pk = os.getenv("POLYGON_PRIVATE_KEY", "")
            if pk:
                self.wallet = Wallet(private_key=pk)
            else:
                logger.error("LIVE mode requires POLYGON_PRIVATE_KEY in .env")
        self.executor = Executor(mode=config.mode, clob_client=None)

    def shutdown(self) -> None:
        self.running = False
        logger.info("Shutdown requested — finishing current cycle")

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
                self.notifier.send(f"*Takvim Hatırlatma*\n{message}")
                logger.info("Milestone reminder sent: Day %d", day_number)
                break
        else:
            # No exact match — send daily status on non-milestone days
            if day_number > 0:
                self.notifier.send(
                    f"*Günlük Durum — {day_number}. gün*\n"
                    f"Bakiye: `${self.portfolio.bankroll:.2f}`\n"
                    f"Pozisyon: `{len(self.portfolio.positions)}`\n"
                    f"API bütçe: `${self.ai.budget_remaining_usd:.2f}`"
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
                f"*Bot durdu — {self.bets_since_approval} bet tamamlandı*\n"
                f"Onay bekleniyor. Devam etmek için /resume gönderin."
            )
            logger.warning("Bet limit reached (%d). Paused for approval.", self.bets_since_approval)
            self.bets_since_approval = 0

    def _count_resolved(self) -> int:
        """Count resolved predictions in calibration file."""
        cal = Path("logs/calibration.jsonl")
        if not cal.exists():
            return 0
        return sum(1 for line in cal.read_text(encoding="utf-8").strip().split("\n") if line.strip())

    def _check_self_improve_ready(self) -> None:
        """Notify via Telegram when enough new data exists for self-improvement."""
        current = self._count_resolved()
        new_resolved = current - self._last_resolved_count
        if new_resolved >= 15:
            self.notifier.send(
                f"\U0001f9ea *Self-Improve Hazir*\n"
                f"\U0001f4c8 {new_resolved} yeni resolved prediction\n"
                f"\U0001f4ca Toplam: {current} resolved\n"
                f"\U0001f449 Claude Code'da `/self-improve` calistirin"
            )
            self._last_resolved_count = current
            logger.info("Self-improve readiness notification sent (%d new resolved)", new_resolved)

    def run_cycle(self) -> None:
        # Skip cycle if paused
        if self._is_paused():
            return
        self.cycle_count += 1
        logger.info("=== Cycle #%d start ===", self.cycle_count)

        # 0. Daily milestone reminder + self-reflection
        self._maybe_send_milestone_reminder()
        self._maybe_run_reflection()

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

        # 2. Check resolved markets for calibration
        self._check_resolved_markets()

        # 3. Update position prices from current market data
        self._update_position_prices()

        # 4. Check stop-losses and take-profits
        for cid in self.portfolio.check_stop_losses(self.config.risk.stop_loss_pct):
            self._exit_position(cid, "stop_loss")
        for cid in self.portfolio.check_take_profits(self.config.risk.take_profit_pct):
            self._exit_position(cid, "take_profit")

        # 5. Scan markets
        markets = self.scanner.fetch()
        if not markets:
            self._log_cycle_summary(bankroll, "no qualifying markets")
            return

        # 5b. Pre-filter: remove logically impossible markets before spending AI tokens
        markets = filter_impossible_markets(markets)
        if not markets:
            self._log_cycle_summary(bankroll, "all markets filtered as impossible")
            return

        # 7. Select markets for analysis (whale pre-filter disabled — Data API requires wallet address)
        prioritized = markets[:self.config.ai.batch_size]

        # 8. Fetch news (multi-source: NewsAPI → GNews → RSS)
        _STOP_WORDS = {"will", "the", "a", "an", "is", "are", "was", "were", "be", "been",
                        "to", "of", "in", "on", "at", "by", "for", "or", "and", "not", "no",
                        "do", "does", "did", "has", "have", "had", "this", "that", "it",
                        "with", "from", "as", "but", "if", "than", "win", "before", "after",
                        "vs", "vs.", "over", "more", "most", "between"}
        market_keywords = {
            m.condition_id: [w for w in m.question.lower().split() if w not in _STOP_WORDS][:5]
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

        # 9. Skip markets already in portfolio (save API budget)
        new_markets = [m for m in prioritized if m.condition_id not in self.portfolio.positions]
        if len(new_markets) < len(prioritized):
            logger.info("Skipped %d markets already in portfolio (saved API calls)",
                        len(prioritized) - len(new_markets))
        prioritized = new_markets

        # 10. Analyze markets
        estimates = self.ai.analyze_batch(prioritized, news_context)

        # 10a. Check budget alerts
        for alert in self.ai.check_budget_alerts():
            self.notifier.send(alert)
            logger.warning("Budget alert sent: %s", alert[:60])

        # 11. Generate signals
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
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": 0, "mode": self.config.mode.value,
                    "rejected": f"MANIPULATION: {manip_check.recommendation}",
                    "manip_flags": manip_check.flags,
                })
                continue

            # Edge calculation (whale signal disabled — Data API requires wallet address)
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
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": edge, "mode": self.config.mode.value,
                    "manip_risk": manip_check.risk_level,
                })
                continue

            # Ignorance edge guard: low confidence + high edge = AI has no info,
            # defaulting to ~50% creates fake edge against extreme market prices
            if estimate.confidence == "low" and edge > 0.25:
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": edge, "mode": self.config.mode.value,
                    "rejected": f"IGNORANCE_EDGE: low confidence ({estimate.confidence}) with "
                                f"suspiciously high edge ({edge:.1%}) — AI likely has no real info",
                })
                logger.info("Ignorance edge blocked: %s | edge=%.1f%% conf=%s",
                            market.slug[:40], edge * 100, estimate.confidence)
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
                self.trade_log.log({
                    "market": market.slug, "action": direction.value,
                    "edge": edge, "rejected": f"SANITY: {sanity.reason}",
                    "mode": self.config.mode.value,
                })
                self.notifier.send(self.notifier.format_suspicious_bet(
                    market.question, direction.value, adjusted_size, edge, sanity.reason
                ))
                logger.warning("Sanity BLOCKED: %s — %s", market.slug[:40], sanity.reason)
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
            self.portfolio.add_position(
                market.condition_id, token_id, direction.value,
                market.yes_price, adjusted_size, shares, market.slug,
                market.tags[0] if market.tags else "",
                confidence=estimate.confidence,
                ai_probability=estimate.ai_probability,
            )
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
            })
            # Write human-readable reasoning log
            self._log_reasoning(
                market.question, direction.value, adjusted_size, price,
                edge, estimate, manip_check.risk_level,
            )
            self.notifier.send(
                f"\U0001f3af *Cycle #{self.cycle_count} — Trade*\n"
                f"{market.question}\n"
                f"\U0001f4cd `{direction.value}` | \U0001f4b5 `${adjusted_size:.0f}` @ `{price:.3f}` | "
                f"\U0001f4c8 Edge: `{edge:.1%}`"
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

    def _exit_position(self, condition_id: str, reason: str) -> None:
        pos = self.portfolio.remove_position(condition_id)
        if not pos:
            return
        result = self.executor.place_exit_order(pos.token_id, pos.shares)
        self.portfolio.record_realized(pos.unrealized_pnl_usdc)
        self.risk.record_outcome(win=pos.unrealized_pnl_usdc > 0)
        self.trade_log.log({
            "market": pos.slug, "action": "EXIT",
            "reason": reason, "pnl": pos.unrealized_pnl_usdc,
            "mode": self.config.mode.value, "status": result.get("status", ""),
        })
        pnl_emoji = "\u2705" if pos.unrealized_pnl_usdc >= 0 else "\u274c"
        pnl_sign = "+" if pos.unrealized_pnl_usdc >= 0 else ""
        self.notifier.send(
            f"\U0001f6aa *Cycle #{self.cycle_count} — Exit ({reason})*\n"
            f"{pos.slug}\n"
            f"{pnl_emoji} PnL: `{pnl_sign}${pos.unrealized_pnl_usdc:.2f}`"
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
        for cid, pos in self.portfolio.positions.items():
            try:
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"conditionId": cid}, timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                if data:
                    prices = json.loads(data[0].get("outcomePrices", '["0.5","0.5"]'))
                    new_yes_price = float(prices[0])
                    self.portfolio.update_price(cid, new_yes_price)
            except Exception as e:
                logger.debug("Price update failed for %s: %s", pos.slug[:30], e)

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
        self.portfolio_log.log({
            "bankroll": bankroll,
            "positions": len(self.portfolio.positions),
            "unrealized_pnl": self.portfolio.total_unrealized_pnl(),
            "realized_pnl": self.portfolio.realized_pnl,
            "realized_wins": self.portfolio.realized_wins,
            "realized_losses": self.portfolio.realized_losses,
            "hwm": self.portfolio.high_water_mark,
            "status": status,
        })

    def run(self) -> None:
        logger.info("Agent starting in %s mode", self.config.mode)
        pos_count = len(self.portfolio.positions)
        self.notifier.send(
            "\U0001f7e2 *Agent Online* | `{mode}`\n"
            "\U0001f4b0 `${bank:.2f}` | \U0001f4ca {pos} pozisyon | "
            "\U0001f916 API: `${api:.2f}`".format(
                mode=self.config.mode.value,
                bank=self.portfolio.bankroll,
                pos=pos_count,
                api=self.ai.budget_remaining_usd,
            )
        )
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

            interval = self.cycle_timer.get_interval()
            logger.info("Next cycle in %d min", interval)
            for tick in range(interval * 60):
                if not self.running:
                    break
                # Poll Telegram commands every 5 seconds
                if tick % 5 == 0:
                    self.notifier.handle_commands(self)
                time.sleep(1)

        self.notifier.send(
            f"\U0001f534 *Agent Offline* | {self.cycle_count} cycle\n"
            f"\U0001f4b0 `${self.portfolio.bankroll:.2f}` | "
            f"\U0001f4ca {len(self.portfolio.positions)} pozisyon"
        )
        logger.info("Agent stopped")


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
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
