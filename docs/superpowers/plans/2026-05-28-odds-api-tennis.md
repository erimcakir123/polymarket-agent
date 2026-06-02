# Odds API Tennis Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sackmann/Glicko2 tahmin modelini tennis-lab + tennis-paper-lab'dan tamamen sil, Odds API bookmaker konsensüsü ile değiştir.

**Architecture:** Sackmann pipeline (Glicko-2 ratings → predictor → anchor_probability) yerine Odds API pipeline (multi-bookmaker odds → vig-removed consensus → A confidence + anchor_probability). Basket bot pattern'i (`derive_confidence` + `probability`) ana bot'tan kopyalanır.

**Tech Stack:** Python 3.12+, Pydantic configs, pytest TDD, httpx (Odds API), Polymarket gamma_client (mevcut).

**Spec:** [docs/superpowers/specs/2026-05-28-odds-api-tennis-design.md](../specs/2026-05-28-odds-api-tennis-design.md)

---

## File Map

### Phase 1 — tennis-paper-lab değişiklikleri

| Dosya | Action | Kaynak |
|---|---|---|
| `src/domain/analysis/confidence.py` | CREATE | Ana bot'tan kopya |
| `src/domain/analysis/probability.py` | CREATE | Ana bot'tan kopya |
| `src/infrastructure/apis/odds_client.py` | CREATE | Ana bot'tan kopya + tennis method'lar |
| `src/domain/matching/tennis_odds_matcher.py` | CREATE | YENİ |
| `src/strategy/enrichment/tennis_market_enricher.py` | REWRITE | Sackmann çağrıları → Odds API pipeline |
| `src/strategy/entry/tennis_signal_adapter.py` | MODIFY | anchor_probability kaynağı değişti |
| `src/orchestration/tennis_factory.py` | MODIFY | Sackmann deps kaldır, odds_client ekle |
| `config_tennis.yaml` | MODIFY | Sackmann sectionları kaldır |
| `src/domain/prediction/` | DELETE | Glicko2 + predictor + features (komple dizin) |
| `src/domain/matching/tennis_player_resolver.py` | DELETE | Sackmann player lookup |
| `src/infrastructure/data/sackmann_csv_client.py` | DELETE | Sackmann CSV |
| `src/infrastructure/data/sackmann_refresher.py` | DELETE | Sackmann refresh |
| `src/infrastructure/data/tennis_data_uk_client.py` | DELETE | TennisDataUK |
| `src/infrastructure/data/tennis_ratings_store.py` | DELETE | Ratings store |
| `src/infrastructure/data/tml_csv_client.py` | DELETE | TML client |
| `data/sackmann_cache/` | DELETE | Cache dizini |
| `data/tennis_ratings.json` (~14MB) | DELETE | Ratings cache |
| `data/tennis_ratings.before_itf_rebuild.json` (~3.5MB) | DELETE | Old ratings backup |
| `data/tml_cache/` | DELETE | TML cache dizini |
| `tests/unit/domain/prediction/` | DELETE | Sackmann unit tests |
| `tests/unit/domain/matching/test_tennis_player_resolver.py` | DELETE | Sackmann matcher test |
| `tests/unit/infrastructure/data/` | DELETE | Sackmann infrastructure tests (selektif) |

**Yeni test dosyaları:**
- `tests/unit/domain/analysis/test_confidence.py` — ana bot'tan kopya
- `tests/unit/domain/analysis/test_probability.py` — ana bot'tan kopya
- `tests/unit/infrastructure/apis/test_odds_client.py` — tennis method için extend
- `tests/unit/domain/matching/test_tennis_odds_matcher.py` — YENİ
- `tests/unit/strategy/enrichment/test_tennis_market_enricher.py` — REWRITE

### Phase 2 — tennis-lab mirror
Phase 1'in birebir aynısı, tennis-lab worktree'sine uygulanır.

### Phase 3 — Drift check + commit
Üç bot karşılaştırma + DECISIONS.md güncelleme.

---

## ARCH_GUARD Self-Check (her Edit/Write ÖNCESİ)

Her task'ın ilk adımı: implementer subagent şu satırı output etmeli (CLAUDE.md kuralı):

> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."

---

# PHASE 1 — tennis-paper-lab

## Task 1: Setup feature branch

**Files:**
- Branch: `tennis-paper-lab/feature/odds-api-tennis`

- [ ] **Step 1: Check current branch + uncommitted state**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
git branch --show-current && git status --short | head -10
```

Expected: master (or current feature) + minor uncommitted state files.

- [ ] **Step 2: Create feature branch**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
git checkout -b feature/odds-api-tennis
```

Expected: `Switched to a new branch 'feature/odds-api-tennis'`

- [ ] **Step 3: Verify ARCH_GUARD + CLAUDE.md files (if exist)**

```bash
ls "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/" | grep -iE "ARCHITECTURE|CLAUDE"
```

If files exist: read them. If not: use parent project rules.

---

## Task 2: Copy confidence.py from ana bot

**Files:**
- Create: `src/domain/analysis/__init__.py` (if missing)
- Create: `src/domain/analysis/confidence.py`
- Create: `tests/unit/domain/analysis/test_confidence.py`

- [ ] **Step 1: Output ARCH_GUARD self-check**

- [ ] **Step 2: Verify source file exists in ana bot**

```bash
ls "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/src/domain/analysis/confidence.py"
```

- [ ] **Step 3: Copy file**

```bash
cp "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/src/domain/analysis/confidence.py" \
   "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/domain/analysis/confidence.py"
```

