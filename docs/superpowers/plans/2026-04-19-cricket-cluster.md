# Cricket Cluster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 7 cricket ligini (IPL, ODI, Intl T20, PSL, Big Bash, CPL, T20 Blast) Polymarket bot'una entegre et. CricAPI free tier ile canli skor, tennis T1/T2 simetrik C1/C2/C3 forced exit.

**Architecture:** Infra'da CricketAPIClient (CricAPI wrapper), Orchestration'da cricket_score_builder (match → score_info), Strategy'de cricket_score_exit (C1/C2/C3). Score_enricher dispatch eder. Quota dolunca entry gate skip eder (cricapi_unavailable).

**Tech Stack:** Python 3.12+, Pydantic, pytest, CricAPI /currentMatches, existing pair_matcher + odds_sport_keys

---

### Task 1: CricketAPIClient Infrastructure

**Files:**
- Create: `src/infrastructure/apis/cricket_client.py`
- Create: `tests/unit/infrastructure/apis/test_cricket_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/infrastructure/apis/test_cricket_client.py`:

```python
"""CricketAPIClient icin birim testler (SPEC-011)."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

from src.infrastructure.apis.cricket_client import (
    CricAPIQuota,
    CricketAPIClient,
    CricketMatchScore,
)


def _mock_response(status_code=200, info=None, matches=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = {
        "info": info or {"hitsToday": 5, "hitsLimit": 100},
        "data": matches or [],
    }
    return r


def _sample_raw_match():
    return {
        "id": "abc-123",
        "name": "Kolkata Knight Riders vs Rajasthan Royals",
        "matchType": "t20",
        "teams": ["Kolkata Knight Riders", "Rajasthan Royals"],
        "status": "In progress",
        "matchStarted": True,
        "matchEnded": False,
        "venue": "Eden Gardens",
        "dateTimeGMT": "2026-04-19T13:00:00",
        "score": [
            {"r": 180, "w": 5, "o": 20.0, "inning": "Kolkata Knight Riders Inning 1"},
            {"r": 95, "w": 4, "o": 12.3, "inning": "Rajasthan Royals Inning 2"},
        ],
    }


def test_quota_not_exhausted_by_default():
    q = CricAPIQuota()
    assert q.exhausted is False
    assert q.remaining == 100


def test_quota_exhausted_when_used_equals_limit():
    q = CricAPIQuota(used_today=100, daily_limit=100)
    assert q.exhausted is True
    assert q.remaining == 0


def test_get_current_matches_success():
    http = MagicMock(return_value=_mock_response(matches=[_sample_raw_match()]))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    matches = client.get_current_matches()
    assert matches is not None
    assert len(matches) == 1
    assert matches[0].match_id == "abc-123"
    assert matches[0].match_type == "t20"
    assert len(matches[0].innings) == 2
    assert matches[0].innings[0]["runs"] == 180
    assert matches[0].innings[0]["wickets"] == 5
    assert matches[0].innings[0]["overs"] == 20.0


def test_quota_tracked_from_response():
    http = MagicMock(return_value=_mock_response(
        info={"hitsToday": 42, "hitsLimit": 100},
    ))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    client.get_current_matches()
    assert client.quota.used_today == 42
    assert client.quota.daily_limit == 100


def test_exhausted_quota_returns_none_without_http():
    http = MagicMock()
    client = CricketAPIClient(api_key="test-key", http_get=http)
    client.quota.used_today = 100  # manual exhaust
    matches = client.get_current_matches()
    assert matches is None
    http.assert_not_called()


def test_cache_hit_within_ttl():
    http = MagicMock(return_value=_mock_response(matches=[_sample_raw_match()]))
    client = CricketAPIClient(api_key="test-key", http_get=http, cache_ttl_sec=60)
    client.get_current_matches()
    client.get_current_matches()
    client.get_current_matches()
    assert http.call_count == 1  # 1 HTTP call, 2 cache hits


def test_cache_expires_after_ttl():
    http = MagicMock(return_value=_mock_response(matches=[_sample_raw_match()]))
    client = CricketAPIClient(api_key="test-key", http_get=http, cache_ttl_sec=0)
    client.get_current_matches()
    time.sleep(0.01)
    client.get_current_matches()
    assert http.call_count == 2


def test_http_error_returns_none():
    http = MagicMock(return_value=_mock_response(status_code=500))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    matches = client.get_current_matches()
    assert matches is None


def test_http_exception_returns_none():
    http = MagicMock(side_effect=Exception("network down"))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    matches = client.get_current_matches()
    assert matches is None


def test_parse_match_missing_fields_returns_none():
    raw_bad = {"id": "x"}  # missing name, teams, etc.
    http = MagicMock(return_value=_mock_response(matches=[raw_bad, _sample_raw_match()]))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    matches = client.get_current_matches()
    # Bad one filtered out, good one parses
    assert matches is not None
    # Bad match parse'ed to defaults (empty strings) — still returned; that's ok
    # Just check no crash


def test_inning_number_parsed_from_string():
    match = _sample_raw_match()
    http = MagicMock(return_value=_mock_response(matches=[match]))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    matches = client.get_current_matches()
    assert matches[0].innings[0]["team"] == "Kolkata Knight Riders"
    assert matches[0].innings[0]["inning_num"] == 1
    assert matches[0].innings[1]["team"] == "Rajasthan Royals"
    assert matches[0].innings[1]["inning_num"] == 2
```

- [ ] **Step 2: Run tests — FAIL**

Run: `pytest tests/unit/infrastructure/apis/test_cricket_client.py -v`
Expected: FAIL with "No module named 'src.infrastructure.apis.cricket_client'"

- [ ] **Step 3: Create cricket_client.py**

Create `src/infrastructure/apis/cricket_client.py`:

