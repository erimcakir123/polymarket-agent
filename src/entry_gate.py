"""entry_gate.py -- Unified market entry pipeline.

ALL entry types (normal, Early Entry, FAV, consensus) go through this single gate.
Entry type only changes sizing multiplier and slot count -- same sanity check
for everyone. Early Entry markets no longer bypass sanity (fixes known bug).

Data flow:
  agent.py calls:
    entry_gate.run(fresh_markets, entries_allowed=True, analyze=True)   # heavy cycle
    entry_gate.run(stock_queue,   entries_allowed=True, analyze=False)  # stock drain

  run() flow:
    if not entries_allowed -> return []
    if analyze -> prioritize + fetch data + AI batch
    for each market -> sanity + esports rules + edge/consensus -> candidates
    assert entries_allowed or len(candidates) == 0  ← safety guard
    execute top N -> return entered condition_ids
"""
from __future__ import annotations

import concurrent.futures
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from src.sport_rules import is_esports, is_esports_slug
from src.matching import match_markets as matcher_match_batch

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
    from src.sports_discovery import SportsDiscovery
    from src.sports_ws import SportsWebSocket

logger = logging.getLogger(__name__)

# Confidence score for ranking (A=4, B+=3, B-=2, C=1)
_CONF_SCORE: dict[str, int] = {"A": 4, "B+": 3, "B-": 2, "C": 1}

# Sport-aware thin data thresholds.
# Tennis/MMA: individual sports with sparse match history.
# Golf/Racing: event-based, even 1 recent result is informative.
# Default: lowered from 5 to 3 after ESPN overhaul.
_THIN_DATA_THRESHOLDS = {
    "tennis": 2,
    "mma": 2,
    "golf": 1,
    "racing": 1,
    "cricket": 3,
    "default": 3,
}


def _underdog_elapsed_size_multiplier(elapsed_pct: float) -> float:
    """Graduated size multiplier for underdog entries based on match progress.

    0-10% elapsed -> 1.0 (full size)
    10-25% -> 0.75
    25-40% -> 0.50
    40-50% -> 0.25 (minimum)
    >50% -> 0.0 (blocked)
    """
    if elapsed_pct > 0.50:
        return 0.0
    if elapsed_pct > 0.40:
        return 0.25
    if elapsed_pct > 0.25:
        return 0.50
    if elapsed_pct > 0.10:
        return 0.75
    return 1.0


def _sport_category(sport_tag: str) -> str:
    """Map a sport_tag to a threshold category key."""
    sp = (sport_tag or "").lower()
    if sp in ("atp", "wta") or "tennis" in sp:
        return "tennis"
    if sp in ("ufc",) or "mma" in sp:
        return "mma"
    if "golf" in sp or "pga" in sp:
        return "golf"
    if "racing" in sp or "f1" in sp or "nascar" in sp:
        return "racing"
    if "cricket" in sp:
        return "cricket"
    return "default"


