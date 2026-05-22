# Tennis ESPN Real-Match Fetch — Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mevcut `TennisStartEnricher` ESPN'den 0 maç çekiyor (önceki plan'ın canlı doğrulamasında saptandı). ESPN tennis API'sinin gerçek yapısına göre yeniden yazmak: 3-aşamalı fetch (turnuva listesi → turnuva maçları → oyuncu adları) + athlete cache.

**Architecture:** ESPN client'a yeni public metod `fetch_tennis_matches_today(league, date)` eklenir; in-memory ID-keyed athlete cache (24h TTL) infra katmanında tutulur. TennisStartEnricher mevcut `fetch_scoreboard` çağrısını bu yeni metoda yönlendirir, doubles slug desteği eklenir. Public iz: ESPNClient public API +1 metod, ESPNMatchScore aynı kalır.

**Tech Stack:** Python 3.12, httpx, pytest, mevcut ESPN client (`src/infrastructure/apis/espn_client.py`).

---

## Mimari Doğrulama (ARCH_GUARD ✓)

8 anti-pattern tarandı:
- ✓ DRY — ESPN client mevcut, yeni metod aynı modülde
- ✓ <400 satır — espn_client.py şu an ~200 satır, +~120 satır eklenir → ~320 (limit altında). Limit aşılırsa böl.
- ✓ Domain I/O yok — tüm HTTP iş infra'da
- ✓ Katman düzeni — Orchestration (enricher) → Infrastructure (client). Aynı
- ✓ Magic number yok — TTL config'den (`tennis_start_cache_ttl_sec` + yeni `tennis_athlete_cache_ttl_sec`)
- ✓ utils/helpers/misc yok
- ✓ Sessiz hata yok — fail → log warning + boş liste
- ✓ P(YES) anchor — dokunulmuyor

---

## ESPN tennis API'sinin gerçek yapısı (keşfedildi 2026-05-23)

```
1. Aktif turnuvalar:
   GET https://site.api.espn.com/apis/site/v2/sports/tennis/{league}/scoreboard?dates=YYYYMMDD
   → events: [{id: "172-2026", name: "Roland Garros", date: "...", endDate: "..."}, ...]

2. Turnuvanın bugünkü maçları:
   GET https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/events/{tid}/competitions?dates=YYYYMMDD&limit=50
   → items: [{$ref: "...competitions/178427", date: "2026-05-23T08:05Z", competitors: [...]}]

3. Competition detayı (item'ın $ref'inden dereference):
   GET (item.$ref)
   → competitors: [{athlete: {$ref: ".../athletes/3897"}, homeAway: null}, ...]

4. Athlete adı (her competitor.athlete.$ref'ten dereference):
   GET (athlete.$ref)
   → displayName: "Jesper de Jong", fullName: "..."
```

**Performans tahmini:** Aktif turnuvalar (~3) × bugünkü maçlar (~7/turnuva) = ~21 maç × 2 athlete = ~42 athlete call. Her athlete sonradan tekrar gelirse cache hit. League başına ~46 HTTP call ilk fetch, sonraki 5 dakika boyunca 0 call (TennisStartEnricher seviyesinde cache). Athlete cache 24h TTL — gün boyu aynı oyuncular tekrar tekrar sorgulanmaz.

---

## Task 1: ESPN client'a tennis-özel public metod ekle (TDD)

**Files:**
- Modify: `src/infrastructure/apis/espn_client.py`
- Modify: `tests/unit/infrastructure/apis/test_espn_client.py` (varsa) veya Create
- Modify: `src/config/settings.py` — yeni alan
- Modify: `config.yaml` — yeni satır

### Step 1 — Config alanı

[settings.py](src/config/settings.py) `ScoreConfig` veya yeni `ESPNTennisConfig` yerine en basit: scanner config altında. Aslında tek başına olmalı.

`ScannerConfig`'e ekle (Task 6'da eklediğimiz `tennis_start_cache_ttl_sec` ile yan yana):

```python
tennis_athlete_cache_ttl_sec: int = 86400  # 24 saat
```

[config.yaml](config.yaml) scanner bloğuna ekle:

```yaml
  tennis_athlete_cache_ttl_sec: 86400
```

### Step 2 — TDD: failing tests

Mevcut `tests/unit/infrastructure/apis/test_espn_client.py` varsa oraya, yoksa yeni dosya.

