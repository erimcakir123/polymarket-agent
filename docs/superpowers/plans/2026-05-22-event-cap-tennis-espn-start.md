# Event Cap (2→3) + Tennis ESPN Start Time Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Event başına pozisyon limitini 2'den 3'e çıkar. (2) Tennis market'lerinde maç saatini ESPN tennis scoreboard'dan çek — Polymarket startTime fallback, ikisi de yoksa scanner filtresi market'i eler.

**Architecture:** İki bağımsız faz. Faz 1 saf config + test güncellemesi (kod akışı değişmez). Faz 2 yeni orchestration modülü `TennisStartEnricher` ekler, scanner'a dependency injection ile bağlanır; sport_rules.py'a tennis entry eklenir; ESPN client'ı yeniden kullanılır.

**Tech Stack:** Python 3.12, pydantic, pytest, httpx (mevcut ESPN client).

---

## Mimari Doğrulama (ARCH_GUARD ✓)

8 anti-pattern tarandı:
- ✓ DRY — ESPN client mevcut (`infrastructure/apis/espn_client.py`), yeniden kullanılır
- ✓ <400 satır — `tennis_start_enricher.py` ~120 satır hedeflenir
- ✓ Domain I/O yok — enricher orchestration katmanında, ESPN call'ı infra'ya delege
- ✓ Katman düzeni — Orchestration (enricher) → Infrastructure (ESPN client). Alt yönde.
- ✓ Magic number yok — TTL, league listesi config'den
- ✓ utils/helpers/misc yok — `src/orchestration/` altına
- ✓ Sessiz hata yok — ESPN fail → log warning, Polymarket startTime fallback
- ✓ P(YES) anchor — dokunulmuyor

---

## FAZ 1 — Event Cap 2 → 3

### Task 1: Config defaultlarını ve doküman değerlerini güncelle

**Files:**
- Modify: `config.yaml:72`
- Modify: `src/config/settings.py:64`
- Modify: `src/strategy/entry/gate.py:48`
- Modify: `ARCHITECTURE_GUARD.md:120`
- Modify: `DECISIONS.md:37,802`

- [ ] **Step 1: config.yaml**