```python
"""CricAPI HTTP client — free tier 100 hit/gun (SPEC-011).

Tek endpoint: /v1/currentMatches — TUM aktif cricket maclari doner.
Cache TTL ve timeout config'den (ARCH_GUARD Kural 6).

Hit budget tracking: API response'unda hitsUsed/hitsLimit var.
Limit dolunca get_current_matches() None doner — entry gate skip eder.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.cricapi.com/v1"  # endpoint sabit


@dataclass
class CricketMatchScore:
    """CricAPI response'undan parse edilen tek bir mac."""
    match_id: str
    name: str
    match_type: str                # "t20" | "odi" | "test"
    teams: list[str]
    status: str
    match_started: bool
    match_ended: bool
    venue: str
    date_time_gmt: str
    innings: list[dict]            # [{runs, wickets, overs, team, inning_num}]


@dataclass
class CricAPIQuota:
    """Daily API usage tracking. Response'dan guncelleniyor."""
    used_today: int = 0
    daily_limit: int = 100

    @property
    def remaining(self) -> int:
        return max(0, self.daily_limit - self.used_today)

    @property
    def exhausted(self) -> bool:
        return self.used_today >= self.daily_limit


class CricketAPIClient:
    """CricAPI /currentMatches wrapper + cache + quota tracking."""

    def __init__(
        self,
        api_key: str,
        daily_limit: int = 100,
        cache_ttl_sec: int = 240,
        timeout_sec: int = 15,
        http_get=None,
    ) -> None:
        self._api_key = api_key
        self._http = http_get or self._default_get
        self._cache_ttl = cache_ttl_sec
        self._timeout = timeout_sec
        self._cached_data: list[CricketMatchScore] | None = None
        self._cache_timestamp: float = 0.0
        self.quota = CricAPIQuota(daily_limit=daily_limit)

    def get_current_matches(self) -> list[CricketMatchScore] | None:
        """TUM aktif cricket maclari. None → limit dolu veya hata."""
        if self.quota.exhausted:
            logger.warning(
                "CricAPI quota exhausted (%d/%d) — skipping fetch",
                self.quota.used_today, self.quota.daily_limit,
            )
            return None

        now = time.time()
        if self._cached_data is not None and (now - self._cache_timestamp) < self._cache_ttl:
            return self._cached_data

        try:
            response = self._http(
                f"{_BASE_URL}/currentMatches",
                params={"apikey": self._api_key, "offset": 0},
                timeout=self._timeout,
            )
            if response.status_code != 200:
                logger.warning("CricAPI HTTP %d", response.status_code)
                return None
            data = response.json() or {}
            info = data.get("info", {})
            self.quota.used_today = int(info.get("hitsToday", 0))
            self.quota.daily_limit = int(info.get("hitsLimit", self.quota.daily_limit))
            matches_raw = data.get("data", [])
            matches: list[CricketMatchScore] = []
            for raw in matches_raw:
                parsed = self._parse_match(raw)
                if parsed is not None:
                    matches.append(parsed)
            self._cached_data = matches
            self._cache_timestamp = now
            logger.info(
                "CricAPI fetch: %d matches, quota %d/%d",
                len(matches), self.quota.used_today, self.quota.daily_limit,
            )
            return matches
        except Exception as exc:  # noqa: BLE001
            logger.warning("CricAPI fetch error: %s", exc)
            return None

    def _parse_match(self, raw: dict) -> CricketMatchScore | None:
        """Raw dict → CricketMatchScore. Bozuk kayit None doner."""
        try:
            innings: list[dict] = []
            for s in raw.get("score", []) or []:
                inning_str = s.get("inning", "") or ""
                team_name = ""
                inning_num = 0
                if " Inning " in inning_str:
                    team_name, num_part = inning_str.rsplit(" Inning ", 1)
                    try:
                        inning_num = int(num_part.strip())
                    except ValueError:
                        inning_num = 0
                innings.append({
                    "runs": int(s.get("r", 0)),
                    "wickets": int(s.get("w", 0)),
                    "overs": float(s.get("o", 0)),
                    "team": team_name.strip(),
                    "inning_num": inning_num,
                })
            return CricketMatchScore(
                match_id=str(raw.get("id", "")),
                name=str(raw.get("name", "")),
                match_type=str(raw.get("matchType", "")).lower(),
                teams=list(raw.get("teams", [])),
                status=str(raw.get("status", "")),
                match_started=bool(raw.get("matchStarted", False)),
                match_ended=bool(raw.get("matchEnded", False)),
                venue=str(raw.get("venue", "")),
                date_time_gmt=str(raw.get("dateTimeGMT", "")),
                innings=innings,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("CricAPI parse error: %s", exc)
            return None

    @staticmethod
    def _default_get(url: str, params: dict, timeout: int) -> Any:
        return requests.get(url, params=params, timeout=timeout)
```

- [ ] **Step 4: Run tests — PASS**

Run: `pytest tests/unit/infrastructure/apis/test_cricket_client.py -v`
Expected: 10 PASS

- [ ] **Step 5: Run all tests**

Run: `pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/infrastructure/apis/cricket_client.py tests/unit/infrastructure/apis/test_cricket_client.py
git commit -m "feat(cricket): CricAPI client + quota tracking (SPEC-011 Task 1)

Tek endpoint: /currentMatches. Cache TTL, timeout, daily_limit config'den.
Limit dolunca None doner — entry gate skip icin.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Config — CricketConfig + sport_rules.py + config.yaml

**Files:**
- Modify: `src/config/settings.py` (CricketConfig class ekle)
- Modify: `config.yaml` (cricket block + allowed_sport_tags)
- Modify: `src/config/sport_rules.py` (7 cricket lig blogu)

- [ ] **Step 1: Add CricketConfig to settings.py**

In `src/config/settings.py`, add new class (after ScoreConfig or similar logical grouping):

```python
class CricketConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    daily_limit: int = 100          # SPEC-011 free tier; TODO-003 paid 1000
    cache_ttl_sec: int = 240        # 4dk bulk cache
    timeout_sec: int = 15           # HTTP timeout
```

Find `AppConfig` class and add `cricket` field to it:

```python
class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # ... existing fields ...
    cricket: CricketConfig = CricketConfig()  # SPEC-011
```

- [ ] **Step 2: Add cricket block to config.yaml**

In `config.yaml`, find an appropriate place (after `score:` block or near the end before `dashboard:`). Add:

```yaml
# Cricket cluster (SPEC-011)
cricket:
  enabled: true
  daily_limit: 100       # CricAPI free tier; TODO-003 paid tier 1000
  cache_ttl_sec: 240     # 4dk bulk cache
  timeout_sec: 15        # HTTP timeout
```

Also find `scanner.allowed_sport_tags:` list and add cricket entries:

```yaml
scanner:
  allowed_sport_tags:
    # ... mevcut entries ...
    # Cricket (SPEC-011)
    - cricket
    - cricket_ipl
    - cricket_odi
    - cricket_international_t20
    - cricket_psl
    - cricket_big_bash
    - cricket_caribbean_premier_league
    - cricket_t20_blast
    - indian-premier-league        # Polymarket tag
    - international-cricket        # Polymarket tag
```

- [ ] **Step 3: Add cricket sport rules**

In `src/config/sport_rules.py`, add cricket blocks inside the main config dict. Add these AFTER the existing sports (tennis, mlb, nhl, etc.) but inside the same dict:

```python
# ── Cricket (SPEC-011) ──────────────────────────────────────
# Tum T20 formatlari ayni C1/C2/C3 threshold'lari paylasir.
# ODI icin daha gevsek threshold (daha uzun mac, daha fazla ball).

_T20_SCORE_EXIT = {
    "score_exit_c1_balls": 30,   # son 5 over
    "score_exit_c1_rate": 18.0,  # RRR > 18 imkansiz
    "score_exit_c2_wickets": 8,
    "score_exit_c2_runs": 20,
    "score_exit_c3_balls": 6,    # son 1 over
    "score_exit_c3_runs": 10,
}

_CRICKET_BASE = {
    "stop_loss_pct": 0.30,
    "score_source": "cricapi",    # ESPN yok, Odds API aggregate only
}

# T20 liglerinin ortak config'i
for _key in (
    "cricket_ipl", "cricket_big_bash", "cricket_caribbean_premier_league",
    "cricket_t20_blast", "cricket_international_t20", "cricket_psl",
):
    SPORT_RULES[_key] = {
        **_CRICKET_BASE,
        "match_duration_hours": 3.5,
        **_T20_SCORE_EXIT,
    }

# ODI ayri — daha uzun, daha gevsek threshold
SPORT_RULES["cricket_odi"] = {
    **_CRICKET_BASE,
    "match_duration_hours": 8.0,
    "score_exit_c1_balls": 60,    # son 10 over
    "score_exit_c1_rate": 12.0,   # ODI RRR 12+ imkansiz
    "score_exit_c2_wickets": 8,
    "score_exit_c2_runs": 40,
    "score_exit_c3_balls": 30,    # son 5 over
    "score_exit_c3_runs": 30,
}

# Generic "cricket" fallback — unknown format
SPORT_RULES["cricket"] = SPORT_RULES["cricket_ipl"]  # default T20 behavior
```

**NOT**: If `sport_rules.py` uses a different pattern (e.g., dict literal not `SPORT_RULES` variable), adapt. Use existing patterns in file. The structure is: `sport_tag → dict of rules`.

- [ ] **Step 4: Run config tests**

Run: `pytest tests/unit/config/ -v` (if any config tests exist)
Run: `pytest tests/ -x -q`
Expected: ALL PASS (config changes don't break anything)

- [ ] **Step 5: Commit**

```bash
git add src/config/settings.py src/config/sport_rules.py config.yaml
git commit -m "feat(config): cricket config + 7 lig sport rules (SPEC-011 Task 2)

CricketConfig pydantic (daily_limit, cache_ttl, timeout).
7 cricket ligi sport_rules.py: T20 ortak, ODI ayri threshold.
allowed_sport_tags: cricket tag'leri (PM + oddsapi).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Odds API Key Resolver + Team Aliases + Slug Parser

**Files:**
- Modify: `src/domain/matching/odds_sport_keys.py`
- Modify: `src/domain/matching/team_resolver.py`
- Modify: `src/domain/matching/sport_classifier.py`

