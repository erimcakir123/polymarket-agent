# Score Matching Fix + Baseball Symmetry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score enricher'in sophisticated pair_matcher kullanmasini sagla, baseball icin tennis/hockey ile simetrik FORCED exit (M1/M2/M3) ekle, SPEC-008 defensive guard'i kaldir, iyi donem config degerlerini geri yukle.

**Architecture:** 6 task. Task 1 score matching fix (en kritik). Task 2 baseball_score_exit yeni dosya + unit test. Task 3 monitor wire. Task 4 SPEC-008 baseball guard sil. Task 5 config rollback (edge, max_bet, scale-out). Task 6 docs + final verification.

**Tech Stack:** Python 3.12+, Pydantic, pytest, existing pair_matcher module

---

### Task 1: Score Enricher — pair_matcher Wire

**Files:**
- Modify: `src/orchestration/score_enricher.py:53-107` (replace `_team_match`, `_find_espn_match`, `_find_match`)
- Modify: `tests/unit/orchestration/test_score_enricher.py` (update helper tests)

- [ ] **Step 1: Update import block in score_enricher.py**

Find (around line 19-23):
```python
from src.config.sport_rules import _normalize, get_sport_rule
from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.infrastructure.apis.score_client import MatchScore, fetch_scores
from src.infrastructure.persistence.archive_logger import (
    ArchiveLogger,
    ArchiveMatchResult,
    ArchiveScoreEvent,
)
from src.models.position import Position
from src.strategy.enrichment.question_parser import extract_teams
```

Add before `from src.models.position import Position`:
```python
from src.domain.matching.pair_matcher import match_pair, match_team
```

- [ ] **Step 2: Replace _team_match, _find_espn_match, _find_match with single function**

Find (around line 53-107) the 3 functions `_team_match`, `_find_espn_match`, `_find_match`. DELETE all three.

Replace with single new function:

```python
def _find_match_via_pair(
    pos: Position,
    scores: list,
    home_attr: str,
    away_attr: str,
    min_confidence: float = 0.80,
) -> object | None:
    """pair_matcher kullanarak skor listesinden eslesen event'i bul.

    home_attr/away_attr: ESPN icin "home_name"/"away_name", Odds API icin
    "home_team"/"away_team". Ayni logic her iki kaynakta calisir.

    Pair matching: team_a + team_b verildi → her iki takim da eslemeli
    (swap destekli). Sadece team_a verildi → single-team fallback.
    """
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None

    best_match = None
    best_conf = 0.0

    for ms in scores:
        home = getattr(ms, home_attr, "") or ""
        away = getattr(ms, away_attr, "") or ""
        if not home or not away:
            continue

        if team_b:
            # Pair matching: HER IKI takim da eslemeli (normal + swap)
            is_match, conf = match_pair((team_a, team_b), (home, away))
            if is_match and conf > best_conf:
                best_match = ms
                best_conf = conf
        else:
            # Single team fallback
            mh, ch, _ = match_team(team_a, home)
            ma, ca, _ = match_team(team_a, away)
            best_side = max(ch, ca)
            if (mh or ma) and best_side > best_conf:
                best_match = ms
                best_conf = best_side

    return best_match if best_conf >= min_confidence else None
```

- [ ] **Step 3: Update _match_cached to use new function**

Find `_match_cached` method in `ScoreEnricher` class (around line 265-304). Replace internal calls:

Old:
```python
            espn_scores = self._cached_espn.get(tag, [])
            if espn_scores:
                em = _find_espn_match(pos, espn_scores)
                if em:
                    result[cid] = _build_score_info(pos, em)
                    matched_score_obj = em

            if matched_score_obj is None:
                odds_scores = self._cached_odds.get(tag, [])
                if odds_scores:
                    ms = _find_match(pos, odds_scores)
                    if ms:
                        result[cid] = _build_score_info(pos, ms)
                        matched_score_obj = ms
```

New:
```python
            espn_scores = self._cached_espn.get(tag, [])
            if espn_scores:
                em = _find_match_via_pair(pos, espn_scores, "home_name", "away_name")
                if em:
                    result[cid] = _build_score_info(pos, em)
                    matched_score_obj = em

            if matched_score_obj is None:
                odds_scores = self._cached_odds.get(tag, [])
                if odds_scores:
                    ms = _find_match_via_pair(pos, odds_scores, "home_team", "away_team")
                    if ms:
                        result[cid] = _build_score_info(pos, ms)
                        matched_score_obj = ms
```

- [ ] **Step 4: Update test_score_enricher.py helper tests**

In `tests/unit/orchestration/test_score_enricher.py`, find tests named `test_team_match_*` and `test_find_match_*`. These tested internal functions that no longer exist. Replace with pair-based tests:

