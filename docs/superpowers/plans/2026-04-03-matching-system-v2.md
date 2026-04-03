# Matching System v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 3 broken matching systems with one clean pipeline, raising match rate from 3.9% to 15-20%+.

**Architecture:** Single `src/matching/` package with 4 components: slug_parser, team_resolver, pair_matcher, sport_classifier. Entry point is `match_markets()`. Replaces `market_matcher.py` and `team_matcher.py`.

**Tech Stack:** Python 3.11, rapidfuzz, requests, Pydantic (existing), pytest

**Key context:**
- `entry_gate.py:337` calls `matcher_match_batch(markets, scout._queue, alias_store)` — this is the main integration point
- `sports_data.py`, `esports_data.py`, `vlr_data.py`, `odds_api.py` use `match_team()` and `find_best_event_match()` from `team_matcher.py` — these must remain available
- `MarketData` model (src/models.py) has: `question`, `slug`, `tags`, `sport_tag`, `condition_id`
- Scout queue entries have: `team_a`, `team_b`, `abbrev_a` (currently EMPTY — bug), `abbrev_b` (EMPTY), `short_a` (EMPTY), `short_b`, `sport`, `league`, `is_esports`, `match_time`
- Polymarket GET /teams returns: `name`, `league`, `abbreviation`, `alias`
- Existing test: `tests/test_market_matcher.py` uses `FakeMarket` dataclass

---

### Task 1: Create `src/matching/` package — sport_classifier.py

**Files:**
- Create: `src/matching/__init__.py` (empty for now)
- Create: `src/matching/sport_classifier.py`
- Create: `tests/test_matching_sport_classifier.py`

- [ ] **Step 1: Write failing tests for sport_classifier**

```python
# tests/test_matching_sport_classifier.py
"""Tests for sport classification from Polymarket market data."""
from dataclasses import dataclass
from src.matching.sport_classifier import classify_sport


@dataclass
class FakeMarket:
    slug: str = ""
    sport_tag: str = ""
    tags: list = None
    question: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class TestClassifySport:
    def test_slug_prefix_nba(self):
        m = FakeMarket(slug="nba-lal-bos-2026-04-05")
        assert classify_sport(m) == "basketball"

    def test_slug_prefix_cs2(self):
        m = FakeMarket(slug="cs2-hero-nip-2026-04-03")
        assert classify_sport(m) == "esports"

    def test_slug_prefix_epl(self):
        m = FakeMarket(slug="epl-liv-mci-2026-04-03")
        assert classify_sport(m) == "soccer"

    def test_slug_prefix_mlb(self):
        m = FakeMarket(slug="mlb-nyy-bos-2026-04-05")
        assert classify_sport(m) == "baseball"

    def test_slug_prefix_nhl(self):
        m = FakeMarket(slug="nhl-nyr-bos-2026-04-05")
        assert classify_sport(m) == "hockey"

    def test_slug_prefix_val(self):
        m = FakeMarket(slug="val-fnc-tl-2026-04-05")
        assert classify_sport(m) == "esports"

    def test_slug_prefix_lol(self):
        m = FakeMarket(slug="lol-t1-geng-2026-04-05")
        assert classify_sport(m) == "esports"

    def test_slug_prefix_dota2(self):
        m = FakeMarket(slug="dota2-spirit-navi-2026-04-05")
        assert classify_sport(m) == "esports"

    def test_slug_prefix_ufc(self):
        m = FakeMarket(slug="ufc-jones-miocic-2026-04-05")
        assert classify_sport(m) == "mma"

    def test_slug_prefix_atp(self):
        m = FakeMarket(slug="atp-sinner-djokovic-2026-04-05")
        assert classify_sport(m) == "tennis"

    def test_slug_prefix_cricket_ipl(self):
        m = FakeMarket(slug="ipl-csk-mi-2026-04-05")
        assert classify_sport(m) == "cricket"

    def test_slug_prefix_rugby(self):
        m = FakeMarket(slug="ruprem-eng-fra-2026-04-05")
        assert classify_sport(m) == "rugby"

    def test_sport_tag_fallback(self):
        m = FakeMarket(slug="unknown-slug-here", sport_tag="cs2")
        assert classify_sport(m) == "esports"

    def test_question_keyword_fallback(self):
        m = FakeMarket(slug="will-team-win", question="NBA: Will the Lakers beat the Celtics?")
        assert classify_sport(m) == "basketball"

    def test_unknown_returns_none(self):
        m = FakeMarket(slug="some-random-market")
        assert classify_sport(m) is None

    def test_cross_sport_check(self):
        from src.matching.sport_classifier import sports_compatible
        assert sports_compatible("basketball", "basketball") is True
        assert sports_compatible("basketball", "football") is False
        assert sports_compatible("esports", "basketball") is False
        assert sports_compatible(None, "basketball") is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_matching_sport_classifier.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Create package init and implement sport_classifier**

```python
# src/matching/__init__.py
"""Matching pipeline — bridges Polymarket markets to scout entries."""
```

```python
# src/matching/sport_classifier.py
"""Classify market sport from slug prefix, sport_tag, or question keywords."""
from __future__ import annotations
from typing import Optional