Create `__init__.py` if missing:
```bash
mkdir -p "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/domain/analysis" && \
touch "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/domain/analysis/__init__.py"
```

- [ ] **Step 4: Copy test file**

```bash
find "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/tests" -name "test_confidence.py"
```

Then `cp` the test file to `tests/unit/domain/analysis/test_confidence.py` in tennis-paper-lab. If subdirs missing, create them.

- [ ] **Step 5: Run test, expect PASS**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/domain/analysis/test_confidence.py -v
```

Expected: All confidence tests PASS.

---

## Task 3: Copy probability.py from ana bot

**Files:**
- Create: `src/domain/analysis/probability.py`
- Create: `tests/unit/domain/analysis/test_probability.py`

- [ ] **Step 1: ARCH_GUARD self-check**

- [ ] **Step 2: Copy probability.py**

```bash
cp "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/src/domain/analysis/probability.py" \
   "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/domain/analysis/probability.py"
```

- [ ] **Step 3: Find + copy test**

```bash
find "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/tests" -name "test_probability.py"
```

Copy to `tennis-paper-lab/tests/unit/domain/analysis/test_probability.py`.

- [ ] **Step 4: Run tests, fix import errors if any**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/domain/analysis/ -v
```

If imports fail (e.g., probability.py imports from a module not present in tennis-paper-lab), copy the missing modules too. Likely needed: `src/models/bookmaker_prob.py` or similar (check via grep).

```bash
grep -r "from src\." "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/domain/analysis/probability.py"
```

For each missing import, find in ana bot + copy.

Expected after fixes: All probability tests PASS.

---

## Task 4: Copy odds_client.py base from ana bot

**Files:**
- Create: `src/infrastructure/apis/odds_client.py`
- Create: `tests/unit/infrastructure/apis/test_odds_client.py`

- [ ] **Step 1: ARCH_GUARD self-check**

- [ ] **Step 2: Copy odds_client.py**

```bash
cp "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/src/infrastructure/apis/odds_client.py" \
   "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/infrastructure/apis/odds_client.py"
```

- [ ] **Step 3: Find + copy existing test file**

```bash
find "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/tests" -name "test_odds_client.py" | head -1
```

Copy to `tennis-paper-lab/tests/unit/infrastructure/apis/test_odds_client.py`.

- [ ] **Step 4: Run + fix import errors**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/infrastructure/apis/test_odds_client.py -v 2>&1 | tail -20
```

If imports fail (config settings differences), adjust by hand. May need to modify import paths.

Expected: All odds_client tests PASS.

- [ ] **Step 5: Verify ODDS_API_KEY env loaded by config**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
PYTHONIOENCODING=utf-8 python -c "
import os
print('ODDS_API_KEY set:', bool(os.getenv('ODDS_API_KEY')))
"
```

If not set: add to tennis-paper-lab/.env or read from parent.

---

## Task 5: Add tennis fetch methods to odds_client

**Files:**
- Modify: `src/infrastructure/apis/odds_client.py`
- Modify: `tests/unit/infrastructure/apis/test_odds_client.py`

- [ ] **Step 1: Write failing test for tennis fetch**

Append to `test_odds_client.py`:

```python
def test_fetch_tennis_atp_french_open_returns_matches(monkeypatch):
    """ATP French Open endpoint'i çağırır + match list döner."""
    from src.infrastructure.apis.odds_client import OddsClient

    fake_resp = [
        {
            "id": "abc123",
            "sport_key": "tennis_atp_french_open",
            "commence_time": "2026-05-28T14:00:00Z",
            "home_team": "Yuta Shimizu",
            "away_team": "Bernard Tomic",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "markets": [
                        {"key": "h2h", "outcomes": [
                            {"name": "Yuta Shimizu", "price": 2.5},
                            {"name": "Bernard Tomic", "price": 1.6},
                        ]}
                    ],
                }
            ],
        }
    ]
    class FakeResp:
        status_code = 200
        def json(self): return fake_resp

    def fake_get(url, params=None, timeout=None):
        assert "tennis_atp_french_open" in url
        return FakeResp()

    client = OddsClient(api_key="test", http_get=fake_get)
    matches = client.fetch_tennis_odds("tennis_atp_french_open")
    assert len(matches) == 1
    assert matches[0]["home_team"] == "Yuta Shimizu"


def test_fetch_tennis_odds_api_error_returns_empty():
    """5xx → boş liste, no exception."""
    from src.infrastructure.apis.odds_client import OddsClient
    import httpx

    def fake_get(url, params=None, timeout=None):
        raise httpx.HTTPError("server error")

    client = OddsClient(api_key="test", http_get=fake_get)
    matches = client.fetch_tennis_odds("tennis_atp_french_open")
    assert matches == []
```

- [ ] **Step 2: Run, expect FAIL (no method)**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/infrastructure/apis/test_odds_client.py::test_fetch_tennis -v
```

Expected: FAIL "no attribute 'fetch_tennis_odds'"

- [ ] **Step 3: Implement fetch_tennis_odds**

Add to `OddsClient` class in `src/infrastructure/apis/odds_client.py`:

```python
def fetch_tennis_odds(self, sport_key: str, regions: str = "us,uk,eu",
                     markets: str = "h2h,totals") -> list:
    """Tennis-specific endpoint çağrısı.

    sport_key: tennis_atp_french_open, tennis_wta_french_open, etc.
    regions: comma-separated region codes
    markets: comma-separated market keys (h2h, totals, spreads)

    Returns: list of match dicts with bookmakers + outcomes. API error → [].
    """
    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": self.api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "decimal",
    }
    try:
        resp = self._http_get(url, params=params, timeout=15)
        if resp.status_code != 200:
            logger.warning("Odds API %s returned %d", sport_key, resp.status_code)
            return []
        return resp.json() or []
    except (httpx.HTTPError, httpx.TimeoutException, ValueError) as e:
        logger.warning("Odds API %s fetch failed: %s", sport_key, e)
        return []