```python
def test_find_match_via_pair_exact_names():
    """pair_matcher: tam isim eslesmesi."""
    from src.orchestration.score_enricher import _find_match_via_pair
    from src.infrastructure.apis.espn_client import ESPNMatchScore

    pos = _pos_with_event(
        event_id="E1",
        question="Boston Red Sox vs. New York Yankees",
        sport_tag="mlb",
    )
    scores = [
        ESPNMatchScore(
            event_id="x", home_name="Boston Red Sox", away_name="New York Yankees",
            home_score=1, away_score=0, period="Top 5th",
            is_completed=False, is_live=True, last_updated="",
            linescores=[], commence_time="",
        ),
    ]
    result = _find_match_via_pair(pos, scores, "home_name", "away_name")
    assert result is not None
    assert result.home_name == "Boston Red Sox"


def test_find_match_via_pair_swapped_order():
    """pair_matcher: home/away ters olsa bile eslesme."""
    from src.orchestration.score_enricher import _find_match_via_pair
    from src.infrastructure.apis.espn_client import ESPNMatchScore

    pos = _pos_with_event(
        event_id="E1",
        question="Boston Red Sox vs. New York Yankees",
        sport_tag="mlb",
    )
    # ESPN home=Yankees, away=Red Sox (ters sirada)
    scores = [
        ESPNMatchScore(
            event_id="x", home_name="New York Yankees", away_name="Boston Red Sox",
            home_score=3, away_score=2, period="Top 5th",
            is_completed=False, is_live=True, last_updated="",
            linescores=[], commence_time="",
        ),
    ]
    result = _find_match_via_pair(pos, scores, "home_name", "away_name")
    assert result is not None


def test_find_match_via_pair_phantom_no_match():
    """Phantom matchup: Polymarket slug gercek ESPN maciyla eslesmiyor."""
    from src.orchestration.score_enricher import _find_match_via_pair
    from src.infrastructure.apis.espn_client import ESPNMatchScore

    pos = _pos_with_event(
        event_id="E1",
        question="Tampa Bay Rays vs. Pittsburgh Pirates",
        sport_tag="mlb",
    )
    # ESPN'de Tampa vs Yankees var (phantom Polymarket slug)
    scores = [
        ESPNMatchScore(
            event_id="x", home_name="Tampa Bay Rays", away_name="New York Yankees",
            home_score=0, away_score=1, period="Top 9th",
            is_completed=True, is_live=False, last_updated="",
            linescores=[], commence_time="",
        ),
    ]
    # Pittsburgh yok → match_pair False dondurmeli
    result = _find_match_via_pair(pos, scores, "home_name", "away_name")
    assert result is None


def test_find_match_via_pair_low_confidence_rejected():
    """Confidence < 0.80 olan eslesme reddedilmeli."""
    from src.orchestration.score_enricher import _find_match_via_pair
    from src.infrastructure.apis.espn_client import ESPNMatchScore

    pos = _pos_with_event(
        event_id="E1",
        question="Abc vs. Xyz",
        sport_tag="mlb",
    )
    scores = [
        ESPNMatchScore(
            event_id="x", home_name="Unrelated Team", away_name="Another Team",
            home_score=0, away_score=0, period="",
            is_completed=False, is_live=False, last_updated="",
            linescores=[], commence_time="",
        ),
    ]
    result = _find_match_via_pair(pos, scores, "home_name", "away_name")
    assert result is None
```

Delete old tests: `test_team_match_exact`, `test_team_match_substring`, `test_team_match_last_word`, `test_team_match_no_match`, `test_find_match_by_team_name`, `test_find_match_no_match`.

Keep these existing tests (they call higher-level methods, pair_matcher is used internally):
- `test_build_score_info_*` (tests `_build_score_info` pure)
- `test_enricher_*` (integration tests calling `get_scores_if_due`)
- `test_find_espn_match_*` — rename and update to call `_find_match_via_pair` if they test match logic
- `test_score_change_logs_to_archive` (archive)
- `test_match_completion_logs_result` (archive)

For `test_find_espn_match_skips_wrong_match_same_player`, `test_find_espn_match_correct_two_team`, `test_find_espn_match_single_team_fallback`, `test_find_espn_match_prefers_correct_over_old`:
- Rename to `test_find_match_via_pair_skips_wrong_match_same_player`, etc.
- Replace `_find_espn_match(pos, scores)` call with `_find_match_via_pair(pos, scores, "home_name", "away_name")`

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/unit/orchestration/test_score_enricher.py -v
```
Expected: ALL PASS

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/ -x -q
```
Expected: ALL PASS (tennis/hockey tests that depend on score_enricher should still work)

- [ ] **Step 7: Commit**

```bash
git add src/orchestration/score_enricher.py tests/unit/orchestration/test_score_enricher.py
git commit -m "feat(score-enricher): pair_matcher wire (SPEC-010 Task 1)

Basit substring _team_match kaldirildi, sophisticated pair_matcher
kullaniliyor artik. Alias, fuzzy, swap order, confidence threshold
destekli. Phantom matchup'larda yanlis baglanti yok.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: baseball_score_exit.py — Yeni Dosya + Unit Testler

**Files:**
- Create: `src/strategy/exit/baseball_score_exit.py`
- Create: `tests/unit/strategy/exit/test_baseball_score_exit.py`
- Modify: `src/config/sport_rules.py` (mlb config: comeback_thresholds sil, score_exit thresholds ekle)

- [ ] **Step 1: Update sport_rules.py mlb config**

In `src/config/sport_rules.py`, find the `"mlb":` block. Replace the existing block (around the lines currently containing `comeback_thresholds` and `extra_inning_threshold`):

Old:
```python
    "mlb": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.0,
        "inning_exit": True,
        "inning_exit_deficit": 5,
        "inning_exit_after": 6,
        "comeback_thresholds": {3: 6, 5: 5, 7: 4, 8: 3, 9: 2},
        "extra_inning_threshold": 1,
        "score_source": "espn",
        "espn_sport": "baseball",
        "espn_league": "mlb",
    },
```

New:
```python
    "mlb": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.0,
        # SPEC-010: M1/M2/M3 forced exit (tennis T1/T2, hockey K1-K4 simetrik)
        "score_exit_m1_inning": 7,     # M1 tetik inning (blowout)
        "score_exit_m1_deficit": 5,    # M1 run deficit threshold
        "score_exit_m2_inning": 8,     # M2 tetik inning (late big deficit)
        "score_exit_m2_deficit": 3,    # M2 run deficit threshold
        "score_exit_m3_inning": 9,     # M3 tetik inning (final inning)
        "score_exit_m3_deficit": 1,    # M3 run deficit threshold
        "score_source": "espn",
        "espn_sport": "baseball",
        "espn_league": "mlb",
    },
