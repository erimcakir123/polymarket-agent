# MLB Model Anchor Completion + Sizing Guards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tamamlamak için yarım kalmış MLB submarket model engine'i (team binding, park binding, DH, moneyline pricer, bullpen, Marcel multi-season), ardından bimodal sizing + aynı-tür-event guard kurallarını uygulamak.

**Architecture:** Mevcut engine (`src/strategy/entry/mlb_submarket_engine.py`) Plan 4 simplifications'ı hardcoded içeriyor: "pick first game", "first ballpark", `dh_game=False`. Bunlar düzeltilecek; moneyline pricer eklenip totals/spread pricer pattern'i izlenecek; bullpen segmenter + Marcel weighting devreye alınacak. Sonra config-level bimodal sizing + portfolio-guard same-type kuralı eklenecek. Tüm değişiklikler 5-katman mimaride kalır.

**Tech Stack:** Python 3.12+, pydantic, pytest. Mevcut: StatsApiClient (Stats API), StatcastClient, WeatherClient, RateCache, EntryGate, PortfolioManager.

**Sıra:** A → C → B → D ardışık. Gözlem checkpoint'i yok. Hepsi master branch üzerinde feature branch açılıp uygulanır.

---

## Faz A: Team + Park + DH Binding (kritik 3 simplification)

Engine `process()` şu an `schedule[0]` ile o günün ilk maçını alıyor (yanlış takım) ve `next(iter(ballpark_metadata.values()))` ile sözlüğün ilk park'ını alıyor (yanlış stadyum). DH her zaman 9-inning sayılıyor. Faz A bu üç şeyi düzeltir.

### Task A1: Team Abbreviation → MLB Team ID Lookup

**Files:**
- Create: `src/infrastructure/mlb_data/team_lookup.py`
- Test: `tests/unit/infrastructure/mlb_data/test_team_lookup.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infrastructure/mlb_data/test_team_lookup.py
from src.infrastructure.mlb_data.team_lookup import (
    abbreviation_to_team_id,
    team_id_to_abbreviation,
    TEAM_ABBREVIATIONS,
)


def test_cle_returns_cleveland_id():
    assert abbreviation_to_team_id("cle") == 114


def test_phi_returns_phillies_id():
    assert abbreviation_to_team_id("phi") == 143


def test_uppercase_input_normalized():
    assert abbreviation_to_team_id("CLE") == 114


def test_unknown_returns_none():
    assert abbreviation_to_team_id("zzz") is None


def test_reverse_lookup_phi():
    assert team_id_to_abbreviation(143) == "phi"


def test_reverse_unknown_returns_none():
    assert team_id_to_abbreviation(999) is None


def test_all_30_teams_present():
    assert len(TEAM_ABBREVIATIONS) == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/mlb_data/test_team_lookup.py -v`
Expected: ImportError or FAIL (modülü yok henüz)

- [ ] **Step 3: Write minimal implementation**

```python
# src/infrastructure/mlb_data/team_lookup.py
"""MLB takım kısaltma ↔ Stats API team_id lookup (sabit veri).

Slug formatı (`mlb-cle-phi-2026-05-22-total-9pt5`) takım kısaltmaları kullanır
ama Stats API `get_schedule()` `home_team_id`/`away_team_id` döndürür. Bu modül
çeviri sağlar.
"""
from __future__ import annotations

# Stats API team_id'leri (statsapi.mlb.com/api/v1/teams sportId=1).
# 30 MLB takımı + AL/NL ID'leri (sabit, MLB sayısı 30 yıllardır değişmez).
TEAM_ABBREVIATIONS: dict[str, int] = {
    # AL East
    "bal": 110, "bos": 111, "nyy": 147, "tb": 139, "tor": 141,
    # AL Central
    "cws": 145, "cle": 114, "det": 116, "kc": 118, "min": 142,
    # AL West
    "hou": 117, "laa": 108, "oak": 133, "sea": 136, "tex": 140,
    # NL East
    "atl": 144, "mia": 146, "nym": 121, "phi": 143, "wsh": 120,
    # NL Central
    "chc": 112, "cin": 113, "mil": 158, "pit": 134, "stl": 138,
    # NL West
    "ari": 109, "col": 115, "lad": 119, "sd": 135, "sf": 137,
}

_REVERSE: dict[int, str] = {v: k for k, v in TEAM_ABBREVIATIONS.items()}


def abbreviation_to_team_id(abbr: str) -> int | None:
    """`cle` → 114. Bilinmeyen → None."""
    return TEAM_ABBREVIATIONS.get((abbr or "").lower())


def team_id_to_abbreviation(team_id: int) -> str | None:
    """114 → `cle`. Bilinmeyen → None."""
    return _REVERSE.get(team_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/mlb_data/test_team_lookup.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/mlb_data/team_lookup.py tests/unit/infrastructure/mlb_data/test_team_lookup.py
git commit -m "feat(mlb): team_lookup — abbreviation ↔ Stats API team_id (30 teams)"
```

---

### Task A2: Team ID → Park ID Mapping

**Files:**
- Modify: `src/orchestration/factory.py` (yeni sabit ekleme — etrafı: ~satır 41-74'deki `_DEFAULT_BALLPARK_METADATA`'nın hemen altına)
- Test: `tests/unit/orchestration/test_factory_park_mapping.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_factory_park_mapping.py
from src.orchestration.factory import (
    _DEFAULT_BALLPARK_METADATA,
    TEAM_ID_TO_PARK_ID,
    park_meta_for_team,
)


def test_phillies_maps_to_citizens_bank():
    park_id = TEAM_ID_TO_PARK_ID[143]  # PHI
    assert park_id == "CITIZENS"


def test_guardians_maps_to_progressive():
    park_id = TEAM_ID_TO_PARK_ID[114]  # CLE
    assert park_id == "PROGRESSIVE"


def test_park_meta_for_phi_returns_park_dict():
    meta = park_meta_for_team(143)
    assert meta is not None
    assert "lat" in meta and "lon" in meta and "cf_orientation_deg" in meta


def test_park_meta_unknown_team_returns_none():
    assert park_meta_for_team(99999) is None


def test_all_30_teams_have_park():
    assert len(TEAM_ID_TO_PARK_ID) == 30
    for team_id, park_id in TEAM_ID_TO_PARK_ID.items():
        assert park_id in _DEFAULT_BALLPARK_METADATA, f"park {park_id} missing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestration/test_factory_park_mapping.py -v`
Expected: ImportError on `TEAM_ID_TO_PARK_ID`

- [ ] **Step 3: Implementation — Add to `src/orchestration/factory.py`**

Mevcut `_DEFAULT_BALLPARK_METADATA = {...}` blokunun hemen altına (öğeden sonra, sonraki fonksiyondan önce) ekle:

```python
# Stats API team_id → ballpark_id (factory._DEFAULT_BALLPARK_METADATA anahtarı).
# 2026 sezonu (Athletics Sacramento'ya geçici taşındı 2025-2027, OAK key korunur).
TEAM_ID_TO_PARK_ID: dict[int, str] = {
    110: "CAMDEN",      # Orioles
    111: "FENWAY",      # Red Sox
    147: "YANKEE",      # Yankees
    139: "TROPICANA",   # Rays
    141: "ROGERS",      # Blue Jays
    145: "GUARANTEED",  # White Sox
    114: "PROGRESSIVE", # Guardians
    116: "COMERICA",    # Tigers
    118: "KAUFFMAN",    # Royals
    142: "TARGET",      # Twins
    117: "MINUTE_MAID", # Astros
    108: "ANGEL",       # Angels
    133: "SUTTER",      # Athletics (geçici Sacramento)
    136: "TMOBILE",     # Mariners
    140: "GLOBE_LIFE",  # Rangers
    144: "TRUIST",      # Braves
    146: "LOAN_DEPOT",  # Marlins
    121: "CITI",        # Mets
    143: "CITIZENS",    # Phillies
    120: "NATIONALS",   # Nationals
    112: "WRIGLEY",     # Cubs
    113: "GREAT_AMERICAN", # Reds
    158: "AMERICAN_FAMILY", # Brewers
    134: "PNC",         # Pirates
    138: "BUSCH",       # Cardinals
    109: "CHASE",       # D-backs
    115: "COORS",       # Rockies
    119: "DODGER",      # Dodgers
    135: "PETCO",       # Padres
    137: "ORACLE",      # Giants
}


def park_meta_for_team(team_id: int) -> dict | None:
    """Stats API team_id → ballpark metadata. Bilinmeyen takım → None."""
    park_id = TEAM_ID_TO_PARK_ID.get(team_id)
    if park_id is None:
        return None
    return _DEFAULT_BALLPARK_METADATA.get(park_id)
```

**ÖNEMLI:** `_DEFAULT_BALLPARK_METADATA`'daki park_id anahtarları yukarıdaki listeyle birebir uyumlu olmalı. Bu task uygulanırken o sözlüğün anahtarlarını listele ve eşleşmeyen varsa düzelt (test `test_all_30_teams_have_park` bunu yakalar).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/orchestration/test_factory_park_mapping.py -v`
Expected: 5 passed. Eğer "park X missing" hatası verirse `_DEFAULT_BALLPARK_METADATA` anahtarlarıyla `TEAM_ID_TO_PARK_ID` değerleri uyumla.

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/factory.py tests/unit/orchestration/test_factory_park_mapping.py
git commit -m "feat(mlb): TEAM_ID_TO_PARK_ID — 30 takım stadyum eşlemesi"
```

---

### Task A3: Engine _parse_slug → return team abbreviations

**Files:**
- Modify: `src/strategy/entry/mlb_submarket_engine.py` (satır 247-258, `_parse_slug` metodu)
- Test: `tests/unit/strategy/entry/test_mlb_engine_parse_slug.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/strategy/entry/test_mlb_engine_parse_slug.py
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def test_parse_totals_slug_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-total-8pt5"
    )
    assert result == ("2026-05-22", "totals", 8.5, "cle", "phi")


def test_parse_run_line_neg_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-spread-neg1pt5"
    )
    assert result == ("2026-05-22", "run_line", -1.5, "cle", "phi")


