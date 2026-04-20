# ESPN Score Client + Agent Loop Wire — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ESPN API'yi primary skor kaynağı olarak entegre et, agent loop'a bağla, hockey K1-K4 kurallarını aktif hale getir.

**Architecture:** ESPN client (Infrastructure) → sport-dispatch ScoreEnricher (Orchestration) → mevcut exit_processor/monitor pipeline. Odds API fallback olarak kalır (tennis hariç — Odds API tennis'te skor vermiyor).

**Tech Stack:** Python 3.12+, httpx, dataclasses, pytest

**Spec:** `docs/superpowers/specs/2026-04-17-espn-score-client-wire-design.md`

---

## File Map

| Dosya | Aksiyon | Sorumluluk |
|---|---|---|
| `src/infrastructure/apis/espn_client.py` | **CREATE** | ESPN scoreboard HTTP + parse |
| `tests/unit/infrastructure/apis/test_espn_client.py` | **CREATE** | ESPN parse testleri |
| `src/config/sport_rules.py` | **MODIFY** | `score_source` + ESPN mapping per sport |
| `tests/unit/config/test_sport_rules.py` | **MODIFY** | Yeni field testleri |
| `src/config/settings.py` | **MODIFY** | ScoreConfig adaptif polling fields |
| `src/orchestration/score_enricher.py` | **MODIFY** | Sport-dispatch + ESPN primary + Odds fallback + adaptif poll |
| `tests/unit/orchestration/test_score_enricher.py` | **MODIFY** | Dispatch + fallback + adaptif testleri |
| `src/orchestration/agent.py` | **MODIFY** | AgentDeps + light cycle score_map inject |
| `src/orchestration/factory.py` | **MODIFY** | ESPNClient + ScoreEnricher wire |
| `config.yaml` | **MODIFY** | Yeni polling config |

---

## Task 1: ESPN Client — Parse + Fetch

**Files:**
- Create: `src/infrastructure/apis/espn_client.py`
- Create: `tests/unit/infrastructure/apis/test_espn_client.py`

- [ ] **Step 1: Write failing tests for ESPN parse**

```python
# tests/unit/infrastructure/apis/test_espn_client.py
"""ESPN scoreboard client testleri (SPEC-005)."""
from __future__ import annotations

from src.infrastructure.apis.espn_client import ESPNMatchScore, parse_scoreboard


# ── Hockey parse ──

_HOCKEY_RESPONSE = {
    "events": [{
        "name": "NHL Game",
        "groupings": [{
            "competitions": [{
                "id": "12345",
                "status": {
                    "period": 3,
                    "type": {"description": "Final", "completed": True, "state": "post"},
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "winner": True,
                        "athlete": {"displayName": "New York Rangers"},
                        "linescores": [{"value": 2.0}, {"value": 1.0}, {"value": 1.0}],
                    },
                    {
                        "homeAway": "away",
                        "winner": False,
                        "athlete": {"displayName": "Tampa Bay Lightning"},
                        "linescores": [{"value": 0.0}, {"value": 1.0}, {"value": 0.0}],
                    },
                ],
                "notes": [{"text": "Rangers 4, Lightning 1"}],
            }],
        }],
    }],
}


def test_parse_hockey_final_score() -> None:
    scores = parse_scoreboard(_HOCKEY_RESPONSE)
    assert len(scores) == 1
    s = scores[0]
    assert s.home_name == "New York Rangers"
    assert s.away_name == "Tampa Bay Lightning"
    assert s.home_score == 4
    assert s.away_score == 1
    assert s.is_completed is True
    assert s.period == "Final"


# ── Tennis parse ──

_TENNIS_RESPONSE = {
    "events": [{
        "name": "BMW Open",
        "groupings": [{
            "competitions": [{
                "id": "99999",
                "status": {
                    "period": 3,
                    "type": {"description": "Final", "completed": True, "state": "post"},
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "winner": True,
                        "athlete": {"displayName": "Karolina Muchova"},
                        "linescores": [{"value": 6.0}, {"value": 5.0}, {"value": 6.0}],
                    },
                    {
                        "homeAway": "away",
                        "winner": False,
                        "athlete": {"displayName": "Coco Gauff"},
                        "linescores": [{"value": 3.0}, {"value": 7.0}, {"value": 3.0}],
                    },
                ],
                "notes": [],
            }],
        }],
    }],
}


def test_parse_tennis_set_scores() -> None:
    scores = parse_scoreboard(_TENNIS_RESPONSE)
    assert len(scores) == 1
    s = scores[0]
    assert s.home_name == "Karolina Muchova"
    assert s.away_name == "Coco Gauff"
    assert s.linescores == [[6, 3], [5, 7], [6, 3]]
    # Tennis home_score = sets won
    assert s.home_score == 2  # Muchova won 2 sets
    assert s.away_score == 1  # Gauff won 1 set


# ── In progress ──

_LIVE_RESPONSE = {
    "events": [{
        "name": "Match",
        "groupings": [{
            "competitions": [{
                "id": "77777",
                "status": {
                    "period": 2,
                    "type": {"description": "In Progress", "completed": False, "state": "in"},
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "winner": False,
                        "athlete": {"displayName": "Player A"},
                        "linescores": [{"value": 6.0}, {"value": 3.0}],
                    },
                    {
                        "homeAway": "away",
                        "winner": False,
                        "athlete": {"displayName": "Player B"},
                        "linescores": [{"value": 4.0}, {"value": 5.0}],
                    },
                ],
                "notes": [],
            }],
        }],
    }],
}


def test_parse_live_match() -> None:
    scores = parse_scoreboard(_LIVE_RESPONSE)
    s = scores[0]
    assert s.is_live is True
    assert s.is_completed is False


# ── Empty / error ──

def test_parse_empty_response() -> None:
    assert parse_scoreboard({}) == []
    assert parse_scoreboard({"events": []}) == []


def test_parse_no_competitors() -> None:
    data = {"events": [{"name": "X", "groupings": [{"competitions": [{"id": "1", "status": {"type": {"description": "Final", "completed": True, "state": "post"}, "period": 1}, "competitors": [], "notes": []}]}]}]}
    assert parse_scoreboard(data) == []
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
python -m pytest tests/unit/infrastructure/apis/test_espn_client.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.infrastructure.apis.espn_client'`

- [ ] **Step 3: Implement espn_client.py**

```python
# src/infrastructure/apis/espn_client.py
"""ESPN public scoreboard client (SPEC-005).

Ücretsiz, API key gerektirmez. Primary skor kaynağı.
Hockey, MLB, NBA, Tennis (ATP/WTA) destekler.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://site.api.espn.com/apis/site/v2/sports"
_TIMEOUT = 10


@dataclass
class ESPNMatchScore:
    """Tek maçın ESPN skor verisi."""

    event_id: str
    home_name: str
    away_name: str
    home_score: int | None
    away_score: int | None
    period: str  # "Final", "In Progress", ""
    is_completed: bool
    is_live: bool
    last_updated: str
    linescores: list[list[int]] = field(default_factory=list)


def parse_scoreboard(data: dict) -> list[ESPNMatchScore]:
    """ESPN scoreboard JSON → ESPNMatchScore listesi.

    ESPN yapısı: events[] → groupings[] → competitions[] → competitors[]
    """
    results: list[ESPNMatchScore] = []
    for event in data.get("events", []):
        for group in event.get("groupings", []):
            for comp in group.get("competitions", []):
                parsed = _parse_competition(comp)
                if parsed is not None:
                    results.append(parsed)
    return results


def _parse_competition(comp: dict) -> ESPNMatchScore | None:
    """Tek competition → ESPNMatchScore."""
    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        return None

    status = comp.get("status", {})
    status_type = status.get("type", {})
    state = status_type.get("state", "")
    description = status_type.get("description", "")
    is_completed = status_type.get("completed", False)
    is_live = state == "in"

    home = away = None
    for c in competitors:
        if c.get("homeAway") == "home":
            home = c
        else:
            away = c
    if home is None or away is None:
        # Fallback: first=home, second=away
        home, away = competitors[0], competitors[1]

    home_name = home.get("athlete", {}).get("displayName", "")
    away_name = away.get("athlete", {}).get("displayName", "")

    home_ls = [int(s.get("value", 0)) for s in home.get("linescores", [])]
    away_ls = [int(s.get("value", 0)) for s in away.get("linescores", [])]

    # linescores paired: [[home_set1, away_set1], [home_set2, away_set2], ...]
    linescores = list(zip(home_ls, away_ls)) if home_ls else []
    linescores = [list(pair) for pair in linescores]

    # Total score: sum of linescores (hockey: total goals, tennis: sets won)
    home_score = _compute_total(home_ls, away_ls, is_tennis=False)
    away_score = _compute_total(away_ls, home_ls, is_tennis=False)

    # Tennis: score = sets won (not total games)
    # Detect tennis by checking if any linescore value >= 6 (tennis set)
    if home_ls and max(max(home_ls, default=0), max(away_ls, default=0)) >= 6:
        home_score = sum(1 for h, a in zip(home_ls, away_ls) if h > a)
        away_score = sum(1 for h, a in zip(home_ls, away_ls) if a > h)

    return ESPNMatchScore(
        event_id=comp.get("id", ""),
        home_name=home_name,
        away_name=away_name,
        home_score=home_score if home_ls else None,
        away_score=away_score if away_ls else None,
        period=description,
        is_completed=is_completed,
        is_live=is_live,
        last_updated="",
        linescores=linescores,
    )


def _compute_total(scores: list[int], opp_scores: list[int], is_tennis: bool) -> int:
    """Linescore'lardan toplam skor hesapla."""
    if is_tennis:
        return sum(1 for s, o in zip(scores, opp_scores) if s > o)
    return sum(scores)


def fetch_scoreboard(sport: str, league: str, date: str | None = None) -> list[ESPNMatchScore]:
    """ESPN scoreboard'dan maç skorlarını çek.

    Args:
        sport: ESPN sport slug ("hockey", "tennis", "baseball", "basketball")
        league: ESPN league slug ("nhl", "atp", "wta", "mlb", "nba")
        date: YYYYMMDD formatında tarih (None = bugün)

    Returns:
        ESPNMatchScore listesi. Hata → boş liste.
    """
    url = f"{_BASE}/{sport}/{league}/scoreboard"
    params = {}
    if date:
        params["dates"] = date
    try:
        resp = httpx.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        return parse_scoreboard(resp.json())
    except Exception as exc:
        logger.warning("ESPN fetch failed (%s/%s): %s", sport, league, exc)
        return []
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
python -m pytest tests/unit/infrastructure/apis/test_espn_client.py -v
```
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/apis/espn_client.py tests/unit/infrastructure/apis/test_espn_client.py
git commit -m "feat(infra): ESPN scoreboard client + parse (SPEC-005 Task 1)"
```

---

## Task 2: Sport Rules — score_source Config

**Files:**
- Modify: `src/config/sport_rules.py`
- Modify: `tests/unit/config/test_sport_rules.py`

- [ ] **Step 1: Write failing test**

```python
# Append to tests/unit/config/test_sport_rules.py

def test_get_score_source_nhl() -> None:
    from src.config.sport_rules import get_sport_rule
    assert get_sport_rule("nhl", "score_source") == "espn"


def test_get_espn_mapping_nhl() -> None:
    from src.config.sport_rules import get_sport_rule
    assert get_sport_rule("nhl", "espn_sport") == "hockey"
    assert get_sport_rule("nhl", "espn_league") == "nhl"


def test_get_espn_mapping_tennis() -> None:
    from src.config.sport_rules import get_sport_rule
    assert get_sport_rule("tennis", "score_source") == "espn"
    assert get_sport_rule("tennis", "espn_sport") == "tennis"
    assert get_sport_rule("tennis", "espn_league") == "atp"


def test_get_score_source_mlb() -> None:
    from src.config.sport_rules import get_sport_rule
    assert get_sport_rule("mlb", "score_source") == "espn"


def test_get_score_source_unknown_returns_none() -> None:
    from src.config.sport_rules import get_sport_rule
    assert get_sport_rule("unknown_sport", "score_source") is None
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
python -m pytest tests/unit/config/test_sport_rules.py::test_get_score_source_nhl -v
```
Expected: FAIL — `score_source` key doesn't exist yet

- [ ] **Step 3: Add score_source + ESPN mapping to sport_rules.py**

In `src/config/sport_rules.py`, add to each sport dict in SPORT_RULES:

```python
"nba": {
    "stop_loss_pct": 0.35,
    "match_duration_hours": 2.5,
    "halftime_exit": True,
    "halftime_exit_deficit": 15,
    "score_source": "espn",
    "espn_sport": "basketball",
    "espn_league": "nba",
},
"nfl": {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 3.25,
    "halftime_exit": True,
    "halftime_exit_deficit": 14,
    "score_source": "espn",
    "espn_sport": "football",
    "espn_league": "nfl",
},
"nhl": {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 2.5,
    "period_exit": True,
    "period_exit_deficit": 3,
    "late_deficit": 2,
    "late_elapsed_gate": 0.67,
    "score_price_confirm": 0.35,
    "final_elapsed_gate": 0.92,
    "score_source": "espn",
    "espn_sport": "hockey",
    "espn_league": "nhl",
},
"mlb": {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 3.0,
    "inning_exit": True,
    "inning_exit_deficit": 5,
    "inning_exit_after": 6,
    "score_source": "espn",
    "espn_sport": "baseball",
    "espn_league": "mlb",
},
"tennis": {
    "stop_loss_pct": 0.35,
    "match_duration_hours": 2.5,
    "match_duration_hours_bo3": 1.75,
    "match_duration_hours_bo5": 3.5,
    "set_exit": True,
    "score_source": "espn",
    "espn_sport": "tennis",
    "espn_league": "atp",
},
"golf": {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 4.0,
    "playoff_aware": True,
},
```

Note: golf has no score_source (scores not available).

- [ ] **Step 4: Run tests — verify PASS**

```bash
python -m pytest tests/unit/config/test_sport_rules.py -v
```
Expected: All PASS (existing + 5 new)

- [ ] **Step 5: Commit**

```bash
git add src/config/sport_rules.py tests/unit/config/test_sport_rules.py
git commit -m "feat(config): score_source + ESPN mapping per sport (SPEC-005 Task 2)"
```

---

## Task 3: Settings — Adaptif Polling Config

**Files:**
- Modify: `src/config/settings.py:155-159`
- Modify: `config.yaml`

- [ ] **Step 1: Update ScoreConfig in settings.py**

Replace the existing `ScoreConfig` class (lines 155-159) with:

```python
class ScoreConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    poll_normal_sec: int = 60
    poll_critical_sec: int = 30
    critical_price_threshold: float = 0.35
    match_window_hours: float = 4.0
```

- [ ] **Step 2: Update config.yaml score section**

Replace the existing `score:` block with:

```yaml
score:
  enabled: true
  poll_normal_sec: 60
  poll_critical_sec: 30
  critical_price_threshold: 0.35
  match_window_hours: 4
```

- [ ] **Step 3: Run existing config tests**

```bash
python -m pytest tests/unit/config/test_settings.py -v
```
Expected: All PASS (backward compatible — new fields have defaults)

- [ ] **Step 4: Commit**

```bash
git add src/config/settings.py config.yaml
git commit -m "feat(config): adaptif score polling config (SPEC-005 Task 3)"
```

---

## Task 4: ScoreEnricher — Sport-Dispatch + ESPN Primary + Fallback

**Files:**
- Modify: `src/orchestration/score_enricher.py`
- Modify: `tests/unit/orchestration/test_score_enricher.py`

- [ ] **Step 1: Write failing tests for ESPN dispatch + fallback + adaptif polling**

Append to `tests/unit/orchestration/test_score_enricher.py`:

```python
from src.infrastructure.apis.espn_client import ESPNMatchScore


class _FakeESPN:
    """Mock ESPN client."""
    def __init__(self, scores: list[ESPNMatchScore] | None = None, fail: bool = False) -> None:
        self.call_count = 0
        self._scores = scores or []
        self._fail = fail

    def fetch(self, sport: str, league: str, date: str | None = None) -> list[ESPNMatchScore]:
        self.call_count += 1
        if self._fail:
            return []
        return self._scores


def _espn_score(
    home: str = "New York Rangers",
    away: str = "Tampa Bay Lightning",
    h_score: int = 3,
    a_score: int = 1,
) -> ESPNMatchScore:
    return ESPNMatchScore(
        event_id="e1", home_name=home, away_name=away,
        home_score=h_score, away_score=a_score,
        period="2nd", is_completed=False, is_live=True,
        last_updated="", linescores=[],
    )


# ── ESPN primary dispatch ──

def test_enricher_uses_espn_for_nhl() -> None:
    espn = _FakeESPN([_espn_score()])
    odds = _FakeClient()  # existing mock
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        poll_normal_sec=0, poll_critical_sec=0,
    )
    pos = _pos(cid="c1", question="Rangers vs. Lightning", sport_tag="nhl", hours_ago=1.0)
    result = enricher.get_scores_if_due({"c1": pos})
    assert espn.call_count >= 1
    assert odds.call_count == 0  # ESPN worked, no fallback
    assert "c1" in result
    assert result["c1"]["available"]


