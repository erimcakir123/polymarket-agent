# WTA Predictor Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add WTA (women's tennis) market support to tennis lab. Currently all `wta-*` slugs are skipped at parse time because the Sackmann historical dataset is ATP-only. After this work, both ATP and WTA matches will produce candidates and trades.

**Architecture:** Predictor module (`tennis_predictor.py`) is already tour-agnostic — it operates on Glicko-2 ratings without knowing the tour. The work is in (a) data ingestion: load Sackmann WTA CSVs in parallel with ATP, (b) rating storage: use tour-prefixed keys (`atp:Name`, `wta:Name`) to prevent name collisions, (c) parser/matcher: detect tour from slug and route lookups to the correct tour's player pool. Single JSON ratings file holds both tours.

**Tech Stack:** Python 3.12, Sackmann WTA CSV dataset (https://github.com/JeffSackmann/tennis_wta), existing Glicko-2 + Klaassen-Magnus stack.

**Drift Policy (user request 2026-05-24):** After functional implementation, remove ALL obsolete WTA-skip code, comments, and tests. No half-deleted legacy paths.

---

## Task 1: Download Sackmann WTA CSVs

**Files:**
- Create: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\data\sackmann_cache\wta_matches_2022.csv` (and 2023-2026)

- [ ] **Step 1: Fetch 5 years of WTA match CSVs from Jeff Sackmann's public repo**

Run from tennis-lab worktree root:
```bash
PYTHONIOENCODING=utf-8 python -c "
import urllib.request
from pathlib import Path

dest = Path('data/sackmann_cache')
dest.mkdir(parents=True, exist_ok=True)
base = 'https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master'
for year in (2022, 2023, 2024, 2025, 2026):
    url = f'{base}/wta_matches_{year}.csv'
    out = dest / f'wta_matches_{year}.csv'
    print(f'Fetching {url}...')
    try:
        urllib.request.urlretrieve(url, str(out))
        print(f'  saved {out} ({out.stat().st_size} bytes)')
    except Exception as e:
        print(f'  FAILED: {e}')
"
```

Expected: 5 files (or fewer if some years missing — 2026 may be partial/empty depending on date).

- [ ] **Step 2: Verify files exist and have data**

```bash
ls -la data/sackmann_cache/wta_matches_*.csv
```

Expected: ≥4 files (2022-2025 guaranteed), each ≥100 KB. If 2026 fails, OK — current year may not be published yet.

- [ ] **Step 3: Spot-check CSV column compatibility with ATP format**

```bash
head -2 data/sackmann_cache/wta_matches_2024.csv
head -2 data/sackmann_cache/atp_matches_2024.csv
```

Expected: same 49 columns in same order (winner_name, loser_name, surface, tourney_date, etc.). If WTA has extra/missing columns, downstream parsing must handle it.

- [ ] **Step 4: No commit yet — data files are gitignored**

Skip — `data/sackmann_cache/` is typically gitignored. Move to Task 2.

---

## Task 2: Add WTA CSV reader methods to SackmannCsvClient

**Files:**
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\src\infrastructure\data\sackmann_csv_client.py`
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\tests\unit\infrastructure\data\test_sackmann_csv_client.py`

- [ ] **Step 1: Write failing test for `load_wta_year`**

In `tests/unit/infrastructure/data/test_sackmann_csv_client.py`, add:

```python
def test_load_wta_year_reads_csv(tmp_path: Path) -> None:
    csv_content = (
        "tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,"
        "match_num,winner_id,winner_name,winner_hand,loser_id,loser_name,loser_hand,"
        "score,best_of,round,minutes,"
        "w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,"
        "l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,"
        "winner_rank,winner_rank_points,loser_rank,loser_rank_points\n"
        "2024-W-1,US Open,Hard,128,G,20240826,1,12345,Iga Swiatek,R,67890,Coco Gauff,R,"
        "6-3 6-4,3,F,90,5,2,60,40,30,15,10,2,3,4,3,55,35,28,12,9,3,4,1,1500,3,1200\n"
    )
    csv_path = tmp_path / "wta_matches_2024.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    client = SackmannCsvClient(cache_dir=tmp_path)
    matches = client.load_wta_year(2024)
    assert len(matches) == 1
    assert matches[0].winner_name == "Iga Swiatek"
    assert matches[0].loser_name == "Coco Gauff"
    assert matches[0].surface == "Hard"


def test_load_wta_year_missing_file_returns_empty(tmp_path: Path) -> None:
    client = SackmannCsvClient(cache_dir=tmp_path)
    matches = client.load_wta_year(1999)
    assert matches == []


def test_load_wta_years_sorted_chronologically(tmp_path: Path) -> None:
    def _row(date: str, winner: str, loser: str) -> str:
        return (
            f"id,T,Hard,32,A,{date},1,1,{winner},R,2,{loser},R,"
            "6-3,3,F,,,,,,,,,,,,,,,,,,,,,,,,\n"
        )
    header = (
        "tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,"
        "match_num,winner_id,winner_name,winner_hand,loser_id,loser_name,loser_hand,"
        "score,best_of,round,minutes,"
        "w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,"
        "l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,"
        "winner_rank,winner_rank_points,loser_rank,loser_rank_points\n"
    )
    (tmp_path / "wta_matches_2023.csv").write_text(header + _row("20230615", "Sabalenka", "Rybakina"), encoding="utf-8")
    (tmp_path / "wta_matches_2024.csv").write_text(header + _row("20240115", "Swiatek", "Pegula"), encoding="utf-8")
    client = SackmannCsvClient(cache_dir=tmp_path)
    matches = client.load_wta_years([2024, 2023])
    assert len(matches) == 2
    assert matches[0].match_date.year == 2023
    assert matches[1].match_date.year == 2024
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/infrastructure/data/test_sackmann_csv_client.py::test_load_wta_year_reads_csv -v
```

Expected: FAIL with `AttributeError: 'SackmannCsvClient' object has no attribute 'load_wta_year'`

- [ ] **Step 3: Add `load_wta_year` and `load_wta_years` methods**

In `src/infrastructure/data/sackmann_csv_client.py`, after `load_year` method (after line 91), insert:

```python
    def load_wta_year(self, year: int) -> list[SackmannMatch]:
        """Tek yılın WTA main-draw CSV'sini oku. Dosya yoksa boş döner.

        WTA CSV formatı ATP ile aynı 49-kolon — sadece dosya adı 'wta_matches_'.
        """
        path = self._cache_dir / f"wta_matches_{year}.csv"
        if not path.exists():
            logger.warning("Sackmann WTA CSV missing: %s", path)
            return []
        matches: list[SackmannMatch] = []
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                m = self._parse_row(row)
                if m is not None:
                    matches.append(m)
        logger.info("Loaded %d WTA matches from %s", len(matches), path.name)
        return matches

    def load_wta_years(self, years: list[int]) -> list[SackmannMatch]:
        """Birden fazla yıl WTA main-draw yükle, birleştir, kronolojik sırala."""
        all_matches: list[SackmannMatch] = []
        for y in years:
            all_matches.extend(self.load_wta_year(y))
        all_matches.sort(key=lambda m: m.match_date)
        return all_matches
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/infrastructure/data/test_sackmann_csv_client.py -v
```

Expected: all tests PASS (including 3 new ones).

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/data/sackmann_csv_client.py tests/unit/infrastructure/data/test_sackmann_csv_client.py
git commit -m "feat(sackmann): WTA CSV reader methods (load_wta_year/_years)"
```

---

## Task 3: Add `sackmann_wta_years` to AppConfig + config_tennis.yaml

**Files:**
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\src\config\settings.py`
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\config_tennis.yaml`
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\tests\unit\config\test_settings.py` (if test exists for tennis config; check first)

- [ ] **Step 1: Find tennis config dataclass in settings.py**

```bash
grep -n "sackmann_years\|challenger_years\|class.*Tennis\|class TennisConfig" src/config/settings.py
```

Expected: a dataclass (probably `TennisConfig`) with `sackmann_years: list[int]` field.

- [ ] **Step 2: Add `sackmann_wta_years: list[int]` field to TennisConfig dataclass**

In `src/config/settings.py`, locate the TennisConfig dataclass. Add a new field next to `challenger_years`:

```python
    sackmann_wta_years: list[int] = field(default_factory=list)
```

(Empty default = WTA disabled if not configured.)

- [ ] **Step 3: Add `sackmann_wta_years` to config_tennis.yaml**

In `config_tennis.yaml`, under the `tennis:` block, after `challenger_years:`, add:

```yaml
  sackmann_wta_years: [2022, 2023, 2024, 2025, 2026]
```

- [ ] **Step 4: Verify config loads cleanly**

```bash
PYTHONIOENCODING=utf-8 python -c "
from src.config.settings import load_config
from pathlib import Path
cfg = load_config(Path('config_tennis.yaml'))
print('wta_years:', cfg.tennis.sackmann_wta_years)
assert cfg.tennis.sackmann_wta_years == [2022, 2023, 2024, 2025, 2026]
print('OK')
"
```

Expected: prints `wta_years: [2022, 2023, 2024, 2025, 2026]` and `OK`.

- [ ] **Step 5: Commit**

```bash
git add src/config/settings.py config_tennis.yaml
git commit -m "feat(config): sackmann_wta_years tennis config field"
```

---

## Task 4: Add `tour` field to PlayerRating + tour-prefixed storage

**Files:**
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\src\infrastructure\data\tennis_ratings_store.py`
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\tests\unit\infrastructure\data\test_tennis_ratings_store.py`

- [ ] **Step 1: Write failing test for tour field round-trip**

In `tests/unit/infrastructure/data/test_tennis_ratings_store.py`, add:

```python
def test_store_save_load_preserves_tour_field(tmp_path: Path) -> None:
    """tour field round-trips through save → load."""
    path = tmp_path / "ratings.json"
    store = TennisRatingsStore(path=path)
    sr = SurfaceRating(rating=1500.0, rd=350.0, volatility=0.06)
    atp_player = PlayerRating(
        player_id="atp:Federer", player_name="Roger Federer", tour="atp",
        overall=sr, serve_clay=sr, serve_grass=sr, serve_hard=sr,
        return_clay=sr, return_grass=sr, return_hard=sr,
        last_match_date="2023-09-01", match_count_12mo=20,
    )
    wta_player = PlayerRating(
        player_id="wta:Swiatek", player_name="Iga Swiatek", tour="wta",
        overall=sr, serve_clay=sr, serve_grass=sr, serve_hard=sr,
        return_clay=sr, return_grass=sr, return_hard=sr,
        last_match_date="2024-09-01", match_count_12mo=55,
    )
    store.save({"atp:Federer": atp_player, "wta:Swiatek": wta_player})
    loaded = store.load()
    assert loaded["atp:Federer"].tour == "atp"
    assert loaded["wta:Swiatek"].tour == "wta"
    assert loaded["atp:Federer"].player_name == "Roger Federer"
    assert loaded["wta:Swiatek"].player_name == "Iga Swiatek"


def test_store_load_missing_tour_field_defaults_to_atp(tmp_path: Path) -> None:
    """Backward compat: old JSON without tour field loads as ATP."""
    path = tmp_path / "ratings.json"
    legacy_json = {
        "Federer": {
            "player_id": "Federer", "player_name": "Federer",
            "overall": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "serve_clay": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "serve_grass": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "serve_hard": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "return_clay": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "return_grass": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "return_hard": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "last_match_date": "2023-09-01", "match_count_12mo": 20,
        }
    }
    import json
    path.write_text(json.dumps(legacy_json), encoding="utf-8")
    store = TennisRatingsStore(path=path)
    loaded = store.load()
    assert loaded["Federer"].tour == "atp"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/infrastructure/data/test_tennis_ratings_store.py::test_store_save_load_preserves_tour_field -v
```

Expected: FAIL with `TypeError: __init__() missing required positional argument 'tour'` (or similar).

- [ ] **Step 3: Add `tour` field to PlayerRating dataclass**

In `src/infrastructure/data/tennis_ratings_store.py`, modify PlayerRating:

```python
@dataclass
class PlayerRating:
    player_id: str
    player_name: str
    tour: str           # "atp" | "wta"
    overall: SurfaceRating
    serve_clay: SurfaceRating
    serve_grass: SurfaceRating
    serve_hard: SurfaceRating
    return_clay: SurfaceRating
    return_grass: SurfaceRating
    return_hard: SurfaceRating
    last_match_date: str
    match_count_12mo: int
```

- [ ] **Step 4: Update `load()` to handle missing `tour` field (backward compat)**

In `src/infrastructure/data/tennis_ratings_store.py`, in the `load` method's PlayerRating construction, change:

```python
                out[pid] = PlayerRating(
                    player_id=d["player_id"],
                    player_name=d["player_name"],
                    tour=d.get("tour", "atp"),  # backward compat for pre-WTA JSONs
                    overall=SurfaceRating(**d["overall"]),
                    serve_clay=SurfaceRating(**d["serve_clay"]),
                    serve_grass=SurfaceRating(**d["serve_grass"]),
                    serve_hard=SurfaceRating(**d["serve_hard"]),
                    return_clay=SurfaceRating(**d["return_clay"]),
                    return_grass=SurfaceRating(**d["return_grass"]),
                    return_hard=SurfaceRating(**d["return_hard"]),
                    last_match_date=d["last_match_date"],
                    match_count_12mo=int(d["match_count_12mo"]),
                )
```

(`save` uses `asdict`, so `tour` is auto-serialized — no change needed there.)

- [ ] **Step 5: Run tests to verify they pass**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/infrastructure/data/test_tennis_ratings_store.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/infrastructure/data/tennis_ratings_store.py tests/unit/infrastructure/data/test_tennis_ratings_store.py
git commit -m "feat(ratings): add tour field to PlayerRating + backward-compat load"
```

---

## Task 5: Dual-tour build script with tour-prefixed keys

**Files:**
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\scripts\build_tennis_ratings.py`
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\tests\unit\scripts\test_build_tennis_ratings.py` (if exists)

- [ ] **Step 1: Write failing test for tour-prefixed output**

In `tests/unit/scripts/test_build_tennis_ratings.py` (create if missing — use TDD conventions of existing test files), add:

```python
def test_build_ratings_tour_prefix_keys_no_collision() -> None:
    """Players with same name in ATP and WTA must be stored under different keys."""
    from datetime import datetime
    from scripts.build_tennis_ratings import build_ratings_from_matches
    from src.infrastructure.data.sackmann_csv_client import SackmannMatch

    def _m(date: str, w: str, l: str) -> SackmannMatch:
        return SackmannMatch(
            tourney_id="x", tourney_name="x", surface="Hard", draw_size=32,
            tourney_level="A", match_date=datetime.strptime(date, "%Y%m%d"),
            match_num=1, winner_id="1", winner_name=w, winner_hand="R",
            loser_id="2", loser_name=l, loser_hand="R", score="6-3 6-4",
            best_of=3, round="F", minutes=None,
            w_ace=None, w_df=None, w_svpt=None, w_1stIn=None, w_1stWon=None,
            w_2ndWon=None, w_SvGms=None, w_bpSaved=None, w_bpFaced=None,
            l_ace=None, l_df=None, l_svpt=None, l_1stIn=None, l_1stWon=None,
            l_2ndWon=None, l_SvGms=None, l_bpSaved=None, l_bpFaced=None,
            winner_rank=None, winner_rank_points=None,
            loser_rank=None, loser_rank_points=None,
        )

    atp = [_m("20240101", "Williams", "Other ATP")]
    wta = [_m("20240101", "Williams", "Other WTA")]
    snap = datetime(2024, 6, 1)
    out = build_ratings_from_matches(atp, wta, snapshot_date=snap)

    assert "atp:Williams" in out
    assert "wta:Williams" in out
    assert out["atp:Williams"].tour == "atp"
    assert out["wta:Williams"].tour == "wta"
    assert out["atp:Williams"].player_name == "Williams"
    assert out["wta:Williams"].player_name == "Williams"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/scripts/test_build_tennis_ratings.py::test_build_ratings_tour_prefix_keys_no_collision -v
```

Expected: FAIL (function signature doesn't accept two match lists; or `tour:` keys not produced).

- [ ] **Step 3: Refactor `build_ratings_from_matches` to accept dual-tour input**

In `scripts/build_tennis_ratings.py`, replace the existing `build_ratings_from_matches` function signature and body. The new signature:

```python
def build_ratings_from_matches(
    atp_matches: list[SackmannMatch],
    wta_matches: list[SackmannMatch],
    snapshot_date: datetime,
    tau: float = 0.5,
) -> dict[str, PlayerRating]:
    """Build ratings dict for ATP + WTA. Keys are tour-prefixed (atp:Name / wta:Name).

    Each tour's ratings are computed independently — no cross-tour matches feed
    into the same player profile (Williams in ATP and WTA are different entities).

    Returns:
        dict mapping "{tour}:{player_name}" → PlayerRating(tour=...)
    """
    output: dict[str, PlayerRating] = {}
    for tour, matches in (("atp", atp_matches), ("wta", wta_matches)):
        per_tour = _build_single_tour(matches, snapshot_date, tau)
        for name, rating in per_tour.items():
            output[f"{tour}:{name}"] = PlayerRating(
                player_id=f"{tour}:{name}",
                player_name=name,
                tour=tour,
                overall=rating.overall,
                serve_clay=rating.serve_clay,
                serve_grass=rating.serve_grass,
                serve_hard=rating.serve_hard,
                return_clay=rating.return_clay,
                return_grass=rating.return_grass,
                return_hard=rating.return_hard,
                last_match_date=rating.last_match_date,
                match_count_12mo=rating.match_count_12mo,
            )
    return output


def _build_single_tour(
    matches: list[SackmannMatch],
    snapshot_date: datetime,
    tau: float,
) -> dict[str, PlayerRating]:
    """Build per-tour rating dict (keyed by raw player name). Internal helper."""
    if not matches:
        return {}

    profiles: dict[str, dict] = {}
    matches_sorted = sorted(matches, key=lambda m: m.match_date)

    for m in matches_sorted:
        winner = m.winner_name
        loser = m.loser_name
        if not winner or not loser:
            continue

        surface_key = _surface_key(m.surface)

        if winner not in profiles:
            profiles[winner] = _new_player()
        if loser not in profiles:
            profiles[loser] = _new_player()

        w_overall = profiles[winner]["overall"]
        l_overall = profiles[loser]["overall"]
        profiles[winner]["overall"] = update_rating(w_overall, [(l_overall, 1.0)], tau=tau)
        profiles[loser]["overall"] = update_rating(l_overall, [(w_overall, 0.0)], tau=tau)

        w_serve_key = f"serve_{surface_key}"
        l_serve_key = f"serve_{surface_key}"
        w_serve = profiles[winner][w_serve_key]
        l_serve = profiles[loser][l_serve_key]
        profiles[winner][w_serve_key] = update_rating(w_serve, [(l_serve, 1.0)], tau=tau)
        profiles[loser][l_serve_key] = update_rating(l_serve, [(w_serve, 0.0)], tau=tau)

        w_return_key = f"return_{surface_key}"
        l_return_key = f"return_{surface_key}"
        w_return = profiles[winner][w_return_key]
        l_return = profiles[loser][l_return_key]
        profiles[winner][w_return_key] = update_rating(w_return, [(l_return, 1.0)], tau=tau)
        profiles[loser][l_return_key] = update_rating(l_return, [(w_return, 0.0)], tau=tau)

        profiles[winner]["last_match_date"] = m.match_date
        profiles[loser]["last_match_date"] = m.match_date
        profiles[winner]["match_dates"].append(m.match_date)
        profiles[loser]["match_dates"].append(m.match_date)

    cutoff = snapshot_date - timedelta(days=365)
    output: dict[str, PlayerRating] = {}
    for name, p in profiles.items():
        count_12mo = sum(1 for d in p["match_dates"] if d >= cutoff)
        last_date = p["last_match_date"]
        output[name] = PlayerRating(
            player_id=name,
            player_name=name,
            tour="atp",  # placeholder — caller overwrites with correct tour
            overall=_glicko_to_surface(p["overall"]),
            serve_clay=_glicko_to_surface(p["serve_clay"]),
            serve_grass=_glicko_to_surface(p["serve_grass"]),
            serve_hard=_glicko_to_surface(p["serve_hard"]),
            return_clay=_glicko_to_surface(p["return_clay"]),
            return_grass=_glicko_to_surface(p["return_grass"]),
            return_hard=_glicko_to_surface(p["return_hard"]),
            last_match_date=last_date.strftime("%Y-%m-%d") if last_date else "1970-01-01",
            match_count_12mo=count_12mo,
        )
    return output
```

- [ ] **Step 4: Update `main()` to feed both ATP and WTA matches**

In `scripts/build_tennis_ratings.py`, replace the existing `main()` function body:

```python
def main() -> None:
    logging.basicConfig(level=logging.INFO)
    cfg = load_config(Path("config_tennis.yaml"))
    sackmann_dir = Path(cfg.tennis.data_dir)
    ratings_path = Path(cfg.tennis.ratings_cache)

    client = SackmannCsvClient(cache_dir=sackmann_dir)
    atp_main = client.load_years(cfg.tennis.sackmann_years)
    atp_chall = client.load_challenger_years(cfg.tennis.challenger_years)
    atp_matches = sorted(atp_main + atp_chall, key=lambda m: m.match_date)
    wta_matches = client.load_wta_years(cfg.tennis.sackmann_wta_years)
    logger.info(
        "Loaded %d ATP matches (%d main + %d challenger) + %d WTA matches",
        len(atp_matches), len(atp_main), len(atp_chall), len(wta_matches),
    )

    snapshot_date = datetime.utcnow()
    ratings = build_ratings_from_matches(
        atp_matches, wta_matches,
        snapshot_date=snapshot_date, tau=cfg.tennis.glicko_tau,
    )
    logger.info("Built ratings for %d player-tour entries", len(ratings))

    store = TennisRatingsStore(path=ratings_path)
    store.save(ratings)
    logger.info("Saved ratings to %s", ratings_path)
```

- [ ] **Step 5: Run all build script tests**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/scripts/ -v
```

Expected: all PASS. If old tests called `build_ratings_from_matches(matches, snapshot_date=...)` with single arg, update them to pass `[]` for the WTA arg or split the existing list into atp/wta as the test scenario requires.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_tennis_ratings.py tests/unit/scripts/test_build_tennis_ratings.py
git commit -m "feat(build): dual-tour ratings build with tour-prefixed keys"
```

---

## Task 6: Parser tour detection (remove WTA skip, add tour field)

**Files:**
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\src\strategy\enrichment\tennis_question_parser.py`
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\tests\unit\strategy\enrichment\test_tennis_question_parser.py`
- Delete: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\tests\unit\strategy\enrichment\test_wta_filter.py`

- [ ] **Step 1: Write failing tests for tour detection**

In `tests/unit/strategy/enrichment/test_tennis_question_parser.py`, add:

```python
def test_parse_atp_slug_returns_tour_atp() -> None:
    parsed = parse_tennis_question(
        question="Set 1 Winner: Djokovic vs Alcaraz",
        sports_market_type="tennis_first_set_winner",
        slug="atp-djokovic-alcaraz-roland-garros-2026",
    )
    assert parsed is not None
    assert parsed["tour"] == "atp"


def test_parse_wta_slug_returns_tour_wta() -> None:
    parsed = parse_tennis_question(
        question="Set 1 Winner: Swiatek vs Gauff",
        sports_market_type="tennis_first_set_winner",
        slug="wta-swiatek-gauff-roland-garros-2026",
    )
    assert parsed is not None
    assert parsed["tour"] == "wta"


def test_parse_unknown_prefix_defaults_to_atp() -> None:
    """Slugs without atp-/wta- prefix default to atp (back-compat for malformed slugs)."""
    parsed = parse_tennis_question(
        question="Set 1 Winner: A vs B",
        sports_market_type="tennis_first_set_winner",
        slug="someother-prefix-a-b-2026",
    )
    assert parsed is not None
    assert parsed["tour"] == "atp"
```

- [ ] **Step 2: Run tests to verify failure**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/strategy/enrichment/test_tennis_question_parser.py::test_parse_wta_slug_returns_tour_wta -v
```

Expected: FAIL — current code returns `None` for `wta-` slugs.

- [ ] **Step 3: Replace WTA skip with tour detection**

In `src/strategy/enrichment/tennis_question_parser.py`:

(a) Remove these lines (the WTA skip block and module-level counter — currently lines ~21-23, 35-38, 188-198):

```python
# WTA filter (2026-05-20): predictor uses ATP-only Sackmann data. Any `wta-*`
# slug is rejected at parse time to avoid (a) silent skips from missing ratings
# or (b) coincidental ATP name collisions yielding garbage predictions.
```

```python
# WTA prefix filter: predictor model uses ATP-only Sackmann historical data.
# Any market whose slug indicates WTA is unparseable → return None.
_WTA_SLUG_PREFIX = "wta-"
_wta_skipped_count = 0
```

```python
    # WTA filter (2026-05-20): Sackmann historical data is ATP-only. WTA slugs
    # would either fail player lookup or hit coincidental ATP collisions.
    if slug and slug.lower().startswith(_WTA_SLUG_PREFIX):
        global _wta_skipped_count
        _wta_skipped_count += 1
        if _wta_skipped_count % 10 == 1:
            logger.info(
                "tennis_parser: WTA slug skipped (count=%d) — ATP-only predictor; example=%s",
                _wta_skipped_count, slug[:60],
            )
        return None
```

(b) Add tour detection helper near the top (after `_MARKET_TYPE_MAP`):

```python
def _detect_tour(slug: str) -> str:
    """Detect tour from slug prefix. 'wta-' → wta, else atp."""
    if slug and slug.lower().startswith("wta-"):
        return "wta"
    return "atp"
```

(c) In `parse_tennis_question`, add `tour` to the returned dict:

```python
    surface = _detect_surface(slug=slug, question=question)
    tour = _detect_tour(slug=slug)

    return {
        "p1_name": p1_name,
        "p2_name": p2_name,
        "market_type": market_type,
        "surface": surface,
        "tour": tour,
    }
```

(d) Remove the docstring paragraph about WTA filter (line ~21-23 in module docstring) — update to reflect new behavior:

Replace the docstring lines about "WTA filter" with: `Tour ('atp'/'wta') is inferred from slug prefix.`

- [ ] **Step 4: Delete the obsolete WTA filter test file**

```bash
git rm tests/unit/strategy/enrichment/test_wta_filter.py
```

- [ ] **Step 5: Run parser tests**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/strategy/enrichment/test_tennis_question_parser.py -v
```

Expected: all PASS (including 3 new tour tests).

- [ ] **Step 6: Commit**

```bash
git add src/strategy/enrichment/tennis_question_parser.py tests/unit/strategy/enrichment/test_tennis_question_parser.py
git commit -m "refactor(parser): replace WTA skip with tour detection field"
```

---

## Task 7: Tour-aware player matcher

**Files:**
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\src\domain\matching\tennis_player_matcher.py`
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\src\strategy\enrichment\tennis_market_enricher.py`
- Modify: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\tests\unit\domain\matching\test_tennis_player_matcher.py`

- [ ] **Step 1: Read the existing matcher in full to understand signature**

```bash
cat src/domain/matching/tennis_player_matcher.py
```

Note current signatures of `build_match_index(ratings)` and `match_player(name, ratings, by_full, by_last)`.

- [ ] **Step 2: Write failing test for tour-scoped lookup**

In `tests/unit/domain/matching/test_tennis_player_matcher.py`, add:

```python
def test_match_player_tour_scoped_no_cross_tour_collision() -> None:
    """ATP Williams and WTA Williams resolve to different PlayerRating objects."""
    from src.infrastructure.data.tennis_ratings_store import PlayerRating, SurfaceRating
    sr = SurfaceRating(rating=1500.0, rd=350.0, volatility=0.06)
    atp_williams = PlayerRating(
        player_id="atp:Williams", player_name="Williams", tour="atp",
        overall=sr, serve_clay=sr, serve_grass=sr, serve_hard=sr,
        return_clay=sr, return_grass=sr, return_hard=sr,
        last_match_date="2023-01-01", match_count_12mo=10,
    )
    wta_williams = PlayerRating(
        player_id="wta:Williams", player_name="Williams", tour="wta",
        overall=sr, serve_clay=sr, serve_grass=sr, serve_hard=sr,
        return_clay=sr, return_grass=sr, return_hard=sr,
        last_match_date="2023-01-01", match_count_12mo=50,
    )
    ratings = {"atp:Williams": atp_williams, "wta:Williams": wta_williams}
    by_full, by_last = build_match_index(ratings, tour="atp")
    atp_hit = match_player("Williams", ratings, by_full=by_full, by_last=by_last, tour="atp")
    assert atp_hit is not None
    assert atp_hit.tour == "atp"
    assert atp_hit.match_count_12mo == 10

    by_full_w, by_last_w = build_match_index(ratings, tour="wta")
    wta_hit = match_player("Williams", ratings, by_full=by_full_w, by_last=by_last_w, tour="wta")
    assert wta_hit is not None
    assert wta_hit.tour == "wta"
    assert wta_hit.match_count_12mo == 50
```

- [ ] **Step 3: Run test to verify failure**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/domain/matching/test_tennis_player_matcher.py::test_match_player_tour_scoped_no_cross_tour_collision -v
```

Expected: FAIL — `build_match_index` and `match_player` don't accept `tour` kwarg.

- [ ] **Step 4: Add `tour` parameter to `build_match_index` and `match_player`**

In `src/domain/matching/tennis_player_matcher.py`:

(a) Modify `build_match_index` signature:

```python
def build_match_index(
    ratings: dict[str, PlayerRating],
    tour: str = "atp",
) -> tuple[dict[str, PlayerRating], dict[str, list[PlayerRating]]]:
    """Build (by_full, by_last) lookup indexes filtered to a single tour.

    Only players whose `tour` field matches the argument are included. This
    prevents cross-tour name collisions (e.g., Williams in both ATP and WTA).
    """
    filtered = {pid: r for pid, r in ratings.items() if r.tour == tour}
    # ... rest of existing logic operates on `filtered` instead of `ratings`
```

Replace the existing body so it builds indexes from `filtered`, not `ratings`. The exact internal logic depends on what the current function does — just substitute the filtered dict.

(b) Modify `match_player` signature:

```python
def match_player(
    name: str,
    ratings: dict[str, PlayerRating],
    by_full: dict[str, PlayerRating],
    by_last: dict[str, list[PlayerRating]],
    tour: str = "atp",
) -> Optional[PlayerRating]:
    """Resolve player name → PlayerRating, scoped to one tour.

    `tour` filters fuzzy/fallback candidates so cross-tour matches cannot occur.
    """
```

In the body, if the function has a fallback that scans `ratings.values()` (e.g., for fuzzy matching), filter that scan: `for r in ratings.values() if r.tour == tour`. The `by_full` and `by_last` indexes are already tour-filtered by `build_match_index`.

- [ ] **Step 5: Update existing matcher tests for tour parameter**

Other tests in `test_tennis_player_matcher.py` that build a ratings dict need:
- Each PlayerRating gets `tour="atp"`
- `build_match_index` calls get `tour="atp"`
- `match_player` calls get `tour="atp"`

Quick approach: grep for `PlayerRating(` in that test file, add `tour="atp",` to each instantiation; grep for `build_match_index(` / `match_player(` and add `tour="atp"` if not present.

- [ ] **Step 6: Update `tennis_market_enricher.py` to pass tour through**

In `src/strategy/enrichment/tennis_market_enricher.py`:

(a) Pull `tour` from the parser result:

```python
    p1_name: str = parsed["p1_name"]
    p2_name: str = parsed["p2_name"]
    market_type: str = parsed["market_type"]
    surface: str = parsed["surface"]
    tour: str = parsed["tour"]
```

(b) Pass `tour` to the matcher. Since `by_full`/`by_last` are tour-scoped, they must be rebuilt per tour (cheap, but happens once per market). Simplest:

```python
    # Step 2: Match player names → PlayerRating (tour-scoped lookup)
    if by_full is None or by_last is None:
        by_full, by_last = build_match_index(ratings, tour=tour)

    p1_rating = match_player(p1_name, ratings, by_full=by_full, by_last=by_last, tour=tour)
    p2_rating = match_player(p2_name, ratings, by_full=by_full, by_last=by_last, tour=tour)
```

Caveat: the pre-built `by_full`/`by_last` caches passed by the orchestrator are ATP-only. **Remove that caching path** — the indexes must be tour-aware. Change to always rebuild per market:

```python
    # Tour-scoped indexes. Caching across markets is unsafe since tour differs.
    by_full, by_last = build_match_index(ratings, tour=tour)

    p1_rating = match_player(p1_name, ratings, by_full=by_full, by_last=by_last, tour=tour)
    p2_rating = match_player(p2_name, ratings, by_full=by_full, by_last=by_last, tour=tour)
```

Drop the `by_full=None, by_last=None` kwargs from the `enrich()` signature since they no longer help (different tour per market means no reuse). If callers pass them, accept and ignore them gracefully — or update callers in the same task. Grep for `enrich(` calls in `src/orchestration/` and remove the `by_full=`, `by_last=` kwargs.

- [ ] **Step 7: Run all relevant tests**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/domain/matching/test_tennis_player_matcher.py tests/unit/strategy/enrichment/test_tennis_market_enricher.py -v
```

Expected: all PASS. If enricher test fails due to missing `tour` field on stub ratings, add `tour="atp"` to test fixtures.

- [ ] **Step 8: Commit**

```bash
git add src/domain/matching/tennis_player_matcher.py src/strategy/enrichment/tennis_market_enricher.py tests/unit/domain/matching/test_tennis_player_matcher.py
git commit -m "feat(matcher): tour-scoped player lookup with build_match_index(tour=...)"
```

---

## Task 8: Build WTA ratings + end-to-end smoke test

**Files:**
- Run script: `scripts/build_tennis_ratings.py`
- Verify: `data/tennis_ratings.json`

- [ ] **Step 1: Run the rebuild script**

```bash
PYTHONIOENCODING=utf-8 python scripts/build_tennis_ratings.py 2>&1 | tail -20
```

Expected log lines:
- `Loaded N matches from atp_matches_*.csv` (for each year)
- `Loaded N WTA matches from wta_matches_*.csv` (for each year)
- `Loaded total: ATP=... WTA=...`
- `Built ratings for X player-tour entries` (where X = ATP players + WTA players)
- `Saved ratings to data/tennis_ratings.json`

If WTA CSV fetch failed for a year (Task 1), only those years are skipped — script still succeeds.

- [ ] **Step 2: Verify JSON has both tours**

```bash
PYTHONIOENCODING=utf-8 python -c "
import json
from collections import Counter
d = json.load(open('data/tennis_ratings.json', encoding='utf-8'))
tours = Counter(v['tour'] for v in d.values())
print('Tour distribution:', dict(tours))
print('Total entries:', len(d))
atp_sample = [k for k in d if k.startswith('atp:')][:3]
wta_sample = [k for k in d if k.startswith('wta:')][:3]
print('ATP sample keys:', atp_sample)
print('WTA sample keys:', wta_sample)
"
```

Expected: both `atp` and `wta` counts ≥ 100. Sample keys show prefix.

- [ ] **Step 3: Run full unit test suite to confirm no regression**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/ -q 2>&1 | tail -10
```

Expected: all tests PASS (or only pre-existing failures unrelated to this work).

- [ ] **Step 4: Reboot tennis bot and observe first cycle for WTA candidates**

```bash
PYTHONIOENCODING=utf-8 python scripts/reboot_tennis.py --wipe
```

Then wait for first heavy cycle:

```bash
until PYTHONIOENCODING=utf-8 grep -q "Heavy cycle logged" logs/runtime/bot.log; do sleep 5; done
PYTHONIOENCODING=utf-8 grep -E "Heavy cycle logged|WTA slug skipped" logs/runtime/bot.log | tail -10
```

Expected:
- `Heavy cycle logged N candidates` where N > previous baseline (was 26 with cap 500 ATP-only)
- ZERO `WTA slug skipped` messages (the obsolete log line should be gone after Task 6 drift cleanup)

If WTA slug skipped messages reappear, Task 6 cleanup was incomplete — find and remove.

- [ ] **Step 5: Check trade history for at least one WTA trade**

```bash
PYTHONIOENCODING=utf-8 python -c "
import json
rows = [json.loads(l) for l in open('logs/audit/trade_history.jsonl', encoding='utf-8')]
wta = [r for r in rows if r.get('slug','').startswith('wta-')]
atp = [r for r in rows if r.get('slug','').startswith('atp-')]
print(f'ATP trades: {len(atp)}, WTA trades: {len(wta)}')
if wta:
    print('Sample WTA:', wta[0]['slug'], wta[0]['entry_price'], wta[0]['confidence'])
"
```

Expected: WTA trades ≥ 1 (subject to first-cycle candidate randomness; if 0, run another cycle).

- [ ] **Step 6: Commit final state**

```bash
git add data/tennis_ratings.json  # if not gitignored
git commit -m "feat(wta): rebuild ratings with WTA support enabled" --allow-empty
```

(`--allow-empty` because if ratings JSON is gitignored, the commit message documents the cutover regardless.)

---

## Drift Audit Checklist (run after Task 8)

Per user directive 2026-05-24: "drift falan olacaksa olanları sil sonrasdan".

- [ ] **No `_WTA_SLUG_PREFIX` or `_wta_skipped_count` references remain**

```bash
PYTHONIOENCODING=utf-8 grep -rn "_WTA_SLUG_PREFIX\|_wta_skipped_count" src/ tests/
```

Expected: no results.

- [ ] **No "ATP-only" or "WTA skip" comments remain in active code**

```bash
PYTHONIOENCODING=utf-8 grep -rn "ATP-only\|WTA skip\|wta_skipped\|wta_filter" src/ tests/
```

Expected: no results. (Module docstrings may say "Tour-aware" — that's fine.)

- [ ] **No `test_wta_filter.py` file exists**

```bash
ls tests/unit/strategy/enrichment/test_wta_filter.py 2>&1
```

Expected: "No such file" error.

- [ ] **`enrich()` signature no longer has stale `by_full`/`by_last` kwargs**

```bash
PYTHONIOENCODING=utf-8 grep -n "by_full\|by_last" src/strategy/enrichment/tennis_market_enricher.py
```

Expected: only internal usage inside `enrich()` body (no signature kwargs, no caller plumbing through orchestration).

Any drift found here means a Task didn't finish cleanly — fix in a small follow-up commit before moving on.
