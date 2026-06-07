# Zarar-kes Çıkışında Gerçekçi Piyasa Davranışı — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zarar-kes (PARTIAL_SL + tam stop-loss) çıkışlarını gerçek bir Polymarket piyasa emri gibi davrandır — gerçek alıcı varken yapay kayma tabanı engellemesin; çöken fiyat sıçrama korumasıyla donmasın.

**Architecture:** `walk_sell`'e market modu (kayma tabanı = 0) eklenir; kayıp-tarafı çıkışlar bu modu kullanır. `price_feed` sıçrama reddini canlı iki-taraflı kotasyonla doğrular. `min_order_usdc` ve gerçek-derinlik dolumu (hayalet icat yok) korunur — gerçekçi olan budur.

**Tech Stack:** Python 3.12, pytest. Katmanlar: domain (`paper_fill`), orchestration (`paper_executor`, `exit_processor`), infrastructure (`executor`, `price_feed`), config (`settings`).

**Spec:** [docs/superpowers/specs/2026-06-08-stop-loss-exit-realism-design.md](../specs/2026-06-08-stop-loss-exit-realism-design.md)

**ARCH_GUARD:** Her kod Task'ında Edit/Write öncesi `ARCHITECTURE_GUARD.md` okunup 8-madde self-check yazılacak.

---

## Dosya Haritası

| Dosya | Sorumluluk | Değişiklik |
|---|---|---|
| `src/domain/execution/paper_fill.py` | Saf defter yürüyüşü | `walk_sell`'e `market: bool` (kayma tabanı bypass) |
| `src/orchestration/paper_executor.py` | Paper fill koordinasyonu | `place_sell`/`partial_sell`'e `market` parametresi |
| `src/infrastructure/executor.py` | Mode dispatch | `partial_sell`/`exit_position` PAPER yolunda `market` aktar |
| `src/orchestration/exit_processor.py` | Çıkış yürütme | Kayıp-tarafı çıkışta `market=True` iste |
| `src/infrastructure/websocket/price_feed.py` | WS fiyat + sıçrama reddi | Sıçramayı iki-taraflı kotasyonla doğrula |
| `src/config/settings.py` | Config modelleri | `max_spike_corroboration_spread` alanı |
| `config.yaml` | Config değerleri | yeni alanın değeri |

---

## Task 1: `walk_sell` market modu (domain)

**Files:**
- Modify: `src/domain/execution/paper_fill.py:80-120`
- Test: `tests/unit/domain/execution/test_paper_fill.py`

- [ ] **Step 1: Failing test yaz**

`tests/unit/domain/execution/test_paper_fill.py` içine ekle:

```python
from src.domain.execution.paper_fill import walk_sell, FillStatus


def test_walk_sell_market_mode_fills_below_slippage_floor():
    # Referans 0.30, alıcı 0.26'da derin — %5 kayma normalde reddederdi.
    bids = [{"price": 0.26, "size": 6483}]  # Polymarket bids ASC; tek seviye
    res = walk_sell(bids=bids, target_price=0.30, shares=29.0,
                    max_slippage_pct=0.05, market=True)
    assert res.status == FillStatus.FILLED
    assert abs(res.filled_shares - 29.0) < 1e-9
    assert abs(res.weighted_avg_price - 0.26) < 1e-9


def test_walk_sell_non_market_still_rejects_below_slippage():
    # Regresyon: market=False eski davranış (reddet).
    bids = [{"price": 0.26, "size": 6483}]
    res = walk_sell(bids=bids, target_price=0.30, shares=29.0,
                    max_slippage_pct=0.05, market=False)
    assert res.status == FillStatus.REJECTED
    assert res.reason == "no_bids_above_slippage"


def test_walk_sell_market_mode_only_fills_real_depth():
    # Hayalet alıcı: 1¢'te 2 hisse → 29 istense de yalnız 2 dolar (gerçek derinlik).
    bids = [{"price": 0.01, "size": 2}]
    res = walk_sell(bids=bids, target_price=0.30, shares=29.0,
                    max_slippage_pct=0.05, market=True)
    assert res.status == FillStatus.PARTIAL_FILL
    assert abs(res.filled_shares - 2.0) < 1e-9
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/unit/domain/execution/test_paper_fill.py -k market -v`
Expected: FAIL — `walk_sell() got an unexpected keyword argument 'market'`

- [ ] **Step 3: `walk_sell`'e `market` ekle**

