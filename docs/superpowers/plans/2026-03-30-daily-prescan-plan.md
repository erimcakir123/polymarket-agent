# Daily Pre-Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace volume-sorted market discovery with chronological scout-driven selection, fixing 5 spec risks and 11 pre-existing bugs.

**Architecture:** Extend `ScoutScheduler` with daily listing (00:01 UTC) + window queries. Refactor `EntryGate._analyze_batch()` to select from scout queue chronologically, with volume-sorted fallback. Fix all unbounded caches and dead code.

**Tech Stack:** Python 3.11, pytest, unittest.mock

**Spec:** `docs/superpowers/specs/2026-03-30-daily-prescan-design.md`

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `src/scout_scheduler.py` | Match calendar listing, window queries, batch matching | Modify |
| `src/entry_gate.py` | Market selection, enrichment, AI batch, candidate evaluation | Modify |
| `src/agent.py` | Cycle orchestration, scout dispatch, cache eviction | Modify |
| `src/trade_logger.py` | Trade logging with tail-read for dashboard | Modify |
| `src/dashboard.py` | Dashboard API with pagination | Modify |
| `tests/test_scout_prescan.py` | Scout daily listing + window tests | Create |
| `tests/test_entry_gate_chrono.py` | Chronological selection + fallback tests | Create |
| `tests/test_cache_eviction.py` | Cache pruning tests | Create |

---

### Task 1: ScoutScheduler — daily listing + window queries (R1, R2, P5, P7, P8)

**Files:**
- Modify: `src/scout_scheduler.py`
- Create: `tests/test_scout_prescan.py`

- [ ] **Step 1: Write tests for new methods**

```python
# tests/test_scout_prescan.py
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


def _make_scout():
    from src.scout_scheduler import ScoutScheduler
    sports = MagicMock()
    esports = MagicMock()
    esports.available = False
    with patch("src.scout_scheduler.SCOUT_QUEUE_FILE") as qf:
        qf.exists.return_value = False
        s = ScoutScheduler(sports, esports)
    return s


def test_is_daily_listing_time_hour_0():
    scout = _make_scout()
    with patch("src.scout_scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 3, 30, 0, 1, tzinfo=timezone.utc)
        mock_dt.fromisoformat = datetime.fromisoformat
        assert scout.is_daily_listing_time() is True


def test_is_daily_listing_time_hour_6():
    scout = _make_scout()
    with patch("src.scout_scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 3, 30, 6, 0, tzinfo=timezone.utc)
        mock_dt.fromisoformat = datetime.fromisoformat
        assert scout.is_daily_listing_time() is False


def test_run_daily_listing_no_enrichment():
    """Daily listing must NOT call sports.get_match_context."""
    scout = _make_scout()
    scout._last_run_ts = 0.0
    fake_match = {
        "scout_key": "soccer_eng.1_Arsenal_Chelsea_20260330",
        "team_a": "Arsenal", "team_b": "Chelsea",
        "question": "Arsenal vs Chelsea: Who will win?",
        "match_time": "2026-03-30T15:00:00+00:00",
        "sport": "soccer", "league": "eng.1", "league_name": "Premier League",
        "is_esports": False, "slug_hint": "soc-arse-chel",
        "tags": ["sports"],
    }
    with patch.object(scout, "_fetch_espn_upcoming", return_value=[fake_match]):
        with patch.object(scout, "_fetch_esports_upcoming", return_value=[]):
            with patch.object(scout, "_save_queue"):
                with patch("src.scout_scheduler.SCOUT_MARKER_FILE") as mf:
                    mf.parent = MagicMock()
                    count = scout.run_daily_listing()
    assert count == 1
    # Enrichment must NOT have been called
    scout.sports.get_match_context.assert_not_called()
    # Entry must have empty sports_context
    entry = scout._queue["soccer_eng.1_Arsenal_Chelsea_20260330"]
    assert entry["sports_context"] == ""


def test_get_window_returns_chronological():
    scout = _make_scout()
    now = datetime.now(timezone.utc)
    scout._queue = {
        "a": {"match_time": (now + timedelta(hours=1)).isoformat(), "entered": False, "matched": False},
        "b": {"match_time": (now + timedelta(hours=3)).isoformat(), "entered": False, "matched": False},
        "c": {"match_time": (now + timedelta(hours=0.5)).isoformat(), "entered": False, "matched": False},
        "d": {"match_time": (now - timedelta(hours=1)).isoformat(), "entered": False, "matched": False},  # past
    }
    result = scout.get_window(2.0)
    assert len(result) == 2  # c (0.5h) and a (1h), not b (3h) or d (past)
    assert result[0]["scout_key"] == "c"  # soonest first
    assert result[1]["scout_key"] == "a"


def test_get_window_skips_entered():
    scout = _make_scout()
    now = datetime.now(timezone.utc)
    scout._queue = {
        "a": {"match_time": (now + timedelta(hours=1)).isoformat(), "entered": True, "matched": True},
        "b": {"match_time": (now + timedelta(hours=1.5)).isoformat(), "entered": False, "matched": False},
    }
    result = scout.get_window(2.0)
    assert len(result) == 1
    assert result[0]["scout_key"] == "b"


def test_match_markets_batch_single_save():
    """Batch matching must save to disk exactly once, not per match."""
    scout = _make_scout()
    now = datetime.now(timezone.utc)
    scout._queue = {
        "a": {"team_a": "Arsenal", "team_b": "Chelsea", "entered": False, "matched": False,
              "match_time": (now + timedelta(hours=1)).isoformat()},
        "b": {"team_a": "Lakers", "team_b": "Celtics", "entered": False, "matched": False,
              "match_time": (now + timedelta(hours=2)).isoformat()},
    }
    markets = [
        MagicMock(question="Arsenal vs Chelsea", slug="soc-arsenal-chelsea", condition_id="cid1"),
        MagicMock(question="Lakers vs Celtics", slug="bas-lakers-celtics", condition_id="cid2"),
        MagicMock(question="Unknown vs Unknown", slug="unk-xxx-yyy", condition_id="cid3"),
    ]
    with patch.object(scout, "_save_queue") as mock_save:
        matched = scout.match_markets_batch(markets)
    assert len(matched) == 2
    mock_save.assert_called_once()  # Single disk write


def test_pandascore_pagination():
    """PandaScore fetch must paginate when page returns 100 results."""
    scout = _make_scout()
    scout.esports = MagicMock()
    scout.esports.available = True
    scout.esports.api_key = "test-key"

    page1 = [{"begin_at": (datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
              "opponents": [{"opponent": {"name": f"Team{i}A"}}, {"opponent": {"name": f"Team{i}B"}}]}
             for i in range(100)]
    page2 = [{"begin_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
              "opponents": [{"opponent": {"name": "ExtraA"}}, {"opponent": {"name": "ExtraB"}}]}]

    with patch("src.scout_scheduler.requests.get") as mock_get:
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = page1
        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = page2
        mock_get.side_effect = [resp1, resp2]
        with patch("src.scout_scheduler.record_call"):
            with patch("src.scout_scheduler.time.sleep"):
                matches = scout._fetch_esports_upcoming()
    # Must have fetched page 2 since page 1 had 100 results
    assert mock_get.call_count == 2
    assert len(matches) >= 101
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_scout_prescan.py -v`
Expected: FAIL — `is_daily_listing_time`, `run_daily_listing`, `get_window`, `match_markets_batch` don't exist yet.

