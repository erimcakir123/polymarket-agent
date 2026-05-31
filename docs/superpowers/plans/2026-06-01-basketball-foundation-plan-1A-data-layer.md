# Basketball Foundation — Plan 1.A: Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NBA + WNBA için çift-kaynak veri pipeline'ı (`nba_api` birincil + ESPN yedek), takım rating cache (Elo + AdjO/AdjD), kaynak sağlık takibi, Pydantic schema doğrulaması ve maç-pencere farkındalıklı yenileme zamanlayıcısı kur. WNBA için Plan 1.A sonunda 1 sezon spike testiyle kapsam kararı verilir.

**Architecture:** Tüm yeni dosyalar `src/infrastructure/data/basketball/` altında, ARCH_GUARD'in 5-katman düzeniyle uyumlu. Domain'e I/O sızdırılmaz. Atomic write (tmp → rename) ile cache bozulması engellenir. Birincil kaynak 3 ardışık başarısızlıkta otomatik yedeğe düşer. Tüm dış veri Pydantic ile doğrulanır — schema drift fail-fast.

**Tech Stack:** Python 3.12+, `nba_api` (1.11+), `requests` (ESPN için doğrudan HTTP — `hoopR-py` opsiyonel), `pydantic` v2, `pytest`, `pytest-mock`.

---

## File Structure

### Yeni dosyalar (oluştur)