```

Also check if there are similar blocks for `"kbo"`, `"npb"`, `"baseball"` generic. For any that exist, add the same 6 `score_exit_m*` keys with same values (kbo/npb/baseball use same rules).

If `kbo`/`npb`/`baseball` blocks don't exist in sport_rules, they'll fall back to `get_sport_rule` defaults (7, 5, 8, 3, 9, 1) which is what we want.

- [ ] **Step 2: Write failing test (TDD red)**

Create `tests/unit/strategy/exit/test_baseball_score_exit.py`:

```python
"""baseball_score_exit.py unit tests (SPEC-010)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit.baseball_score_exit import (
    BaseballExitResult,
    _parse_inning,
    check,
)


def _score_info(inning_str: str, our_score: int, opp_score: int) -> dict:
    """Test helper: score_info dict olustur."""
    return {
        "available": True,
        "period": inning_str,
        "deficit": opp_score - our_score,
        "our_score": our_score,
        "opp_score": opp_score,
    }


# ── Parse testleri ─────────────────────────────────────────────

def test_parse_inning_top_1st():
    assert _parse_inning("Top 1st") == 1


def test_parse_inning_bot_5th():
    assert _parse_inning("Bot 5th") == 5


def test_parse_inning_mid_9th():
    assert _parse_inning("Mid 9th") == 9


def test_parse_inning_extra_11th():
    assert _parse_inning("Top 11th") == 11


def test_parse_inning_empty_returns_none():
    assert _parse_inning("") is None


def test_parse_inning_final_returns_none():
    assert _parse_inning("Final") is None


def test_parse_inning_in_progress_returns_none():
    assert _parse_inning("In Progress") is None


# ── M1: Blowout (7th+ + 5 run deficit) ─────────────────────────

def test_m1_blowout_7th_5run_exits():
    """7. inning, 5 run geride → M1 exit."""
    info = _score_info("Top 7th", our_score=0, opp_score=5)
    r = check(info, current_price=0.20, sport_tag="mlb")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "M1" in r.detail


def test_m1_blowout_7th_4run_no_exit():
    """7. inning, 4 run geride → M1 tetiklenmez (threshold 5)."""
    info = _score_info("Top 7th", our_score=0, opp_score=4)
    r = check(info, current_price=0.20, sport_tag="mlb")
    # M1 yok, M2 (8. inning+ 3 run) tetiklenmez (inning 7), M3 (9. inning+) yok
    assert r is None


def test_m1_blowout_8th_5run_exits():
    """8. inning, 5 run geride → M1 (inning 8 >= 7)."""
    info = _score_info("Bot 8th", our_score=2, opp_score=7)
    r = check(info, current_price=0.10, sport_tag="mlb")
    assert r is not None
    assert "M1" in r.detail


# ── M2: Late big deficit (8th+ + 3 run) ────────────────────────

def test_m2_late_deficit_8th_3run_exits():
    """8. inning, 3 run geride → M2 exit."""
    info = _score_info("Top 8th", our_score=2, opp_score=5)
    r = check(info, current_price=0.25, sport_tag="mlb")
    assert r is not None
    assert "M2" in r.detail


def test_m2_late_deficit_8th_2run_no_exit():
    """8. inning, 2 run geride → M2 tetiklenmez (threshold 3)."""
    info = _score_info("Top 8th", our_score=3, opp_score=5)
    r = check(info, current_price=0.30, sport_tag="mlb")
    # M1 yok (4 run < 5), M2 yok (2 run < 3), M3 yok (inning 8 < 9)
    assert r is None


# ── M3: Final inning (9th+ + 1 run) ────────────────────────────

def test_m3_final_inning_1run_exits():
    """9. inning, 1 run geride → M3 exit."""
    info = _score_info("Top 9th", our_score=3, opp_score=4)
    r = check(info, current_price=0.15, sport_tag="mlb")
    assert r is not None
    assert "M3" in r.detail


def test_m3_extra_inning_1run_exits():
    """11. inning (extra), 1 run geride → M3 exit (inning >= 9)."""
    info = _score_info("Top 11th", our_score=5, opp_score=6)
    r = check(info, current_price=0.10, sport_tag="mlb")
    assert r is not None
    assert "M3" in r.detail


# ── Non-exit cases ─────────────────────────────────────────────

def test_deficit_zero_no_exit():
    """Esit skor → exit yok."""
    info = _score_info("Top 9th", our_score=3, opp_score=3)
    r = check(info, current_price=0.50, sport_tag="mlb")
    assert r is None


def test_leading_no_exit():
    """Onde → exit yok (deficit negatif)."""
    info = _score_info("Top 9th", our_score=5, opp_score=2)
    r = check(info, current_price=0.90, sport_tag="mlb")
    assert r is None


def test_score_info_unavailable_no_exit():
    info = {"available": False}
    r = check(info, current_price=0.30, sport_tag="mlb")
    assert r is None


def test_period_unparseable_no_exit():
    info = _score_info("In Progress", our_score=1, opp_score=5)
    r = check(info, current_price=0.30, sport_tag="mlb")
    assert r is None


def test_early_inning_big_deficit_no_exit():
    """1. inning, 6 run geride ama M1 threshold 7. inning → exit yok."""
    info = _score_info("Top 1st", our_score=0, opp_score=6)
    r = check(info, current_price=0.10, sport_tag="mlb")
    assert r is None


def test_kbo_sport_tag_uses_defaults():
    """KBO sport_tag'iyle de calisir (default thresholds)."""
    info = _score_info("Top 9th", our_score=3, opp_score=5)
    r = check(info, current_price=0.10, sport_tag="kbo")
    # 9. inning + 2 run deficit → M3 (default deficit=1) tetiklenmeli
    assert r is not None
    assert "M3" in r.detail