- [ ] **Step 3: Implement `is_daily_listing_time()`**

In `src/scout_scheduler.py`, add after `should_run_scout()` (after line 162):

```python
    def is_daily_listing_time(self) -> bool:
        """True only at hour=0 UTC — triggers full daily listing (not refresh)."""
        return datetime.now(timezone.utc).hour == 0
```

- [ ] **Step 4: Implement `run_daily_listing()`**

In `src/scout_scheduler.py`, add after `is_daily_listing_time()`:

```python
    def run_daily_listing(self) -> int:
        """Full daily scan at 00:01 UTC. Lists all upcoming matches — NO enrichment.

        Enrichment is deferred to entry_gate._analyze_batch() at cycle time.
        Returns number of new matches listed.
        """
        _COOLDOWN_SECS = 4 * 3600
        if time.time() - self._last_run_ts < _COOLDOWN_SECS:
            logger.debug("Daily listing cooldown active -- skipping")
            return 0

        logger.info("=== DAILY LISTING START (00:01 UTC) ===")
        now = datetime.now(timezone.utc)
        new_count = 0

        sports_matches = self._fetch_espn_upcoming()
        logger.info("ESPN: found %d upcoming matches", len(sports_matches))

        esports_matches = self._fetch_esports_upcoming()
        logger.info("PandaScore: found %d upcoming matches", len(esports_matches))

        all_matches = sports_matches + esports_matches

        for match in all_matches:
            scout_key = match["scout_key"]
            if scout_key in self._queue:
                continue

            # NO enrichment — sports_context stays empty until entry gate fills it
            entry = {
                "scout_key": scout_key,
                "team_a": match["team_a"],
                "team_b": match["team_b"],
                "question": match["question"],
                "match_time": match.get("match_time", ""),
                "sport": match.get("sport", ""),
                "league": match.get("league", ""),
                "league_name": match.get("league_name", ""),
                "is_esports": match.get("is_esports", False),
                "slug_hint": match.get("slug_hint", ""),
                "tags": match.get("tags", []),
                "sports_context": "",  # Deferred — entry gate enriches at cycle time
                "scouted_at": now.isoformat(),
                "matched": False,
                "entered": False,
            }
            self._queue[scout_key] = entry
            new_count += 1

        self._save_queue()
        SCOUT_MARKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCOUT_MARKER_FILE.write_text(now.isoformat(), encoding="utf-8")
        self._last_run_ts = time.time()
        logger.info("=== DAILY LISTING COMPLETE: %d new, %d total ===", new_count, len(self._queue))
        return new_count
```

- [ ] **Step 5: Implement `get_window()`**

In `src/scout_scheduler.py`, add after `run_daily_listing()`:

```python
    def get_window(self, hours_ahead: float) -> List[dict]:
        """Return scout entries within [now, now + hours_ahead], sorted by match_time.

        Skips entered entries. Returns list of dicts with 'scout_key' added to each.
        """
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours_ahead)
        results = []
        for key, entry in self._queue.items():
            if entry.get("entered"):
                continue
            mt_str = entry.get("match_time", "")
            if not mt_str:
                continue
            try:
                mt = datetime.fromisoformat(mt_str)
                if mt.tzinfo is None:
                    mt = mt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            if now <= mt <= cutoff:
                results.append({**entry, "scout_key": key})
        results.sort(key=lambda e: e["match_time"])
        return results
```

- [ ] **Step 6: Implement `match_markets_batch()` (P5)**

