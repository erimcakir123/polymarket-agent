# Position Match State Refresh + LIVE Rozet Düzeltmesi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Açık pozisyonların `match_start_iso` ve `match_live` değerlerini her cycle'da ESPN/Polymarket ile güncelleyerek (1) exit kararlarının doğru saatle çalışmasını ve (2) dashboard LIVE rozetinin doğru anda görünmesini sağla.

**Architecture:** Mevcut `TennisStartEnricher` orchestration sınıfını genişletiyoruz — `refresh_positions(positions)` yeni public metoduyla canlı pozisyonların `match_start_iso`'sunu in-place günceller. `Position.match_live` entry'de Polymarket `event.live` bayrağından doldurulur. Cycle hook `agent.py`'da exit_processor öncesi çağrılır. Dashboard JS `_countdownPill` mevcut `match_live` argümanını gerçekten kullanır.

**Tech Stack:** Python 3.12, pytest, mevcut `ESPNClient.fetch_tennis_matches_today`, mevcut `TennisStartEnricher`.

---

## Mimari Doğrulama (ARCH_GUARD ✓)

8 anti-pattern tarandı:
- ✓ DRY — `TennisStartEnricher`'in mevcut `_is_tennis`, `_match_event`, `_norm`, `_slug_surnames`, `_fetch_dates` helper'ları yeniden kullanılır
- ✓ <400 satır — enricher şu an ~202 satır, +~60 satır → ~260 (limit altında)
- ✓ Domain I/O yok — Position model (domain) dokunulmuyor, sadece field set; enricher orchestration'da kalır
- ✓ Katman düzeni — Orchestration (enricher) → Infrastructure (ESPN client). Aynı
- ✓ Magic number yok — TTL config'den, tüm sabitler module-level named
- ✓ utils/helpers/misc yok
- ✓ Sessiz hata yok — refresh fail → log warning + pozisyon dokunulmaz
- ✓ P(YES) anchor — dokunulmuyor

**Drift kontrolü:**
- `Position.match_live` mevcut field, `False` default, **şu an hiçbir yerde `True` set edilmiyor** — ölü default. Bu plan dolduruyor.
- `_countdownPill(matchStartIso, matchLive)` JS argümanı **kullanılmıyor** (yarım iz). Bu plan kullanıyor.
- `TennisStartEnricher` MarketData için. Aynı sınıf Position için yeni metod alır — yeni dosya/yeni helper yok, DRY.

**Dead code temizliği:**
- Plan tamamlandığında `_countdownPill`'in `matchLive` parametresi gerçek kullanım kazanır → ölü argüman kaybolur.
- `Position.match_live` default'u canlanır → ölü field kaybolur.

---

## Task 1: Entry'de Position.match_live = market.event_live set

**Files:**
- Modify: `src/orchestration/entry_processor.py` — `Position(...)` constructor çağrıları
- Modify: `tests/unit/orchestration/test_entry_processor.py` veya yeni test

### Step 1 — failing test

Add to `tests/unit/orchestration/test_entry_processor.py` (uygun bir yer bul, mevcut "phantom-restored" testler arasında):

```python
def test_position_inherits_event_live_from_market():
    """Entry'de market.event_live True ise Position.match_live True olmalı."""
    from src.models.market import MarketData
    from src.models.position import Position
    from src.models.signal import EntrySignal, EntryReason, Direction, Confidence

    market = MarketData(
        condition_id="cid-live", question="X vs Y", slug="atp-x-y-2026-05-23",
        yes_token_id="t1", no_token_id="t2", yes_price=0.5, no_price=0.5,
        liquidity=1000.0, volume_24h=100.0, tags=[],
        end_date_iso="2026-05-30T00:00:00Z",
        match_start_iso="2026-05-23T13:00:00Z",
        sport_tag="tennis",
        event_live=True,  # ← canlı maç
    )
    # Test: market.event_live True ise position oluşturma path'inde match_live True ile geçmeli.
    # entry_processor'in Position(...) çağrısı match_live=market.event_live olmalı.
    # Bu testte direkt mapping doğrula:
    pos = Position(
        condition_id=market.condition_id, token_id="t1",
        direction="BUY_YES", entry_price=0.5, size_usdc=50.0, shares=100.0,
        current_price=0.5, anchor_probability=0.5,
        match_start_iso=market.match_start_iso, sport_tag=market.sport_tag,
        match_live=market.event_live,
    )
    assert pos.match_live is True
```

Run:
```bash
pytest tests/unit/orchestration/test_entry_processor.py::test_position_inherits_event_live_from_market -v
```
Expected: PASS (Position model `match_live` zaten kabul ediyor, sadece doğrulama).

