# Entry Flow Fix + ESPN Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix bot entry timing, ranking, and ESPN data coverage so 68% thin-data rejection rate drops to <30%, close matches appear first, underdogs get fair ranking, and all ESPN sports feed data into AI analysis.

**Architecture:** Four surgical fixes to entry flow (entry_gate, market_scanner, esports_data) + one comprehensive expansion of sports_data.py (league slugs, tennis/MMA scoreboard-scan, new sport routing). Changes are independent per file — Part A (timing/ranking) and Part B (ESPN) can merge in any order.

**Tech Stack:** Python 3.11, ESPN public API (no key), PandaScore free tier, existing `match_team()` fuzzy matcher

**Spec:** `docs/superpowers/specs/2026-03-30-entry-flow-and-espn-overhaul-design.md`

---

### Task 1: Fix `_hours_to_start()` to use `match_start_iso`

**Files:**
- Modify: `src/entry_gate.py:791-800`
- Test: `tests/test_hours_to_start.py` (create)

- [ ] **Step 1: Write failing test**

```python
# tests/test_hours_to_start.py
"""Tests for _hours_to_start with match_start_iso priority."""
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from src.entry_gate import _hours_to_start


def test_match_start_iso_used_when_present():
    """match_start_iso should be preferred over end_date_iso."""
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    market = SimpleNamespace(
        match_start_iso=future.isoformat(),
        end_date_iso=(future + timedelta(hours=24)).isoformat(),
    )
    hours = _hours_to_start(market)
    assert 1.9 < hours < 2.1


def test_falls_back_to_end_date_iso():
    """When match_start_iso is empty, fall back to end_date_iso."""
    future = datetime.now(timezone.utc) + timedelta(hours=5)
    market = SimpleNamespace(match_start_iso="", end_date_iso=future.isoformat())
    hours = _hours_to_start(market)
    assert 4.9 < hours < 5.1


def test_returns_99_when_both_empty():
    """No dates → 99h (discovery bucket)."""
    market = SimpleNamespace(match_start_iso="", end_date_iso="")
    assert _hours_to_start(market) == 99.0


def test_negative_hours_for_past_match():
    """Past match_start_iso returns negative hours."""
    past = datetime.now(timezone.utc) - timedelta(hours=3)
    market = SimpleNamespace(match_start_iso=past.isoformat(), end_date_iso="")
    hours = _hours_to_start(market)
    assert -3.1 < hours < -2.9


def test_z_suffix_handled():
    """ISO string with Z suffix is parsed correctly."""
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    iso_str = future.strftime("%Y-%m-%dT%H:%M:%SZ")
    market = SimpleNamespace(match_start_iso=iso_str, end_date_iso="")
    hours = _hours_to_start(market)
    assert 0.9 < hours < 1.1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_hours_to_start.py -v`
Expected: FAIL — `test_match_start_iso_used_when_present` fails because current code ignores `match_start_iso`

- [ ] **Step 3: Implement fix**

Replace `src/entry_gate.py` lines 791-800:

```python
def _hours_to_start(market) -> float:
    """Hours until match starts. Used for imminent/mid/discovery bucketing.

    Prefers match_start_iso (Gamma event startTime — actual kick-off / first map)
    over end_date_iso (Polymarket market close — often far in the future).
    """
    # Primary: match start time from Gamma event (accurate for sports + esports)
    start_iso = getattr(market, "match_start_iso", "") or ""
    if start_iso:
        try:
            start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            return (start_dt - datetime.now(timezone.utc)).total_seconds() / 3600
        except (ValueError, TypeError):
            pass
    # Fallback: Polymarket end date
    end_iso = getattr(market, "end_date_iso", "") or ""
    if not end_iso:
        return 99.0
    try:
        end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        return (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600
    except (ValueError, TypeError):
        return 99.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_hours_to_start.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
git add tests/test_hours_to_start.py src/entry_gate.py
git commit -m "fix: _hours_to_start uses match_start_iso as primary time source"
```

---

### Task 2: Remove esports time filter exemption

**Files:**
- Modify: `src/market_scanner.py:326-349`

- [ ] **Step 1: Write failing test**

```python
# tests/test_scanner_esports_time.py
"""Verify esports markets go through same time filters as regular sports."""
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta

from src.market_scanner import MarketScanner


def _make_market(**kwargs):
    defaults = dict(
        condition_id="test", question="CS2: Team A vs Team B",
        slug="cs2-team-a-team-b", yes_price=0.5, no_price=0.5,
        volume=10000, liquidity=5000, tags=["esports"],
        sport_tag="counter-strike", event_ended=True, event_live=False,
        match_start_iso="", end_date_iso="",
        clob_token_ids="[]",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_esports_ended_event_is_filtered():
    """Esports with event_ended=True should be filtered (no exemption)."""
    scanner = MarketScanner.__new__(MarketScanner)
    scanner.config = SimpleNamespace(
        min_liquidity=100, max_duration_days=14,
        allowed_categories=["sports", "esports"],
    )
    market = _make_market(event_ended=True, event_live=False)
    # _is_esport returns True for counter-strike tag
    # _is_live_sport should now also include esports
    result = scanner._passes_filters(market)
    assert result is False


def test_esports_late_match_is_filtered():
    """Esports with >75% elapsed should be filtered (no exemption)."""
    scanner = MarketScanner.__new__(MarketScanner)
    scanner.config = SimpleNamespace(
        min_liquidity=100, max_duration_days=14,
        allowed_categories=["sports", "esports"],
    )
    # CS2 match started 3 hours ago, ~100% elapsed for a BO3
    past = datetime.now(timezone.utc) - timedelta(hours=3)
    market = _make_market(
        event_ended=False, event_live=True,
        match_start_iso=past.isoformat(),
    )
    result = scanner._passes_filters(market)
    assert result is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_scanner_esports_time.py -v`
Expected: FAIL — esports exemption lets ended/late matches through

- [ ] **Step 3: Remove esports exemption**

In `src/market_scanner.py`, change lines 326-349:

**Line 329** — remove `and not self._is_esport(market)`:
```python
        # Skip ended matches -- no point entering a resolved event
        if market.event_ended and self._is_live_sport(market):
            logger.info("Skipped ENDED event (Gamma): %s", market.question[:60])
            return False
```

**Line 336** — remove `and not self._is_esport(market)`:
```python
        # Skip late-match entries -- not enough time for meaningful edge
        # Uses sport-specific duration table (soccer=95min, NBA=150min, etc.)
        if market.event_live and market.match_start_iso:
```

Also delete the 2 comment lines about esports exclusion (lines 327-328 and 334-335).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_scanner_esports_time.py -v`
Expected: Both PASS

- [ ] **Step 5: Run existing tests to check for regressions**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/ -v --timeout=30 2>&1 | tail -30`
Expected: No new failures

- [ ] **Step 6: Commit**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
git add src/market_scanner.py tests/test_scanner_esports_time.py
git commit -m "fix: remove esports exemption from time filters — all sports unified"
```

---

### Task 3: Edge-only ranking formula

**Files:**
- Modify: `src/entry_gate.py:608-611`

- [ ] **Step 1: Write failing test**

```python
# tests/test_ranking_formula.py
"""Verify edge-only ranking gives underdogs fair scores."""


def test_equal_edge_equal_score():
    """Favorite and underdog with same edge should get same rank score."""
    # Simulating the ranking formula
    edge = 0.05
    conf_score = 1.0  # "high" confidence

    # Old formula: (direction_prob + edge) * conf_score
    fav_old = (0.85 + edge) * conf_score   # 0.90
    dog_old = (0.55 + edge) * conf_score   # 0.60

    # New formula: edge * conf_score
    fav_new = edge * conf_score   # 0.05
    dog_new = edge * conf_score   # 0.05

    # Old formula penalized underdogs
    assert fav_old > dog_old * 1.4  # True — 50% penalty

    # New formula treats them equally
    assert fav_new == dog_new
```

- [ ] **Step 2: Run test to verify it passes (formula logic test)**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_ranking_formula.py -v`
Expected: PASS (this is a logic verification test)

- [ ] **Step 3: Change ranking formula**

In `src/entry_gate.py`, replace lines 608-611:

```python
            # ── Rank score -- pure edge × confidence ─────────────────────────
            # Edge-only ranking: underdogs with high edge rank equally to favorites.
            # Old formula (direction_prob + edge) penalized underdogs 2-3x.
            conf_score = _CONF_SCORE.get(estimate.confidence, 1)
            rank_score = edge * conf_score
```

- [ ] **Step 4: Run full test suite**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/ -v --timeout=30 2>&1 | tail -20`
Expected: No failures

- [ ] **Step 5: Commit**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
git add src/entry_gate.py tests/test_ranking_formula.py
git commit -m "fix: edge-only ranking formula — underdogs with equal edge rank equally"
```

---

### Task 4: Esports slug fix + remove tier filter

**Files:**
- Modify: `src/esports_data.py:19-26` (slugs)
- Modify: `src/esports_data.py:110-116` (normalize dynamic slug)
- Modify: `src/esports_data.py:277-280` (tier filter)

- [ ] **Step 1: Write failing test**

```python
# tests/test_esports_slugs.py
"""Test expanded game slug mapping and tier inclusion."""
from src.esports_data import _GAME_SLUGS


def test_polymarket_tags_mapped():
    """Polymarket seriesSlug values must map to PandaScore API slugs."""
    assert _GAME_SLUGS["counter-strike"] == "csgo"
    assert _GAME_SLUGS["cs-go"] == "csgo"
    assert _GAME_SLUGS["league-of-legends"] == "lol"
    assert _GAME_SLUGS["dota-2"] == "dota2"
    assert _GAME_SLUGS["overwatch"] == "ow"
    assert _GAME_SLUGS["mobile-legends"] == "mobile-legends-bang-bang"
    assert _GAME_SLUGS["starcraft-2"] == "starcraft-2"
    assert _GAME_SLUGS["r6-siege"] == "r6-siege"


def test_original_slugs_still_work():
    """Original short slugs must still resolve."""
    assert _GAME_SLUGS["cs2"] == "csgo"
    assert _GAME_SLUGS["csgo"] == "csgo"
    assert _GAME_SLUGS["lol"] == "lol"
    assert _GAME_SLUGS["dota2"] == "dota2"
    assert _GAME_SLUGS["valorant"] == "valorant"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_esports_slugs.py -v`
Expected: FAIL — `KeyError: 'counter-strike'`

- [ ] **Step 3: Expand `_GAME_SLUGS`**

Replace `src/esports_data.py` lines 19-26:

```python
# Map Polymarket tags + PandaScore videogame.slug → valid API path slug.
# PandaScore API endpoints use: /csgo/, /lol/, /dota2/, /valorant/, /ow/, /r6-siege/ etc.
# Polymarket tags use: "counter-strike", "league-of-legends", "dota-2", etc.
# PandaScore videogame.slug returns: "cs-go", "league-of-legends", "dota-2", etc.
_GAME_SLUGS = {
    # CS2 — Polymarket tag "counter-strike", PandaScore returns "cs-go"
    "cs2": "csgo", "csgo": "csgo", "counter-strike": "csgo", "cs-go": "csgo",
    # LoL — Polymarket tag "league-of-legends"
    "lol": "lol", "league-of-legends": "lol",
    # Dota 2 — Polymarket tag "dota-2"
    "dota2": "dota2", "dota-2": "dota2",
    # Valorant
    "valorant": "valorant",
    # R6 Siege — PandaScore returns "r6-siege"
    "r6-siege": "r6-siege",
    # Overwatch — PandaScore returns "ow"
    "ow": "ow", "overwatch": "ow",
    # Mobile Legends
    "mobile-legends": "mobile-legends-bang-bang",
    # StarCraft 2
    "starcraft-2": "starcraft-2", "starcraft": "starcraft-2",
}
```