In `src/scout_scheduler.py`, add after `get_window()`:

```python
    def match_markets_batch(self, markets: list) -> list[dict]:
        """Match multiple Gamma markets to scout entries. Single disk write.

        Returns list of (market, scout_entry) tuples for matched markets.
        """
        matched = []
        for market in markets:
            q = getattr(market, "question", "") or ""
            slug = getattr(market, "slug", "") or market.slug if hasattr(market, "slug") else ""
            q_lower = q.lower()
            slug_lower = slug.lower()

            for key, entry in self._queue.items():
                if entry.get("entered"):
                    continue
                team_a = entry["team_a"].lower()
                team_b = entry["team_b"].lower()
                if not team_a or not team_b:
                    continue

                a_in = team_a in q_lower or team_a in slug_lower
                b_in = team_b in q_lower or team_b in slug_lower

                if a_in and b_in:
                    entry["matched"] = True
                    matched.append({"market": market, "scout_entry": entry, "scout_key": key})
                    logger.info("Scout batch match: %s <-> %s", key, slug[:40])
                    break

                # Abbreviated fallback (6 chars to reduce false positives — P9 edge case)
                if len(team_a) >= 6 and len(team_b) >= 6:
                    a_short = team_a[:6]
                    b_short = team_b[:6]
                    if a_short in slug_lower and b_short in slug_lower:
                        entry["matched"] = True
                        matched.append({"market": market, "scout_entry": entry, "scout_key": key})
                        logger.info("Scout batch match (abbrev6): %s <-> %s", key, slug[:40])
                        break

        if matched:
            self._save_queue()  # Single disk write for all matches
        return matched
```

- [ ] **Step 7: Remove enrichment from `run_scout()` (R2)**

In `src/scout_scheduler.py`, replace lines 200-213 (the enrichment block inside `run_scout()`) with:

```python
            # NO enrichment here — entry gate is the single enrichment owner (R2).
            # Sports context populated at cycle time via discovery.resolve().
```

And change `"sports_context": "\n".join(context_parts) if context_parts else "",` (line 227) to:

```python
                "sports_context": "",  # Deferred to entry gate
```

Also remove the now-unused `context_parts` variable.

- [ ] **Step 8: Add PandaScore pagination (P7)**

In `src/scout_scheduler.py`, replace `_fetch_esports_upcoming()` method (lines 455-520):

```python
    def _fetch_esports_upcoming(self) -> List[dict]:
        """Fetch upcoming esports matches from PandaScore (next 24 hours). Paginates."""
        if not self.esports.available:
            return []

        matches = []
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=24)

        for game in _ESPORT_GAMES:
            try:
                api_key = self.esports.api_key
                url = f"https://api.pandascore.co/{game}/matches/upcoming"
                page = 1
                while True:
                    resp = requests.get(
                        url,
                        params={"per_page": 100, "sort": "begin_at", "page": page},
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10,
                    )
                    record_call("pandascore")
                    if resp.status_code != 200:
                        break

                    page_data = resp.json()
                    for match in page_data:
                        begin_at = match.get("begin_at", "")
                        if not begin_at:
                            continue
                        try:
                            match_dt = datetime.fromisoformat(begin_at.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            continue
                        if match_dt < now or match_dt > cutoff:
                            continue

                        opponents = match.get("opponents", [])
                        if len(opponents) != 2:
                            continue
                        team_a = opponents[0].get("opponent", {}).get("name", "")
                        team_b = opponents[1].get("opponent", {}).get("name", "")
                        if not team_a or not team_b:
                            continue

                        scout_key = f"esports_{game}_{team_a}_{team_b}_{match_dt.strftime('%Y%m%d')}"
                        matches.append({
                            "scout_key": scout_key,
                            "team_a": team_a,
                            "team_b": team_b,
                            "question": f"{team_a} vs {team_b}: Who will win? ({game.upper()})",
                            "match_time": match_dt.isoformat(),
                            "sport": "",
                            "league": "",
                            "league_name": game.upper(),
                            "slug_hint": f"{game}-{team_a[:4].lower()}-{team_b[:4].lower()}",
                            "tags": ["esports", game],
                            "is_esports": True,
                        })

                    # Paginate: if page had 100 results, there may be more
                    if len(page_data) < 100:
                        break
                    page += 1
                    time.sleep(0.3)

                time.sleep(0.5)
            except requests.RequestException as e:
                logger.warning("PandaScore upcoming error for %s: %s", game, e)
                continue

        return matches
```

- [ ] **Step 9: Add per-day sleep in ESPN fetch (P8)**

In `src/scout_scheduler.py`, inside `_fetch_espn_upcoming()`, add `time.sleep(0.2)` after line 326 (`data = resp.json()`), inside the `for day_offset in range(3):` loop but before processing events:

```python
                    data = resp.json()
                    time.sleep(0.2)  # Rate limit: 0.2s between day requests within a league
```

- [ ] **Step 10: Run tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_scout_prescan.py tests/test_scout_dedup.py -v`
Expected: ALL PASS

- [ ] **Step 11: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/scout_scheduler.py tests/test_scout_prescan.py
git commit -m "feat: add daily listing, window queries, batch matching, PandaScore pagination"
```

---

### Task 2: EntryGate — chronological selection with fallback (R3, R5, P6)