```

- [ ] **Step 3: Run test — verify FAIL**

```bash
python -m pytest tests/unit/strategy/exit/test_baseball_score_exit.py -v
```
Expected: FAIL with "No module named 'src.strategy.exit.baseball_score_exit'"

- [ ] **Step 4: Create baseball_score_exit.py**

Create `src/strategy/exit/baseball_score_exit.py`:

```python
"""Baseball inning-based score exit (SPEC-010) — pure.

A-conf pozisyonlar icin FORCED exit kurallari. Tennis T1/T2 ve
hockey K1-K4 ile simetrik.

M1: Blowout — inning >= 7 AND deficit >= 5
M2: Late big deficit — inning >= 8 AND deficit >= 3
M3: Final inning — inning >= 9 AND deficit >= 1

deficit = opp_score - our_score (pozitif = gerideyiz)
Esikler sport_rules.py config'inden (magic number yok).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason

_INNING_RE = re.compile(r"(\d+)(?:st|nd|rd|th)")


@dataclass
class BaseballExitResult:
    """Baseball exit sonucu — monitor.py ExitSignal'a cevirir."""

    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    current_price: float,
    sport_tag: str = "mlb",
) -> BaseballExitResult | None:
    """Baseball M1/M2/M3 exit kontrolu.

    Args:
        score_info: score_enricher'dan gelen dict (available, period, deficit, ...)
        current_price: pozisyonun o anki fiyati (suan direct kullanilmiyor,
            gelecekteki genisletme icin rezerv)
        sport_tag: "mlb", "kbo", "npb", "baseball" — config lookup icin

    Returns:
        BaseballExitResult → cik; None → tetiklenmedi.
    """
    if not score_info.get("available"):
        return None

    period = score_info.get("period", "")
    inning = _parse_inning(period)
    if inning is None:
        return None

    deficit = score_info.get("deficit", 0)
    if deficit <= 0:
        return None  # onde veya esit

    # Config thresholds (sport_rules.py)
    m1_inning = int(get_sport_rule(sport_tag, "score_exit_m1_inning", 7))
    m1_deficit = int(get_sport_rule(sport_tag, "score_exit_m1_deficit", 5))
    m2_inning = int(get_sport_rule(sport_tag, "score_exit_m2_inning", 8))
    m2_deficit = int(get_sport_rule(sport_tag, "score_exit_m2_deficit", 3))
    m3_inning = int(get_sport_rule(sport_tag, "score_exit_m3_inning", 9))
    m3_deficit = int(get_sport_rule(sport_tag, "score_exit_m3_deficit", 1))

    # M1: blowout
    if inning >= m1_inning and deficit >= m1_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M1: inning={inning} deficit={deficit} threshold={m1_deficit}",
        )

    # M2: late big deficit
    if inning >= m2_inning and deficit >= m2_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M2: inning={inning} deficit={deficit} threshold={m2_deficit}",
        )

    # M3: final inning, any deficit
    if inning >= m3_inning and deficit >= m3_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M3: inning={inning} deficit={deficit} threshold={m3_deficit}",
        )

    return None


def _parse_inning(period: str) -> int | None:
    """ESPN period stringinden inning numarasi.

    "Top 1st" → 1, "Bot 5th" → 5, "Mid 9th" → 9, "Top 11th" → 11.
    Parse edilemezse None.
    """
    if not period:
        return None
    m = _INNING_RE.search(period)
    return int(m.group(1)) if m else None
```

- [ ] **Step 5: Run test — verify PASS**

```bash
python -m pytest tests/unit/strategy/exit/test_baseball_score_exit.py -v
```
Expected: ALL PASS (17 tests)

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/ -x -q
```
Expected: ALL PASS (mevcut testler baseball guard'da hala calisiyor — Task 4'te temizlenecek)

- [ ] **Step 7: Commit**

```bash
git add src/strategy/exit/baseball_score_exit.py tests/unit/strategy/exit/test_baseball_score_exit.py src/config/sport_rules.py
git commit -m "feat(exit): baseball_score_exit M1/M2/M3 — tennis/hockey simetri (SPEC-010 Task 2)

Tennis T1/T2 ve hockey K1-K4 gibi A-conf pozisyonlar icin FORCED
exit. Inning ve deficit bazli 3 kural:
  M1: 7. inning+ 5 run deficit (blowout)
  M2: 8. inning+ 3 run deficit (late big deficit)
  M3: 9. inning+ 1 run deficit (final inning)

sport_rules.py: comeback_thresholds kaldirildi, score_exit_m* eklendi.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: monitor.py — baseball_score_exit Wire

**Files:**
- Modify: `src/strategy/exit/monitor.py` (import + a_conf_hold branch'ine ekle)
- Modify: `tests/unit/strategy/exit/test_monitor.py` (wire test)

- [ ] **Step 1: Write integration test (TDD red)**

In `tests/unit/strategy/exit/test_monitor.py`, add:

```python
def test_baseball_score_exit_triggers_for_a_conf_mlb(make_position):
    """A-conf MLB pozisyonu + M3 score_info → SCORE_EXIT tetiklenir."""
    pos = make_position(
        sport_tag="mlb",
        confidence="A",
        entry_price=0.65,
        current_price=0.15,  # A-conf hold (entry >= 0.60)
    )
    score_info = {
        "available": True,
        "period": "Top 9th",
        "deficit": 3,  # 3 run geride, 9. inning → M3
        "our_score": 2,
        "opp_score": 5,
    }

    from src.strategy.exit import monitor as exit_monitor
    result = exit_monitor.evaluate(pos, score_info=score_info, scale_out_tiers=[])

    assert result.exit_signal is not None
    assert result.exit_signal.reason == ExitReason.SCORE_EXIT
    assert "M3" in result.exit_signal.detail


def test_baseball_score_exit_doesnt_fire_for_nba(make_position):
    """NBA sport_tag → baseball_score_exit skip."""
    pos = make_position(
        sport_tag="nba",
        confidence="A",
        entry_price=0.65,
        current_price=0.55,
    )
    score_info = {
        "available": True,
        "period": "Top 9th",
        "deficit": 5,
        "our_score": 0,
        "opp_score": 5,
    }

    from src.strategy.exit import monitor as exit_monitor
    result = exit_monitor.evaluate(pos, score_info=score_info, scale_out_tiers=[])

    # NBA baseball_score_exit'i skip eder — M1/M2/M3 tetiklenmez
    # Ama NBA icin score-based exit yok, tek korumasi market_flip + near_resolve
    # score_exit reason tetiklenmemeli
    if result.exit_signal is not None:
        assert result.exit_signal.reason != ExitReason.SCORE_EXIT
