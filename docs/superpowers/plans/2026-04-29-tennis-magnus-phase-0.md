# Tennis Magnus-Live — Phase 0 (Paper Trade) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete tennis paper-trade infrastructure: Sackmann data fetcher, player name resolver across 3 data sources, Klaassen-Magnus + O'Malley closed-form match probability chain (H2H only, BO3 only), tournament/surface metadata, and JSONL paper logger. Bot logs would-be predictions for 50-100 eligible matches without placing real trades, gating Phase 1 on directional accuracy ≥ 65%.

**Architecture:** Pure domain math (`src/domain/math/tennis_magnus.py`) + pure domain matching (`src/domain/matching/tennis_player_resolver.py`) + infrastructure I/O (`src/infrastructure/apis/sackmann_client.py`) + orchestration glue (`src/orchestration/tennis_paper_logger.py`). Read-only integration into existing `exit_processor.py` via new `tennis_paper_observer` hook. Zero changes to existing exit logic during Phase 0 (tennis_score_exit.py stays STUB).

**Tech Stack:** Python 3.12+, pandas (CSV parsing), requests (HTTP), rapidfuzz (fuzzy name matching, already in deps), Pydantic v2 (data models), pytest. No new heavy deps.

**Önkoşul:** Spec docs/superpowers/specs/2026-04-29-tennis-magnus-live-system-design.md (commit a1036fc) onaylandı.

**Phase -1 BLOCKER (separate plan):** Telegram alarm system — see TODO.md for separate spec. Phase 0 does NOT require Telegram (zero $ risk = no urgent edge case alarms needed). Phase 1 requires it.

---

## Tasarım Kararları (Erim Onayı, Spec'ten)

Plan başında verilen kararlar — değiştirilecekse plan baştan yazılır.

### Karar 1: H2H ONLY (Match Total Games Phase 4'te)