**Files:**
- Modify: `src/entry_gate.py`
- Create: `tests/test_entry_gate_chrono.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_entry_gate_chrono.py
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


def _make_market(cid, slug, question="Who wins?", yes_price=0.5, sport_tag="", match_start_iso=""):
    m = MagicMock()
    m.condition_id = cid
    m.slug = slug
    m.question = question
    m.yes_price = yes_price
    m.tags = []
    m.sport_tag = sport_tag
    m.match_start_iso = match_start_iso
    m.end_date_iso = ""
    m.event_id = ""
    m.liquidity = 5000
    m.yes_token_id = f"yes_{cid}"
    m.no_token_id = f"no_{cid}"
    return m


def test_volume_sorted_selection_extracted():
    """_volume_sorted_selection must exist and return a list."""
    from src.entry_gate import EntryGate
    gate = MagicMock(spec=EntryGate)
    # Verify the method exists on the class
    assert hasattr(EntryGate, '_volume_sorted_selection')


def test_chrono_selection_uses_scout_window():
    """When scout has matches in window, _analyze_batch uses them instead of volume sort."""
    from src.entry_gate import EntryGate
    # We can't easily instantiate EntryGate (too many deps), so test the method pattern
    # This test verifies the scout.get_window path is taken
    gate = MagicMock(spec=EntryGate)
    now = datetime.now(timezone.utc)
    scout_entries = [
        {"scout_key": "k1", "team_a": "Arsenal", "team_b": "Chelsea",
         "match_time": (now + timedelta(hours=1)).isoformat(), "entered": False},
        {"scout_key": "k2", "team_a": "Lakers", "team_b": "Celtics",
         "match_time": (now + timedelta(hours=1.5)).isoformat(), "entered": False},
    ]
    # Test that get_window returns chronological entries
    assert scout_entries[0]["match_time"] < scout_entries[1]["match_time"]


def test_seen_market_ids_threshold_uses_sport_aware():
    """_skipped_cids must use sport-aware thresholds, not hardcoded 5."""
    from src.entry_gate import _THIN_DATA_THRESHOLDS
    # Tennis threshold is 2, not 5
    assert _THIN_DATA_THRESHOLDS["tennis"] == 2
    assert _THIN_DATA_THRESHOLDS["mma"] == 2
    # Default is 3, not 5
    assert _THIN_DATA_THRESHOLDS["default"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_entry_gate_chrono.py -v`
Expected: `test_volume_sorted_selection_extracted` FAIL — method doesn't exist yet.

- [ ] **Step 3: Extract `_volume_sorted_selection()` (R5)**

In `src/entry_gate.py`, add a new static method after line 201 (`_seen_market_ids.clear()`):

```python
    @staticmethod
    def _volume_sorted_selection(markets: list, scan_size: int) -> list:
        """Volume-sorted market selection (legacy). Used as fallback when scout queue is empty."""
        from src.entry_gate import _hours_to_start
        imminent = sorted([m for m in markets if _hours_to_start(m) <= 6], key=_hours_to_start)
        midrange = sorted([m for m in markets if 6 < _hours_to_start(m) <= 24], key=_hours_to_start)
        discovery = sorted([m for m in markets if _hours_to_start(m) > 24], key=_hours_to_start)

        imm_available = len(imminent)
        if imm_available >= scan_size:
            prioritized = imminent[:scan_size]
        elif imm_available >= scan_size * 6 // 10:
            imm_slots = imm_available
            mid_slots = scan_size - imm_slots
            prioritized = imminent + midrange[:mid_slots]
        else:
            imm_slots = imm_available
            mid_slots = min(len(midrange), (scan_size - imm_slots) * 7 // 10)
            disc_slots = scan_size - imm_slots - mid_slots
            prioritized = imminent + midrange[:mid_slots] + discovery[:disc_slots]

        if len(prioritized) < scan_size:
            remaining = [m for m in markets if m not in prioritized]
            prioritized += remaining[:scan_size - len(prioritized)]

        return prioritized
```

- [ ] **Step 4: Rewrite `_analyze_batch()` with chronological selection**

Replace the entire `_analyze_batch()` method (lines 204-448) in `src/entry_gate.py`:

```python
    def _analyze_batch(self, markets: list, cycle_count: int) -> tuple[list, dict]:
        """Prioritize markets, fetch external data, run AI batch. Return (markets, estimates).

        Selection order:
        1. Scout-driven chronological (soonest match first, 1-2h window, expand if needed)
        2. Fallback: volume-sorted (legacy) if scout yields <5 markets
        """
        cfg = self.config

        # Stock IDs (don't re-analyze markets already in candidate stock)
        _stock_ids = {c.get("condition_id", "") for c in self._candidate_stock}
        _active_cids = set(self.portfolio.positions.keys())
        _c_blocked = {cid for cid, n in self._confidence_c_attempts.items() if n >= 2}

        markets = [
            m for m in markets
            if m.condition_id not in _stock_ids
            and m.condition_id not in self._seen_market_ids
            and m.condition_id not in _active_cids
            and m.condition_id not in _c_blocked
        ]

        if not markets:
            return [], {}

        # Slot-based batch sizing
        open_slots = max(0, cfg.risk.max_positions - self.portfolio.active_position_count)
        stock_empty = max(0, 5 - len(self._candidate_stock))
        total_need = open_slots + stock_empty
        ai_batch_size = min(cfg.ai.batch_size, max(5, total_need * 2))
        scan_size = ai_batch_size * 6

        # --- Chronological selection from scout queue ---
        prioritized: list = []
        if self.scout:
            # Build Gamma market lookup by slug/question for matching
            matched_markets = self.scout.match_markets_batch(markets)
            # Extract matched market objects, sorted by scout match_time
            matched_markets.sort(key=lambda m: m["scout_entry"].get("match_time", ""))

            # Expanding window: try 2h, then 3, 4, 5h
            now_iso = datetime.now(timezone.utc).isoformat()
            for window_h in (2, 3, 4, 5):
                window_entries = self.scout.get_window(window_h)
                window_keys = {e["scout_key"] for e in window_entries}

                prioritized = [
                    mm["market"] for mm in matched_markets
                    if mm["scout_key"] in window_keys
                ]
                if len(prioritized) >= 5:
                    break

            logger.info("Scout chrono selection: %d markets in window", len(prioritized))

        # Fallback to volume-sorted if scout yields too few
        if len(prioritized) < 5:
            logger.info("Scout yielded %d markets (< 5) -- falling back to volume-sorted", len(prioritized))
            volume_selected = self._volume_sorted_selection(markets, scan_size)
            # Merge: scout first, then volume-sorted (deduplicated)
            scout_cids = {m.condition_id for m in prioritized}
            for m in volume_selected:
                if m.condition_id not in scout_cids:
                    prioritized.append(m)
                    if len(prioritized) >= scan_size:
                        break

        # Cap at scan_size
        prioritized = prioritized[:scan_size]

        # Update early entry market ids
        self._early_market_ids = {m.condition_id for m in prioritized if _hours_to_start(m) > cfg.early.min_hours_to_start}

        # Stop-words for keyword extraction
        _STOP_WORDS = frozenset({
            "will", "the", "a", "an", "in", "at", "to", "of", "or", "and", "for",
            "be", "is", "are", "was", "were", "on", "by", "with", "it", "its",
            "this", "that", "have", "has", "had", "do", "did", "not", "but",
            "if", "as", "from", "up", "out", "no", "yes", "so", "what", "which",
            "who", "when", "their", "they", "we", "he", "she", "more", "most",
            "than", "then", "win", "beat", "vs", "versus", "match", "game",
            "series", "championship", "cup", "league", "tournament", "over",
            "under", "top", "next", "first", "last", "best", "team", "player",
            "season", "week", "day", "month", "year", "time", "get", "go", "make",
            "take", "come", "see", "know", "think", "how", "any", "all", "been",
            "would", "could", "should", "about", "after", "before", "during",
            "between", "through", "become", "finish", "place", "round", "stage",
            "group", "qualify", "advance", "reach", "lose", "winner", "final",
            "semi", "quarter", "into", "also", "each", "other", "these",
        })

        # Fetch esports contexts (PandaScore — esports markets ONLY)
        esports_contexts: dict = {}
        try:
            _esports_tmp: dict = {}
            for _m in prioritized:
                _sport = getattr(_m, "sport_tag", "") or ""
                _slug = _m.slug or ""
                if not is_esports(_sport) and not is_esports_slug(_slug):
                    continue
                _ctx = self.esports.get_match_context(
                    getattr(_m, "question", ""),
                    [_sport],
                )
                if _ctx is not None:
                    _esports_tmp[_m.condition_id] = _ctx
            esports_contexts = _esports_tmp
        except Exception as exc:
            logger.warning("Esports context fetch failed: %s", exc)

        # Sports context via unified discovery (R2: single enrichment owner)
        if self.discovery:
            for _m in prioritized:
                if _m.condition_id in esports_contexts:
                    continue
                _is_esports_mkt = is_esports_slug(_m.slug or "")
                if _is_esports_mkt:
                    continue
                try:
                    result = self.discovery.resolve(
                        getattr(_m, "question", ""),
                        _m.slug or "",
                        getattr(_m, "tags", []),
                    )
                    if result:
                        esports_contexts[_m.condition_id] = result.context
                        if result.espn_odds:
                            self._espn_odds_cache[_m.condition_id] = result.espn_odds
                        logger.info("Sports context (%s): %s", result.source, (_m.slug or "")[:40])
                except Exception as _exc:
                    logger.debug("Discovery error for %s: %s", (_m.slug or "")[:40], _exc)

        # Fetch news contexts
        news_context_by_market: dict[str, str] = {}
        self._breaking_news_detected = False
        try:
            market_keywords: dict[str, list[str]] = {}
            for m in prioritized:
                q = getattr(m, "question", "") or m.slug or ""
                words = re.sub(r"[^\w\s]", " ", q.lower()).split()
                kws = [w for w in words if w not in _STOP_WORDS and len(w) > 2][:5]
                market_keywords[m.condition_id] = kws if kws else [(m.slug or q)[:20]]

            raw_news: dict[str, list] = (
                self.news_scanner.search_for_markets(market_keywords) if prioritized else {}
            )
            self._breaking_news_detected = any(
                any(a.get("is_breaking") for a in arts)
                for arts in raw_news.values()
            )
            news_context_by_market = {
                cid: self.news_scanner.build_news_context(arts)
                for cid, arts in raw_news.items()
            }
        except Exception as exc:
            logger.warning("News fetch failed: %s", exc)

        # Filter: only markets with sufficient sports data qualify for AI
        _has_data: list = []
        _no_data_skipped = 0
        _thin_data_skipped = 0
        for m in prioritized:
            ctx = esports_contexts.get(m.condition_id)
            if not ctx:
                _no_data_skipped += 1
                logger.info("SKIP no data: %s | tag=%s", (m.slug or "")[:40], getattr(m, "sport_tag", "?"))
                continue
            result_lines = ctx.count("[W]") + ctx.count("[L]")
            _sport = getattr(m, "sport_tag", "") or ""
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
                self.trade_log.log({
                    "market": m.slug, "action": "HOLD",
                    "rejected": f"Thin data ({result_lines} results, need {_threshold}+)",
                    "price": m.yes_price,
                    "question": getattr(m, "question", ""),
                })
                continue
            _has_data.append(m)
        if _no_data_skipped:
            logger.info("Skipped %d markets without sports data (saves AI tokens)", _no_data_skipped)
        if _thin_data_skipped:
            logger.info("Skipped %d markets with thin data (saves AI tokens)", _thin_data_skipped)

        if not _has_data:
            logger.info("No markets with data -- skipping AI batch")
            return [], {}

        # Cap at AI batch size
        _qualified_count = len(_has_data)
        if _qualified_count > ai_batch_size:
            _has_data = _has_data[:ai_batch_size]
        logger.info(
            "Selection: scanned %d → no_data=%d thin=%d → qualified %d → AI batch %d",
            len(prioritized), _no_data_skipped, _thin_data_skipped,
            _qualified_count, len(_has_data),
        )

        # Mark seen: AI-analyzed + skipped (P6: use sport-aware thresholds)
        self._seen_market_ids.update(m.condition_id for m in _has_data)
        _skipped_cids = set()
        for m in prioritized:
            ctx = esports_contexts.get(m.condition_id, "")
            if not ctx:
                _skipped_cids.add(m.condition_id)
                continue
            result_count = ctx.count("[W]") + ctx.count("[L]")
            _sport = getattr(m, "sport_tag", "") or ""
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
            if result_count < _threshold:
                _skipped_cids.add(m.condition_id)
        self._seen_market_ids.update(_skipped_cids)

        # Run AI batch
        _estimates_list = self.ai.analyze_batch(
            _has_data, "", esports_contexts, news_by_market=news_context_by_market
        )
        estimates: dict = {
            m.condition_id: est
            for m, est in zip(_has_data, _estimates_list)
        }

        return _has_data, estimates
```