# ── Fallback: ESPN fails → Odds API ──

def test_enricher_falls_back_to_odds_api() -> None:
    espn = _FakeESPN(fail=True)
    odds_data = [
        {"id": "e1", "home_team": "New York Rangers", "away_team": "Tampa Bay Lightning",
         "scores": [{"name": "New York Rangers", "score": "3"}, {"name": "Tampa Bay Lightning", "score": "1"}],
         "completed": False, "last_update": ""},
    ]
    odds = _FakeClient(data=odds_data)
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        poll_normal_sec=0, poll_critical_sec=0,
    )
    pos = _pos(cid="c1", question="Rangers vs. Lightning", sport_tag="nhl", hours_ago=1.0)
    result = enricher.get_scores_if_due({"c1": pos})
    assert espn.call_count >= 1  # ESPN tried
    assert odds.call_count >= 1  # Fallback called
    assert "c1" in result


# ── Tennis: no Odds API fallback ──

def test_enricher_tennis_no_fallback() -> None:
    espn = _FakeESPN(fail=True)
    odds = _FakeClient()
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        poll_normal_sec=0, poll_critical_sec=0,
    )
    pos = _pos(cid="c1", question="Muchova vs. Gauff", sport_tag="tennis", hours_ago=1.0)
    result = enricher.get_scores_if_due({"c1": pos})
    assert odds.call_count == 0  # Tennis: no Odds API fallback
    assert "c1" not in result