`src/domain/execution/paper_fill.py` `walk_sell` imzası ve `min_acceptable`:

```python
def walk_sell(
    bids: list[dict],
    target_price: float,
    shares: float,
    max_slippage_pct: float,
    market: bool = False,
) -> FillResult:
    """Walk bids descending, accumulate fill while price >= target * (1 - slippage).

    market=True → kayma tabanı yok (gerçek piyasa emri): tüm gerçek bid
    derinliği yürünür. Yalnız her seviyedeki gerçek `size` kadar doldurulur
    (hayalet icat yok). Returns FILLED / PARTIAL_FILL / REJECTED.
    """
    if shares <= 0:
        return FillResult(FillStatus.FILLED, 0.0, 0.0, 0.0, "")
    if not bids:
        return FillResult(FillStatus.REJECTED, 0.0, 0.0, 0.0, "empty_book")

    min_acceptable = 0.0 if market else target_price * (1.0 - max_slippage_pct)
```

(Geri kalan döngü aynı kalır.)

- [ ] **Step 4: Testlerin geçtiğini doğrula**

Run: `pytest tests/unit/domain/execution/test_paper_fill.py -v`
Expected: PASS (yeni 3 test + mevcut testler)

- [ ] **Step 5: Commit**

```bash
git add src/domain/execution/paper_fill.py tests/unit/domain/execution/test_paper_fill.py
git commit -m "feat(exit): walk_sell market modu — zarar-keste kayma tabanı bypass"
```

---

## Task 2: `paper_executor` market parametresi (orchestration)

**Files:**
- Modify: `src/orchestration/paper_executor.py:76-116`
- Test: `tests/integration/test_partial_sell_realism.py`

- [ ] **Step 1: Failing test yaz**

`tests/integration/test_partial_sell_realism.py` içine ekle (mevcut http_get/book stub desenini izle):

```python
def test_partial_sell_market_mode_fills_below_slippage(monkeypatch):
    from src.orchestration.paper_executor import PaperExecutor
    from src.config.settings import PaperConfig

    book = {"bids": [{"price": 0.26, "size": 6483}], "asks": []}
    ex = PaperExecutor(PaperConfig(), http_get=lambda *a, **k: book)
    monkeypatch.setattr(ex._book, "fetch", lambda token_id: book)

    res = ex.partial_sell(token_id="t", shares=29.0, target_price=0.30,
                          reason="partial_sl", market=True)
    assert res["status"] == "FILLED"
    assert abs(res["avg_price"] - 0.26) < 1e-9
```

- [ ] **Step 2: Başarısızlığı doğrula**

Run: `pytest tests/integration/test_partial_sell_realism.py -k market -v`
Expected: FAIL — `partial_sell() got an unexpected keyword argument 'market'`

- [ ] **Step 3: `place_sell` ve `partial_sell`'e `market` ekle**

`src/orchestration/paper_executor.py`:

```python
    def place_sell(self, token_id: str, target_price: float, shares: float,
                   market: bool = False) -> dict:
        target_price = round(target_price, 2)
        notional = shares * target_price
        if notional < self.cfg.min_order_usdc:
            return self._rejected(token_id, "SELL", target_price, notional, "below_min_order_usdc", {})
        book = self._book.fetch(token_id)
        strategy = choose_order_strategy(book, "SELL", target_price, notional)
        result = walk_sell(
            bids=book.get("bids", []),
            target_price=strategy["price"],
            shares=shares,
            max_slippage_pct=self.cfg.max_sell_slippage_pct,
            market=market,
        )
        return self._record_and_return(token_id, "SELL", strategy, target_price, notional, result, book, shares_in=shares)

    def partial_sell(self, token_id: str, shares: float, target_price: float,
                     reason: str = "scale_out", market: bool = False) -> dict:
        target_price = round(target_price, 2)
        notional = shares * target_price
        if notional < self.cfg.min_order_usdc:
            return self._rejected(token_id, "SELL", target_price, notional, "below_min_order_usdc", {})
        book = self._book.fetch(token_id)
        strategy = choose_order_strategy(book, "SELL", target_price, notional)
        result = walk_sell(
            bids=book.get("bids", []),
            target_price=strategy["price"],
            shares=shares,
            max_slippage_pct=self.cfg.max_sell_slippage_pct,
            market=market,
        )
        rec = self._record_and_return(
            token_id, "SELL", strategy, target_price, notional, result, book,
            shares_in=shares,
        )
        rec["reason"] = reason
        rec["kind"] = "partial_sell"
        return rec
```