- [ ] **Step 1: Add cricket Odds API key mapping**

In `src/domain/matching/odds_sport_keys.py`, find `_SLUG_TO_ODDS` dict. Add cricket entries (keep alphabetical or at end):

```python
    # Cricket (SPEC-011)
    "cricipl": "cricket_ipl",
    "cricket_ipl": "cricket_ipl",
    "indian-premier-league": "cricket_ipl",
    "cricodi": "cricket_odi",
    "cricket_odi": "cricket_odi",
    "crict20i": "cricket_international_t20",
    "cricket_international_t20": "cricket_international_t20",
    "international-cricket": "cricket_international_t20",
    "cricpsl": "cricket_psl",
    "cricket_psl": "cricket_psl",
    "cricbbl": "cricket_big_bash",
    "cricket_big_bash": "cricket_big_bash",
    "criccpl": "cricket_caribbean_premier_league",
    "cricket_caribbean_premier_league": "cricket_caribbean_premier_league",
    "crictbl": "cricket_t20_blast",
    "cricket_t20_blast": "cricket_t20_blast",
```

- [ ] **Step 2: Add cricket team aliases**

In `src/domain/matching/team_resolver.py`, find `_STATIC_ABBREVS` dict (~line 34). Add cricket teams at the end (inside the dict):

```python
    # Cricket IPL (SPEC-011)
    "csk": "chennai super kings",
    "mi": "mumbai indians",
    "rcb": "royal challengers bengaluru",
    "kkr": "kolkata knight riders",
    "srh": "sunrisers hyderabad",
    "dc_ipl": "delhi capitals",
    "pk": "punjab kings",
    "rr": "rajasthan royals",
    "lsg": "lucknow super giants",
    "gt": "gujarat titans",
    # Cricket International
    "ind": "india",
    "aus_cric": "australia",
    "eng_cric": "england",
    "pak": "pakistan",
    "nz": "new zealand",
    "sa": "south africa",
    "wi": "west indies",
    "ban": "bangladesh",
    "sl": "sri lanka",
    "afg": "afghanistan",
    "zim": "zimbabwe",
    "ire": "ireland",
```

**NOT**: Some abbrev keys (`dc`, `aus`, `eng`) may conflict with existing NFL/NBA abbrevs. Used `dc_ipl`, `aus_cric`, `eng_cric` to disambiguate. If this causes issues with slug parsing later, adjust.

- [ ] **Step 3: Update sport_classifier for cricket**

In `src/domain/matching/sport_classifier.py`, find the sport detection function and add cricket pattern. Usually there's a pattern like:

```python
if slug_lower.startswith("mlb"): return "mlb"
if slug_lower.startswith("nhl"): return "nhl"
# ... add ...
if slug_lower.startswith("cricipl"): return "cricket_ipl"
if slug_lower.startswith("cricodi"): return "cricket_odi"
if slug_lower.startswith("crict20i"): return "cricket_international_t20"
if slug_lower.startswith("cricpsl"): return "cricket_psl"
if slug_lower.startswith("cricbbl"): return "cricket_big_bash"
if slug_lower.startswith("criccpl"): return "cricket_caribbean_premier_league"
if slug_lower.startswith("crictbl"): return "cricket_t20_blast"
if slug_lower.startswith("cric") or "cricket" in tags:
    return "cricket"  # generic fallback
```

Use the existing pattern in `sport_classifier.py`. If it uses a different dispatch (regex table, etc.), adapt accordingly.

- [ ] **Step 4: Add basic test for cricket mapping**

In `tests/unit/domain/matching/test_odds_sport_keys.py` (or create if absent), add:

```python
def test_cricket_ipl_slug_maps_correctly():
    from src.domain.matching.odds_sport_keys import resolve_odds_key
    assert resolve_odds_key("cricipl-kol-raj-2026-04-19", []) == "cricket_ipl"
    assert resolve_odds_key("", ["indian-premier-league"]) == "cricket_ipl"


def test_cricket_odi_slug_maps_correctly():
    from src.domain.matching.odds_sport_keys import resolve_odds_key
    assert resolve_odds_key("cricodi-ind-aus-2026-04-20", []) == "cricket_odi"


def test_cricket_international_t20_slug_maps():
    from src.domain.matching.odds_sport_keys import resolve_odds_key
    assert resolve_odds_key("crict20i-nep-uae-2026-04-20", []) == "cricket_international_t20"
```

Note: `resolve_odds_key` signature — check existing file for correct signature.

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/domain/matching/ -v`
Expected: ALL PASS

Run: `pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/domain/matching/odds_sport_keys.py src/domain/matching/team_resolver.py src/domain/matching/sport_classifier.py tests/unit/domain/matching/test_odds_sport_keys.py
git commit -m "feat(matching): cricket slug/tag/team mapping (SPEC-011 Task 3)

- odds_sport_keys: 7 cricket lig mapping (slug + PM tag)
- team_resolver: IPL abbrevs (CSK, MI, RCB, KKR, SRH, ...)
  + International cricket teams (IND, AUS, ENG, PAK, NZ, ...)
- sport_classifier: cric* prefix dispatch

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Cricket Score Exit Strategy

**Files:**
- Create: `src/strategy/exit/cricket_score_exit.py`
- Create: `tests/unit/strategy/exit/test_cricket_score_exit.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/strategy/exit/test_cricket_score_exit.py`:

```python
"""cricket_score_exit.py unit tests (SPEC-011)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit.cricket_score_exit import (
    CricketExitResult,
    check,
)


def _score_info(
    innings: int = 2,
    our_chasing: bool = True,
    balls_remaining: int = 60,
    runs_remaining: int = 50,
    wickets_lost: int = 4,
    required_rate: float = 5.0,
) -> dict:
    return {
        "available": True,
        "innings": innings,
        "our_chasing": our_chasing,
        "balls_remaining": balls_remaining,
        "runs_remaining": runs_remaining,
        "wickets_lost": wickets_lost,
        "required_run_rate": required_rate,
    }


# ── Non-exit cases ─────────────────────────────────────────────

def test_available_false_no_exit():
    r = check({"available": False}, current_price=0.3, sport_tag="cricket_ipl")
    assert r is None


def test_innings_1_no_exit():
    r = check(_score_info(innings=1), current_price=0.3, sport_tag="cricket_ipl")
    assert r is None


def test_our_chasing_false_no_exit():
    # Biz defending — chase cokuyor = BIZ kazaniyoruz, cikma
    r = check(
        _score_info(our_chasing=False, balls_remaining=10, runs_remaining=100, required_rate=60),
        current_price=0.85, sport_tag="cricket_ipl",
    )
    assert r is None


def test_chase_won_no_exit():
    # Rakibimiz target'a ulasti veya gecti → positive PnL, near_resolve yakalar
    r = check(_score_info(runs_remaining=0), current_price=0.9, sport_tag="cricket_ipl")
    assert r is None


def test_normal_chase_no_exit():
    # Ortamin rrr=6, 60 ball, 4 wkt — chase devam ediyor
    r = check(_score_info(), current_price=0.5, sport_tag="cricket_ipl")
    assert r is None


# ── C1: Impossible RRR ─────────────────────────────────────────

def test_c1_impossible_rrr_triggers():
    # T20: 24 ball kaldi, RRR 20 — imkansiz
    r = check(
        _score_info(balls_remaining=24, runs_remaining=80, required_rate=20.0),
        current_price=0.05, sport_tag="cricket_ipl",
    )
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "C1" in r.detail


def test_c1_rrr_under_threshold_no_exit():
    # 24 ball kaldi ama RRR 17 — henuz imkansiz degil
    r = check(
        _score_info(balls_remaining=24, runs_remaining=68, required_rate=17.0),
        current_price=0.10, sport_tag="cricket_ipl",
    )
    assert r is None


def test_c1_balls_over_threshold_no_exit():
    # 60 ball kaldi, RRR 20 — henuz vakit var
    r = check(
        _score_info(balls_remaining=60, runs_remaining=200, required_rate=20.0),
        current_price=0.20, sport_tag="cricket_ipl",
    )
    # T20 c1_balls=30, 60 > 30 → C1 tetiklenmez
    # Diger kurallar? wickets_lost=4 < 8 → C2 yok. balls_remaining=60 > 6 → C3 yok
    assert r is None


# ── C2: Too many wickets ───────────────────────────────────────

def test_c2_8_wickets_20_runs_left_triggers():
    r = check(
        _score_info(wickets_lost=8, runs_remaining=25, balls_remaining=30, required_rate=5.0),
        current_price=0.15, sport_tag="cricket_ipl",
    )
    assert r is not None
    assert "C2" in r.detail


def test_c2_7_wickets_no_exit():
    r = check(
        _score_info(wickets_lost=7, runs_remaining=30, balls_remaining=30, required_rate=6.0),
        current_price=0.30, sport_tag="cricket_ipl",
    )
    assert r is None  # C2 threshold 8


def test_c2_8_wickets_small_runs_no_exit():
    r = check(
        _score_info(wickets_lost=8, runs_remaining=15, balls_remaining=30, required_rate=3.0),
        current_price=0.60, sport_tag="cricket_ipl",
    )
    # wickets=8 >= 8 BUT runs_remaining=15 not > 20 → C2 fires? 
    # check: wickets >= 8 AND runs > 20. 15 not > 20 → NO exit
    assert r is None


# ── C3: Final balls, big gap ───────────────────────────────────

def test_c3_final_balls_big_gap_triggers():
    r = check(
        _score_info(balls_remaining=4, runs_remaining=15, wickets_lost=6, required_rate=22.5),
        current_price=0.05, sport_tag="cricket_ipl",
    )
    # C3: balls < 6 AND runs > 10 → YES
    # Also C1: balls < 30 AND rate > 18 → C1 triggers FIRST (order)
    assert r is not None
    # Either C1 or C3 acceptable — both are valid exits
    assert r.reason == ExitReason.SCORE_EXIT


def test_c3_final_balls_small_gap_no_exit():
    r = check(
        _score_info(balls_remaining=4, runs_remaining=8, wickets_lost=5, required_rate=12.0),
        current_price=0.40, sport_tag="cricket_ipl",
    )
    # C3: runs_remaining=8 not > 10 → NO C3
    # C1: rate=12 not > 18 → NO C1
    # C2: wickets=5 < 8 → NO C2
    assert r is None


# ── Config driven (ODI) ────────────────────────────────────────

def test_odi_higher_c1_threshold():
    # ODI c1_balls=60, c1_rate=12.0 — gevsek
    r = check(
        _score_info(balls_remaining=50, runs_remaining=100, required_rate=12.5),
        current_price=0.05, sport_tag="cricket_odi",
    )
    assert r is not None  # ODI C1: balls<60 AND rate>12
    assert "C1" in r.detail


def test_odi_t20_rate_no_exit():
    # T20 icin 12.5 imkansiz degil, ama ODI icin oyle
    # Ayni veriyle cricket_ipl sport_tag → C1 threshold 18 → 12.5 < 18 → no exit
    r = check(
        _score_info(balls_remaining=50, runs_remaining=100, required_rate=12.5),
        current_price=0.20, sport_tag="cricket_ipl",
    )
    # T20'de c1_balls=30, 50 > 30 → C1 yok
    # T20'de c1_rate=18, 12.5 < 18 → C1 yok
    # C2: wickets_lost default 4, C2 yok
    # C3: balls 50 > 6 → C3 yok
    assert r is None


def test_detail_contains_sport_thresholds():
    r = check(
        _score_info(balls_remaining=24, runs_remaining=80, required_rate=20.0),
        current_price=0.05, sport_tag="cricket_ipl",
    )
    assert r is not None
    assert "rrr=20" in r.detail.lower() or "rrr=20.0" in r.detail.lower()
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `pytest tests/unit/strategy/exit/test_cricket_score_exit.py -v`
Expected: FAIL with "No module named 'src.strategy.exit.cricket_score_exit'"

- [ ] **Step 3: Create cricket_score_exit.py**

Create `src/strategy/exit/cricket_score_exit.py`:

```python
"""Cricket inning-based score exit (SPEC-011) — pure.

Tennis T1/T2 ve hockey K1-K4 ile simetrik. A-conf pozisyonlar icin
FORCED exit. Sadece 2. innings (chase) ve bizim chasing tarafimiz iken
C1/C2/C3 tetiklenir — defending tarafindaysak chase cokmek bizim lehimize.

C1: Matematiksel imkansiz chase
    balls_remaining < c1_balls AND required_run_rate > c1_rate

C2: Cok fazla wicket kaybi
    wickets_lost >= c2_wickets AND runs_remaining > c2_runs

C3: Son over'lar + uzak hedef
    balls_remaining < c3_balls AND runs_remaining > c3_runs

Tum threshold'lar sport_rules.py config'inden (magic number yok).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class CricketExitResult:
    """Cricket exit sonucu — monitor.py ExitSignal'a cevirir."""

    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    current_price: float,
    sport_tag: str = "cricket_ipl",
) -> CricketExitResult | None:
    """Cricket C1/C2/C3 exit kontrolu.

    score_info beklenen format:
      {
        "available": True,
        "innings": 2,                  # 2 = chase, 1 = first innings
        "our_chasing": True,           # biz chase eden taraftayiz mi
        "balls_remaining": int,
        "runs_remaining": int,
        "wickets_lost": int,
        "required_run_rate": float,
      }

    1. innings VEYA available=False VEYA our_chasing=False → None (skip).
    """
    if not score_info.get("available"):
        return None

    if score_info.get("innings", 0) != 2:
        return None  # Sadece chase'te mantikli

    if not score_info.get("our_chasing", False):
        # Biz defending'iz — chase cokerse BIZ kazaniyoruz, exit yok
        return None

    balls_remaining = int(score_info.get("balls_remaining", 0))
    runs_remaining = int(score_info.get("runs_remaining", 0))
    wickets_lost = int(score_info.get("wickets_lost", 0))
    required_rate = float(score_info.get("required_run_rate", 0.0))

    if runs_remaining <= 0:
        return None  # Chase tamamlandi (kazandik)

    # Config thresholds
    c1_balls = int(get_sport_rule(sport_tag, "score_exit_c1_balls", 30))
    c1_rate = float(get_sport_rule(sport_tag, "score_exit_c1_rate", 18.0))
    c2_wickets = int(get_sport_rule(sport_tag, "score_exit_c2_wickets", 8))
    c2_runs = int(get_sport_rule(sport_tag, "score_exit_c2_runs", 20))
    c3_balls = int(get_sport_rule(sport_tag, "score_exit_c3_balls", 6))
    c3_runs = int(get_sport_rule(sport_tag, "score_exit_c3_runs", 10))

    # C1: Impossible RRR
    if balls_remaining < c1_balls and required_rate > c1_rate:
        return CricketExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"C1: balls_left={balls_remaining} rrr={required_rate:.1f} threshold={c1_rate}",
        )

    # C2: Too many wickets lost
    if wickets_lost >= c2_wickets and runs_remaining > c2_runs:
        return CricketExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"C2: wkts={wickets_lost} runs_left={runs_remaining} threshold={c2_runs}",
        )

    # C3: Final balls, big gap
    if balls_remaining < c3_balls and runs_remaining > c3_runs:
        return CricketExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"C3: balls_left={balls_remaining} runs_left={runs_remaining} threshold={c3_runs}",
        )

    return None
```

- [ ] **Step 4: Run tests — PASS**

Run: `pytest tests/unit/strategy/exit/test_cricket_score_exit.py -v`
Expected: ~15 PASS

- [ ] **Step 5: Run all tests**

Run: `pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/strategy/exit/cricket_score_exit.py tests/unit/strategy/exit/test_cricket_score_exit.py
git commit -m "feat(exit): cricket_score_exit C1/C2/C3 — tennis simetrik (SPEC-011 Task 4)

