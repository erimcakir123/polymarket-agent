# SPEC-009: Archive System — Retrospective Rule Analysis

> **Durum**: DRAFT
> **Tarih**: 2026-04-19
> **Katman**: infrastructure (archive_logger) + orchestration (exit_processor, score_enricher)
> **Scope**: append-only archive katmani + reboot/reload koruma + dokuman

---

## 1. Problem

Mevcut veri akisinda geriye donuk analiz icin eksikler var:

1. **Reboot active state'i sifirliyor** — `trade_history.jsonl`, `positions.json`
   vs. silinir. Onceki trade'lerin structured veri'si kaybolur.
2. **.bak dosyalari manuel ve sistematik degil** — kod uretmiyor, elle olusturulmus.
3. **Maci skor progression'i kaydedilmiyor** — sadece exit anindaki skor
   positions.json'da tutulur, o da silinir.
4. **Maci final result saklanmiyor** — biz cikip sonra macin nasil bittigini
   (kim kazandi, final skor) bilmiyoruz. "Dogru zamanda mi ciktik" sorusuna
   cevap verilemiyor.

**Sonuc**: Kurallarin (scale-out tier'lari, market_flip threshold'lari, near_resolve)
dogru calisip calismadigi retrospektif olarak degerlendirilemiyor.

---

## 2. Cozum

3 ayri append-only JSONL dosyasi `logs/archive/` altinda:

```
logs/archive/
  exits.jsonl          — her exit'in tam snapshot'i + o andaki skor
  score_events.jsonl   — mac sirasindaki her skor degisikligi
  match_results.jsonl  — mac bitince final result + winner
```

3 dosya `event_id` ile JOIN edilebilir:
- `SELECT exit FROM exits WHERE event_id = X` → exit anini bul
- `SELECT scores FROM score_events WHERE event_id = X ORDER BY timestamp` → mac
  icindeki skor progression'i
- `SELECT result FROM match_results WHERE event_id = X` → final

Analiz ornegi: "MLB 2-1 gerideyken ciktigimiz maclarin kaci geri donup kazandi?"

---

## 3. Mimari

### 3a. Yeni Dosya: `src/infrastructure/persistence/archive_logger.py`

Pure I/O wrapper — diger logger'larla ayni pattern (trade_logger, equity_history).

```python
from pydantic import BaseModel

class ArchiveExitRecord(BaseModel):
    # Trade kimligi
    slug: str
    condition_id: str
    event_id: str
    token_id: str
    sport_tag: str
    question: str

    # Entry (trade_history ile ayni field'lar)
    direction: str
    entry_price: float
    entry_timestamp: str
    size_usdc: float
    shares: float
    confidence: str
    anchor_probability: float
    entry_reason: str

    # Exit
    exit_price: float
    exit_pnl_usdc: float
    exit_reason: str
    exit_timestamp: str
    partial_exits: list[dict] = []

    # Exit anindaki skor (B seviye detay)
    score_at_exit: str = ""    # "2-1", "0-6 2-1" gibi — sport_tag'e gore
    period_at_exit: str = ""   # "5th inning top", "set 2 game 3" gibi
    elapsed_pct_at_exit: float = -1.0


class ArchiveScoreEvent(BaseModel):
    event_id: str
    slug: str
    sport_tag: str
    timestamp: str            # skor degisikligi zamani
    prev_score: str           # "1-1"
    new_score: str            # "2-1"
    period: str = ""
    # elapsed_pct hesaplanabilir ama skor event'te zorunlu degil


class ArchiveMatchResult(BaseModel):
    event_id: str
    slug: str
    sport_tag: str
    final_score: str          # "3-1"
    winner_home: bool | None  # True=home, False=away, None=draw
    completed_timestamp: str  # ESPN/OddsAPI final fetch zamani
    source: str = "espn"      # data kaynagi


class ArchiveLogger:
    """3 ayri JSONL'e append-only yazar. Append-only = thread-safe."""

    def __init__(self, archive_dir: str) -> None:
        self.dir = Path(archive_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def log_exit(self, record: ArchiveExitRecord) -> None:
        self._append("exits.jsonl", record)

    def log_score_event(self, event: ArchiveScoreEvent) -> None:
        self._append("score_events.jsonl", event)

    def log_match_result(self, result: ArchiveMatchResult) -> None:
        self._append("match_results.jsonl", result)

    def _append(self, filename: str, record: BaseModel) -> None:
        with open(self.dir / filename, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
```

ARCH_GUARD:
- Infrastructure katmani — I/O var, dogru yer
- Tek sorumluluk: arsiv yazma
- 4 public method (log_exit, log_score_event, log_match_result, + `__init__`)
- ~80 satir tahmini

### 3b. Call Site'lar

