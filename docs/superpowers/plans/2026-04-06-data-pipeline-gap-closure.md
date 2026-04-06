# Data Pipeline Gap Closure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate all known data-pipeline gaps that cause the bot to miss bookmaker odds, misparse team names, or silently skip unknown sports — closing every path where a Polymarket match could be under-analysed.

**Architecture:** Six independent tasks, each touching one concern. T1 adds missing Odds API sport-key mappings; T2 hardens the probability engine for bookmaker-less markets; T3 widens the question parser; T4 adds unknown-slug alerting; T5 persists the `/sports` tag cache to disk; T6 adds missing ESPN league mappings. Every task follows TDD — failing test first, then implementation, then green run.

**Tech Stack:** Python 3.11, pytest, Pydantic, requests, existing `src/matching/` + `src/probability_engine.py` modules

---

### Task 1: Odds API Sport-Key Mapping Expansion

**Files:**
- Modify: `src/matching/odds_sport_keys.py:16-131`
- Test: `tests/test_odds_sport_keys.py`

Adds mappings for boxing, cricket, rugby, AFL, WNBA, NCAA basketball, and extra European soccer leagues that The Odds API supports but our mapping currently misses.

- [ ] **Step 1: Write failing tests for new slug mappings**

Append to `tests/test_odds_sport_keys.py`:

```python
def test_slug_prefix_to_odds_key_boxing():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("box") == "boxing_boxing"


def test_slug_prefix_to_odds_key_cricket():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("ipl") == "cricket_ipl"
    assert slug_to_odds_key("cric") == "cricket_test_match"


def test_slug_prefix_to_odds_key_rugby():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("ruprem") == "rugbyunion_premiership"
    assert slug_to_odds_key("rusixnat") == "rugbyunion_six_nations"
    assert slug_to_odds_key("ruurc") == "rugbyunion_urc"


def test_slug_prefix_to_odds_key_afl():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("afl") == "aussierules_afl"


def test_slug_prefix_to_odds_key_wnba():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("wnba") == "basketball_wnba"


def test_slug_prefix_to_odds_key_ncaab():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("cbb") == "basketball_ncaab"
    assert slug_to_odds_key("ncaab") == "basketball_ncaab"


def test_slug_prefix_to_odds_key_extra_soccer():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("sui") == "soccer_switzerland_superleague"
    assert slug_to_odds_key("pol") == "soccer_poland_ekstraklasa"
    assert slug_to_odds_key("cze1") == "soccer_czech_republic_fnl"
    assert slug_to_odds_key("fin") == "soccer_finland_veikkausliiga"


def test_tag_to_odds_key_cricket():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("indian-premier-league") == "cricket_ipl"
    assert tag_to_odds_key("cricket") == "cricket_test_match"


def test_tag_to_odds_key_rugby():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("six-nations") == "rugbyunion_six_nations"
    assert tag_to_odds_key("rugby-premiership") == "rugbyunion_premiership"
    assert tag_to_odds_key("united-rugby-championship") == "rugbyunion_urc"


def test_tag_to_odds_key_afl():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("afl") == "aussierules_afl"


def test_tag_to_odds_key_boxing():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("boxing") == "boxing_boxing"


def test_tag_to_odds_key_wnba():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("wnba") == "basketball_wnba"


def test_tag_to_odds_key_extra_soccer():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("swiss-super-league") == "soccer_switzerland_superleague"
    assert tag_to_odds_key("ekstraklasa") == "soccer_poland_ekstraklasa"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_odds_sport_keys.py -v`
Expected: All new tests FAIL with `AssertionError` (slug/tag returns `None`).

- [ ] **Step 3: Add mappings to `_SLUG_TO_ODDS`**

In `src/matching/odds_sport_keys.py`, add to `_SLUG_TO_ODDS` dict (inside the existing dict, after the `"aus"` entry around line 82):