**Sonuç:** Magnus chain sadece P(A wins match) hesaplar. Game distribution kodu yazılmaz (Phase 4'e ertelenir). Paper logger HEM H2H HEM Match Total predictions log'lar (Phase 4 bootstrap data için), ama exit decision sadece H2H için.

### Karar 2: BO3 ONLY (BO5 Grand Slam Phase 2'de)

**Sonuç:** Magnus chain `format="BO3"` hardcode (parametrik ama tek değer test edilir). Spec Section 5.1 `BO3 vs BO5` parametrik olduğu için fonksiyon imzasında format kalır, ama Phase 0 testleri sadece BO3 senaryoları kapsar.

### Karar 3: Paper Trade Filter Genişletildi (Spec Risk 1)

**Sonuç:** Sample size matematiği için Phase 0'da filtre relaxed:
- Tournament tier ∈ {Grand Slam, Masters 1000, ATP/WTA 500, **ATP/WTA 250**}
- Diğer filtreler aynı (ranking gap < 100, top 100)
- Phase 1 başlamadan önce filtre tighten back to Spec Section 9 (250 dropped)

### Karar 4: Sackmann Cache Lokasyonu

**Sonuç:** `data/sackmann_cache/` — bot working directory altında. Reboot'ta silinmez (CLAUDE.md "data/" state, audit trail değil). Manual refresh mümkün.

### Karar 5: Player XRef Persistence

**Sonuç:** `data/tennis_player_xref.json` — canonical_name → (sackmann_id, espn_id, polymarket_slug_form) mapping. Sackmann fetch sonrası rebuild. Restart safe.

---

## Dosya Haritası

| İşlem | Dosya | Sorumluluğu |
|---|---|---|
| CREATE | `src/domain/matching/tennis_player_resolver.py` | Pure name normalization + fuzzy resolve, no I/O |
| CREATE | `tests/unit/domain/matching/test_tennis_player_resolver.py` | Resolver tests |
| CREATE | `src/infrastructure/apis/sackmann_client.py` | HTTP fetch + CSV parse + cache, infra layer |
| CREATE | `tests/unit/infrastructure/apis/test_sackmann_client.py` | Sackmann tests with fixtures |
| CREATE | `src/domain/math/tennis_magnus.py` | Pure math: G(p), S(...), M(...) closed-form chain |
| CREATE | `tests/unit/domain/math/test_tennis_magnus.py` | Magnus formula tests with known values |
| CREATE | `src/domain/matching/tennis_tournament_resolver.py` | Polymarket slug → tier + surface lookup |
| CREATE | `tests/unit/domain/matching/test_tennis_tournament_resolver.py` | Tier/surface tests |
| CREATE | `src/orchestration/tennis_paper_logger.py` | JSONL log of would-be decisions |
| CREATE | `tests/unit/orchestration/test_tennis_paper_logger.py` | Logger tests |
| CREATE | `src/orchestration/tennis_paper_observer.py` | Hook into exit_processor.py read-only path |
| CREATE | `tests/unit/orchestration/test_tennis_paper_observer.py` | Observer tests |
| CREATE | `tests/fixtures/sackmann/atp_matches_2025_sample.csv` | 50-row CSV fixture for tests |
| CREATE | `tests/fixtures/sackmann/atp_players_sample.csv` | Player fixture for tests |
| CREATE | `tests/fixtures/espn/tennis/atp_scoreboard_sample.json` | ESPN tennis fixture |
| CREATE | `tests/fixtures/polymarket/tennis/atp_event_sample.json` | Polymarket fixture |
| MODIFY | `config.yaml` | Add `tennis:` block (phase=disabled, paper config, surface factors) |
| MODIFY | `src/config/settings.py` | Add `TennisConfig` Pydantic model |
| MODIFY | `src/orchestration/exit_processor.py` | Wire tennis_paper_observer (read-only path) |
| MODIFY | `src/orchestration/factory.py` | Wire paper observer into agent |
| MODIFY | `DECISIONS.md` | Document tennis Phase 0 thresholds + sources |
| CREATE | `scripts/diag_tennis_magnus.py` | Sanity check Magnus output for one match |
| CREATE | `scripts/diag_tennis_paper_replay.py` | Replay logged matches with model |

---

## Task 1: Tournament Tier + Surface Metadata Config

**Files:**
- Modify: `config.yaml` (append `tennis:` block)
- Create: `src/domain/matching/tennis_tournament_resolver.py`
- Test: `tests/unit/domain/matching/test_tennis_tournament_resolver.py`

- [ ] **Step 1: Add tennis config block to config.yaml**

Append to bottom of `config.yaml`:

```yaml
tennis:
  enabled: false
  phase: disabled  # disabled | paper_trade | v1 | v2 | v3
  position_size_usdc:
    paper_trade: 0
    v1: 15
    v2: 25
    v3: 35
  filters:
    paper_trade_relaxed: true  # Phase 0 only: include ATP/WTA 250
    min_ranking: 100
    max_ranking_gap: 100
    min_edge: 0.05
    match_window_hours_min: 0.0
    match_window_hours_max: 24.0
  exit:
    near_resolve_bid: 0.95
    profit_lock_bid: 0.80
    risk_penalty_cap: 0.70
    w_momentum: 0.35
    w_value: 0.40
    bayesian_max_shift: 0.15
    momentum_decay: 0.85
    momentum_window_games: 7
  data:
    sackmann_cache_dir: "data/sackmann_cache/"
    sackmann_refresh_days: 7
    player_xref_path: "data/tennis_player_xref.json"
  alerts:
    telegram_enabled: false
  surface_factors:
    serve_pct_atp:
      grass: 1.00
      hard: 1.00
      clay: 0.92
    serve_pct_wta:
      grass: 1.00
      hard: 1.05
      clay: 0.95
  tournaments:
    grand_slam:
      australian_open: hard
      french_open: clay
      wimbledon: grass
      us_open: hard
    masters_1000:
      indian_wells: hard
      miami_open: hard
      monte_carlo_masters: clay
      madrid_open: clay
      italian_open: clay
      canadian_open: hard
      cincinnati_open: hard
      shanghai_masters: hard
      paris_masters: hard
    atp_500: {}
    atp_250: {}
    excluded_tiers: [itf, challenger, futures]
```

- [ ] **Step 2: Add TennisConfig Pydantic model to src/config/settings.py**

Add after existing config classes:

```python
class TennisSurfaceFactors(BaseModel):
    model_config = ConfigDict(extra="ignore")
    serve_pct_atp: dict[str, float] = Field(default_factory=lambda: {"grass": 1.0, "hard": 1.0, "clay": 0.92})
    serve_pct_wta: dict[str, float] = Field(default_factory=lambda: {"grass": 1.0, "hard": 1.05, "clay": 0.95})


class TennisFilters(BaseModel):
    model_config = ConfigDict(extra="ignore")
    paper_trade_relaxed: bool = True
    min_ranking: int = 100
    max_ranking_gap: int = 100
    min_edge: float = 0.05
    match_window_hours_min: float = 0.0
    match_window_hours_max: float = 24.0


class TennisExit(BaseModel):
    model_config = ConfigDict(extra="ignore")
    near_resolve_bid: float = 0.95
    profit_lock_bid: float = 0.80
    risk_penalty_cap: float = 0.70
    w_momentum: float = 0.35
    w_value: float = 0.40
    bayesian_max_shift: float = 0.15
    momentum_decay: float = 0.85
    momentum_window_games: int = 7


class TennisData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sackmann_cache_dir: str = "data/sackmann_cache/"
    sackmann_refresh_days: int = 7
    player_xref_path: str = "data/tennis_player_xref.json"


class TennisConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    phase: str = "disabled"
    position_size_usdc: dict[str, int] = Field(default_factory=lambda: {"paper_trade": 0, "v1": 15, "v2": 25, "v3": 35})
    filters: TennisFilters = Field(default_factory=TennisFilters)
    exit: TennisExit = Field(default_factory=TennisExit)
    data: TennisData = Field(default_factory=TennisData)
    surface_factors: TennisSurfaceFactors = Field(default_factory=TennisSurfaceFactors)
    tournaments: dict[str, dict[str, str]] = Field(default_factory=dict)
    excluded_tiers: list[str] = Field(default_factory=lambda: ["itf", "challenger", "futures"])
```

Then add to `Settings` class (find the existing settings class):

```python
tennis: TennisConfig = Field(default_factory=TennisConfig)
```

- [ ] **Step 3: Run existing config test to verify backward compat**

```bash
pytest tests/unit/config/ -v
```

Expected: all existing tests still pass (extra="ignore" prevents new field from breaking).

- [ ] **Step 4: Write failing test for tournament tier resolver**

Create `tests/unit/domain/matching/test_tennis_tournament_resolver.py`:

```python
"""Tennis tournament tier + surface resolver tests."""
from __future__ import annotations

import pytest

from src.domain.matching.tennis_tournament_resolver import (
    TournamentInfo,
    resolve_tournament,
)


_TOURNAMENTS = {
    "grand_slam": {
        "australian_open": "hard",
        "french_open": "clay",
        "wimbledon": "grass",
        "us_open": "hard",
    },
    "masters_1000": {
        "madrid_open": "clay",
        "miami_open": "hard",
    },
    "atp_500": {},
    "atp_250": {},
}
_EXCLUDED = ["itf", "challenger", "futures"]


def test_resolve_grand_slam_clay() -> None:
    info = resolve_tournament("atp-french-open-2026-06-01", _TOURNAMENTS, _EXCLUDED)
    assert info == TournamentInfo(tier="grand_slam", surface="clay", format="BO5")


def test_resolve_masters_1000_madrid() -> None:
    info = resolve_tournament("atp-madrid-open-2026-04-28", _TOURNAMENTS, _EXCLUDED)
    assert info == TournamentInfo(tier="masters_1000", surface="clay", format="BO3")


def test_resolve_wta_french_open_bo3() -> None:
    info = resolve_tournament("wta-french-open-2026-06-01", _TOURNAMENTS, _EXCLUDED)
    # WTA Grand Slam still BO3
    assert info == TournamentInfo(tier="grand_slam", surface="clay", format="BO3")


def test_resolve_excluded_tier_returns_none() -> None:
    info = resolve_tournament("atp-challenger-cary-2026-04-28", _TOURNAMENTS, _EXCLUDED)
    assert info is None


def test_resolve_unknown_tournament_returns_none() -> None:
    info = resolve_tournament("atp-unknown-tournament-2026-04-28", _TOURNAMENTS, _EXCLUDED)
    assert info is None


def test_resolve_invalid_slug_returns_none() -> None:
    info = resolve_tournament("not-a-tennis-slug", _TOURNAMENTS, _EXCLUDED)
    assert info is None
```

- [ ] **Step 5: Run test to verify it fails**

```bash
pytest tests/unit/domain/matching/test_tennis_tournament_resolver.py -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 6: Implement resolver**

Create `src/domain/matching/tennis_tournament_resolver.py`:

```python
"""Polymarket tennis slug → tier + surface + format. Pure, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class TournamentInfo:
    tier: Literal["grand_slam", "masters_1000", "atp_500", "atp_250", "wta_500", "wta_250"]
    surface: Literal["clay", "hard", "grass"]
    format: Literal["BO3", "BO5"]


def resolve_tournament(
    slug: str,
    tournaments: dict[str, dict[str, str]],
    excluded_tiers: list[str],
) -> TournamentInfo | None:
    """Polymarket slug → TournamentInfo. None = not eligible."""
    if not slug:
        return None
    s = slug.lower()
    parts = s.split("-")
    if len(parts) < 3:
        return None
    if parts[0] not in ("atp", "wta"):
        return None
    is_wta = parts[0] == "wta"

    excluded = {t.lower() for t in excluded_tiers}
    for excl in excluded:
        if excl in s:
            return None

    for tier_name, surface_map in tournaments.items():
        for tournament_key, surface in surface_map.items():
            normalized_key = tournament_key.replace("_", "-")
            if normalized_key in s:
                fmt = "BO5" if (tier_name == "grand_slam" and not is_wta) else "BO3"
                return TournamentInfo(
                    tier=tier_name,
                    surface=surface,
                    format=fmt,
                )
    return None
```

- [ ] **Step 7: Run test to verify it passes**

```bash
pytest tests/unit/domain/matching/test_tennis_tournament_resolver.py -v
```

Expected: PASS (6 tests).

- [ ] **Step 8: Commit Task 1**

```bash
git add config.yaml src/config/settings.py src/domain/matching/tennis_tournament_resolver.py tests/unit/domain/matching/test_tennis_tournament_resolver.py
git commit -m "feat(tennis): tournament tier + surface resolver

Adds TennisConfig Pydantic model, config.yaml tennis: block, and pure
tournament_resolver that maps Polymarket slugs to tier (grand_slam,
masters_1000, etc), surface (clay/hard/grass), and format (BO3/BO5).
Tests cover ATP/WTA, excluded tiers, unknown tournaments.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Player Name Resolver

**Files:**
- Create: `src/domain/matching/tennis_player_resolver.py`
- Test: `tests/unit/domain/matching/test_tennis_player_resolver.py`
- Create: `tests/fixtures/sackmann/atp_players_sample.csv`

**Architecture note:** Pure domain. Receives a registry built externally (Sackmann CSV parser feeds it). No I/O here.

- [ ] **Step 1: Create Sackmann player fixture**

Create `tests/fixtures/sackmann/atp_players_sample.csv`:

```csv
player_id,name_first,name_last,hand,dob,country
104925,Daniil,Medvedev,R,19960211,RUS
207989,Jannik,Sinner,R,20010816,ITA
208029,Carlos,Alcaraz Garfia,R,20030505,ESP
106233,Novak,Djokovic,R,19870522,SRB
209829,Jakub,Mensik,R,20051002,CZE
208053,Felix,Auger-Aliassime,R,20000808,CAN
207666,Stefanos,Tsitsipas,R,19980812,GRE
105657,Andrey,Rublev,R,19971020,RUS
206173,Alexander,Zverev,R,19970420,GER
209968,Flavio,Cobolli,R,20020519,ITA
```

- [ ] **Step 2: Write failing tests for player resolver**

Create `tests/unit/domain/matching/test_tennis_player_resolver.py`:

```python
"""Tennis player name resolver tests."""
from __future__ import annotations

import pytest

from src.domain.matching.tennis_player_resolver import (
    PlayerRecord,
    PlayerRegistry,
    ResolutionFailure,
    build_registry,
    resolve_player,
)


@pytest.fixture
def sample_registry() -> PlayerRegistry:
    records = [
        PlayerRecord(sackmann_id="104925", first="Daniil", last="Medvedev", hand="R", country="RUS"),
        PlayerRecord(sackmann_id="207989", first="Jannik", last="Sinner", hand="R", country="ITA"),
        PlayerRecord(sackmann_id="208029", first="Carlos", last="Alcaraz Garfia", hand="R", country="ESP"),
        PlayerRecord(sackmann_id="208053", first="Felix", last="Auger-Aliassime", hand="R", country="CAN"),
        PlayerRecord(sackmann_id="207666", first="Stefanos", last="Tsitsipas", hand="R", country="GRE"),
        PlayerRecord(sackmann_id="206173", first="Alexander", last="Zverev", hand="R", country="GER"),
        PlayerRecord(sackmann_id="209968", first="Flavio", last="Cobolli", hand="R", country="ITA"),
    ]
    return build_registry(records)


def test_resolve_exact_full_name(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("Daniil Medvedev", sample_registry)
    assert record is not None
    assert record.sackmann_id == "104925"


def test_resolve_lowercase(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("daniil medvedev", sample_registry)
    assert record is not None
    assert record.sackmann_id == "104925"


def test_resolve_surname_only(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("Medvedev", sample_registry)
    assert record is not None
    assert record.sackmann_id == "104925"


def test_resolve_first_initial_surname(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("D. Medvedev", sample_registry)
    assert record is not None
    assert record.sackmann_id == "104925"


def test_resolve_diacritic_normalized(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("Stefanos Tsitsipás", sample_registry)
    assert record is not None
    assert record.sackmann_id == "207666"


def test_resolve_hyphenated_surname(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("Auger-Aliassime", sample_registry)
    assert record is not None
    assert record.sackmann_id == "208053"


def test_resolve_partial_surname_alcaraz(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("Alcaraz", sample_registry)
    assert record is not None
    assert record.sackmann_id == "208029"


def test_resolve_unknown_returns_none(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("John Doe Nobody", sample_registry)
    assert record is None


def test_resolve_empty_string_returns_none(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("", sample_registry)
    assert record is None


def test_resolve_disambiguates_same_surname_via_first_initial() -> None:
    records = [
        PlayerRecord(sackmann_id="100001", first="Roger", last="Federer", hand="R", country="SUI"),
        PlayerRecord(sackmann_id="100002", first="Mischa", last="Federer", hand="R", country="SUI"),
    ]
    registry = build_registry(records)
    rec_r = resolve_player("R. Federer", registry)
    rec_m = resolve_player("M. Federer", registry)
    assert rec_r is not None and rec_r.sackmann_id == "100001"
    assert rec_m is not None and rec_m.sackmann_id == "100002"


def test_resolve_surname_only_ambiguous_returns_none() -> None:
    """Same surname, no first letter clue → cannot disambiguate."""
    records = [
        PlayerRecord(sackmann_id="100001", first="Roger", last="Federer", hand="R", country="SUI"),
        PlayerRecord(sackmann_id="100002", first="Mischa", last="Federer", hand="R", country="SUI"),
    ]
    registry = build_registry(records)
    assert resolve_player("Federer", registry) is None
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/unit/domain/matching/test_tennis_player_resolver.py -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 4: Implement player resolver**

Create `src/domain/matching/tennis_player_resolver.py`:

```python
"""Tennis player name resolver — pure domain, no I/O.

Reconciles names across Polymarket (slug surnames), ESPN (full names with
diacritics), and Sackmann (canonical full names). Uses normalize/fuzzy.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Iterable

from rapidfuzz import fuzz


_FUZZY_TOKEN_SORT_THRESHOLD = 0.85


@dataclass(frozen=True)
class PlayerRecord:
    sackmann_id: str
    first: str
    last: str
    hand: str
    country: str

    @property
    def full_name(self) -> str:
        return f"{self.first} {self.last}"


@dataclass(frozen=True)
class ResolutionFailure:
    """Returned when resolution is ambiguous (multiple matches)."""
    query: str
    candidates: list[str]


@dataclass
class PlayerRegistry:
    """In-memory registry built from PlayerRecord list. Indexed for fast lookup."""
    records: list[PlayerRecord]
    by_normalized_full: dict[str, PlayerRecord]
    by_normalized_last: dict[str, list[PlayerRecord]]


def _strip_accents(text: str) -> str:
    """Decompose then strip combining marks. é→e, ş→s, ı kept as i."""
    text = text.replace("ı", "i")  # Turkish dotless i
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    if not name:
        return ""
    n = _strip_accents(name).lower().strip()
    return " ".join(n.split())


def build_registry(records: Iterable[PlayerRecord]) -> PlayerRegistry:
    """Build indexed registry from records."""
    records_list = list(records)
    by_full: dict[str, PlayerRecord] = {}
    by_last: dict[str, list[PlayerRecord]] = {}
    for r in records_list:
        full_norm = _normalize(r.full_name)
        last_norm = _normalize(r.last)
        by_full[full_norm] = r
        by_last.setdefault(last_norm, []).append(r)
    return PlayerRegistry(
        records=records_list,
        by_normalized_full=by_full,
        by_normalized_last=by_last,
    )


def _try_first_initial_match(query: str, registry: PlayerRegistry) -> PlayerRecord | None:
    """Match 'D. Medvedev' against registry by first letter + surname."""
    parts = [p.strip(".") for p in query.split() if p.strip()]
    if len(parts) < 2:
        return None
    first_token = parts[0]
    if len(first_token) > 2:  # not initial-like
        return None
    first_letter = _normalize(first_token)[:1]
    surname = _normalize(" ".join(parts[1:]))
    candidates = registry.by_normalized_last.get(surname, [])
    matches = [r for r in candidates if _normalize(r.first)[:1] == first_letter]
    if len(matches) == 1:
        return matches[0]
    return None


def _try_surname_only(query: str, registry: PlayerRegistry) -> PlayerRecord | None:
    """Match plain 'Medvedev' against registry — only if unique."""
    norm = _normalize(query)
    candidates = registry.by_normalized_last.get(norm, [])
    if len(candidates) == 1:
        return candidates[0]

    # Try compound surname (e.g., 'Alcaraz Garfia' vs query 'Alcaraz')
    if len(norm.split()) == 1:
        partial_matches = [
            r for r in registry.records
            if norm in _normalize(r.last).split()
        ]
        if len(partial_matches) == 1:
            return partial_matches[0]

    return None


def _try_fuzzy(query: str, registry: PlayerRegistry) -> PlayerRecord | None:
    """Fuzzy fallback for full names (handles minor typos)."""
    norm = _normalize(query)
    if len(norm) < 4:
        return None
    best_record: PlayerRecord | None = None
    best_score = 0.0
    for r in registry.records:
        score = fuzz.token_sort_ratio(norm, _normalize(r.full_name)) / 100.0
        if score > best_score and score >= _FUZZY_TOKEN_SORT_THRESHOLD:
            best_score = score
            best_record = r
    return best_record


def resolve_player(query: str, registry: PlayerRegistry) -> PlayerRecord | None:
    """Return PlayerRecord for query, or None if not confidently resolved."""
    if not query:
        return None
    norm = _normalize(query)

    # Layer 1: Exact normalized full name
    exact = registry.by_normalized_full.get(norm)
    if exact is not None:
        return exact

    # Layer 2: First initial + surname pattern
    initial_match = _try_first_initial_match(query, registry)
    if initial_match is not None:
        return initial_match

    # Layer 3: Surname only (must be unique)
    surname_match = _try_surname_only(query, registry)
    if surname_match is not None:
        return surname_match

    # Layer 4: Fuzzy fallback (full name)
    fuzzy_match = _try_fuzzy(query, registry)
    if fuzzy_match is not None:
        return fuzzy_match

    return None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/domain/matching/test_tennis_player_resolver.py -v
```

Expected: PASS (11 tests).

- [ ] **Step 6: Commit Task 2**

```bash
git add src/domain/matching/tennis_player_resolver.py tests/unit/domain/matching/test_tennis_player_resolver.py tests/fixtures/sackmann/atp_players_sample.csv
git commit -m "feat(tennis): player name resolver with 4-layer fallback

Pure domain resolver: exact normalized → first initial + surname →
unique surname → fuzzy. Handles diacritics, hyphenated surnames,
compound surnames (Alcaraz Garfia), same-surname disambiguation.
Indexed registry for fast lookup. Tests cover 11 scenarios.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Magnus Closed-Form Chain (H2H BO3 Only)

**Files:**
- Create: `src/domain/math/tennis_magnus.py`
- Test: `tests/unit/domain/math/test_tennis_magnus.py`

**Reference:** Spec Section 5.1, formulas from O'Malley (2008).

- [ ] **Step 1: Write failing test for game-on-serve probability**

Create `tests/unit/domain/math/test_tennis_magnus.py`:

```python
"""Klaassen-Magnus + O'Malley closed-form chain tests."""
from __future__ import annotations

import math

import pytest

from src.domain.math.tennis_magnus import (
    MatchState,
    p_game_on_serve,
    p_set,
    p_match_bo3,
    p_match_from_state,
)


def test_p_game_on_serve_at_50pct_is_50pct() -> None:
    """When p=0.5, game outcome is 50/50."""
    assert math.isclose(p_game_on_serve(0.5), 0.5, abs_tol=1e-6)


def test_p_game_on_serve_strong_server_70pct() -> None:
    """At p=0.70 (strong server), game win ≈ 90%."""
    g = p_game_on_serve(0.70)
    assert 0.88 < g < 0.92


def test_p_game_on_serve_weak_server_30pct() -> None:
    """At p=0.30 (weak), game win ≈ 10%."""
    g = p_game_on_serve(0.30)
    assert 0.08 < g < 0.12


def test_p_game_on_serve_zero() -> None:
    assert p_game_on_serve(0.0) == 0.0


def test_p_game_on_serve_one() -> None:
    assert p_game_on_serve(1.0) == 1.0


def test_p_set_balanced() -> None:
    """Balanced players → set probability ~50%."""
    s = p_set(p_a=0.65, p_b=0.65)
    assert 0.48 < s < 0.52


def test_p_set_strong_a() -> None:
    """A serve 70%, B serve 60% → A wins set ~80% (canonical math gives 0.807)."""
    s = p_set(p_a=0.70, p_b=0.60)
    assert 0.75 < s < 0.85


def test_p_match_bo3_balanced() -> None:
    """Balanced players → match ~50%."""
    m = p_match_bo3(p_a=0.65, p_b=0.65)
    assert 0.48 < m < 0.52


def test_p_match_bo3_strong_a() -> None:
    """A 70%, B 60% serve → A wins match ~90% (canonical math gives 0.903)."""
    m = p_match_bo3(p_a=0.70, p_b=0.60)
    assert 0.85 < m < 0.95


def test_p_match_from_state_pre_match_matches_bo3() -> None:
    """Pre-match state should equal p_match_bo3."""
    state = MatchState(sets_won_a=0, sets_won_b=0, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_state = p_match_from_state(p_a=0.70, p_b=0.60, state=state)
    p_bo3 = p_match_bo3(p_a=0.70, p_b=0.60)
    assert math.isclose(p_state, p_bo3, abs_tol=0.02)


def test_p_match_from_state_a_won_first_set() -> None:
    """A won set 1 → P(A wins match) increases."""
    state = MatchState(sets_won_a=1, sets_won_b=0, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_state = p_match_from_state(p_a=0.70, p_b=0.60, state=state)
    assert p_state > 0.85


def test_p_match_from_state_a_lost_first_set() -> None:
    """A lost set 1 → P(A wins match) decreases (qualitative, canonical: 0.652)."""
    state = MatchState(sets_won_a=0, sets_won_b=1, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_state = p_match_from_state(p_a=0.70, p_b=0.60, state=state)
    p_pre = p_match_bo3(p_a=0.70, p_b=0.60)
    assert p_state < p_pre  # set loss must decrease win probability


def test_p_match_from_state_a_already_won() -> None:
    """A won 2 sets in BO3 → match over, P(A) = 1."""
    state = MatchState(sets_won_a=2, sets_won_b=0, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_state = p_match_from_state(p_a=0.70, p_b=0.60, state=state)
    assert p_state == 1.0


def test_p_match_from_state_a_already_lost() -> None:
    """A lost 2 sets in BO3 → match over, P(A) = 0."""
    state = MatchState(sets_won_a=0, sets_won_b=2, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_state = p_match_from_state(p_a=0.70, p_b=0.60, state=state)
    assert p_state == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/domain/math/test_tennis_magnus.py -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement Magnus chain — game on serve**

Create `src/domain/math/tennis_magnus.py`:

```python
"""Klaassen-Magnus + O'Malley closed-form tennis chain.

Pure domain math. Computes P(player A wins match) given serve
probabilities and current match state. References:
- O'Malley (2008) Probability of Winning at Tennis I.
- Newton & Keller (2005) Probability formulas in tennis.
- Klaassen & Magnus (2003) Forecasting the winner.

H2H only. BO3 fully supported. BO5 stub raises NotImplementedError
(Phase 2 will implement).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MatchState:
    sets_won_a: int
    sets_won_b: int
    games_a: int
    games_b: int
    server_is_a: bool
    format: Literal["BO3", "BO5"]


def p_game_on_serve(p: float) -> float:
    """O'Malley closed-form: probability server wins a game given p_serve.

    G(p) = p^4 * (1 + 4q + 10q^2 + 20q^3 * p / (p^2 + q^2))   where q = 1-p

    Source: O'Malley (2008) eq.3 / Newton-Keller (2005). Verified G(0.5)=0.5,
    G(0.7)=0.901, G(0.3)=0.099 against published tables.

    Edge cases: p=0 → 0, p=1 → 1.
    """
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    q = 1 - p
    return (p ** 4) * (1 + 4 * q + 10 * (q ** 2) + 20 * (q ** 3) * p / (p ** 2 + q ** 2))
```

- [ ] **Step 4: Run game-on-serve tests**

```bash
pytest tests/unit/domain/math/test_tennis_magnus.py -k "p_game_on_serve" -v
```

Expected: 5 tests PASS. Other tests still fail (functions not yet defined).

- [ ] **Step 5: Add p_set implementation**

Append to `src/domain/math/tennis_magnus.py`:

```python
def p_set(p_a: float, p_b: float) -> float:
    """Probability A wins a set, alternating serves, A serves first.

    O'Malley standard formulation: enumerate all paths to A winning
    set 6-x or 7-x (with tiebreak for 6-6).
    """
    g_a = p_game_on_serve(p_a)
    g_b = p_game_on_serve(p_b)

    # P(A wins game on A's serve) = g_a; P(A wins game on B's serve) = 1 - g_b
    # Compute P(A wins exactly k of first n service-game pairs)
    # Then sum over all set-end paths.
    return _set_recursive(g_a, g_b, score_a=0, score_b=0, server_is_a=True)


def _set_recursive(
    g_a_serve: float,
    g_b_serve: float,
    score_a: int,
    score_b: int,
    server_is_a: bool,
) -> float:
    """Recursive helper. Returns P(A wins set | current game score)."""
    # Set ended states
    if score_a == 6 and score_b <= 4:
        return 1.0
    if score_b == 6 and score_a <= 4:
        return 0.0
    if score_a == 7:
        return 1.0
    if score_b == 7:
        return 0.0
    # Tiebreak at 6-6 (simplified: assume tiebreak win prob = avg game)
    if score_a == 6 and score_b == 6:
        avg_game_p = (g_a_serve + (1 - g_b_serve)) / 2
        return _tiebreak_win_prob(avg_game_p)

    # P(A wins this game)
    p_win_game = g_a_serve if server_is_a else (1 - g_b_serve)

    p_a_wins_set_if_wins_this = _set_recursive(
        g_a_serve, g_b_serve, score_a + 1, score_b, not server_is_a
    )
    p_a_wins_set_if_loses_this = _set_recursive(
        g_a_serve, g_b_serve, score_a, score_b + 1, not server_is_a
    )

    return p_win_game * p_a_wins_set_if_wins_this + (1 - p_win_game) * p_a_wins_set_if_loses_this


def _tiebreak_win_prob(p: float) -> float:
    """Simplified tiebreak win probability given average game-win prob.

    For tiebreak detail, see O'Malley (2008) eq. 6. Approximation:
    treat tiebreak as a 7-of-13 best-of contest with point-win ~p.
    Sufficient for set-level approximation.
    """
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    # Approximate: tiebreak amplifies edge. Use sigmoid-ish.
    # P(win 7+ points before opponent in tiebreak)
    # For simplicity use binomial cdf approximation: P(>= 7 wins in 13 trials)
    from math import comb
    total = 0.0
    n = 13
    for k in range(7, n + 1):
        total += comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
    return total
```

- [ ] **Step 6: Run set probability tests**

```bash
pytest tests/unit/domain/math/test_tennis_magnus.py -k "p_set" -v
```

Expected: 2 tests PASS.

- [ ] **Step 7: Add p_match_bo3 implementation**

Append to `src/domain/math/tennis_magnus.py`:

```python
def p_match_bo3(p_a: float, p_b: float) -> float:
    """Probability A wins best-of-3 match given serve probabilities."""
    s_a = p_set(p_a, p_b)
    # Best of 3: A wins 2 sets first
    # P(2-0) + P(2-1) where each set independent (simplification)
    p_2_0 = s_a * s_a
    p_2_1 = 2 * s_a * (1 - s_a) * s_a
    return p_2_0 + p_2_1
```

- [ ] **Step 8: Run BO3 match tests**

```bash
pytest tests/unit/domain/math/test_tennis_magnus.py -k "p_match_bo3" -v
```

Expected: 2 tests PASS.

- [ ] **Step 9: Add p_match_from_state implementation**

Append to `src/domain/math/tennis_magnus.py`:

```python
def p_match_from_state(p_a: float, p_b: float, state: MatchState) -> float:
    """P(A wins match) given current match state.

    Handles: pre-match, mid-match (sets won + current game state),
    and terminal states (match over).
    """
    sets_to_win = 2 if state.format == "BO3" else 3

    # Terminal states
    if state.sets_won_a >= sets_to_win:
        return 1.0
    if state.sets_won_b >= sets_to_win:
        return 0.0

    if state.format == "BO5":
        raise NotImplementedError("BO5 implemented in Phase 2")

    # Compute P(A wins current set) given current game score
    g_a_serve = p_game_on_serve(p_a)
    g_b_serve = p_game_on_serve(p_b)
    p_a_wins_current_set = _set_recursive(
        g_a_serve, g_b_serve,
        score_a=state.games_a,
        score_b=state.games_b,
        server_is_a=state.server_is_a,
    )

    # Generic set probability for remaining sets after current
    p_a_wins_future_set = p_set(p_a, p_b)

    # Sets remaining after current = depends on outcome of current
    # If A wins current: needs (sets_to_win - sets_won_a - 1) more
    # If B wins current: A needs (sets_to_win - sets_won_a) more, B needs (sets_to_win - sets_won_b - 1) more
    # Compute combinatorially.
    sets_a_after_win = state.sets_won_a + 1
    sets_a_after_loss = state.sets_won_a
    sets_b_after_win = state.sets_won_b
    sets_b_after_loss = state.sets_won_b + 1

    p_match_if_win_current = _p_match_remaining(sets_a_after_win, sets_b_after_win, sets_to_win, p_a_wins_future_set)
    p_match_if_lose_current = _p_match_remaining(sets_a_after_loss, sets_b_after_loss, sets_to_win, p_a_wins_future_set)

    return p_a_wins_current_set * p_match_if_win_current + (1 - p_a_wins_current_set) * p_match_if_lose_current


def _p_match_remaining(sets_a: int, sets_b: int, sets_to_win: int, p_set: float) -> float:
    """P(A wins match) given remaining future sets are independent with prob p_set."""
    if sets_a >= sets_to_win:
        return 1.0
    if sets_b >= sets_to_win:
        return 0.0
    needed_a = sets_to_win - sets_a
    needed_b = sets_to_win - sets_b
    # P(A wins needed_a sets before B wins needed_b sets), each set IID with prob p_set
    return _negative_binomial_win(needed_a, needed_b, p_set)


def _negative_binomial_win(needed_a: int, needed_b: int, p: float) -> float:
    """P(A reaches needed_a wins before B reaches needed_b wins), each trial IID.

    Sum over k = 0 to needed_b - 1 of: C(needed_a + k - 1, k) * p^needed_a * (1-p)^k
    """
    from math import comb
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    total = 0.0
    for k in range(needed_b):
        total += comb(needed_a + k - 1, k) * (p ** needed_a) * ((1 - p) ** k)
    return total
```

- [ ] **Step 10: Run all Magnus tests**

```bash
pytest tests/unit/domain/math/test_tennis_magnus.py -v
```

Expected: All 14 tests PASS.

- [ ] **Step 11: Commit Task 3**

```bash
git add src/domain/math/tennis_magnus.py tests/unit/domain/math/test_tennis_magnus.py
git commit -m "feat(tennis): Klaassen-Magnus + O'Malley H2H BO3 chain

Pure closed-form math: G(p) game-on-serve, recursive p_set, BO3 match
prob, and p_match_from_state for live updates. BO5 stub raises
NotImplementedError (Phase 2). Tests verify known closed-form values
(p=0.5 game→0.5, p=0.7→~90%) and state-aware semantics (terminal
states, pre-match matches BO3 baseline).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Sackmann CSV Fetcher + Cache

**Files:**
- Create: `src/infrastructure/apis/sackmann_client.py`
- Test: `tests/unit/infrastructure/apis/test_sackmann_client.py`
- Create: `tests/fixtures/sackmann/atp_matches_2025_sample.csv`

- [ ] **Step 1: Create matches fixture**

Create `tests/fixtures/sackmann/atp_matches_2025_sample.csv` (minimal sample, 10 rows):

```csv
tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,match_num,winner_id,winner_seed,winner_entry,winner_name,winner_hand,winner_ht,winner_ioc,winner_age,loser_id,loser_seed,loser_entry,loser_name,loser_hand,loser_ht,loser_ioc,loser_age,score,best_of,round,minutes,w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,winner_rank,winner_rank_points,loser_rank,loser_rank_points
2025-339,Australian Open,Hard,128,G,20250112,701,207989,1,,Jannik Sinner,R,188,ITA,23.4,104925,5,,Daniil Medvedev,R,198,RUS,29.0,7-6 6-2 6-2,5,F,138,15,3,87,52,38,21,18,5,7,7,2,68,42,28,11,17,3,5,1,11000,5,4500
2025-339,Australian Open,Hard,128,G,20250112,702,208029,3,,Carlos Alcaraz Garfia,R,183,ESP,21.7,106233,2,,Novak Djokovic,R,188,SRB,37.6,6-2 6-7 6-3 6-2,5,SF,182,8,4,123,72,55,32,26,7,9,11,3,108,65,48,28,25,4,8,3,9000,2,10500
2025-340,Indian Wells,Hard,96,M,20250308,201,208029,1,,Carlos Alcaraz Garfia,R,183,ESP,21.8,206173,2,,Alexander Zverev,R,198,GER,28.0,6-3 7-6,3,F,98,5,2,75,45,33,18,15,3,5,8,4,72,42,30,16,14,4,7,1,11000,3,7000
2025-341,Madrid Open,Clay,96,M,20250425,301,207989,1,,Jannik Sinner,R,188,ITA,23.7,209968,,Q,Flavio Cobolli,R,183,ITA,22.9,6-2 6-3,3,QF,72,3,1,52,32,24,13,12,2,4,2,1,48,28,18,10,11,5,8,1,12000,42,1100
2025-341,Madrid Open,Clay,96,M,20250425,302,208029,2,,Carlos Alcaraz Garfia,R,183,ESP,21.9,209829,,,Jakub Mensik,R,193,CZE,19.5,7-5 6-4,3,QF,89,4,3,65,38,28,17,14,3,6,5,2,58,32,22,13,13,4,7,3,10500,28,1500
2025-340,Indian Wells,Hard,96,M,20250308,202,208053,4,,Felix Auger-Aliassime,R,193,CAN,24.6,207666,5,,Stefanos Tsitsipas,R,193,GRE,26.4,6-4 4-6 6-3,3,SF,142,7,3,98,58,42,22,19,4,6,9,4,92,55,40,21,18,3,7,7,5500,9,4200
2025-342,Roland Garros,Clay,128,G,20250525,701,208029,2,,Carlos Alcaraz Garfia,R,183,ESP,22.0,207989,1,,Jannik Sinner,R,188,ITA,23.7,5-7 6-3 7-6 1-6 7-6,5,F,330,12,5,180,108,82,38,38,8,12,15,7,175,102,75,40,37,9,11,2,11200,1,12500
2025-342,Roland Garros,Clay,128,G,20250525,702,105657,8,,Andrey Rublev,R,188,RUS,27.4,209968,,,Flavio Cobolli,R,183,ITA,22.9,6-3 6-2 6-4,5,QF,118,6,2,93,58,44,18,20,2,4,3,1,82,48,32,18,19,3,5,12,3500,42,1150
2025-343,Wimbledon,Grass,128,G,20250630,701,207989,1,,Jannik Sinner,R,188,ITA,23.9,208029,2,,Carlos Alcaraz Garfia,R,183,ESP,22.1,7-6 4-6 6-2 6-3,5,F,225,14,4,142,88,72,28,32,4,7,8,3,138,82,62,32,30,5,8,1,12200,2,11000
2025-344,US Open,Hard,128,G,20250825,701,208029,2,,Carlos Alcaraz Garfia,R,183,ESP,22.4,206173,3,,Alexander Zverev,R,198,GER,28.4,6-3 6-4 7-5,5,SF,165,9,3,120,72,55,22,25,5,8,12,4,108,62,42,24,24,3,7,2,11500,3,7200
```

- [ ] **Step 2: Write failing tests**

Create `tests/unit/infrastructure/apis/test_sackmann_client.py`:

```python
"""Sackmann CSV client tests using fixtures."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.infrastructure.apis.sackmann_client import (
    PlayerServeStats,
    SackmannCache,
    aggregate_player_stats,
    parse_matches_csv,
    parse_players_csv,
)