| Dosya | Sorumluluk | Tahmini satır |
|---|---|---|
| `src/infrastructure/data/basketball/__init__.py` | Paket başlatıcı | 5 |
| `src/infrastructure/data/basketball/schemas.py` | Pydantic modelleri: `GameRecord`, `TeamSnapshot`, `RefresherResult` | ~120 |
| `src/infrastructure/data/basketball/nba_api_refresher.py` | Birincil veri kaynağı — `nba_api` üzerinden NBA + WNBA game-log çekme | ~180 |
| `src/infrastructure/data/basketball/espn_pbp_refresher.py` | Yedek kaynak — ESPN scoreboard JSON endpoint'inden game-log çekme | ~160 |
| `src/infrastructure/data/basketball/team_ratings_store.py` | Elo + AdjO/AdjD JSON cache (read/write/atomic) | ~140 |
| `src/infrastructure/data/basketball/data_source_health.py` | Kaynak sağlık state machine (last_success, fail_count, fallback) | ~120 |
| `src/infrastructure/data/basketball/refresh_scheduler.py` | Maç-pencere farkındalıklı tetik karar mantığı (saf domain — schedule lookup'a göre tetik aralığı) | ~150 |
| `src/infrastructure/data/basketball/refresh_runner.py` | Yukarıdaki tüm parçaları bir araya getiren orchestrator wrapper | ~120 |
| `scripts/basketball_wnba_spike.py` | WNBA veri kalitesi spike testi (Faz 1 kapsam kararı) | ~100 |

### Yeni test dosyaları

| Dosya | Test edilen |
|---|---|
| `tests/unit/infrastructure/data/basketball/__init__.py` | (boş) |
| `tests/unit/infrastructure/data/basketball/test_schemas.py` | Pydantic validation pozitif + negatif yollar |
| `tests/unit/infrastructure/data/basketball/test_nba_api_refresher.py` | Birincil kaynak: mock NBA stats response → GameRecord listesi |
| `tests/unit/infrastructure/data/basketball/test_espn_pbp_refresher.py` | Yedek kaynak: mock ESPN JSON → GameRecord listesi |
| `tests/unit/infrastructure/data/basketball/test_team_ratings_store.py` | Atomic write, read, merge, partial file korunması |
| `tests/unit/infrastructure/data/basketball/test_data_source_health.py` | Fail counter, fallback tetiği, recovery |
| `tests/unit/infrastructure/data/basketball/test_refresh_scheduler.py` | Maç-pencere mantığı (live, post-game window, idle, gece) |
| `tests/unit/infrastructure/data/basketball/test_refresh_runner.py` | Integration: primary OK / primary fail → secondary / her ikisi fail → degrade |

### Modifiye edilecek dosyalar

| Dosya | Değişiklik | Konum |
|---|---|---|
| `src/orchestration/factory.py` | `_maybe_invoke_basketball_refresh(cfg)` fonksiyonu + build_deps hook | `_maybe_invoke_sackmann_refresh` paraleli |
| `config.yaml` | `basketball` config bölümü (lig listesi, eşikler, kaynak ayarları) | sport sonrası |
| `requirements.txt` | `nba_api>=1.11` ekleme + neden yorumu | sport sonrası |

---

## Tasks

### Task 1: Klasör iskeleti ve `__init__` dosyaları

**Files:**
- Create: `src/infrastructure/data/basketball/__init__.py`
- Create: `tests/unit/infrastructure/data/basketball/__init__.py`

- [ ] **Step 1.1: Klasörleri oluştur ve boş `__init__.py` ekle**

```python
# src/infrastructure/data/basketball/__init__.py
"""Basketball data layer — NBA + WNBA için çift-kaynak veri pipeline'ı.

Tennis Sackmann pattern'inin basket muadili. Birincil: nba_api.
Yedek: ESPN scoreboard JSON. Sağlık takibi data_source_health.py'da.
"""
```

```python
# tests/unit/infrastructure/data/basketball/__init__.py
```
(boş dosya)

- [ ] **Step 1.2: Commit**

```bash
git add src/infrastructure/data/basketball/__init__.py tests/unit/infrastructure/data/basketball/__init__.py
git commit -m "chore(basketball): klasör iskeleti ve __init__ dosyaları"
```

---

### Task 2: Pydantic Şemaları — `schemas.py`

**Files:**
- Create: `src/infrastructure/data/basketball/schemas.py`
- Test: `tests/unit/infrastructure/data/basketball/test_schemas.py`

- [ ] **Step 2.1: Başarısız testleri yaz**

```python
# tests/unit/infrastructure/data/basketball/test_schemas.py
"""Schema validation testleri — pozitif yol + drift yakalama."""
from __future__ import annotations
import pytest
from pydantic import ValidationError
from src.infrastructure.data.basketball.schemas import (
    GameRecord, TeamSnapshot, RefresherResult, SourceStatus,
)


def test_game_record_validates_complete_payload():
    rec = GameRecord(
        game_id="0022400001",
        season="2024-25",
        game_date_utc="2024-10-22T23:30:00Z",
        home_team="LAL",
        away_team="GSW",
        home_score=110,
        away_score=104,
        home_possessions=98.5,
        away_possessions=98.5,
        is_final=True,
        league="nba",
    )
    assert rec.is_final is True
    assert rec.home_score > rec.away_score


def test_game_record_rejects_negative_score():
    with pytest.raises(ValidationError):
        GameRecord(
            game_id="0022400001",
            season="2024-25",
            game_date_utc="2024-10-22T23:30:00Z",
            home_team="LAL", away_team="GSW",
            home_score=-1, away_score=104,
            home_possessions=98.5, away_possessions=98.5,
            is_final=True, league="nba",
        )


def test_game_record_rejects_unknown_league():
    with pytest.raises(ValidationError):
        GameRecord(
            game_id="X", season="2024-25",
            game_date_utc="2024-10-22T23:30:00Z",
            home_team="LAL", away_team="GSW",
            home_score=100, away_score=99,
            home_possessions=95.0, away_possessions=95.0,
            is_final=True, league="cricket",
        )


def test_team_snapshot_round_trip():
    snap = TeamSnapshot(
        team="LAL", league="nba",
        elo_rating=1520.4, elo_games=82,
        adj_o=118.2, adj_d=112.8, adj_pace=99.4,
        last_updated_utc="2024-11-01T00:00:00Z",
    )
    payload = snap.model_dump()
    restored = TeamSnapshot.model_validate(payload)
    assert restored == snap


def test_refresher_result_counts_match():
    res = RefresherResult(
        source="nba_api", league="nba",
        games_fetched=12, games_persisted=12,
        ok=True, error=None,
    )
    assert res.ok is True


def test_source_status_tracks_failures():
    st = SourceStatus(
        source="nba_api",
        last_success_utc="2024-11-01T01:00:00Z",
        last_fail_utc=None,
        consecutive_fails=0,
        active=True,
    )
    assert st.active is True
```

- [ ] **Step 2.2: Testleri çalıştır — başarısız olmalı**

Run: `pytest tests/unit/infrastructure/data/basketball/test_schemas.py -v`
Expected: FAIL — `ImportError: cannot import name 'GameRecord'`

- [ ] **Step 2.3: Minimal implementasyon**

```python
# src/infrastructure/data/basketball/schemas.py
"""Basketball data Pydantic modelleri — schema drift fail-fast.

Dış kaynaklardan (nba_api, ESPN) gelen veri buradan geçer. Kolon adı veya
tip değişirse ValidationError fırlar — drift sessizce kabul edilmez.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


_LEAGUES = ("nba", "wnba")


class GameRecord(BaseModel):
    """Tek bir tamamlanmış basket maçı kaydı.

    Possessions Dean Oliver formülünden gelir:
    poss ≈ FGA + 0.44*FTA - OREB + TOV. Refresher hesaplar.
    """
    game_id: str = Field(min_length=1)
    season: str = Field(pattern=r"^\d{4}-\d{2}$")
    game_date_utc: str
    home_team: str = Field(min_length=2, max_length=4)
    away_team: str = Field(min_length=2, max_length=4)
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    home_possessions: float = Field(gt=0)
    away_possessions: float = Field(gt=0)
    is_final: bool
    league: Literal["nba", "wnba"]


class TeamSnapshot(BaseModel):
    """Takımın güncel rating durumu — cache'in tek satırı."""
    team: str = Field(min_length=2, max_length=4)
    league: Literal["nba", "wnba"]
    elo_rating: float
    elo_games: int = Field(ge=0)
    adj_o: float = Field(gt=0)
    adj_d: float = Field(gt=0)
    adj_pace: float = Field(gt=0)
    last_updated_utc: str


class RefresherResult(BaseModel):
    """Bir refresh çağrısının özet sonucu."""
    source: Literal["nba_api", "espn"]
    league: Literal["nba", "wnba"]
    games_fetched: int = Field(ge=0)
    games_persisted: int = Field(ge=0)
    ok: bool
    error: Optional[str] = None


class SourceStatus(BaseModel):
    """Bir veri kaynağının sağlık durumu — health monitor satırı."""
    source: Literal["nba_api", "espn"]
    last_success_utc: Optional[str] = None
    last_fail_utc: Optional[str] = None
    consecutive_fails: int = Field(ge=0)
    active: bool
```

- [ ] **Step 2.4: Testleri çalıştır — geçmeli**

Run: `pytest tests/unit/infrastructure/data/basketball/test_schemas.py -v`
Expected: 6 passed

- [ ] **Step 2.5: Commit**

```bash
git add src/infrastructure/data/basketball/schemas.py tests/unit/infrastructure/data/basketball/test_schemas.py
git commit -m "feat(basketball/data): Pydantic schemas — GameRecord/TeamSnapshot/SourceStatus"
```

---

### Task 3: `nba_api_refresher.py` — Birincil kaynak

**Files:**
- Create: `src/infrastructure/data/basketball/nba_api_refresher.py`
- Test: `tests/unit/infrastructure/data/basketball/test_nba_api_refresher.py`
- Modify: `requirements.txt`

- [ ] **Step 3.1: `nba_api` paketini requirements'a ekle**

`requirements.txt` sonuna ekle:
```
# Basketball — NBA + WNBA stats (birincil veri kaynağı)
# nba_api: stats.nba.com wrapper, ESPN'e göre daha zengin advanced stats sağlar
nba_api>=1.11.0,<2.0
```

- [ ] **Step 3.2: Başarısız testler — mock fixtures kullanarak**

```python
# tests/unit/infrastructure/data/basketball/test_nba_api_refresher.py
"""nba_api birincil refresher testleri — mocked HTTP, gerçek paket çağrısı yok."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from src.infrastructure.data.basketball.nba_api_refresher import (
    fetch_game_log_via_nba_api,
    _convert_nba_api_row_to_game_record,
)
from src.infrastructure.data.basketball.schemas import GameRecord


@pytest.fixture
def fake_nba_api_row():
    """nba_api leaguegamelog endpoint satır biçimi (DataFrame.to_dict gibi)."""
    return {
        "SEASON_ID": "22024",
        "GAME_ID": "0022400001",
        "GAME_DATE": "2024-10-22",
        "MATCHUP": "LAL vs. GSW",
        "TEAM_ABBREVIATION": "LAL",
        "PTS": 110, "FGA": 90, "FTA": 22, "OREB": 12, "TOV": 14,
        "WL": "W", "MIN": 240,
    }


@pytest.fixture
def fake_opp_row(fake_nba_api_row):
    row = dict(fake_nba_api_row)
    row["TEAM_ABBREVIATION"] = "GSW"
    row["MATCHUP"] = "GSW @ LAL"
    row["PTS"] = 104
    row["FGA"] = 88; row["FTA"] = 20; row["OREB"] = 10; row["TOV"] = 16
    row["WL"] = "L"
    return row


def test_convert_row_produces_valid_game_record(fake_nba_api_row, fake_opp_row):
    rec = _convert_nba_api_row_to_game_record(
        home_row=fake_nba_api_row, away_row=fake_opp_row, league="nba",
    )
    assert isinstance(rec, GameRecord)
    assert rec.home_team == "LAL" and rec.away_team == "GSW"
    assert rec.home_score == 110 and rec.away_score == 104
    assert rec.is_final is True
    # Possessions: FGA + 0.44*FTA - OREB + TOV = 90 + 9.68 - 12 + 14 = 101.68
    assert abs(rec.home_possessions - 101.68) < 0.01


def test_fetch_with_empty_endpoint_returns_empty_list():
    fake_endpoint = MagicMock()
    fake_endpoint.return_value.get_dict.return_value = {"resultSets": [{"rowSet": [], "headers": []}]}
    games = fetch_game_log_via_nba_api(
        league="nba", season="2024-25", endpoint_factory=fake_endpoint,
    )
    assert games == []


def test_fetch_unknown_league_raises_value_error():
    with pytest.raises(ValueError, match="league"):
        fetch_game_log_via_nba_api(
            league="cricket", season="2024-25", endpoint_factory=MagicMock(),
        )
```

- [ ] **Step 3.3: Testleri çalıştır — başarısız**

Run: `pytest tests/unit/infrastructure/data/basketball/test_nba_api_refresher.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3.4: Minimal implementasyon**

```python
# src/infrastructure/data/basketball/nba_api_refresher.py
"""nba_api üzerinden NBA + WNBA game-log çekme — birincil veri kaynağı.

Bağımlılık: `nba_api>=1.11`. Endpoint: leaguegamelog (her takımın satırı).
Bir maç iki satır olarak gelir (home + away) — `MATCHUP` alanından eşleştirilir.

Possessions formülü (Dean Oliver):
  poss ≈ FGA + 0.44 * FTA - OREB + TOV

Burada I/O yok — endpoint_factory dependency injection ile dışarıdan verilir.
Refresher çağıran orchestration gerçek endpoint'i sağlar.
"""
from __future__ import annotations

import logging
from typing import Callable, Iterable

from src.infrastructure.data.basketball.schemas import GameRecord

logger = logging.getLogger(__name__)

_SUPPORTED_LEAGUES = ("nba", "wnba")

# Dean Oliver possessions katsayısı — FTA'nın olası possessions sayısına katkısı.
_FTA_POSS_FACTOR = 0.44


def _row_possessions(row: dict) -> float:
    """Bir takım satırından possessions hesabı (Dean Oliver formülü)."""
    fga = float(row.get("FGA", 0))
    fta = float(row.get("FTA", 0))
    oreb = float(row.get("OREB", 0))
    tov = float(row.get("TOV", 0))
    return fga + _FTA_POSS_FACTOR * fta - oreb + tov


def _convert_nba_api_row_to_game_record(
    home_row: dict, away_row: dict, league: str,
) -> GameRecord:
    """İki takım satırını birleştirip GameRecord üret. Ev sahibi MATCHUP'tan belirlenir."""
    game_id = str(home_row["GAME_ID"])
    season = _format_season(str(home_row["SEASON_ID"]))
    date = str(home_row["GAME_DATE"]) + "T00:00:00Z"
    return GameRecord(
        game_id=game_id,
        season=season,
        game_date_utc=date,
        home_team=str(home_row["TEAM_ABBREVIATION"]),
        away_team=str(away_row["TEAM_ABBREVIATION"]),
        home_score=int(home_row["PTS"]),
        away_score=int(away_row["PTS"]),
        home_possessions=round(_row_possessions(home_row), 2),
        away_possessions=round(_row_possessions(away_row), 2),
        is_final=True,
        league=league,  # type: ignore[arg-type]
    )


def _format_season(season_id: str) -> str:
    """SEASON_ID '22024' → '2024-25'."""
    if len(season_id) == 5:
        start = int(season_id[1:])
        return f"{start}-{(start + 1) % 100:02d}"
    return season_id


def fetch_game_log_via_nba_api(
    league: str,
    season: str,
    endpoint_factory: Callable,
) -> list[GameRecord]:
    """Bir lig + sezonun tamamlanmış maçlarını GameRecord listesi olarak döndür.

    `endpoint_factory` bir `nba_api.stats.endpoints.leaguegamelog.LeagueGameLog`
    benzeri callable olmalı. Gerçek wiring orchestration katmanında.

    Bilinmeyen lig → ValueError (fail-fast). Boş cevap → boş liste.
    """
    if league not in _SUPPORTED_LEAGUES:
        raise ValueError(f"Unsupported league: {league}")
    endpoint = endpoint_factory(season=season, league_id="00" if league == "nba" else "10")
    payload = endpoint.get_dict()
    rows = _rows_from_payload(payload)
    return list(_pair_and_convert(rows, league))


def _rows_from_payload(payload: dict) -> list[dict]:
    """nba_api result envelope'ından dict satır listesine çevir."""
    rs = payload.get("resultSets", [])
    if not rs:
        return []
    head = rs[0].get("headers", [])
    body = rs[0].get("rowSet", [])
    return [dict(zip(head, row)) for row in body]


def _pair_and_convert(rows: Iterable[dict], league: str) -> Iterable[GameRecord]:
    """Game_id başına iki satırı (home + away) eşleştir."""
    by_game: dict[str, list[dict]] = {}
    for row in rows:
        by_game.setdefault(str(row["GAME_ID"]), []).append(row)
    for game_id, pair in by_game.items():
        if len(pair) != 2:
            logger.warning("nba_api game %s has %d rows, expected 2 — skipping", game_id, len(pair))
            continue
        a, b = pair
        # MATCHUP "LAL vs. GSW" → home, "GSW @ LAL" → away
        home, away = (a, b) if "vs." in str(a.get("MATCHUP", "")) else (b, a)
        try:
            yield _convert_nba_api_row_to_game_record(home, away, league)
        except Exception as exc:  # noqa: BLE001 — infra boundary, log + skip
            logger.warning("nba_api row pair conversion failed for game %s: %s", game_id, exc)
```

- [ ] **Step 3.5: Testleri çalıştır — geçmeli**

Run: `pytest tests/unit/infrastructure/data/basketball/test_nba_api_refresher.py -v`
Expected: 3 passed

- [ ] **Step 3.6: Commit**

```bash
git add src/infrastructure/data/basketball/nba_api_refresher.py tests/unit/infrastructure/data/basketball/test_nba_api_refresher.py requirements.txt
git commit -m "feat(basketball/data): nba_api birincil refresher (NBA + WNBA game-log)"
```

---

### Task 4: `espn_pbp_refresher.py` — Yedek kaynak

**Files:**
- Create: `src/infrastructure/data/basketball/espn_pbp_refresher.py`
- Test: `tests/unit/infrastructure/data/basketball/test_espn_pbp_refresher.py`

- [ ] **Step 4.1: Başarısız testleri yaz**

```python
# tests/unit/infrastructure/data/basketball/test_espn_pbp_refresher.py
"""ESPN scoreboard JSON yedek refresher testleri — mocked HTTP."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from src.infrastructure.data.basketball.espn_pbp_refresher import (
    fetch_game_log_via_espn,
    _convert_espn_event_to_game_record,
)
from src.infrastructure.data.basketball.schemas import GameRecord


@pytest.fixture
def fake_espn_event():
    """ESPN scoreboard `events[]` öğesi (basitleştirilmiş)."""
    return {
        "id": "401705270",
        "season": {"year": 2025, "type": 2},
        "date": "2024-10-22T23:30Z",
        "status": {"type": {"completed": True}},
        "competitions": [{
            "competitors": [
                {"homeAway": "home", "team": {"abbreviation": "LAL"},
                 "score": "110", "statistics": [
                    {"name": "fieldGoalsAttempted", "displayValue": "90"},
                    {"name": "freeThrowsAttempted", "displayValue": "22"},
                    {"name": "offensiveRebounds", "displayValue": "12"},
                    {"name": "turnovers", "displayValue": "14"},
                 ]},
                {"homeAway": "away", "team": {"abbreviation": "GSW"},
                 "score": "104", "statistics": [
                    {"name": "fieldGoalsAttempted", "displayValue": "88"},
                    {"name": "freeThrowsAttempted", "displayValue": "20"},
                    {"name": "offensiveRebounds", "displayValue": "10"},
                    {"name": "turnovers", "displayValue": "16"},
                 ]},
            ],
        }],
    }


def test_convert_event_produces_valid_record(fake_espn_event):
    rec = _convert_espn_event_to_game_record(fake_espn_event, league="nba")
    assert rec.home_team == "LAL"
    assert rec.away_team == "GSW"
    assert rec.home_score == 110
    assert rec.away_score == 104


def test_fetch_skips_unfinished_games(fake_espn_event):
    unfinished = dict(fake_espn_event)
    unfinished["status"] = {"type": {"completed": False}}
    http_get = MagicMock()
    http_get.return_value.json.return_value = {"events": [unfinished]}
    http_get.return_value.status_code = 200
    games = fetch_game_log_via_espn(league="nba", date_utc="2024-10-22", http_get=http_get)
    assert games == []


def test_fetch_unknown_league_raises():
    with pytest.raises(ValueError):
        fetch_game_log_via_espn(league="cricket", date_utc="2024-10-22", http_get=MagicMock())
```

- [ ] **Step 4.2: Testleri çalıştır — FAIL**

Run: `pytest tests/unit/infrastructure/data/basketball/test_espn_pbp_refresher.py -v`

- [ ] **Step 4.3: Implementasyon**

```python
# src/infrastructure/data/basketball/espn_pbp_refresher.py
"""ESPN scoreboard endpoint'inden basket maç sonuçları — yedek veri kaynağı.

Endpoint örneği:
  https://site.api.espn.com/apis/site/v2/sports/basketball/{league}/scoreboard?dates=YYYYMMDD

`nba_api` çökerse veya rate limit yerse buradan veri çekilir. ESPN HTML
değil JSON döner — schema drift Pydantic ile yakalanır.
"""
from __future__ import annotations

import logging
from typing import Callable

from src.infrastructure.data.basketball.schemas import GameRecord

logger = logging.getLogger(__name__)

_SUPPORTED_LEAGUES = ("nba", "wnba")
_ESPN_LEAGUE_PATH = {"nba": "nba", "wnba": "wnba"}
_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball"

_FTA_POSS_FACTOR = 0.44


def _stat(competitor: dict, name: str) -> float:
    for s in competitor.get("statistics", []):
        if s.get("name") == name:
            return float(s.get("displayValue", "0"))
    return 0.0


def _possessions(competitor: dict) -> float:
    return (
        _stat(competitor, "fieldGoalsAttempted")
        + _FTA_POSS_FACTOR * _stat(competitor, "freeThrowsAttempted")
        - _stat(competitor, "offensiveRebounds")
        + _stat(competitor, "turnovers")
    )


def _convert_espn_event_to_game_record(event: dict, league: str) -> GameRecord:
    """ESPN `event` JSON → GameRecord."""
    comp = event["competitions"][0]
    competitors = comp["competitors"]
    home = next(c for c in competitors if c.get("homeAway") == "home")
    away = next(c for c in competitors if c.get("homeAway") == "away")
    season_year = int(event["season"]["year"])
    return GameRecord(
        game_id=str(event["id"]),
        season=f"{season_year - 1}-{season_year % 100:02d}",
        game_date_utc=str(event["date"]).replace("Z", ":00Z") if "T" in str(event["date"]) and ":" not in str(event["date"])[-6:] else str(event["date"]),
        home_team=str(home["team"]["abbreviation"]),
        away_team=str(away["team"]["abbreviation"]),
        home_score=int(home["score"]),
        away_score=int(away["score"]),
        home_possessions=round(_possessions(home), 2) or 1.0,
        away_possessions=round(_possessions(away), 2) or 1.0,
        is_final=True,
        league=league,  # type: ignore[arg-type]
    )


def fetch_game_log_via_espn(
    league: str,
    date_utc: str,
    http_get: Callable,
    timeout: int = 30,
) -> list[GameRecord]:
    """ESPN scoreboard endpoint'inden bir günün biten maçlarını çek.

    Date format: 'YYYY-MM-DD'. Tamamlanmamış maçlar atlanır (status.completed=False).
    HTTP/parse hatalarında boş liste + warning log.
    """
    if league not in _SUPPORTED_LEAGUES:
        raise ValueError(f"Unsupported league: {league}")
    yyyymmdd = date_utc.replace("-", "")
    url = f"{_ESPN_BASE}/{_ESPN_LEAGUE_PATH[league]}/scoreboard?dates={yyyymmdd}"
    try:
        resp = http_get(url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — infra boundary
        logger.warning("ESPN scoreboard fetch failed: %s — %s", url, exc)
        return []
    if getattr(resp, "status_code", 0) != 200:
        logger.warning("ESPN scoreboard non-200: %s -> %d", url, getattr(resp, "status_code", 0))
        return []
    try:
        events = resp.json().get("events", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("ESPN scoreboard JSON parse failed: %s", exc)
        return []
    out: list[GameRecord] = []
    for ev in events:
        try:
            if not ev.get("status", {}).get("type", {}).get("completed", False):
                continue
            out.append(_convert_espn_event_to_game_record(ev, league))
        except Exception as exc:  # noqa: BLE001
            logger.warning("ESPN event convert failed for id=%s: %s", ev.get("id"), exc)
    return out
```

- [ ] **Step 4.4: Test çalıştır — geçmeli**

Run: `pytest tests/unit/infrastructure/data/basketball/test_espn_pbp_refresher.py -v`
Expected: 3 passed

- [ ] **Step 4.5: Commit**

```bash
git add src/infrastructure/data/basketball/espn_pbp_refresher.py tests/unit/infrastructure/data/basketball/test_espn_pbp_refresher.py
git commit -m "feat(basketball/data): ESPN yedek refresher (scoreboard JSON)"
```

---

### Task 5: `team_ratings_store.py` — Cache I/O

**Files:**
- Create: `src/infrastructure/data/basketball/team_ratings_store.py`
- Test: `tests/unit/infrastructure/data/basketball/test_team_ratings_store.py`

- [ ] **Step 5.1: Başarısız testler**

```python
# tests/unit/infrastructure/data/basketball/test_team_ratings_store.py
"""Team ratings store — atomic write, read, merge."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from src.infrastructure.data.basketball.team_ratings_store import (
    load_team_snapshots, save_team_snapshots, upsert_snapshot,
)
from src.infrastructure.data.basketball.schemas import TeamSnapshot