- [ ] **Step 4: Geçtiğini doğrula**

Run: `pytest tests/integration/test_partial_sell_realism.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/paper_executor.py tests/integration/test_partial_sell_realism.py
git commit -m "feat(exit): paper_executor place_sell/partial_sell market parametresi"
```

---

## Task 3: `executor` dispatch market aktarımı (infrastructure)

**Files:**
- Modify: `src/infrastructure/executor.py:113-173`
- Test: `tests/unit/infrastructure/test_executor_market_exit.py` (yeni)

- [ ] **Step 1: Failing test yaz**

`tests/unit/infrastructure/test_executor_market_exit.py`:

```python
from types import SimpleNamespace
from src.infrastructure.executor import Executor, Mode


def _paper_executor(monkeypatch):
    ex = Executor.__new__(Executor)
    ex.mode = Mode.PAPER
    calls = {}
    def fake_partial_sell(token_id, shares, target_price, reason="scale_out", market=False):
        calls["partial"] = {"market": market}
        return {"status": "FILLED", "filled_shares": shares, "avg_price": target_price}
    def fake_place_sell(token_id, target_price, shares, market=False):
        calls["place"] = {"market": market}
        return {"status": "FILLED", "filled_shares": shares, "avg_price": target_price}
    ex._paper = SimpleNamespace(partial_sell=fake_partial_sell, place_sell=fake_place_sell)
    return ex, calls


def test_partial_sell_passes_market_flag(monkeypatch):
    ex, calls = _paper_executor(monkeypatch)
    ex.partial_sell("t", 10.0, 0.2, reason="partial_sl", market=True)
    assert calls["partial"]["market"] is True


def test_exit_position_loss_uses_market(monkeypatch):
    ex, calls = _paper_executor(monkeypatch)
    pos = SimpleNamespace(slug="x", shares=10.0, token_id="t", bid_price=0.05, current_price=0.05)
    ex.exit_position(pos, reason="stop_loss", market=True)
    assert calls["place"]["market"] is True
```

- [ ] **Step 2: Başarısızlığı doğrula**

Run: `pytest tests/unit/infrastructure/test_executor_market_exit.py -v`
Expected: FAIL — `partial_sell()`/`exit_position()` `market` kabul etmiyor

- [ ] **Step 3: `executor.py`'ye `market` ekle**

`partial_sell` imzasına `market: bool = False` ekle; PAPER dalında aktar:

```python
    def partial_sell(self, token_id: str, shares: float, target_price: float,
                     reason: str = "scale_out", market: bool = False) -> dict:
```
PAPER dalı:
```python
        if self.mode == Mode.PAPER:
            assert self._paper is not None
            return self._paper.partial_sell(token_id, shares, target_price, reason=reason, market=market)
```

`exit_position` imzasına `market: bool = False` ekle; PAPER dalında place_sell'e aktar:

```python
    def exit_position(self, pos: Any, reason: str = "", market: bool = False) -> dict:
```
```python
        if self.mode == Mode.PAPER:
            assert self._paper is not None
            token_id = getattr(pos, "token_id", "")
            bid_price = getattr(pos, "bid_price", None) or getattr(pos, "current_price", 0) or 0
            res = self._paper.place_sell(token_id, target_price=float(bid_price), shares=float(shares), market=market)
            return {**res, "reason": reason}
```

- [ ] **Step 4: Geçtiğini doğrula**

Run: `pytest tests/unit/infrastructure/test_executor_market_exit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/executor.py tests/unit/infrastructure/test_executor_market_exit.py
git commit -m "feat(exit): executor partial_sell/exit_position market aktarımı (PAPER)"
```

---

## Task 4: `exit_processor` kayıp-tarafı çıkışta market iste (orchestration)

**Files:**
- Modify: `src/orchestration/exit_processor.py:177-200, 252-286`
- Test: `tests/unit/orchestration/test_exit_processor_market.py` (yeni)

**Loss-cut reason kümesi** (market modu uygulananlar): `STOP_LOSS`, `GRADUATED_SL`, `PARTIAL_SL`, `NEVER_IN_PROFIT`, `ULTRA_LOW_GUARD`, `HOLD_REVOKED`. `NEAR_RESOLVE` ve `SCALE_OUT` market modu KULLANMAZ (kâr/yüksek-fiyat tarafı; kayma kontrolü gerçekçi).

