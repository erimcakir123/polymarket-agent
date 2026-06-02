# Avrupa Basket Scraper'lar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Bağımlılık:** Bu plan SPEC-TG-001 (Telegram Alert) önce tamamlanmış olmalı — scraper health alert'leri telegram'a düşmeli. Tek başına çalışsa da observability eksik kalır.

**Goal:** ACB (İspanya), BSL (Türkiye), Lega (İtalya), VTB (Rusya) için kendi scraper'larımızı yaz + NO_DATA_NO_TRADE prensibi + health monitor entegrasyonu.

**Architecture:** Abstract base class `EuropeanBasketScraper`, her lig için override (3 metod). Common: retry/backoff/cache fallback/health update. Output: `<lig>_ratings.json` (mevcut format ile uyumlu).

**Tech Stack:** Python 3.12+, requests, BeautifulSoup4, pytest, mevcut Glicko engine.

---

## Task 1: Base Scraper + Health Update Pattern

**Files:**
- Create: `src/infrastructure/data/basketball/base_scraper.py` (~200 satır)
- Modify: `src/infrastructure/data/basketball/data_source_health.py` (`mark_stale`, `mark_broken` metod ekle)
- Test: `tests/unit/infrastructure/test_base_scraper.py`

- [ ] **Step 1.1: data_source_health.py state'leri genişlet**

```python
# src/infrastructure/data/basketball/data_source_health.py
# Mevcut: record_success, record_failure
# Yeni: mark_stale (cache > stale_hours), mark_broken (parse fail), get_state

class HealthTracker:
    def mark_stale(self, source: str, cache_age_hours: float, at_utc: datetime) -> None:
        ...

    def mark_broken(self, source: str, error: str, at_utc: datetime) -> None:
        ...

    def get_state(self, source: str) -> str:
        """'healthy' | 'stale' | 'broken' | 'unknown'."""
        ...
```

- [ ] **Step 1.2: Test yaz — broken state**

```python
def test_mark_broken_sets_state(tmp_path):
    tracker = HealthTracker(tmp_path / "health.json", now_fn=...)
    tracker.mark_broken("acb", "HTML parse fail", at_utc=...)
    assert tracker.get_state("acb") == "broken"


def test_state_persists_across_instances(tmp_path):
    """File-based persistence — process restart sonrası state korunur."""
    ...
```

- [ ] **Step 1.3: Test PASS**

Run: `pytest tests/unit/infrastructure/test_data_source_health.py -v`

- [ ] **Step 1.4: base_scraper.py implement**