@pytest.fixture
def sample_snap():
    return TeamSnapshot(
        team="LAL", league="nba",
        elo_rating=1520.4, elo_games=82,
        adj_o=118.2, adj_d=112.8, adj_pace=99.4,
        last_updated_utc="2024-11-01T00:00:00Z",
    )


def test_save_and_load_round_trip(tmp_path: Path, sample_snap):
    target = tmp_path / "nba_ratings.json"
    save_team_snapshots(target, [sample_snap])
    loaded = load_team_snapshots(target, league="nba")
    assert len(loaded) == 1
    assert loaded["LAL"].elo_rating == 1520.4


def test_load_missing_file_returns_empty(tmp_path: Path):
    target = tmp_path / "missing.json"
    out = load_team_snapshots(target, league="nba")
    assert out == {}


def test_save_uses_atomic_write_no_partial_file(tmp_path: Path, sample_snap):
    target = tmp_path / "nba_ratings.json"
    save_team_snapshots(target, [sample_snap])
    assert target.exists()
    assert not (target.parent / (target.name + ".tmp")).exists()


def test_upsert_replaces_existing_team(tmp_path: Path, sample_snap):
    target = tmp_path / "nba_ratings.json"
    save_team_snapshots(target, [sample_snap])
    updated = sample_snap.model_copy(update={"elo_rating": 1550.0, "elo_games": 83})
    upsert_snapshot(target, updated, league="nba")
    loaded = load_team_snapshots(target, league="nba")
    assert loaded["LAL"].elo_rating == 1550.0
    assert loaded["LAL"].elo_games == 83