**Exit** — `src/orchestration/exit_processor.py`:

Exit isleminden SONRA, `trade_logger.log()` cagrisindan SONRA, archive'a da yaz.

```python
# exit_processor.py run_light() icinde, full/partial exit sonrasi:
archive_record = ArchiveExitRecord(
    # ... trade fields'lari doldur (mevcut trade_record ile ayni) ...
    score_at_exit=pos.match_score,
    period_at_exit=pos.match_period,
    elapsed_pct_at_exit=result.elapsed_pct,
)
self.archive_logger.log_exit(archive_record)
```

**Score change** — `src/orchestration/score_enricher.py`:

Her mac icin onceki skor memory'de tutulur. Skor degisirse archive'a yaz.

```python
# score_enricher.py _enrich_position() icinde:
new_score = score_info.get("score", "")
if new_score and new_score != prev_score_by_event.get(event_id, ""):
    archive_logger.log_score_event(ArchiveScoreEvent(
        event_id=event_id,
        slug=slug,
        sport_tag=sport_tag,
        timestamp=now_iso(),
        prev_score=prev_score_by_event.get(event_id, ""),
        new_score=new_score,
        period=period,
    ))
    prev_score_by_event[event_id] = new_score
```

**Match result** — `score_enricher.py`:

ESPN response'unda `status=completed` veya `match_ended=True` olunca:

```python
if score_info.get("match_ended") and event_id not in logged_results:
    archive_logger.log_match_result(ArchiveMatchResult(
        event_id=event_id,
        slug=slug,
        sport_tag=sport_tag,
        final_score=score_info.get("score", ""),
        winner_home=score_info.get("winner_home"),
        completed_timestamp=now_iso(),
    ))
    logged_results.add(event_id)
```

`logged_results` memory-only set — restart'ta bellek sifir. Duplicate
yazim riskine karsi startup'ta match_results.jsonl'i okuyup event_id set'i
doldurulur:

```python
# agent.py startup:
logged_results = set()
for line in open("logs/archive/match_results.jsonl"):
    logged_results.add(json.loads(line)["event_id"])
```

Bu yuzlerce satir bile olsa startup'ta birkac ms surer.

### 3c. DI Wiring — `src/orchestration/factory.py`

```python
archive_logger = ArchiveLogger("logs/archive")
# exit_processor ve score_enricher'a gecir
```

---

## 4. Reboot/Reload Davranisi

### Reload (kod guncelle, veri koru)
- Archive'a dokunulmaz (zaten append-only, aktif degil)
- Aktif data korunur (positions, trade_history vs.)
- Normal davranis, degisiklik yok

### Reboot (aktif data sifirla)
- Aktif data sifirlanir:
  - `logs/positions.json` → sifir
  - `logs/trade_history.jsonl` → bos
  - `logs/equity_history.jsonl` → bos
  - `logs/circuit_breaker_state.json` → sifir
  - `logs/stock_queue.json` → bos
- **Archive ASLA silinmez**:
  - `logs/archive/exits.jsonl` → korunur
  - `logs/archive/score_events.jsonl` → korunur
  - `logs/archive/match_results.jsonl` → korunur

CLAUDE.md'deki Restart Protokolu bu kuralla guncellenir:
> "**Archive korunur**: `logs/archive/` dizinine reboot'ta bile dokunulmaz.
> Sadece `logs/` kokunde olan aktif state dosyalari sifirlanir."

---

## 5. Trade Silme Protokolu Etkilesimi

CLAUDE.md'deki mevcut protokol:
- trade_history.jsonl'den satir sil
- positions.json guncelle
- equity_history.jsonl retroaktif duzelt
- circuit_breaker_state guncelle

**Archive'da ne olacak?**

Kural: **Archive dokunulmaz** — audit trail korunmali.

Silinen trade'in `exits.jsonl`'deki kaydi KALIR. Silme bilgisi active data'ya
yansir ama archive "hic olmamis gibi" degil — "olmus ama silinmis" olarak kalir.

CLAUDE.md guncellenir:
> "Archive dokunulmaz. Silinen trade'in `logs/archive/exits.jsonl`'deki
> kaydi audit trail olarak korunur. Analiz yapinca 'bu trade silindi ama
> aslinda X'di' gorulebilir."

Kullanici isterse ileride:
- Archive entry'ye `deleted_at: timestamp` ekleyebiliriz (yeni append, eski
  kayit da kalir)

---

## 6. Etkilenen Dosyalar

