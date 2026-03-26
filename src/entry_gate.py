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
import re
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
    from src.scout_scheduler import ScoutScheduler
    from src.sports_data import SportsDataClient

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
        sports: "SportsDataClient | None" = None,
        scout: "ScoutScheduler | None" = None,
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
        self.sports = sports
        self.scout = scout
        from src.thesportsdb import TheSportsDBClient
        self.tsdb = TheSportsDBClient()

        # Per-session state (survives across cycles)
        self._far_market_ids: set[str] = set()
        self._analyzed_market_ids: dict[str, float] = self._load_recent_analyses()
        self._eligible_cache: list = []
        self._eligible_pointer: int = 0
        self._eligible_cache_ts: float = 0.0
        self._seen_market_ids: set[str] = set()
        self._breaking_news_detected: bool = False

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
            markets = [m for m in markets if not blacklist.is_blocked(m.condition_id, cycle_count)]
        markets = [m for m in markets if m.condition_id not in exited_markets]

        estimates: dict = {}

        if analyze:
            # Prioritize + fetch external data + run AI batch
            markets, estimates = self._analyze_batch(markets, cycle_count)
        else:
            # Stock queue: pull estimates from candidate dicts (no AI cost)
            stock_by_cid: dict[str, dict] = {}
            for c in self._candidate_stock:
                mkt = c.get("market")
                cid_key = mkt.condition_id if mkt else c.get("condition_id", "")
                if cid_key:
                    stock_by_cid[cid_key] = c
            estimates = {
                cid_key: c["estimate"]
                for cid_key, c in stock_by_cid.items()
                if c.get("estimate")
            }

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

        # Stop-words for keyword extraction (match old main.py behaviour)
        _STOP_WORDS = frozenset({
            "will", "the", "a", "an", "in", "at", "to", "of", "or", "and", "for",
            "be", "is", "are", "was", "were", "on", "by", "with", "it", "its",
            "this", "that", "have", "has", "had", "do", "did", "not", "but",
            "if", "as", "from", "up", "out", "no", "yes", "so", "what", "which",
            "who", "when", "their", "they", "we", "he", "she", "more", "most",
            "than", "then", "win", "beat", "vs", "versus", "match", "game",
            "series", "championship", "cup", "league", "tournament", "over",
            "under", "top", "next", "first", "last", "best", "team", "player",
            "season", "week", "day", "month", "year", "time", "get", "go", "make",
            "take", "come", "see", "know", "think", "how", "any", "all", "been",
            "would", "could", "should", "about", "after", "before", "during",
            "between", "through", "become", "finish", "place", "round", "stage",
            "group", "qualify", "advance", "reach", "lose", "winner", "final",
            "semi", "quarter", "into", "also", "each", "other", "these",
        })

        # Fetch esports contexts
        esports_contexts: dict = {}
        try:
            _esports_tmp: dict = {}
            for _m in prioritized:
                _ctx = self.esports.get_match_context(
                    getattr(_m, "question", ""),
                    [getattr(_m, "sport_tag", "") or ""],
                )
                if _ctx is not None:
                    _esports_tmp[_m.condition_id] = _ctx
            esports_contexts = _esports_tmp
        except Exception as exc:
            logger.warning("Esports context fetch failed: %s", exc)

        # Scout inject: match scouted events → inject sports_context into esports_contexts
        if self.scout:
            for _m in prioritized:
                _scout_entry = self.scout.match_market(
                    getattr(_m, "question", ""), _m.slug or ""
                )
                if _scout_entry and _m.condition_id not in esports_contexts:
                    # Extract pre-fetched string; dict would crash ai_analyst .lower() calls
                    _ctx_str = _scout_entry.get("sports_context") or (
                        f"=== SCOUTED MATCH ===\n"
                        f"{_scout_entry.get('team_a', '?')} vs {_scout_entry.get('team_b', '?')}\n"
                        f"League: {_scout_entry.get('league_name', '?')}\n"
                        f"Match time: {_scout_entry.get('match_time', '?')[:16]}"
                    )
                    esports_contexts[_m.condition_id] = _ctx_str
                    logger.info("Scout context injected: %s", _m.slug[:40])

        # Traditional sports context: ESPN + TheSportsDB fallback for non-esports markets
        if self.sports:
            for _m in prioritized:
                if _m.condition_id in esports_contexts:
                    continue  # Already covered by esports/scout
                _is_esports_mkt = is_esports_slug(_m.slug or "")
                if _is_esports_mkt:
                    continue  # Skip esports (handled above)
                try:
                    _ctx = self.sports.get_match_context(
                        getattr(_m, "question", ""), _m.slug or "", []
                    )
                    if not _ctx:
                        # Fallback: TheSportsDB (international teams, qualifiers)
                        _ctx = self.tsdb.get_match_context(getattr(_m, "question", ""))
                    if _ctx:
                        esports_contexts[_m.condition_id] = _ctx
                        logger.info("Sports context fetched (%s): %s",
                                    "ESPN" if "ESPN" in _ctx else "TheSportsDB",
                                    _m.slug[:40])
                except Exception as _exc:
                    logger.debug("Sports context fetch error for %s: %s", _m.slug[:40], _exc)

        # Fetch news contexts (stop-word filtered keywords → topic grouping works correctly)
        news_context_by_market: dict[str, str] = {}
        self._breaking_news_detected = False
        try:
            market_keywords: dict[str, list[str]] = {}
            for m in prioritized:
                q = getattr(m, "question", "") or m.slug or ""
                words = re.sub(r"[^\w\s]", " ", q.lower()).split()
                kws = [w for w in words if w not in _STOP_WORDS and len(w) > 2][:5]
                market_keywords[m.condition_id] = kws if kws else [(m.slug or q)[:20]]

            raw_news: dict[str, list] = (
                self.news_scanner.search_for_markets(market_keywords) if prioritized else {}
            )

            # Detect breaking news for cycle_timer signal (checked by agent after run())
            self._breaking_news_detected = any(
                any(a.get("is_breaking") for a in arts)
                for arts in raw_news.values()
            )

            # Convert raw article lists → AI-ready text strings
            news_context_by_market = {
                cid: self.news_scanner.build_news_context(arts)
                for cid, arts in raw_news.items()
            }
        except Exception as exc:
            logger.warning("News fetch failed: %s", exc)

        # Filter: only markets with any data (sports context OR news)
        # Odds API is NOT used here — it's an anchor, not a data gate check.
        # esports_contexts holds ALL sports context (esports + scout + ESPN + TheSportsDB).
        _has_data: list = []
        for m in prioritized:
            has_sports_ctx = bool(esports_contexts.get(m.condition_id))
            has_news = bool(news_context_by_market.get(m.condition_id))
            if has_sports_ctx or has_news:
                _has_data.append(m)

        if not _has_data:
            logger.info("No markets with data — skipping AI batch")
            return [], {}

        # Run AI batch — returns List[AIEstimate] in same order as _has_data
        _estimates_list = self.ai.analyze_batch(
            _has_data, "", esports_contexts, news_by_market=news_context_by_market
        )
        estimates: dict = {
            m.condition_id: est
            for m, est in zip(_has_data, _estimates_list)
        }

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
        """Evaluate each market using three-mode strategy. Return ranked candidate list."""
        from src.edge_calculator import scale_min_edge
        from src.probability_engine import calculate_anchored_probability, get_edge_threshold_adjustment
        from src.sanity_check import check_bet_sanity
        from src.models import Direction

        cfg = self.config
        candidates: list[dict] = []
        _CONF_SKIP = {"C", "", "?"}
        _WINNER_UNDERDOG_CONF = {"A", "B+"}  # B- not allowed in winner/underdog modes

        # Fill-ratio edge scaling
        fill_ratio = self.portfolio.active_position_count / max(1, cfg.risk.max_positions)
        effective_min_edge = cfg.edge.min_edge
        if cfg.edge.fill_ratio_scaling:
            effective_min_edge = scale_min_edge(cfg.edge.min_edge, fill_ratio)

        # Mode priority constant (defined once, not per-iteration)
        _MODE_PRIORITY = {"WINNER": 4, "DEADZONE": 3, "UNDERDOG": 2, "HOLD": 1}

        for market in markets:
            cid = market.condition_id

            estimate = estimates.get(cid)
            if estimate is None:
                continue
            if estimate.confidence in _CONF_SKIP:
                continue

            # ── Bookmaker anchor (cached — batch refresh 4x/day via OddsAPIClient) ─
            # get_bookmaker_odds() fetches all events for a sport in 1 call and caches.
            # Cache only invalidates at scheduled refresh hours (7,15,19,21 UTC).
            _is_esports_mkt = is_esports(getattr(market, "sport_tag", "") or "")
            _anchor_book_prob = None
            _anchor_num_books = 0
            if not _is_esports_mkt and self.odds_api.available:
                try:
                    _mkt_odds = self.odds_api.get_bookmaker_odds(
                        market.question, market.slug or "", market.tags or []
                    )
                    if _mkt_odds:
                        # P(YES) = bookmaker_prob_a if question is about team A winning
                        _anchor_book_prob = _mkt_odds.get("bookmaker_prob_a")
                        _anchor_num_books = _mkt_odds.get("num_bookmakers", 0)
                except Exception:
                    pass
            anchored = calculate_anchored_probability(
                ai_prob=estimate.ai_probability,
                bookmaker_prob=_anchor_book_prob,
                num_bookmakers=_anchor_num_books,
            )
            _edge_threshold_adj = get_edge_threshold_adjustment(anchored)
            threshold = effective_min_edge + _edge_threshold_adj

            # ── Three-mode classifier ─────────────────────────────────────────
            ai_p = anchored.probability          # P(YES)
            ai_n = 1.0 - ai_p                   # P(NO)
            mkt_p = market.yes_price             # market P(YES)
            mkt_n = 1.0 - mkt_p

            edge_yes = ai_p - mkt_p             # positive → YES has value
            edge_no = ai_n - mkt_n              # positive → NO has value

            def _classify_side(direction_prob: float, direction_edge: float) -> str:
                if direction_prob >= 0.65:
                    return "WINNER"
                if direction_prob >= 0.50 and direction_edge >= threshold:
                    return "DEADZONE"
                if direction_prob < 0.50 and direction_edge >= threshold:
                    return "UNDERDOG"
                return "HOLD"

            yes_mode = _classify_side(ai_p, edge_yes)
            no_mode = _classify_side(ai_n, edge_no)

            # Pick direction: higher mode priority wins; ties broken by edge size
            if _MODE_PRIORITY[yes_mode] > _MODE_PRIORITY[no_mode]:
                direction = Direction.BUY_YES
                mode = yes_mode
                edge = edge_yes
                direction_prob = ai_p
            elif _MODE_PRIORITY[no_mode] > _MODE_PRIORITY[yes_mode]:
                direction = Direction.BUY_NO
                mode = no_mode
                edge = edge_no
                direction_prob = ai_n
            else:
                # Equal mode: pick direction with larger edge
                if edge_yes >= edge_no:
                    direction = Direction.BUY_YES
                    mode = yes_mode
                    edge = edge_yes
                    direction_prob = ai_p
                else:
                    direction = Direction.BUY_NO
                    mode = no_mode
                    edge = edge_no
                    direction_prob = ai_n

            if mode == "HOLD":
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge_yes": round(edge_yes, 4), "edge_no": round(edge_no, 4),
                })
                self._analyzed_market_ids[cid] = time.time()
                continue

            # ── Sanity check (after direction is known) ──────────────────────
            sanity_result = check_bet_sanity(
                question=getattr(market, "question", ""),
                direction=direction.value,
                ai_probability=estimate.ai_probability,
                market_price=market.yes_price,
                edge=0.0,
                confidence=estimate.confidence,
            )
            if not sanity_result.ok:
                self.trade_log.log({
                    "market": market.slug, "action": "BLOCKED",
                    "question": market.question,
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "rejected": f"SANITY: {sanity_result.reason}",
                })
                continue

            # ── Confidence gate (mode-specific) ──────────────────────────────
            if mode in ("WINNER", "UNDERDOG") and estimate.confidence not in _WINNER_UNDERDOG_CONF:
                logger.info("%s mode requires A/B+, got %s: %s",
                            mode, estimate.confidence, market.slug[:40])
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"{mode}_CONF_GATE: conf={estimate.confidence} (need A/B+)",
                })
                continue

            # ── Esports underdog guard ────────────────────────────────────────
            if is_esports(getattr(market, "sport_tag", "") or ""):
                if direction == Direction.BUY_YES and ai_p < 0.50 and mode != "UNDERDOG":
                    self.trade_log.log({
                        "market": market.slug, "action": "HOLD",
                        "rejected": f"ESPORTS_UNDERDOG_NO_EDGE: AI={ai_p:.0%}",
                    })
                    continue

            # ── FAR market: require minimum edge ─────────────────────────────
            if cid in self._far_market_ids and mode != "WINNER" and edge < 0.08:
                logger.info("FAR market edge too low (%.1f%% < 8%%): %s",
                            edge * 100, market.slug[:40])
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"FAR_LOW_EDGE: {edge*100:.1f}% < 8%",
                })
                continue

            # ── Position sizing ───────────────────────────────────────────────
            # Winner mode: use floor edge (0.05) so Kelly stays positive
            sizing_edge = edge if mode != "WINNER" else max(edge, 0.05)
            manip_check = self.manip_guard.check_market(market, estimate)
            adjusted_size = self.risk.calculate_position_size(
                edge=sizing_edge, bankroll=bankroll, confidence=estimate.confidence,
            )
            adjusted_size = self.manip_guard.adjust_position_size(adjusted_size, manip_check)

            # ── Rank score ────────────────────────────────────────────────────
            conf_score = _CONF_SCORE.get(estimate.confidence, 1)
            if mode == "WINNER":
                rank_score = direction_prob * conf_score
            else:
                rank_score = edge * direction_prob * conf_score

            logger.info(
                "%s mode: %s | AI=%.0f%% mkt=%.0f%% edge=%.1f%% conf=%s score=%.3f",
                mode, market.slug[:35],
                direction_prob * 100,
                mkt_p * 100 if direction == Direction.BUY_YES else mkt_n * 100,
                edge * 100, estimate.confidence, rank_score,
            )

            candidates.append({
                "score": rank_score,
                "mode": mode,
                "market": market,
                "estimate": estimate,
                "direction": direction,
                "edge": edge,
                "direction_prob": direction_prob,
                "adjusted_size": adjusted_size,
                "sanity": sanity_result,
                "manip_check": manip_check,
                "is_consensus": False,
                "entry_reason": mode.lower(),
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