```

If `make_position` helper fixture doesn't exist, add it. Check file for existing patterns. If tests use inline Position(...) construction, follow that pattern — adapt the test accordingly.

- [ ] **Step 2: Run test — verify FAIL**

```bash
python -m pytest tests/unit/strategy/exit/test_monitor.py::test_baseball_score_exit_triggers_for_a_conf_mlb -v
```
Expected: FAIL — baseball_score_exit not wired

- [ ] **Step 3: Update monitor.py imports**

In `src/strategy/exit/monitor.py`, find line 22:

```python
from src.strategy.exit import a_conf_hold, catastrophic_watch, favored, graduated_sl, near_resolve, scale_out, hockey_score_exit, stop_loss, tennis_score_exit
```

Replace with (add `baseball_score_exit`):

```python
from src.strategy.exit import a_conf_hold, baseball_score_exit, catastrophic_watch, favored, graduated_sl, near_resolve, scale_out, hockey_score_exit, stop_loss, tennis_score_exit
```

- [ ] **Step 4: Wire baseball_score_exit in a_conf_hold branch**

In `src/strategy/exit/monitor.py`, find the tennis_score_exit block (around line 199-211). After the tennis block, BEFORE the market_flip block (around line 213), add:

```python
        # 3a-baseball. Score-based exit — baseball (SPEC-010 M1/M2/M3)
        if _normalize(pos.sport_tag) in ("mlb", "kbo", "npb", "baseball") and score_info.get("available"):
            b_result = baseball_score_exit.check(
                score_info=score_info,
                current_price=pos.current_price,
                sport_tag=pos.sport_tag,
            )
            if b_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(reason=b_result.reason, detail=b_result.detail),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )
```

The full a_conf_hold branch should now check: tennis → baseball → hockey (score) → market_flip (last resort).

Exact placement: after the `tennis_score_exit` `if t_result is not None: return ...` block.

- [ ] **Step 5: Run test — verify PASS**

```bash
python -m pytest tests/unit/strategy/exit/test_monitor.py::test_baseball_score_exit_triggers_for_a_conf_mlb -v
```
Expected: PASS

- [ ] **Step 6: Run all monitor tests**

```bash
python -m pytest tests/unit/strategy/exit/test_monitor.py -v
```
Expected: ALL PASS

- [ ] **Step 7: Run full test suite**

```bash
python -m pytest tests/ -x -q
```
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
git add src/strategy/exit/monitor.py tests/unit/strategy/exit/test_monitor.py
git commit -m "feat(monitor): baseball_score_exit wire — a_conf_hold branch (SPEC-010 Task 3)

Tennis T1/T2 ve hockey K1-K4 gibi baseball M1/M2/M3 de A-conf
pozisyonlarda FORCED exit yapar. sport_tag: mlb, kbo, npb, baseball.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: SPEC-008 Baseball Guard Sil

**Files:**
- Modify: `src/strategy/exit/stop_loss.py` (parse_baseball_inning, is_baseball_alive, baseball block, score_info param sil)
- Modify: `src/strategy/exit/monitor.py` (stop_loss.check() score_info param kaldir)
- Delete: `tests/unit/strategy/exit/test_baseball_guard.py`
- Modify: `tests/unit/strategy/exit/test_stop_loss.py` (baseball guard testleri kaldir varsa)

- [ ] **Step 1: Delete test_baseball_guard.py**

```bash
rm tests/unit/strategy/exit/test_baseball_guard.py
```

If file doesn't exist, skip.

- [ ] **Step 2: Replace stop_loss.py**

Replace ENTIRE contents of `src/strategy/exit/stop_loss.py`:

```python
"""Flat stop-loss helper — 6-katman oncelik (TDD §6.7).

Tek kaynak: hem WebSocket path (exit_monitor._ws_check_exits) hem light cycle
(monitor.py) buradan cagirir.

Katmanlar (oncelik sirasina gore):
  1. Stale price skip (WS tick gelmedi → fake -100% PnL)
  2. Totals/spread skip (hold to resolution, SL yok)
  3. Ultra-low entry (eff < 9¢) → genis %50 SL
  4. Low-entry graduated (9-20¢) → linear %60 → %40
  5. Sport-specific SL (sport_rules.py)
  6. Lossy reentry carpani (×0.75)

Not (SPEC-010): SPEC-008 baseball inning guard kaldirildi. Baseball
forced exit artik baseball_score_exit.py'da (tennis/hockey ile simetrik).
A-conf pozisyonlar zaten monitor.py'da flat SL'yi atliyor — baseball
guard A-conf'ta calismazdi.
"""
from __future__ import annotations

from src.config.sport_rules import get_stop_loss
from src.models.position import Position

_ULTRA_LOW_THRESHOLD = 0.09
_LOW_ENTRY_UPPER = 0.20
_LOW_ENTRY_SL_HIGH = 0.60
_LOW_ENTRY_SL_LOW = 0.40
_REENTRY_MULT = 0.75
_TOTALS_KEYWORDS = ("o/u", "total", "spread")