| Dosya | Islem | Detay |
|---|---|---|
| `src/infrastructure/persistence/archive_logger.py` | **YENI** | 3 model + ArchiveLogger class |
| `src/orchestration/exit_processor.py` | GUNCELLE | exit sonrasi archive_logger.log_exit() |
| `src/orchestration/score_enricher.py` | GUNCELLE | skor degisikligi + mac bitisinde log |
| `src/orchestration/factory.py` | GUNCELLE | ArchiveLogger DI |
| `src/orchestration/agent.py` | GUNCELLE | AgentDeps'e archive_logger eklenir |
| `tests/unit/infrastructure/persistence/test_archive_logger.py` | **YENI** | 3 log tipi + append-only |
| `tests/unit/orchestration/test_exit_processor.py` | GUNCELLE | archive_logger assert'leri |
| `tests/unit/orchestration/test_score_enricher.py` | GUNCELLE | archive_logger assert'leri |
| `CLAUDE.md` | GUNCELLE | Restart + Trade Silme protokolleri archive kurali |
| `TDD.md` | GUNCELLE | §5.8 reboot archive preservation, §5.x archive system |
| `PRD.md` | GUNCELLE | F9 "Trade Archive for Rule Analysis" |
| `logs/*.bak*`, `logs/*backup*` | **SILINDI** | Temiz sayfa (manuel, SPEC onayinda yapildi) |

---

## 7. Sinir Durumlari

| Durum | Davranis |
|---|---|
| Archive dizini yok | ArchiveLogger.__init__() mkdir(parents=True, exist_ok=True) |
| Disk dolu | IOError firlar, orchestration log'lar, cycle devam eder (exit'ler etkilenmez cunku archive secondary) |
| Skor ayni kalirsa (1-0 → 1-0) | log_score_event tetiklenmez (prev_score check) |
| Skor icin ESPN dondurmuyorsa | skor event'i yazilmaz, exit ve result yine yazilir |
| Mac final ESPN'de yok (no score data) | match_result yazilmaz, sadece exit + score_events kalir |
| Restart sonrasi ayni mac icin 2. defa match_result | Startup'ta match_results.jsonl okunup logged_results set'i doldurulur — duplicate yazilmaz |
| Trade silme sirasinda archive | Dokunulmaz, audit trail korunur |

---

## 8. Test Senaryolari

### Archive Logger (unit)

- `test_log_exit_writes_jsonl_line`: exits.jsonl'e tek satir yazar
- `test_log_score_event_writes_jsonl_line`: score_events.jsonl'e yazar
- `test_log_match_result_writes_jsonl_line`: match_results.jsonl'e yazar
- `test_archive_directory_created_on_init`: dizin yoksa olusturur
- `test_multiple_exits_append_only`: N cagri → N satir (overwrite degil)
- `test_concurrent_writes_safe`: Thread-safe (Python GIL altinda append)

### Exit Processor (integration)

- `test_exit_triggers_archive_log`: full exit → archive'da exit kaydi
- `test_partial_exit_triggers_archive_log`: scale-out → archive'da exit kaydi
- `test_exit_archive_includes_score_snapshot`: score_at_exit, period doldurulur

### Score Enricher (integration)

- `test_score_change_triggers_archive_log`: skor degisince score_event yazilir
- `test_same_score_no_archive_log`: skor degismezse tetiklenmez
- `test_match_completion_triggers_result_log`: mac bitince match_result yazilir

---

## 9. Tahmini Disk Kullanimi

| Kaynak | Gun basi satir | Satir boyutu | Gun basi MB |
|---|---|---|---|
| exits.jsonl | ~20-30 trade | ~800 byte | ~0.02 MB |
| score_events.jsonl | ~100-200 skor degisikligi (10-15 maç × 10 goal avg) | ~200 byte | ~0.03 MB |
| match_results.jsonl | ~10-15 mac | ~300 byte | ~0.004 MB |

**Toplam ~0.06 MB/gun = ~22 MB/yil**. Sinirsiz append kabul edilebilir.

---

## 10. Rollback Plani

Rollback basit (archive append-only, zarar vermez):

1. `archive_logger.py` sil
2. exit_processor + score_enricher'dan archive cagrilarini kaldir
3. factory.py DI'dan cikart
4. `logs/archive/` dizinini manuel olarak birakabilirsin (ya da sil)

Bot restart sonrasi normal calisir, archive eksik olur.

---

## 11. Degisiklik Ozeti (Teknik Olmayan)

1. **Yeni arsiv sistemi** — Her exit, skor degisikligi ve mac sonucu ayri bir
   dosyaya kaydedilir. Hiçbir zaman silinmez.

2. **Reboot arsive dokunmaz** — Botu sifirlasak bile gecmis analizler
   icin veri duruyor.

3. **Trade silme koruyor** — "Sil" dediginizde aktif dosyalardan silinir
   ama arsivden silinmez (audit trail).

4. **Analiz icin veri** — Sonradan "su maclarda dogru ciktik mi" sorusu
   gercek verilerle cevaplanir.
