"""entry_gate.py — Unified market entry pipeline.

ALL entry types (normal, FAR, FAV, consensus) go through this single gate.
Entry type only changes sizing multiplier and slot count — same sanity check
for everyone. FAR markets no longer bypass sanity (fixes known bug).

Data flow:
  agent.py calls:
    entry_gate.run(fresh_markets, entries_allowed=True, analyze=True)   # heavy cycle
    entry_gate.run(stock_queue,   entries_allowed=True, analyze=False)  # stock drain

  run() flow:
    if not entries_allowed → return []
    if analyze → prioritize + fetch data + AI batch
    for each market → sanity + esports rules + edge/consensus → candidates
    assert entries_allowed or len(candidates) == 0  ← safety guard
    execute top N → return entered condition_ids
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import requests

from src.sport_rules import is_esports, is_esports_slug

if TYPE_CHECKING:
    from src.config import AppConfig
    from src.portfolio import Portfolio
    from src.executor import Executor
    from src.ai_analyst import AIAnalyst
    from src.market_scanner import MarketScanner
    from src.risk_manager import RiskManager
    from src.odds_api import OddsAPIClient
    from src.esports_data import EsportsDataClient
    from src.news_scanner import NewsScanner
    from src.manipulation_guard import ManipulationGuard
    from src.trade_logger import TradeLogger
    from src.notifier import TelegramNotifier

logger = logging.getLogger(__name__)

# Confidence score for ranking (A=4, B+=3, B-=2, C=1)
_CONF_SCORE: dict[str, int] = {"A": 4, "B+": 3, "B-": 2, "C": 1}
_SKIP_CONFIDENCE: set[str] = {"C", "", "?"}


class EntryGate:
    """Single unified market entry pipeline.

    Instantiate once. Stateful: owns market cache, AI analysis cache,
    candidate stock queues, and far_market_ids.
    """

    def __init__(
        self,
        config: "AppConfig",
        portfolio: "Portfolio",
        executor: "Executor",
        ai: "AIAnalyst",
        scanner: "MarketScanner",
        risk: "RiskManager",
        odds_api: "OddsAPIClient",
        esports: "EsportsDataClient",
        news_scanner: "NewsScanner",
        manip_guard: "ManipulationGuard",
        trade_log: "TradeLogger",
        notifier: "TelegramNotifier",
    ) -> None:
        self.config = config
        self.portfolio = portfolio
        self.executor = executor
        self.ai = ai
        self.scanner = scanner
        self.risk = risk
        self.odds_api = odds_api
        self.esports = esports
        self.news_scanner = news_scanner
        self.manip_guard = manip_guard
        self.trade_log = trade_log
        self.notifier = notifier

        # Per-session state (survives across cycles)
        self._far_market_ids: set[str] = set()
        self._analyzed_market_ids: dict[str, float] = self._load_recent_analyses()
        self._eligible_cache: list = []
        self._eligible_pointer: int = 0
        self._eligible_cache_ts: float = 0.0
        self._seen_market_ids: set[str] = set()

        # Candidate stock queues (pre-analyzed, waiting for slots)
        self._candidate_stock: list[dict] = []
        self._fav_stock: list[dict] = []
        self._far_stock: list[dict] = []

    # ── Public API ─────────────────────────────────────────────────────────

    def run(
        self,
        markets: list,
        entries_allowed: bool,
        analyze: bool = True,
        bankroll: float = 0.0,
        cycle_count: int = 0,
        blacklist=None,
        exited_markets: set | None = None,
    ) -> list[str]:
        """Run the entry pipeline. Return list of entered condition_ids.

        Args:
            markets: MarketData objects to evaluate.
            entries_allowed: False → skip all entries immediately.
            analyze: True → run AI batch. False → use cached estimates (stock queue).
            bankroll: Current USDC bankroll for sizing.
            cycle_count: Current cycle number (for cooldown checks).
            blacklist: Blacklist object for filtering.
            exited_markets: Set of cids that have been permanently exited.
        """
        if not entries_allowed:
            return []

        if not markets:
            return []

        cfg = self.config
        exited_markets = exited_markets or set()

        # Filter out blacklisted and permanently exited markets
        if blacklist:
            markets = [m for m in markets if not blacklist.is_blocked(m.condition_id)]
        markets = [m for m in markets if m.condition_id not in exited_markets]

        estimates: dict = {}

        if analyze:
            # Prioritize + fetch external data + run AI batch
            markets, estimates = self._analyze_batch(markets, cycle_count)
        else:
            # Stock queue: use cached AI estimates (no AI cost)
            for m in markets:
                cid = m.condition_id
                if cid in self._analyzed_market_ids:
                    # Estimate was already stored when market was analyzed;
                    # for stock queue, the candidate dict carries the estimate.
                    pass
            # estimates already in candidate dicts — handled in _evaluate_candidates
            estimates = {}  # signal to evaluator to use candidate.get("estimate")

        # Collect + rank candidates
        candidates = self._evaluate_candidates(markets, estimates, bankroll, cycle_count, analyze)

        # SAFETY GUARD: if somehow entries aren't allowed, candidates must be empty
        assert entries_allowed or len(candidates) == 0, (
            "BUG: candidates collected but entries_allowed=False — halt flag not propagated"
        )

        # Execute top N
        entered = self._execute_candidates(candidates, bankroll, cycle_count)
        return entered

    def drain_stock(self, entries_allowed: bool, bankroll: float, cycle_count: int,
                    blacklist=None, exited_markets: set | None = None) -> list[str]:
        """Process pre-analyzed candidate stock (analyze=False). Separate from fresh scan."""
        stock_markets = [c.get("market") for c in self._candidate_stock if c.get("market")]
        if not stock_markets:
            return []
        return self.run(
            stock_markets, entries_allowed, analyze=False,
            bankroll=bankroll, cycle_count=cycle_count,
            blacklist=blacklist, exited_markets=exited_markets,
        )

    def push_to_stock(self, candidate: dict) -> None:
        """Add a candidate to the stock queue (called by agent for demoted positions)."""
        self._candidate_stock.append(candidate)

    def invalidate_cache(self, condition_id: str) -> None:
        """Remove a market from the AI analysis cache (e.g., after price drift reanalysis)."""
        self._analyzed_market_ids.pop(condition_id, None)

    # ── Analysis phase ─────────────────────────────────────────────────────

    def _analyze_batch(self, markets: list, cycle_count: int) -> tuple[list, dict]:
        """Prioritize markets, fetch external data, run AI batch. Return (markets, estimates)."""
        cfg = self.config

        # Prune stale analysis cache (>24h old entries)
        _24h = 86400
        self._analyzed_market_ids = {
            cid: ts for cid, ts in self._analyzed_market_ids.items()
            if time.time() - ts < _24h
        }

        # Stock IDs (don't re-analyze)
        _stock_ids = {c.get("condition_id", "") for c in self._candidate_stock}

        # Skip already-analyzed markets (HOLD cache)
        markets = [
            m for m in markets
            if m.condition_id not in self._analyzed_market_ids
            and m.condition_id not in _stock_ids
        ]

        if not markets:
            return [], {}

        # Slot-based batch sizing
        open_slots = max(0, cfg.risk.max_positions - self.portfolio.active_position_count)
        stock_empty = max(0, 5 - len(self._candidate_stock))
        total_need = open_slots + stock_empty
        batch_size = min(cfg.ai.batch_size, max(5, total_need * 2))

        # Bucket markets into imminent / mid / discovery
        imminent = sorted([m for m in markets if _hours_to_start(m) <= 6], key=_hours_to_start)
        midrange  = sorted([m for m in markets if 6 < _hours_to_start(m) <= 24], key=_hours_to_start)
        discovery = sorted([m for m in markets if _hours_to_start(m) > 24], key=_hours_to_start)

        imm_available = len(imminent)
        if imm_available >= batch_size:
            prioritized = imminent[:batch_size]
        elif imm_available >= batch_size * 6 // 10:
            imm_slots = imm_available
            mid_slots = batch_size - imm_slots
            prioritized = imminent + midrange[:mid_slots]
        else:
            imm_slots = imm_available
            mid_slots = min(len(midrange), (batch_size - imm_slots) * 7 // 10)
            disc_slots = batch_size - imm_slots - mid_slots
            prioritized = imminent + midrange[:mid_slots] + discovery[:disc_slots]

        if len(prioritized) < batch_size:
            remaining = [m for m in markets if m not in prioritized]
            prioritized += remaining[:batch_size - len(prioritized)]

        # Update FAR market ids (>6h to start = FAR, needs higher edge)
        self._far_market_ids = {m.condition_id for m in prioritized if _hours_to_start(m) > 6}

        # Fetch esports contexts
        esports_contexts: dict = {}
        try:
            esports_contexts = self.esports.get_contexts_batch(prioritized) if prioritized else {}
        except Exception as exc:
            logger.warning("Esports context fetch failed: %s", exc)

        # Fetch news contexts
        news_context_by_market: dict = {}
        try:
            news_context_by_market = self.news_scanner.fetch_for_batch(prioritized) if prioritized else {}
        except Exception as exc:
            logger.warning("News fetch failed: %s", exc)

        # Filter: only markets with any data (esports OR odds OR news)
        _has_data: list = []
        for m in prioritized:
            _slug_prefix = (m.slug or "")[:8].lower()
            _is_esports_mkt = is_esports_slug(m.slug or "")
            has_odds = False
            if self.odds_api.available and not _is_esports_mkt:
                try:
                    _odds = self.odds_api.get_market_odds(m)
                    has_odds = bool(_odds)
                except Exception:
                    pass
            has_esports = bool(esports_contexts.get(m.condition_id))
            has_news = bool(news_context_by_market.get(m.condition_id))
            if has_odds or has_esports or has_news:
                _has_data.append(m)

        if not _has_data:
            logger.info("No markets with data — skipping AI batch")
            return [], {}

        # Run AI batch
        estimates = self.ai.analyze_batch(
            _has_data, "", esports_contexts, news_by_market=news_context_by_market
        )

        # Mark as analyzed (suppress re-analysis next cycle)
        for m in _has_data:
            self._analyzed_market_ids[m.condition_id] = time.time()

        return _has_data, estimates

    # ── Evaluation phase ───────────────────────────────────────────────────

    def _evaluate_candidates(
        self,
        markets: list,
        estimates: dict,
        bankroll: float,
        cycle_count: int,
        fresh_scan: bool,
    ) -> list[dict]:
        """Evaluate each market, return ranked candidate list."""
        from src.edge_calculator import calculate_edge, calculate_anchored_probability
        from src.edge_calculator import get_edge_threshold_adjustment
        from src.sanity_check import SanityChecker
        from src.models import Direction
        from src.scale_out import fill_ratio_scaling as scale_min_edge

        cfg = self.config
        sanity = SanityChecker(cfg.sanity)
        candidates: list[dict] = []
        _CONF_SKIP = {"C", "", "?"}

        # Fill-ratio edge scaling
        fill_ratio = self.portfolio.active_position_count / max(1, cfg.risk.max_positions)
        effective_min_edge = cfg.edge.min_edge
        if cfg.edge.fill_ratio_scaling:
            effective_min_edge = scale_min_edge(
                cfg.edge.min_edge, fill_ratio,
                cfg.edge.fill_ratio_aggressive,
                cfg.edge.fill_ratio_selective,
            )

        for market in markets:
            cid = market.condition_id

            # Get estimate (fresh scan → from estimates dict; stock → from candidate)
            estimate = estimates.get(cid)
            if estimate is None:
                continue
            if estimate.confidence in _CONF_SKIP:
                continue

            # ── Sanity check (ALL markets including FAR — no bypass) ────────
            sanity_result = sanity.check(market, estimate)
            if not sanity_result.passed:
                self.trade_log.log({
                    "market": market.slug, "action": "BLOCKED",
                    "question": market.question,
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "rejected": f"SANITY: {sanity_result.reason}",
                })
                continue

            # ── Anchored probability (odds_api bookmaker anchor) ───────────
            _is_esports_mkt = is_esports(getattr(market, "sport_tag", "") or "")
            _anchor_book_prob = None
            _anchor_num_books = 0
            if not _is_esports_mkt and self.odds_api.available:
                try:
                    _mkt_odds = self.odds_api.get_market_odds(market)
                    if _mkt_odds:
                        _anchor_book_prob = _mkt_odds.get("probability")
                        _anchor_num_books = _mkt_odds.get("num_bookmakers", 0)
                except Exception:
                    pass
            anchored = calculate_anchored_probability(
                ai_prob=estimate.ai_probability,
                bookmaker_prob=_anchor_book_prob,
                num_bookmakers=_anchor_num_books,
            )
            _edge_threshold_adj = get_edge_threshold_adjustment(anchored)

            # ── Edge calculation ───────────────────────────────────────────
            direction, edge = calculate_edge(
                ai_prob=anchored.probability,
                market_yes_price=market.yes_price,
                min_edge=effective_min_edge,
                confidence=estimate.confidence,
                confidence_multipliers=cfg.edge.confidence_multipliers,
                spread=cfg.edge.default_spread,
                edge_threshold_adjustment=_edge_threshold_adj,
            )

            # ── Esports-specific entry rules ───────────────────────────────
            _sport_tag = getattr(market, "sport_tag", "") or ""
            if is_esports(_sport_tag):
                # Rule 1: AI > 65% → force BUY_YES (winner override)
                if anchored.probability > 0.65 and direction in (Direction.BUY_NO, Direction.HOLD):
                    win_potential = 1.0 - market.yes_price
                    logger.info(
                        "ESPORTS_WINNER_OVERRIDE: %s | AI=%.0f%% > 65%% | was %s → BUY_YES",
                        market.slug[:40], anchored.probability * 100, direction.value,
                    )
                    direction = Direction.BUY_YES
                    edge = win_potential
                # Rule 2: AI < 50% + BUY_YES → skip (don't bet on predicted loser)
                elif direction == Direction.BUY_YES and anchored.probability < 0.50:
                    logger.info("Esports underdog skip: %s | AI=%.0f%% < 50%%",
                                market.slug[:40], anchored.probability * 100)
                    self.trade_log.log({
                        "market": market.slug, "action": "HOLD",
                        "rejected": f"ESPORTS_UNDERDOG: AI={anchored.probability:.0%} < 50%",
                    })
                    continue

            # ── Consensus entry override (HOLD → BUY if AI + market ≥65%) ─
            is_consensus = False
            entry_reason = ""
            if direction == Direction.HOLD:
                _ce = cfg.consensus_entry
                if _ce.enabled and estimate.confidence in ("A", "B+"):
                    _ai = estimate.ai_probability
                    _mp = market.yes_price
                    _cyes = _ai >= _ce.min_price and _mp >= _ce.min_price
                    _cno = (1 - _ai) >= _ce.min_price and (1 - _mp) >= _ce.min_price
                    _is_far_mkt = cid in self._far_market_ids
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
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": edge,
                })
                # Cache this HOLD to avoid re-analyzing next cycle
                # (but NOT for consensus candidates — they may qualify next cycle)
                if not is_consensus:
                    self._analyzed_market_ids[cid] = time.time()
                continue

            # ── FAR market: require higher edge ────────────────────────────
            if cid in self._far_market_ids and not is_consensus and edge < 0.08:
                logger.info("Far market edge too low (%.1f%% < 8%%): %s",
                            edge * 100, market.slug[:40])
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"FAR_LOW_EDGE: {edge*100:.1f}% < 8%",
                })
                continue

            # ── Manipulation guard + position sizing ───────────────────────
            manip_check = self.manip_guard.check(market, estimate)
            adjusted_size = self.risk.calculate_position_size(
                edge=edge, bankroll=bankroll, confidence=estimate.confidence,
            )
            adjusted_size = self.manip_guard.adjust_position_size(
                adjusted_size, manip_check,
            )

            # Consensus: fixed bet_pct (no Kelly — edge≈0)
            if is_consensus:
                _ce = cfg.consensus_entry
                adjusted_size = min(
                    _ce.bet_pct * bankroll, cfg.risk.max_single_bet_usdc,
                )

            # ── Rank score ─────────────────────────────────────────────────
            entry_price = market.yes_price if direction == Direction.BUY_YES else (1 - market.yes_price)
            _effective_edge = (1 - entry_price) if is_consensus else edge
            rank_score = (
                _effective_edge
                * _CONF_SCORE.get(estimate.confidence, 1)
            )

            candidates.append({
                "score": rank_score,
                "market": market,
                "estimate": estimate,
                "direction": direction,
                "edge": edge,
                "adjusted_size": adjusted_size,
                "sanity": sanity_result,
                "manip_check": manip_check,
                "is_consensus": is_consensus,
                "entry_reason": entry_reason,
                "is_far": cid in self._far_market_ids,
            })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates

    # ── Execution phase ────────────────────────────────────────────────────

    def _execute_candidates(
        self, candidates: list[dict], bankroll: float, cycle_count: int,
    ) -> list[str]:
        """Execute top candidates. Return list of entered condition_ids."""
        entered: list[str] = []
        cfg = self.config

        for c in candidates:
            market = c["market"]
            cid = market.condition_id
            direction = c["direction"]
            size = c["adjusted_size"]
            estimate = c["estimate"]

            # Slot check
            open_slots = cfg.risk.max_positions - self.portfolio.active_position_count
            if open_slots <= 0:
                break

            # Min bet check
            if size < cfg.risk.min_bet_usdc:
                continue

            # Execute
            result = self.executor.place_order(
                market=market,
                direction=direction,
                size_usdc=size,
                mode=cfg.mode,
            )
            if not result or not result.get("success"):
                logger.warning("Order failed: %s — %s", market.slug[:40], result)
                continue

            # Record position
            entry_price = result.get("fill_price", market.yes_price)
            self.portfolio.add_position(
                condition_id=cid,
                slug=market.slug,
                question=getattr(market, "question", ""),
                token_id=market.yes_token_id if direction == "BUY_YES" else market.no_token_id,
                direction=direction.value if hasattr(direction, "value") else direction,
                entry_price=entry_price,
                size_usdc=size,
                ai_probability=estimate.ai_probability,
                confidence=estimate.confidence,
                sport_tag=getattr(market, "sport_tag", "") or "",
                event_id=getattr(market, "event_id", "") or "",
                end_date_iso=getattr(market, "end_date_iso", "") or "",
                entry_reason=c.get("entry_reason", ""),
            )

            self.trade_log.log({
                "market": market.slug, "action": "BUY",
                "direction": direction.value if hasattr(direction, "value") else direction,
                "size_usdc": size, "entry_price": entry_price,
                "ai_prob": estimate.ai_probability,
                "confidence": estimate.confidence,
                "edge": c["edge"],
                "is_consensus": c["is_consensus"],
                "entry_reason": c.get("entry_reason", ""),
                "is_far": c["is_far"],
            })

            logger.info(
                "ENTERED: %s | dir=%s | size=$%.2f | price=%.2f | AI=%.0f%% | conf=%s%s",
                market.slug[:45], direction, size, entry_price,
                estimate.ai_probability * 100, estimate.confidence,
                " [CONSENSUS]" if c["is_consensus"] else "",
            )

            entered.append(cid)

            # Notify on entry
            self.notifier.send(
                f"📈 *ENTRY*: {market.slug[:40]}\n"
                f"dir={direction} size=${size:.2f} price={entry_price:.2f} "
                f"AI={estimate.ai_probability:.0%} conf={estimate.confidence}"
            )

        return entered

    # ── Persistence ─────────────────────────────────────────────────────────

    def _load_recent_analyses(self) -> dict[str, float]:
        """Load recent HOLD analyses from predictions.jsonl to avoid re-spending AI.

        BUY-worthy and consensus candidates are NOT cached (they re-evaluate fresh).
        """
        import json
        from pathlib import Path
        results: dict[str, float] = {}
        path = Path("logs/predictions.jsonl")
        if not path.exists():
            return results
        try:
            cutoff = time.time() - 3600 * 6  # 6h window
            _ce_min = 0.65
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = rec.get("timestamp", 0)
                    try:
                        ts = float(ts)
                    except (TypeError, ValueError):
                        continue
                    if ts < cutoff:
                        continue
                    cid = rec.get("condition_id", "")
                    if not cid:
                        continue
                    action = rec.get("action", "")
                    if action != "HOLD":
                        continue
                    # Don't cache consensus candidates
                    ai_prob = rec.get("ai_prob", 0.5)
                    mkt_price = rec.get("price", 0.5)
                    conf = rec.get("confidence", "")
                    _is_cyes = ai_prob >= _ce_min and mkt_price >= _ce_min
                    _is_cno = (1 - ai_prob) >= _ce_min and (1 - mkt_price) >= _ce_min
                    if (_is_cyes or _is_cno) and conf in ("A", "B+"):
                        continue  # potential consensus candidate → don't skip
                    results[cid] = float(ts)
        except Exception as exc:
            logger.warning("Could not load recent analyses: %s", exc)
        logger.info("Loaded %d recent HOLD analyses from predictions.jsonl", len(results))
        return results


# ── Module-level helpers ───────────────────────────────────────────────────

def _hours_to_start(market) -> float:
    """Hours until market start/end. Used for imminent/mid/discovery bucketing."""
    end_iso = getattr(market, "end_date_iso", "") or ""
    if not end_iso:
        return 99.0
    try:
        end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        return max(0.0, (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600)
    except (ValueError, TypeError):
        return 99.0
