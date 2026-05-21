# MLB Submarket Infrastructure — Implementation Plan (Plan 3 / 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Each task brief is built per-dispatch (outline format).

**Goal:** `src/infrastructure/mlb_data/` altına Plan 2 domain modüllerini gerçek MLB verisiyle besleyen 5 modül kur: MLB Stats API client (schedule + lineup + game state), Statcast/FanGraphs cache (rate stats via pybaseball), weather client (Open-Meteo), pitcher/batter rate cache (JSONL persistence), scratch detector (lineup change detection).

**Architecture:** Infrastructure layer = I/O. Her client'ın tek sorumluluğu var. Hatalı API çağrılarında retry + structured logging (ARCH_GUARD Kural 12 hata yönetimi). Pure domain modülleri (Plan 2) bu client'ları DIRECTLY import etmez — Plan 4 engine orchestrator dependency injection ile bağlar.

**Tech Stack:** Python 3.12, requests, pybaseball (Statcast wrapper), Open-Meteo HTTP, JSONL persistence. **Yeni bağımlılıklar:** `pybaseball>=2.2`, mevcut: requests/httpx.

**Spec Reference:** [`docs/superpowers/specs/2026-05-21-mlb-submarket-mainbot-integration-design.md`](../specs/2026-05-21-mlb-submarket-mainbot-integration-design.md) §3.1 Infrastructure block.

**Prensipler:**
- TDD: HTTP client'lar için `responses` veya `requests-mock` ile mock'lu test; cache için tmp_path test.
- ARCH_GUARD: infrastructure katmanı ⇒ I/O izinli. Domain import etmez.
- Logging: API success → INFO, hata → WARNING+retry, persistent hata → ERROR.
- Secret yok (Stats API + Statcast public, Open-Meteo public).
- Rate limit: MLB Stats API ~3000/day, polite spacing (1 req/sec). Cache yardımcı.
- No dead code, no drift.

---

## File Structure (Plan 3'te oluşturulacak)

```
src/infrastructure/mlb_data/__init__.py
src/infrastructure/mlb_data/statsapi_client.py        # T1 — MLB Stats API
src/infrastructure/mlb_data/statcast_client.py        # T2 — Baseball Savant via pybaseball
src/infrastructure/mlb_data/weather_client.py         # T3 — Open-Meteo
src/infrastructure/mlb_data/rate_cache.py             # T4 — JSONL persistence
src/infrastructure/mlb_data/scratch_detector.py       # T5 — Lineup change detector

tests/unit/infrastructure/mlb_data/__init__.py
tests/unit/infrastructure/mlb_data/test_<each>.py
```

**Toplam:** 5 modül × ~150 satır + testler. Hiçbiri 400 satır limitini geçmez.

---

## Task 1: statsapi_client.py — MLB Stats API client

**Dosyalar:** `src/infrastructure/mlb_data/statsapi_client.py` + test.

**Endpoints (statsapi.mlb.com):**
- Schedule: `/api/v1/schedule?sportId=1&date=YYYY-MM-DD` → list of games (gamePk, home/away, status).
- Game feed: `/api/v1.1/game/{gamePk}/feed/live` → full GUMBO (lineups, current state, etc.).
- Probable pitchers: `/api/v1/schedule?sportId=1&date=YYYY-MM-DD&hydrate=probablePitcher` → starter info.

**Public API:**
```python
class StatsApiClient:
    def __init__(self, base_url: str = "https://statsapi.mlb.com", timeout: float = 10.0): ...
    def get_schedule(self, date: str) -> list[dict]: ...      # date = YYYY-MM-DD
    def get_game_feed(self, game_pk: int) -> dict: ...
    def get_probable_pitchers(self, date: str) -> dict[int, dict]: ...  # gamePk → {home_pitcher_id, away_pitcher_id, ...}
    def get_lineup(self, game_pk: int) -> dict[str, list[int]]: ...  # {"home": [9 batter_ids], "away": [...]}
```