```

- [ ] **Step 4: Run tests, expect PASS**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/infrastructure/apis/test_odds_client.py -v
```

Expected: All odds_client tests PASS (including 2 new tennis tests).

---

## Task 6: Create tennis_odds_matcher.py (NEW)

**Files:**
- Create: `src/domain/matching/tennis_odds_matcher.py`
- Create: `tests/unit/domain/matching/test_tennis_odds_matcher.py`

- [ ] **Step 1: Write 10 failing tests**

Create `tests/unit/domain/matching/test_tennis_odds_matcher.py`:

```python
"""Polymarket slug → Odds API match — fuzzy player name matching."""
from datetime import date
from src.domain.matching.tennis_odds_matcher import (
    parse_polymarket_slug,
    normalize_player_name,
    match_polymarket_to_odds,
)


def test_parse_polymarket_slug_atp_moneyline():
    parsed = parse_polymarket_slug("atp-shimizu-tomic-2026-05-27")
    assert parsed.tour == "atp"
    assert parsed.players == ["shimizu", "tomic"]
    assert parsed.date == date(2026, 5, 27)


def test_parse_polymarket_slug_wta_with_market_suffix():
    parsed = parse_polymarket_slug("wta-vekic-osaka-2026-05-28-match-total-21pt5")
    assert parsed.tour == "wta"
    assert parsed.players == ["vekic", "osaka"]
    assert parsed.date == date(2026, 5, 28)


def test_normalize_player_name_lowercase():
    assert normalize_player_name("Yuta Shimizu") == "yuta shimizu"


def test_normalize_player_name_strips_accents():
    assert normalize_player_name("Félix Auger-Aliassime") == "felix auger-aliassime"


def test_match_polymarket_to_odds_exact_lastname_match():
    polymarket_slug = "atp-shimizu-tomic-2026-05-27"
    odds_matches = [
        {
            "home_team": "Yuta Shimizu",
            "away_team": "Bernard Tomic",
            "commence_time": "2026-05-27T14:00:00Z",
        }
    ]
    result = match_polymarket_to_odds(polymarket_slug, odds_matches)
    assert result is not None
    assert result["home_team"] == "Yuta Shimizu"


def test_match_no_player_match_returns_none():
    polymarket_slug = "atp-federer-nadal-2026-05-27"
    odds_matches = [
        {
            "home_team": "Novak Djokovic",
            "away_team": "Stefanos Tsitsipas",
            "commence_time": "2026-05-27T14:00:00Z",
        }
    ]
    result = match_polymarket_to_odds(polymarket_slug, odds_matches)
    assert result is None


def test_match_date_tolerance_plus_minus_one_day():
    polymarket_slug = "atp-shimizu-tomic-2026-05-27"
    odds_matches = [
        {
            "home_team": "Yuta Shimizu",
            "away_team": "Bernard Tomic",
            "commence_time": "2026-05-28T01:00:00Z",  # next day UTC, +/-1 day OK
        }
    ]
    result = match_polymarket_to_odds(polymarket_slug, odds_matches)
    assert result is not None


def test_match_date_outside_tolerance_returns_none():
    polymarket_slug = "atp-shimizu-tomic-2026-05-27"
    odds_matches = [
        {
            "home_team": "Yuta Shimizu",
            "away_team": "Bernard Tomic",
            "commence_time": "2026-05-30T14:00:00Z",  # 3 days off
        }
    ]
    result = match_polymarket_to_odds(polymarket_slug, odds_matches)
    assert result is None


def test_match_hyphenated_last_name():
    polymarket_slug = "atp-auger-medvedev-2026-05-27"
    odds_matches = [
        {
            "home_team": "Felix Auger-Aliassime",
            "away_team": "Daniil Medvedev",
            "commence_time": "2026-05-27T14:00:00Z",
        }
    ]
    result = match_polymarket_to_odds(polymarket_slug, odds_matches)
    assert result is not None


def test_match_truncated_polymarket_name():
    """Polymarket truncates: 'khachan' → 'khachanov'."""
    polymarket_slug = "atp-khachan-trungel-2026-05-27"
    odds_matches = [
        {
            "home_team": "Karen Khachanov",
            "away_team": "Marco Trungelliti",
            "commence_time": "2026-05-27T14:00:00Z",
        }
    ]
    result = match_polymarket_to_odds(polymarket_slug, odds_matches)
    assert result is not None
```

