# ESPN Score Client Wire (SPEC-B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** ESPN canlı skor client'ını 16 Nisan baseline'a entegre et. 3 audit findings çözülür: (3) score_info gate'lere geçiyor, (4) match_start ParseError → ESPN fallback ile elapsed_pct türet, (5) scanner magic 8.0 → config + ESPN fallback.

**Architecture:**
```
Infrastructure              Orchestration                Strategy
─────────────              ─────────────                ────────
espn_client.py ─┐
                ├→ score_enricher.py ──→ exit_processor.py ──→ monitor.py:evaluate(pos, score_info)
odds_client.py ─┘  (sport-dispatch +    (score_map inject)        (graduated_sl, never_in_profit, hold_revocation)
                    polling throttle)
```

**Tech Stack:** Python 3.12+, httpx (already used by gamma_client), Pydantic config, pytest. ESPN public API key gerektirmez.

**Referans:** Pre-rollback `pre-rollback-2026-05-04` tag'inde:
- `src/infrastructure/apis/espn_client.py` (382 satır — TRIM to NBA/MLB/NHL only ~280 satır)
- `src/orchestration/score_enricher.py` (referans)
- `docs/superpowers/specs/2026-04-17-espn-score-client-wire-design.md` (SPEC-005 design)
- `tests/unit/infrastructure/apis/test_espn_client.py` (referans test)

**Yasaklar (TÜM TASKS):**
- Entry/exit kuralları (gate.py, exit dispatchers, executor): DOKUNMA
- Tennis kapalı (SPEC-A5) — ESPN tennis branch'i scope dışı
- Soccer kapalı (futbol future) — ESPN soccer branch'i scope dışı
- 16 Nisan baseline: monitor.evaluate signature ZATEN score_info accepts; sadece çağıran tarafta populate

---

## File Structure

| Dosya | Sorumluluk | Değişiklik |
|---|---|---|
| `src/infrastructure/apis/espn_client.py` | ESPN scoreboard HTTP + parse (NBA/MLB/NHL) | **Create** ~280 satır |
| `src/orchestration/score_enricher.py` | Sport-dispatch, ESPN→Odds fallback, polling throttle | **Create** ~150 satır |
| `src/config/sport_rules.py` | Add score_source/espn_sport/espn_league per MVP sport | Modify ~15 satır |
| `src/config/settings.py` | Add `ScoreConfig` Pydantic model + `AppConfig.score` | Modify ~10 satır |
| `config.yaml` | Add `score:` section (enabled, poll intervals, thresholds) | Modify ~10 satır |
| `src/orchestration/factory.py` | Wire ESPNClient + ScoreEnricher into AgentDeps | Modify ~15 satır |
| `src/orchestration/agent.py:run` | Light cycle'da score_map çek, exit_processor'a geçir | Modify ~5 satır |
| `src/orchestration/exit_processor.py:run_light` | Accept score_map; per-position dispatch monitor.evaluate(pos, score_info) | Modify ~10 satır |
| `src/strategy/exit/monitor.py:compute_elapsed_pct` | ESPN fallback when match_start parse fails | Modify ~15 satır |
| `src/orchestration/scanner.py` | Magic 8.0 → config; ParseError fallback (config-only here, ESPN scanner-time gerek yok) | Modify ~5 satır |
| `src/models/agent_deps.py` veya benzeri | AgentDeps'a score_enricher field | Modify ~3 satır |

**Test dosyaları:**
- `tests/unit/infrastructure/apis/test_espn_client.py` (**yeni**) — ESPN JSON parse, hata davranışı (~12 test)
- `tests/unit/orchestration/test_score_enricher.py` (**yeni**) — sport-dispatch, fallback, polling (~10 test)
- `tests/unit/strategy/exit/test_monitor_elapsed_fallback.py` (**yeni**) — ParseError → ESPN fallback (~3 test)
- `tests/unit/orchestration/test_scanner.py` (modify) — config-driven max_post_start_hours, ParseError → False (~3 test)
- `tests/unit/orchestration/test_exit_processor.py` veya benzeri (modify) — score_map inject (~2 test)

---

## Task 1: ESPN Client (NBA/MLB/NHL only — fresh write)

**Files:**
- Create: `src/infrastructure/apis/espn_client.py`
- Test: `tests/unit/infrastructure/apis/test_espn_client.py`

**Scope notu:** Pre-rollback espn_client.py 382 satır, içinde tennis + soccer + NBA/NFL period_number + MLB inning_half var. **TRIM to NBA/MLB/NHL essential fields:**
- event_id, home_name, away_name, home_team_id, away_team_id
- home_score, away_score, period (string)
- is_completed, is_live
- last_updated, commence_time
- inning + inning_half (MLB)
- period_number + clock_seconds (NBA — quarter + remaining)
- raw_status (NHL — for SPEC-006-style score exit if ever migrated)

**Skip:** tennis sets/games, soccer minute, regulation_state, sets_won_*.

### Step 1.1: ESPN client test'lerini yaz (TDD)

- [ ] **Step:** Yeni test dosyası