**TDD steps:**
1. Test: mock requests (responses library) — schedule returns 2 games for date 2026-05-21; one game's feed JSON parse-able.
2. Test: timeout error → raises specific exception (`StatsApiError`).
3. Test: 404 (invalid gamePk) → returns empty/raises.
4. Test: rate-limit (HTTP 429) → retry with backoff (max 3 retries).
5. Fail → impl → pass.
6. Commit: `feat(mlb_data): statsapi_client — schedule + game feed + probable pitchers (SPEC-R Plan 3 T1)`

**Bağımlılık:** `requests`. Yeni paket eklenmiyor.

---

## Task 2: statcast_client.py — Baseball Savant via pybaseball

**Dosyalar:** `src/infrastructure/mlb_data/statcast_client.py` + test.

**Concept:** Plan 2 rate_shrinker'ı pitcher/batter PA outcome rate'leri ister (K%, BB%, HR%). Statcast verisi pybaseball ile gelir.

**Public API:**
```python
class StatcastClient:
    def __init__(self, cache_dir: Path | None = None): ...
    def get_batter_rates(self, mlbam_id: int, season: int) -> dict[str, float]:
        """K%, BB%, HBP%, HR%, 1B%, 2B%, 3B%, OUT_IN_PLAY% — sums to 1.0.
        
        Uses pybaseball.statcast_batter(start, end, mlbam_id) and aggregates 
        events by type.
        """
    def get_pitcher_rates(self, mlbam_id: int, season: int) -> dict[str, float]: ...
```

**Mapping Statcast event → PA outcome:**
- "strikeout" → K
- "walk" → BB
- "hit_by_pitch" → HBP
- "home_run" → HR
- "single" → 1B
- "double" → 2B
- "triple" → 3B
- All other events (field_out, force_out, double_play, etc.) → OUT_IN_PLAY

**TDD steps:**
1. Test: mock pybaseball.statcast_batter return DataFrame with known events → aggregate to rates summing to 1.0.
2. Test: empty DataFrame (no PA) → returns league_constants as fallback.
3. Test: unknown event types → counted in OUT_IN_PLAY (catch-all).
4. Test: pybaseball error → raise `StatcastError`, no silent swallow.
5. Test: file cache works — second call same params reads cached file (no second API call).
6. Fail → impl → pass.
7. Commit: `feat(mlb_data): statcast_client — pybaseball wrapper + event aggregation (SPEC-R Plan 3 T2)`