def test_parse_run_line_pos_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-spread-pos1pt5"
    )
    assert result == ("2026-05-22", "run_line", 1.5, "cle", "phi")


def test_parse_unknown_returns_none():
    assert MlbSubmarketEngine._parse_slug_static("nba-okc-sas-2026-05-22") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_parse_slug.py -v`
Expected: AttributeError on `_parse_slug_static` or wrong tuple shape

- [ ] **Step 3: Refactor `_parse_slug` in `src/strategy/entry/mlb_submarket_engine.py`**

Satır 247-258'i (`_parse_slug` metodu) bununla değiştir:

```python
    @staticmethod
    def _parse_slug_static(slug: str) -> tuple[str, str, float, str, str] | None:
        """Parse slug → (date_str, market_type, line, away_abbr, home_abbr).

        Returns None on mismatch.
        """
        m_t = _SLUG_TOTALS_RE.match(slug)
        if m_t:
            away, home, date, n = m_t.groups()
            return date, "totals", float(n) + 0.5, away, home
        m_r = _SLUG_RUN_LINE_RE.match(slug)
        if m_r:
            away, home, date, sign = m_r.groups()
            line = -1.5 if sign == "neg" else 1.5
            return date, "run_line", line, away, home
        return None

    def _parse_slug(self, slug: str) -> tuple[str, str, float, str, str] | None:
        return self._parse_slug_static(slug)
```

Bu, static helper ekler (test edilebilir) + instance method (geriye uyumlu çağrılar için). `process()` içinde satır 92'deki `parsed = self._parse_slug(...)` çağrısını şununla değiştir:

```python
        parsed = self._parse_slug(getattr(market, "slug", "") or "")
        if parsed is None:
            return None
        date_str, market_type, line, away_abbr, home_abbr = parsed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_parse_slug.py -v`
Expected: 4 passed

Mevcut engine integration testleri varsa (`tests/integration/test_mlb_engine_*.py`) kırılmaması için onları da çalıştır:
```
pytest tests/ -k "mlb" -v
```

- [ ] **Step 5: Commit**

```bash
git add src/strategy/entry/mlb_submarket_engine.py tests/unit/strategy/entry/test_mlb_engine_parse_slug.py
git commit -m "refactor(mlb): _parse_slug returns away/home abbreviations"
```

---

### Task A4: process() uses team-matched game

**Files:**
- Modify: `src/strategy/entry/mlb_submarket_engine.py` (satır 103-111, "Plan 4 simplification: pick first game" bloğu)
- Test: `tests/unit/strategy/entry/test_mlb_engine_team_matching.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/strategy/entry/test_mlb_engine_team_matching.py
from unittest.mock import MagicMock
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine
from src.models.market import MarketData
from src.config.settings import MlbSubmarketConfig


def _make_engine(schedule_return):
    statsapi = MagicMock()
    statsapi.get_schedule.return_value = schedule_return
    statsapi.get_lineup.return_value = {"home": [], "away": []}
    engine = MlbSubmarketEngine(
        statsapi=statsapi,
        statcast=MagicMock(),
        weather=MagicMock(),
        rate_cache=MagicMock(),
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata={"FAKE": {"lat": 0, "lon": 0, "cf_orientation_deg": 0, "park_id": "FAKE"}},
    )
    return engine, statsapi


def test_process_picks_game_matching_slug_teams():
    schedule = [
        {"gamePk": 111, "home_team_id": 999, "away_team_id": 999, "status": "Scheduled"},  # wrong teams
        {"gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled"},  # PHI vs CLE
    ]
    engine, statsapi = _make_engine(schedule)
    market = MarketData(condition_id="c1", slug="mlb-cle-phi-2026-05-22-total-8pt5", yes_price=0.5)
    engine.process(market)
    # get_lineup was called with the matched gamePk
    statsapi.get_lineup.assert_called_with(222)


def test_process_returns_none_when_no_team_match():
    schedule = [
        {"gamePk": 111, "home_team_id": 999, "away_team_id": 999, "status": "Scheduled"},
    ]
    engine, statsapi = _make_engine(schedule)
    market = MarketData(condition_id="c1", slug="mlb-cle-phi-2026-05-22-total-8pt5", yes_price=0.5)
    result = engine.process(market)
    assert result is None
    statsapi.get_lineup.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_team_matching.py -v`
Expected: 2 failed (engine currently picks `schedule[0]`)

- [ ] **Step 3: Implementation — replace "pick first game" block**

`src/strategy/entry/mlb_submarket_engine.py` üstündeki importlara ekle:

```python
from src.infrastructure.mlb_data.team_lookup import abbreviation_to_team_id
```

Satır 103-111 ("# Plan 4 simplification: pick first game..." bloğu) şu kodla değiştir:

```python
        # Team matching: schedule içinde slug'ın home/away'i ile eşleşen game
        home_team_id = abbreviation_to_team_id(home_abbr)
        away_team_id = abbreviation_to_team_id(away_abbr)
        if home_team_id is None or away_team_id is None:
            logger.info("mlb_engine: unknown team abbreviation in slug %s/%s",
                        away_abbr, home_abbr)
            return None

        matched = next(
            (g for g in schedule
             if g.get("home_team_id") == home_team_id
             and g.get("away_team_id") == away_team_id),
            None,
        )
        if matched is None:
            logger.info("mlb_engine: no schedule game for %s @ %s on %s",
                        away_abbr, home_abbr, date_str)
            return None

        game = matched
        game_pk = game.get("gamePk")
        if game_pk is None:
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_team_matching.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/strategy/entry/mlb_submarket_engine.py tests/unit/strategy/entry/test_mlb_engine_team_matching.py
git commit -m "fix(mlb): engine picks team-matched schedule game (was: first game)"
```

---

### Task A5: process() uses home-team-bound park

**Files:**
- Modify: `src/strategy/entry/mlb_submarket_engine.py` (satır 181-186, "Plan 4 simplification: first ballpark" bloğu)
- Modify: Engine constructor + `factory.py` — engine ek dependency olarak `team_id_to_park_id` veya `park_meta_for_team` callable alır
- Test: `tests/unit/strategy/entry/test_mlb_engine_park_matching.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/strategy/entry/test_mlb_engine_park_matching.py
from unittest.mock import MagicMock
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine
from src.models.market import MarketData
from src.config.settings import MlbSubmarketConfig


def test_engine_uses_home_team_park_meta():
    statsapi = MagicMock()
    statsapi.get_schedule.return_value = [
        {"gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled"},
    ]
    statsapi.get_lineup.return_value = {"home": [1]*9, "away": [2]*9}
    statsapi.get_probable_pitchers.return_value = {222: {"home_pitcher_id": 50, "away_pitcher_id": 60}}
    statsapi.get_player_handedness.return_value = {"bat_side": "R", "pitch_hand": "R"}

    statcast = MagicMock()
    statcast.get_batter_rates.return_value = {"hr_rate": 0.04}
    statcast.get_pitcher_rates.return_value = {"hr_rate": 0.04}

    rate_cache = MagicMock()
    rate_cache.get.return_value = None
    weather = MagicMock()
    weather.get_conditions.return_value = {"wind_dir_deg": 0, "wind_mph": 0, "temp_f": 70, "humidity_pct": 50}

    ballpark_metadata = {
        "CITIZENS": {"lat": 39.9, "lon": -75.1, "cf_orientation_deg": 0.0, "park_id": "CITIZENS"},
        "PROGRESSIVE": {"lat": 41.4, "lon": -81.6, "cf_orientation_deg": 0.0, "park_id": "PROGRESSIVE"},
    }
    team_id_to_park_id = {143: "CITIZENS", 114: "PROGRESSIVE"}

    engine = MlbSubmarketEngine(
        statsapi=statsapi, statcast=statcast, weather=weather,
        rate_cache=rate_cache,
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata=ballpark_metadata,
        team_id_to_park_id=team_id_to_park_id,
    )

    market = MarketData(condition_id="c1", slug="mlb-cle-phi-2026-05-22-total-8pt5", yes_price=0.5)
    engine.process(market)
    # PHI home → CITIZENS park; weather called with CITIZENS lat/lon
    args = weather.get_conditions.call_args[0]
    assert args[0] == 39.9 and args[1] == -75.1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_park_matching.py -v`
Expected: TypeError on `team_id_to_park_id` kwarg or wrong park selected

- [ ] **Step 3: Implementation — add `team_id_to_park_id` to constructor + use in process()**

`src/strategy/entry/mlb_submarket_engine.py` constructor'a (satır 63-82) parametre ekle:

```python
    def __init__(
        self,
        statsapi: StatsApiClient,
        statcast: StatcastClient,
        weather: WeatherClient,
        rate_cache: RateCache,
        config: MlbSubmarketConfig,
        ballpark_metadata: dict[str, dict[str, Any]],
        team_id_to_park_id: dict[int, str],
        league_rates: dict[str, float] | None = None,
        fixed_bet_usdc: dict[str, float] | None = None,
    ) -> None:
        self.statsapi = statsapi
        self.statcast = statcast
        self.weather = weather
        self.rate_cache = rate_cache
        self.config = config
        self.ballpark_metadata = ballpark_metadata
        self.team_id_to_park_id = team_id_to_park_id
        self.league_rates = league_rates or LEAGUE_PA_RATES
        self.fixed_bet_usdc = fixed_bet_usdc or {"A": 50.0, "B": 30.0}
```

Satır 181-186 ("# Weather — Plan 4 simplification: use first ballpark..." bloğu) şununla değiştir:

```python
        # Park selection: home_team_id → park_id → ballpark_metadata
        park_id = self.team_id_to_park_id.get(home_team_id)
        park_meta = self.ballpark_metadata.get(park_id) if park_id else None
        if park_meta is None:
            logger.info("mlb_engine: no ballpark for home_team_id=%s", home_team_id)
            return None
