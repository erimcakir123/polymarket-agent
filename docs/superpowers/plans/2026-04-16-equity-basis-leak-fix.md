# Equity Chart + Partial-Exit Basis-Leak Fix

**Goal:** (1) Fix silent basis-leak in `apply_partial_exit` (bankroll under-reports cash after every scale-out). (2) Rebuild Total Equity chart on top of `trade_history.jsonl` cumulative realized PnL so it is identity-correct by construction.

**Architecture:** Two surgical fixes, independent but shipped together.
- **Accounting (domain):** `apply_partial_exit` now takes `basis_returned_usdc + realized_usdc`; credits both to bankroll (mirror of `remove_position`). `exit_processor` computes basis BEFORE shrinking `pos.size_usdc`.
- **Chart (presentation):** `setEquity` consumes `trades` (from `/api/trades`) and plots `initial + cumulative realized_pnl_usdc` stepped. `equity_history.jsonl` stays as audit artifact; peak/drawdown continue to read it.

**Tech Stack:** Python 3.12 (domain + orchestration), vanilla JS (Chart.js step line).

**TDD refs:** §5.7.7 (Total Equity Chart — Realized-Only Stepped), §6.6 (Scale-Out 3-tier), §6.15 (Exposure cap — consumes bankroll).

**ARCH_GUARD refs:** Kural 1 (katman düzeni), Kural 2 (domain I/O yok), Kural 6 (magic number yok), Kural 11 (test zorunlu), Kural 12 (hata yönetimi).

---

## File Structure

**Modify:**
- `src/domain/portfolio/manager.py:74-79` — `apply_partial_exit` signature + body
- `src/orchestration/exit_processor.py:84-91` — compute `basis_returned` before shrinking, pass both args
- `src/presentation/dashboard/static/js/dashboard.js:146-154` — `setEquity(trades, initial)` via cumulative sum
- `src/presentation/dashboard/static/js/dashboard.js:315-330` — dashboard refresh flow feeds trades into setEquity
- `TDD.md §5.7.7` — implementation note: chart source switches from snapshot to trade-history cumsum

**Tests:**
- `tests/unit/domain/portfolio/test_manager.py` — new: `test_apply_partial_exit_credits_basis_and_realized`, `test_apply_partial_exit_preserves_identity`
- `tests/unit/orchestration/test_exit_processor.py` (or closest existing) — extend partial-exit test to assert `portfolio.bankroll + portfolio.total_invested() == initial + realized_pnl` after partial

**NOT touched:**
- `src/infrastructure/persistence/equity_history.py` — snapshot schema unchanged; snapshots continue for audit + peak calc
- `src/presentation/dashboard/computed.py::_peak_total_equity` — keeps reading snapshots (already uses `bankroll+invested+unrealized` which post-fix will match identity)
- `logs/equity_history.jsonl` — kept as-is; chart no longer depends on it so the historical leak becomes irrelevant

---

## Task 1 — Domain: `apply_partial_exit` takes basis + realized (TDD)

**Files:**
- Modify: `src/domain/portfolio/manager.py:74-79`
- Test: `tests/unit/domain/portfolio/test_manager.py`

- [ ] **Step 1.1 — Write failing test (identity after partial)**

Add to `tests/unit/domain/portfolio/test_manager.py`:

```python
def test_apply_partial_exit_credits_basis_and_realized():
    pm = PortfolioManager(initial_bankroll=1000.0)
    pos = Position(
        condition_id="c1", token_id="t1", direction="BUY_YES",
        entry_price=0.50, size_usdc=30.0, shares=60.0,
        slug="x", sport_tag="x", question="q", event_id="e1",
        confidence="A", anchor_probability=0.6,
        current_price=0.575, bid_price=0.57,
    )
    assert pm.add_position(pos) is True
    # Simulate 30% partial: basis returned = 9.0, realized = (60*0.575 - 30) * 0.3 = 1.35
    pm.apply_partial_exit("c1", basis_returned_usdc=9.0, realized_usdc=1.35)
    # Bankroll change: -30 (entry) + 9.0 + 1.35 = -19.65
    assert pm.bankroll == pytest.approx(1000.0 - 30.0 + 9.0 + 1.35)
    assert pm.realized_pnl == pytest.approx(1.35)


def test_apply_partial_exit_preserves_identity():
    pm = PortfolioManager(initial_bankroll=1000.0)
    pos = Position(
        condition_id="c1", token_id="t1", direction="BUY_YES",
        entry_price=0.50, size_usdc=30.0, shares=60.0,
        slug="x", sport_tag="x", question="q", event_id="e1",
        confidence="A", anchor_probability=0.6,
        current_price=0.575, bid_price=0.57,
    )
    pm.add_position(pos)
    # Caller is responsible for shrinking pos.size_usdc; simulate that.
    pos.size_usdc = 21.0
    pos.shares = 42.0
    pm.apply_partial_exit("c1", basis_returned_usdc=9.0, realized_usdc=1.35)
    # Identity: bankroll + invested == initial + realized_pnl
    invested = sum(p.size_usdc for p in pm.positions.values())
    assert pm.bankroll + invested == pytest.approx(1000.0 + pm.realized_pnl)
```

- [ ] **Step 1.2 — Run tests, confirm failure**

```
pytest tests/unit/domain/portfolio/test_manager.py::test_apply_partial_exit_credits_basis_and_realized -v
pytest tests/unit/domain/portfolio/test_manager.py::test_apply_partial_exit_preserves_identity -v
```

Expected: FAIL — current signature is `(condition_id, realized_usdc)`, no `basis_returned_usdc`.

- [ ] **Step 1.3 — Update `apply_partial_exit`**

Edit `src/domain/portfolio/manager.py`:

```python
def apply_partial_exit(
    self,
    condition_id: str,
    basis_returned_usdc: float,
    realized_usdc: float,
) -> None:
    """Scale-out: partial exit realize et.

    Caller pos.size_usdc'yi küçültmeden ÖNCE basis_returned_usdc'yi hesaplar
    (`old_size × sell_pct`) ve buraya verir. Bankroll hem basis geri alımı
    hem realized PnL ile kredilenir → `remove_position` pattern'iyle simetrik.
    Identity: `bankroll + invested = initial + realized_pnl` her zaman korunur.
    """
    if condition_id not in self.positions:
        return
    self.bankroll += basis_returned_usdc + realized_usdc
    self.realized_pnl += realized_usdc
```

- [ ] **Step 1.4 — Run tests, confirm pass**

```
pytest tests/unit/domain/portfolio/test_manager.py -v
```

Expected: both new tests PASS; existing tests still pass.

- [ ] **Step 1.5 — Commit**

```
git add src/domain/portfolio/manager.py tests/unit/domain/portfolio/test_manager.py
git commit -m "fix(domain): apply_partial_exit credits basis + realized to preserve identity"
```

---

## Task 2 — Orchestration: exit_processor passes basis before shrinking

**Files:**
- Modify: `src/orchestration/exit_processor.py:84-91`
- Test: `tests/unit/orchestration/test_exit_processor.py`

- [ ] **Step 2.1 — Write failing test (identity after orchestrated partial)**

Find existing partial-exit test in `tests/unit/orchestration/test_exit_processor.py`; extend with:

```python
def test_partial_exit_preserves_identity(exit_processor_with_winning_pos):
    ep, pos = exit_processor_with_winning_pos  # fixture: pos.size=30, shares=60, current_price=0.575
    pm = ep.deps.state.portfolio
    initial_bankroll = pm.initial_bankroll
    realized_before = pm.realized_pnl

    ep._do_partial_exit(pos, signal_with_sell_pct_30())

    invested = sum(p.size_usdc for p in pm.positions.values())
    # Identity holds strictly:
    assert pm.bankroll + invested == pytest.approx(initial_bankroll + pm.realized_pnl)
    # Realized grew by pos unrealized×0.3:
    assert pm.realized_pnl - realized_before == pytest.approx(4.5 * 0.3)
    # pos.size shrunk to 70%:
    assert pos.size_usdc == pytest.approx(21.0)
```