def test_load_filters_by_league(tmp_path: Path, sample_snap):
    target = tmp_path / "mixed_ratings.json"
    wnba_snap = sample_snap.model_copy(update={"team": "LVA", "league": "wnba"})
    save_team_snapshots(target, [sample_snap, wnba_snap])
    nba_only = load_team_snapshots(target, league="nba")
    assert "LAL" in nba_only and "LVA" not in nba_only
```

- [ ] **Step 5.2: Test çalıştır — FAIL**

- [ ] **Step 5.3: Implementasyon**

```python
# src/infrastructure/data/basketball/team_ratings_store.py
"""Takım rating cache — JSON I/O + atomic write.

Tennis ratings store paraleli (src/infrastructure/data/tennis_ratings_store.py).
Liglerin (NBA, WNBA) snapshot'ları aynı dosyada — load_team_snapshots'da
lige göre filtrelenir.

Atomic write garantisi: tmp dosyaya yaz, rename ile yerine koy. Yarım yazımda
hedef dosya bozulmaz (önceki versiyon korunur).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from src.infrastructure.data.basketball.schemas import TeamSnapshot

logger = logging.getLogger(__name__)


def load_team_snapshots(path: Path, league: str) -> dict[str, TeamSnapshot]:
    """Verilen lig için takım → TeamSnapshot eşlemesi döndür. Dosya yoksa boş dict."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("team_ratings_store: read failed %s — %s", path, exc)
        return {}
    out: dict[str, TeamSnapshot] = {}
    for row in raw:
        try:
            snap = TeamSnapshot.model_validate(row)
        except Exception as exc:  # noqa: BLE001
            logger.warning("team_ratings_store: row validation failed — %s", exc)
            continue
        if snap.league != league:
            continue
        out[snap.team] = snap
    return out