```

`src/orchestration/factory.py` engine yaratımına `team_id_to_park_id=TEAM_ID_TO_PARK_ID` parametresi ekle (satır 194-202):

```python
    mlb_engine = MlbSubmarketEngine(
        statsapi=statsapi,
        statcast=statcast,
        weather=weather,
        rate_cache=rate_cache,
        config=cfg.mlb_submarket,
        ballpark_metadata=_DEFAULT_BALLPARK_METADATA,
        team_id_to_park_id=TEAM_ID_TO_PARK_ID,
        fixed_bet_usdc=fixed_bet,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_park_matching.py -v`
Expected: 1 passed

Mevcut engine integration testleri çalıştır:
```
pytest tests/ -k "mlb_engine" -v
```
Çalışmıyorlarsa constructor signature değişimine bağlı; mevcut testlerde `team_id_to_park_id={}` veya gerçek mapping ekle.

- [ ] **Step 5: Commit**

```bash
git add src/strategy/entry/mlb_submarket_engine.py src/orchestration/factory.py tests/unit/strategy/entry/test_mlb_engine_park_matching.py
git commit -m "fix(mlb): engine uses home-team-bound ballpark (was: first ballpark)"
```

---

### Task A6: DH (Doubleheader) Detection

**Files:**
- Modify: `src/infrastructure/mlb_data/statsapi_client.py` (`get_schedule` — `gameType` ve `doubleHeader` alanlarını ekle)
- Modify: `src/strategy/entry/mlb_submarket_engine.py` (`process()` içinde `dh_game` belirleme)
- Test: `tests/unit/infrastructure/mlb_data/test_statsapi_doubleheader.py`
- Test: `tests/unit/strategy/entry/test_mlb_engine_dh_detection.py`

**Bağlam:** MLB 2023+ kuralları: çift maçların ikinci oyunu **7 inning DEĞİL, 9 inning** (2023'te geri çevrildi). Ancak yedek alanlarda (rainout makeup veya bazı playoff senaryoları) hâlâ 7 inning olabiliyor. Stats API `gameType` alanı (`"R"` regular, `"D"` doubleheader-second, vb.) ve `doubleHeader` flag'i (`"N"` no, `"S"` traditional, `"Y"` split) sağlar. Faz A'da konservatif yaklaşım: `gameType == "D"` AND `scheduledInnings < 9` → `dh_game=True` (7-inning). Diğer her durumda `dh_game=False`.

- [ ] **Step 1: Write the failing test (statsapi schedule)**

```python
# tests/unit/infrastructure/mlb_data/test_statsapi_doubleheader.py
from unittest.mock import patch, MagicMock
from src.infrastructure.mlb_data.statsapi_client import StatsApiClient


@patch("src.infrastructure.mlb_data.statsapi_client.httpx.Client")
def test_get_schedule_includes_doubleheader_fields(mock_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "dates": [{
            "games": [{
                "gamePk": 222,
                "gameType": "D",
                "scheduledInnings": 7,
                "doubleHeader": "S",
                "status": {"abstractGameState": "Scheduled"},
                "teams": {
                    "home": {"team": {"id": 143}},
                    "away": {"team": {"id": 114}},
                },
            }],
        }],
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.return_value.__enter__.return_value.get.return_value = mock_response

    client = StatsApiClient()
    games = client.get_schedule("2026-05-22")
    assert len(games) == 1
    g = games[0]
    assert g["gamePk"] == 222
    assert g["game_type"] == "D"
    assert g["scheduled_innings"] == 7
    assert g["double_header"] == "S"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/mlb_data/test_statsapi_doubleheader.py -v`
Expected: KeyError on `game_type` (alanlar yok)

- [ ] **Step 3: Implementation — `get_schedule` döndürdüğü her game dict'e 3 alan ekle**

`src/infrastructure/mlb_data/statsapi_client.py` `get_schedule` metodunda, game dict yaratan döngüde (yaklaşık satır 70-86, mevcut yapıya göre) game dict'ine ekle:

```python
                games.append({
                    "gamePk": game.get("gamePk"),
                    "home_team_id": game.get("teams", {}).get("home", {}).get("team", {}).get("id"),
                    "away_team_id": game.get("teams", {}).get("away", {}).get("team", {}).get("id"),
                    "status": game.get("status", {}).get("abstractGameState", ""),
                    "game_type": game.get("gameType", "R"),         # YENİ
                    "scheduled_innings": game.get("scheduledInnings", 9),  # YENİ
                    "double_header": game.get("doubleHeader", "N"),  # YENİ
                })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/mlb_data/test_statsapi_doubleheader.py -v`
Expected: 1 passed

- [ ] **Step 5: Write the engine DH test**

```python
# tests/unit/strategy/entry/test_mlb_engine_dh_detection.py
from unittest.mock import MagicMock, patch
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine
from src.models.market import MarketData
from src.config.settings import MlbSubmarketConfig


def _stub_engine_full(schedule_game):
    statsapi = MagicMock()
    statsapi.get_schedule.return_value = [schedule_game]
    statsapi.get_lineup.return_value = {"home": [1]*9, "away": [2]*9}
    statsapi.get_probable_pitchers.return_value = {
        schedule_game["gamePk"]: {"home_pitcher_id": 50, "away_pitcher_id": 60}
    }
    statsapi.get_player_handedness.return_value = {"bat_side": "R", "pitch_hand": "R"}

    statcast = MagicMock()
    statcast.get_batter_rates.return_value = {"hr_rate": 0.04}
    statcast.get_pitcher_rates.return_value = {"hr_rate": 0.04}

    weather = MagicMock()
    weather.get_conditions.return_value = {"wind_dir_deg": 0, "wind_mph": 0, "temp_f": 70, "humidity_pct": 50}

    return MlbSubmarketEngine(
        statsapi=statsapi, statcast=statcast, weather=weather,
        rate_cache=MagicMock(get=MagicMock(return_value=None)),
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata={"CITIZENS": {"lat": 39.9, "lon": -75.1, "cf_orientation_deg": 0.0, "park_id": "CITIZENS"}},
        team_id_to_park_id={143: "CITIZENS", 114: "CITIZENS"},
    )


@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_dh_7_inning_sets_dh_game_true(mock_sim):
    mock_sim.return_value = ({0: 1.0}, {0: 1.0})
    game = {
        "gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled",
        "game_type": "D", "scheduled_innings": 7, "double_header": "S",
    }
    engine = _stub_engine_full(game)
    market = MarketData(condition_id="c1", slug="mlb-cle-phi-2026-05-22-total-8pt5", yes_price=0.5)
    engine.process(market)
    _, kwargs = mock_sim.call_args
    assert kwargs.get("dh_game") is True


@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_regular_9_inning_sets_dh_game_false(mock_sim):
    mock_sim.return_value = ({0: 1.0}, {0: 1.0})
    game = {
        "gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled",
        "game_type": "R", "scheduled_innings": 9, "double_header": "N",
    }
    engine = _stub_engine_full(game)
    market = MarketData(condition_id="c1", slug="mlb-cle-phi-2026-05-22-total-8pt5", yes_price=0.5)
    engine.process(market)
    _, kwargs = mock_sim.call_args
    assert kwargs.get("dh_game") is False
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_dh_detection.py -v`
Expected: FAIL — `dh_game=False` hardcoded

- [ ] **Step 7: Implementation — DH detection in engine**

`src/strategy/entry/mlb_submarket_engine.py` satır 209-214 (mevcut `simulate_game` çağrısı) bloğunu şununla değiştir:

```python
        # DH detection: gameType "D" + scheduledInnings < 9 → 7-inning DH game.
        # Diğer her durum (regular, makeup, traditional DH game 1, vs.) 9-inning.
        is_dh_7inning = (
            game.get("game_type") == "D"
            and game.get("scheduled_innings", 9) < 9
        )

        # Simulate
        home_dist, away_dist = simulate_game(
            home_per_inning, away_per_inning,
            dh_game=is_dh_7inning,
            mc_iterations=_DEFAULT_MC_ITERATIONS,
            seed=42,
        )
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_dh_detection.py -v`
Expected: 2 passed

- [ ] **Step 9: Commit**

```bash
git add src/infrastructure/mlb_data/statsapi_client.py src/strategy/entry/mlb_submarket_engine.py tests/unit/infrastructure/mlb_data/test_statsapi_doubleheader.py tests/unit/strategy/entry/test_mlb_engine_dh_detection.py
git commit -m "feat(mlb): DH detection (gameType D + 7-inning → dh_game=True)"
```

---

### Task A7: Faz A entegrasyon doğrulama

- [ ] **Step 1: Tüm MLB testlerini çalıştır**

```bash
pytest tests/ -k "mlb" -v
```
Expected: tüm yeşil

- [ ] **Step 2: Full test suite**

```bash
pytest -q
```
Expected: tüm yeşil. Kırılan varsa Faz A değişikliklerinden mi (constructor signature, slug return) kontrol et, gerekirse uyumla.

- [ ] **Step 3: DECISIONS.md kayıt ekle (Faz A tamamlandı)**

`DECISIONS.md` §B (kronolojik SPEC log) en başına:

```markdown
### SPEC-S — MLB Submarket Engine Plan 4 Simplifications Resolved (2026-05-23)

**Karar:** Engine'in 3 kritik simplification'ı kaldırıldı:
1. Team matching: slug'tan home/away abbreviation parse → Stats API team_id ile maç bulma (TEAM_ABBREVIATIONS lookup table)
2. Park binding: home_team_id → park_id (TEAM_ID_TO_PARK_ID) → ballpark_metadata
3. DH detection: gameType "D" + scheduled_innings < 9 → 7-inning sim path

**Sonuç:** Engine artık doğru maç + doğru stadyum + DH'ye duyarlı edge üretir. MLB totals + run-line için model anchor gerçek değer üretmeye başlar.
```

- [ ] **Step 4: Commit**

```bash
git add DECISIONS.md
git commit -m "docs(DECISIONS): SPEC-S — MLB engine Plan 4 simplifications resolved"
```

---

## Faz C: MLB Moneyline Pricer

Engine motoru `home_dist` + `away_dist` (her takımın skor olasılık dağılımı) üretiyor. Moneyline = P(home_runs > away_runs). Mevcut totals/spread pricer pattern'i izlenir.

### Task C1: Moneyline Pricer Domain Module

**Files:**
- Create: `src/domain/mlb_submarket/moneyline_pricer.py`
- Test: `tests/unit/domain/mlb_submarket/test_moneyline_pricer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/domain/mlb_submarket/test_moneyline_pricer.py
import math
from src.domain.mlb_submarket.moneyline_pricer import moneyline_probability


def test_home_certain_winner_returns_1():
    # home always scores 5, away always scores 0
    home_dist = {5: 1.0}
    away_dist = {0: 1.0}
    p_home, p_away = moneyline_probability(home_dist, away_dist)
    assert math.isclose(p_home, 1.0)
    assert math.isclose(p_away, 0.0)


def test_away_certain_winner_returns_1():
    home_dist = {0: 1.0}
    away_dist = {5: 1.0}
    p_home, p_away = moneyline_probability(home_dist, away_dist)
    assert math.isclose(p_home, 0.0)
    assert math.isclose(p_away, 1.0)


def test_tied_distributions_split_50_50():
    # MLB no ties → assume 50/50 on tie (extras determine winner)
    home_dist = {3: 1.0}
    away_dist = {3: 1.0}
    p_home, p_away = moneyline_probability(home_dist, away_dist)
    assert math.isclose(p_home, 0.5)
    assert math.isclose(p_away, 0.5)


def test_mixed_distributions_sum_to_one():
    home_dist = {2: 0.5, 4: 0.5}
    away_dist = {1: 0.3, 3: 0.4, 5: 0.3}
    p_home, p_away = moneyline_probability(home_dist, away_dist)
    assert math.isclose(p_home + p_away, 1.0, abs_tol=1e-9)


def test_known_joint_probabilities():
    # home={2:0.5, 4:0.5}, away={3:1.0}
    # joint: (2,3)→home loses 0.5; (4,3)→home wins 0.5
    home_dist = {2: 0.5, 4: 0.5}
    away_dist = {3: 1.0}
    p_home, p_away = moneyline_probability(home_dist, away_dist)
    assert math.isclose(p_home, 0.5)
    assert math.isclose(p_away, 0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/mlb_submarket/test_moneyline_pricer.py -v`
Expected: ImportError

- [ ] **Step 3: Implementation**

```python
# src/domain/mlb_submarket/moneyline_pricer.py
"""Moneyline pricer — P(home wins) ve P(away wins).

MLB resmi maçlar berabere bitmez (ekstra inning'ler kazananı belirler).
home_dist + away_dist regulation runs (9 veya 7 inning). Ties simulation'da
50/50 olarak dağıtılır — bu basitleştirme, kazananın ekstra inning'lerde
rastgele belirlendiği varsayımına dayanır.

Pattern referansı: totals_pricer.py ve spread_pricer.py.
"""
from __future__ import annotations


def moneyline_probability(
    home_dist: dict[int, float],
    away_dist: dict[int, float],
) -> tuple[float, float]:
    """P(home_wins) ve P(away_wins).

    Args:
        home_dist: {runs: probability} — home team regulation runs.
        away_dist: {runs: probability} — away team regulation runs.

    Returns:
        (p_home, p_away). Toplam 1.0.
    """
    p_home = 0.0
    p_away = 0.0
    for h_runs, h_prob in home_dist.items():
        for a_runs, a_prob in away_dist.items():
            joint = h_prob * a_prob
            if h_runs > a_runs:
                p_home += joint
            elif h_runs < a_runs:
                p_away += joint
            else:
                p_home += joint * 0.5
                p_away += joint * 0.5
    return p_home, p_away
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/mlb_submarket/test_moneyline_pricer.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/domain/mlb_submarket/moneyline_pricer.py tests/unit/domain/mlb_submarket/test_moneyline_pricer.py
git commit -m "feat(mlb): moneyline_pricer — P(home wins) from run distributions"
```

---

### Task C2: Moneyline slug regex + parse branch

**Files:**
- Modify: `src/strategy/entry/mlb_submarket_engine.py` (regex sabitleri + `_parse_slug_static`)
- Test: `tests/unit/strategy/entry/test_mlb_engine_parse_slug.py` (ekleme)

**Bağlam:** MLB moneyline slug formatı: `mlb-{away}-{home}-{YYYY-MM-DD}` (suffix yok). Audit'te `mlb-cle-phi-2026-05-22`, `mlb-tex-laa-2026-05-22` gibi.

- [ ] **Step 1: Test ekle (mevcut dosyaya append)**

```python
# tests/unit/strategy/entry/test_mlb_engine_parse_slug.py (eklenir)
def test_parse_moneyline_slug_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22"
    )
    assert result == ("2026-05-22", "moneyline", 0.0, "cle", "phi")


def test_parse_moneyline_with_dh_suffix_rejected():
    # DH 2'inci maç slug'ı: mlb-cle-phi-2026-05-22-g2 — şu an kapsam dışı
    # Ya da diğer suffix'ler totals/run-line dışında → None
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-foo"
    )
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_parse_slug.py::test_parse_moneyline_slug_returns_teams -v`
Expected: FAIL — `None` döner

- [ ] **Step 3: Implementation — regex + parse branch**

`src/strategy/entry/mlb_submarket_engine.py` satır 43-48 (regex sabitleri) altına ekle:

```python
_SLUG_MONEYLINE_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})$"
)
```

`_parse_slug_static` metodunu şununla değiştir (mevcut totals/run_line dallarına moneyline EN SONRA eklenir, çünkü daha gevşek pattern; totals ve run_line önce eşleşmeli):

```python
    @staticmethod
    def _parse_slug_static(slug: str) -> tuple[str, str, float, str, str] | None:
        """Parse slug → (date_str, market_type, line, away_abbr, home_abbr).

        Sıra önemli: totals/run_line önce eşleşir, moneyline son fallback.
        """
        m_t = _SLUG_TOTALS_RE.match(slug)
        if m_t:
            away, home, date, n = m_t.groups()
            return date, "totals", float(n) + 0.5, away, home
        m_r = _SLUG_RUN_LINE_RE.match(slug)
        if m_r:
            away, home, date, sign = m_r.groups()
            line = -1.5 if sign == "neg" else 1.5
            return date, "run_line", line, away, home
        m_m = _SLUG_MONEYLINE_RE.match(slug)
        if m_m:
            away, home, date = m_m.groups()
            return date, "moneyline", 0.0, away, home
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_parse_slug.py -v`
Expected: 6 passed (yeni 2 + eski 4)

- [ ] **Step 5: Commit**

```bash
git add src/strategy/entry/mlb_submarket_engine.py tests/unit/strategy/entry/test_mlb_engine_parse_slug.py
git commit -m "feat(mlb): _parse_slug accepts moneyline slug"
```

---

### Task C3: Engine process() moneyline branch + adapter passthrough

**Files:**
- Modify: `src/strategy/entry/mlb_submarket_engine.py` (satır ~217-238, market_type dispatch)
- Modify: `src/strategy/entry/mlb_signal_adapter.py` (EdgeCandidate.market_type "moneyline" desteği — direction logic değişebilir)
- Test: `tests/unit/strategy/entry/test_mlb_engine_moneyline.py`

**Bağlam:** Mevcut adapter şöyle (mlb_signal_adapter.py):
```python
direction = Direction.BUY_YES if candidate.edge > 0 else Direction.BUY_NO
```
Bu **totals + run-line** için doğru çünkü `model_p` = P(YES tarafı) ve `edge = model_p - market_p`. Moneyline için de aynı mantık çalışır: model home kazanır diyorsa ve market home YES tarafıysa, edge > 0 → BUY_YES (home wins). Yani adapter'da değişiklik **gerekmez** — sadece market_p ve model_p doğru tarafın olasılığı olmalı.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/strategy/entry/test_mlb_engine_moneyline.py
from unittest.mock import MagicMock, patch
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine
from src.models.market import MarketData
from src.config.settings import MlbSubmarketConfig
from src.models.enums import Direction, EntryReason


def _stub_engine(home_dist, away_dist):
    statsapi = MagicMock()
    statsapi.get_schedule.return_value = [{
        "gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled",
        "game_type": "R", "scheduled_innings": 9, "double_header": "N",
    }]
    statsapi.get_lineup.return_value = {"home": [1]*9, "away": [2]*9}
    statsapi.get_probable_pitchers.return_value = {222: {"home_pitcher_id": 50, "away_pitcher_id": 60}}
    statsapi.get_player_handedness.return_value = {"bat_side": "R", "pitch_hand": "R"}

    statcast = MagicMock()
    statcast.get_batter_rates.return_value = {"hr_rate": 0.04}
    statcast.get_pitcher_rates.return_value = {"hr_rate": 0.04}

    weather = MagicMock()
    weather.get_conditions.return_value = {"wind_dir_deg": 0, "wind_mph": 0, "temp_f": 70, "humidity_pct": 50}

    engine = MlbSubmarketEngine(
        statsapi=statsapi, statcast=statcast, weather=weather,
        rate_cache=MagicMock(get=MagicMock(return_value=None)),
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata={"CITIZENS": {"lat": 39.9, "lon": -75.1, "cf_orientation_deg": 0.0, "park_id": "CITIZENS"}},
        team_id_to_park_id={143: "CITIZENS", 114: "CITIZENS"},
    )
    return engine


@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_moneyline_high_edge_returns_buy_yes_signal(mock_sim):
    # Model: home wins 80% (very lopsided); market: home YES at 60¢
    mock_sim.return_value = ({5: 1.0}, {2: 1.0})  # home certain 5, away certain 2 → P(home)=1.0
    engine = _stub_engine({5: 1.0}, {2: 1.0})
    market = MarketData(
        condition_id="c1", slug="mlb-cle-phi-2026-05-22",
        yes_price=0.60, event_id="e1",
    )
    signal = engine.process(market)
    assert signal is not None
    assert signal.direction == Direction.BUY_YES
    assert signal.entry_reason == EntryReason.MLB_SUBMARKET
    # edge = 1.0 - 0.60 = 0.40 (tier A)
    assert signal.edge >= 0.07


@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_moneyline_low_edge_returns_none(mock_sim):
    # Model: home 50.4%, market 50% → edge 0.004 < min_edge 0.05
    mock_sim.return_value = ({3: 0.504, 2: 0.496}, {2: 1.0})
    engine = _stub_engine(None, None)
    market = MarketData(condition_id="c1", slug="mlb-cle-phi-2026-05-22", yes_price=0.50)
    signal = engine.process(market)
    assert signal is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_moneyline.py -v`