```python
# src/infrastructure/data/basketball/base_scraper.py
"""Abstract base — Avrupa basket lig scraper'ları için ortak iskelet.

NO_DATA_NO_TRADE prensibi: scraper fail → cache fallback (≤48h) → yine fail
→ ratings boş + health 'broken' → basketball_dispatch skip eder, trade YOK.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
import time
import logging
import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GameRecord:
    date_utc: datetime
    home_team: str  # standart kısaltma
    away_team: str
    home_score: int
    away_score: int


@dataclass
class ScrapeResult:
    state: str  # 'healthy' | 'stale' | 'broken'
    games: list[GameRecord]
    teams: list[str]
    error: str | None = None


class EuropeanBasketScraper(ABC):
    """Lig-spesifik scraper'ların türediği base class.

    Override edilen metodlar: _fetch_html, _parse_teams, _parse_games.
    Common davranış: retry/backoff, cache fallback, health update, rating outlier filter.
    """

    SPORT_TAG: str  # subclass set eder: "acb", "bsl", "lega", "vtb"
    CACHE_TTL_HOURS = 48
    REQUEST_TIMEOUT = 15
    USER_AGENT = "Polymarket-Agent-Basketball-Bot/1.0"
    RETRY_COUNT = 3
    RETRY_BACKOFF_SEC = 5

    def __init__(self, cache_dir: Path, health_tracker, now_fn=lambda: datetime.now(timezone.utc)):
        self.cache_dir = cache_dir
        self.health = health_tracker
        self._now = now_fn

    @abstractmethod
    def _fetch_html(self, season: str) -> str:
        """Lig sitesinden HTML çek. requests.get + headers + timeout."""

    @abstractmethod
    def _parse_teams(self, html: str) -> list[str]:
        """HTML'den takım listesi (standart kısaltma)."""

    @abstractmethod
    def _parse_games(self, html: str) -> list[GameRecord]:
        """HTML'den maç sonuçları."""

    def refresh(self, season: str) -> ScrapeResult:
        """Ana entry point — retry + cache fallback + health update."""
        now = self._now()
        # Retry loop
        for attempt in range(self.RETRY_COUNT):
            try:
                html = self._fetch_html(season)
                teams = self._parse_teams(html)
                games = self._parse_games(html)
                if not games:
                    # Sezon dışı varsay (silent skip)
                    return ScrapeResult(state="healthy", games=[], teams=teams)
                self.health.record_success(self.SPORT_TAG, at_utc=now)
                return ScrapeResult(state="healthy", games=games, teams=teams)
            except (requests.RequestException, requests.HTTPError) as e:
                logger.warning("%s fetch fail attempt %d: %s", self.SPORT_TAG, attempt + 1, e)
                if attempt < self.RETRY_COUNT - 1:
                    time.sleep(self.RETRY_BACKOFF_SEC * (2 ** attempt))
                    continue
                # Tüm retry fail
                return self._cache_fallback(now, error=str(e))
            except (ValueError, KeyError, IndexError) as e:
                # Parse fail — broken state
                logger.error("%s parse fail: %s", self.SPORT_TAG, e)
                self.health.mark_broken(self.SPORT_TAG, error=str(e), at_utc=now)
                return ScrapeResult(state="broken", games=[], teams=[], error=str(e))

    def _cache_fallback(self, now: datetime, error: str) -> ScrapeResult:
        """Cache var ve ≤ 48h ise stale state ile döndür; eski ise broken."""
        cache_file = self.cache_dir / f"{self.SPORT_TAG}_ratings.json"
        if not cache_file.exists():
            self.health.mark_broken(self.SPORT_TAG, error=error, at_utc=now)
            return ScrapeResult(state="broken", games=[], teams=[], error=error)
        cache_age_hours = (now.timestamp() - cache_file.stat().st_mtime) / 3600
        if cache_age_hours <= self.CACHE_TTL_HOURS:
            self.health.mark_stale(self.SPORT_TAG, cache_age_hours, at_utc=now)
            return ScrapeResult(state="stale", games=[], teams=[], error=error)
        self.health.mark_broken(self.SPORT_TAG, error=f"{error} + cache stale {cache_age_hours:.1f}h", at_utc=now)
        return ScrapeResult(state="broken", games=[], teams=[], error=error)

    def _http_get(self, url: str) -> str:
        """Helper — User-Agent + timeout + status check."""
        resp = requests.get(
            url,
            headers={"User-Agent": self.USER_AGENT},
            timeout=self.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.text
```

- [ ] **Step 1.5: Test base — retry + cache fallback**

```python
def test_retry_then_cache_fallback(tmp_path):
    """3 fail → cache var + ≤48h → stale state."""
    cache_file = tmp_path / "test_ratings.json"
    cache_file.write_text("[]")
    # Mock _fetch_html → fail
    class TestScraper(EuropeanBasketScraper):
        SPORT_TAG = "test"
        def _fetch_html(self, season): raise requests.ConnectionError("ban")
        def _parse_teams(self, html): return []
        def _parse_games(self, html): return []
    health = Mock()
    scraper = TestScraper(tmp_path, health)
    result = scraper.refresh("2026")
    assert result.state == "stale"
    health.mark_stale.assert_called_once()


def test_parse_fail_triggers_broken_state(tmp_path):
    """Parse fail → broken (cache var olsa bile parser bozuk = sistematik problem)."""
    ...


def test_no_games_silent_skip(tmp_path):
    """0 game data → healthy state (sezon dışı normal)."""
    ...
```

- [ ] **Step 1.6: Test PASS**

Run: `pytest tests/unit/infrastructure/test_base_scraper.py -v`

- [ ] **Step 1.7: Commit**