- [ ] **Step 1: Failing test yaz**

`tests/unit/orchestration/test_exit_processor_market.py`:

```python
from src.orchestration.exit_processor import _is_loss_cut
from src.models.enums import ExitReason


def test_loss_cut_reasons_true():
    for r in (ExitReason.STOP_LOSS, ExitReason.GRADUATED_SL, ExitReason.PARTIAL_SL,
              ExitReason.NEVER_IN_PROFIT, ExitReason.ULTRA_LOW_GUARD, ExitReason.HOLD_REVOKED):
        assert _is_loss_cut(r) is True


def test_non_loss_cut_reasons_false():
    for r in (ExitReason.NEAR_RESOLVE, ExitReason.SCALE_OUT):
        assert _is_loss_cut(r) is False
```

- [ ] **Step 2: Başarısızlığı doğrula**

Run: `pytest tests/unit/orchestration/test_exit_processor_market.py -v`
Expected: FAIL — `cannot import name '_is_loss_cut'`

- [ ] **Step 3: `_is_loss_cut` + çağrılara market geçir**

`src/orchestration/exit_processor.py` modül seviyesine ekle:

```python
_LOSS_CUT_REASONS = frozenset({
    ExitReason.STOP_LOSS, ExitReason.GRADUATED_SL, ExitReason.PARTIAL_SL,
    ExitReason.NEVER_IN_PROFIT, ExitReason.ULTRA_LOW_GUARD, ExitReason.HOLD_REVOKED,
})


def _is_loss_cut(reason: ExitReason) -> bool:
    return reason in _LOSS_CUT_REASONS
```

`_execute_exit` tam-çıkış dalı (`exit_position` çağrısı):

```python
        self.deps.executor.exit_position(
            pos, reason=signal.reason.value, market=_is_loss_cut(signal.reason),
        )
```

`_execute_partial_exit` içindeki `partial_sell` çağrısı:

```python
        order = self.deps.executor.partial_sell(
            token_id=pos.token_id,
            shares=intended_shares,
            target_price=pos.current_price,
            reason="scale_out",
            market=(signal.reason == ExitReason.PARTIAL_SL),
        )
```

- [ ] **Step 4: Geçtiğini doğrula**

Run: `pytest tests/unit/orchestration/test_exit_processor_market.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/exit_processor.py tests/unit/orchestration/test_exit_processor_market.py
git commit -m "feat(exit): kayıp-tarafı çıkışlar market modunda satar"
```

---

## Task 5: Sıçrama reddini iki-taraflı kotasyonla doğrula (infrastructure + config)

