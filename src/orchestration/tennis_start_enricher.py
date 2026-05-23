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
from datetime import datetime, timezone
from typing import Iterable

from src.config.sport_rules import get_sport_rule
from src.infrastructure.apis.espn_client import ESPNClient, ESPNMatchScore
from src.models.market import MarketData
from src.models.position import Position

logger = logging.getLogger(__name__)

_VALID_LEAGUES = ("atp", "wta")
_MIN_SLUG_PARTS = 4  # league + surname1 + surname2 + date
_DOUBLES_TOKEN = "doubles"


def _is_tennis(m: MarketData) -> bool:
    """sport_tag tennis ile basliyor mu, ya da slug 'atp-'/'wta-' ile mi?"""
    tag = (m.sport_tag or "").lower()
    if tag.startswith("tennis"):
        return True
    slug = (m.slug or "").lower()
    return slug.startswith("atp-") or slug.startswith("wta-")


def _is_position_tennis(p: Position) -> bool:
    """Position icin tennis kontrolu — sport_tag tennis veya slug atp-/wta-."""
    tag = (p.sport_tag or "").lower()
    if tag.startswith("tennis"):
        return True
    slug = (p.slug or "").lower()
    return slug.startswith("atp-") or slug.startswith("wta-")


def _iso_to_yyyymmdd(iso: str) -> str | None:
    """ISO timestamp'in tarih kismini YYYYMMDD'ye cevir. Parse edemezse None."""
    if not iso or len(iso) < 10:
        return None
    # ISO'nun ilk 10 karakteri YYYY-MM-DD; tireleri sil
    head = iso[:10]
    if head[4] != "-" or head[7] != "-":
        return None
    return head[0:4] + head[5:7] + head[8:10]


def _same_day(iso_a: str, iso_b: str) -> bool:
    """Iki ISO timestamp ayni UTC gunde mi? Parse edemezse False (override iptal)."""
    a = _iso_to_yyyymmdd(iso_a)
    b = _iso_to_yyyymmdd(iso_b)
    return bool(a) and a == b


def _league_for_slug(slug: str) -> str | None:
    """Slug prefix'inden league cikar: 'atp-...' -> 'atp', 'wta-...' -> 'wta'."""
    s = (slug or "").lower()
    if s.startswith("atp-"):
        return "atp"
    if s.startswith("wta-"):
        return "wta"
    return None


