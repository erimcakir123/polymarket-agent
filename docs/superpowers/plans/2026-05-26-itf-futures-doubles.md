# ITF Futures + Doubles Data Expansion Plan

> **For agentic workers:** Use superpowers:subagent-driven-development.

**Goal:** Boost match-count signal so B-tier players with sub-40 main-draw matches/12mo can qualify for A-tier via combined main + Challenger + ITF Futures + doubles match counts. Research showed RD is strongest filter, but `min_matches_12mo` (drives RD via Glicko sample) is a strong second.

**Architecture:**
- Add ITF Futures CSVs to Sackmann pipeline (same author, MIT license, same schema).
- Add doubles match counts to PlayerRating (count for tier filter, but DO NOT update singles Glicko ratings from doubles — different skill).
- Tier-A criterion expanded: A tier qualifies if main_count >= 40 OR combined (main + challenger + futures) >= 60.
- Singles Glicko ratings: unchanged math, but ITF matches feed updates with weight 0.5 (lower-tier reliability).

**Repo:** `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\`

**Drift policy:** Per CLAUDE.md, after each task check `_TOTALS_KEYWORDS`-style residuals. Final ARCH_GUARD sweep at end of all plans.

---

## Task 1: Download Sackmann ITF Futures CSVs

**Files:**
- Create: `data/sackmann_cache/atp_futures_{year}.csv` (and `wta_futures_{year}.csv`) — 2022-2026

- [ ] **Step 1: Fetch via Python urllib**

```bash
PYTHONIOENCODING=utf-8 python -c "
import urllib.request
from pathlib import Path
dest = Path('data/sackmann_cache')
for tour in ('atp', 'wta'):
    base = f'https://raw.githubusercontent.com/JeffSackmann/tennis_{tour}/master'
    # ATP/WTA futures dir uses qual_chall pattern for ITF
    for year in (2022, 2023, 2024, 2025, 2026):
        # Try ITF-specific file path (may be in tennis_futures subdir)
        urls = [
            f'https://raw.githubusercontent.com/JeffSackmann/tennis_{tour}/master/{tour}_matches_futures_{year}.csv',
            f'https://raw.githubusercontent.com/JeffSackmann/tennis_futures/master/{tour}_matches_futures_{year}.csv',
        ]
        for url in urls:
            out = dest / f'{tour}_futures_{year}.csv'
            try:
                urllib.request.urlretrieve(url, str(out))
                print(f'OK {out} from {url}')
                break
            except Exception as e:
                continue
        else:
            print(f'FAIL all URLs for {tour} {year}')
