# Matching System v2 — Design Spec

## Problem

Market-to-scout matching rate: **75/1929 = 3.9%**. Root causes:

1. **Bug**: `scout_scheduler.run_scout()` fetches `abbrev_a/b` and `short_a/b` from ESPN/PandaScore but **never saves them** to the scout queue entry dict (L371-387 missing these fields). All 218 entries have empty abbreviations.
2. **Three separate matching systems** with different logic, none complete:
   - `market_matcher.py` — 3-layer (abbrev→short→fuzzy), but abbrevs always empty
   - `scout_scheduler.py` — substring + 6-char prefix, naive
   - `team_matcher.py` — alias + token + fuzzy, used by odds_api only
3. **Polymarket's own `/teams` API** (abbreviation, alias, league) not used for matching.

## Solution

Replace all three with a single `src/matching/` package. Clean pipeline, no dead code.

## Architecture

### New Files

```
src/matching/
  __init__.py          — public API: match_markets(markets, scout_queue) -> list[MatchResult]
  slug_parser.py       — Polymarket slug -> (sport_code, abbrev_a, abbrev_b)
  team_resolver.py     — abbreviation/alias -> canonical name, multi-source + disk cache
  pair_matcher.py      — compare two team pairs, 4-layer confidence scoring
  sport_classifier.py  — market -> sport category (slug prefix, tags, question keywords)
```

### Deleted Files

| File | Reason |
|------|--------|
| `src/market_matcher.py` | Replaced by `src/matching/` |
| `src/team_matcher.py` | Replaced by `pair_matcher.py` + `team_resolver.py` |

### Modified Files

| File | Change |
|------|--------|
| `src/scout_scheduler.py` | (1) Add abbrev_a/b, short_a/b to entry dict. (2) Delete `match_market()` and `match_markets_batch()` methods. |
| `src/agent.py` or caller | Import from `src.matching` instead of `src.market_matcher` |
| `src/odds_api.py` | Import from `src.matching.pair_matcher` instead of `src.team_matcher` |
| Any other file importing market_matcher or team_matcher | Update imports |

## Pipeline

```
Market (question, slug, tags)
  │
  ├─ 1. sport_classifier  →  sport category (basketball, esports, soccer, ...)
  │     Source: slug prefix mapping + tag hints + question keywords
  │     Filters: only match within same sport category
  │
  ├─ 2. slug_parser        →  (sport_code, abbrev_a, abbrev_b)
  │     Pattern: "{sport}-{abbrev_a}-{abbrev_b}-{date}" for moneyline markets
  │     Handles: variable token count, date at end, sport prefix
  │
  ├─ 3. team_resolver      →  canonical team names from abbreviations
  │     Priority: Polymarket /teams > ESPN /teams > PandaScore /teams > static dict
  │     Cache: logs/team_resolver_cache.json, 24h TTL, background refresh
  │
  └─ 4. pair_matcher        →  match resolved names against scout entry names
        L1: exact canonical match           (confidence 1.0)
        L2: token overlap (meaningful)      (confidence 0.90)
        L3: abbreviation in slug tokens     (confidence 0.85)
        L4: rapidfuzz token_sort ≥ 80       (confidence 0.80)
        Both teams must match. Tries normal + swapped order.
```

## Component Details

### slug_parser.py

Input: `"nba-lal-bos-2026-04-05"`
Output: `SlugParts(sport="nba", tokens=["lal", "bos"], date="2026-04-05")`

Logic:
- Split slug by `-`
- First token = sport code (if in known sport codes from Polymarket /sports)
- Last 3 tokens = date (YYYY-MM-DD) if they look like a date
- Middle tokens = team abbreviations
- For esports: `"cs2-hero-nip-2026-04-03"` → sport="cs2", tokens=["hero", "nip"]

### team_resolver.py

Single class `TeamResolver` replacing both `AliasStore` and `TEAM_ALIASES`:

```python
class TeamResolver:
    def resolve(self, token: str) -> str | None:
        """Token -> canonical lowercase name, or None if unknown."""

    def resolve_pair(self, token_a: str, token_b: str) -> tuple[str|None, str|None]:
        """Resolve both tokens, using sport context for disambiguation."""

    def refresh(self):
        """Background refresh from 3 APIs. Called on init + every 24h."""
```

Data sources (fetched in refresh):
1. **Polymarket `GET /teams`** — `abbreviation` and `alias` fields → canonical `name`
2. **ESPN `/teams` endpoints** — `abbreviation` and `shortDisplayName` → `displayName`
3. **PandaScore `/teams` endpoints** — `acronym` → `name`
4. **Static fallback** — merged from current TEAM_ALIASES + STATIC_ABBREVS

Cache file: `logs/team_resolver_cache.json`

### pair_matcher.py

```python
def match_pair(
    market_names: tuple[str, str],     # resolved from slug or question
    entry_names: tuple[str, str],      # from scout entry
    entry_abbrevs: tuple[str, str],    # from scout entry (ESPN/PandaScore)
    slug_tokens: set[str],             # raw slug tokens
) -> tuple[bool, float]:              # (is_match, confidence)
```

Four layers, short-circuit on first match:
1. **Exact canonical**: both names match after normalization + alias resolution
2. **Token overlap**: meaningful token overlap ≥ 50% of smaller set
3. **Abbreviation**: both entry abbrevs found in slug tokens
4. **Fuzzy**: rapidfuzz token_sort_ratio ≥ 80 for both teams

### sport_classifier.py

```python
def classify(slug: str, tags: list[str], question: str) -> str | None:
```

Uses the 170 sport codes from Polymarket `/sports` (cached).
Slug prefix is primary signal. Tags and question keywords are fallback.
Returns sport category string or None.

## scout_scheduler.py Changes

### Bug fix — add fields to entry dict

In `run_scout()` and `run_daily_listing()`, the entry dict (currently L371-387) needs:

```python
"abbrev_a": match.get("abbrev_a", ""),
"abbrev_b": match.get("abbrev_b", ""),
"short_a": match.get("short_a", ""),
"short_b": match.get("short_b", ""),
```

### Delete matching methods

Remove `match_market()` (L406-445) and `match_markets_batch()` (L284-329).
These are replaced by `src.matching.match_markets()`.

## Integration Point

The caller (likely `agent.py` or `entry_gate.py`) currently does:

```python
from src.market_matcher import match_batch, AliasStore
matched = match_batch(markets, scout_queue, alias_store)
```

New:

```python
from src.matching import match_markets
matched = match_markets(markets, scout_queue)
```

`match_markets()` internally creates/reuses TeamResolver (singleton with background refresh).

## What This Does NOT Change

- Market discovery (`market_scanner.py`) — untouched
- Scout data collection (`scout_scheduler.run_scout()`) — only adds missing fields
- Entry gate logic — untouched, receives same MatchResult format
- Risk manager, AI analyst, executor — untouched
- odds_api.py team matching — migrates to `pair_matcher` but same logic

## Expected Impact

Current: 75/1929 matched (3.9%)
- Bug fix alone (abbrevs): ~150-200 matches (Layer 1 + Layer 2 activate)
- Polymarket /teams resolver: +50-100 more (slug abbreviations resolve correctly)
- Target: 250-350 matches (~15-20% of 1929)
- Remaining gap: markets for sports we don't scout (cricket, rugby, etc.) — Phase B

## Implementation Sessions

- **Session 1**: `src/matching/` package — slug_parser, team_resolver, pair_matcher, sport_classifier, __init__.py
- **Session 2**: Integration — scout_scheduler bug fix, delete old files, update imports, wire into agent
- **Session 3**: Test with live data, tune thresholds if needed
