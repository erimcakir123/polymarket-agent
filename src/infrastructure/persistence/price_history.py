"""CLOB price-history collector (exit sonrası post-mortem kayıt)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

_CLOB_HISTORY_URL = "https://clob.polymarket.com/prices-history"
_DEFAULT_TIMEOUT_SEC = 15


def _default_http_get(url: str, params: dict, timeout: int) -> Any:
    return requests.get(url, params=params, timeout=timeout)


class PriceHistorySaver:
    def __init__(
        self,
        base_dir: Path | str = Path("logs/price_history"),
        http_get: Callable[..., Any] = _default_http_get,
    ) -> None:
        self.base_dir = Path(base_dir)
        self._http_get = http_get

    def save(
        self,
        slug: str,
        token_id: str,
        entry_price: float,
        exit_price: float,
        exit_reason: str,
        match_score: str,
        match_start_iso: str = "",
        ever_in_profit: bool = False,
        peak_pnl_pct: float = 0.0,
    ) -> None:
        try:
            resp = self._http_get(
                _CLOB_HISTORY_URL,
                params={"market": token_id, "interval": "max", "fidelity": "60"},
                timeout=_DEFAULT_TIMEOUT_SEC,
            )
            if resp.status_code != 200:
                logger.warning("price_history fetch %s status=%d", slug[:30], resp.status_code)
                return
            history = resp.json().get("history", [])
        except Exception as e:
            logger.warning("price_history fetch failed for %s: %s", slug[:30], e)
            return

        record = {
            "slug": slug,
            "token_id": token_id,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "match_start_iso": match_start_iso,
            "ever_in_profit": ever_in_profit,
            "peak_pnl_pct": peak_pnl_pct,
            "match_score": match_score,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "price_history": history,
        }

        self.base_dir.mkdir(parents=True, exist_ok=True)
        safe = slug.replace("/", "_").replace(" ", "_")[:80]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self.base_dir / f"{safe}_{ts}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        logger.info("Saved price history: %s (%d points)", slug[:30], len(history))
