# BUY_NO PnL Formülü + Exposure Cap Fix

> **For agentic workers:** Use superpowers:executing-plans or single-subagent execution. Bu plan 2 kritik bug'ı düzeltir.

**Goal:** (1) BUY_NO pozisyonlarının giriş anında yanlış PnL göstermesini (anlık ±%50-150) düzelt. (2) Heavy cycle'da exposure cap bypass'ını (37 pozisyon, $1850 invested vs $500 cap) düzelt.

**Architecture:** 
- Position.current_value formülünden `effective_price` kaldır — token-native fiyat kullan (bu BUY_YES/NO için doğru dolar değeri verir).
- Agent._process_markets execution loop'una per-signal exposure re-check ekle.
- `effective_price` fonksiyonu SL/FAV threshold karşılaştırmaları için KALIYOR (orada doğru iş yapıyor — "bizim tarafımızın implied probability'si").

**Tech Stack:** Python, Pydantic, pytest.

**Kök neden analizi** (kısaca):
- BUY_NO'da `current_price = NO token ask` (WS), `entry_price = NO fill price`, `shares = size/no_price`. 
- Eski formül: `current_value = shares × (1 - current_price) = shares × yes_price`. Bu **NO token değerini YES token üzerinden hesaplar** — tamamen yanlış.
- Doğrusu: `current_value = shares × current_price` (kaç NO token var × NO token birim fiyatı).

---

## File Structure

**Değişen:**
- `src/models/position.py` — current_value formülü (1 satır + import temizlik)
- `src/orchestration/agent.py` — _process_markets'e exposure re-check + import
- `tests/unit/models/test_position.py` — BUY_NO PnL test'ini düzelt + yeni test
- `tests/unit/strategy/entry/test_gate.py` — kontrol (gate testi mevcut davranışa bağımlı mı?)

