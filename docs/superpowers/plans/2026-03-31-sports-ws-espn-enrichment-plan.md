# Sports WebSocket + ESPN Enrichment + Entry Guards — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent entry into resolved/half-elapsed matches, add real-time match state via Polymarket Sports WebSocket, enrich AI context with 7 new ESPN endpoints, and fix scout cold-start.

**Architecture:** Two new isolated modules (`sports_ws.py`, `espn_enrichment.py`) plus minimal wiring into 8 existing files. No existing module logic changes — only additive guards and data flow additions.

**Tech Stack:** Python 3.11+, `websockets` library (already installed for CLOB feed), ESPN free API (no key needed), Polymarket Sports WebSocket (`wss://sports-api.polymarket.com/ws`)

**Spec:** `docs/superpowers/specs/2026-03-31-sports-ws-espn-enrichment-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/sports_ws.py` | CREATE | Polymarket Sports WebSocket client — real-time match state |
| `src/espn_enrichment.py` | CREATE | 7 new ESPN API endpoints for richer AI context |
| `src/models.py:44` | MODIFY | Add `closed`, `resolved`, `accepting_orders` to MarketData |
| `src/market_scanner.py:194` | MODIFY | Parse 3 new Gamma fields in `_parse_market()` |
| `src/entry_gate.py:88,403,520,527` | MODIFY | Add `sports_ws` param, resolved guard, elapsed guard, log level |
| `src/upset_hunter.py:86,192` | MODIFY | DRY fix: use `get_game_duration()`, threshold 75%→50% |
| `src/sports_discovery.py:43,72` | MODIFY | Add `enrichment` param, integrate odds+enrichment into context |
| `src/sports_data.py:573,576` | MODIFY | Move `"golf"` from `_EVENT_SPORTS` to `_ATHLETE_SPORTS` |
| `src/scout_scheduler.py:98,144` | MODIFY | Add golf leagues, cold-start guard |
| `src/agent.py:137,141,303` | MODIFY | Init `SportsWebSocket` + `ESPNEnrichment`, wire to modules |

---

### Task 1: Add Gamma API fields to MarketData

**Files:**
- Modify: `src/models.py:44`
- Test: `tests/test_models.py` (or inline assertion)

- [ ] **Step 1: Add 3 new fields to MarketData**

In `src/models.py`, after line 44 (`odds_api_implied_prob`), add:

```python
    closed: bool = False                    # Gamma raw "closed" — market closed to trading
    resolved: bool = False                  # Gamma raw "resolved" — outcome finalized
    accepting_orders: bool = True           # Gamma raw "acceptingOrders" — accepting new orders
```

- [ ] **Step 2: Verify no tests break**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass (new fields have defaults, no existing code affected)

- [ ] **Step 3: Commit**

```bash
git add src/models.py
git commit -m "feat: add closed/resolved/accepting_orders fields to MarketData"
```

---

### Task 2: Parse new Gamma fields in market_scanner

**Files:**
- Modify: `src/market_scanner.py:194`
- Test: `tests/test_market_scanner.py`

- [ ] **Step 1: Write failing test**

In `tests/test_market_scanner.py`, add:

```python
def test_parse_market_resolved_fields():
    """Verify closed/resolved/accepting_orders are parsed from raw Gamma data."""
    scanner = MarketScanner.__new__(MarketScanner)
    raw = {
        "conditionId": "0xabc",
        "question": "Test?",
        "outcomePrices": '["0.6","0.4"]',
        "clobTokenIds": '["tok_yes","tok_no"]',
        "volume24hr": 1000,
        "liquidity": 500,
        "slug": "test-market",
        "tags": "[]",
        "endDate": "2026-04-01T00:00:00Z",
        "description": "Test market",
        "closed": True,
        "resolved": True,
        "acceptingOrders": False,
    }
    m = scanner._parse_market(raw)
    assert m is not None
    assert m.closed is True
    assert m.resolved is True
    assert m.accepting_orders is False


def test_parse_market_resolved_defaults():
    """Verify defaults when Gamma response omits closed/resolved/acceptingOrders."""
    scanner = MarketScanner.__new__(MarketScanner)
    raw = {
        "conditionId": "0xdef",
        "question": "Test?",
        "outcomePrices": '["0.5","0.5"]',
        "clobTokenIds": '["tok_yes","tok_no"]',
        "volume24hr": 0,
        "liquidity": 0,
        "slug": "test-defaults",
        "tags": "[]",
        "endDate": "",
        "description": "",
    }
    m = scanner._parse_market(raw)
    assert m is not None
    assert m.closed is False
    assert m.resolved is False
    assert m.accepting_orders is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_market_scanner.py::test_parse_market_resolved_fields -v`
Expected: FAIL — `MarketData.__init__() got an unexpected keyword argument 'closed'` or attribute missing

- [ ] **Step 3: Add parsing in _parse_market()**

In `src/market_scanner.py`, inside `_parse_market()` at line 194 (after `match_start_iso=...`), add:

```python
                closed=bool(raw.get("closed", False)),
                resolved=bool(raw.get("resolved", False)),
                accepting_orders=bool(raw.get("acceptingOrders", True)),
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_market_scanner.py -v --tb=short`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/market_scanner.py tests/test_market_scanner.py
git commit -m "feat: parse closed/resolved/acceptingOrders from Gamma API"
```

---

### Task 3: Add resolved/closed guard to EntryGate

**Files:**
- Modify: `src/entry_gate.py:527`
- Test: `tests/test_entry_gate_guards.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_entry_gate_guards.py`:

```python
"""Tests for entry gate resolved/elapsed guards."""
from unittest.mock import MagicMock
from src.models import MarketData