Yeni test'ler:

```python
# tests/unit/infrastructure/apis/test_espn_client_tennis.py
"""ESPNClient.fetch_tennis_matches_today: 3-aşamalı tennis fetch + athlete cache."""
from __future__ import annotations
from unittest.mock import MagicMock
import json

from src.infrastructure.apis.espn_client import ESPNClient


def _resp(payload: dict, status: int = 200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = payload
    return m


def _scoreboard_payload(events):
    return {"events": events}


def _competitions_payload(items):
    return {"count": len(items), "items": items}


def _competition_detail(comp_id: str, date_iso: str, p1_ref: str, p2_ref: str):
    return {
        "id": comp_id, "date": date_iso,
        "competitors": [
            {"athlete": {"$ref": p1_ref}, "homeAway": None},
            {"athlete": {"$ref": p2_ref}, "homeAway": None},
        ],
        "status": {"type": {"description": "Scheduled", "completed": False, "state": "pre"}},
    }


def _athlete_payload(name: str):
    return {"displayName": name, "fullName": name, "id": name.replace(" ", "")}


def test_fetch_tennis_matches_today_returns_match_list_for_active_tournament():
    """Tek turnuva, tek maç senaryosu — full happy path."""
    http_get = MagicMock(side_effect=[
        # 1. scoreboard
        _resp(_scoreboard_payload([
            {"id": "172-2026", "name": "Roland Garros", "endDate": "2026-06-08T03:59Z"}
        ])),
        # 2. competitions list
        _resp(_competitions_payload([
            {"$ref": "https://x/competitions/178427"}
        ])),
        # 3. competition detail
        _resp(_competition_detail(
            "178427", "2026-05-23T08:05Z",
            "https://x/athletes/3897", "https://x/athletes/2567",
        )),
        # 4-5. athletes
        _resp(_athlete_payload("Jesper de Jong")),
        _resp(_athlete_payload("Sun Fajing")),
    ])
    client = ESPNClient(http_get=http_get)
    out = client.fetch_tennis_matches_today("atp", "20260523")
    assert len(out) == 1
    m = out[0]
    assert m.event_id == "178427"
    assert m.home_name == "Jesper de Jong"
    assert m.away_name == "Sun Fajing"
    assert m.commence_time == "2026-05-23T08:05Z"


def test_fetch_tennis_matches_today_caches_athlete_lookups():
    """Aynı athlete birden fazla competition'da geçerse tek HTTP call."""
    http_get = MagicMock(side_effect=[
        _resp(_scoreboard_payload([{"id": "T1", "endDate": "2026-06-01T00:00Z"}])),
        _resp(_competitions_payload([
            {"$ref": "https://x/comp/1"},
            {"$ref": "https://x/comp/2"},
        ])),
        _resp(_competition_detail("1", "2026-05-23T10:00Z",
                                   "https://x/athletes/A", "https://x/athletes/B")),
        _resp(_competition_detail("2", "2026-05-23T12:00Z",
                                   "https://x/athletes/A", "https://x/athletes/C")),
        _resp(_athlete_payload("Player A")),
        _resp(_athlete_payload("Player B")),
        _resp(_athlete_payload("Player C")),
    ])
    client = ESPNClient(http_get=http_get)
    out = client.fetch_tennis_matches_today("atp", "20260523")
    assert len(out) == 2
    # 5 unique URLs fetched (2 athlete lookups for A, B, C — A is cached on 2nd use):
    # 1 scoreboard + 1 competitions + 2 competition detail + 3 athletes (A,B,C) = 7
    assert http_get.call_count == 7


def test_fetch_tennis_matches_today_no_active_tournaments_returns_empty():
    http_get = MagicMock(return_value=_resp(_scoreboard_payload([])))
    client = ESPNClient(http_get=http_get)
    assert client.fetch_tennis_matches_today("atp", "20260523") == []
    assert http_get.call_count == 1


def test_fetch_tennis_matches_today_athlete_lookup_failure_skips_match():
    """Athlete fetch fail → ilgili maç atlanır, log warning, diğer maçlar etkilenmez."""
    http_get = MagicMock(side_effect=[
        _resp(_scoreboard_payload([{"id": "T1", "endDate": "2026-06-01T00:00Z"}])),
        _resp(_competitions_payload([{"$ref": "https://x/comp/1"}])),
        _resp(_competition_detail("1", "2026-05-23T10:00Z",
                                   "https://x/athletes/A", "https://x/athletes/B")),
        _resp({}, status=500),  # athlete A fail
        _resp(_athlete_payload("Player B")),
    ])
    client = ESPNClient(http_get=http_get)
    out = client.fetch_tennis_matches_today("atp", "20260523")
    assert out == []  # match dropped, no partial data


def test_fetch_tennis_matches_today_scoreboard_fail_returns_empty():
    http_get = MagicMock(return_value=_resp({}, status=500))
    client = ESPNClient(http_get=http_get)
    assert client.fetch_tennis_matches_today("atp", "20260523") == []


def test_fetch_tennis_matches_today_ended_tournaments_filtered():
    """endDate geçmiş turnuvalar atlanır."""
    http_get = MagicMock(return_value=_resp(_scoreboard_payload([
        {"id": "OLD", "endDate": "2026-05-20T00:00Z"},  # geçmiş
        # NOT: implementer için ipucu — "endDate" yoksa veya parse edemezse turnuvayı bırak
    ])))
    client = ESPNClient(http_get=http_get)
    out = client.fetch_tennis_matches_today("atp", "20260523")
    # endDate < today → bu turnuva atlanır, başka turnuva yok → []
    # Tek call (scoreboard); competitions çağrılmaz.
    assert out == []
    assert http_get.call_count == 1
```