```bash
git add src/infrastructure/data/basketball/base_scraper.py src/infrastructure/data/basketball/data_source_health.py tests/unit/infrastructure/test_*
git commit -m "feat(basketball): EuropeanBasketScraper base class — NO_DATA_NO_TRADE pattern"
```

---

## Task 2: ACB Scraper (İspanya Liga Endesa)

**Files:**
- Create: `src/infrastructure/data/basketball/acb_scraper.py` (~150 satır)
- Test: `tests/unit/infrastructure/test_acb_scraper.py` (fixture: gerçek ACB HTML snapshot)
- Modify: `src/domain/matching/basketball_team_resolver.py` (`_ACB_TEAMS` dict)

- [ ] **Step 2.1: ACB takım listesi araştırma**

ACB resmi sitesi (acb.com) takım listesi:
```
RM (Real Madrid), FCB (FC Barcelona), VAL (Valencia), BAS (Baskonia), UCM (Unicaja),
LEN (Lenovo Tenerife), GCA (Gran Canaria), BIL (Surne Bilbao), CAN (Casademont Zaragoza),
JOV (Joventut), MAN (Manresa), MUR (Murcia), GRA (Granada), ZUN (Zunder Palencia),
LAL (La Laguna Tenerife), VAL (Valencia)... toplam 18 takım
```

Polymarket slug convention (gözlem: `bkligend-val-bil-2026-06-03`):
- Prefix `bkligend` (basketball Liga Endesa)
- Kısaltmalar: `val`, `bil`, `rea`, `la`, `bas`, vs.

- [ ] **Step 2.2: Slug-prefix mapping ekle**

```python
# src/infrastructure/apis/gamma_client.py _SLUG_PREFIX_SPORT'a ekle
"bkligend": "liga_acb",
"bkbsl": "turkey_bsl",     # tahmin — gözlem ile doğrulanır
"bklega": "italy_lega",
"bkvtb": "vtb",
```

- [ ] **Step 2.3: ACB resolver mapping**

```python
# src/domain/matching/basketball_team_resolver.py
_ACB_TEAMS: dict[str, str] = {
    "rea": "RM", "madrid": "RM", "realmadrid": "RM",
    "fcb": "FCB", "barcelona": "FCB", "barca": "FCB",
    "val": "VAL", "valencia": "VAL", "valenciabasket": "VAL",
    "bas": "BAS", "baskonia": "BAS", "vitoria": "BAS",
    "ucm": "UCM", "unicaja": "UCM", "malaga": "UCM",
    "len": "LEN", "tenerife": "LEN",
    "gca": "GCA", "grancanaria": "GCA", "gc": "GCA",
    "bil": "BIL", "bilbao": "BIL",
    "can": "CAN", "zaragoza": "CAN",
    "jov": "JOV", "joventut": "JOV", "badalona": "JOV",
    "man": "MAN", "manresa": "MAN",
    "mur": "MUR", "murcia": "MUR",
    "gra": "GRA", "granada": "GRA",
    "zun": "ZUN", "palencia": "ZUN",
    "la": "LAL", "lalaguna": "LAL",  # NOT: "la" çakışıyor WNBA ile! Sport_tag ile ayrıştır
    "sas": "SAS", "sevilla": "SAS",  # eğer Sevilla varsa
}

def _lookup(league: str) -> dict[str, str]:
    # ... mevcut + yeni:
    if league == "liga_acb":
        return _ACB_TEAMS
    if league == "turkey_bsl":
        return _BSL_TEAMS
    if league == "italy_lega":
        return _LEGA_TEAMS
    if league == "vtb":
        return _VTB_TEAMS
```

- [ ] **Step 2.4: ACB Scraper class**

