"""Polymarket Gamma API client — event/market discovery (DECISIONS §8)."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

import requests

from src.models.market import MarketData

logger = logging.getLogger(__name__)

GAMMA_BASE = "https://gamma-api.polymarket.com"

# Slug prefix → doğru sport_tag. Gamma API event tag sırası güvenilmez
# (ör. ncaab tag'i atp- slug'lu market'e atanabiliyor, ya da nba event'i
# "raptors" team tag'iyle geliyor). Slug prefix en güvenilir kaynak.
#
# Değer config.scanner.allowed_sport_tags whitelist'iyle hizalı olmak zorunda —
# generic "hockey"/"basketball"/"football" SPEC-003'te CBA/KBL/VTB/KHL
# (Odds API kapsamı yok) nedeniyle whitelist'ten çıkarıldı; bu yüzden değerler
# spesifik lig adıdır. Generic "baseball"/"tennis"/"mma" whitelist'te olan
# sporlarda generic kullanılabilir.
#
# Kapsam DECISIONS §7.1 MVP sporlarıyla uyumlu (NFL dahil — tag="nfl" whitelist'te
# olmadığı için scanner zaten ele alıyor, override defansif tutarlılık için).
_SLUG_PREFIX_SPORT: dict[str, str] = {
    # Tennis
    "atp": "tennis", "wta": "tennis",
    # Hockey (specific league — SPEC-003)
    "nhl": "nhl", "ahl": "ahl",
    "liiga": "liiga", "mestis": "mestis",
    "shl": "shl", "allsvenskan": "allsvenskan",
    # Basketball (specific league — SPEC-003)
    "nba": "nba", "wnba": "wnba",
    "ncaab": "ncaab", "wncaab": "wncaab", "cbb": "cbb",
    "euroleague": "euroleague", "nbl": "nbl",
    # Baseball (generic "baseball" whitelist'te)
    "mlb": "baseball", "milb": "baseball",
    "npb": "baseball", "kbo": "baseball",
    # American Football (NFL MVP dışı ama defansif eklendi)
    "nfl": "nfl", "ncaaf": "ncaaf",
    "cfl": "cfl", "ufl": "ufl",
    # Combat (generic "mma" whitelist'te)
    "ufc": "mma", "mma": "mma", "boxing": "boxing",
    # Golf (wildcards lpga*/liv*/pga* whitelist'te)
    "lpga": "lpga", "liv": "liv", "pga": "pga",
}
EVENTS_PER_PAGE = 200
_SPORTS_CACHE_SEC = 21_600  # 6h
PARENT_TAGS: list[tuple[str, int]] = [
    ("sports", 1),
    ("esports", 64),
]
_DEFAULT_TIMEOUT = 20

# SPEC-Z (2026-05-24): start_date_min/max API filter hack'i kaldırıldı.
# Eski yorumda Polymarket-side bug (yakın event'leri tag fetch'inde göstermeme)
# için workaround idi; 2026-05-24 test'inde bu davranış görülmüyor, API tüm aktif
# event'leri döndürüyor. Match-saat filtreleme zaten MarketScanner._passes_filters
# içinde match_start_iso bazlı yapılıyor (24h hours_to_start + match_start_recent
# kontrolleri). İki katmanlı filter karışıklığı + 24h lookback hack'inin "bugünkü
# event'leri kaçırma" yan etkisi giderildi.


def _default_http_get(url: str, params: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.get(url, params=params or {}, timeout=timeout)


def _safe_float(v: Any) -> float | None:
    """None / "" / hatalı string güvenli float conversion. Phantom orderbook için kritik."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _normalize_iso(raw: str) -> str:
    """Polymarket tarih string'ini ISO 8601 formatına çevirir.

    SPEC-Z3 (2026-05-24): market.gameStartTime "2026-05-24 16:35:00+00" gibi boşluklu
    Postgres timestamp formatı dönebilir; Python datetime.fromisoformat 'T' separator
    bekliyor. Bu helper boşluğu 'T' yapar ve "+00" → "+00:00" düzeltir.
    """
    if not raw:
        return ""
    s = raw.strip()
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    # Postgres style "+00" suffix → ISO "+00:00"
    if s.endswith("+00"):
        s = s + ":00"
    return s


