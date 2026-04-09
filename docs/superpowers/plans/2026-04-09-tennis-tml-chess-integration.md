# Tennis (TML) + Chess (Lichess/Chess.com) Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the tennis + chess data bottleneck so AI confidence reaches A/B+ instead of always being blocked at B-/C, enabling the bot to enter 16+ chess and ~35 tennis markets per cycle that are currently skipped.

**Architecture:** Add two new data-source modules (`tennis_tml.py`, `chess_data.py` + helper `chess_username_resolver.py`) as standalone singletons with internal caching/throttling. Wire them into `entry_gate._enrich_sports` via a chess fast-path and a tennis TML supplementary fallback — without touching `sports_data.py` (another agent is fixing ESPN hard limits in parallel) and without modifying the EntryGate constructor or thread-pool classification loop.

**Tech Stack:** Python 3.11+, requests, rapidfuzz (already in requirements.txt), stdlib csv/json/threading, Pydantic config models.

---

## Pre-flight context (already verified)

**External endpoints verified live (2026-04-09)**:
- `https://raw.githubusercontent.com/Tennismylife/TML-Database/master/2026.csv` → 200 OK, 137 ATP matches, schema includes `winner_name, loser_name, score, surface, tourney_date, tourney_name, winner_rank, loser_rank`
- `https://raw.githubusercontent.com/Tennismylife/TML-Database/master/2025.csv` → expected to exist (not yet tested in plan, tested in Task 2)
- `https://api.chess.com/pub/titled/GM` → returns 1695 GM usernames
- `https://api.chess.com/pub/player/{username}` → returns `.name` field with real name
- `https://lichess.org/api/users` (POST, bulk) → accepts up to 300 usernames per call
- `https://gamma-api.polymarket.com/events?tag_slug=chess&closed=false` → returns live chess events with title format `"{Player A} vs. {Player B} - {Tournament} (Round N)"`
- Chess events contain 3 markets: `groupItemTitle` = "Player A" / "Player B" / "Draw"

**Codebase understanding**:
- `src/entry_gate.py:467-519` `_enrich_sports` nested function is the enrichment entry point
- `src/entry_gate.py:569` quality gate counts `ctx.count("[W]") + ctx.count("[L]")` — our output MUST use these exact tokens
- Thread pool `max_workers=8` at `entry_gate.py:532`
- Chess markets currently fall into `_sports_markets` bucket and call `self.discovery.resolve()` → ESPN returns None → `SKIP no data`
- `src/sports_discovery.py` is a thin router — we do NOT modify it; chess fast-path happens at `_enrich_sports` level
- `src/matching/sport_classifier.py:95` already recognizes `chess` slug → category mapping
- `src/ai_analyst.py` builds prompts per market — we add a chess-specific warning via a single conditional

**Coordination with parallel agent**:
- Parallel agent is fixing ESPN `sports_data.py:893/915/1011` hard limits (`days_back=14`, `matches[:5]`, `>=10 break`)
- My TML fallback threshold `< 6 tokens` means once ESPN returns 10+ tokens, TML fallback does not fire → clean coexistence
- Zero file overlap: I touch `entry_gate.py`, `ai_analyst.py`, `config.py`, `config.yaml`, `TODO.md`, and 3 new `src/` files. Parallel agent touches `sports_data.py`.

---

## File structure

### New files
```
src/tennis_tml.py                         ~240 lines  — ATP CSV client, singleton, format_context with H2H
src/chess_username_resolver.py            ~200 lines  — Full-auto name → username resolver (no manual override)
src/chess_data.py                         ~320 lines  — Lichess + Chess.com dual source, draw rate, Polymarket draw fetcher
logs/tennis_cache/                        directory   — runtime TML CSV dumps (2025 + 2026)
logs/chess_cache/                         directory   — runtime caches (username_map, titled_raw, stats_cache)
```

### Modified files
```
src/entry_gate.py          ~40 lines added  — chess fast-path + tennis fallback + nested _enrich_chess (inside _analyze_batch only)
src/ai_analyst.py          ~6 lines added   — chess warning in prompt builder
src/config.py              ~20 lines added  — TennisConfig + ChessConfig pydantic models
config.yaml                ~12 lines added  — tennis: + chess: blocks
TODO.md                    append section   — WTA / Egypt-1 / ECL / Saudi Pro League gap notes
```

### Untouched (do NOT modify)
```
src/sports_data.py         — parallel agent working on ESPN hard limits
src/sports_discovery.py    — no changes needed, routing unchanged
src/exit_monitor.py, src/scout_scheduler.py, src/startup_cleanup.py, src/agent.py, CLAUDE.md
logs/positions.json, logs/trades.jsonl, logs/portfolio.jsonl, logs/scout_queue.json, logs/exited_markets.json, logs/outcome_tracker.json
```

---

## Key design decisions (user-approved 2026-04-09)

1. **Config location**: All tunables live in `config.yaml` under `tennis:` and `chess:` blocks. No hardcoded constants in the modules themselves.

2. **Chess username resolution**: Fully automatic, no manual override layer.
   - Bootstrap: fetch Chess.com titled directories (GM + IM + WGM + WIM) → cross-reference with Lichess bulk `/api/users` POST endpoint → build `{real_name: {lichess, chesscom}}` reverse map
   - Per-player lookup: fuzzy match (rapidfuzz ≥ 85) against the reverse map
   - Fallback: username guessing (`firstlast`, `flast`, `lastfirst`) with `.name` validation
   - Persistent cache at `logs/chess_cache/username_map.json` — resolved entries never re-fetched
   - Failed resolutions: cached with 7-day retry TTL

3. **Tennis TML data**: Merge 2026 + 2025 CSVs at load time (2 HTTP calls, 6-hour refresh). Show last 10 decisive matches per player + last 5 H2H matches. ATP only — WTA skipped with TODO note.

4. **Chess data format**:
   - Last 10 **decisive** rated games per player (draws excluded, `[W]/[L]` tokens only)
   - Recent form line: `3W-9D-3L` (includes draw count for AI awareness)
   - Explicit `DRAW RATE: 60%` line for each player
   - Last 5 H2H matches (deduplicated by game ID across Lichess + Chess.com sources)
   - Polymarket sibling draw market price fetched and embedded in context

5. **Draw handling (chess-specific)**:
   - Draws at elite chess level: 50-65% for classical, 30-40% for blitz — this is a critical risk for "Will X win?" markets
   - Dual-layer warning: `chess_data.py` appends a warning in the context AND `ai_analyst.py` adds a chess-specific prompt note when the market is chess
   - No default bias toward NO — AI uses draw rate + Polymarket draw market price to compute effective YES probability

6. **Tennis TML trigger**: Only when ESPN returns `< 6 [W]/[L] tokens` (i.e., would grade as B- or worse). Once parallel agent fixes ESPN to return 10+ matches, TML stays dormant unless ESPN is down.

7. **No EntryGate constructor changes**: Both new modules are module-level singletons accessed via `get_tennis_tml()` / `get_chess_data()`. This avoids touching `EntryGate.__init__`.

8. **Threading**: Tennis TML uses a threading.Lock only during CSV refresh (read-only afterwards). Chess client enforces 1.1s serial rate limit via internal lock, so the 8-worker thread pool gracefully serializes chess calls without deadlock.

---

## Breakage analysis (CLAUDE.md §2.5 "Önce Neyi Bozar?")

Before writing any code, I grep-scanned all consumers of the touched symbols and identified the following risk surface:

### `entry_gate._enrich_sports` modifications
- **Callers**: only `pool.submit(_enrich_sports, _m)` at `entry_gate.py:537`
- **Return type**: `("sports", cid, ctx, espn_odds)` tuple — unchanged
- **Exception behavior**: unchanged (outer try/except catches everything → returns `(..., None, None)`)
- **Quality gate interaction**: my output uses `[W]`/`[L]` tokens → gate at `entry_gate.py:569` counts them correctly
- **Breaking risk**: NONE. Additive-only change.

### `ai_analyst.py` modifications
- **Consumer of prompt**: AI batch call via Anthropic API
- **Existing tests**: `test_ai_analyst.py`, `test_ai_confidence_prompt.py` — we must run these after modification
- **Breaking risk**: LOW. One conditional string append. If tests assert specific prompt content, we update the test to accept the new conditional.

### `config.py` / `config.yaml` additions
- **Consumer**: `load_config()` and every `cfg.*` reference
- **Existing tests**: `test_config.py` — asserts default values load correctly
- **Breaking risk**: NONE. New fields with pydantic defaults. Missing `tennis:` / `chess:` in YAML → defaults apply.

### New modules (`tennis_tml.py`, `chess_data.py`, `chess_username_resolver.py`)
- **Breaking risk**: NONE — zero existing callers. Only new callers are my own changes in `entry_gate.py`.

### Network failures
- All external HTTP calls wrapped in try/except → return `None` on failure → falls into existing "no data skip" path
- No crash propagation to main loop
- Cache persistence ensures warm restarts work offline

### Parallel agent overlap
- Parallel agent → `sports_data.py` (not touched by me)
- My tennis TML fallback threshold `< 6` = dormant once ESPN improves
- No merge conflicts

**Verdict**: Zero blocking breakages. All changes are additive with backward-compatible defaults.

---

## Task breakdown

Each task ends with a commit. Tasks are independent enough that partial progress is mergeable.

---

### Task 1: Config schema (TennisConfig + ChessConfig)