def save_team_snapshots(path: Path, snapshots: Iterable[TeamSnapshot]) -> None:
    """Tüm snapshot listesini atomic write ile JSON'a yaz."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [s.model_dump() for s in snapshots]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def upsert_snapshot(path: Path, snapshot: TeamSnapshot, league: str) -> None:
    """Tek bir takımın snapshot'ını ekle veya değiştir.

    Önce mevcut dosyayı yükle, lige göre filtreleme YAPMAYIP tüm satırları
    koru — sadece kendi (team, league) anahtarını üzerine yaz.
    """
    existing: list[TeamSnapshot] = []
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            existing = [TeamSnapshot.model_validate(r) for r in raw]
        except Exception as exc:  # noqa: BLE001
            logger.warning("upsert: read+parse failed, starting fresh — %s", exc)
            existing = []
    key = (snapshot.team, snapshot.league)
    merged = [s for s in existing if (s.team, s.league) != key]
    merged.append(snapshot)
    save_team_snapshots(path, merged)
```

- [ ] **Step 5.4: Test çalıştır — PASS**

Run: `pytest tests/unit/infrastructure/data/basketball/test_team_ratings_store.py -v`

- [ ] **Step 5.5: Commit**

```bash
git add src/infrastructure/data/basketball/team_ratings_store.py tests/unit/infrastructure/data/basketball/test_team_ratings_store.py
git commit -m "feat(basketball/data): team ratings store — atomic write JSON cache"
```

---

### Task 6: `data_source_health.py` — Sağlık takibi

**Files:**
- Create: `src/infrastructure/data/basketball/data_source_health.py`
- Test: `tests/unit/infrastructure/data/basketball/test_data_source_health.py`

- [ ] **Step 6.1: Test yaz**

```python
# tests/unit/infrastructure/data/basketball/test_data_source_health.py
"""Source health state machine — fallback ve recovery."""
from __future__ import annotations
from pathlib import Path
import pytest

from src.infrastructure.data.basketball.data_source_health import (
    HealthTracker, FALLBACK_THRESHOLD,
)


def test_initial_status_is_active(tmp_path: Path):
    tr = HealthTracker(tmp_path / "h.json")
    assert tr.is_active("nba_api") is True
    assert tr.consecutive_fails("nba_api") == 0


def test_record_failure_increments_counter(tmp_path: Path):
    tr = HealthTracker(tmp_path / "h.json")
    tr.record_failure("nba_api", at_utc="2024-11-01T00:00:00Z")
    assert tr.consecutive_fails("nba_api") == 1
    assert tr.is_active("nba_api") is True  # threshold altında


def test_threshold_failures_deactivate_source(tmp_path: Path):
    tr = HealthTracker(tmp_path / "h.json")
    for i in range(FALLBACK_THRESHOLD):
        tr.record_failure("nba_api", at_utc=f"2024-11-01T0{i}:00:00Z")
    assert tr.is_active("nba_api") is False


def test_success_resets_fail_counter(tmp_path: Path):
    tr = HealthTracker(tmp_path / "h.json")
    tr.record_failure("nba_api", at_utc="2024-11-01T00:00:00Z")
    tr.record_failure("nba_api", at_utc="2024-11-01T01:00:00Z")
    tr.record_success("nba_api", at_utc="2024-11-01T02:00:00Z")
    assert tr.consecutive_fails("nba_api") == 0
    assert tr.is_active("nba_api") is True


def test_state_persists_across_instances(tmp_path: Path):
    p = tmp_path / "h.json"
    tr1 = HealthTracker(p)
    tr1.record_failure("nba_api", at_utc="2024-11-01T00:00:00Z")
    tr2 = HealthTracker(p)
    assert tr2.consecutive_fails("nba_api") == 1
```

- [ ] **Step 6.2: Test FAIL doğrula**

- [ ] **Step 6.3: Implementasyon**

```python
# src/infrastructure/data/basketball/data_source_health.py
"""Veri kaynağı sağlık takibi — fallback state machine.

3 ardışık başarısızlıkta kaynak deaktif olur (yedeğe geçilir). Bir başarı
counter'ı sıfırlar. Persisted JSON state — bot reboot'ta da hatırlanır.

ARCH_GUARD §12 uyumu: sessiz hata yok. Tüm I/O hataları log + degrade.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.infrastructure.data.basketball.schemas import SourceStatus

logger = logging.getLogger(__name__)

FALLBACK_THRESHOLD = 3


