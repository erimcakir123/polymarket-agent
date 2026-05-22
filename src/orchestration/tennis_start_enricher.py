"""Tennis market'lerin match_start_iso'sunu ESPN ile override eder.

Polymarket tennis startTime'i bazen gec guncellenir veya bos olur (turnuva-level
event). ESPN ATP/WTA scoreboard otoritedir. Cycle basina TTL-cached fetch.

Akis (enrich):
  1. raw market'lerde tennis var mi? Yoksa NO-OP, ESPN'e dokunma.
  2. ESPN tennis/atp + tennis/wta scoreboard fetch (cached).
  3. Her tennis market icin slug-surnames eslestirmesi.
  4. Eslesme bulundu -> market.match_start_iso = ESPN event.commence_time.
  5. Eslesme yok -> market'e dokunma (Polymarket startTime fallback).
  6. ESPN fail -> log warning, override yapma.
"""
from __future__ import annotations

import logging
import time
import unicodedata
from typing import Iterable

from src.config.sport_rules import get_sport_rule
from src.infrastructure.apis.espn_client import ESPNClient, ESPNMatchScore
from src.models.market import MarketData

logger = logging.getLogger(__name__)

_ESPN_TENNIS_SPORT = "tennis"
_VALID_LEAGUES = ("atp", "wta")
_MIN_SLUG_PARTS = 4  # league + surname1 + surname2 + date


def _is_tennis(m: MarketData) -> bool:
    """sport_tag tennis ile basliyor mu, ya da slug 'atp-'/'wta-' ile mi?"""
    tag = (m.sport_tag or "").lower()
    if tag.startswith("tennis"):
        return True
    slug = (m.slug or "").lower()
    return slug.startswith("atp-") or slug.startswith("wta-")


def _league_for_slug(slug: str) -> str | None:
    """Slug prefix'inden league cikar: 'atp-...' -> 'atp', 'wta-...' -> 'wta'."""
    s = (slug or "").lower()
    if s.startswith("atp-"):
        return "atp"
    if s.startswith("wta-"):
        return "wta"
    return None


def _slug_surnames(slug: str) -> tuple[str, str] | None:
    """'atp-minaur-paul-2026-05-22' -> ('minaur', 'paul'). Gecersizse None."""
    parts = (slug or "").lower().split("-")
    if len(parts) < _MIN_SLUG_PARTS:
        return None
    if parts[0] not in _VALID_LEAGUES:
        return None
    surname1 = parts[1].strip()
    surname2 = parts[2].strip()
    if not surname1 or not surname2:
        return None
    return surname1, surname2


def _norm(name: str) -> str:
    """Lowercase + Turkce 'i' donusumu + aksan strip (NFKD)."""
    if not name:
        return ""
    s = name.replace("I", "i").replace("ı", "i")
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    # Combining marks (aksanlar) at
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _match_event(market_slug: str, events: list[ESPNMatchScore]) -> ESPNMatchScore | None:
    """Slug'taki iki soyad ESPN event'in home+away'inde zit taraflarda gecerse eslesme.

    Tennis singles: bir oyuncu home, digeri away. Bu sebeple iki soyad ayni tarafta
    bulunursa eslesme sayilmaz (false-positive engellenir, ornegin doubles slug'lari).
    """
    surnames = _slug_surnames(market_slug)
    if surnames is None:
        return None
    s1, s2 = _norm(surnames[0]), _norm(surnames[1])
    if not s1 or not s2:
        return None
    for ev in events:
        home_n = _norm(ev.home_name)
        away_n = _norm(ev.away_name)
        s1_in_home = s1 in home_n
        s1_in_away = s1 in away_n
        s2_in_home = s2 in home_n
        s2_in_away = s2 in away_n
        # Iki soyad da en az bir tarafta bulunmali, AYRI taraflarda (biri home, digeri away)
        if (s1_in_home and s2_in_away) or (s1_in_away and s2_in_home):
            return ev
    return None


class TennisStartEnricher:
    """Tennis market'lerin match_start_iso'sunu ESPN scoreboard ile override eder.

    Orchestration katmani: ESPN'i (infrastructure) cagirip enriched market listesi
    uretir. Scanner cycle basina bir kere kullanir.
    """

    def __init__(self, espn_client: ESPNClient, cache_ttl_sec: int) -> None:
        self._espn = espn_client
        self._ttl = cache_ttl_sec
        # league -> (fetch_timestamp, events)
        self._cache: dict[str, tuple[float, list[ESPNMatchScore]]] = {}

    def enrich(self, markets: list[MarketData]) -> list[MarketData]:
        # 1) Tennis market var mi? Yoksa NO-OP — ESPN'e dokunma.
        tennis_markets = [m for m in markets if _is_tennis(m)]
        if not tennis_markets:
            return markets

        # 2) Hangi league'leri cekecegiz? Sport rule'dan al.
        leagues_raw = get_sport_rule("tennis", "espn_leagues", default=_VALID_LEAGUES)
        leagues = tuple(leagues_raw) if leagues_raw else _VALID_LEAGUES

        # 3) ESPN scoreboard fetch (cached).
        events_by_league = self._fetch_leagues(leagues)

        # 4) Her tennis market icin eslesme dene, match_start_iso override et.
        out: list[MarketData] = []
        for m in markets:
            if not _is_tennis(m):
                out.append(m)
                continue
            target_leagues = self._leagues_for_market(m, leagues)
            event = self._find_matching_event(m, target_leagues, events_by_league)
            if event is not None and event.commence_time:
                out.append(m.model_copy(update={"match_start_iso": event.commence_time}))
            else:
                out.append(m)
        return out

    def _leagues_for_market(
        self,
        m: MarketData,
        all_leagues: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Slug prefix'i 'atp-' / 'wta-' ise sadece o league. Aksi halde hepsi."""
        slug_league = _league_for_slug(m.slug)
        if slug_league is not None and slug_league in all_leagues:
            return (slug_league,)
        return all_leagues

    def _find_matching_event(
        self,
        m: MarketData,
        target_leagues: tuple[str, ...],
        events_by_league: dict[str, list[ESPNMatchScore]],
    ) -> ESPNMatchScore | None:
        for lg in target_leagues:
            events = events_by_league.get(lg, [])
            ev = _match_event(m.slug, events)
            if ev is not None:
                return ev
        return None

    def _fetch_leagues(
        self,
        leagues: Iterable[str],
    ) -> dict[str, list[ESPNMatchScore]]:
        """League listesi icin ESPN scoreboard cek. TTL cache, basarisizlik cache'lenmez."""
        now = time.time()
        result: dict[str, list[ESPNMatchScore]] = {}
        for lg in leagues:
            cached = self._cache.get(lg)
            if cached is not None and (now - cached[0]) < self._ttl:
                result[lg] = cached[1]
                continue
            try:
                events = self._espn.fetch_scoreboard(_ESPN_TENNIS_SPORT, lg)
            except Exception as e:  # noqa: BLE001 — defensive; ESPN client kendisi de yutar
                logger.warning("ESPN tennis/%s fetch failed: %s", lg, e)
                result[lg] = []
                # basarisizlik cache'lenmez; bir sonraki cycle yeniden dener
                continue
            self._cache[lg] = (now, events)
            result[lg] = events
        return result