Expected: FAIL — moneyline branch yok

- [ ] **Step 3: Implementation — import + dispatch branch**

`src/strategy/entry/mlb_submarket_engine.py` üstündeki importlara ekle:

```python
from src.domain.mlb_submarket.moneyline_pricer import moneyline_probability
```

Satır 217-223 (market_type dispatch bloğu) şununla değiştir:

```python
        # Price market
        if market_type == "totals":
            p_over, _p_under = totals_probability(home_dist, away_dist, line)
            model_p = p_over  # market YES = over
        elif market_type == "run_line":
            home_line = line  # e.g., -1.5 or +1.5
            p_home, _p_away = spread_probability(home_dist, away_dist, home_line)
            model_p = p_home
        elif market_type == "moneyline":
            p_home, _p_away = moneyline_probability(home_dist, away_dist)
            model_p = p_home  # market YES = home wins (slug format: away-home, YES = home)
        else:
            return None
```

**ÖNEMLI:** Slug `mlb-cle-phi-...` formatında **ilk takım away, ikinci home**. Polymarket condition genelde "Cleveland Guardians vs. Philadelphia Phillies" başlığıyla home YES taraf olarak fiyatlandırır. `model_p = P(home wins)` ve `market_p = yes_price` aynı tarafı temsil eder. Eğer audit verisinden YES tarafının kimin olduğu farklıysa (örn ilk takım = YES), task'ın son commit'inden önce bir manuel doğrulama gerekir (audit'ten 2-3 örneğe bak).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_moneyline.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/strategy/entry/mlb_submarket_engine.py tests/unit/strategy/entry/test_mlb_engine_moneyline.py
git commit -m "feat(mlb): engine process() handles moneyline market_type"
```

---

### Task C4: sport_rules.py — MLB moneyline anchor "model"

**Files:**
- Modify: `src/config/sport_rules.py` (mlb `submarket_anchor` dict — satır 51-54)
- Test: `tests/unit/config/test_sport_rules_anchor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/config/test_sport_rules_anchor.py
from src.config.sport_rules import anchor_source


def test_mlb_moneyline_uses_model_anchor():
    assert anchor_source("mlb", "moneyline") == "model"


def test_mlb_totals_uses_model_anchor():
    assert anchor_source("mlb", "totals") == "model"


def test_mlb_run_line_uses_model_anchor():
    assert anchor_source("mlb", "run_line") == "model"


def test_nba_moneyline_still_bookmaker():
    assert anchor_source("nba", "moneyline") == "bookmaker"


def test_nhl_moneyline_still_bookmaker():
    assert anchor_source("nhl", "moneyline") == "bookmaker"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/config/test_sport_rules_anchor.py -v`
Expected: `test_mlb_moneyline_uses_model_anchor` FAIL (default "bookmaker")

- [ ] **Step 3: Implementation**

`src/config/sport_rules.py` satır 51-54 — `mlb.submarket_anchor` dict'ini güncelle:

```python
    "mlb": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.0,
        "inning_exit": True,
        "inning_exit_deficit": 5,
        "inning_exit_after": 6,
        "score_source": "espn",
        "espn_sport": "baseball",
        "espn_league": "mlb",
        "submarket_anchor": {
            "moneyline": "model",   # YENİ — SPEC-S Faz C
            "totals": "model",
            "run_line": "model",
        },
    },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/config/test_sport_rules_anchor.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/config/sport_rules.py tests/unit/config/test_sport_rules_anchor.py