**Değişmeyen:** Config, TDD, PRD, CLAUDE, effective_price fonksiyonu (SL/FAV'da kalır), compute_stop_loss_pct, portfolio.manager, exposure.py.

---

## Task 1: Position.current_value formülü düzelt

**Files:**
- Modify: `src/models/position.py` (satır 78-86 civarı)

- [ ] **Step 1: Formülü değiştir**

Edit tool:

`old_string`:
```
    @computed_field
    @property
    def current_value(self) -> float:
        return self.shares * effective_price(self.current_price, self.direction)
```

`new_string`:
```
    @computed_field
    @property
    def current_value(self) -> float:
        # shares ve current_price AYNI token'a aittir (BUY_YES → YES token, BUY_NO → NO token).
        # Dolar değeri = miktar × birim fiyatı. effective_price SADECE SL/FAV eşikleri için kullanılır.
        return self.shares * self.current_price
```

- [ ] **Step 2: Kullanılmayan import'u kontrol et**

Run: `grep -n "effective_price" src/models/position.py`
Expected: `effective_price` fonksiyonu tanımı hala var (diğer modüller tarafından kullanılıyor — `from src.models.position import Position, effective_price`). current_value artık kullanmıyor ama fonksiyon public export olarak kalıyor. Dokunma.

- [ ] **Step 3: Spot-check (manuel hesap)**

Hypothetical BUY_NO position:
- direction=BUY_NO, entry_price=0.30 (NO fill price), current_price=0.30 (WS güncellemeden önce), size_usdc=50, shares=166.67 (50/0.30)

Yeni formülle:
- current_value = 166.67 × 0.30 = 50.00
- unrealized_pnl_usdc = 50 - 50 = 0 ✓
- unrealized_pnl_pct = 0 ✓

BUY_NO NO fiyatı 0.40'a çıkarsa (NO güçlendi, profit):
- current_value = 166.67 × 0.40 = 66.67
- unrealized_pnl_usdc = 16.67 (+33%)

BUY_NO NO fiyatı 0.20'ye düşerse (NO zayıfladı, loss):
- current_value = 166.67 × 0.20 = 33.33
- unrealized_pnl_usdc = -16.67 (-33%)

Tutarlı. BUY_YES için aynı şekilde (shares ve current_price aynı token).

---

## Task 2: test_position.py — BUY_NO PnL testini düzelt + yeni test ekle

**Files:**
- Modify: `tests/unit/models/test_position.py`

Mevcut test (`test_position_unrealized_pnl_pct_buy_no_profit`) yanlış davranışı test ediyor: BUY_NO, entry=0.40, current=0.30 (NO düştü) için +%75 profit bekliyor. Gerçekte bu LOSS olmalı.

- [ ] **Step 1: Yanlış testi doğru semantikle güncelle + yeni test ekle**

Edit tool:

`old_string`:
```
def test_position_unrealized_pnl_pct_buy_no_profit() -> None:
    p = _valid(direction="BUY_NO", entry_price=0.40, current_price=0.30, shares=100.0, size_usdc=40.0)
    # eff_current = 0.70 → current_value = 70, pnl = 30, pct = 0.75
    assert abs(p.unrealized_pnl_pct - 0.75) < 1e-9
```

`new_string`:
```
def test_position_unrealized_pnl_pct_buy_no_loss_when_no_price_drops() -> None:
    # BUY_NO: pozisyon NO token'dan oluşur. NO fiyatı düşerse LOSS.
    # entry NO=0.40, current NO=0.30, shares=100, size=$40
    # current_value = shares × current_price = 100 × 0.30 = 30
    # pnl = 30 - 40 = -10 = -25%
    p = _valid(direction="BUY_NO", entry_price=0.40, current_price=0.30, shares=100.0, size_usdc=40.0)
    assert abs(p.unrealized_pnl_pct - (-0.25)) < 1e-9


def test_position_unrealized_pnl_pct_buy_no_profit_when_no_price_rises() -> None:
    # BUY_NO: NO token fiyatı yükselirse PROFIT.
    # entry NO=0.40, current NO=0.60, shares=100, size=$40
    # current_value = 100 × 0.60 = 60, pnl = 20 = +50%
    p = _valid(direction="BUY_NO", entry_price=0.40, current_price=0.60, shares=100.0, size_usdc=40.0)
    assert abs(p.unrealized_pnl_pct - 0.50) < 1e-9


def test_position_unrealized_pnl_zero_at_entry_buy_no() -> None:
    # Entry anında (current_price == entry_price) PnL sıfır olmalı — direction'dan bağımsız.
    # BUY_NO regression: eski formülde aynı fiyatta current_value ≠ size_usdc idi.
    p = _valid(direction="BUY_NO", entry_price=0.30, current_price=0.30, shares=166.67, size_usdc=50.0)
    assert abs(p.unrealized_pnl_usdc) < 0.01  # ≈0 (float tolerans)


def test_position_unrealized_pnl_zero_at_entry_buy_yes() -> None:
    # Entry anında BUY_YES için de PnL sıfır (regresyon koruma).
    p = _valid(direction="BUY_YES", entry_price=0.70, current_price=0.70, shares=71.43, size_usdc=50.0)
    assert abs(p.unrealized_pnl_usdc) < 0.01
```

- [ ] **Step 2: Test dosyasında BUY_YES için var olan test'i de gözden geçir**

Run: `grep -B 2 -A 5 "test_position_unrealized_pnl_pct_buy_yes" tests/unit/models/test_position.py`

Eğer mevcut BUY_YES testi `current_value = 100 × 0.50 = 50` formülünü bekliyorsa, hala doğru (BUY_YES için yeni formül aynı sonucu verir). Dokunma.

- [ ] **Step 3: Test çalıştır**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m pytest tests/unit/models/test_position.py -v`

Expected: Tüm position testleri geçer (eski bozuk test yerine 4 yeni test).

---

## Task 3: agent.py — _process_markets'e exposure re-check

**Files:**
- Modify: `src/orchestration/agent.py`

- [ ] **Step 1: Import ekle**

Edit tool:

`old_string`:
```
from src.domain.risk.cooldown import CooldownTracker
```

`new_string`:
```
from src.domain.portfolio.exposure import exceeds_exposure_limit
from src.domain.risk.cooldown import CooldownTracker
```

- [ ] **Step 2: _process_markets loop'una re-check ekle**

Edit tool — `_process_markets` metodunu değiştir:

`old_string`:
```
    def _process_markets(self, markets: list[MarketData]) -> None:
        """Gate'ten geçir, onaylı signal'leri execute et."""
        results = self.deps.gate.run(markets)
        by_cid = {m.condition_id: m for m in markets}

        for r in results:
            market = by_cid.get(r.condition_id)
            if r.signal is None:
                if market is not None:
                    self._log_skip(market, r.skipped_reason)
                    if r.skipped_reason in ("max_positions_reached", "exposure_cap_reached"):
                        self.deps.scanner.push_eligible(market)
                continue

            if market is not None:
                self._execute_entry(market, r.signal)
```

`new_string`:
```
    def _process_markets(self, markets: list[MarketData]) -> None:
        """Gate'ten geçir, onaylı signal'leri execute et.

        Gate'de yapılan exposure check statik (300 market tek pass'te değerlendirilir,
        portfolio o an boş gibi görünür). Bu loop'ta execution öncesi TEKRAR kontrol
        edilir — çünkü her add_position sonrası portfolio değişiyor ve cap aşılabilir.
        """
        results = self.deps.gate.run(markets)
        by_cid = {m.condition_id: m for m in markets}
        max_exposure_pct = self.deps.gate.config.max_exposure_pct

        for r in results:
            market = by_cid.get(r.condition_id)
            if r.signal is None:
                if market is not None:
                    self._log_skip(market, r.skipped_reason)
                    if r.skipped_reason in ("max_positions_reached", "exposure_cap_reached"):
                        self.deps.scanner.push_eligible(market)
                continue

            if market is None:
                continue

            # Execution-time exposure re-check (gate-time statik check yetersiz)
            if exceeds_exposure_limit(
                self.deps.state.portfolio.positions,
                r.signal.size_usdc,
                self.deps.state.portfolio.bankroll,
                max_exposure_pct,
            ):
                self._log_skip(market, "exposure_cap_reached")
                self.deps.scanner.push_eligible(market)
                continue

            self._execute_entry(market, r.signal)
```

- [ ] **Step 3: Doğrula**

Run: `grep -n "exceeds_exposure_limit\|max_exposure_pct" src/orchestration/agent.py`
Expected: İki satır görünür (import + re-check kullanımı).

---

## Task 4: Agent testi çalıştır (regresyon kontrolü)

**Files:** (yok, sadece doğrulama)

- [ ] **Step 1: Agent testleri**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m pytest tests/unit/orchestration/test_agent.py -v`

Beklenen: Hepsi geçer. Eğer bir test eski `_process_markets` davranışına bağımlıysa (örn. tüm signal'lerin execute edildiğini assert ediyorsa), fail olabilir. O durumda test'i düzelt — yeni davranış daha doğrudur (exposure cap aşılınca skip yaparız).

- [ ] **Step 2: Exposure cap testi varsa**

Run: `grep -rn "exposure" tests/ | head -10`

Eğer exposure ile ilgili test varsa çalıştır ve geçtiğini doğrula.

---

## Task 5: Tüm suite

- [ ] **Step 1: Tüm testler**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m pytest -q`

Beklenen: 
- Task 2'de 4 yeni test eklendi, 1 silindi → net +3 test.
- Başlangıç 598 → beklenen 601 passed.

Eğer başka yerde regresyon varsa (örn. test_scanner, test_gate, test_monitor) raporla, durdur. Fix ile birlikte o test'leri de gözden geçirmek gerekebilir.

---

## Task 6: Final rapor

- [ ] Kullanıcıya:
  - Değişen dosyalar: position.py, agent.py, test_position.py
  - pytest: X/X
  - Düzeltilen buglar:
    - Position.current_value artık token-native — BUY_NO pozisyonları doğru PnL veriyor
    - Agent.exposure cap execution loop'unda re-check ediliyor — cap aşılmaz
  - Yan etki: Test suite'de 1 eski test (yanlış semantikli) silindi, 4 yeni test eklendi
  - Beklenen bot davranışı: BUY_NO pozisyonları açılır açılmaz SL/scale-out tetiklemez; 37 pozisyon açılması yerine ~10 pozisyonda (cap $500) durur.

---

## Self-Review

**Kapsam tam:** İki bug da fix'lendi. Test kapsamı yeterli (entry zero PnL hem BUY_YES hem BUY_NO için, hem profit hem loss).

**Placeholder yok:** Tüm Edit'ler tam `old_string`/`new_string` içerikli.

**Risk:**
- `test_position_unrealized_pnl_pct_buy_no_profit` (eski yanlış test) silinirken başka test dosyaları bu semantiğe bağlıysa kırılabilir. Task 5'te full pytest bunu yakalar.
- Scale-out ve SL davranışı BUY_NO için değişecek — bu iyi, çünkü bugün bot'u test ettiğimizde anormal davranış gözledik. Regresyon testi değil, fix doğrulaması.

**Rule-change protokolü uyumu:** Bu fix bir kural değişikliği sayılır (BUY_NO semantiği). PRD §2.1 "P(YES) anchor" invariant'ı etkilenmiyor (o anchor_probability ile ilgili, price değil). TDD §6.X kalibrasyonları etkilenmiyor. CLAUDE.md Dosya Rolleri tablosu etkilenmiyor. Sadece kod + test değişimi.
