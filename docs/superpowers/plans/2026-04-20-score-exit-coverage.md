# SPEC-014 Score-Exit Coverage Bug Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 3 score-exit bug fix: AHL → hockey family'ye bağlan, MLB inning ESPN `status.period`'dan parse et, `score_at_exit` archive'a dolu yaz.

**Architecture:** AHL sport_rules NHL'i spread ile paylaşır. ESPN parse `status.period` int'ini kullanır, `_parse_inning` regex ölü kodu silinir. `score_enricher._match_cached` pozisyona `match_score`/`match_period` yazar.

**Tech Stack:** Python 3.12, pytest. ARCH_GUARD: <400 satır, domain I/O yok, magic number yok, dead code temizle.

---

### Task 1: MLB ESPN inning parse (Bug #2)

**Files:**
- Modify: `src/infrastructure/apis/espn_client.py` — `ESPNMatchScore.inning: int | None` field + parse
- Modify: `src/orchestration/score_enricher.py` — `_build_score_info` `inning` geçirir
- Modify: `src/strategy/exit/baseball_score_exit.py` — `score_info["inning"]` okur, `_INNING_RE` + `_parse_inning` silinir
- Modify: `tests/unit/infrastructure/apis/test_espn_client.py` — MLB inning parse testi
- Modify: `tests/unit/strategy/exit/test_baseball_score_exit.py` — period→inning signature

- [ ] **Step 1: Diag — canlı ESPN MLB response'unda `status.period` doğrula**

`scripts/diag_mlb_espn.py` (yeni, disposable):
```python
"""MLB ESPN API response inceleme — inning hangi field'da?"""
import json, requests
r = requests.get(
    "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    timeout=15,
)
data = r.json()
for event in data.get("events", [])[:3]:
    for comp in event.get("competitions", [{}])[:1]:
        status = comp.get("status", {})
        print(f"Event: {event.get('name', '')[:60]}")
        print(f"  status.period: {status.get('period')}")
        print(f"  status.type.description: {status.get('type', {}).get('description', '')}")
        print(f"  status.type.detail: {status.get('type', {}).get('detail', '')}")
        print(f"  status.type.state: {status.get('type', {}).get('state', '')}")
```

Run: `python scripts/diag_mlb_espn.py`
Expected output pattern: `status.period: 7` (int) for in-progress games, `0` or missing for pre-game.

**Karar**: Eğer `status.period` int dönüyorsa → Task devam. Eğer dönmüyorsa → fallback regex `status.type.detail` ile "Top 7th" parse. SPEC risk notu.

- [ ] **Step 2: Write failing ESPN parse test**

`tests/unit/infrastructure/apis/test_espn_client.py` içine ekle:

```python
def test_parse_competition_extracts_mlb_inning() -> None:
    """MLB event: status.period int olarak inning -> ESPNMatchScore.inning."""
    from src.infrastructure.apis.espn_client import _parse_competition
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "Yankees"}, "score": "3"},
            {"homeAway": "away", "team": {"displayName": "Red Sox"}, "score": "2"},
        ],
        "status": {
            "period": 7,
            "type": {"description": "Top 7th", "state": "in", "completed": False},
        },
        "startDate": "2026-04-20T18:00:00Z",
    }
    ms = _parse_competition(comp, sport="baseball")
    assert ms is not None
    assert ms.inning == 7
    assert ms.home_score == 3
    assert ms.away_score == 2


def test_parse_competition_mlb_inning_none_pregame() -> None:
    """Pregame: status.period 0 veya eksik -> inning None."""
    from src.infrastructure.apis.espn_client import _parse_competition
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "Yankees"}, "score": "0"},
            {"homeAway": "away", "team": {"displayName": "Red Sox"}, "score": "0"},
        ],
        "status": {
            "period": 0,
            "type": {"description": "Scheduled", "state": "pre", "completed": False},
        },
        "startDate": "2026-04-20T18:00:00Z",
    }
    ms = _parse_competition(comp, sport="baseball")
    assert ms is not None
    assert ms.inning is None  # 0 veya missing -> None


def test_parse_competition_non_baseball_no_inning() -> None:
    """Non-baseball (ör. NHL): inning field default None."""
    from src.infrastructure.apis.espn_client import _parse_competition
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "Rangers"}, "score": "2"},
            {"homeAway": "away", "team": {"displayName": "Bruins"}, "score": "1"},
        ],
        "status": {
            "period": 2,
            "type": {"description": "2nd Period", "state": "in", "completed": False},
        },
        "startDate": "2026-04-20T19:00:00Z",
    }
    ms = _parse_competition(comp, sport="hockey")
    assert ms is not None
    assert ms.inning is None  # non-baseball
```