```python
    # Boxing
    "box": "boxing_boxing",
    # Cricket
    "ipl": "cricket_ipl",
    "cric": "cricket_test_match",
    "cricipl": "cricket_ipl",
    "cricbbl": "cricket_big_bash",
    "cricpsl": "cricket_psl",
    "criccpl": "cricket_caribbean_premier_league",
    "cricilt20": "cricket_ipl",  # alias
    # Rugby Union
    "ruprem": "rugbyunion_premiership",
    "rusixnat": "rugbyunion_six_nations",
    "ruurc": "rugbyunion_urc",
    "ruchamp": "rugbyunion_european_champions_cup",
    "rueuchamp": "rugbyunion_european_champions_cup",
    # Rugby League
    "nrl": "rugbyleague_nrl",
    # AFL
    "afl": "aussierules_afl",
    # WNBA
    "wnba": "basketball_wnba",
    # NCAA
    "cbb": "basketball_ncaab",
    "ncaab": "basketball_ncaab",
    "cwbb": "basketball_wncaab",
    # Extra European soccer
    "sui": "soccer_switzerland_superleague",
    "pol": "soccer_poland_ekstraklasa",
    "cze1": "soccer_czech_republic_fnl",
    "fin": "soccer_finland_veikkausliiga",
    "rou1": "soccer_romania_liga_1",
    "ukr1": "soccer_ukraine_premier_league",
    "hr1": "soccer_croatia_hnl",
    "svk1": "soccer_slovakia_super_liga",
```

- [ ] **Step 4: Add mappings to `_TAG_TO_ODDS`**

In `src/matching/odds_sport_keys.py`, add to `_TAG_TO_ODDS` dict (after the existing `"nfl"` entry around line 131):

```python
    # Boxing
    "boxing": "boxing_boxing",
    # Cricket
    "indian-premier-league": "cricket_ipl",
    "cricket": "cricket_test_match",
    "ipl": "cricket_ipl",
    "big-bash-league": "cricket_big_bash",
    "pakistan-super-league": "cricket_psl",
    # Rugby
    "six-nations": "rugbyunion_six_nations",
    "rugby-premiership": "rugbyunion_premiership",
    "united-rugby-championship": "rugbyunion_urc",
    "european-rugby-champions-cup": "rugbyunion_european_champions_cup",
    # Rugby League
    "nrl": "rugbyleague_nrl",
    # AFL
    "afl": "aussierules_afl",
    # WNBA
    "wnba": "basketball_wnba",
    # Extra soccer
    "swiss-super-league": "soccer_switzerland_superleague",
    "ekstraklasa": "soccer_poland_ekstraklasa",
    "czech-first-league": "soccer_czech_republic_fnl",
    "veikkausliiga": "soccer_finland_veikkausliiga",
    "liga-i": "soccer_romania_liga_1",
    "ukrainian-premier-league": "soccer_ukraine_premier_league",
    "croatian-first-league": "soccer_croatia_hnl",
```

- [ ] **Step 5: Run all tests to verify they pass**

Run: `python -m pytest tests/test_odds_sport_keys.py -v`
Expected: ALL tests PASS (old + new).

- [ ] **Step 6: Commit**

```bash
git add src/matching/odds_sport_keys.py tests/test_odds_sport_keys.py
git commit -m "feat(odds): add boxing, cricket, rugby, AFL, WNBA, NCAA, extra soccer mappings"
```

---

### Task 2: Probability Engine Hardening (Shrinkage + Edge Penalty)

**Files:**
- Modify: `src/probability_engine.py:26-28,120-133`
- Create: `tests/test_probability_engine.py`

Increases the shrinkage factor and edge penalty for bookmaker-less markets to guard against LLM overconfidence.

- [ ] **Step 1: Write failing tests for new shrinkage behaviour**

Create `tests/test_probability_engine.py`:

```python
"""Tests for bookmaker-anchored probability engine."""
import pytest
from src.probability_engine import (
    calculate_anchored_probability,
    get_edge_threshold_adjustment,
    SHRINKAGE_FACTOR,
    BOOK_WEIGHT,
    AI_WEIGHT,
)


def test_shrinkage_factor_is_at_least_020():
    """Guard: shrinkage must be >= 0.20 to counter LLM overconfidence."""
    assert SHRINKAGE_FACTOR >= 0.20


def test_anchored_with_bookmaker():
    """Bookmaker data available -> anchored formula, no penalty."""
    result = calculate_anchored_probability(
        ai_prob=0.75, bookmaker_prob=0.65, num_bookmakers=3
    )
    assert result.method == "anchored"
    expected = BOOK_WEIGHT * 0.65 + AI_WEIGHT * 0.75
    assert result.probability == pytest.approx(expected, abs=0.001)
    assert result.num_bookmakers == 3


def test_shrunk_without_bookmaker():
    """No bookmaker -> shrinkage toward 0.50, higher penalty."""
    result = calculate_anchored_probability(ai_prob=0.75)
    assert result.method == "shrunk_no_bookmaker"
    expected = 0.75 * (1 - SHRINKAGE_FACTOR) + 0.50 * SHRINKAGE_FACTOR
    assert result.probability == pytest.approx(expected, abs=0.001)


def test_shrunk_pulls_toward_50():
    """Shrinkage must noticeably reduce extreme predictions."""
    result = calculate_anchored_probability(ai_prob=0.90)
    assert result.probability < 0.85, "90% AI should shrink below 85%"


def test_edge_adjustment_no_bookmaker():
    """No-bookmaker penalty must be >= 0.04 (was 0.02, too lenient)."""
    result = calculate_anchored_probability(ai_prob=0.75)
    adj = get_edge_threshold_adjustment(result)
    assert adj >= 0.04


def test_edge_adjustment_high_divergence():
    """High divergence penalty must be >= 0.04."""
    result = calculate_anchored_probability(
        ai_prob=0.80, bookmaker_prob=0.55, num_bookmakers=3
    )
    assert result.high_divergence is True
    adj = get_edge_threshold_adjustment(result)
    assert adj >= 0.04


def test_edge_adjustment_normal_anchored():
    """Normal anchored (low divergence) -> no extra penalty."""
    result = calculate_anchored_probability(
        ai_prob=0.65, bookmaker_prob=0.63, num_bookmakers=3
    )
    assert result.high_divergence is False
    adj = get_edge_threshold_adjustment(result)
    assert adj == 0.0


def test_clamps_to_valid_range():
    """Probability must be clamped to [0.05, 0.95]."""
    high = calculate_anchored_probability(ai_prob=0.99)
    assert high.probability <= 0.95
    low = calculate_anchored_probability(ai_prob=0.01)
    assert low.probability >= 0.05
```

- [ ] **Step 2: Run tests to verify failures**

Run: `python -m pytest tests/test_probability_engine.py -v`
Expected: `test_shrinkage_factor_is_at_least_020`, `test_shrunk_pulls_toward_50`, `test_edge_adjustment_no_bookmaker` FAIL (current values too low).

- [ ] **Step 3: Update constants in probability_engine.py**

In `src/probability_engine.py`, change lines 26-28:

```python
# OLD:
SHRINKAGE_FACTOR = 0.10
# NEW:
SHRINKAGE_FACTOR = 0.20
```

And in `get_edge_threshold_adjustment()` (around line 130), change:

```python
# OLD:
    if anchored.method == "shrunk_no_bookmaker":
        return 0.02
# NEW:
    if anchored.method == "shrunk_no_bookmaker":
        return 0.04
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_probability_engine.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Run existing edge calculator tests to verify no breakage**

Run: `python -m pytest tests/test_edge_calculator.py tests/test_edge_decay.py -v`
Expected: ALL PASS (edge_calculator.py is not modified, only its input changes).

- [ ] **Step 6: Commit**

```bash
git add src/probability_engine.py tests/test_probability_engine.py
git commit -m "fix(risk): harden shrinkage 0.10->0.20 and no-bookmaker penalty 0.02->0.04"
```

---

### Task 3: Question Parser Expansion (`_extract_teams`)

**Files:**
- Modify: `src/odds_api.py:578-626`
- Create: `tests/test_extract_teams.py`

Adds "X to beat Y", "Winner: X vs Y", and "X or Y" patterns that appear in some Polymarket questions.

- [ ] **Step 1: Write failing tests for new patterns**

Create `tests/test_extract_teams.py`:

```python
"""Tests for OddsAPIClient._extract_teams question parsing."""
import pytest