class EntryGate:
    """Single unified market entry pipeline.

    Instantiate once. Stateful: owns market cache, AI analysis cache,
    candidate stock queues, and early_market_ids.
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
        discovery: "SportsDiscovery | None" = None,
        scout: "ScoutScheduler | None" = None,
        sports_ws: "SportsWebSocket | None" = None,
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
        self.discovery = discovery
        self.scout = scout
        self.sports_ws = sports_ws

        # Per-session state (survives across cycles)
        self._early_market_ids: set[str] = set()
        self._seen_market_ids: set[str] = set()
        self._espn_odds_cache: dict[str, dict] = {}  # cid -> ESPN odds from discovery
        self._confidence_c_attempts: dict[str, int] = {}  # cid -> how many times AI returned conf=C
        self._breaking_news_detected: bool = False
        # TeamResolver is now handled internally by src.matching

        # Candidate stock queues (pre-analyzed, waiting for slots)
        self._candidate_stock: list[dict] = []
        self._last_scout_matches: list = []  # Set by _analyze_batch for mark_entered

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
            entries_allowed: False -> skip all entries immediately.
            analyze: True -> run AI batch. False -> use cached estimates (stock queue).
            bankroll: Current USDC bankroll for sizing.
            cycle_count: Current cycle number (for cooldown checks).
            blacklist: Blacklist object for filtering.
            exited_markets: Set of cids that have been permanently exited.
        """
        if not entries_allowed:
            return []

        if not markets:
            return []

        self._prune_candidate_stock()

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
            "BUG: candidates collected but entries_allowed=False -- halt flag not propagated"
        )

        # Execute top N
        entered = self._execute_candidates(candidates, bankroll, cycle_count)
        self._save_candidate_stock()
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
        if "added_at" not in candidate:
            candidate["added_at"] = datetime.now(timezone.utc).isoformat()
        self._candidate_stock.append(candidate)

    def _prune_candidate_stock(self) -> None:
        """Remove stale candidates from stock queue (P2). Max 20, TTL 2 hours."""
        now = datetime.now(timezone.utc)
        _MAX_STOCK = 20
        # Remove candidates older than 2h
        self._candidate_stock = [
            c for c in self._candidate_stock
            if (now - datetime.fromisoformat(
                c.get("added_at", now.isoformat())
            ).replace(tzinfo=timezone.utc)).total_seconds() < 7200
        ]
        # Cap at max
        if len(self._candidate_stock) > _MAX_STOCK:
            self._candidate_stock = self._candidate_stock[-_MAX_STOCK:]

    def _save_candidate_stock(self) -> None:
        """Persist candidate stock to disk so dashboard STOCK tab shows it."""
        stock_path = Path("logs/candidate_stock.json")
        try:
            stock_path.parent.mkdir(parents=True, exist_ok=True)
            serializable = []
            for c in self._candidate_stock:
                entry = {}
                market = c.get("market")
                if market:
                    entry["condition_id"] = getattr(market, "condition_id", "")
                    entry["slug"] = getattr(market, "slug", "")
                    entry["question"] = getattr(market, "question", "")
                    entry["yes_price"] = getattr(market, "yes_price", 0)
                    entry["sport_tag"] = getattr(market, "sport_tag", "")
                entry["score"] = c.get("score", 0)
                est = c.get("estimate")
                entry["confidence"] = getattr(est, "confidence", "") if est else ""
                entry["edge"] = c.get("edge", 0)
                entry["added_at"] = c.get("added_at", "")
                entry["entry_reason"] = c.get("entry_reason", "")
                serializable.append(entry)
            tmp = stock_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(serializable, default=str), encoding="utf-8")
            tmp.replace(stock_path)
        except Exception as exc:
            logger.debug("Could not save candidate stock: %s", exc)

    def reset_seen_markets(self) -> None:
        """Reset seen market tracking. Called at start of each heavy cycle and each refill."""
        self._seen_market_ids.clear()

    def reset_daily_caches(self) -> None:
        """Reset stale caches daily (P3). Called when daily listing runs at 00:01 UTC."""
        old_c = len(self._confidence_c_attempts)
        old_odds = len(self._espn_odds_cache)
        self._confidence_c_attempts.clear()
        self._espn_odds_cache.clear()
        if old_c or old_odds:
            logger.info("Daily cache reset: cleared %d C-attempts, %d ESPN odds", old_c, old_odds)

    @staticmethod
    def _volume_sorted_selection(markets: list, scan_size: int) -> list:
        """Time-prioritized market selection. Prefers imminent matches, then unknown-time
        (likely close but missing match_start_iso), then midrange, then discovery."""
        imminent = []     # ≤6h — confirmed close
        unknown_time = [] # No match_start_iso but end_date ≤48h — probably close
        midrange = []     # 6-24h
        discovery = []    # >24h

        for m in markets:
            h = _hours_to_start(m)
            has_start = bool((getattr(m, "match_start_iso", "") or "").strip())
            if has_start and h <= 6:
                imminent.append(m)
            elif not has_start and h <= 48:
                unknown_time.append(m)
            elif h <= 24:
                midrange.append(m)
            else:
                discovery.append(m)

        imminent.sort(key=_hours_to_start)
        midrange.sort(key=_hours_to_start)
        discovery.sort(key=_hours_to_start)

        # Priority: imminent → unknown_time → midrange → discovery
        prioritized = imminent + unknown_time + midrange + discovery
        return prioritized[:scan_size]

    # ── Analysis phase ─────────────────────────────────────────────────────

    def _analyze_batch(self, markets: list, cycle_count: int) -> tuple[list, dict]:
        """Prioritize markets, fetch external data, run AI batch. Return (markets, estimates)."""
        cfg = self.config

        # Stock IDs (don't re-analyze markets already in candidate stock)
        _stock_ids = {c.get("condition_id", "") for c in self._candidate_stock}

        # Active portfolio positions (don't re-analyze markets we already hold)
        _active_cids = set(self.portfolio.positions.keys())

        # Skip stock-queued, already-analyzed, active positions, and conf=C with 2+ attempts
        _c_blocked = {cid for cid, n in self._confidence_c_attempts.items() if n >= 2}
        markets = [
            m for m in markets
            if m.condition_id not in _stock_ids
            and m.condition_id not in self._seen_market_ids
            and m.condition_id not in _active_cids
            and m.condition_id not in _c_blocked
        ]

        if not markets:
            return [], {}

        # Slot-based batch sizing — scale AI calls with open slots
        open_slots = max(0, cfg.risk.max_positions - self.portfolio.active_position_count)
        if open_slots == 0:
            logger.info("Pool full (0 open slots) -- skipping AI analysis")
            return [], {}
        ai_batch_size = min(cfg.ai.batch_size, open_slots * 2)
        # Over-scan 6x: wider net ensures AI batch stays full even with high no_data rate.
        # Polymarket-first pipeline pre-sorts by match proximity.
        scan_size = ai_batch_size * 6

        # --- Polymarket-first: sort by match proximity, scout as bonus ---
        prioritized = self._volume_sorted_selection(
            [m for m in markets if m.condition_id not in self._seen_market_ids],
            scan_size,
        )

        # Bonus: scout-matched markets get priority (move to front)
        if self.scout:
            matched_markets = matcher_match_batch(markets, self.scout._queue)
            if matched_markets:
                self._last_scout_matches = matched_markets
                scout_cids = {mm["market"].condition_id for mm in matched_markets}
                scout_prioritized = [m for m in prioritized if m.condition_id in scout_cids]
                non_scout = [m for m in prioritized if m.condition_id not in scout_cids]
                prioritized = scout_prioritized + non_scout
                prioritized = prioritized[:scan_size]
                logger.info("Polymarket-first: %d total, %d scout-boosted",
                            len(prioritized), len(scout_prioritized))
            else:
                logger.info("Polymarket-first: %d total, 0 scout matches", len(prioritized))
        else:
            logger.info("Polymarket-first: %d total (no scout)", len(prioritized))

        # NOTE: _seen_market_ids is updated AFTER quality filter (below),
        # so qualified markets that didn't fit in AI batch get re-evaluated next cycle.

        # Update early entry market ids (>6h to start = early entry, needs higher edge)
        self._early_market_ids = {m.condition_id for m in prioritized if _hours_to_start(m) > cfg.early.min_hours_to_start}

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

        # Fetch esports + sports contexts in parallel
        esports_contexts: dict = {}
        _t0 = time.time()

        def _enrich_esports(_m):
            """Fetch PandaScore context for a single esports market."""
            try:
                _ctx = self.esports.get_match_context(
                    getattr(_m, "question", ""),
                    [getattr(_m, "sport_tag", "") or ""],
                )
                return ("esports", _m.condition_id, _ctx, None)
            except Exception as exc:
                logger.warning("Esports enrichment error for %s: %s", (_m.slug or "")[:40], exc)
                return ("esports", _m.condition_id, None, None)

        def _enrich_sports(_m):
            """Fetch ESPN/discovery context + Odds API for a single sports market."""
            try:
                result = self.discovery.resolve(
                    getattr(_m, "question", ""),
                    _m.slug or "",
                    getattr(_m, "tags", []),
                )
                ctx = result.context if result else None
                espn_odds = result.espn_odds if result else None

                # Odds API: fetch bookmaker odds (Pinnacle etc.) — especially for tennis
                # where ESPN doesn't provide odds but Odds API does
                odds_api_result = None
                if self.odds_api and self.odds_api.available:
                    try:
                        odds_api_result = self.odds_api.get_bookmaker_odds(
                            getattr(_m, "question", ""), _m.slug or "", getattr(_m, "tags", [])
                        )
                    except Exception:
                        pass

                # If no ESPN odds but Odds API found odds, use as fallback
                if not espn_odds and odds_api_result:
                    espn_odds = odds_api_result

                # Append bookmaker info to context so AI sees it for confidence grading
                if odds_api_result:
                    bm_count = odds_api_result.get("num_bookmakers", 0)
                    has_sharp = odds_api_result.get("has_sharp", False)
                    prob_a = odds_api_result.get("bookmaker_prob_a", 0)
                    prob_b = odds_api_result.get("bookmaker_prob_b", 0)
                    team_a = odds_api_result.get("team_a", "Team A")
                    team_b = odds_api_result.get("team_b", "Team B")
                    odds_section = (f"\n\n=== BOOKMAKER ODDS ({bm_count} bookmakers"
                                    f"{', incl. Pinnacle' if has_sharp else ''}) ===\n"
                                    f"  {team_a}: {prob_a:.0%}\n"
                                    f"  {team_b}: {prob_b:.0%}\n")
                    if ctx:
                        ctx += odds_section
                    else:
                        # No ESPN data but Odds API found odds — create minimal context
                        ctx = (f"=== {getattr(_m, 'question', _m.slug)} ===\n"
                               f"No match statistics available.\n"
                               + odds_section)

                if ctx:
                    logger.info("Sports context (%s): %s", result.source if result else "odds", (_m.slug or "")[:40])
                    return ("sports", _m.condition_id, ctx, espn_odds)
                return ("sports", _m.condition_id, None, None)
            except Exception as exc:
                logger.warning("Discovery error for %s: %s", (_m.slug or "")[:40], exc)
                return ("sports", _m.condition_id, None, None)

        # Classify markets and submit to thread pool
        _esports_markets = []
        _sports_markets = []
        for _m in prioritized:
            _sport = getattr(_m, "sport_tag", "") or ""
            _slug = _m.slug or ""
            if is_esports(_sport) or is_esports_slug(_slug):
                _esports_markets.append(_m)
            elif self.discovery and not is_esports_slug(_slug):
                _sports_markets.append(_m)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = {}
            for _m in _esports_markets:
                futures[_m.condition_id] = pool.submit(_enrich_esports, _m)
            for _m in _sports_markets:
                futures[_m.condition_id] = pool.submit(_enrich_sports, _m)

            for cid, fut in futures.items():
                try:
                    kind, _, ctx, espn_odds = fut.result(timeout=30)
                    if ctx is not None:
                        esports_contexts[cid] = ctx
                    if espn_odds is not None:
                        self._espn_odds_cache[cid] = espn_odds
                except Exception as exc:
                    logger.warning("Enrichment future error for %s: %s", cid[:12], exc)

        logger.info("Enrichment completed: %d markets in %.1fs", len(esports_contexts), time.time() - _t0)

        # News scanning disabled: 96% fail rate, adds 15 min to cycle for negligible data.
        # ESPN stats + Odds API bookmaker odds are sufficient for A/B+ confidence.
        # TODO: Re-enable when news APIs stabilize or find better provider.
        news_context_by_market: dict[str, str] = {}
        self._breaking_news_detected = False

        # Filter: only markets with sufficient sports data qualify for AI analysis
        _has_data: list = []
        _no_data_skipped = 0
        _thin_data_skipped = 0
        for m in prioritized:
            ctx = esports_contexts.get(m.condition_id)
            if not ctx:
                _no_data_skipped += 1
                logger.info("SKIP no data: %s | tag=%s", (m.slug or "")[:40], getattr(m, "sport_tag", "?"))
                continue
            # Pre-AI quality gate: count match result lines in context
            # Lines like "[W]" or "[L]" indicate actual game results
            result_lines = ctx.count("[W]") + ctx.count("[L]")
            # Sport-aware threshold: tennis/MMA/golf need fewer results
            _sport_cat = _sport_category(getattr(m, "sport_tag", ""))
            _threshold = _THIN_DATA_THRESHOLDS.get(_sport_cat, _THIN_DATA_THRESHOLDS["default"])
            if result_lines < _threshold:
                _thin_data_skipped += 1
                logger.info("SKIP thin data: %s | only %d match results (need %d+, sport=%s)",
                            (m.slug or "")[:35], result_lines, _threshold, _sport_cat)
                self.trade_log.log({
                    "market": m.slug, "action": "HOLD",
                    "rejected": f"Thin data ({result_lines} results, need {_threshold}+)",
                    "price": m.yes_price,
                    "question": getattr(m, "question", ""),
                })
                continue
            _has_data.append(m)
        if _no_data_skipped:
            logger.info("Skipped %d markets without sports data (saves AI tokens)", _no_data_skipped)
        if _thin_data_skipped:
            logger.info("Skipped %d markets with thin data (saves AI tokens)", _thin_data_skipped)

        if not _has_data:
            logger.info("No markets with data -- skipping AI batch")
            return [], {}

        # Re-sort by match start time (enrichment may have filled match_start_iso from ESPN)
        _has_data.sort(key=_hours_to_start)

        # Cap at AI batch size (over-scanned to find enough quality markets)
        _qualified_count = len(_has_data)
        if _qualified_count > ai_batch_size:
            _has_data = _has_data[:ai_batch_size]
        logger.info(
            "Over-scan: scanned %d → no_data=%d thin=%d → qualified %d → AI batch %d",
            len(prioritized), _no_data_skipped, _thin_data_skipped,
            _qualified_count, len(_has_data),
        )

        # Mark seen: AI-analyzed + no-data + thin-data (don't re-scan these).
        # Qualified markets that didn't fit in AI batch are NOT marked --
        # they get priority in the next cycle.
        self._seen_market_ids.update(m.condition_id for m in _has_data)
        _skipped_cids = set()
        for m in prioritized:
            if m.condition_id not in esports_contexts:
                _skipped_cids.add(m.condition_id)
                continue
            _ctx_str = esports_contexts.get(m.condition_id, "")
            _result_count = _ctx_str.count("[W]") + _ctx_str.count("[L]")
            _sp_cat = _sport_category(getattr(m, "sport_tag", ""))
            _thr = _THIN_DATA_THRESHOLDS.get(_sp_cat, _THIN_DATA_THRESHOLDS["default"])
            if _result_count < _thr:
                _skipped_cids.add(m.condition_id)
        self._seen_market_ids.update(_skipped_cids)

        # Run AI batch -- returns List[AIEstimate] in same order as _has_data
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
        from src.models import Direction, effective_price
        from src.match_exit import get_game_duration

        cfg = self.config
        candidates: list[dict] = []
        _CONF_SKIP = {"C", "B-", "", "?"}  # C = veri yetersiz, B- = ince data, skip

        for market in markets:
            cid = market.condition_id

            # --- Guard: resolved / closed / not accepting orders ---
            if market.closed or market.resolved or not market.accepting_orders:
                logger.info("SKIP resolved/closed: %s", (market.slug or "")[:40])
                continue

            # --- Guard: match already ended (Gamma says active but event ended) ---
            if getattr(market, "event_ended", False) is True:
                logger.info("SKIP event-ended: %s", (market.slug or "")[:40])
                continue

            # --- Guard: price indicates near-certain outcome (≥95¢ either side) ---
            _yes = market.yes_price
            if _yes >= 0.95 or _yes <= 0.05:
                logger.info("SKIP near-resolved price: %s | YES=%.0f¢",
                            (market.slug or "")[:40], _yes * 100)
                continue

            # --- Guard: match past 50% elapsed → skip ---
            elapsed_pct = 0.0
            _slug = market.slug or ""
            _sport = getattr(market, "sport_tag", "") or ""
            _nogs = getattr(market, "number_of_games", 0) or 0
            _msi = getattr(market, "match_start_iso", "") or ""

            # Prefer Sports WebSocket (real-time)
            if self.sports_ws:
                _ws = self.sports_ws.get_match_state(_slug)
                if _ws and _ws.get("ended"):
                    logger.info("SKIP ws-ended: %s", _slug[:40])
                    continue
                if _ws and _ws.get("elapsed"):
                    _parts = _ws["elapsed"].split(":")
                    _el_min = int(_parts[0]) + int(_parts[1]) / 60 if len(_parts) == 2 else 0
                    _dur = get_game_duration(_slug, _nogs, _sport)
                    elapsed_pct = _el_min / max(_dur, 1)

            # Fallback: match_start_iso + sport duration
            if elapsed_pct == 0.0 and _msi:
                try:
                    _start = datetime.fromisoformat(_msi.replace("Z", "+00:00"))
                    _now = datetime.now(timezone.utc)
                    _el_min = (_now - _start).total_seconds() / 60
                    if _el_min > 0:
                        _dur = get_game_duration(_slug, _nogs, _sport)
                        elapsed_pct = _el_min / max(_dur, 1)
                except (ValueError, TypeError):
                    pass

            if elapsed_pct > 0.50:
                logger.info("SKIP half-elapsed: %s | %.0f%% through", _slug[:35], elapsed_pct * 100)
                continue

            estimate = estimates.get(cid)
            if estimate is None:
                continue
            if estimate.confidence in _CONF_SKIP:
                logger.info("SKIP confidence: %s | conf=%s (insufficient data)",
                            market.slug[:35], estimate.confidence)
                self._confidence_c_attempts[cid] = self._confidence_c_attempts.get(cid, 0) + 1  # Block after 2 attempts
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"Insufficient data (conf={estimate.confidence})",
                    "ai_prob": estimate.ai_probability,
                    "price": market.yes_price,
                    "question": getattr(market, "question", ""),
                    "sport_tag": getattr(market, "sport_tag", ""),
                })
                continue

            # ── Bookmaker anchor (Odds API + ESPN odds combined) ────────────
            _is_esports_mkt = is_esports(getattr(market, "sport_tag", "") or "")
            _anchor_book_prob = None
            _anchor_num_books = 0
            _odds_probs: list[tuple[float, float]] = []  # (prob, total_weight) pairs
            _odds_api_is_3way = False  # True when Odds API returned a real 3-way soccer quote

            # Source 1: Odds API (paid, multi-bookmaker average)
            if not _is_esports_mkt and self.odds_api.available:
                try:
                    _mkt_odds = self.odds_api.get_bookmaker_odds(
                        market.question, market.slug or "", market.tags or []
                    )
                    if _mkt_odds and _mkt_odds.get("bookmaker_prob_a") is not None:
                        _odds_probs.append((
                            _mkt_odds["bookmaker_prob_a"],
                            _mkt_odds.get("total_weight") or _mkt_odds.get("num_bookmakers", 1),
                        ))
                        if _mkt_odds.get("bookmaker_prob_draw") is not None:
                            _odds_api_is_3way = True
                except Exception:
                    pass

            # Source 2: ESPN odds (free, cached from discovery phase -- no extra API call).
            # Skip ESPN when Odds API already returned a real 3-way soccer quote:
            # ESPN is 2-way only (draw mass absorbed into home/away), so averaging a
            # 2-way P(home) with a 3-way P(home) would inflate the anchor for soccer
            # favorites. For soccer we trust the 3-way Odds API value exclusively.
            if not _odds_api_is_3way:
                _espn_odds = self._espn_odds_cache.get(cid)
                if _espn_odds and _espn_odds.get("bookmaker_prob_a") is not None:
                    _odds_probs.append((
                        _espn_odds["bookmaker_prob_a"],
                        _espn_odds.get("total_weight") or _espn_odds.get("num_bookmakers", 1),
                    ))

            # Combine: weighted average by number of bookmakers
            _has_espn_odds = cid in self._espn_odds_cache
            logger.debug("DATA: %s | ESPN=%s OddsAPI=%s | conf=%s",
                         market.slug[:35],
                         "YES" if _has_espn_odds else "NO",
                         "YES" if _odds_probs else "NO",
                         estimate.confidence)
            if _odds_probs:
                total_weight = sum(w for _, w in _odds_probs)
                _anchor_book_prob = sum(p * w for p, w in _odds_probs) / total_weight
                _anchor_num_books = total_weight
            anchored = calculate_anchored_probability(
                ai_prob=estimate.ai_probability,
                bookmaker_prob=_anchor_book_prob,
                num_bookmakers=_anchor_num_books,
            )
            # ── Two-case strategy: consensus vs disagree ─────────────────
            ai_p = estimate.ai_probability     # Raw AI P(YES) -- before anchoring
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
                # Use raw AI probability (skip shrinkage -- market already confirms).
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
            if direction_prob < 0.50:
                logger.info("SKIP prob: %s | prob=%.0f%% conf=%s (< 50%%)",
                            market.slug[:35], direction_prob * 100, estimate.confidence)
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"Low probability ({direction_prob*100:.0f}% < 50%)",
                    "ai_prob": estimate.ai_probability,
                    "edge": edge if 'edge' in dir() else 0,
                    "price": market.yes_price,
                    "question": getattr(market, "question", ""),
                })
                continue
            elif direction_prob >= 0.60:
                mode = "WINNER"
            else:
                # Deadzone (50-60%) -- too uncertain to trade
                logger.info("SKIP deadzone: %s | prob=%.0f%% (50-60%% zone)",
                            market.slug[:35], direction_prob * 100)
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"Deadzone ({direction_prob*100:.0f}% in 50-60%)",
                    "ai_prob": estimate.ai_probability,
                    "edge": edge,
                    "price": market.yes_price,
                    "question": getattr(market, "question", ""),
                    "sport_tag": getattr(market, "sport_tag", ""),
                    "bookmaker_prob": _anchor_book_prob,
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

            # ── Underdog elapsed guard (eff_entry < 20¢) ─────────────────
            # Low-price entries need match timing; graduated size reduction.
            _eff_entry_price = effective_price(mkt_p, direction)
            if _eff_entry_price < 0.20:
                _has_timing = bool(_msi) or elapsed_pct > 0.0
                if not _has_timing:
                    logger.info("SKIP no-start-time upset: %s | entry=%.0f¢",
                                market.slug[:35], _eff_entry_price * 100)
                    continue
                _udog_mult = _underdog_elapsed_size_multiplier(elapsed_pct)
                if _udog_mult <= 0.0:
                    logger.info("SKIP upset-half-elapsed: %s | %.0f%% through",
                                market.slug[:35], elapsed_pct * 100)
                    continue
                if _udog_mult < 1.0:
                    adjusted_size *= _udog_mult
                    logger.info("Underdog size reduction: %s | %.0f%% elapsed -> %.0f%% size",
                                market.slug[:35], elapsed_pct * 100, _udog_mult * 100)

            # ── Rank score -- pure edge × confidence ─────────────────────────
            # Edge-only ranking: underdogs with high edge rank equally to favorites.
            # Old formula (direction_prob + edge) penalized underdogs 2-3x.
            conf_score = _CONF_SCORE.get(estimate.confidence, 1)
            rank_score = edge * conf_score

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
                "is_early": cid in self._early_market_ids,
                "bookmaker_prob": _anchor_book_prob,
                "bookmaker_count": _anchor_num_books,
            })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates

    # ── Execution phase ────────────────────────────────────────────────────

    def _execute_candidates(
        self, candidates: list[dict], bankroll: float, cycle_count: int,
    ) -> list[str]:
        """Execute top candidates. Return list of entered condition_ids."""
        from src.models import Direction, effective_price
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

            # Same-event dual-side check -- never enter both sides of same match
            market_event_id = getattr(market, "event_id", "") or ""
            if market_event_id and market_event_id in entered_event_ids:
                logger.info("SKIP same-event: %s | event_id=%s already in portfolio",
                            market.slug[:35], market_event_id[:20])
                continue

            # Slot check — save remaining candidates to stock when full
            open_slots = cfg.risk.max_positions - self.portfolio.active_position_count
            if open_slots <= 0:
                remaining_idx = candidates.index(c)
                overflow = candidates[remaining_idx:]
                for rc in overflow:
                    rc["added_at"] = datetime.now(timezone.utc).isoformat()
                    self._candidate_stock.append(rc)
                if overflow:
                    logger.info("Slots full — saved %d candidates to stock queue", len(overflow))
                break

            # Min bet check
            if size < 5.0:  # Polymarket minimum order size
                logger.info("SKIP min-bet: %s | size=$%.2f < $5.00 | conf=%s edge=%.1f%%",
                            market.slug[:35], size, estimate.confidence, c.get("edge", 0) * 100)
                continue

            # Extreme price guard -- don't enter markets already at 0% or 100%
            _yes_p = market.yes_price
            _eff_entry = effective_price(_yes_p, direction)
            if _eff_entry <= 0.05 or _eff_entry >= 0.85:
                logger.info(
                    "SKIP extreme price: %s | eff_price=%.0f%% -- market already resolved/extreme",
                    market.slug[:40], _eff_entry * 100,
                )
                continue

            # Exposure guard -- if cap reached, save remaining to stock and stop
            from src.risk_manager import exceeds_exposure_limit
            if exceeds_exposure_limit(
                self.portfolio.positions, size,
                self.portfolio.bankroll, self.config.risk.max_exposure_pct,
            ):
                logger.info(
                    "EXPOSURE CAP: %s | size=$%.1f | %.0f%% cap -- saving remaining to stock",
                    market.slug[:35], size,
                    self.config.risk.max_exposure_pct * 100,
                )
                # Save this and all remaining candidates to stock queue
                remaining_idx = candidates.index(c)
                for rc in candidates[remaining_idx:]:
                    rc["added_at"] = datetime.now(timezone.utc).isoformat()
                    self._candidate_stock.append(rc)
                logger.info("Saved %d candidates to stock queue (exposure cap)",
                            len(candidates) - remaining_idx)
                break

            # Execute
            _token_id = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
            _order_price = effective_price(market.yes_price, direction)
            result = self.executor.place_order(
                token_id=_token_id,
                side="BUY",
                price=_order_price,
                size_usdc=size,
            )
            if not result or result.get("status") == "error":
                logger.warning("Order failed: %s -- %s", market.slug[:40], result)
                continue

            # Record position -- entry_price is always YES-side for storage consistency.
            # Executor may have adjusted the fill price via the stale-price guard
            # (scanner Gamma snapshot vs live CLOB), so prefer result["price"] and
            # convert back to YES-side if we bought NO.
            _fill_side_price = result.get("price", _order_price)
            if direction == Direction.BUY_YES:
                entry_price = _fill_side_price
            else:
                entry_price = 1.0 - _fill_side_price
            eff_price = effective_price(entry_price, direction)
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
                match_start_iso=getattr(market, "match_start_iso", "") or "",
                entry_reason=c.get("entry_reason", ""),
                is_consensus=c.get("is_consensus", False),
            )

            # Mark scout entry as entered (P1: wire up dead code)
            if self.scout:
                for mm in getattr(self, '_last_scout_matches', []):
                    if mm.get("market") and mm["market"].condition_id == cid:
                        self.scout.mark_entered(mm["scout_key"])
                        break

            self.trade_log.log({
                "market": market.slug, "action": "BUY",
                "direction": direction.value if hasattr(direction, "value") else direction,
                "size_usdc": size, "entry_price": entry_price,
                "ai_prob": estimate.ai_probability,
                "confidence": estimate.confidence,
                "edge": c["edge"],
                "is_consensus": c["is_consensus"],
                "entry_reason": c.get("entry_reason", ""),
                "is_early": c["is_early"],
                "reasoning_pro": getattr(estimate, "reasoning_pro", ""),
                "reasoning_con": getattr(estimate, "reasoning_con", ""),
                "bookmaker_prob": c.get("bookmaker_prob"),
                "bookmaker_count": c.get("bookmaker_count"),
                "sport_tag": getattr(market, "sport_tag", ""),
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
            _eff_p = effective_price(entry_price, direction)
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

        # Log WINNER candidates that didn't enter (debug: why not?)
        entered_set = set(entered)
        for c in candidates:
            _c_cid = c["market"].condition_id
            if _c_cid not in entered_set:
                logger.info("WINNER NOT ENTERED: %s | score=%.3f conf=%s edge=%.1f%% size=$%.2f",
                            c["market"].slug[:35], c["score"], c["estimate"].confidence,
                            c.get("edge", 0) * 100, c["adjusted_size"])

        return entered


# ── Module-level helpers ───────────────────────────────────────────────────

def _hours_to_start(market) -> float:
    """Hours until match starts. Used for imminent/mid/discovery bucketing.

    Prefers match_start_iso (Gamma event startTime — actual kick-off / first map)
    over end_date_iso (Polymarket market close — often far in the future).
    """
    # Primary: match start time from Gamma event (accurate for sports + esports)
    start_iso = getattr(market, "match_start_iso", "") or ""
    if start_iso:
        try:
            start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            return (start_dt - datetime.now(timezone.utc)).total_seconds() / 3600
        except (ValueError, TypeError):
            pass
    # Fallback: Polymarket end date
    end_iso = getattr(market, "end_date_iso", "") or ""
    if not end_iso:
        return 99.0
    try:
        end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        return (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600
    except (ValueError, TypeError):
        return 99.0
