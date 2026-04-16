# Dynamic Continuity — Cap Clipping + Match-Start Priority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate'in `exposure_cap_reached` skip'ini sıralı size-clipping + match_start öncelik mekanizmasıyla değiştir.

**Architecture:** `available_under_cap` pure fn domain'e eklenir (soft+hard cap hesabı). Gate ve agent bu fn'i çağırıp signal.size_usdc'yi kırpar ya da skip eder. Agent entry loop'u signal'leri match_start ASC (tie-break: volume_24h DESC) sıralar — yakın maçlar cap'te yerini önce alır.

**Tech Stack:** Python 3.12, Pydantic BaseModel, pytest, pyyaml.

**Spec:** [docs/superpowers/specs/2026-04-16-dynamic-continuity-cap-clip-design.md](../specs/2026-04-16-dynamic-continuity-cap-clip-design.md)

---

## File Structure

| Dosya | Rol | Değişiklik tipi |
|---|---|---|
| `src/config/settings.py` | `RiskConfig` — 2 yeni alan | Modify |
| `config.yaml` | Runtime config | Modify |
| `src/domain/portfolio/exposure.py` | Pure cap math | Modify (+1 fn) |
| `src/strategy/entry/gate.py` | Cap-skip → cap-clip | Modify |
| `src/orchestration/agent.py` | Match-start priority + runtime clip | Modify |
| `tests/unit/domain/portfolio/test_exposure.py` | Yeni fn testi | Modify |
| `tests/unit/strategy/entry/test_gate.py` | Clip davranışı | Modify |
| `tests/unit/orchestration/test_agent.py` | Priority sort | Modify |
| `TDD.md` | §6.15 cap mantığı güncelle | Modify |

---

## Task 1 — Config schema: yeni alanlar

**Files:**
- Modify: `src/config/settings.py:47-56` (RiskConfig)
- Modify: `config.yaml:67-77` (risk: bloğu)

- [ ] **Step 1.1 — Settings.py'a 2 alan ekle**

`src/config/settings.py` RiskConfig (satır 47-56):

```python
class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_single_bet_usdc: float = 75
    max_bet_pct: float = 0.05
    max_positions: int = 20
    max_exposure_pct: float = 0.50
    hard_cap_overflow_pct: float = 0.02      # YENİ
    min_entry_size_pct: float = 0.015        # YENİ
    max_entry_price: float = 0.88
    consecutive_loss_cooldown: int = 3
    cooldown_cycles: int = 2
    stop_loss_pct: float = 0.30
```

- [ ] **Step 1.2 — config.yaml risk: bloğunu güncelle**