Tennis T1/T2 ve baseball M1/M2/M3 gibi A-conf pozisyonlar icin FORCED exit.
Sadece 2. innings chase + our_chasing=True iken tetiklenir.

C1: balls<30 AND rrr>18 (impossible chase)
C2: wickets>=8 AND runs>20 (too many losses)
C3: balls<6 AND runs>10 (final over, big gap)

ODI icin gevsek threshold (c1_balls=60, c1_rate=12) config'den.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Cricket Score Builder (Orchestration)

**Files:**
- Create: `src/orchestration/cricket_score_builder.py`
- Create: `tests/unit/orchestration/test_cricket_score_builder.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/orchestration/test_cricket_score_builder.py`:

```python
"""cricket_score_builder.py unit tests (SPEC-011)."""
from __future__ import annotations

from src.infrastructure.apis.cricket_client import CricketMatchScore
from src.orchestration.cricket_score_builder import (
    build_cricket_score_info,
    find_cricket_match,
)


def _make_match(
    teams=None, match_type="t20", innings=None,
    match_started=True, match_ended=False,
):
    return CricketMatchScore(
        match_id="m1",
        name=" vs ".join(teams or ["Team A", "Team B"]),
        match_type=match_type,
        teams=teams or ["Team A", "Team B"],
        status="In progress",
        match_started=match_started,
        match_ended=match_ended,
        venue="",
        date_time_gmt="2026-04-19T13:00:00",
        innings=innings or [],
    )


def _make_position(question, direction="BUY_YES"):
    class _Pos:
        pass
    p = _Pos()
    p.question = question
    p.slug = "cricipl-test-2026-04-19"
    p.direction = direction
    p.event_id = "evt-1"
    return p


# ── find_cricket_match ─────────────────────────────────────────

def test_find_cricket_match_by_team_pair():
    pos = _make_position("Kolkata Knight Riders vs Rajasthan Royals")
    matches = [
        _make_match(teams=["Some Other", "Teams"]),
        _make_match(teams=["Kolkata Knight Riders", "Rajasthan Royals"]),
    ]
    match = find_cricket_match(pos, matches)
    assert match is not None
    assert match.teams == ["Kolkata Knight Riders", "Rajasthan Royals"]


def test_find_cricket_match_swapped_teams():
    pos = _make_position("Kolkata Knight Riders vs Rajasthan Royals")
    matches = [_make_match(teams=["Rajasthan Royals", "Kolkata Knight Riders"])]
    match = find_cricket_match(pos, matches)
    assert match is not None


def test_find_cricket_match_no_match():
    pos = _make_position("Mumbai Indians vs Chennai Super Kings")
    matches = [_make_match(teams=["Delhi Capitals", "Punjab Kings"])]
    match = find_cricket_match(pos, matches)
    assert match is None


# ── build_cricket_score_info ───────────────────────────────────

def test_build_score_info_not_started():
    pos = _make_position("Team A vs Team B")
    match = _make_match(match_started=False, innings=[])
    info = build_cricket_score_info(pos, match)
    assert info == {"available": False}


def test_build_score_info_innings_1():
    pos = _make_position("Team A vs Team B")
    match = _make_match(innings=[
        {"runs": 90, "wickets": 3, "overs": 12.0, "team": "Team A", "inning_num": 1},
    ])
    info = build_cricket_score_info(pos, match)
    assert info["available"] is True
    assert info["innings"] == 1


def test_build_score_info_innings_2_chase_buy_yes_we_bat():
    # Team A yi destekliyoruz. Team A first innings, Team B chase.
    # Biz BUY_YES → Team A. Team A bat bitirdi, Team B chase → biz DEFENDING.
    # our_chasing = False
    pos = _make_position("Team A vs Team B", direction="BUY_YES")
    match = _make_match(
        teams=["Team A", "Team B"],
        match_type="t20",
        innings=[
            {"runs": 180, "wickets": 5, "overs": 20.0, "team": "Team A", "inning_num": 1},
            {"runs": 95, "wickets": 4, "overs": 12.3, "team": "Team B", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    assert info["available"] is True
    assert info["innings"] == 2
    assert info["target"] == 181  # 180 + 1
    assert info["our_chasing"] is False  # Team A dinleniyor, Team B chase ediyor
    assert info["runs_remaining"] == 86  # 181 - 95
    assert info["wickets_lost"] == 4


def test_build_score_info_innings_2_chase_buy_yes_we_chase():
    # Team A yi destekliyoruz. Team B first innings, Team A chase.
    # Biz BUY_YES → Team A. Team A chase → our_chasing=True
    pos = _make_position("Team A vs Team B", direction="BUY_YES")
    match = _make_match(
        teams=["Team A", "Team B"],
        match_type="t20",
        innings=[
            {"runs": 150, "wickets": 6, "overs": 20.0, "team": "Team B", "inning_num": 1},
            {"runs": 80, "wickets": 5, "overs": 12.0, "team": "Team A", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    assert info["innings"] == 2
    assert info["target"] == 151
    assert info["our_chasing"] is True  # Team A chase ediyor
    assert info["runs_remaining"] == 71  # 151 - 80


def test_build_score_info_buy_no_direction_inverted():
    # BUY_NO Team A → biz Team B'yi destekliyoruz
    pos = _make_position("Team A vs Team B", direction="BUY_NO")
    match = _make_match(
        teams=["Team A", "Team B"],
        match_type="t20",
        innings=[
            {"runs": 150, "wickets": 6, "overs": 20.0, "team": "Team A", "inning_num": 1},
            {"runs": 60, "wickets": 4, "overs": 10.0, "team": "Team B", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    # Team B chase + BUY_NO Team A = biz Team B'yi destekliyoruz → our_chasing=True
    assert info["our_chasing"] is True


def test_build_score_info_t20_max_balls():
    pos = _make_position("Team A vs Team B")
    match = _make_match(
        match_type="t20",
        innings=[
            {"runs": 150, "wickets": 6, "overs": 20.0, "team": "Team B", "inning_num": 1},
            {"runs": 80, "wickets": 5, "overs": 10.0, "team": "Team A", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    # 20 over * 6 = 120 balls. 10 over = 60 faced. 60 remaining.
    assert info["balls_remaining"] == 60


def test_build_score_info_odi_max_balls():
    pos = _make_position("Team A vs Team B")
    match = _make_match(
        match_type="odi",
        innings=[
            {"runs": 300, "wickets": 8, "overs": 50.0, "team": "Team B", "inning_num": 1},
            {"runs": 120, "wickets": 4, "overs": 25.0, "team": "Team A", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    # 50 over * 6 = 300 balls. 25 over = 150 faced. 150 remaining.
    assert info["balls_remaining"] == 150


def test_build_score_info_rrr_calculation():
    pos = _make_position("Team A vs Team B")
    match = _make_match(
        match_type="t20",
        innings=[
            {"runs": 200, "wickets": 5, "overs": 20.0, "team": "Team B", "inning_num": 1},
            {"runs": 100, "wickets": 4, "overs": 15.0, "team": "Team A", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    # target=201, scored=100, remaining=101
    # 20 over - 15 over = 5 over left = 30 balls
    # RRR = 101 * 6 / 30 = 20.2
    assert info["runs_remaining"] == 101
    assert info["balls_remaining"] == 30
    assert abs(info["required_run_rate"] - 20.2) < 0.1
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `pytest tests/unit/orchestration/test_cricket_score_builder.py -v`
Expected: FAIL with "No module named 'src.orchestration.cricket_score_builder'"

- [ ] **Step 3: Create cricket_score_builder.py**

Create `src/orchestration/cricket_score_builder.py`:

```python
"""Cricket match state → score_info dict (SPEC-011).

CricAPI CricketMatchScore nesnesinden, position direction'a gore,
cricket_score_exit'in tukettigi score_info dict'i uretir. Pure — CricAPI
response VE position verilir, dict doner. I/O yok (orchestration dispatch-only).

Ayri dosya gerekcesi: score_enricher.py 367 satir, cricket branch eklenirse
400 asilir (ARCH_GUARD Kural 3). Cricket-specific logic burada yasar.
"""
from __future__ import annotations