# Polymarket sport code -> category mapping
# Built from Polymarket GET /sports (170 codes) grouped into categories
_SLUG_TO_CATEGORY: dict[str, str] = {
    # Basketball
    "nba": "basketball", "wnba": "basketball", "cbb": "basketball",
    "cwbb": "basketball", "ncaab": "basketball",
    "euroleague": "basketball", "bkaba": "basketball", "bkarg": "basketball",
    "bkbbl": "basketball", "bkbsl": "basketball", "bkcba": "basketball",
    "bkcl": "basketball", "bkfr1": "basketball", "bkgr1": "basketball",
    "bkjpn": "basketball", "bkkbl": "basketball", "bkligend": "basketball",
    "bknbl": "basketball", "bkseriea": "basketball", "bkvtb": "basketball",
    "bkfibaqaf": "basketball", "bkfibaqam": "basketball",
    "bkfibaqas": "basketball", "bkfibaqeu": "basketball",
    # American Football
    "nfl": "football", "cfb": "football",
    # Baseball
    "mlb": "baseball", "kbo": "baseball", "wbc": "baseball",
    # Hockey
    "nhl": "hockey", "ahl": "hockey", "khl": "hockey",
    "shl": "hockey", "cehl": "hockey", "dehl": "hockey", "snhl": "hockey",
    # Soccer
    "epl": "soccer", "lal": "soccer", "bun": "soccer", "sea": "soccer",
    "fl1": "soccer", "ucl": "soccer", "uel": "soccer", "uef": "soccer",
    "ere": "soccer", "por": "soccer", "tur": "soccer", "mls": "soccer",
    "efa": "soccer", "efl": "soccer", "dfb": "soccer", "cde": "soccer",
    "cdr": "soccer", "lcs": "soccer", "lib": "soccer", "sud": "soccer",
    "con": "soccer", "cof": "soccer", "ofc": "soccer", "fif": "soccer",
    "mex": "soccer", "bra": "soccer", "bra2": "soccer", "arg": "soccer",
    "col": "soccer", "chi": "soccer", "jap": "soccer", "kor": "soccer",
    "ind": "soccer", "spl": "soccer", "aus": "soccer", "nor": "soccer",
    "den": "soccer", "rus": "soccer", "caf": "soccer", "acn": "soccer",
    "itc": "soccer", "cze1": "soccer", "egy1": "soccer", "mar1": "soccer",
    "per1": "soccer", "rou1": "soccer", "ukr1": "soccer", "uwcl": "soccer",
    "bol1": "soccer", "chi1": "soccer", "col1": "soccer",
    "ja2": "soccer", "j1-100": "soccer", "j2-100": "soccer",
    "abb": "soccer", "ssc": "soccer", "mwoh": "soccer", "wwoh": "soccer",
    # MMA
    "ufc": "mma", "zuffa": "mma",
    # Tennis
    "atp": "tennis", "wta": "tennis", "wttmen": "tennis",
    # Golf
    "pga": "golf", "lpga": "golf",
    # Cricket (all 40+ codes)
    "ipl": "cricket", "odi": "cricket", "t20": "cricket", "test": "cricket",
    "csa": "cricket", "lpl": "cricket", "psp": "cricket", "she": "cricket",
    "sasa": "cricket", "craus": "cricket", "crban": "cricket",
    "creng": "cricket", "crind": "cricket", "crint": "cricket",
    "crnew": "cricket", "crpak": "cricket", "crsou": "cricket",
    "cruae": "cricket", "cru19wc": "cricket", "crwncl": "cricket",
    "crwpl20": "cricket", "crwt20wcgq": "cricket", "crafgwi20": "cricket",
    "crbtnmlyhkg20": "cricket",
    "cricbbl": "cricket", "cricbpl": "cricket", "criccpl": "cricket",
    "criccsat20w": "cricket", "crichkt20w": "cricket", "cricilt20": "cricket",
    "cricipl": "cricket", "criclcl": "cricket", "cricmlc": "cricket",
    "cricnt20c": "cricket", "cricpakt20cup": "cricket", "cricps": "cricket",
    "cricpsl": "cricket", "cricsa20": "cricket", "cricsm": "cricket",
    "cricss": "cricket", "crict20blast": "cricket", "crict20lpl": "cricket",
    "crict20plw": "cricket", "cricthunderbolt": "cricket",
    "cricwncl": "cricket",
    # Rugby
    "ruchamp": "rugby", "rueuchamp": "rugby", "ruprem": "rugby",
    "rusixnat": "rugby", "rusrp": "rugby", "rutopft": "rugby",
    "ruurc": "rugby",
    # Esports
    "cs2": "esports", "lol": "esports", "dota2": "esports", "val": "esports",
    "ow": "esports", "codmw": "esports", "mlbb": "esports", "pubg": "esports",
    "r6siege": "esports", "rl": "esports", "hok": "esports",
    "wildrift": "esports", "sc2": "esports", "sc": "esports", "fifa": "esports",
    # Lacrosse
    "pll": "lacrosse", "wll": "lacrosse",
    # Chess
    "chess": "chess",
}

# Question keyword fallbacks (checked only if slug/tag don't match)
_QUESTION_KEYWORDS: dict[str, str] = {
    "nba": "basketball", "wnba": "basketball", "ncaa basketball": "basketball",
    "nfl": "football", "mlb": "baseball", "nhl": "hockey",
    "premier league": "soccer", "champions league": "soccer",
    "la liga": "soccer", "bundesliga": "soccer", "serie a": "soccer",
    "ligue 1": "soccer", "mls": "soccer",
    "ufc": "mma", "mma": "mma",
    "atp": "tennis", "wta": "tennis",
    "counter-strike": "esports", "cs2": "esports", "valorant": "esports",
    "league of legends": "esports", "dota": "esports",
    "cricket": "cricket", "ipl": "cricket", "t20": "cricket",
    "rugby": "rugby",
}

# Scout sport field -> category (ESPN uses "basketball", "hockey", etc.)
_SCOUT_SPORT_MAP: dict[str, str] = {
    "basketball": "basketball", "football": "football",
    "baseball": "baseball", "hockey": "hockey",
    "soccer": "soccer", "mma": "mma", "tennis": "tennis",
    "golf": "golf", "cricket": "cricket", "rugby": "rugby",
}


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

    return None


def classify_entry(entry: dict) -> str:
    """Classify a scout entry into a sport category."""
    if entry.get("is_esports"):
        return "esports"
    sport = entry.get("sport", "")
    return _SCOUT_SPORT_MAP.get(sport, sport)


def sports_compatible(market_sport: Optional[str], entry_sport: str) -> bool:
    """Check if market and entry sport categories are compatible.

    None (unknown) is compatible with anything.
    Same category matches. Different categories don't.
    """
    if market_sport is None:
        return True
    if not entry_sport:
        return True
    return market_sport == entry_sport
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_matching_sport_classifier.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/matching/__init__.py src/matching/sport_classifier.py tests/test_matching_sport_classifier.py
git commit -m "feat(matching): add sport_classifier module with 170 Polymarket sport codes"
```

---

### Task 2: Create slug_parser.py

**Files:**
- Create: `src/matching/slug_parser.py`
- Create: `tests/test_matching_slug_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_matching_slug_parser.py
"""Tests for Polymarket slug parsing."""
from src.matching.slug_parser import parse_slug, extract_slug_tokens


class TestParseSlug:
    def test_standard_format(self):
        r = parse_slug("nba-lal-bos-2026-04-05")
        assert r.sport == "nba"
        assert r.team_tokens == ["lal", "bos"]

    def test_esports_format(self):
        r = parse_slug("cs2-hero-nip-2026-04-03")
        assert r.sport == "cs2"
        assert r.team_tokens == ["hero", "nip"]

    def test_three_word_team(self):
        # e.g. "nba-okc-gsw-2026-04-05"
        r = parse_slug("nba-okc-gsw-2026-04-05")
        assert r.sport == "nba"
        assert r.team_tokens == ["okc", "gsw"]

    def test_soccer_format(self):
        r = parse_slug("epl-liv-mci-2026-04-03")
        assert r.sport == "epl"
        assert r.team_tokens == ["liv", "mci"]

    def test_no_date(self):
        r = parse_slug("nba-lal-bos")
        assert r.sport == "nba"
        assert r.team_tokens == ["lal", "bos"]

    def test_unknown_sport(self):
        r = parse_slug("will-lakers-beat-celtics")
        assert r.sport is None
        assert "lakers" in r.team_tokens or len(r.team_tokens) > 0

    def test_empty_slug(self):
        r = parse_slug("")
        assert r.sport is None
        assert r.team_tokens == []

    def test_cricket_ipl(self):
        r = parse_slug("ipl-csk-mi-2026-04-05")
        assert r.sport == "ipl"
        assert r.team_tokens == ["csk", "mi"]