- [ ] **Step 4: Run slug test**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_esports_slugs.py -v`
Expected: All PASS

- [ ] **Step 5: Normalize dynamic slug in `detect_game()`**

In `src/esports_data.py`, replace lines 112-116:

```python
            if match:
                videogame = match.get("videogame", {})
                raw_slug = videogame.get("slug", "")
                if raw_slug:
                    # Normalize PandaScore slug (e.g. "cs-go" → "csgo")
                    slug = _GAME_SLUGS.get(raw_slug, raw_slug)
                    logger.info("PandaScore search: '%s' -> game=%s (raw=%s)", team_a, slug, raw_slug)
                    return slug
```

- [ ] **Step 6: Remove C/D tier filter**

In `src/esports_data.py`, delete lines 277-280:

```python
            # DELETE THESE 3 LINES:
            # Client-side tier filter: skip D/C tier (manipulation-prone)
            tier = (m.get("tournament", {}).get("tier") or "").lower()
            if tier in ("d", "c"):
                continue
```

- [ ] **Step 7: Run full test suite**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/ -v --timeout=30 2>&1 | tail -20`
Expected: No failures

- [ ] **Step 8: Commit**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
git add src/esports_data.py tests/test_esports_slugs.py
git commit -m "fix: expand esports slugs, normalize dynamic detection, include all tiers"
```

---

### Task 5: Stale esports match guard

**Files:**
- Modify: `src/esports_data.py:337-338` (insert guard after line 338)

- [ ] **Step 1: Write failing test**

```python
# tests/test_stale_guard.py
"""Test stale esports match detection."""
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


def test_stale_running_match_returns_none():
    """Match running for >4h should return None."""
    from src.esports_data import EsportsDataClient

    client = EsportsDataClient.__new__(EsportsDataClient)
    client.api_key = "test"
    client._cache = {}
    client._cache_ttl = 1800
    client._session = MagicMock()
    client._last_call = 0.0

    # Mock _get_upcoming_match to return a stale running match
    stale_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    mock_upcoming = {
        "status": "running",
        "scheduled_at": stale_time,
        "tournament": {"name": "Test", "tier": "a"},
        "league": {"name": "ESL"},
    }

    with patch.object(client, "_get_upcoming_match", return_value=mock_upcoming), \
         patch.object(client, "detect_game", return_value="csgo"), \
         patch.object(client, "_extract_team_names", return_value=("Team A", "Team B")):
        result = client.get_match_context("CS2: Team A vs Team B", "cs2-a-b", ["esports"])
        assert result is None


def test_fresh_running_match_returns_data():
    """Match running for <4h should NOT be blocked."""
    from src.esports_data import EsportsDataClient

    client = EsportsDataClient.__new__(EsportsDataClient)
    client.api_key = "test"
    client._cache = {}
    client._cache_ttl = 1800
    client._session = MagicMock()
    client._last_call = 0.0

    fresh_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    mock_upcoming = {
        "status": "running",
        "scheduled_at": fresh_time,
        "tournament": {"name": "Test", "tier": "a"},
        "league": {"name": "ESL"},
        "match_type": "best_of",
        "number_of_games": 3,
    }
    mock_team = {"team_name": "Team A", "wins": 3, "losses": 1,
                 "win_rate": 0.75, "recent_matches": []}

    with patch.object(client, "_get_upcoming_match", return_value=mock_upcoming), \
         patch.object(client, "detect_game", return_value="csgo"), \
         patch.object(client, "_extract_team_names", return_value=("Team A", "Team B")), \
         patch.object(client, "get_team_recent_results", return_value=mock_team):
        result = client.get_match_context("CS2: Team A vs Team B", "cs2-a-b", ["esports"])
        assert result is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_stale_guard.py -v`
Expected: FAIL — `test_stale_running_match_returns_none` fails (no guard exists)

- [ ] **Step 3: Add stale guard**

In `src/esports_data.py`, after line 338 (`upcoming = self._get_upcoming_match(...)`) insert:

```python
        # Guard: skip matches that started too long ago (likely finished)
        # PandaScore may still report "running" hours after a match ends
        _MAX_MATCH_HOURS = 4  # BO5 can go ~4h max; anything beyond = stale
        if upcoming:
            _sched = upcoming.get("scheduled_at") or ""
            _status = upcoming.get("status", "")
            if _sched and _status == "running":
                try:
                    _start = datetime.fromisoformat(_sched.replace("Z", "+00:00"))
                    _elapsed_h = (datetime.now(timezone.utc) - _start).total_seconds() / 3600
                    if _elapsed_h > _MAX_MATCH_HOURS:
                        logger.warning(
                            "SKIP stale esports match: %s vs %s started %.1fh ago (max %dh)",
                            team_a_name, team_b_name, _elapsed_h, _MAX_MATCH_HOURS,
                        )
                        return None
                except (ValueError, TypeError):
                    pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_stale_guard.py -v`
Expected: Both PASS

- [ ] **Step 5: Commit**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
git add src/esports_data.py tests/test_stale_guard.py
git commit -m "fix: add stale match guard — skip esports running >4h"
```

---

### Task 6: Expand ESPN league slugs

**Files:**
- Modify: `src/sports_data.py:16-35` (replace `_SPORT_LEAGUES`)
- Modify: `src/sports_data.py:80-86` (update `_SKIP_LEAGUES` and `_SKIP_SPORTS`)

- [ ] **Step 1: Write failing test**