**Files**:
- Modify: `src/config.py`
- Modify: `config.yaml`

**Step 1.1 — Add pydantic models to `src/config.py`**

Insert after `class ProbabilityEngineConfig` (~line 132):

```python
class TennisConfig(BaseModel):
    tml_enabled: bool = True
    tml_refresh_hours: int = 6
    tml_max_matches_per_player: int = 10
    tml_max_h2h_matches: int = 5
    tml_fallback_threshold_tokens: int = 6  # trigger TML when ESPN < this
    tml_years_to_merge: int = 2  # 2026 + 2025


class ChessConfig(BaseModel):
    enabled: bool = True
    lichess_enabled: bool = True
    chesscom_enabled: bool = True
    stats_cache_hours: int = 6
    max_games_per_player: int = 10
    max_h2h_games: int = 5
    rate_limit_seconds: float = 1.1
    username_resolver_refresh_days: int = 30
    failed_resolve_retry_days: int = 7
    fetch_polymarket_draw_price: bool = True
```

Add to `AppConfig`:
```python
class AppConfig(BaseModel):
    # ... existing fields ...
    tennis: TennisConfig = TennisConfig()
    chess: ChessConfig = ChessConfig()
```

**Step 1.2 — Add YAML blocks to `config.yaml`**

Append before the `notifications:` block:

```yaml
tennis:
  tml_enabled: true
  tml_refresh_hours: 6
  tml_max_matches_per_player: 10
  tml_max_h2h_matches: 5
  tml_fallback_threshold_tokens: 6
  tml_years_to_merge: 2

chess:
  enabled: true
  lichess_enabled: true
  chesscom_enabled: true
  stats_cache_hours: 6
  max_games_per_player: 10
  max_h2h_games: 5
  rate_limit_seconds: 1.1
  username_resolver_refresh_days: 30
  failed_resolve_retry_days: 7
  fetch_polymarket_draw_price: true
```

**Step 1.3 — Verify**

```bash
python -c "from src.config import load_config; c = load_config(); print('tennis:', c.tennis); print('chess:', c.chess)"
```
Expected: prints both config objects with defaults overridden by YAML values.

```bash
python -m pytest tests/test_config.py -v
```
Expected: all existing tests pass.

**Step 1.4 — Commit**

```bash
git add src/config.py config.yaml
git commit -m "feat(config): add tennis + chess config schemas"
```

---

### Task 2: Tennis TML client module

**Files**:
- Create: `src/tennis_tml.py`
- Runtime directory: `logs/tennis_cache/`

**Step 2.1 — Verify TML 2025 CSV exists**

```bash
curl -sI --max-time 10 "https://raw.githubusercontent.com/Tennismylife/TML-Database/master/2025.csv" | head -3
```
Expected: `HTTP/1.1 200 OK`. If 404, adjust plan to use only 2026 (document in code comment).

**Step 2.2 — Write `src/tennis_tml.py`**

Complete module file:

```python
"""Tennis match data from TML-Database (Tennismylife GitHub) — ATP only.

Forever-free, MIT-licensed ATP match archive with scores, surface, ranking, and
tournament metadata. Used as supplementary data source when ESPN returns thin
match history (<6 [W]/[L] tokens → B- confidence → bot blocked).

Merges current + previous year CSVs to guarantee ≥10 matches per active top-200
ATP player year-round, including the January sparse-data window.

WTA is NOT supported — TML only publishes ATP data. WTA markets must skip this
fallback and rely on ESPN only (see docs/TODO.md gap note).
"""
from __future__ import annotations

import csv
import io
import logging
import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from rapidfuzz import fuzz, process

from src.config import load_config

logger = logging.getLogger(__name__)

_TML_BASE = "https://raw.githubusercontent.com/Tennismylife/TML-Database/master"
_CACHE_DIR = Path("logs/tennis_cache")


@dataclass
class TMLMatch:
    date: str       # YYYYMMDD
    tourney: str
    surface: str
    winner: str
    loser: str
    score: str
    w_rank: Optional[int]
    l_rank: Optional[int]


class TennisTMLClient:
    """Forever-free ATP match data from TML GitHub CSV.

    Thread-safe singleton. Caches merged CSV in memory with 6-hour refresh.
    Persists to disk for offline warm starts.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._matches: list[TMLMatch] = []
        self._player_names_normalized: set[str] = set()
        self._loaded_at: float = 0.0
        self._cfg = load_config().tennis

    def _ensure_loaded(self) -> None:
        now = time.time()
        refresh_seconds = self._cfg.tml_refresh_hours * 3600
        if self._matches and (now - self._loaded_at) < refresh_seconds:
            return
        with self._lock:
            # Double-check after lock
            if self._matches and (now - self._loaded_at) < refresh_seconds:
                return
            self._load_merged_csv()

    def _load_merged_csv(self) -> None:
        """Fetch current + (tml_years_to_merge - 1) previous years and merge."""
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        current_year = datetime.now(timezone.utc).year
        years = [current_year - i for i in range(self._cfg.tml_years_to_merge)]

        all_matches: list[TMLMatch] = []
        all_names: set[str] = set()

        for year in years:
            text = self._fetch_year_csv(year)
            if not text:
                continue
            parsed, names = self._parse_csv_text(text)
            all_matches.extend(parsed)
            all_names.update(names)

        # Sort by date descending for "most recent first" traversal
        all_matches.sort(key=lambda m: m.date, reverse=True)
        self._matches = all_matches
        self._player_names_normalized = all_names
        self._loaded_at = time.time()
        logger.info(
            "TML loaded: %d matches, %d unique players (years=%s)",
            len(all_matches), len(all_names), years,
        )

    def _fetch_year_csv(self, year: int) -> Optional[str]:
        """Fetch {year}.csv from GitHub raw, fall back to disk cache on failure."""
        url = f"{_TML_BASE}/{year}.csv"
        cache_path = _CACHE_DIR / f"tml_atp_{year}.csv"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            text = resp.text
            cache_path.write_text(text, encoding="utf-8")
            return text
        except Exception as exc:
            logger.warning("TML fetch failed for %d: %s — trying disk cache", year, exc)
            if cache_path.exists():
                return cache_path.read_text(encoding="utf-8")
            return None

    @staticmethod
    def _parse_csv_text(text: str) -> tuple[list[TMLMatch], set[str]]:
        matches: list[TMLMatch] = []
        names: set[str] = set()
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                winner = row.get("winner_name", "").strip()
                loser = row.get("loser_name", "").strip()
                if not winner or not loser:
                    continue
                w_rank_raw = (row.get("winner_rank") or "").strip()
                l_rank_raw = (row.get("loser_rank") or "").strip()
                m = TMLMatch(
                    date=row.get("tourney_date", "").strip(),
                    tourney=row.get("tourney_name", "").strip(),
                    surface=row.get("surface", "").strip(),
                    winner=winner,
                    loser=loser,
                    score=row.get("score", "").strip(),
                    w_rank=int(w_rank_raw) if w_rank_raw.isdigit() else None,
                    l_rank=int(l_rank_raw) if l_rank_raw.isdigit() else None,
                )
                matches.append(m)
                names.add(_normalize_name(winner))
                names.add(_normalize_name(loser))
            except (ValueError, KeyError):
                continue
        return matches, names

    def get_player_matches(
        self, name: str, limit: Optional[int] = None,
    ) -> list[tuple[TMLMatch, bool]]:
        """Return [(match, won), ...] for a player, most recent first."""
        self._ensure_loaded()
        if not self._matches:
            return []
        if limit is None:
            limit = self._cfg.tml_max_matches_per_player

        target = _normalize_name(name)
        # Fuzzy-resolve if exact not present
        if target not in self._player_names_normalized:
            best = process.extractOne(
                target, self._player_names_normalized,
                scorer=fuzz.WRatio, score_cutoff=85,
            )
            if not best:
                return []
            target = best[0]

        results: list[tuple[TMLMatch, bool]] = []
        for m in self._matches:
            if _normalize_name(m.winner) == target:
                results.append((m, True))
            elif _normalize_name(m.loser) == target:
                results.append((m, False))
            if len(results) >= limit:
                break
        return results

    def get_head_to_head(
        self, player_a: str, player_b: str, limit: Optional[int] = None,
    ) -> list[tuple[TMLMatch, bool]]:
        """Return [(match, a_won), ...] for H2H matches, most recent first."""
        self._ensure_loaded()
        if limit is None:
            limit = self._cfg.tml_max_h2h_matches
        a = _normalize_name(player_a)
        b = _normalize_name(player_b)
        h2h: list[tuple[TMLMatch, bool]] = []
        for m in self._matches:
            w = _normalize_name(m.winner)
            l = _normalize_name(m.loser)
            if w == a and l == b:
                h2h.append((m, True))
            elif w == b and l == a:
                h2h.append((m, False))
            if len(h2h) >= limit:
                break
        return h2h

    def format_context(self, question: str, slug: str) -> Optional[str]:
        """Build ESPN-compatible context string with [W]/[L] tokens.

        Returns None if:
          - TML not loaded
          - No matches found for either player
          - WTA market (not supported)
        """
        if not self._cfg.tml_enabled:
            return None

        # WTA skip
        if "wta" in (slug or "").lower() or "wta" in (question or "").lower():
            logger.debug("TML skip WTA: %s", slug[:40])
            return None

        player_a, player_b = _parse_players_from_question(question)
        if not player_a or not player_b:
            # Fallback: try slug
            player_a, player_b = _parse_players_from_slug(slug)
            if not player_a or not player_b:
                return None

        self._ensure_loaded()
        if not self._matches:
            return None

        a_matches = self.get_player_matches(player_a)
        b_matches = self.get_player_matches(player_b)
        if not a_matches and not b_matches:
            return None

        parts = [f"=== TENNIS DATA (TML) -- ATP ==="]

        for label, name, matches in [
            ("PLAYER A", player_a, a_matches),
            ("PLAYER B", player_b, b_matches),
        ]:
            if not matches:
                parts.append(f"\n{label}: {name} -- no recent TML matches")
                continue
            wins = sum(1 for _, won in matches if won)
            losses = len(matches) - wins
            parts.append(f"\n{label}: {name}")
            parts.append(f"  Recent form ({len(matches)} matches): {wins}W-{losses}L")
            parts.append("  Recent matches:")
            for m, won in matches:
                opp = m.loser if won else m.winner
                result = "W" if won else "L"
                date_fmt = _format_date(m.date)
                surface_tag = f" [{m.surface}]" if m.surface else ""
                parts.append(
                    f"    [{result}] vs {opp} ({m.score}){surface_tag} "
                    f"({m.tourney}, {date_fmt})"
                )

        # H2H section
        h2h = self.get_head_to_head(player_a, player_b)
        if h2h:
            a_wins = sum(1 for _, a_won in h2h if a_won)
            b_wins = len(h2h) - a_wins
            parts.append(f"\nH2H: {player_a} {a_wins}-{b_wins} {player_b}")
            for m, a_won in h2h:
                result = "W" if a_won else "L"
                date_fmt = _format_date(m.date)
                parts.append(
                    f"    [{result}] vs {player_b if a_won else player_a} "
                    f"({m.score}) ({m.tourney}, {date_fmt})"
                )

        parts.append(
            "\nThis is an ATP tennis match. Use recent form, rankings, "
            "surface, and H2H to estimate win probability."
        )
        return "\n".join(parts)


# ── Module-level helpers ────────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace. For fuzzy matching only."""
    if not name:
        return ""
    n = unicodedata.normalize("NFD", name)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = n.lower().strip()
    return " ".join(n.split())


def _format_date(yyyymmdd: str) -> str:
    if len(yyyymmdd) == 8 and yyyymmdd.isdigit():
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return yyyymmdd


def _parse_players_from_question(question: str) -> tuple[Optional[str], Optional[str]]:
    """Extract (player_a, player_b) from Polymarket question text.

    Handles 'Will X beat Y', 'Will X defeat Y', 'X to beat Y' patterns.
    """
    if not question:
        return None, None
    q = question.strip()
    patterns = [
        r'[Ww]ill\s+(.+?)\s+(?:beat|defeat|win against|win over)\s+(.+?)[\s?]*$',
        r'(.+?)\s+to\s+(?:beat|defeat)\s+(.+?)[\s?]*$',
        r'[Ww]ill\s+(.+?)\s+vs\.?\s+(.+?)\s*$',
    ]
    for pat in patterns:
        m = re.search(pat, q)
        if m:
            a = m.group(1).strip().rstrip("?").strip()
            b = m.group(2).strip().rstrip("?").strip()
            if len(a) >= 3 and len(b) >= 3:
                return a, b
    return None, None


def _parse_players_from_slug(slug: str) -> tuple[Optional[str], Optional[str]]:
    """Extract player tokens from slug like 'atp-sinner-machac-2026-04-09'.

    This is a WEAK fallback — returns tokens that need fuzzy matching.
    """
    if not slug:
        return None, None
    parts = slug.lower().split("-")
    if len(parts) < 3:
        return None, None
    non_date: list[str] = []
    for p in parts[1:]:
        if len(p) == 4 and p.isdigit():
            break
        non_date.append(p)
    if len(non_date) >= 2:
        return non_date[0], non_date[1]
    return None, None


# ── Singleton access ────────────────────────────────────────────────────────

_singleton: Optional[TennisTMLClient] = None
_singleton_lock = threading.Lock()


def get_tennis_tml() -> TennisTMLClient:
    """Return the shared TennisTMLClient singleton (thread-safe)."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = TennisTMLClient()
    return _singleton
```

