"""Large position monitoring via Polymarket Data API."""
from __future__ import annotations
import logging
from typing import Dict, List, Optional

import requests

from src.config import WhaleConfig

logger = logging.getLogger(__name__)

DATA_API_BASE = "https://data-api.polymarket.com"


class WhaleTracker:
    def __init__(self, config: WhaleConfig) -> None:
        self.config = config
        self._whale_history: Dict[str, List[dict]] = {}

    def check_market(self, condition_id: str) -> List[dict]:
        try:
            resp = requests.get(
                f"{DATA_API_BASE}/positions",
                params={"market": condition_id, "sizeThreshold": self.config.min_position_usd},
                timeout=10,
            )
            resp.raise_for_status()
            positions = resp.json()
        except Exception as e:
            logger.warning("Whale tracker API error: %s", e)
            return []

        whales = []
        for pos in positions:
            size = float(pos.get("size", 0))
            if size >= self.config.min_position_usd:
                whales.append({
                    "address": pos.get("proxyWallet", ""),
                    "direction": pos.get("outcome", "").upper(),
                    "size_usd": size,
                    "condition_id": condition_id,
                })
        return whales

    def compute_signal(self, whale_positions: List[dict]) -> Optional[float]:
        if not whale_positions:
            return None
        yes_total = sum(w["size_usd"] for w in whale_positions if w.get("direction") == "YES")
        no_total = sum(w["size_usd"] for w in whale_positions if w.get("direction") == "NO")
        total = yes_total + no_total
        if total == 0:
            return None
        return yes_total / total