Run: `pytest tests/unit/infrastructure/apis/test_espn_client.py::test_parse_competition_extracts_mlb_inning -v`
Expected: FAIL (`inning` field yok)

- [ ] **Step 3: Add `inning` to `ESPNMatchScore` dataclass + parse logic**

In `src/infrastructure/apis/espn_client.py`:

```python
@dataclass
class ESPNMatchScore:
    """ESPN scoreboard tek maç."""
    sport: str
    league: str
    event_id: str
    home_name: str
    away_name: str
    home_score: int
    away_score: int
    period: str           # "Final", "In Progress", ""
    is_completed: bool
    commence_time: str
    linescores: list[list[int]] = field(default_factory=list)
    inning: int | None = None   # SPEC-014: MLB-specific, status.period int
```

In `_parse_competition`:

```python
# ... existing parse logic for home/away/scores ...

description: str = type_block.get("description", "")
# ... existing period assignment ...

# SPEC-014: MLB inning parse — status.period int, 0 = pregame
inning: int | None = None
if sport == "baseball":
    raw_period = status_block.get("period")
    if isinstance(raw_period, int) and raw_period > 0:
        inning = raw_period

return ESPNMatchScore(
    sport=sport,
    league=league,
    event_id=event_id,
    home_name=home_name,
    away_name=away_name,
    home_score=home_score,
    away_score=away_score,
    period=description,
    is_completed=is_completed,
    commence_time=commence_time,
    linescores=linescores,
    inning=inning,   # SPEC-014
)
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
pytest tests/unit/infrastructure/apis/test_espn_client.py -v
```
Expected: Yeni 3 test PASS + mevcut PASS

- [ ] **Step 5: `_build_score_info` inning geçirir**

In `src/orchestration/score_enricher.py` find `_build_score_info`. Add `inning` to return dict:

```python
def _build_score_info(pos, ms) -> dict:
    return {
        "available": True,
        # ... existing fields ...
        "inning": getattr(ms, "inning", None),   # SPEC-014: MLB
    }
```

- [ ] **Step 6: Rewrite `baseball_score_exit.py` — int inning, dead code silinir**

Current file uses `_INNING_RE` + `_parse_inning`. Replace:

```python
"""Baseball score exit (MLB/KBO/NPB) — SPEC-010 + SPEC-014.

M1: Late-inning big deficit (blowout)
M2: Mid-late inning deficit
M3: Final inning any deficit

Tum threshold'lar sport_rules.py config'inden (magic number yok).
SPEC-014: inning artik score_info['inning'] int olarak gelir — ESPN
status.period'dan parse edilmis. Regex-based _parse_inning olu kod.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class BaseballExitResult:
    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    current_price: float,
    sport_tag: str = "mlb",
) -> BaseballExitResult | None:
    """M1/M2/M3 exit kontrolu."""
    if not score_info.get("available"):
        return None

    inning = score_info.get("inning")
    if not isinstance(inning, int) or inning <= 0:
        return None

    home_score = int(score_info.get("home_score", 0))
    away_score = int(score_info.get("away_score", 0))
    our_is_home = bool(score_info.get("our_is_home", False))

    if our_is_home:
        deficit = away_score - home_score
    else:
        deficit = home_score - away_score

    if deficit <= 0:
        return None  # onde/berabere -> exit yok

    m1_inning = int(get_sport_rule(sport_tag, "score_exit_m1_inning", 7))
    m1_deficit = int(get_sport_rule(sport_tag, "score_exit_m1_deficit", 5))
    m2_inning = int(get_sport_rule(sport_tag, "score_exit_m2_inning", 8))
    m2_deficit = int(get_sport_rule(sport_tag, "score_exit_m2_deficit", 3))
    m3_inning = int(get_sport_rule(sport_tag, "score_exit_m3_inning", 9))
    m3_deficit = int(get_sport_rule(sport_tag, "score_exit_m3_deficit", 1))

    if inning >= m1_inning and deficit >= m1_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M1: inn={inning} deficit={deficit} threshold={m1_deficit}",
        )
    if inning >= m2_inning and deficit >= m2_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M2: inn={inning} deficit={deficit} threshold={m2_deficit}",
        )
    if inning >= m3_inning and deficit >= m3_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M3: inn={inning} deficit={deficit} threshold={m3_deficit}",
        )
    return None
```