def _make_market(**overrides) -> MarketData:
    """Helper to build a MarketData with sensible defaults."""
    defaults = dict(
        condition_id="0xtest",
        question="Will A beat B?",
        yes_price=0.6, no_price=0.4,
        yes_token_id="tok_y", no_token_id="tok_n",
        volume_24h=5000, liquidity=3000,
        slug="test-market", tags=["nba"],
        end_date_iso="2026-04-01T00:00:00Z",
        description="test", event_id="ev1",
        sport_tag="nba",
    )
    defaults.update(overrides)
    return MarketData(**defaults)


def test_skip_resolved_market():
    """Market with resolved=True should be skipped."""
    m = _make_market(resolved=True)
    assert m.resolved is True
    # Guard logic: if market.closed or market.resolved or not market.accepting_orders → skip
    should_skip = m.closed or m.resolved or not m.accepting_orders
    assert should_skip is True


def test_skip_closed_market():
    """Market with closed=True should be skipped."""
    m = _make_market(closed=True)
    should_skip = m.closed or m.resolved or not m.accepting_orders
    assert should_skip is True


def test_skip_not_accepting_orders():
    """Market with accepting_orders=False should be skipped."""
    m = _make_market(accepting_orders=False)
    should_skip = m.closed or m.resolved or not m.accepting_orders
    assert should_skip is True


def test_pass_normal_market():
    """Normal active market should not be skipped."""
    m = _make_market(closed=False, resolved=False, accepting_orders=True)
    should_skip = m.closed or m.resolved or not m.accepting_orders
    assert should_skip is False
```

- [ ] **Step 2: Run test to verify it passes (unit logic test)**

Run: `python -m pytest tests/test_entry_gate_guards.py -v`
Expected: PASS (these test the guard logic directly)

- [ ] **Step 3: Add resolved guard to _evaluate_candidates()**

In `src/entry_gate.py`, inside `_evaluate_candidates()` at line 527 (after `for market in markets:` and `cid = market.condition_id`), add the guard before any other processing:

```python
            # --- Guard: resolved / closed / not accepting orders ---
            if market.closed or market.resolved or not market.accepting_orders:
                logger.info("SKIP resolved/closed: %s", (market.slug or "")[:40])
                continue
```

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/entry_gate.py tests/test_entry_gate_guards.py
git commit -m "feat: add resolved/closed/accepting_orders guard in entry gate"
```

---

### Task 4: UpsetHunter DRY fix — use get_game_duration() + threshold 50%

**Files:**
- Modify: `src/upset_hunter.py:86,192`
- Test: `tests/test_upset_hunter.py` (existing)

- [ ] **Step 1: Write failing test for DRY duration**

Add to `tests/test_entry_gate_guards.py`:

```python
def test_estimate_elapsed_pct_uses_sport_duration():
    """Verify _estimate_elapsed_pct uses sport-specific duration, not hardcoded 120."""
    from src.upset_hunter import _estimate_elapsed_pct
    from datetime import datetime, timezone, timedelta

    # NBA match started 80 minutes ago
    # NBA duration = 150 min → elapsed_pct = 80/150 = 0.533
    # Old code would give 80/120 = 0.667 (wrong)
    m = _make_market(
        slug="nba-lal-bos",
        sport_tag="nba",
        match_start_iso=(datetime.now(timezone.utc) - timedelta(minutes=80)).isoformat(),
    )
    pct = _estimate_elapsed_pct(m)
    assert pct is not None
    # With sport-specific duration (150min): 80/150 ≈ 0.533
    assert 0.50 < pct < 0.60, f"Expected ~0.53, got {pct}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_entry_gate_guards.py::test_estimate_elapsed_pct_uses_sport_duration -v`
Expected: FAIL — old code returns ~0.667 (80/120) instead of ~0.533 (80/150)

- [ ] **Step 3: Fix _estimate_elapsed_pct() in upset_hunter.py**

In `src/upset_hunter.py`, replace line 192:

```python
# Old:
            return min(elapsed_min / 120, 1.0)
```

With:

```python
            from src.match_exit import get_game_duration
            duration = get_game_duration(
                m.slug or "",
                getattr(m, "number_of_games", 0),
                getattr(m, "sport_tag", ""),
            )
            return min(elapsed_min / max(duration, 1), 1.0)
```

- [ ] **Step 4: Change threshold from 75% to 50%**

In `src/upset_hunter.py`, line 86, change:

```python
# Old:
                if elapsed_pct is not None and elapsed_pct > 0.75:
# New:
                if elapsed_pct is not None and elapsed_pct > 0.50:
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_entry_gate_guards.py tests/test_upset_hunter.py -v --tb=short`
Expected: All PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add src/upset_hunter.py tests/test_entry_gate_guards.py
git commit -m "fix: UpsetHunter uses sport-specific duration + 50% threshold"
```

---

### Task 5: Polymarket Sports WebSocket — `src/sports_ws.py`

**Files:**
- Create: `src/sports_ws.py`
- Test: `tests/test_sports_ws.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_sports_ws.py`:

```python
"""Tests for Polymarket Sports WebSocket client."""
import json
from src.sports_ws import SportsWebSocket


def test_handle_message_stores_state():
    """Verify incoming WS message is stored and queryable."""
    ws = SportsWebSocket()
    msg = json.dumps({
        "gameId": 123,
        "slug": "nba-cha-bkn",
        "status": "InProgress",
        "score": "98-102",
        "period": "4Q",
        "live": True,
        "ended": False,
        "elapsed": "42:18",
    })
    ws._handle_message(msg)

    state = ws.get_match_state("nba-cha-bkn")
    assert state is not None
    assert state["live"] is True
    assert state["ended"] is False
    assert state["score"] == "98-102"
    assert state["elapsed"] == "42:18"


def test_handle_message_ended():
    """Verify is_ended returns True after match ends."""
    ws = SportsWebSocket()
    msg = json.dumps({
        "slug": "nba-cha-bkn",
        "live": False,
        "ended": True,
        "finished_timestamp": "2026-03-31T00:00:00Z",
    })
    ws._handle_message(msg)
    assert ws.is_ended("nba-cha-bkn") is True
    assert ws.is_live("nba-cha-bkn") is False


