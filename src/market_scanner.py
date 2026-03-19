"""Gamma API market discovery and filtering."""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import List

import requests

from src.config import ScannerConfig
from src.models import MarketData

logger = logging.getLogger(__name__)

GAMMA_BASE = "https://gamma-api.polymarket.com"



class MarketScanner:
    def __init__(self, config: ScannerConfig) -> None:
        self.config = config

    def fetch(self) -> List[MarketData]:
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
        except requests.RequestException as e:
            logger.error("Gamma API error: %s", e)
            return []

        result: List[MarketData] = []
        for raw in resp.json():
            market = self._parse_market(raw)
            if market and self._passes_filters(market):
                result.append(market)

        # Prioritize markets that resolve soon (faster test feedback)
        if self.config.prefer_short_duration:
            result = self._sort_by_end_date(result)

        return result

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

    def _passes_filters(self, market: MarketData) -> bool:
        if market.volume_24h < self.config.min_volume_24h:
            return False
        if market.liquidity < self.config.min_liquidity:
            return False
        # Only filter by tags if the market actually has tags
        # (Gamma API often returns empty tags)
        if self.config.tags and market.tags:
            if not any(t in self.config.tags for t in market.tags):
                return False
        # Skip extreme-priced markets (>95% or <5%) — nearly resolved, minimal edge
        if market.yes_price > 0.95 or market.yes_price < 0.05:
            logger.debug("Excluded extreme price (%.1f%%): %s", market.yes_price * 100, market.question[:60])
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
        # Skip in-progress sports matches only — bot can't watch live scores
        # Before kickoff is fine (can research). Match ~2-3h, so end <3h = likely in-progress
        if market.end_date_iso and self._is_live_sport(market):
            try:
                end_dt = datetime.fromisoformat(market.end_date_iso.replace("Z", "+00:00"))
                hours_left = (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600
                if 0 < hours_left < 3:
                    logger.info("Skipped in-progress sport (%.1fh to end): %s", hours_left, market.question[:60])
                    return False
            except (ValueError, TypeError):
                pass
        return True
