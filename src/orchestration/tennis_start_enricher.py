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
from datetime import datetime, timedelta, timezone
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

    def __init__(
        self,
        espn_client: ESPNClient,
        cache_ttl_sec: int,
        lookahead_days: int = 3,
    ) -> None:
        self._espn = espn_client
        self._ttl = cache_ttl_sec
        # SPEC-Z14 (2026-06-03): bugun + N gun ESPN scoreboard pencere.
        # Polymarket gameStartTime ±1 gun yanlis olabiliyor → ESPN penceresi
        # genis tutulur, slug-surname eslesmesi otoriter kabul edilir.
        self._lookahead_days = max(0, lookahead_days)
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
        # Bugun + lookahead penceresi + her market'in Polymarket startTime gunu.
        # Polymarket startTime ±1 gun yanlis olabilir; pencere genis tutulur.
        dates = self._collect_dates(
            (m.match_start_iso for m in tennis_markets),
        )
        events_by_league = self._fetch_dates(leagues, dates)

        # 4) Her tennis market icin eslesme dene, match_start_iso override et.
        # SPEC-Z14: ESPN otoriter (docstring §). Eslesme bulundu → commence_time
        # her durumda override edilir; slug-surname iki taraf eslesmesi yeterince
        # spesifik (false-positive riski dusuk). Eski same_day guard kaldirildi —
        # Polymarket'in yanlis gun gostermesi durumunda ESPN'in dogru tarihinin
        # iptal edilmesini engelliyordu (Wendelken-Lajal 06-03 vs 06-04 vakasi).
        out: list[MarketData] = []
        for m in markets:
            if not _is_tennis(m):
                out.append(m)
                continue
            target_leagues = self._leagues_for_slug(m.slug, leagues)
            event = self._find_matching_event_by_slug(
                m.slug, target_leagues, events_by_league,
            )
            if event is not None and event.commence_time:
                out.append(m.model_copy(update={"match_start_iso": event.commence_time}))
            else:
                # Eslesme yok → Polymarket startTime fallback.
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

        dates = self._collect_dates(
            (p.match_start_iso for p in tennis_positions),
        )
        events_by_league = self._fetch_dates(leagues, dates)

        # SPEC-Z14: ESPN otoriter — same_day guard kaldirildi. Slug-surname
        # eslesmesi bulundu → commence_time override (Polymarket'in yanlis
        # gun gostermesi durumunda dogru tarihe duzelir).
        for p in tennis_positions:
            target_leagues = self._leagues_for_slug(p.slug, leagues)
            event = self._find_matching_event_by_slug(
                p.slug, target_leagues, events_by_league,
            )
            if event is None or not event.commence_time:
                continue
            p.match_start_iso = event.commence_time

    def _collect_dates(self, market_isos: Iterable[str]) -> tuple[str, ...]:
        """ESPN fetch icin tarih kumesi: bugun + lookahead penceresi + market gunleri.

        Polymarket gameStartTime ±1 gun yanlis olabiliyor (slug-tarihi/event
        fallback). Pencere bugun..bugun+N gun arasi tum tarihleri kapsar; ek
        olarak market'lerin kendi Polymarket gunu de eklenir (pencere disinda
        kalmis gec maclari yakalamak icin)."""
        today = datetime.now(timezone.utc)
        dates: set[str] = set()
        for offset in range(0, self._lookahead_days + 1):
            d = (today + timedelta(days=offset)).strftime("%Y%m%d")
            dates.add(d)
        for iso in market_isos:
            d = _iso_to_yyyymmdd(iso)
            if d:
                dates.add(d)
        return tuple(sorted(dates))

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
