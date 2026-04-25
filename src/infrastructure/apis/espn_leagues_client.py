"""ESPN soccer league listesi fetch (PLAN-012).

ESPN core API tek endpoint'te 250+ soccer liglerini döndürür. Her öğede `$ref`
URL içinde league slug (arg.1, rus.1, uefa.champions vb.) bulunur.

Runtime discovery için kullanılır: fetch 24h'de bir, slug listesi disk cache'e
yazılır (persistence/soccer_league_cache.py). Espn_client.py kardeşi — aynı
hata yönetimi paterni (try → boş liste + WARNING).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_LEAGUES_URL = "https://sports.core.api.espn.com/v2/sports/soccer/leagues"
_DEFAULT_LIMIT = 500
_HTTP_TIMEOUT = 15


def fetch_soccer_leagues(
    http_get: Callable[..., Any] | None = None,
    timeout: int = _HTTP_TIMEOUT,
) -> list[str]:
    """ESPN soccer league slug listesini getir.

    Args:
        http_get: HTTP GET callable (test mock için). Default: httpx.get.
        timeout: HTTP timeout (saniye).

    Returns:
        ["arg.1", "rus.1", "uefa.champions", ...]. Hata → boş liste + WARNING.
    """
    get = http_get or httpx.get
    try:
        resp = get(_LEAGUES_URL, params={"limit": _DEFAULT_LIMIT}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json() or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("ESPN leagues fetch failed: %s", exc)
        return []

    items = data.get("items") or []
    slugs: list[str] = []
    for item in items:
        ref = (item.get("$ref") or "") if isinstance(item, dict) else ""
        if not ref or "/leagues/" not in ref:
            continue
        tail = ref.split("/leagues/", 1)[1]
        slug = tail.split("?", 1)[0].strip()
        if slug:
            slugs.append(slug)
    return slugs