[config.yaml:72](config.yaml#L72) — değiştir:

```yaml
max_positions_per_event: 3  # ARCH Kural 8 (gevşedi): aynı event'te max 3 bağımsız market (moneyline + spread + totals)
```

- [ ] **Step 2: settings.py default**

[settings.py:64](src/config/settings.py#L64):

```python
max_positions_per_event: int = 3  # SPEC-J/K: aynı event'te moneyline+spread+totals bağımsız bahisler (Kural 8 gevşedi)
```

- [ ] **Step 3: gate.py default**

[gate.py:48](src/strategy/entry/gate.py#L48):

```python
max_positions_per_event: int = 3  # SPEC-J/K: ARCH Kural 8 gevşedi (max N / event_id)
```

- [ ] **Step 4: ARCHITECTURE_GUARD.md güncelle**

[ARCHITECTURE_GUARD.md:120](ARCHITECTURE_GUARD.md#L120):

```
N = config.risk.max_positions_per_event (default 3 — SPEC-J/K + 2026-05-22 cap artırımı).
```

Ayrıca [ARCHITECTURE_GUARD.md:131](ARCHITECTURE_GUARD.md#L131) örneğindeki "3. bir pozisyon AÇILAMAZ (cap=2)" satırını "4. bir pozisyon AÇILAMAZ (cap=3)" yap.

- [ ] **Step 5: DECISIONS.md güncelle**

[DECISIONS.md:37](DECISIONS.md#L37) ve [DECISIONS.md:802](DECISIONS.md#L802) — "default N=2" → "default N=3".

§B kronolojik log'a yeni entry ekle (2026-05-22):
```
### 2026-05-22 — Event cap 2 → 3
Reason: Aynı event'te moneyline + totals + run_line (MLB submarket) üçü birden çalışabilmeli. SPEC-J/K bağımsız bahis tanımına uyar.
Impact: config.yaml + settings.py + gate.py + tests.
```

- [ ] **Step 6: Commit (sadece source)**

```bash
git add config.yaml src/config/settings.py src/strategy/entry/gate.py ARCHITECTURE_GUARD.md DECISIONS.md
git commit -m "feat(risk): event-cap 2 → 3 (ARCH Kural 8 default güncellendi)"
```

### Task 2: Test güncellemeleri

**Files:** 8 test dosyası — hepsinde `max_positions_per_event=2` → `=3` ve assertion'lar.

- [ ] **Step 1: Hardcoded 2 değerlerini 3 yap**

Aşağıdaki dosyalarda `max_positions_per_event=2` ifadesi `=3` ile değiştirilir:

```
tests/integration/test_mlb_submarket_smoke.py:50
tests/unit/orchestration/test_portfolio_guards.py:100,112,125,138
tests/unit/orchestration/test_entry_processor_signals.py:51
tests/unit/orchestration/test_entry_processor_basketball.py:68
tests/unit/orchestration/test_entry_processor.py:58,138,203
tests/unit/orchestration/test_agent_heavy_stages.py:57,119,140
```

- [ ] **Step 2: test_gate.py senaryo testini güncelle**

[test_gate.py:85](tests/unit/strategy/entry/test_gate.py#L85) — docstring + test body:

eski:
```python
"""SPEC-J/K: max_positions_per_event=2. İlk 2 kabul, 3. blok."""
```

yeni:
```python
"""SPEC-J/K + 2026-05-22: max_positions_per_event=3. İlk 3 kabul, 4. blok."""
```

Test body'sinde 3 pozisyon kabul + 4. blok edilecek şekilde mock'ları çoğalt. Mevcut test 2 mock pozisyon yapıyorsa 3'e çıkar; assertion 3 success + 1 reject.

- [ ] **Step 3: Tüm testleri çalıştır**

Run: `pytest tests/ -q --tb=short`
Expected: ALL PASS.

Eğer fail varsa stack trace'i incele — başka yerlerde de hardcoded `==2` veya `>=2` varsa düzelt.

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test(risk): event-cap=3 ile test'leri uyumla"
```

---

## FAZ 2 — Tennis ESPN Match-Start Resolver

### Tasarım Özeti

**Akış:**
```
Scanner.scan():
  raw = gamma.fetch_events()             # Polymarket
  raw = tennis_start_enricher.enrich(raw)  # YENİ: tennis market.match_start_iso ESPN'den override
  filtered = filter(_passes_filters, raw)
  filtered.sort(...)
  return top N
```

**Enricher davranışı:**
1. raw market listesinde tennis market'leri tespit et (sport_tag prefix "tennis" veya slug prefix "atp-"/"wta-").
2. Tennis market varsa ESPN tennis/atp + tennis/wta scoreboard'larını çek (her ikisi de, basitlik).
3. Her tennis market için ESPN event'lerinde slug-surnames eşleştirmesi yap.
4. Eşleşme bulunduysa market.match_start_iso = ESPN event.date ile override et.
5. Eşleşme yoksa market'e dokunma — Polymarket startTime kalır (fallback).
6. ESPN HTTP fail → log warning, hiçbir override yapma (mevcut davranışla geri uyumlu).

**Cache:** ESPN call'ı pahalı, scan() her cycle çağrılır. Cycle başına bir kez fetch, in-memory TTL cache (default 5 dakika, config'den).

### Task 3: ESPN client'a tennis docstring güncelle (mimari iz)

**Files:**
- Modify: `src/infrastructure/apis/espn_client.py:6-8`

- [ ] **Step 1: Docstring güncelle**

[espn_client.py:6-8](src/infrastructure/apis/espn_client.py#L6-L8) — değiştir:

eski:
```python
Desteklenen sporlar: hokey (NHL), beyzbol (MLB), basketbol (NBA).
Tennis ve soccer scope dışı (SPEC-A5 + SPEC-C ileri faz).
```

yeni:
```python
Desteklenen sporlar: hokey (NHL), beyzbol (MLB), basketbol (NBA),
tenis (ATP/WTA — sadece match_start için, skor entegrasyonu yok).
Soccer scope dışı.
```

- [ ] **Step 2: Commit (Task 4 sonu ile birleşir, şimdi commit yok)**

### Task 4: sport_rules.py'a tennis entry geri ekle (match_start için)

**Files:**
- Modify: `src/config/sport_rules.py:56` (kaldırma yorumu silinir)
- Modify: `src/config/sport_rules.py` — `_ALIASES` tennis girdileri geri ekle

- [ ] **Step 1: Test yaz**

Create: `tests/unit/config/test_sport_rules_tennis.py`

```python
"""Tennis sport_rules girdisinin var olduğunu doğrula."""
from src.config.sport_rules import get_sport_rule


def test_tennis_has_start_source_espn():
    assert get_sport_rule("tennis", "start_source") == "espn"


def test_tennis_espn_leagues():
    leagues = get_sport_rule("tennis", "espn_leagues")
    assert "atp" in leagues
    assert "wta" in leagues


def test_tennis_atp_alias_normalizes():
    # Polymarket sport_tag "tennis_atp" → "tennis" kuralına düşmeli
    assert get_sport_rule("tennis_atp", "start_source") == "espn"
    assert get_sport_rule("tennis_wta", "start_source") == "espn"
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/unit/config/test_sport_rules_tennis.py -v`
Expected: FAIL (`start_source` yok, alias yok)

- [ ] **Step 3: sport_rules.py güncelle**

[sport_rules.py:56](src/config/sport_rules.py#L56) — "Tennis kaldırıldı" yorumunu sil, yerine entry koy:

```python
"tennis": {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 2.0,
    "start_source": "espn",
    "espn_sport": "tennis",
    "espn_leagues": ("atp", "wta"),  # tuple — iki league birden çekilir
},
```

`_ALIASES` dict'ine [sport_rules.py:106](src/config/sport_rules.py#L106) civarı tennis alias'larını geri ekle:

```python
# Tennis (geri açıldı 2026-05-22 — ESPN match_start için)
"tennis_atp": "tennis",
"tennis_wta": "tennis",
"tennis_itf_men": "tennis",
"tennis_itf_women": "tennis",
"tennis": "tennis",
```

- [ ] **Step 4: Run test — pass**

Run: `pytest tests/unit/config/test_sport_rules_tennis.py -v`
Expected: PASS (3 test)

- [ ] **Step 5: Tüm sport_rules test'leri**

Run: `pytest tests/unit/config/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/infrastructure/apis/espn_client.py src/config/sport_rules.py tests/unit/config/test_sport_rules_tennis.py
git commit -m "feat(tennis): sport_rules'a tennis entry geri eklendi (ESPN start_source)"
```

### Task 5: TennisStartEnricher class'ı (TDD)

**Files:**
- Create: `src/orchestration/tennis_start_enricher.py`
- Create: `tests/unit/orchestration/test_tennis_start_enricher.py`

- [ ] **Step 1: Test yaz (TDD)**

Create `tests/unit/orchestration/test_tennis_start_enricher.py`:

```python
"""TennisStartEnricher: tennis market'lerin match_start_iso'sunu ESPN ile override eder."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.models.market import MarketData
from src.orchestration.tennis_start_enricher import TennisStartEnricher


def _mkt(slug: str, sport_tag: str = "tennis", start: str = "") -> MarketData:
    return MarketData(
        condition_id=f"cid-{slug}",
        question="",
        slug=slug,
        yes_token_id="t1",
        no_token_id="t2",
        yes_price=0.5,
        no_price=0.5,
        liquidity=1000.0,
        volume_24h=100.0,
        tags=[],
        end_date_iso="2026-05-30T00:00:00Z",
        match_start_iso=start,
        sport_tag=sport_tag,
    )


def _espn(home: str, away: str, date_iso: str) -> ESPNMatchScore:
    return ESPNMatchScore(
        event_id=f"{home}-{away}",
        home_name=home,
        away_name=away,
        commence_time=date_iso,
    )


def test_enrich_overrides_match_start_when_espn_match_found():
    espn_client = MagicMock()
    espn_client.fetch_scoreboard.return_value = [
        _espn("Alex de Minaur", "Tommy Paul", "2026-05-22T16:00:00Z"),
    ]
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    markets = [_mkt("atp-minaur-paul-2026-05-22", start="2026-05-22T15:30:00Z")]
    out = enricher.enrich(markets)
    assert out[0].match_start_iso == "2026-05-22T16:00:00Z"


def test_enrich_keeps_polymarket_start_when_no_espn_match():
    espn_client = MagicMock()
    espn_client.fetch_scoreboard.return_value = []
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    markets = [_mkt("atp-minaur-paul-2026-05-22", start="2026-05-22T15:30:00Z")]
    out = enricher.enrich(markets)
    assert out[0].match_start_iso == "2026-05-22T15:30:00Z"


def test_enrich_skips_non_tennis_markets():
    espn_client = MagicMock()
    espn_client.fetch_scoreboard.return_value = [_espn("a", "b", "2026-05-22T20:00:00Z")]
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    markets = [_mkt("mlb-yankees-redsox", sport_tag="mlb", start="2026-05-22T19:05:00Z")]
    out = enricher.enrich(markets)
    assert out[0].match_start_iso == "2026-05-22T19:05:00Z"
    espn_client.fetch_scoreboard.assert_not_called()


def test_enrich_no_tennis_markets_skips_espn_call():
    espn_client = MagicMock()
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    enricher.enrich([_mkt("mlb-yankees-redsox", sport_tag="mlb")])
    espn_client.fetch_scoreboard.assert_not_called()


def test_enrich_espn_fail_returns_markets_unchanged():
    espn_client = MagicMock()
    espn_client.fetch_scoreboard.side_effect = Exception("ESPN down")
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    markets = [_mkt("atp-minaur-paul-2026-05-22", start="2026-05-22T15:30:00Z")]
    out = enricher.enrich(markets)
    assert out[0].match_start_iso == "2026-05-22T15:30:00Z"


def test_enrich_caches_espn_response_within_ttl():
    espn_client = MagicMock()
    espn_client.fetch_scoreboard.return_value = []
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    enricher.enrich([_mkt("atp-x-y-2026-05-22")])
    enricher.enrich([_mkt("atp-a-b-2026-05-22")])
    # 2 league × 1 fetch (cached) = 2 call. Without cache it'd be 4.
    assert espn_client.fetch_scoreboard.call_count == 2


def test_enrich_atp_slug_matches_atp_only_event():
    """Slug 'atp-...' ile başlayan market sadece atp league'inden eşleşmeli."""
    espn_client = MagicMock()
    def fetch(sport, league, date=None):
        if league == "atp":
            return [_espn("Alex de Minaur", "Tommy Paul", "2026-05-22T16:00:00Z")]
        return []
    espn_client.fetch_scoreboard.side_effect = fetch
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    out = enricher.enrich([_mkt("atp-minaur-paul-2026-05-22", start="")])
    assert out[0].match_start_iso == "2026-05-22T16:00:00Z"
```

- [ ] **Step 2: Run tests — fail**

Run: `pytest tests/unit/orchestration/test_tennis_start_enricher.py -v`
Expected: FAIL (`tennis_start_enricher` module not found)

- [ ] **Step 3: Enricher implement**

Create `src/orchestration/tennis_start_enricher.py`:

```python
"""Tennis market'lerin match_start_iso'sunu ESPN ile override eder.

Polymarket tennis startTime'ı bazen geç güncellenir veya boş olur (turnuva-level
event). ESPN ATP/WTA scoreboard otoritedir. Cycle başına TTL-cached fetch.

Akış (enrich):
  1. raw market'lerde tennis var mı? Yoksa NO-OP, ESPN'e dokunma.
  2. ESPN tennis/atp + tennis/wta scoreboard fetch (cached).
  3. Her tennis market için slug-surnames eşleştirmesi.
  4. Eşleşme bulundu → market.match_start_iso = ESPN event.commence_time.
  5. Eşleşme yok → market'e dokunma (Polymarket startTime fallback).
  6. ESPN fail → log warning, override yapma.
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


def _is_tennis(m: MarketData) -> bool:
    tag = (m.sport_tag or "").lower()
    if tag.startswith("tennis"):
        return True
    slug = (m.slug or "").lower()
    return slug.startswith("atp-") or slug.startswith("wta-")


def _league_for_slug(slug: str) -> str | None:
    """Slug 'atp-...' → 'atp', 'wta-...' → 'wta'. Else None (her ikisi denenir)."""
    s = (slug or "").lower()
    if s.startswith("atp-"):
        return "atp"
    if s.startswith("wta-"):
        return "wta"
    return None


def _slug_surnames(slug: str) -> tuple[str, str] | None:
    """'atp-minaur-paul-2026-05-22' → ('minaur', 'paul'). 4 parça olmazsa None."""
    if not slug:
        return None
    parts = slug.lower().split("-")
    if len(parts) < 4:
        return None
    if parts[0] not in ("atp", "wta"):
        return None
    return parts[1], parts[2]


def _norm(name: str) -> str:
    """Lowercase + accent strip. Tennis player isim normalizasyonu."""
    if not name:
        return ""
    name = name.replace("ı", "i")
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.lower()


def _match_event(market_slug: str, events: list[ESPNMatchScore]) -> ESPNMatchScore | None:
    surnames = _slug_surnames(market_slug)
    if surnames is None:
        return None
    p1, p2 = surnames
    for ev in events:
        home = _norm(ev.home_name)
        away = _norm(ev.away_name)
        hit1 = p1 in home or p1 in away
        hit2 = p2 in home or p2 in away
        if hit1 and hit2:
            return ev
    return None


class TennisStartEnricher:
    """Cycle başına ESPN tennis scoreboard → tennis market match_start override.

    Constructor dep: ESPNClient, cache_ttl_sec (config'den).
    """

    def __init__(self, espn_client: ESPNClient, cache_ttl_sec: int) -> None:
        self._espn = espn_client
        self._ttl = cache_ttl_sec
        self._cache: dict[str, tuple[float, list[ESPNMatchScore]]] = {}

    def enrich(self, markets: list[MarketData]) -> list[MarketData]:
        tennis_markets = [m for m in markets if _is_tennis(m)]
        if not tennis_markets:
            return markets

        leagues = get_sport_rule("tennis", "espn_leagues", default=("atp", "wta"))
        events_by_league = self._fetch_leagues(leagues)

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

    def _fetch_leagues(self, leagues: Iterable[str]) -> dict[str, list[ESPNMatchScore]]:
        now = time.time()
        result: dict[str, list[ESPNMatchScore]] = {}
        for lg in leagues:
            cached = self._cache.get(lg)
            if cached is not None and (now - cached[0]) < self._ttl:
                result[lg] = cached[1]
                continue
            try:
                evs = self._espn.fetch_scoreboard("tennis", lg)
            except Exception as e:
                logger.warning("ESPN tennis/%s fetch failed: %s — Polymarket start kalır", lg, e)
                result[lg] = []
                continue
            self._cache[lg] = (now, evs)
            result[lg] = evs
        return result
```

- [ ] **Step 4: Run tests — pass**

Run: `pytest tests/unit/orchestration/test_tennis_start_enricher.py -v`
Expected: ALL PASS (7 test)

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/tennis_start_enricher.py tests/unit/orchestration/test_tennis_start_enricher.py
git commit -m "feat(tennis): TennisStartEnricher — ESPN match_start override (TDD)"
```

### Task 6: Scanner'a enricher inject + akışa ekle

**Files:**
- Modify: `src/orchestration/scanner.py`
- Modify: `src/orchestration/factory.py`
- Modify: `src/config/settings.py` — yeni config: `scanner.tennis_start_cache_ttl_sec`
- Modify: `config.yaml` — yeni satır
- Modify: `tests/unit/orchestration/test_scanner.py` — opsiyonel enricher arg

- [ ] **Step 1: Config alanı ekle**

[settings.py:36-48](src/config/settings.py#L36-L48) ScannerConfig'e ekle:

```python
tennis_start_cache_ttl_sec: int = 300
```

[config.yaml:14-18](config.yaml#L14-L18) scanner bloğuna ekle:

```yaml
  tennis_start_cache_ttl_sec: 300
```

- [ ] **Step 2: Scanner test — failing**

Add to `tests/unit/orchestration/test_scanner.py`:

```python
def test_scanner_calls_tennis_enricher_when_provided():
    from unittest.mock import MagicMock
    enricher = MagicMock()
    enricher.enrich.side_effect = lambda ms: ms  # passthrough
    sc = MarketScanner(
        _config(),
        gamma_client=_mock_gamma([]),
        tennis_start_enricher=enricher,
    )
    sc.scan()
    assert enricher.enrich.call_count == 1


def test_scanner_uses_enricher_overridden_start_for_filter():
    """Polymarket match_start 40h ileride, ESPN ile 20h'ye düşerse filter geçer."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import MagicMock
    future_40h = (datetime.now(timezone.utc) + timedelta(hours=40)).isoformat()
    future_20h = (datetime.now(timezone.utc) + timedelta(hours=20)).isoformat()
    m = _make_market(
        slug="atp-minaur-paul-2026-05-22",
        sport_tag="tennis",
        match_start_iso=future_40h,
    )
    enricher = MagicMock()
    enricher.enrich.return_value = [m.model_copy(update={"match_start_iso": future_20h})]
    sc = MarketScanner(
        _config(max_hours_to_start=24, allowed_sport_tags=["tennis*"]),
        gamma_client=_mock_gamma([m]),
        tennis_start_enricher=enricher,
    )
    result = sc.scan()
    assert len(result) == 1
    assert result[0].slug == "atp-minaur-paul-2026-05-22"
```

(`_make_market` ve `_mock_gamma` zaten test_scanner.py'da mevcut; gerekirse var olan helper'lara `match_start_iso` parametresi ekle.)

- [ ] **Step 3: Run test — fail**

Run: `pytest tests/unit/orchestration/test_scanner.py -k tennis -v`
Expected: FAIL (TypeError, tennis_start_enricher beklenmiyor)

- [ ] **Step 4: Scanner'a parametre + akış**

[scanner.py:93-114](src/orchestration/scanner.py#L93-L114):

```python
class MarketScanner:
    """Gamma → tennis enrich → filter → sort → top N."""

    def __init__(
        self,
        config: ScannerConfig,
        gamma_client: GammaClient | None = None,
        tennis_start_enricher: "TennisStartEnricher | None" = None,
    ) -> None:
        self.config = config
        self._gamma = gamma_client or GammaClient()
        self._tennis_enricher = tennis_start_enricher

    def scan(self) -> list[MarketData]:
        raw = self._gamma.fetch_events()
        if self._tennis_enricher is not None:
            raw = self._tennis_enricher.enrich(raw)
        filtered = [m for m in raw if self._passes_filters(m)]
        filtered.sort(key=_sort_key)
        top = filtered[: self.config.max_markets_per_cycle]
        logger.info("Scanner: %d raw → %d filtered → top %d",
                    len(raw), len(filtered), len(top))
        return top
```

Import ekle dosyanın üst kısmına:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.orchestration.tennis_start_enricher import TennisStartEnricher
```

(Forward ref string formu, runtime'da circular import riski yok çünkü enricher scanner'ı import etmiyor; yine de TYPE_CHECKING güvenli kalıp.)

- [ ] **Step 5: Run scanner tests — pass**

Run: `pytest tests/unit/orchestration/test_scanner.py -v`
Expected: ALL PASS

- [ ] **Step 6: Factory'de wire et**

[factory.py](src/orchestration/factory.py) — MarketScanner oluşturulan yerde:

```python
from src.orchestration.tennis_start_enricher import TennisStartEnricher

espn_client = ESPNClient()  # zaten varsa yeniden kullan
tennis_enricher = TennisStartEnricher(
    espn_client=espn_client,
    cache_ttl_sec=cfg.scanner.tennis_start_cache_ttl_sec,
)
scanner = MarketScanner(
    config=cfg.scanner,
    gamma_client=gamma_client,
    tennis_start_enricher=tennis_enricher,
)
```

(Factory.py'da ESPNClient var mı kontrol et; varsa singletonu paylaş, yoksa yeni instance.)

- [ ] **Step 7: Run all tests**

Run: `pytest -q`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
git add src/orchestration/scanner.py src/orchestration/factory.py src/config/settings.py config.yaml tests/unit/orchestration/test_scanner.py
git commit -m "feat(scanner): tennis start ESPN enricher entegrasyonu"
```

### Task 7: DECISIONS.md güncelle

**Files:**
- Modify: `DECISIONS.md`

- [ ] **Step 1: §B kronolojik log entry'si**

DECISIONS.md §B sonuna ekle:

```markdown
### 2026-05-22 — Tennis ESPN match_start (geri açıldı)

**Karar:** Tennis market'leri için match_start_iso ESPN ATP/WTA scoreboard'dan
çekilir. Polymarket startTime fallback. İkisi de yoksa scanner filtresi eler.

**Neden:** Polymarket tennis startTime'ı zaman zaman boş veya gecikmeli;
end_date_iso fallback'i turnuva sonunu gösterip 24h filtresini şişiriyor.
ESPN otorite + program değişikliklerini günceller.

**Etki:**
- `src/orchestration/tennis_start_enricher.py` (yeni)
- `src/config/sport_rules.py` — tennis entry geri (2026-05-05 kaldırılmıştı)
- `src/orchestration/scanner.py` — enricher inject
- ESPN tennis için skor entegrasyonu yok; sadece match_start.
```

- [ ] **Step 2: Commit**

```bash
git add DECISIONS.md
git commit -m "docs(DECISIONS): tennis ESPN match_start kararı eklendi"
```

---

## Sonuç Kontrol Listesi

- [ ] `pytest -q` tüm testler yeşil
- [ ] `config.yaml`, `settings.py`, `gate.py` üçünde de `max_positions_per_event=3`
- [ ] `ARCHITECTURE_GUARD.md` ve `DECISIONS.md` default 3 olarak güncellendi
- [ ] `tennis_start_enricher.py` ≤200 satır (hedef ~150)
- [ ] Scanner enricher inject edildi, eksiklik halinde `None` ile geri uyumlu çalışır
- [ ] DECISIONS.md §B'ye iki yeni log entry (event-cap, tennis-espn)