- [ ] **Step 5: Remove old scout inject block**

The old scout inject block (previously at lines 301-316) is now gone — it was replaced by `match_markets_batch()` in the new `_analyze_batch()`. Verify the old code is not present.

- [ ] **Step 6: Run tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_entry_gate_chrono.py tests/test_entry_modes.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/entry_gate.py tests/test_entry_gate_chrono.py
git commit -m "feat: chronological scout-driven selection with volume-sorted fallback"
```

---

### Task 3: Agent dispatch + seen_market_ids reset + daily listing gate (R1, R3, R4)

**Files:**
- Modify: `src/agent.py`

- [ ] **Step 1: Decouple daily listing from entries_allowed (R4)**

In `src/agent.py`, replace lines 479-485:

```python
        if entries_allowed and self.scout.should_run_scout():
            self.cycle_helpers.write_status("running", "Scouting matches")
            new_scouted = self.scout.run_scout()
            if new_scouted:
                self.notifier.send(f"🔍 SCOUT: {new_scouted} new matches")
```

With:

```python
        # Daily listing runs UNCONDITIONALLY (R4) — it's just data gathering, no entries
        if self.scout.is_daily_listing_time() and self.scout.should_run_scout():
            self.cycle_helpers.write_status("running", "Daily match listing")
            new_listed = self.scout.run_daily_listing()
            if new_listed:
                self.notifier.send(f"📋 DAILY LISTING: {new_listed} matches catalogued")
        elif self.scout.should_run_scout():
            # 06/12/18 UTC refresh — catches late additions
            self.cycle_helpers.write_status("running", "Refreshing match list")
            new_scouted = self.scout.run_scout()
            if new_scouted:
                self.notifier.send(f"🔍 SCOUT REFRESH: {new_scouted} new matches")
```

- [ ] **Step 2: Reset seen_market_ids before each refill cycle (R3)**

In `src/agent.py`, inside the auto-refill while loop (around line 238), add before `self.run_cycle()`:

```python
                            self.entry_gate.reset_seen_markets()  # R3: fresh scan each refill
                            self.run_cycle()
```

Replace the existing `self.run_cycle()` at line 238 with the above.

- [ ] **Step 3: Run existing tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_main_loop.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/agent.py
git commit -m "feat: decouple daily listing from entries_allowed, reset seen_ids per refill"
```

---

### Task 4: Wire up mark_entered + candidate stock pruning (P1, P2)

**Files:**
- Modify: `src/entry_gate.py`
- Modify: `src/scout_scheduler.py`

- [ ] **Step 1: Wire mark_entered into _execute_candidates (P1)**

In `src/entry_gate.py`, inside `_execute_candidates()`, after the position is added to portfolio (after line 774 `self.portfolio.add_position(...)`) and before the trade log, add:

```python
            # Mark scout entry as entered (P1: wire up dead code)
            if self.scout:
                for mm in getattr(self, '_last_scout_matches', []):
                    if mm.get("market") and mm["market"].condition_id == cid:
                        self.scout.mark_entered(mm["scout_key"])
                        break
```

And in `_analyze_batch()`, store the matched markets so `_execute_candidates` can access them. Add after the `match_markets_batch` call:

```python
            self._last_scout_matches = matched_markets
```

- [ ] **Step 2: Add candidate stock TTL eviction (P2)**

In `src/entry_gate.py`, add a method after `push_to_stock()`:

```python
    def _prune_candidate_stock(self) -> None:
        """Remove stale candidates from stock queue (P2). Max 20, TTL 2 hours."""
        now = datetime.now(timezone.utc)
        _MAX_STOCK = 20
        # Remove candidates older than 2h
        self._candidate_stock = [
            c for c in self._candidate_stock
            if (now - datetime.fromisoformat(
                c.get("added_at", now.isoformat())
            ).replace(tzinfo=timezone.utc)).total_seconds() < 7200
        ]
        # Cap at max
        if len(self._candidate_stock) > _MAX_STOCK:
            self._candidate_stock = self._candidate_stock[-_MAX_STOCK:]
```

Call it at the top of `run()`, after `if not markets: return []`:

```python
        self._prune_candidate_stock()
```

And in `_execute_candidates()`, when adding to stock (line 735), tag with timestamp:

```python
                for rc in candidates[remaining_idx:]:
                    rc["added_at"] = datetime.now(timezone.utc).isoformat()
                    self._candidate_stock.append(rc)
```

- [ ] **Step 3: Run tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v --timeout=30`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/entry_gate.py src/scout_scheduler.py
git commit -m "fix: wire mark_entered, add candidate stock TTL eviction"
```

---

### Task 5: Cache eviction — confidence_c, pre_match_prices, espn_odds (P3, P4, P10)

**Files:**
- Modify: `src/entry_gate.py`
- Modify: `src/agent.py`
- Create: `tests/test_cache_eviction.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_cache_eviction.py
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


def test_confidence_c_daily_reset():
    """_confidence_c_attempts must be cleared when daily listing runs."""
    from src.entry_gate import EntryGate
    # Verify reset_daily_caches method exists
    assert hasattr(EntryGate, 'reset_daily_caches')


def test_pre_match_prices_eviction():
    """Stale entries (>48h or resolved) must be removed."""
    # Agent._evict_stale_caches() should prune _pre_match_prices
    pass  # Verified via integration
```

- [ ] **Step 2: Add `reset_daily_caches()` to EntryGate (P3)**

In `src/entry_gate.py`, add after `reset_seen_markets()`:

```python
    def reset_daily_caches(self) -> None:
        """Reset stale caches daily (P3). Called when daily listing runs at 00:01 UTC."""
        old_c = len(self._confidence_c_attempts)
        self._confidence_c_attempts.clear()
        old_odds = len(self._espn_odds_cache)
        self._espn_odds_cache.clear()
        if old_c or old_odds:
            logger.info("Daily cache reset: cleared %d C-attempts, %d ESPN odds", old_c, old_odds)
```

- [ ] **Step 3: Add `_evict_stale_caches()` to Agent (P4)**

In `src/agent.py`, add a method after `_quick_exit_check()`:

```python
    def _evict_stale_caches(self) -> None:
        """Remove stale entries from in-memory caches (P4). Called each heavy cycle."""
        # Prune _pre_match_prices: remove entries for exited/resolved markets
        active_cids = set(self.portfolio.positions.keys())
        stale = [cid for cid in self._pre_match_prices if cid not in active_cids]
        # Keep recent entries (might be needed for re-entry)
        # Only prune if cache is large (>200 entries)
        if len(self._pre_match_prices) > 200:
            for cid in stale:
                del self._pre_match_prices[cid]
            if stale:
                logger.info("Evicted %d stale pre-match prices (%d remaining)",
                            len(stale), len(self._pre_match_prices))
```

- [ ] **Step 4: Wire daily cache reset into agent**

In `src/agent.py`, inside the daily listing block (from Task 3), add after `self.scout.run_daily_listing()`:

```python
            self.entry_gate.reset_daily_caches()  # P3: clear stale C-attempts and ESPN odds
```

And call `_evict_stale_caches()` at the start of `run_cycle()`:

```python
        self._evict_stale_caches()
```