**Files:**
- Modify: `src/config/settings.py` (price_feed config'ine alan), `config.yaml` (price_feed bölümü)
- Modify: `src/infrastructure/websocket/price_feed.py:96-100, 311-329`
- Test: `tests/unit/infrastructure/test_price_feed_spike.py` (yeni)

**Kural:** `|Δ| > max_spike_pct` bir hareket, yeni en-iyi-alıcı (`bid_price`) ile **iki taraflı tutarlıysa** kabul edilir: `bid_price > 0` ve `(yes_price - bid_price) <= max_spike_corroboration_spread`. Aksi halde (tek taraflı bayat baskı — KBO) reddedilir. `bid_price` yoksa (0) → eski davranış (reddet).

- [ ] **Step 1: Config alanı + failing test**

`tests/unit/infrastructure/test_price_feed_spike.py`:

```python
from src.infrastructure.websocket.price_feed import PriceFeed


def _feed():
    pf = PriceFeed(on_price_update=None, max_spike_pct=0.50,
                   max_spike_corroboration_spread=0.10)
    return pf


def test_corroborated_collapse_accepted():
    pf = _feed()
    pf._update_price("t", yes_price=0.48, bid_price=0.47)   # baseline
    # Gerçek çöküş: ask ve bid birlikte ~0'a (tutarlı iki-taraflı kota)
    pf._update_price("t", yes_price=0.02, bid_price=0.01)
    assert abs(pf._prices["t"].yes_price - 0.02) < 1e-9   # kabul edildi


def test_one_sided_stale_spike_rejected():
    pf = _feed()
    pf._update_price("t", yes_price=0.61, bid_price=0.60)  # baseline
    # KBO: ask 0.97'ye fırladı ama bid hâlâ 0.60 (geniş spread → sahte)
    pf._update_price("t", yes_price=0.97, bid_price=0.60)
    assert abs(pf._prices["t"].yes_price - 0.61) < 1e-9   # reddedildi, eski kaldı
```

- [ ] **Step 2: Başarısızlığı doğrula**

Run: `pytest tests/unit/infrastructure/test_price_feed_spike.py -v`
Expected: FAIL — `PriceFeed.__init__() got an unexpected keyword argument 'max_spike_corroboration_spread'`

- [ ] **Step 3: Config alanı ekle**

`src/config/settings.py` price_feed config sınıfına (max_spread_for_near_resolve'ün yanına):

```python
    max_spike_corroboration_spread: float = 0.10  # iki-taraflı kota teyidi için max spread
```

`config.yaml` `price_feed:` bölümüne:

```yaml
  max_spike_corroboration_spread: 0.10   # sıçrama gerçek mi: ask-bid spread bu altındaysa kabul
```

- [ ] **Step 4: `price_feed.py`'yi güncelle**

Constructor:

```python
    def __init__(
        self,
        on_price_update: PriceCallback | None = None,
        max_spike_pct: float = 0.50,
        max_spike_corroboration_spread: float = 0.10,
    ) -> None:
        self._callback = on_price_update
        self._max_spike_pct = max_spike_pct
        self._max_spike_corroboration_spread = max_spike_corroboration_spread
```

`_update_price` sıçrama bloğu:

```python
        if prev is not None and prev.yes_price > 0:
            pct_change = abs(yes_price - prev.yes_price) / prev.yes_price
            if pct_change > self._max_spike_pct:
                corroborated = (
                    bid_price > 0
                    and (yes_price - bid_price) <= self._max_spike_corroboration_spread
                )
                if not corroborated:
                    self.stats["spikes_rejected"] += 1
                    logger.warning(
                        "price_feed: spike reject %s: %.3f -> %.3f (%.0f%% change > %.0f%% limit, bid=%.3f)",
                        token_id[:16], prev.yes_price, yes_price,
                        pct_change * 100, self._max_spike_pct * 100, bid_price,
                    )
                    return
```

Çağıran yer (PriceFeed örnekleme — factory/bootstrap) `max_spike_corroboration_spread=config.price_feed.max_spike_corroboration_spread` ile geçirilecek (grep: `PriceFeed(` kullanımları).

- [ ] **Step 5: Geçtiğini doğrula**

Run: `pytest tests/unit/infrastructure/test_price_feed_spike.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/config/settings.py config.yaml src/infrastructure/websocket/price_feed.py tests/unit/infrastructure/test_price_feed_spike.py
git commit -m "feat(price_feed): sıçramayı iki-taraflı kotasyonla doğrula (çöküşü dondurma)"
```

---

## Task 6: Tam regresyon + DECISIONS güncelle

- [ ] **Step 1: Tüm test paketi**

Run: `pytest -q`
Expected: tümü PASS (mevcut + yeni). Kırılma varsa düzelt.

- [ ] **Step 2: PriceFeed instantiation grep**

Run: `grep -rn "PriceFeed(" src/`
Expected: tüm üretim çağrıları yeni config alanını geçiriyor (test dışında).

- [ ] **Step 3: DECISIONS.md güncelle**

`DECISIONS.md` ilgili exit bölümüne not: zarar-kes çıkışları market modunda (kayma tabanı yok, gerçek derinlik), sıçrama reddi iki-taraflı kota ile doğrulanır; `min_order_usdc` gerçekçi sınır olarak korunur. Spec referansı ekle.

- [ ] **Step 4: Commit + spec/plan temizliği**

```bash
git add DECISIONS.md
git commit -m "docs(decisions): zarar-kes market exit + sıçrama teyidi kararı"
```

Plan tamamlanınca: spec `docs/superpowers/specs/` tarihsel kayıt olarak kalır; PLAN.md kullanılmadı (bu plan dosyası kayıttır).

---

## Self-Review (yazar kontrolü — tamamlandı)
- **Spec kapsamı:** Parça A → Task 1-4; Parça B → Task 5; min_order/derinlik korunması → Task 1 testleriyle doğrulanır. ✓
- **Placeholder:** yok; tüm adımlar somut kod içerir. ✓
- **Tip tutarlılığı:** `market: bool` tüm katmanlarda aynı; `_is_loss_cut(reason)` tek tanım. ✓
- **Kapsam dışı:** LIVE executor, kademe eşikleri, reload/reboot — dokunulmaz. ✓