def compute_stop_loss_pct(pos: Position) -> float | None:
    """Pozisyon icin dogru SL yuzdesini hesapla.

    Returns:
        float: SL yuzdesi (ornek 0.30 = %30).
        None: bu pozisyonda flat SL UYGULANMAZ (totals/spread, stale price).
    """
    # 1. Stale price — WS tick hic gelmemis gibi
    if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
        return None

    # 2. Totals/spread — hold to resolution
    q = (pos.question or "").lower()
    slug = (pos.slug or "").lower()
    if any(k in q or k in slug for k in _TOTALS_KEYWORDS):
        return None

    # entry_price zaten token-native (owned side).
    eff_entry = pos.entry_price

    # 3. Ultra-low entry — genis %50 SL
    if eff_entry < _ULTRA_LOW_THRESHOLD:
        sl = 0.50
    elif eff_entry < _LOW_ENTRY_UPPER:
        # 4. Low-entry graduated: 9¢ → %60, 20¢ → %40 linear
        t = (eff_entry - _ULTRA_LOW_THRESHOLD) / (_LOW_ENTRY_UPPER - _ULTRA_LOW_THRESHOLD)
        sl = _LOW_ENTRY_SL_HIGH - t * (_LOW_ENTRY_SL_HIGH - _LOW_ENTRY_SL_LOW)
    else:
        # 5. Sport-specific SL
        sl = get_stop_loss(pos.sport_tag)

    # 6. Lossy reentry carpani
    if pos.sl_reentry_count >= 1:
        sl *= _REENTRY_MULT

    return sl


def check(pos: Position) -> bool:
    """Flat SL tetiklendi mi? True → exit sinyali.

    unrealized_pnl_pct < -sl_pct tetikler. None sl_pct → False (muaf).
    """
    sl = compute_stop_loss_pct(pos)
    if sl is None:
        return False
    return pos.unrealized_pnl_pct < -sl
```

This removes:
- `parse_baseball_inning()` (moved to baseball_score_exit.py as `_parse_inning`)
- `is_baseball_alive()`
- Import of `re`, `get_sport_rule`, `_normalize`
- `_INNING_RE` constant
- `score_info: dict | None = None` param from both functions
- Baseball block in `compute_stop_loss_pct()` (lines 82-88)

- [ ] **Step 3: Update monitor.py stop_loss.check call**

In `src/strategy/exit/monitor.py`, find `stop_loss.check(pos, score_info)` (around line 224). Replace:

Old:
```python
            if stop_loss.check(pos, score_info):
```

New:
```python
            if stop_loss.check(pos):
```

- [ ] **Step 4: Update test_stop_loss.py if baseball tests exist**

```bash
python -m pytest tests/unit/strategy/exit/test_stop_loss.py -v 2>&1 | head -40
```

If any tests fail because of removed `score_info` parameter or baseball-specific tests, update them:
- Remove `score_info=...` arg from `stop_loss.check(pos, score_info=...)` calls → `stop_loss.check(pos)`
- Remove any `test_baseball_*` tests that test removed functions

- [ ] **Step 5: Run all tests**

```bash
python -m pytest tests/ -x -q
```
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/strategy/exit/stop_loss.py src/strategy/exit/monitor.py tests/unit/strategy/exit/test_stop_loss.py
git rm tests/unit/strategy/exit/test_baseball_guard.py 2>/dev/null || true
git commit -m "refactor(stop-loss): SPEC-008 baseball inning guard kaldirildi (SPEC-010 Task 4)

SPEC-008 defensive guard A-conf'ta zaten calismiyordu (A-conf monitor'da
SL'yi atliyor). Baseball forced exit artik baseball_score_exit.py'da
tennis/hockey ile simetrik calisiyor (SPEC-010 Task 2-3).

- stop_loss.py: parse_baseball_inning, is_baseball_alive, baseball block sil
- stop_loss.py: score_info param kaldir (kullanilmiyor)
- monitor.py: stop_loss.check() score_info gecisini kaldir
- test_baseball_guard.py sil

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Config Rollback — Edge, Scale-out, max_single_bet_usdc

**Files:**
- Modify: `config.yaml` (edge multiplier, scale_out tiers, risk.max_single_bet_usdc)
- Modify: `src/config/settings.py` (RiskConfig.max_single_bet_usdc field geri)
- Modify: `src/domain/risk/position_sizer.py` (max_bet_usdc param geri)
- Modify: `src/strategy/entry/gate.py` (max_single_bet_usdc field + kullanim)
- Modify: `src/orchestration/factory.py` (max_single_bet_usdc gecis)
- Modify: `tests/unit/domain/risk/test_position_sizer.py` (cap testleri ekle)

- [ ] **Step 1: Update config.yaml**

In `config.yaml`:

Find (around line 63-66):
```yaml
edge:
  min_edge: 0.06
  confidence_multipliers:
    A: 0.67    # sharp data güvenilir → düşük eşik (%4). Eski: 1.25
    B: 1.00    # reputable-only → baz eşik (%6)
```

Replace with:
```yaml
edge:
  min_edge: 0.06
  confidence_multipliers:
    A: 1.00    # SPEC-010: iyi donem degeri (%6 eşik). Onceki: 0.67 (%4)
    B: 1.00    # reputable-only → baz eşik (%6)
```

Find (around line 69-71):
```yaml
risk:
  max_bet_pct: 0.05
  confidence_bet_pct:
```

Replace with:
```yaml
risk:
  max_single_bet_usdc: 50           # SPEC-010: bet tavani geri, iyi donemde max $56'da kalmıştı
  max_bet_pct: 0.05
  confidence_bet_pct:
```

Find scale_out section (around line 110-115):
```yaml
scale_out:
  enabled: true
  tiers:
    - threshold: 0.35
      sell_pct: 0.25
    - threshold: 0.50
      sell_pct: 0.50
```

Replace with:
```yaml
scale_out:
  enabled: true
  tiers:
    - threshold: 0.25    # SPEC-010: iyi donem — agresif erken kar kilitle
      sell_pct: 0.40
    - threshold: 0.50
      sell_pct: 0.50
```

- [ ] **Step 2: Update settings.py RiskConfig**

In `src/config/settings.py`, find `RiskConfig`:

Old:
```python
class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_bet_pct: float = 0.05
    confidence_bet_pct: dict[str, float] = {"A": 0.05, "B": 0.04}
    max_positions: int = 20
    ...
