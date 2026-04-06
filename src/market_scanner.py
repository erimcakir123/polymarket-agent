"""Gamma API market discovery and filtering."""
from __future__ import annotations
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List

import requests

from src.config import ScannerConfig
from src.models import MarketData

logger = logging.getLogger(__name__)

GAMMA_BASE = "https://gamma-api.polymarket.com"

# Fallback parent tags (used when /sports endpoint is unreachable)
PARENT_TAGS: list[tuple[str, int]] = [
    ("sports", 1),      # All traditional sports
    ("esports", 64),    # All esports
]

EVENTS_PER_PAGE = 200  # Gamma API max per request

# Cache for league-specific tag_ids discovered from /sports endpoint
_league_tags_cache: list[tuple[str, int]] = []
_league_tags_ts: float = 0.0

# Esport identifiers -- includes both short names and seriesSlug values from Gamma
ESPORT_TAGS: set[str] = {
    # Short names (from /sports endpoint)
    "cs2", "lol", "dota2", "val", "mlbb", "ow", "codmw", "pubg",
    "r6siege", "rl", "hok", "wildrift", "sc2", "sc", "fifa",
    # seriesSlug values (from parent tag scan)
    "counter-strike", "league-of-legends", "dota-2", "valorant",
    "overwatch", "mobile-legends", "call-of-duty", "pubg-esports",
    "rainbow-six", "rocket-league", "honor-of-kings", "wild-rift",
    "starcraft-2", "starcraft", "fifa-esports",
}