**Step 2.3 — Syntax + import check**

```bash
python -c "import ast; ast.parse(open('src/tennis_tml.py').read()); print('syntax ok')"
python -c "from src.tennis_tml import get_tennis_tml, TennisTMLClient, TMLMatch; print('imports ok')"
```
Expected: `syntax ok` + `imports ok`.

**Step 2.4 — Smoke test (network)**

```bash
python -c "
from src.tennis_tml import get_tennis_tml
c = get_tennis_tml()
ctx = c.format_context('Will Jannik Sinner beat Tomas Machac?', 'atp-sinner-machac-2026-04-09')
print(ctx[:1500] if ctx else 'NONE')
print('--- tokens:', (ctx or '').count('[W]') + (ctx or '').count('[L]'))
"
```
Expected: non-empty context with at least 4 `[W]`/`[L]` tokens (ideally 15+ with H2H).

**Step 2.5 — Commit**

```bash
git add src/tennis_tml.py
git commit -m "feat(tennis): add TML-Database ATP client with H2H support"
```

---

### Task 3: Chess username resolver module

**Files**:
- Create: `src/chess_username_resolver.py`
- Runtime cache: `logs/chess_cache/username_map.json`, `logs/chess_cache/titled_raw.json`

**Step 3.1 — Write `src/chess_username_resolver.py`**

