# BUY_NO Token-Native PnL — 6 Lokasyon DRY-Uyumlu Fix

> **For agentic workers:** Use superpowers:executing-plans or single subagent. Bu plan önceki Position.current_value fix'inden kalan 5 ek lokasyonu kapsar + DRY ihlali olmadan ortak helper kullanır.

**Goal:** BUY_NO pozisyonları için yanlış "shares × (1 − current_price)" hesabını 6 lokasyondan tamamen kaldır. Aynı formülün copy-paste edilmesi yerine Position computed_field'ları ve ortak helper fonksiyonu kullanılarak DRY ilkesi korunur.

**Architecture:**
- **agent.py (Orchestration, Position objesi var)**: `pos.unrealized_pnl_usdc` computed property kullan — tek satır.
- **cli.py (Presentation, dict)**: computed.py'nin `_position_unrealized` helper'ını import et — DRY koruma.
- **computed.py (Presentation, dict)**: `_position_unrealized` helper'ından direction-eff mantığı kaldır, token-native formüle çevir (tek yer, tek doğru formül).
- **feed.js (Presentation/frontend, JS ayrı dil)**: inline formülü direction-agnostic hale getir — JS Python import edemez, tek kopya kaçınılmaz.

**Tech Stack:** Python (Pydantic computed_field), JavaScript.

**Mimari self-check (plan yazımı için):**
- ✓ DRY: Fix 6 lokasyonu 1 computed property + 1 helper + 1 JS inline'a düşürüyor (toplam 3 mantıksal kopya, 6'dan iyi; JS kaçınılmaz).
- ✓ <400 satır: Dosyalar değişmez boyut, biri biraz azalır.
- ✓ Domain I/O yok: Sadece Orchestration + Presentation düzenlemesi.
- ✓ Katman düzeni: Presentation katmanı kendi içinde helper paylaşıyor (aynı katman → serbest).
- ✓ Magic number yok: Formüllerde sabit yok.
- ✓ utils/helpers/misc yok: Mevcut `computed.py`'yi kullanıyor.
- ✓ Sessiz hata yok: Pure hesaplama, try/except yok.
- ✓ P(YES) anchor: `anchor_probability` dokunulmuyor, sadece dolar değeri hesabı düzeltiliyor.

---

## File Structure

**Değişen:**
- `src/orchestration/agent.py` — 3 lokasyon (scale-out, full exit, equity snapshot)
- `src/presentation/dashboard/computed.py` — `_position_unrealized` helper düzeltiliyor
- `src/presentation/cli.py` — computed.py helper import, kullan
- `src/presentation/dashboard/static/js/feed.js` — inline formül düzelt
- `tests/unit/orchestration/test_agent.py` VEYA yeni test dosyası — BUY_NO exit senaryoları
- `tests/unit/presentation/test_computed.py` (varsa) — direction-agnostic test

**Değişmeyen:** Position model, TDD, PRD, ARCH_GUARD, CLAUDE, config.

---

## Task 1: agent.py scale-out (3 satır değişim → 1 satır)

**Files:** `src/orchestration/agent.py`

**Mimari self-check (kod edit öncesi):**
- ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni (Orchestration içi), ✓ magic number yok, ✓ utils/helpers yok, ✓ sessiz hata yok, ✓ P(YES) anchor.

- [ ] **Step 1: Scale-out proceeds hesabını computed property'den al**

Edit:

`old_string`:
```
        if signal.partial:
            # Scale-out: pozisyon kalır, tier güncellenir, realized PnL kaydedilir
            shares_to_sell = pos.shares * signal.sell_pct
            # Dry_run'da executor sahte response döner; realized PnL yaklaşık hesaplanır
            eff = pos.current_price if pos.direction == "BUY_YES" else (1 - pos.current_price)
            proceeds = shares_to_sell * eff
            cost_basis = pos.size_usdc * signal.sell_pct
            realized = proceeds - cost_basis
```

`new_string`:
```
        if signal.partial:
            # Scale-out: pozisyon kalır, tier güncellenir, realized PnL kaydedilir.
            # Realized = unrealized_pnl × sell_pct (Position computed property, token-native).
            shares_to_sell = pos.shares * signal.sell_pct
            realized = pos.unrealized_pnl_usdc * signal.sell_pct
            cost_basis = pos.size_usdc * signal.sell_pct
```

