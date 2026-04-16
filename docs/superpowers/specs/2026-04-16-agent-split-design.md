# Agent.py God Object Split — Design

**Tarih:** 2026-04-16
**Amaç:** `src/orchestration/agent.py` (420 satır, 13 method) → ARCH_GUARD Kural 3 (<400 satır) ve Kural 4 (<10 method) uyumu.

---

## Problem

`agent.py` hem entry flow (heavy cycle), hem exit flow (light cycle), hem lifecycle yönetiyor. 420 satır (>400) ve 13 method (>10) — iki ARCH_GUARD ihlali.

## Çözüm: Composition Split

Agent class'ı 3 dosyaya bölünür. Agent lifecycle'ı tutar, entry/exit işlerini delegate eder.

### Dosya yapısı

| Dosya | Class | Sorumluluk | Method | Satır (~) |
|---|---|---|---|---|
| `src/orchestration/agent.py` | `Agent` | Lifecycle + delegation | 5 | ~120 |
| `src/orchestration/entry_processor.py` | `EntryProcessor` | Heavy cycle entry flow | 4 | ~200 |
| `src/orchestration/exit_processor.py` | `ExitProcessor` | Light cycle exit flow | 4 | ~120 |

### Method dağılımı

**Agent (lifecycle):**
- `__init__` — deps alır, EntryProcessor + ExitProcessor oluşturur
- `request_stop`
- `run` — main loop (heavy/light dispatch)
- `_start_ws_if_needed`
- `_on_price_update`

**EntryProcessor (heavy cycle):**
- `__init__` — deps alır (AgentDeps referansı)
- `run_heavy` (eski `_run_heavy`)
- `process_markets` (eski `_process_markets`)
- `_execute_entry` (eski `_execute_entry` + `_log_trade_entry` birleşir)

**ExitProcessor (light cycle):**
- `__init__` — deps alır
- `run_light` (eski `_run_light`)
- `_apply_fav_transition`
- `_execute_exit`
- `_execute_partial_exit`

### Bağlantı modeli

```python
# agent.py
class Agent:
    def __init__(self, deps: AgentDeps):
        self.deps = deps
        self._entry = EntryProcessor(deps)
        self._exit = ExitProcessor(deps)
    
    def run(self, ...):
        ...
        if heavy: self._entry.run_heavy(...)
        if light: self._exit.run_light()
```

`AgentDeps` dataclass değişmiyor — her üç class aynı deps'i paylaşır (shared state: portfolio, executor, logger vs).

### Test stratejisi

- Mevcut `tests/unit/orchestration/test_agent.py` testleri çoğu Agent.run() veya internal method'lar test ediyor.
- Import path'ler değişecek (`Agent._process_markets` → `EntryProcessor.process_markets`).
- Mevcut testlerin büyük kısmı Agent seviyesinde kalabilir (Agent hâlâ delegation yapıyor, API aynı).
- Entry-specific testler `test_entry_processor.py`'a, exit-specific testler `test_exit_processor.py`'a taşınabilir — ama YAGNI: mevcut testler Agent seviyesinde çalışıyorsa taşımaya gerek yok.

### `_log_trade_entry` birleşme

`_log_trade_entry` (30 satır) sadece `_execute_entry` tarafından çağrılıyor → `_execute_entry` içine inline edilir (ayrı method gereksiz). EntryProcessor'da tek `_execute_entry` method'u olur.

### ARCH_GUARD uyum

- **Kural 3 (400 satır):** 3 dosya, her biri <200 ✓
- **Kural 4 (10 method):** Agent 5, Entry 4, Exit 5 ✓
- **Kural 1 (katman):** Hepsi orchestration — katman değişmiyor ✓
- **Kural 9 (yeni dosya):** Mevcut dizine (`src/orchestration/`) ekleniyor, yeni dizin yok ✓

### Kapsam dışı

- AgentDeps yapısı değişmiyor
- Factory değişikliği: `Agent(deps)` constructor aynı kalıyor (internal composition)
- Yeni feature eklenmesi yok — pure refactoring