**Not:** Bu test pür model testi. Asıl entry_processor.py'ın `match_live=market.event_live` set ettiğini doğrulayan integration test ek olarak yazılacak.

### Step 2 — entry_processor'da set

[entry_processor.py:178-200](src/orchestration/entry_processor.py#L178-L200) civarında `Position(...)` constructor'lar var (2-3 yer; phantom-restored ve normal). Hepsine `match_live=market.event_live` ekle.

Grep ile bul:
```bash
grep -n "Position(" src/orchestration/entry_processor.py
```

Her `Position(...)` çağrısında `match_start_iso=market.match_start_iso` satırı var; hemen altına ekle:
```python
            match_start_iso=market.match_start_iso,
            match_live=market.event_live,
```

### Step 3 — integration test

Add to `tests/unit/orchestration/test_entry_processor.py`:

```python
def test_entry_processor_propagates_event_live_to_position(monkeypatch):
    """entry_processor.py Position oluştururken market.event_live'i match_live'a kopyalamalı."""
    # _build_position_from_signal veya benzer dahili çağrı pattern'i:
    # Mevcut entry_processor testlerinde Position'ı pmportfolio.add_position ile
    # gözleyen mock var; aynı pattern'i kullan.
    # Mevcut testleri okuyup pattern'i kopyala.
    pass  # implementasyon mevcut testlere göre yazılır
```

Test'i mevcut entry_processor test stilini takip ederek doldur (deps + bir signal + bir live market → assert added position.match_live==True).

### Step 4 — testleri çalıştır

```bash
pytest tests/unit/orchestration/test_entry_processor.py -v
```
Expected: tüm yeni testler PASS.

### Step 5 — full suite

```bash
pytest -q
```
Expected: yeşil. Mevcut testlerde `match_live=False` assertion'u yoksa regresyon yok.

### Step 6 — commit

```bash
git add src/orchestration/entry_processor.py tests/unit/orchestration/test_entry_processor.py
git commit -m "feat(position): match_live'i market.event_live'den propagate et"
```

---

## Task 2: TennisStartEnricher.refresh_positions(positions)

**Files:**
- Modify: `src/orchestration/tennis_start_enricher.py` — yeni public metod
- Modify: `tests/unit/orchestration/test_tennis_start_enricher.py` — yeni testler

### Step 1 — failing testler

Add to `tests/unit/orchestration/test_tennis_start_enricher.py`:

```python
from src.models.position import Position


def _pos(slug: str, start: str = "", sport_tag: str = "tennis") -> Position:
    return Position(
        condition_id=f"cid-{slug}", token_id="t1",
        direction="BUY_YES", entry_price=0.5, size_usdc=50.0, shares=100.0,
        current_price=0.5, anchor_probability=0.5,
        slug=slug, match_start_iso=start, sport_tag=sport_tag,
        match_live=False,
    )


def test_refresh_positions_updates_match_start_when_espn_match_found():
    """ESPN'de eşleşme bulunan tennis pozisyonun match_start_iso'su güncellenir."""
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = [
        _espn("Alex de Minaur", "Tommy Paul", "2026-05-25T04:00:00Z"),
    ]
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    pos = _pos("atp-minaur-paul-2026-05-25", start="2026-05-24T09:00:00Z")
    enricher.refresh_positions([pos])
    assert pos.match_start_iso == "2026-05-25T04:00:00Z"


def test_refresh_positions_skips_non_tennis():
    """Non-tennis pozisyon dokunulmaz."""
    espn_client = MagicMock()
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    pos = _pos("mlb-x-y", sport_tag="baseball", start="2026-05-23T22:00:00Z")
    enricher.refresh_positions([pos])
    espn_client.fetch_tennis_matches_today.assert_not_called()
    assert pos.match_start_iso == "2026-05-23T22:00:00Z"


def test_refresh_positions_no_tennis_skips_espn():
    """Hiç tennis pozisyon yoksa ESPN'e çağrı yok."""
    espn_client = MagicMock()
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    enricher.refresh_positions([])
    espn_client.fetch_tennis_matches_today.assert_not_called()


def test_refresh_positions_same_day_guard():
    """ESPN eşleşmesi farklı bir günde ise override iptal (false-positive koruması)."""
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = [
        _espn("Alex de Minaur", "Tommy Paul", "2026-02-24T12:00:00Z"),  # 3 ay önce
    ]
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    pos = _pos("atp-minaur-paul-2026-05-25", start="2026-05-25T04:00:00Z")
    enricher.refresh_positions([pos])
    # Tarih uyumsuz → override yok
    assert pos.match_start_iso == "2026-05-25T04:00:00Z"


def test_refresh_positions_no_match_keeps_existing():
    """ESPN bulamazsa mevcut saat korunur (no-op)."""
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = []
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    pos = _pos("atp-x-y-2026-05-23", start="2026-05-23T13:00:00Z")
    enricher.refresh_positions([pos])
    assert pos.match_start_iso == "2026-05-23T13:00:00Z"
```

Run:
```bash
pytest tests/unit/orchestration/test_tennis_start_enricher.py -k refresh -v
```
Expected: 5 test FAIL (refresh_positions yok).

### Step 2 — implement

`src/orchestration/tennis_start_enricher.py`, `TennisStartEnricher` sınıfının altına ekle (mevcut `enrich` metodunun yanına):

```python
    def refresh_positions(self, positions: list[Position]) -> None:
        """Açık tennis pozisyonlarının match_start_iso'sunu ESPN ile in-place günceller.

        Akış:
          1. positions içinde tennis var mı? Yoksa NO-OP, ESPN'e dokunma.
          2. Her tennis pos'un match_start_iso'sundan YYYYMMDD topla → unique dates.
          3. ESPN'i bu günler için fetch (cached).
          4. Slug-surname eşleştirmesi ile her tennis pos'un match_start_iso'sunu
             güncelle. Same-day guard, no-match-keep, ESPN-fail-keep mantığı `enrich`
             ile birebir aynı (DRY: aynı helper'lar).
          5. Non-tennis dokunulmaz.

        Position objesi pydantic v2; `pos.match_start_iso = ...` doğrudan atama
        BaseModel.__init__ validate'i atlatır ama tutar değiştirir — istenen davranış
        bu (state mutation, yeniden inşa değil).
        """
        tennis_positions = [p for p in positions if _is_position_tennis(p)]
        if not tennis_positions:
            return

        leagues_raw = get_sport_rule("tennis", "espn_leagues", default=_VALID_LEAGUES)
        leagues = tuple(leagues_raw) if leagues_raw else _VALID_LEAGUES

        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        dates: set[str] = {today_str}
        for tp in tennis_positions:
            d = _iso_to_yyyymmdd(tp.match_start_iso)
            if d:
                dates.add(d)
        events_by_league = self._fetch_dates(leagues, tuple(sorted(dates)))

        for p in tennis_positions:
            target_leagues = self._leagues_for_market_like(p.slug, leagues)
            event = self._find_matching_event_by_slug(
                p.slug, target_leagues, events_by_league,
            )
            if event is None or not event.commence_time:
                continue
            if not _same_day(p.match_start_iso, event.commence_time):
                continue
            p.match_start_iso = event.commence_time
```

Yardımcı: `_is_tennis` MarketData için. Position için aynı mantığın helper'ı:

Module-level (mevcut `_is_tennis`'in altına):
```python
def _is_position_tennis(p: Position) -> bool:
    """sport_tag tennis veya slug atp-/wta- ile başlar mı?"""
    tag = (p.sport_tag or "").lower()
    if tag.startswith("tennis"):
        return True
    slug = (p.slug or "").lower()
    return slug.startswith("atp-") or slug.startswith("wta-")
```

Mevcut `_leagues_for_market` Position için de çalışacak şekilde sadeleştir:

Mevcut metod:
```python
def _leagues_for_market(self, m: MarketData, all_leagues: tuple[str, ...]) -> tuple[str, ...]:
    slug_league = _league_for_slug(m.slug)
    if slug_league is not None and slug_league in all_leagues:
        return (slug_league,)
    return all_leagues
```

Refactor: slug parametre olarak alsın (MarketData/Position bağımsız):
```python
def _leagues_for_market_like(self, slug: str, all_leagues: tuple[str, ...]) -> tuple[str, ...]:
    """Slug prefix'i atp-/wta- ise sadece o league. Aksi halde hepsi."""
    slug_league = _league_for_slug(slug)
    if slug_league is not None and slug_league in all_leagues:
        return (slug_league,)
    return all_leagues
```

Eski `_leagues_for_market` çağrılarını da `_leagues_for_market_like(m.slug, ...)`'a uyarla (mevcut `enrich` içinde).

`_find_matching_event` benzer şekilde slug parametre alsın:
```python
def _find_matching_event_by_slug(
    self,
    slug: str,
    target_leagues: tuple[str, ...],
    events_by_league: dict[str, list[ESPNMatchScore]],
) -> ESPNMatchScore | None:
    for lg in target_leagues:
        events = events_by_league.get(lg, [])
        ev = _match_event(slug, events)
        if ev is not None:
            return ev
    return None
```

Mevcut `_find_matching_event(m, ...)` artık `_find_matching_event_by_slug(m.slug, ...)` çağırsın veya kaldır (drift önlemek için). En temiz: eski metod sil, yeniyle değiştir, `enrich` içinde de kullan.

### Step 3 — testleri çalıştır

```bash
pytest tests/unit/orchestration/test_tennis_start_enricher.py -v
```
Expected: tüm testler (mevcut + 5 yeni) PASS.

### Step 4 — full suite

```bash
pytest -q
```
Expected: yeşil.

### Step 5 — commit

```bash
git add src/orchestration/tennis_start_enricher.py tests/unit/orchestration/test_tennis_start_enricher.py
git commit -m "feat(tennis): refresh_positions — açık pozisyonların match_start'ı ESPN ile günceller"
```

---

## Task 3: Agent cycle'a refresh_positions hook'u

**Files:**
- Modify: `src/orchestration/agent.py` veya `src/orchestration/exit_processor.py` — refresh çağrısı

### Step 1 — Mevcut cycle akışını keşfet

```bash
grep -nE "tennis_start_enricher|exit_processor|portfolio.positions" src/orchestration/agent.py
```

`AgentDeps` içinde `tennis_start_enricher` zaten inject ediliyor mu? Eğer factory'de inject edilmemişse:
- `src/orchestration/factory.py`'da `Agent(deps=AgentDeps(..., tennis_start_enricher=tennis_enricher))` çağrısı kontrol et
- Eksikse ekle

### Step 2 — failing test

Add to `tests/unit/orchestration/test_agent_heavy_stages.py` veya yeni test dosyası:

```python
def test_agent_cycle_calls_tennis_refresh_positions_when_enricher_provided():
    """Cycle her çalıştığında enricher.refresh_positions çağrılmalı (açık tennis pozisyonları varsa veya yoksa enricher kendisi karar verir)."""
    from unittest.mock import MagicMock
    from src.orchestration.agent import Agent
    # Mevcut test'lerden Agent + deps fixture'ını kopyala.
    # tennis_start_enricher = MagicMock() inject et.
    # bir cycle çalıştır (light veya heavy)
    # enricher.refresh_positions.assert_called_once()
    pass  # mevcut test pattern'ine göre doldur
```

### Step 3 — implement

`src/orchestration/agent.py` içinde `_run_light_cycle` veya `_run_heavy_cycle` (hangisi exit_processor'i çağırıyorsa) içine, exit_processor.run() çağrısının HEMEN ÖNCESİNE ekle:

```python
if self.deps.tennis_start_enricher is not None:
    positions = list(self.deps.state.portfolio.positions.values())
    self.deps.tennis_start_enricher.refresh_positions(positions)
```

**Not:** Cache TTL zaten 5 dk; her cycle ESPN'i ezmez. Tennis pozisyon yoksa enricher kendisi NO-OP.

### Step 4 — testleri çalıştır

```bash
pytest tests/unit/orchestration/test_agent_heavy_stages.py -v
pytest -q
```
Expected: yeşil.

### Step 5 — commit

```bash
git add src/orchestration/agent.py tests/unit/orchestration/
git commit -m "feat(agent): cycle'da tennis pozisyonlarını ESPN ile refresh et"
```

---

## Task 4: Dashboard JS LIVE rozeti — match_live argümanını kullan

**Files:**
- Modify: `src/presentation/dashboard/static/js/feed.js:109-122`

### Step 1 — Mevcut kodu oku

```bash
sed -n '109,122p' src/presentation/dashboard/static/js/feed.js
```

Mevcut:
```javascript
_countdownPill(matchStartIso, matchLive) {
  if (!matchStartIso) return "";
  const start = new Date(matchStartIso).getTime();
  if (isNaN(start)) return "";
  const diff = start - Date.now();
  if (diff <= 0) {
    return `<span class="feed-countdown live">LIVE</span>`;
  }
  const mins = Math.floor(diff / MS_PER_MIN);
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  const label = hours > 0 ? `${hours}h ${remMins}m` : `${mins}m`;
  return `<span class="feed-countdown">${label}</span>`;
}
```

### Step 2 — düzelt (SPEC kuralına göre)

[2026-04-15-dashboard-cycle-stages-and-card-redesign-design.md:114-121](docs/superpowers/specs/2026-04-15-dashboard-cycle-stages-and-card-redesign-design.md#L114-L121) — SPEC:
```
delta > 3600s  → "Xh Ym"
0 < delta ≤ 3600s → "Xm"
delta ≤ 0 AND matchLive → "LIVE"
delta ≤ 0 AND NOT matchLive → pill gizlenir
```

Yeni kod:
```javascript
_countdownPill(matchStartIso, matchLive) {
  if (!matchStartIso) return "";
  const start = new Date(matchStartIso).getTime();
  if (isNaN(start)) return "";
  const diff = start - Date.now();
  if (diff <= 0) {
    if (matchLive) {
      return `<span class="feed-countdown live">LIVE</span>`;
    }
    // Saat geçti ama Polymarket henüz live demedi — rozet gizlenir (maç gecikti).
    return "";
  }
  const mins = Math.floor(diff / MS_PER_MIN);
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  const label = hours > 0 ? `${hours}h ${remMins}m` : `${mins}m`;
  return `<span class="feed-countdown">${label}</span>`;
}
```

### Step 3 — manuel doğrulama

Dashboard reload sonrası `_activeCard`'da `p.match_live` boolean olarak geliyor mu kontrol et. Readers.py veya routes.py'da pozisyon serialize edilirken `match_live` field'ı response'a dahil mi?

```bash
grep -nE "match_live" src/presentation/dashboard/readers.py src/presentation/dashboard/routes.py
```

Eğer eksikse readers.py'da `_position_to_dict` benzeri serializer'a `"match_live": pos.match_live` ekle.

### Step 4 — commit

```bash
git add src/presentation/dashboard/static/js/feed.js src/presentation/dashboard/readers.py
git commit -m "fix(dashboard): LIVE rozeti match_live'a göre gösterilir (SPEC uyumu)"
```

---

## Task 5: DECISIONS.md log + doğrulama

**Files:**
- Modify: `DECISIONS.md`

### Step 1 — §B'ye yeni entry

DECISIONS.md §B en üste (newest at top kuralı):

```markdown
### 2026-05-23 — Position match_start refresh + LIVE rozet düzeltmesi

**Karar:** Açık tennis pozisyonların `match_start_iso`'su her cycle'da `TennisStartEnricher.refresh_positions()` ile ESPN'den güncellenir. `Position.match_live` entry'de `market.event_live`'den doldurulur. Dashboard `_countdownPill` JS'i artık `match_live` argümanını gerçekten kullanır.

**Neden:**
- Önceki ESPN entegrasyonu (2026-05-22/23) yalnızca scanner'a inject edilmişti; entry sonrası `Position.match_start_iso` Polymarket startTime'ında donuyordu → exit kararları yanlış saatle çalışabiliyordu.
- `Position.match_live` field'ı vardı ama hiçbir yerde set edilmiyordu (ölü default). Dashboard JS `match_live` argümanı kullanılmıyordu (yarım iz). Bu plan ikisini de canlandırır.

**Etki:**
- `src/orchestration/tennis_start_enricher.py` — `refresh_positions()` + helper refactor (DRY)
- `src/orchestration/entry_processor.py` — Position(...) çağrılarında `match_live=market.event_live`
- `src/orchestration/agent.py` — cycle hook
- `src/presentation/dashboard/static/js/feed.js` — `_countdownPill` SPEC uyumu
- `src/presentation/dashboard/readers.py` — `match_live` field'ı response'a (gerekiyorsa)
```

### Step 2 — full canlı doğrulama

```bash
pytest -q
python scripts/reboot.py reload
```
Sonra dashboard'da:
- Yarın başlayacak maç → countdown gösterir (Xh Ym)
- Saat geçmiş ama henüz live olmayan maç → rozet boş
- ESPN'de tarih düzeltmesi olan maç → açık pozisyon kartında doğru kalan süre

### Step 3 — commit

```bash
git add DECISIONS.md
git commit -m "docs(DECISIONS): position refresh + LIVE rozet kararı eklendi"
```

---

## Sonuç Kontrol Listesi

- [ ] `pytest -q` tüm testler yeşil
- [ ] `Position.match_live` artık entry'de doluyor (test ile kanıtlı)
- [ ] `TennisStartEnricher.refresh_positions` çalışıyor (5 unit test)
- [ ] Cycle'da refresh_positions çağrılıyor (integration test)
- [ ] Dashboard `_countdownPill` SPEC uyumlu (delta + matchLive ikili kontrol)
- [ ] `Position.match_live` ve `_countdownPill match_live` ölü kod değil — gerçek kullanım
- [ ] DECISIONS.md §B'ye log eklendi
- [ ] `tennis_start_enricher.py` < 400 satır (mevcut 202, +~60 = ~260)
- [ ] `_leagues_for_market` ve `_find_matching_event` refactor: tek slug-bazlı versiyon, eski drift yok