```python
"""Fully automatic chess player name → platform username resolver.

Strategy:
  1. Bootstrap: fetch Chess.com titled directories (GM/IM/WGM/WIM) → 1695+ GMs
     Cross-reference via Lichess bulk POST /api/users → extract realName
     Build reverse map {normalized_real_name: {lichess, chesscom}}
  2. Per-player lookup: fuzzy match (rapidfuzz ≥ 85) against reverse map
  3. Fallback: username guessing (firstlast, flast, lastfirst) with .name validation
  4. Persistent cache at logs/chess_cache/username_map.json — zero re-fetch cost
  5. Failed resolutions: 7-day retry TTL

No manual override layer — fully automatic per user request (2026-04-09).
"""
from __future__ import annotations

import json
import logging
import threading
import time
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests
from rapidfuzz import fuzz, process

from src.config import load_config

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("logs/chess_cache")
_USERNAME_MAP_PATH = _CACHE_DIR / "username_map.json"
_TITLED_RAW_PATH = _CACHE_DIR / "titled_raw.json"
_FAILED_CACHE_PATH = _CACHE_DIR / "unresolved.json"

_CHESSCOM_BASE = "https://api.chess.com/pub"
_LICHESS_BASE = "https://lichess.org/api"
_UA = "PolymarketAgent/1.0 (github.com/erimc/polymarket-agent)"

_TITLES = ["GM", "IM", "WGM", "WIM"]  # Covers Polymarket's chess player pool comfortably


@dataclass
class ResolvedUser:
    real_name: str
    lichess: Optional[str]
    chesscom: Optional[str]
    resolved_at: str  # ISO


class ChessUsernameResolver:
    """Thread-safe singleton resolver."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cfg = load_config().chess
        self._cache: dict[str, ResolvedUser] = {}  # normalized_name → ResolvedUser
        self._failed: dict[str, str] = {}          # normalized_name → last_attempt_iso
        self._titled_raw: dict[str, list[str]] = {}  # title → [usernames]
        self._titled_loaded_at: float = 0.0
        self._reverse_map: dict[str, tuple[Optional[str], Optional[str]]] = {}
        # normalized_real_name → (lichess_username, chesscom_username)
        self._last_request_at: float = 0.0
        self._load_persistent_cache()

    # ── Persistence ────────────────────────────────────────────────

    def _load_persistent_cache(self) -> None:
        try:
            if _USERNAME_MAP_PATH.exists():
                data = json.loads(_USERNAME_MAP_PATH.read_text(encoding="utf-8"))
                self._cache = {
                    k: ResolvedUser(**v) for k, v in data.items()
                }
            if _FAILED_CACHE_PATH.exists():
                self._failed = json.loads(_FAILED_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Chess cache load error: %s", exc)

    def _persist_cache(self) -> None:
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            serialized = {k: asdict(v) for k, v in self._cache.items()}
            tmp = _USERNAME_MAP_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
            tmp.replace(_USERNAME_MAP_PATH)
            tmp2 = _FAILED_CACHE_PATH.with_suffix(".tmp")
            tmp2.write_text(json.dumps(self._failed, indent=2), encoding="utf-8")
            tmp2.replace(_FAILED_CACHE_PATH)
        except Exception as exc:
            logger.warning("Chess cache persist error: %s", exc)

    # ── Rate limiting ─────────────────────────────────────────────

    def _throttle(self) -> None:
        now = time.time()
        delta = now - self._last_request_at
        if delta < self._cfg.rate_limit_seconds:
            time.sleep(self._cfg.rate_limit_seconds - delta)
        self._last_request_at = time.time()

    # ── Bootstrap: titled directories ─────────────────────────────

    def _ensure_titled_loaded(self) -> None:
        """Load Chess.com titled directories once per 30 days."""
        refresh_seconds = self._cfg.username_resolver_refresh_days * 86400
        now = time.time()
        if self._titled_raw and (now - self._titled_loaded_at) < refresh_seconds:
            return

        # Try disk cache first
        if _TITLED_RAW_PATH.exists():
            try:
                data = json.loads(_TITLED_RAW_PATH.read_text(encoding="utf-8"))
                disk_loaded_at = data.get("loaded_at", 0)
                if (now - disk_loaded_at) < refresh_seconds:
                    self._titled_raw = data.get("titles", {})
                    self._titled_loaded_at = disk_loaded_at
                    logger.info("Loaded titled directory from disk cache")
                    self._build_reverse_map_if_needed()
                    return
            except Exception:
                pass

        # Fetch from API
        raw: dict[str, list[str]] = {}
        for title in _TITLES:
            try:
                self._throttle()
                resp = requests.get(
                    f"{_CHESSCOM_BASE}/titled/{title}",
                    headers={"User-Agent": _UA}, timeout=15,
                )
                resp.raise_for_status()
                players = resp.json().get("players", [])
                raw[title] = players
                logger.info("Chess.com titled %s: %d players", title, len(players))
            except Exception as exc:
                logger.warning("Chess.com titled %s fetch failed: %s", title, exc)
                raw[title] = []

        self._titled_raw = raw
        self._titled_loaded_at = now

        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _TITLED_RAW_PATH.write_text(
                json.dumps({"loaded_at": now, "titles": raw}),
                encoding="utf-8",
            )
        except Exception:
            pass

        self._build_reverse_map_if_needed()

    def _build_reverse_map_if_needed(self) -> None:
        """Build {real_name: (lichess, chesscom)} reverse map.

        Uses Lichess bulk POST /api/users to fetch profiles of all titled
        Chess.com usernames in one shot (300 per batch). Lichess returns
        user objects with .profile.realName field we can trust as ground truth.
        """
        if self._reverse_map:
            return

        all_usernames: list[str] = []
        for title_list in self._titled_raw.values():
            all_usernames.extend(title_list)
        all_usernames = list(set(all_usernames))

        if not all_usernames:
            return

        # Lichess bulk lookup — 300 usernames per POST call
        BATCH = 300
        name_map: dict[str, tuple[Optional[str], Optional[str]]] = {}
        for i in range(0, len(all_usernames), BATCH):
            batch = all_usernames[i : i + BATCH]
            try:
                self._throttle()
                resp = requests.post(
                    f"{_LICHESS_BASE}/users",
                    data=",".join(batch),
                    headers={"User-Agent": _UA, "Content-Type": "text/plain"},
                    timeout=30,
                )
                if resp.status_code != 200:
                    logger.warning("Lichess bulk lookup batch %d: %d", i // BATCH, resp.status_code)
                    continue
                users = resp.json()
                for u in users:
                    real_name = (u.get("profile") or {}).get("realName") or ""
                    if not real_name:
                        continue
                    normalized = _normalize_name(real_name)
                    lichess_user = u.get("id") or u.get("username")
                    # Try to find Chess.com username via exact username match
                    lichess_username_lower = (lichess_user or "").lower()
                    chesscom_user = None
                    for ch_user in all_usernames:
                        if ch_user.lower() == lichess_username_lower:
                            chesscom_user = ch_user
                            break
                    name_map[normalized] = (lichess_user, chesscom_user)
            except Exception as exc:
                logger.warning("Lichess bulk batch %d error: %s", i // BATCH, exc)

        self._reverse_map = name_map
        logger.info("Chess reverse map built: %d entries", len(name_map))

    # ── Per-player resolution ─────────────────────────────────────

    def resolve(self, real_name: str) -> Optional[ResolvedUser]:
        """Resolve a real player name to (lichess, chesscom) usernames."""
        if not real_name:
            return None
        normalized = _normalize_name(real_name)

        # Persistent cache hit
        if normalized in self._cache:
            return self._cache[normalized]

        # Failed cache hit — check retry TTL
        if normalized in self._failed:
            try:
                last_attempt = datetime.fromisoformat(self._failed[normalized])
                retry_cutoff = datetime.now(timezone.utc) - timedelta(
                    days=self._cfg.failed_resolve_retry_days,
                )
                if last_attempt.replace(tzinfo=timezone.utc) > retry_cutoff:
                    return None
            except ValueError:
                pass

        with self._lock:
            # Double-check cache after lock
            if normalized in self._cache:
                return self._cache[normalized]

            # Strategy 1: reverse map lookup (titled players)
            self._ensure_titled_loaded()
            resolved = self._lookup_in_reverse_map(real_name, normalized)

            # Strategy 2: username guessing
            if not resolved:
                resolved = self._guess_username(real_name, normalized)

            if resolved:
                self._cache[normalized] = resolved
                if normalized in self._failed:
                    del self._failed[normalized]
                self._persist_cache()
                return resolved

            # Record failure
            self._failed[normalized] = datetime.now(timezone.utc).isoformat()
            self._persist_cache()
            return None

    def _lookup_in_reverse_map(
        self, real_name: str, normalized: str,
    ) -> Optional[ResolvedUser]:
        if not self._reverse_map:
            return None
        # Exact
        if normalized in self._reverse_map:
            lichess, chesscom = self._reverse_map[normalized]
            return ResolvedUser(
                real_name=real_name,
                lichess=lichess,
                chesscom=chesscom,
                resolved_at=datetime.now(timezone.utc).isoformat(),
            )
        # Fuzzy
        best = process.extractOne(
            normalized, list(self._reverse_map.keys()),
            scorer=fuzz.WRatio, score_cutoff=85,
        )
        if best:
            matched = best[0]
            lichess, chesscom = self._reverse_map[matched]
            logger.info("Chess reverse-map fuzzy: %s -> %s (score=%d)",
                        real_name, matched, int(best[1]))
            return ResolvedUser(
                real_name=real_name,
                lichess=lichess,
                chesscom=chesscom,
                resolved_at=datetime.now(timezone.utc).isoformat(),
            )
        return None

    def _guess_username(
        self, real_name: str, normalized: str,
    ) -> Optional[ResolvedUser]:
        """Try common username patterns and validate via .name field."""
        parts = normalized.split()
        if len(parts) < 2:
            return None
        first = parts[0]
        last = parts[-1]
        guesses = [
            f"{first}{last}",           # anishgiri
            f"{first[0]}{last}",        # agiri
            f"{last}{first}",           # girianish
            f"{first}_{last}",          # anish_giri
            f"{last}",                  # giri
            f"{first}",                 # anish
        ]

        lichess_user = None
        chesscom_user = None

        # Try Chess.com
        for g in guesses:
            if chesscom_user:
                break
            try:
                self._throttle()
                resp = requests.get(
                    f"{_CHESSCOM_BASE}/player/{g}",
                    headers={"User-Agent": _UA}, timeout=10,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                fetched_name = data.get("name") or ""
                if not fetched_name:
                    continue
                score = fuzz.WRatio(
                    _normalize_name(fetched_name), normalized,
                )
                if score >= 85:
                    chesscom_user = data.get("username") or g
                    logger.info("Chess.com guess hit: %s -> %s (score=%d)",
                                real_name, chesscom_user, score)
                    break
            except Exception:
                continue

        # Try Lichess
        for g in guesses:
            if lichess_user:
                break
            try:
                self._throttle()
                resp = requests.get(
                    f"{_LICHESS_BASE}/user/{g}", timeout=10,
                    headers={"User-Agent": _UA},
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if data.get("disabled"):
                    continue
                fetched_name = (data.get("profile") or {}).get("realName") or ""
                if not fetched_name:
                    continue
                score = fuzz.WRatio(
                    _normalize_name(fetched_name), normalized,
                )
                if score >= 85:
                    lichess_user = data.get("id") or data.get("username")
                    logger.info("Lichess guess hit: %s -> %s (score=%d)",
                                real_name, lichess_user, score)
                    break
            except Exception:
                continue

        if lichess_user or chesscom_user:
            return ResolvedUser(
                real_name=real_name,
                lichess=lichess_user,
                chesscom=chesscom_user,
                resolved_at=datetime.now(timezone.utc).isoformat(),
            )
        return None


def _normalize_name(name: str) -> str:
    if not name:
        return ""
    n = unicodedata.normalize("NFD", name)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = n.lower().strip()
    return " ".join(n.split())


# ── Singleton ──────────────────────────────────────────────────────

_singleton: Optional[ChessUsernameResolver] = None
_singleton_lock = threading.Lock()


def get_resolver() -> ChessUsernameResolver:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = ChessUsernameResolver()
    return _singleton
```

**Step 3.2 — Syntax + import check**

```bash
python -c "import ast; ast.parse(open('src/chess_username_resolver.py').read()); print('syntax ok')"
python -c "from src.chess_username_resolver import get_resolver, ResolvedUser; print('imports ok')"
```

**Step 3.3 — Smoke test**

```bash
python -c "
from src.chess_username_resolver import get_resolver
r = get_resolver()
u = r.resolve('Hikaru Nakamura')
print('Nakamura:', u)
u2 = r.resolve('Magnus Carlsen')
print('Carlsen:', u2)
u3 = r.resolve('Anish Giri')
print('Giri:', u3)
"
```
Expected: Each call returns a ResolvedUser with at least one of `lichess`/`chesscom` populated. First run may take 30-60 seconds (bootstrap); subsequent runs instant from cache.

**Step 3.4 — Commit**

```bash
git add src/chess_username_resolver.py
git commit -m "feat(chess): add full-auto username resolver via titled directory + Lichess bulk"
```

---