# ── Adaptif polling ──

def test_enricher_adaptif_polling_critical() -> None:
    """Fiyat < threshold → poll_critical_sec kullanılır."""
    espn = _FakeESPN([_espn_score()])
    odds = _FakeClient()
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        poll_normal_sec=60, poll_critical_sec=30,
        critical_price_threshold=0.35,
    )
    pos = _pos(cid="c1", sport_tag="nhl", hours_ago=1.0)
    pos.current_price = 0.20  # critical
    enricher.get_scores_if_due({"c1": pos})
    assert enricher._poll_sec == 30  # adapted to critical
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
python -m pytest tests/unit/orchestration/test_score_enricher.py::test_enricher_uses_espn_for_nhl -v
```
Expected: FAIL — ScoreEnricher doesn't accept `espn_client` parameter yet

- [ ] **Step 3: Rewrite ScoreEnricher with sport-dispatch**

Replace `src/orchestration/score_enricher.py` with the updated version. Key changes:
- Constructor accepts `espn_client` + `odds_client`
- `_refresh_scores` dispatches to ESPN or Odds API per sport
- Adaptif polling: `_effective_poll_sec()` checks min current_price
- `_build_score_info` adds `linescores` field from ESPN data
- Tennis league resolve: slug `wta-*` → `"wta"`, else `"atp"`

```python
"""Score enricher — ESPN primary + Odds API fallback (SPEC-005).

Sport-dispatch: her sport için score_source config'den okunur.
Adaptif polling: fiyat < threshold → daha sık poll.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

from src.config.sport_rules import _normalize, get_sport_rule
from src.infrastructure.apis.espn_client import ESPNMatchScore, fetch_scoreboard
from src.infrastructure.apis.score_client import MatchScore, fetch_scores
from src.models.position import Position
from src.strategy.enrichment.question_parser import extract_teams

logger = logging.getLogger(__name__)


def _is_within_match_window(pos: Position, window_hours: float) -> bool:
    if not pos.match_start_iso:
        return False
    try:
        start = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    now = datetime.now(timezone.utc)
    diff_hours = abs((now - start).total_seconds()) / 3600.0
    return diff_hours <= window_hours


def _team_match(pos_team: str, api_team: str) -> bool:
    if not pos_team or not api_team:
        return False
    p = pos_team.lower().strip()
    a = api_team.lower().strip()
    if p == a:
        return True
    if p in a or a in p:
        return True
    p_last = p.rsplit(maxsplit=1)[-1] if " " in p else p
    a_last = a.rsplit(maxsplit=1)[-1] if " " in a else a
    return p_last == a_last and len(p_last) >= 3


def _find_espn_match(pos: Position, scores: list[ESPNMatchScore]) -> ESPNMatchScore | None:
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None
    for ms in scores:
        home_a = _team_match(team_a, ms.home_name)
        home_b = _team_match(team_b or "", ms.home_name) if team_b else False
        away_a = _team_match(team_a, ms.away_name)
        away_b = _team_match(team_b or "", ms.away_name) if team_b else False
        if (home_a and away_b) or (home_b and away_a) or (home_a or away_a):
            return ms
    return None


def _find_odds_match(pos: Position, scores: list[MatchScore]) -> MatchScore | None:
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None
    for ms in scores:
        home_a = _team_match(team_a, ms.home_team)
        home_b = _team_match(team_b or "", ms.home_team) if team_b else False
        away_a = _team_match(team_a, ms.away_team)
        away_b = _team_match(team_b or "", ms.away_team) if team_b else False
        if (home_a and away_b) or (home_b and away_a) or (home_a or away_a):
            return ms
    return None


def _build_espn_score_info(pos: Position, ms: ESPNMatchScore) -> dict:
    if ms.home_score is None or ms.away_score is None:
        return {"available": False}

    team_a, _ = extract_teams(pos.question)
    a_is_home = _team_match(team_a or "", ms.home_name)

    if a_is_home:
        yes_score, no_score = ms.home_score, ms.away_score
    else:
        yes_score, no_score = ms.away_score, ms.home_score

    if pos.direction == "BUY_YES":
        our_score, opp_score = yes_score, no_score
    else:
        our_score, opp_score = no_score, yes_score

    deficit = opp_score - our_score
    return {
        "available": True,
        "our_score": our_score,
        "opp_score": opp_score,
        "deficit": deficit,
        "period": ms.period,
        "map_diff": -deficit,
        "linescores": ms.linescores,
    }


def _build_odds_score_info(pos: Position, ms: MatchScore) -> dict:
    if ms.home_score is None or ms.away_score is None:
        return {"available": False}

    team_a, _ = extract_teams(pos.question)
    a_is_home = _team_match(team_a or "", ms.home_team)

    if a_is_home:
        yes_score, no_score = ms.home_score, ms.away_score
    else:
        yes_score, no_score = ms.away_score, ms.home_score

    if pos.direction == "BUY_YES":
        our_score, opp_score = yes_score, no_score
    else:
        our_score, opp_score = no_score, yes_score

    deficit = opp_score - our_score
    return {
        "available": True,
        "our_score": our_score,
        "opp_score": opp_score,
        "deficit": deficit,
        "period": ms.period,
        "map_diff": -deficit,
        "linescores": [],
    }


def _resolve_tennis_league(slug: str) -> str:
    if slug and slug.startswith("wta"):
        return "wta"
    return "atp"


class ScoreEnricher:
    """ESPN primary + Odds API fallback score enricher."""

    def __init__(
        self,
        espn_client=None,
        odds_client=None,
        poll_normal_sec: int = 60,
        poll_critical_sec: int = 30,
        critical_price_threshold: float = 0.35,
        match_window_hours: float = 4.0,
    ) -> None:
        self._espn = espn_client
        self._odds = odds_client
        self._poll_normal = poll_normal_sec
        self._poll_critical = poll_critical_sec
        self._critical_threshold = critical_price_threshold
        self._window_hours = match_window_hours
        self._last_poll_ts: float = 0.0
        self._poll_sec: int = poll_normal_sec
        self._espn_cache: dict[str, list[ESPNMatchScore]] = {}
        self._odds_cache: dict[str, list[MatchScore]] = {}

    def get_scores_if_due(self, positions: dict[str, Position]) -> dict[str, dict]:
        self._adapt_poll_interval(positions)
        now = time.monotonic()
        if (now - self._last_poll_ts) < self._poll_sec:
            return self._match_all(positions)

        self._last_poll_ts = now
        self._refresh(positions)
        return self._match_all(positions)

    def _adapt_poll_interval(self, positions: dict[str, Position]) -> None:
        min_price = min(
            (p.current_price for p in positions.values() if p.current_price > 0),
            default=1.0,
        )
        if min_price <= self._critical_threshold:
            self._poll_sec = self._poll_critical
        else:
            self._poll_sec = self._poll_normal

    def _refresh(self, positions: dict[str, Position]) -> None:
        espn_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        odds_fallback_keys: set[str] = set()

        for pos in positions.values():
            if not _is_within_match_window(pos, self._window_hours):
                continue
            tag = _normalize(pos.sport_tag)
            if not tag:
                continue
            source = get_sport_rule(tag, "score_source")
            if source != "espn":
                continue
            espn_sport = get_sport_rule(tag, "espn_sport", "")
            espn_league = get_sport_rule(tag, "espn_league", "")
            if tag == "tennis":
                espn_league = _resolve_tennis_league(pos.slug)
            if espn_sport and espn_league:
                espn_groups[(espn_sport, espn_league)].append(tag)

        self._espn_cache.clear()
        self._odds_cache.clear()

        for (sport, league), tags in espn_groups.items():
            cache_key = f"{sport}/{league}"
            if self._espn is not None:
                scores = self._espn.fetch(sport, league)
            else:
                scores = fetch_scoreboard(sport, league)
            if scores:
                self._espn_cache[cache_key] = scores
                logger.info("ESPN score: %s/%s → %d matches", sport, league, len(scores))
            else:
                logger.warning("ESPN failed: %s/%s — trying Odds API fallback", sport, league)
                tag = tags[0] if tags else ""
                if tag != "tennis" and self._odds is not None:
                    odds_key = self._sport_tag_to_odds_key(tag)
                    odds_scores = fetch_scores(self._odds, odds_key)
                    if odds_scores:
                        self._odds_cache[odds_key] = odds_scores
                        logger.info("Odds fallback: %s → %d events", odds_key, len(odds_scores))

    def _match_all(self, positions: dict[str, Position]) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for cid, pos in positions.items():
            info = self._match_position(pos)
            if info:
                result[cid] = info
        return result

    def _match_position(self, pos: Position) -> dict | None:
        tag = _normalize(pos.sport_tag)
        if not tag:
            return None
        espn_sport = get_sport_rule(tag, "espn_sport", "")
        espn_league = get_sport_rule(tag, "espn_league", "")
        if tag == "tennis":
            espn_league = _resolve_tennis_league(pos.slug)

        # Try ESPN first
        cache_key = f"{espn_sport}/{espn_league}"
        espn_scores = self._espn_cache.get(cache_key, [])
        if espn_scores:
            ms = _find_espn_match(pos, espn_scores)
            if ms:
                return _build_espn_score_info(pos, ms)

        # Try Odds API fallback
        if tag != "tennis":
            odds_key = self._sport_tag_to_odds_key(tag)
            odds_scores = self._odds_cache.get(odds_key, [])
            if odds_scores:
                ms = _find_odds_match(pos, odds_scores)
                if ms:
                    return _build_odds_score_info(pos, ms)

        return None

    @staticmethod
    def _sport_tag_to_odds_key(sport_tag: str) -> str:
        tag = (sport_tag or "").lower().strip()
        mapping = {
            "nhl": "icehockey_nhl",
            "ahl": "icehockey_ahl",
            "hockey": "icehockey_nhl",
            "nba": "basketball_nba",
            "mlb": "baseball_mlb",
            "nfl": "americanfootball_nfl",
        }
        return mapping.get(tag, f"icehockey_{tag}")
```

- [ ] **Step 4: Update existing enricher tests for new constructor**

The existing `test_enricher_polls_only_when_due` and `test_enricher_no_live_positions_no_call` use the old `ScoreEnricher(client, poll_interval_sec=...)` signature. Update them:

```python
# Replace existing test_enricher_polls_only_when_due:
def test_enricher_polls_only_when_due() -> None:
    espn = _FakeESPN([])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=120, poll_critical_sec=120,
    )
    pos = _pos(hours_ago=1.0)
    positions = {"c1": pos}

    enricher.get_scores_if_due(positions)
    assert espn.call_count >= 1

    # 120 sn geçmeden tekrar çağır — API çağrılmamalı
    old_count = espn.call_count
    enricher.get_scores_if_due(positions)
    assert espn.call_count == old_count  # cache'den döner


# Replace existing test_enricher_no_live_positions_no_call:
def test_enricher_no_live_positions_no_call() -> None:
    espn = _FakeESPN([])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=120, poll_critical_sec=120,
    )
    pos = _pos(hours_ago=10.0)  # pencere dışı
    positions = {"c1": pos}

    enricher.get_scores_if_due(positions)
    assert espn.call_count == 0  # API hiç çağrılmadı
```

- [ ] **Step 5: Run all enricher tests**

```bash
python -m pytest tests/unit/orchestration/test_score_enricher.py -v
```
Expected: All PASS (updated existing + 4 new)

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest tests/ -q
```
Expected: All PASS (no regressions)

- [ ] **Step 7: Commit**

```bash
git add src/orchestration/score_enricher.py tests/unit/orchestration/test_score_enricher.py
git commit -m "feat(orchestration): ESPN sport-dispatch + fallback + adaptif polling (SPEC-005 Task 4)"
```

---

## Task 5: Agent Loop Wire — Factory + Light Cycle

**Files:**
- Modify: `src/orchestration/agent.py:34-50`
- Modify: `src/orchestration/factory.py:35-136`

- [ ] **Step 1: Add score_enricher to AgentDeps**

In `src/orchestration/agent.py`, add import and field:

```python
# Add import at top (after existing imports):
from src.orchestration.score_enricher import ScoreEnricher

# Add field to AgentDeps (after price_feed line 49):
    score_enricher: ScoreEnricher | None = None
```

- [ ] **Step 2: Wire score_map in light cycle**

In `src/orchestration/agent.py`, replace line 83:

```python
# Old:
                    self._exit.run_light()

# New:
                    score_map = {}
                    if self.deps.score_enricher is not None:
                        score_map = self.deps.score_enricher.get_scores_if_due(
                            self.deps.state.portfolio.positions,
                        )
                    self._exit.run_light(score_map=score_map)
```

- [ ] **Step 3: Create ScoreEnricher in factory.py**

In `src/orchestration/factory.py`, add import:

```python
from src.infrastructure.apis.espn_client import ESPNMatchScore, fetch_scoreboard
from src.orchestration.score_enricher import ScoreEnricher
```

Before the `deps = AgentDeps(...)` block (around line 111), add:

```python
    # Score enricher: ESPN primary + Odds API fallback
    score_enricher: ScoreEnricher | None = None
    if cfg.score.enabled:
        # ESPN client wrapper — passed as object with .fetch method
        class _ESPNBridge:
            @staticmethod
            def fetch(sport: str, league: str, date: str | None = None) -> list:
                return fetch_scoreboard(sport, league, date)

        score_enricher = ScoreEnricher(
            espn_client=_ESPNBridge(),
            odds_client=odds,
            poll_normal_sec=cfg.score.poll_normal_sec,
            poll_critical_sec=cfg.score.poll_critical_sec,
            critical_price_threshold=cfg.score.critical_price_threshold,
            match_window_hours=cfg.score.match_window_hours,
        )
```

Add `score_enricher=score_enricher,` to the AgentDeps constructor call.

- [ ] **Step 4: Run full test suite**

```bash
python -m pytest tests/ -q
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/agent.py src/orchestration/factory.py
git commit -m "feat(wire): score_enricher → agent loop (SPEC-005 Task 5)"
```

---

## Task 6: Integration Smoke Test + Final Validation

**Files:**
- Create: `tests/integration/test_espn_live.py`

- [ ] **Step 1: Write integration smoke test**

```python
# tests/integration/test_espn_live.py
"""ESPN API smoke test — gerçek API çağrısı, CI'da skip."""
from __future__ import annotations