class TestExtractSlugTokens:
    def test_basic(self):
        tokens = extract_slug_tokens("nba-lal-bos-2026-04-05")
        assert "nba" in tokens
        assert "lal" in tokens
        assert "bos" in tokens
        assert "2026" not in tokens

    def test_single_char_excluded(self):
        tokens = extract_slug_tokens("a-bb-ccc")
        assert "a" not in tokens
        assert "bb" in tokens
        assert "ccc" in tokens
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_matching_slug_parser.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement slug_parser**

```python
# src/matching/slug_parser.py
"""Parse Polymarket market slugs into sport code + team abbreviation tokens."""
from __future__ import annotations
from dataclasses import dataclass, field

from src.matching.sport_classifier import _SLUG_TO_CATEGORY


@dataclass
class SlugParts:
    sport: str | None = None
    team_tokens: list[str] = field(default_factory=list)
    raw_tokens: list[str] = field(default_factory=list)


def parse_slug(slug: str) -> SlugParts:
    """Parse a Polymarket slug into sport code and team abbreviation tokens.

    Standard format: "{sport}-{abbrev_a}-{abbrev_b}-{YYYY}-{MM}-{DD}"
    Returns SlugParts with sport code (if recognized) and team tokens.
    """
    if not slug:
        return SlugParts()

    parts = slug.lower().split("-")
    if not parts:
        return SlugParts()

    # Strip date tokens from the end (YYYY, MM, DD pattern)
    clean = []
    i = len(parts) - 1
    # Walk backwards, strip trailing date-like digits
    date_count = 0
    while i >= 0 and parts[i].isdigit() and date_count < 3:
        i -= 1
        date_count += 1
    clean = parts[:i + 1]

    if not clean:
        return SlugParts()

    # First token: sport code?
    sport = None
    team_start = 0
    if clean[0] in _SLUG_TO_CATEGORY:
        sport = clean[0]
        team_start = 1

    # Team tokens: everything after sport code, excluding noise
    _NOISE = {"will", "win", "beat", "vs", "the", "over", "against"}
    team_tokens = [
        t for t in clean[team_start:]
        if len(t) >= 2 and t not in _NOISE
    ]

    return SlugParts(
        sport=sport,
        team_tokens=team_tokens,
        raw_tokens=clean,
    )


def extract_slug_tokens(slug: str) -> set[str]:
    """Extract all meaningful tokens from slug (for abbreviation matching).

    Excludes: single-char tokens, pure digits.
    """
    return {
        p for p in slug.lower().split("-")
        if len(p) >= 2 and not p.isdigit()
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_matching_slug_parser.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/matching/slug_parser.py tests/test_matching_slug_parser.py
git commit -m "feat(matching): add slug_parser for Polymarket slug decomposition"
```

---

### Task 3: Create team_resolver.py

**Files:**
- Create: `src/matching/team_resolver.py`
- Create: `tests/test_matching_team_resolver.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_matching_team_resolver.py
"""Tests for team name resolution from abbreviations/aliases."""
import json
from src.matching.team_resolver import TeamResolver


class TestTeamResolver:
    def _resolver(self, tmp_path):
        return TeamResolver(cache_path=tmp_path / "resolver_cache.json", auto_refresh=False)

    def test_static_nba(self, tmp_path):
        r = self._resolver(tmp_path)
        assert r.resolve("lal") == "los angeles lakers"
        assert r.resolve("bos") == "boston celtics"

    def test_static_esports(self, tmp_path):
        r = self._resolver(tmp_path)
        assert r.resolve("fnc") == "fnatic"
        assert r.resolve("navi") == "natus vincere"
        assert r.resolve("g2") == "g2 esports"

    def test_case_insensitive(self, tmp_path):
        r = self._resolver(tmp_path)
        assert r.resolve("LAL") == "los angeles lakers"
        assert r.resolve("FNC") == "fnatic"

    def test_unknown_returns_none(self, tmp_path):
        r = self._resolver(tmp_path)
        assert r.resolve("zzzzz") is None

    def test_alias_nicknames(self, tmp_path):
        r = self._resolver(tmp_path)
        assert r.resolve("lakers") == "los angeles lakers"
        assert r.resolve("celtics") == "boston celtics"
        assert r.resolve("spirit") == "team spirit"

    def test_load_from_cache(self, tmp_path):
        cache = tmp_path / "resolver_cache.json"
        cache.write_text(json.dumps({
            "abbrevs": {"xyz": "xyz gaming"},
            "aliases": {"xyz team": "xyz gaming"},
        }))
        r = TeamResolver(cache_path=cache, auto_refresh=False)
        assert r.resolve("xyz") == "xyz gaming"

    def test_normalize(self, tmp_path):
        from src.matching.team_resolver import normalize
        assert normalize("Team Liquid FC") == "team liquid"
        assert normalize("  Fnatic Esports  ") == "fnatic"
        assert normalize("G2 Gaming") == "g2"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_matching_team_resolver.py -v`
Expected: FAIL

- [ ] **Step 3: Implement team_resolver**