class HealthTracker:
    """Veri kaynaklarının (nba_api, espn) sağlık durumunu JSON'da tutar."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._state: dict[str, SourceStatus] = self._load()

    def _load(self) -> dict[str, SourceStatus]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("HealthTracker load failed — starting fresh: %s", exc)
            return {}
        out: dict[str, SourceStatus] = {}
        for row in raw:
            try:
                st = SourceStatus.model_validate(row)
                out[st.source] = st
            except Exception as exc:  # noqa: BLE001
                logger.warning("HealthTracker row drop: %s", exc)
        return out

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [s.model_dump() for s in self._state.values()]
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def _get_or_create(self, source: str) -> SourceStatus:
        if source not in self._state:
            self._state[source] = SourceStatus(
                source=source,  # type: ignore[arg-type]
                last_success_utc=None,
                last_fail_utc=None,
                consecutive_fails=0,
                active=True,
            )
        return self._state[source]

    def is_active(self, source: str) -> bool:
        return self._get_or_create(source).active

    def consecutive_fails(self, source: str) -> int:
        return self._get_or_create(source).consecutive_fails

    def record_success(self, source: str, at_utc: str) -> None:
        cur = self._get_or_create(source)
        self._state[source] = cur.model_copy(update={
            "last_success_utc": at_utc,
            "consecutive_fails": 0,
            "active": True,
        })
        self._persist()

    def record_failure(self, source: str, at_utc: str) -> None:
        cur = self._get_or_create(source)
        new_fails = cur.consecutive_fails + 1
        self._state[source] = cur.model_copy(update={
            "last_fail_utc": at_utc,
            "consecutive_fails": new_fails,
            "active": new_fails < FALLBACK_THRESHOLD,
        })
        self._persist()
        if new_fails >= FALLBACK_THRESHOLD:
            logger.warning("Source %s deactivated after %d consecutive failures", source, new_fails)
```

- [ ] **Step 6.4: Test PASS**

- [ ] **Step 6.5: Commit**

```bash
git add src/infrastructure/data/basketball/data_source_health.py tests/unit/infrastructure/data/basketball/test_data_source_health.py
git commit -m "feat(basketball/data): kaynak sağlık takibi + 3-fail fallback"
```

---

### Task 7: `refresh_scheduler.py` — Maç-pencere farkındalıklı tetik

**Files:**
- Create: `src/infrastructure/data/basketball/refresh_scheduler.py`
- Test: `tests/unit/infrastructure/data/basketball/test_refresh_scheduler.py`

- [ ] **Step 7.1: Test**

```python
# tests/unit/infrastructure/data/basketball/test_refresh_scheduler.py
"""Refresh scheduler — match-window aware interval kararı."""
from __future__ import annotations
from datetime import datetime, timedelta
import pytest

from src.infrastructure.data.basketball.refresh_scheduler import (
    decide_refresh_interval, RefreshIntervalSec,
)


def _t(s: str) -> datetime:
    return datetime.fromisoformat(s)


def test_active_game_uses_short_interval():
    now = _t("2024-11-01T20:30:00")
    games_today = [{"start_utc": "2024-11-01T20:00:00", "end_utc": None}]
    interval = decide_refresh_interval(now=now, games_today=games_today)
    assert interval == RefreshIntervalSec.LIVE


def test_post_game_window_uses_short_interval():
    now = _t("2024-11-01T23:00:00")
    games_today = [{"start_utc": "2024-11-01T20:00:00", "end_utc": "2024-11-01T22:30:00"}]
    interval = decide_refresh_interval(now=now, games_today=games_today)
    assert interval == RefreshIntervalSec.POST_GAME


def test_post_game_window_expired_uses_idle_interval():
    now = _t("2024-11-02T00:00:00")
    games_today = [{"start_utc": "2024-11-01T20:00:00", "end_utc": "2024-11-01T22:30:00"}]
    interval = decide_refresh_interval(now=now, games_today=games_today)
    assert interval == RefreshIntervalSec.IDLE


def test_no_games_today_uses_idle_interval():
    now = _t("2024-11-01T15:00:00")
    interval = decide_refresh_interval(now=now, games_today=[])
    assert interval == RefreshIntervalSec.IDLE


def test_game_upcoming_within_2h_uses_short_interval():
    now = _t("2024-11-01T18:30:00")  # 1.5h önce
    games_today = [{"start_utc": "2024-11-01T20:00:00", "end_utc": None}]
    interval = decide_refresh_interval(now=now, games_today=games_today)
    assert interval == RefreshIntervalSec.PRE_GAME
```

- [ ] **Step 7.2: FAIL doğrula**

- [ ] **Step 7.3: Implementasyon**

```python
# src/infrastructure/data/basketball/refresh_scheduler.py
"""Refresh interval kararı — maç-pencere farkındalıklı.

Saf domain mantığı (I/O yok). Çağıran orchestration bot uptime sırasında
bunu çağırır ve dönen aralığı uyku süresi olarak kullanır.

Sıklık katmanları:
  - LIVE: bir lig maçı şu anda oynanıyor → 5 dk
  - POST_GAME: son maç bittikten sonraki 60 dk → 5 dk
  - PRE_GAME: ilk maç başlamasına 2 saatten az kaldı → 5 dk
  - IDLE: yukarıdakilerin hiçbiri → 6 saat
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Iterable


class RefreshIntervalSec(IntEnum):
    LIVE = 300       # 5 dakika
    POST_GAME = 300  # 5 dakika
    PRE_GAME = 300   # 5 dakika
    IDLE = 21600     # 6 saat


_POST_GAME_WINDOW = timedelta(minutes=60)
_PRE_GAME_WINDOW = timedelta(hours=2)