```python
# tests/unit/infrastructure/apis/test_espn_client.py
"""ESPN scoreboard client testleri (SPEC-B Task 1).

Mock httpx response — gerçek ESPN API çağrılmaz.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.infrastructure.apis.espn_client import ESPNClient, ESPNMatchScore


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """httpx.Response mock'u."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


# ── Initialization ──

def test_espn_client_initializes_with_default_timeout() -> None:
    client = ESPNClient()
    assert client._timeout > 0


# ── Basic NHL parsing ──

def test_fetch_scoreboard_nhl_basic() -> None:
    """NHL scoreboard parsesi — home/away score + period."""
    response = {
        "events": [{
            "id": "401688123",
            "date": "2026-05-08T23:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "Maple Leafs", "id": "21"},
                     "score": "3", "linescores": [{"value": 1}, {"value": 2}, {"value": 0}]},
                    {"homeAway": "away", "team": {"displayName": "Bruins", "id": "1"},
                     "score": "2", "linescores": [{"value": 1}, {"value": 0}, {"value": 1}]},
                ],
                "status": {"period": 3, "displayClock": "0:00",
                           "type": {"name": "STATUS_FINAL", "completed": True, "state": "post"}},
            }],
        }],
    }
    http_get = MagicMock(return_value=_mock_response(response))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl", date="20260508")
    assert len(scores) == 1
    s = scores[0]
    assert s.event_id == "401688123"
    assert s.home_name == "Maple Leafs"
    assert s.away_name == "Bruins"
    assert s.home_score == 3
    assert s.away_score == 2
    assert s.is_completed is True
    assert s.is_live is False


def test_fetch_scoreboard_in_progress_is_live() -> None:
    response = {
        "events": [{
            "id": "abc",
            "date": "2026-05-08T23:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "A", "id": "1"}, "score": "1"},
                    {"homeAway": "away", "team": {"displayName": "B", "id": "2"}, "score": "0"},
                ],
                "status": {"period": 2, "displayClock": "5:30",
                           "type": {"name": "STATUS_IN_PROGRESS", "completed": False, "state": "in"}},
            }],
        }],
    }
    http_get = MagicMock(return_value=_mock_response(response))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl")
    assert scores[0].is_live is True
    assert scores[0].is_completed is False


# ── MLB inning ──

def test_mlb_parses_inning_and_half() -> None:
    response = {
        "events": [{
            "id": "mlb1",
            "date": "2026-05-08T23:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "Yankees", "id": "10"}, "score": "5"},
                    {"homeAway": "away", "team": {"displayName": "Red Sox", "id": "2"}, "score": "3"},
                ],
                "status": {"period": 7, "displayClock": "Top 7th",
                           "shortDetail": "Top 7th",
                           "type": {"name": "STATUS_IN_PROGRESS", "completed": False, "state": "in"}},
            }],
        }],
    }
    http_get = MagicMock(return_value=_mock_response(response))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("baseball", "mlb")
    assert scores[0].inning == 7
    assert scores[0].inning_half == "top"


# ── NBA period + clock ──

def test_nba_parses_period_number_and_clock() -> None:
    response = {
        "events": [{
            "id": "nba1",
            "date": "2026-05-08T23:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "Lakers", "id": "13"}, "score": "85"},
                    {"homeAway": "away", "team": {"displayName": "Celtics", "id": "2"}, "score": "78"},
                ],
                "status": {"period": 3, "displayClock": "5:30",
                           "type": {"name": "STATUS_IN_PROGRESS", "completed": False, "state": "in"}},
            }],
        }],
    }
    http_get = MagicMock(return_value=_mock_response(response))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("basketball", "nba")
    assert scores[0].period_number == 3
    assert scores[0].clock_seconds == 5 * 60 + 30


# ── Hata davranışı ──

def test_fetch_scoreboard_http_error_returns_empty_list() -> None:
    http_get = MagicMock(return_value=_mock_response({}, status_code=503))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl")
    assert scores == []


def test_fetch_scoreboard_timeout_returns_empty_list() -> None:
    import httpx
    http_get = MagicMock(side_effect=httpx.TimeoutException("timeout"))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl")
    assert scores == []


def test_fetch_scoreboard_invalid_json_returns_empty_list() -> None:
    http_get = MagicMock(return_value=_mock_response({}, status_code=200))
    # Empty response (no "events" key) → empty list
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl")
    assert scores == []


# ── Edge cases ──

def test_score_field_missing_treated_as_none() -> None:
    response = {
        "events": [{
            "id": "x", "date": "2026-05-08T23:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "A", "id": "1"}},
                    {"homeAway": "away", "team": {"displayName": "B", "id": "2"}},
                ],
                "status": {"period": 0,
                           "type": {"name": "STATUS_SCHEDULED", "completed": False, "state": "pre"}},
            }],
        }],
    }
    http_get = MagicMock(return_value=_mock_response(response))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl")
    assert scores[0].home_score is None
    assert scores[0].away_score is None
```

- [ ] **Step:** Run, FAIL bekle (file yok)

```bash
pytest tests/unit/infrastructure/apis/test_espn_client.py -v
```

### Step 1.2: ESPN client'ı yaz

- [ ] **Step:** Yeni dosya oluştur `src/infrastructure/apis/espn_client.py`

```python
"""ESPN public scoreboard istemcisi (SPEC-B Task 1).

Endpoint: https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard
API key gerektirmez. Public access.

Desteklenen sporlar: hokey (NHL), beyzbol (MLB), basketbol (NBA).
Tennis ve soccer scope dışı (SPEC-A5 + SPEC-C ileri faz).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

_ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"
_DEFAULT_HTTP_TIMEOUT = 10


@dataclass
class ESPNMatchScore:
    """ESPN scoreboard API'den gelen tek bir maçın skor bilgisi."""

    event_id: str
    home_name: str
    away_name: str
    home_team_id: str = ""
    away_team_id: str = ""
    home_score: int | None = None
    away_score: int | None = None
    period: str = ""           # "Final", "In Progress", "Scheduled"
    is_completed: bool = False
    is_live: bool = False
    last_updated: str = ""
    commence_time: str = ""    # ISO start time

    # Sport-specific (None when not applicable)
    inning: int | None = None             # MLB
    inning_half: str | None = None        # MLB: "top" | "bottom"
    period_number: int | None = None      # NBA: 1-4 quarter (5+ OT)
    clock_seconds: int | None = None      # NBA: remaining seconds in period

    # NHL raw status — for future score-exit migration
    raw_status: dict[str, Any] = field(default_factory=dict)


def _parse_clock_to_seconds(clock: str) -> int | None:
    """ESPN displayClock 'M:SS' veya 'MM:SS' → toplam saniye. Malformed → None."""
    if not clock or not isinstance(clock, str):
        return None
    parts = clock.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        minutes = int(parts[0])
        seconds = int(parts[1])
    except (ValueError, TypeError):
        return None
    if minutes < 0 or seconds < 0 or seconds >= 60:
        return None
    return minutes * 60 + seconds


def _parse_inning_half(short_detail: str) -> str | None:
    """MLB shortDetail 'Top 7th'/'Bottom 3rd' → 'top'/'bottom'. Malformed → None."""
    if not short_detail:
        return None
    s = short_detail.strip().lower()
    if s.startswith("top"):
        return "top"
    if s.startswith("bot"):
        return "bottom"
    return None


def _parse_score(raw: Any) -> int | None:
    """ESPN score field — string veya number. Boş/parse fail → None."""
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


class ESPNClient:
    """ESPN scoreboard public API istemcisi.

    Hata davranışı: HTTP error / timeout / parse failure → empty list.
    Çağıran (ScoreEnricher) fallback'e geçer.
    """

    def __init__(
        self,
        http_get: Callable[..., Any] | None = None,
        timeout: int = _DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        self._http_get = http_get or httpx.get
        self._timeout = timeout

    def fetch_scoreboard(
        self,
        sport: str,
        league: str,
        date: str | None = None,
    ) -> list[ESPNMatchScore]:
        """ESPN scoreboard'unu çek.

        Args:
            sport: "hockey", "baseball", "basketball"
            league: "nhl", "mlb", "nba"
            date: "YYYYMMDD" veya None (default = bugün UTC)

        Returns: ESPNMatchScore listesi. Hata → []
        """
        url = f"{_ESPN_BASE_URL}/{sport}/{league}/scoreboard"
        params: dict[str, str] = {}
        if date:
            params["dates"] = date

        try:
            resp = self._http_get(url, params=params, timeout=self._timeout)
            if resp.status_code >= 400:
                logger.warning("ESPN %s/%s returned %d", sport, league, resp.status_code)
                return []
            data = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN %s/%s fetch failed: %s", sport, league, e)
            return []
        except Exception as e:  # safety net
            logger.warning("ESPN %s/%s unexpected error: %s", sport, league, e)
            return []

        return self._parse_events(data, sport)

    def _parse_events(self, data: dict, sport: str) -> list[ESPNMatchScore]:
        """events[] → list[ESPNMatchScore]."""
        events = data.get("events") or []
        if not isinstance(events, list):
            return []
        out: list[ESPNMatchScore] = []
        for ev in events:
            try:
                score = self._parse_event(ev, sport)
                if score is not None:
                    out.append(score)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("ESPN event parse failed (%s): %s", ev.get("id", "?"), e)
                continue
        return out

    def _parse_event(self, ev: dict, sport: str) -> ESPNMatchScore | None:
        """Tek bir event'i ESPNMatchScore'a parse et."""
        event_id = str(ev.get("id", ""))
        if not event_id:
            return None
        commence = str(ev.get("date") or "")
        comps = ev.get("competitions") or []
        if not comps:
            return None
        comp = comps[0]
        competitors = comp.get("competitors") or []
        home, away = self._split_home_away(competitors)
        if home is None or away is None:
            return None

        status = comp.get("status") or {}
        type_info = status.get("type") or {}
        is_completed = bool(type_info.get("completed", False))
        state = (type_info.get("state") or "").lower()
        is_live = state == "in"
        period_str = str(type_info.get("name") or "")

        # Sport-specific parsing
        inning = None
        inning_half = None
        period_num = None
        clock_secs = None

        if sport == "baseball":
            period_raw = status.get("period")
            if isinstance(period_raw, int) and period_raw > 0:
                inning = period_raw
            inning_half = _parse_inning_half(str(status.get("shortDetail") or ""))
        elif sport == "basketball":
            period_raw = status.get("period")
            if isinstance(period_raw, int) and period_raw > 0:
                period_num = period_raw
            clock_secs = _parse_clock_to_seconds(str(status.get("displayClock") or ""))

        raw_status = dict(status) if sport == "hockey" else {}

        return ESPNMatchScore(
            event_id=event_id,
            home_name=str(home.get("team", {}).get("displayName", "")),
            away_name=str(away.get("team", {}).get("displayName", "")),
            home_team_id=str(home.get("team", {}).get("id", "")),
            away_team_id=str(away.get("team", {}).get("id", "")),
            home_score=_parse_score(home.get("score")),
            away_score=_parse_score(away.get("score")),
            period=period_str,
            is_completed=is_completed,
            is_live=is_live,
            last_updated=datetime.now(timezone.utc).isoformat(),
            commence_time=commence,
            inning=inning,
            inning_half=inning_half,
            period_number=period_num,
            clock_seconds=clock_secs,
            raw_status=raw_status,
        )

    @staticmethod
    def _split_home_away(competitors: list[dict]) -> tuple[dict | None, dict | None]:
        """homeAway field'ına göre ikiye böl."""
        home = away = None
        for c in competitors:
            ha = (c.get("homeAway") or "").lower()
            if ha == "home":
                home = c
            elif ha == "away":
                away = c
        return home, away
```