`_INNING_RE` ve `_parse_inning` tamamen kaldırıldı (dead code).

- [ ] **Step 7: Update existing baseball tests**

`tests/unit/strategy/exit/test_baseball_score_exit.py` — tüm testlerde `score_info` içinde `"period": "Top 7th"` gibi string yerine `"inning": 7` int kullan.

Grep + replace pattern.

- [ ] **Step 8: Run tests**

```bash
pytest tests/unit/strategy/exit/test_baseball_score_exit.py -v
pytest tests/unit/orchestration/test_score_enricher.py -v
pytest tests/ -x -q
```
Expected: ALL PASS, no regression

- [ ] **Step 9: Commit Task 1**

```bash
git add src/infrastructure/apis/espn_client.py src/orchestration/score_enricher.py src/strategy/exit/baseball_score_exit.py tests/unit/infrastructure/apis/test_espn_client.py tests/unit/strategy/exit/test_baseball_score_exit.py scripts/diag_mlb_espn.py
git commit -m "feat(baseball): ESPN MLB inning parse from status.period (SPEC-014 Task 1)

Bug #2 fix: MLB M1/M2/M3 score-exit tetiklenmiyordu cunku:
- ESPN response 'period' field (string 'In Progress') kullaniliyordu
- baseball_score_exit _parse_inning regex 'In Progress' matchlemiyordu
- inning None -> check erken return

Fix:
- ESPNMatchScore.inning: int | None (SPEC-014)
- _parse_competition MLB icin status.period int'ini okuyor
- score_enricher _build_score_info inning geciyor
- baseball_score_exit: _parse_inning + _INNING_RE silindi (dead code)
- 3 yeni test (ESPN parse), mevcut testler int formata migrate

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: AHL sport rules + hockey family (Bug #1)

**Files:**
- Modify: `src/config/sport_rules.py` — SPORT_RULES'a "ahl" bloğu
- Modify: `src/strategy/exit/hockey_score_exit.py` — `_is_hockey` → `_is_hockey_family`
- Modify: `src/strategy/exit/monitor.py` — `== "nhl"` → `_is_hockey_family(tag)`
- Modify: `tests/unit/config/test_sport_rules.py` — AHL inherits NHL
- Modify: `tests/unit/strategy/exit/test_hockey_score_exit.py` — AHL K1-K4 testi
- Modify: `tests/unit/strategy/exit/test_monitor.py` — AHL score-exit tetiği

- [ ] **Step 1: Write failing tests**

`tests/unit/config/test_sport_rules.py` — ekle:

```python
def test_ahl_inherits_nhl_thresholds() -> None:
    from src.config.sport_rules import get_sport_rule
    # NHL ile AHL aynı K1-K4 eşikleri paylaşır
    assert get_sport_rule("ahl", "period_exit_deficit") == get_sport_rule("nhl", "period_exit_deficit")
    assert get_sport_rule("ahl", "late_deficit") == get_sport_rule("nhl", "late_deficit")
    assert get_sport_rule("ahl", "final_elapsed_gate") == get_sport_rule("nhl", "final_elapsed_gate")


def test_ahl_has_own_espn_league() -> None:
    from src.config.sport_rules import get_sport_rule
    assert get_sport_rule("ahl", "espn_league") == "ahl"
    assert get_sport_rule("ahl", "espn_sport") == "hockey"


def test_normalize_ahl_returns_ahl() -> None:
    from src.config.sport_rules import _normalize
    assert _normalize("ahl") == "ahl"  # kendi key'i var (alias degil)
