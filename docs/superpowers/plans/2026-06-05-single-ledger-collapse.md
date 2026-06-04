# Tek-Defter Sadeleştirmesi (audit/session çift-yazım kaldırma) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `trade_events.jsonl` ve `equity_history.jsonl` için `audit/` + `session/` çift kopyasını **tek dosyaya** (`audit/`) indir; divergence sınıfı hataları kökten yok et.

**Architecture:** Bot tek bir audit dosyasına append eder (mirror yok). Dashboard tek audit dosyasını okur. Reboot dosyayı `*.archive.<ts>.jsonl`'e taşır (copy+delete = move, zaten var) → canlı dosya boş → dashboard 0. Reload dokunmaz → dashboard devam eder. İki kopya olmadığı için ayrışma (audit=4 vs session=113) imkânsız.

**Tech Stack:** Python 3.12, pytest, stdlib JSON/JSONL.

**Neden (SPEC-Z8/Z17 bağlamı):** "Gizemli scheduler" yoktu — forensic log 358 kaydın 352'si pytest, 6'sı gerçek reboot. Geçmiş audit kaybı (a) eski atomic-rewrite bug'ı (Z17 kaldırdı) + (b) çift kopyanın ayrışması + (c) tek-kullanımlık migration script'lerinin `write_text` ezmesi. Reboot=tam-wipe kararı (2026-05-23) audit/session ayrımını anlamsız kıldı → tek dosya doğru model.

---

## File Structure

| Dosya | Sorumluluk | Değişiklik |
|---|---|---|
| `src/infrastructure/persistence/trade_event_log.py` | Append-only trade event yazıcı | `mirror_path` kaldır |
| `src/infrastructure/persistence/equity_history.py` | Append-only equity snapshot yazıcı | `mirror_path` kaldır |
| `src/orchestration/_factory_loggers.py` | Logger fabrikaları | `mirror_path=` argümanlarını kaldır |
| `src/presentation/dashboard/readers.py` | Dashboard dosya okuyucuları | 3 fonksiyon tek audit dosyası okusun |
| `scripts/reboot.py` | reload/reboot kontrolü | Davranış zaten doğru — sadece doğrulama + ölü session referans temizliği |
| `tests/...` | Test güncellemeleri | Çift-yazım/çift-okuma assertion'larını tek-dosyaya çevir |
| `DECISIONS.md` | Karar kaydı | SPEC-Z18 girişi |

**Kapsam dışı:** `ArchiveLogger` (score_events/match_results) çift-yazımı — ayrı pattern, bu planda dokunulmaz.

---

### Task 1: TradeEventLog tek-dosya

**Files:**
- Modify: `src/infrastructure/persistence/trade_event_log.py:36-54`
- Test: `tests/unit/infrastructure/persistence/test_trade_event_log.py`

- [ ] **Step 1: Failing test yaz** — mirror artık yok, tek dosya append edilmeli.

```python
def test_trade_event_log_single_file_no_mirror(tmp_path):
    from src.infrastructure.persistence.trade_event_log import TradeEventLog
    p = tmp_path / "audit" / "trade_events.jsonl"
    log = TradeEventLog(str(p))                      # mirror_path YOK
    log.append_final(condition_id="c1", slug="s", question="q",
                     sport_tag="tennis", source="model", exit_price=0.5,
                     exit_reason="partial_sl", exit_pnl_usdc=-1.0,
                     exit_timestamp="2026-06-05T00:00:00+00:00")
    assert p.exists()
    assert len(p.read_text(encoding="utf-8").strip().splitlines()) == 1
    # session/ aynası OLUŞMAMALI
    assert not (tmp_path / "session" / "trade_events.jsonl").exists()
```