Run:
```bash
pytest tests/unit/infrastructure/apis/test_espn_client_tennis.py -v
```
Expected: tüm 6 test FAIL (`fetch_tennis_matches_today` yok).

### Step 3 — Implement `fetch_tennis_matches_today`

[espn_client.py](src/infrastructure/apis/espn_client.py) içine ekle:

```python
# Modül üstü, mevcut sabitler yanı
_ESPN_CORE_URL = "https://sports.core.api.espn.com/v2/sports"
_TENNIS_COMPETITIONS_LIMIT = 50


class ESPNClient:
    def __init__(
        self,
        http_get: Callable[..., Any] | None = None,
        timeout: int = _DEFAULT_HTTP_TIMEOUT,
        athlete_cache_ttl_sec: int = 86400,
    ) -> None:
        self._http_get = http_get or httpx.get
        self._timeout = timeout
        self._athlete_ttl = athlete_cache_ttl_sec
        self._athlete_cache: dict[str, tuple[float, str]] = {}  # athlete_url → (ts, name)

    def fetch_tennis_matches_today(
        self,
        league: str,
        date_yyyymmdd: str,
    ) -> list[ESPNMatchScore]:
        """Tennis için 3-aşamalı bugünkü maç fetch.

        Akış:
          1. scoreboard?dates=DATE → aktif (henüz bitmemiş) turnuva ID'leri
          2. Her turnuva için competitions?dates=DATE → bugünkü maç competition'ları
          3. Her competition detail + athlete dereference → maç + oyuncu adları

        Athlete fetch'leri _athlete_cache içinde TTL ile saklanır (24h default).
        Herhangi bir HTTP fail → ilgili maç atlanır, log warning. Tüm sonuç boşsa [].
        """
        tournaments = self._fetch_tennis_active_tournaments(league, date_yyyymmdd)
        if not tournaments:
            return []
        matches: list[ESPNMatchScore] = []
        for tid in tournaments:
            comps = self._fetch_tennis_competitions(league, tid, date_yyyymmdd)
            for comp_ref in comps:
                score = self._build_tennis_match(comp_ref)
                if score is not None:
                    matches.append(score)
        return matches

    def _fetch_tennis_active_tournaments(self, league: str, date: str) -> list[str]:
        url = f"{_ESPN_BASE_URL}/tennis/{league}/scoreboard"
        try:
            resp = self._http_get(url, params={"dates": date}, timeout=self._timeout)
            if resp.status_code >= 400:
                logger.warning("ESPN tennis/%s scoreboard returned %d", league, resp.status_code)
                return []
            data = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN tennis/%s scoreboard fetch failed: %s", league, e)
            return []
        events = data.get("events") or []
        active: list[str] = []
        for ev in events:
            tid = str(ev.get("id", ""))
            end = ev.get("endDate") or ev.get("date") or ""
            if not tid or not end:
                continue
            # date_yyyymmdd vs end (ISO): basit string karşılaştırma. ISO "2026-05-23T..." > "2026-05-20T..."
            iso_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            if end[:10] < iso_date:
                continue
            active.append(tid)
        return active

    def _fetch_tennis_competitions(self, league: str, tid: str, date: str) -> list[str]:
        url = f"{_ESPN_CORE_URL}/tennis/leagues/{league}/events/{tid}/competitions"
        try:
            resp = self._http_get(
                url,
                params={"dates": date, "limit": _TENNIS_COMPETITIONS_LIMIT},
                timeout=self._timeout,
            )
            if resp.status_code >= 400:
                logger.warning("ESPN tennis/%s/%s competitions returned %d",
                               league, tid, resp.status_code)
                return []
            data = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN tennis/%s/%s competitions fetch failed: %s", league, tid, e)
            return []
        refs: list[str] = []
        for it in data.get("items") or []:
            ref = it.get("$ref")
            if ref:
                refs.append(str(ref))
        return refs

    def _build_tennis_match(self, comp_ref: str) -> ESPNMatchScore | None:
        try:
            resp = self._http_get(comp_ref, timeout=self._timeout)
            if resp.status_code >= 400:
                logger.warning("ESPN tennis competition %s returned %d",
                               comp_ref, resp.status_code)
                return None
            comp = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN tennis competition fetch failed (%s): %s", comp_ref, e)
            return None
        competitors = comp.get("competitors") or []
        if len(competitors) < 2:
            return None
        athlete_refs = []
        for c in competitors[:2]:
            ref = ((c.get("athlete") or {}).get("$ref") or "").strip()
            if not ref:
                return None
            athlete_refs.append(ref)
        names = [self._resolve_athlete_name(r) for r in athlete_refs]
        if not all(names):
            return None
        return ESPNMatchScore(
            event_id=str(comp.get("id", "")),
            home_name=str(names[0]),
            away_name=str(names[1]),
            commence_time=str(comp.get("date", "")),
        )

    def _resolve_athlete_name(self, athlete_ref: str) -> str:
        now = time.time()
        cached = self._athlete_cache.get(athlete_ref)
        if cached is not None and (now - cached[0]) < self._athlete_ttl:
            return cached[1]
        try:
            resp = self._http_get(athlete_ref, timeout=self._timeout)
            if resp.status_code >= 400:
                logger.warning("ESPN athlete %s returned %d",
                               athlete_ref, resp.status_code)
                return ""
            data = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN athlete fetch failed (%s): %s", athlete_ref, e)
            return ""
        name = str(data.get("displayName") or data.get("fullName") or "")
        if name:
            self._athlete_cache[athlete_ref] = (now, name)
        return name
```

