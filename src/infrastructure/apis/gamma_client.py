"""Polymarket Gamma API client — event/market discovery (TDD §8)."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

import requests

from src.models.market import MarketData

logger = logging.getLogger(__name__)

GAMMA_BASE = "https://gamma-api.polymarket.com"
EVENTS_PER_PAGE = 200
_SPORTS_CACHE_SEC = 21_600  # 6h
PARENT_TAGS: list[tuple[str, int]] = [
    ("sports", 1),
    ("esports", 64),
]
_DEFAULT_TIMEOUT = 20


def _default_http_get(url: str, params: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.get(url, params=params or {}, timeout=timeout)


class GammaClient:
    """Ham pazar verisini çeken infra istemcisi. Filtering orkestrasyonda."""

    def __init__(self, http_get: Callable[..., Any] = _default_http_get) -> None:
        self._http = http_get
        self._league_tags: list[tuple[str, int]] = []
        self._league_tags_ts: float = 0.0

    def fetch_events(self) -> list[MarketData]:
        try:
            tags = self._fetch_league_tags() or PARENT_TAGS
        except Exception as e:
            logger.warning("Gamma /sports failed: %s — using parent tags", e)
            tags = PARENT_TAGS

        seen: set[str] = set()
        out: list[MarketData] = []

        for category, tag_id in tags:
            try:
                self._fetch_by_tag(tag_id, category, seen, out)
            except Exception as e:
                logger.warning("Gamma fetch tag=%s failed: %s", tag_id, e)

        # Parent fallback (yeni tag'ler için)
        for category, tag_id in PARENT_TAGS:
            try:
                self._fetch_by_tag(tag_id, category, seen, out)
            except Exception as e:
                logger.warning("Gamma parent-tag fetch failed: %s", e)

        logger.info("Gamma fetched %d unique markets", len(out))
        return out

    def _fetch_by_tag(
        self,
        tag_id: int,
        category: str,
        seen: set[str],
        out: list[MarketData],
    ) -> None:
        offset = 0
        while True:
            params = {
                "tag_id": tag_id,
                "active": "true",
                "closed": "false",
                "limit": EVENTS_PER_PAGE,
                "offset": offset,
            }
            resp = self._http(f"{GAMMA_BASE}/events", params=params, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
            events = resp.json() or []
            if not events:
                return
            for event in events:
                self._ingest_event(event, category, seen, out)
            if len(events) < EVENTS_PER_PAGE:
                return
            offset += EVENTS_PER_PAGE

    def _ingest_event(self, event: dict, category: str, seen: set[str], out: list[MarketData]) -> None:
        event_id = str(event.get("id", "")) or None
        event_live = bool(event.get("live", False))
        event_ended = bool(event.get("ended", False))
        sport_tag = category
        # Sport-specific tag: 'sports'/'esports' parent'ı atla, ilk spesifik tag'i al
        tags = event.get("tags") or []
        if isinstance(tags, list):
            _GENERIC = {"sports", "esports", "games", "all", ""}
            for t in tags:
                if not isinstance(t, dict):
                    continue
                slug = str(t.get("slug", "") or "").lower()
                if slug and slug not in _GENERIC:
                    sport_tag = slug
                    break
        for raw in event.get("markets", []) or []:
            cid = raw.get("conditionId", "")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            raw["_event_id"] = event_id or ""
            raw["_event_live"] = event_live
            raw["_event_ended"] = event_ended
            raw["_sport_tag"] = sport_tag
            raw["_event_start_time"] = event.get("startTime", "") or ""
            parsed = self._parse_market(raw)
            if parsed is not None:
                out.append(parsed)

    def _parse_market(self, raw: dict) -> MarketData | None:
        try:
            tokens = raw.get("clobTokenIds")
            if isinstance(tokens, str):
                tokens = json.loads(tokens)
            prices = raw.get("outcomePrices")
            if isinstance(prices, str):
                prices = json.loads(prices)
            if not tokens or not prices or len(tokens) < 2 or len(prices) < 2:
                return None
            return MarketData(
                condition_id=str(raw.get("conditionId", "")),
                question=str(raw.get("question", "")),
                slug=str(raw.get("slug", "")),
                yes_token_id=str(tokens[0]),
                no_token_id=str(tokens[1]),
                yes_price=float(prices[0]),
                no_price=float(prices[1]),
                liquidity=float(raw.get("liquidity", 0) or 0),
                volume_24h=float(raw.get("volume24hr", 0) or 0),
                tags=[],
                end_date_iso=str(raw.get("endDate", "") or ""),
                # match_start_iso öncelik: event.startTime (single-game maç saati,
                # mevcutsa) → market.startDate (futures fallback — market yaratılma
                # tarihi) → "" (ikisi de yoksa)
                match_start_iso=str(
                    raw.get("_event_start_time", "")
                    or raw.get("startDate", "")
                    or ""
                ),
                event_id=raw.get("_event_id") or None,
                event_live=bool(raw.get("_event_live", False)),
                event_ended=bool(raw.get("_event_ended", False)),
                sport_tag=str(raw.get("_sport_tag", "") or ""),
                sports_market_type=str(raw.get("sportsMarketType", "") or ""),
                closed=bool(raw.get("closed", False)),
                resolved=bool(raw.get("resolved", False)),
                accepting_orders=bool(raw.get("acceptingOrders", True)),
            )
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            logger.debug("parse_market failed for %s: %s", raw.get("conditionId", "?"), e)
            return None

    def _fetch_league_tags(self) -> list[tuple[str, int]]:
        if self._league_tags and (time.time() - self._league_tags_ts) < _SPORTS_CACHE_SEC:
            return self._league_tags
        resp = self._http(f"{GAMMA_BASE}/sports", timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
        sports = resp.json() or []
        seen: set[int] = set()
        result: list[tuple[str, int]] = []
        for entry in sports:
            sport_code = entry.get("sport", "")
            for t in str(entry.get("tags", "")).split(","):
                t = t.strip()
                if t.isdigit():
                    tid = int(t)
                    if tid not in seen:
                        seen.add(tid)
                        result.append((sport_code, tid))
        if result:
            self._league_tags = result
            self._league_tags_ts = time.time()
        return result