class GammaClient:
    """Ham pazar verisini çeken infra istemcisi. Filtering orkestrasyonda."""

    def __init__(self, http_get: Callable[..., Any] = _default_http_get) -> None:
        self._http = http_get
        # Cache holds (category, kind, id) tuples where kind in {"tag","series"}.
        # Series-based fetch picks up ITF tennis events that tag query misses.
        self._league_sources: list[tuple[str, str, int]] = []
        self._league_sources_ts: float = 0.0

    def fetch_events(self) -> list[MarketData]:
        try:
            sources = self._fetch_league_sources() or [(c, "tag", i) for c, i in PARENT_TAGS]
        except Exception as e:
            logger.warning("Gamma /sports failed: %s — using parent tags", e)
            sources = [(c, "tag", i) for c, i in PARENT_TAGS]

        seen: set[str] = set()
        out: list[MarketData] = []

        for category, kind, value in sources:
            try:
                self._fetch_by_param(f"{kind}_id", value, category, seen, out)
            except Exception as e:
                logger.warning("Gamma fetch %s=%s failed: %s", kind, value, e)

        # Parent fallback (yeni tag'ler için)
        for category, tag_id in PARENT_TAGS:
            try:
                self._fetch_by_param("tag_id", tag_id, category, seen, out)
            except Exception as e:
                logger.warning("Gamma parent-tag fetch failed: %s", e)

        logger.info("Gamma fetched %d unique markets", len(out))
        return out

    def _fetch_by_param(
        self,
        param_name: str,
        value: int,
        category: str,
        seen: set[str],
        out: list[MarketData],
    ) -> None:
        """Paginate /events filtered by tag_id or series_id and ingest each event."""
        offset = 0
        while True:
            params = {
                param_name: value,
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
            # Slug-prefix ile event tag tutarsızlığını düzelt (DECISIONS §7.3)
            slug_val = str(raw.get("slug", ""))
            sport_tag_val = str(raw.get("_sport_tag", "") or "")
            slug_prefix = slug_val.lower().split("-")[0] if slug_val else ""
            corrected_sport = _SLUG_PREFIX_SPORT.get(slug_prefix)
            if corrected_sport and corrected_sport != sport_tag_val:
                logger.warning(
                    "sport_tag override: slug=%s tag=%s -> %s",
                    slug_val, sport_tag_val, corrected_sport,
                )
                sport_tag_val = corrected_sport

            return MarketData(
                condition_id=str(raw.get("conditionId", "")),
                question=str(raw.get("question", "")),
                slug=slug_val,
                yes_token_id=str(tokens[0]),
                no_token_id=str(tokens[1]),
                yes_price=float(prices[0]),
                no_price=float(prices[1]),
                liquidity=float(raw.get("liquidity", 0) or 0),
                volume_24h=float(raw.get("volume24hr", 0) or 0),
                tags=[],
                end_date_iso=str(raw.get("endDate", "") or ""),
                # match_start_iso öncelik: market.gameStartTime (kesin maç saati,
                # SPEC-Z3 2026-05-24) → event.startTime (single-game) → market.startDate
                # (futures fallback) → "". gameStartTime "2026-05-24 16:35:00+00" gibi
                # boşluklu olabilir, ISO formatına çevir.
                match_start_iso=_normalize_iso(
                    raw.get("gameStartTime", "")
                    or raw.get("_event_start_time", "")
                    or raw.get("startDate", "")
                    or ""
                ),
                event_id=raw.get("_event_id") or None,
                event_live=bool(raw.get("_event_live", False)),
                event_ended=bool(raw.get("_event_ended", False)),
                sport_tag=sport_tag_val,
                sports_market_type=str(raw.get("sportsMarketType", "") or ""),
                closed=bool(raw.get("closed", False)),
                resolved=bool(raw.get("resolved", False)),
                accepting_orders=bool(raw.get("acceptingOrders", True)),
                best_bid=_safe_float(raw.get("bestBid")),
                best_ask=_safe_float(raw.get("bestAsk")),
            )
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            logger.debug("parse_market failed for %s: %s", raw.get("conditionId", "?"), e)
            return None

    def fetch_closed_market_by_condition(self, condition_id: str) -> dict | None:
        """Polymarket gamma'da kapanmis (resolved) market'i condition_id ile getir.

        Sadece closed=true market'lere bakar — yeni open market'leri fetch_events handles.
        Bot acik pozisyonun underlying market'i bu arada resolve oldu mu kontrol icin
        kullanir (ExitProcessor polymarket-resolution check).

        Hicbir hit yok ise None. HTTP hata sessiz None doner (warning log) — caller
        graceful skip yapar, bot crash etmez.
        """
        try:
            resp = self._http(
                f"{GAMMA_BASE}/markets",
                params={"condition_ids": condition_id, "closed": "true"},
                timeout=_DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0]
            if isinstance(data, dict):
                return data
            return None
        except Exception as e:
            logger.warning("Gamma closed-market fetch failed %s: %s", condition_id[:20], e)
            return None

    def _fetch_league_sources(self) -> list[tuple[str, str, int]]:
        """Returns (category, kind, id) where kind in {"tag","series"}. Cached.

        Series-based queries surface markets that tag queries miss — most
        notably ITF tennis, which has no tennis-specific tag in Polymarket's
        taxonomy and is only reachable via series_id (e.g. 11634).
        """
        if self._league_sources and (time.time() - self._league_sources_ts) < _SPORTS_CACHE_SEC:
            return self._league_sources
        resp = self._http(f"{GAMMA_BASE}/sports", timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
        sports = resp.json() or []
        seen_tags: set[int] = set()
        seen_series: set[int] = set()
        result: list[tuple[str, str, int]] = []
        for entry in sports:
            sport_code = entry.get("sport", "")
            for t in str(entry.get("tags", "")).split(","):
                t = t.strip()
                if t.isdigit():
                    tid = int(t)
                    if tid not in seen_tags:
                        seen_tags.add(tid)
                        result.append((sport_code, "tag", tid))
            series_raw = str(entry.get("series", "") or "").strip()
            if series_raw.isdigit():
                sid = int(series_raw)
                if sid not in seen_series:
                    seen_series.add(sid)
                    result.append((sport_code, "series", sid))
        if result:
            self._league_sources = result
            self._league_sources_ts = time.time()
        return result