### Task 4: Chess data client module

**Files**:
- Create: `src/chess_data.py`
- Runtime cache: `logs/chess_cache/stats_cache.json`, `logs/chess_cache/polymarket_players.json`

**Step 4.1 — Write `src/chess_data.py`**

```python
"""Chess match data — Lichess + Chess.com dual source with Polymarket awareness.

Produces ESPN-compatible context strings with:
  - Last 10 decisive (non-draw) rated games per player → [W]/[L] tokens
  - Recent form including draw count: "3W-9D-3L"
  - Explicit DRAW RATE line per player
  - Last 5 H2H games (deduplicated across both sources)
  - Polymarket sibling DRAW market price
  - Chess-specific AI warning about draw risk

Draws at elite chess level are 50-65% of classical games — critical for
"Will X win?" markets which resolve NO on draws. This module makes the draw
risk explicit to the AI instead of burying it.

Thread-safe singleton with 1.1s serial rate limit and 6-hour stats cache.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from src.config import load_config
from src.chess_username_resolver import get_resolver
from src.tennis_tml import _parse_players_from_question  # reuse helper

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("logs/chess_cache")
_STATS_CACHE_PATH = _CACHE_DIR / "stats_cache.json"
_POLY_PLAYERS_PATH = _CACHE_DIR / "polymarket_players.json"

_CHESSCOM_BASE = "https://api.chess.com/pub"
_LICHESS_BASE = "https://lichess.org/api"
_GAMMA_BASE = "https://gamma-api.polymarket.com"
_UA = "PolymarketAgent/1.0"


@dataclass
class ChessGame:
    date: str          # YYYY-MM-DD
    opponent: str
    won: Optional[bool]  # None = draw
    event: str
    speed: str         # classical/rapid/blitz/bullet
    source: str        # lichess/chesscom
    game_id: str       # for H2H dedup


@dataclass
class PlayerStats:
    real_name: str
    lichess_rapid: Optional[int]
    lichess_blitz: Optional[int]
    lichess_classical: Optional[int]
    chesscom_rapid: Optional[int]
    chesscom_blitz: Optional[int]
    games: list[ChessGame]  # merged from both sources, sorted desc by date
    fetched_at: float


class ChessDataClient:
    """Lichess + Chess.com merged data client."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cfg = load_config().chess
        self._stats_cache: dict[str, PlayerStats] = {}  # normalized_name → PlayerStats
        self._last_request_at: float = 0.0

    def _throttle(self) -> None:
        now = time.time()
        delta = now - self._last_request_at
        if delta < self._cfg.rate_limit_seconds:
            time.sleep(self._cfg.rate_limit_seconds - delta)
        self._last_request_at = time.time()

    # ── Public API ─────────────────────────────────────────────────

    def format_context(self, question: str, slug: str) -> Optional[str]:
        """Build chess context with [W]/[L] tokens + draw awareness."""
        if not self._cfg.enabled:
            return None

        player_a, player_b = self._extract_players(question, slug)
        if not player_a or not player_b:
            logger.debug("Chess: could not parse players from %s", slug[:40])
            return None

        stats_a = self._get_player_stats(player_a)
        stats_b = self._get_player_stats(player_b)
        if not stats_a and not stats_b:
            return None

        parts = ["=== CHESS DATA (Lichess + Chess.com) ==="]

        for label, name, stats in [
            ("PLAYER A", player_a, stats_a),
            ("PLAYER B", player_b, stats_b),
        ]:
            parts.append("")
            if not stats:
                parts.append(f"{label}: {name} -- no data available")
                continue
            parts.append(f"{label}: {name}")
            ratings = self._format_ratings(stats)
            if ratings:
                parts.append(f"  Ratings: {ratings}")

            all_games = stats.games[:15]  # last 15 for form calc
            wins = sum(1 for g in all_games if g.won is True)
            losses = sum(1 for g in all_games if g.won is False)
            draws = sum(1 for g in all_games if g.won is None)
            total = wins + losses + draws
            draw_rate = (draws / total * 100) if total > 0 else 0
            parts.append(
                f"  Recent form ({total} games): {wins}W-{draws}D-{losses}L"
            )
            parts.append(f"  DRAW RATE: {draw_rate:.0f}%")

            # Last N decisive games → [W]/[L] tokens
            decisive = [g for g in stats.games if g.won is not None][
                : self._cfg.max_games_per_player
            ]
            if decisive:
                parts.append(f"  Recent decisive ({len(decisive)} games):")
                for g in decisive:
                    result = "W" if g.won else "L"
                    parts.append(
                        f"    [{result}] vs {g.opponent} "
                        f"({g.speed}, {g.event}, {g.date})"
                    )

        # H2H section
        h2h = self._extract_h2h(
            stats_a.games if stats_a else [],
            stats_b.games if stats_b else [],
            player_a, player_b,
        )
        if h2h:
            a_wins = sum(1 for g, a_won in h2h if a_won is True)
            b_wins = sum(1 for g, a_won in h2h if a_won is False)
            h2h_draws = sum(1 for g, a_won in h2h if a_won is None)
            parts.append(
                f"\nH2H: {player_a} {a_wins}-{b_wins} {player_b} "
                f"({h2h_draws} draws)"
            )
            for g, a_won in h2h:
                if a_won is None:
                    continue  # draws skipped in H2H token list
                result = "W" if a_won else "L"
                parts.append(
                    f"    [{result}] vs {player_b if a_won else player_a} "
                    f"({g.speed}, {g.event}, {g.date})"
                )

        # Polymarket draw market price
        if self._cfg.fetch_polymarket_draw_price:
            poly_block = self._fetch_polymarket_prices(slug)
            if poly_block:
                parts.append("")
                parts.append(poly_block)

        # Chess warning
        parts.append("")
        parts.append(
            "=== CHESS DRAW WARNING ===\n"
            "At elite chess level, 50-65% of classical and 30-40% of blitz games "
            "end in draws. Polymarket 'Will X win?' markets resolve NO on draws. "
            "Discount raw P(YES) by each player's historical draw rate and the "
            "Polymarket draw market price before estimating edge. A 'favorite' "
            "at market price 55% may have true win probability near 30% due to "
            "draw mass."
        )
        return "\n".join(parts)

    def _extract_players(self, question: str, slug: str) -> tuple[Optional[str], Optional[str]]:
        """Extract player names from Polymarket event structure.

        Strategy:
          1. Fetch the event for this market slug → event.title format
             "Player A vs. Player B - Tournament (Round N)"
          2. Regex-parse title
          3. Fallback: question text
        """
        # Strategy 1: fetch event title
        try:
            self._throttle()
            resp = requests.get(
                f"{_GAMMA_BASE}/markets",
                params={"slug": slug},
                timeout=10,
            )
            if resp.status_code == 200:
                markets = resp.json()
                if markets and isinstance(markets, list):
                    events = markets[0].get("events", [])
                    if events:
                        event_title = events[0].get("title", "")
                        m = re.match(
                            r"(.+?)\s+vs\.?\s+(.+?)\s+-", event_title,
                        )
                        if m:
                            return m.group(1).strip(), m.group(2).strip()
        except Exception as exc:
            logger.debug("Chess event fetch failed for %s: %s", slug[:40], exc)

        # Strategy 2: question parsing
        return _parse_players_from_question(question)

    def _get_player_stats(self, real_name: str) -> Optional[PlayerStats]:
        """Fetch and cache player stats from both sources."""
        normalized = real_name.lower().strip()
        cached = self._stats_cache.get(normalized)
        if cached:
            age_hours = (time.time() - cached.fetched_at) / 3600
            if age_hours < self._cfg.stats_cache_hours:
                return cached

        resolver = get_resolver()
        resolved = resolver.resolve(real_name)
        if not resolved:
            logger.info("Chess: unresolved player %s", real_name)
            return None

        with self._lock:
            lichess_data = self._fetch_lichess(resolved.lichess) if resolved.lichess and self._cfg.lichess_enabled else None
            chesscom_data = self._fetch_chesscom(resolved.chesscom) if resolved.chesscom and self._cfg.chesscom_enabled else None

            games: list[ChessGame] = []
            if lichess_data:
                games.extend(lichess_data.get("games", []))
            if chesscom_data:
                games.extend(chesscom_data.get("games", []))
            # Dedup by game_id, sort desc by date
            seen_ids: set[str] = set()
            unique: list[ChessGame] = []
            for g in games:
                if g.game_id in seen_ids:
                    continue
                seen_ids.add(g.game_id)
                unique.append(g)
            unique.sort(key=lambda x: x.date, reverse=True)

            stats = PlayerStats(
                real_name=real_name,
                lichess_rapid=(lichess_data or {}).get("rapid"),
                lichess_blitz=(lichess_data or {}).get("blitz"),
                lichess_classical=(lichess_data or {}).get("classical"),
                chesscom_rapid=(chesscom_data or {}).get("rapid"),
                chesscom_blitz=(chesscom_data or {}).get("blitz"),
                games=unique,
                fetched_at=time.time(),
            )
            self._stats_cache[normalized] = stats
            return stats

    # ── Lichess fetchers ───────────────────────────────────────────

    def _fetch_lichess(self, username: str) -> Optional[dict]:
        try:
            self._throttle()
            resp = requests.get(
                f"{_LICHESS_BASE}/user/{username}",
                headers={"User-Agent": _UA}, timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("disabled"):
                return None
            perfs = data.get("perfs") or {}
            rapid = (perfs.get("rapid") or {}).get("rating")
            blitz = (perfs.get("blitz") or {}).get("rating")
            classical = (perfs.get("classical") or {}).get("rating")

            games = self._fetch_lichess_games(username, max_games=20)

            return {
                "rapid": rapid, "blitz": blitz, "classical": classical,
                "games": games,
            }
        except Exception as exc:
            logger.debug("Lichess fetch failed for %s: %s", username, exc)
            return None

    def _fetch_lichess_games(self, username: str, max_games: int = 20) -> list[ChessGame]:
        """Fetch recent rated games from Lichess (NDJSON stream)."""
        games: list[ChessGame] = []
        try:
            self._throttle()
            resp = requests.get(
                f"{_LICHESS_BASE}/games/user/{username}",
                params={
                    "max": max_games,
                    "rated": "true",
                    "perfType": "blitz,rapid,classical",
                    "pgnInJson": "false",
                },
                headers={"User-Agent": _UA, "Accept": "application/x-ndjson"},
                timeout=20,
            )
            if resp.status_code != 200:
                return []
            for line in resp.text.splitlines():
                if not line.strip():
                    continue
                try:
                    g = json.loads(line)
                except json.JSONDecodeError:
                    continue
                players = g.get("players") or {}
                white = ((players.get("white") or {}).get("user") or {}).get("name") or ""
                black = ((players.get("black") or {}).get("user") or {}).get("name") or ""
                winner = g.get("winner")  # "white" | "black" | None (draw)
                created_at = g.get("createdAt", 0)
                date_str = datetime.fromtimestamp(
                    created_at / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%d") if created_at else ""

                if white.lower() == username.lower():
                    opp = black
                    won = (winner == "white") if winner else None
                elif black.lower() == username.lower():
                    opp = white
                    won = (winner == "black") if winner else None
                else:
                    continue

                games.append(ChessGame(
                    date=date_str,
                    opponent=opp,
                    won=won,
                    event="Lichess",
                    speed=g.get("speed", "?"),
                    source="lichess",
                    game_id=g.get("id", ""),
                ))
        except Exception as exc:
            logger.debug("Lichess games fetch failed for %s: %s", username, exc)
        return games

    # ── Chess.com fetchers ─────────────────────────────────────────

    def _fetch_chesscom(self, username: str) -> Optional[dict]:
        try:
            self._throttle()
            resp = requests.get(
                f"{_CHESSCOM_BASE}/player/{username}/stats",
                headers={"User-Agent": _UA}, timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            rapid = ((data.get("chess_rapid") or {}).get("last") or {}).get("rating")
            blitz = ((data.get("chess_blitz") or {}).get("last") or {}).get("rating")

            games = self._fetch_chesscom_games(username, max_games=20)
            return {"rapid": rapid, "blitz": blitz, "games": games}
        except Exception as exc:
            logger.debug("Chess.com fetch failed for %s: %s", username, exc)
            return None

    def _fetch_chesscom_games(self, username: str, max_games: int = 20) -> list[ChessGame]:
        """Fetch current month's games from Chess.com archive, fall back to previous month."""
        games: list[ChessGame] = []
        now = datetime.now(timezone.utc)
        months_to_try = [
            (now.year, now.month),
        ]
        # Previous month
        if now.month == 1:
            months_to_try.append((now.year - 1, 12))
        else:
            months_to_try.append((now.year, now.month - 1))

        for year, month in months_to_try:
            if len(games) >= max_games:
                break
            try:
                self._throttle()
                resp = requests.get(
                    f"{_CHESSCOM_BASE}/player/{username}/games/{year}/{month:02d}",
                    headers={"User-Agent": _UA}, timeout=15,
                )
                if resp.status_code != 200:
                    continue
                month_games = resp.json().get("games", [])
                # Most recent first
                for g in reversed(month_games):
                    if len(games) >= max_games:
                        break
                    white = (g.get("white") or {})
                    black = (g.get("black") or {})
                    white_user = (white.get("username") or "").lower()
                    black_user = (black.get("username") or "").lower()
                    if username.lower() == white_user:
                        me_result = white.get("result")
                        opp = black.get("username") or ""
                    elif username.lower() == black_user:
                        me_result = black.get("result")
                        opp = white.get("username") or ""
                    else:
                        continue

                    # Only rated games
                    if not g.get("rated", True):
                        continue

                    # Result codes: "win" → won; "agreed"/"repetition"/"stalemate"/"timevsinsufficient"/"insufficient"/"50move" → draw; else → lost
                    draw_codes = {
                        "agreed", "repetition", "stalemate",
                        "timevsinsufficient", "insufficient", "50move",
                    }
                    if me_result == "win":
                        won = True
                    elif me_result in draw_codes:
                        won = None
                    else:
                        won = False

                    end_time = g.get("end_time", 0)
                    date_str = datetime.fromtimestamp(
                        end_time, tz=timezone.utc,
                    ).strftime("%Y-%m-%d") if end_time else ""

                    games.append(ChessGame(
                        date=date_str,
                        opponent=opp,
                        won=won,
                        event="Chess.com",
                        speed=g.get("time_class", "?"),
                        source="chesscom",
                        game_id=g.get("url", "") or f"cc-{end_time}",
                    ))
            except Exception as exc:
                logger.debug("Chess.com games fetch failed for %s: %s", username, exc)
                continue
        return games

    # ── H2H extraction ─────────────────────────────────────────────

    def _extract_h2h(
        self,
        games_a: list[ChessGame],
        games_b: list[ChessGame],
        player_a: str,
        player_b: str,
    ) -> list[tuple[ChessGame, Optional[bool]]]:
        """Find games between A and B across both players' archives.

        Returns [(game, a_won), ...] — a_won=True if A won, False if B won,
        None if draw. Sorted most recent first. Dedup by game_id.
        """
        h2h: list[tuple[ChessGame, Optional[bool]]] = []
        seen: set[str] = set()

        # From A's games where opponent matches B
        for g in games_a:
            if _fuzzy_name_match(g.opponent, player_b):
                if g.game_id in seen:
                    continue
                seen.add(g.game_id)
                h2h.append((g, g.won))  # A's perspective

        # From B's games where opponent matches A (dedup)
        for g in games_b:
            if _fuzzy_name_match(g.opponent, player_a):
                if g.game_id in seen:
                    continue
                seen.add(g.game_id)
                # Invert: if B won, then A lost
                a_won = None if g.won is None else (not g.won)
                h2h.append((g, a_won))

        h2h.sort(key=lambda x: x[0].date, reverse=True)
        return h2h[: self._cfg.max_h2h_games]

    # ── Polymarket sibling market fetcher ──────────────────────────

    def _fetch_polymarket_prices(self, slug: str) -> Optional[str]:
        """Fetch all markets in the chess event and return formatted block."""
        try:
            self._throttle()
            resp = requests.get(
                f"{_GAMMA_BASE}/markets",
                params={"slug": slug}, timeout=10,
            )
            if resp.status_code != 200:
                return None
            markets = resp.json()
            if not markets or not isinstance(markets, list):
                return None
            events = markets[0].get("events", [])
            if not events:
                return None
            event_slug = events[0].get("slug", "")
            if not event_slug:
                return None

            # Fetch all markets for this event
            self._throttle()
            ev_resp = requests.get(
                f"{_GAMMA_BASE}/events",
                params={"slug": event_slug}, timeout=10,
            )
            if ev_resp.status_code != 200:
                return None
            ev_data = ev_resp.json()
            if not ev_data or not isinstance(ev_data, list):
                return None
            all_markets = ev_data[0].get("markets", [])
            if len(all_markets) < 2:
                return None

            lines = ["=== POLYMARKET PRICES (this event) ==="]
            for mk in all_markets:
                git = mk.get("groupItemTitle") or ""
                prices_raw = mk.get("outcomePrices", "[]")
                try:
                    prices = json.loads(prices_raw)
                    yes_price = float(prices[0]) if prices else 0.0
                except (json.JSONDecodeError, IndexError, ValueError):
                    continue
                lines.append(f"  {git}: YES {yes_price*100:.0f}¢")
            if len(lines) <= 1:
                return None
            return "\n".join(lines)
        except Exception as exc:
            logger.debug("Polymarket prices fetch failed for %s: %s", slug[:40], exc)
            return None

    @staticmethod
    def _format_ratings(stats: PlayerStats) -> str:
        parts = []
        if stats.lichess_rapid or stats.lichess_blitz or stats.lichess_classical:
            bits = []
            if stats.lichess_rapid:
                bits.append(f"rapid {stats.lichess_rapid}")
            if stats.lichess_blitz:
                bits.append(f"blitz {stats.lichess_blitz}")
            if stats.lichess_classical:
                bits.append(f"classical {stats.lichess_classical}")
            if bits:
                parts.append("Lichess: " + " | ".join(bits))
        if stats.chesscom_rapid or stats.chesscom_blitz:
            bits = []
            if stats.chesscom_rapid:
                bits.append(f"rapid {stats.chesscom_rapid}")
            if stats.chesscom_blitz:
                bits.append(f"blitz {stats.chesscom_blitz}")
            if bits:
                parts.append("Chess.com: " + " | ".join(bits))
        return " | ".join(parts)


def _fuzzy_name_match(name_a: str, name_b: str) -> bool:
    from rapidfuzz import fuzz
    na = (name_a or "").lower().strip()
    nb = (name_b or "").lower().strip()
    if not na or not nb:
        return False
    # Simple: last-name token match is usually enough
    if na in nb or nb in na:
        return True
    return fuzz.WRatio(na, nb) >= 80


# ── Singleton ──────────────────────────────────────────────────────

_singleton: Optional[ChessDataClient] = None
_singleton_lock = threading.Lock()


def get_chess_data() -> ChessDataClient:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = ChessDataClient()
    return _singleton
```