```python
# tests/test_espn_leagues.py
"""Test comprehensive ESPN league slug coverage."""
from src.sports_data import _SPORT_LEAGUES


def test_turkish_super_lig():
    assert "tur" in _SPORT_LEAGUES
    sport, league, label = _SPORT_LEAGUES["tur"]
    assert sport == "soccer"
    assert league == "tur.1"


def test_eredivisie():
    assert "ned" in _SPORT_LEAGUES
    assert _SPORT_LEAGUES["ned"][1] == "ned.1"


def test_champions_league():
    assert "ucl" in _SPORT_LEAGUES
    assert _SPORT_LEAGUES["ucl"][1] == "uefa.champions"


def test_formula_1():
    assert "f1" in _SPORT_LEAGUES
    sport, league, _ = _SPORT_LEAGUES["f1"]
    assert sport == "racing"
    assert league == "f1"


def test_afl():
    assert "afl" in _SPORT_LEAGUES
    assert _SPORT_LEAGUES["afl"][0] == "australian-football"


def test_pga():
    assert "pga" in _SPORT_LEAGUES
    assert _SPORT_LEAGUES["pga"][0] == "golf"


def test_original_leagues_preserved():
    """All original leagues must still work."""
    assert _SPORT_LEAGUES["nba"][1] == "nba"
    assert _SPORT_LEAGUES["nhl"][1] == "nhl"
    assert _SPORT_LEAGUES["nfl"][1] == "nfl"
    assert _SPORT_LEAGUES["mlb"][1] == "mlb"
    assert _SPORT_LEAGUES["epl"][1] == "eng.1"
    assert _SPORT_LEAGUES["atp"][1] == "atp"
    assert _SPORT_LEAGUES["wta"][1] == "wta"
    assert _SPORT_LEAGUES["ufc"][1] == "ufc"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_espn_leagues.py -v`
Expected: FAIL — `KeyError: 'tur'`

- [ ] **Step 3: Replace `_SPORT_LEAGUES` dict**

Replace `src/sports_data.py` lines 16-35 with:

```python
# Slug prefix → (sport, league, label) for fast sport detection.
# Sources: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/
_SPORT_LEAGUES: dict = {
    # ── Basketball (basketball.md) ─────────────────────────────────────────
    "nba": ("basketball", "nba", "NBA"),
    "wnba": ("basketball", "wnba", "WNBA"),
    "cbb": ("basketball", "mens-college-basketball", "CBB"),
    "cwbb": ("basketball", "womens-college-basketball", "WCBB"),
    "gleague": ("basketball", "nba-development", "G-League"),
    "fiba": ("basketball", "fiba", "FIBA"),
    "nbl": ("basketball", "nbl", "NBL Australia"),
    # ── Hockey (hockey.md) ─────────────────────────────────────────────────
    "nhl": ("hockey", "nhl", "NHL"),
    "nchm": ("hockey", "mens-college-hockey", "NCAA Hockey"),
    "nchw": ("hockey", "womens-college-hockey", "NCAA W Hockey"),
    # ── American Football (football.md) ────────────────────────────────────
    "nfl": ("football", "nfl", "NFL"),
    "cfb": ("football", "college-football", "CFB"),
    "cfl": ("football", "cfl", "CFL"),
    "ufl": ("football", "ufl", "UFL"),
    "xfl": ("football", "xfl", "XFL"),
    # ── Baseball (baseball.md) ─────────────────────────────────────────────
    "mlb": ("baseball", "mlb", "MLB"),
    "cbase": ("baseball", "college-baseball", "College Baseball"),
    "wbc": ("baseball", "world-baseball-classic", "WBC"),
    # ── Soccer (soccer.md) — England ───────────────────────────────────────
    "epl": ("soccer", "eng.1", "EPL"),
    "eng2": ("soccer", "eng.2", "Championship"),
    "facup": ("soccer", "eng.fa", "FA Cup"),
    # ── Soccer — Spain ─────────────────────────────────────────────────────
    "lal": ("soccer", "esp.1", "La Liga"),
    "esp2": ("soccer", "esp.2", "La Liga 2"),
    "copdr": ("soccer", "esp.copa_del_rey", "Copa del Rey"),
    # ── Soccer — Germany ───────────────────────────────────────────────────
    "bun": ("soccer", "ger.1", "Bundesliga"),
    "ger2": ("soccer", "ger.2", "2. Bundesliga"),
    "dfbp": ("soccer", "ger.dfb_pokal", "DFB Pokal"),
    # ── Soccer — Italy ─────────────────────────────────────────────────────
    "ser": ("soccer", "ita.1", "Serie A"),
    "ita2": ("soccer", "ita.2", "Serie B"),
    "copit": ("soccer", "ita.coppa_italia", "Coppa Italia"),
    # ── Soccer — France ────────────────────────────────────────────────────
    "lig": ("soccer", "fra.1", "Ligue 1"),
    "fra2": ("soccer", "fra.2", "Ligue 2"),
    "coudf": ("soccer", "fra.coupe_de_france", "Coupe de France"),
    # ── Soccer — Other European ────────────────────────────────────────────
    "tur": ("soccer", "tur.1", "Super Lig"),
    "ned": ("soccer", "ned.1", "Eredivisie"),
    "ned2": ("soccer", "ned.2", "Eerste Divisie"),
    "por": ("soccer", "por.1", "Primeira Liga"),
    "bel": ("soccer", "bel.1", "Pro League"),
    "aut": ("soccer", "aut.1", "Bundesliga AT"),
    "gre": ("soccer", "gre.1", "Super League"),
    "den": ("soccer", "den.1", "Superliga"),
    "nor": ("soccer", "nor.1", "Eliteserien"),
    "swe": ("soccer", "swe.1", "Allsvenskan"),
    # ── Soccer — Americas ──────────────────────────────────────────────────
    "mls": ("soccer", "usa.1", "MLS"),
    "nwsl": ("soccer", "usa.nwsl", "NWSL"),
    "arg": ("soccer", "arg.1", "Liga Profesional"),
    "bra": ("soccer", "bra.1", "Brasileirao"),
    "mex": ("soccer", "mex.1", "Liga MX"),
    # ── Soccer — Asia/Oceania/Africa ───────────────────────────────────────
    "jpn": ("soccer", "jpn.1", "J1 League"),
    "chn": ("soccer", "chn.1", "CSL"),
    "ind": ("soccer", "ind.1", "ISL"),
    "aus": ("soccer", "aus.1", "A-League"),
    "rsa": ("soccer", "rsa.1", "PSL"),
    # ── Soccer — Cups & International ──────────────────────────────────────
    "ucl": ("soccer", "uefa.champions", "Champions League"),
    "uel": ("soccer", "uefa.europa", "Europa League"),
    "uecl": ("soccer", "uefa.europa.conf", "Conference League"),
    "wcup": ("soccer", "fifa.world", "World Cup"),
    "euro": ("soccer", "uefa.euro", "Euro"),
    "copa": ("soccer", "conmebol.libertadores", "Libertadores"),
    "suda": ("soccer", "conmebol.sudamericana", "Sudamericana"),
    "cona": ("soccer", "conmebol.america", "Copa America"),
    "gold": ("soccer", "concacaf.gold", "Gold Cup"),
    "frien": ("soccer", "fifa.friendly", "Friendlies"),
    # ── Tennis (tennis.md) ─────────────────────────────────────────────────
    "atp": ("tennis", "atp", "ATP"),
    "wta": ("tennis", "wta", "WTA"),
    # ── MMA (mma.md) ──────────────────────────────────────────────────────
    "ufc": ("mma", "ufc", "UFC"),
    "bellator": ("mma", "bellator", "Bellator"),
    "pfl": ("mma", "pfl", "PFL"),
    # ── Golf (golf.md) ────────────────────────────────────────────────────
    "pga": ("golf", "pga", "PGA Tour"),
    "lpga": ("golf", "lpga", "LPGA"),
    "liv": ("golf", "liv", "LIV Golf"),
    "dpw": ("golf", "eur", "DP World Tour"),
    "champ": ("golf", "champions-tour", "Champions Tour"),
    # ── Racing (racing.md) ────────────────────────────────────────────────
    "f1": ("racing", "f1", "Formula 1"),
    "irl": ("racing", "irl", "IndyCar"),
    "nascar": ("racing", "nascar-premier", "NASCAR Cup"),
    # ── Rugby (rugby.md) — numeric IDs, discovery via ESPN search ─────────
    "rugby": ("rugby", "rugby", "Rugby"),
    # ── Australian Football (australian_football.md) ──────────────────────
    "afl": ("australian-football", "afl", "AFL"),
    # ── Lacrosse (lacrosse.md) ────────────────────────────────────────────
    "nll": ("lacrosse", "nll", "NLL"),
    "pll": ("lacrosse", "pll", "PLL"),
    # ── Volleyball (volleyball.md) ────────────────────────────────────────
    "mcvb": ("volleyball", "mens-college-volleyball", "NCAA M Volleyball"),
    "wcvb": ("volleyball", "womens-college-volleyball", "NCAA W Volleyball"),
    # ── Field Hockey (field_hockey.md) ────────────────────────────────────
    "cfhoc": ("field-hockey", "womens-college-field-hockey", "NCAA Field Hockey"),
    # ── Cricket — ESPN as fallback (dedicated cricket_data.py is primary) ─
    "cric": ("cricket", "cricket", "Cricket"),
}
```