Not: `proceeds` değişkeni artık kullanılmıyor — bilinçli çıkarıldı, realized tek adımda hesaplanıyor. Eğer `proceeds` aşağıda kullanılıyorsa (scale-out log'u, vb.), kodu korumak için:
```python
proceeds = realized + cost_basis
```
ekle (matematiksel eşdeğer).

- [ ] **Step 2: Devam eden satırları kontrol et**

`pos.shares -= shares_to_sell`, `pos.size_usdc *= (1 - signal.sell_pct)` gibi satırlar DOKUNULMAZ. Dokunursak DRY/state bozulur.

---

## Task 2: agent.py full exit realized

**Files:** `src/orchestration/agent.py`

**Mimari self-check (kod edit öncesi):**
- ✓ DRY (unrealized_pnl_usdc computed property kullanımı), ✓ diğer hepsi uygun.

- [ ] **Step 1: Full exit realized hesabını computed property'den al**

Edit:

`old_string`:
```
        # Full exit
        self.deps.executor.exit_position(pos, reason=signal.reason.value)

        eff = pos.current_price if pos.direction == "BUY_YES" else (1 - pos.current_price)
        proceeds = pos.shares * eff
        realized = proceeds - pos.size_usdc
```

`new_string`:
```
        # Full exit
        self.deps.executor.exit_position(pos, reason=signal.reason.value)

        # Realized = unrealized_pnl (Position computed property, token-native).
        realized = pos.unrealized_pnl_usdc
```

`proceeds` alt satırlarda kullanılıyorsa (log ya da callback), ekle:
```python
proceeds = realized + pos.size_usdc
```

---

## Task 3: agent.py equity snapshot

**Files:** `src/orchestration/agent.py`

**Mimari self-check (kod edit öncesi):**
- ✓ DRY (computed property kullanımı), ✓ diğerleri.
- Not: `effective_price` import'u başka yerde kullanılıyor mu kontrol et; kullanılmıyorsa çıkar.

- [ ] **Step 1: Equity snapshot unrealized toplamı**

Edit:

`old_string`:
```
        for pos in portfolio.positions.values():
            invested += pos.size_usdc
            eff = effective_price(pos.current_price, pos.direction)
            unrealized += (pos.shares * eff) - pos.size_usdc
```

`new_string`:
```
        for pos in portfolio.positions.values():
            invested += pos.size_usdc
            unrealized += pos.unrealized_pnl_usdc
```

- [ ] **Step 2: effective_price import kontrolü**

Run: `grep -n "effective_price" src/orchestration/agent.py`
Eğer **sadece import satırında** varsa (bu Edit sonrası agent.py'nin başka yerinde kullanılmıyorsa) import'u kaldır. Aksi durumda dokunma.

---

## Task 4: computed.py `_position_unrealized` — direction-agnostic

**Files:** `src/presentation/dashboard/computed.py`

**Mimari self-check (kod edit öncesi):**
- ✓ DRY (tek helper kalıyor, cli.py bunu kullanacak), ✓ diğerleri.
- Not: `_eff_price` fonksiyonu kalıyor mu? Başka yerde kullanılıyorsa kalır; sadece bu helper'da kullanılıyorsa kaldır.

- [ ] **Step 1: Helper düzelt**

Edit:

`old_string`:
```
# ── Position helpers (pure) ──

def _eff_price(current: float, direction: str) -> float:
    return (1.0 - current) if direction == "BUY_NO" else current


def _position_unrealized(pos: dict[str, Any]) -> float:
    shares = float(pos.get("shares", 0.0))
    size = float(pos.get("size_usdc", 0.0))
    eff = _eff_price(float(pos.get("current_price", 0.0)), pos.get("direction", ""))
    return shares * eff - size
```

`new_string`:
```
# ── Position helpers (pure) ──

def _position_unrealized(pos: dict[str, Any]) -> float:
    """Token-native PnL hesabı. shares × current_price − size_usdc.

    Direction-agnostic çünkü current_price zaten pozisyon token'ının fiyatıdır
    (BUY_YES → YES token price, BUY_NO → NO token price). Hiçbir yön çevrimi
    gerekmez. Eski `_eff_price(current, direction)` yanlış hesaplıyordu.
    """
    shares = float(pos.get("shares", 0.0))
    size = float(pos.get("size_usdc", 0.0))
    current_price = float(pos.get("current_price", 0.0))
    return shares * current_price - size
```

- [ ] **Step 2: `_eff_price` kullanımı başka yerde var mı**

Run: `grep -n "_eff_price" src/presentation/dashboard/computed.py`
Eğer başka yerde kullanılmıyorsa (bu Edit sonrası sadece silinen satırlarda vardı), bir şey yapma — fonksiyon zaten silindi. Eğer başka fonksiyonda hala kullanılıyorsa, o kullanımı da gözden geçir (muhtemelen aynı bug!).

---

## Task 5: cli.py — computed.py'nin helper'ını kullan (DRY)

**Files:** `src/presentation/cli.py`

**Mimari self-check (kod edit öncesi):**
- ✓ DRY (helper paylaşıyor), ✓ <400 satır, ✓ katman (Presentation içi), ✓ diğerleri.
- Katman ihlali kontrolü: cli.py Presentation, computed.py Presentation → aynı katman, import serbest.

- [ ] **Step 1: Import ekle**

Edit:

`old_string`:
```
from src.config.settings import load_config
from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
```

`new_string`:
```
from src.config.settings import load_config
from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.presentation.dashboard.computed import _position_unrealized
```

- [ ] **Step 2: cmd_positions PnL hesabı**

Edit:

`old_string`:
```
    for pos in positions.values():
        shares = pos.get("shares", 0)
        size = pos.get("size_usdc", 0)
        current = pos.get("current_price", 0)
        direction = pos.get("direction", "BUY_YES")
        eff = (1 - current) if direction == "BUY_NO" else current
        pnl_pct = ((shares * eff - size) / size * 100) if size > 0 else 0
        print(f"{(pos.get('slug','') or '')[:33]:<35} "
              f"{direction:<8} {pos.get('confidence','B'):<5} "
              f"${pos.get('entry_price',0):>6.3f} ${current:>7.3f} "
              f"${size:>7.2f} {pnl_pct:>6.1f}%")
```

`new_string`:
```
    for pos in positions.values():
        size = pos.get("size_usdc", 0)
        current = pos.get("current_price", 0)
        direction = pos.get("direction", "BUY_YES")
        pnl = _position_unrealized(pos)
        pnl_pct = (pnl / size * 100) if size > 0 else 0
        print(f"{(pos.get('slug','') or '')[:33]:<35} "
              f"{direction:<8} {pos.get('confidence','B'):<5} "
              f"${pos.get('entry_price',0):>6.3f} ${current:>7.3f} "
              f"${size:>7.2f} {pnl_pct:>6.1f}%")
```

Not: `shares` ve `eff` local variable'ları artık kullanılmıyor, kaldırıldı.

---

## Task 6: feed.js (JavaScript, inline fix)

**Files:** `src/presentation/dashboard/static/js/feed.js`

**Mimari self-check (kod edit öncesi):**
- ✓ JS ayrı dil, Python helper import edemez → inline kaçınılmaz.
- ✓ Direction kontrolü kaldırılır, token-native formül kullanılır.
- ✓ <400 satır, diğerleri N/A.

- [ ] **Step 1: Inline formül düzelt**

Edit:

`old_string`:
```
    _activeCard(p) {
      const icon = ICONS.getSportEmoji(p.sport_tag, p.slug);
      const dir = p.direction === "BUY_YES" ? "YES" : "NO";
      const dirCls = p.direction === "BUY_YES" ? "badge-yes" : "badge-no";
      const eff = p.direction === "BUY_NO" ? 1 - p.current_price : p.current_price;
      const pnl = p.shares * eff - p.size_usdc;
```

`new_string`:
```
    _activeCard(p) {
      const icon = ICONS.getSportEmoji(p.sport_tag, p.slug);
      const dir = p.direction === "BUY_YES" ? "YES" : "NO";
      const dirCls = p.direction === "BUY_YES" ? "badge-yes" : "badge-no";
      // Token-native PnL: shares × current_price − size_usdc. Direction-agnostic
      // çünkü current_price pozisyonun token'ına aittir (YES/NO).
      const pnl = p.shares * p.current_price - p.size_usdc;
```

- [ ] **Step 2: feed.js'de başka `1 - p.current_price` kalmış mı**

Run: `grep -n "1 - p.current_price\|1-p.current_price" src/presentation/dashboard/static/js/`
Eğer başka yer varsa → orada da aynı Edit yapılır.

---

## Task 7: Testler — BUY_NO exit ve dashboard

**Files:**
- `tests/unit/orchestration/test_agent.py` (BUY_NO exit testleri)
- Gerekirse `tests/unit/presentation/test_computed.py` (yeni dosya veya mevcut)

**Mimari self-check (kod edit öncesi):**
- ✓ Test olmadan merge yasak (Kural 11), yeni davranış için test.
- ✓ Diğerleri uygun.

- [ ] **Step 1: BUY_NO full exit realized testi** (tests/unit/orchestration/test_agent.py)

Mevcut test dosyasına test ekle. Detaylar:
- BUY_NO pozisyon: entry NO=0.40, current NO=0.60 (NO güçlendi, profit)
- shares = 100, size = $40
- Beklenen realized = unrealized_pnl = 100 × 0.60 − 40 = +$20
- Full exit tetikle, `realized` değerinin +$20 olduğunu assert et

Eğer agent test pattern'i karmaşıksa (executor mock, portfolio mock gerekiyorsa), şöyle bir minimal test ekle:
```python
def test_buy_no_full_exit_realized_uses_unrealized_pnl():
    """BUY_NO pozisyonu full exit'te realized = shares × current_price − size."""
    # Position oluştur - BUY_NO, entry 0.40, current 0.60
    # Mocked agent, executor.exit_position no-op, portfolio.remove_position mock
    # Agent._execute_exit çağır (full exit signal)
    # portfolio.remove_position'ın realized_pnl_usdc=+20.0 ile çağrıldığını assert et
```

- [ ] **Step 2: BUY_NO scale-out realized testi**

Aynı desen, ama partial=True signal, sell_pct=0.40.
- Beklenen realized = (100 × 0.60 − 40) × 0.40 = +$8
- Assert scale_out_realized_usdc veya `apply_partial_exit` arg'ı

- [ ] **Step 3: computed.py direction-agnostic test** (yeni dosya gerekirse)

Run: `ls tests/unit/presentation/` — dashboard/computed.py için test var mı

Yoksa yeni dosya oluşturma (mimari kural: test olmadan merge yasak). İçinde:
```python
def test_position_unrealized_buy_yes():
    pos = {"shares": 100.0, "current_price": 0.50, "size_usdc": 40.0, "direction": "BUY_YES"}
    assert _position_unrealized(pos) == 10.0  # 50 - 40

def test_position_unrealized_buy_no():
    pos = {"shares": 100.0, "current_price": 0.30, "size_usdc": 40.0, "direction": "BUY_NO"}
    # Token-native: 100*0.30 - 40 = -10 (NO düştü, loss)
    # Eski bug'lı formül: 100*(1-0.30) - 40 = +30 (yanlış)
    assert _position_unrealized(pos) == -10.0


def test_position_unrealized_zero_at_entry():
    pos = {"shares": 100.0, "current_price": 0.40, "size_usdc": 40.0, "direction": "BUY_NO"}
    assert _position_unrealized(pos) == 0.0
```

---

## Task 8: Doğrulama

- [ ] **Step 1: pytest tüm suite**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m pytest -q`
Beklenen: 601 + yeni testler ≈ **605+ passed**. Sayı sapmalı → incele.

- [ ] **Step 2: Eski bug pattern'i tamamen gitti mi**

Run: `grep -rn "1 - .*current_price\|eff = pos.current_price if" src/`
Beklenen: feed.js referansı YOK, Python dosyalarında eski pattern yok. Sadece effective_price fonksiyonun kendisi (SL/FAV threshold'ları için) kalabilir.

- [ ] **Step 3: DRY spot-check**

Run: `grep -rn "shares \* pos.current_price\|pos.shares \* current_price" src/`
Beklenen: agent.py'da KALMIYOR (computed property kullanıyor). Sadece feed.js'de inline var (JS ayrı).

- [ ] **Step 4: effective_price KULLANIMI SL/FAV için korundu mu**

Run: `grep -rn "effective_price" src/`
Beklenen: stop_loss.py, graduated_sl.py, monitor.py, favored.py, near_resolve.py, a_conf_hold.py'da hala kullanılıyor (bunlar threshold-probability karşılaştırmaları, doğru kullanım). Position.py'da fonksiyon tanımı durmakta (public API korundu).

---

## Task 9: Final rapor

- [ ] Kullanıcıya:
  - Değişen dosyalar (6): agent.py (3 yer), computed.py, cli.py, feed.js
  - Eklenen test sayısı + pytest sonucu
  - Bug pattern taraması: "şimdi yok"
  - effective_price SL/FAV yerlerinde korundu: "evet"
  - DRY durumu: computed property + shared helper + JS inline (kaçınılmaz tek kopya)
  - Mimari uyum: ✓ 8 self-check her Edit öncesi yapıldı

---

## Self-Review

**Kapsam tam:** 6 lokasyonun hepsi kapsanıyor. Testler BUY_NO exit senaryolarını kapsıyor.

**Placeholder yok:** Tüm Edit'ler tam old_string/new_string. Test içeriği örneklerle belirtildi.

**Mimari uyum:** Her Task'ta self-check satırı var. Hook bu satır yazılmazsa uyarır. Kullanıcı self-check yazılmazsa "nerde?" diyebilir.

**Risk:**
- agent.py'daki `proceeds` değişkeni alt satırlarda kullanılıyorsa log eksik kalır. Edit'lerde `proceeds = realized + cost_basis` fallback mevcut.
- feed.js başka yerlerde aynı bug varsa Task 6 Step 2 yakalar.
- Test dosyası yoksa yeni dosya oluşturmak gerek (Task 7 Step 3).