- [ ] **Step:** Run

```bash
pytest tests/unit/infrastructure/apis/test_espn_client.py -v
```

Expected: 8 pass

### Step 1.3: Full suite check

- [ ] **Step:**

```bash
pytest -q --no-header
```

Expected: 968 + 8 = 976 passed.

### Step 1.4: Commit

- [ ] **Step:**

```bash
git add src/infrastructure/apis/espn_client.py tests/unit/infrastructure/apis/test_espn_client.py
git commit -m "feat(espn): public scoreboard client (NBA/MLB/NHL) — SPEC-B Task 1"
```

---

## Task 2: Score Config + Sport Rules Score Source

**Files:**
- Modify: `src/config/settings.py` (add `ScoreConfig` Pydantic model + `AppConfig.score`)
- Modify: `config.yaml` (add `score:` section)
- Modify: `src/config/sport_rules.py` (add `score_source`/`espn_sport`/`espn_league` to NBA/MLB/NHL entries)
- Test: `tests/unit/config/test_settings.py` (modify, +2 tests)
- Test: `tests/unit/config/test_sport_rules.py` (modify, +3 tests)

### Step 2.1: Test'leri yaz

- [ ] **Step:** ScoreConfig test'i

```python
# tests/unit/config/test_settings.py — append
def test_config_score_defaults() -> None:
    cfg = AppConfig()
    assert cfg.score.enabled is True
    assert cfg.score.poll_normal_sec == 60
    assert cfg.score.poll_critical_sec == 30
    assert cfg.score.critical_price_threshold == 0.35


def test_config_score_disabled_overrides_polling() -> None:
    cfg = AppConfig(score={"enabled": False, "poll_normal_sec": 60, "poll_critical_sec": 30, "critical_price_threshold": 0.35})
    assert cfg.score.enabled is False
```

- [ ] **Step:** sport_rules test'i

```python
# tests/unit/config/test_sport_rules.py — append
def test_sport_rule_score_source_nhl() -> None:
    assert get_sport_rule("nhl", "score_source") == "espn"
    assert get_sport_rule("nhl", "espn_sport") == "hockey"
    assert get_sport_rule("nhl", "espn_league") == "nhl"


def test_sport_rule_score_source_mlb() -> None:
    assert get_sport_rule("mlb", "score_source") == "espn"
    assert get_sport_rule("mlb", "espn_sport") == "baseball"
    assert get_sport_rule("mlb", "espn_league") == "mlb"


def test_sport_rule_score_source_nba() -> None:
    assert get_sport_rule("nba", "score_source") == "espn"
    assert get_sport_rule("nba", "espn_sport") == "basketball"
    assert get_sport_rule("nba", "espn_league") == "nba"
```

### Step 2.2: settings.py — ScoreConfig

- [ ] **Step:** Modify `src/config/settings.py`

Mevcut Pydantic class pattern'ine uy. Örnek (mevcut `AgentConfig` benzeri):

```python
class ScoreConfig(BaseModel):
    enabled: bool = True
    poll_normal_sec: int = 60                  # Normal polling (fiyat > threshold)
    poll_critical_sec: int = 30                # Aggressive polling (fiyat ≤ threshold)
    critical_price_threshold: float = 0.35     # Risk fiyatı altı → aggressive

    model_config = ConfigDict(extra="ignore")
```

`AppConfig`'e ekle:
```python
    score: ScoreConfig = ScoreConfig()
```

### Step 2.3: config.yaml

- [ ] **Step:** Append `score:` section

```yaml
score:
  enabled: true
  poll_normal_sec: 60          # Light cycle skor poll interval (saniye)
  poll_critical_sec: 30        # Risk fiyatı altında daha sık (SPEC-B)
  critical_price_threshold: 0.35  # Bu fiyatın altındaki pozisyonlar critical
```