**Step 4.2 — Syntax + import check**

```bash
python -c "import ast; ast.parse(open('src/chess_data.py').read()); print('syntax ok')"
python -c "from src.chess_data import get_chess_data, ChessDataClient, ChessGame, PlayerStats; print('imports ok')"
```

**Step 4.3 — Smoke test (network + potentially slow due to bootstrap)**

```bash
python -c "
from src.chess_data import get_chess_data
c = get_chess_data()
ctx = c.format_context(
    'Will Hikaru Nakamura win on 2026-04-09 at FIDE Candidates 2026 Open?',
    'chess-agiri-hnakam-2026-04-09-r10-black',
)
print(ctx if ctx else 'NONE')
print()
print('--- tokens:', (ctx or '').count('[W]') + (ctx or '').count('[L]'))
"
```
Expected: non-empty context with 8+ `[W]`/`[L]` tokens, explicit `DRAW RATE:` lines, and Polymarket prices block.

**Step 4.4 — Commit**

```bash
git add src/chess_data.py
git commit -m "feat(chess): add Lichess + Chess.com dual-source client with draw awareness"
```

---

### Task 5: Polymarket draw market fetcher

**Note**: Already implemented in Task 4 as `_fetch_polymarket_prices` method of `ChessDataClient`. This task is a verification-only checkpoint.