```python
# src/matching/team_resolver.py
"""Resolve team abbreviations and aliases to canonical names.

Data sources (priority order):
1. Polymarket GET /teams — abbreviation + alias
2. ESPN /teams — abbreviation + shortDisplayName
3. PandaScore /teams — acronym
4. Static fallback — hardcoded common abbreviations/nicknames
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_STRIP_SUFFIXES = (" fc", " sc", " esports", " gaming", " clan", " team")


def normalize(name: str) -> str:
    """Lowercase, strip whitespace and common suffixes."""
    name = name.lower().strip()
    for suffix in _STRIP_SUFFIXES:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name


# Combined static data from old STATIC_ABBREVS + TEAM_ALIASES
_STATIC_ABBREVS: dict[str, str] = {
    # NBA
    "lal": "los angeles lakers", "bos": "boston celtics",
    "gsw": "golden state warriors", "bkn": "brooklyn nets",
    "nyk": "new york knicks", "phi": "philadelphia 76ers",
    "mil": "milwaukee bucks", "mia": "miami heat",
    "chi": "chicago bulls", "phx": "phoenix suns",
    "dal": "dallas mavericks", "den": "denver nuggets",
    "min": "minnesota timberwolves", "okc": "oklahoma city thunder",
    "cle": "cleveland cavaliers", "lac": "la clippers",
    "hou": "houston rockets", "mem": "memphis grizzlies",
    "nop": "new orleans pelicans", "atl": "atlanta hawks",
    "ind": "indiana pacers", "orl": "orlando magic",
    "tor": "toronto raptors", "wsh": "washington wizards",
    "det": "detroit pistons", "cha": "charlotte hornets",
    "sac": "sacramento kings", "por": "portland trail blazers",
    "uta": "utah jazz", "sas": "san antonio spurs",
    # NFL
    "kc": "kansas city chiefs", "buf": "buffalo bills",
    "bal": "baltimore ravens", "sf": "san francisco 49ers",
    "gb": "green bay packers", "tb": "tampa bay buccaneers",
    "ne": "new england patriots", "sea": "seattle seahawks",
    "pit": "pittsburgh steelers", "cin": "cincinnati bengals",
    "jax": "jacksonville jaguars", "ten": "tennessee titans",
    "lar": "los angeles rams", "nyg": "new york giants",
    "nyj": "new york jets", "car": "carolina panthers",
    "no": "new orleans saints", "lv": "las vegas raiders",
    "ari": "arizona cardinals",
    # MLB
    "nyy": "new york yankees", "lad": "los angeles dodgers",
    "nym": "new york mets", "chc": "chicago cubs",
    "cws": "chicago white sox", "sd": "san diego padres",
    "tex": "texas rangers", "stl": "st. louis cardinals",
    # NHL
    "mtl": "montreal canadiens", "nyr": "new york rangers",
    "edm": "edmonton oilers", "cgy": "calgary flames",
    "van": "vancouver canucks", "col": "colorado avalanche",
    # Esports
    "fnc": "fnatic", "tl": "team liquid", "g2": "g2 esports",
    "c9": "cloud9", "t1": "t1", "geng": "gen.g", "drx": "drx",
    "sen": "sentinels", "100t": "100 thieves", "eg": "evil geniuses",
    "navi": "natus vincere", "faze": "faze clan", "vit": "team vitality",
    "spirit": "team spirit", "mouz": "mouz", "hero": "heroic",
    "loud": "loud", "furia": "furia", "mibr": "mibr",
    "blg": "bilibili gaming", "tes": "top esports", "jdg": "jd gaming",
    "weibo": "weibo gaming", "lng": "lng esports",
    "rng": "royal never give up", "edg": "edward gaming",
    "fpx": "funplus phoenix",
}

_STATIC_ALIASES: dict[str, str] = {
    # Nicknames -> canonical
    "lakers": "los angeles lakers", "celtics": "boston celtics",
    "warriors": "golden state warriors", "bucks": "milwaukee bucks",
    "sixers": "philadelphia 76ers", "76ers": "philadelphia 76ers",
    "knicks": "new york knicks", "nets": "brooklyn nets",
    "heat": "miami heat", "nuggets": "denver nuggets",
    "suns": "phoenix suns", "mavs": "dallas mavericks",
    "thunder": "oklahoma city thunder", "wolves": "minnesota timberwolves",
    "cavs": "cleveland cavaliers", "clips": "la clippers",
    "rockets": "houston rockets", "grizzlies": "memphis grizzlies",
    "pelicans": "new orleans pelicans", "hawks": "atlanta hawks",
    "bulls": "chicago bulls", "pacers": "indiana pacers",
    "magic": "orlando magic", "raptors": "toronto raptors",
    "hornets": "charlotte hornets", "kings": "sacramento kings",
    "blazers": "portland trail blazers", "jazz": "utah jazz",
    "spurs": "san antonio spurs",
    # Soccer
    "man utd": "manchester united", "man city": "manchester city",
    "liverpool": "liverpool fc", "chelsea": "chelsea fc",
    "arsenal": "arsenal fc", "tottenham": "tottenham hotspur",
    "barca": "fc barcelona", "bayern": "bayern munich",
    "psg": "paris saint-germain", "juve": "juventus",
    "dortmund": "borussia dortmund", "bvb": "borussia dortmund",
    # Esports
    "na'vi": "natus vincere", "liquid": "team liquid",
    "vitality": "team vitality", "mousesports": "mouz",
    "complexity": "complexity gaming", "cloud9": "cloud9",
    # NHL
    "leafs": "toronto maple leafs", "habs": "montreal canadiens",
    "bruins": "boston bruins", "rangers": "new york rangers",
    "pens": "pittsburgh penguins", "caps": "washington capitals",
    "oilers": "edmonton oilers", "flames": "calgary flames",
    "avs": "colorado avalanche",
    # NFL
    "chiefs": "kansas city chiefs", "eagles": "philadelphia eagles",
    "niners": "san francisco 49ers", "cowboys": "dallas cowboys",
    "bills": "buffalo bills", "ravens": "baltimore ravens",
    "steelers": "pittsburgh steelers", "packers": "green bay packers",
    # MLB
    "yankees": "new york yankees", "dodgers": "los angeles dodgers",
    "red sox": "boston red sox", "mets": "new york mets",
    "astros": "houston astros", "braves": "atlanta braves",
    "cubs": "chicago cubs", "phillies": "philadelphia phillies",
    # Tennis
    "djokovic": "novak djokovic", "sinner": "jannik sinner",
    "alcaraz": "carlos alcaraz", "medvedev": "daniil medvedev",
}


class TeamResolver:
    """Resolve abbreviations/aliases to canonical team names.

    Single source of truth replacing old AliasStore + TEAM_ALIASES.
    """

    def __init__(self, cache_path: Path | None = None, auto_refresh: bool = True):
        self._cache_path = cache_path or Path("logs/team_resolver_cache.json")
        self._abbrevs: dict[str, str] = {}   # abbreviation -> canonical
        self._aliases: dict[str, str] = {}    # alias/nickname -> canonical
        self._lock = threading.Lock()

        # Load from cache or static
        if not self._load_cache():
            self._abbrevs = dict(_STATIC_ABBREVS)
            self._aliases = dict(_STATIC_ALIASES)

        if auto_refresh:
            t = threading.Thread(target=self._background_refresh, daemon=True)
            t.start()

    def resolve(self, token: str) -> Optional[str]:
        """Resolve a token (abbreviation, alias, or name) to canonical name.

        Returns canonical lowercase name, or None if unknown.
        """
        key = token.lower().strip()
        with self._lock:
            # 1. Direct abbreviation
            if key in self._abbrevs:
                return self._abbrevs[key]
            # 2. Alias/nickname
            if key in self._aliases:
                return self._aliases[key]
        return None

    def _load_cache(self) -> bool:
        try:
            if not self._cache_path.exists():
                return False
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            abbrevs = data.get("abbrevs", {})
            aliases = data.get("aliases", {})
            if not abbrevs:
                return False
            with self._lock:
                self._abbrevs = {k.lower(): v.lower() for k, v in abbrevs.items()}
                self._aliases = {k.lower(): v.lower() for k, v in aliases.items()}
            logger.info("TeamResolver: loaded %d abbrevs + %d aliases from cache",
                        len(self._abbrevs), len(self._aliases))
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("TeamResolver: cache load failed: %s", e)
            return False

    def _save_cache(self):
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                data = {"abbrevs": dict(self._abbrevs), "aliases": dict(self._aliases)}
            self._cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("TeamResolver: cache save failed: %s", e)

    def _background_refresh(self):
        """Refresh from APIs in background thread."""
        try:
            new_abbrevs = dict(_STATIC_ABBREVS)
            new_aliases = dict(_STATIC_ALIASES)

            self._fetch_polymarket_teams(new_abbrevs, new_aliases)
            self._fetch_espn_teams(new_abbrevs)
            self._fetch_pandascore_teams(new_abbrevs)

            with self._lock:
                self._abbrevs = {k.lower(): v.lower() for k, v in new_abbrevs.items()}
                self._aliases = {k.lower(): v.lower() for k, v in new_aliases.items()}
            self._save_cache()
            logger.info("TeamResolver: refresh complete — %d abbrevs, %d aliases",
                        len(self._abbrevs), len(self._aliases))
        except Exception as e:
            logger.warning("TeamResolver: refresh failed: %s", e)

    def _fetch_polymarket_teams(self, abbrevs: dict, aliases: dict):
        """Polymarket GET /teams — GOLD STANDARD for abbreviations."""
        try:
            resp = requests.get("https://gamma-api.polymarket.com/teams",
                                params={"limit": 5000}, timeout=15)
            if resp.status_code != 200:
                return
            teams = resp.json()
            if not isinstance(teams, list):
                return
            for team in teams:
                abbr = (team.get("abbreviation") or "").strip()
                name = (team.get("name") or "").strip()
                alias = (team.get("alias") or "").strip()
                if abbr and name and len(abbr) >= 2:
                    abbrevs[abbr.lower()] = name.lower()
                if alias and name:
                    aliases[alias.lower()] = name.lower()
            logger.info("TeamResolver: Polymarket — %d teams fetched", len(teams))
        except Exception as e:
            logger.debug("TeamResolver: Polymarket fetch failed: %s", e)

    def _fetch_espn_teams(self, abbrevs: dict):
        """ESPN /teams — abbreviation + shortDisplayName."""
        from src.scout_scheduler import _SCOUT_LEAGUES
        for sport, league, _ in _SCOUT_LEAGUES:
            if sport in ("tennis", "golf", "mma"):
                continue
            try:
                url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for sport_data in data.get("sports", []):
                    for league_data in sport_data.get("leagues", []):
                        for team_entry in league_data.get("teams", []):
                            t = team_entry.get("team", {})
                            abbr = (t.get("abbreviation") or "").strip()
                            display = (t.get("displayName") or "").strip()
                            short = (t.get("shortDisplayName") or "").strip()
                            if abbr and display:
                                abbrevs[abbr.lower()] = display.lower()
                            if short and display:
                                abbrevs[short.lower()] = display.lower()
                time.sleep(0.3)
            except Exception:
                pass

    def _fetch_pandascore_teams(self, abbrevs: dict):
        """PandaScore /teams — acronym."""
        api_key = os.getenv("PANDASCORE_API_KEY", "")
        if not api_key:
            return
        for game in ["csgo", "lol", "dota2", "valorant"]:
            try:
                resp = requests.get(
                    f"https://api.pandascore.co/{game}/teams",
                    params={"page[size]": 100, "page[number]": 1},
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10,
                )
                if resp.status_code != 200:
                    continue
                for team in resp.json():
                    acronym = (team.get("acronym") or "").strip()
                    name = (team.get("name") or "").strip()
                    if acronym and name:
                        abbrevs[acronym.lower()] = name.lower()
                time.sleep(0.5)
            except Exception:
                pass
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_matching_team_resolver.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/matching/team_resolver.py tests/test_matching_team_resolver.py
git commit -m "feat(matching): add TeamResolver with Polymarket/ESPN/PandaScore sources"
```