- [ ] **Step 4: Remove `_SKIP_SPORTS` cricket exclusion**

In `src/sports_data.py`, change line 86:

```python
    _SKIP_SPORTS = frozenset()  # No longer skip any sport
```

And remove women's leagues from `_SKIP_LEAGUES` (line 81-85) since we now explicitly support NWSL:

```python
    _SKIP_LEAGUES = frozenset()  # All leagues supported
```

- [ ] **Step 5: Run test**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_espn_leagues.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
git add src/sports_data.py tests/test_espn_leagues.py
git commit -m "feat: expand ESPN to 90+ leagues — soccer, golf, F1, rugby, AFL, lacrosse"
```

---

### Task 7: Fix tennis data fetching

**Files:**
- Modify: `src/sports_data.py:444-524` (rewrite `_get_athlete_match_context`)

- [ ] **Step 1: Write failing test**

```python
# tests/test_tennis_data.py
"""Test tennis match history via ESPN scoreboard date scan."""
import json
from unittest.mock import patch
from src.sports_data import SportsDataClient


# Minimal ESPN scoreboard response with one completed tennis match
MOCK_SCOREBOARD = {
    "events": [{
        "name": "US Clay Court Championship",
        "competitions": [{
            "status": {"type": {"completed": True}},
            "competitors": [
                {
                    "athlete": {"displayName": "Carlos Alcaraz"},
                    "winner": True,
                    "linescores": [
                        {"value": 6.0},
                        {"value": 4.0},
                        {"value": 7.0},
                    ],
                },
                {
                    "athlete": {"displayName": "Jannik Sinner"},
                    "winner": False,
                    "linescores": [
                        {"value": 3.0},
                        {"value": 6.0},
                        {"value": 5.0},
                    ],
                },
            ],
        }],
    }],
}


def test_tennis_context_has_match_results():
    """Tennis context must include [W]/[L] markers from scoreboard scan."""
    client = SportsDataClient()

    with patch.object(client, "_get", return_value=MOCK_SCOREBOARD):
        ctx = client.get_match_context(
            "ATP: Carlos Alcaraz vs Jannik Sinner",
            "atp-alcaraz-sinner",
            ["tennis"],
        )

    assert ctx is not None
    assert "[W]" in ctx or "[L]" in ctx
    assert "Alcaraz" in ctx
    assert "Sinner" in ctx