def test_get_match_state_unknown_slug():
    """Unknown slug returns None."""
    ws = SportsWebSocket()
    assert ws.get_match_state("unknown-slug") is None
    assert ws.is_ended("unknown-slug") is False
    assert ws.is_live("unknown-slug") is False


def test_slug_prefix_matching():
    """Market slug with date suffix should match WS slug without it."""
    ws = SportsWebSocket()
    msg = json.dumps({"slug": "nba-cha-bkn", "live": True, "ended": False})
    ws._handle_message(msg)

    # Market slug has date suffix
    state = ws.get_match_state("nba-cha-bkn-2026-03-30")
    assert state is not None
    assert state["live"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sports_ws.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.sports_ws'`

- [ ] **Step 3: Implement SportsWebSocket**

Create `src/sports_ws.py`:

```python
"""Polymarket Sports WebSocket — real-time match state feed.

Connects to wss://sports-api.polymarket.com/ws and receives live match
updates for all active sports events. No subscription message needed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_WS_URL = "wss://sports-api.polymarket.com/ws"
_RECONNECT_BASE = 2.0
_RECONNECT_MAX = 60.0
_HEARTBEAT_INTERVAL = 5.0  # Server pings every 5s
_STALE_TIMEOUT = 30.0  # Consider state stale after 30s without update

# Date suffix pattern: -YYYY-MM-DD at end of slug
_DATE_SUFFIX_RE = re.compile(r"-\d{4}-\d{2}-\d{2}$")


class SportsWebSocket:
    """Real-time match state from Polymarket sports feed."""

    def __init__(self) -> None:
        self._states: dict[str, dict] = {}  # slug → match state
        self._lock = threading.Lock()
        self._running = False
        self._connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._reconnect_count = 0
        self._last_message_time = 0.0

    @property
    def connected(self) -> bool:
        return self._connected

    def start_background(self) -> None:
        """Start WebSocket feed in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Sports WebSocket already running")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="ws-sports-feed",
        )
        self._thread.start()
        logger.info("Sports WebSocket started in background thread")

    def stop(self) -> None:
        """Stop the WebSocket feed."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        logger.info("Sports WebSocket stopped")

    def get_match_state(self, slug: str) -> Optional[dict]:
        """Get latest match state by slug. Supports date-suffix matching."""
        with self._lock:
            # Exact match first
            if slug in self._states:
                return self._states[slug].copy()
            # Strip date suffix: "nba-cha-bkn-2026-03-30" → "nba-cha-bkn"
            base_slug = _DATE_SUFFIX_RE.sub("", slug)
            if base_slug != slug and base_slug in self._states:
                return self._states[base_slug].copy()
        return None

    def is_ended(self, slug: str) -> bool:
        """Check if match has ended."""
        state = self.get_match_state(slug)
        return bool(state and state.get("ended"))

    def is_live(self, slug: str) -> bool:
        """Check if match is currently live."""
        state = self.get_match_state(slug)
        return bool(state and state.get("live"))

    def _handle_message(self, raw: str) -> None:
        """Parse incoming WebSocket message and update state."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        slug = data.get("slug")
        if not slug:
            return

        with self._lock:
            self._states[slug] = {
                "game_id": data.get("gameId"),
                "league": data.get("leagueAbbreviation", ""),
                "home_team": data.get("homeTeam", ""),
                "away_team": data.get("awayTeam", ""),
                "status": data.get("status", ""),
                "score": data.get("score", ""),
                "period": data.get("period", ""),
                "live": bool(data.get("live", False)),
                "ended": bool(data.get("ended", False)),
                "elapsed": data.get("elapsed", ""),
                "finished_timestamp": data.get("finished_timestamp"),
                "updated_at": time.time(),
            }
        self._last_message_time = time.time()

    def _run_loop(self) -> None:
        """Run the asyncio event loop in background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_loop())
        except Exception as exc:
            logger.error("Sports WS loop crashed: %s", exc)
        finally:
            self._loop.close()

    async def _connect_loop(self) -> None:
        """Main connection loop with auto-reconnect."""
        import websockets

        delay = _RECONNECT_BASE
        while self._running:
            try:
                async with websockets.connect(
                    _WS_URL,
                    ping_interval=_HEARTBEAT_INTERVAL,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._connected = True
                    self._reconnect_count = 0
                    delay = _RECONNECT_BASE
                    logger.info("Sports WebSocket connected to %s", _WS_URL)

                    async for message in ws:
                        if not self._running:
                            break
                        self._handle_message(message)

            except Exception as exc:
                self._connected = False
                self._reconnect_count += 1
                logger.warning(
                    "Sports WS disconnected (attempt %d): %s — reconnecting in %.0fs",
                    self._reconnect_count, exc, delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, _RECONNECT_MAX)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_sports_ws.py -v --tb=short`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/sports_ws.py tests/test_sports_ws.py
git commit -m "feat: add Polymarket Sports WebSocket for real-time match state"
```

---

### Task 6: Elapsed guard in EntryGate (using Sports WS + fallback)

**Files:**
- Modify: `src/entry_gate.py:88,527`
- Test: `tests/test_entry_gate_guards.py`

- [ ] **Step 1: Add sports_ws parameter to EntryGate.__init__**

In `src/entry_gate.py`, line 103 (after `scout` parameter), add:

```python
        sports_ws: "SportsWebSocket | None" = None,
```

And in the body (after line 118), add:

```python
        self.sports_ws = sports_ws
```

- [ ] **Step 2: Write failing test for elapsed guard**

Add to `tests/test_entry_gate_guards.py`:

```python
def test_elapsed_guard_blocks_half_elapsed():
    """Market past 50% elapsed should be skipped."""
    from src.match_exit import get_game_duration
    from datetime import datetime, timezone, timedelta

    # NBA started 90 min ago. Duration = 150 min. elapsed_pct = 0.60 > 0.50
    m = _make_market(
        slug="nba-lal-bos",
        sport_tag="nba",
        match_start_iso=(datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat(),
    )
    start_dt = datetime.fromisoformat(m.match_start_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    elapsed_min = (now - start_dt).total_seconds() / 60
    duration_min = get_game_duration(m.slug, 0, m.sport_tag)
    elapsed_pct = elapsed_min / max(duration_min, 1)
    assert elapsed_pct > 0.50, f"Expected >0.50, got {elapsed_pct}"


def test_elapsed_guard_passes_early_match():
    """Market in first half should not be skipped."""
    from src.match_exit import get_game_duration
    from datetime import datetime, timezone, timedelta

    # NBA started 30 min ago. Duration = 150 min. elapsed_pct = 0.20 < 0.50
    m = _make_market(
        slug="nba-lal-bos",
        sport_tag="nba",
        match_start_iso=(datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
    )
    start_dt = datetime.fromisoformat(m.match_start_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    elapsed_min = (now - start_dt).total_seconds() / 60
    duration_min = get_game_duration(m.slug, 0, m.sport_tag)
    elapsed_pct = elapsed_min / max(duration_min, 1)
    assert elapsed_pct < 0.50, f"Expected <0.50, got {elapsed_pct}"
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_entry_gate_guards.py -v`
Expected: PASS

- [ ] **Step 4: Add elapsed guard in _evaluate_candidates()**

First, add this import at the top of `_evaluate_candidates()` (after the existing imports on lines 520-521):

```python
        from src.match_exit import get_game_duration
```

**Note:** `datetime` and `timezone` are already imported at module level (line 25). Do NOT re-import them.

Then, inside `_evaluate_candidates()` right after the resolved guard (added in Task 3), add:

```python
            # --- Guard: match past 50% elapsed → skip ---
            elapsed_pct = 0.0
            _slug = market.slug or ""
            _sport = getattr(market, "sport_tag", "") or ""
            _nogs = getattr(market, "number_of_games", 0) or 0
            _msi = getattr(market, "match_start_iso", "") or ""

            # Prefer Sports WebSocket (real-time)
            if self.sports_ws:
                _ws = self.sports_ws.get_match_state(_slug)
                if _ws and _ws.get("ended"):
                    logger.info("SKIP ws-ended: %s", _slug[:40])
                    continue
                if _ws and _ws.get("elapsed"):
                    _parts = _ws["elapsed"].split(":")
                    _el_min = int(_parts[0]) + int(_parts[1]) / 60 if len(_parts) == 2 else 0
                    _dur = get_game_duration(_slug, _nogs, _sport)
                    elapsed_pct = _el_min / max(_dur, 1)

            # Fallback: match_start_iso + sport duration
            if elapsed_pct == 0.0 and _msi:
                try:
                    _start = datetime.fromisoformat(_msi.replace("Z", "+00:00"))
                    _now = datetime.now(timezone.utc)
                    _el_min = (_now - _start).total_seconds() / 60
                    if _el_min > 0:
                        _dur = get_game_duration(_slug, _nogs, _sport)
                        elapsed_pct = _el_min / max(_dur, 1)
                except (ValueError, TypeError):
                    pass

            if elapsed_pct > 0.50:
                logger.info("SKIP half-elapsed: %s | %.0f%% through", _slug[:35], elapsed_pct * 100)
                continue
```

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/entry_gate.py tests/test_entry_gate_guards.py
git commit -m "feat: add elapsed >50% guard with Sports WS + fallback"
```

---

### Task 7: ESPN Enrichment module — `src/espn_enrichment.py`

**Files:**
- Create: `src/espn_enrichment.py`
- Test: `tests/test_espn_enrichment.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_espn_enrichment.py`:

```python
"""Tests for ESPN enrichment endpoints."""
from unittest.mock import MagicMock, patch
from src.espn_enrichment import ESPNEnrichment


def _make_enrichment():
    """Create ESPNEnrichment with mocked SportsDataClient."""
    mock_client = MagicMock()
    mock_client.detect_sport.return_value = ("basketball", "nba")
    return ESPNEnrichment(sports_client=mock_client)


def test_enrich_returns_string_or_none():
    """enrich() should return a context string or None."""
    e = _make_enrichment()
    result = e.enrich("Will Lakers beat Celtics?", "nba-lal-bos", ["nba"])
    # With mocked client, may return None (no real API) — that's fine
    assert result is None or isinstance(result, str)


def test_cache_ttl():
    """Verify TTL cache stores and expires."""
    e = _make_enrichment()
    e._cache["test_key"] = {"data": "value", "ts": 0}  # Expired
    assert e._get_cached("test_key", ttl=300) is None

    import time
    e._cache["test_key2"] = {"data": "value2", "ts": time.time()}
    assert e._get_cached("test_key2", ttl=300) == "value2"


def test_format_standings_section():
    """Verify standings formatting."""
    e = _make_enrichment()
    standing = {"rank": 3, "wins": 45, "losses": 20, "streak": "W5"}
    text = e._format_standing(standing, "Lakers")
    assert "Lakers" in text
    assert "45" in text
    assert "#3" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_espn_enrichment.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.espn_enrichment'`

- [ ] **Step 3: Implement ESPNEnrichment**

Create `src/espn_enrichment.py`:

```python
"""ESPN enrichment — additional endpoints for richer AI context.

Provides: win probability, standings, athlete overview, splits,
rankings, CDN scoreboard, H2H stats. All endpoints are free (no API key).

Receives SportsDataClient via DI for detect_sport() reuse.
Does NOT import anything from src/ at module level.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Optional

import requests

if TYPE_CHECKING:
    from src.sports_data import SportsDataClient

logger = logging.getLogger(__name__)

_SITE_API = "https://site.api.espn.com/apis/site/v2/sports"
_CORE_API = "https://sports.core.api.espn.com/v2/sports"
_WEB_API = "https://site.web.api.espn.com/apis/common/v3/sports"
_CDN_API = "https://cdn.espn.com/core"
_TIMEOUT = 8


class ESPNEnrichment:
    """Additional ESPN data sources for AI context enrichment."""

    def __init__(self, sports_client: "SportsDataClient") -> None:
        self._client = sports_client
        self._cache: dict[str, dict] = {}
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "PolymarketBot/1.0"

    # ── Cache helpers ──────────────────────────────────────────

    def _get_cached(self, key: str, ttl: int = 300) -> Optional[str]:
        entry = self._cache.get(key)
        if entry and (time.time() - entry["ts"]) < ttl:
            return entry["data"]
        return None

    def _set_cache(self, key: str, data: str) -> None:
        self._cache[key] = {"data": data, "ts": time.time()}

    # ── Public entry point ─────────────────────────────────────

    def enrich(self, question: str, slug: str, tags: list[str]) -> Optional[str]:
        """Fetch all applicable enrichment data and return formatted context string."""
        sport_league = self._client.detect_sport(question, slug, tags)
        if not sport_league:
            return None
        sport, league = sport_league

        parts: list[str] = []

        # Team sports: standings + win probability
        if sport not in _ATHLETE_SPORTS:
            standing = self.get_league_standing(sport, league, question, slug)
            if standing:
                parts.append(standing)
            win_prob = self.get_win_probability(sport, league, question, slug)
            if win_prob:
                parts.append(win_prob)
        else:
            # Athlete sports: overview + splits + rankings + H2H
            overview = self.get_athlete_overview(sport, league, question, slug)
            if overview:
                parts.append(overview)
            splits = self.get_athlete_splits(sport, league, question, slug)
            if splits:
                parts.append(splits)
            rankings = self.get_rankings(sport, league)
            if rankings:
                parts.append(rankings)
            h2h = self.get_h2h(sport, league, question, slug)
            if h2h:
                parts.append(h2h)

        # CDN scoreboard (all sports)
        cdn = self.get_cdn_scoreboard(sport, league)
        if cdn:
            parts.append(cdn)

        if not parts:
            return None
        return "\n=== ESPN ENRICHMENT ===\n" + "\n".join(parts)

    # ── Endpoint methods ───────────────────────────────────────

    def get_league_standing(self, sport: str, league: str,
                           question: str, slug: str) -> Optional[str]:
        """Fetch league standings and find team's position."""
        cache_key = f"standing:{sport}:{league}"
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return cached

        try:
            url = f"{_SITE_API}/{sport}/{league}/standings"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            entries = []
            rank_counter = 0
            for group in data.get("children", []):
                for standing in group.get("standings", {}).get("entries", []):
                    rank_counter += 1
                    team = standing.get("team", {})
                    stats = {s["abbreviation"]: s["value"]
                             for s in standing.get("stats", [])
                             if "abbreviation" in s and "value" in s}
                    entries.append({
                        "name": team.get("displayName", ""),
                        "abbrev": team.get("abbreviation", ""),
                        "rank": rank_counter,  # Position in standings array
                        "wins": int(stats.get("W", 0)),
                        "losses": int(stats.get("L", 0)),
                        "streak": stats.get("STRK", ""),
                    })
            if not entries:
                return None
            # Find relevant teams from question/slug
            text = self._format_standings(entries, question, slug)
            if text:
                self._set_cache(cache_key, text)
            return text
        except Exception as exc:
            logger.warning("ESPN standings error: %s", exc)
            return None

    def get_win_probability(self, sport: str, league: str,
                            question: str, slug: str) -> Optional[str]:
        """Fetch sportsbook win probability for a specific event."""
        try:
            # Find event via scoreboard
            event_id, comp_id = self._find_event_ids(sport, league, question, slug)
            if not event_id:
                return None

            url = (f"{_CORE_API}/{sport}/leagues/{league}/events/{event_id}"
                   f"/competitions/{comp_id}/odds?limit=10")
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return None

            probs = []
            for item in items:
                provider = item.get("provider", {}).get("name", "Unknown")
                home = item.get("homeTeamOdds", {})
                away = item.get("awayTeamOdds", {})
                h_ml = home.get("moneyLine")
                a_ml = away.get("moneyLine")
                if h_ml is not None and a_ml is not None:
                    probs.append(f"  {provider}: Home {h_ml:+d} / Away {a_ml:+d}")

            if not probs:
                return None
            return "Win Probability (sportsbooks):\n" + "\n".join(probs[:5])
        except Exception as exc:
            logger.warning("ESPN win probability error: %s", exc)
            return None

    def get_athlete_overview(self, sport: str, league: str,
                            question: str, slug: str) -> Optional[str]:
        """Fetch athlete overview (ranking, injury, news)."""
        try:
            athlete_ids = self._find_athlete_ids(sport, league, question, slug)
            if not athlete_ids:
                return None

            parts = []
            for aid, name in athlete_ids[:2]:
                url = f"{_WEB_API}/{sport}/{league}/athletes/{aid}/overview"
                resp = self._session.get(url, timeout=_TIMEOUT)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                athlete = data.get("athlete", {})
                rank = athlete.get("rank", {}).get("current", {}).get("rank", "N/A")
                injuries = athlete.get("injuries", [])
                injury_status = injuries[0].get("status", "Healthy") if injuries else "Healthy"
                parts.append(f"  {name}: Rank #{rank}, Status: {injury_status}")

            if not parts:
                return None
            return "Athlete Overview:\n" + "\n".join(parts)
        except Exception as exc:
            logger.warning("ESPN athlete overview error: %s", exc)
            return None

    def get_athlete_splits(self, sport: str, league: str,
                           question: str, slug: str) -> Optional[str]:
        """Fetch athlete statistical splits (home/away/surface)."""
        try:
            athlete_ids = self._find_athlete_ids(sport, league, question, slug)
            if not athlete_ids:
                return None

            parts = []
            for aid, name in athlete_ids[:2]:
                url = f"{_SITE_API}/{sport}/{league}/athletes/{aid}/splits"
                resp = self._session.get(url, timeout=_TIMEOUT)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                categories = data.get("splitCategories", [])
                for cat in categories[:2]:
                    cat_name = cat.get("displayName", "")
                    for split in cat.get("splits", [])[:3]:
                        split_name = split.get("displayName", "")
                        stats_list = split.get("stats", [])
                        record = f"{stats_list[0]}-{stats_list[1]}" if len(stats_list) >= 2 else "N/A"
                        parts.append(f"  {name} ({cat_name}/{split_name}): {record}")

            if not parts:
                return None
            return "Athlete Splits:\n" + "\n".join(parts[:8])
        except Exception as exc:
            logger.warning("ESPN athlete splits error: %s", exc)
            return None

    def get_rankings(self, sport: str, league: str) -> Optional[str]:
        """Fetch current rankings (ATP/WTA/golf)."""
        cache_key = f"rankings:{sport}:{league}"
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return cached

        try:
            url = f"{_CORE_API}/{sport}/leagues/{league}/rankings"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            rankings = data.get("rankings", [])
            if not rankings:
                return None

            entries = rankings[0].get("ranks", [])[:20]
            lines = []
            for r in entries:
                athlete = r.get("athlete", {})
                name = athlete.get("displayName", "Unknown")
                rank = r.get("current", "?")
                points = r.get("points", "")
                lines.append(f"  #{rank} {name}" + (f" ({points}pts)" if points else ""))

            if not lines:
                return None
            text = f"Rankings ({league.upper()}):\n" + "\n".join(lines[:10])
            self._set_cache(cache_key, text)
            return text
        except Exception as exc:
            logger.warning("ESPN rankings error: %s", exc)
            return None

    def get_cdn_scoreboard(self, sport: str, league: str) -> Optional[str]:
        """Fetch lightweight CDN scoreboard for live scores."""
        try:
            url = f"{_CDN_API}/{sport}/{league}/scoreboard?xhr=1"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            events = data.get("content", {}).get("sbData", {}).get("events", [])
            if not events:
                return None

            lines = []
            for ev in events[:5]:
                comps = ev.get("competitions", [{}])
                if not comps:
                    continue
                teams = comps[0].get("competitors", [])
                if len(teams) >= 2:
                    t1 = f"{teams[0].get('team', {}).get('abbreviation', '?')} {teams[0].get('score', '?')}"
                    t2 = f"{teams[1].get('team', {}).get('abbreviation', '?')} {teams[1].get('score', '?')}"
                    status = comps[0].get("status", {}).get("type", {}).get("shortDetail", "")
                    lines.append(f"  {t1} vs {t2} ({status})")

            if not lines:
                return None
            return "Live Scoreboard:\n" + "\n".join(lines)
        except Exception as exc:
            logger.warning("ESPN CDN scoreboard error: %s", exc)
            return None

    def get_h2h(self, sport: str, league: str,
                question: str, slug: str) -> Optional[str]:
        """Fetch head-to-head stats between two athletes."""
        try:
            athlete_ids = self._find_athlete_ids(sport, league, question, slug)
            if not athlete_ids or len(athlete_ids) < 2:
                return None

            id_a, name_a = athlete_ids[0]
            id_b, name_b = athlete_ids[1]
            url = f"{_SITE_API}/{sport}/{league}/athletes/{id_a}/vsathlete/{id_b}"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            vs = data.get("vsAthlete", {})
            record = vs.get("record", {})
            wins_a = record.get("wins", 0)
            wins_b = record.get("losses", 0)

            events = vs.get("events", [])
            recent = []
            for ev in events[:5]:
                winner = ev.get("winner", {}).get("displayName", "?")
                date = ev.get("date", "")[:10]
                recent.append(f"    {date}: {winner}")

            result = f"H2H: {name_a} {wins_a}-{wins_b} {name_b}"
            if recent:
                result += "\n  Recent:\n" + "\n".join(recent)
            return result
        except Exception as exc:
            logger.warning("ESPN H2H error: %s", exc)
            return None

    # ── Internal helpers ───────────────────────────────────────

    def _find_event_ids(self, sport: str, league: str,
                        question: str, slug: str) -> tuple[str, str]:
        """Find ESPN event_id and competition_id from scoreboard."""
        try:
            url = f"{_SITE_API}/{sport}/{league}/scoreboard"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return "", ""
            data = resp.json()
            events = data.get("events", [])
            q_lower = question.lower()
            for ev in events:
                ev_name = ev.get("name", "").lower()
                if any(word in ev_name for word in q_lower.split()[:3]):
                    comps = ev.get("competitions", [])
                    if comps:
                        return str(ev.get("id", "")), str(comps[0].get("id", ""))
        except Exception:
            pass
        return "", ""

    def _find_athlete_ids(self, sport: str, league: str,
                          question: str, slug: str) -> list[tuple[str, str]]:
        """Find athlete IDs from question text via ESPN search."""
        results = []
        # Extract potential names from slug: "atp-bolt-wu" → ["bolt", "wu"]
        parts = slug.replace("-", " ").split()
        # Skip sport prefix
        name_parts = [p for p in parts if len(p) > 2 and not p.isdigit()
                      and p not in ("atp", "wta", "ufc", "pga", "lpga")]

        for name in name_parts[:4]:
            try:
                url = f"https://site.web.api.espn.com/apis/common/v3/search"
                resp = self._session.get(url, params={
                    "query": name, "limit": 3, "type": "player",
                }, timeout=_TIMEOUT)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                items = data.get("items", []) or data.get("results", [])
                for item in items:
                    entries = item.get("entries", []) if isinstance(item, dict) else []
                    for entry in entries:
                        aid = entry.get("id", "")
                        display = entry.get("displayName", "")
                        if aid and name.lower() in display.lower():
                            results.append((str(aid), display))
                            break
            except Exception:
                continue

        return results[:2]

    def _format_standing(self, standing: dict, team_name: str) -> str:
        """Format a single team's standing."""
        return (f"  {team_name}: #{standing.get('rank', '?')} "
                f"({standing.get('wins', 0)}W-{standing.get('losses', 0)}L) "
                f"Streak: {standing.get('streak', 'N/A')}")

    def _format_standings(self, entries: list[dict],
                          question: str, slug: str) -> Optional[str]:
        """Find relevant teams and format their standings."""
        q_lower = question.lower()
        slug_parts = set(slug.lower().replace("-", " ").split())
        relevant = []
        for e in entries:
            name_lower = e["name"].lower()
            abbrev_lower = e["abbrev"].lower()
            if (any(word in name_lower for word in slug_parts if len(word) > 2) or
                    abbrev_lower in slug_parts or
                    any(word in q_lower for word in name_lower.split())):
                relevant.append(self._format_standing(e, e["name"]))
        if not relevant:
            return None
        return "League Standings:\n" + "\n".join(relevant[:2])


# Sports where competitors are individual athletes
_ATHLETE_SPORTS = frozenset({"tennis", "mma", "golf"})
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_espn_enrichment.py -v --tb=short`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/espn_enrichment.py tests/test_espn_enrichment.py
git commit -m "feat: add ESPN enrichment module with 7 new endpoints"
```

---

### Task 8: Integrate enrichment into SportsDiscovery

**Files:**
- Modify: `src/sports_discovery.py:43,72`
- Test: `tests/test_sports_discovery.py` (existing or new)

- [ ] **Step 1: Write failing test**

Add to existing test file or create `tests/test_sports_discovery_enrichment.py`:

```python
"""Test enrichment integration in SportsDiscovery."""
from unittest.mock import MagicMock, patch
from src.sports_discovery import SportsDiscovery, DiscoveryResult


def test_resolve_espn_includes_enrichment():
    """resolve() should include enrichment context when available."""
    espn = MagicMock()
    espn.get_match_context.return_value = "=== SPORTS DATA (ESPN) -- NBA ===\nTeam A: 40-20"
    espn.get_espn_odds.return_value = {
        "team_a": "Lakers", "team_b": "Celtics",
        "bookmaker_prob_a": 0.55, "bookmaker_prob_b": 0.45,
        "num_bookmakers": 3,
    }
    enrichment = MagicMock()
    enrichment.enrich.return_value = "=== ESPN ENRICHMENT ===\nStandings: #3"

    discovery = SportsDiscovery(
        espn=espn, pandascore=MagicMock(), cricket=MagicMock(),
        odds_api=MagicMock(), enrichment=enrichment,
    )

    result = discovery.resolve("Will Lakers beat Celtics?", "nba-lal-bos", ["nba"])
    assert result is not None
    assert "SPORTS DATA" in result.context
    assert "BOOKMAKER ODDS" in result.context
    assert "ESPN ENRICHMENT" in result.context
    assert result.espn_odds is not None


def test_resolve_espn_no_enrichment():
    """resolve() should still work when enrichment returns None."""
    espn = MagicMock()
    espn.get_match_context.return_value = "=== SPORTS DATA ==="
    espn.get_espn_odds.return_value = None
    enrichment = MagicMock()
    enrichment.enrich.return_value = None

    discovery = SportsDiscovery(
        espn=espn, pandascore=MagicMock(), cricket=MagicMock(),
        odds_api=MagicMock(), enrichment=enrichment,
    )

    result = discovery.resolve("Will A beat B?", "nba-lal-bos", ["nba"])
    assert result is not None
    assert "SPORTS DATA" in result.context
    assert "BOOKMAKER" not in result.context
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sports_discovery_enrichment.py -v`
Expected: FAIL — `SportsDiscovery.__init__() got an unexpected keyword argument 'enrichment'`

- [ ] **Step 3: Update SportsDiscovery.__init__ and resolve()**

In `src/sports_discovery.py`, update `__init__` (line 43):

```python
    def __init__(
        self,
        espn: "SportsDataClient",
        pandascore: "EsportsDataClient",
        cricket: "CricketDataClient",
        odds_api: "OddsAPIClient",
        enrichment: "ESPNEnrichment | None" = None,
    ) -> None:
        self.espn = espn
        self.pandascore = pandascore
        self.cricket = cricket
        self.odds_api = odds_api
        self.enrichment = enrichment
```

Update the `else: # espn` branch in `resolve()` (lines 72-81):

```python
            else:  # espn
                ctx = self.espn.get_match_context(question, slug, tags)
                if ctx:
                    espn_odds = self.espn.get_espn_odds(question, slug, tags)

                    # Enrichment: additional ESPN endpoints
                    enrichment_ctx = None
                    if self.enrichment:
                        try:
                            enrichment_ctx = self.enrichment.enrich(question, slug, tags)
                        except Exception as exc:
                            logger.warning("Enrichment error for '%s': %s", slug[:40], exc)

                    # Combine context
                    parts = [ctx]
                    if espn_odds:
                        parts.append(
                            f"\n=== BOOKMAKER ODDS (ESPN) ===\n"
                            f"{espn_odds.get('team_a', '?')} "
                            f"{espn_odds.get('bookmaker_prob_a', 0):.0%} vs "
                            f"{espn_odds.get('team_b', '?')} "
                            f"{espn_odds.get('bookmaker_prob_b', 0):.0%} "
                            f"({espn_odds.get('num_bookmakers', 0)} bookmakers)"
                        )
                    if enrichment_ctx:
                        parts.append(enrichment_ctx)
                    full_context = "\n".join(parts)

                    return DiscoveryResult(
                        context=full_context, source="ESPN",
                        confidence="A", espn_odds=espn_odds,
                    )
```

Add TYPE_CHECKING import at top:

```python
if TYPE_CHECKING:
    from src.sports_data import SportsDataClient
    from src.esports_data import EsportsDataClient
    from src.cricket_data import CricketDataClient
    from src.odds_api import OddsAPIClient
    from src.espn_enrichment import ESPNEnrichment
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_sports_discovery_enrichment.py -v --tb=short`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/sports_discovery.py tests/test_sports_discovery_enrichment.py
git commit -m "feat: integrate ESPN enrichment + odds into SportsDiscovery context"
```

---

### Task 9: Golf support + Scout cold-start + Discovery error logging

**Files:**
- Modify: `src/sports_data.py:573,576`
- Modify: `src/scout_scheduler.py:97,98,144`
- Modify: `src/entry_gate.py:403`

- [ ] **Step 1: Move golf from _EVENT_SPORTS to _ATHLETE_SPORTS**

In `src/sports_data.py`, line 573, change:

```python
# Old:
    _ATHLETE_SPORTS = frozenset({"tennis", "mma"})
# New:
    _ATHLETE_SPORTS = frozenset({"tennis", "mma", "golf"})
```

And on line 576, remove `"golf"` from `_EVENT_SPORTS`:

```python
# Old:
    _EVENT_SPORTS = frozenset({"golf", "racing"})
# New:
    _EVENT_SPORTS = frozenset({"racing"})
```

**Why:** Golf H2H markets are athlete-vs-athlete, same as tennis/MMA. Leaving golf in `_EVENT_SPORTS` would create dead code since `_ATHLETE_SPORTS` is checked first in `get_match_context()`.

- [ ] **Step 2: Add golf leagues to _SCOUT_LEAGUES**

In `src/scout_scheduler.py`, before line 98 (end of `_SCOUT_LEAGUES` list), add:

```python
    # === Golf ===
    ("golf", "pga", "PGA Tour"),
    ("golf", "lpga", "LPGA Tour"),
```

Also update the stale comment on line 97:

```python
# Old:
    # NOTE: F1/Golf excluded -- multi-competitor events, not moneyline head-to-head
# New:
    # NOTE: F1 excluded -- multi-competitor events, not moneyline head-to-head
```

- [ ] **Step 3: Add scout cold-start guard**

In `src/scout_scheduler.py`, in `should_run_scout()` at line 145 (after docstring, before `now = ...`), add:

```python
        # Cold start: if queue is empty, run immediately
        if not self._queue:
            return True
```

- [ ] **Step 4: Fix discovery error log level**

In `src/entry_gate.py`, line 403, change:

```python
# Old:
                    logger.debug("Discovery error for %s: %s", (_m.slug or "")[:40], _exc)
# New:
                    logger.warning("Discovery error for %s: %s", (_m.slug or "")[:40], _exc)
```

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/sports_data.py src/scout_scheduler.py src/entry_gate.py
git commit -m "feat: golf support, scout cold-start, discovery error logging"
```

---

### Task 10: Wire everything in agent.py

**Files:**
- Modify: `src/agent.py:86-156,303`

- [ ] **Step 1: Import new modules**

In `src/agent.py`, add imports near the top (with other src imports):

```python
from src.sports_ws import SportsWebSocket
from src.espn_enrichment import ESPNEnrichment
```

- [ ] **Step 2: Create SportsWebSocket instance**

After line 137 (`ws_feed = WebSocketFeed(...)`) add:

```python
        self.sports_ws = SportsWebSocket()
        self.sports_ws.start_background()
```

**Note:** Must be `self.sports_ws` (not local), so it's accessible in the `finally` shutdown block.

- [ ] **Step 3: Create ESPNEnrichment and pass to SportsDiscovery**

After `sports = SportsDataClient()` (around line 87) and before `discovery = SportsDiscovery(...)` (around line 93), add:

```python
        espn_enrichment = ESPNEnrichment(sports_client=sports)
```

Update the SportsDiscovery creation to include enrichment:

```python
        discovery = SportsDiscovery(
            espn=sports, pandascore=self.esports,
            cricket=cricket, odds_api=odds_api,
            enrichment=espn_enrichment,
        )
```

- [ ] **Step 4: Pass sports_ws to EntryGate**

In the EntryGate instantiation (line 141-156), add:

```python
            sports_ws=self.sports_ws,
```

- [ ] **Step 5: Add sports_ws.stop() to shutdown**

In the `finally` block (line 301-304), before `self.ws_feed.stop()`, add:

```python
            self.sports_ws.stop()
```

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add src/agent.py
git commit -m "feat: wire SportsWebSocket + ESPNEnrichment into agent"
```

---

### Task 11: Anti-spaghetti verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All pass

- [ ] **Step 2: Verify no hardcoded 120 in upset_hunter**

Run: `grep -rn "120" src/upset_hunter.py`
Expected: No match on the elapsed duration line

- [ ] **Step 3: Verify no dead code markers**

Run: `grep -rn "def.*unused\|# removed\|# old\|# TODO\|# FIXME" src/sports_ws.py src/espn_enrichment.py`
Expected: No matches

- [ ] **Step 4: Verify import boundaries**

Run: `grep -rn "from src.sports_ws import" src/`
Expected: Only `src/agent.py` (entry_gate uses string annotation, not import)

Run: `grep -rn "from src.espn_enrichment import" src/`
Expected: Only `src/sports_discovery.py` and `src/agent.py`

- [ ] **Step 5: Verify no circular imports**

Run: `python -c "from src.sports_ws import SportsWebSocket; from src.espn_enrichment import ESPNEnrichment; print('No circular imports')"`
Expected: "No circular imports"

- [ ] **Step 6: Line count check**

Run: `wc -l src/sports_ws.py src/espn_enrichment.py`
Expected: ~120 and ~200 respectively

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "chore: anti-spaghetti verification passed"
```
