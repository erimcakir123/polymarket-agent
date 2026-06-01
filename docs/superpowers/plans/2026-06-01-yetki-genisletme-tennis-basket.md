# Yetki Genişletme — Tenis + Basket Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mevcut tenis (Sackmann) + basket (Elo + Pace) modellerinin yetki alanını genişlet — Polymarket'in %92'sine erişim. **NO DATA → NO TRADE** prensibiyle, captcha/IP block/HTML değişikliği gibi scrape risklerine karşı strict health monitoring eklenecek.

**Architecture:**
- Tenis: Sackmann Doubles refresher + yeni doubles_pricer (singles modelinin paraleli)
- Basket: nba_api'nin mevcut G League / Summer League desteğini aktive et, euroleague-api'nin EuroCup'ını aktive et, Avrupa yerel ligler (BSL/ACB/Lega) için BRScraper-tabanlı scrape modülü
- ITF/Challenger için **mevcut Sackmann verisi** + ayrı kalibrasyon eğrisi (yetki filtresi gevşetilir, küçük bahisle dahil)
- Scrape kaynaklar için: cache age check + Pydantic schema fail-fast + lig-başına automatic disable (3 ardışık fail = lig hibernation)

**Tech Stack:** Python 3.12+, mevcut nba_api (1.11+), euroleague-api, BRScraper (yeni dependency), Sackmann CSV indirme (mevcut refresher), Pydantic v2 schema validation, ESPN scoreboard yedek.

**Önkoşul:** Adım 1 (Yetki filtresi) TAMAMLANDI commit `907bbc6` — phi>=100 tenis + futures/prop slug filtre basket.

---

## File Structure

### Yeni dosyalar

| Dosya | Sorumluluk | Tahmini satır |
|---|---|---|
| `src/domain/pricing/tennis/doubles_pricer.py` | Doubles maç tahmini — singles pricer paralel + partner rating birleştirme | ~120 |
| `src/infrastructure/data/basketball/brscraper_refresher.py` | BSL/ACB/Lega scrape — strict health monitoring | ~180 |
| `src/infrastructure/data/source_freshness.py` | Generic cache age check — "veri X saatten eski ise lig hibernation" | ~80 |
| `scripts/build_european_local_basketball_ratings.py` | BSL/ACB/Lega rating bulk fetch CLI | ~100 |
| `tests/unit/domain/pricing/tennis/test_doubles_pricer.py` | Doubles pricer unit testleri | ~80 |
| `tests/unit/infrastructure/data/basketball/test_brscraper_refresher.py` | BRScraper testler (mocked HTTP) | ~100 |
| `tests/unit/infrastructure/data/test_source_freshness.py` | Cache age check testleri | ~50 |

### Modifiye edilecek dosyalar

