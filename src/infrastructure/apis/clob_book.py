"""Polymarket CLOB orderbook fetch with TTL cache.

Read-only, no auth, free endpoint. Used by paper mode to simulate fills
against real orderbook state.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

_CLOB_BOOK_URL = "https://clob.polymarket.com/book"
_DEFAULT_TIMEOUT = 10


def _default_http_get(url: str, params: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.get(url, params=params or {}, timeout=timeout)


class ClobBook:
    """Cached orderbook fetch. TTL per token_id."""

    def __init__(
        self,
        http_get: Callable[..., Any] | None = None,
        cache_ttl_sec: int = 5,
    ) -> None:
        self._http = http_get or _default_http_get
        self._ttl = cache_ttl_sec
        self._cache: dict[str, tuple[float, dict]] = {}

    def fetch(self, token_id: str) -> dict:
        """Returns {"asks": [{"price": "...", "size": "..."}], "bids": [...]}.

        Empty {"asks": [], "bids": []} on HTTP failure (logged WARNING).
        """
        now = time.time()
        cached = self._cache.get(token_id)
        if cached and (now - cached[0]) < self._ttl:
            return cached[1]
        try:
            resp = self._http(_CLOB_BOOK_URL, params={"token_id": token_id}, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
            book = resp.json() or {}
            normalized = {"asks": book.get("asks") or [], "bids": book.get("bids") or []}
            self._cache[token_id] = (now, normalized)
            return normalized
        except Exception as e:
            logger.warning("clob_book fetch failed for %s: %s", token_id[:16], e)
            return {"asks": [], "bids": []}