**Bağımlılık:** `pybaseball>=2.2` (eklenecek requirements.txt'e).

---

## Task 3: weather_client.py — Open-Meteo (free, no API key)

**Dosyalar:** `src/infrastructure/mlb_data/weather_client.py` + test.

**Endpoint:** `https://api.open-meteo.com/v1/forecast?latitude=...&longitude=...&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m`

**Public API:**
```python
class WeatherClient:
    def __init__(self, timeout: float = 5.0): ...
    def get_conditions(self, lat: float, lon: float, time_iso: str) -> dict[str, float]:
        """Returns {wind_mph_to_cf: float, temp_f: float, humidity_pct: float}.
        
        wind_mph_to_cf computed from wind_direction relative to ballpark CF orientation.
        For Plan 3, return raw wind_mph and wind_direction_deg — Plan 4 engine
        converts to CF-relative based on ballpark.
        """
```

**Update v2:** Plan 3'te raw weather döndür. CF projection Plan 4 engine'in işi (ballpark orientation lookup).

So public API simplified:
```python
def get_conditions(self, lat: float, lon: float, time_iso: str) -> dict[str, float]:
    """Returns:
        wind_mph: float
        wind_dir_deg: float  (0=N, 90=E, 180=S, 270=W)
        temp_f: float        (converted from C)
        humidity_pct: float
    """
```

**TDD steps:**
1. Test: mock HTTP → parse Open-Meteo response shape (well-known JSON).
2. Test: unit conversion C→F correct.
3. Test: time_iso outside forecast window → raise ValueError.
4. Test: HTTP error → raise `WeatherError`.
5. Fail → impl → pass.
6. Commit: `feat(mlb_data): weather_client — Open-Meteo raw conditions (SPEC-R Plan 3 T3)`

**Bağımlılık:** requests (mevcut).

---

## Task 4: rate_cache.py — JSONL persistence for player rates

**Dosyalar:** `src/infrastructure/mlb_data/rate_cache.py` + test.

**Concept:** Statcast API çağrıları yavaş (büyük DataFrame). Player rate'lerini cache et: JSONL formatında, key = (mlbam_id, season, role).

**Public API:**
```python
class RateCache:
    def __init__(self, cache_path: Path): ...
    def get(self, mlbam_id: int, season: int, role: str) -> dict[str, float] | None:
        """role = 'batter' | 'pitcher'. Returns rates if cached, else None."""
    def put(self, mlbam_id: int, season: int, role: str, rates: dict[str, float]) -> None: ...
    def clear_expired(self, max_age_days: int = 7) -> None:
        """Remove entries older than max_age_days. Called periodically."""
```

**Storage format (JSONL):** Each line = `{"mlbam_id": int, "season": int, "role": str, "rates": dict, "ts": iso8601}`.

**TDD steps:**
1. Test: put/get roundtrip — cached value matches.
2. Test: get on missing key returns None.
3. Test: rewrite overwrites stale entry (latest wins).
4. Test: clear_expired removes old entries, keeps fresh.
5. Test: cache_path directory created if missing.
6. Test: malformed JSONL line is skipped with WARNING log (no crash).
7. Fail → impl → pass.
8. Commit: `feat(mlb_data): rate_cache — JSONL persistence (SPEC-R Plan 3 T4)`

**Bağımlılık:** stdlib only (json, pathlib, datetime).

---

## Task 5: scratch_detector.py — Lineup change detection

**Dosyalar:** `src/infrastructure/mlb_data/scratch_detector.py` + test.

**Concept:** Lineups announced T-90 minutes. Scratches happen until T-15. Compare current lineup vs previous → detect scratch.

**Public API:**
```python
class ScratchDetector:
    def __init__(self, statsapi: StatsApiClient): ...
    def get_current_lineup(self, game_pk: int) -> dict[str, list[int]]:
        """Wrapper around statsapi.get_lineup with timestamp."""
    def diff(
        self,
        previous: dict[str, list[int]],
        current: dict[str, list[int]],
    ) -> dict[str, list[tuple[int, int]]]:
        """Returns {"home": [(out, in), ...], "away": [...]} — list of swaps."""
```

**TDD steps:**
1. Test: identical lineups → empty diff.
2. Test: one batter swap detected → {"home": [(old_id, new_id)]}.
3. Test: multiple swaps detected.
4. Test: unequal lineup lengths → raise ValueError.
5. Fail → impl → pass.
6. Commit: `feat(mlb_data): scratch_detector — lineup change detection (SPEC-R Plan 3 T5)`

**Bağımlılık:** statsapi_client (T1).

---

## Final Tasks

**Plan 3 tamamlandığında:**
1. Full test suite: `pytest -q` — tüm yeni testler yeşil.
2. DECISIONS.md SPEC-R kaydına Plan 3 tamamlandı notu ekle.
3. Plan dosyasını sil:
   ```bash
   git rm docs/superpowers/plans/2026-05-21-mlb-submarket-infrastructure.md
   git commit -m "chore(plans): SPEC-R Plan 3 (infrastructure) tamamlandı"
   ```
4. requirements.txt'te pybaseball satırı doğrulanır.

---

## Self-Review

- [x] 5 task, her biri tek sorumluluk
- [x] Infrastructure katmanı — I/O izinli, domain import yok
- [x] TDD steps + concrete commit
- [x] Hata yönetimi: ARCH_GUARD Kural 12 (infra → try/except, anlamlı hata)
- [x] No silent error swallow
- [x] Cache + retry stratejisi belirgin
- [x] Plan 2 domain modülleri DIRECTLY çağrılmıyor (Plan 4 engine bağlar)

Plan 3 hazır.