- [ ] **Step 2: Testi çalıştır, FAIL gör**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_event_log.py::test_trade_event_log_single_file_no_mirror -v`
Expected: PASS olabilir (constructor mirror_path opsiyonel) — bu durumda asıl hedef: `mirror` parametresini imzadan KALDIRMAK. Mirror kullanan eski testi (varsa) FAIL'a çevir: `TradeEventLog(path, mirror_path=...)` → TypeError.

- [ ] **Step 3: Implement — mirror tamamen kaldır**

`__init__` ve `_write` yeni hali:

```python
    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False) + "\n"
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
        except OSError as e:
            logger.error("TradeEventLog write failed: %s", e)
```

Docstring'den "mirror" cümlelerini sil; sınıf docstring'ine not: "Tek dosya — session aynası SPEC-Z18'de kaldırıldı (audit=session ayrımı reboot=tam-wipe ile anlamsız)."

- [ ] **Step 4: Testi çalıştır, PASS gör**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_event_log.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/persistence/trade_event_log.py tests/unit/infrastructure/persistence/test_trade_event_log.py
git commit -m "refactor(infra): SPEC-Z18 TradeEventLog tek-dosya — session aynasi kaldirildi"
```

---

### Task 2: EquityHistoryLogger tek-dosya

**Files:**
- Modify: `src/infrastructure/persistence/equity_history.py:29-49`
- Test: `tests/unit/infrastructure/persistence/test_equity_history.py`

- [ ] **Step 1: Failing test yaz**

```python
def test_equity_history_single_file_no_mirror(tmp_path):
    from src.infrastructure.persistence.equity_history import EquityHistoryLogger, EquitySnapshot
    p = tmp_path / "audit" / "equity_history.jsonl"
    log = EquityHistoryLogger(str(p))                # mirror_path YOK
    log.log(EquitySnapshot(timestamp="2026-06-05T00:00:00+00:00", bankroll=100.0,
                           realized_pnl=0.0, unrealized_pnl=0.0, invested=0.0,
                           open_positions=0))
    assert p.exists()
    assert not (tmp_path / "session" / "equity_history.jsonl").exists()
```

- [ ] **Step 2: Testi çalıştır, FAIL gör** (mirror_path imzadan kaldırılınca eski mirror testleri TypeError)

Run: `pytest tests/unit/infrastructure/persistence/test_equity_history.py -v`

- [ ] **Step 3: Implement — mirror kaldır**

```python
    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, snapshot: EquitySnapshot) -> None:
        line = snapshot.model_dump_json() + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
```

Docstring "mirror_path verilirse..." satırını sil.

- [ ] **Step 4: Testi çalıştır, PASS gör**

Run: `pytest tests/unit/infrastructure/persistence/test_equity_history.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/persistence/equity_history.py tests/unit/infrastructure/persistence/test_equity_history.py
git commit -m "refactor(infra): SPEC-Z18 EquityHistoryLogger tek-dosya"
```

---

### Task 3: Logger fabrikaları — mirror argümanı kaldır

**Files:**
- Modify: `src/orchestration/_factory_loggers.py:20-32`

- [ ] **Step 1: Implement (bu dosya fabrika — testi factory smoke testi kapsar)**

```python
def build_trade_event_log() -> TradeEventLog:
    """SPEC-Z18: tek dosya — tek truth kaynağı (session aynası kaldırıldı)."""
    return TradeEventLog(f"{_AUDIT}/trade_events.jsonl")


def build_equity_logger() -> EquityHistoryLogger:
    return EquityHistoryLogger(f"{_AUDIT}/equity_history.jsonl")
```

Dosya başı docstring'deki "3-tier dual-write" notunu güncelle: "SPEC-Z18: trade_events + equity_history tek dosya (audit). session aynası yalnızca ArchiveLogger için kaldı."

- [ ] **Step 2: Factory smoke testini çalıştır**