Import güncellemesi:
```python
import time  # mevcut import'lara ekle
```

### Step 4 — Run tests until green

```bash
pytest tests/unit/infrastructure/apis/test_espn_client_tennis.py -v
```
Expected: 6/6 pass.

Tüm suite:
```bash
pytest -q
```
Expected: yeşil.

### Step 5 — Commit

```bash
git add src/infrastructure/apis/espn_client.py src/config/settings.py config.yaml tests/unit/infrastructure/apis/test_espn_client_tennis.py
git commit -m "feat(espn): fetch_tennis_matches_today (3-aşamalı + athlete cache)"
```

---

## Task 2: TennisStartEnricher'i yeni metoda yönlendir + doubles desteği

**Files:**
- Modify: `src/orchestration/tennis_start_enricher.py`
- Modify: `tests/unit/orchestration/test_tennis_start_enricher.py`

### Step 1 — Doubles slug parser

Mevcut `_slug_surnames` slug formatları:
- `atp-minaur-paul-2026-05-22` → ("minaur", "paul") ✓
- `wta-mboko-cristia-2026-05-22` → ("mboko", "cristia") ✓
- `atp-doubles-fortrom-gadatu-2026-05-22` → ŞU AN ("doubles", "fortrom") — YANLIŞ
- `atp-doubles-ariza-bourgue-fortrom-gadatu-2026-05-22` → 2v2 doubles, 4 oyuncu

Yeni davranış: slug'da `doubles` token görünüyorsa, sonraki 2 token'ı al (singles için: parts[1], parts[2]; doubles için: parts[2], parts[3]).

Test ekle (`test_tennis_start_enricher.py` içine):