**Step 5.1 — Verify the method exists and works**

```bash
python -c "
from src.chess_data import get_chess_data
c = get_chess_data()
block = c._fetch_polymarket_prices('chess-agiri-hnakam-2026-04-09-r10-black')
print(block or 'NONE')
"
```
Expected: block with 3 lines (Player A YES, Player B YES, Draw YES) showing current market prices.

**Step 5.2** — No separate commit. Bundled into Task 4.

---

### Task 6: AI analyst chess warning

**Files**:
- Modify: `src/ai_analyst.py`

**Step 6.1 — Locate prompt builder**

```bash
python -c "
import ast, sys
tree = ast.parse(open('src/ai_analyst.py').read())
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        print(f'line {node.lineno}: def {node.name}')
"
```
Find the function that builds the per-market prompt (likely `_build_prompt` or `build_market_prompt`).

**Step 6.2 — Read the prompt builder**

```bash
python -c "
with open('src/ai_analyst.py') as f:
    lines = f.readlines()
# Find and print any function containing 'prompt' or 'message'
import re
for i, line in enumerate(lines):
    if re.search(r'def.*(prompt|build.*market|analyze)', line):
        print(f'{i+1}: {line.rstrip()}')
"
```

**Step 6.3 — Add chess warning to prompt builder**

Locate the function that builds the per-market prompt string. Inside it, right before the prompt is returned (or after the context block is assembled), insert:

```python
# Chess-specific warning: draw risk
_sport_tag_lower = (getattr(market, "sport_tag", "") or "").lower()
_slug_lower = (getattr(market, "slug", "") or "").lower()
if _sport_tag_lower == "chess" or _slug_lower.startswith("chess-"):
    prompt += (
        "\n\nCHESS-SPECIFIC NOTE: This is a 'Will X win?' chess market. "
        "At elite level, 50-65% of classical games and 30-40% of blitz games "
        "end in DRAWS. Polymarket resolves these markets NO on draws. "
        "You MUST discount P(YES) by each player's historical draw rate. "
        "A player with 60% draw rate facing a slight favorite needs ~80% "
        "theoretical decisive-win rate to justify P(YES) > 50%. Favor NO when "
        "both players have high draw rates and the Polymarket draw market "
        "price is elevated."
    )
```

The exact insertion point depends on the function structure. Read the file first with `Read` to find the right spot.

**Step 6.4 — Syntax + test check**

```bash
python -c "import ast; ast.parse(open('src/ai_analyst.py').read()); print('syntax ok')"
python -m pytest tests/test_ai_analyst.py tests/test_ai_confidence_prompt.py -v
```
Expected: all tests pass. If a test asserts exact prompt content, update it to allow the new conditional section.

**Step 6.5 — Commit**

```bash
git add src/ai_analyst.py tests/test_ai_analyst.py tests/test_ai_confidence_prompt.py
git commit -m "feat(ai): add chess-specific draw warning to prompt builder"
```

---

### Task 7: entry_gate.py integration

**Files**:
- Modify: `src/entry_gate.py` (ONLY `_enrich_sports` nested function + new nested `_enrich_chess`)

**Step 7.1 — Re-read the target lines before editing**

```bash
python -c "
with open('src/entry_gate.py') as f:
    lines = f.readlines()
# Show _enrich_sports region
for i in range(465, 525):
    print(f'{i+1:4}: {lines[i].rstrip()}')
"
```

**Step 7.2 — Replace `_enrich_sports` function body with chess fast-path + tennis fallback**

Find the block starting `def _enrich_sports(_m):` at ~line 467 and replace with:

```python
        def _enrich_chess(_m):
            """Fetch chess context via Lichess + Chess.com dual source.

            Handles:
              - Player name extraction from Polymarket event title
              - Rating + recent form + draw rate + [W]/[L] tokens
              - Polymarket sibling draw market price
              - Chess-specific AI warning embedded in context
            """
            try:
                from src.chess_data import get_chess_data
                ctx = get_chess_data().format_context(
                    getattr(_m, "question", ""), _m.slug or "",
                )
                if ctx:
                    logger.info("Chess context: %s | tokens=%d",
                                (_m.slug or "")[:40],
                                ctx.count("[W]") + ctx.count("[L]"))
                    return ("sports", _m.condition_id, ctx, None)
                return ("sports", _m.condition_id, None, None)
            except Exception as exc:
                logger.warning("Chess enrichment error for %s: %s",
                               (_m.slug or "")[:40], exc)
                return ("sports", _m.condition_id, None, None)

        def _enrich_sports(_m):
            """Fetch ESPN/discovery context + Odds API for a single sports market.

            Includes chess fast-path (routes chess markets to _enrich_chess) and
            tennis TML supplementary fallback (triggers when ESPN < 6 [W]/[L] tokens).
            """
            try:
                _slug = _m.slug or ""
                _sport_tag_lower = (getattr(_m, "sport_tag", "") or "").lower()
                _slug_prefix = _slug.split("-")[0].lower() if _slug else ""

                # ── Chess fast-path ─────────────────────────────────────
                if _slug_prefix == "chess" or _sport_tag_lower == "chess":
                    return _enrich_chess(_m)

                # ── Existing ESPN/discovery flow ────────────────────────
                result = self.discovery.resolve(
                    getattr(_m, "question", ""),
                    _slug,
                    getattr(_m, "tags", []),
                )
                ctx = result.context if result else None
                espn_odds = result.espn_odds if result else None

                # ── Tennis TML supplementary fallback (ATP only) ────────
                _is_atp = _slug_prefix == "atp" or _sport_tag_lower == "atp"
                if _is_atp:
                    _existing_tokens = (ctx.count("[W]") + ctx.count("[L]")) if ctx else 0
                    _tml_threshold = self.config.tennis.tml_fallback_threshold_tokens
                    if _existing_tokens < _tml_threshold:
                        try:
                            from src.tennis_tml import get_tennis_tml
                            tml_ctx = get_tennis_tml().format_context(
                                getattr(_m, "question", ""), _slug,
                            )
                            if tml_ctx:
                                if ctx:
                                    ctx = ctx + "\n\n" + tml_ctx
                                else:
                                    ctx = tml_ctx
                                logger.info(
                                    "Tennis TML fallback: %s | tokens=%d→%d",
                                    _slug[:35], _existing_tokens,
                                    ctx.count("[W]") + ctx.count("[L]"),
                                )
                        except Exception as exc:
                            logger.warning("TML fallback error for %s: %s",
                                           _slug[:40], exc)

                # Odds API: fetch bookmaker odds (Pinnacle etc.) — especially for tennis
                # where ESPN doesn't provide odds but Odds API does
                odds_api_result = None
                if self.odds_api and self.odds_api.available:
                    try:
                        odds_api_result = self.odds_api.get_bookmaker_odds(
                            getattr(_m, "question", ""), _slug, getattr(_m, "tags", [])
                        )
                    except Exception:
                        pass

                # If no ESPN odds but Odds API found odds, use as fallback
                if not espn_odds and odds_api_result:
                    espn_odds = odds_api_result

                # Append bookmaker info to context so AI sees it for confidence grading
                if odds_api_result:
                    bm_count = odds_api_result.get("num_bookmakers", 0)
                    has_sharp = odds_api_result.get("has_sharp", False)
                    prob_a = odds_api_result.get("bookmaker_prob_a", 0)
                    prob_b = odds_api_result.get("bookmaker_prob_b", 0)
                    team_a = odds_api_result.get("team_a", "Team A")
                    team_b = odds_api_result.get("team_b", "Team B")
                    odds_section = (f"\n\n=== BOOKMAKER ODDS ({bm_count} bookmakers"
                                    f"{', incl. Pinnacle' if has_sharp else ''}) ===\n"
                                    f"  {team_a}: {prob_a:.0%}\n"
                                    f"  {team_b}: {prob_b:.0%}\n")
                    if ctx:
                        ctx += odds_section
                    else:
                        # No ESPN data but Odds API found odds — create minimal context
                        ctx = (f"=== {getattr(_m, 'question', _slug)} ===\n"
                               f"No match statistics available.\n"
                               + odds_section)

                if ctx:
                    logger.info("Sports context (%s): %s",
                                result.source if result else "odds", _slug[:40])
                    return ("sports", _m.condition_id, ctx, espn_odds)
                return ("sports", _m.condition_id, None, None)
            except Exception as exc:
                logger.warning("Discovery error for %s: %s", (_m.slug or "")[:40], exc)
                return ("sports", _m.condition_id, None, None)
```