```python
# src/infrastructure/data/basketball/acb_scraper.py
from bs4 import BeautifulSoup
from src.infrastructure.data.basketball.base_scraper import EuropeanBasketScraper, GameRecord
from datetime import datetime, timezone


class AcbScraper(EuropeanBasketScraper):
    SPORT_TAG = "liga_acb"
    BASE_URL = "https://www.acb.com/calendario/jornada/ver/temporada_id"  # gerçek URL araştırılır

    def _fetch_html(self, season: str) -> str:
        url = f"{self.BASE_URL}/{season}"
        return self._http_get(url)

    def _parse_teams(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        teams = set()
        for el in soup.select(".equipo-nombre"):  # CSS selector araştırılır
            short = el.get("data-abbr", "").upper()
            if short:
                teams.add(short)
        return sorted(teams)

    def _parse_games(self, html: str) -> list[GameRecord]:
        soup = BeautifulSoup(html, "html.parser")
        games = []
        for row in soup.select(".partido"):  # CSS selector araştırılır
            try:
                date_str = row.select_one(".fecha").get_text(strip=True)
                home = row.select_one(".equipo-local").get("data-abbr", "").upper()
                away = row.select_one(".equipo-visitante").get("data-abbr", "").upper()
                score_text = row.select_one(".resultado").get_text(strip=True)
                home_score, away_score = map(int, score_text.split("-"))
                games.append(GameRecord(
                    date_utc=datetime.strptime(date_str, "%d/%m/%Y").replace(tzinfo=timezone.utc),
                    home_team=home, away_team=away,
                    home_score=home_score, away_score=away_score,
                ))
            except (AttributeError, ValueError, KeyError):
                continue
        return games
```

- [ ] **Step 2.5: Fixture-based test**

Gerçek HTML snapshot al (manuel curl + kaydet `tests/fixtures/acb_sample.html`):

```python
def test_acb_parses_real_html_sample():
    """Gerçek ACB HTML fixture'ı doğru takım + maç parse eder."""
    html = (Path(__file__).parent.parent / "fixtures" / "acb_sample.html").read_text(encoding="utf-8")
    class TestScraper(AcbScraper):
        def _fetch_html(self, season): return html
    scraper = TestScraper(...)
    result = scraper.refresh("2025-26")
    assert result.state == "healthy"
    assert len(result.teams) >= 18  # 18 ACB takımı
    assert len(result.games) > 0
```

- [ ] **Step 2.6: Test PASS**

Run: `pytest tests/unit/infrastructure/test_acb_scraper.py -v`

- [ ] **Step 2.7: Config'e ACB ekle**

```yaml
# config.yaml
basketball:
  enabled_leagues:
    - nba
    - wnba
    # ... mevcut
    - liga_acb     # YENİ
  leagues:
    liga_acb:
      home_advantage: 80.0
      k_factor: 20.0
      blend_elo: 0.55
      margin_std: 10.0
      total_std: 18.0
```

- [ ] **Step 2.8: factory_basketball'da ratings build hook**

`scripts/build_european_basket_ratings.py` (yeni) — manuel build için. Boot'ta otomatik refresh `_maybe_invoke_basketball_refresh`'e entegre.

- [ ] **Step 2.9: Full pytest**

Run: `python -m pytest -q`

- [ ] **Step 2.10: Commit**

```bash
git add src/infrastructure/data/basketball/acb_scraper.py src/domain/matching/basketball_team_resolver.py src/infrastructure/apis/gamma_client.py config.yaml tests/
git commit -m "feat(basketball): ACB Liga Endesa scraper + team resolver + slug mapping"
```

---

## Task 3: BSL Scraper (Türkiye Basketbol Süper Ligi)

**Files:**
- Create: `src/infrastructure/data/basketball/bsl_scraper.py`
- Test: `tests/unit/infrastructure/test_bsl_scraper.py`
- Modify: resolver `_BSL_TEAMS` dict

- [ ] **Step 3.1: BSL takım listesi**

TBF (Türkiye Basketbol Federasyonu) veya tblstat.com kaynak araştırılır.

Takım listesi (16 takım):
```
FB (Fenerbahçe Beko), EFES (Anadolu Efes), GS (Galatasaray Nef), TF (Türk Telekom), DAR (Darüşşafaka),
BAH (Bahçeşehir Koleji), BES (Beşiktaş Emlakjet), MER (Merkezefendi), TOF (Tofaş), KAR (Karşıyaka),
PET (Petkimspor), MAN (Manisa), SAM (Samsunspor), ART (Aliağa Petkim), YIL (Yılmaz İnşaat), ONV (Onvo Büyükçekmece)
```

- [ ] **Step 3.2: BSL Scraper class**

ACB pattern paralel — sadece URL + CSS selector + tarih format değişir.