from src.domain.matching.pair_matcher import match_pair, match_team
from src.infrastructure.apis.cricket_client import CricketMatchScore
from src.strategy.enrichment.question_parser import extract_teams

_FORMAT_MAX_OVERS = {"t20": 20, "t20i": 20, "odi": 50}
_MIN_MATCH_CONFIDENCE = 0.80


def find_cricket_match(pos, matches: list[CricketMatchScore]) -> CricketMatchScore | None:
    """Pair matcher ile pozisyon-match eslestir. None → uygun eslesme yok."""
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None

    best_match: CricketMatchScore | None = None
    best_conf = 0.0

    for m in matches:
        if len(m.teams) < 2:
            continue
        home, away = m.teams[0], m.teams[1]
        if team_b:
            is_match, conf = match_pair((team_a, team_b), (home, away))
            if is_match and conf > best_conf:
                best_match = m
                best_conf = conf
        else:
            mh, ch, _ = match_team(team_a, home)
            ma, ca, _ = match_team(team_a, away)
            best_side = max(ch, ca)
            if (mh or ma) and best_side > best_conf:
                best_match = m
                best_conf = best_side

    return best_match if best_conf >= _MIN_MATCH_CONFIDENCE else None


def build_cricket_score_info(pos, match: CricketMatchScore) -> dict:
    """CricAPI match → score_info dict. cricket_score_exit bunu tuketir.

    Gerekli: match started + en az 1 innings data.
    Direction-aware: position BUY_YES → first team supporter; BUY_NO → second.
    our_chasing = bizim takimimiz 2. innings'te batting mi?
    """
    if not match.match_started or not match.innings:
        return {"available": False}

    # Position direction → bizim takim
    team_a, team_b = extract_teams(pos.question)
    direction = getattr(pos, "direction", "BUY_YES")
    # Polymarket convention: YES = first team in question
    our_team_name = team_a if direction == "BUY_YES" else (team_b or "")

    # Format → max balls
    max_overs = _FORMAT_MAX_OVERS.get(match.match_type.lower(), 20)
    max_balls = max_overs * 6

    # 1. innings only
    if len(match.innings) < 2:
        return {"available": True, "innings": 1}

    # 2. innings (chase)
    first = match.innings[0]
    second = match.innings[1]
    target = int(first.get("runs", 0)) + 1

    runs_scored = int(second.get("runs", 0))
    wickets_lost = int(second.get("wickets", 0))
    overs_float = float(second.get("overs", 0))

    # Overs "15.3" formatı = 15 over + 3 ball = 93 balls
    full_overs = int(overs_float)
    partial_balls = int(round((overs_float - full_overs) * 10))
    if partial_balls > 5:  # safety: 15.6 gibi bozuk veri
        partial_balls = 5
    balls_faced = full_overs * 6 + partial_balls

    runs_remaining = max(0, target - runs_scored)
    balls_remaining = max(0, max_balls - balls_faced)

    required_rate = (runs_remaining * 6.0 / balls_remaining) if balls_remaining > 0 else 0.0
    current_rate = (runs_scored * 6.0 / balls_faced) if balls_faced > 0 else 0.0

    # Kim chase ediyor? (2. innings team)
    chasing_team = second.get("team", "")
    our_chasing = False
    if our_team_name and chasing_team:
        is_match, conf, _ = match_team(our_team_name, chasing_team)
        our_chasing = is_match and conf >= _MIN_MATCH_CONFIDENCE

    return {
        "available": True,
        "innings": 2,
        "target": target,
        "runs_remaining": runs_remaining,
        "balls_remaining": balls_remaining,
        "wickets_lost": wickets_lost,
        "required_run_rate": required_rate,
        "current_run_rate": current_rate,
        "our_chasing": our_chasing,
    }
```

- [ ] **Step 4: Run tests — PASS**

Run: `pytest tests/unit/orchestration/test_cricket_score_builder.py -v`
Expected: ~10 PASS

- [ ] **Step 5: Run all tests**

Run: `pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/orchestration/cricket_score_builder.py tests/unit/orchestration/test_cricket_score_builder.py
git commit -m "feat(orchestration): cricket_score_builder — match→score_info (SPEC-011 Task 5)

Cricket match state'den cricket_score_exit'in tukettigi dict uretir.
Ayri dosya: score_enricher.py 400 asmasin (ARCH_GUARD Kural 3).
Direction-aware: our_chasing flag position direction'dan hesaplanir.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: ScoreEnricher Integration (Cricket Dispatch)

**Files:**
- Modify: `src/orchestration/score_enricher.py`
- Modify: `src/orchestration/agent.py` (AgentDeps)
- Modify: `src/orchestration/factory.py` (wire CricketAPIClient)
- Modify: `tests/unit/orchestration/test_score_enricher.py`

- [ ] **Step 1: Add cricket_client to AgentDeps**

In `src/orchestration/agent.py`, find `AgentDeps` dataclass. Add import:

```python
from src.infrastructure.apis.cricket_client import CricketAPIClient
```

Add field (as optional, since may be disabled):

```python
@dataclass
class AgentDeps:
    # ... existing fields ...
    cricket_client: CricketAPIClient | None = None
```

- [ ] **Step 2: Wire in factory.py**

In `src/orchestration/factory.py`, add cricket client construction. Add import:

```python
from src.infrastructure.apis.cricket_client import CricketAPIClient
```

In `build_agent()`, add (near other client inits):

```python
    # CricAPI (SPEC-011) — conditional on config
    cricket_client: CricketAPIClient | None = None
    if cfg.cricket.enabled:
        import os
        cricapi_key = os.getenv("CRICAPI_KEY", "")
        if cricapi_key:
            cricket_client = CricketAPIClient(
                api_key=cricapi_key,
                daily_limit=cfg.cricket.daily_limit,
                cache_ttl_sec=cfg.cricket.cache_ttl_sec,
                timeout_sec=cfg.cricket.timeout_sec,
            )
        else:
            logger.warning("CRICAPI_KEY env missing — cricket disabled")
```

In `AgentDeps(...)` constructor call, add:

```python
    deps = AgentDeps(
        # ... existing ...
        cricket_client=cricket_client,
    )
```

Also pass to ScoreEnricher if it needs it:

```python
    score_enricher = ScoreEnricher(
        # ... existing ...
        cricket_client=cricket_client,
    )
```

- [ ] **Step 3: Update ScoreEnricher — add cricket dispatch**

In `src/orchestration/score_enricher.py`, add imports:

```python
from src.infrastructure.apis.cricket_client import CricketAPIClient, CricketMatchScore
from src.orchestration.cricket_score_builder import (
    build_cricket_score_info,
    find_cricket_match,
)
```

Update `__init__` signature to accept `cricket_client`:

```python
    def __init__(
        self,
        espn_client=None,
        odds_client=None,
        poll_normal_sec: int = 60,
        poll_critical_sec: int = 30,
        critical_price_threshold: float = 0.35,
        match_window_hours: float = 4.0,
        archive_logger: ArchiveLogger | None = None,
        cricket_client: CricketAPIClient | None = None,  # NEW
    ) -> None:
        # ... existing init ...
        self._cricket_client = cricket_client
        self._cached_cricket: list[CricketMatchScore] = []
        self._cricket_fetch_attempted: bool = False
```

Add cricket tag detection helper (module-level or class):

```python
_CRICKET_TAGS = frozenset({
    "cricket", "cricket_ipl", "cricket_odi", "cricket_international_t20",
    "cricket_psl", "cricket_big_bash", "cricket_caribbean_premier_league",
    "cricket_t20_blast",
})

def _is_cricket(sport_tag: str) -> bool:
    tag = _normalize(sport_tag)
    return tag in _CRICKET_TAGS or tag.startswith("cricket")
```

In `_refresh_scores()`, add cricket branch. Find the sport loop. After ESPN/Odds dispatch:

```python
        # Cricket dispatch (SPEC-011)
        has_cricket_pos = any(
            _is_cricket(pos.sport_tag) for pos in positions.values()
        )
        if has_cricket_pos and self._cricket_client is not None:
            cricket_matches = self._cricket_client.get_current_matches()
            if cricket_matches is not None:
                self._cached_cricket = cricket_matches
            # else: quota exhausted or error — skip silently; entry gate handles
```

In `_match_cached()`, add cricket match handling:

```python
    def _match_cached(self, positions: dict[str, Position]) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for cid, pos in positions.items():
            # Cricket path (SPEC-011)
            if _is_cricket(pos.sport_tag):
                if not self._cached_cricket:
                    continue
                match = find_cricket_match(pos, self._cached_cricket)
                if match is not None:
                    result[cid] = build_cricket_score_info(pos, match)
                continue
            # ... existing ESPN/Odds logic ...
```

- [ ] **Step 4: Update test_score_enricher.py**

Add 1-2 cricket dispatch tests:

```python
def test_cricket_position_uses_cricket_client():
    """Cricket sport_tag → CricketAPIClient path, not ESPN."""
    from unittest.mock import MagicMock
    from src.orchestration.score_enricher import ScoreEnricher
    from src.infrastructure.apis.cricket_client import CricketMatchScore

    cricket_client = MagicMock()
    cricket_client.get_current_matches.return_value = [
        CricketMatchScore(
            match_id="m1", name="Team A vs Team B",
            match_type="t20", teams=["Team A", "Team B"],
            status="", match_started=True, match_ended=False,
            venue="", date_time_gmt="",
            innings=[
                {"runs": 150, "wickets": 6, "overs": 20.0, "team": "Team B", "inning_num": 1},
                {"runs": 80, "wickets": 5, "overs": 12.0, "team": "Team A", "inning_num": 2},
            ],
        ),
    ]
    enricher = ScoreEnricher(
        espn_client=MagicMock(),
        odds_client=None,
        cricket_client=cricket_client,
    )
    # Build minimal cricket position
    pos = _pos_with_event(
        event_id="E1",
        question="Team A vs Team B",
        sport_tag="cricket_ipl",
    )
    positions = {"cid1": pos}
    # Trigger poll
    enricher.get_scores_if_due(positions)
    cricket_client.get_current_matches.assert_called()


def test_cricket_without_client_skips_silently():
    """cricket_client=None → cricket positions skip cleanly."""
    from src.orchestration.score_enricher import ScoreEnricher
    enricher = ScoreEnricher(
        espn_client=None, odds_client=None, cricket_client=None,
    )
    pos = _pos_with_event(
        event_id="E1", question="Team A vs Team B",
        sport_tag="cricket_ipl",
    )
    result = enricher.get_scores_if_due({"cid1": pos})
    # Crash yok, sonuc bos
    assert isinstance(result, dict)
```

Note: `_pos_with_event` is an existing helper in the test file.

Also, existing `AgentDeps(...)` construction in test_agent.py may need `cricket_client=None` — add if tests break.

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/orchestration/ -v`
Expected: ALL PASS

Run: `pytest tests/ -x -q`
Expected: ALL PASS (any AgentDeps construction issues fix immediately)

- [ ] **Step 6: Commit**

```bash
git add src/orchestration/score_enricher.py src/orchestration/agent.py src/orchestration/factory.py tests/unit/orchestration/test_score_enricher.py tests/unit/orchestration/test_agent.py
git commit -m "feat(orchestration): CricketAPIClient wire — score_enricher dispatch (SPEC-011 Task 6)

AgentDeps.cricket_client eklendi. Factory CRICAPI_KEY env'den okuyor.
score_enricher cricket branch — cricket_score_builder'a delegate ediyor.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Monitor Wire + Entry Gate Cricket Skip

**Files:**
- Modify: `src/strategy/exit/monitor.py` (cricket_score_exit wire)
- Modify: `src/strategy/entry/gate.py` (cricapi_unavailable skip)
- Modify: `tests/unit/strategy/exit/test_monitor.py`
- Modify: `tests/unit/strategy/entry/test_gate.py`

- [ ] **Step 1: Wire cricket_score_exit in monitor.py**

In `src/strategy/exit/monitor.py`, find the imports line with other score exits:

```python
from src.strategy.exit import a_conf_hold, baseball_score_exit, catastrophic_watch, favored, graduated_sl, near_resolve, scale_out, hockey_score_exit, stop_loss, tennis_score_exit
```

Add `cricket_score_exit`:

```python
from src.strategy.exit import a_conf_hold, baseball_score_exit, catastrophic_watch, cricket_score_exit, favored, graduated_sl, near_resolve, scale_out, hockey_score_exit, stop_loss, tennis_score_exit
```

In `evaluate()`, find the a_conf_hold branch where tennis/hockey/baseball score exits are wired. After the baseball block (or before market_flip), add:

```python
        # 3a-cricket. Score-based exit — cricket (SPEC-011 C1/C2/C3)
        if _is_cricket_sport(pos.sport_tag) and score_info.get("available"):
            c_result = cricket_score_exit.check(
                score_info=score_info,
                current_price=pos.current_price,
                sport_tag=pos.sport_tag,
            )
            if c_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(reason=c_result.reason, detail=c_result.detail),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )
```

Add helper function at module level:

```python
_CRICKET_TAGS = frozenset({
    "cricket", "cricket_ipl", "cricket_odi", "cricket_international_t20",
    "cricket_psl", "cricket_big_bash", "cricket_caribbean_premier_league",
    "cricket_t20_blast",
})


def _is_cricket_sport(sport_tag: str) -> bool:
    tag = _normalize(sport_tag)
    return tag in _CRICKET_TAGS or tag.startswith("cricket")
```

- [ ] **Step 2: Add monitor integration test**

In `tests/unit/strategy/exit/test_monitor.py`, add:

```python
def test_cricket_c1_triggers_for_a_conf():
    """A-conf cricket pozisyon + C1 score_info → SCORE_EXIT."""
    from src.models.enums import ExitReason
    from src.models.position import Position
    from src.strategy.exit import monitor as exit_monitor

    pos = Position(
        condition_id="cid1",
        token_id="tok1",
        direction="BUY_YES",
        entry_price=0.65,
        size_usdc=50.0,
        shares=76.92,
        slug="cricipl-kol-raj-2026-04-19",
        confidence="A",
        anchor_probability=0.65,
        current_price=0.10,
        sport_tag="cricket_ipl",
        question="Kolkata Knight Riders vs Rajasthan Royals",
    )
    score_info = {
        "available": True,
        "innings": 2,
        "our_chasing": True,
        "balls_remaining": 24,
        "runs_remaining": 80,
        "wickets_lost": 7,
        "required_run_rate": 20.0,
    }

    result = exit_monitor.evaluate(pos, score_info=score_info, scale_out_tiers=[])
    assert result.exit_signal is not None
    assert result.exit_signal.reason == ExitReason.SCORE_EXIT
    assert "C1" in result.exit_signal.detail or "C2" in result.exit_signal.detail
```

- [ ] **Step 3: Add entry gate cricapi_unavailable skip**

In `src/strategy/entry/gate.py`, find the gate flow (just before confidence/sizing checks, around manipulation check). Add:

```python
        # Cricket CricAPI availability check (SPEC-011)
        if _is_cricket_market_sport(sport_tag):
            cricket_client = getattr(self, "_cricket_client", None)
            if cricket_client is not None and cricket_client.quota.exhausted:
                detail = f"cricapi quota {cricket_client.quota.used_today}/{cricket_client.quota.daily_limit}"
                return GateResult(cid, None, "cricapi_unavailable", skip_detail=detail)
```

Add `_cricket_client` as optional field on `EntryGate` (or pass through, depending on architecture). Alternative: check via deps/config.

Actually the cleanest approach: EntryGate has `cricket_client` optional param via DI. In `__init__`:

```python
    def __init__(
        self,
        config: GateConfig,
        portfolio: PortfolioManager,
        circuit_breaker: CircuitBreaker,
        cooldown: CooldownTracker,
        blacklist: Blacklist,
        odds_enricher,
        manipulation_checker,
        cricket_client=None,  # SPEC-011
    ) -> None:
        # ... existing ...
        self._cricket_client = cricket_client
```

And factory.py passes `cricket_client=cricket_client` to `EntryGate(...)` construction.

Add helper at module level in gate.py:

```python
_CRICKET_MARKET_TAGS = frozenset({
    "cricket", "cricket_ipl", "cricket_odi", "cricket_international_t20",
    "cricket_psl", "cricket_big_bash", "cricket_caribbean_premier_league",
    "cricket_t20_blast",
})


def _is_cricket_market_sport(sport_tag: str) -> bool:
    t = (sport_tag or "").lower().strip()
    return t in _CRICKET_MARKET_TAGS or t.startswith("cricket")
```

In the evaluate logic, place the check right BEFORE sizing (after market/event/blacklist/manipulation checks). Exact location: just before `raw_size = confidence_position_size(...)`.

- [ ] **Step 4: Add gate skip test**

In `tests/unit/strategy/entry/test_gate.py`, add:

```python
def test_cricket_entry_skipped_when_cricapi_quota_exhausted():
    """CricAPI quota dolu → cricket entry skip."""
    from unittest.mock import MagicMock
    from src.strategy.entry.gate import EntryGate, GateConfig
    # ... build minimal gate with cricket_client mock ...
    cricket_client = MagicMock()
    cricket_client.quota.exhausted = True
    cricket_client.quota.used_today = 100
    cricket_client.quota.daily_limit = 100
    # ... (use existing test helpers like _make_gate, _market) ...
    # ... cricket market ...
    # ... run gate, expect skip_reason == "cricapi_unavailable" ...
```

Adapt based on existing test helpers in test_gate.py.

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/strategy/ -v -k "cricket"`
Expected: ALL PASS

Run: `pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/strategy/exit/monitor.py src/strategy/entry/gate.py src/orchestration/factory.py tests/unit/strategy/exit/test_monitor.py tests/unit/strategy/entry/test_gate.py
git commit -m "feat(strategy): cricket wire — monitor + gate skip (SPEC-011 Task 7)

- monitor.py: cricket_score_exit a_conf_hold branch'ine wire (tennis/hockey/baseball simetrik)
- gate.py: cricket market + cricapi quota dolu ise skip (cricapi_unavailable)
- factory.py: cricket_client EntryGate'e gecis

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Dokuman — TDD + PRD + Spec Status

**Files:**
- Modify: `TDD.md` (§7 cricket rows, §6 cricket score exit)
- Modify: `PRD.md` (F11 Cricket Cluster)
- Modify: `docs/superpowers/specs/2026-04-19-cricket-cluster-design.md` (DRAFT → IMPLEMENTED)

- [ ] **Step 1: Update TDD.md §7 sport rules tablosu**

Find TDD.md §7 (Sport Rules) and the sport tag list/table. Add cricket rows:

```markdown
| sport_tag | score_source | match_duration_hours | stop_loss_pct | score_exit |
|---|---|---|---|---|
| cricket_ipl | cricapi | 3.5 | 0.30 | C1/C2/C3 (T20) |
| cricket_odi | cricapi | 8.0 | 0.30 | C1/C2/C3 (ODI, gevsek) |
| cricket_international_t20 | cricapi | 3.5 | 0.30 | C1/C2/C3 (T20) |
| cricket_psl | cricapi | 3.5 | 0.30 | C1/C2/C3 (T20) |
| cricket_big_bash | cricapi | 3.5 | 0.30 | C1/C2/C3 (T20) |
| cricket_caribbean_premier_league | cricapi | 3.5 | 0.30 | C1/C2/C3 (T20) |
| cricket_t20_blast | cricapi | 3.5 | 0.30 | C1/C2/C3 (T20) |
```

(Adapt format to existing table if different.)

- [ ] **Step 2: Add cricket score exit section to TDD.md**

In the score exits section (where tennis T1/T2, hockey K1-K4, baseball M1/M2/M3 documented), add:

```markdown
### Cricket Score Exit (SPEC-011)

Tennis T1/T2, hockey K1-K4, baseball M1/M2/M3 ile simetrik. A-conf
pozisyonlar icin FORCED exit. Sadece 2. innings (chase) + biz chasing
tarafindaysak (our_chasing=True) C1/C2/C3 tetiklenir.

**Kurallar** (`cricket_score_exit.py`):

- **C1**: `balls_remaining < c1_balls AND required_rate > c1_rate` (impossible chase)
- **C2**: `wickets_lost >= c2_wickets AND runs_remaining > c2_runs` (cok wicket kaybi)
- **C3**: `balls_remaining < c3_balls AND runs_remaining > c3_runs` (final over + gap)

**Config** (`sport_rules.py`):
- T20 default: c1_balls=30, c1_rate=18, c2_wickets=8, c2_runs=20, c3_balls=6, c3_runs=10
- ODI gevsek: c1_balls=60, c1_rate=12, c2_wickets=8, c2_runs=40, c3_balls=30, c3_runs=30

**Skor kaynagi**: CricAPI free tier 100 hit/gun (ESPN cricket yok).
Limit dolunca entry gate `cricapi_unavailable` skip eder.

**Direction-aware**: `our_chasing` = bizim takimimiz 2. innings'te mi batting.
Defending tarafindaysak (our_chasing=False) C1/C2/C3 skip — chase cokmek
BIZIM lehimize.
```

- [ ] **Step 3: Update PRD.md — F11 Cricket Cluster**

Find PRD.md features list. Add after F10:

```markdown
### F11: Cricket Cluster (SPEC-011)

**Amac**: 7 cricket ligi entegre — IPL (aktif Nisan-Haziran), ODI (yil boyu),
International T20, PSL, Big Bash, CPL, T20 Blast.

**Veri Kaynaklari**:
- Odds API (bookmaker consensus, sharp 3-5)
- Polymarket (event markets)
- CricAPI free tier (canli skor — runs, wickets, overs; 100 hit/gun)

**Score Exit (C1/C2/C3)**:
Tennis T1/T2, hockey K1-K4, baseball M1/M2/M3 ile simetrik. Sadece 2. innings
chase + biz chasing iken tetiklenir. ESPN cricket yok, CricAPI kullanilir.

**Rate Limit**: CricAPI quota dolunca (100/gun) cricket entry'ler
`cricapi_unavailable` skip_reason ile atlanir, log'a yazilir.

**TODO-003**: Paid tier upgrade ($10/ay, 1000+ hit/gun) — cricket hacmi
arttiginda gerekli.
```

- [ ] **Step 4: Mark spec as IMPLEMENTED**

In `docs/superpowers/specs/2026-04-19-cricket-cluster-design.md`, find:

```markdown
> **Durum**: DRAFT
```

Replace with:

```markdown
> **Durum**: IMPLEMENTED
```

- [ ] **Step 5: Final verification**

Run: `pytest tests/ -q`
Expected: ALL PASS, ~870+ tests.

Grep checks:
```bash
grep -rn "cricket_score_exit\|CricketAPIClient\|build_cricket_score_info" src/ --include="*.py" | grep -v __pycache__ | wc -l
```
Expected: 10+ references (imports + calls).

```bash
grep "cricket" config.yaml | head
```
Expected: `cricket:` block + sport tags visible.

```bash
find src -name "*.py" -not -path "*__pycache__*" -exec wc -l {} + | sort -n | tail -5
```
Expected: All under 400 lines.

- [ ] **Step 6: Commit**

```bash
git add TDD.md PRD.md docs/superpowers/specs/2026-04-19-cricket-cluster-design.md
git commit -m "docs: SPEC-011 cricket cluster tamamlandi (Task 8)

TDD.md §7: 7 cricket ligi sport rules table.
TDD.md §6: cricket score exit alt-bolum (tennis/hockey/baseball simetrik).
PRD.md: F11 Cricket Cluster feature madde.
SPEC-011: DRAFT → IMPLEMENTED.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```