Run: `pytest tests/unit/orchestration/ -k factory -v`
Expected: PASS (mirror argümanı kalkınca kıran test varsa Task 6'da düzeltilir)

- [ ] **Step 3: Commit**

```bash
git add src/orchestration/_factory_loggers.py
git commit -m "refactor(orch): SPEC-Z18 logger fabrikalari tek-dosya"
```

---

### Task 4: Dashboard okuyucuları tek audit dosyası

**Files:**
- Modify: `src/presentation/dashboard/readers.py:101-138` (read_trades), `:204-206` (read_equity_history), `:261-290` (read_balance_from_session)
- Test: `tests/unit/presentation/dashboard/test_readers_z17.py`, `test_readers.py`, `test_balance_from_session.py`

- [ ] **Step 1: Failing test yaz** — dashboard SADECE audit okur, session yok.

```python
def test_read_trades_single_audit_file(tmp_path):
    from src.presentation.dashboard.readers import read_trades
    logs = tmp_path / "logs"; (logs / "audit").mkdir(parents=True)
    (logs / "audit" / "trade_events.jsonl").write_text(
        '{"kind":"entry","condition_id":"c1","slug":"s","question":"q",'
        '"sport_tag":"tennis","source":"model","direction":"BUY_YES",'
        '"entry_price":0.5,"entry_timestamp":"2026-06-05T00:00:00+00:00",'
        '"size_usdc":10,"shares":20,"confidence":"A","bookmaker_prob":0.5,'
        '"anchor_probability":0.5,"num_bookmakers":5,"has_sharp":true,'
        '"entry_reason":"normal"}\n', encoding="utf-8")
    trades = read_trades(logs)
    assert len(trades) == 1
```

- [ ] **Step 2: Testi çalıştır, FAIL gör** (mevcut kod session+audit okur; session olmadan da geçebilir — asıl değişiklik session path'i KALDIRMAK)

Run: `pytest tests/unit/presentation/dashboard/test_readers_z17.py -v`

- [ ] **Step 3: Implement**

`read_trades` — `paths` listesini tek dosyaya indir (dedup mantığı tek dosyada da güvenli, kalsın):

```python
    paths = [logs_dir / "audit" / "trade_events.jsonl"]
```

Docstring satır 104'ü güncelle: `Dosya: audit/trade_events.jsonl (tek truth — SPEC-Z18, session aynası yok).`

`read_equity_history` (204-206):

```python
def read_equity_history(logs_dir: Path, n: int = 100) -> list[dict[str, Any]]:
    """equity_history.jsonl son N snapshot — audit/ (tek truth, SPEC-Z18)."""
    return _read_jsonl_tail(logs_dir / "audit" / "equity_history.jsonl", n, _BYTES_EQUITY)
```

`read_balance_from_session` (261-290) — `paths` listesini tek dosyaya indir; isim geriye-uyum için korunur, docstring güncellenir:

```python
    paths = [logs_dir / "audit" / "equity_history.jsonl"]
```

Docstring'e: `SPEC-Z18: tek dosya (audit). Z11 session+audit fallback kaldırıldı — ayrışacak ikinci kopya yok.`

- [ ] **Step 4: Testleri çalıştır, PASS gör**

Run: `pytest tests/unit/presentation/dashboard/ -v`
Expected: PASS (session-bağımlı assertion'lar Task 6'da güncellenir)

- [ ] **Step 5: Commit**

```bash
git add src/presentation/dashboard/readers.py tests/unit/presentation/dashboard/
git commit -m "refactor(dashboard): SPEC-Z18 tek audit dosyasi okuma — session aynasi kaldirildi"
```

---

### Task 5: Reboot doğrulama + ölü session referans temizliği

**Files:**
- Modify (gerekirse): `scripts/reboot.py` docstring satır 7-9
- Test: `tests/integration/test_reboot.py`

**Not:** Reboot DAVRANIŞI zaten doğru — `archive_audit_logs` (copy) + `clear_audit_logs` (delete) = "arşive taşı". `trade_events.jsonl` + `equity_history.jsonl` zaten `_AUDIT_FILES_CLEAR` listesinde. Yeni kod yazılmaz; sadece doğrulanır + docstring güncellenir.

- [ ] **Step 1: Mevcut reboot testleri yeşil mi doğrula**

Run: `pytest tests/integration/test_reboot.py -v`
Expected: PASS

- [ ] **Step 2: "Tek dosya reboot'ta arşivlenir, sonra boşalır" testini netleştir** (mevcut `test_reboot_archives_trade_events_jsonl` yeterli — equity için eşdeğer ekle)

```python
def test_reboot_archives_equity_history_jsonl():
    from scripts.reboot import _AUDIT_FILES_CLEAR
    names = {p.name for p in _AUDIT_FILES_CLEAR}
    assert "equity_history.jsonl" in names
```

- [ ] **Step 3: Docstring güncelle** — satır 7-9'daki "session aynası" ifadesini koru ama not düş: `SPEC-Z18: trade_events + equity_history artık session aynası YAZMAZ; tek dosya audit/, reboot taşır.`

- [ ] **Step 4: Testleri çalıştır, PASS gör**

Run: `pytest tests/integration/test_reboot.py -v`

- [ ] **Step 5: Commit**

```bash
git add scripts/reboot.py tests/integration/test_reboot.py
git commit -m "test(reboot): SPEC-Z18 equity arsiv testi + tek-dosya docstring"
```

---

### Task 6: Kalan testleri tek-dosyaya hizala + tam suite

**Files:**
- Test: `tests/unit/orchestration/test_agent.py`, `test_health_monitor.py`, `tests/unit/presentation/test_cli.py`, `tests/unit/presentation/dashboard/test_routes.py`

- [ ] **Step 1: Tam suite çalıştır, kırıkları bul**

Run: `pytest -q`
Expected: Mirror/session referansı olan testler FAIL — her birini tek-dosya kurgusuna çevir (session yazımı bekleyen assertion'ları audit'e taşı, `mirror_path=` argümanlı çağrıları sadeleştir).

- [ ] **Step 2: Her kırık testi düzelt** (session fixture → audit fixture). Örn `test_routes.py:181` session yazımını audit'e çevir.

- [ ] **Step 3: Tam suite tekrar — tümü PASS**

Run: `pytest -q`
Expected: tümü yeşil

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: SPEC-Z18 kalan testler tek-dosya kurgusuna hizalandi"
```

---

### Task 7: DECISIONS.md güncelle + plan kapat

**Files:**
- Modify: `DECISIONS.md` (§B kronolojik log'a SPEC-Z18 girişi; `_factory_loggers` 3-tier notu ve Z11 fallback notu güncelle/işaretle)

- [ ] **Step 1: SPEC-Z18 kaydı ekle** — özet: audit/session çift-yazım kaldırıldı, tek dosya; "gizemli scheduler yoktu (forensic kanıt)"; divergence sınıfı kapandı.

- [ ] **Step 2: Commit + planı sil**

```bash
git add DECISIONS.md docs/superpowers/plans/2026-06-05-single-ledger-collapse.md
git commit -m "docs: SPEC-Z18 DECISIONS girisi — tek-defter sadelestirmesi"
```

---

## Opsiyonel (ayrı karar — bu planın parçası değil)

- **Mevcut 113-satır session verisini koru:** Cutover öncesi `session/trade_events.jsonl` → `audit/trade_events.jsonl` seed. Kullanıcı "reboot atacağız, önemli değil" dedi → varsayılan: seed YOK, reboot ile sıfırdan.
- **Mayın script temizliği:** `scripts/_z17_*.py` tek-kullanımlık migration script'leri (`write_text` ezen) sil. Reboot dışında defteri silebilecek tek yol bunlar.
- **Hayalet-avı kodu temizliği:** TODO-007 forensic logger + `.bak.before_split` + `_split_trade_history` — forensic "scheduler yok" kanıtladı; reboot.py sadeleşir.