```

Run: `pytest tests/unit/config/test_sport_rules.py -v`
Expected: FAIL

- [ ] **Step 2: Add AHL block to `src/config/sport_rules.py`**

Find SPORT_RULES "nhl" block. AFTER nhl entry, add:

```python
    "ahl": {
        # SPEC-014: NHL eşiklerini paylaşır, sadece ESPN league farklı
        # Spread önemli — NHL eşik değişirse AHL de takip eder (drift imkansız)
    },
```

Wait — Python dict spread with literal value insertion inside dict literal is tricky. Approach: post-dict assignment:

```python
# NHL block dogrudan dict literal icinde kalir (mevcut).

# SPEC-014: AHL — NHL family, ESPN AHL endpoint
SPORT_RULES["ahl"] = {
    **SPORT_RULES["nhl"],
    "espn_league": "ahl",
}
```

Ekle SPORT_RULES dict kapatıldıktan sonra, `DEFAULT_RULES`'dan önce.

- [ ] **Step 3: Update `hockey_score_exit.py` — `_is_hockey_family`**

```python
_HOCKEY_FAMILY: frozenset[str] = frozenset({"nhl", "ahl"})


def _is_hockey_family(sport_tag: str) -> bool:
    """NHL + AHL — ayni K1-K4 kurallari."""
    from src.config.sport_rules import _normalize
    return _normalize(sport_tag) in _HOCKEY_FAMILY


# Backward-compat alias (silinebilir future):
_is_hockey = _is_hockey_family
```

- [ ] **Step 4: Update `monitor.py` — kullan `_is_hockey_family`**

Import + satır 188 değişir:

```python
from src.strategy.exit.hockey_score_exit import _is_hockey_family

# ...

# 3a. Score-based exit — hockey A-conf only (SPEC-004 K1-K4)
if _is_hockey_family(pos.sport_tag) and score_info.get("available"):
    sc_result = hockey_score_exit.check(...)
```

- [ ] **Step 5: Write monitor integration test**

`tests/unit/strategy/exit/test_monitor.py` — ekle:

```python
def test_monitor_triggers_score_exit_for_ahl() -> None:
    """AHL A-conf pozisyon + score_info deficit=3 -> SCORE_EXIT."""
    from src.models.enums import ExitReason
    from src.models.position import Position
    from src.strategy.exit import monitor as exit_monitor

    pos = Position(
        condition_id="cid", token_id="tok", direction="BUY_YES",
        entry_price=0.65, size_usdc=45.0, shares=69.2, slug="ahl-leh-cha-2026",
        confidence="A", anchor_probability=0.65, current_price=0.30,
        sport_tag="ahl", question="Lehigh Valley Phantoms vs Charlotte",
        match_start_iso="2026-04-19T18:00:00Z",
    )
    score_info = {
        "available": True,
        "home_score": 5, "away_score": 2,
        "our_is_home": False,
        "period": "3rd Period",
        "period_num": 3,
    }
    result = exit_monitor.evaluate(pos, score_info=score_info, scale_out_tiers=[])
    assert result.exit_signal is not None
    assert result.exit_signal.reason == ExitReason.SCORE_EXIT
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/unit/config/test_sport_rules.py -v
pytest tests/unit/strategy/exit/test_hockey_score_exit.py -v
pytest tests/unit/strategy/exit/test_monitor.py -v
pytest tests/ -x -q
```
Expected: ALL PASS

- [ ] **Step 7: Commit Task 2**

```bash
git add src/config/sport_rules.py src/strategy/exit/hockey_score_exit.py src/strategy/exit/monitor.py tests/unit/config/test_sport_rules.py tests/unit/strategy/exit/test_hockey_score_exit.py tests/unit/strategy/exit/test_monitor.py
git commit -m "feat(hockey): AHL -> hockey family (SPEC-014 Task 2)

Bug #1 fix: AHL score-exit hicbir zaman tetiklenmiyordu cunku:
- sport_rules.py SPORT_RULES'ta 'ahl' key yoktu
- _normalize('ahl') -> '' -> DEFAULT_RULES
- monitor.py '_normalize(tag) == 'nhl'' -> AHL icin False