```

Replace with:
```python
class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_single_bet_usdc: float = 50    # SPEC-010: bet tavani
    max_bet_pct: float = 0.05
    confidence_bet_pct: dict[str, float] = {"A": 0.05, "B": 0.04}
    max_positions: int = 20
    ...
```

Keep remaining fields (max_exposure_pct, hard_cap_overflow_pct, etc.) untouched.

- [ ] **Step 3: Update position_sizer.py**

Replace `src/domain/risk/position_sizer.py` ENTIRE content:

```python
"""Confidence-based position sizing (TDD §6.5) — pure, no I/O.

Confidence bet yuzdeleri config'den gelir (ARCH_GUARD Kural 6).
max_bet_usdc cap (SPEC-010) + max_bet_pct cap (yuzde) birlikte uygulanir.
"""
from __future__ import annotations

REENTRY_MULTIPLIER = 0.80
POLYMARKET_MIN_ORDER_USDC = 5.0


def confidence_position_size(
    confidence: str,
    bankroll: float,
    confidence_bet_pct: dict[str, float],
    max_bet_usdc: float = 50.0,
    max_bet_pct: float = 0.05,
    is_reentry: bool = False,
) -> float:
    """Confidence tier bazli pozisyon boyutu.

    Args:
        confidence_bet_pct: config'den {"A": 0.05, "B": 0.04}.
        max_bet_usdc: USDC cinsinden tek-bet tavan (SPEC-010: $50).
        max_bet_pct: bankroll % cinsinden tavan.

    Tabloda olmayan confidence → 0 (entry bloklanir).
    Cap: min(bankroll*bet_pct, max_bet_usdc, bankroll*max_bet_pct, bankroll).
    """
    bet_pct = confidence_bet_pct.get(confidence, 0.0)
    if bet_pct == 0.0:
        return 0.0

    if is_reentry:
        bet_pct *= REENTRY_MULTIPLIER

    size = bankroll * bet_pct
    size = min(size, max_bet_usdc, bankroll * max_bet_pct, bankroll)
    return max(0.0, round(size, 2))
```

- [ ] **Step 4: Update gate.py GateConfig**

In `src/strategy/entry/gate.py`, find `GateConfig` dataclass (around line 40-60). Find the field list and add `max_single_bet_usdc`:

Old (around line 47-50):
```python
    confidence_bet_pct: dict[str, float] = field(default_factory=lambda: {"A": 0.05, "B": 0.04})
    max_bet_pct: float = 0.05
    max_entry_price: float = 0.88
```

Replace with:
```python
    confidence_bet_pct: dict[str, float] = field(default_factory=lambda: {"A": 0.05, "B": 0.04})
    max_single_bet_usdc: float = 50.0    # SPEC-010: bet tavani
    max_bet_pct: float = 0.05
    max_entry_price: float = 0.88
```

Then find the position_sizer call (around line 175). Add `max_bet_usdc` argument:

Old:
```python
        raw_size = confidence_position_size(
            confidence=signal.confidence,
            bankroll=self.portfolio.bankroll,
            confidence_bet_pct=self.config.confidence_bet_pct,
            max_bet_pct=self.config.max_bet_pct,
        )
```

New:
```python
        raw_size = confidence_position_size(
            confidence=signal.confidence,
            bankroll=self.portfolio.bankroll,
            confidence_bet_pct=self.config.confidence_bet_pct,
            max_bet_usdc=self.config.max_single_bet_usdc,
            max_bet_pct=self.config.max_bet_pct,
        )