```python
def test_enrich_doubles_slug_parses_surnames_correctly():
    """atp-doubles-{p1}-{p2}-date slug formatı için ilk 2 soyad doubles kelimesinden sonra."""
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = [
        # ESPN doubles event'lerinde competitor.displayName "Fortrom/Gadatu" gibi olabilir;
        # şimdilik sadece parser doğruluğunu test ediyoruz — match'leme ESPN data
        # formatına bağlı, ayrı senaryo. Bu testte slug parse'ın doğru olduğunu
        # kanıtlamak için sahte ESPN event home/away'inde tam isimleri kullan.
        ESPNMatchScore(
            event_id="d1",
            home_name="Fortrom Player",
            away_name="Gadatu Player",
            commence_time="2026-05-23T15:00:00Z",
        ),
    ]
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    out = enricher.enrich([_mkt("atp-doubles-fortrom-gadatu-2026-05-23",
                                  sport_tag="tennis", start="2026-05-23T14:00:00Z")])
    assert out[0].match_start_iso == "2026-05-23T15:00:00Z"


def test_slug_surnames_skips_doubles_token():
    """Direkt parser unit testi."""
    from src.orchestration.tennis_start_enricher import _slug_surnames
    assert _slug_surnames("atp-minaur-paul-2026-05-22") == ("minaur", "paul")
    assert _slug_surnames("atp-doubles-fortrom-gadatu-2026-05-22") == ("fortrom", "gadatu")
    assert _slug_surnames("wta-doubles-smith-jones-2026-05-22") == ("smith", "jones")
    assert _slug_surnames("xyz-foo-bar-2026") is None  # atp/wta degil
```

### Step 2 — Mevcut 7 testi yeni ESPN metoduna güncelle

Mevcut testler `espn_client.fetch_scoreboard` mock'luyor. Yeni testler `espn_client.fetch_tennis_matches_today` mock'lamalı. Aynı 7 senaryo:

```python
def test_enrich_overrides_match_start_when_espn_match_found():
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = [
        _espn("Alex de Minaur", "Tommy Paul", "2026-05-22T16:00:00Z"),
    ]
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    markets = [_mkt("atp-minaur-paul-2026-05-22", start="2026-05-22T15:30:00Z")]
    out = enricher.enrich(markets)
    assert out[0].match_start_iso == "2026-05-22T16:00:00Z"


def test_enrich_caches_espn_response_within_ttl():
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = []
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    enricher.enrich([_mkt("atp-x-y-2026-05-22")])
    enricher.enrich([_mkt("atp-a-b-2026-05-22")])
    # ATP + WTA = 2 league, 1 fetch each (cached) = 2 call. Without cache it'd be 4.
    assert espn_client.fetch_tennis_matches_today.call_count == 2


def test_enrich_atp_slug_matches_atp_only_event():
    espn_client = MagicMock()
    def fetch(league, date):
        if league == "atp":
            return [_espn("Alex de Minaur", "Tommy Paul", "2026-05-22T16:00:00Z")]
        return []
    espn_client.fetch_tennis_matches_today.side_effect = fetch
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    out = enricher.enrich([_mkt("atp-minaur-paul-2026-05-22", start="")])
    assert out[0].match_start_iso == "2026-05-22T16:00:00Z"
```

Diğer 4 test (espn_fail, non_tennis, no_tennis, no_match) — mock metodunu `fetch_scoreboard` yerine `fetch_tennis_matches_today` yap, yapı aynı kalır.

`_espn` helper:
```python
def _espn(home: str, away: str, date_iso: str) -> ESPNMatchScore:
    return ESPNMatchScore(
        event_id=f"{home}-{away}", home_name=home, away_name=away,
        commence_time=date_iso,
    )
```

### Step 3 — Run tests — fail (mock mismatch)

```bash
pytest tests/unit/orchestration/test_tennis_start_enricher.py -v
```
Expected: çoğu FAIL.

### Step 4 — Refactor enricher

[tennis_start_enricher.py](src/orchestration/tennis_start_enricher.py) içinde:

(a) `_slug_surnames` güncelle:

```python
def _slug_surnames(slug: str) -> tuple[str, str] | None:
    """'atp-minaur-paul-2026-05-22' → ('minaur', 'paul').
    'atp-doubles-fortrom-gadatu-2026-05-22' → ('fortrom', 'gadatu') — 'doubles' atlanır.
    4+ parça yoksa None. parts[0] atp/wta degilse None.
    """
    if not slug:
        return None
    parts = slug.lower().split("-")
    if len(parts) < 4 or parts[0] not in ("atp", "wta"):
        return None
    offset = 2 if parts[1] == "doubles" else 1
    if len(parts) < offset + 2:
        return None
    return parts[offset], parts[offset + 1]
```

(b) `_fetch_leagues` metodunu sil, yerine yeni cache yapısı:

```python
class TennisStartEnricher:
    def __init__(self, espn_client: ESPNClient, cache_ttl_sec: int) -> None:
        self._espn = espn_client
        self._ttl = cache_ttl_sec
        self._cache: dict[str, tuple[float, list[ESPNMatchScore]]] = {}

    def enrich(self, markets: list[MarketData]) -> list[MarketData]:
        tennis_markets = [m for m in markets if _is_tennis(m)]
        if not tennis_markets:
            return markets
        leagues = get_sport_rule("tennis", "espn_leagues", default=("atp", "wta"))
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        events_by_league = self._fetch_today(leagues, date_str)
        out: list[MarketData] = []
        for m in markets:
            if not _is_tennis(m):
                out.append(m)
                continue
            target_league = _league_for_slug(m.slug)
            candidates: list[ESPNMatchScore] = []
            for lg, evs in events_by_league.items():
                if target_league is None or lg == target_league:
                    candidates.extend(evs)
            match = _match_event(m.slug, candidates)
            if match is None or not match.commence_time:
                out.append(m)
                continue
            out.append(m.model_copy(update={"match_start_iso": match.commence_time}))
        return out

    def _fetch_today(self, leagues: Iterable[str], date_str: str) -> dict[str, list[ESPNMatchScore]]:
        now = time.time()
        result: dict[str, list[ESPNMatchScore]] = {}
        for lg in leagues:
            cached = self._cache.get(lg)
            if cached is not None and (now - cached[0]) < self._ttl:
                result[lg] = cached[1]
                continue
            try:
                evs = self._espn.fetch_tennis_matches_today(lg, date_str)
            except Exception as e:  # noqa: BLE001
                logger.warning("ESPN tennis/%s fetch failed: %s — Polymarket start kalır", lg, e)
                result[lg] = []
                continue
            self._cache[lg] = (now, evs)
            result[lg] = evs
        return result
```

`datetime` import zaten var (önceki kodda), yoksa ekle.

### Step 5 — Tests pass

```bash
pytest tests/unit/orchestration/test_tennis_start_enricher.py -v
```
Expected: 9/9 (7 mevcut + 2 yeni doubles) pass.

Full suite:
```bash
pytest -q
```
Expected: yeşil.

### Step 6 — Commit

```bash
git add src/orchestration/tennis_start_enricher.py tests/unit/orchestration/test_tennis_start_enricher.py
git commit -m "feat(tennis): enricher fetch_tennis_matches_today'a yönlendi + doubles slug desteği"
```

---

## Task 3: Factory athlete cache TTL wire-up

**Files:**
- Modify: `src/orchestration/factory.py`

### Step 1 — Factory'de ESPNClient TTL geçir

[factory.py](src/orchestration/factory.py) — mevcut `espn = ESPNClient()` satırı (line ~83) `cfg.scanner.tennis_athlete_cache_ttl_sec`'i alacak şekilde değiştir:

```python
espn = ESPNClient(athlete_cache_ttl_sec=cfg.scanner.tennis_athlete_cache_ttl_sec)
```

### Step 2 — Run full suite

```bash
pytest -q
```
Expected: yeşil. ScoreEnricher'ın ESPN client'ı paylaştığını da doğrula (test_factory.py varsa).

### Step 3 — Commit

```bash
git add src/orchestration/factory.py
git commit -m "feat(factory): ESPN athlete cache TTL config-driven"
```

---

## Task 4: Live verification + DECISIONS log

**Files:**
- Create: `scripts/verify_tennis_enricher.py` (tek seferlik diagnostic, commit edilir)
- Modify: `DECISIONS.md`

### Step 1 — Live verification script

Create `scripts/verify_tennis_enricher.py`:

