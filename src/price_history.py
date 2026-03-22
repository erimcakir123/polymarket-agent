"""Collect CLOB price history on position close for future calibration."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

PRICE_HISTORY_DIR = Path("logs/price_history")


def save_price_history(
    slug: str,
    token_id: str,
    entry_price: float,
    exit_price: float,
    exit_reason: str,
    exit_layer: str,
    match_start_iso: str,
    number_of_games: int,
    ever_in_profit: bool,
    peak_pnl_pct: float,
    match_score: str,
) -> None:
    """Fetch CLOB price history and save to disk."""
    try:
        resp = requests.get(
            "https://clob.polymarket.com/prices-history",
            params={"market": token_id, "interval": "max", "fidelity": "60"},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("Price history fetch failed for %s: %d", slug[:30], resp.status_code)
            return

        history = resp.json().get("history", [])

        record = {
            "slug": slug,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "exit_layer": exit_layer,
            "match_start_iso": match_start_iso,
            "number_of_games": number_of_games,
            "ever_in_profit": ever_in_profit,
            "peak_pnl_pct": peak_pnl_pct,
            "match_score": match_score,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "price_history": history,
        }

        PRICE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        safe_slug = slug.replace("/", "_")[:80]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = PRICE_HISTORY_DIR / f"{safe_slug}_{ts}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        logger.info("Saved price history: %s (%d points)", slug[:30], len(history))

    except Exception as e:
        logger.warning("Price history save failed for %s: %s", slug[:30], e)