---

### Task 4: Create pair_matcher.py

**Files:**
- Create: `src/matching/pair_matcher.py`
- Create: `tests/test_matching_pair_matcher.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_matching_pair_matcher.py
"""Tests for team pair matching."""
from src.matching.pair_matcher import match_team, match_pair


class TestMatchTeam:
    def test_exact_same(self):
        ok, conf, method = match_team("fnatic", "fnatic")
        assert ok and conf == 1.0

    def test_alias_match(self):
        ok, conf, method = match_team("lakers", "los angeles lakers")
        assert ok and conf == 1.0 and method == "exact_alias"

    def test_token_substring(self):
        ok, conf, method = match_team("lakers", "LA Lakers Basketball")
        assert ok and conf >= 0.85

    def test_fuzzy_high(self):
        ok, conf, method = match_team("manchester united", "man united fc")
        assert ok and conf >= 0.80

    def test_no_match(self):
        ok, conf, method = match_team("fnatic", "team liquid")
        assert not ok

    def test_normalized_suffix_strip(self):
        ok, conf, _ = match_team("team liquid", "liquid")
        assert ok


class TestMatchPair:
    def test_normal_order(self):
        ok, conf = match_pair(
            ("los angeles lakers", "boston celtics"),
            ("Los Angeles Lakers", "Boston Celtics"),
        )
        assert ok and conf >= 0.85

    def test_swapped_order(self):
        ok, conf = match_pair(
            ("boston celtics", "los angeles lakers"),
            ("Los Angeles Lakers", "Boston Celtics"),
        )
        assert ok and conf >= 0.85

    def test_no_match(self):
        ok, conf = match_pair(
            ("fnatic", "team liquid"),
            ("g2 esports", "natus vincere"),
        )
        assert not ok

    def test_partial_match_fails(self):
        """Only one team matching is not enough."""
        ok, conf = match_pair(
            ("fnatic", "team liquid"),
            ("fnatic", "natus vincere"),
        )
        assert not ok
```

- [ ] **Step 2: Run tests to verify fail**

Run: `python -m pytest tests/test_matching_pair_matcher.py -v`

- [ ] **Step 3: Implement pair_matcher**