- [ ] **Step 2: Run, expect 10 fail (ImportError)**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/domain/matching/test_tennis_odds_matcher.py -v
```

- [ ] **Step 3: Implement matcher**

Create `src/domain/matching/tennis_odds_matcher.py`:

```python
"""Polymarket tennis market slug → Odds API match resolver.

Polymarket slug pattern: "atp-{player1}-{player2}-YYYY-MM-DD[-suffix]"
Player names truncated to 7-8 chars typically.

Odds API: full player names ("Karen Khachanov" vs "Marco Trungelliti")
+ commence_time ISO datetime.

Matcher: tokenize + lowercase + accent strip + prefix match + date ± 1 day.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional


@dataclass(frozen=True)
class ParsedSlug:
    """Polymarket slug parsed into components."""
    tour: str  # "atp" or "wta"
    players: list[str]  # 2 truncated last-name tokens
    date: date


def parse_polymarket_slug(slug: str) -> ParsedSlug:
    """Parse Polymarket slug to extract tour + players + date.

    Slug format: "{tour}-{p1}-{p2}-YYYY-MM-DD[-suffix]"
    e.g. "atp-shimizu-tomic-2026-05-27" or
         "wta-vekic-osaka-2026-05-28-match-total-21pt5"
    """
    parts = slug.split("-")
    # parts: [tour, p1, p2, YYYY, MM, DD, ...suffix]
    if len(parts) < 6:
        raise ValueError(f"Invalid slug: {slug}")
    tour = parts[0]
    p1, p2 = parts[1], parts[2]
    year, month, day = int(parts[3]), int(parts[4]), int(parts[5])
    return ParsedSlug(tour=tour, players=[p1, p2], date=date(year, month, day))


def normalize_player_name(name: str) -> str:
    """Lowercase + strip accents (NFD decompose + remove combining marks)."""
    nfd = unicodedata.normalize("NFD", name)
    no_accents = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return no_accents.lower()


def _token_prefix_match(slug_token: str, odds_name: str) -> bool:
    """Slug token is prefix of any word in odds_name (after normalize)."""
    norm_name = normalize_player_name(odds_name)
    words = norm_name.replace("-", " ").split()
    return any(w.startswith(slug_token.lower()) for w in words)


def match_polymarket_to_odds(slug: str, odds_matches: list[dict]) -> Optional[dict]:
    """Polymarket slug → Odds API match dict (or None).

    Args:
        slug: Polymarket slug "atp-shimizu-tomic-2026-05-27"
        odds_matches: List of Odds API match dicts (home_team, away_team, commence_time).

    Returns:
        Best matching odds dict if both players + date within ±1 day match. None otherwise.
    """
    try:
        parsed = parse_polymarket_slug(slug)
    except ValueError:
        return None
    target_date = parsed.date
    for m in odds_matches:
        commence = m.get("commence_time", "")
        try:
            odds_dt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
        except ValueError:
            continue
        # Date tolerance ±1 day
        date_delta = abs((odds_dt.date() - target_date).days)
        if date_delta > 1:
            continue
        home = m.get("home_team", "")
        away = m.get("away_team", "")
        # Both slug players must match SOMETHING in home or away names
        p1_matches = _token_prefix_match(parsed.players[0], home) or \
                     _token_prefix_match(parsed.players[0], away)
        p2_matches = _token_prefix_match(parsed.players[1], home) or \
                     _token_prefix_match(parsed.players[1], away)
        if p1_matches and p2_matches:
            return m
    return None
```

- [ ] **Step 4: Run tests, expect 10 PASS**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/domain/matching/test_tennis_odds_matcher.py -v
```

Expected: 10/10 PASS.

---

## Task 7: Rewrite tennis_market_enricher.py

**Files:**
- Rewrite: `src/strategy/enrichment/tennis_market_enricher.py`
- Rewrite: `tests/unit/strategy/enrichment/test_tennis_market_enricher.py`

This is the BIGGEST task. Subagent should:

- [ ] **Step 1: ARCH_GUARD self-check + read current file**

```bash
wc -l "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/strategy/enrichment/tennis_market_enricher.py"
cat "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/strategy/enrichment/tennis_market_enricher.py" | head -80
```

Note the current interface: function signature, inputs, outputs, return type. The REWRITE must preserve the EXTERNAL interface (caller in entry pipeline). Internal logic replaced.

- [ ] **Step 2: Write new tests (15+ cases)**

Existing tests assume Sackmann pipeline. REWRITE the test file with Odds API pipeline:

Key test cases:
1. `test_enricher_no_odds_match_returns_none` — Polymarket slug not in Odds API → skip
2. `test_enricher_insufficient_bookmakers_returns_none` — bm_weight < 5 → skip
3. `test_enricher_no_sharp_returns_none` — has_sharp=False → skip (B confidence basket pattern)
4. `test_enricher_sharp_present_returns_enriched` — full pipeline → EnrichedMarket
5. `test_enricher_anchor_probability_set_from_bookmaker` — anchor_prob = bookmaker_prob.probability
6. `test_enricher_confidence_A_when_sharp` — confidence == "A"
7. `test_enricher_h2h_market_processed` — moneyline path
8. `test_enricher_totals_market_processed` — match_total path
9. `test_enricher_buy_yes_direction_probability_correct` — owned side prob
10. `test_enricher_buy_no_direction_probability_correct` — inverted side prob
11. `test_enricher_odds_api_error_falls_back_gracefully` — API down → skip not crash
12. `test_enricher_exclude_combos_still_applies` — FAZ 1 filter still respected
13. `test_enricher_audit_fields_set` — bookmaker_prob, num_bookmakers, has_sharp set on EnrichedMarket
14. `test_enricher_market_not_in_atp_endpoint_tries_wta` — endpoint fallback
15. `test_enricher_extra_polymarket_market_skipped_log_warning` — unsupported market_type logged

Full test code provided in spec annexes — subagent expands this scaffold with actual code matching existing EnrichedMarket dataclass shape.

- [ ] **Step 3: Read EnrichedMarket model**

```bash
grep -rn "class EnrichedMarket" "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/" 2>/dev/null
```

Inspect the dataclass to know what fields enricher must produce.

- [ ] **Step 4: Rewrite enricher**

Replace `src/strategy/enrichment/tennis_market_enricher.py` with new implementation. Key changes:
- Remove Sackmann predictor import
- Add OddsClient + tennis_odds_matcher imports
- Add probability + confidence imports
- enrich_market signature unchanged (preserve callers)
- Internal:
  1. parse slug → tour, players, date, market_type
  2. Check tour in active endpoints (config-driven list)
  3. odds_client.fetch_tennis_odds(endpoint) (cached)
  4. tennis_odds_matcher.match_polymarket_to_odds(slug, odds_matches)
  5. If no match → return None (log skipped)
  6. probability.compute_consensus_probability(odds_match.bookmakers, owned_side)
  7. confidence.derive_confidence(bm_weight, has_sharp)
  8. If confidence != "A" → return None
  9. Build EnrichedMarket with anchor_probability = bookmaker_prob.probability + audit fields

Sample skeleton (subagent fills full body):

```python
"""Tennis market enricher — Odds API bookmaker konsensüsünden anchor_probability.