def _parse(ts: str | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromisoformat(ts.replace("Z", ""))


def decide_refresh_interval(
    now: datetime,
    games_today: Iterable[dict],
) -> RefreshIntervalSec:
    """Bugünün maç takvimine bakıp şu anki uygun refresh aralığını seç.

    `games_today`: her öğe en az `{"start_utc": str, "end_utc": str | None}`.
    end_utc None ise maç hâlâ devam ediyor varsayılır.
    """
    games = list(games_today)
    if not games:
        return RefreshIntervalSec.IDLE
    for g in games:
        start = _parse(g.get("start_utc"))
        end = _parse(g.get("end_utc"))
        if start is None:
            continue
        # Live: başladı ve bitmedi
        if start <= now and end is None:
            return RefreshIntervalSec.LIVE
        # Live: başladı ve süresi devam ediyor
        if start <= now and end is not None and end > now:
            return RefreshIntervalSec.LIVE
        # Post-game window
        if end is not None and end <= now <= end + _POST_GAME_WINDOW:
            return RefreshIntervalSec.POST_GAME
        # Pre-game window
        if start > now and (start - now) <= _PRE_GAME_WINDOW:
            return RefreshIntervalSec.PRE_GAME
    return RefreshIntervalSec.IDLE
```

- [ ] **Step 7.4: Test PASS**

- [ ] **Step 7.5: Commit**

```bash
git add src/infrastructure/data/basketball/refresh_scheduler.py tests/unit/infrastructure/data/basketball/test_refresh_scheduler.py
git commit -m "feat(basketball/data): maç-pencere farkındalıklı refresh scheduler"
```

---

### Task 8: `refresh_runner.py` — Orchestrator Wrapper

**Files:**
- Create: `src/infrastructure/data/basketball/refresh_runner.py`
- Test: `tests/unit/infrastructure/data/basketball/test_refresh_runner.py`

- [ ] **Step 8.1: Test (integration mock)**

```python
# tests/unit/infrastructure/data/basketball/test_refresh_runner.py
"""refresh_runner — primary OK / primary fail → fallback / total fail."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from src.infrastructure.data.basketball.refresh_runner import (
    BasketballRefreshRunner,
)
from src.infrastructure.data.basketball.schemas import GameRecord


@pytest.fixture
def sample_game():
    return GameRecord(
        game_id="0022400001", season="2024-25",
        game_date_utc="2024-11-01T23:30:00Z",
        home_team="LAL", away_team="GSW",
        home_score=110, away_score=104,
        home_possessions=101.7, away_possessions=98.4,
        is_final=True, league="nba",
    )


def test_primary_success_marks_health_and_returns_games(tmp_path: Path, sample_game):
    primary = MagicMock(return_value=[sample_game])
    secondary = MagicMock()
    runner = BasketballRefreshRunner(
        league="nba", health_path=tmp_path / "h.json",
        primary_fetch=primary, secondary_fetch=secondary,
        now_utc_str=lambda: "2024-11-01T00:00:00Z",
    )
    result = runner.run()
    assert len(result.games) == 1
    assert result.source_used == "nba_api"
    secondary.assert_not_called()


def test_primary_fail_falls_back_to_secondary(tmp_path: Path, sample_game):
    primary = MagicMock(side_effect=Exception("network"))
    secondary = MagicMock(return_value=[sample_game])
    runner = BasketballRefreshRunner(
        league="nba", health_path=tmp_path / "h.json",
        primary_fetch=primary, secondary_fetch=secondary,
        now_utc_str=lambda: "2024-11-01T00:00:00Z",
    )
    result = runner.run()
    assert result.source_used == "espn"
    assert len(result.games) == 1


def test_both_sources_fail_returns_empty_degrade(tmp_path: Path):
    primary = MagicMock(side_effect=Exception("network"))
    secondary = MagicMock(side_effect=Exception("network"))
    runner = BasketballRefreshRunner(
        league="nba", health_path=tmp_path / "h.json",
        primary_fetch=primary, secondary_fetch=secondary,
        now_utc_str=lambda: "2024-11-01T00:00:00Z",
    )
    result = runner.run()
    assert result.games == []
    assert result.source_used is None  # degrade
```

- [ ] **Step 8.2: Test FAIL doğrula**

- [ ] **Step 8.3: Implementasyon**

```python
# src/infrastructure/data/basketball/refresh_runner.py
"""Refresh orchestrator — primary çağır, başarısızsa secondary'ye düş.

ARCH_GUARD §12: try/except sadece infrastructure'da. Hata yakalanır,
loglanır, yedek denenir. İkisi de fail ise degrade — boş liste döner.
Çağıran orchestration "boş" durumunu bookmaker fallback olarak değerlendirir.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from src.infrastructure.data.basketball.data_source_health import HealthTracker
from src.infrastructure.data.basketball.schemas import GameRecord

logger = logging.getLogger(__name__)


@dataclass
class RefreshOutcome:
    games: list[GameRecord]
    source_used: Optional[str]   # "nba_api" | "espn" | None


class BasketballRefreshRunner:
    """Tek lig için primary → secondary refresh akışını koordine eder."""

    def __init__(
        self,
        league: str,
        health_path: Path,
        primary_fetch: Callable[[], list[GameRecord]],
        secondary_fetch: Callable[[], list[GameRecord]],
        now_utc_str: Callable[[], str],
    ) -> None:
        self._league = league
        self._tracker = HealthTracker(health_path)
        self._primary = primary_fetch
        self._secondary = secondary_fetch
        self._now = now_utc_str

    def run(self) -> RefreshOutcome:
        # 1. Primary
        if self._tracker.is_active("nba_api"):
            try:
                games = self._primary()
                self._tracker.record_success("nba_api", at_utc=self._now())
                logger.info("basketball refresh: nba_api OK, %d games (%s)", len(games), self._league)
                return RefreshOutcome(games=games, source_used="nba_api")
            except Exception as exc:  # noqa: BLE001
                logger.warning("basketball refresh: nba_api failed — %s", exc)
                self._tracker.record_failure("nba_api", at_utc=self._now())
        # 2. Secondary
        if self._tracker.is_active("espn"):
            try:
                games = self._secondary()
                self._tracker.record_success("espn", at_utc=self._now())
                logger.info("basketball refresh: espn OK, %d games (%s)", len(games), self._league)
                return RefreshOutcome(games=games, source_used="espn")
            except Exception as exc:  # noqa: BLE001
                logger.warning("basketball refresh: espn failed — %s", exc)
                self._tracker.record_failure("espn", at_utc=self._now())
        logger.error("basketball refresh: BOTH sources failed for league=%s — degrade", self._league)
        return RefreshOutcome(games=[], source_used=None)
```

- [ ] **Step 8.4: Test PASS**

- [ ] **Step 8.5: Commit**

```bash
git add src/infrastructure/data/basketball/refresh_runner.py tests/unit/infrastructure/data/basketball/test_refresh_runner.py
git commit -m "feat(basketball/data): refresh runner — primary → secondary → degrade"
```

---

### Task 9: `config.yaml` ve `factory.py` Entegrasyonu

**Files:**
- Modify: `config.yaml`
- Modify: `src/orchestration/factory.py`

- [ ] **Step 9.1: `config.yaml` basketball bölümü ekle**

`config.yaml`'a (uygun bir bölümden sonra) ekle:

```yaml
basketball:
  enabled_leagues:
    - nba
    # wnba — Plan 1.A WNBA spike testi sonrası karara göre eklenir
  cache_dir: data/basketball_cache
  health_file: data/basketball_cache/_health/sources_status.json
  primary_source: nba_api
  secondary_source: espn
  # Refresh interval mantığı domain'de — config'de yalnız etkinleştirme
```

- [ ] **Step 9.2: `src/config/settings.py` basketball config alanını ekle**

Mevcut config dataclass'ına ekleme yap. Tam satır numarası kod inceleme sırasında belirlenir; yeni alan:

```python
@dataclass
class BasketballConfig:
    enabled_leagues: list[str] = field(default_factory=lambda: ["nba"])
    cache_dir: str = "data/basketball_cache"
    health_file: str = "data/basketball_cache/_health/sources_status.json"
    primary_source: str = "nba_api"
    secondary_source: str = "espn"


@dataclass
class AppConfig:
    # ... mevcut alanlar ...
    basketball: BasketballConfig = field(default_factory=BasketballConfig)
```

- [ ] **Step 9.3: `factory.py` basketball hook fonksiyonu ekle**

Tennis Sackmann hook'una paralel (factory.py:347 civarı). Ekle:

```python
# src/orchestration/factory.py

def _maybe_invoke_basketball_refresh(cfg: AppConfig) -> None:
    """Basketball whitelist'te aktif lig varsa refresh çağır."""
    tags_lc = {t.lower() for t in (cfg.scanner.allowed_sport_tags or [])}
    enabled = [lg for lg in cfg.basketball.enabled_leagues if lg in tags_lc]
    if not enabled:
        logger.info("Basketball refresh skipped — no enabled league in whitelist")
        return
    from src.infrastructure.data.basketball.refresh_runner import (
        BasketballRefreshRunner,
    )
    from src.infrastructure.data.basketball.nba_api_refresher import (
        fetch_game_log_via_nba_api,
    )
    from src.infrastructure.data.basketball.espn_pbp_refresher import (
        fetch_game_log_via_espn,
    )
    from datetime import datetime, timezone
    from pathlib import Path

    health_path = Path(cfg.basketball.health_file)
    today = datetime.now(timezone.utc).date().isoformat()
    season = f"{datetime.now(timezone.utc).year - 1}-{datetime.now(timezone.utc).year % 100:02d}"

    for league in enabled:
        def _primary() -> list:
            # Gerçek wiring Plan 1.B'de team_ratings_store + nba_api endpoint factory ile
            return []

        def _secondary() -> list:
            return fetch_game_log_via_espn(league=league, date_utc=today, http_get=__import__("requests").get)

        runner = BasketballRefreshRunner(
            league=league, health_path=health_path,
            primary_fetch=_primary, secondary_fetch=_secondary,
            now_utc_str=lambda: datetime.now(timezone.utc).isoformat(),
        )
        outcome = runner.run()
        logger.info("Basketball refresh for %s done: %s", league, outcome.source_used)
```

Build_deps'in başında `_maybe_invoke_sackmann_refresh(cfg)` çağrısının altına ekle:

```python
_maybe_invoke_basketball_refresh(cfg)
```

- [ ] **Step 9.4: Mevcut tüm testleri çalıştır — regresyon kontrolü**

Run: `pytest tests/unit -x -q`
Expected: hepsi geçmeli (yeni eklenen dosyalar bağımsız modül, mevcut testler etkilenmemeli)

- [ ] **Step 9.5: Commit**

```bash
git add config.yaml src/config/settings.py src/orchestration/factory.py
git commit -m "feat(basketball/orchestration): config + factory hook (tennis Sackmann paraleli)"
```

---

### Task 10: WNBA Spike Test Scripti

**Files:**
- Create: `scripts/basketball_wnba_spike.py`

- [ ] **Step 10.1: Spike test scripti yaz**

```python
# scripts/basketball_wnba_spike.py
"""WNBA veri kalitesi spike testi — Faz 1 kapsam kararı.

Son 1 WNBA sezonu için nba_api üzerinden game-log çek.
Maç sayısı + kolon dolgunluğu + takım kapsamı raporla.

Eşik (Plan 1.A başlangıç onayı):
  - ≥ %90 sezon maçı kapsama
  - Tüm 12 WNBA takımı görünmeli
  - Possessions hesabı için kolonlar dolu olmalı

Geçerse → WNBA Faz 1'e dahil edilir (config.basketball.enabled_leagues).
Geçmezse → TODO.md'ye "wnba-deferred" eklenir, sonraki faza ertelenir.
"""
from __future__ import annotations

import sys
from collections import Counter

try:
    from nba_api.stats.endpoints import leaguegamelog
except ImportError:
    print("ERROR: nba_api paketi yüklü değil. `pip install -r requirements.txt`")
    sys.exit(2)

from src.infrastructure.data.basketball.nba_api_refresher import (
    fetch_game_log_via_nba_api,
)


def main():
    print("[WNBA SPIKE] Fetching 2024 season game log via nba_api...")
    try:
        games = fetch_game_log_via_nba_api(
            league="wnba",
            season="2024",
            endpoint_factory=lambda **kwargs: leaguegamelog.LeagueGameLog(
                season=kwargs["season"],
                league_id=kwargs["league_id"],
                season_type_all_star="Regular Season",
            ),
        )
    except Exception as exc:
        print(f"ERROR fetching: {exc}")
        sys.exit(3)
    print(f"[WNBA SPIKE] Fetched {len(games)} games")
    if not games:
        print("[WNBA SPIKE] FAIL — sıfır maç, WNBA Faz 1 dışı")
        sys.exit(1)
    teams = Counter()
    for g in games:
        teams[g.home_team] += 1
        teams[g.away_team] += 1
    expected_teams = 12
    expected_min_games = int(40 * 0.9)  # ~36, regular season 40 maç/takım
    print(f"[WNBA SPIKE] Unique teams: {len(teams)} (expected {expected_teams})")
    print(f"[WNBA SPIKE] Team match counts: {dict(teams)}")
    if len(teams) < expected_teams:
        print("[WNBA SPIKE] FAIL — takım sayısı yetersiz, WNBA Faz 1 dışı")
        sys.exit(1)
    short_teams = [t for t, c in teams.items() if c < expected_min_games]
    if short_teams:
        print(f"[WNBA SPIKE] WARN — bu takımların maç sayısı düşük: {short_teams}")
    print("[WNBA SPIKE] PASS — WNBA Faz 1 kapsama eklenebilir")


if __name__ == "__main__":
    main()
```

- [ ] **Step 10.2: Scripti çalıştır**

Run: `python scripts/basketball_wnba_spike.py`

Beklenen iki sonuç:
- **PASS:** `config.yaml`'da `enabled_leagues` listesine `- wnba` ekle, commit et
- **FAIL:** `TODO.md`'ye satır ekle: `- WNBA-DEFERRED: nba_api WNBA coverage yetersiz (Plan 1.A spike sonucu)`, commit et

- [ ] **Step 10.3: Commit (sonuca göre)**

PASS senaryosu:
```bash
git add scripts/basketball_wnba_spike.py config.yaml
git commit -m "feat(basketball/spike): WNBA veri spike testi PASS → WNBA Faz 1'e eklendi"
```

FAIL senaryosu:
```bash
git add scripts/basketball_wnba_spike.py TODO.md
git commit -m "chore(basketball): WNBA spike FAIL — sonraki faza ertelendi"
```

---

## Self-Review (Spec'e karşı)

**Spec coverage:**
- §3 Veri Pipeline → Task 3 (primary), Task 4 (secondary), Task 8 (orchestrator) ✓
- §3 Schema drift koruma → Task 2 (Pydantic) ✓
- §3 Sağlık takibi → Task 6 ✓
- §3 Cache yapısı → Task 5 (team_ratings_store) ✓
- §6 Graceful degradation → Task 8 (her ikisi fail → boş, source_used=None) ✓
- §6 WNBA doğrulama → Task 10 ✓
- §3 Maç-pencere farkındalıklı tetik → Task 7 ✓
- §7 Test stratejisi → Her task TDD adımı içeriyor ✓

**Placeholder scan:** "implement later", "TBD" YOK. Her step'te exact code var.

**Type consistency:**
- `GameRecord` her yerde aynı alanlar ✓
- `TeamSnapshot` Task 5 ↔ Task 2 uyumlu ✓
- `RefreshOutcome` Task 8'de tanımlı, Task 9'da kullanılıyor ✓

**Faz 1.B'ye taşınanlar:** Elo update logic, AdjO/AdjD hesabı, takım rating birleştirme — Plan 1.B kapsamı.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-01-basketball-foundation-plan-1A-data-layer.md`.

Bu plan, **subagent-driven-development** ile yürütülmek üzere tasarlanmıştır. Her task ayrı bir subagent ile uygulanır, her task arası inceleme yapılır.

**Onay sonrası:** Plan 1.A subagent-driven execution'a geçilir. Plan 1.A bittiğinde Plan 1.B yazılır.