`config.yaml` `risk:` altına (satır 71 civarı, `max_exposure_pct: 0.50`'den hemen sonra):

```yaml
  max_exposure_pct: 0.50
  hard_cap_overflow_pct: 0.02   # soft cap üstüne +%2 buffer (hard cap = %52 @ %50 soft)
  min_entry_size_pct: 0.015     # min pozisyon = bankroll × %1.5 (transaction cost floor)
  max_entry_price: 0.88
```

- [ ] **Step 1.3 — Commit**

```bash
git add src/config/settings.py config.yaml
git commit -m "feat(config): add hard_cap_overflow_pct + min_entry_size_pct fields"
```

---

## Task 2 — Domain: `available_under_cap` pure function

**Files:**
- Modify: `src/domain/portfolio/exposure.py` (+1 fn)
- Modify: `tests/unit/domain/portfolio/test_exposure.py` (+5 test)

- [ ] **Step 2.1 — Testi yaz (failing)**

`tests/unit/domain/portfolio/test_exposure.py` dosyasının sonuna ekle:

```python
from src.domain.portfolio.exposure import available_under_cap


class _Pos:
    def __init__(self, size): self.size_usdc = size


def test_available_under_cap_soft_cap_not_reached_returns_full_buffer():
    # $100 exposure, $1000 portfolio, soft 50%, hard +2% (=52%)
    positions = {"a": _Pos(100.0)}
    avail = available_under_cap(positions, total_portfolio_value=1000.0,
                                soft_cap_pct=0.50, overflow_pct=0.02)
    # hard cap = 520, exposure = 100, available = 420
    assert avail == 420.0


def test_available_under_cap_soft_cap_exactly_at_limit():
    positions = {"a": _Pos(500.0)}
    avail = available_under_cap(positions, 1000.0, 0.50, 0.02)
    assert avail == 20.0  # hard cap 520 - 500 invested


def test_available_under_cap_hard_cap_fully_used_returns_zero():
    positions = {"a": _Pos(520.0)}
    avail = available_under_cap(positions, 1000.0, 0.50, 0.02)
    assert avail == 0.0


def test_available_under_cap_negative_over_hard_cap_clamps_to_zero():
    positions = {"a": _Pos(600.0)}  # somehow over hard cap
    avail = available_under_cap(positions, 1000.0, 0.50, 0.02)
    assert avail == 0.0


def test_available_under_cap_zero_portfolio_returns_zero():
    avail = available_under_cap({}, 0.0, 0.50, 0.02)
    assert avail == 0.0
```

- [ ] **Step 2.2 — Failing olduğunu doğrula**

```
pytest tests/unit/domain/portfolio/test_exposure.py -v
```

Expected: 5 test FAIL, "cannot import name 'available_under_cap'".

- [ ] **Step 2.3 — Implementasyon**

`src/domain/portfolio/exposure.py` dosyasının sonuna ekle:

```python
def available_under_cap(
    positions: dict,
    total_portfolio_value: float,
    soft_cap_pct: float,
    overflow_pct: float,
) -> float:
    """Hard cap altında yeni pozisyon için kalan tutar (USDC).

    hard_cap = total_portfolio_value × (soft_cap_pct + overflow_pct)
    available = max(0, hard_cap - mevcut_invested)

    Dönüş 0 ise: skip. >0 ise: min(kelly_size, available) kırpılarak girilir.
    """
    if total_portfolio_value <= 0:
        return 0.0
    hard_cap = total_portfolio_value * (soft_cap_pct + overflow_pct)
    total_invested = sum(getattr(p, "size_usdc", 0.0) for p in positions.values())
    return max(0.0, hard_cap - total_invested)
```

- [ ] **Step 2.4 — Test geçtiğini doğrula**

```
pytest tests/unit/domain/portfolio/test_exposure.py -v
```

Expected: tüm testler PASS.

- [ ] **Step 2.5 — Commit**

```bash
git add src/domain/portfolio/exposure.py tests/unit/domain/portfolio/test_exposure.py
git commit -m "feat(domain): add available_under_cap with soft+hard cap math"
```

---

## Task 3 — Gate: exposure-skip → exposure-clip

**Files:**
- Modify: `src/strategy/entry/gate.py:40-58` (GateConfig — 2 yeni alan)
- Modify: `src/strategy/entry/gate.py:161-167` (cap check skip → clip)
- Modify: `tests/unit/strategy/entry/test_gate.py` (+3 test)

- [ ] **Step 3.1 — Test yaz (failing): clip davranışı**

`tests/unit/strategy/entry/test_gate.py` dosyasına ekle (mevcut gate test fixture'larının yanına):

```python
def test_gate_clips_signal_size_when_partial_space_in_hard_cap(
    gate_factory,  # mevcut fixture: EntryGate inşa eder
):
    # $497 açık, bankroll $1000 → portfolio $1497 (cash $503)
    # soft 50% = $748, hard 52% = $778, available = $778 - $497 = $281 (uyduruk)
    # Basit: bankroll/portfolio hesapları fixture'dan.
    # Bu test mevcut gate fixture ile uyumlandırılmalı.
    # Beklenen: Kelly $50 ama available $23 → signal.size_usdc = $23 olmalı.
    ...  # fixture'a göre senaryo kur


def test_gate_skips_when_available_below_min_entry_size():
    # available = $8, min_entry_size_pct × bankroll = $15 → skip, reason=exposure_cap_reached
    ...


def test_gate_skips_when_hard_cap_fully_used():
    # total_invested = bankroll × (soft+overflow) → available = 0 → skip
    ...
```

> NOT: Gate test fixture'ları projede mevcut. Çağıran engineer fixture'a uygun senaryo parametrelerini doldurmalı. Pseudo-kod yerine gerçek fixture semantiğini `tests/unit/strategy/entry/test_gate.py` dosyasından kopyalayıp parametreleri ayarla.

- [ ] **Step 3.2 — GateConfig'e 2 alan ekle**

`src/strategy/entry/gate.py:40-58` dataclass:

```python
@dataclass
class GateConfig:
    min_edge: float = 0.06
    max_positions: int = 50
    max_exposure_pct: float = 0.50
    hard_cap_overflow_pct: float = 0.02      # YENİ
    min_entry_size_pct: float = 0.015        # YENİ
    max_single_bet_usdc: float = 75.0
    max_bet_pct: float = 0.05
    max_entry_price: float = 0.88
    # ...consensus/early aynı
```

- [ ] **Step 3.3 — Gate cap-check bloğunu clip'e çevir**

`src/strategy/entry/gate.py:161-171` bloğunu şu şekilde değiştir:

```python
        # 7. Exposure cap — soft + hard buffer + min size clipping.
        from src.domain.portfolio.exposure import available_under_cap
        total_portfolio = self.portfolio.bankroll + self.portfolio.total_invested()
        available = available_under_cap(
            self.portfolio.positions, total_portfolio,
            self.config.max_exposure_pct, self.config.hard_cap_overflow_pct,
        )
        min_size = self.portfolio.bankroll * self.config.min_entry_size_pct
        if available < min_size:
            return GateResult(cid, None, "exposure_cap_reached", manipulation=manip)

        final_size = min(adjusted_size, available)
        if final_size < POLYMARKET_MIN_ORDER_USDC:
            return GateResult(cid, None,
                              f"size_below_min ({final_size:.2f} < {POLYMARKET_MIN_ORDER_USDC})",
                              manipulation=manip)

        # Signal'a size yaz ve onayla
        approved = signal.model_copy(update={"size_usdc": round(final_size, 2)})
        return GateResult(cid, approved, "", manipulation=manip)
```

**Import taşı:** `from src.domain.portfolio.exposure import available_under_cap, exceeds_exposure_limit` — mevcut import satırında `available_under_cap`'i de ekle, `exceeds_exposure_limit` referansını kaldır (bu fn gate'te artık çağrılmıyor, ama agent'ta hâlâ kullanıyor olabilir — Task 5'te halledilir).

- [ ] **Step 3.4 — Testleri çalıştır**

```
pytest tests/unit/strategy/entry/test_gate.py -v
```

Expected: 3 yeni test PASS + mevcut gate testleri PASS.

- [ ] **Step 3.5 — Commit**

```bash
git add src/strategy/entry/gate.py tests/unit/strategy/entry/test_gate.py
git commit -m "feat(gate): replace exposure-skip with soft+hard cap size clipping"
```

---

## Task 4 — Agent: match_start ASC priority + runtime clip

**Files:**
- Modify: `src/orchestration/agent.py:198-231` (_process_markets entry loop)
- Modify: `tests/unit/orchestration/test_agent.py` (+2 test)

- [ ] **Step 4.1 — Test yaz: signal'ler match_start ASC sırayla değerlendirilir**

`tests/unit/orchestration/test_agent.py` dosyasına ekle:

```python
def test_agent_entry_loop_evaluates_in_match_start_ascending_order(mock_agent_deps):
    """3 aday: T+10h, T+1h, T+3h. Execute sırası: T+1h, T+3h, T+10h."""
    # mock_agent_deps fixture'ından yararlan; 3 fake market + 3 GateResult üret.
    # Expected: deps.executor.place_order ilk T+1h slug ile çağrılsın.
    ...


def test_agent_entry_loop_tiebreak_by_volume24h_desc():
    """Aynı match_start, farklı volume_24h → yüksek volume önce."""
    ...
```

- [ ] **Step 4.2 — Agent loop'unu güncelle**

`src/orchestration/agent.py` `_process_markets` fonksiyonunun gate.run sonrası loop'u (satır 205-231) şu şekilde değiştir:

```python
        results = self.deps.gate.run(markets)
        by_cid = {m.condition_id: m for m in markets}
        max_exposure_pct = self.deps.gate.config.max_exposure_pct
        overflow_pct = self.deps.gate.config.hard_cap_overflow_pct
        min_entry_pct = self.deps.gate.config.min_entry_size_pct
        executing_written = False

        # Match-start ASC priority: yakın maçlar cap'ten yerini önce alır.
        # Tie-break: volume_24h DESC (daha likit önce).
        def _priority_key(r):
            market = by_cid.get(r.condition_id)
            if market is None or r.signal is None:
                return ("9999-99-99", 0.0)
            return (market.match_start_iso or "9999-99-99", -market.volume_24h)

        # Skip'leri (signal=None) önce işle — stock'a eklensin, priority sort sadece approved için
        for r in results:
            if r.signal is not None:
                continue
            market = by_cid.get(r.condition_id)
            if market is not None:
                operational_writers.log_skip(self.deps.skipped_logger, market, r.skipped_reason)
                self.deps.stock.add(market, r.skipped_reason)

        approved_sorted = sorted(
            [r for r in results if r.signal is not None],
            key=_priority_key,
        )

        for r in approved_sorted:
            market = by_cid.get(r.condition_id)
            if market is None:
                continue

            # Execution-time cap clipping — portfolio her add sonrası değişir.
            from src.domain.portfolio.exposure import available_under_cap
            pm = self.deps.state.portfolio
            total_portfolio = pm.bankroll + pm.total_invested()
            available = available_under_cap(
                pm.positions, total_portfolio, max_exposure_pct, overflow_pct,
            )
            min_size = pm.bankroll * min_entry_pct
            if available < min_size:
                operational_writers.log_skip(self.deps.skipped_logger, market, "exposure_cap_reached")
                self.deps.stock.add(market, "exposure_cap_reached")
                continue

            final_size = min(r.signal.size_usdc, available)
            clipped_signal = r.signal.model_copy(update={"size_usdc": round(final_size, 2)})

            if not executing_written:
                self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="executing")
                executing_written = True
            self._execute_entry(market, clipped_signal)
            self.deps.stock.remove(market.condition_id)
```

**İthalat:** `from src.domain.portfolio.exposure import exceeds_exposure_limit` kullanımı kaldırılır (Agent artık `available_under_cap` kullanıyor). Import satırını güncelle.

- [ ] **Step 4.3 — Testleri çalıştır**

```
pytest tests/unit/orchestration/test_agent.py -v
```

Expected: yeni 2 test PASS + mevcut testler PASS.

- [ ] **Step 4.4 — Commit**

```bash
git add src/orchestration/agent.py tests/unit/orchestration/test_agent.py
git commit -m "feat(agent): match_start ASC priority + runtime size clipping"
```

---

## Task 5 — TDD.md güncelle

**Files:**
- Modify: `TDD.md` (§6.15 cap ve §13 entry gate bölümleri)

- [ ] **Step 5.1 — TDD.md §6.15 (exposure cap) bölümünü bul ve güncelle**

Grep:
```
grep -n "exposure_cap\|max_exposure_pct\|hard.cap" TDD.md
```

İlgili bölüme (varsa) veya §6.15'e şu notu ekle:

```markdown
### Soft + Hard Cap Buffer + Size Clipping

`max_exposure_pct` soft cap; gate+agent cap'i aşan signal'i **skip etmez, kırpar**.

- `soft_cap = portfolio × max_exposure_pct` (default %50)
- `hard_cap = portfolio × (max_exposure_pct + hard_cap_overflow_pct)` (default %52)
- `available = max(0, hard_cap − total_invested)`
- `min_size = bankroll × min_entry_size_pct` (default %1.5)

Akış:
1. `available ≤ 0` → skip (`exposure_cap_reached`)
2. `available < min_size` → skip (tx-cost floor; komisyonla zararlı mini-pozisyon)
3. diğer → `entry_size = min(kelly, available)` ile gir

Neden: Kelly-sizing büyük-edge fırsatlarda cap'i aşar; tamamen reddetmek yakın yüksek-edge pozisyonları kaybettiriyordu (2026-04-15 SF-CIN live-edge kaybı). Clip mantığı: cap'i aşan kısmı kes, kalanı yine aç.

Pure fn: `src.domain.portfolio.exposure.available_under_cap`.
```

- [ ] **Step 5.2 — TDD.md §13 (entry gate) bölümüne not ekle**

`§13` veya "entry_gate / gate" başlıklı bölümde:

```markdown
#### Match-start ASC Priority
Agent gate.run sonrası approved signal'leri `match_start ASC, volume_24h DESC` sıralar.
Erken başlayan maçlar cap'ten yerini önce alır; yakın maçlar cap dolmadan girer, 10h sonraki adaylar kalan yere bakar.

Uygulandığı yer: `src/orchestration/agent.py::_process_markets`.
```

- [ ] **Step 5.3 — Commit**

```bash
git add TDD.md
git commit -m "docs(tdd): document soft+hard cap clipping + match_start priority"
```

---

## Task 6 — Full test suite + smoke check

- [ ] **Step 6.1 — Full pytest run**

```
pytest -q
```

Expected: tüm testler PASS. Başarısız test varsa ilgili dosyada fix.

- [ ] **Step 6.2 — Grep kontrolü: artık eski skip mantığı kalmamalı**

```
grep -rn "exceeds_exposure_limit" src/
```

Expected: Kullanılan dosya YOK ya da sadece backward-compat için (exposure.py'de fn duruyor ama çağrılmıyor). Eğer gate/agent'ta hâlâ import varsa kaldır.

- [ ] **Step 6.3 — Grep: config alanları geçerli**

```
grep -rn "hard_cap_overflow_pct\|min_entry_size_pct" src/ config.yaml
```

Expected: `settings.py`, `gate.py`, `agent.py`, `config.yaml` — hepsinde mevcut.

- [ ] **Step 6.4 — Smoke: bot dry_run tek cycle**

```
python -m src.main --mode dry_run --once
```

Expected: Exception yok, log'da `clipped:` satırı olabilir ama skip count'ları tutarlı.

- [ ] **Step 6.5 — Final commit (gerekirse)**

```bash
git status
# Eğer fix gerektiyse:
git add -u && git commit -m "fix: test/integration fixes after cap clipping rollout"
```

---

## Self-Review

**Spec coverage:**
- ✓ Soft cap + hard cap buffer + min size floor — Task 1, 2
- ✓ Gate cap-skip → cap-clip — Task 3
- ✓ Agent match_start ASC priority + runtime clip — Task 4
- ✓ Test cases (5 domain + 3 gate + 2 agent) — Tasks 2, 3, 4
- ✓ TDD.md update — Task 5
- ✓ ARCH_GUARD uyum (katman düzeni, magic number yok, test zorunlu)

**Placeholder scan:** "..." placeholder'lar Task 3.1 ve 4.1'de var — engineer fixture semantiğine göre gerçek test case yazmalı. Not eklendi.

**Type consistency:**
- `available_under_cap(positions, total_portfolio_value, soft_cap_pct, overflow_pct) -> float` — gate ve agent aynı signature ile çağırıyor ✓
- `GateConfig.hard_cap_overflow_pct`, `.min_entry_size_pct` — her iki yerde aynı isim ✓
- `Signal.size_usdc` — `model_copy(update=...)` ile kırpılıyor (Pydantic pattern) ✓

---

## Execution Handoff

Plan complete. İki seçenek:

1. **Subagent-Driven (önerilen)** — her task için fresh subagent, task aralarında review, hızlı iterasyon.
2. **Inline Execution** — bu session'da task'leri çalıştır, checkpoint'lerle review.

Hangisi?