Sackmann/Glicko2 modelinden geçilen sürüm. Tek tahmin kaynağı: Odds API
multi-bookmaker konsensüsü, vig-removed (basket pattern).
"""
from __future__ import annotations

import logging
from typing import Optional

from src.config.settings import AppConfig
from src.domain.analysis.confidence import derive_confidence
from src.domain.analysis.probability import compute_consensus_probability
from src.domain.matching.tennis_odds_matcher import (
    match_polymarket_to_odds,
    parse_polymarket_slug,
)
from src.infrastructure.apis.odds_client import OddsClient
from src.models.enriched_market import EnrichedMarket  # adjust per actual import
from src.models.market import MarketCandidate  # adjust per actual

logger = logging.getLogger(__name__)


def enrich_market(
    market: MarketCandidate,
    cfg: AppConfig,
    odds_client: OddsClient,
    odds_cache: dict,
) -> Optional[EnrichedMarket]:
    """Polymarket market → EnrichedMarket (Odds API based).

    Returns None if:
      - Polymarket slug Odds API'de eşleşmiyor (Challenger / yok)
      - bookmaker_weight < 5 (confidence C)
      - has_sharp=False (confidence B, basket pattern: skip)
      - Edge altında veya exclude_combos kapatılmış (downstream handle)
    """
    try:
        parsed = parse_polymarket_slug(market.slug)
    except ValueError:
        logger.warning("Tennis enricher: slug parse failed: %s", market.slug)
        return None

    # Match in active endpoints
    endpoints = cfg.tennis.active_odds_endpoints  # config-driven list
    odds_match = None
    for endpoint in endpoints:
        if not endpoint.startswith(f"tennis_{parsed.tour}"):
            continue
        matches = odds_cache.get(endpoint, [])
        odds_match = match_polymarket_to_odds(market.slug, matches)
        if odds_match is not None:
            break

    if odds_match is None:
        return None  # Skip: no bookmaker data (Challenger / not covered)

    # Compute consensus probability for OWNED side
    bm_prob = compute_consensus_probability(odds_match.get("bookmakers", []),
                                            market.owned_side)
    if bm_prob is None:
        return None

    conf = derive_confidence(bm_prob.num_bookmakers, bm_prob.has_sharp)
    if conf != "A":
        return None  # basket pattern: only A trades

    return EnrichedMarket(
        # ... existing required fields, copying from market ...
        anchor_probability=bm_prob.probability,
        bookmaker_prob=bm_prob.probability,
        num_bookmakers=bm_prob.num_bookmakers,
        has_sharp=bm_prob.has_sharp,
        confidence=conf,
        # ... other fields ...
    )
```

(Subagent: fill EnrichedMarket fields per actual class definition.)

- [ ] **Step 5: Run tests, expect 15+ PASS**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/strategy/enrichment/test_tennis_market_enricher.py -v
```

If failures: debug + fix mismatch between test expectations and EnrichedMarket actual schema.

---

## Task 8: Update tennis_signal_adapter.py

**Files:**
- Modify: `src/strategy/entry/tennis_signal_adapter.py`

- [ ] **Step 1: ARCH_GUARD self-check + read current file**

```bash
cat "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/strategy/entry/tennis_signal_adapter.py"
```

- [ ] **Step 2: Replace anchor_probability source**

Currently: `anchor_probability=candidate.model_p` (Sackmann output).

New: `anchor_probability=candidate.bookmaker_prob` or equivalent from EnrichedMarket.

(Subagent reads actual line numbers, makes minimal edit.)

- [ ] **Step 3: Run signal adapter tests**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/strategy/entry/test_tennis_signal_adapter.py -v
```

Expected: PASS.

---

## Task 9: Update tennis_factory.py

**Files:**
- Modify: `src/orchestration/tennis_factory.py`

- [ ] **Step 1: ARCH_GUARD self-check + identify Sackmann deps**

```bash
grep -nE "sackmann|Glicko|predictor|tennis_player_resolver|ratings_store" \
  "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/orchestration/tennis_factory.py"
```

- [ ] **Step 2: Replace Sackmann construction with odds_client**

Remove import lines + replace with:

```python
from src.infrastructure.apis.odds_client import OddsClient

# ... in factory function:
odds_client = OddsClient()  # uses ODDS_API_KEY env
```

Update the enricher construction call to pass `odds_client`.

(Subagent edits actual lines.)

- [ ] **Step 3: Run factory + integration tests**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/orchestration/test_tennis_factory.py tests/integration/ -v 2>&1 | tail -20
```

Expected: PASS or known failures (e.g., integration tests reaching for Sackmann that will be deleted in next tasks — note them but proceed).

---

## Task 10: Update config_tennis.yaml

**Files:**
- Modify: `config_tennis.yaml`

- [ ] **Step 1: ARCH_GUARD self-check**

- [ ] **Step 2: Find Sackmann sections**

```bash
grep -nE "confidence_tier_a|confidence_tier_b|data_dir|tml_dir|ratings_cache|sackmann_years|challenger_years|diagnostic_log_dir|match_start_refresh_every_n_ticks" \
  "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/config_tennis.yaml"
```

- [ ] **Step 3: Remove identified lines + replace tennis section with active_odds_endpoints**

Edit `config_tennis.yaml`:

OLD (Sackmann sections under `tennis:`):
```yaml
tennis:
  data_dir: "data/sackmann_cache"
  tml_dir: "data/tml_cache"
  ratings_cache: "data/tennis_ratings.json"
  # ... other Sackmann config ...
  confidence_tier_a: { ... }
  confidence_tier_b: { ... }
```

NEW:
```yaml
tennis:
  # 2026-05-28 (SPEC-odds-api-tennis): Sackmann silindi, Odds API bookmaker
  # konsensüsü kullanılır. Aktif endpoint listesi MVP'de manuel update
  # (sezon değişimleri için).
  active_odds_endpoints:
    - tennis_atp_french_open
    - tennis_wta_french_open
    # Wimbledon başladığında ekle: tennis_atp_wimbledon, tennis_wta_wimbledon
    # US Open: tennis_atp_us_open, tennis_wta_us_open
    # Australian Open: tennis_atp_aus_open, tennis_wta_aus_open_singles
  # Odds API kapsaması: h2h (moneyline) + totals (match_total). Sub-market'ler
  # (set_handicap, set_totals, first_set_winner) DESTEKLENMEZ — exclude_combos
  # ile kapatılır.
```

- [ ] **Step 4: Verify config loads**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
PYTHONIOENCODING=utf-8 python -c "
from pathlib import Path
from src.config.settings import load_config
cfg = load_config(Path('config_tennis.yaml'))
print('active_odds_endpoints:', cfg.tennis.active_odds_endpoints)
"
```

May fail if `TennisConfig` Pydantic model still requires removed fields. If so:
- Step 4a: Read `src/config/settings.py` TennisConfig class
- Step 4b: Remove fields not in new yaml + add `active_odds_endpoints: list[str] = Field(default_factory=list)`

Re-run config load — expected PASS.

---

## Task 11: Delete Sackmann domain code

**Files (DELETE):**
- `src/domain/prediction/` (komple dizin)
- `src/domain/matching/tennis_player_resolver.py`
- Tests bunlara ait

- [ ] **Step 1: Check no other code imports them**

```bash
grep -rnE "from src\.domain\.prediction|from src\.domain\.matching\.tennis_player_resolver" \
  "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/" 2>/dev/null
```

If any imports remain: STOP. Those files need refactoring first (probably tennis_market_enricher OR tennis_factory still has reference).

- [ ] **Step 2: Delete prediction dir + tests**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
rm -rf src/domain/prediction/ && \
rm -f src/domain/matching/tennis_player_resolver.py && \
rm -rf tests/unit/domain/prediction/ && \
rm -f tests/unit/domain/matching/test_tennis_player_resolver.py
```

- [ ] **Step 3: Run full test suite**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q 2>&1 | tail -10
```

Expected: all PASS (Sackmann test'leri silindi, kalan testler hâlâ geçmeli).

---

## Task 12: Delete Sackmann infrastructure code

**Files (DELETE):**
- `src/infrastructure/data/sackmann_csv_client.py`
- `src/infrastructure/data/sackmann_refresher.py`
- `src/infrastructure/data/tennis_data_uk_client.py`
- `src/infrastructure/data/tennis_ratings_store.py`
- `src/infrastructure/data/tml_csv_client.py`
- Tests bunlara ait

- [ ] **Step 1: Check no imports remain**

```bash
grep -rnE "sackmann_csv_client|sackmann_refresher|tennis_data_uk_client|tennis_ratings_store|tml_csv_client" \
  "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/" 2>/dev/null
```

If any remain → STOP, refactor caller.

- [ ] **Step 2: Delete**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
rm -f src/infrastructure/data/sackmann_csv_client.py \
      src/infrastructure/data/sackmann_refresher.py \
      src/infrastructure/data/tennis_data_uk_client.py \
      src/infrastructure/data/tennis_ratings_store.py \
      src/infrastructure/data/tml_csv_client.py && \
find tests/unit/infrastructure/data/ -iname "*sackmann*" -delete && \
find tests/unit/infrastructure/data/ -iname "*tennis_data_uk*" -delete && \
find tests/unit/infrastructure/data/ -iname "*ratings_store*" -delete && \
find tests/unit/infrastructure/data/ -iname "*tml*" -delete
```

- [ ] **Step 3: Verify tests still pass**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q 2>&1 | tail -10
```

---

## Task 13: Delete Sackmann data files

**Files (DELETE):**
- `data/sackmann_cache/`
- `data/tennis_ratings.json` (~14MB)
- `data/tennis_ratings.before_itf_rebuild.json` (~3.5MB)
- `data/tml_cache/`

- [ ] **Step 1: ARCH_GUARD self-check + verify size**

```bash
du -sh "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/data/sackmann_cache/" \
       "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/data/tennis_ratings.json" \
       "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/data/tml_cache/" 2>/dev/null
```

- [ ] **Step 2: Delete data files**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
rm -rf data/sackmann_cache/ data/tml_cache/ && \
rm -f data/tennis_ratings.json data/tennis_ratings.before_itf_rebuild.json
```

- [ ] **Step 3: Verify no code references these paths**

```bash
grep -rnE "sackmann_cache|tennis_ratings\.json|tml_cache" \
  "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/" 2>/dev/null
```

Expected: 0 sonuç (config'den de silindi).

---

## Task 14: Final regression test + acceptance

**Files:** none (verification only)

- [ ] **Step 1: Final ARCH_GUARD scan**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
grep -rli "sackmann\|Glicko" src/ tests/ data/ 2>/dev/null
```

Expected: 0 dosya.

- [ ] **Step 2: File size check**

```bash
find src/ -name "*.py" -exec wc -l {} \; | sort -n | tail -5
```

Expected: hiçbir dosya 400 satırı aşmıyor.

- [ ] **Step 3: Full pytest**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q 2>&1 | tail -10
```

Expected: all PASS, 0 FAIL.

- [ ] **Step 4: Bot reload + live verification**

```bash
PYTHONIOENCODING=utf-8 python scripts/reboot.py reload 2>&1 | tail -10
```

Wait 60 saniye, sonra:

```bash
sleep 60 && \
cat data/bot_status.json && \
tail -20 logs/runtime/bot.log
```

Expected:
- bot_status.json: cycle=light (heavy bitti)
- bot.log: bootstrap success, no Sackmann references, Odds API fetches başlamış
- Hiçbir traceback yok

- [ ] **Step 5: Final commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
git add -A && \
git commit -m "$(cat <<'EOF'
feat(tennis): Sackmann tam silme + Odds API bookmaker entegrasyonu

Sackmann/Glicko2 tahmin modeli sport-resolution analizinde %36.7 dogru
(random %50, market %61.5). Buy-and-hold simulasyonu: SL+spike yok ise bot
-$494 yapardi (97 trade). Sackmann winner picking'de zayif: anchor>0.85
"kesin kazanir" dedigi 55 trade'de bile %43.6 dogruluk.

Cozum: Basket bot pattern (derive_confidence + probability) tennis'e
adapte. Sadece A confidence (bookmaker_weight>=5 + sharp Pinnacle/Betfair).
Volume %37'e duser (sadece moneyline + match_total Odds API'de var) ama
beklenen EV pozitife doner.

Silinen:
- src/domain/prediction/ (Glicko2 + tennis_predictor + features)
- src/domain/matching/tennis_player_resolver
- src/infrastructure/data/sackmann_*, tennis_data_uk_*, ratings_store, tml_*
- data/sackmann_cache/, data/tennis_ratings.json (17MB), data/tml_cache/
- Config: tennis.confidence_tier_a/b, data_dir, tml_dir, ratings_cache, vs

Eklenen:
- src/domain/analysis/{confidence,probability}.py (ana bot kopya)
- src/infrastructure/apis/odds_client.py (ana bot kopya + tennis methods)
- src/domain/matching/tennis_odds_matcher.py (Polymarket slug → Odds API)

Rewrite:
- src/strategy/enrichment/tennis_market_enricher.py (Sackmann → Odds API)
- src/orchestration/tennis_factory.py (deps)
- config_tennis.yaml: active_odds_endpoints list

Tests: tum yeni + adapte testler PASS. 0 Sackmann referansi src/, tests/, data/'da.

Spec: docs/superpowers/specs/2026-05-28-odds-api-tennis-design.md (ana bot)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)" 2>&1 | tail -5
```

---

# PHASE 2 — tennis-lab mirror

## Task 15: tennis-lab feature branch

- [ ] **Step 1: Create branch**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab" && \
git checkout -b feature/odds-api-tennis-lab
```

(Note: ana bot worktree olduğu için ana bot'un branch namespace'inde unique olmalı.)

## Task 16: Mirror Phase 1 changes to tennis-lab

- [ ] **Step 1: Diff strategy — Phase 1 sonrası tennis-paper-lab'in commit'inden patch çıkart**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && \
git show HEAD --format="" > /tmp/odds-api-tennis.patch
```

- [ ] **Step 2: Apply file changes manually**

Patch DIRECT apply çalışmaz (farklı repo). Onun yerine:

Her dosya için: `cp` paper-lab'dan tennis-lab'a, sonra config farklarını manuel patch.

```bash
# Yeni dosyalar (verbatim copy):
for f in \
  src/domain/analysis/__init__.py \
  src/domain/analysis/confidence.py \
  src/domain/analysis/probability.py \
  src/infrastructure/apis/odds_client.py \
  src/domain/matching/tennis_odds_matcher.py; do
  mkdir -p "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/$(dirname $f)" && \
  cp "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/$f" \
     "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/$f"
done

# Rewrite'lar (verbatim copy):
for f in \
  src/strategy/enrichment/tennis_market_enricher.py \
  src/strategy/entry/tennis_signal_adapter.py \
  src/orchestration/tennis_factory.py; do
  cp "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/$f" \
     "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/$f"
done

# Test dosyalari:
for f in \
  tests/unit/domain/analysis/test_confidence.py \
  tests/unit/domain/analysis/test_probability.py \
  tests/unit/infrastructure/apis/test_odds_client.py \
  tests/unit/domain/matching/test_tennis_odds_matcher.py \
  tests/unit/strategy/enrichment/test_tennis_market_enricher.py; do
  mkdir -p "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/$(dirname $f)" && \
  cp "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/$f" \
     "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/$f"
done
```

- [ ] **Step 3: Delete Sackmann files in tennis-lab**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab" && \
rm -rf src/domain/prediction/ && \
rm -f src/domain/matching/tennis_player_resolver.py \
      src/infrastructure/data/sackmann_csv_client.py \
      src/infrastructure/data/sackmann_refresher.py \
      src/infrastructure/data/tennis_data_uk_client.py \
      src/infrastructure/data/tennis_ratings_store.py \
      src/infrastructure/data/tml_csv_client.py && \
rm -rf data/sackmann_cache/ data/tml_cache/ && \
rm -f data/tennis_ratings.json data/tennis_ratings.before_itf_rebuild.json && \
rm -rf tests/unit/domain/prediction/ && \
find tests/unit/ -iname "*sackmann*" -delete && \
find tests/unit/ -iname "*ratings_store*" -delete && \
find tests/unit/ -iname "*tml*" -delete
```

- [ ] **Step 4: Update config_tennis.yaml**

Apply same yaml edits as Task 10 (remove Sackmann sections, add active_odds_endpoints).

Lab-specific differences:
- port: 5051 (paper-lab 5052) — keep lab-specific
- bankroll: lab-specific, keep

- [ ] **Step 5: Run full pytest**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab" && \
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q 2>&1 | tail -10
```

Expected: all PASS.

- [ ] **Step 6: Drift check — paper-lab vs lab core files identical**

```bash
for f in src/domain/analysis/confidence.py \
         src/domain/analysis/probability.py \
         src/domain/matching/tennis_odds_matcher.py \
         src/infrastructure/apis/odds_client.py \
         src/strategy/enrichment/tennis_market_enricher.py; do
  echo "=== $f ===" && \
  diff "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/$f" \
       "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/$f"
done
```

Expected: hiç diff yok (birebir aynı).

- [ ] **Step 7: Reload + verify**

```bash
PYTHONIOENCODING=utf-8 python scripts/reboot.py reload 2>&1 | tail -10
sleep 60 && tail -20 logs/runtime/bot.log
```

Expected: bootstrap success, no errors.

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "$(cat <<'EOF'
feat(tennis): Sackmann tam silme + Odds API (tennis-lab mirror)

tennis-paper-lab Phase 1 (commit <SHA>) tennis-lab worktree'sine birebir
mirror edildi. Config-spesifik farklar korundu (port 5051, lab bankroll).

Tests: drift check PASS (5 core dosya birebir aynı). Full pytest PASS.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

# PHASE 3 — Final verification + DECISIONS

## Task 17: 24h live observation + decision gate

Bu manuel iş — implementer SUBAGENT değil, KULLANICI yapar.

- [ ] **Step 1: Tennis-paper-lab 24h çalıştır + win rate'e bak**

Beklenen başarı kriteri (24h sonra):
- En az 10 pozisyon açılmış olmalı
- Sadece A confidence pozisyonları
- Skipped trade'de "no_bookmaker_match", "no_sharp_book", "insufficient_bookmakers" reason'ları görünmeli
- Win rate %60+ (consensus following beklentisi)

Eğer win rate < %50 veya bot pozisyon açmıyor → ROLLBACK.

- [ ] **Step 2: Tennis-lab 24h çalıştır + aynı**

## Task 18: DECISIONS.md SPEC kaydı

**Files:**
- Modify: `c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/DECISIONS.md`

- [ ] **Step 1: SPEC kaydı ekle**

DECISIONS.md §B sonuna append:

```markdown
## SPEC-odds-api-tennis (2026-05-28) — DONE

**Sorun:** Sackmann/Glicko2 tahmin modeli buy-and-hold simulasyonunda 
-$494 net (84 trade, %35.7 win rate). Spike catch yalanı SL+spike ile 
+$238 görüntüsü oluştu ama paper reality'de -$302. Sackmann sub-market'lerde 
yıkıcı: set_totals %16, first_set_winner %29, moneyline %33 doğruluk.

**Çözüm:** Sackmann tam silme + Odds API tennis entegrasyonu. Basket bot 
pattern (derive_confidence + probability) tennis'e adapte. Sadece A confidence 
(bookmaker_weight≥5 + sharp Pinnacle/Betfair).

**Etki:** Volume %37'e düştü (moneyline + match_total Odds API'de var). 
Sub-market'ler (set_handicap, set_totals, first_set_winner) kapandı. Beklenen 
EV: pozitif (%74 favori follow simulasyonu).

**Spec:** docs/superpowers/specs/2026-05-28-odds-api-tennis-design.md
**Plan:** docs/superpowers/plans/2026-05-28-odds-api-tennis.md
**Kapsam:** tennis-lab + tennis-paper-lab (ana bot dışında)
```

- [ ] **Step 2: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && \
git add DECISIONS.md && \
git commit -m "docs(DECISIONS): SPEC-odds-api-tennis kaydı"
```

---

# Acceptance Verification

Plan tamamlandığında bu maddelerin hepsi check'lenmiş olmalı:

- [ ] tennis-paper-lab + tennis-lab'da `grep -ri sackmann\|Glicko` 0 sonuç
- [ ] data/sackmann_cache, data/tennis_ratings.json, data/tml_cache silindi (her iki bot)
- [ ] config_tennis.yaml'da Sackmann sectionları yok
- [ ] 4 yeni komponent (confidence, probability, odds_client, tennis_odds_matcher) tests PASS
- [ ] Enricher rewrite + 15+ test PASS
- [ ] 24h live observation tennis-paper-lab: A confidence pozisyonları açıldı
- [ ] 24h live observation tennis-lab: aynı
- [ ] Drift check: 5 core dosya birebir aynı paper-lab + lab
- [ ] DECISIONS.md SPEC kaydı mevcut
- [ ] pytest full suite PASS her iki bot
- [ ] Hiçbir dosyada `# TODO` / `# FIXME` placeholder yok