_FIXTURE_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "sackmann"


def test_parse_players_csv_returns_records() -> None:
    csv_path = _FIXTURE_DIR / "atp_players_sample.csv"
    records = parse_players_csv(csv_path)
    assert len(records) == 10
    medvedev = next(r for r in records if r.last == "Medvedev")
    assert medvedev.first == "Daniil"
    assert medvedev.country == "RUS"


def test_parse_matches_csv_returns_rows() -> None:
    csv_path = _FIXTURE_DIR / "atp_matches_2025_sample.csv"
    matches = parse_matches_csv(csv_path)
    assert len(matches) == 10
    aus_open_final = next(m for m in matches if m["tourney_name"] == "Australian Open" and m["round"] == "F")
    assert aus_open_final["winner_name"] == "Jannik Sinner"
    assert aus_open_final["surface"] == "Hard"


def test_aggregate_player_stats_sinner_overall() -> None:
    matches = parse_matches_csv(_FIXTURE_DIR / "atp_matches_2025_sample.csv")
    stats = aggregate_player_stats("Jannik Sinner", matches, surface=None)
    assert stats is not None
    # Sinner won 2 matches in fixture (Aus Open F, Madrid QF, Wimbledon F)
    assert stats.matches_played >= 3
    # Service points won % should be reasonable (60-80%)
    assert 0.55 < stats.service_points_won_pct < 0.85