- [ ] **Step 3.3: Test + config + commit**

ACB pattern paralel.

---

## Task 4: Lega Scraper (İtalya Lega Basket Serie A)

**Files:**
- Create: `src/infrastructure/data/basketball/lega_scraper.py`
- Test: `tests/unit/infrastructure/test_lega_scraper.py`
- Modify: resolver `_LEGA_TEAMS`

Kaynak: `legabasket.it`. ACB pattern paralel.

Takım listesi (16 takım):
```
MIL (Olimpia Milano), VIRT (Virtus Bologna), TRT (Trento), VEN (Reyer Venezia),
TOR (Reale Mutua Torino), BRE (Germani Brescia), VAR (Openjobmetis Varese),
SAS (Sassari Dinamo), TRP (Trapani), SCV (Scaligera Verona), CAN (Pallacanestro Cantù),
NAP (Napoli), CRE (Cremona), TRE (Treviso), PIS (Pistoia), REG (Reggio Emilia)
```

---

## Task 5: VTB Scraper (Rusya VTB United League)

**Files:**
- Create: `src/infrastructure/data/basketball/vtb_scraper.py`
- Test: `tests/unit/infrastructure/test_vtb_scraper.py`
- Modify: resolver `_VTB_TEAMS`

Kaynak: `vtb-league.com`. ACB pattern paralel.

Takım listesi (12 takım):
```
CSKA (CSKA Moscow), ZEN (Zenit St. Petersburg), UNI (UNICS Kazan), LOK (Lokomotiv Kuban),
PARMA (Parma-PARI), AVT (Avtodor Saratov), MBA (MBA Moscow), URA (Ural'maş),
NIZ (Niznhy Novgorod), SAM (Samara), PAR (PARMA-PARI), ENI (Enisey)
```

---

## Task 6: factory_basketball Entegrasyonu — Tüm Yeni Ligler

**Files:**
- Modify: `src/orchestration/factory_basketball.py`
- Modify: `src/strategy/enrichment/basketball_dispatch.py` (`_BASKETBALL_LEAGUES` set)

- [ ] **Step 6.1: `_BASKETBALL_LEAGUES` set güncelle**

```python
_BASKETBALL_LEAGUES = frozenset({
    "nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl",
    "g_league", "summer_league", "eurocup",
    # YENİ
    "liga_acb", "turkey_bsl", "italy_lega", "vtb",
})
```

- [ ] **Step 6.2: `_maybe_invoke_basketball_refresh` her scraper için**

```python
# factory_basketball.py
EUROPEAN_LEAGUES = {"liga_acb", "turkey_bsl", "italy_lega", "vtb"}

for league in enabled:
    if league in EUROPEAN_LEAGUES:
        scraper = _get_european_scraper(league)  # acb_scraper, bsl_scraper, ...
        result = scraper.refresh(season=current_season)
        if result.state == "healthy":
            # ratings build (Glicko) + save
            ratings = _build_glicko_from_games(result.games, result.teams, params)
            save_ratings(ratings, cache_dir / f"{league}_ratings.json")
        # state ne olursa olsun health tracker güncel (scraper.refresh içinde)
```

- [ ] **Step 6.3: Full pytest + bot reload test**

Run: `python -m pytest -q`
Expected: tüm test passed.

Bot reload → bot.log'da:
```
basketball refresh: league=liga_acb source=acb_scraper games=120
basketball refresh: league=turkey_bsl source=bsl_scraper games=80
...
```

- [ ] **Step 6.4: Commit**

```bash
git add src/orchestration/factory_basketball.py src/strategy/enrichment/basketball_dispatch.py
git commit -m "feat(basketball): factory entegrasyon — 4 Avrupa lig scraper"
```

---

## Task 7: Outlier Filter + NO_DATA_NO_TRADE Doğrulama

**Files:**
- Modify: `src/orchestration/factory_basketball.py` (rating outlier filter)
- Test: `tests/integration/test_european_basket_no_data_no_trade.py`

- [ ] **Step 7.1: Outlier filter ekle**