```python
# src/matching/pair_matcher.py
"""Team pair matching — compare two team names with 4-layer confidence.

Replaces src/team_matcher.py. Used by:
- matching pipeline (market ↔ scout)
- odds_api.py (market ↔ Odds API event)
- sports_data.py, esports_data.py (team lookup)
"""
from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Optional

from rapidfuzz import fuzz

from src.matching.team_resolver import normalize, _STATIC_ALIASES, _STATIC_ABBREVS

logger = logging.getLogger(__name__)


def _canonicalize(name: str) -> str:
    """Resolve through aliases/abbrevs to canonical name."""
    n = normalize(name)
    if n in _STATIC_ALIASES:
        return _STATIC_ALIASES[n]
    if n in _STATIC_ABBREVS:
        return _STATIC_ABBREVS[n]
    return n


def match_team(query: str, candidate: str) -> tuple[bool, float, str]:
    """Match two team names. Returns (is_match, confidence, method).

    L1: Exact / alias (1.0)
    L2: Token overlap (0.85-0.90)
    L3: Fuzzy SequenceMatcher >= 0.80
    """
    q = normalize(query)
    c = normalize(candidate)

    # L1: Exact canonical
    if _canonicalize(query) == _canonicalize(candidate):
        return True, 1.0, "exact_alias"

    # L2: Token overlap
    q_tokens = set(q.split())
    c_tokens = set(c.split())
    noise = {"team", "the", "of", "de", "fc", "sc", "city", "united"}

    if len(q_tokens) == 1:
        q_word = list(q_tokens)[0]
        if q_word not in noise and (q_word in c_tokens or any(q_word in ct for ct in c_tokens)):
            return True, 0.90, "token_substring"

    if len(q_tokens) > 1 and len(c_tokens) > 1:
        overlap = q_tokens & c_tokens
        meaningful = overlap - noise
        if meaningful and len(overlap) / min(len(q_tokens), len(c_tokens)) >= 0.5:
            return True, 0.85, "token_overlap"

    # L3: Fuzzy — high threshold only
    score = SequenceMatcher(None, q, c).ratio()
    if score >= 0.80:
        return True, score, "fuzzy"

    # L3b: rapidfuzz token_sort for longer names
    if len(q) >= 4 and len(c) >= 4:
        rf_score = fuzz.token_sort_ratio(q, c) / 100.0
        if rf_score >= 0.85:
            return True, rf_score, "fuzzy_token_sort"

    return False, max(score, 0.0), "no_match"


def match_pair(
    market_names: tuple[str, str],
    entry_names: tuple[str, str],
) -> tuple[bool, float]:
    """Match two team pairs. Both must match. Tries normal + swapped order."""
    # Normal order
    ma, ca, _ = match_team(market_names[0], entry_names[0])
    mb, cb, _ = match_team(market_names[1], entry_names[1])
    if ma and mb:
        return True, min(ca, cb)

    # Swapped
    ma2, ca2, _ = match_team(market_names[0], entry_names[1])
    mb2, cb2, _ = match_team(market_names[1], entry_names[0])
    if ma2 and mb2:
        return True, min(ca2, cb2)

    return False, 0.0


def find_best_event_match(
    team_a: str,
    team_b: str,
    events: list[dict],
    home_key: str = "home_team",
    away_key: str = "away_team",
    min_confidence: float = 0.80,
) -> Optional[tuple[dict, float]]:
    """Find best matching event for a team pair (used by odds_api.py)."""
    best_event = None
    best_conf = 0.0

    for event in events:
        home = event.get(home_key, "")
        away = event.get(away_key, "")
        if not home or not away:
            continue
        is_match, conf = match_pair((team_a, team_b), (home, away))
        if is_match and conf > best_conf:
            best_conf = conf
            best_event = event

    if best_event and best_conf >= min_confidence:
        return best_event, best_conf
    return None
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_matching_pair_matcher.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/matching/pair_matcher.py tests/test_matching_pair_matcher.py
git commit -m "feat(matching): add pair_matcher with 4-layer team matching"
```

---

### Task 5: Create `__init__.py` — main match_markets() function

**Files:**
- Modify: `src/matching/__init__.py`
- Create: `tests/test_matching_pipeline.py`

- [ ] **Step 1: Write failing integration tests**

```python
# tests/test_matching_pipeline.py
"""Integration tests for the full matching pipeline."""
from dataclasses import dataclass
from src.matching import match_markets


@dataclass
class FakeMarket:
    condition_id: str = "cond_123"
    question: str = ""
    slug: str = ""
    sport_tag: str = ""
    tags: list = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class TestMatchMarkets:
    def test_nba_abbreviation_match(self, tmp_path):
        market = FakeMarket(
            slug="nba-lal-bos-2026-04-05",
            question="Will the Los Angeles Lakers beat the Boston Celtics?",
        )
        queue = {
            "k1": {
                "team_a": "Los Angeles Lakers", "team_b": "Boston Celtics",
                "abbrev_a": "LAL", "abbrev_b": "BOS",
                "short_a": "Lakers", "short_b": "Celtics",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball", "league": "nba",
                "is_esports": False, "entered": False,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        assert len(results) == 1
        assert results[0]["scout_key"] == "k1"

    def test_esports_match(self, tmp_path):
        market = FakeMarket(
            slug="cs2-hero-nip-2026-04-03",
            question="Counter-Strike: Heroic vs NIP",
        )
        queue = {
            "k1": {
                "team_a": "Heroic", "team_b": "NIP",
                "abbrev_a": "HERO", "abbrev_b": "NIP",
                "short_a": "", "short_b": "",
                "match_time": "2026-04-03T12:00:00+00:00",
                "sport": "", "league": "",
                "is_esports": True, "entered": False,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        assert len(results) == 1

    def test_no_cross_sport(self, tmp_path):
        market = FakeMarket(slug="nba-phi-mia-2026-04-05", question="76ers vs Heat")
        queue = {
            "k1": {
                "team_a": "Philadelphia Eagles", "team_b": "Miami Dolphins",
                "abbrev_a": "PHI", "abbrev_b": "MIA",
                "short_a": "Eagles", "short_b": "Dolphins",
                "match_time": "2026-04-05T20:00:00+00:00",
                "sport": "football", "league": "nfl",
                "is_esports": False, "entered": False,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        assert len(results) == 0

    def test_skips_entered(self, tmp_path):
        market = FakeMarket(slug="nba-lal-bos-2026-04-05", question="Lakers vs Celtics")
        queue = {
            "k1": {
                "team_a": "Los Angeles Lakers", "team_b": "Boston Celtics",
                "abbrev_a": "LAL", "abbrev_b": "BOS",
                "short_a": "Lakers", "short_b": "Celtics",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball", "league": "nba",
                "is_esports": False, "entered": True,  # Already used
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        assert len(results) == 0

    def test_empty_abbrevs_still_matches_by_name(self, tmp_path):
        """Even without abbreviations, full names in question should match."""
        market = FakeMarket(
            slug="some-unknown-slug",
            question="Will the Los Angeles Lakers beat the Boston Celtics?",
        )
        queue = {
            "k1": {
                "team_a": "Los Angeles Lakers", "team_b": "Boston Celtics",
                "abbrev_a": "", "abbrev_b": "",
                "short_a": "", "short_b": "",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball", "league": "nba",
                "is_esports": False, "entered": False,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        assert len(results) == 1

    def test_return_format(self, tmp_path):
        market = FakeMarket(slug="nba-lal-bos-2026-04-05", question="Lakers vs Celtics")
        queue = {
            "k1": {
                "team_a": "Los Angeles Lakers", "team_b": "Boston Celtics",
                "abbrev_a": "LAL", "abbrev_b": "BOS",
                "short_a": "Lakers", "short_b": "Celtics",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball", "league": "nba",
                "is_esports": False, "entered": False,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        r = results[0]
        assert "market" in r and "scout_entry" in r and "scout_key" in r
        assert r["scout_entry"]["matched"] is True
        assert "match_confidence" in r["scout_entry"]
```