git commit -m "feat(mlb): moneyline anchor → model (sport_rules dispatch)"
```

---

### Task C5: Faz C entegrasyon doğrulama + Scanner dispatch test

- [ ] **Step 1: Scanner collect_model_signals MLB ML için engine'i çağırıyor mu testle**

```python
# tests/unit/orchestration/test_scanner_mlb_ml_dispatch.py
from unittest.mock import MagicMock
from src.orchestration.scanner import collect_model_signals
from src.models.market import MarketData


def test_mlb_moneyline_dispatched_to_engine():
    engine = MagicMock()
    engine.process.return_value = None
    market = MarketData(
        condition_id="c1", slug="mlb-cle-phi-2026-05-22",
        sport_tag="mlb", sports_market_type="moneyline", yes_price=0.5,
    )
    collect_model_signals(candidates=[market], engine=engine)
    engine.process.assert_called_once_with(market)


def test_nba_moneyline_NOT_dispatched():
    engine = MagicMock()
    market = MarketData(
        condition_id="c1", slug="nba-okc-sas-2026-05-22",
        sport_tag="nba", sports_market_type="moneyline", yes_price=0.5,
    )
    collect_model_signals(candidates=[market], engine=engine)
    engine.process.assert_not_called()
```

Run: `pytest tests/unit/orchestration/test_scanner_mlb_ml_dispatch.py -v`
Expected: 2 passed (no code changes; sport_rules zaten dispatch ediyor)

- [ ] **Step 2: Tüm MLB testlerini çalıştır**

Run: `pytest tests/ -k "mlb" -v`
Expected: tüm yeşil

- [ ] **Step 3: DECISIONS.md güncelle (Faz C tamamlandı)**

§B'deki SPEC-S girişine ek:

```markdown
**Faz C eklemesi (2026-05-23):** MLB moneyline pricer eklendi (`moneyline_pricer.py` — P(home wins) joint distribution'dan), sport_rules `mlb.submarket_anchor.moneyline = "model"`, engine `process()` 3'üncü dal kazandı. MLB ML için artık bookmaker konsensüsü yerine model anchor kullanılır.
```

- [ ] **Step 4: Commit**

```bash
git add DECISIONS.md tests/unit/orchestration/test_scanner_mlb_ml_dispatch.py
git commit -m "docs(DECISIONS): SPEC-S Faz C — MLB moneyline model anchor"
```

---

## Faz B: Doğruluk Artırımları

Engine çalışıyor ama model 6 simplification ile çıktı. A+C'den sonra kalan: **bullpen segmentation** (en yüksek etki) + **Marcel multi-season weighting** (orta etki) + **TTO refinement** (düşük etki). Faz B her birini ardışık yapar.

### Task B1: Bullpen Segmentation Integration

**Files:**
- Modify: `src/strategy/entry/mlb_submarket_engine.py` — `_build_inning_lineups` (satır 278-322); starter sadece ilk N inning, kalan kısımda bullpen segmenter çağırılır
- Modify: Engine constructor — bullpen rates (cache veya statcast'ten) eklenir
- Test: `tests/unit/strategy/entry/test_mlb_engine_bullpen.py`

**Bağlam:** Mevcut `_build_inning_lineups` 9 inning boyunca aynı `pitcher_rates` (starter) kullanıyor. Gerçekte starter ortalama 5.5 inning gider, sonra bullpen geçer. `src/domain/mlb_submarket/bullpen_segmenter.py` var (Plan 2 T14'te yazıldı) ama engine bunu kullanmıyor.

- [ ] **Step 1: Bullpen segmenter API'sini incele**

Aç: `src/domain/mlb_submarket/bullpen_segmenter.py`. İmza muhtemelen şu şekilde:
```python
def segment_bullpen_rates(
    team_id: int,
    rate_cache: RateCache,
    statcast: StatcastClient,
    season: int,
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Returns (low_leverage, medium_leverage, high_leverage) rates."""
```
veya benzeri. Gerçek imzayı kontrol et — sonraki adımlar buna göre düzenle.

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/strategy/entry/test_mlb_engine_bullpen.py
from unittest.mock import MagicMock, patch, ANY
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine
# ... fixtures gibi C3'teki _stub_engine pattern'i


@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_innings_7_8_9_use_bullpen_rates(mock_sim):
    """Starter 1-6 atar, bullpen 7-9 atar — pitcher_rates per-inning farklı."""
    # Bu testi bullpen_segmenter imzasına göre tamamla:
    # - Engine'e bullpen rates inject et (constructor veya factory)
    # - _build_inning_lineups çıktısında 7-9 innings'in pitcher_rates'ı 1-6'dan farklı olduğunu doğrula
    pass  # imza belirlenince doldur
```

**NOT:** Bu task imza-bağımlı; Step 1'de bullpen_segmenter'ın gerçek API'sini gör, sonra test ve implementation'ı net yaz. Implementation'da engine `_build_inning_lineups` döngüsü her inning için doğru tier'ı seçer (örn. inning 1-6 starter, 7 setup, 8 setup, 9 closer).

- [ ] **Step 3: Test fail doğrulama**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_bullpen.py -v`
Expected: FAIL (test placeholder, implement after step 1)

- [ ] **Step 4: Implementation — engine _build_inning_lineups'a bullpen geçişi ekle**

(Detay: bullpen_segmenter çıktısına göre engine `pitcher_rates` parametresini her inning için doğru tier'dan seçer. Constructor'a `bullpen_rates: dict[int, tuple[dict, dict, dict]]` eklenir (team_id → (low, med, high)) veya helper function inject edilir.)

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_bullpen.py -v`

- [ ] **Step 6: Commit**

```bash
git add src/strategy/entry/mlb_submarket_engine.py src/orchestration/factory.py tests/unit/strategy/entry/test_mlb_engine_bullpen.py
git commit -m "feat(mlb): engine wires bullpen segmenter (starter 1-6, bullpen 7-9)"
```

---

### Task B2: Marcel Multi-Season Rate Weighting

**Files:**
- Modify: `src/domain/mlb_submarket/rate_shrinker.py` — Marcel weights ekle (mevcut "current season only" yerine 5/4/3 weight for current/prev/prev-prev)
- Modify: `src/strategy/entry/mlb_submarket_engine.py` `_get_pitcher_rates` ve `_get_batter_rates` — çoklu sezon çağrısı
- Test: `tests/unit/domain/mlb_submarket/test_rate_shrinker_marcel.py`

**Bağlam:** Marcel projeksiyonu (Tom Tango) — sezonu ağırlıklı ortalama: current_year × 5 + prev_year × 4 + prev_prev × 3. Sample size azlığında league mean'e shrink uygulanır (zaten yapılıyor).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/domain/mlb_submarket/test_rate_shrinker_marcel.py
from src.domain.mlb_submarket.rate_shrinker import marcel_weighted_rates


def test_marcel_weights_three_seasons():
    current = {"hr_rate": 0.04, "pa": 600}
    prev = {"hr_rate": 0.03, "pa": 600}
    prev_prev = {"hr_rate": 0.02, "pa": 600}
    result = marcel_weighted_rates(current, prev, prev_prev)
    # weight: 5*600 + 4*600 + 3*600 = 7200 total PA
    # hr: (5*0.04 + 4*0.03 + 3*0.02) * 600 / 7200 = (0.20+0.12+0.06)/12 = 0.038/...
    # weighted hr_rate = (0.04*5*600 + 0.03*4*600 + 0.02*3*600) / 7200
    #                  = (120 + 72 + 36) / 7200 = 228/7200 = 0.0316...
    assert abs(result["hr_rate"] - 0.0316667) < 0.001
    assert result["pa"] == 7200


def test_marcel_missing_prev_seasons_falls_back_to_current():
    current = {"hr_rate": 0.04, "pa": 600}
    result = marcel_weighted_rates(current, {}, {})
    assert result == current


def test_marcel_missing_prev_prev_uses_2_seasons():
    current = {"hr_rate": 0.04, "pa": 600}
    prev = {"hr_rate": 0.03, "pa": 600}
    result = marcel_weighted_rates(current, prev, {})
    # 5*600 + 4*600 = 5400
    # hr: (5*0.04 + 4*0.03) * 600 / 5400 = 0.20+0.12 = 0.32/9 = 0.0356
    assert abs(result["hr_rate"] - 0.0355556) < 0.001
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/mlb_submarket/test_rate_shrinker_marcel.py -v`
Expected: ImportError or AttributeError on `marcel_weighted_rates`

- [ ] **Step 3: Implementation in rate_shrinker.py**

`src/domain/mlb_submarket/rate_shrinker.py` sonuna ekle:

```python
_MARCEL_WEIGHTS = (5, 4, 3)  # current, prev, prev-prev (Marcel 5/4/3)


def marcel_weighted_rates(
    current: dict[str, float],
    prev: dict[str, float],
    prev_prev: dict[str, float],
) -> dict[str, float]:
    """3 sezonun Marcel ağırlıklı ortalaması.

    Ağırlık: current × 5 + prev × 4 + prev_prev × 3 (Marcel).
    Eksik sezon (boş dict) → o ağırlık 0.

    Args:
        current: bu sezon rates (en az 'pa' ve oran alanları)
        prev: önceki sezon
        prev_prev: 2 önceki sezon

    Returns:
        dict: weighted rates + toplam 'pa'.
    """
    seasons = [(current, _MARCEL_WEIGHTS[0]),
               (prev, _MARCEL_WEIGHTS[1]),
               (prev_prev, _MARCEL_WEIGHTS[2])]
    seasons = [(s, w) for s, w in seasons if s.get("pa", 0) > 0]
    if not seasons:
        return current
    if len(seasons) == 1:
        return seasons[0][0]

    total_pa = sum(s.get("pa", 0) * w for s, w in seasons)
    if total_pa == 0:
        return current

    out: dict[str, float] = {}
    rate_keys = {k for s, _ in seasons for k in s.keys() if k != "pa"}
    for key in rate_keys:
        weighted_sum = sum(s.get(key, 0.0) * s.get("pa", 0) * w for s, w in seasons)
        out[key] = weighted_sum / total_pa
    out["pa"] = total_pa
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/mlb_submarket/test_rate_shrinker_marcel.py -v`
Expected: 3 passed

- [ ] **Step 5: Engine wires multi-season**

`src/strategy/entry/mlb_submarket_engine.py` `_get_pitcher_rates` ve `_get_batter_rates` metodlarını şununla değiştir:

```python
    def _get_batter_rates(self, mlbam_id: int, season: int) -> dict[str, float]:
        current = self._rates_for_season(mlbam_id, season, "batter")
        prev = self._rates_for_season(mlbam_id, season - 1, "batter")
        prev_prev = self._rates_for_season(mlbam_id, season - 2, "batter")
        return marcel_weighted_rates(current, prev, prev_prev)

    def _get_pitcher_rates(self, mlbam_id: int, season: int) -> dict[str, float]:
        current = self._rates_for_season(mlbam_id, season, "pitcher")
        prev = self._rates_for_season(mlbam_id, season - 1, "pitcher")
        prev_prev = self._rates_for_season(mlbam_id, season - 2, "pitcher")
        return marcel_weighted_rates(current, prev, prev_prev)

    def _rates_for_season(self, mlbam_id: int, season: int, kind: str) -> dict[str, float]:
        cached = self.rate_cache.get(mlbam_id, season, kind)
        if cached:
            return cached
        if kind == "batter":
            rates = self.statcast.get_batter_rates(mlbam_id, season)
        else:
            rates = self.statcast.get_pitcher_rates(mlbam_id, season)
        if rates:
            self.rate_cache.put(mlbam_id, season, kind, rates)
        return rates or {}
```

Import ekle:
```python
from src.domain.mlb_submarket.rate_shrinker import marcel_weighted_rates
```

- [ ] **Step 6: Engine entegrasyon testi**

```python
# tests/unit/strategy/entry/test_mlb_engine_multiseason.py
from unittest.mock import MagicMock
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine
from src.config.settings import MlbSubmarketConfig


def test_engine_fetches_three_seasons_for_each_player():
    statcast = MagicMock()
    statcast.get_batter_rates.return_value = {"hr_rate": 0.04, "pa": 600}
    statcast.get_pitcher_rates.return_value = {"hr_rate": 0.04, "pa": 600}
    rate_cache = MagicMock()
    rate_cache.get.return_value = None

    engine = MlbSubmarketEngine(
        statsapi=MagicMock(), statcast=statcast, weather=MagicMock(),
        rate_cache=rate_cache,
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata={"FAKE": {"lat": 0, "lon": 0, "cf_orientation_deg": 0, "park_id": "FAKE"}},
        team_id_to_park_id={143: "FAKE"},
    )

    engine._get_batter_rates(1, 2026)
    # 3 sezon × 1 batter call = 3 statcast call
    assert statcast.get_batter_rates.call_count == 3
    calls = [c.args[1] for c in statcast.get_batter_rates.call_args_list]
    assert sorted(calls) == [2024, 2025, 2026]
```

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_multiseason.py -v`
Expected: 1 passed (yeni rate fetch davranışı)

- [ ] **Step 7: Commit**

```bash
git add src/domain/mlb_submarket/rate_shrinker.py src/strategy/entry/mlb_submarket_engine.py tests/unit/domain/mlb_submarket/test_rate_shrinker_marcel.py tests/unit/strategy/entry/test_mlb_engine_multiseason.py
git commit -m "feat(mlb): Marcel 5/4/3 multi-season rate weighting"
```

---

### Task B3: TTO Refinement (PA tracking)

**Files:**
- Modify: `src/strategy/entry/mlb_submarket_engine.py` `_build_inning_lineups` (satır 278-322) — TTO hesabını lineup PA pozisyonuna göre yap
- Test: `tests/unit/strategy/entry/test_mlb_engine_tto.py`

**Bağlam:** Mevcut TTO `min(((inning - 1) // 3) + 1, 4)` — yani 1-3 inning → 1st time, 4-6 → 2nd, 7-9 → 3rd. Bu kaba çünkü gerçekte 1st batter inning 1'de 1st TTO, ama inning 4'te bile leadoff hâlâ 2nd TTO olmayabilir (eğer lineup 1-3'te flip etmediyse). Doğru hesap: cumulative_PA / 9.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/strategy/entry/test_mlb_engine_tto.py
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def test_tto_for_first_batter_inning_1_is_1():
    # 0 önceki PA → TTO 1
    assert MlbSubmarketEngine._tto_for_pa(0) == 1


def test_tto_for_9th_batter_inning_1_is_1():
    # 8 önceki PA → TTO 1
    assert MlbSubmarketEngine._tto_for_pa(8) == 1


def test_tto_for_1st_batter_2nd_loop_is_2():
    # 9 önceki PA → TTO 2 (lineup döndü)
    assert MlbSubmarketEngine._tto_for_pa(9) == 2


def test_tto_caps_at_4():
    # 50 PA → TTO 4 (max)
    assert MlbSubmarketEngine._tto_for_pa(50) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_tto.py -v`
Expected: AttributeError on `_tto_for_pa`

- [ ] **Step 3: Implementation**

`src/strategy/entry/mlb_submarket_engine.py` sınıf içinde statik helper ekle:

```python
    @staticmethod
    def _tto_for_pa(cumulative_pa: int) -> int:
        """Cumulative PA → TTO (1, 2, 3, 4). 9 PA = 1 tur lineup."""
        return min(cumulative_pa // 9 + 1, 4)
```

`_build_inning_lineups` döngüsünü şu şekilde değiştir (cumulative_pa tracking ile):

```python
        innings = []
        cumulative_pa = 0
        for inning in range(1, 10):
            inning_lineup = []
            for batter_idx, (b_rates, b_hand) in enumerate(zip(batter_rates, batter_hands)):
                ctx: PAContext = {
                    "park_id": park_meta.get("park_id", ""),
                    "batter_hand": b_hand,
                    "pitcher_hand": pitcher_hand,
                    "times_through": self._tto_for_pa(cumulative_pa),
                    "wind_mph_to_cf": wind_to_cf,
                    "temp_f": weather["temp_f"],
                    "humidity_pct": weather["humidity_pct"],
                }
                inning_lineup.append(compute_pa_outcome(
                    batter_rates=b_rates,
                    pitcher_rates=pitcher_rates,
                    league_rates=self.league_rates,
                    context=ctx,
                ))
                cumulative_pa += 1
            innings.append(inning_lineup)
        return innings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/strategy/entry/test_mlb_engine_tto.py -v`
Expected: 4 passed

- [ ] **Step 5: Tüm MLB suite + integration**

```bash
pytest tests/ -k "mlb" -v
pytest -q
```
Expected: tüm yeşil

- [ ] **Step 6: Commit**

```bash
git add src/strategy/entry/mlb_submarket_engine.py tests/unit/strategy/entry/test_mlb_engine_tto.py
git commit -m "feat(mlb): TTO uses cumulative PA tracking (was: rough inning estimate)"
```

---

### Task B4: Faz B kapanışı — DECISIONS.md güncelle

- [ ] **Step 1: §B'deki SPEC-S girişine ek**

```markdown
**Faz B eklemesi (2026-05-23):** Doğruluk artırımları tamamlandı: (1) bullpen segmentation engine'e bağlandı, starter 1-6 inning sonra bullpen low/med/high leverage atıcılarına geçilir; (2) Marcel 5/4/3 multi-season weighting devrede — current/prev/prev-prev sezonların PA-weighted ortalaması; (3) TTO artık cumulative PA tracking (lineup turu) ile hesaplanır.
```

- [ ] **Step 2: Commit**

```bash
git add DECISIONS.md
git commit -m "docs(DECISIONS): SPEC-S Faz B — bullpen + Marcel + TTO refinements"
```

---

## Faz D: Bimodal Sizing + Same-Type-Per-Event Guard

Referans spec: `docs/superpowers/specs/2026-05-23-bimodal-and-same-type-guard-design.md`.

### Task D1: Bimodal sizing — config + test güncelleme

**Files:**
- Modify: `config.yaml` (risk.fixed_bet_usdc)
- Modify: `tests/unit/domain/risk/test_position_sizer.py` (mevcut assertion'lar)

- [ ] **Step 1: Mevcut testi güncelle (50→15, 30→10)**

`tests/unit/domain/risk/test_position_sizer.py` satır 10 ve assertion'ları:

```python
FIXED_BET_USDC = {"A": 15.0, "B": 10.0}  # 2026-05-23 bimodal (was A=50, B=30)


def test_A_confidence_returns_fixed_15() -> None:
    assert confidence_position_size("A", fixed_bet_usdc=FIXED_BET_USDC) == 15.0


def test_B_confidence_returns_fixed_10() -> None:
    assert confidence_position_size("B", fixed_bet_usdc=FIXED_BET_USDC) == 10.0
```

(Mevcut `test_A_confidence_returns_fixed_50` ve `test_B_..._30` testlerini bu iki yeni testle değiştir; eski test isimlerini silmeyi unutma.)

- [ ] **Step 2: Run — eski testler fail, yeniler yok**

Run: `pytest tests/unit/domain/risk/test_position_sizer.py -v`
Expected: 2 yeni testlerden 2 PASS (config'den gelmiyor, hardcoded fixture)

- [ ] **Step 3: config.yaml güncelle**

`config.yaml` satır 71-73:

```yaml
risk:
  # SPEC-P (2026-05-21): sabit-tier sizing. Bankroll dalgalanmasından bağımsız.
  # SPEC-S Faz D (2026-05-23): bimodal cap — tüm spor marketleri binary, $15 cap (tennis paritesi).
  fixed_bet_usdc:
    A: 15
    B: 10
```

- [ ] **Step 4: Full test suite — eski 50/30 assertion'lı testler var mı?**

```bash
grep -rn "50.0\|30.0" tests/ | grep -i "fixed_bet\|position_size\|size_usdc"
```

Çıkan her dosya için 50→15, 30→10 güncellemesi yap. Tipik adaylar:
- `tests/unit/strategy/entry/test_gate.py` (sizing assertion'ları)
- `tests/integration/test_*.py` (sizing'i geçen testler)

Her dosya için aynı pattern: assert değerlerini değiştir.

- [ ] **Step 5: Full pytest**

Run: `pytest -q`
Expected: tüm yeşil. Hâlâ kırılan varsa magic number kontrol et.

- [ ] **Step 6: Commit**

```bash
git add config.yaml tests/
git commit -m "feat(risk): bimodal sizing A=15 B=10 (was A=50 B=30) — SPEC-S Faz D"
```

---

### Task D2: portfolio_guards.py — same-type-per-event kontrol

**Files:**
- Modify: `src/orchestration/portfolio_guards.py` (`check_per_market_guards` satır 81-105)
- Test: `tests/unit/orchestration/test_portfolio_guards_same_type.py`

**Bağlam (Explore raporundan):** `_MarketLike` protokolünde `sports_market_type` yok. `MarketData` ve `Position` modellerinde var. Guard'a yeni field eklemek için protokolü genişlet.

- [ ] **Step 1: Mevcut protokolü incele**

Aç: `src/orchestration/portfolio_guards.py`. `_MarketLike` ve `_PortfolioLike` protocol'lerini bul. Genelde:

```python
class _MarketLike(Protocol):
    condition_id: str
    event_id: str | None
    # ekleyeceğiz: sports_market_type: str | SportsMarketType


class _PortfolioLike(Protocol):
    def count_event(self, event_id: str) -> int: ...
    # ekleyeceğiz: def positions_for_event(self, event_id: str) -> list[Position]: ...
```

- [ ] **Step 2: PortfolioManager'a yeni method ekle**

`src/domain/portfolio/manager.py` `PortfolioManager` sınıfına ekle (mevcut `count_event` yanına):

```python
    def positions_for_event(self, event_id: str) -> list[Position]:
        """Bu event_id'ye ait tüm açık pozisyonların listesi."""
        if not event_id:
            return []
        return [p for p in self.positions.values() if p.event_id == event_id]
```

Quick test:

```python
# tests/unit/domain/portfolio/test_manager_event_lookup.py
from src.domain.portfolio.manager import PortfolioManager
from src.models.position import Position


def test_positions_for_event_returns_matching():
    pm = PortfolioManager(initial_bankroll=1000)
    p1 = Position(condition_id="c1", event_id="e1", ...)  # mevcut Position constructor pattern
    p2 = Position(condition_id="c2", event_id="e1", ...)
    p3 = Position(condition_id="c3", event_id="e2", ...)
    pm.positions = {"c1": p1, "c2": p2, "c3": p3}
    assert len(pm.positions_for_event("e1")) == 2
    assert len(pm.positions_for_event("e2")) == 1
    assert pm.positions_for_event("") == []
```

(Position constructor için mevcut testlerden örnek al — alanlar değişebilir.)

Run + commit:
```bash
pytest tests/unit/domain/portfolio/test_manager_event_lookup.py -v
git add src/domain/portfolio/manager.py tests/unit/domain/portfolio/test_manager_event_lookup.py
git commit -m "feat(portfolio): positions_for_event(event_id) helper"
```

- [ ] **Step 3: Same-type guard test yaz**

```python
# tests/unit/orchestration/test_portfolio_guards_same_type.py
from unittest.mock import MagicMock
from src.orchestration.portfolio_guards import check_per_market_guards


def _make_market(condition_id, event_id, sports_market_type):
    m = MagicMock()
    m.condition_id = condition_id
    m.event_id = event_id
    m.sports_market_type = sports_market_type
    return m


def _make_position(sports_market_type):
    p = MagicMock()
    p.sports_market_type = sports_market_type
    return p


def test_second_totals_in_same_event_blocked():
    portfolio = MagicMock()
    portfolio.count_event.return_value = 1
    portfolio.positions_for_event.return_value = [_make_position("totals")]
    blacklist = MagicMock()
    blacklist.is_blacklisted.return_value = False

    market = _make_market("c2", "e1", "totals")
    result = check_per_market_guards(
        market=market, portfolio=portfolio, blacklist=blacklist,
        max_positions_per_event=3,
    )
    assert result is not None
    assert result.reason == "same_market_type_per_event"


def test_different_types_in_same_event_allowed():
    portfolio = MagicMock()
    portfolio.count_event.return_value = 1
    portfolio.positions_for_event.return_value = [_make_position("moneyline")]
    blacklist = MagicMock()
    blacklist.is_blacklisted.return_value = False

    market = _make_market("c2", "e1", "totals")
    result = check_per_market_guards(
        market=market, portfolio=portfolio, blacklist=blacklist,
        max_positions_per_event=3,
    )
    assert result is None


def test_event_cap_still_enforced_at_3_regardless_of_types():
    portfolio = MagicMock()
    portfolio.count_event.return_value = 3
    portfolio.positions_for_event.return_value = [
        _make_position("moneyline"),
        _make_position("totals"),
        _make_position("spreads"),
    ]
    blacklist = MagicMock()
    blacklist.is_blacklisted.return_value = False

    market = _make_market("c4", "e1", "moneyline")
    result = check_per_market_guards(
        market=market, portfolio=portfolio, blacklist=blacklist,
        max_positions_per_event=3,
    )
    assert result is not None
    assert result.reason == "event_already_held"
```

Run: `pytest tests/unit/orchestration/test_portfolio_guards_same_type.py -v`
Expected: 3 fail

- [ ] **Step 4: Implementation — check_per_market_guards genişletme**

`src/orchestration/portfolio_guards.py` `_MarketLike` ve `_PortfolioLike` protokollerine alan/method ekle:

```python
class _MarketLike(Protocol):
    condition_id: str
    event_id: str | None
    sports_market_type: Any  # str or SportsMarketType


class _PortfolioLike(Protocol):
    def count_event(self, event_id: str) -> int: ...
    def positions_for_event(self, event_id: str) -> list: ...
```

`check_per_market_guards` fonksiyonunu genişlet (satır 81-105):

```python
def check_per_market_guards(
    *,
    market: _MarketLike,
    portfolio: _PortfolioLike,
    blacklist: _BlacklistLike,
    max_positions_per_event: int,
) -> GuardSkip | None:
    """Tek market için per-market guard kontrolleri (event_cap + same_type + blacklist)."""
    if market.event_id:
        event_count = portfolio.count_event(market.event_id)
        if event_count >= max_positions_per_event:
            return GuardSkip(
                reason="event_already_held",
                detail=(
                    f"event_id={market.event_id} "
                    f"count={event_count}/{max_positions_per_event}"
                ),
            )
        # SPEC-S Faz D: aynı event'te aynı market_type yasak
        existing = portfolio.positions_for_event(market.event_id)
        market_type = _normalize_market_type(market.sports_market_type)
        same_type = [p for p in existing
                     if _normalize_market_type(p.sports_market_type) == market_type]
        if same_type:
            return GuardSkip(
                reason="same_market_type_per_event",
                detail=f"event_id={market.event_id} type={market_type}",
            )

    if blacklist.is_blacklisted(condition_id=market.condition_id):
        return GuardSkip(reason="blacklisted", detail="match=condition_id")
    if market.event_id and blacklist.is_blacklisted(event_id=market.event_id):
        return GuardSkip(reason="blacklisted", detail="match=event_id")

    return None


def _normalize_market_type(t) -> str:
    """SportsMarketType enum veya str → lowercase str. Boş → ''."""
    if t is None:
        return ""
    if hasattr(t, "value"):
        return str(t.value).lower()
    return str(t).lower()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/orchestration/test_portfolio_guards_same_type.py -v`
Expected: 3 passed

- [ ] **Step 6: Full test suite**

Run: `pytest -q`
Expected: tüm yeşil. Eğer existing testlerde `count_event` mock'u var ama `positions_for_event` yoksa, o testleri güncelle (mock'a method ekle).

- [ ] **Step 7: Commit**

```bash
git add src/orchestration/portfolio_guards.py tests/unit/orchestration/test_portfolio_guards_same_type.py
git commit -m "feat(guards): same_market_type_per_event — aynı event'te aynı tür yasak"
```

---

### Task D3: Dashboard skip-reason help güncelleme

**Files:**
- Modify: `src/presentation/dashboard/static/js/skip_reason_help.js` (yeni skip reason açıklaması)

- [ ] **Step 1: skip_reason_help.js'i incele**

Aç: `src/presentation/dashboard/static/js/skip_reason_help.js`. Mevcut skip reason → human-readable map'i bul.

- [ ] **Step 2: Yeni entry ekle**

```javascript
// Mevcut map'e ekle:
"same_market_type_per_event": "Aynı maçta aynı tür markette zaten pozisyon var (1 ML + 1 totals + 1 spread kuralı)",
```

- [ ] **Step 3: Commit**

```bash
git add src/presentation/dashboard/static/js/skip_reason_help.js
git commit -m "feat(dashboard): same_market_type_per_event skip reason açıklaması"
```

---

### Task D4: Faz D kapanışı — DECISIONS.md güncelle + integration smoke

- [ ] **Step 1: §B'deki SPEC-S girişine ek**

```markdown
**Faz D eklemesi (2026-05-23):** (1) Bimodal sizing A=$15, B=$10 — tüm spor marketleri binary, tek tip sizing cap'i tenis paritesinde. (2) Same-market-type-per-event guard: aynı event_id'de aynı sports_market_type'tan ikinci pozisyon açılamaz. max_positions_per_event=3 kalır ama her biri farklı tür olmalı.
```

- [ ] **Step 2: End-to-end integration smoke**

```bash
pytest tests/integration/ -v
```
Expected: tüm yeşil. Beklenmeyen kırılma → ilgili test'i Faz A/C/D değişikliklerine uyumla.

- [ ] **Step 3: Commit**

```bash
git add DECISIONS.md
git commit -m "docs(DECISIONS): SPEC-S Faz D — bimodal sizing + same-type guard"
```

---

## Faz E: Kapanış + Onaylama

### Task E1: Spec dosyalarını "DONE" durumuna geçir

- [ ] **Step 1: Spec başlığını güncelle**

`docs/superpowers/specs/2026-05-23-bimodal-and-same-type-guard-design.md` üst başlığında:
- "Durum: DRAFT" → "Durum: DONE (2026-05-23)"
- Onaylayan satırına "Erim" ekle.

`docs/superpowers/specs/2026-05-21-mlb-submarket-mainbot-integration-design.md` başlığında:
- "Durum: DRAFT" → "Durum: DONE (Faz A+C+B tamamlandı 2026-05-23)"

- [ ] **Step 2: Plan dosyasını silmek YOK**

CLAUDE.md "kod + test yazıldıktan sonra SPEC.md'den sil" diyor — ancak `docs/superpowers/plans/*` tarihsel kayıt, dokunulmaz. Plan ve spec dosyaları kalır.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/
git commit -m "docs(spec): SPEC-S complete — MLB engine + bimodal/same-type DONE"
```

### Task E2: Memory güncelleme

- [ ] **Step 1: `MEMORY.md`'deki "MLB Submarket Ana Bot Entegrasyonu" satırını güncelle**

Eski:
> MLB Submarket Ana Bot Entegrasyonu — SPEC-R, feature/mlb-submarket branch, Plan 1 done, Plan 2-3-4 sırada

Yeni:
> MLB Submarket Ana Bot Entegrasyonu — SPEC-R DONE 2026-05-23: Plan 4 simplifications çözüldü (team+park+DH binding), moneyline pricer eklendi, bullpen+Marcel+TTO refined. SPEC-S Faz D: bimodal sizing A=$15 B=$10 + same-type-per-event guard.

- [ ] **Step 2: Yeni memory entry — same-type guard**

`feedback_same_type_per_event.md` oluştur:

```markdown
---
name: Aynı Event Aynı Tür Yasağı
description: Aynı maçta aynı sports_market_type'tan birden fazla pozisyon yasak — max 3 farklı tür (ML/totals/spread)
type: feedback
---

Aynı event_id altında aynı sports_market_type'tan ikinci pozisyon açılamaz.

**Why:** 22-23 May UTC+3 gecesi NBA OKC/SAS aynı maçta 2 farklı totals (215.5 + 222.5) açıldı, ikisi de kaybetti -$52. Aynı maç ters giderse korelasyonlu kayıp. Tek maçtan max 3 ama farklı tür olmalı: 1 ML + 1 totals + 1 spread.

**How to apply:** Tüm branş ve liglerde geçerli, sport-bazlı istisna yok. Gate seviyesinde check_per_market_guards içinde uygulanır.
```

`MEMORY.md` index'ine yeni satır:
```
- [Aynı Event Aynı Tür Yasağı](feedback_same_type_per_event.md) — aynı maçta aynı türde max 1 pozisyon, tüm sporlar için
```

- [ ] **Step 3: Commit (memory dosyaları repo dışında, commit gereksiz)**

Memory `C:\Users\erimc\.claude\projects\...` altında, repo dışında. Sadece Write tool kullan.

---

## Doğrulama: 4 Faz Sonu Smoke Test

- [ ] **Step 1: Tüm testler**

```bash
pytest -q
```
Expected: tüm yeşil, kırılan yok

- [ ] **Step 2: Engine canlı smoke (bot dry_run)**

```bash
python scripts/reboot.py reload
# 5-10 dakika bekle
# Dashboard'a bak: MLB markets için skipped_trades reason'ları görmeli (no_edge, lineup_not_posted gibi sağlıklı sebepler)
```

- [ ] **Step 3: Audit kontrol**

5-10 dakika sonra `logs/audit/trade_history.jsonl` yeni MLB submarket trade'leri (totals/run-line/moneyline) var mı? Edge'ler %5-15 aralığında mantıklı mı? Direction (BUY_YES/BUY_NO) slug'a uygun mu?

- [ ] **Step 4: Kullanıcı raporlama**

Kısa rapor:
- Toplam commit sayısı (~25-30)
- Tüm testler yeşil mi (yes/no)
- Engine ilk trade üretti mi (yes/no/observe later)
- Risk: bilinen edge case'ler (DH 2'inci maç slug formatı belirsiz → ileride v3)

---

## Self-Review

**1. Spec coverage:** Her iki spec (2026-05-21 MLB submarket + 2026-05-23 bimodal/same-type) bu plan'da kapsanıyor. Faz A = MLB engine Plan 4 simplifications, Faz C = moneyline pricer (eski spec'in v2 TODO listesi), Faz B = bullpen + Marcel + TTO (yine v2 TODO), Faz D = bimodal + same-type guard (2026-05-23 spec).

**2. Placeholder scan:** Task B1 (bullpen) Step 1'de "bullpen_segmenter API'sini incele" var — burada test ve implementation içeriği imzaya bağımlı, plan'da tam kod yok. Bu bir gap; uygulayan engineer Step 1'de gerçek API'yi okuyup test/impl'i tamamlamalı. Dürüst etiket: bu task **kısmen-detaylı**, engineer kararı gerekir.

**3. Type consistency:**
- `_parse_slug_static` Task A3'te ekleniyor, Task A4, A5, A6, C1, C2'de tutarlı kullanılıyor.
- `team_id_to_park_id` Task A2'de dict olarak tanımlı, A5'te aynı şekilde geçilir.
- `MarketData.sports_market_type` field'ı zaten mevcut (Explore raporu §8).
- `EntryReason.MLB_SUBMARKET` mevcut (Explore raporu §6).

**4. Karar bağımlı**: Task B1 (bullpen) bullpen_segmenter API'sini engineer Step 1'de göreceği için ne yazacağı tam belirlenemedi. Bu task'a iki saat ekstra hazırlama gerekebilir.

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-05-23-mlb-model-completion-and-sizing-guards.md`.

**İki çalıştırma seçeneği:**

1. **Subagent-Driven (önerilen)** — Her task için ayrı subagent dispatch, aralarda review, hızlı iterasyon. Toplam ~25 task / faz başına 4-7 task.

2. **Inline Execution** — Tek session'da batch ve checkpoint'ler. Daha kısa session, daha az context overhead.

**Hangisi?**
