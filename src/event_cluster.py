"""Correlated market grouping by event_id."""
from __future__ import annotations
import logging
from typing import Dict, List

from src.models import MarketData

logger = logging.getLogger(__name__)


class EventCluster:
    def group(self, markets: List[MarketData]) -> Dict[str, List[MarketData]]:
        clusters: Dict[str, List[MarketData]] = {}
        for m in markets:
            if m.event_id:
                clusters.setdefault(m.event_id, []).append(m)
        return clusters

    def check_arbitrage(
        self, cluster_markets: List[MarketData], threshold: float = 0.05
    ) -> dict:
        sum_yes = sum(m.yes_price for m in cluster_markets)
        return {
            "sum_yes": round(sum_yes, 4),
            "is_arbitrage": abs(sum_yes - 1.0) > threshold,
            "direction": "SELL" if sum_yes > 1.0 + threshold else "BUY" if sum_yes < 1.0 - threshold else "NONE",
            "markets": [m.slug for m in cluster_markets],
        }