- [ ] **Step 2: Run tests to verify fail**

Run: `python -m pytest tests/test_matching_pipeline.py -v`

- [ ] **Step 3: Implement match_markets in __init__.py**

```python
# src/matching/__init__.py
"""Matching pipeline — bridges Polymarket markets to scout entries.

Public API:
    match_markets(markets, scout_queue, cache_dir=None) -> list[dict]

Replaces: src/market_matcher.py (match_batch + AliasStore)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.matching.sport_classifier import classify_sport, classify_entry, sports_compatible
from src.matching.slug_parser import parse_slug, extract_slug_tokens
from src.matching.team_resolver import TeamResolver, normalize
from src.matching.pair_matcher import match_team, match_pair

logger = logging.getLogger(__name__)

# Module-level singleton (created on first call)
_resolver: Optional[TeamResolver] = None


def _get_resolver(cache_dir: Optional[Path] = None) -> TeamResolver:
    global _resolver
    if _resolver is None:
        cache_path = (cache_dir / "team_resolver_cache.json") if cache_dir else None
        _resolver = TeamResolver(cache_path=cache_path, auto_refresh=cache_dir is None)
    return _resolver


def match_markets(
    markets: list,
    scout_queue: dict,
    cache_dir: Optional[Path] = None,
) -> list[dict]:
    """Match Polymarket markets to scout entries.

    Returns list of dicts: {"market": m, "scout_entry": entry_copy, "scout_key": key}
    Same format as old market_matcher.match_batch().
    """
    resolver = _get_resolver(cache_dir)
    matched = []
    used_keys: set[str] = set()

    for market in markets:
        slug = (getattr(market, "slug", "") or "").lower()
        question = (getattr(market, "question", "") or "").lower()
        market_sport = classify_sport(market)
        slug_parts = parse_slug(slug)
        slug_tokens = extract_slug_tokens(slug)

        # Resolve slug abbreviations to names
        resolved_names: list[str] = []
        for token in slug_parts.team_tokens:
            name = resolver.resolve(token)
            if name:
                resolved_names.append(name)

        best_match = None
        best_confidence = 0.0
        best_key = ""
        candidates: list[tuple[str, dict, float]] = []

        for key, entry in scout_queue.items():
            if entry.get("entered") or key in used_keys:
                continue

            entry_sport = classify_entry(entry)
            if not sports_compatible(market_sport, entry_sport):
                continue

            entry_a = entry.get("team_a", "")
            entry_b = entry.get("team_b", "")
            if not entry_a or not entry_b:
                continue

            abbrev_a = (entry.get("abbrev_a") or "").lower()
            abbrev_b = (entry.get("abbrev_b") or "").lower()
            short_a = (entry.get("short_a") or "").lower()
            short_b = (entry.get("short_b") or "").lower()

            confidence = 0.0

            # Layer 1: Abbreviation in slug tokens (both must match)
            if abbrev_a and abbrev_b:
                if abbrev_a in slug_tokens and abbrev_b in slug_tokens:
                    confidence = 1.0

            # Layer 2: Resolved slug names match entry names
            if confidence < 0.9 and len(resolved_names) >= 2:
                is_match, conf = match_pair(
                    (resolved_names[0], resolved_names[1]),
                    (entry_a, entry_b),
                )
                if is_match:
                    confidence = max(confidence, conf)

            # Layer 3: Short names in question/slug
            if confidence < 0.9:
                if short_a and short_b:
                    if ((short_a in question or short_a in slug) and
                            (short_b in question or short_b in slug)):
                        confidence = max(confidence, 0.90)

            # Layer 4: Full name in question
            if confidence < 0.85:
                norm_a = normalize(entry_a)
                norm_b = normalize(entry_b)
                if norm_a and norm_b:
                    if ((norm_a in question or norm_a in slug) and
                            (norm_b in question or norm_b in slug)):
                        confidence = max(confidence, 0.85)

            # Layer 5: Fuzzy on question text
            if confidence < 0.80:
                norm_a = normalize(entry_a)
                norm_b = normalize(entry_b)
                if len(norm_a) >= 4 and len(norm_b) >= 4:
                    from rapidfuzz import fuzz
                    score_a = max(
                        fuzz.token_sort_ratio(norm_a, question),
                        fuzz.partial_ratio(norm_a, question),
                    )
                    score_b = max(
                        fuzz.token_sort_ratio(norm_b, question),
                        fuzz.partial_ratio(norm_b, question),
                    )
                    if score_a >= 65 and score_b >= 65:
                        fuzzy_conf = min(score_a, score_b) / 100.0
                        if fuzzy_conf >= 0.80:
                            confidence = max(confidence, fuzzy_conf)

            if confidence > 0.0:
                candidates.append((key, entry, confidence))
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = entry
                best_key = key

        # Doubleheader: same team pair, pick earliest
        if len(candidates) > 1 and best_match:
            team_pair = frozenset([
                best_match.get("team_a", "").lower(),
                best_match.get("team_b", "").lower(),
            ])
            same_pair = [
                (k, e, c) for k, e, c in candidates
                if frozenset([e.get("team_a", "").lower(),
                              e.get("team_b", "").lower()]) == team_pair
            ]
            if len(same_pair) > 1:
                same_pair.sort(key=lambda x: x[1].get("match_time", ""))
                best_key, best_match, best_confidence = same_pair[0]

        # Threshold
        if best_match and best_confidence >= 0.60:
            entry_copy = dict(best_match)
            entry_copy["matched"] = True
            entry_copy["match_confidence"] = best_confidence
            matched.append({
                "market": market,
                "scout_entry": entry_copy,
                "scout_key": best_key,
            })
            used_keys.add(best_key)
            logger.debug("Matched [%.2f]: %s -> %s vs %s",
                         best_confidence, slug[:40],
                         best_match.get("team_a", ""),
                         best_match.get("team_b", ""))

    if matched:
        logger.info("matching: %d/%d markets matched", len(matched), len(markets))

    return matched
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_matching_pipeline.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/matching/__init__.py tests/test_matching_pipeline.py
git commit -m "feat(matching): implement match_markets pipeline with 5-layer matching"
```