```

- [ ] **Step 5: Update factory.py**

In `src/orchestration/factory.py`, find the `GateConfig(...)` construction (around line 87-105). Add `max_single_bet_usdc`:

Old:
```python
    gate_cfg = GateConfig(
        min_edge=cfg.edge.min_edge,
        max_positions=cfg.risk.max_positions,
        max_exposure_pct=cfg.risk.max_exposure_pct,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_bet_pct=cfg.risk.max_bet_pct,
        max_entry_price=cfg.risk.max_entry_price,
```

Replace with:
```python
    gate_cfg = GateConfig(
        min_edge=cfg.edge.min_edge,
        max_positions=cfg.risk.max_positions,
        max_exposure_pct=cfg.risk.max_exposure_pct,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_single_bet_usdc=cfg.risk.max_single_bet_usdc,
        max_bet_pct=cfg.risk.max_bet_pct,
        max_entry_price=cfg.risk.max_entry_price,
```

- [ ] **Step 6: Update test_position_sizer.py**

In `tests/unit/domain/risk/test_position_sizer.py`, add these tests (or update existing):

```python
def test_max_bet_usdc_cap_applied():
    """max_bet_usdc cap: bankroll*pct > cap olsa bile cap devrede (SPEC-010)."""
    from src.domain.risk.position_sizer import confidence_position_size
    result = confidence_position_size(
        "A", bankroll=10_000,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
        max_bet_usdc=50.0,
    )
    # 10_000 × 5% = 500, ama cap 50 → 50
    assert result == 50.0


def test_max_bet_usdc_below_cap_not_clipped():
    """bankroll dusukse cap devrede degil."""
    from src.domain.risk.position_sizer import confidence_position_size
    result = confidence_position_size(
        "A", bankroll=500,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
        max_bet_usdc=50.0,
    )
    # 500 × 5% = 25, cap 50 → 25
    assert result == 25.0
```

Also find the existing `test_no_hard_cap` test (added in SPEC-008). It tested that cap was removed. Delete it OR update to the new expected behavior:

Old test (if exists):
```python
def test_no_hard_cap():
    """max_single_bet_usdc kaldirildi — $75 cap yok."""
    result = confidence_position_size("A", bankroll=10_000, confidence_bet_pct=BET_PCT)
    assert result == 500.0
```

Delete this test or replace with:
```python
def test_max_bet_usdc_default_cap_50():
    """SPEC-010: default max_bet_usdc=50."""
    from src.domain.risk.position_sizer import confidence_position_size
    result = confidence_position_size(
        "A", bankroll=10_000, confidence_bet_pct={"A": 0.05, "B": 0.04},
    )
    # Default max_bet_usdc=50, 10_000 × 5% = 500 → capped at 50
    assert result == 50.0
```

Other existing tests with bankroll=1000 should still pass (1000 × 5% = 50 = default cap, exactly at limit).

Check for any test calling `confidence_position_size` without `max_bet_usdc` kwarg — those rely on defaults, should still pass.

- [ ] **Step 7: Run all tests**

```bash
python -m pytest tests/ -x -q
```
Expected: ALL PASS (may need to fix a few tests around position_sizer)

If `test_agent.py` has GateConfig construction, add `max_single_bet_usdc=50.0` there too.

- [ ] **Step 8: Commit**

```bash
git add config.yaml src/config/settings.py src/domain/risk/position_sizer.py src/strategy/entry/gate.py src/orchestration/factory.py tests/unit/domain/risk/test_position_sizer.py tests/unit/orchestration/test_agent.py tests/unit/strategy/entry/test_gate.py
git commit -m "feat(config): iyi donem config rollback + max_bet \$50 (SPEC-010 Task 5)

- edge.confidence_multipliers.A: 0.67 → 1.00 (eşik %4 → %6)
- risk.max_single_bet_usdc: 50 ekle (bet tavani geri)
- scale_out tiers: +%25/%40 + +%50/%50 (orijinal, SPEC-008 oncesi)

Bet sizing: min(bankroll×pct, max_bet_usdc, ...) — 3-way cap.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Docs Update + Final Verification

**Files:**
- Modify: `TDD.md` (§6.7 baseball guard kaldir; baseball score exit ekle)
- Modify: `PRD.md` (F-madde baseball score exit)
- Modify: `docs/superpowers/specs/2026-04-18-baseball-inning-guard-design.md` (durum SUPERSEDED_BY SPEC-010)
- Modify: `docs/superpowers/specs/2026-04-19-score-matching-baseball-symmetry-design.md` (durum IMPLEMENTED)

- [ ] **Step 1: Update TDD.md §6.7**

Find §6.7 `stop_loss.py` section in TDD.md. Remove references to baseball_inning_guard:
- "Katman 2.5 Baseball canlılık guard" bolumunu kaldir
- parse_baseball_inning, is_baseball_alive aciklamalarini kaldir
- comeback_thresholds referansini kaldir

Add a new section §6.X "Baseball Score Exit" (next to tennis T1/T2 and hockey K1-K4):

```markdown
### §6.X Baseball Score Exit (SPEC-010)

Tennis T1/T2 ve hockey K1-K4 gibi A-conf pozisyonlar için FORCED exit:

- **M1**: `inning >= 7 AND deficit >= 5` (blowout)
- **M2**: `inning >= 8 AND deficit >= 3` (late big deficit)
- **M3**: `inning >= 9 AND deficit >= 1` (final inning)

Config: `score_exit_m*_inning` ve `score_exit_m*_deficit` `sport_rules.py`'de.
Tetiklendiğinde `ExitReason.SCORE_EXIT` döner.

deficit = opp_score - our_score (pozitif = geride).
```

- [ ] **Step 2: Update PRD.md**

Find F-madde list. Add new feature (or merge into existing F9):

```markdown
### F10: Baseball Score Exit (SPEC-010)

**Amaç**: A-conf baseball pozisyonlarda maç tersine giderken full wipeout
önlenir. Tennis T1/T2 ve hockey K1-K4 ile simetrik FORCED exit.

**Kurallar**:
- M1: 7. inning+ ve ≥5 run deficit → exit
- M2: 8. inning+ ve ≥3 run deficit → exit
- M3: 9. inning+ ve ≥1 run deficit → exit

**Eski sistem (SPEC-008)**: defensive guard (SL ertele), A-conf'ta
çalışmıyordu. Kaldırıldı.
```

- [ ] **Step 3: Mark SPEC-008 as superseded**

In `docs/superpowers/specs/2026-04-18-baseball-inning-guard-design.md`, change the status line:

Old:
```
> **Durum:** DRAFT
```

Or whatever the current status is. Replace with:
```
> **Durum:** SUPERSEDED_BY SPEC-010 (baseball guard kaldirildi, yerine baseball_score_exit.py FORCED exit geldi)
```

- [ ] **Step 4: Update SPEC-010 status**

In `docs/superpowers/specs/2026-04-19-score-matching-baseball-symmetry-design.md`, change status:

Old:
```
> **Durum**: DRAFT
```

New:
```
> **Durum**: IMPLEMENTED
```

- [ ] **Step 5: Final verification**

Run full test suite:
```bash
python -m pytest tests/ -v 2>&1 | tail -20
```
Expected: ALL PASS

Grep to verify cleanup:
```bash
grep -rn "parse_baseball_inning\|is_baseball_alive\|comeback_thresholds" src/ --include="*.py" | grep -v __pycache__
```
Expected: 0 results (all baseball guard code removed).

```bash
grep -rn "_team_match\|_find_espn_match\|_find_match(pos" src/ --include="*.py" | grep -v __pycache__ | grep -v "find_match_via_pair\|match_pair\|match_team"
```
Expected: 0 results (old match functions removed).

```bash
grep -n "max_single_bet_usdc" config.yaml
```
Expected: `max_single_bet_usdc: 50`

- [ ] **Step 6: Commit**

```bash
git add TDD.md PRD.md docs/superpowers/specs/2026-04-18-baseball-inning-guard-design.md docs/superpowers/specs/2026-04-19-score-matching-baseball-symmetry-design.md
git commit -m "docs: SPEC-010 tamamlandi — matching fix + baseball symmetry + rollback

TDD.md: baseball_inning_guard kaldirildi, baseball_score_exit eklendi.
PRD.md: F10 baseball score exit.
SPEC-008: SUPERSEDED_BY SPEC-010.
SPEC-010: IMPLEMENTED.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```