class MarketScanner:
    def __init__(self, config: ScannerConfig) -> None:
        self.config = config

    def _fetch_league_tags(self) -> list[tuple[str, int]]:
        """Discover all league-specific tag_ids from Polymarket /sports endpoint.

        Daily H2H match markets live under league-specific tags (e.g. Turkish
        Super Lig = tag_id 102564), NOT under parent tags 1/64 which only cover
        season-long/futures markets. This method fetches the full list, caches
        it for 24h, and falls back to PARENT_TAGS on failure.
        """
        import time
        global _league_tags_cache, _league_tags_ts
        if _league_tags_cache and (time.time() - _league_tags_ts) < 21600:  # 6h
            return _league_tags_cache

        try:
            resp = requests.get(f"{GAMMA_BASE}/sports", timeout=15)
            resp.raise_for_status()
            sports = resp.json()
        except Exception as exc:
            logger.warning("/sports endpoint failed: %s — falling back to parent tags", exc)
            return PARENT_TAGS

        seen_tags: set[int] = set()
        result: list[tuple[str, int]] = []
        for entry in sports:
            sport_code = entry.get("sport", "")
            for t in entry.get("tags", "").split(","):
                t = t.strip()
                if t.isdigit():
                    tid = int(t)
                    if tid not in seen_tags:
                        seen_tags.add(tid)
                        result.append((sport_code, tid))

        if result:
            _league_tags_cache = result
            _league_tags_ts = time.time()
            logger.info("Discovered %d league tags from /sports (%d entries)",
                        len(result), len(sports))
        else:
            logger.warning("No tags from /sports — falling back to parent tags")
            return PARENT_TAGS
        return result

    def fetch(self) -> List[MarketData]:
        use_tag_ids = False
        if self.config.allowed_categories:
            cats_lower = {c.lower() for c in self.config.allowed_categories}
            if cats_lower & {"sports", "esports"}:
                use_tag_ids = True

        if use_tag_ids:
            all_raw = self._fetch_by_tag_ids()
        else:
            all_raw = self._fetch_volume_sorted()

        result: List[MarketData] = []
        for raw in all_raw:
            market = self._parse_market(raw)
            if market and self._passes_filters(market):
                result.append(market)

        if self.config.prefer_short_duration:
            result = self._sort_by_end_date(result)

        logger.info("Scanner: %d markets passed filters (from %d raw)", len(result), len(all_raw))
        return result

    def _fetch_by_tag_ids(self) -> list[dict]:
        """Fetch ALL sports & esports markets using league-specific tags + pagination.

        Discovers tag_ids from /sports endpoint (171 leagues, each with unique tags).
        Daily H2H match markets live under these league tags, not under parent tags
        1/64 which only cover futures/season-long markets.
        """
        seen_ids: set[str] = set()
        all_raw: list[dict] = []
        total_events = 0
        total_queries = 0

        now = datetime.now(timezone.utc)
        date_min = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        league_tags = self._fetch_league_tags()
        for category, tag_id in league_tags:
            offset = 0
            while True:
                params: dict = {
                    "tag_id": tag_id,
                    "active": "true",
                    "closed": "false",
                    "limit": EVENTS_PER_PAGE,
                    "offset": offset,
                    "end_date_min": date_min,
                }
                try:
                    resp = requests.get(f"{GAMMA_BASE}/events", params=params, timeout=20)
                    resp.raise_for_status()
                    events = resp.json()
                    total_queries += 1

                    if not events:
                        break

                    total_events += len(events)
                    for event in events:
                        event_live = event.get("live", False)
                        # Detect sport from event's series slug or title
                        sport_tag = self._detect_sport_tag(event, category)
                        for raw_market in event.get("markets", []):
                            cid = raw_market.get("conditionId", "")
                            if cid and cid not in seen_ids:
                                seen_ids.add(cid)
                                raw_market["_event_live"] = bool(event_live)
                                raw_market["_event_ended"] = bool(event.get("ended", False))
                                raw_market["_sport_tag"] = sport_tag
                                raw_market["_event_start_time"] = event.get("startTime", "")
                                all_raw.append(raw_market)

                    # If we got fewer than the page size, no more pages
                    if len(events) < EVENTS_PER_PAGE:
                        break
                    offset += EVENTS_PER_PAGE

                except requests.RequestException as e:
                    logger.error("Gamma /events error (tag_id=%s, %s): %s", tag_id, category, e)
                    break

        # Supplementary parent-tag scan: catches newly-added leagues not yet in /sports
        # Parent tags 1 (sports) and 64 (esports) cover ALL sports/esports events
        # including ones that may not have league-specific tags yet.
        parent_new = 0
        for category, tag_id in PARENT_TAGS:
            offset = 0
            while True:
                params = {
                    "tag_id": tag_id,
                    "active": "true",
                    "closed": "false",
                    "limit": EVENTS_PER_PAGE,
                    "offset": offset,
                    "end_date_min": date_min,
                }
                try:
                    resp = requests.get(f"{GAMMA_BASE}/events", params=params, timeout=20)
                    resp.raise_for_status()
                    events = resp.json()
                    total_queries += 1
                    if not events:
                        break
                    for event in events:
                        sport_tag = self._detect_sport_tag(event, category)
                        for raw_market in event.get("markets", []):
                            cid = raw_market.get("conditionId", "")
                            if cid and cid not in seen_ids:
                                seen_ids.add(cid)
                                raw_market["_event_live"] = bool(event.get("live", False))
                                raw_market["_event_ended"] = bool(event.get("ended", False))
                                raw_market["_sport_tag"] = sport_tag
                                raw_market["_event_start_time"] = event.get("startTime", "")
                                all_raw.append(raw_market)
                                parent_new += 1
                    if len(events) < EVENTS_PER_PAGE:
                        break
                    offset += EVENTS_PER_PAGE
                except requests.RequestException:
                    break
        if parent_new:
            logger.info("Parent-tag fallback found %d NEW markets not in league tags", parent_new)

        logger.info("Total scan: %d tags + 2 parent, %d queries -> %d unique markets",
                     len(league_tags), total_queries, len(all_raw))
        return all_raw

    @staticmethod
    def _detect_sport_tag(event: dict, category: str) -> str:
        """Detect the sport name from event metadata."""
        # seriesSlug is most reliable (e.g. "cs2", "nba", "epl")
        series = event.get("seriesSlug", "")
        if series:
            return series
        # Fallback: try to infer from title
        title = event.get("title", "").lower()
        slug = event.get("slug", "").lower()
        for indicator, sport in [
            ("counter-strike", "cs2"), ("league of legends", "lol"),
            ("dota", "dota2"), ("valorant", "val"), ("overwatch", "ow"),
            ("nba", "nba"), ("nhl", "nhl"), ("mlb", "mlb"), ("nfl", "nfl"),
            ("soccer", "soccer"), ("cricket", "cricket"), ("tennis", "tennis"),
            ("ufc", "ufc"), ("mma", "mma"), ("boxing", "boxing"),
            ("formula", "f1"), ("rugby", "rugby"),
        ]:
            if indicator in title or indicator in slug:
                return sport
        return category  # "sports" or "esports" as generic fallback

    def _fetch_volume_sorted(self) -> list[dict]:
        """Fallback: fetch markets sorted by volume (original behavior)."""
        params = {
            "active": "true",
            "closed": "false",
            "limit": self.config.max_markets_per_cycle,
            "order": "volume24hr",
            "ascending": "false",
        }
        try:
            resp = requests.get(f"{GAMMA_BASE}/markets", params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error("Gamma API error: %s", e)
            return []

    def _parse_market(self, raw: dict) -> MarketData | None:
        try:
            prices = json.loads(raw.get("outcomePrices", '["0.5","0.5"]'))
            tokens = json.loads(raw.get("clobTokenIds", '["",""]'))
            tags_raw = json.loads(raw.get("tags", "[]"))
            tag_labels = [t.get("label", "") for t in tags_raw if isinstance(t, dict)]

            # Skip markets with empty token IDs (can't trade without them)
            if not tokens[0] or not tokens[1]:
                logger.debug("Skipping market with empty token IDs: %s", raw.get("question", ""))
                return None

            return MarketData(
                condition_id=raw.get("conditionId", ""),
                question=raw.get("question", ""),
                yes_price=float(prices[0]),
                no_price=float(prices[1]),
                yes_token_id=tokens[0],
                no_token_id=tokens[1],
                volume_24h=float(raw.get("volume24hr", 0) or 0),
                liquidity=float(raw.get("liquidity", 0) or 0),
                slug=raw.get("slug", ""),
                tags=tag_labels,
                end_date_iso=raw.get("endDate", ""),
                description=raw.get("description", ""),
                event_id=raw.get("eventId"),
                event_live=raw.get("_event_live", False),
                event_ended=raw.get("_event_ended", False),
                sport_tag=raw.get("_sport_tag", ""),
                accepting_orders_at=raw.get("acceptingOrdersTimestamp", ""),
                match_start_iso=raw.get("_event_start_time", ""),
                closed=bool(raw.get("closed", False)),
                resolved=bool(raw.get("resolved", False)),
                accepting_orders=bool(raw.get("acceptingOrders", True)),
                sports_market_type=raw.get("sportsMarketType", ""),
            )
        except (json.JSONDecodeError, IndexError, ValueError) as e:
            logger.warning("Failed to parse market: %s", e)
            return None

    _SPORT_KEYWORDS = {
        "win", "score", "goal", "match", "game", "vs", "vs.",
        "fc", "afc", "utd", "city",
        "nba", "nfl", "nhl", "mlb", "ncaa", "ncaab", "ufc", "mma",
        "premier league", "la liga", "serie a", "bundesliga", "ligue 1",
        "champions league", "ucl", "europa league",
        "march madness", "super bowl", "world cup",
        "tennis", "boxing", "f1", "formula 1", "grand prix",
    }

    _ELECTION_KEYWORDS = {
        "election", "vote", "referendum", "ballot", "polling",
        "president", "presidential", "prime minister", "governor",
        "parliament", "congressional", "senate", "mayor",
        "party", "candidate", "incumbent", "runoff",
    }

    def _is_election(self, market: MarketData) -> bool:
        """Check if market is election-related."""
        q_lower = market.question.lower()
        tags_lower = [t.lower() for t in market.tags]
        has_election_tag = "elections" in tags_lower or "politics" in tags_lower
        has_election_keyword = any(kw in q_lower for kw in self._ELECTION_KEYWORDS if kw != "party")
        # "party" alone is too broad (matches esports "LAN party" etc.) -- require tag confirmation
        has_party_with_tag = "party" in q_lower and has_election_tag
        return has_election_keyword or has_party_with_tag

    def _is_live_sport(self, market: MarketData) -> bool:
        """Check if market is a sports event based on question and tags."""
        q = market.question.lower()
        tags_lower = [t.lower() for t in market.tags]
        sport_tags = {"sports", "soccer", "football", "basketball", "baseball",
                      "hockey", "tennis", "boxing", "mma", "cricket", "esports"}
        if sport_tags & set(tags_lower):
            return True
        return any(kw in q for kw in self._SPORT_KEYWORDS)

    def _sort_by_end_date(self, markets: List[MarketData]) -> List[MarketData]:
        """Sort markets so those resolving soonest come first. No end_date -> last."""
        now = datetime.now(timezone.utc)
        far_future = datetime(2099, 1, 1, tzinfo=timezone.utc)

        def sort_key(m: MarketData) -> datetime:
            if not m.end_date_iso:
                return far_future
            try:
                return datetime.fromisoformat(m.end_date_iso.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return far_future

        return sorted(markets, key=sort_key)

    def _is_sports_or_esports(self, market: MarketData) -> bool:
        """Check if market is sports or esports (not politics, crypto, etc.)."""
        if market.sport_tag:
            return True
        return self._is_live_sport(market)

    def _passes_filters(self, market: MarketData) -> bool:
        # Category filter: only allow specified categories (e.g. sports, esports)
        if self.config.allowed_categories:
            allowed = {c.lower() for c in self.config.allowed_categories}
            if "sports" in allowed or "esports" in allowed:
                if not self._is_sports_or_esports(market):
                    logger.debug("Skipped non-sports market: %s", market.question[:60])
                    return False
            elif market.tags:
                tags_lower = {t.lower() for t in market.tags}
                if not (tags_lower & allowed):
                    logger.debug("Skipped category mismatch: %s", market.question[:60])
                    return False
        # Liquidity filter -- ensures orderbook has enough depth to fill our entry
        # Volume filter removed: we hold to resolution, so trading activity doesn't matter
        if market.liquidity < self.config.min_liquidity:
            return False
        # Only filter by tags if the market actually has tags
        # (Gamma API often returns empty tags)
        if self.config.tags and market.tags:
            if not any(t in self.config.tags for t in market.tags):
                return False
        # Block alt bets via Gamma's sportsMarketType (authoritative, no heuristics)
        # When present: only allow "moneyline" (match winner / H2H)
        # When absent: fall back to slug/question keyword heuristics below
        if market.sports_market_type and market.sports_market_type.lower() != "moneyline":
            logger.debug("Blocked non-moneyline (type=%s): %s",
                         market.sports_market_type, market.slug[:60])
            return False
        # Block alt bets: keyword heuristics (backup for markets without sportsMarketType)
        q_lower = market.question.lower()
        slug_lower = market.slug.lower()
        _ALT_SLUG = (
            "-total-", "-spread-", "-handicap-", "-over-", "-under-",
            "-1h-", "-first-half-", "-first-set-", "-draw", "-btts",
            # Season-long props (not match results)
            "-award", "-trophy", "ballon-dor", "cy-young", "hart-memorial",
            "-mvp", "-rookie-of", "-coach-of", "-manager-of",
            "-traded", "-be-traded", "-signed", "-be-signed", "-fired", "-be-fired",
            "-draft", "first-pick", "-relegated", "-relegation", "-promoted",
        )
        _ALT_Q = (
            "o/u", "over/under", "point spread", "handicap:", "set handicap",
            "1h moneyline", "first half", "end in a draw", "both teams to score",
            "1st quarter", "2nd quarter", "3rd quarter", "4th quarter",
            "1st inning", "1st period", "2nd period", "3rd period",
            "exact score", "correct score", "most kills", "most assists",
        )
        if any(t in slug_lower for t in _ALT_SLUG) or any(t in q_lower for t in _ALT_Q):
            logger.debug("Blocked alt bet (total/spread): %s", market.slug[:60])
            return False
        # Block esports sub-markets (Map X, Game X, specific in-game events)
        _SUB_PATTERNS = [
            "map 1", "map 2", "map 3", "map 4", "map 5",
            "game 1", "game 2", "game 3", "game 4", "game 5",
            "- map ", "- game ", "map winner", "game winner",
            "first blood", "first kill", "first tower", "first baron",
            "first dragon", "pistol round", "round handicap",
            "round 1 winner", "round 2 winner", "round 3 winner",
            "mvp of the match", "player of the match",
        ]
        is_sub = any(p in q_lower for p in _SUB_PATTERNS)
        is_sub = is_sub or any(s in slug_lower for s in ["-game", "-map-"])
        if is_sub:
            logger.debug("Blocked sub-market: %s", market.question[:60])
            return False

        # Skip nearly-resolved markets (>95%) -- no edge left
        # Allow low-price tokens (<5%) through -- Early Entry/penny alpha candidates
        if market.yes_price > 0.95:
            logger.debug("Excluded near-resolved (%.1f%%): %s", market.yes_price * 100, market.question[:60])
            return False
        # Skip markets resolving too far out -- elections get a longer window (90 days)
        if market.end_date_iso and self.config.max_duration_days > 0:
            try:
                end_dt = datetime.fromisoformat(market.end_date_iso.replace("Z", "+00:00"))
                days_left = (end_dt - datetime.now(timezone.utc)).total_seconds() / 86400
                max_days = 30 if self._is_election(market) else self.config.max_duration_days
                if days_left > max_days:
                    logger.info("Skipped too far out (%.0fd, max=%dd): %s",
                                days_left, max_days, market.question[:60])
                    return False
            except (ValueError, TypeError):
                pass
        # Skip ended matches -- no point entering a resolved event
        # All sports (including esports) go through the same time filters.
        if market.event_ended and self._is_live_sport(market):
            logger.info("Skipped ENDED event (Gamma): %s", market.question[:60])
            return False
        # Skip late-match entries -- not enough time for meaningful edge
        # Uses sport-specific duration table (soccer=95min, NBA=150min, etc.)
        # Check elapsed regardless of event_live flag — Gamma sometimes doesn't
        # set live=True for tennis/esports, letting 3h-old matches slip through.
        if market.match_start_iso:
            try:
                from src.match_exit import get_game_duration
                start_dt = datetime.fromisoformat(market.match_start_iso.replace("Z", "+00:00"))
                elapsed_min = (datetime.now(timezone.utc) - start_dt).total_seconds() / 60
                duration = get_game_duration(market.slug, 0, market.sport_tag)
                if duration > 0:
                    elapsed_pct = elapsed_min / duration
                    if elapsed_pct >= 0.50:
                        logger.info("Skipped late-match (%.0f%% elapsed, %s): %s",
                                    elapsed_pct * 100, market.sport_tag, market.question[:60])
                        return False
            except (ValueError, TypeError, ImportError):
                pass
        # Live matches in early/mid phase pass through -- we bet on winners mid-match
        return True