```python
def _filter_outlier_ratings(ratings: dict) -> dict:
    """Glicko rating < 800 veya > 2400 ise outlier — reject."""
    return {
        team: r for team, r in ratings.items()
        if 800 < r.elo_rating < 2400
    }
```

- [ ] **Step 7.2: NO_DATA_NO_TRADE integration test**

```python
def test_scraper_broken_no_trade(tmp_path):
    """ACB scraper broken state → basketball_dispatch ACB market'i reddeder."""
    # 1. Health "broken" set et
    # 2. ACB ratings boş dict
    # 3. basketball_dispatch.enrich_with_basketball_dispatch(market, ...)
    # 4. Expected: result.probability is None, fail_reason = MODEL_BASKETBALL_DATA_MISSING
    ...


def test_scraper_stale_uses_cache(tmp_path):
    """Stale state — cache var, 48h içinde → ratings yüklü, trade edilebilir."""
    ...
```

- [ ] **Step 7.3: Telegram alert integration test (sahte scraper down)**

```python
def test_scraper_broken_triggers_telegram_critical(tmp_path):
    """Health "broken" state → HealthMonitor critical alert atar."""
    # Plan 2'deki HealthMonitor + scraper down kombinasyonu
    ...
```

- [ ] **Step 7.4: Full pytest**

Run: `python -m pytest -q`

- [ ] **Step 7.5: Commit**

```bash
git add src/orchestration/factory_basketball.py tests/integration/test_european_basket_no_data_no_trade.py
git commit -m "feat(basketball): outlier filter + NO_DATA_NO_TRADE integration test"
```

---

## Final Self-Review

- [ ] **Spec coverage:** SPEC-EUROBASKET-001 4 lig + NO_DATA_NO_TRADE + telegram entegrasyonu → 7 Task ✓
- [ ] **Yan task atlama:**
  - Slug-prefix mapping (Task 2.2) ✓
  - Team resolver alias (her lig için) ✓
  - Config enabled_leagues (Task 2.7) ✓
  - Factory refresh hook (Task 6) ✓
  - Outlier filter (Task 7) ✓
- [ ] **Pattern sport-agnostic:** Base scraper class → 4 lig aynı pattern, gelecekte 5. lig eklemek 1 saat
- [ ] **ARCH_GUARD:** Her scraper < 200 satır, base class < 200 satır, domain I/O yok (HTTP infra'da), magic number yok (config'den)
- [ ] **Dead code yok:** BRScraper geçmişte silindi, yeni scraper'lar TAZE yazıldı
- [ ] **Drift yok:** Base class + health tracker pattern her yeni lig için aynı

---

## Execution Order

1. Task 1 (Base scraper + health) — temel, bağımsız (~45dk)
2. Task 2 (ACB) — Task 1 bağımlı (~60dk — HTML fixture al, parser yaz, test)
3. Task 3 (BSL) — Task 1 bağımlı, ACB pattern paralel (~45dk)
4. Task 4 (Lega) — aynı (~45dk)
5. Task 5 (VTB) — aynı (~45dk)
6. Task 6 (Factory entegrasyon) — Task 2-5 bağımlı (~30dk)
7. Task 7 (Outlier + NO_DATA_NO_TRADE test) — Task 6 bağımlı (~30dk)

**Toplam:** ~5-6 saat (uzun sprint; kullanıcı tek seferde değil aşamalı isteyebilir)

## Bağımlılık Sırası

```
SPEC-AUDIT-001 (Plan 1) → resolver alias coverage genel pattern hazır olmalı
   ↓
SPEC-TG-001 (Plan 2) → telegram alert sistemi hazır olmalı
   ↓
SPEC-EUROBASKET-001 (Plan 3) → bu plan
```

## Verification Before Completion

- [ ] 1894+ pytest passed
- [ ] 4 scraper test fixture ile doğrulanmış
- [ ] Bot reload sonrası bot.log'da 4 yeni "basketball refresh: league=..." satırı görülmeli
- [ ] Sahte broken state senaryosu → telegram critical alert düşer
- [ ] Polymarket Avrupa basket maçı (bkligend-X-Y veya bkbsl-X-Y) açıkken bot trade etmeye başlar
- [ ] DECISIONS.md'ye "SPEC-EUROBASKET-001 done" notu eklenmiş