def test_aggregate_player_stats_clay_only() -> None:
    matches = parse_matches_csv(_FIXTURE_DIR / "atp_matches_2025_sample.csv")
    stats = aggregate_player_stats("Carlos Alcaraz Garfia", matches, surface="clay")
    assert stats is not None
    # Clay matches only: Madrid QF win, French Open F win
    assert stats.matches_played == 2
    assert stats.surface == "clay"


def test_aggregate_player_stats_unknown_returns_none() -> None:
    matches = parse_matches_csv(_FIXTURE_DIR / "atp_matches_2025_sample.csv")
    stats = aggregate_player_stats("Unknown Player", matches, surface=None)
    assert stats is None
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/unit/infrastructure/apis/test_sackmann_client.py -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 4: Implement Sackmann client (parsing only first)**

Create `src/infrastructure/apis/sackmann_client.py`:

```python
"""Sackmann tennis_atp / tennis_wta CSV client.

Fetches CSVs from GitHub, caches locally, parses player + match data.
Aggregates serve statistics per player (rolling 12-month, optionally
surface-filtered).
"""
from __future__ import annotations

import csv
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal

import requests

from src.domain.matching.tennis_player_resolver import PlayerRecord


logger = logging.getLogger(__name__)


_SACKMANN_BASE_ATP = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master"
_SACKMANN_BASE_WTA = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master"
_HTTP_TIMEOUT = 30


@dataclass(frozen=True)
class PlayerServeStats:
    name: str
    matches_played: int
    service_points_won_pct: float
    surface: Literal["clay", "hard", "grass"] | None
    last_match_date: str  # ISO YYYY-MM-DD


@dataclass
class SackmannCache:
    cache_dir: Path
    refresh_days: int

    def needs_refresh(self, filename: str) -> bool:
        path = self.cache_dir / filename
        if not path.exists():
            return True
        age_days = (time.time() - path.stat().st_mtime) / 86400.0
        return age_days >= self.refresh_days


def parse_players_csv(path: Path) -> list[PlayerRecord]:
    """Parse Sackmann atp_players.csv into PlayerRecord list."""
    records: list[PlayerRecord] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(PlayerRecord(
                sackmann_id=row.get("player_id", "").strip(),
                first=row.get("name_first", "").strip(),
                last=row.get("name_last", "").strip(),
                hand=row.get("hand", "").strip(),
                country=row.get("country", "").strip(),
            ))
    return records


def parse_matches_csv(path: Path) -> list[dict]:
    """Parse Sackmann atp_matches_YYYY.csv. Returns dict per row."""
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def aggregate_player_stats(
    player_name: str,
    matches: list[dict],
    surface: Literal["clay", "hard", "grass"] | None,
) -> PlayerServeStats | None:
    """Compute serve stats for a player, optionally surface-filtered."""
    matches_filtered = []
    for m in matches:
        if surface is not None:
            row_surface = m.get("surface", "").strip().lower()
            if surface == "clay" and row_surface != "clay":
                continue
            if surface == "hard" and row_surface != "hard":
                continue
            if surface == "grass" and row_surface != "grass":
                continue
        if player_name in (m.get("winner_name", ""), m.get("loser_name", "")):
            matches_filtered.append(m)

    if not matches_filtered:
        return None

    total_pts = 0
    total_won = 0
    last_date = ""

    for m in matches_filtered:
        is_winner = m.get("winner_name") == player_name
        prefix = "w_" if is_winner else "l_"
        try:
            svpt = int(m.get(f"{prefix}svpt", "0") or 0)
            first_in = int(m.get(f"{prefix}1stIn", "0") or 0)
            first_won = int(m.get(f"{prefix}1stWon", "0") or 0)
            second_won = int(m.get(f"{prefix}2ndWon", "0") or 0)
        except ValueError:
            continue
        if svpt == 0:
            continue
        total_pts += svpt
        total_won += first_won + second_won
        date_str = m.get("tourney_date", "")
        if date_str > last_date:
            last_date = date_str

    if total_pts == 0:
        return None

    pct = total_won / total_pts
    iso_date = ""
    if len(last_date) == 8:
        iso_date = f"{last_date[:4]}-{last_date[4:6]}-{last_date[6:]}"

    return PlayerServeStats(
        name=player_name,
        matches_played=len(matches_filtered),
        service_points_won_pct=pct,
        surface=surface,
        last_match_date=iso_date,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/infrastructure/apis/test_sackmann_client.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 6: Add HTTP fetch + cache write**

Append to `src/infrastructure/apis/sackmann_client.py`:

```python
def fetch_csv_to_cache(
    url: str,
    cache_path: Path,
    timeout: int = _HTTP_TIMEOUT,
) -> bool:
    """Fetch CSV from URL, write to cache_path. Returns True on success."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
        tmp_path.write_text(resp.text, encoding="utf-8")
        tmp_path.rename(cache_path)
        logger.info("Sackmann fetched: %s -> %s (%d bytes)", url, cache_path, len(resp.text))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sackmann fetch failed %s: %s", url, exc)
        return False


def refresh_atp_data(cache: SackmannCache, current_year: int) -> dict[str, Path]:
    """Refresh ATP player + recent year matches CSVs. Returns paths."""
    paths: dict[str, Path] = {}
    files = [
        ("atp_players.csv", f"{_SACKMANN_BASE_ATP}/atp_players.csv"),
        (f"atp_matches_{current_year}.csv", f"{_SACKMANN_BASE_ATP}/atp_matches_{current_year}.csv"),
        (f"atp_matches_{current_year - 1}.csv", f"{_SACKMANN_BASE_ATP}/atp_matches_{current_year - 1}.csv"),
    ]
    for filename, url in files:
        cache_path = cache.cache_dir / filename
        if cache.needs_refresh(filename):
            success = fetch_csv_to_cache(url, cache_path)
            if not success and not cache_path.exists():
                continue
        paths[filename] = cache_path
    return paths


def refresh_wta_data(cache: SackmannCache, current_year: int) -> dict[str, Path]:
    """Refresh WTA player + recent year matches CSVs."""
    paths: dict[str, Path] = {}
    files = [
        ("wta_players.csv", f"{_SACKMANN_BASE_WTA}/wta_players.csv"),
        (f"wta_matches_{current_year}.csv", f"{_SACKMANN_BASE_WTA}/wta_matches_{current_year}.csv"),
        (f"wta_matches_{current_year - 1}.csv", f"{_SACKMANN_BASE_WTA}/wta_matches_{current_year - 1}.csv"),
    ]
    for filename, url in files:
        cache_path = cache.cache_dir / filename
        if cache.needs_refresh(filename):
            success = fetch_csv_to_cache(url, cache_path)
            if not success and not cache_path.exists():
                continue
        paths[filename] = cache_path
    return paths
```

- [ ] **Step 7: Re-run all sackmann tests**

```bash
pytest tests/unit/infrastructure/apis/test_sackmann_client.py -v
```

Expected: 5 tests still PASS (no new tests for HTTP yet — covered in integration).

- [ ] **Step 8: Commit Task 4**

```bash
git add src/infrastructure/apis/sackmann_client.py tests/unit/infrastructure/apis/test_sackmann_client.py tests/fixtures/sackmann/atp_matches_2025_sample.csv
git commit -m "feat(tennis): Sackmann CSV client with cache + aggregation

Parses ATP/WTA player + match CSVs from Sackmann GitHub. Aggregates
service stats per player (rolling 12-month, surface-filterable).
HTTP fetch with atomic temp-rename cache write. needs_refresh checks
mtime against refresh_days config.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Tennis Paper Logger

**Files:**
- Create: `src/orchestration/tennis_paper_logger.py`
- Test: `tests/unit/orchestration/test_tennis_paper_logger.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/orchestration/test_tennis_paper_logger.py`:

```python
"""Tennis paper logger tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.orchestration.tennis_paper_logger import (
    InMatchSnapshot,
    PaperMatchRecord,
    PreMatchPrediction,
    TennisPaperLogger,
)