```python
"""Tennis enricher canlı doğrulama — Polymarket tennis market'leri için ESPN
match-start override gerçekten çalışıyor mu, manuel olarak gör.

Çağrı: python scripts/verify_tennis_enricher.py
"""
from __future__ import annotations

import json
from pathlib import Path

from src.infrastructure.apis.espn_client import ESPNClient
from src.models.market import MarketData
from src.orchestration.tennis_start_enricher import TennisStartEnricher


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    stock_path = project_root / "data" / "stock_queue.json"
    with stock_path.open(encoding="utf-8") as f:
        rows = json.load(f)
    tennis_markets: list[MarketData] = []
    for r in rows:
        m = r.get("market") or {}
        if "tennis" not in (m.get("sport_tag") or "").lower():
            continue
        try:
            tennis_markets.append(MarketData(**m))
        except Exception as e:
            print(f"[skip] {m.get('slug','?')}: {e}")

    if not tennis_markets:
        print("Stock queue'da tennis market yok — script bitti.")
        return

    print(f"{len(tennis_markets)} tennis market bulundu:\n")
    for m in tennis_markets:
        print(f"  POLY  {m.slug!r:60} start={m.match_start_iso}")

    print("\nESPN sorgu yapılıyor...\n")
    enricher = TennisStartEnricher(espn_client=ESPNClient(), cache_ttl_sec=300)
    out = enricher.enrich(tennis_markets)

    print("\nSonuç:\n")
    for orig, new in zip(tennis_markets, out):
        flag = "ESPN override" if orig.match_start_iso != new.match_start_iso else "Polymarket kaldı"
        print(f"  {new.slug!r:60}")
        print(f"    poly  = {orig.match_start_iso}")
        print(f"    final = {new.match_start_iso}   [{flag}]")


if __name__ == "__main__":
    main()
```

### Step 2 — Run

```bash
python scripts/verify_tennis_enricher.py
```
Expected: Hiç değilse 1 tennis market'in ESPN'den override edildiğini gör. (ATP/WTA single market varsa.) ITF/doubles için "Polymarket kaldı" beklenir (ITF ESPN'de yok).

### Step 3 — DECISIONS.md log

[DECISIONS.md](DECISIONS.md) §B en üste yeni entry ekle (2026-05-22 entry'lerinin üstüne):

```markdown
### 2026-05-23 — Tennis ESPN gerçek-fetch düzeltmesi

**Karar:** ESPN tennis için 3-aşamalı public metod `fetch_tennis_matches_today` eklendi (scoreboard → competitions → athlete dereference). Athlete dereference 24h in-memory cache'lenir.

**Neden:** Önceki entegrasyon (2026-05-22) `fetch_scoreboard` çağrısı yapıyordu; ESPN tennis scoreboard'u turnuvaları döndürür, tek tek maçları değil. Canlı doğrulamada 0 maç çıktı — enricher fiilen no-op'tu. Doğru endpoint: `sports.core.api.espn.com/.../competitions`.

**Etki:**
- `src/infrastructure/apis/espn_client.py` — yeni public metod + athlete cache
- `src/orchestration/tennis_start_enricher.py` — yeni metoda yönlendi + doubles slug desteği
- `src/orchestration/factory.py` — athlete cache TTL config-driven
- `config.yaml`, `src/config/settings.py` — `tennis_athlete_cache_ttl_sec: 86400`
- `scripts/verify_tennis_enricher.py` — canlı doğrulama
- ITF/Challenger ESPN'de yok → Polymarket fallback (mevcut davranış, doğru)
```

### Step 4 — Commit

```bash
git add scripts/verify_tennis_enricher.py DECISIONS.md
git commit -m "docs(DECISIONS): tennis ESPN gerçek-fetch fix + verification script"
```

---

## Sonuç Kontrol Listesi

- [ ] `pytest -q` tüm testler yeşil
- [ ] `python scripts/verify_tennis_enricher.py` çalışıyor — en az 1 tennis market'i ESPN'den override ediliyor (singles varsa)
- [ ] ITF / doubles market'leri için davranış: doubles ESPN'de bulunursa override, yoksa Polymarket fallback (silent)
- [ ] `espn_client.py` < 400 satır
- [ ] `tennis_start_enricher.py` < 400 satır (mevcut 185, doubles+refactor sonrası ~190)
- [ ] DECISIONS.md §B'ye yeni log entry ekledi (en yeni üstte konvansiyonu)