"
```

- [ ] **Step 2: Verify file presence + spot-check schema matches ATP/WTA main draw CSV**

```bash
ls -la data/sackmann_cache/*_futures_*.csv | head
head -1 data/sackmann_cache/atp_futures_2024.csv > /dev/null && echo "atp 2024 readable"
head -2 data/sackmann_cache/atp_futures_2024.csv | tail -1 | wc -c  # rough row width
```

If schemas match the existing 49-column ATP/WTA format (high probability), no parser changes needed.

If schemas differ, report DONE_WITH_CONCERNS and stop — Task 2 will need adjustment.

- [ ] **Step 3: No commit (data files gitignored)**

Verify with `git check-ignore data/sackmann_cache/atp_futures_2024.csv`. If tracked, skip the commit step entirely.

---

## Task 2: Add load_itf_year / load_itf_years to SackmannCsvClient

**Files:**
- Modify: `src/infrastructure/data/sackmann_csv_client.py`
- Modify: `tests/unit/infrastructure/data/test_sackmann_csv_client.py`

- [ ] **Step 1: Write failing test mirroring load_wta_year**

In `test_sackmann_csv_client.py`, add:

```python
def test_load_itf_year_reads_csv(tmp_path: Path) -> None:
    """ATP ITF Futures CSV uses same 49-column schema as main draw."""
    csv_content = (
        "tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,"
        "match_num,winner_id,winner_name,winner_hand,loser_id,loser_name,loser_hand,"
        "score,best_of,round,minutes,"
        "w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,"
        "l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,"
        "winner_rank,winner_rank_points,loser_rank,loser_rank_points\n"
        "2024-ITF1,M15 Cancun,Hard,32,15,20240615,1,99,Some Junior,R,98,Other,R,"
        "6-3 6-4,3,F,90,3,2,55,38,28,15,8,2,3,2,3,52,32,25,10,7,3,4,300,80,310,75\n"
    )
    csv_path = tmp_path / "atp_futures_2024.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    client = SackmannCsvClient(cache_dir=tmp_path)
    matches = client.load_itf_year("atp", 2024)
    assert len(matches) == 1
    assert matches[0].winner_name == "Some Junior"


def test_load_itf_years_sorts_chronologically(tmp_path: Path) -> None:
    # Mirror existing load_wta_years test pattern
    pass  # IMPLEMENT
```

- [ ] **Step 2: Run failing → AttributeError**

- [ ] **Step 3: Add methods**

In `sackmann_csv_client.py`, after load_wta_years methods:

```python
def load_itf_year(self, tour: str, year: int) -> list[SackmannMatch]:
    """ITF Futures CSV (atp veya wta) — alt tour, ana draw ile aynı 49-kolon şema."""
    path = self._cache_dir / f"{tour}_futures_{year}.csv"
    if not path.exists():
        logger.warning("Sackmann ITF CSV missing: %s", path)
        return []
    matches: list[SackmannMatch] = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            m = self._parse_row(row)
            if m is not None:
                matches.append(m)
    logger.info("Loaded %d %s ITF matches from %s", len(matches), tour.upper(), path.name)
    return matches


def load_itf_years(self, tour: str, years: list[int]) -> list[SackmannMatch]:
    all_matches: list[SackmannMatch] = []
    for y in years:
        all_matches.extend(self.load_itf_year(tour, y))
    all_matches.sort(key=lambda m: m.match_date)
    return all_matches
```

- [ ] **Step 4: Tests pass → commit**

```bash
git add src/infrastructure/data/sackmann_csv_client.py tests/
git commit -m "feat(sackmann): ITF Futures CSV readers (load_itf_year/_years)"
```

---

## Task 3: Add ITF years to AppConfig + config_tennis.yaml

**Files:**
- Modify: `src/config/settings.py` (TennisConfig: add `sackmann_atp_itf_years`, `sackmann_wta_itf_years`)
- Modify: `config_tennis.yaml`

- [ ] **Step 1: Test config loads new fields**

In `tests/unit/config/test_tennis_settings.py`:

```python
def test_itf_years_loaded() -> None:
    from src.config.settings import load_config
    from pathlib import Path
    cfg = load_config(Path("config_tennis.yaml"))
    assert cfg.tennis.sackmann_atp_itf_years == [2022, 2023, 2024, 2025, 2026]
    assert cfg.tennis.sackmann_wta_itf_years == [2022, 2023, 2024, 2025, 2026]
```

- [ ] **Step 2: Add fields**

In `settings.py` TennisConfig:

```python
sackmann_atp_itf_years: list[int] = []
sackmann_wta_itf_years: list[int] = []
```

- [ ] **Step 3: Add to yaml**

Under `tennis:`:

```yaml
  sackmann_atp_itf_years: [2022, 2023, 2024, 2025, 2026]
  sackmann_wta_itf_years: [2022, 2023, 2024, 2025, 2026]
```

- [ ] **Step 4: Test passes, commit**

```bash
git commit -m "feat(config): sackmann_atp_itf_years + sackmann_wta_itf_years"
```

---

## Task 4: Update build_tennis_ratings.py to feed ITF (weight 0.5)

**Files:**
- Modify: `scripts/build_tennis_ratings.py`
- Modify: `tests/unit/scripts/test_build_tennis_ratings.py`

- [ ] **Step 1: Read existing build_ratings_from_matches**

```bash
PYTHONIOENCODING=utf-8 grep -n "def build_ratings_from_matches\|def _build_single_tour\|def main" scripts/build_tennis_ratings.py
```

- [ ] **Step 2: Add ITF matches to build script with reduced weight**

The current signature: `build_ratings_from_matches(atp_matches, wta_matches, snapshot_date, tau=0.5)`.

Extend to accept ITF batches separately. New signature:

```python
def build_ratings_from_matches(
    atp_main: list[SackmannMatch],
    wta_main: list[SackmannMatch],
    atp_itf: list[SackmannMatch] | None = None,
    wta_itf: list[SackmannMatch] | None = None,
    snapshot_date: datetime,
    tau: float = 0.5,
    itf_weight: float = 0.5,
) -> dict[str, PlayerRating]:
    """ITF matches feed Glicko updates with reduced weight (0.5x); match counts unchanged."""
    # For each tour: combine main + itf, but mark itf entries with weight
    # _build_single_tour gains weight-aware update logic
```

This requires `_build_single_tour` to weight Glicko updates. The simplest approach:

```python
# In _build_single_tour, accept matches as list of (match, weight) tuples instead of just match
# Default weight 1.0 for main draw
```

OR simpler: do TWO passes — first main draw at full weight, then ITF at half weight. Less surgical but easier to implement.

**Recommended**: tuple-with-weight approach. Add weight param to update calls.

- [ ] **Step 3: Update main() to load ITF + pass to builder**

```python
atp_itf = client.load_itf_years("atp", cfg.tennis.sackmann_atp_itf_years)
wta_itf = client.load_itf_years("wta", cfg.tennis.sackmann_wta_itf_years)
ratings = build_ratings_from_matches(
    atp_main=atp_main + atp_chall,
    wta_main=wta_main,
    atp_itf=atp_itf,
    wta_itf=wta_itf,
    snapshot_date=snapshot_date,
    tau=cfg.tennis.glicko_tau,
)
```

- [ ] **Step 4: Update existing test fixtures**

Most existing tests call `build_ratings_from_matches(atp, wta, snapshot_date=...)`. They'll break — add `atp_itf=None, wta_itf=None` (or `=[]`) to fixtures.

- [ ] **Step 5: Add test that ITF matches feed with reduced weight**

```python
def test_build_ratings_itf_matches_have_reduced_glicko_impact() -> None:
    """ITF match update should move rating less than equivalent main-draw match."""
    # Build minimal: 1 player with no matches.
    # Add 1 main-draw win → measure rating delta.
    # Reset, add 1 ITF win → measure rating delta.
    # Assert ITF delta < main delta (because itf_weight=0.5).
    pass  # IMPLEMENT — depends on _build_single_tour weight handling
```

- [ ] **Step 6: Run tests, commit**

```bash
git add scripts/build_tennis_ratings.py tests/
git commit -m "feat(build): ITF Futures matches feed Glicko with 0.5x weight"
```

---

## Task 5: Add singles_match_count + doubles_match_count to PlayerRating

**Files:**
- Modify: `src/infrastructure/data/tennis_ratings_store.py` (PlayerRating dataclass)
- Modify: `scripts/build_tennis_ratings.py` (compute and populate)
- Modify: `tests/unit/infrastructure/data/test_tennis_ratings_store.py`

**Rationale:** Tier-A classifier needs combined match count. Currently `match_count_12mo` only tracks singles main draw. We'll separate:
- `singles_main_count_12mo` (renamed from `match_count_12mo`)
- `singles_itf_count_12mo`  (new)
- `doubles_count_12mo` (new — for filter signal only)

The classifier (in tennis_market_enricher.classify_tier) sums these for the A-tier `min_matches_12mo` check.

- [ ] **Step 1: Migration plan — keep `match_count_12mo` for backward compat OR rename cleanly?**

Per drift policy ("no drift"): RENAME cleanly. Rename `match_count_12mo` → `singles_main_count_12mo`, add new fields. Backward-compat JSON load: old field → singles_main_count_12mo + 0 itf + 0 doubles.

- [ ] **Step 2: Write failing tests for round-trip**

```python
def test_player_rating_includes_singles_itf_doubles_counts() -> None:
    sr = SurfaceRating(...)
    p = PlayerRating(
        ...,
        singles_main_count_12mo=30,
        singles_itf_count_12mo=15,
        doubles_count_12mo=10,
    )
    store.save({"atp:X": p})
    loaded = store.load()
    assert loaded["atp:X"].singles_main_count_12mo == 30
    assert loaded["atp:X"].singles_itf_count_12mo == 15
    assert loaded["atp:X"].doubles_count_12mo == 10


def test_legacy_match_count_12mo_loaded_as_singles_main() -> None:
    """Old JSON with match_count_12mo loads as singles_main_count_12mo, zeros for itf/doubles."""
    # Hand-write legacy JSON with match_count_12mo=20, no new fields
    # Assert loaded singles_main = 20, itf = 0, doubles = 0
    pass
```

- [ ] **Step 3: Implement dataclass change + backward-compat load**

In `tennis_ratings_store.py`:

```python
@dataclass
class PlayerRating:
    player_id: str
    player_name: str
    tour: str
    overall: SurfaceRating
    serve_clay: SurfaceRating
    # ... unchanged ...
    last_match_date: str
    singles_main_count_12mo: int
    singles_itf_count_12mo: int = 0
    doubles_count_12mo: int = 0
```

Update load() construction:

```python
singles_main = d.get("singles_main_count_12mo")
if singles_main is None:
    singles_main = int(d.get("match_count_12mo", 0))  # backward-compat
out[pid] = PlayerRating(
    ...,
    singles_main_count_12mo=int(singles_main),
    singles_itf_count_12mo=int(d.get("singles_itf_count_12mo", 0)),
    doubles_count_12mo=int(d.get("doubles_count_12mo", 0)),
)
```

- [ ] **Step 4: Update all callsites that reference match_count_12mo**

```bash
PYTHONIOENCODING=utf-8 grep -rn "match_count_12mo" src/ tests/ scripts/ 2>/dev/null
```

For each hit, replace with `singles_main_count_12mo` OR use a property `total_match_count_12mo = singles_main + singles_itf + doubles` if appropriate.

In classify_tier (tennis_market_enricher), the existing check:
```python
features.p1_match_count_12mo >= tier_a.min_matches_12mo
```
should become:
```python
features.p1_main_count + features.p1_itf_count + features.p1_doubles_count >= tier_a.min_matches_12mo
```

(or via a computed `p1_total_count_12mo`). Check feature_extractor too.

- [ ] **Step 5: Populate counts in build script**

In build_tennis_ratings.py, when constructing PlayerRating:

```python
singles_main_count_12mo = count_main_matches_in_12mo(name)  # count from main+chall sources
singles_itf_count_12mo = count_itf_matches_in_12mo(name)
doubles_count_12mo = 0  # set in Task 6 when doubles added
```

For now, populate singles_itf properly. Doubles in Task 6.

- [ ] **Step 6: Tests + commit**

```bash
git add src/infrastructure/data/tennis_ratings_store.py scripts/build_tennis_ratings.py tests/
git commit -m "feat(ratings): split match_count_12mo into singles_main/itf/doubles fields"
```

---

## Task 6: Add ATP/WTA doubles match counts

**Files:**
- Modify: `src/infrastructure/data/sackmann_csv_client.py` (load_doubles_year)
- Modify: `scripts/build_tennis_ratings.py` (count doubles, don't update Glicko)
- Modify: tests

**Doubles handling**: count matches for filter ONLY. Doubles wins/losses do NOT update singles Glicko ratings (different skill set).

- [ ] **Step 1: Download doubles CSVs**

```bash
PYTHONIOENCODING=utf-8 python -c "
import urllib.request
from pathlib import Path
dest = Path('data/sackmann_cache')
for tour in ('atp', 'wta'):
    for year in (2022, 2023, 2024, 2025, 2026):
        urls = [
            f'https://raw.githubusercontent.com/JeffSackmann/tennis_{tour}/master/{tour}_matches_doubles_{year}.csv',
        ]
        for url in urls:
            try:
                out = dest / f'{tour}_doubles_{year}.csv'
                urllib.request.urlretrieve(url, str(out))
                print(f'OK {out}')
                break
            except: pass
"
```

- [ ] **Step 2: Add load_doubles_year/load_doubles_years**

Mirror load_itf pattern. Doubles CSV may have FOUR player columns (winner1, winner2, loser1, loser2). Schema differs from singles — needs new parser or simpler "count only" approach.

For COUNT-ONLY use case: parse winner_name + loser_name fields if present, OR parse all 4 player names from the doubles CSV. Either way, return a list of match dates per player name.

Simpler API:

```python
def load_doubles_match_counts_by_player(self, tour: str, years: list[int], cutoff_date: datetime) -> dict[str, int]:
    """Return {player_name: count_of_doubles_matches_since_cutoff}."""
    counts: dict[str, int] = {}
    # Read each year's CSV, parse 4 player names per row, increment count if date >= cutoff
    return counts
```

- [ ] **Step 3: Wire into build_tennis_ratings.py**

After building singles ratings, compute doubles counts and populate `PlayerRating.doubles_count_12mo`:

```python
cutoff = snapshot_date - timedelta(days=365)
atp_doubles_counts = client.load_doubles_match_counts_by_player("atp", cfg.tennis.sackmann_atp_doubles_years, cutoff)
for name, p in atp_main_ratings.items():
    p.doubles_count_12mo = atp_doubles_counts.get(name, 0)
# same for wta
```

- [ ] **Step 4: Test that doubles count populates without affecting ratings**

```python
def test_doubles_match_counts_populated_but_singles_ratings_unchanged() -> None:
    """Adding doubles CSV must NOT change singles Glicko ratings (different skill)."""
    # Build with only singles data — note p.overall.rating
    # Add doubles data and rebuild — assert p.overall.rating IDENTICAL, but p.doubles_count_12mo > 0
    pass
```

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/data/sackmann_csv_client.py scripts/build_tennis_ratings.py tests/
git commit -m "feat(ratings): doubles match count for tier filter (no Glicko impact)"
```

---

## Task 7: Run rebuild + verify B → A migration

- [ ] **Step 1: Rebuild ratings**

```bash
PYTHONIOENCODING=utf-8 python scripts/build_tennis_ratings.py 2>&1 | tail -15
```

Verify log lines show ITF + doubles loaded.

- [ ] **Step 2: Count B → A transitions**

```bash
PYTHONIOENCODING=utf-8 python -c "
import json
# Load old ratings (if backed up) and new ratings
# For each player, compute would_be_tier under A criteria (main+itf+doubles >= 40, RD <= 100)
# Report how many B players now meet A
new = json.load(open('data/tennis_ratings.json', encoding='utf-8'))
a_capable = 0
b_capable = 0
for k, p in new.items():
    total = p.get('singles_main_count_12mo', 0) + p.get('singles_itf_count_12mo', 0) + p.get('doubles_count_12mo', 0)
    if total >= 40 and p['overall']['rd'] <= 100:
        a_capable += 1
    elif total >= 20 and p['overall']['rd'] <= 150:
        b_capable += 1
print(f'A-capable: {a_capable}, B-capable: {b_capable}')
"
```

Compare to pre-rebuild numbers.

- [ ] **Step 3: Reload tennis bot (state preserved)**

```bash
PYTHONIOENCODING=utf-8 python scripts/reboot_tennis.py --reload
```

- [ ] **Step 4: Restart tennis dashboard (separate process, port 5051)**

Find PID via Get-NetTCPConnection -LocalPort 5051, kill, restart scripts/tennis_dashboard.py.

---

## Per-task drift check (after each commit)

User directive: "her task sonrası var mı dead code drift kod kontrol et".

After each task commit, run:

```bash
PYTHONIOENCODING=utf-8 grep -rn "match_count_12mo" src/ tests/ scripts/ 2>/dev/null | grep -v singles_main_count_12mo
# Should show only legacy fallback in load() — no new code using the old name
```

Plus:

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q 2>&1 | tail -5
```

All passing.

---

## After all tasks: report final state

- B-tier player count → A-tier transition count
- Test count
- Drift grep results
- Files touched
