# BUY_NO Exit Semantic Fix — Design Spec

**Tarih:** 2026-04-15
**Kapsam:** Exit modüllerinin BUY_NO pozisyonlarda yanlış karar vermesine sebep olan çift-flip bug'ını düzelt. Dashboard görünümü değişmez (zaten doğru); bot exit kararları artık gerçek dünya PnL'i ile tutarlı olur.

**Kapsam dışı:** Yeni exit kuralı, yeni config anahtarı, Position model rename, effective_price() fonksiyonunu silme.

---

## Problem

### Kanıt

Senin tennis pozisyonun (BUY_NO, Porsche Tennis):
- entry_price = **0.82** (NO token fiyatı; agent `market.no_price`'dan set eder)
- current_price = **0.97** (WS NO token ask'ı; agent `pos.token_id = no_token_id`'ye subscribe olur)
- Dashboard görünümü: Entry 82¢ / Now 97¢ / **+$9.15 / +18.3%** ✓ (doğru — `shares × current_price - size_usdc`)
- Bot'un `near_resolve` kararı: `effective_price(0.97, "BUY_NO")` = 1 − 0.97 = **0.03** → 0.03 < 0.94 → **exit tetiklenmiyor** ❌

### Kök sebep

`effective_price(yes_price, direction)` fonksiyonu **yes-side input** bekler. BUY_NO için 1 − yes döndürür → owned side'ı verir.

`pos.current_price` ve `pos.entry_price` **ZATEN token-native** (owned side):
- BUY_YES pozisyonu: current_price = YES token fiyatı
- BUY_NO pozisyonu: current_price = NO token fiyatı

`effective_price(pos.current_price, direction)` çağrısı BUY_NO için:
- Input'u yes_price SANIYOR (yanlış varsayım)
- 1 − NO = YES döndürüyor → **yanlış side**

### Etkilenen dosyalar

```
src/strategy/exit/near_resolve.py:28    eff_current = effective_price(pos.current_price, pos.direction)
src/strategy/exit/a_conf_hold.py:28,45  eff_entry + eff_current
src/strategy/exit/favored.py:30,44      eff = effective_price(pos.current_price, ...)
src/strategy/exit/monitor.py:73-74,87-88,107  eff_entry/eff_current çeşitli
```

BUY_YES pozisyonları etkilenmez (effective_price pass-through olduğu için).

---

## Design

### Kural (single source of truth)

**`effective_price(price, direction)` YALNIZCA market-side YES price input için kullanılır.**

Meşru kullanım: `gate.py:142` — `signal.market_price` (MarketData.yes_price) → owned side'a çevrim.

**Position field'ları (`current_price`, `entry_price`) zaten token-native = effective → direkt kullanılır.**

### Değişiklikler

**1. Exit modüllerinde `effective_price(pos.X, direction)` → `pos.X`:**

| Dosya | Satır | Öncesi | Sonrası |
|---|---|---|---|
| `near_resolve.py` | 28 | `eff_current = effective_price(pos.current_price, pos.direction)` | `eff_current = pos.current_price` |
| `a_conf_hold.py` | 28 | `eff_entry = effective_price(pos.entry_price, pos.direction)` | `eff_entry = pos.entry_price` |
| `a_conf_hold.py` | 45 | `eff_current = effective_price(pos.current_price, pos.direction)` | `eff_current = pos.current_price` |
| `favored.py` | 30 | `eff = effective_price(pos.current_price, pos.direction)` | `eff = pos.current_price` |
| `favored.py` | 44 | aynı | aynı |
| `monitor.py` | 73-74, 87-88, 107 | 3 blokta eff_entry/eff_current | direct `pos.entry_price` / `pos.current_price` |

Import temizlik: `effective_price` kullanılmayan modüllerden kaldırılır (a_conf_hold, favored, near_resolve muhtemelen, monitor'dan kaldırılır). Dead import yok.

**2. Position model docstring** (`src/models/position.py`):

`current_price` ve `entry_price` field'larına Field docstring:
```python
current_price: float = Field(
    description=(
        "Owned token-native fiyat (BUY_YES → YES token ask, BUY_NO → NO token ask). "
        "`effective_price()` UYGULANMAZ — field zaten effective. Exit modüllerinde "
        "threshold karşılaştırmaları direkt bu field'la yapılır."
    ),
)
```

Aynısı `entry_price` için. `effective_price()` docstring'ine uyarı eklenir: "Input MUST be YES-side price. Position field'ları için ÇAĞIRMA."

**3. Regression testler:**

`tests/unit/strategy/exit/test_near_resolve.py` (varsa güncelle, yoksa oluştur):
```python
def test_buy_no_fires_at_owned_token_94cents():
    pos = _pos(direction="BUY_NO", current_price=0.94, match_start=now - 30min)
    assert near_resolve.check(pos) is True
```

`tests/unit/strategy/exit/test_monitor.py`:
```python
def test_buy_no_pnl_pct_token_native():
    # NO 0.82 → 0.97 = +18% gain (bot bet on NO side)
    pos = _pos(direction="BUY_NO", entry_price=0.82, current_price=0.97, ...)
    # monitor'un iç PnL% hesabı dashboard'la match etmeli
    assert monitor.pnl_pct(pos) == pytest.approx(0.183, rel=0.01)
```

`tests/unit/strategy/exit/test_favored.py`:
```python
def test_buy_no_no_spurious_demote():
    pos = _pos(direction="BUY_NO", current_price=0.80)  # NO winning
    assert favored.should_demote(pos) is False
```

**4. TDD güncelleme:**

TDD §6.11 (near-resolve) altında not ekle:
> `pos.current_price` token-native (owned side). Direkt `>= threshold_cents/100` karşılaştırılır. `effective_price()` bu context'te KULLANILMAZ.

Benzer not §6.8 (graduated SL / monitor) içine.

---

## ARCH_GUARD uyumluluk

- ✓ DRY: `effective_price()` tek anlama sahip (yes-side→owned conversion); Position fields tek semantiğe sahip (token-native)
- ✓ <400 satır: Exit modülleri küçük, değişim 10-20 satır
- ✓ Domain I/O yok: pure fonksiyonlar
- ✓ Katman düzeni: strategy/exit değişmez
- ✓ Magic number yok: threshold'lar config
- ✓ utils/helpers/misc yok: modüller anlamlı
- ✓ Sessiz hata yok: explicit guards korunur
- ✓ P(YES) anchor: `anchor_probability` still P(YES). Token-native current_price ayrı alan.

---

## Risk

**Runtime risk**: 10 açık BUY_NO pozisyon var (şu an). Fix deploy olunca bir sonraki light cycle tick'te:
- near_resolve: current_price ≥ 0.94 olan BUY_NO'lar exit edecek (beklenen)
- monitor pnl_pct: gerçek değer (eski hesap zaten kullanılmıyordu decision için, sadece log/eval'da)
- favored: BUY_NO winning pozisyonlar demote edilmez (eski: edilirdi yanlışlıkla)

dry_run olduğu için para kaybı yok. Simulation doğruluğu artar.

**Test risk**: Mevcut testler BUY_YES-only. Fix sonrası bunlar hâlâ geçer (BUY_YES semantikleri değişmedi). Yeni BUY_NO testleri eklenir → gelecek drift engellenir.

---

## Başarı kriteri

- Tüm mevcut testler yeşil (646+)
- 3 yeni BUY_NO regression test geçer
- Senin tennis pozisyonun (BUY_NO current=0.97) bir sonraki light cycle tick'te **near_resolve exit eder**
- Dashboard gösterimi değişmez (zaten doğruydu)
- Bot log'unda `EXIT reason=near_resolve_profit` satırı görülür
- ARCH_GUARD checklist tam

---

## Execution

Tek commit, atomik:
```
fix(exit): remove double-flip of effective_price for BUY_NO positions
```

4 dosya kod + 1 Position model docstring + 3 regression test + 1 TDD note.