(If a matching fixture does not exist, build one inline — don't add to a shared fixtures file.)

- [ ] **Step 2.2 — Run test, confirm failure**

```
pytest tests/unit/orchestration/test_exit_processor.py::test_partial_exit_preserves_identity -v
```

Expected: FAIL — identity breaks by `basis_returned` each call (current behaviour).

- [ ] **Step 2.3 — Update `exit_processor._do_partial_exit`**

Edit `src/orchestration/exit_processor.py` (replace the partial exit block):

```python
def _do_partial_exit(self, pos, signal) -> None:
    """Scale-out partial exit."""
    shares_to_sell = pos.shares * signal.sell_pct
    realized = pos.unrealized_pnl_usdc * signal.sell_pct
    basis_returned = pos.size_usdc * signal.sell_pct

    pos.shares -= shares_to_sell
    pos.size_usdc *= (1 - signal.sell_pct)
    pos.scale_out_tier = signal.tier or pos.scale_out_tier
    pos.scale_out_realized_usdc += realized

    self.deps.state.portfolio.apply_partial_exit(
        pos.condition_id,
        basis_returned_usdc=basis_returned,
        realized_usdc=realized,
    )
    self.deps.trade_logger.log_partial_exit(
        condition_id=pos.condition_id,
        tier=signal.tier or pos.scale_out_tier,
        sell_pct=signal.sell_pct,
        realized_pnl_usdc=realized,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
```

(Preserve rest of the method — log lines, persistence — untouched.)

- [ ] **Step 2.4 — Grep for other callers of `apply_partial_exit`**

```
grep -rn "apply_partial_exit" src tests
```

Expected callers: `exit_processor.py` (Task 2.3) + test files. Update any stale call sites to new signature.

- [ ] **Step 2.5 — Run full orchestration suite**

```
pytest tests/unit/orchestration -v
pytest tests/unit/domain/portfolio -v
```

Expected: all pass.

- [ ] **Step 2.6 — Commit**

```
git add src/orchestration/exit_processor.py tests/unit/orchestration/test_exit_processor.py
git commit -m "fix(orchestration): pass basis_returned to apply_partial_exit in scale-out"
```

---

## Task 3 — Presentation: Total Equity chart from trade cumsum

**Files:**
- Modify: `src/presentation/dashboard/static/js/dashboard.js:146-154` + `:315-330`

- [ ] **Step 3.1 — Rewrite `setEquity`**

Edit `static/js/dashboard.js` (replace lines 146-154):

```javascript
setEquity(trades, initialBankroll) {
  // TDD §5.7.7: chart = initial + cumulative realized PnL from trade history.
  // `trades` comes from /api/trades (computed.exit_events) — sorted DESC by
  // exit_timestamp. Reverse → chronological, then cumsum.
  const chronological = [...trades].reverse();
  let running = Number(initialBankroll) || 0;
  const labels = [""];
  const data = [running];
  for (const t of chronological) {
    const pnl = Number(t.exit_pnl_usdc || 0);
    running += pnl;
    labels.push(t.exit_timestamp || "");
    data.push(running);
  }
  this.equity.data.labels = labels;
  this.equity.data.datasets[0].data = data;
  this.equity.update("none");
},
```

- [ ] **Step 3.2 — Update caller to pass trades + initial**

Locate the refresh block around `static/js/dashboard.js:315-330`. Change the `CHARTS.setEquity(equityHistory)` call to:

```javascript
CHARTS.setEquity(trades, CONFIG.initialBankroll);
```

- [ ] **Step 3.3 — Wire `initialBankroll` into `CONFIG`**

Confirm `CONFIG.initialBankroll` is rendered from the template. If missing, add to `templates/dashboard.html` where `CONFIG` is declared:

```html
<script>
  window.CONFIG = {
    ...,
    initialBankroll: {{ initial_bankroll|tojson }},
  };
</script>
```

- [ ] **Step 3.4 — Drop the unused `equityHistory` fetch from the refresh batch (optional cleanup)**

If no other consumer uses `equityHistory` in the refresh flow, remove `API.equityHistory()` from the `Promise.all` and the destructured name. Leave `/api/equity_history` endpoint alive — `/api/summary` still uses `read_equity_history` server-side for peak calc.

- [ ] **Step 3.5 — Manual verification in browser**

Start dev dashboard, reload, visually check:
- Total Equity chart starts at $1000 baseline
- Each step matches a Per-Trade PnL bar (same number of steps as exit events including partials)
- Final value equals $1000 + current `realized_pnl` from Balance card

- [ ] **Step 3.6 — Commit**

```
git add src/presentation/dashboard/static/js/dashboard.js src/presentation/dashboard/templates/dashboard.html
git commit -m "feat(dashboard): equity chart from trade cumsum (identity-correct by construction)"
```

---

## Task 4 — Docs: update TDD §5.7.7

**Files:**
- Modify: `TDD.md` §5.7.7

- [ ] **Step 4.1 — Rewrite §5.7.7 implementation note**

Find `#### 5.7.7 Total Equity Chart — Realized-Only Stepped` in `TDD.md` and replace body with:

```markdown
#### 5.7.7 Total Equity Chart — Realized-Only Stepped

Chart formülü: `initial + cumulative realized_pnl` (trade history üzerinden
kümülatif). **Unrealized hariç** — açık pozisyonların anlık fiyat
dalgalanması chart'ı kirletmez.

Veri kaynağı: `/api/trades` (`computed.exit_events`) — full-close exit'ler +
partial scale-out event'leri kronolojik sıraya çevrilir, `exit_pnl_usdc`
kümülatif toplanır.

Rendering: `stepped: "before"`, `tension: 0` — yumuşak eğri yerine
basamaklı plateau. Her exit/partial event net bir zıplama.

**Neden snapshot değil trade-cumsum:** `equity_history.jsonl` snapshots
`portfolio.bankroll` stored value kullanıyordu; partial exit basis-leak'i
nedeniyle kimlik kırılıyordu (2026-04-16 fix). Trade-history cumsum
inşaatı gereği kimliği korur.

Identity: `initial + Σ exit_pnl_usdc = initial + realized_pnl`
(positions.json'daki stored `realized_pnl` ile karşılaştırma doğrulama noktasıdır).

Lokasyon: `static/js/dashboard.js::CHARTS.setEquity` (trades + initial).
```

- [ ] **Step 4.2 — Commit**

```
git add TDD.md
git commit -m "docs(tdd): §5.7.7 equity chart source switch to trade cumsum"
```

---

## Task 5 — Final verification

- [ ] **Step 5.1 — Full test suite**

```
pytest -q
```

Expected: all green.

- [ ] **Step 5.2 — Identity sanity check**

In a REPL against current logs:

```python
import json
from pathlib import Path
trades = [json.loads(l) for l in Path("logs/trade_history.jsonl").read_text().splitlines() if l.strip()]
pos = json.loads(Path("logs/positions.json").read_text())
realized_from_trades = sum(
    (t.get("exit_pnl_usdc") or 0.0) for t in trades if t.get("exit_price") is not None
) + sum(
    (pe.get("realized_pnl_usdc") or 0.0)
    for t in trades for pe in (t.get("partial_exits") or [])
)
print("stored realized:", pos["realized_pnl"])
print("trade-cumsum:   ", realized_from_trades)
# These must match within 0.01.
```

- [ ] **Step 5.3 — Start bot briefly, trigger a partial (paper mode)**

Manually force a scale-out event or wait for one; confirm after the partial:
- `portfolio.bankroll + sum(p.size_usdc) == initial_bankroll + portfolio.realized_pnl` (no leak)
- Chart gains a single upward step equal to the partial's realized PnL

---

## Risk & Rollback

- **Risk 1:** Existing `equity_history.jsonl` leaky snapshots no longer feed the chart — peak/drawdown panel still reads them, so peak may be understated until fresh snapshots accumulate post-fix. Acceptable (peak converges with new data).
- **Risk 2:** JS change depends on `CONFIG.initialBankroll` being rendered. If template lacks it, chart starts at 0. Task 3.3 explicitly adds it.
- **Rollback:** Revert Task 1 + 2 + 3 commits. Snapshot format unchanged, no data migration.