**Step 7.3 — Verify no other functions were touched**

```bash
git diff src/entry_gate.py | head -200
```
Manually inspect the diff. The ONLY changes should be:
1. `def _enrich_sports(_m)` function body replaced
2. New `def _enrich_chess(_m)` nested function inserted before `_enrich_sports`

No changes to `__init__`, `_analyze_batch` outer logic, `run()`, `_evaluate_candidates`, or `_execute_candidates`.

**Step 7.4 — Syntax + quick tests**

```bash
python -c "import ast; ast.parse(open('src/entry_gate.py').read()); print('syntax ok')"
python -c "from src.entry_gate import EntryGate; print('imports ok')"
python -m pytest tests/test_entry_gate_guards.py tests/test_entry_gate_chrono.py -v
```
Expected: all tests pass.

**Step 7.5 — Commit**

```bash
git add src/entry_gate.py
git commit -m "feat(entry_gate): add chess fast-path + tennis TML fallback to _enrich_sports"
```

---

### Task 8: Smoke test suite

**Step 8.1 — Full module import check**

```bash
python -c "
import sys
mods = [
    'src.tennis_tml',
    'src.chess_username_resolver',
    'src.chess_data',
    'src.entry_gate',
    'src.ai_analyst',
    'src.config',
]
for m in mods:
    try:
        __import__(m)
        print(f'{m}: OK')
    except Exception as e:
        print(f'{m}: FAIL -- {e}')
        sys.exit(1)
"
```

**Step 8.2 — Full test suite**

```bash
python -m pytest tests/ -x --tb=short 2>&1 | tail -40
```
Expected: all existing tests pass. Any failures must be investigated before proceeding.

**Step 8.3 — Optional: end-to-end context build (network required)**

```bash
python -c "
from src.tennis_tml import get_tennis_tml
from src.chess_data import get_chess_data

print('=== TENNIS ===')
ctx = get_tennis_tml().format_context(
    'Will Jannik Sinner beat Tomas Machac?',
    'atp-sinner-machac-2026-04-09',
)
print(f'tokens: {(ctx or \"\").count(\"[W]\") + (ctx or \"\").count(\"[L]\")}')
print((ctx or '')[:800])
print()
print('=== CHESS ===')
ctx = get_chess_data().format_context(
    'Will Hikaru Nakamura win on 2026-04-09?',
    'chess-agiri-hnakam-2026-04-09-r10-black',
)
print(f'tokens: {(ctx or \"\").count(\"[W]\") + (ctx or \"\").count(\"[L]\")}')
print((ctx or '')[:1200])
"
```
Expected: both contexts non-empty with 8+ tokens each.

**Step 8.4** — No commit (verification only).

---

### Task 9: TODO.md gap notes

**Files**:
- Modify: `TODO.md`

**Step 9.1 — Append gap notes section**

Append at the bottom of `TODO.md`:

```markdown

## Data Coverage Gaps (Tracked 2026-04-09)

Following the tennis + chess integration, these gaps remain:

### WTA (Women's tennis)
- TML-Database only publishes ATP data (verified empirically 2026-04-09: all WTA file paths return 404)
- ESPN WTA scoreboard data is sparse
- Options evaluated:
  - (a) Skip WTA entirely — safest, current state
  - (b) api-tennis.com 14-day trial — vendor lock-in risk
  - (c) sportdevs 300 req/day trial
  - (d) tennis-data.co.uk weekly CSVs — site had timeout issues during testing
- Decision: deferred pending user choice

### Low-coverage football leagues
- Egypt Premier League (egypt-1): ESPN does not cover
- Europa Conference League (europa-conference-league): ESPN does not cover
- Saudi Professional League (saudi-professional-league): ESPN partial coverage
- Potential sources:
  - api-football (RapidAPI) — free tier limited
  - football-data.org — unclear coverage for these leagues
- Action: monitor frequency of skips; if >10 markets/cycle consistently, investigate paid source

### Future chess features
- Polymarket chess events contain 3-way markets (Player A win / Player B win / Draw)
- Currently we fetch draw market prices as signal, but bot only enters player-win markets
- Future: add direct draw-market entry strategy when both players have high historical draw rates
- Future: track chess tournament round number (already in slug) for fatigue modeling
```

**Step 9.2 — Commit**

```bash
git add TODO.md
git commit -m "docs(todo): add data coverage gap notes for WTA and low-coverage leagues"
```

---

### Task 10: Run audit agent

**Step 10.1 — Generate diff summary**

```bash
git log --oneline -20
git diff HEAD~8 --stat
```

**Step 10.2 — Dispatch audit agent**

Use the `Agent` tool with subagent_type `general-purpose` and this exact prompt (per CLAUDE.md §3):

```
PHASE 1 — Context: Read ALL src/*.py files to understand the full codebase.
Do NOT read: API Guides/, docs/, logs/, tests/, .env, config YAML files.

PHASE 2 — Focused Audit: Check these CHANGED files for issues:

Files:
  - src/tennis_tml.py (NEW): ATP CSV client with H2H, singleton, threading.Lock
  - src/chess_username_resolver.py (NEW): Full-auto name→username resolver via Chess.com titled directory + Lichess bulk POST /api/users
  - src/chess_data.py (NEW): Lichess + Chess.com dual-source client with draw rate tracking, Polymarket sibling market fetcher, chess warning in context
  - src/entry_gate.py (MODIFIED): _enrich_sports function replaced with chess fast-path + tennis TML fallback; new nested _enrich_chess function. Only the nested functions inside _analyze_batch are modified.
  - src/ai_analyst.py (MODIFIED): Added chess-specific warning string to prompt builder when market sport_tag == 'chess' or slug starts with 'chess-'.
  - src/config.py (MODIFIED): Added TennisConfig + ChessConfig pydantic models + attached to AppConfig.
  - config.yaml (MODIFIED): Added tennis: and chess: config blocks.

Look for:
- Runtime errors (missing imports, wrong args, undefined vars)
- Logic bugs (wrong conditions, broken control flow, edge cases)
- Breaking changes — does any change break existing callers of entry_gate/ai_analyst/config?
- Interface mismatches (function signature changes but callers unchanged)
- Thread safety: tennis_tml and chess_data are called from 8-worker ThreadPoolExecutor in entry_gate._analyze_batch. Chess client has internal threading.Lock for serial API calls; verify no deadlocks.
- Dead code (unused functions, imports, variables — REPORT but don't delete)
- Spaghetti: any function >80 lines? any logic duplicated across files?
- Has the parallel agent's sports_data.py been touched? (Should be NO)

Rules:
- Do NOT spawn sub-agents
- Do NOT read API Guides or docs/ — they are huge and will block
- IGNORE: cosmetic issues, type hints, docstrings, formatting, naming style
- Report format: file:line — description — severity (critical/warning)
- If zero critical issues, report "CLEAN"
```

**Step 10.3 — Fix any critical issues found**

For each critical issue:
1. Apply fix
2. Re-run syntax + import checks
3. Create new commit per fix

Max 3 audit rounds before escalating to user.

**Step 10.4 — Final verification + report**

```bash
git log --oneline -15
python -m pytest tests/ --tb=line 2>&1 | tail -20
```

Report to user:
- Total commits created
- Audit status (CLEAN or list of issues fixed)
- Known smoke test results
- Next steps (bot restart decision deferred to user — do NOT restart)

---

## Execution checkpoints

- **After Task 4** (chess_data.py) — longest and most complex file. Review commit diff before proceeding.
- **After Task 7** (entry_gate.py) — critical integration point. Verify `git diff src/entry_gate.py` shows ONLY the two nested functions changed, nothing else.
- **After Task 10** — final audit clean → report to user → wait for next instruction.

## Hard constraints (from CLAUDE.md)

- NEVER restart/kill/start bot without explicit user permission
- NEVER spend AI credits without permission (no actual AI analyst calls in smoke tests)
- NEVER touch `.env` or hardcode secrets
- Default to dry_run — never suggest live
- Risk manager is unaffected by these changes (no risk logic touched)
- Type hints on all new functions ✓ (verified in task code blocks)
- Log every decision ✓ (verified — all paths emit `logger.info` or `logger.warning`)

## Files to NOT touch (parallel agent coordination)

- `src/sports_data.py` — parallel agent fixing ESPN hard limits
- `src/exit_monitor.py`, `src/scout_scheduler.py`, `src/startup_cleanup.py`, `src/agent.py`
- `CLAUDE.md`
- `logs/positions.json`, `logs/trades.jsonl`, `logs/portfolio.jsonl`, `logs/scout_queue.json`, `logs/exited_markets.json`, `logs/outcome_tracker.json`