Fix:
- SPORT_RULES['ahl'] = {**SPORT_RULES['nhl'], 'espn_league': 'ahl'}
  (spread ile NHL eşik drift'i imkansiz)
- hockey_score_exit._is_hockey_family (NHL + AHL frozenset)
- monitor.py import + tek satir guncelleme

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: score_at_exit doğru yazımı (Bug #3)

**Files:**
- Modify: `src/orchestration/score_enricher.py` — `_match_cached` pos.match_score yazar
- Modify: `tests/unit/orchestration/test_score_enricher.py` — pos.match_score yazılma testi

- [ ] **Step 1: Write failing test**

`tests/unit/orchestration/test_score_enricher.py` — ekle:

```python
def test_score_enricher_writes_match_score_to_position() -> None:
    """_match_cached pos.match_score/period alanlarina yazmali (SPEC-014)."""
    from unittest.mock import MagicMock
    from src.infrastructure.apis.espn_client import ESPNMatchScore
    from src.orchestration.score_enricher import ScoreEnricher

    # Minimal enricher + synthetic ESPN match
    enricher = ScoreEnricher(espn_client=None, odds_client=None)
    # Manuel inject cache
    espn_score = ESPNMatchScore(
        sport="hockey", league="nhl", event_id="E1",
        home_name="Rangers", away_name="Bruins",
        home_score=3, away_score=1,
        period="End of 2nd Period",
        is_completed=False, commence_time="2026-04-20T18:00:00Z",
        linescores=[[1,0],[2,1]],
    )
    enricher._cached_espn = {"nhl": [espn_score]}

    pos = _pos_with_event(
        event_id="E1", question="Rangers vs. Bruins", sport_tag="nhl",
    )
    # match_score/period bosken baslat
    pos.match_score = ""
    pos.match_period = ""

    result = enricher._match_cached({"cid1": pos})
    # score eslesmeli, pos.match_score yazilmali
    assert "cid1" in result
    assert pos.match_score == "3-1"
    assert pos.match_period == "End of 2nd Period"


def test_score_enricher_no_match_leaves_position_fields_unchanged() -> None:
    """Eslesme yoksa pos.match_score dokunulmaz."""
    from src.orchestration.score_enricher import ScoreEnricher

    enricher = ScoreEnricher(espn_client=None, odds_client=None)
    enricher._cached_espn = {"nhl": []}

    pos = _pos_with_event(event_id="E1", question="Rangers vs. Bruins", sport_tag="nhl")
    pos.match_score = "previous"
    pos.match_period = "prev_period"

    enricher._match_cached({"cid1": pos})
    # Eslesme yok -> dokunulmaz
    assert pos.match_score == "previous"
    assert pos.match_period == "prev_period"
```

NOT: `_pos_with_event` test helper mevcut file'da zaten olmalı — varsa kullan, yoksa minimal inline oluştur.

Run: `pytest tests/unit/orchestration/test_score_enricher.py::test_score_enricher_writes_match_score_to_position -v`
Expected: FAIL

- [ ] **Step 2: Update `_match_cached` to write pos.match_score**

In `src/orchestration/score_enricher.py` find `_match_cached`. Eşleşme bulunduğunda (yani `matched_score_obj is not None`) pozisyona yazar:

```python
def _match_cached(self, positions: dict[str, Position]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for cid, pos in positions.items():
        # Cricket path (SPEC-011)
        if is_cricket_sport(pos.sport_tag):
            # ... existing cricket logic ...
            continue

        tag = _normalize(pos.sport_tag)
        matched_score_obj = None

        # ESPN cache priority
        espn_scores = self._cached_espn.get(tag, [])
        if espn_scores:
            em = _find_match_via_pair(pos, espn_scores, "home_name", "away_name")
            if em:
                result[cid] = _build_score_info(pos, em)
                matched_score_obj = em

        # Odds API fallback
        if matched_score_obj is None:
            odds_scores = self._cached_odds.get(tag, [])
            if odds_scores:
                ms = _find_match_via_pair(pos, odds_scores, "home_team", "away_team")
                if ms:
                    result[cid] = _build_score_info(pos, ms)
                    matched_score_obj = ms

        # SPEC-014: Pozisyon state mutasyonu — match_score/period yaz
        if matched_score_obj is not None:
            pos.match_score = f"{matched_score_obj.home_score}-{matched_score_obj.away_score}"
            pos.match_period = getattr(matched_score_obj, "period", "") or ""
            # Archive log (mevcut)
            self._maybe_log_score_event(pos, matched_score_obj)
            self._maybe_log_match_result(pos, matched_score_obj)

    return result
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/unit/orchestration/test_score_enricher.py -v
pytest tests/ -x -q
```
Expected: ALL PASS

- [ ] **Step 4: Commit Task 3**

```bash
git add src/orchestration/score_enricher.py tests/unit/orchestration/test_score_enricher.py
git commit -m "feat(score): score_enricher writes match_score to position (SPEC-014 Task 3)

Bug #3 fix: score_at_exit archive'da hep bostu cunku:
- Position.match_score/period alanlari tanimli ama doldurulmuyordu
- exit_processor pos.match_score okuyor ama yazan yoktu
- Sonuc: 13/13 exit kaydi score_at_exit='' (SPEC-009 baltalanmis)

Fix:
- _match_cached eslesme bulunca pos.match_score = f'{home}-{away}'
- pos.match_period = ms.period
- 2 yeni test

Exit_processor kodu degistirilmedi — zaten pos.match_score okuyor,
simdi dolu geliyor.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: TDD update + dead code verification

**Files:**
- Modify: `TDD.md` §7.2 — AHL NHL kuralları paylaşımı + baseball inning kaynağı

- [ ] **Step 1: Find TDD.md sport rules section**

Grep: `grep -n "§7.2\|AHL\|hockey\|period_exit\|inning" TDD.md`

Mevcut sport rules tablosunda AHL satırı var mı kontrol et.

- [ ] **Step 2: Update TDD.md**

AHL satırı eklenir (veya NHL notu güncellenir):

```markdown
### 7.2 NHL / AHL (hockey family)

NHL + AHL aynı K1-K4 eşiklerini paylaşır — AHL NHL'i dict spread ile genişletir,
sadece `espn_league` farklı ("ahl"). Kural: hockey_score_exit._is_hockey_family
tek kaynakta tanımlı, monitor ondan çağırır.

**Baseball inning kaynağı (SPEC-014)**:
- ESPN response'da `status.period` int (MLB için 1-9+, 0=pregame)
- `status.type.description` dilsel ("In Progress"/"Top 7th") — kullanılmaz
- `ESPNMatchScore.inning: int | None` — baseball dışında None
- `score_info['inning']` baseball_score_exit tarafından doğrudan okunur
  (eski _parse_inning regex kaldırıldı — dead code)
```

- [ ] **Step 3: Final verification**

```bash
pytest tests/ -q
```
Expected: ALL PASS

Dead code grep:
```bash
grep -rn "_parse_inning\|_INNING_RE" src/ | grep -v __pycache__
```
Expected: 0 sonuç

Old pattern grep:
```bash
grep -rn "_normalize.*== *.nhl" src/ | grep -v __pycache__
```
Expected: 0 sonuç (helper'a taşındı)

Archive check — yeni exit'lerde `score_at_exit` dolu mu (bot çalışırsa görülür; bu commit'te değil).

- [ ] **Step 4: Update spec doc status**

`docs/superpowers/specs/2026-04-20-score-exit-coverage-design.md`:
```markdown
**Durum**: IMPLEMENTED (2026-04-20)
```

- [ ] **Step 5: Commit Task 4**

```bash
git add TDD.md docs/superpowers/specs/2026-04-20-score-exit-coverage-design.md
git commit -m "docs: SPEC-014 score-exit coverage IMPLEMENTED (Task 4)

TDD §7.2: AHL hockey family + baseball inning kaynağı (status.period)
SPEC-014 status: IMPLEMENTED

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: Bug #1 (Task 2), Bug #2 (Task 1), Bug #3 (Task 3), docs (Task 4)
- [x] **No placeholders**: tüm kod blokları tam, grep komutları concrete
- [x] **Type consistency**: `inning: int | None` tüm yerlerde aynı, `_is_hockey_family` tek kaynak
- [x] **Dead code**: `_parse_inning` + `_INNING_RE` Task 1'de silinir

## Plan tamamlandı