def _extract(question: str):
    """Helper: instantiate client and call _extract_teams."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient.__new__(OddsAPIClient)
    return client._extract_teams(question)


# --- Existing patterns (regression tests) ---

def test_vs_pattern():
    a, b = _extract("Manchester City vs Arsenal")
    assert a == "Manchester City"
    assert b == "Arsenal"


def test_will_beat_pattern():
    a, b = _extract("Will the Lakers beat the Celtics?")
    assert a is not None
    assert b is not None


def test_will_win_pattern():
    a, b = _extract("Will Ajax win?")
    assert a is not None
    assert b is None


def test_prefix_stripped():
    a, b = _extract("NBA: Lakers vs Celtics")
    assert a == "Lakers"
    assert b == "Celtics"


# --- NEW patterns ---

def test_to_beat_pattern():
    a, b = _extract("India to beat Australia")
    assert a is not None and "india" in a.lower()
    assert b is not None and "australia" in b.lower()


def test_to_defeat_pattern():
    a, b = _extract("Fnatic to defeat Natus Vincere")
    assert a is not None and "fnatic" in a.lower()
    assert b is not None


def test_winner_colon_pattern():
    a, b = _extract("Winner: Team Liquid vs Cloud9")
    assert a is not None
    assert b is not None


def test_or_pattern_two_teams():
    """'X or Y to win' format seen in some Polymarket markets."""
    a, b = _extract("Will Liverpool or Chelsea win the FA Cup?")
    # Should extract at least one team
    assert a is not None


def test_empty_string():
    a, b = _extract("")
    assert a is None
    assert b is None


def test_no_match():
    a, b = _extract("What is the weather tomorrow?")
    assert a is None
    assert b is None


def test_question_mark_stripped():
    a, b = _extract("Will Sinner beat Alcaraz?")
    assert b is not None
    assert "?" not in b
```

- [ ] **Step 2: Run tests to verify failures**

Run: `python -m pytest tests/test_extract_teams.py -v`
Expected: `test_to_beat_pattern`, `test_to_defeat_pattern`, `test_winner_colon_pattern` FAIL.

- [ ] **Step 3: Add new regex patterns to `_extract_teams`**

In `src/odds_api.py`, in the `_extract_teams` method, add these patterns **after** the existing "Will X beat/defeat Y" block (after line 617) and **before** the "Will X win" block:

```python
        # "X to beat/defeat Y" pattern (cricket, esports)
        to_beat_match = re.search(
            r'(?:the\s+)?(.+?)\s+to\s+(?:beat|defeat|win against|win over)\s+(?:the\s+)?(.+?)[\s?]*$',
            q, re.IGNORECASE,
        )
        if to_beat_match:
            return to_beat_match.group(1).strip(), to_beat_match.group(2).rstrip("?").strip()

        # "Winner: X vs Y" or "Winner of X vs Y" pattern
        winner_match = re.search(
            r'winner\s*(?:of\s*)?:?\s*(.+?)\s+vs\.?\s+(.+?)[\s?]*$',
            q, re.IGNORECASE,
        )
        if winner_match:
            return winner_match.group(1).strip(), winner_match.group(2).rstrip("?").strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_extract_teams.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Run existing odds API tests for regression**

Run: `python -m pytest tests/test_odds_api_bugs.py -v`
Expected: ALL PASS.

- [ ] **Step 6: Commit**

```bash
git add src/odds_api.py tests/test_extract_teams.py
git commit -m "feat(parser): add 'to beat' and 'Winner:' question patterns"
```

---

### Task 4: Unknown Slug Prefix Alerting

**Files:**
- Modify: `src/matching/sport_classifier.py:115-139`
- Modify: `tests/test_odds_sport_keys.py` (add classifier test)
- Create: `tests/test_sport_classifier_alert.py`

When `classify_sport()` returns `None` for a sports market (detected by tag or event context), logs a warning with the unknown prefix so we know to add it.

- [ ] **Step 1: Write failing test for unknown-prefix logging**

Create `tests/test_sport_classifier_alert.py`:

```python
"""Tests for unknown-slug-prefix alerting in sport_classifier."""
import logging


def test_classify_sport_logs_unknown_prefix(caplog):
    """Unknown slug prefix should emit a WARNING log."""
    from src.matching.sport_classifier import classify_sport

    class FakeMarket:
        slug = "handball-ger-vs-fra-2026-04-10"
        sport_tag = ""
        question = "Germany vs France"

    with caplog.at_level(logging.WARNING, logger="src.matching.sport_classifier"):
        result = classify_sport(FakeMarket())

    assert result is None
    assert any("unknown sport prefix" in r.message.lower() for r in caplog.records), \
        f"Expected 'unknown sport prefix' warning, got: {[r.message for r in caplog.records]}"


def test_classify_sport_known_prefix_no_warning(caplog):
    """Known slug prefix should NOT emit a warning."""
    from src.matching.sport_classifier import classify_sport

    class FakeMarket:
        slug = "nba-lal-bos-2026-04-10"
        sport_tag = ""
        question = "Lakers vs Celtics"

    with caplog.at_level(logging.WARNING, logger="src.matching.sport_classifier"):
        result = classify_sport(FakeMarket())

    assert result == "basketball"
    assert not any("unknown sport prefix" in r.message.lower() for r in caplog.records)


def test_classify_sport_empty_slug_no_warning(caplog):
    """Empty slug should not trigger unknown-prefix warning."""
    from src.matching.sport_classifier import classify_sport

    class FakeMarket:
        slug = ""
        sport_tag = ""
        question = "Some random question"

    with caplog.at_level(logging.WARNING, logger="src.matching.sport_classifier"):
        classify_sport(FakeMarket())

    assert not any("unknown sport prefix" in r.message.lower() for r in caplog.records)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_sport_classifier_alert.py -v`
Expected: `test_classify_sport_logs_unknown_prefix` FAILS (no warning emitted currently).

- [ ] **Step 3: Add warning to `classify_sport()`**

In `src/matching/sport_classifier.py`, modify the `classify_sport` function. Add a warning log before the final `return None`:

```python
def classify_sport(market) -> Optional[str]:
    """Classify a Polymarket market into a sport category.

    Checks in order: slug prefix, sport_tag, question keywords.
    Returns category string or None if unclassifiable.
    """
    slug = (getattr(market, "slug", "") or "").lower()
    sport_tag = (getattr(market, "sport_tag", "") or "").lower()

    # 1. Slug prefix (most reliable — Polymarket sport codes)
    prefix = slug.split("-")[0] if slug else ""
    if prefix in _SLUG_TO_CATEGORY:
        return _SLUG_TO_CATEGORY[prefix]

    # 2. sport_tag from market_scanner
    if sport_tag in _SLUG_TO_CATEGORY:
        return _SLUG_TO_CATEGORY[sport_tag]

    # 3. Question keywords
    question = (getattr(market, "question", "") or "").lower()
    for keyword, category in _QUESTION_KEYWORDS.items():
        if keyword in question:
            return category

    # Alert on unknown prefix so we can add mapping
    if prefix and len(prefix) >= 2:
        logger.warning("Unknown sport prefix '%s' in slug '%s' — add to _SLUG_TO_CATEGORY?",
                        prefix, slug[:80])

    return None
```

Also add logger import at the top of the file (if not already present):

```python
import logging
logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sport_classifier_alert.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add src/matching/sport_classifier.py tests/test_sport_classifier_alert.py
git commit -m "feat(alert): log warning on unknown Polymarket slug prefix"
```

---

### Task 5: Persist `/sports` Tag Cache to Disk

**Files:**
- Modify: `src/market_scanner.py:17-27,46-87`
- Add test to: `tests/test_market_scanner.py`

Persists the last successful `/sports` response to `logs/sports_tags_cache.json` so that if the endpoint goes down, we fall back to the last-known-good league tags instead of the 2 useless parent tags.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_market_scanner.py`:

```python
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_league_tags_persist_to_disk(tmp_path):
    """After successful /sports fetch, tags should be saved to disk."""
    from src.market_scanner import MarketScanner
    from src.config import ScannerConfig
    import src.market_scanner as ms

    cache_file = tmp_path / "sports_tags_cache.json"
    original = ms._TAGS_CACHE_FILE
    ms._TAGS_CACHE_FILE = cache_file
    # Reset in-memory cache
    ms._league_tags_cache = []
    ms._league_tags_ts = 0.0

    scanner = MarketScanner(ScannerConfig())

    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"sport": "nba", "tags": "100"},
        {"sport": "epl", "tags": "200"},
    ]
    mock_resp.raise_for_status = MagicMock()

    try:
        with patch("src.market_scanner.requests.get", return_value=mock_resp):
            tags = scanner._fetch_league_tags()

        assert len(tags) == 2
        assert cache_file.exists(), "Cache file should be written to disk"
        saved = json.loads(cache_file.read_text(encoding="utf-8"))
        assert len(saved) == 2
    finally:
        ms._TAGS_CACHE_FILE = original
        ms._league_tags_cache = []
        ms._league_tags_ts = 0.0


def test_league_tags_fallback_to_disk_cache(tmp_path):
    """If /sports fails, should load from disk cache (not parent tags)."""
    from src.market_scanner import MarketScanner, PARENT_TAGS
    from src.config import ScannerConfig
    import src.market_scanner as ms

    cache_file = tmp_path / "sports_tags_cache.json"
    cache_file.write_text(json.dumps([["nba", 100], ["epl", 200]]), encoding="utf-8")
    original = ms._TAGS_CACHE_FILE
    ms._TAGS_CACHE_FILE = cache_file
    ms._league_tags_cache = []
    ms._league_tags_ts = 0.0

    scanner = MarketScanner(ScannerConfig())

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("503 Service Unavailable")

    try:
        with patch("src.market_scanner.requests.get", return_value=mock_resp):
            tags = scanner._fetch_league_tags()

        # Should get disk-cached tags, NOT parent tags
        assert len(tags) == 2
        assert tags != PARENT_TAGS
        assert tags[0] == ("nba", 100)
    finally:
        ms._TAGS_CACHE_FILE = original
        ms._league_tags_cache = []
        ms._league_tags_ts = 0.0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_market_scanner.py::test_league_tags_persist_to_disk tests/test_market_scanner.py::test_league_tags_fallback_to_disk_cache -v`
Expected: FAIL (no `_TAGS_CACHE_FILE` attribute; no disk persistence).

- [ ] **Step 3: Add disk persistence to `_fetch_league_tags`**

In `src/market_scanner.py`, add after line 16 (after `GAMMA_BASE`):

```python
_TAGS_CACHE_FILE = Path("logs/sports_tags_cache.json")
```

Add `import json` and `from pathlib import Path` at the top if not present.

Then modify `_fetch_league_tags` to save on success and load from disk on failure:

```python
    def _fetch_league_tags(self) -> list[tuple[str, int]]:
        """Discover all league-specific tag_ids from Polymarket /sports endpoint.

        Daily H2H match markets live under league-specific tags (e.g. Turkish
        Super Lig = tag_id 102564), NOT under parent tags 1/64 which only cover
        season-long/futures markets. This method fetches the full list, caches
        it for 24h, and falls back to disk cache (then PARENT_TAGS) on failure.
        """
        import time
        global _league_tags_cache, _league_tags_ts
        if _league_tags_cache and (time.time() - _league_tags_ts) < 86400:
            return _league_tags_cache

        try:
            resp = requests.get(f"{GAMMA_BASE}/sports", timeout=15)
            resp.raise_for_status()
            sports = resp.json()
        except Exception as exc:
            logger.warning("/sports endpoint failed: %s — trying disk cache", exc)
            return self._load_tags_from_disk()

        seen_tags: set[int] = set()
        result: list[tuple[str, int]] = []
        for entry in sports:
            sport_code = entry.get("sport", "")
            for t in entry.get("tags", "").split(","):
                t = t.strip()
                if t.isdigit():
                    tid = int(t)
                    if tid not in seen_tags:
                        seen_tags.add(tid)
                        result.append((sport_code, tid))

        if result:
            _league_tags_cache = result
            _league_tags_ts = time.time()
            logger.info("Discovered %d league tags from /sports (%d entries)",
                        len(result), len(sports))
            self._save_tags_to_disk(result)
        else:
            logger.warning("No tags from /sports — trying disk cache")
            return self._load_tags_from_disk()
        return result

    @staticmethod
    def _save_tags_to_disk(tags: list[tuple[str, int]]) -> None:
        """Persist league tags to disk for crash/downtime recovery."""
        try:
            _TAGS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [[sport, tid] for sport, tid in tags]
            tmp = _TAGS_CACHE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            tmp.replace(_TAGS_CACHE_FILE)
        except Exception as e:
            logger.debug("Could not save tags cache: %s", e)

    @staticmethod
    def _load_tags_from_disk() -> list[tuple[str, int]]:
        """Load league tags from disk cache. Falls back to PARENT_TAGS."""
        try:
            if _TAGS_CACHE_FILE.exists():
                data = json.loads(_TAGS_CACHE_FILE.read_text(encoding="utf-8"))
                tags = [(entry[0], entry[1]) for entry in data]
                if tags:
                    logger.info("Loaded %d league tags from disk cache", len(tags))
                    return tags
        except Exception as e:
            logger.debug("Could not load tags cache: %s", e)
        logger.warning("No disk cache available — falling back to parent tags")
        return PARENT_TAGS
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_market_scanner.py -v`
Expected: ALL PASS (old + new).

- [ ] **Step 5: Commit**

```bash
git add src/market_scanner.py tests/test_market_scanner.py
git commit -m "fix(scanner): persist /sports tag cache to disk for downtime recovery"
```

---

### Task 6: ESPN League Mapping Expansion

**Files:**
- Modify: `src/sports_data.py:21-157`
- Modify: `src/sports_data.py:161-208` (series mapping)
- No separate test file (ESPN mappings are static data; verified by integration)

Adds missing European + South American soccer leagues and series mappings.

- [ ] **Step 1: Write failing tests**

Create `tests/test_espn_league_mapping.py`:

```python
"""Tests for ESPN league mapping coverage."""


def test_slug_prefix_swiss_super_league():
    from src.sports_data import _SPORT_LEAGUES
    assert "sui" in _SPORT_LEAGUES
    sport, league, _ = _SPORT_LEAGUES["sui"]
    assert sport == "soccer"
    assert league == "sui.1"


def test_slug_prefix_polish_ekstraklasa():
    from src.sports_data import _SPORT_LEAGUES
    assert "pol" in _SPORT_LEAGUES
    sport, league, _ = _SPORT_LEAGUES["pol"]
    assert sport == "soccer"


def test_slug_prefix_paraguayan():
    from src.sports_data import _SPORT_LEAGUES
    assert "par" in _SPORT_LEAGUES
    sport, league, _ = _SPORT_LEAGUES["par"]
    assert sport == "soccer"


def test_slug_prefix_uruguayan():
    from src.sports_data import _SPORT_LEAGUES
    assert "uru" in _SPORT_LEAGUES
    sport, league, _ = _SPORT_LEAGUES["uru"]
    assert sport == "soccer"


def test_series_swiss_super_league():
    from src.sports_data import _SERIES_TO_ESPN
    assert "swiss-super-league" in _SERIES_TO_ESPN
    sport, league = _SERIES_TO_ESPN["swiss-super-league"]
    assert sport == "soccer"


def test_series_ekstraklasa():
    from src.sports_data import _SERIES_TO_ESPN
    assert "ekstraklasa" in _SERIES_TO_ESPN
    sport, league = _SERIES_TO_ESPN["ekstraklasa"]
    assert sport == "soccer"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_espn_league_mapping.py -v`
Expected: FAIL (keys not in dicts).

- [ ] **Step 3: Add mappings to `_SPORT_LEAGUES`**

In `src/sports_data.py`, add inside `_SPORT_LEAGUES` dict (after the `# ── Soccer — Other European` section, around line 83):

```python
    "sui": ("soccer", "sui.1", "Swiss Super League"),
    "pol": ("soccer", "pol.1", "Ekstraklasa"),
    "fin": ("soccer", "fin.1", "Veikkausliiga"),
    "srb": ("soccer", "srb.1", "Serbian SuperLiga"),
    "bul": ("soccer", "bul.1", "First Professional League"),
    "cyp": ("soccer", "cyp.1", "Cypriot First Division"),
    "hun": ("soccer", "hun.1", "NB I"),
```

And in the `# ── Soccer — Americas` section (after the existing entries):

```python
    "par": ("soccer", "par.1", "Primera Paraguay"),
    "uru": ("soccer", "uru.1", "Primera Uruguay"),
    "ecu": ("soccer", "ecu.1", "LigaPro Ecuador"),
    "ven": ("soccer", "ven.1", "Primera Venezuela"),
```

- [ ] **Step 4: Add mappings to `_SERIES_TO_ESPN`**

In `src/sports_data.py`, add inside `_SERIES_TO_ESPN` dict (after the existing entries):

```python
    "swiss-super-league": ("soccer", "sui.1"),
    "ekstraklasa": ("soccer", "pol.1"),
    "veikkausliiga": ("soccer", "fin.1"),
    "serbian-superliga": ("soccer", "srb.1"),
    "primera-division-paraguay": ("soccer", "par.1"),
    "primera-division-uruguay": ("soccer", "uru.1"),
    "ligapro-ecuador": ("soccer", "ecu.1"),
    "hungarian-nb-i": ("soccer", "hun.1"),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_espn_league_mapping.py -v`
Expected: ALL PASS.

- [ ] **Step 6: Commit**

```bash
git add src/sports_data.py tests/test_espn_league_mapping.py
git commit -m "feat(espn): add Swiss, Polish, Paraguayan, Uruguayan + other league mappings"
```

---

## Post-Implementation Verification

After all 6 tasks are complete:

- [ ] **Full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: ALL PASS. Zero regressions.

- [ ] **Import sanity check**

Run: `python -c "from src.main import *; print('OK')"`
Expected: No import errors.

- [ ] **Final commit (if any stragglers)**

```bash
git status
```