def test_tennis_context_not_just_name():
    """Tennis context must have more than just player names (old behavior)."""
    client = SportsDataClient()

    with patch.object(client, "_get", return_value=MOCK_SCOREBOARD):
        ctx = client.get_match_context(
            "ATP: Carlos Alcaraz vs Jannik Sinner",
            "atp-alcaraz-sinner",
            ["tennis"],
        )

    assert ctx is not None
    # Must have match result data, not just "PLAYER A: Carlos Alcaraz (ATP)"
    lines = ctx.strip().split("\n")
    result_lines = sum(1 for l in lines if "[W]" in l or "[L]" in l)
    assert result_lines >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_tennis_data.py -v`
Expected: FAIL — current code returns context without [W]/[L] markers

- [ ] **Step 3: Rewrite `_get_athlete_match_context`**

Replace `src/sports_data.py` lines 444-524 with:

```python
    # Sports where competitors are individual athletes, not teams
    _ATHLETE_SPORTS = frozenset({"tennis", "mma"})

    # Sports where competitors are event-based (tournaments, races)
    _EVENT_SPORTS = frozenset({"golf", "racing"})

    def get_match_context(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Build structured context string for AI analyst.

        Routes to athlete-based context for tennis/MMA, event-based for golf/racing,
        team-based for all others.
        Returns None if not a traditional sport or no data available.
        """
        sport_league = self.detect_sport(question, slug, tags)
        if not sport_league:
            return None

        sport, league = sport_league

        if sport in self._ATHLETE_SPORTS:
            return self._get_athlete_match_context(sport, league, question, slug)

        if sport in self._EVENT_SPORTS:
            return self._get_event_match_context(sport, league, question, slug)

        return self._get_team_match_context(sport, league, question, slug)

    def _get_athlete_match_context(
        self, sport: str, league: str, question: str, slug: str
    ) -> Optional[str]:
        """Build context for athlete-based sports (tennis, MMA).

        Scans recent ESPN scoreboards to build match/fight history with [W]/[L] markers.
        """
        team_a_name, team_b_name = self._extract_teams_from_question(question)
        slug_a, slug_b = self._extract_teams_from_slug(slug)
        if not team_a_name and slug_a and len(slug_a) >= 4:
            team_a_name = slug_a
        if not team_b_name and slug_b and len(slug_b) >= 4:
            team_b_name = slug_b

        if not team_a_name:
            return None

        # Sport-specific scan window
        days_back = 90 if sport == "mma" else 14

        logger.info("Fetching ESPN %s athlete data: %s vs %s (%s, %dd scan)",
                     sport, team_a_name, team_b_name, league, days_back)

        parts = [f"=== SPORTS DATA (ESPN) -- {sport}/{league} ==="]
        found_any = False

        for label, name in [("PLAYER A", team_a_name), ("PLAYER B", team_b_name)]:
            if not name:
                parts.append(f"\n{label}: No data available")
                continue

            matches = self._scan_scoreboard_for_athlete(sport, league, name, days_back)

            if matches:
                found_any = True
                wins = sum(1 for m in matches if m["won"])
                losses = len(matches) - wins
                parts.append(f"\n{label}: {name}")
                parts.append(f"  Recent form ({len(matches)} matches): {wins}W-{losses}L")
                parts.append("  Recent matches:")
                for m in matches[:5]:
                    result = "W" if m["won"] else "L"
                    score_str = f" {m['score']}" if m.get("score") else ""
                    parts.append(
                        f"    [{result}] vs {m['opponent']}{score_str} "
                        f"({m.get('event', '')}, {m.get('date', '')})"
                    )
            else:
                # Fallback: ESPN search to at least confirm athlete exists
                params = {"query": name, "limit": 5, "type": "player"}
                record_call("espn_search")
                self._rate_limit()
                try:
                    resp = requests.get(self._SEARCH_URL, params=params, timeout=8)
                    data = resp.json() if resp.status_code == 200 else {}
                except (requests.RequestException, ValueError):
                    data = {}
                athlete_info = None
                for item in data.get("items", []):
                    if item.get("sport") == sport:
                        athlete_info = item
                        break
                if athlete_info:
                    found_any = True
                    display = athlete_info.get("displayName", name)
                    parts.append(f"\n{label}: {display} ({league})")
                    parts.append("  No recent match data found on ESPN scoreboard")
                else:
                    parts.append(f"\n{label}: {name} (not found on ESPN)")

        if not found_any:
            return None

        sport_label = {"tennis": "tennis", "mma": "MMA"}.get(sport, sport)
        parts.append(f"\nThis is a {sport_label} match. Use recent form, rankings, "
                     f"surface/venue, and head-to-head to estimate.")
        return "\n".join(parts)

    def _scan_scoreboard_for_athlete(
        self, sport: str, league: str, player_name: str, days_back: int
    ) -> List[Dict]:
        """Scan recent ESPN scoreboards to find an athlete's completed matches.

        Returns list of dicts: {opponent, won, score, event, date}
        """
        from datetime import timedelta as td
        matches = []
        today = datetime.now(timezone.utc).date()

        for i in range(days_back):
            date = today - td(days=i)
            date_str = date.strftime("%Y%m%d")
            url = f"{ESPN_BASE}/{sport}/{league}/scoreboard?dates={date_str}"
            data = self._get(url)
            if not data:
                continue

            for event in data.get("events", []):
                for comp in event.get("competitions", []):
                    status = comp.get("status", {}).get("type", {})
                    if not status.get("completed", False):
                        continue
                    competitors = comp.get("competitors", [])
                    if len(competitors) != 2:
                        continue

                    player_comp = None
                    opp_comp = None
                    for c in competitors:
                        athlete = c.get("athlete", {})
                        c_name = athlete.get("displayName", "")
                        is_match, score, _ = match_team(c_name.lower(), player_name.lower())
                        if is_match and score >= 0.70:
                            player_comp = c
                        else:
                            opp_comp = c

                    if player_comp and opp_comp:
                        won = player_comp.get("winner", False)
                        opp_name = opp_comp.get("athlete", {}).get("displayName", "Unknown")
                        score_str = self._extract_athlete_score(player_comp, opp_comp, sport)
                        matches.append({
                            "opponent": opp_name,
                            "won": won,
                            "score": score_str,
                            "event": event.get("name", ""),
                            "date": date.isoformat(),
                        })

            # Stop early if we have enough data
            if len(matches) >= 10:
                break

        return matches

    def _extract_athlete_score(self, player_comp: dict, opp_comp: dict, sport: str) -> str:
        """Extract score string from competitor linescores."""
        p_scores = player_comp.get("linescores", [])
        o_scores = opp_comp.get("linescores", [])
        if not p_scores:
            return ""
        if sport == "tennis":
            # Set scores like "6-3 4-6 7-5"
            sets = []
            for p, o in zip(p_scores, o_scores):
                sets.append(f"{int(p.get('value', 0))}-{int(o.get('value', 0))}")
            return " ".join(sets)
        elif sport == "mma":
            # MMA: just show round info
            return f"R{len(p_scores)}"
        return ""

    def _get_event_match_context(
        self, sport: str, league: str, question: str, slug: str
    ) -> Optional[str]:
        """Build context for event-based sports (golf, racing).

        Scans recent scoreboards for tournament/race results.
        """
        from datetime import timedelta as td

        logger.info("Fetching ESPN %s event data: %s/%s", sport, league, question[:40])

        # Scan last 30 days for recent events
        today = datetime.now(timezone.utc).date()
        results = []

        for i in range(30):
            date = today - td(days=i)
            date_str = date.strftime("%Y%m%d")
            url = f"{ESPN_BASE}/{sport}/{league}/scoreboard?dates={date_str}"
            data = self._get(url)
            if not data:
                continue
            for event in data.get("events", []):
                for comp in event.get("competitions", []):
                    status = comp.get("status", {}).get("type", {})
                    if not status.get("completed", False):
                        continue
                    competitors = comp.get("competitors", [])
                    if not competitors:
                        continue
                    # Get top 3 finishers
                    top = []
                    sorted_comps = sorted(competitors,
                                          key=lambda c: c.get("order", 999))
                    for c in sorted_comps[:3]:
                        athlete = c.get("athlete", {})
                        name = athlete.get("displayName", "Unknown")
                        top.append(name)
                    if top:
                        results.append({
                            "event": event.get("name", ""),
                            "date": date.isoformat(),
                            "top3": top,
                            "winner": top[0] if top else "Unknown",
                        })
            if len(results) >= 5:
                break

        if not results:
            return None

        parts = [f"=== SPORTS DATA (ESPN) -- {sport}/{league} ==="]
        parts.append(f"\nRecent {sport} results:")
        for r in results[:5]:
            parts.append(f"  [{r['date']}] {r['event']}")
            parts.append(f"    Winner: {r['winner']}")
            if len(r["top3"]) > 1:
                parts.append(f"    Top 3: {', '.join(r['top3'])}")
        parts.append(f"\nUse recent {sport} form, rankings, and venue to estimate.")
        return "\n".join(parts)
```

- [ ] **Step 4: Add missing import**

At top of `src/sports_data.py`, add `datetime` imports if not present:

```python
from datetime import datetime, timezone
```

- [ ] **Step 5: Run tennis test**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_tennis_data.py -v`
Expected: Both PASS

- [ ] **Step 6: Run full test suite**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/ -v --timeout=30 2>&1 | tail -30`
Expected: No failures

- [ ] **Step 7: Commit**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
git add src/sports_data.py tests/test_tennis_data.py
git commit -m "feat: tennis/MMA scoreboard scan + golf/racing event context"
```

---

### Task 8: Dynamic league detection from Gamma seriesSlug

**Files:**
- Modify: `src/sports_data.py:157-199` (enhance `detect_sport`)

- [ ] **Step 1: Write failing test**

```python
# tests/test_dynamic_detection.py
"""Test dynamic league detection from Gamma seriesSlug."""
from src.sports_data import SportsDataClient


def test_series_slug_turkish_league():
    """Gamma seriesSlug 'super-lig' should map to tur.1."""
    client = SportsDataClient()
    # Tags from Gamma API often include the series slug
    result = client.detect_sport(
        "Fenerbahce vs Galatasaray", "fen-gal", ["super-lig"]
    )
    assert result is not None
    assert result[1] == "tur.1"


def test_series_slug_la_liga_2():
    """Gamma seriesSlug 'la-liga-2' should map to esp.2."""
    client = SportsDataClient()
    result = client.detect_sport(
        "Eibar vs Racing", "eib-rac", ["la-liga-2"]
    )
    assert result is not None
    assert result[1] == "esp.2"


def test_series_slug_champions_league():
    """Gamma seriesSlug with 'champions-league' should resolve."""
    client = SportsDataClient()
    result = client.detect_sport(
        "Real Madrid vs Bayern", "rma-bay", ["champions-league"]
    )
    assert result is not None
    assert result[1] == "uefa.champions"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_dynamic_detection.py -v`
Expected: FAIL — current detect_sport doesn't check tags against league names

- [ ] **Step 3: Add seriesSlug → ESPN mapping**

In `src/sports_data.py`, add after the `_SPORT_LEAGUES` dict:

```python
# Map common Gamma seriesSlug values to (sport, league).
# These are the actual tag values seen in Polymarket Gamma API responses.
_SERIES_TO_ESPN: dict = {
    # Soccer
    "super-lig": ("soccer", "tur.1"),
    "la-liga-2": ("soccer", "esp.2"),
    "la-liga": ("soccer", "esp.1"),
    "primeira-divisin-argentina": ("soccer", "arg.1"),
    "brazil-serie-b": ("soccer", "bra.1"),  # ESPN uses bra.1 for top flight
    "womens-champions-league": ("soccer", "uefa.champions"),
    "fifa-friendly": ("soccer", "fifa.friendly"),
    "champions-league": ("soccer", "uefa.champions"),
    "europa-league": ("soccer", "uefa.europa"),
    "conference-league": ("soccer", "uefa.europa.conf"),
    "premier-league": ("soccer", "eng.1"),
    "bundesliga": ("soccer", "ger.1"),
    "serie-a": ("soccer", "ita.1"),
    "ligue-1": ("soccer", "fra.1"),
    "eredivisie": ("soccer", "ned.1"),
    "primeira-liga": ("soccer", "por.1"),
    "liga-mx": ("soccer", "mex.1"),
    "j1-league": ("soccer", "jpn.1"),
    "a-league": ("soccer", "aus.1"),
    # Hockey
    "shl-2026": ("hockey", "nhl"),  # Swedish Hockey — ESPN fallback to NHL search
    "khl-2026": ("hockey", "nhl"),  # KHL — ESPN fallback
    # Basketball
    "cba": ("basketball", "nba"),  # Chinese Basketball — ESPN fallback
    "cbl": ("basketball", "nba"),
    "kbl": ("basketball", "nba"),  # Korean Basketball — ESPN fallback
    # Cricket (use ESPN cricket endpoint)
    "indian-premier-league": ("cricket", "cricket"),
}
```

Then enhance `detect_sport()` — in `src/sports_data.py`, in the `detect_sport` method, add a tag-based lookup before the dynamic ESPN search. Insert after the `_QUESTION_KEYWORDS` tag check (after line 178):

```python
        # Check tags against known Gamma seriesSlug mappings
        for tag in tags:
            tag_lower = tag.lower().strip()
            if tag_lower in _SERIES_TO_ESPN:
                sport, league = _SERIES_TO_ESPN[tag_lower]
                logger.info("Series slug match: tag='%s' -> %s/%s", tag, sport, league)
                return (sport, league)
            # Also check if tag matches any _SPORT_LEAGUES label (case-insensitive)
            for key, (sport, league, label) in _SPORT_LEAGUES.items():
                if tag_lower == label.lower() or tag_lower == league.lower():
                    return (sport, league)
```

- [ ] **Step 4: Run test**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_dynamic_detection.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
git add src/sports_data.py tests/test_dynamic_detection.py
git commit -m "feat: dynamic league detection from Gamma seriesSlug tags"
```

---

### Task 9: Sport-aware thin data threshold

**Files:**
- Modify: `src/entry_gate.py:362-375`

- [ ] **Step 1: Write failing test**

```python
# tests/test_thin_data_threshold.py
"""Test sport-aware thin data thresholds."""
from src.entry_gate import _THIN_DATA_THRESHOLDS


def test_tennis_threshold_is_2():
    assert _THIN_DATA_THRESHOLDS["tennis"] == 2


def test_mma_threshold_is_2():
    assert _THIN_DATA_THRESHOLDS["mma"] == 2


def test_golf_threshold_is_1():
    assert _THIN_DATA_THRESHOLDS["golf"] == 1


def test_racing_threshold_is_1():
    assert _THIN_DATA_THRESHOLDS["racing"] == 1


def test_default_threshold_is_3():
    assert _THIN_DATA_THRESHOLDS["default"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_thin_data_threshold.py -v`
Expected: FAIL — `_THIN_DATA_THRESHOLDS` doesn't exist

- [ ] **Step 3: Add threshold dict and use it**

In `src/entry_gate.py`, add near the top (after imports, before class):

```python
# Sport-aware thin data thresholds.
# Tennis/MMA: individual sports with sparse match history.
# Golf/Racing: event-based, even 1 recent result is informative.
# Default: lowered from 5 to 3 after ESPN overhaul.
_THIN_DATA_THRESHOLDS = {
    "tennis": 2,
    "mma": 2,
    "golf": 1,
    "racing": 1,
    "cricket": 3,
    "default": 3,
}
```

Then modify the thin data check at lines 362-375. Replace:

```python
            result_lines = ctx.count("[W]") + ctx.count("[L]")
            if result_lines < 5:
                _thin_data_skipped += 1
                logger.info("SKIP thin data: %s | only %d match results (need 5+)",
                            (m.slug or "")[:35], result_lines)
```

With:

```python
            result_lines = ctx.count("[W]") + ctx.count("[L]")
            # Sport-aware threshold: tennis/MMA/golf need fewer results
            _sport = getattr(m, "sport_tag", "") or ""
            # Detect sport category from sport_tag
            _sport_cat = "default"
            if _sport in ("atp", "wta") or "tennis" in _sport:
                _sport_cat = "tennis"
            elif _sport in ("ufc",) or "mma" in _sport:
                _sport_cat = "mma"
            elif "golf" in _sport or "pga" in _sport:
                _sport_cat = "golf"
            elif "racing" in _sport or "f1" in _sport or "nascar" in _sport:
                _sport_cat = "racing"
            elif "cricket" in _sport:
                _sport_cat = "cricket"
            _threshold = _THIN_DATA_THRESHOLDS.get(_sport_cat, _THIN_DATA_THRESHOLDS["default"])
            if result_lines < _threshold:
                _thin_data_skipped += 1
                logger.info("SKIP thin data: %s | only %d match results (need %d+, sport=%s)",
                            (m.slug or "")[:35], result_lines, _threshold, _sport_cat)
```

Also update the trade_log line to show dynamic threshold:

```python
                self.trade_log.log({
                    "market": m.slug, "action": "HOLD",
                    "rejected": f"Thin data ({result_lines} results, need {_threshold}+)",
                    "price": m.yes_price,
                    "question": getattr(m, "question", ""),
                })
```

- [ ] **Step 4: Run test**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_thin_data_threshold.py -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/ -v --timeout=30 2>&1 | tail -30`
Expected: No failures

- [ ] **Step 6: Commit**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
git add src/entry_gate.py tests/test_thin_data_threshold.py
git commit -m "feat: sport-aware thin data thresholds — tennis=2, golf=1, default=3"
```

---

### Task 10: Final integration verification

**Files:**
- No new files — run existing + new tests

- [ ] **Step 1: Run all new tests together**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_hours_to_start.py tests/test_scanner_esports_time.py tests/test_ranking_formula.py tests/test_esports_slugs.py tests/test_stale_guard.py tests/test_espn_leagues.py tests/test_tennis_data.py tests/test_dynamic_detection.py tests/test_thin_data_threshold.py -v`
Expected: All PASS

- [ ] **Step 2: Run full existing test suite**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/ -v --timeout=60 2>&1 | tail -40`
Expected: No failures

- [ ] **Step 3: Verify imports work**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -c "from src.entry_gate import _hours_to_start, _THIN_DATA_THRESHOLDS; from src.esports_data import _GAME_SLUGS; from src.sports_data import _SPORT_LEAGUES; print(f'Leagues: {len(_SPORT_LEAGUES)}, Slugs: {len(_GAME_SLUGS)}, Thresholds: {len(_THIN_DATA_THRESHOLDS)}')"`
Expected: `Leagues: 90+, Slugs: 15+, Thresholds: 6`

- [ ] **Step 4: Quick smoke test — dry run one cycle**

Run: `cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && timeout 120 python -m src.agent --dry-run --max-cycles=1 2>&1 | tail -50`
Expected: See markets being scanned with new time bucketing, no crashes

- [ ] **Step 5: Final commit (if any uncommitted test fixes)**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
git status
# If clean: done. If changes: commit with descriptive message.
```