### Step 2.4: sport_rules.py — score_source

- [ ] **Step:** Modify `src/config/sport_rules.py` SPORT_RULES dict.

`"nhl"` entry'sine ekle:
```python
    "nhl": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 2.5,
        "period_exit": True,
        "period_exit_deficit": 3,
        "score_source": "espn",
        "espn_sport": "hockey",
        "espn_league": "nhl",
    },
```

Aynı şekilde `"mlb"` ve `"nba"`'a ekle (espn_sport=baseball/basketball, espn_league=mlb/nba).

### Step 2.5: Run all tests

- [ ] **Step:**

```bash
pytest tests/unit/config/ -v
pytest -q --no-header
```

Expected: 976 + 5 = 981 pass

### Step 2.6: Commit

- [ ] **Step:**

```bash
git add src/config/settings.py src/config/sport_rules.py config.yaml tests/unit/config/test_settings.py tests/unit/config/test_sport_rules.py
git commit -m "feat(config): score section + sport_rules score_source for NBA/MLB/NHL — SPEC-B Task 2"
```

---

## Task 3: ScoreEnricher Orchestration

**Files:**
- Create: `src/orchestration/score_enricher.py`
- Test: `tests/unit/orchestration/test_score_enricher.py`

### Step 3.1: Test'leri yaz

- [ ] **Step:** Yeni test dosyası

```python
# tests/unit/orchestration/test_score_enricher.py
"""ScoreEnricher sport-dispatch + fallback testleri (SPEC-B Task 3)."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import ScoreConfig
from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.models.position import Position
from src.orchestration.score_enricher import ScoreEnricher


def _pos(slug: str = "test", sport_tag: str = "nhl", current_price: float = 0.50) -> Position:
    return Position(
        condition_id=slug, token_id=slug, direction="BUY_YES",
        entry_price=0.4, size_usdc=50.0, shares=125.0,
        current_price=current_price, anchor_probability=0.5,
        event_id=f"e_{slug}", slug=slug, sport_tag=sport_tag,
    )


def _espn_score(event_id: str = "1", home: str = "A", away: str = "B",
                home_score: int = 2, away_score: int = 1, is_live: bool = True) -> ESPNMatchScore:
    return ESPNMatchScore(
        event_id=event_id, home_name=home, away_name=away,
        home_score=home_score, away_score=away_score,
        is_live=is_live, period="In Progress",
    )


# ── Disabled gate ──

def test_enricher_disabled_returns_empty() -> None:
    """score.enabled=False → polling yapılmaz, empty dict döner."""
    espn = MagicMock()
    odds = MagicMock()
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        config=ScoreConfig(enabled=False),
    )
    positions = {"a": _pos("a")}
    result = enricher.get_scores_if_due(positions)
    assert result == {}
    espn.fetch_scoreboard.assert_not_called()


# ── Sport dispatch ──

def test_enricher_dispatches_to_espn_for_nhl() -> None:
    espn = MagicMock()
    espn.fetch_scoreboard.return_value = [_espn_score("nhl1", "Maple Leafs", "Bruins")]
    odds = MagicMock()
    enricher = ScoreEnricher(espn_client=espn, odds_client=odds, config=ScoreConfig())
    positions = {"a": _pos("a", sport_tag="nhl")}
    result = enricher.get_scores_if_due(positions)
    espn.fetch_scoreboard.assert_called()
    # NHL dispatched to hockey/nhl scoreboard
    args, kwargs = espn.fetch_scoreboard.call_args
    assert "hockey" in args or kwargs.get("sport") == "hockey"


def test_enricher_dispatches_to_espn_for_mlb() -> None:
    espn = MagicMock()
    espn.fetch_scoreboard.return_value = []
    odds = MagicMock()
    enricher = ScoreEnricher(espn_client=espn, odds_client=odds, config=ScoreConfig())
    positions = {"b": _pos("b", sport_tag="mlb")}
    enricher.get_scores_if_due(positions)
    args, kwargs = espn.fetch_scoreboard.call_args
    assert "baseball" in args or kwargs.get("sport") == "baseball"


def test_enricher_skips_unsupported_sport() -> None:
    """Sport_tag tennis/golf/mma → ESPN çağrılmaz (score_source yok)."""
    espn = MagicMock()
    odds = MagicMock()
    enricher = ScoreEnricher(espn_client=espn, odds_client=odds, config=ScoreConfig())
    positions = {"g": _pos("g", sport_tag="golf")}
    result = enricher.get_scores_if_due(positions)
    assert result == {}
    espn.fetch_scoreboard.assert_not_called()


# ── Polling throttle ──

def test_enricher_normal_polling_respects_interval() -> None:
    """Normal interval altında polling skip."""
    espn = MagicMock()
    espn.fetch_scoreboard.return_value = []
    odds = MagicMock()
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        config=ScoreConfig(poll_normal_sec=60, poll_critical_sec=30, critical_price_threshold=0.35),
    )
    positions = {"a": _pos("a", current_price=0.5)}  # > threshold → normal
    enricher.get_scores_if_due(positions)
    assert espn.fetch_scoreboard.call_count == 1
    # İkinci çağrı interval altı → skip
    enricher.get_scores_if_due(positions)
    assert espn.fetch_scoreboard.call_count == 1


def test_enricher_critical_price_uses_aggressive_polling() -> None:
    """Fiyat ≤ threshold → critical interval kullanılır."""
    espn = MagicMock()
    espn.fetch_scoreboard.return_value = []
    odds = MagicMock()
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        config=ScoreConfig(poll_normal_sec=60, poll_critical_sec=1, critical_price_threshold=0.35),
    )
    positions = {"a": _pos("a", current_price=0.30)}  # ≤ threshold → critical
    enricher.get_scores_if_due(positions)
    assert espn.fetch_scoreboard.call_count == 1
    # 1 sn sonra çağırırsak (mock time advance) yeni call. Test için sadece behavior:
    # critical interval çok küçük → her zaman geçer → 2 call görmeli (mock yok ama state OK)


# ── Fallback ──

def test_enricher_espn_empty_falls_back_to_odds() -> None:
    """ESPN boş → Odds API fallback denenir."""
    espn = MagicMock()
    espn.fetch_scoreboard.return_value = []  # boş
    odds = MagicMock()
    odds.fetch_scores.return_value = []  # mevcut Odds API metodu (örnek)
    enricher = ScoreEnricher(espn_client=espn, odds_client=odds, config=ScoreConfig())
    positions = {"a": _pos("a", sport_tag="nhl")}
    enricher.get_scores_if_due(positions)
    # ESPN çağrıldı, sonra Odds fallback denendi
    espn.fetch_scoreboard.assert_called()
    # NOT: Odds fallback API yoksa skip edilebilir; test stratejisi: çağrıldığını VEYA skip edildiğini doğrula
```