import pytest

from src.infrastructure.apis.espn_client import fetch_scoreboard


@pytest.mark.skipif(True, reason="Manuel çalıştır: pytest tests/integration/ -k espn --no-header -rN")
def test_espn_nhl_scoreboard_returns_data() -> None:
    scores = fetch_scoreboard("hockey", "nhl")
    # NHL sezonu aktifse en az 1 maç olmalı
    assert isinstance(scores, list)
    if scores:
        s = scores[0]
        assert s.home_name
        assert s.away_name


@pytest.mark.skipif(True, reason="Manuel çalıştır")
def test_espn_tennis_atp_scoreboard() -> None:
    scores = fetch_scoreboard("tennis", "atp")
    assert isinstance(scores, list)
    if scores:
        s = scores[0]
        assert s.home_name
        # Tennis: linescores should have set data
        if s.linescores:
            assert len(s.linescores[0]) == 2  # [home_games, away_games]
```

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest tests/ -q
```
Expected: All PASS (integration tests skipped by default)

- [ ] **Step 3: Run integration test manually (optional)**

```bash
python -m pytest tests/integration/test_espn_live.py -v --no-header -rN -k espn -p no:skip
```

- [ ] **Step 4: Final commit**

```bash
git add tests/integration/test_espn_live.py
git commit -m "test(integration): ESPN live smoke test (SPEC-005 Task 6)"
```

---

## Task 7: TDD.md + SPEC Status Update

**Files:**
- Modify: `TDD.md`
- Modify: `SPEC.md`

- [ ] **Step 1: Update TDD.md §6.9 with ESPN info**

Add after the existing §6.9b catastrophic watch section:

```markdown
#### 6.9c Score Polling Altyapısı (SPEC-005)

**Primary:** ESPN public API (`site.api.espn.com`) — ücretsiz, API key gereksiz.
Hockey (gol), Tennis (set+game), MLB (koşu), NBA (sayı) skor verir.

**Fallback:** Odds API `/scores` — hockey/MLB/NBA için çalışır, tennis'te skor vermiyor.

**Adaptif polling:** Normal 60s, fiyat ≤ 35¢ → 30s. Config: `config.yaml → score`.

**Kill switch:** `score.enabled: false` → tüm skor polling durur.
```

- [ ] **Step 2: Update SPEC.md status**

Change SPEC-005 status from DRAFT to IMPLEMENTED.

- [ ] **Step 3: Commit**

```bash
git add TDD.md SPEC.md
git commit -m "docs: SPEC-005 ESPN score wire — TDD + SPEC status update"
```
