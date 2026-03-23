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

# Verified tag_ids from Gamma /sports endpoint (2026-03-23)
# Parent tags cover all sub-leagues (e.g. 100350 = ALL soccer)
SPORT_TAG_IDS: dict[str, int] = {
    # Esports
    "cs2": 100780,
    "lol": 65,
    "dota2": 102366,
    "valorant": 101672,
    "mlbb": 102750,
    "overwatch": 102753,
    # Traditional sports
    "nba": 745,
    "nhl": 899,
    "mlb": 100381,
    "nfl": 450,
    "soccer": 100350,   # Parent — covers EPL, La Liga, Serie A, Bundesliga, UCL, etc.
    "cricket": 517,
}

ESPORT_TAGS: set[str] = {"cs2", "lol", "dota2", "valorant", "mlbb", "overwatch"}

EVENTS_PER_TAG = 100  # Max events per tag_id query

# Sports with 500+ events — use date filter to get nearby matches instead of first 100
HIGH_EVENT_TAGS: set[str] = {"soccer", "cricket"}


class MarketScanner:
    def __init__(self, config: ScannerConfig) -> None:
        self.config = config

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
        """Fetch markets via /events endpoint using tag_id (numeric).
        The broken text `tag` parameter is bypassed entirely.
        Each tag_id call returns events with nested markets arrays."""
        seen_ids: set[str] = set()
        all_raw: list[dict] = []
        total_events = 0

        for sport, tag_id in SPORT_TAG_IDS.items():
            params: dict = {
                "tag_id": tag_id,
                "active": "true",
                "closed": "false",
                "limit": EVENTS_PER_TAG,
            }
            # High-event sports (soccer, cricket): use date filter to get
            # nearby daily matches instead of first 100 (mostly long-term)
            if sport in HIGH_EVENT_TAGS:
                now = datetime.now(timezone.utc)
                params["end_date_min"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
                params["end_date_max"] = (now + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")

            try:
                resp = requests.get(f"{GAMMA_BASE}/events", params=params, timeout=20)
                resp.raise_for_status()
                events = resp.json()
                event_count = len(events)
                total_events += event_count
                market_count = 0

                for event in events:
                    event_live = event.get("live", False)
                    markets = event.get("markets", [])
                    for raw_market in markets:
                        cid = raw_market.get("conditionId", "")
                        if cid and cid not in seen_ids:
                            seen_ids.add(cid)
                            raw_market["_event_live"] = bool(event_live)
                            raw_market["_event_ended"] = bool(event.get("ended", False))
                            raw_market["_sport_tag"] = sport
                            all_raw.append(raw_market)
                            market_count += 1

                logger.debug("tag_id %s (%s): %d events, %d new markets",
                             tag_id, sport, event_count, market_count)
            except requests.RequestException as e:
                logger.error("Gamma /events error (tag_id=%s, %s): %s", tag_id, sport, e)

        logger.info("Tag-ID scan: %d tag queries → %d events → %d unique markets",
                     len(SPORT_TAG_IDS), total_events, len(all_raw))
        return all_raw

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
        if "elections" in tags_lower or "politics" in tags_lower:
            # Only if question also has election keywords (not all politics = elections)
            if any(kw in q_lower for kw in self._ELECTION_KEYWORDS):
                return True
        return any(kw in q_lower for kw in self._ELECTION_KEYWORDS)

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
        """Sort markets so those resolving soonest come first. No end_date → last."""
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

    def _is_esport(self, market: MarketData) -> bool:
        """Check if market is an esports event (volume spikes only in last ~2h)."""
        if market.sport_tag in ESPORT_TAGS:
            return True
        tags_lower = {t.lower() for t in market.tags}
        return bool(tags_lower & {"esports"})

    def _is_sports_or_esports(self, market: MarketData) -> bool:
        """Check if market is sports or esports (not politics, crypto, etc.)."""
        return self._is_live_sport(market)  # Already covers sports + esports tags & keywords

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
        # Esports markets: volume spikes only in last ~2h before match,
        # so skip volume filter — only require liquidity
        is_esport = self._is_esport(market)
        if not is_esport and market.volume_24h < self.config.min_volume_24h:
            return False
        if market.liquidity < self.config.min_liquidity:
            return False
        # Only filter by tags if the market actually has tags
        # (Gamma API often returns empty tags)
        if self.config.tags and market.tags:
            if not any(t in self.config.tags for t in market.tags):
                return False
        # Skip nearly-resolved markets (>95%) — no edge left
        # Allow low-price tokens (<5%) through — FAR/penny alpha candidates
        if market.yes_price > 0.95:
            logger.debug("Excluded near-resolved (%.1f%%): %s", market.yes_price * 100, market.question[:60])
            return False
        # Skip markets resolving too far out — elections get a longer window (90 days)
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
        # Skip live/ended matches — Gamma API provides definitive live & ended status
        if (market.event_live or market.event_ended) and self._is_live_sport(market):
            status = "ENDED" if market.event_ended else "LIVE"
            logger.info("Skipped %s event (Gamma): %s", status, market.question[:60])
            return False
        return True