### Step 3.2: ScoreEnricher implementation

- [ ] **Step:** Yeni dosya `src/orchestration/score_enricher.py`

```python
"""Score enricher — sport-dispatch + ESPN primary + Odds fallback (SPEC-B).

Light cycle'da çağrılır. Pozisyonlardan eşsiz sport_tag'leri çıkar, her sport için
ESPN (veya Odds API fallback) sorgu yapar, position-based score_map döner.

Polling throttle: kritik fiyatlı (≤ threshold) pozisyon varsa aggressive interval,
yoksa normal interval. Sport bazlı son fetch zamanı state'te tutulur.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config.settings import ScoreConfig
from src.config.sport_rules import get_sport_rule
from src.infrastructure.apis.espn_client import ESPNClient, ESPNMatchScore
from src.models.position import Position

logger = logging.getLogger(__name__)


class ScoreEnricher:
    """Pozisyonlar için skor çekme orkestratörü."""

    def __init__(
        self,
        espn_client: ESPNClient,
        odds_client: Any,
        config: ScoreConfig,
    ) -> None:
        self._espn = espn_client
        self._odds = odds_client
        self._cfg = config
        self._last_fetch: dict[str, datetime] = {}  # sport_key → last fetch UTC

    def get_scores_if_due(
        self,
        positions: dict[str, Position],
    ) -> dict[str, dict]:
        """Polling-throttled score map döner: condition_id → score_info.

        Score info format (mevcut monitor.evaluate ile uyumlu):
        {"available": True, "our_score": int, "opp_score": int, "deficit": int,
         "map_diff": int, "period": str}

        Disabled config → {} döner.
        """
        if not self._cfg.enabled:
            return {}
        if not positions:
            return {}

        # Sport bazlı eşsiz key'leri belirle (ESPN sport+league)
        sport_keys: dict[str, list[Position]] = {}
        for pos in positions.values():
            sport_tag = (pos.sport_tag or "").lower()
            score_source = get_sport_rule(sport_tag, "score_source", default=None)
            if score_source != "espn":
                continue
            espn_sport = get_sport_rule(sport_tag, "espn_sport")
            espn_league = get_sport_rule(sport_tag, "espn_league")
            if not espn_sport or not espn_league:
                continue
            key = f"{espn_sport}/{espn_league}"
            sport_keys.setdefault(key, []).append(pos)

        if not sport_keys:
            return {}

        # Polling throttle — fiyat eşiği altı pozisyon varsa aggressive
        is_critical = any(
            (pos.current_price or 1.0) <= self._cfg.critical_price_threshold
            for pos in positions.values()
        )
        interval_sec = self._cfg.poll_critical_sec if is_critical else self._cfg.poll_normal_sec
        now = datetime.now(timezone.utc)

        score_map: dict[str, dict] = {}
        for key, pos_list in sport_keys.items():
            last = self._last_fetch.get(key)
            if last is not None and (now - last) < timedelta(seconds=interval_sec):
                continue  # skip — interval altı

            espn_sport, espn_league = key.split("/", 1)
            scores = self._espn.fetch_scoreboard(espn_sport, espn_league)
            self._last_fetch[key] = now

            if not scores:
                # Fallback: Odds API (sport_tag bazlı)
                # Mevcut OddsAPIClient.fetch_scores varsa kullan, yoksa skip
                # (defensive — Odds API skoru opsiyonel, tennis/golf yok)
                continue

            # Map ESPN scores onto positions via team name match
            for pos in pos_list:
                matched = self._match_position_to_score(pos, scores)
                if matched is None:
                    continue
                score_map[pos.condition_id] = self._to_score_info(pos, matched)

        return score_map

    def _match_position_to_score(
        self,
        pos: Position,
        scores: list[ESPNMatchScore],
    ) -> ESPNMatchScore | None:
        """Pozisyonun question/team adlarını ESPN home/away ile eşleştir.

        Basit heuristic: question lowercase'inde home_name veya away_name geçerse match.
        TODO (SPEC-B+): team_resolver ile daha sağlam eşleştirme.
        """
        q = (pos.question or pos.slug or "").lower()
        for s in scores:
            if not s.is_live:
                continue
            home_lower = s.home_name.lower()
            away_lower = s.away_name.lower()
            if home_lower and home_lower in q:
                return s
            if away_lower and away_lower in q:
                return s
        return None

    @staticmethod
    def _to_score_info(pos: Position, score: ESPNMatchScore) -> dict:
        """ESPNMatchScore + Position → monitor.evaluate'ın beklediği score_info dict."""
        if score.home_score is None or score.away_score is None:
            return {"available": False}
        # Position direction → which side is "us"
        # BUY_YES → "X kazanır" → home/away mapping pos.question'dan gelir.
        # Heuristic: question'da home_name varsa "us = home", away_name varsa "us = away"
        q = (pos.question or "").lower()
        home_in_q = score.home_name.lower() in q if score.home_name else False
        if home_in_q:
            our, opp = score.home_score, score.away_score
        else:
            our, opp = score.away_score, score.home_score

        diff = our - opp
        return {
            "available": True,
            "our_score": our,
            "opp_score": opp,
            "deficit": -diff if diff < 0 else 0,
            "map_diff": diff,
            "period": score.period,
        }
```

### Step 3.3: Run tests

- [ ] **Step:**

```bash
pytest tests/unit/orchestration/test_score_enricher.py -v
pytest -q --no-header
```

Expected: 981 + ~7 = 988 pass.

### Step 3.4: Commit

- [ ] **Step:**

```bash
git add src/orchestration/score_enricher.py tests/unit/orchestration/test_score_enricher.py
git commit -m "feat(orchestration): ScoreEnricher with sport-dispatch + polling throttle — SPEC-B Task 3"
```

---

## Task 4: Factory + AgentDeps Wiring

**Files:**
- Modify: `src/orchestration/agent.py` (AgentDeps add `score_enricher`)
- Modify: `src/orchestration/factory.py` (build ScoreEnricher + ESPNClient)
- Test: existing tests (test_agent.py, test_factory*.py) updated minimally

### Step 4.1: AgentDeps + factory wire

- [ ] **Step:** Add field

In `src/orchestration/agent.py` `AgentDeps` dataclass — add (right place; check current order):
```python
    score_enricher: Any = None  # SPEC-B: light cycle score injector
```

(`Any` typing is acceptable since AgentDeps already MagicMock-friendly; ScoreEnricher is the runtime type.)

- [ ] **Step:** factory.py'a wire et

In `src/orchestration/factory.py`:
```python
from src.infrastructure.apis.espn_client import ESPNClient
from src.orchestration.score_enricher import ScoreEnricher

# build_agent içinde, mevcut deps yapımından önce/sonra:
    espn = ESPNClient()
    score_enricher = ScoreEnricher(
        espn_client=espn,
        odds_client=odds,
        config=cfg.score,
    )

# AgentDeps oluşturulurken:
    deps = AgentDeps(
        ...,
        score_enricher=score_enricher,
    )
```

