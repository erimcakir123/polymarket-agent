"""Gamma API market discovery and filtering."""
from __future__ import annotations
import json
import logging
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
        return result

    def _parse_market(self, raw: dict) -> MarketData | None:
        try:
            prices = json.loads(raw.get("outcomePrices", '["0.5","0.5"]'))
            tokens = json.loads(raw.get("clobTokenIds", '["",""]'))
            tags_raw = json.loads(raw.get("tags", "[]"))
            tag_labels = [t.get("label", "") for t in tags_raw if isinstance(t, dict)]

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

    def _passes_filters(self, market: MarketData) -> bool:
        if market.volume_24h < self.config.min_volume_24h:
            return False
        if market.liquidity < self.config.min_liquidity:
            return False
        if self.config.tags:
            if not any(t in self.config.tags for t in market.tags):
                return False
        return True