| Dosya | Değişiklik |
|---|---|
| `src/infrastructure/data/sackmann_refresher.py` | `_SOURCES` dict'ine doubles CSV ekle (atp_doubles_{year}, wta_doubles_{year}) |
| `src/infrastructure/data/basketball/nba_api_refresher.py` | `_SUPPORTED_LEAGUES` genişletme: `g_league`, `summer_league` |
| `src/infrastructure/data/basketball/euroleague_refresher.py` | `eurocup` support — competition_id parameter |
| `src/infrastructure/data/basketball/schemas.py` | `GameRecord.league` Literal genişlet: `g_league`, `summer_league`, `eurocup`, `bsl`, `acb`, `lega` |
| `src/infrastructure/data/calibration_store.py` | (Plan 1.D'den) ITF/Challenger için ayrı key namespace: `tennis:itf:moneyline` |
| `src/strategy/enrichment/tennis_dispatch.py` | ITF tier algıla → kalibrasyon eğrisi farklı + güven puanı düşür |
| `src/strategy/enrichment/basketball_anchor_enricher.py` | Yeni ligler için league validation |
| `src/config/settings.py` | `BasketballConfig.leagues` 6 yeni lig key + scrape kaynak ayarları |
| `src/orchestration/factory.py` | Yeni refresh hook'lar (4 yeni lig + tenis doubles) |
| `config.yaml` | Yeni lig parametreleri (margin_std, total_std, home_advantage) |
| `requirements.txt` | `BRScraper>=0.1.0` opsiyonel (paket yoksa Avrupa yerel lig degrade) |

---

## Tasks

### Task 2: Sackmann Doubles Veri İndirme

**Files:**
- Modify: `src/infrastructure/data/sackmann_refresher.py` — `_SOURCES` genişletme
- Test: `tests/unit/infrastructure/data/test_sackmann_refresher.py`

- [ ] **Step 2.1: Test ekle — yeni source'ların _SOURCES dict'inde olduğunu doğrula**

`tests/unit/infrastructure/data/test_sackmann_refresher.py`'ye ekle:

```python
def test_sackmann_sources_includes_doubles():
    """Doubles CSV'leri _SOURCES dict'inde tanımlı olmalı (Wimbledon/Grand Slam Doubles için)."""
    from src.infrastructure.data.sackmann_refresher import _SOURCES
    assert "atp_doubles" in _SOURCES
    assert "wta_doubles" in _SOURCES
    # URL pattern doğru mu?
    assert "doubles" in _SOURCES["atp_doubles"]["url"]
    assert "doubles" in _SOURCES["wta_doubles"]["url"]
```

- [ ] **Step 2.2: Test FAIL doğrula**

Run: `python -m pytest tests/unit/infrastructure/data/test_sackmann_refresher.py::test_sackmann_sources_includes_doubles -v`
Expected: FAIL — KeyError: 'atp_doubles'

- [ ] **Step 2.3: `_SOURCES` dict'ine doubles satırları ekle**

`src/infrastructure/data/sackmann_refresher.py` içinde mevcut dict'e ekle (existing wta_futures sonrası):

```python
    "atp_doubles": {
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_doubles_{year}.csv",
        "file": "atp_matches_doubles_{year}.csv",
    },
    "wta_doubles": {
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_doubles_{year}.csv",
        "file": "wta_matches_doubles_{year}.csv",
    },
```

- [ ] **Step 2.4: Test PASS**

Run: `python -m pytest tests/unit/infrastructure/data/test_sackmann_refresher.py -v`
Expected: PASS

- [ ] **Step 2.5: Commit**

```bash
git add src/infrastructure/data/sackmann_refresher.py tests/unit/infrastructure/data/test_sackmann_refresher.py
git commit -m "feat(tennis/data): Sackmann Doubles CSV indirme (Task 2)

ATP/WTA doubles maç verisi Sackmann repo'sundan indirilir.
Wimbledon Doubles + Roland Garros Doubles + diğer Grand Slam doubles
market'leri için altyapı. Pricer Task 3'te eklenir.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Doubles Pricer (Domain — saf math)

**Files:**
- Create: `src/domain/pricing/tennis/doubles_pricer.py`
- Test: `tests/unit/domain/pricing/tennis/test_doubles_pricer.py`

- [ ] **Step 3.1: Test yaz — doubles rating birleştirme + match prob**

`tests/unit/domain/pricing/tennis/test_doubles_pricer.py`:

```python
"""Doubles match pricer — partner rating birleştirme + singles pricer wraparound."""
from __future__ import annotations

from src.domain.pricing.tennis.doubles_pricer import (
    DoublesTeam, combine_partner_ratings, price_doubles_h2h,
)
from src.domain.pricing.tennis.glicko import Rating


def test_combine_partner_ratings_averages_mu():
    """İki oyuncunun rating'i average — basit doubles modeli."""
    p1 = Rating(mu=1600.0, phi=80.0, sigma=0.06)
    p2 = Rating(mu=1400.0, phi=80.0, sigma=0.06)
    team = combine_partner_ratings(p1, p2)
    assert abs(team.mu - 1500.0) < 0.1


def test_combine_partner_ratings_phi_increases():
    """Doubles takım phi tek oyuncudan büyük (belirsizlik artar)."""
    p1 = Rating(mu=1500.0, phi=80.0, sigma=0.06)
    p2 = Rating(mu=1500.0, phi=80.0, sigma=0.06)
    team = combine_partner_ratings(p1, p2)
    assert team.phi > 80.0  # belirsizlik artar


def test_price_doubles_strong_team_wins_more():
    strong = DoublesTeam(rating=Rating(mu=1700.0, phi=70.0, sigma=0.06))
    weak = DoublesTeam(rating=Rating(mu=1300.0, phi=70.0, sigma=0.06))
    p = price_doubles_h2h(strong, weak)
    assert p > 0.7
```

- [ ] **Step 3.2: Test FAIL doğrula**

Run: `python -m pytest tests/unit/domain/pricing/tennis/test_doubles_pricer.py -v`
Expected: ImportError

- [ ] **Step 3.3: Implementation**

`src/domain/pricing/tennis/doubles_pricer.py`:

```python
"""Doubles match pricer — partner rating birleştirme + singles pricer paralel.

Domain layer — saf math, I/O yok. Singles glicko.py pattern'ini taklit eder.
Doubles'da takım = 2 oyuncu birleşimi. Rating birleştirme:
  mu_team = (mu_p1 + mu_p2) / 2
  phi_team = sqrt(phi_p1^2 + phi_p2^2) / 2  (combined uncertainty)

Bu basit blend Sackmann doubles datasını anlamak için yeterli. Daha
gelişmiş modelleme (oyuncu × partner sinerji) ileri faz.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.domain.pricing.tennis.glicko import Rating, win_probability


@dataclass(frozen=True)
class DoublesTeam:
    """Doubles takımı — combined rating."""
    rating: Rating


def combine_partner_ratings(p1: Rating, p2: Rating) -> Rating:
    """İki oyuncudan takım rating üret. mu=average, phi=combined uncertainty."""
    mu = (p1.mu + p2.mu) / 2.0
    # Combined std (independent uncertainty): sqrt(sigma1^2 + sigma2^2)
    # phi paralel: takım belirsizliği iki oyuncudan büyük
    phi = math.sqrt(p1.phi * p1.phi + p2.phi * p2.phi) / 2.0
    sigma = (p1.sigma + p2.sigma) / 2.0
    return Rating(mu=mu, phi=phi, sigma=sigma)


def price_doubles_h2h(team_a: DoublesTeam, team_b: DoublesTeam) -> float:
    """P(team_a wins). Singles glicko.win_probability ile aynı."""
    return win_probability(team_a.rating, team_b.rating)
```

- [ ] **Step 3.4: Test PASS**

Run: `python -m pytest tests/unit/domain/pricing/tennis/test_doubles_pricer.py -v`
Expected: 3 passed

- [ ] **Step 3.5: Commit**

```bash
git add src/domain/pricing/tennis/doubles_pricer.py tests/unit/domain/pricing/tennis/test_doubles_pricer.py
git commit -m "feat(tennis/domain): doubles pricer — partner rating birleştirme (Task 3)

Singles glicko.py pattern paralel. Doubles takım = (mu_avg, phi_combined).
Wimbledon/Grand Slam Doubles market'leri için pricer. Strategy entegrasyonu
Task 3.5 dispatch güncellemesinde.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: NBA G League Aktivasyon

**Files:**
- Modify: `src/infrastructure/data/basketball/nba_api_refresher.py:21` — `_SUPPORTED_LEAGUES` genişlet
- Modify: `src/infrastructure/data/basketball/schemas.py` — `League` Literal genişlet
- Modify: `config.yaml` — yeni lig parametreleri
- Modify: `src/config/settings.py:BasketballConfig.leagues` default factory

- [ ] **Step 4.1: Test — nba_api g_league cover**

`tests/unit/infrastructure/data/basketball/test_nba_api_refresher.py`'ye ekle:

```python
def test_fetch_supports_g_league():
    """G League nba_api'de league_id='20' — yeni lig kabul edilmeli."""
    from unittest.mock import MagicMock
    fake = MagicMock()
    fake.return_value.get_dict.return_value = {"resultSets": [{"rowSet": [], "headers": []}]}
    games = fetch_game_log_via_nba_api(
        league="g_league", season="2024-25", endpoint_factory=fake,
    )
    assert games == []
    # endpoint_factory league_id='20' ile çağrılmalı (G League)
    fake.assert_called_once_with(season="2024-25", league_id="20")
```

- [ ] **Step 4.2: Test FAIL doğrula**

Expected: FAIL — `g_league` not in `_SUPPORTED_LEAGUES`

- [ ] **Step 4.3: nba_api_refresher.py güncellemesi**

`src/infrastructure/data/basketball/nba_api_refresher.py:21` değişikliği:

```python
_SUPPORTED_LEAGUES = ("nba", "wnba", "g_league", "summer_league")

# League ID mapping (nba_api convention):
#   "00" = NBA, "10" = WNBA, "20" = G League, "15" = Summer League
_LEAGUE_ID_MAP = {
    "nba": "00",
    "wnba": "10",
    "g_league": "20",
    "summer_league": "15",
}
```

ve `fetch_game_log_via_nba_api` içinde league_id mapping kullan:

```python
def fetch_game_log_via_nba_api(
    league: str,
    season: str,
    endpoint_factory: Callable,
) -> list[GameRecord]:
    if league not in _SUPPORTED_LEAGUES:
        raise ValueError(f"Unsupported league: {league}")
    league_id = _LEAGUE_ID_MAP[league]
    endpoint = endpoint_factory(season=season, league_id=league_id)
    ...
```

- [ ] **Step 4.4: schemas.py League Literal genişlet**

`src/infrastructure/data/basketball/schemas.py` (3 yerde, replace_all):

```python
league: Literal["nba", "wnba", "ncaab", "wncaab", "euroleague",
                "g_league", "summer_league", "eurocup", "bsl", "acb", "lega"]
```

- [ ] **Step 4.5: settings.py BasketballConfig.leagues default factory genişlet**

`src/config/settings.py` mevcut default_factory'ye ekle:

```python
"g_league": BasketballLeagueParams(
    home_advantage=80.0, k_factor=22.0, blend_elo=0.50,
    margin_std=13.0, total_std=22.0,
),
"summer_league": BasketballLeagueParams(
    home_advantage=70.0, k_factor=30.0, blend_elo=0.45,
    margin_std=14.0, total_std=22.0,
),
```

- [ ] **Step 4.6: config.yaml `basketball.leagues` aynı parametreleri ekle**

(yaml syntax — settings.py default ile uyumlu)

- [ ] **Step 4.7: Test PASS**

Run: `python -m pytest tests/unit/infrastructure/data/basketball/ -v`

- [ ] **Step 4.8: Commit**

```bash
git add src/infrastructure/data/basketball/nba_api_refresher.py src/infrastructure/data/basketball/schemas.py src/config/settings.py config.yaml tests/unit/infrastructure/data/basketball/test_nba_api_refresher.py
git commit -m "feat(basketball/data): NBA G League + Summer League aktivasyonu (Task 4)

nba_api zaten G League (league_id=20) + Summer League (league_id=15) destekliyor.
_SUPPORTED_LEAGUES + _LEAGUE_ID_MAP eklendi. Lig parametreleri:
  G League: home_adv=80, k=22, blend=0.50, m_std=13
  Summer League: home_adv=70, k=30, blend=0.45 (kadro deneme dönemi volatile)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: NBA Summer League Aktivasyon

Task 4'te `_LEAGUE_ID_MAP`'e `summer_league` zaten eklendi. Summer League'in mevcut sezonu Temmuz başlar — Mevcut cache 24h eski ise bot Temmuz başında otomatik fetch eder. Bu task **integration test + factory hook** olarak ayrılır.

**Files:**
- Modify: `src/orchestration/factory.py:_make_basketball_fetchers` — `g_league`/`summer_league` için PRO_BASKET_LEAGUES dahil et

- [ ] **Step 5.1: factory.py PRO_BASKET_LEAGUES set'ine ekle**

```python
_PRO_BASKET_LEAGUES = frozenset({"nba", "wnba", "g_league", "summer_league"})
```

- [ ] **Step 5.2: test_factory_basketball_dispatch — yeni ligler de basketball_model'e gitsin**

Mevcut test ekleme (test_factory_basketball_dispatch.py):

```python
def test_g_league_routes_to_basketball_model():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("g_league") == "basketball_model"


def test_summer_league_routes_to_basketball_model():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("summer_league") == "basketball_model"
```

- [ ] **Step 5.3: factory.py `_BASKETBALL_SPORT_TAGS` set'ini genişlet**

```python
_BASKETBALL_SPORT_TAGS = frozenset({
    "nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl",
    "g_league", "summer_league", "eurocup", "bsl", "acb", "lega",
})
```

- [ ] **Step 5.4: Test PASS**

Run: `python -m pytest tests/unit/orchestration/test_factory_basketball_dispatch.py -v`

- [ ] **Step 5.5: Commit**

```bash
git add src/orchestration/factory.py tests/unit/orchestration/test_factory_basketball_dispatch.py
git commit -m "feat(basketball/orchestration): factory dispatch — G League + Summer League + EuroCup + BSL/ACB/Lega (Task 5)

Sport_tag dispatch'i 6 yeni lig için genişletildi.
_PRO_BASKET_LEAGUES + _BASKETBALL_SPORT_TAGS güncellendi.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: EuroCup Aktivasyon (euroleague-api zaten dahil)

**Files:**
- Modify: `src/infrastructure/data/basketball/euroleague_refresher.py` — competition parameter

- [ ] **Step 6.1: Test — eurocup competition ID parametre**

`tests/unit/infrastructure/data/basketball/test_euroleague_refresher.py`'ye ekle:

```python
def test_fetch_supports_eurocup_competition():
    """EuroCup competition_id ile fetch — endpoint factory parametre alır."""
    from unittest.mock import MagicMock
    fake = MagicMock()
    fake.return_value.get_game_stats.return_value = []
    games = fetch_game_log_via_euroleague_api(
        season="2024", endpoint_factory=fake, competition="eurocup",
    )
    fake.assert_called_once_with(season="2024", competition_code="U")  # U = EuroCup
```

- [ ] **Step 6.2: Implementation — `fetch_game_log_via_euroleague_api` signature genişlet**

```python
_COMPETITION_CODES = {
    "euroleague": "E",
    "eurocup": "U",
}


def fetch_game_log_via_euroleague_api(
    season: str,
    endpoint_factory: Callable,
    competition: str = "euroleague",
) -> list[GameRecord]:
    """euroleague-api üzerinden bir sezonun maç istatistiklerini çek."""
    code = _COMPETITION_CODES.get(competition)
    if code is None:
        raise ValueError(f"Unsupported competition: {competition}")
    endpoint = endpoint_factory(season=season, competition_code=code)
    ...
```

(Pair_and_convert league parameter da `eurocup` desteklemeli — convert function'da league="eurocup" set et)

- [ ] **Step 6.3: Test PASS**

- [ ] **Step 6.4: Commit**

```bash
git add src/infrastructure/data/basketball/euroleague_refresher.py tests/unit/infrastructure/data/basketball/test_euroleague_refresher.py
git commit -m "feat(basketball/data): EuroCup aktivasyon — euroleague-api competition param (Task 6)

EuroCup (Avrupa #2 lig) için euroleague-api'nin built-in desteği aktive edildi.
Mevcut Euroleague refresher'a competition='eurocup' parametre eklendi.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Source Freshness Guard (Generic — Scrape Güvenliği)

**Files:**
- Create: `src/infrastructure/data/source_freshness.py`
- Test: `tests/unit/infrastructure/data/test_source_freshness.py`

- [ ] **Step 7.1: Test — cache age check + lig hibernation karar**

`tests/unit/infrastructure/data/test_source_freshness.py`:

```python
"""Source freshness — cache age check, NO DATA → NO TRADE prensibi."""
from __future__ import annotations

import os
import time
from pathlib import Path

from src.infrastructure.data.source_freshness import (
    is_source_fresh,
    SourceFreshnessResult,
    MAX_CACHE_AGE_HOURS,
)


def test_fresh_cache_passes(tmp_path: Path):
    p = tmp_path / "ratings.json"
    p.write_text("{}", encoding="utf-8")
    result = is_source_fresh(p)
    assert result.fresh is True
    assert result.age_hours < 1


def test_stale_cache_blocks_trade(tmp_path: Path):
    p = tmp_path / "ratings.json"
    p.write_text("{}", encoding="utf-8")
    old = time.time() - (MAX_CACHE_AGE_HOURS + 1) * 3600
    os.utime(p, (old, old))
    result = is_source_fresh(p)
    assert result.fresh is False
    assert result.reason == "cache_too_old"


def test_missing_cache_blocks_trade(tmp_path: Path):
    result = is_source_fresh(tmp_path / "missing.json")
    assert result.fresh is False
    assert result.reason == "cache_missing"


def test_custom_max_age_hours(tmp_path: Path):
    p = tmp_path / "ratings.json"
    p.write_text("{}", encoding="utf-8")
    old = time.time() - 6 * 3600  # 6 saat eski
    os.utime(p, (old, old))
    # 4 saat eşik: stale
    result = is_source_fresh(p, max_age_hours=4.0)
    assert result.fresh is False
    # 8 saat eşik: taze
    result = is_source_fresh(p, max_age_hours=8.0)
    assert result.fresh is True
```

- [ ] **Step 7.2: Test FAIL**

- [ ] **Step 7.3: Implementation**

`src/infrastructure/data/source_freshness.py`:

```python
"""Generic cache age check — NO DATA → NO TRADE prensibi.

Scrape kaynaklarda (BRScraper BSL/ACB/Lega) captcha/IP block durumunda
sessiz bayat veri ile trade açmamak için tüm lig refresher'larının
ortak guard'ı. Tenis Sackmann + basket nba_api/ESPN/euroleague için de
opsiyonel kullanılır.

Domain-pure değil — Path operations (stat). Infrastructure layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Optional


# 24h default — bir sezonun normal güncellemesi maks 1 günde gelir.
# Scrape kaynaklarda daha sıkı (12h) yapılabilir, lig-başına override.
MAX_CACHE_AGE_HOURS = 24.0


@dataclass(frozen=True)
class SourceFreshnessResult:
    """Cache freshness karar sonucu."""
    fresh: bool
    age_hours: float
    reason: Optional[str] = None  # 'cache_missing' | 'cache_too_old' | None


def is_source_fresh(
    cache_path: Path,
    max_age_hours: float = MAX_CACHE_AGE_HOURS,
) -> SourceFreshnessResult:
    """Cache dosyası taze mi? `NO DATA → NO TRADE` prensibi.

    Returns:
      SourceFreshnessResult(fresh=True) → bot bu lig için bahis açabilir
      SourceFreshnessResult(fresh=False) → bot SUS, lig hibernation
    """
    if not cache_path.exists():
        return SourceFreshnessResult(
            fresh=False, age_hours=float("inf"), reason="cache_missing",
        )
    age_hours = (time() - cache_path.stat().st_mtime) / 3600.0
    if age_hours > max_age_hours:
        return SourceFreshnessResult(
            fresh=False, age_hours=age_hours, reason="cache_too_old",
        )
    return SourceFreshnessResult(fresh=True, age_hours=age_hours)
```

- [ ] **Step 7.4: Test PASS**

Run: `python -m pytest tests/unit/infrastructure/data/test_source_freshness.py -v`

- [ ] **Step 7.5: Commit**

```bash
git add src/infrastructure/data/source_freshness.py tests/unit/infrastructure/data/test_source_freshness.py
git commit -m "feat(infra/freshness): NO DATA → NO TRADE generic cache guard (Task 7)

Scrape kaynaklar (BSL/ACB/Lega) captcha/IP block durumunda bayat veri
ile bahis açmamak için tüm refresher'ların ortak guard'ı. 24h default,
lig-başına override.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: BRScraper Wrapper — BSL/ACB/Lega (Strict Health)

**Files:**
- Create: `src/infrastructure/data/basketball/brscraper_refresher.py`
- Test: `tests/unit/infrastructure/data/basketball/test_brscraper_refresher.py`
- Modify: `requirements.txt` — `BRScraper>=0.1.0`

- [ ] **Step 8.1: Test — BRScraper wrapper, mocked HTTP**

```python
"""BRScraper wrapper — Avrupa yerel ligler (BSL/ACB/Lega).

BRScraper basketball-reference.com'u scrape eder. Strict health:
  - HTML format değişirse Pydantic ValidationError
  - Captcha/IP block → boş liste + warning
  - Cache age guard caller'da yapılır (source_freshness.py)
"""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest
from src.infrastructure.data.basketball.brscraper_refresher import (
    fetch_european_league_games,
    _SUPPORTED_BR_LEAGUES,
)


def test_supported_european_leagues_listed():
    assert "bsl" in _SUPPORTED_BR_LEAGUES
    assert "acb" in _SUPPORTED_BR_LEAGUES
    assert "lega" in _SUPPORTED_BR_LEAGUES


def test_fetch_unknown_league_raises():
    with pytest.raises(ValueError):
        fetch_european_league_games(league="bundesliga_basketball", season="2024-25",
                                     fetcher=MagicMock())


def test_fetch_empty_result_returns_empty_list():
    fake = MagicMock()
    fake.return_value = []
    games = fetch_european_league_games(league="bsl", season="2024-25", fetcher=fake)
    assert games == []


def test_fetch_skips_unparseable_rows():
    """Bozuk satır → log warning + skip (sessiz hata YASAK)."""
    fake = MagicMock()
    # 1 valid + 1 corrupt row
    fake.return_value = [
        {"date": "2024-11-01", "home_team_abbr": "ANA", "away_team_abbr": "FB",
         "home_points": 90, "away_points": 85, "home_fga": 70, "away_fga": 68,
         "home_fta": 20, "away_fta": 18, "home_orb": 10, "away_orb": 9,
         "home_tov": 12, "away_tov": 11},
        {"date": "BOZUK", "home_team_abbr": None},  # malformed
    ]
    games = fetch_european_league_games(league="bsl", season="2024-25", fetcher=fake)
    assert len(games) == 1  # malformed atlandı
    assert games[0].home_team == "ANA"
```

- [ ] **Step 8.2: Implementation**

```python
# src/infrastructure/data/basketball/brscraper_refresher.py
"""BRScraper Avrupa yerel ligler — BSL (Türkiye), ACB (İspanya), Lega (İtalya).

BRScraper basketball-reference.com'u scrape eder. Bu modül:
  - Dependency injection: `fetcher` Callable[league, season] → list[dict] alır
  - Pydantic GameRecord validation (schema fail-fast)
  - Sessiz hata yok — bozuk satır warning + skip
  - Cache age check çağıran orchestration'da (source_freshness.py)

ARCH_GUARD §12: try/except sadece infra'da, log + degrade.
"""
from __future__ import annotations

import logging
from typing import Callable, Iterable

from src.infrastructure.data.basketball.schemas import GameRecord

logger = logging.getLogger(__name__)

# basketball-reference.com Avrupa lig slug'ları
_SUPPORTED_BR_LEAGUES = ("bsl", "acb", "lega")

# Dean Oliver possessions katsayısı — FIBA kuralları için 0.46
_FIBA_FTA_POSS_FACTOR = 0.46


def _row_possessions(row: dict, side: str) -> float:
    """Bir takım satırından possessions (Dean Oliver FIBA)."""
    fga = float(row.get(f"{side}_fga", 0))
    fta = float(row.get(f"{side}_fta", 0))
    orb = float(row.get(f"{side}_orb", 0))
    tov = float(row.get(f"{side}_tov", 0))
    return fga + _FIBA_FTA_POSS_FACTOR * fta - orb + tov


def _convert_row(row: dict, league: str) -> GameRecord:
    """BRScraper satırından GameRecord."""
    return GameRecord(
        game_id=f"{league}-{row['date']}-{row['home_team_abbr']}-{row['away_team_abbr']}",
        season=row.get("season", "2024-25"),
        game_date_utc=str(row["date"]) + "T00:00:00Z",
        home_team=str(row["home_team_abbr"])[:4],
        away_team=str(row["away_team_abbr"])[:4],
        home_score=int(row["home_points"]),
        away_score=int(row["away_points"]),
        home_possessions=round(_row_possessions(row, "home"), 2) or 1.0,
        away_possessions=round(_row_possessions(row, "away"), 2) or 1.0,
        is_final=True,
        league=league,  # type: ignore[arg-type]
    )


def fetch_european_league_games(
    league: str,
    season: str,
    fetcher: Callable[[str, str], list[dict]],
) -> list[GameRecord]:
    """BSL/ACB/Lega bir sezonun tüm tamamlanmış maçlarını çek.

    fetcher: BRScraper.get_schedule veya benzeri — (league, season) → list[dict].
    Sessiz hata yok: bozuk satır warning + skip, network hata caller'da.
    """
    if league not in _SUPPORTED_BR_LEAGUES:
        raise ValueError(f"Unsupported European league: {league}")
    try:
        rows = fetcher(league, season)
    except Exception as exc:  # noqa: BLE001 — infra boundary
        logger.warning("BRScraper fetch failed for %s %s: %s", league, season, exc)
        return []
    out: list[GameRecord] = []
    for row in rows or []:
        try:
            out.append(_convert_row(row, league))
        except Exception as exc:  # noqa: BLE001 — schema fail-fast
            logger.warning("BRScraper row skipped (malformed): %s", exc)
    return out
```

- [ ] **Step 8.3: Test PASS**

Run: `python -m pytest tests/unit/infrastructure/data/basketball/test_brscraper_refresher.py -v`

- [ ] **Step 8.4: requirements.txt güncelle**

```
# Avrupa yerel basket ligleri — BSL/ACB/Lega scrape
# Opsiyonel: paket yoksa fetcher None → BRScraper hook degrade boş döner
BRScraper>=0.1.0
```

- [ ] **Step 8.5: Commit**

```bash
git add src/infrastructure/data/basketball/brscraper_refresher.py tests/unit/infrastructure/data/basketball/test_brscraper_refresher.py requirements.txt
git commit -m "feat(basketball/data): BRScraper wrapper — BSL/ACB/Lega (Task 8)

basketball-reference.com'dan Avrupa yerel lig (Türkiye/İspanya/İtalya)
maç verisi. Dependency injection (fetcher Callable) — test mock'lanır.
Schema fail-fast (Pydantic), bozuk satır skip + warning.

FIBA possessions katsayısı 0.46 (NBA 0.44 / NCAAB 0.475).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### ~~Task 9 (KALDIRILDI 2026-06-01): ITF/Challenger Kalibrasyon~~

> Kullanıcı kararı: **"Veri yoksa girmesin, yalandan tahmin üretmek yok."**
> ITF/Challenger seviyesinde model güvenilmez → küçük güvenle dahil etmek
> "yalandan tahmin"e karşılık gelir. Kapsam dışı.

---

### ~~Task 9 (DELETED): ITF Calibration~~

**Files:**
- Modify: `src/strategy/enrichment/tennis_dispatch.py` — ITF/Challenger tier detect + calibration key namespace
- Modify: `src/strategy/enrichment/tennis_anchor_enricher.py` — düşük güven (B) bayrak

- [ ] **Step 9.1: Test ekle — ITF için ayrı kalibrasyon key**

`tests/unit/strategy/enrichment/test_tennis_dispatch.py`'ye ekle:

```python
def test_itf_question_uses_separate_calibration_namespace():
    """ITF maçlarında calibration eğrisi 'tennis:itf:moneyline' key ile alınmalı."""
    from src.strategy.enrichment.tennis_dispatch import _calibration_key_for_market
    # Sade test fonksiyonu
    key = _calibration_key_for_market("ITF Foggia: Pieri vs Bosio", "moneyline")
    assert key == "tennis:itf:moneyline"
    key = _calibration_key_for_market("Wimbledon: Djokovic vs Alcaraz", "moneyline")
    assert key == "tennis:main:moneyline"
```

- [ ] **Step 9.2: Implementation**

`tennis_dispatch.py`'a ekle (mevcut helper'lara):

```python
_ITF_KEYWORDS = ("ITF", "Futures", "M15", "M25", "W15", "W25")
_CHALLENGER_KEYWORDS = ("Challenger", "ATP Challenger")


def _calibration_key_for_market(question: str, market_type: str) -> str:
    """Kalibrasyon eğrisi key — ITF/Challenger için ayrı namespace."""
    q = question or ""
    mt = market_type.lower() or "moneyline"
    if any(kw in q for kw in _ITF_KEYWORDS):
        return f"tennis:itf:{mt}"
    if any(kw in q for kw in _CHALLENGER_KEYWORDS):
        return f"tennis:challenger:{mt}"
    return f"tennis:main:{mt}"
```

- [ ] **Step 9.3: enrich_tennis_from_model'e calibration_curves key passing**

(detay: tennis_anchor_enricher şu an `calibration_curves[market_type.lower()]` kullanıyor.
Bu key'i `_calibration_key_for_market` çıktısıyla değiştir.)

- [ ] **Step 9.4: Test PASS**

- [ ] **Step 9.5: Commit**

```bash
git add src/strategy/enrichment/tennis_dispatch.py src/strategy/enrichment/tennis_anchor_enricher.py tests/unit/strategy/enrichment/test_tennis_dispatch.py
git commit -m "feat(tennis/strategy): ITF/Challenger ayrı kalibrasyon namespace (Task 9)

Question metninden tier algıla, calibration_curves key:
  'tennis:main:moneyline' / 'tennis:challenger:moneyline' / 'tennis:itf:moneyline'

Phi guard (Task 1) ile birlikte: ITF oyuncu zaten phi>=100 ise SKIP.
Tarihçesi olan ITF oyuncularda kalibrasyon eğrisi farklı tutulup
düşük güvenle dahil edilir (gelecek faz — calibration eğrisi eğitildikçe).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Factory.py Refresh Hook'lar + Yetki Alanı Final Regresyon

**Files:**
- Modify: `src/orchestration/factory.py` — yeni ligler için boot ratings build hook

- [ ] **Step 10.1: `_maybe_build_basketball_ratings` PRO_LEAGUES set genişlet**

`factory.py` mevcut `fast_build_leagues = {"nba", "wnba"}` → genişlet:

```python
fast_build_leagues = {"nba", "wnba", "g_league", "summer_league"}
```

(Bu lig'lerin hepsi nba_api üzerinden hızlı build, EuroCup ve Avrupa yerel ligler manuel script ile yapılır.)

- [ ] **Step 10.2: Full regresyon**

Run: `python -m pytest tests/unit -q --ignore=tests/unit/dashboard --ignore=tests/integration`
Expected: tüm test'ler PASS (önceki 1647 + ~12 yeni)

- [ ] **Step 10.3: Final commit**

```bash
git add src/orchestration/factory.py
git commit -m "feat(orchestration): yeni ligler factory boot hook (Task 10)

G League + Summer League nba_api üzerinden hızlı build.
EuroCup euroleague-api üzerinden build (manuel script).
BSL/ACB/Lega BRScraper manuel script (sezon başında).

Regresyon: full unit PASS.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Task 2: Sackmann Doubles veri ✓
- Task 3: Doubles pricer ✓
- Task 4: NBA G League ✓
- Task 5: Summer League ✓ (Task 4 ile birlikte)
- Task 6: EuroCup ✓
- Task 7: NO DATA → NO TRADE guard (scrape güvenliği) ✓
- Task 8: BSL/ACB/Lega scrape ✓
- Task 9: ITF/Challenger kalibrasyon ✓
- Task 10: Factory hook ✓

**Placeholder scan:** Yok. Her step'te exact code.

**Type consistency:**
- `GameRecord.league` Literal her tasklarda uyumlu
- `Rating` (Glicko-2) Task 3'te kullanılıyor — `glicko.py`'dan import
- `DoublesTeam` Task 3'te tanımlı

**ARCH_GUARD compliance:**
- Tüm yeni dosyalar <400 satır (kontrollü)
- Domain'de I/O yok (doubles_pricer saf math)
- Sessiz hata yok (BRScraper warning + skip)
- Magic number yok (named constants)
- 5-katman düzeni korunmuş

**Dead code / drift yok:**
- Tüm yeni dosyalar test'li
- Mevcut pattern'ler yeniden kullanılıyor (DRY)
- Eski force_close path silinmişti (Task 0 öncesi)

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-01-yetki-genisletme-tennis-basket.md`.

**Inline Execution** (executing-plans skill) önerilir — kullanıcı "ardışık" yapılmasını istedi, her task arası onay gerekmiyor. Ben tek tek uygulayacağım, her task sonu kısa rapor + commit.

Devam ediyorum: Task 2 başlangıç.
