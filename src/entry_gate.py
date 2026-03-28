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
        from src.football_data import FootballDataClient
        self.football_data = FootballDataClient()
        from src.cricket_data import CricketDataClient
        self.cricket_data = CricketDataClient()

        # Per-session state (survives across cycles)
        self._far_market_ids: set[str] = set()
        self._analyzed_market_ids: dict[str, float] = self._load_recent_analyses()
        self._eligible_cache: list = []
        self._eligible_pointer: int = 0
        self._eligible_cache_ts: float = 0.0
        self._seen_market_ids: set[str] = set()
        self._confidence_c_cids: set[str] = set()  # Markets that got conf=C — never re-analyze
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

    def reset_seen_markets(self) -> None:
        """Reset seen market tracking. Call at start of each fresh heavy cycle (not refill)."""
        self._seen_market_ids.clear()

    def invalidate_cache(self, condition_id: str) -> None:
        """Remove a market from the AI analysis cache (e.g., after price drift reanalysis)."""
        self._analyzed_market_ids.pop(condition_id, None)

    # ── Analysis phase ─────────────────────────────────────────────────────

    def _analyze_batch(self, markets: list, cycle_count: int) -> tuple[list, dict]:
        """Prioritize markets, fetch external data, run AI batch. Return (markets, estimates)."""
        cfg = self.config

        # Stock IDs (don't re-analyze markets already in candidate stock)
        _stock_ids = {c.get("condition_id", "") for c in self._candidate_stock}

        # Active portfolio positions (don't re-analyze markets we already hold)
        _active_cids = set(self.portfolio.positions.keys())

        # Skip stock-queued, already-analyzed, active positions, and conf=C blacklisted
        markets = [
            m for m in markets
            if m.condition_id not in _stock_ids
            and m.condition_id not in self._seen_market_ids
            and m.condition_id not in _active_cids
            and m.condition_id not in self._confidence_c_cids
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

        # Track analyzed markets so refill cycles move to next batch
        self._seen_market_ids.update(m.condition_id for m in prioritized)

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

        # Odds API Bridge: match Polymarket markets to Odds API events for clean team names
        _bridge_names: dict[str, dict] = {}
        if self.odds_api and self.odds_api.available:
            try:
                for _m in prioritized:
                    if _m.condition_id in esports_contexts:
                        continue
                    if is_esports_slug(_m.slug or ""):
                        continue
                    _br = self.odds_api.bridge_match(
                        getattr(_m, "question", ""), _m.slug or "",
                        getattr(_m, "tags", []),
                    )
                    if _br:
                        _bridge_names[_m.condition_id] = _br
                if _bridge_names:
                    logger.info("Bridge matched %d/%d non-esports markets",
                                len(_bridge_names), len(prioritized))
            except Exception as exc:
                logger.warning("Bridge match failed: %s", exc)

        # Traditional sports context: Bridge->ESPN -> ESPN -> football-data.org -> CricketData -> TheSportsDB
        # Track which source provided data — only reliable sources qualify for AI analysis
        _reliable_source_cids: set[str] = set()  # Markets with ESPN/Bridge/football-data/Cricket/PandaScore
        if self.sports:
            for _m in prioritized:
                if _m.condition_id in esports_contexts:
                    _reliable_source_cids.add(_m.condition_id)  # PandaScore/Scout = reliable
                    continue
                _is_esports_mkt = is_esports_slug(_m.slug or "")
                if _is_esports_mkt:
                    continue
                try:
                    _ctx = None
                    _source = ""
                    _bridge_info = _bridge_names.get(_m.condition_id)
                    _question = getattr(_m, "question", "")
                    _slug = _m.slug or ""
                    _tags = getattr(_m, "tags", [])

                    # Kademe 1: Bridge clean names -> ESPN
                    if _bridge_info:
                        _clean_q = f"{_bridge_info['home_team']} vs {_bridge_info['away_team']}"
                        _ctx = self.sports.get_match_context(_clean_q, _slug, [])
                        if _ctx:
                            _source = "Bridge->ESPN"

                    # Kademe 2: Original question -> ESPN
                    if not _ctx:
                        _ctx = self.sports.get_match_context(_question, _slug, [])
                        if _ctx:
                            _source = "ESPN"

                    # Kademe 3: football-data.org (soccer fallback + Copa Libertadores)
                    if not _ctx and self.football_data.available:
                        if _bridge_info:
                            _clean_q = f"{_bridge_info['home_team']} vs {_bridge_info['away_team']}"
                            _ctx = self.football_data.get_match_context(_clean_q, _slug, _tags)
                        if not _ctx:
                            _ctx = self.football_data.get_match_context(_question, _slug, _tags)
                        if _ctx:
                            _source = "football-data.org"

                    # Kademe 4: CricketData (IPL, PSL, T20)
                    if not _ctx and self.cricket_data.available:
                        _ctx = self.cricket_data.get_match_context(_question, _slug, _tags)
                        if _ctx:
                            _source = "CricketData"

                    # Kademe 5: TheSportsDB fallback (supplementary only — NOT enough alone)
                    if not _ctx:
                        if _bridge_info:
                            _clean_q = f"{_bridge_info['home_team']} vs {_bridge_info['away_team']}"
                            _ctx = self.tsdb.get_match_context(_clean_q)
                        if not _ctx:
                            _ctx = self.tsdb.get_match_context(_question)
                        if _ctx:
                            _source = "TheSportsDB"

                    if _ctx:
                        esports_contexts[_m.condition_id] = _ctx
                        logger.info("Sports context fetched (%s): %s", _source, _slug[:40])
                        # Only mark as reliable if from a primary source (not TheSportsDB alone)
                        if _source != "TheSportsDB":
                            _reliable_source_cids.add(_m.condition_id)
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

        # Filter: only markets with RELIABLE sports data qualify for AI analysis.
        # TheSportsDB alone is NOT enough (weak data → confidence C → wasted tokens).
        # News alone is NOT enough either (no team stats → AI can't assess winner).
        # Reliable = ESPN, Bridge->ESPN, football-data.org, CricketData, PandaScore, Scout.
        _has_data: list = []
        _no_reliable_skipped = 0
        for m in prioritized:
            if m.condition_id in _reliable_source_cids:
                _has_data.append(m)
            else:
                _no_reliable_skipped += 1
        if _no_reliable_skipped:
            logger.info("Skipped %d markets without reliable sports data (saves AI tokens)", _no_reliable_skipped)

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
        from src.probability_engine import calculate_anchored_probability
        from src.models import Direction

        cfg = self.config
        candidates: list[dict] = []
        _CONF_SKIP = {"C", "", "?"}  # C = veri yetersiz, skip

        for market in markets:
            cid = market.condition_id

            estimate = estimates.get(cid)
            if estimate is None:
                continue
            if estimate.confidence in _CONF_SKIP:
                logger.info("SKIP confidence: %s | conf=%s (insufficient data)",
                            market.slug[:35], estimate.confidence)
                self._confidence_c_cids.add(cid)  # Blacklist — don't re-analyze this session
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"Insufficient data (conf={estimate.confidence})",
                    "ai_prob": estimate.ai_probability,
                    "price": market.yes_price,
                    "question": getattr(market, "question", ""),
                })
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
            # ── Two-case strategy: consensus vs disagree ─────────────────
            ai_p = estimate.ai_probability     # Raw AI P(YES) — before anchoring
            ai_n = 1.0 - ai_p                  # Raw AI P(NO)
            mkt_p = market.yes_price            # Market P(YES)
            mkt_n = 1.0 - mkt_p                # Market P(NO)

            # Determine favorites
            ai_favors_yes = ai_p >= 0.50
            mkt_favors_yes = mkt_p >= 0.50
            is_consensus = ai_favors_yes == mkt_favors_yes

            if is_consensus:
                # CASE A: AI and market agree on favorite
                # Direction = favorite side. Edge = payout potential (99¢ - entry).
                # Use raw AI probability (skip shrinkage — market already confirms).
                if ai_favors_yes:
                    direction = Direction.BUY_YES
                    direction_prob = ai_p
                    entry_price = mkt_p
                else:
                    direction = Direction.BUY_NO
                    direction_prob = ai_n
                    entry_price = mkt_n
                edge = 0.99 - entry_price
            else:
                # CASE B: AI and market disagree on favorite
                # Use anchored (shrunk) probability. Standard edge calculation.
                ai_p_anchored = anchored.probability
                ai_n_anchored = 1.0 - ai_p_anchored
                edge_yes = ai_p_anchored - mkt_p
                edge_no = ai_n_anchored - mkt_n

                if ai_p_anchored >= ai_n_anchored:
                    direction = Direction.BUY_YES
                    direction_prob = ai_p_anchored
                    edge = edge_yes
                else:
                    direction = Direction.BUY_NO
                    direction_prob = ai_n_anchored
                    edge = edge_no

            # Mode classification by direction probability
            if direction_prob < 0.55:
                logger.info("SKIP prob: %s | prob=%.0f%% conf=%s (< 55%%)",
                            market.slug[:35], direction_prob * 100, estimate.confidence)
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"Low probability ({direction_prob*100:.0f}% < 55%)",
                    "ai_prob": estimate.ai_probability,
                    "edge": edge if 'edge' in dir() else 0,
                    "price": market.yes_price,
                    "question": getattr(market, "question", ""),
                })
                continue
            elif direction_prob >= 0.65:
                mode = "WINNER"
            else:
                # Deadzone (55-65%) disabled — historically net negative
                logger.info("SKIP deadzone: %s | prob=%.0f%% (55-65%% zone)",
                            market.slug[:35], direction_prob * 100)
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"Deadzone ({direction_prob*100:.0f}% in 55-65%)",
                    "ai_prob": estimate.ai_probability,
                    "edge": edge,
                    "price": market.yes_price,
                    "question": getattr(market, "question", ""),
                })
                continue

            # ── Liquidity gate (confidence-aware) ────────────────────────────
            # High-confidence entries (prob≥65%, conf B+/A) hold to resolution
            # so orderbook depth doesn't matter. Lower confidence needs $1K+.
            _high_conf = estimate.confidence in {"A", "B+"}
            _high_prob = direction_prob >= 0.65
            _liq_val = getattr(market, 'liquidity', 0) or 0
            _low_liq = isinstance(_liq_val, (int, float)) and _liq_val < 1_000
            if _low_liq and not (_high_conf and _high_prob):
                logger.info("SKIP liquidity: %s | liq=$%.0f conf=%s prob=%.0f%%",
                            market.slug[:35], getattr(market, 'liquidity', 0),
                            estimate.confidence, direction_prob * 100)
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"Low liquidity (${getattr(market, 'liquidity', 0):.0f})",
                    "ai_prob": estimate.ai_probability,
                    "edge": edge,
                    "price": market.yes_price,
                    "question": getattr(market, "question", ""),
                })
                continue

            # ── Position sizing (confidence-based, no edge dependency) ────────
            manip_check = self.manip_guard.check_market(
                question=market.question,
                description=getattr(market, 'description', ''),
                liquidity=getattr(market, 'liquidity', 0),
            )
            from src.models import Signal
            signal = Signal(
                condition_id=cid,
                direction=direction,
                ai_probability=ai_p,
                market_price=mkt_p,
                edge=edge,
                confidence=estimate.confidence,
            )
            risk_decision = self.risk.evaluate(
                signal=signal,
                bankroll=bankroll,
                open_positions=self.portfolio.positions,
            )
            adjusted_size = risk_decision.size_usdc
            adjusted_size = self.manip_guard.adjust_position_size(adjusted_size, manip_check)

            # ── Rank score — edge + prob + confidence ─────────────────────────
            # Higher edge = higher priority. Negative edge already filtered above.
            conf_score = _CONF_SCORE.get(estimate.confidence, 1)
            rank_score = (direction_prob + edge) * conf_score

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
                "manip_check": manip_check,
                "is_consensus": is_consensus,
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
        from src.models import Direction
        entered: list[str] = []
        cfg = self.config

        # Collect event_ids already in portfolio to prevent same-event dual-side
        entered_event_ids: set[str] = set()
        for pos in self.portfolio.positions.values():
            eid = getattr(pos, "event_id", "") or ""
            if eid:
                entered_event_ids.add(eid)

        for c in candidates:
            market = c["market"]
            cid = market.condition_id
            direction = c["direction"]
            size = c["adjusted_size"]
            estimate = c["estimate"]

            # Same-event dual-side check — never enter both sides of same match
            market_event_id = getattr(market, "event_id", "") or ""
            if market_event_id and market_event_id in entered_event_ids:
                logger.info("SKIP same-event: %s | event_id=%s already in portfolio",
                            market.slug[:35], market_event_id[:20])
                continue

            # Slot check
            open_slots = cfg.risk.max_positions - self.portfolio.active_position_count
            if open_slots <= 0:
                break

            # Min bet check
            if size < 5.0:  # Polymarket minimum order size
                continue

            # Execute
            _token_id = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
            _order_price = market.yes_price if direction == Direction.BUY_YES else (1 - market.yes_price)
            result = self.executor.place_order(
                token_id=_token_id,
                side="BUY",
                price=_order_price,
                size_usdc=size,
            )
            if not result or result.get("status") == "error":
                logger.warning("Order failed: %s — %s", market.slug[:40], result)
                continue

            # Record position — entry_price is always YES-side for storage consistency
            entry_price = market.yes_price
            eff_price = (1 - entry_price) if direction == Direction.BUY_NO else entry_price
            shares = size / eff_price if eff_price > 0 else 0
            _token_id_for_pos = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
            self.portfolio.add_position(
                condition_id=cid,
                slug=market.slug,
                question=getattr(market, "question", ""),
                token_id=_token_id_for_pos,
                direction=direction.value if hasattr(direction, "value") else direction,
                entry_price=entry_price,
                size_usdc=size,
                shares=shares,
                ai_probability=estimate.ai_probability,
                confidence=estimate.confidence,
                sport_tag=getattr(market, "sport_tag", "") or "",
                event_id=getattr(market, "event_id", "") or "",
                end_date_iso=getattr(market, "end_date_iso", "") or "",
                entry_reason=c.get("entry_reason", ""),
                is_consensus=c.get("is_consensus", False),
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

            # Track event_id so we don't enter other side in same cycle
            if market_event_id:
                entered_event_ids.add(market_event_id)

            # Notify on entry
            _eff_p = (1 - entry_price) if direction == Direction.BUY_NO else entry_price
            _dir_label = "YES" if direction == Direction.BUY_YES else "NO"
            _hrs = _hours_to_start(market)
            _time_label = "LIVE" if _hrs <= 0 else f"{_hrs:.0f}h" if _hrs < 24 else f"{_hrs/24:.0f}d"
            _sport = getattr(market, "sport_tag", "") or "?"
            _consensus_label = "Consensus" if c.get("is_consensus") else "Disagree"
            self.notifier.send(
                f"📈 *ENTRY*: {market.slug[:40]}\n"
                f"Entry {_dir_label} @ {_eff_p:.0%} | AI {estimate.ai_probability:.0%}\n\n"
                f"🏷 {_sport} | {_consensus_label}\n"
                f"🎯 Conf: {estimate.confidence}\n"
                f"📊 Edge: {c['edge']:.1%}\n"
                f"💰 Size: ${size:.2f}\n"
                f"⏱ {_time_label}"
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
