# Yan Task Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bugün yapılan 4 ORTA-risk fix'inin yan task atlama riskini kapatmak — genel pattern uygulayarak gelecekteki eklemelere otomatik adapte ol.

**Architecture:** Her audit kategorisi için 3 aşama: (1) paralel ajanla kapsama tarama, (2) regression testi yaz (kapsama assertion'ları), (3) genel pattern implement. TDD prensibi.

**Tech Stack:** Python 3.12+, pytest, Pydantic (Position model), Polymarket gamma client.

---

## Task 1: UI Etiket Genel Pattern

**Files:**
- Modify: `src/presentation/dashboard/static/js/fmt.js:251-280` (exitReasonLabel)
- Modify: `src/presentation/dashboard/static/js/feed.js:214` (caller)
- Test: yok (frontend, manuel test)

- [ ] **Step 1.1: Kapsama tarama**

Tüm `ExitReason` enum değerlerini listele (`src/models/enums.py`). Her birinin PnL'ye göre tone değişmesi gereken/gerekmeyen tarafını belirle:

```
ExitReason → PnL bazlı etiket gerek mi?
- scale_out_tier_N  : ✓ kar→Take Profit, zarar→Partial sell (mevcut fix)
- partial_sl        : ✗ adı zaten "negatif" anlamı taşıyor (her zaman zarar)
- stop_loss         : ✗ aynı
- graduated_sl      : ✗ aynı (artık kapalı)
- near_resolve      : ✓ resolve_yes=kâr, resolve_no=zarar olabilir
- market_flip       : ✓ teorik olarak iki yönde
- score_exit        : ✗ her zaman zarar
- hold_revoked      : ✗ her zaman zarar
- never_in_profit   : ✗ her zaman zarar
- ultra_low_guard   : ✗ her zaman zarar
- predictive_dead   : ✗ her zaman zarar
- blind_sl          : ✗ her zaman zarar
```

- [ ] **Step 1.2: fmt.js güncelle — near_resolve da PnL bazlı**

```js
// fmt.js içinde exitReasonLabel(raw, pnl)
if (r === "near_resolve") {
  return isLoss
    ? { text: "Closed (loss)", emoji: "❌", tone: "neg" }
    : { text: "Near resolve", emoji: "✅", tone: "pos" };
}
if (r === "market_flip") {
  return isLoss
    ? { text: "Market flipped", emoji: "🔄", tone: "neg" }
    : { text: "Market reversal", emoji: "🔄", tone: "pos" };
}
```

- [ ] **Step 1.3: Dashboard hard refresh test**

Manuel: bot reload → dashboard Ctrl+F5 → exited tab'da near_resolve trade'ler için kâr/zararlı doğru etiket gör.

- [ ] **Step 1.4: Commit**

```bash
git add src/presentation/dashboard/static/js/fmt.js
git commit -m "ui(dashboard): exit reason label PnL-aware for near_resolve + market_flip"
```

---

## Task 2: Position.source Field Genel Coverage

**Files:**
- Modify: `src/orchestration/entry_processor.py:198` (mevcut)
- Search/Modify: `src/orchestration/startup.py`, `src/orchestration/lifecycle.py`, `src/orchestration/factory.py`, `src/domain/portfolio/snapshot.py` (Position constructor çağrıları)
- Test: `tests/regression/test_position_source_coverage.py` (yeni)

- [ ] **Step 2.1: Kapsama tarama (paralel ajan)**

Dispatch agent: "src/ altında `Position(...)` constructor çağrılan tüm satırları bul. Her birinde `source=...` parametresi geçiliyor mu? Rapor."

Beklenen output: lokasyonlar + her birinde source eksik mi tablosu.

- [ ] **Step 2.2: Regression test yaz (kapsama assertion)**

```python
# tests/regression/test_position_source_coverage.py
"""Tüm Position(...) constructor'larında source field set ediliyor mu?

AST tarama ile src/ altında Position(...) çağrılarını bul, source kwarg'ı var mı kontrol.
"""
import ast
from pathlib import Path

POSITION_CALLERS = [
    "src/orchestration/entry_processor.py",
    "src/orchestration/startup.py",
    "src/orchestration/lifecycle.py",
    # ...kapsama tarama sonucu eklenir
]

def _has_source_kwarg(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Name) or node.func.id != "Position":
        return False
    return any(kw.arg == "source" for kw in node.keywords)


def test_all_position_constructors_set_source():
    missing = []
    for path in POSITION_CALLERS:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Position":
                if not _has_source_kwarg(node):
                    missing.append(f"{path}:{node.lineno}")
    assert not missing, f"Position(...) source eksik: {missing}"
```

- [ ] **Step 2.3: Test çalıştır → FAIL bekleniyor**

Run: `pytest tests/regression/test_position_source_coverage.py -v`
Expected: FAIL (kapsamadaki bazı dosyalarda source eksik)

- [ ] **Step 2.4: Eksik constructor'lara source ekle**

Her FAIL eden satır için: `source=signal.source` veya `source="model"` veya `source="bookmaker"` (context'e göre).

- [ ] **Step 2.5: Test PASS doğrula**

Run: `pytest tests/regression/test_position_source_coverage.py -v`
Expected: PASS

- [ ] **Step 2.6: Full pytest**

Run: `python -m pytest -q`
Expected: 1894+ passed, 0 fail.

- [ ] **Step 2.7: Commit**

```bash
git add src/orchestration/ tests/regression/test_position_source_coverage.py
git commit -m "feat(position): source field coverage — regression test + missing constructors"
```

---

## Task 3: Lab Auto-Sync Genel Liste

**Files:**
- Modify: `lab_v2/start.py:_SYNC_FROM_MAIN`
- Test: `tests/integration/test_lab_sync.py` (yeni)

- [ ] **Step 3.1: Mevcut sync liste + tüm potansiyel shared data tara**

```bash
ls data/*.json data/basketball_cache/*.json | sort
```

Sınıflandır:
- **MODEL-LEVEL (sync edilmeli)**: calibration, ratings (Sackmann + nba_api + euroleague)
- **STATE-LEVEL (sync edilmemeli)**: positions, stock_queue, bot_status, blacklist, circuit_breaker, session_start
- **CACHE-LEVEL (sync edilmemeli, lab kendi cache'ini üretir)**: tennis_athlete_cache, mlb_rate_cache

- [ ] **Step 3.2: `_SYNC_FROM_MAIN` listesini genişlet**

```python
# lab_v2/start.py
_SYNC_FROM_MAIN: tuple[tuple[str, ...], ...] = (
    # (relative_path,) — main_repo/<path> → lab_root/<path>
    ("data/tennis_calibration.json",),
    ("data/tennis_ratings_surface.json",),
    ("data/tennis_ratings.json",),
    ("data/basketball_cache/nba_ratings.json",),
    ("data/basketball_cache/wnba_ratings.json",),
    ("data/basketball_cache/g_league_ratings.json",),
    ("data/basketball_cache/summer_league_ratings.json",),
    # Yeni rating dosyaları otomatik dahil: glob ile
)
_SYNC_GLOB = ("data/basketball_cache/*_ratings.json",)
```

- [ ] **Step 3.3: Sync fonksiyonu glob desteği ekle**

```python
def _sync_reference_data() -> None:
    log = logging.getLogger(__name__)
    main_data = MAIN_REPO
    lab_data = LAB_ROOT
    # 1. Sabit liste
    for (rel,) in _SYNC_FROM_MAIN:
        src = main_data / rel
        dst = lab_data / rel
        _sync_one(src, dst, log)
    # 2. Glob (yeni rating dosyaları otomatik)
    for pattern in _SYNC_GLOB:
        for src in main_data.glob(pattern):
            dst = lab_data / src.relative_to(main_data)
            _sync_one(src, dst, log)


def _sync_one(src: Path, dst: Path, log) -> None:
    if not src.exists():
        log.warning("[LAB] sync skip: %s (main yok)", src.name)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
        log.info("[LAB] synced: %s (%d bytes)", src.name, dst.stat().st_size)
```

- [ ] **Step 3.4: Test yaz**

```python
# tests/integration/test_lab_sync.py
def test_lab_sync_covers_all_rating_files(tmp_path):
    """Lab sync glob pattern yeni rating dosyalarını otomatik kapsar."""
    main = tmp_path / "main"
    lab = tmp_path / "lab"
    (main / "data" / "basketball_cache").mkdir(parents=True)
    (lab / "data" / "basketball_cache").mkdir(parents=True)
    # Yeni hayali lig rating dosyası
    new_rating = main / "data" / "basketball_cache" / "eurocup_ratings.json"
    new_rating.write_text('[{"team": "RM"}]')
    # Sync fonksiyonunu çağır
    # ... (lab_v2.start._sync_reference_data taklit)
    # Beklenen: lab/data/basketball_cache/eurocup_ratings.json oluştu
```

- [ ] **Step 3.5: Pytest + lab restart**

Run: `python -m pytest tests/integration/test_lab_sync.py -v`

- [ ] **Step 3.6: Commit**

```bash
git add lab_v2/start.py tests/integration/test_lab_sync.py
git commit -m "feat(lab): auto-sync ratings dosyalarını glob ile kapsa — yeni ligler otomatik"
```

---

## Task 4: Team Resolver Alias Coverage — Tüm Ligler

**Files:**
- Modify: `src/domain/matching/basketball_team_resolver.py` (NBA, WNBA, NCAAB, Euroleague)
- Test: `tests/regression/test_team_resolver_coverage.py` (yeni)
- Optional: `scripts/sync_team_aliases.py` (yeni — canlı kaynak'tan auto-update)

- [ ] **Step 4.1: Tüm liglerin alias listesi audit (paralel ajan)**

Dispatch agent: "Polymarket'in basket sayfasında (https://polymarket.com/sports/basketball/games) tüm aktif maçların slug pattern'lerini incele. Her lig için kullanılan kısaltma listesini çıkar (örn. NBA: lal, gsw, bos... WNBA: atl, chi, gsv... NCAAB: duke, unc, ...). Karşılaştır: bizim `_NBA_TEAMS`, `_WNBA_TEAMS`, `_NCAAB_TEAMS_FULL`, `_EUROLEAGUE_TEAMS` dict'lerinde eksik olanlar nelerdir?"

Beklenen output: tablo halinde eksik alias'lar.

- [ ] **Step 4.2: Regression test yaz — bilinen Polymarket slug'larına assertion**

```python
# tests/regression/test_team_resolver_coverage.py
from src.domain.matching.basketball_team_resolver import resolve_team_pair

# Polymarket'ten gerçek slug örnekleri (kapsama tarama sonucu)
KNOWN_NBA_SLUGS = [
    "nba-lal-gsw-2026-06-15",
    "nba-bos-mia-2026-06-20",
    "nba-nyk-sas-2026-06-08",
    # ...
]
KNOWN_WNBA_SLUGS = [
    "wnba-las-la-2026-06-02",  # Las Vegas vs LA Sparks
    "wnba-por-gsv-2026-06-02", # Portland vs Golden State Valkyries (2026 yeni)
    "wnba-chi-wsh-2026-06-02",
    "wnba-conn-atl-2026-06-02",
    # ...
]

def test_nba_slugs_resolve():
    for slug in KNOWN_NBA_SLUGS:
        r = resolve_team_pair(slug, league="nba")
        assert r.ok, f"NBA resolve fail: {slug} (home={r.home}, away={r.away})"


def test_wnba_slugs_resolve():
    for slug in KNOWN_WNBA_SLUGS:
        r = resolve_team_pair(slug, league="wnba")
        assert r.ok, f"WNBA resolve fail: {slug}"
```

- [ ] **Step 4.3: Test → FAIL bekleniyor (audit sonucu eksikler için)**

Run: `pytest tests/regression/test_team_resolver_coverage.py -v`

- [ ] **Step 4.4: Eksik alias'ları ekle (paralel ajan raporu temelinde)**

Her FAIL eden slug için: ilgili `_LIG_TEAMS` dict'ine alias ekle. Yeni ekspansiyon takımları (örn. WNBA 2027 yeni lig, NBA expansion) için yer açık tut.

- [ ] **Step 4.5: Auto-sync script (opsiyonel, future-proof)**

```python
# scripts/sync_team_aliases.py
"""nba_api / ESPN API'den canlı takım listesi çek + alias üret."""
# nba_api.stats.endpoints.commonteamyears veya benzeri
# Output: dict[str, str] (kısaltma → standart code)
```

Bu script periyodik çalıştırılır (cron veya manuel sezon başında). Yeni takım eklenince hardcoded liste otomatik güncellenir.

- [ ] **Step 4.6: Test PASS doğrula**

Run: `pytest tests/regression/test_team_resolver_coverage.py -v`
Expected: PASS

- [ ] **Step 4.7: Full pytest**

Run: `python -m pytest -q`
Expected: 1894+ passed, 0 fail.

- [ ] **Step 4.8: Commit**

```bash
git add src/domain/matching/basketball_team_resolver.py tests/regression/test_team_resolver_coverage.py
git commit -m "feat(resolver): tüm basket ligleri alias coverage + regression test"
```

---

## Final Self-Review

- [ ] **Spec coverage check:** SPEC-AUDIT-001 4 kategori → 4 Task ✓
- [ ] **Yan task atlama:** Her task'ta "kapsama tarama" adımı var (paralel ajan dispatch)
- [ ] **Future-proof:** Her task'ta yeni eklemelere otomatik adaptasyon (glob, regression test, auto-sync)
- [ ] **ARCH_GUARD:** Yeni dosyalar doğru katmanda (`tests/regression/`, `scripts/`), 400 satır altında, magic number yok
- [ ] **Dead code yok:** Eski hardcoded liste değiştirildi/genişletildi (eklenmedi)
- [ ] **Drift yok:** Regression test her commit'te kapsama doğrular

---

## Execution Order

1. Task 1 (UI etiket) — bağımsız, hızlı (~20dk)
2. Task 2 (Position.source) — bağımsız, paralel ajan + test (~40dk)
3. Task 3 (Lab auto-sync) — bağımsız (~20dk)
4. Task 4 (Team resolver) — paralel ajan + test + alias ekleme (~60dk)

**Toplam:** ~2-3 saat

## Verification Before Completion

- [ ] 1894+ pytest passed, 0 fail
- [ ] 4 regression test eklenmiş (Task 2 + Task 4)
- [ ] Bot reload sonrası dashboard'da yeni etiketler görünür (Task 1)
- [ ] Lab restart sonrası yeni rating dosyaları otomatik sync (Task 3)
- [ ] DECISIONS.md'ye "SPEC-AUDIT-001 done" notu eklenmiş