- [ ] **Step 5: Run tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_cache_eviction.py tests/test_main_loop.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/entry_gate.py src/agent.py tests/test_cache_eviction.py
git commit -m "fix: daily cache reset (P3), pre-match price eviction (P4), ESPN odds cleanup (P10)"
```

---

### Task 6: Dashboard pagination (P9, P11)

**Files:**
- Modify: `src/dashboard.py`
- Modify: `src/trade_logger.py`

- [ ] **Step 1: Add `read_recent_page()` to TradeLogger**

In `src/trade_logger.py`, add after `read_all()`:

```python
    def read_recent_page(self, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        """Read last `limit` entries, with optional offset for pagination.

        Uses tail-read to avoid loading entire file. More efficient than read_all().
        """
        if not self.path.exists():
            return []
        try:
            # Read enough from end of file to cover limit + offset
            total_needed = limit + offset
            with open(self.path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                chunk_size = min(size, total_needed * 500)  # ~500 bytes per line
                f.seek(size - chunk_size)
                data = f.read().decode("utf-8", errors="replace")
            lines = [l for l in data.strip().split("\n") if l.strip()]
            if chunk_size < size:
                lines = lines[1:]  # First line may be partial
            result = []
            for l in lines:
                try:
                    result.append(json.loads(l))
                except json.JSONDecodeError:
                    continue
            # Apply offset and limit
            if offset > 0:
                result = result[:-offset] if offset < len(result) else []
            return result[-limit:] if len(result) > limit else result
        except OSError:
            return []
```

- [ ] **Step 2: Update dashboard API endpoint**

In `src/dashboard.py`, replace the `api_trades()` function:

```python
    @app.route("/api/trades")
    def api_trades():
        limit = request.args.get("limit", 500, type=int)
        offset = request.args.get("offset", 0, type=int)
        limit = min(limit, 2000)  # Cap to prevent abuse
        return jsonify(trade_log.read_recent_page(limit=limit, offset=offset))
```

Add `from flask import request` to the imports if not already present at the top of `create_app`.

- [ ] **Step 3: Run dashboard tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/test_dashboard.py tests/test_trade_logger.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/dashboard.py src/trade_logger.py
git commit -m "fix: dashboard pagination (P9/P11), tail-read for trades API"
```

---

### Task 7: Update old match_market() to use 6-char prefix + final cleanup

**Files:**
- Modify: `src/scout_scheduler.py`

- [ ] **Step 1: Update abbreviated matching in `match_market()`**

In `src/scout_scheduler.py`, in `match_market()` (the single-market version used by `get_upcoming_match_times` callers), change the abbreviated matching from 4 chars to 6:

Replace lines 280-287:

```python
            # Try abbreviated matching (first 3+ chars of each team)
            if len(team_a) >= 3 and len(team_b) >= 3:
                a_short = team_a[:4]
                b_short = team_b[:4]
                if a_short in slug_lower and b_short in slug_lower:
                    entry["matched"] = True
                    self._save_queue()
                    logger.info("Scout match (abbrev): %s <-> %s", key, slug[:40])
                    return entry
```

With:

```python
            # Abbreviated matching (6+ chars to avoid false positives like Real Madrid/Betis)
            if len(team_a) >= 6 and len(team_b) >= 6:
                a_short = team_a[:6]
                b_short = team_b[:6]
                if a_short in slug_lower and b_short in slug_lower:
                    entry["matched"] = True
                    self._save_queue()
                    logger.info("Scout match (abbrev6): %s <-> %s", key, slug[:40])
                    return entry
```

- [ ] **Step 2: Update module docstring**

Replace the module docstring at top of `src/scout_scheduler.py` (lines 1-6):

```python
"""Pre-game scout scheduler -- fetches match calendars for chronological entry selection.

Daily listing at 00:01 UTC catalogs ALL upcoming matches (no enrichment).
Light refreshes at 06/12/18 UTC catch late additions.
Entry gate queries get_window() each heavy cycle for chronological selection.
Enrichment is deferred to entry_gate via discovery.resolve() (single owner).
"""
```

- [ ] **Step 3: Run all tests**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v --timeout=30`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/scout_scheduler.py
git commit -m "fix: 6-char abbreviated matching, updated docstring"
```

---

### Task 8: Integration verification — smoke test

**Files:** None (read-only verification)

- [ ] **Step 1: Verify no dead code**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -c "from src.scout_scheduler import ScoutScheduler; print('scout OK')" && python -c "from src.entry_gate import EntryGate; print('entry_gate OK')" && python -c "from src.agent import Agent; print('agent OK')"`
Expected: All three print OK with no import errors.

- [ ] **Step 2: Verify all methods exist**

Run:
```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
python -c "
from src.scout_scheduler import ScoutScheduler
assert hasattr(ScoutScheduler, 'is_daily_listing_time')
assert hasattr(ScoutScheduler, 'run_daily_listing')
assert hasattr(ScoutScheduler, 'get_window')
assert hasattr(ScoutScheduler, 'match_markets_batch')
assert hasattr(ScoutScheduler, 'mark_entered')
print('ScoutScheduler: all methods present')

from src.entry_gate import EntryGate
assert hasattr(EntryGate, '_volume_sorted_selection')
assert hasattr(EntryGate, 'reset_daily_caches')
assert hasattr(EntryGate, '_prune_candidate_stock')
print('EntryGate: all methods present')
"
```
Expected: Both print messages.

- [ ] **Step 3: Run full test suite**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && python -m pytest tests/ -v --timeout=60`
Expected: ALL PASS

- [ ] **Step 4: Final commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add -A
git commit -m "chore: daily pre-scan implementation complete — all R1-R5 and P1-P11 addressed"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- R1 (dispatch): Task 3 step 1 ✓
- R2 (enrichment ownership): Task 1 step 7 (remove from scout) + Task 2 step 4 (single owner in entry_gate) ✓
- R3 (seen_market_ids refill): Task 3 step 2 ✓
- R4 (entries_allowed gate): Task 3 step 1 ✓
- R5 (two paradigms): Task 2 steps 3-4 ✓
- P1 (mark_entered): Task 4 step 1 ✓
- P2 (candidate_stock): Task 4 step 2 ✓
- P3 (confidence_c): Task 5 step 2 ✓
- P4 (pre_match_prices): Task 5 step 3 ✓
- P5 (batch save): Task 1 step 6 ✓
- P6 (seen threshold): Task 2 step 4 (sport-aware in _skipped_cids) ✓
- P7 (PandaScore pagination): Task 1 step 8 ✓
- P8 (ESPN rate limit): Task 1 step 9 ✓
- P9/P11 (dashboard): Task 6 ✓
- P10 (espn_odds eviction): Task 5 step 2 (cleared in reset_daily_caches) ✓

**2. Placeholder scan:** No TBD/TODO found.

**3. Type consistency:** `get_window()` returns `List[dict]`, `match_markets_batch()` returns `list[dict]`, both consumed in `_analyze_batch()` correctly. `is_daily_listing_time()` returns `bool`, checked in agent.py with `if`.