def _slug_surnames(slug: str) -> tuple[str, str] | None:
    """Slug'dan iki soyad cikar.

    'atp-minaur-paul-2026-05-22'              -> ('minaur', 'paul')
    'atp-doubles-fortrom-gadatu-2026-05-22'   -> ('fortrom', 'gadatu') — 'doubles' atlanir
    'wta-doubles-smith-jones-2026-05-22'      -> ('smith', 'jones')
    4+ parca yoksa ya da parts[0] atp/wta degilse None.
    """
    if not slug:
        return None
    parts = slug.lower().split("-")
    if len(parts) < _MIN_SLUG_PARTS or parts[0] not in _VALID_LEAGUES:
        return None
    offset = 2 if parts[1] == _DOUBLES_TOKEN else 1
    if len(parts) < offset + 2:
        return None
    surname1 = parts[offset].strip()
    surname2 = parts[offset + 1].strip()
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
        # (league, date_yyyymmdd) -> (fetch_timestamp, events)
        self._cache: dict[tuple[str, str], tuple[float, list[ESPNMatchScore]]] = {}

    def enrich(self, markets: list[MarketData]) -> list[MarketData]:
        # 1) Tennis market var mi? Yoksa NO-OP — ESPN'e dokunma.
        tennis_markets = [m for m in markets if _is_tennis(m)]
        if not tennis_markets:
            return markets

        # 2) Hangi league'leri cekecegiz? Sport rule'dan al.
        leagues_raw = get_sport_rule("tennis", "espn_leagues", default=_VALID_LEAGUES)
        leagues = tuple(leagues_raw) if leagues_raw else _VALID_LEAGUES

        # 3) Tennis market'lerin ihtiyac duydugu ESPN gunlerini topla.
        # Her market'in match_start_iso'sundan YYYYMMDD cikar; UTC bugun de eklenir
        # (Polymarket startTime bos gelirse fallback). Her unique gun icin ESPN fetch.
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        dates: set[str] = {today_str}
        for tm in tennis_markets:
            d = _iso_to_yyyymmdd(tm.match_start_iso)
            if d:
                dates.add(d)
        events_by_league = self._fetch_dates(leagues, tuple(sorted(dates)))

        # 4) Her tennis market icin eslesme dene, match_start_iso override et.
        out: list[MarketData] = []
        for m in markets:
            if not _is_tennis(m):
                out.append(m)
                continue
            target_leagues = self._leagues_for_slug(m.slug, leagues)
            event = self._find_matching_event_by_slug(
                m.slug, target_leagues, events_by_league,
            )
            if event is not None and event.commence_time and _same_day(
                m.match_start_iso, event.commence_time
            ):
                out.append(m.model_copy(update={"match_start_iso": event.commence_time}))
            else:
                # Tarih uyumsuz ESPN eslesmesi false-positive sayilir (ayni soyad
                # farkli turnuva). Sessizce Polymarket startTime'a fallback.
                out.append(m)
        return out

    def refresh_positions(self, positions: list[Position]) -> None:
        """Acik tennis pozisyonlarinin match_start_iso'sunu ESPN ile in-place gunceller.

        Akis:
          1. positions icinde tennis var mi? Yoksa NO-OP, ESPN'e dokunma.
          2. Her tennis pos'un match_start_iso'sundan YYYYMMDD topla → unique dates.
          3. ESPN'i bu gunler icin fetch (cached).
          4. Slug-surname eslestirmesi ile her tennis pos'un match_start_iso'sunu
             guncelle. Same-day guard, no-match-keep, ESPN-fail-keep mantigi enrich
             ile birebir ayni (DRY: ayni helper'lar).
          5. Non-tennis dokunulmaz.
        """
        tennis_positions = [p for p in positions if _is_position_tennis(p)]
        if not tennis_positions:
            return

        leagues_raw = get_sport_rule("tennis", "espn_leagues", default=_VALID_LEAGUES)
        leagues = tuple(leagues_raw) if leagues_raw else _VALID_LEAGUES

        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        dates: set[str] = {today_str}
        for tp in tennis_positions:
            d = _iso_to_yyyymmdd(tp.match_start_iso)
            if d:
                dates.add(d)
        events_by_league = self._fetch_dates(leagues, tuple(sorted(dates)))

        for p in tennis_positions:
            target_leagues = self._leagues_for_slug(p.slug, leagues)
            event = self._find_matching_event_by_slug(
                p.slug, target_leagues, events_by_league,
            )
            if event is None or not event.commence_time:
                continue
            if not _same_day(p.match_start_iso, event.commence_time):
                continue
            p.match_start_iso = event.commence_time

    def _leagues_for_slug(
        self,
        slug: str,
        all_leagues: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Slug prefix'i 'atp-' / 'wta-' ise sadece o league. Aksi halde hepsi."""
        slug_league = _league_for_slug(slug)
        if slug_league is not None and slug_league in all_leagues:
            return (slug_league,)
        return all_leagues

    def _find_matching_event_by_slug(
        self,
        slug: str,
        target_leagues: tuple[str, ...],
        events_by_league: dict[str, list[ESPNMatchScore]],
    ) -> ESPNMatchScore | None:
        for lg in target_leagues:
            events = events_by_league.get(lg, [])
            ev = _match_event(slug, events)
            if ev is not None:
                return ev
        return None

    def _fetch_dates(
        self,
        leagues: Iterable[str],
        dates: Iterable[str],
    ) -> dict[str, list[ESPNMatchScore]]:
        """(league, date) ciftleri icin ESPN tennis maclari fetch.

        TTL cache (league, date) anahtarli. Birden fazla gun istenirse her gun ayri
        fetch (ATP+WTA × bugun+yarin = 4 fetch). Cache hit fetch'i atlar. Basarisizlik
        cache'lenmez.

        Donus: league -> tum gunlerin birlesik event listesi.
        """
        now = time.time()
        result: dict[str, list[ESPNMatchScore]] = {lg: [] for lg in leagues}
        for lg in result.keys():
            for date_str in dates:
                key = (lg, date_str)
                cached = self._cache.get(key)
                if cached is not None and (now - cached[0]) < self._ttl:
                    result[lg].extend(cached[1])
                    continue
                try:
                    events = self._espn.fetch_tennis_matches_today(lg, date_str)
                except Exception as e:  # noqa: BLE001 — defensive; ESPN client kendisi de yutar
                    logger.warning(
                        "ESPN tennis/%s @ %s fetch failed: %s — Polymarket start kalir",
                        lg, date_str, e,
                    )
                    # basarisizlik cache'lenmez; bir sonraki cycle yeniden dener
                    continue
                self._cache[key] = (now, events)
                result[lg].extend(events)
        return result