---

### Task 6: Fix scout_scheduler bug + delete old matching methods

**Files:**
- Modify: `src/scout_scheduler.py` — add abbrev fields to entry dict, delete match_market() and match_markets_batch()

- [ ] **Step 1: Add missing fields to run_scout() entry dict**

In `src/scout_scheduler.py`, find the entry dict in `run_scout()` (around line 371-387) and add the 4 missing fields:

```python
# After "tags": match.get("tags", []),
# ADD these 4 lines:
"abbrev_a": match.get("abbrev_a", ""),
"abbrev_b": match.get("abbrev_b", ""),
"short_a": match.get("short_a", ""),
"short_b": match.get("short_b", ""),
```

Apply the same fix to `run_daily_listing()` entry dict (around line 216-232).

- [ ] **Step 2: Delete match_market() and match_markets_batch()**

Delete `match_market()` (lines ~406-445) and `match_markets_batch()` (lines ~284-329) from `scout_scheduler.py`. These are replaced by `src.matching.match_markets()`.

- [ ] **Step 3: Verify no internal references**

Run: `python -c "from src.scout_scheduler import ScoutScheduler; print('OK')"`
Expected: OK (no import errors)

- [ ] **Step 4: Commit**

```bash
git add src/scout_scheduler.py
git commit -m "fix(scout): save abbrev/short fields to queue, remove old matching methods"
```

---

### Task 7: Integration — update all imports

**Files:**
- Modify: `src/entry_gate.py` — switch to `src.matching`
- Modify: `src/odds_api.py` — switch to `src.matching.pair_matcher`
- Modify: `src/sports_data.py` — switch import
- Modify: `src/esports_data.py` — switch import
- Modify: `src/vlr_data.py` — switch import

- [ ] **Step 1: Update entry_gate.py**

Replace:
```python
from src.market_matcher import match_batch as matcher_match_batch, AliasStore
```
With:
```python
from src.matching import match_markets as matcher_match_batch
```

Remove `self._alias_store = AliasStore()` from `__init__`.

Update the call at line ~337 from:
```python
matched_markets = matcher_match_batch(markets, self.scout._queue, self._alias_store)
```
To:
```python
matched_markets = matcher_match_batch(markets, self.scout._queue)
```

- [ ] **Step 2: Update odds_api.py**

Replace:
```python
from src.team_matcher import find_best_event_match, match_team
```
With:
```python
from src.matching.pair_matcher import find_best_event_match, match_team
```

- [ ] **Step 3: Update sports_data.py, esports_data.py, vlr_data.py**

In each file, replace:
```python
from src.team_matcher import match_team
```
With:
```python
from src.matching.pair_matcher import match_team
```

- [ ] **Step 4: Verify all imports work**

Run: `python -c "from src.entry_gate import EntryGate; from src.odds_api import OddsAPIClient; from src.sports_data import SportsDataClient; from src.esports_data import EsportsDataClient; print('ALL OK')"`
Expected: ALL OK

- [ ] **Step 5: Commit**

```bash
git add src/entry_gate.py src/odds_api.py src/sports_data.py src/esports_data.py src/vlr_data.py
git commit -m "refactor: wire all modules to src.matching, remove old import paths"
```

---

### Task 8: Delete old files + migrate tests

**Files:**
- Delete: `src/market_matcher.py`
- Delete: `src/team_matcher.py`
- Modify: `tests/test_market_matcher.py` — update imports to new module

- [ ] **Step 1: Update test_market_matcher.py to use new imports**

Replace imports at top:
```python
from src.matching import match_markets
from src.matching.slug_parser import extract_slug_tokens
from src.matching.sport_classifier import classify_sport, sports_compatible
from src.matching.team_resolver import TeamResolver
```

Update `TestMatchBatch` tests to call `match_markets()` instead of `match_batch()`. The `match_markets()` takes `(markets, queue, cache_dir=tmp_path)` instead of `(markets, queue, alias_store)`.

Update `TestAliasStore` to `TestTeamResolver` using `TeamResolver(cache_path=..., auto_refresh=False)`.

- [ ] **Step 2: Delete old files**

```bash
git rm src/market_matcher.py src/team_matcher.py
```

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short 2>&1 | head -80`

Fix any remaining import errors. Common issues:
- Other test files may import from old modules
- Search: `grep -r "market_matcher\|team_matcher" tests/`

- [ ] **Step 4: Run import validation**

Run: `python -c "from src.main import main; print('Main module OK')"`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: delete old market_matcher.py and team_matcher.py, migrate all tests"
```

---

### Task 9: Smoke test with real data

- [ ] **Step 1: Run matching on current scout queue**

```bash
python -c "
import json
from pathlib import Path
from src.matching import match_markets

# Load real scout queue
sq = json.loads(Path('logs/scout_queue.json').read_text(encoding='utf-8'))

# Create fake markets from known slugs to test
from dataclasses import dataclass
@dataclass
class M:
    condition_id: str = ''
    question: str = ''
    slug: str = ''
    sport_tag: str = ''
    tags: list = None
    def __post_init__(self):
        self.tags = self.tags or []

# Test with a few known patterns
tests = [
    M(slug='nba-lal-bos-2026-04-05', question='Will the Lakers beat the Celtics?'),
    M(slug='cs2-hero-nip-2026-04-03', question='Counter-Strike: Heroic vs NIP'),
    M(slug='mlb-nyy-bos-2026-04-05', question='New York Yankees vs Boston Red Sox'),
]
results = match_markets(tests, sq, cache_dir=Path('logs'))
print(f'Matched: {len(results)}/{len(tests)}')
for r in results:
    print(f'  {r[\"scout_key\"][:50]} conf={r[\"scout_entry\"][\"match_confidence\"]:.2f}')
"
```

- [ ] **Step 2: Verify improvement over baseline**

The baseline was 75/1929 (3.9%). After this change:
- All 218 scout entries should now have working abbreviation matching
- Expected: significant increase in match rate once bot runs with real Polymarket data

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: matching system v2 complete — single pipeline replaces 3 old systems"
```