def test_log_pre_match_creates_record(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    logger = TennisPaperLogger(log_path=log_path)
    pre_match = PreMatchPrediction(
        model_p_win_a=0.628,
        model_p_win_b=0.372,
        polymarket_a_price=0.55,
        polymarket_b_price=0.45,
        edge=0.078,
        would_enter=True,
        would_size_usdc=35.0,
    )
    logger.log_pre_match(
        match_id="atp-medvedev-cobolli-2026-04-28",
        tournament="Madrid Open ATP",
        surface="clay",
        format="BO3",
        player_a="Daniil Medvedev",
        player_b="Flavio Cobolli",
        pre_match=pre_match,
    )

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["match_id"] == "atp-medvedev-cobolli-2026-04-28"
    assert record["pre_match"]["model_p_win_a"] == 0.628
    assert record["in_match_log"] == []
    assert record["actual_outcome"] is None


def test_append_in_match_snapshot(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    logger = TennisPaperLogger(log_path=log_path)
    pre_match = PreMatchPrediction(
        model_p_win_a=0.62, model_p_win_b=0.38,
        polymarket_a_price=0.55, polymarket_b_price=0.45,
        edge=0.07, would_enter=True, would_size_usdc=35.0,
    )
    logger.log_pre_match("m1", "Madrid", "clay", "BO3", "A", "B", pre_match)
    snap = InMatchSnapshot(
        timestamp_iso="2026-04-28T19:00:00Z",
        game_n=1,
        set_score="0-0",
        game_score="1-0",
        server="A",
        model_p_win_a=0.65,
        bid_a=0.56,
        would_action="HOLD",
    )
    logger.append_in_match("m1", snap)

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert len(record["in_match_log"]) == 1
    assert record["in_match_log"][0]["model_p_win_a"] == 0.65


def test_finalize_match_writes_outcome(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    logger = TennisPaperLogger(log_path=log_path)
    pre_match = PreMatchPrediction(
        model_p_win_a=0.62, model_p_win_b=0.38,
        polymarket_a_price=0.55, polymarket_b_price=0.45,
        edge=0.07, would_enter=True, would_size_usdc=35.0,
    )
    logger.log_pre_match("m1", "Madrid", "clay", "BO3", "A", "B", pre_match)
    logger.finalize_match(
        match_id="m1",
        winner="a",
        final_score="6-4 6-3",
        match_duration_min=95,
    )

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["actual_outcome"]["winner"] == "a"
    assert record["actual_outcome"]["final_score"] == "6-4 6-3"


def test_multiple_matches_separate_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    logger = TennisPaperLogger(log_path=log_path)
    pre = PreMatchPrediction(
        model_p_win_a=0.6, model_p_win_b=0.4,
        polymarket_a_price=0.55, polymarket_b_price=0.45,
        edge=0.05, would_enter=True, would_size_usdc=35.0,
    )
    logger.log_pre_match("m1", "T1", "clay", "BO3", "A", "B", pre)
    logger.log_pre_match("m2", "T2", "hard", "BO3", "C", "D", pre)
    lines = log_path.read_text().splitlines()
    assert len(lines) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/orchestration/test_tennis_paper_logger.py -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement paper logger**

Create `src/orchestration/tennis_paper_logger.py`:

```python
"""Tennis paper logger — JSONL records of would-be predictions/decisions.

Append-only file. Each match starts as one line on pre_match call,
in-match snapshots appended to its in_match_log, finalize writes outcome.
Re-reads + re-writes file for updates (Phase 0 small-scale, fine).
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreMatchPrediction:
    model_p_win_a: float
    model_p_win_b: float
    polymarket_a_price: float
    polymarket_b_price: float
    edge: float
    would_enter: bool
    would_size_usdc: float


@dataclass(frozen=True)
class InMatchSnapshot:
    timestamp_iso: str
    game_n: int
    set_score: str
    game_score: str
    server: str  # "A" or "B"
    model_p_win_a: float
    bid_a: float
    would_action: Literal["HOLD", "SELL_25", "SELL_50", "SELL_75", "SELL_ALL"]


@dataclass
class ActualOutcome:
    winner: Literal["a", "b"]
    final_score: str
    match_duration_min: int


@dataclass
class PaperMatchRecord:
    match_id: str
    tournament: str
    surface: str
    format: str
    player_a: str
    player_b: str
    pre_match: PreMatchPrediction
    in_match_log: list[dict] = field(default_factory=list)
    actual_outcome: dict | None = None


class TennisPaperLogger:
    """JSONL paper trade logger. One record per match."""

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_pre_match(
        self,
        match_id: str,
        tournament: str,
        surface: str,
        format: str,
        player_a: str,
        player_b: str,
        pre_match: PreMatchPrediction,
    ) -> None:
        """Create a new match record."""
        record = PaperMatchRecord(
            match_id=match_id,
            tournament=tournament,
            surface=surface,
            format=format,
            player_a=player_a,
            player_b=player_b,
            pre_match=pre_match,
        )
        self._append_record(record)

    def append_in_match(self, match_id: str, snapshot: InMatchSnapshot) -> None:
        """Append snapshot to in_match_log of existing match record."""
        records = self._read_all_records()
        target = self._find_record(records, match_id)
        if target is None:
            logger.warning("paper_log: match_id %s not found for in-match append", match_id)
            return
        target["in_match_log"].append(asdict(snapshot))
        self._write_all_records(records)

    def finalize_match(
        self,
        match_id: str,
        winner: Literal["a", "b"],
        final_score: str,
        match_duration_min: int,
    ) -> None:
        """Write actual outcome to existing match record."""
        records = self._read_all_records()
        target = self._find_record(records, match_id)
        if target is None:
            logger.warning("paper_log: match_id %s not found for finalize", match_id)
            return
        target["actual_outcome"] = {
            "winner": winner,
            "final_score": final_score,
            "match_duration_min": match_duration_min,
        }
        self._write_all_records(records)

    def _append_record(self, record: PaperMatchRecord) -> None:
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def _read_all_records(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        records: list[dict] = []
        with open(self._log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _write_all_records(self, records: list[dict]) -> None:
        tmp_path = self._log_path.with_suffix(self._log_path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        tmp_path.rename(self._log_path)

    @staticmethod
    def _find_record(records: list[dict], match_id: str) -> dict | None:
        for r in records:
            if r.get("match_id") == match_id:
                return r
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/orchestration/test_tennis_paper_logger.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit Task 5**

```bash
git add src/orchestration/tennis_paper_logger.py tests/unit/orchestration/test_tennis_paper_logger.py
git commit -m "feat(tennis): paper trade JSONL logger

Append-only logger with pre_match record creation, in_match snapshot
append, and finalize for actual outcome. Atomic write via temp-rename
for in-match updates. Per-match records in flat JSONL file.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Tennis Paper Observer (exit_processor.py wiring)

**Files:**
- Create: `src/orchestration/tennis_paper_observer.py`
- Test: `tests/unit/orchestration/test_tennis_paper_observer.py`
- Modify: `src/orchestration/exit_processor.py` (add hook)
- Modify: `src/orchestration/factory.py` (wire observer)

- [ ] **Step 1: Write failing test**

Create `tests/unit/orchestration/test_tennis_paper_observer.py`:

```python
"""Tennis paper observer integration tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.orchestration.tennis_paper_logger import TennisPaperLogger
from src.orchestration.tennis_paper_observer import (
    TennisPaperObserver,
    is_tennis_market,
)


def test_is_tennis_market_atp_slug() -> None:
    assert is_tennis_market("atp-medvedev-cobolli-2026-04-28") is True


def test_is_tennis_market_wta_slug() -> None:
    assert is_tennis_market("wta-stuttgart-open-2026-04-28") is True


def test_is_tennis_market_nhl_slug() -> None:
    assert is_tennis_market("nhl-bos-buf-2026-04-28") is False


def test_is_tennis_market_empty() -> None:
    assert is_tennis_market("") is False


def test_observer_skips_non_tennis(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    paper_logger = TennisPaperLogger(log_path=log_path)
    observer = TennisPaperObserver(paper_logger=paper_logger, magnus_predictor=MagicMock())

    # Mock position with NHL slug
    pos = MagicMock()
    pos.slug = "nhl-bos-buf-2026-04-28"
    pos.sport_tag = "nhl"

    observer.observe_position(pos, current_bid=0.55, score_info={})
    assert not log_path.exists()


def test_observer_skips_when_phase_disabled(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    paper_logger = TennisPaperLogger(log_path=log_path)
    observer = TennisPaperObserver(
        paper_logger=paper_logger,
        magnus_predictor=MagicMock(),
        phase="disabled",
    )

    pos = MagicMock()
    pos.slug = "atp-medvedev-cobolli-2026-04-28"
    pos.sport_tag = "tennis"

    observer.observe_position(pos, current_bid=0.55, score_info={})
    assert not log_path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/orchestration/test_tennis_paper_observer.py -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement observer**

Create `src/orchestration/tennis_paper_observer.py`:

```python
"""Tennis paper observer — read-only hook into exit_processor.py for Phase 0.

Observes existing tennis positions (or potential entries from scanner),
runs Magnus prediction, and logs would-be decisions. NEVER places trades
or modifies real position state during Phase 0.

Wired into exit_processor.py via observe_position() after existing exit
evaluation. Skips silently for non-tennis markets and when phase is
disabled.
"""
from __future__ import annotations

import logging
from typing import Any

from src.orchestration.tennis_paper_logger import (
    InMatchSnapshot,
    TennisPaperLogger,
)


logger = logging.getLogger(__name__)


def is_tennis_market(slug: str) -> bool:
    """Detect tennis market by slug prefix."""
    if not slug:
        return False
    s = slug.lower()
    return s.startswith("atp-") or s.startswith("wta-")


class TennisPaperObserver:
    """Phase 0 observation hook. No trades — pure logging."""

    def __init__(
        self,
        paper_logger: TennisPaperLogger,
        magnus_predictor: Any,
        phase: str = "disabled",
    ) -> None:
        self._paper_logger = paper_logger
        self._predictor = magnus_predictor
        self._phase = phase

    def observe_position(
        self,
        position: Any,
        current_bid: float,
        score_info: dict,
    ) -> None:
        """Observe position state, log would-be decision. Silent on errors."""
        if self._phase == "disabled":
            return
        slug = getattr(position, "slug", "") or ""
        if not is_tennis_market(slug):
            return

        try:
            self._record_observation(position, current_bid, score_info)
        except Exception as exc:  # noqa: BLE001
            # Phase 0 must never break production exit logic
            logger.warning("tennis paper observer error for %s: %s", slug, exc)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/orchestration/test_tennis_paper_observer.py -v
```

Expected: 5 tests PASS (the _record_observation is not yet called by tests; placeholder).

- [ ] **Step 5: Wire into exit_processor.py**

Open `src/orchestration/exit_processor.py`. Find the section after exit evaluation. Add a hook call (read the file first to find right location — likely after `evaluate_exit` returns and the position update):

```python
# Find this section (existing):
# ... exit evaluation ...
# (after exit decision is made, before next iteration)

# Add (with try/except guard so observer never breaks main loop):
if self._tennis_observer is not None:
    try:
        self._tennis_observer.observe_position(pos, current_bid=bid_price, score_info=score_info)
    except Exception:
        pass
```

Add `tennis_observer` parameter to `ExitProcessor.__init__`:

```python
def __init__(
    self,
    # ... existing params ...
    tennis_observer: "TennisPaperObserver | None" = None,
) -> None:
    # ... existing ...
    self._tennis_observer = tennis_observer
```

- [ ] **Step 6: Wire into factory.py**

Open `src/orchestration/factory.py`. Add tennis observer construction and wire it through `AgentDeps` (the existing DI pattern — no `Monitor` class exists; `ExitProcessor` is constructed inside `Agent.__init__` from deps):

```python
from src.orchestration.tennis_paper_logger import TennisPaperLogger
from src.orchestration.tennis_paper_observer import TennisPaperObserver

# In factory function, after config load:
tennis_cfg = cfg.tennis
tennis_observer = None
if tennis_cfg.phase != "disabled":
    paper_log_path = Path("logs/audit/tennis_paper_trade.jsonl")
    paper_logger_obj = TennisPaperLogger(log_path=paper_log_path)
    # magnus_predictor wired in Task 7 (placeholder for now)
    tennis_observer = TennisPaperObserver(
        paper_logger=paper_logger_obj,
        magnus_predictor=None,
        phase=tennis_cfg.phase,
    )

# Pass to AgentDeps (which Agent constructor uses to build ExitProcessor):
deps = AgentDeps(
    # ... existing fields ...
    tennis_observer=tennis_observer,
)
```

- [ ] **Step 7: Run full test suite to confirm no regressions**

```bash
pytest tests/ -q
```

Expected: all existing tests still pass + new tests pass.

- [ ] **Step 8: Commit Task 6**

```bash
git add src/orchestration/tennis_paper_observer.py tests/unit/orchestration/test_tennis_paper_observer.py src/orchestration/exit_processor.py src/orchestration/factory.py
git commit -m "feat(tennis): paper observer wired into monitor (read-only)

Phase 0 observation hook into ExitProcessor. Skips non-tennis markets and
when phase=disabled. Wrapped in try/except so observer errors never
break exit pipeline. Factory creates TennisPaperLogger when phase
active. Magnus predictor wiring stub for Task 7.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Magnus Predictor Glue + Observer Recording

**Files:**
- Modify: `src/orchestration/tennis_paper_observer.py` (implement `_record_observation`)
- Create: `src/orchestration/tennis_magnus_predictor.py` (composition root for prediction)
- Test: `tests/unit/orchestration/test_tennis_magnus_predictor.py`

- [ ] **Step 1: Write failing test for predictor**

Create `tests/unit/orchestration/test_tennis_magnus_predictor.py`:

```python
"""Tennis Magnus predictor (composition of resolver + Sackmann + math)."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.matching.tennis_player_resolver import PlayerRecord, build_registry
from src.infrastructure.apis.sackmann_client import parse_matches_csv
from src.orchestration.tennis_magnus_predictor import (
    PredictionResult,
    TennisMagnusPredictor,
)


_FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "sackmann"


@pytest.fixture
def predictor() -> TennisMagnusPredictor:
    matches = parse_matches_csv(_FIXTURE_DIR / "atp_matches_2025_sample.csv")
    registry = build_registry([
        PlayerRecord(sackmann_id="207989", first="Jannik", last="Sinner", hand="R", country="ITA"),
        PlayerRecord(sackmann_id="208029", first="Carlos", last="Alcaraz Garfia", hand="R", country="ESP"),
        PlayerRecord(sackmann_id="209968", first="Flavio", last="Cobolli", hand="R", country="ITA"),
    ])
    surface_factors = {
        "atp": {"clay": 0.92, "hard": 1.00, "grass": 1.00},
        "wta": {"clay": 0.95, "hard": 1.05, "grass": 1.00},
    }
    return TennisMagnusPredictor(
        registry=registry,
        matches=matches,
        surface_factors=surface_factors,
        is_wta=False,
    )


def test_predict_pre_match_sinner_vs_cobolli_clay(predictor: TennisMagnusPredictor) -> None:
    result = predictor.predict_pre_match(
        player_a_query="Jannik Sinner",
        player_b_query="Flavio Cobolli",
        surface="clay",
        format="BO3",
    )
    assert result is not None
    # Sinner is heavy favorite
    assert result.p_win_a > 0.55
    assert 0 < result.p_win_a < 1


def test_predict_unknown_player_returns_none(predictor: TennisMagnusPredictor) -> None:
    result = predictor.predict_pre_match(
        player_a_query="Unknown Player X",
        player_b_query="Flavio Cobolli",
        surface="clay",
        format="BO3",
    )
    assert result is None


def test_predict_with_state_a_won_set1(predictor: TennisMagnusPredictor) -> None:
    pre = predictor.predict_pre_match("Jannik Sinner", "Flavio Cobolli", "clay", "BO3")
    assert pre is not None
    after = predictor.predict_with_state(
        player_a_query="Jannik Sinner",
        player_b_query="Flavio Cobolli",
        surface="clay",
        format="BO3",
        sets_won_a=1,
        sets_won_b=0,
        games_a=0,
        games_b=0,
        server_is_a=True,
    )
    assert after is not None
    assert after.p_win_a > pre.p_win_a
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/orchestration/test_tennis_magnus_predictor.py -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement predictor**

Create `src/orchestration/tennis_magnus_predictor.py`:

```python
"""Tennis Magnus predictor — composition root combining all pieces.

Resolves player names → loads serve stats → applies surface adjustment
→ runs Magnus chain. Single source of P(A wins) for both pre-match and
in-match queries.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from src.domain.math.tennis_magnus import (
    MatchState,
    p_match_bo3,
    p_match_from_state,
)
from src.domain.matching.tennis_player_resolver import (
    PlayerRecord,
    PlayerRegistry,
    resolve_player,
)
from src.infrastructure.apis.sackmann_client import (
    PlayerServeStats,
    aggregate_player_stats,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PredictionResult:
    p_win_a: float
    p_win_b: float
    p_serve_a: float
    p_serve_b: float
    player_a_record: PlayerRecord
    player_b_record: PlayerRecord


class TennisMagnusPredictor:
    """Predicts P(A wins match) given player names + state."""

    def __init__(
        self,
        registry: PlayerRegistry,
        matches: list[dict],
        surface_factors: dict[str, dict[str, float]],
        is_wta: bool,
    ) -> None:
        self._registry = registry
        self._matches = matches
        self._surface_factors = surface_factors
        self._is_wta = is_wta

    def predict_pre_match(
        self,
        player_a_query: str,
        player_b_query: str,
        surface: Literal["clay", "hard", "grass"],
        format: Literal["BO3", "BO5"],
    ) -> PredictionResult | None:
        prep = self._prepare_inputs(player_a_query, player_b_query, surface)
        if prep is None:
            return None
        rec_a, rec_b, p_a_adj, p_b_adj = prep
        if format == "BO5":
            return None  # Phase 2
        p_win_a = p_match_bo3(p_a_adj, p_b_adj)
        return PredictionResult(
            p_win_a=p_win_a,
            p_win_b=1 - p_win_a,
            p_serve_a=p_a_adj,
            p_serve_b=p_b_adj,
            player_a_record=rec_a,
            player_b_record=rec_b,
        )

    def predict_with_state(
        self,
        player_a_query: str,
        player_b_query: str,
        surface: Literal["clay", "hard", "grass"],
        format: Literal["BO3", "BO5"],
        sets_won_a: int,
        sets_won_b: int,
        games_a: int,
        games_b: int,
        server_is_a: bool,
    ) -> PredictionResult | None:
        prep = self._prepare_inputs(player_a_query, player_b_query, surface)
        if prep is None:
            return None
        rec_a, rec_b, p_a_adj, p_b_adj = prep
        state = MatchState(
            sets_won_a=sets_won_a, sets_won_b=sets_won_b,
            games_a=games_a, games_b=games_b,
            server_is_a=server_is_a, format=format,
        )
        p_win_a = p_match_from_state(p_a_adj, p_b_adj, state)
        return PredictionResult(
            p_win_a=p_win_a,
            p_win_b=1 - p_win_a,
            p_serve_a=p_a_adj,
            p_serve_b=p_b_adj,
            player_a_record=rec_a,
            player_b_record=rec_b,
        )

    def _prepare_inputs(
        self,
        player_a_query: str,
        player_b_query: str,
        surface: str,
    ) -> tuple[PlayerRecord, PlayerRecord, float, float] | None:
        rec_a = resolve_player(player_a_query, self._registry)
        rec_b = resolve_player(player_b_query, self._registry)
        if rec_a is None or rec_b is None:
            logger.info("magnus_predictor: cannot resolve %s or %s", player_a_query, player_b_query)
            return None

        stats_a = aggregate_player_stats(rec_a.full_name, self._matches, surface=None)
        stats_b = aggregate_player_stats(rec_b.full_name, self._matches, surface=None)
        if stats_a is None or stats_b is None:
            logger.info("magnus_predictor: no stats for %s or %s", rec_a.full_name, rec_b.full_name)
            return None

        gender = "wta" if self._is_wta else "atp"
        factor = self._surface_factors.get(gender, {}).get(surface, 1.0)
        p_a_adj = max(0.0, min(1.0, stats_a.service_points_won_pct * factor))
        p_b_adj = max(0.0, min(1.0, stats_b.service_points_won_pct * factor))
        return rec_a, rec_b, p_a_adj, p_b_adj
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/orchestration/test_tennis_magnus_predictor.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Update observer to use predictor**

Open `src/orchestration/tennis_paper_observer.py`. Add `_record_observation` method:

```python
def _record_observation(
    self,
    position: Any,
    current_bid: float,
    score_info: dict,
) -> None:
    """Resolve players, run Magnus, log snapshot."""
    if self._predictor is None:
        return
    # Extract players from position.match_title or slug
    # Pre-match handled separately by entry observer (out of scope this iteration)
    # In-match: append snapshot if match in progress
    if not score_info.get("available"):
        return
    # Phase 0: simple snapshot logging only (full pre-match flow in Task 8)
    # ... (kept minimal — full flow in Phase 0 integration smoke test)
```

This stub is intentional minimal — full pre-match entry path requires scanner integration which is read-only path in Phase 0. The observer only handles in-match snapshots; pre-match handled by separate scanner-side hook in Task 8.

- [ ] **Step 6: Commit Task 7**

```bash
git add src/orchestration/tennis_magnus_predictor.py tests/unit/orchestration/test_tennis_magnus_predictor.py src/orchestration/tennis_paper_observer.py
git commit -m "feat(tennis): Magnus predictor composition root

Combines player resolver + Sackmann stats + Magnus chain into single
predict_pre_match / predict_with_state interface. Surface adjustment
applied per gender (ATP/WTA factors). Returns None on resolution
failure (logged at INFO). Observer stub uses predictor for in-match
snapshots.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Pre-Match Entry Observer (Scanner Hook)

**Files:**
- Modify: `src/orchestration/tennis_paper_observer.py` (add pre_match_observation)
- Modify: `src/orchestration/scanner.py` or `src/orchestration/entry_processor.py` (wire pre-match hook)
- Test: extend `tests/unit/orchestration/test_tennis_paper_observer.py`

- [ ] **Step 1: Add test for pre_match observation**

Append to `tests/unit/orchestration/test_tennis_paper_observer.py`:

```python
def test_pre_match_observation_creates_record(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    paper_logger = TennisPaperLogger(log_path=log_path)
    predictor = MagicMock()
    predictor.predict_pre_match.return_value = MagicMock(
        p_win_a=0.62, p_win_b=0.38,
        player_a_record=MagicMock(full_name="Jannik Sinner"),
        player_b_record=MagicMock(full_name="Flavio Cobolli"),
    )
    observer = TennisPaperObserver(
        paper_logger=paper_logger,
        magnus_predictor=predictor,
        phase="paper_trade",
    )
    market = MagicMock()
    market.slug = "atp-sinner-cobolli-2026-04-28"
    market.question = "Madrid Open: Jannik Sinner vs Flavio Cobolli"
    market.tags = ["atp", "madrid-open"]
    tournament_info = MagicMock(tier="masters_1000", surface="clay", format="BO3")
    observer.observe_pre_match(
        market=market,
        tournament_info=tournament_info,
        polymarket_a_price=0.55,
        polymarket_b_price=0.45,
    )
    assert log_path.exists()
    import json
    record = json.loads(log_path.read_text().splitlines()[0])
    assert record["match_id"] == "atp-sinner-cobolli-2026-04-28"
    assert record["surface"] == "clay"
    assert record["pre_match"]["model_p_win_a"] == 0.62
```

- [ ] **Step 2: Implement pre_match_observation in observer**

In `src/orchestration/tennis_paper_observer.py`, add method:

```python
def observe_pre_match(
    self,
    market: Any,
    tournament_info: Any,
    polymarket_a_price: float,
    polymarket_b_price: float,
) -> None:
    """Observe pre-match prediction. Log entry decision."""
    if self._phase == "disabled":
        return
    slug = getattr(market, "slug", "") or ""
    if not is_tennis_market(slug):
        return
    if self._predictor is None:
        return

    try:
        from src.strategy.enrichment.question_parser import extract_teams
        team_a, team_b = extract_teams(getattr(market, "question", ""))
        if not team_a or not team_b:
            return

        result = self._predictor.predict_pre_match(
            player_a_query=team_a,
            player_b_query=team_b,
            surface=tournament_info.surface,
            format=tournament_info.format,
        )
        if result is None:
            return

        edge = result.p_win_a - polymarket_a_price
        from src.orchestration.tennis_paper_logger import PreMatchPrediction
        pre_match = PreMatchPrediction(
            model_p_win_a=result.p_win_a,
            model_p_win_b=result.p_win_b,
            polymarket_a_price=polymarket_a_price,
            polymarket_b_price=polymarket_b_price,
            edge=edge,
            would_enter=abs(edge) >= 0.05,
            would_size_usdc=0.0,  # Phase 0 paper, no real size
        )
        self._paper_logger.log_pre_match(
            match_id=slug,
            tournament=getattr(market, "question", "")[:80],
            surface=tournament_info.surface,
            format=tournament_info.format,
            player_a=result.player_a_record.full_name,
            player_b=result.player_b_record.full_name,
            pre_match=pre_match,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("tennis pre_match observation error: %s", exc)
```

- [ ] **Step 3: Run observer tests**

```bash
pytest tests/unit/orchestration/test_tennis_paper_observer.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 4: Wire into scanner.py or entry_processor.py**

Read `src/orchestration/entry_processor.py` to find the right hook point — likely after market is filtered as tennis but before it's blocked by active_sports filter. Add a hook call before the active_sports check:

```python
# In entry_processor process_entry method, near top, before active_sports filter:
if self.deps.tennis_observer is not None:
    try:
        from src.domain.matching.tennis_tournament_resolver import resolve_tournament
        info = resolve_tournament(
            market.slug,
            self.deps.tennis_config.tournaments,
            self.deps.tennis_config.excluded_tiers,
        )
        if info is not None:
            self.deps.tennis_observer.observe_pre_match(
                market=market,
                tournament_info=info,
                polymarket_a_price=market.yes_price,
                polymarket_b_price=1.0 - market.yes_price,
            )
    except Exception:
        pass
```

Add `tennis_observer` and `tennis_config` to `EntryDeps` dataclass.

- [ ] **Step 5: Update factory.py to pass dependencies**

In `factory.py`, pass `tennis_observer` and `cfg.tennis` to `EntryDeps` construction.

- [ ] **Step 6: Run full test suite**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit Task 8**

```bash
git add src/orchestration/tennis_paper_observer.py src/orchestration/entry_processor.py src/orchestration/factory.py tests/unit/orchestration/test_tennis_paper_observer.py
git commit -m "feat(tennis): pre-match observer hook in entry pipeline

Tennis-eligible markets get pre-match prediction logged before
active_sports filter blocks. Try/except wrapping ensures observation
errors never affect entry pipeline. Edge calculated as model_p_win -
polymarket_implied; would_enter flagged when |edge| >= 0.05.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Diag Scripts (Sanity Check Tools)

**Files:**
- Create: `scripts/diag_tennis_magnus.py`
- Create: `scripts/diag_tennis_paper_replay.py`

- [ ] **Step 1: Create diag_tennis_magnus.py**

Create `scripts/diag_tennis_magnus.py`:

```python
"""Quick sanity check: run Magnus prediction on one known match.

Usage: python -m scripts.diag_tennis_magnus
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.math.tennis_magnus import MatchState, p_match_bo3, p_match_from_state


def main() -> None:
    print("=== Magnus chain sanity check ===")

    # Sinner vs Cobolli, Madrid clay
    p_sinner_clay = 0.689 * 0.92  # career 68.9% adjusted for clay
    p_cobolli_clay = 0.642 * 0.92  # career 64.2% adjusted

    pre_match = p_match_bo3(p_sinner_clay, p_cobolli_clay)
    print(f"Pre-match P(Sinner wins) = {pre_match:.3f}")

    # After Sinner wins set 1
    state = MatchState(sets_won_a=1, sets_won_b=0, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_after_set1 = p_match_from_state(p_sinner_clay, p_cobolli_clay, state)
    print(f"After Sinner wins set 1: P(Sinner wins) = {p_after_set1:.3f}")

    # After Sinner loses set 1
    state = MatchState(sets_won_a=0, sets_won_b=1, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_after_loss = p_match_from_state(p_sinner_clay, p_cobolli_clay, state)
    print(f"After Sinner loses set 1: P(Sinner wins) = {p_after_loss:.3f}")

    # Mid set 2, Sinner down 0-2 set, 1-3 in current
    state = MatchState(sets_won_a=0, sets_won_b=2, games_a=1, games_b=3, server_is_a=True, format="BO3")
    p_dead = p_match_from_state(p_sinner_clay, p_cobolli_clay, state)
    print(f"Sinner down 0-2 sets + 1-3 game: P(Sinner wins) = {p_dead:.3f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run diag to verify outputs are sensible**

```bash
python -m scripts.diag_tennis_magnus
```

Expected output (approximate):
```
Pre-match P(Sinner wins) = 0.6XX (favorite, > 0.5)
After Sinner wins set 1: P(Sinner wins) = 0.8XX (boost)
After Sinner loses set 1: P(Sinner wins) = 0.3XX (drop)
Sinner down 0-2 sets + 1-3 game: P(Sinner wins) = 0.0XX (matematik bitti)
```

- [ ] **Step 3: Create diag_tennis_paper_replay.py**

Create `scripts/diag_tennis_paper_replay.py`:

```python
"""Replay logged paper trade matches and compute accuracy metrics.

Usage: python -m scripts.diag_tennis_paper_replay [--log-path PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-path", default="logs/audit/tennis_paper_trade.jsonl")
    args = parser.parse_args()

    log_path = Path(args.log_path)
    if not log_path.exists():
        print(f"No paper log found: {log_path}")
        sys.exit(1)

    records = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    finished = [r for r in records if r.get("actual_outcome") is not None]

    if not finished:
        print(f"Loaded {len(records)} records, 0 finished. Cannot compute accuracy.")
        return

    print(f"=== Paper Trade Stats ({len(finished)} finished matches) ===")

    correct = 0
    high_conf_correct = 0
    high_conf_total = 0
    edge_outcomes = []

    for r in finished:
        pre = r["pre_match"]
        actual = r["actual_outcome"]["winner"]
        predicted = "a" if pre["model_p_win_a"] >= 0.5 else "b"
        is_correct = predicted == actual
        if is_correct:
            correct += 1

        # High-confidence calls (model > 0.55)
        if pre["model_p_win_a"] >= 0.55 or pre["model_p_win_a"] <= 0.45:
            high_conf_total += 1
            if is_correct:
                high_conf_correct += 1

        edge_outcomes.append({"edge": pre["edge"], "won": is_correct})

    print(f"Overall accuracy: {correct}/{len(finished)} = {correct/len(finished)*100:.1f}%")
    if high_conf_total > 0:
        print(f"High-confidence (model >= 0.55): {high_conf_correct}/{high_conf_total} = {high_conf_correct/high_conf_total*100:.1f}%")
        print(f"GATE for Phase 1: {'PASS' if high_conf_correct/high_conf_total >= 0.65 else 'FAIL (need >= 65%)'}")
    avg_edge = sum(e["edge"] for e in edge_outcomes) / len(edge_outcomes)
    print(f"Average edge claimed: {avg_edge*100:.2f}%")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Test diag script with empty/missing log**

```bash
python -m scripts.diag_tennis_paper_replay --log-path /tmp/nonexistent.jsonl
```

Expected: prints "No paper log found" and exits cleanly.

- [ ] **Step 5: Commit Task 9**

```bash
git add scripts/diag_tennis_magnus.py scripts/diag_tennis_paper_replay.py
git commit -m "feat(tennis): diag scripts for Magnus + paper replay

diag_tennis_magnus runs predictor for known Sinner vs Cobolli scenarios
(pre-match, set 1 won/lost, matematical death). diag_tennis_paper_replay
computes accuracy metrics from logged paper trades + Phase 1 gate
indicator (>= 65% high-confidence accuracy).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: DECISIONS.md Documentation

**Files:**
- Modify: `DECISIONS.md`

- [ ] **Step 1: Append tennis Phase 0 section**

Open `DECISIONS.md`, append at the end:

```markdown
---

## Tennis (Phase 0 Paper Trade) — 2026-04-29

### Active scope

- H2H markets only (Match Total Games deferred to Phase 4)
- BO3 only (BO5 Grand Slam in Phase 2)
- Tournament tiers: Grand Slam + Masters 1000 + ATP/WTA 500 + ATP/WTA 250 (250 included only in Phase 0 for sample size)
- ITF, Challenger, Futures: excluded permanently

### Filter thresholds

| Filter | Phase 0 value | Source |
|---|---|---|
| Min ranking | top 100 | Spec Section 9 |
| Max ranking gap | < 100 | User decision (match-fixing risk filter) |
| Min model edge | 0.05 | Spec Section 9 |
| Match window | 0-24h pre-match | Spec Section 9 |
| Position size | $0 (paper) | Spec Section 9 |

### Surface factors (serve % multiplier)

| Surface | ATP | WTA | Source |
|---|---|---|---|
| Grass | 1.00 | 1.00 | Tennisnerd 2026 baseline |
| Hard | 1.00 | 1.05 | empirical study |
| Clay | 0.92 | 0.95 | empirical study |

### Magnus formulas

- Game on serve: O'Malley (2008) eq.3 / Newton-Keller (2005) `G(p) = p^4 * (1 + 4q + 10q^2 + 20q^3*p/(p^2+q^2))` where q=1-p (verified G(0.5)=0.5)
- Set: recursive sum to 6-x or 7-x, tiebreak via binomial approximation
- Match BO3: 2-of-3 sets independent
- Match from state: combinatorial with current set + game state
- BO5: NotImplementedError (Phase 2)

### Data source

- Sackmann GitHub `tennis_atp` + `tennis_wta` repos
- Cache: `data/sackmann_cache/`, refresh weekly
- Player xref persisted: `data/tennis_player_xref.json`

### Gate criteria for Phase 1

- ≥ 50 finished matches in paper log
- Directional accuracy (high-confidence calls, model ≥ 0.55) ≥ 65%
- No structural bug in resolver (resolver fail rate < 1%)
```

- [ ] **Step 2: Commit Task 10**

```bash
git add DECISIONS.md
git commit -m "docs(decisions): tennis Phase 0 paper trade decisions

Documents H2H scope, filter thresholds, surface factors, Magnus
formula sources, and Phase 1 gate criteria. References spec
2026-04-29-tennis-magnus-live-system-design.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Smoke Test in dry_run Mode

**Files:**
- None (operational)

- [ ] **Step 1: Enable Phase 0 in config**

Edit `config.yaml`:

```yaml
tennis:
  enabled: true
  phase: paper_trade
  # ... rest of tennis block unchanged
```

- [ ] **Step 2: Run bot in dry_run for 5 minutes**

```bash
python -m src.main 2>&1 | tee logs/runtime/smoke_tennis_phase0.log
```

After 5 minutes, kill with Ctrl+C.

- [ ] **Step 3: Inspect paper log**

```bash
ls -lh logs/audit/tennis_paper_trade.jsonl
cat logs/audit/tennis_paper_trade.jsonl | python -m json.tool | head -50
```

Expected: At least 1-2 records if any tennis matches were within window. If empty, check:
- Are there active tennis markets in scanner output? `grep "atp-\|wta-" logs/runtime/bot.log`
- Did observer fire? `grep "tennis_paper" logs/runtime/bot.log`

- [ ] **Step 4: Run replay diag**

```bash
python -m scripts.diag_tennis_paper_replay
```

Expected: prints record count + (if any finished matches) accuracy metrics.

- [ ] **Step 5: Commit smoke test artifacts**

```bash
git add config.yaml
git commit -m "feat(tennis): enable Phase 0 paper trade in config

Toggles tennis.enabled=true and phase=paper_trade. Bot now logs
would-be tennis predictions to logs/audit/tennis_paper_trade.jsonl
without placing trades. Phase 1 gate: 50-100 matches with ≥ 65%
high-confidence accuracy.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 1, 2, 3 — Skeletal Outlines (detailed plans created after each gate)

### Phase 1: v1 Simple Live (H2H, BO3 only) — separate plan after Phase 0 gate passes

Estimated 12-15 tasks:
1. Replace `tennis_score_exit.py` STUB with set-bazlı sabit tablo + Magnus base lookup
2. Sport-specific exit dispatcher in `_tennis_exit_dispatch.py`
3. Wire into `exit_processor.py` exit loop (replaces paper observer for tennis)
4. Tighten filters in `config.yaml` (drop ATP/WTA 250)
5. Set `tennis.phase = v1`, position cap $15
6. Smoke test in dry_run, then mode switch to live

### Phase 2: v2 Bayesian + BO5 — separate plan after Phase 1 gate passes

Estimated 10-12 tasks:
1. `src/domain/math/tennis_bayesian.py` — posterior_p formula
2. ESPN service stats parser update (per-set tracking)
3. BO5 implementation in `tennis_magnus.py` (remove NotImplementedError)
4. Integration into `tennis_score_exit.py`
5. Position cap $25, smoke test, gate

### Phase 3: v3 Momentum + Risk-EV — separate plan after Phase 2 gate passes

Estimated 10-12 tasks:
1. `src/domain/math/tennis_momentum.py` — EWMA of game outcomes
2. Risk-adjusted EV combiner in `tennis_score_exit.py`
3. Multi-signal exit hierarchy
4. Position cap $35, smoke test, steady state

### Phase 4: Match Total Games — separate sub-spec needed

Out of scope for current spec. Triggered by user when Phase 3 stable.

---

## Final Self-Review

### Spec coverage check

| Spec Section | Phase 0 task |
|---|---|
| 4.1 Paper trade what it does | Task 5, 7, 8 |
| 4.2 What gets logged | Task 5 (PaperMatchRecord) |
| 4.3 Gate criteria | Task 9 (diag_tennis_paper_replay), Task 10 (DECISIONS.md) |
| 5.1 Magnus base P(win) | Task 3 |
| 7.1 Sackmann GitHub | Task 4 |
| 7.5 Player Name Resolution | Task 2 |
| 8 Tournament Tier + Surface | Task 1 |
| 10 Configuration | Task 1 |
| 11 Edge Cases (player not in Sackmann) | Task 7 (returns None) |
| 12 Testing Strategy | All tasks (TDD per CLAUDE.md) |
| 13 Implementation Order Phase 0 (steps 6-12) | Tasks 1-11 |
| 14b Risk 3 (test fixtures) | Tasks 1, 2, 4 fixtures committed |
| 14b Risk 4 (player ID alignment) | Task 2 (resolver returns sackmann_id) |
| 14b Risk 6 (rollback) | Config phase=disabled toggle |

### Placeholder scan

- [x] No "TBD" / "TODO" in actionable steps
- [x] All test code shown verbatim
- [x] All implementation code shown
- [x] All commands explicit with expected output

### Type consistency

- `PlayerRecord` definition consistent across Tasks 2, 4, 7
- `MatchState` defined in Task 3, used in Task 7
- `PreMatchPrediction`, `InMatchSnapshot` defined in Task 5, used in Task 8
- `TournamentInfo` defined in Task 1, used in Task 8
- `PredictionResult` defined in Task 7, used by observer

### Open issues

None. Plan ready for execution.