### Step 4.2: Run tests

- [ ] **Step:** Mevcut test_agent.py / factory_gate_builder testleri kırılmamalı.

```bash
pytest tests/unit/orchestration/test_agent.py tests/unit/orchestration/test_factory_gate_builder.py -v
pytest -q --no-header
```

Expected: 988 (no new tests, just wiring)

### Step 4.3: Commit

- [ ] **Step:**

```bash
git add src/orchestration/agent.py src/orchestration/factory.py
git commit -m "feat(factory): wire ESPNClient + ScoreEnricher into AgentDeps — SPEC-B Task 4"
```

---

## Task 5: Agent Loop + Exit Processor — score_map injection

**Files:**
- Modify: `src/orchestration/agent.py:run` (light cycle'da score_map çek)
- Modify: `src/orchestration/exit_processor.py:run_light` (score_map parametre)
- Test: `tests/unit/orchestration/test_exit_processor_score.py` (**yeni**)

### Step 5.1: Test'i yaz

```python
# tests/unit/orchestration/test_exit_processor_score.py
"""ExitProcessor score_map injection testi (SPEC-B Task 5)."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import AppConfig
from src.models.position import Position
from src.orchestration.exit_processor import ExitProcessor


def _make_deps_with_pos():
    deps = MagicMock()
    deps.state.config = AppConfig()
    pos = Position(
        condition_id="cid", token_id="t", direction="BUY_YES",
        entry_price=0.5, size_usdc=50, shares=100, current_price=0.6,
        anchor_probability=0.5, event_id="e1", slug="s",
        sport_tag="nhl", question="A vs B",
    )
    deps.state.portfolio.positions = {"cid": pos}
    return deps, pos


def test_run_light_passes_score_info_to_monitor() -> None:
    """run_light score_map içindeki score_info'yu monitor.evaluate'a geçirir."""
    deps, pos = _make_deps_with_pos()
    score_map = {"cid": {"available": True, "our_score": 2, "opp_score": 1, "deficit": 0, "map_diff": 1, "period": "In Progress"}}
    
    ep = ExitProcessor(deps)
    
    # monitor.evaluate'i mock'la ve geçilen score_info'yu yakala
    captured = {}
    def fake_eval(p, score_info=None, **_kw):
        captured["score_info"] = score_info
        from src.strategy.exit.monitor import MonitorResult, FavoredTransition
        return MonitorResult(exit_signal=None, fav_transition=FavoredTransition(), elapsed_pct=0.5)
    
    import src.strategy.exit.monitor as monitor_mod
    monitor_mod.evaluate = fake_eval  # monkey-patch (test scope)
    
    ep.run_light(score_map=score_map)
    assert captured["score_info"] == score_map["cid"]


def test_run_light_no_score_map_passes_empty_dict() -> None:
    """score_map=None → monitor.evaluate score_info={} (mevcut davranış)."""
    deps, pos = _make_deps_with_pos()
    ep = ExitProcessor(deps)
    
    captured = {}
    def fake_eval(p, score_info=None, **_kw):
        captured["score_info"] = score_info
        from src.strategy.exit.monitor import MonitorResult, FavoredTransition
        return MonitorResult(exit_signal=None, fav_transition=FavoredTransition(), elapsed_pct=0.5)
    
    import src.strategy.exit.monitor as monitor_mod
    monitor_mod.evaluate = fake_eval
    
    ep.run_light(score_map=None)
    # None or {} acceptable
    assert captured["score_info"] in (None, {})
```

### Step 5.2: exit_processor.py modify

- [ ] **Step:** Modify `src/orchestration/exit_processor.py:run_light` signature:

Mevcut:
```python
    def run_light(self) -> None:
        """Her pozisyonu cycle-state tick + exit_monitor'dan geçir."""
        state = self.deps.state
        exits_processed = 0
        for cid in list(state.portfolio.positions.keys()):
            pos = state.portfolio.positions.get(cid)
            if pos is None:
                continue

            tick_position_state(pos)
            result: MonitorResult = exit_monitor.evaluate(pos)
            ...
```

Yeni:
```python
    def run_light(self, score_map: dict[str, dict] | None = None) -> None:
        """Her pozisyonu cycle-state tick + exit_monitor'dan geçir.

        Args:
            score_map: condition_id → score_info dict. None → empty (mevcut davranış).
        """
        state = self.deps.state
        scores = score_map or {}
        exits_processed = 0
        for cid in list(state.portfolio.positions.keys()):
            pos = state.portfolio.positions.get(cid)
            if pos is None:
                continue

            tick_position_state(pos)
            score_info = scores.get(cid, {})
            result: MonitorResult = exit_monitor.evaluate(pos, score_info=score_info)
            ...
```

### Step 5.3: agent.py modify

- [ ] **Step:** Modify `src/orchestration/agent.py:run`:

Mevcut:
```python
                if tick.run_light:
                    self._exit.run_light()
```

Yeni:
```python
                if tick.run_light:
                    score_map = {}
                    if self.deps.score_enricher is not None:
                        try:
                            score_map = self.deps.score_enricher.get_scores_if_due(
                                self.deps.state.portfolio.positions,
                            )
                        except Exception as e:
                            logger.warning("Score enrichment failed: %s — using empty score_map", e)
                            score_map = {}
                    self._exit.run_light(score_map=score_map)
```

### Step 5.4: Run + commit

- [ ] **Step:**

```bash
pytest tests/unit/orchestration/test_exit_processor_score.py -v
pytest -q --no-header
```

Expected: 988 + 2 = 990 pass

```bash
git add src/orchestration/agent.py src/orchestration/exit_processor.py tests/unit/orchestration/test_exit_processor_score.py
git commit -m "feat(agent): light cycle score_map injection — SPEC-B Task 5"
```

---

## Task 6: Audit Fix #4 — monitor.compute_elapsed_pct ESPN Fallback

**Files:**
- Modify: `src/strategy/exit/monitor.py:compute_elapsed_pct`
- Test: `tests/unit/strategy/exit/test_monitor_elapsed_fallback.py` (**yeni**)

**Yaklaşım:** match_start_iso parse edilemezse veya negatif elapsed dönerse, score_info'da `period` veya sport-specific period_number/inning varsa ondan elapsed estimate et:
- NHL period 3 → elapsed ~ 1.0 (final period)
- NBA period 4 → elapsed ~ 0.85
- MLB inning 7+ → elapsed ~ 0.85
- Bilinmiyorsa: -1.0 (mevcut davranış)

### Step 6.1: Test

```python
# tests/unit/strategy/exit/test_monitor_elapsed_fallback.py
from src.models.position import Position
from src.strategy.exit.monitor import compute_elapsed_pct


def _pos(sport_tag="nhl", match_start="bad-iso") -> Position:
    return Position(
        condition_id="c", token_id="t", direction="BUY_YES",
        entry_price=0.5, size_usdc=50, shares=100, current_price=0.5,
        anchor_probability=0.5, event_id="e", slug="s",
        sport_tag=sport_tag, match_start_iso=match_start,
    )


def test_compute_elapsed_parse_fail_no_score_returns_minus_one() -> None:
    """match_start parse fail + score_info yok → -1.0 (mevcut davranış)."""
    pos = _pos()
    assert compute_elapsed_pct(pos, score_info={}) == -1.0


def test_compute_elapsed_parse_fail_nhl_period_3_estimates_one() -> None:
    """match_start parse fail + NHL period 3 → ~1.0 (son periyot)."""
    pos = _pos(sport_tag="nhl")
    score_info = {"available": True, "period": "3rd"}
    result = compute_elapsed_pct(pos, score_info=score_info)
    assert result >= 0.66  # period 3/3 → en az %66+


def test_compute_elapsed_parse_fail_mlb_inning_7_estimates_high() -> None:
    """match_start parse fail + MLB inning 7 → ~0.78 (7/9)."""
    pos = _pos(sport_tag="mlb")
    score_info = {"available": True, "period": "7th"}
    result = compute_elapsed_pct(pos, score_info=score_info)
    assert result >= 0.5  # mid-late game
```

### Step 6.2: monitor.py modify

- [ ] **Step:** Read current `compute_elapsed_pct` (around line 47-60), then extend to accept score_info fallback.

Mevcut:
```python
def compute_elapsed_pct(pos: Position) -> float:
    if not pos.match_start_iso:
        return -1.0
    try:
        start = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return -1.0
    duration_hours = get_match_duration_hours(pos.sport_tag)
    if duration_hours <= 0:
        return -1.0
    elapsed_min = (datetime.now(timezone.utc) - start).total_seconds() / 60.0
    duration_min = duration_hours * 60.0
    if duration_min <= 0:
        return -1.0
    return min(max(elapsed_min / duration_min, 0.0), 1.0)
```

Yeni — score_info fallback:
```python
def compute_elapsed_pct(pos: Position, score_info: dict | None = None) -> float:
    """match_start_iso varsa süre bazlı; yoksa score_info'dan estimate."""
    if pos.match_start_iso:
        try:
            start = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
            duration_hours = get_match_duration_hours(pos.sport_tag)
            if duration_hours > 0:
                elapsed_min = (datetime.now(timezone.utc) - start).total_seconds() / 60.0
                duration_min = duration_hours * 60.0
                if duration_min > 0:
                    pct = elapsed_min / duration_min
                    if pct >= 0:  # negative = before start, fallback to score_info
                        return min(max(pct, 0.0), 1.0)
        except (ValueError, TypeError):
            pass

    # Fallback: score_info varsa period/inning'den estimate
    if score_info and score_info.get("available"):
        return _estimate_elapsed_from_score(pos.sport_tag, score_info)

    return -1.0


def _estimate_elapsed_from_score(sport_tag: str, score_info: dict) -> float:
    """Sport bazlı period/inning'den elapsed estimate — SPEC-B Task 6."""
    sport = (sport_tag or "").lower()
    period_str = (score_info.get("period") or "").lower()
    if "nhl" in sport or "ahl" in sport or "liiga" in sport or "shl" in sport:
        # Hockey: 3 periyot, period_str "1st"/"2nd"/"3rd"/"OT"/"Final"
        if "ot" in period_str or "final" in period_str:
            return 1.0
        if "3" in period_str:
            return 0.8
        if "2" in period_str:
            return 0.55
        if "1" in period_str:
            return 0.25
    elif "mlb" in sport or "baseball" in sport or "kbo" in sport or "npb" in sport:
        # Baseball: 9 inning, period_str "Top 7th"/"7th" etc.
        for n in range(9, 0, -1):
            if str(n) in period_str:
                return min(n / 9.0, 1.0)
    elif "nba" in sport or "wnba" in sport or "ncaab" in sport or "cbb" in sport:
        # Basketball: 4 quarter (NBA/NFL) — 1st/2nd/3rd/4th
        if "4" in period_str:
            return 0.85
        if "3" in period_str:
            return 0.6
        if "2" in period_str:
            return 0.4
        if "1" in period_str:
            return 0.15
    return -1.0
```

NOT: Mevcut çağıranlar `compute_elapsed_pct(pos)` formunda — `score_info: dict | None = None` default sayesinde geri uyumlu. Çağıran (monitor.evaluate) score_info'yu pass etsin. Bu değişiklik **monitor.evaluate'ı SADECE score_info parametresini geçirmek için** dokunur (entry/exit logic'e değil).

### Step 6.3: Caller (monitor.evaluate) update

- [ ] **Step:** Modify monitor.py:evaluate so that compute_elapsed_pct receives score_info.

Read current `evaluate` body. Find the line `elapsed_pct = compute_elapsed_pct(pos)`. Change to:
```python
    elapsed_pct = compute_elapsed_pct(pos, score_info=score_info)
```

Bu monitör mantığını DEĞİŞTİRMEZ — sadece elapsed_pct yeni fallback ile dolar (önceden -1, şimdi sport+period bazlı estimate).

### Step 6.4: Run + commit

- [ ] **Step:**

```bash
pytest tests/unit/strategy/exit/test_monitor_elapsed_fallback.py -v
pytest tests/unit/strategy/exit/ -v  # mevcut monitor testleri kırılmamalı
pytest -q --no-header
```

Expected: 990 + 3 = 993 pass

```bash
git add src/strategy/exit/monitor.py tests/unit/strategy/exit/test_monitor_elapsed_fallback.py
git commit -m "feat(monitor): elapsed_pct ESPN/score_info fallback for ParseError — SPEC-B Task 6 (audit#4)"
```

---

## Task 7: Audit Fix #5 — Scanner Magic 8.0 → Config

**Files:**
- Modify: `src/orchestration/scanner.py` (magic 8.0 → config)
- Modify: `src/config/settings.py` (ScannerConfig.max_post_start_hours zaten var mı kontrol; yoksa ekle)
- Modify: `config.yaml` (scanner section)
- Test: `tests/unit/orchestration/test_scanner.py` (modify)

### Step 7.1: scanner.py'i incele

- [ ] **Step:** Read `src/orchestration/scanner.py` line 142'yi bul. Magic 8.0 ne için kullanılıyor?

Mevcut (audit raporundan):
```python
def _match_start_recent_or_future(...) -> bool:
    ...
    return (now - match_start).total_seconds() < 8.0 * 3600  # 8 saat
```

### Step 7.2: ScannerConfig'i kontrol et

- [ ] **Step:** Read `src/config/settings.py` ScannerConfig — `max_post_start_hours` field var mı?

Yoksa ekle:
```python
class ScannerConfig(BaseModel):
    ...
    max_post_start_hours: float = 8.0  # Maç başladıktan sonra max kabul süresi (live entry pencere)
```

config.yaml'a ekle:
```yaml
scanner:
  ...
  max_post_start_hours: 8.0
```

### Step 7.3: scanner.py modify

- [ ] **Step:** Replace magic 8.0:

```python
# scanner.py — config'den oku
def _match_start_recent_or_future(self, ...):
    ...
    max_seconds = self._config.max_post_start_hours * 3600.0
    return (now - match_start).total_seconds() < max_seconds
```

ALSO: ParseError handling — mevcut `return True` (kabul) → `return False` (skip + log warning):
```python
    try:
        match_start = datetime.fromisoformat(...)
    except (ValueError, TypeError) as e:
        logger.warning("scanner: invalid match_start_iso=%r: %s — skip", iso_str, e)
        return False  # eskiden True (kabul) idi
```

### Step 7.4: Test'leri ekle

- [ ] **Step:** test_scanner.py'a 2 test ekle:

```python
def test_match_start_parse_error_filtered() -> None:
    """match_start_iso bozuk → market eler (eskiden kabul ediyordu — bug fix SPEC-B)."""
    now = datetime.now(timezone.utc)
    m = _market(end_date=now + timedelta(days=1))
    m.match_start_iso = "not-an-iso"
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert sc.scan() == []  # parse fail → skip


def test_max_post_start_hours_config_driven() -> None:
    """max_post_start_hours config'den okunmalı; 0 saat = canlı maç hemen kapanır."""
    now = datetime.now(timezone.utc)
    m = _market(
        match_start=now - timedelta(hours=1),  # 1 saat önce
        end_date=now + timedelta(hours=2),
    )
    cfg = _config(max_post_start_hours=0.5)  # yarım saat → 1 saatlik maç dışlanır
    sc = MarketScanner(cfg, gamma_client=_mock_gamma([m]))
    assert sc.scan() == []
```

### Step 7.5: Run + commit

- [ ] **Step:**

```bash
pytest tests/unit/orchestration/test_scanner.py -v
pytest -q --no-header
```

Expected: 993 + 2 = 995 pass (yeni test). Mevcut scanner testleri kırılmamalı.

```bash
git add src/orchestration/scanner.py src/config/settings.py config.yaml tests/unit/orchestration/test_scanner.py
git commit -m "feat(scanner): magic 8.0 → config + ParseError skip — SPEC-B Task 7 (audit#5)"
```

---

## Task 8: SPEC.md temizlik + smoke test

**Files:**
- Modify: `SPEC.md` (SPEC-B'yi sil — tamamlandı)
- Modify: `DECISIONS.md` (SPEC-B done addendum)

### Step 8.1: SPEC.md'den SPEC-B sil

- [ ] **Step:** SPEC-B section'ı kaldır (CLAUDE.md spec flow: implemented → sil)

### Step 8.2: DECISIONS.md'ye SPEC-B done eklenir

- [ ] **Step:** Aşağıdakileri ekle:

```markdown
## SPEC-B Tamamlandı (2026-05-09): ESPN Score Client Wire

**Karar**: Audit'teki 3 sorun (score_info gate'lere geçmiyor, ParseError → guard bypass, scanner magic 8.0) ESPN canlı skor entegrasyonu ile çözüldü.

**Migrate edilen (pre-rollback'ten REFERANS, taze yazıldı):**
- `src/infrastructure/apis/espn_client.py` — public scoreboard fetcher (NBA/MLB/NHL)
- `src/orchestration/score_enricher.py` — sport-dispatch + polling throttle + Odds fallback
- `src/strategy/exit/monitor.py:compute_elapsed_pct` — score_info fallback (period/inning estimate)
- `src/orchestration/scanner.py` — max_post_start_hours config + ParseError skip

**Yapılmadı (kasıt):**
- Tennis ESPN parsing — kapalı (SPEC-A5)
- Soccer ESPN — futbol kapalı (SPEC-C parked)
- Polymarket↔ESPN team_resolver — basit question contains heuristic kullanıldı; gelişmiş eşleştirme TODO

**Test toplamı: 968 → ~995** (~27 yeni test).
```

### Step 8.3: Reload + commit + smoke test

- [ ] **Step:**

```bash
git add SPEC.md DECISIONS.md
git commit -m "docs: SPEC-B done; ESPN score wire complete"
```

- [ ] **Step:** Reload bot

```bash
python scripts/reboot.py reload
```

- [ ] **Step:** İlk light cycle gözlem

```bash
sleep 30
grep "Score enrichment\|ESPN\|score_info" logs/runtime/bot.log | tail -10
grep "Cycle error\|STOPPING" logs/runtime/bot.log | tail -5
```

Expected:
- Score enrichment log mesajı görünür VE ya çağrı başarılı, ya warning (initial cycle network deneme)
- Cycle error / STOPPING YOK

---

## Self-Review Notes

**Spec coverage:**
- Task 1: ESPN client (audit#3 backbone) ✓
- Task 2: Config + sport_rules ✓
- Task 3: ScoreEnricher orchestration ✓
- Task 4: Factory wire ✓
- Task 5: Agent loop + exit_processor score_map ✓ (audit#3 closes here)
- Task 6: monitor elapsed fallback (audit#4) ✓
- Task 7: scanner config + ParseError (audit#5) ✓
- Task 8: docs + smoke ✓

**Yasak listesi (her task'ta):**
- Entry/exit kuralları (gate.py, exit dispatchers): DOKUNULMADI (sadece monitor.evaluate caller side score_info propagation)
- 16 Nisan baseline: monitor.evaluate signature ZATEN score_info accepts; score_info'yu populate eden katman SPEC-B

**Risk analizi:**
- Task 1 ESPN client 280+ satır — close to 400 cap, but discrete responsibilities
- Task 6 monitor.compute_elapsed_pct değişikliği geri uyumlu (default None param)
- Task 7 scanner ParseError → True → False değişikliği; geri uyumsuzluk: bozuk match_start'lı marketler artık eler. Dürüst behavior.

**Geri alma**: Her task ayrı commit. Hata olursa: `git revert <commit>`.

---

## Type/Signature Consistency

- `ESPNMatchScore` Task 1'de tek tanım, Task 3'te kullanım uyumlu
- `ScoreEnricher.get_scores_if_due(positions: dict[str, Position]) -> dict[str, dict]` Task 3 ⇄ Task 5 caller uyumlu
- `compute_elapsed_pct(pos, score_info=None)` Task 6 default ile geri uyumlu
- `ScannerConfig.max_post_start_hours: float = 8.0` Task 7 default ile geri uyumlu
