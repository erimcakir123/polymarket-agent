# Doc System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLAUDE.md'ye rule-change protokolü + dosya rolleri tablosu ekle; TDD.md'den LAYER 2 bölümleri sil; TDD §6.X Python bloklarını değer tablosu + prose kurallarına dönüştür. Tüm iş tek planda bitsin, follow-up TODO bırakma.

**Architecture:** Tek doğruluk kaynağı. Kod = ne yapıyor. Doküman = formül + sayı + neden + invariant. §6.X Python kodları silinir; tüm sayılar/eşikler/kurallar tablo veya madde halinde korunur, tek bir değer bile kaybolmaz.

**Tech Stack:** Markdown + Edit tool surgical replacements. Kod dokunulmaz.

**Kritik kural:** Hiçbir sayı/eşik/kural kaybolamaz. Her §6.X transformasyonunda before/after değerleri karşılaştırmak zorunlu.

---

## Referanslar

- Spec: [docs/superpowers/specs/2026-04-14-doc-system-design.md](../specs/2026-04-14-doc-system-design.md)
- Hedef dosyalar: [CLAUDE.md](../../../CLAUDE.md), [TDD.md](../../../TDD.md)
- Not: Proje git repo değil — commit adımı yok, pytest + grep sanity check kullanılır.

---

## File Structure

**Değişen dosyalar:**
- `CLAUDE.md` — 3 bölüm değişir/eklenir (Task 1)
- `TDD.md` — LAYER 2 bölümleri silinir (Task 2-3), §6.X Python→prose (Task 5-21), İçindekiler yenilenir (Task 4)

**Değişmeyen dosyalar:** `PRD.md`, `ARCHITECTURE_GUARD.md`, `config.yaml`, `src/`, `tests/`, `TODO.md`

---

## Task 1: CLAUDE.md — Dosya Rolleri + Rule-Change Protokolü

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Stale §5 referansını düzelt**

Edit ile `CLAUDE.md:27`:

`old_string`:
```
- §0 ve §5 her zaman okunur.
```

`new_string`:
```
- §0 her zaman okunur (temel ilkeler). §6 (formüller/kalibrasyonlar) ve §7 (sport rules) göreve göre okunur.
```

- [ ] **Step 2: "Dosya Rolleri" bölümünü ekle**

Edit ile:

`old_string`:
```
---

## Okuma Kuralları

### Her kod görevinden ÖNCE (zorunlu)
1. **ARCHITECTURE_GUARD.md** — İhlal edilemez mimari kurallar
2. **PRD.md** — Ürün gereksinimleri ve demir kurallar
```

`new_string`:
```
---

## Dosya Rolleri (Tek Doğruluk Kaynağı)

Her bilgi türü TEK yerde yaşar. Tekrar yasak.

| Bilgi türü | Tek yeri |
|---|---|
| Fonksiyon imzası, import, dosya yolu, class yapısı | **Kod** (`src/`) |
| Yapısal invariantlar (5-katman, I/O yasağı, max satır) | **ARCHITECTURE_GUARD.md** |
| Ürün vizyonu + demir kurallar (bankroll, event-guard) | **PRD.md** |
| Formül, eşik, kalibrasyon sayıları, "neden" notları | **TDD.md** (§0 + §6 + §7 + §13) |
| Config değerleri | **config.yaml** |
| Testler | **tests/** |
| Ertelenmiş işler | **TODO.md** |
| İn-flight plan | **PLAN.md** |
| Tek kullanımlık spec | **SPEC.md** |

Aynı bilgi iki yerde görünüyorsa: DRIFT riski. Birini sil, doğru kaynaktan referans ver.

---

## Okuma Kuralları

### Her kod görevinden ÖNCE (zorunlu)
1. **ARCHITECTURE_GUARD.md** — İhlal edilemez mimari kurallar
2. **PRD.md** — Ürün gereksinimleri ve demir kurallar
```

- [ ] **Step 3: "Yeni Dosya Eklerken" TDD referansını düzelt**

Edit ile:

`old_string`:
```
### Yeni Dosya Eklerken
1. TDD.md'deki dizin yapısını kontrol et
2. Doğru katmana yerleştir
3. Eğer yapıda yoksa → PLAN.md'ye öner, onay bekle
4. `utils/`, `helpers/`, `misc/` dizinleri YASAK
```

`new_string`:
```
### Yeni Dosya Eklerken
1. `src/` altındaki mevcut dizin yapısını kontrol et (Glob ile)
2. Doğru katmana yerleştir (5-katman kuralı — ARCHITECTURE_GUARD)
3. Katman belirsizse → PLAN.md'ye öner, onay bekle
4. `utils/`, `helpers/`, `misc/` dizinleri YASAK
```

- [ ] **Step 4: "Kural Değişikliği Protokolü" bölümünü ekle**

Edit ile:

`old_string`:
```
---

## Eski Kod Referansı (Selective Migration)
```

`new_string`:
```
---

## Kural Değişikliği Protokolü

Kullanıcı iş diliyle bir kural değişikliği söylediğinde (örn. "daha seçici olalım", "bu spor kapsam dışı", "o eşiği artır"):

### Adım 1 — Somutlaştır
İş niyetini tek/birkaç somut parametreye çevir.
Örnek: "Daha seçici olalım" → `min_edge` artışı (0.06 → 0.08?)

### Adım 2 — Tek satırda doğrulat
Kullanıcıya tek soru:
> "min_edge 0.06 → 0.08 yapıyorum, doğru mu?"

Onay alınmadan Adım 3'e geçme.

### Adım 3 — Tüm geçtiği yerleri grep'le bul
Tipik lokasyonlar:
- `config.yaml`
- `src/` (default değerler, kullanım)
- `tests/` (eşik assertion'ları)
- `TDD.md` (formül/neden notu)
- `PRD.md` (demir kural değişikliğiyse)

`docs/superpowers/plans/*` tarihsel kayıttır — dokunma.

### Adım 4 — Değişim planını sun
Etkilenen dosya + satır listesi göster, onaylat.

### Adım 5 — Tek seferde uygula
Tüm dosyaları aynı turda güncelle. Yarım bırakma yasak.

### Adım 6 — Doğrulama
- `pytest -q` → tümü geçmeli
- Grep'te eski değer kalmamalı (alakasız eşleşmeler hariç)
- Rapor: değişen dosya sayısı, test sonucu, artık referans var mı

**Kritik kural:** Grep'te bir dosyada eski değer görülüyor ama Adım 4 listesinde yoktu → DURDUR, kullanıcıya sor.

---

## Eski Kod Referansı (Selective Migration)
```

- [ ] **Step 5: Sanity check**

Run: `pytest -q` → Expected: `595 passed`

Run: `grep -n "Dosya Rolleri" CLAUDE.md` → tablo başlığı görünür

Run: `grep -n "Kural Değişikliği Protokolü" CLAUDE.md` → bölüm başlığı görünür

Run: `grep -n "§5" CLAUDE.md` → boş (§5 referansı kalmadı)

Run: `grep -n "TDD.md'deki dizin" CLAUDE.md` → boş

---

## Task 2: TDD.md — §1-§5 bloğunu sil

**Files:**
- Modify: `TDD.md`

- [ ] **Step 1: Satır sınırlarını tespit et**

Run: `grep -n "^## " TDD.md | head -10`

Expected: §0 (satır 65), §1 (~77), §6 (~710) görünür.

- [ ] **Step 2: §1 ilk satırından §6 öncesine kadar oku**

Read `TDD.md` offset=77 limit=635 — §1'in ilk satırından §6'nın bitiminden hemen öncesine kadar.

- [ ] **Step 3: Bloğu Edit ile sil**

Edit'in `old_string`'ine §1'in tamamından §6 başlığının hemen öncesindeki `---` ve boş satırlar dahil ver. `new_string` olarak tek `---` satırı + boş satır:

`old_string`:
```
## 1. Mimari Genel Bakış
[... §1, §2, §3, §4, §5 tüm içeriği, Read çıktısından kopyala ...]
---

## 6. Kritik Algoritmalar
```

`new_string`:
```
---

## 6. Kritik Algoritmalar
```

- [ ] **Step 4: Doğrula**

Run: `grep -n "^## " TDD.md | head -10`
Expected: §0, §6, §7, ... sırayla; §1-§5 yok.

Run: `wc -l TDD.md`
Expected: ~900 civarı (başlangıç 1541, ~600 azalma).

Run: `pytest -q` → 595 passed

---

## Task 3: TDD.md — §8-§12 bloğunu sil

**Files:**
- Modify: `TDD.md`

- [ ] **Step 1: Sınırları tespit et**

Run: `grep -n "^## " TDD.md`

Expected: §8 (API), §9 (Konfig), §10 (Test), §11 (Uygulama), §12 (Başarı), §13 (Açık Noktalar) görünür.

- [ ] **Step 2: §8 başından §13 öncesine oku**

Read `TDD.md` offset=<§8 satırı> limit=<§13 satırı - §8 satırı>.

- [ ] **Step 3: Edit ile sil**

`old_string`:
```
## 8. API Entegrasyonları
[... §8, §9, §10, §11, §12 tüm içeriği ...]
---

## 13. Açık Noktalar (ilerisi için)
```

`new_string`:
```
---

## 13. Açık Noktalar (ilerisi için)
```

- [ ] **Step 4: Doğrula**

Run: `grep -n "^## " TDD.md`
Expected: §0, §6, §7, §13 — başka yok.

Run: `pytest -q` → 595 passed

---

## Task 4: TDD.md — İçindekiler tablosunu yeniden yaz

**Files:**
- Modify: `TDD.md` — satır 9-63 civarı (mevcut İçindekiler)

- [ ] **Step 1: Mevcut İçindekiler bölümünü oku**

Read `TDD.md` offset=8 limit=60.

- [ ] **Step 2: Edit ile değiştir**

`old_string`: Read çıktısından mevcut İçindekiler bölümünün TAMAMI (`## İçindekiler — ...`'dan "Güvenlik Ağı" son paragrafının bitişine kadar).

`new_string`:
```
## İçindekiler — Hangi Bölümü Ne Zaman Oku

> **Her zaman oku:** §0 (Temel İlkeler).
> **Göreve göre oku:** Aşağıdaki tabloya bak.
> **Şüphe varsa:** İlgili §6 ve §7 bölümlerinin tamamını oku.

Bu TDD **LAYER 1** içerir: formüller, kalibrasyon sayıları, iş kuralları, "neden" notları. Implementation detayları (dosya yolu, imza, dizin yapısı) için doğrudan kodu oku (`src/`).

| §     | Başlık                          | Ne zaman gerekli?                       |
|-------|---------------------------------|------------------------------------------|
| 0     | Temel İlkeler                   | **HER ZAMAN**                            |
| 6.1   | Bookmaker Probability           | Olasılık / edge işi                      |
| 6.2   | Confidence Grading              | Confidence işi                           |
| 6.3   | Edge Calculation                | Edge işi                                 |
| 6.4   | Consensus Entry (Case A/B)      | Entry gate                               |
| 6.5   | Position Sizing                 | Sizing                                   |
| 6.6   | Scale-Out (3-tier)              | Exit / scale                             |
| 6.7   | Flat Stop-Loss (9-Katman)       | Exit / SL                                |
| 6.8   | Graduated Stop-Loss             | Exit / SL                                |
| 6.9   | A-conf Hold-to-Resolve          | Exit (market flip)                       |
| 6.10  | Never-in-Profit Guard           | Exit                                     |
| 6.11  | Near-Resolve Profit Exit        | Exit                                     |
| 6.12  | Ultra-Low Guard                 | Exit                                     |
| 6.13  | FAV Promotion                   | Pozisyon yönetimi                        |
| 6.14  | Hold Revocation                 | Pozisyon yönetimi                        |
| 6.15  | Circuit Breaker                 | Risk yönetimi                            |
| 6.16  | Manipulation Guard              | Entry / risk                             |
| 6.17  | Liquidity Check                 | Entry                                    |
| 7     | Sport Rules                     | Spor-spesifik / sport tag işi            |
| 13    | Açık Noktalar                   | Referans                                 |

### Güvenlik Ağı

- **§6.x cluster:** Bir alt-bölüme bakacaksan, ilgili §6 komşularını gözden geçir (sizing ↔ confidence ↔ edge).
- **Kod okuma:** Dosya yolu, imza, import gibi sorular → doğrudan `src/` Grep + Read.
- **Mimari soru:** → ARCHITECTURE_GUARD.md.
- **Demir kural sorusu:** → PRD.md §2.
```

- [ ] **Step 3: Doğrula**

Run: `grep -n "İçindekiler" TDD.md` → tek başlık.
Run: `grep -c "^| 6\." TDD.md` → 17 (17 alt-bölüm listelenmiş).

---

## §6.X Transformasyon Protokolü (Task 5-21 için ortak)

Her §6.X task'ı şu protokolü uygular:

**Protokol:**
1. Hedef bölümü Read ile oku (başlık + Python + varsa prose + sonraki başlığın hemen öncesi).
2. Python code block'taki HER sayı, eşik, formül, koşul, default değeri liste halinde not et.
3. Aşağıdaki şablon ile prose + tablo versiyonu hazırla:
   - Başlık aynı kalır
   - Kısa amaç cümlesi
   - Kurallar/eşikler tablolar veya madde listeleri halinde
   - Veri dayanağı (veri notu varsa) KORUNUR
   - File path referansı VERME
4. Edit ile değiştir: `old_string` = mevcut Python bloğu + çevresi, `new_string` = prose versiyon.
5. Doğrula: every value from Step 2 must appear in the new prose.

**Kritik:** Hiçbir sayı atlanmamalı. Python'da `0.85` varsa prose'da da `0.85` olmalı. Aksi halde drift.

---

## Task 5: §6.1 Bookmaker Probability transformasyonu

**Files:**
- Modify: `TDD.md` — §6.1 bölümü

- [ ] **Step 1: Mevcut §6.1'i oku**

Read `TDD.md` offset=712 limit=33 (§6.1'den §6.2 öncesine).

- [ ] **Step 2: Değer listesi çıkar**

Beklenen değerler:
- Fallback probability = 0.5 (invalid girdi)
- Invalid koşul: `bookmaker_prob None veya ≤ 0` VEYA `num_bookmakers < 1`
- Clamp: [0.05, 0.95]
- Round: 4 decimal
- Dönüş nesnesi: BookmakerProbability (probability, confidence, bookmaker_prob, num_bookmakers, has_sharp)

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.1 Bookmaker Probability (Domain — Pure)

```python
def calculate_bookmaker_probability(
    bookmaker_prob: float | None,
    num_bookmakers: float,
    has_sharp: bool,
) -> BookmakerProbability:
    """
    Bookmaker konsensüsünden türetilen olasılık.
    
    num_bookmakers: toplam bookmaker ağırlığı (her bookie ağırlıklı).
    has_sharp: Pinnacle / Betfair Exchange var mı?
    """
    confidence = derive_confidence(num_bookmakers, has_sharp)
    
    if bookmaker_prob is None or bookmaker_prob <= 0 or num_bookmakers < 1:
        return BookmakerProbability(
            probability=0.5, confidence=confidence,
            bookmaker_prob=0.0, num_bookmakers=num_bookmakers,
            has_sharp=has_sharp,
        )
    
    clamped = max(0.05, min(0.95, bookmaker_prob))
    return BookmakerProbability(
        probability=round(clamped, 4),
        confidence=confidence,
        bookmaker_prob=round(bookmaker_prob, 4),
        num_bookmakers=num_bookmakers,
        has_sharp=has_sharp,
    )
```
```

`new_string`:
```
### 6.1 Bookmaker Probability

Bookmaker konsensüsünden olasılık türetir.

**Girdi:**
- `bookmaker_prob` — no-vig sonrası olasılık (0–1)
- `num_bookmakers` — toplam bookmaker ağırlığı (her bookie weighted)
- `has_sharp` — Pinnacle veya Betfair Exchange dahil mi

**Kurallar:**
- **Geçersiz girdi** → `probability = 0.5` fallback
  - Koşul: `bookmaker_prob` None VEYA ≤ 0, VEYA `num_bookmakers < 1`
- **Geçerli girdi** → `probability = clamp(bookmaker_prob, 0.05, 0.95)`
- Round: 4 decimal

**Dönüş:** `BookmakerProbability` (probability, confidence, bookmaker_prob ham, num_bookmakers, has_sharp)

Confidence türetmesi için → §6.2.
```

- [ ] **Step 4: Doğrula**

Run: `grep -n "0\.5\|0\.05\|0\.95" TDD.md` içinde §6.1 aralığında → 3 değer de mevcut.
Run: `grep -n "^### 6\." TDD.md` → §6.1 başlığı hala var.

---

## Task 6: §6.2 Confidence Grading transformasyonu

**Files:**
- Modify: `TDD.md` — §6.2 bölümü

- [ ] **Step 1: Mevcut §6.2'yi oku**

Read `TDD.md` — §6.2 aralığı (yaklaşık 16 satır).

- [ ] **Step 2: Değer listesi**
- A: `has_sharp = True` (Pinnacle / Betfair Exchange var)
- B: `bm_weight ≥ 5`, sharp yok
- C: `bm_weight` None VEYA < 5 → entry bloklanır

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.2 Confidence Grading (Domain — Pure)

```python
def derive_confidence(bm_weight: float | None, has_sharp: bool) -> str:
    """
    A = sharp book var (Pinnacle / Betfair Exchange)
    B = bookmaker weight ≥ 5, standart bookmaker
    C = yetersiz veri (< 5) → entry bloklanır
    """
    if bm_weight is None or bm_weight < 5:
        return "C"
    if has_sharp:
        return "A"
    return "B"
```
```

`new_string`:
```
### 6.2 Confidence Grading

Bookmaker ağırlığı + sharp var mı → A/B/C.

| Confidence | Koşul |
|---|---|
| **A** | `has_sharp = True` (Pinnacle veya Betfair Exchange var) ve `bm_weight ≥ 5` |
| **B** | `bm_weight ≥ 5`, sharp yok |
| **C** | `bm_weight` None VEYA < 5 — entry bloklanır |

Confidence, sizing multiplier'ına (→ §6.3) ve entry kararına direkt etki eder.
```

- [ ] **Step 4: Doğrula**

Tüm 3 confidence level + eşik `5` prose'da görünür.

---

## Task 7: §6.3 Edge Calculation transformasyonu

**Files:**
- Modify: `TDD.md` — §6.3

- [ ] **Step 1: Oku** — §6.3 aralığı (yaklaşık 36 satır).

- [ ] **Step 2: Değer listesi**
- Multipliers: A=1.25, B=1.00, C=blok
- `min_edge` default: 0.06
- `threshold = min_edge × multiplier`
- `raw = anchor_prob - market_yes_price`
- `effective_yes = raw - (spread + slippage)`
- `effective_no = |raw| - (spread + slippage)`
- Yön: raw > 0 → BUY_YES, raw < 0 → BUY_NO, aksi → HOLD
- Koşul: effective > threshold

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.3 Edge Calculation + Confidence Multiplier

```python
DEFAULT_CONFIDENCE_MULTIPLIERS = {
    "A": 1.25,   # Aşırı güven cezası (veride öğrenildi)
    "B": 1.00,   # Baz
    # C → entry bloklanır, sizing'e ulaşmaz
}

def calculate_edge(
    anchor_prob: float,
    market_yes_price: float,
    min_edge: float = 0.06,
    confidence: str = "B",
    spread: float = 0.0,
    slippage: float = 0.0,
) -> tuple[Direction, float]:
    """
    anchor_prob = P(YES). raw > 0 → BUY_YES, raw < 0 → BUY_NO.
    Effective edge = raw - costs.
    """
    multiplier = DEFAULT_CONFIDENCE_MULTIPLIERS.get(confidence, 1.0)
    threshold = min_edge * multiplier
    raw = anchor_prob - market_yes_price
    cost = spread + slippage

    effective_yes = raw - cost
    effective_no = abs(raw) - cost

    if raw > 0 and effective_yes > threshold:
        return Direction.BUY_YES, effective_yes
    elif raw < 0 and effective_no > threshold:
        return Direction.BUY_NO, effective_no
    return Direction.HOLD, 0.0
```
```

`new_string`:
```
### 6.3 Edge Calculation + Confidence Multiplier

Anchor probability (P(YES)) ile market YES fiyatı arasındaki fark; spread + slippage düşülür.

**Formül:**
- `raw = anchor_prob − market_yes_price`
- `effective = |raw| − (spread + slippage)`
- `threshold = min_edge × confidence_multiplier`

**Confidence multipliers (default):**
| Confidence | Multiplier | Not |
|---|---|---|
| A | 1.25 | Aşırı güven cezası (veride öğrenildi) |
| B | 1.00 | Baz |
| C | — | Entry bloklanır, sizing'e ulaşmaz |

**Default `min_edge`:** `0.06` (config.yaml `edge.min_edge`)

**Yön kararı:**
| Koşul | Sonuç |
|---|---|
| `raw > 0` AND `effective > threshold` | `BUY_YES`, edge = effective |
| `raw < 0` AND `effective > threshold` | `BUY_NO`, edge = effective |
| Aksi | `HOLD`, edge = 0 |
```

- [ ] **Step 4: Doğrula**

Tüm değerler prose'da: 1.25, 1.00, 0.06, raw formülü, threshold formülü, 3 yön kararı.

---

## Task 8: §6.4 Consensus Entry transformasyonu

**Files:**
- Modify: `TDD.md` — §6.4

- [ ] **Step 1: Oku**

- [ ] **Step 2: Değer listesi**
- `book_favors_yes = book_prob ≥ 0.50`
- `market_favors_yes = market.yes_price ≥ 0.50`
- `is_consensus = (book_favors_yes == market_favors_yes)`
- Consensus + book_favors_yes: direction=BUY_YES, entry_price = market.yes_price
- Consensus + !book_favors_yes: direction=BUY_NO, entry_price = 1 - market.yes_price
- Consensus edge = 0.99 - entry_price
- Non-consensus → §6.3 formülü

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.4 Consensus Entry (Special Case)

```python
# entry_gate.py (Strategy) — Case A vs Case B mantığı
book_favors_yes = book_prob >= 0.50
mkt_favors_yes = market.yes_price >= 0.50
is_consensus = book_favors_yes == mkt_favors_yes

if is_consensus:
    # Her ikisi de aynı favoriye işaret ediyor
    # Direction = favorite side
    # Edge = payout potential (99¢ - entry_price)
    if book_favors_yes:
        direction = BUY_YES
        entry_price = market.yes_price
    else:
        direction = BUY_NO
        entry_price = 1 - market.yes_price
    edge = 0.99 - entry_price
else:
    # Bookmaker ve market farklı favoriye işaret
    # Standart edge = |book_prob - market_price|
    # Yukarıdaki calculate_edge kullanılır
```
```

`new_string`:
```
### 6.4 Consensus Entry (Special Case)

Bookmaker ve market aynı favoriye işaret ettiğinde "payout edge" kullanılır (standart edge yerine).

**Consensus tespiti:**
- `book_favors_yes = book_prob ≥ 0.50`
- `market_favors_yes = market.yes_price ≥ 0.50`
- `is_consensus = (book_favors_yes == market_favors_yes)`

**Consensus varsa (Case A):**
| Book tarafı | Direction | Entry price |
|---|---|---|
| book_favors_yes = True | `BUY_YES` | `market.yes_price` |
| book_favors_yes = False | `BUY_NO` | `1 − market.yes_price` |

- Edge = `0.99 − entry_price` (Polymarket payout cap)

**Consensus yoksa (Case B):** standart edge hesabı (§6.3) kullanılır.
```

- [ ] **Step 4: Doğrula**

Değerler prose'da: 0.50, 0.99, 2 direction + entry kombinasyonu.

---

## Task 9: §6.5 Position Sizing transformasyonu

**Files:**
- Modify: `TDD.md` — §6.5

- [ ] **Step 1: Oku**

- [ ] **Step 2: Değer listesi**
- CONF_BET_PCT: A=0.05, B=0.04, C=0 (girmez)
- Heavy favorite (market_price ≥ 0.90) → bet_pct × 1.50
- Lossy reentry → bet_pct × 0.80
- Caps: max_bet_usdc = $75, max_bet_pct = %5 bankroll, bankroll üst sınır
- Polymarket min: $5 (reddet altında)

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.5 Position Sizing

```python
CONF_BET_PCT = {
    "A": 0.05,   # %5 bankroll
    "B": 0.04,   # %4 bankroll
    # C → girmez
}

def confidence_position_size(
    confidence: str,
    bankroll: float,
    max_bet_usdc: float = 75,
    max_bet_pct: float = 0.05,
    is_reentry: bool = False,
    market_price: float = 0.0,
) -> float:
    if confidence == "C":
        return 0.0   # Entry bloklanır
    
    bet_pct = CONF_BET_PCT.get(confidence, 0.04)
    
    # Ağır favori: 90¢+ market → size × 1.5
    if market_price >= 0.90:
        bet_pct *= 1.50
    
    # Lossy reentry: size × 0.8
    if is_reentry:
        bet_pct *= 0.80
    
    size = bankroll * bet_pct
    size = min(size, max_bet_usdc, bankroll * max_bet_pct, bankroll)
    return max(0, round(size, 2))
```

**Kap**:
- Tek trade max $75
- Bankroll'un max %5'i
- Polymarket min $5 (altında reddet)
```

`new_string`:
```
### 6.5 Position Sizing

Confidence + market koşullarına göre trade boyutu.

**Base sizing (`CONF_BET_PCT`):**
| Confidence | Yüzde | Uygulama |
|---|---|---|
| A | 5% | bankroll × 0.05 |
| B | 4% | bankroll × 0.04 |
| C | — | 0 (entry bloklanır) |

**Çarpanlar (bet_pct üzerine uygulanır):**
| Koşul | Çarpan |
|---|---|
| Ağır favori — `market_price ≥ 0.90` | × 1.50 |
| Lossy reentry — `is_reentry = True` | × 0.80 |

**Formül:**
```
size = bankroll × bet_pct × multiplier(s)
size = min(size, max_bet_usdc, bankroll × max_bet_pct, bankroll)
size = max(0, round(size, 2))
```

**Kaplar:**
- `max_bet_usdc` = $75 (tek trade üst sınırı)
- `max_bet_pct` = 5% bankroll
- Bankroll üst sınırı (sanity)
- Polymarket minimum: $5 — altında reddet
```

- [ ] **Step 4: Doğrula**

Değerler: 0.05, 0.04, 0.90, 1.50, 0.80, 75, 5 (min), 5% — tümü prose'da.

---

## Task 10: §6.6 Scale-Out transformasyonu

**Files:**
- Modify: `TDD.md` — §6.6

- [ ] **Step 1: Oku**

- [ ] **Step 2: Değer listesi**
- Tier 1: trigger_pnl_pct=0.25, sell_pct=0.40 (risk-free)
- Tier 2: trigger_pnl_pct=0.50, sell_pct=0.50 (profit lock)
- Tier 3: resolution/trailing (PnL-trigger değil)
- Volatility swing istisna (scale-out'a girmez)
- Geçiş: 0 → 1 → 2

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.6 Scale-Out (3-tier)

```python
SCALE_OUT_TIERS = {
    1: {"trigger_pnl_pct": 0.25, "sell_pct": 0.40},  # Risk-free
    2: {"trigger_pnl_pct": 0.50, "sell_pct": 0.50},  # Profit lock
    # Tier 3 = resolution / trailing exit (PnL-triggered değil)
}

def check_scale_out(
    scale_out_tier: int,
    unrealized_pnl_pct: float,
    volatility_swing: bool,
) -> dict | None:
    if volatility_swing:
        return None   # VS kendi TP'sini kullanır
    
    if scale_out_tier == 0 and unrealized_pnl_pct >= 0.25:
        return {"tier": 1, "sell_pct": 0.40, "reason": "risk_free"}
    
    if scale_out_tier == 1 and unrealized_pnl_pct >= 0.50:
        return {"tier": 2, "sell_pct": 0.50, "reason": "profit_lock"}
    
    return None
```
```

`new_string`:
```
### 6.6 Scale-Out (3-tier)

Kâr biriktikçe pozisyonun parçasını satmak.

| Tier | Tetikleyici (unrealized PnL) | Satış oranı | Amaç |
|---|---|---|---|
| 1 | ≥ +25% | 40% | Risk-free |
| 2 | ≥ +50% | 50% | Profit lock |
| 3 | Resolution / trailing | — | PnL-tetikli değil; §6.9-6.14 |

**Geçiş:** `tier 0 → 1 → 2` sırayla. Tier atlanmaz; ileri gider veya aynı kalır.

**İstisna:** `volatility_swing = True` pozisyonlar scale-out'a girmez (kendi TP'sini kullanır).
```

- [ ] **Step 4: Doğrula**

Değerler: 0.25, 0.40, 0.50, 0.50 — tümü prose'da.

---

## Task 11: §6.7 Flat SL 9-Katman transformasyonu

**Files:**
- Modify: `TDD.md` — §6.7

- [ ] **Step 1: Oku** (~50 satır)

- [ ] **Step 2: Değer listesi — 9 katman**
1. Stale price: `current ≤ 0.001` AND `current ≠ entry` → `None`
2. Totals/spread: question/slug "o/u"|"total"|"spread" → `None`
3. VS: `volatility_swing` → `vs_sl_pct` (default 0.20); `sl_reentry_count ≥ 1` → × 0.75
4. Ultra-low: `eff_entry < 0.09` → `sl = 0.50`
5. Low graduated: `0.09 ≤ eff_entry < 0.20` → `sl = 0.60 − t × 0.20` (t = (eff−0.09)/(0.20−0.09))
6. B conf: `confidence == "B"` → `sl = 0.30`
7. Sport default: `get_stop_loss(sport_tag)` (§7)
8. Lossy reentry: `sl_reentry_count ≥ 1` → `sl × 0.75`
9. Return sl

Defaults: `base_sl_pct=0.30`, `vs_sl_pct=0.20`.

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.7 Flat Stop-Loss Helper (9-Katman Öncelik)

```python
def compute_stop_loss_pct(
    pos: Position,
    base_sl_pct: float = 0.30,
    vs_sl_pct: float = 0.20,
) -> float | None:
    """None dönerse: bu pozisyon için flat SL uygulanmaz."""
    
    # 1. Stale price skip (WS tick gelmedi)
    if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
        return None
    
    # 2. Totals/spread → hold to resolution, no SL
    q = (pos.question or "").lower()
    slug = (pos.slug or "").lower()
    if any(k in q or k in slug for k in ("o/u", "total", "spread")):
        return None
    
    # 3. Volatility swing → vs_sl_pct
    if pos.volatility_swing:
        sl = vs_sl_pct
        if pos.sl_reentry_count >= 1:
            sl *= 0.75
        return sl
    
    eff_entry = effective_price(pos.entry_price, pos.direction)
    
    # 4. Ultra-low entry (<9¢) → geniş 50% SL
    if eff_entry < 0.09:
        sl = 0.50
    elif eff_entry < 0.20:
        # 5. Low-entry graduated (9-20¢): linear 60% → 40%
        t = (eff_entry - 0.09) / (0.20 - 0.09)
        sl = 0.60 - t * 0.20
    elif pos.confidence == "B":
        # 6. B confidence → tighter 30%
        sl = 0.30
    else:
        # 7. Sport-specific SL (sport_rules.py)
        sl = get_stop_loss(pos.sport_tag)
    
    # 8. Lossy reentry → tighter ×0.75
    if pos.sl_reentry_count >= 1:
        sl *= 0.75
    
    return sl
```
```

`new_string`:
```
### 6.7 Flat Stop-Loss Helper (9-Katman Öncelik)

Pozisyon için flat SL yüzdesi. Katmanlar öncelik sırasıyla; ilk eşleşen döner. `None` dönerse flat SL uygulanmaz.

| # | Katman | Koşul | Sonuç |
|---|---|---|---|
| 1 | Stale price skip | `current_price ≤ 0.001` AND `current_price ≠ entry_price` | `None` (WS tick beklenir) |
| 2 | Totals/spread skip | question veya slug "o/u", "total", "spread" içerir | `None` (resolution'a kadar tut) |
| 3 | Volatility swing | `pos.volatility_swing = True` | `vs_sl_pct` (default `0.20`); `sl_reentry_count ≥ 1` ise `× 0.75` |
| 4 | Ultra-low entry | `effective_entry < 0.09` | `0.50` (geniş tolerans) |
| 5 | Low-entry graduated | `0.09 ≤ effective_entry < 0.20` | Linear: `sl = 0.60 − t × 0.20`, `t = (eff − 0.09) / (0.20 − 0.09)` — 60% → 40% |
| 6 | B confidence | `pos.confidence == "B"` | `0.30` (tighter) |
| 7 | Sport-specific (default) | Yukarıdakiler eşleşmedi | `get_stop_loss(sport_tag)` (§7) |
| 8 | Lossy reentry modifier | `sl_reentry_count ≥ 1` | Yukarıdaki `sl × 0.75` |
| 9 | Return | — | `sl` |

**Default parametreler:** `base_sl_pct = 0.30`, `vs_sl_pct = 0.20`.

**Effective price:** `effective_price(entry_price, direction)` — direction BUY_NO ise `1 − entry_price`, aksi `entry_price`.
```

- [ ] **Step 4: Doğrula**

Değerler: 0.001, 0.20 (vs), 0.09, 0.50, 0.20 (low-gradated üst), 0.60, 0.20 (delta), 0.30 (B), 0.75 (reentry), 0.30 (base) — tümü prose'da.

---

## Task 12: §6.8 Graduated SL transformasyonu

**Files:**
- Modify: `TDD.md` — §6.8

- [ ] **Step 1: Oku** (~60 satır, momentum tighten dahil)

- [ ] **Step 2: Değer listesi**
- Base tiers: (0.85, 0.15), (0.65, 0.20), (0.40, 0.30), (0.00, 0.40)
- Pre-match (elapsed < 0) → 0.40
- Price mult: <0.20→1.50, <0.35→1.25, ≤0.50→1.00, <0.70→0.85, ≥0.70→0.70
- Score: map_diff>0 → 1.25, <0 → 0.75, else 1.00
- Formula: base × price_mult × score_adj
- Clamp: [0.05, 0.70]
- Momentum tighten: 5+ down + drop ≥0.10 → × 0.60; 3+ down + drop ≥0.05 → × 0.75

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.8 Graduated Stop-Loss (Elapsed-Aware)

```python
# Base tiers: (elapsed_pct_threshold, max_loss_pct)
# İlk eşleşen (en yüksek threshold) kullanılır.
_BASE_TIERS = [
    (0.85, 0.15),   # Final phase
    (0.65, 0.20),   # Late
    (0.40, 0.30),   # Mid
    (0.00, 0.40),   # Early
]

def get_graduated_max_loss(
    elapsed_pct: float,
    entry_price: float,
    score_info: dict,
) -> float:
    """Max allowed loss: base × price_mult × score_adj"""
    if elapsed_pct < 0:
        base = 0.40   # Pre-match = erken davran
    else:
        base = 0.40
        for threshold, loss in _BASE_TIERS:
            if elapsed_pct >= threshold:
                base = loss
                break
    
    # Entry price multiplier
    price_mult = get_entry_price_multiplier(entry_price)
    
    # Score adjustment
    score_adj = 1.0
    if score_info.get("available"):
        md = score_info.get("map_diff", 0)
        if md > 0:
            score_adj = 1.25   # Ahead: loosen
        elif md < 0:
            score_adj = 0.75   # Behind: tighten
    
    result = base * price_mult * score_adj
    return max(0.05, min(0.70, result))


def get_entry_price_multiplier(entry_price: float) -> float:
    """Düşük giriş = geniş tolerans, yüksek giriş = dar."""
    if entry_price < 0.20:
        return 1.50
    elif entry_price < 0.35:
        return 1.25
    elif entry_price <= 0.50:
        return 1.00
    elif entry_price < 0.70:
        return 0.85
    else:
        return 0.70
```

**Momentum tighten** (graduated SL içinde, ardışık düşüşlerde SL daralt):
- `consecutive_down >= 5 AND cumulative_drop >= 0.10` → max_loss × 0.60
- `consecutive_down >= 3 AND cumulative_drop >= 0.05` → max_loss × 0.75
```

`new_string`:
```
### 6.8 Graduated Stop-Loss (Elapsed-Aware)

Zaman/fiyat/score'a duyarlı max allowed loss.

**Formül:**
```
max_loss = base × price_mult × score_adj
max_loss = clamp(max_loss, 0.05, 0.70)
```

**Base tiers (elapsed % — ilk eşleşen, en yüksek eşikten aşağı):**
| Elapsed | Base max loss | Faz |
|---|---|---|
| ≥ 0.85 | 0.15 | Final |
| ≥ 0.65 | 0.20 | Late |
| ≥ 0.40 | 0.30 | Mid |
| ≥ 0.00 | 0.40 | Early |
| < 0.00 (pre-match) | 0.40 | Early davran |

**Entry price multiplier (`get_entry_price_multiplier`):**
| Entry price | Multiplier |
|---|---|
| < 0.20 | 1.50 |
| 0.20 – 0.35 | 1.25 |
| 0.35 – 0.50 (inclusive) | 1.00 |
| 0.50 – 0.70 | 0.85 |
| ≥ 0.70 | 0.70 |

**Score adjustment:**
| Skor durumu | `score_adj` |
|---|---|
| `available = True` AND `map_diff > 0` (önde) | 1.25 (genişlet) |
| `available = True` AND `map_diff < 0` (geride) | 0.75 (daralt) |
| Aksi (skor yok veya beraberlik) | 1.00 |

**Momentum tighten** (yukarıdaki sonuç üzerine ek çarpan):
| Koşul | Çarpan |
|---|---|
| `consecutive_down ≥ 5` AND `cumulative_drop ≥ 0.10` | `max_loss × 0.60` |
| `consecutive_down ≥ 3` AND `cumulative_drop ≥ 0.05` | `max_loss × 0.75` |
```

- [ ] **Step 4: Doğrula**

Değerler: 0.85, 0.15, 0.65, 0.20, 0.40, 0.30, 0.40, 0.20 (price), 1.50, 0.35, 1.25, 0.50, 1.00, 0.70, 0.85, 0.70 (final), 1.25, 0.75, 0.05, 0.70 (clamp), 5, 0.10, 0.60, 3, 0.05, 0.75 — tümü prose'da.

---

## Task 13: §6.9 A-conf Hold-to-Resolve transformasyonu

**Files:**
- Modify: `TDD.md` — §6.9

- [ ] **Step 1: Oku** (~37 satır, veri notu dahil)

- [ ] **Step 2: Değer listesi**
- Hold koşulu: confidence=="A" AND effective_entry ≥ 0.60
- Elapsed < 0.85: atlanan → graduated SL, never-in-profit, hold revocation, edge-decay TP; aktif → scale-out, near-resolve
- Elapsed ≥ 0.85: graduated SL aktif; ekstra market_flip (effective_current < 0.50 → exit)
- Veri: 25 A-conf analizi, market_flip $110.78 tasarruf (-$15.86 vs -$126.64)

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.9 A-conf Hold-to-Resolve (Elapsed-Aware Market Flip)

```python
# match_exit.py içinde

a_conf_hold = (
    pos.confidence == "A"
    and effective_price(pos.entry_price, pos.direction) >= 0.60
)

if a_conf_hold:
    # ATLANACAK kurallar (erken/orta maçta):
    # - Graduated SL
    # - Never-in-profit guard
    # - Hold revocation
    # - Edge decay TP
    
    if elapsed_pct >= 0.85:
        # Geç maç: graduated SL aktif, herkes gibi
        max_loss = get_graduated_max_loss(
            elapsed_pct, effective_entry, score_info
        )
        if pnl_pct < -max_loss:
            return exit("graduated_sl")
        
        # Market flip: eff < 50¢ → çık
        if effective_current < 0.50:
            return exit("market_flip")
    else:
        # Erken/orta maç: hold'a devam, sadece scale-out ve near-resolve aktif
        pass
```

**Veri dayanağı**: 25 A-conf resolved trade analizi:
- Mevcut kurallarla (market_flip dahil): -$15.86
- Hold'a bekleseydik: -$126.64
- **Market flip $110.78 kurtarıyor** — kural kalmalı, ama elapsed gate ile early-match false positive'leri elenir.
```

`new_string`:
```
### 6.9 A-conf Hold-to-Resolve (Elapsed-Aware Market Flip)

Yüksek güvenli pozisyonları resolution'a kadar tutmak — erken maçlarda geniş tolerans.

**Hold koşulu:**
- `pos.confidence == "A"`
- AND `effective_price(entry_price, direction) ≥ 0.60`

**Hold aktifken davranış:**
| Elapsed | Atlanan kurallar | Aktif kurallar |
|---|---|---|
| < 0.85 (erken/orta) | Graduated SL (§6.8), Never-in-profit (§6.10), Hold revocation (§6.14), Edge-decay TP | Scale-out (§6.6), Near-resolve profit (§6.11) |
| ≥ 0.85 (geç) | — | **Graduated SL aktif** + **market_flip**: `effective_current < 0.50` → `exit("market_flip")` |

**Veri dayanağı** (25 A-conf resolved trade analizi):
| Senaryo | Sonuç |
|---|---|
| Market_flip kuralıyla (mevcut) | -$15.86 |
| Hold'a bekleseydik | -$126.64 |
| **Market flip farkı** | **+$110.78 tasarruf** |

Kural korunacak; elapsed gate early-match false positive'leri eler.
```

- [ ] **Step 4: Doğrula**

Değerler: 0.60, 0.85, 0.50 (flip), -$15.86, -$126.64, $110.78 — tümü prose'da.

---

## Task 14: §6.10 Never-in-Profit Guard transformasyonu

**Files:**
- Modify: `TDD.md` — §6.10

- [ ] **Step 1: Oku**

- [ ] **Step 2: Değer listesi**
- Trigger: `not ever_in_profit` AND `peak_pnl_pct ≤ 0.01` AND `elapsed_pct ≥ 0.70`
- score_ahead → stay
- current ≥ entry × 0.90 → stay
- current < entry × 0.75 → exit("never_in_profit")
- 0.75 - 0.90 arası → graduated SL devreye

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.10 Never-in-Profit Guard

```python
if (not ever_in_profit
    and peak_pnl_pct <= 0.01
    and elapsed_pct >= 0.70):
    
    score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
    
    if score_ahead:
        pass   # Stay — winning despite no profit
    elif effective_current >= effective_entry * 0.90:
        pass   # Stay — close to entry
    elif effective_current < effective_entry * 0.75:
        return exit("never_in_profit")
    # Aradaki (0.75 - 0.90): graduated SL devreye giriyor
```
```

`new_string`:
```
### 6.10 Never-in-Profit Guard

Hiç kâra geçmemiş geç-faz pozisyonlar için erken çıkış.

**Tetikleyici (hepsi birlikte):**
- `not ever_in_profit`
- AND `peak_pnl_pct ≤ 0.01`
- AND `elapsed_pct ≥ 0.70`

**Tetiklendiğinde aksiyon:**
| Durum | Aksiyon |
|---|---|
| Skor önde (`map_diff > 0`, available) | **Stay** (winning despite no profit) |
| `effective_current ≥ effective_entry × 0.90` | **Stay** (entry'ye yakın) |
| `effective_current < effective_entry × 0.75` | **Exit** (`never_in_profit`) |
| Aradaki (`0.75 ≤ ratio < 0.90`) | Graduated SL (§6.8) devralır |
```

- [ ] **Step 4: Doğrula**

Değerler: 0.01, 0.70, 0.90, 0.75 — tümü prose'da.

---

## Task 15: §6.11 Near-Resolve Profit Exit transformasyonu

**Files:**
- Modify: `TDD.md` — §6.11

- [ ] **Step 1: Oku**

- [ ] **Step 2: Değer listesi**
- Trigger: `effective_current ≥ 0.94`
- Pre-match reject
- `mins_since_start < 5.0` reject (WS spike guard)
- Veri: 27 exit, +$140.31, %93 WR

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.11 Near-Resolve Profit Exit

```python
# WebSocket path (exit_monitor._ws_check_exits)
if effective_current >= 0.94:
    # SANITY: pre-match veya just-started (< 5 dk) guard
    # WebSocket bazen açılışta spike gönderebiliyor (0.00 veya 1.00)
    
    if _pre_match:
        return   # Reject — match not started
    if _mins_since_start < 5.0:
        return   # Reject — just started, spike risk
    
    return exit("near_resolve_profit")
```

**Veri**: 27 near-resolve exit = +$140.31 (93% WR) → **en büyük kâr kaynağı**.
```

`new_string`:
```
### 6.11 Near-Resolve Profit Exit

94¢ eşiğinde kâr alma — WebSocket path'te çalışır.

**Tetikleyici:** `effective_current ≥ 0.94`

**Sanity guard'ları (WS spike koruması):**
| Koşul | Aksiyon |
|---|---|
| Pre-match (maç başlamadı) | Reject |
| `mins_since_start < 5.0` | Reject (açılış spike'ı — 0.00/1.00 gelebiliyor) |
| Aksi | **Exit** (`near_resolve_profit`) |

**Veri dayanağı:** 27 near-resolve exit = **+$140.31 (%93 WR)** — sistemin en büyük kâr kaynağı.
```

- [ ] **Step 4: Doğrula**

Değerler: 0.94, 5.0, 27, $140.31, %93 — tümü prose'da.

---

## Task 16: §6.12 Ultra-Low Guard transformasyonu

**Files:**
- Modify: `TDD.md` — §6.12

- [ ] **Step 1: Oku**

- [ ] **Step 2: Değer listesi**
- effective_entry < 0.09
- elapsed_pct ≥ 0.75
- effective_current < 0.05

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.12 Ultra-Low Guard

```python
if (effective_entry < 0.09
    and elapsed_pct >= 0.75
    and effective_current < 0.05):
    return exit("ultra_low_guard")
```
```

`new_string`:
```
### 6.12 Ultra-Low Guard

Ultra-düşük giriş pozisyonlarında geç fazda çıkış.

**Tüm koşullar birlikte:**
- `effective_entry < 0.09`
- AND `elapsed_pct ≥ 0.75`
- AND `effective_current < 0.05`

→ **Exit** (`ultra_low_guard`)
```

- [ ] **Step 4: Doğrula**

Değerler: 0.09, 0.75, 0.05 — tümü prose'da.

---

## Task 17: §6.13 FAV Promotion transformasyonu

**Files:**
- Modify: `TDD.md` — §6.13

- [ ] **Step 1: Oku**

- [ ] **Step 2: Değer listesi**
- Promote: `not favored` AND `not volatility_swing` AND `eff_price ≥ 0.65` AND `confidence ∈ {A, B}` → `favored = True`
- Demote: `favored = True` AND `eff_price < 0.65` → `favored = False`
- Favored pozisyonlar A-conf hold mantığına tabi (§6.9)
- Veri: 5 favored trade = +$42.90, %100 WR

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.13 FAV Promotion

Holding sırasında dinamik durum değişikliği:

```python
# portfolio.py price update callback'inde
eff_price = effective_price(pos.current_price, pos.direction)

if not pos.favored and not pos.volatility_swing:
    # PROMOTE: güçlü favori haline geldi
    if eff_price >= 0.65 and pos.confidence in ("A", "B"):
        pos.favored = True
        logger.info("FAV PROMOTED: %s | eff=%.0f%% | conf=%s",
                    pos.slug[:35], eff_price * 100, pos.confidence)
elif pos.favored:
    # DEMOTE: artık favori değil
    if eff_price < 0.65:
        pos.favored = False
        logger.info("FAV DEMOTED: %s | eff=%.0f%% < 65%%",
                    pos.slug[:35], eff_price * 100)
```

**Davranış**: `favored = True` olan pozisyonlar A-conf hold mantığına tabi olur (graduated SL'den kısmen muaf, market_flip elapsed-gated).

**Veri**: 5 favored trade = **+$42.90, %100 WR**. Bu sistem korunacak.
```

`new_string`:
```
### 6.13 FAV Promotion

Holding sırasında dinamik favori statüsü. `effective_price(current_price, direction)` üzerinden değerlendirilir.

**PROMOTE (favori hale gelme) — tüm koşullar:**
- `not favored`
- AND `not volatility_swing`
- AND `effective_price ≥ 0.65`
- AND `confidence ∈ {A, B}`

→ `favored = True`

**DEMOTE (favori statüsü kaybı):**
- `favored = True`
- AND `effective_price < 0.65`

→ `favored = False`

**Davranış:** `favored = True` pozisyonlar A-conf hold mantığına (§6.9) tabi olur — graduated SL'den kısmen muaf, market_flip elapsed-gated.

**Veri dayanağı:** 5 favored trade = **+$42.90, %100 WR** — sistem korunacak.
```

- [ ] **Step 4: Doğrula**

Değerler: 0.65 (promote), 0.65 (demote), 5 trade, +$42.90, %100 WR — tümü prose'da.

---

## Task 18: §6.14 Hold Revocation transformasyonu

**Files:**
- Modify: `TDD.md` — §6.14

- [ ] **Step 1: Oku**

- [ ] **Step 2: Değer listesi**
- Hold candidate: `not a_conf_hold` AND (`favored` OR (`anchor_probability ≥ 0.65` AND `confidence ∈ {A, B}`))
- Dip temporary: `consecutive_down < 3` OR `cumulative_drop < 0.05`
- Ever in profit path: `current < entry × 0.70` AND `elapsed > 0.60` AND NOT score_ahead AND NOT dip_temporary → revoke
- Never in profit path: `current < entry × 0.75` AND `elapsed > 0.70` AND NOT score_ahead AND NOT dip_temporary → revoke + exit("hold_revoked")

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.14 Hold Revocation (non-favored, non-A-conf-hold pozisyonlar için)

```python
# Hold candidate: anchor_probability >= 0.65 AND conf in ("A", "B")
is_hold_candidate = not a_conf_hold and (
    pos.favored or (
        pos.anchor_probability >= 0.65 and pos.confidence in ("A", "B")
    )
)

if is_hold_candidate:
    dip_is_temporary = (consecutive_down < 3 or cumulative_drop < 0.05)
    
    if ever_in_profit and effective_current < effective_entry * 0.70 and elapsed_pct > 0.60:
        if not score_ahead and not dip_is_temporary:
            revoke_hold()   # Hold iptal (normal kurallara geri dön)
    
    if not ever_in_profit and effective_current < effective_entry * 0.75 and elapsed_pct > 0.70:
        if not score_ahead and not dip_is_temporary:
            revoke_hold()
            return exit("hold_revoked")
```
```

`new_string`:
```
### 6.14 Hold Revocation

Non-favored, non-A-conf-hold pozisyonlar için hold iptali — ciddi fiyat düşüşü + skor dezavantajı altında.

**Hold candidate:**
- `not a_conf_hold`
- AND (`favored` OR (`anchor_probability ≥ 0.65` AND `confidence ∈ {A, B}`))

**Dip temporary mi?**
- `consecutive_down < 3` OR `cumulative_drop < 0.05` → TEMPORARY (revoke etme)
- Aksi → KALICI

**Revoke koşulları (hold candidate için):**
| Durum | Koşul | Aksiyon |
|---|---|---|
| `ever_in_profit = True` | `current < entry × 0.70` AND `elapsed > 0.60` AND NOT score_ahead AND NOT dip_temporary | Revoke hold (normal kurallara dön) |
| `ever_in_profit = False` | `current < entry × 0.75` AND `elapsed > 0.70` AND NOT score_ahead AND NOT dip_temporary | Revoke + **Exit** (`hold_revoked`) |
```

- [ ] **Step 4: Doğrula**

Değerler: 0.65 (anchor), 3, 0.05 (dip drop), 0.70 (ever profit price), 0.60 (ever elapsed), 0.75 (never profit price), 0.70 (never elapsed) — tümü prose'da.

---

## Task 19: §6.15 Circuit Breaker transformasyonu

**Files:**
- Modify: `TDD.md` — §6.15

- [ ] **Step 1: Oku** (~35 satır)

- [ ] **Step 2: Değer listesi**
- DAILY_MAX_LOSS_PCT = -0.08
- HOURLY_MAX_LOSS_PCT = -0.05
- CONSECUTIVE_LOSS_LIMIT = 4
- COOLDOWN_AFTER_DAILY = 120 dk
- COOLDOWN_AFTER_HOURLY = 60 dk
- COOLDOWN_AFTER_CONSECUTIVE = 60 dk
- ENTRY_BLOCK_THRESHOLD = -0.03 (soft)
- Asla exit'i durdurmaz (entry halt only)

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.15 Circuit Breaker

```python
DAILY_MAX_LOSS_PCT = -0.08       # -%8 günlük
HOURLY_MAX_LOSS_PCT = -0.05      # -%5 saatlik
CONSECUTIVE_LOSS_LIMIT = 4
COOLDOWN_AFTER_DAILY = 120       # dk
COOLDOWN_AFTER_HOURLY = 60
COOLDOWN_AFTER_CONSECUTIVE = 60
ENTRY_BLOCK_THRESHOLD = -0.03    # Soft block (-%3 günlük)

def should_halt_entries(self) -> tuple[bool, str]:
    """Sadece entry halt — exit'leri asla durdurmaz."""
    if breaker_active:
        return True, f"Cooldown {remaining}min"
    
    if daily_loss <= DAILY_MAX_LOSS_PCT:
        activate(COOLDOWN_AFTER_DAILY)
        return True, "Daily limit hit"
    
    if hourly_loss <= HOURLY_MAX_LOSS_PCT:
        activate(COOLDOWN_AFTER_HOURLY)
        return True, "Hourly limit hit"
    
    if consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
        activate(COOLDOWN_AFTER_CONSECUTIVE)
        return True, "Consecutive loss limit"
    
    if daily_loss <= ENTRY_BLOCK_THRESHOLD:
        return True, "Soft block (-3%)"
    
    return False, ""
```
```

`new_string`:
```
### 6.15 Circuit Breaker

Bankroll koruma — **yalnızca entry halt** eder, exit'i asla durdurmaz.

**Eşikler:**
| Parametre | Değer | Etki |
|---|---|---|
| Günlük max loss (hard halt) | -8% | Halt + 120 dk cooldown |
| Saatlik max loss (hard halt) | -5% | Halt + 60 dk cooldown |
| Ardışık kayıp limiti | 4 trade | Halt + 60 dk cooldown |
| Günlük entry soft block | -3% | Soft block (entry askıya alınır ama hard halt değil) |

**`should_halt_entries` kontrol sırası:**
1. Cooldown aktif mi? → halt (kalan dk gösterilir)
2. Günlük loss ≤ -8% → halt 120 dk ("Daily limit hit")
3. Saatlik loss ≤ -5% → halt 60 dk ("Hourly limit hit")
4. Ardışık kayıp ≥ 4 → halt 60 dk ("Consecutive loss limit")
5. Günlük loss ≤ -3% → soft block ("Soft block (-3%)")
6. Aksi → devam

**Kritik:** Exit kararları breaker'dan asla etkilenmez — zarar artıyorsa SL tetiklenmeli.
```

- [ ] **Step 4: Doğrula**

Değerler: -8%, -5%, 4, 120, 60, 60, -3% — tümü prose'da.

---

## Task 20: §6.16 Manipulation Guard transformasyonu

**Files:**
- Modify: `TDD.md` — §6.16

- [ ] **Step 1: Oku**

- [ ] **Step 2: Değer listesi**
- Subjects (17): trump, biden, elon, musk, putin, zelensky, xi jinping, desantis, vance, newsom, harris, netanyahu, modi, zuckerberg, bezos, altman
- Verbs: say, tweet, post, announce, sign, veto, pardon, fire, hire, appoint, endorse, resign, visit, meet with, call, respond, comment, declare
- Self-resolving (subject + verb) → +3
- Low liquidity < 10000 → +1 (veya +2 eğer ≤ 0)
- ≥ 3 → high (SKIP)
- ≥ 2 → medium (size × 0.5)
- < 2 → low (OK)
- Default min_liquidity_usd = 10000

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.16 Manipulation Guard

```python
SELF_RESOLVING_SUBJECTS = [
    "trump", "biden", "elon", "musk", "putin", "zelensky", "xi jinping",
    "desantis", "vance", "newsom", "harris", "netanyahu", "modi",
    "zuckerberg", "bezos", "altman",
]
SELF_RESOLVING_VERBS = re.compile(
    r"\b(say|tweet|post|announce|sign|veto|pardon|fire|hire|appoint|endorse|"
    r"resign|visit|meet with|call|respond|comment|declare)\b", re.IGNORECASE,
)

def check_market(question, description, liquidity):
    flags = []
    risk_score = 0
    
    # 1. Self-resolving
    if self._is_self_resolving(question, description):
        flags.append("SELF_RESOLVING"); risk_score += 3
    
    # 2. Low liquidity (< $10K)
    if liquidity < 10_000:
        flags.append("LOW_LIQUIDITY"); risk_score += 2 if liquidity <= 0 else 1
    
    if risk_score >= 3:
        return ManipulationCheck(safe=False, risk_level="high")
    elif risk_score >= 2:
        return ManipulationCheck(safe=True, risk_level="medium")  # size × 0.5
    return ManipulationCheck(safe=True, risk_level="low")
```
```

`new_string`:
```
### 6.16 Manipulation Guard

Self-resolving marketler (kişi market sonucunu etkileyebilir) + düşük likidite tespiti.

**Self-resolving subjects** (16 kişi — market sonucunu etkileyebilecekler):
`trump, biden, elon, musk, putin, zelensky, xi jinping, desantis, vance, newsom, harris, netanyahu, modi, zuckerberg, bezos, altman`

**Self-resolving verbs** (regex — case-insensitive, word boundary):
`say, tweet, post, announce, sign, veto, pardon, fire, hire, appoint, endorse, resign, visit, meet with, call, respond, comment, declare`

**Risk skoru:**
| Kontrol | Koşul | Score |
|---|---|---|
| Self-resolving | Subject AND verb metinde birlikte (question + description) | +3 |
| Low liquidity | `liquidity < 10_000` | +1 (+2 eğer `liquidity ≤ 0`) |

**Risk seviyesi → davranış:**
| Toplam score | Level | Davranış |
|---|---|---|
| ≥ 3 | high | **SKIP** (entry reddedilir) |
| = 2 | medium | Size × 0.5 |
| < 2 | low | OK (tam size) |

**Default `min_liquidity_usd`:** `10000` (config.yaml `manipulation.min_liquidity_usd`).
```

- [ ] **Step 4: Doğrula**

Değerler: 16 subject ismi, 18 verb, +3, +1, +2, 10000, score 3/2/</2 seviyeleri, size × 0.5 — tümü prose'da.

---

## Task 21: §6.17 Liquidity Check transformasyonu

**Files:**
- Modify: `TDD.md` — §6.17

- [ ] **Step 1: Oku**

- [ ] **Step 2: Değer listesi**
- Entry: min_depth = 100, halve if size/depth > 0.20
- Exit: floor_price = best_bid × 0.95
- fill_ratio = available / needed
- ≥ 1.0 → market, ≥ 0.80 → limit, < 0.80 → split
- Default min_fill_ratio = 0.80

- [ ] **Step 3: Edit ile değiştir**

`old_string`:
```
### 6.17 Liquidity Check

**Entry**:
```python
def check_entry_liquidity(token_id, size_usdc, min_depth=100.0):
    total_ask_depth = sum(float(a["price"]) * float(a["size"]) for a in book["asks"])
    
    if total_ask_depth < min_depth:
        return {"ok": False, "reason": "Depth < $100"}
    
    # Order > %20 of book → halve size (slippage)
    if size_usdc / total_ask_depth > 0.20:
        return {"ok": True, "recommended_size": size_usdc / 2}
    
    return {"ok": True, "recommended_size": size_usdc}
```

**Exit**:
```python
def check_exit_liquidity(token_id, shares_to_sell, min_fill_ratio=0.80):
    floor_price = best_bid * 0.95
    available = sum(size for bid in book["bids"] if bid.price >= floor_price)
    fill_ratio = available / shares_to_sell
    
    if fill_ratio >= 1.0:
        return {"fillable": True, "strategy": "market"}
    elif fill_ratio >= min_fill_ratio:
        return {"fillable": True, "strategy": "limit"}
    else:
        return {"fillable": False, "strategy": "split"}
```
```

`new_string`:
```
### 6.17 Liquidity Check

Entry ve exit sırasında orderbook derinliği kontrolü.

**Entry check:**

`total_ask_depth = sum(ask.price × ask.size)` tüm ask seviyelerinde.

| Koşul | Aksiyon |
|---|---|
| `total_ask_depth < $100` | **Reject** (`ok=False`, reason: "Depth < $100") |
| `size_usdc / total_ask_depth > 0.20` | Halve size (slippage koruması) — `recommended_size = size / 2` |
| Aksi | Accept, orijinal size |

**Default `min_depth`:** `100.0`.

**Exit check:**

`floor_price = best_bid × 0.95` (piyasa dışına düşmeyi engelle).
`available = sum(bid.size for bid in book.bids if bid.price ≥ floor_price)`.
`fill_ratio = available / shares_to_sell`.

| `fill_ratio` | Strategy |
|---|---|
| ≥ 1.0 | `market` (tek seferde emir) |
| `min_fill_ratio` ≤ ratio < 1.0 | `limit` (floor_price'ta limit emir) |
| < `min_fill_ratio` | `split` (emri böl, zamanla doldur) |

**Default `min_fill_ratio`:** `0.80`.
```

- [ ] **Step 4: Doğrula**

Değerler: 100, 0.20, 0.95, 1.0, 0.80 — tümü prose'da.

---

## Task 22: Final verification

**Files:** (yok — sadece doğrulama)

- [ ] **Step 1: Test suite**

Run: `pytest -q`
Expected: `595 passed`

- [ ] **Step 2: Python code block taraması**

Run: `grep -c '```python' TDD.md`
Expected: `0` (tüm Python blokları temizlenmiş olmalı).

- [ ] **Step 3: TDD boyutu**

Run: `wc -l TDD.md`
Expected: ~500-700 satır civarı (başlangıç 1541 — %50-60 azalma).

- [ ] **Step 4: §6.X başlıkları sayımı**

Run: `grep -c "^### 6\." TDD.md`
Expected: `17` (§6.1–§6.17 hepsi yerinde).

- [ ] **Step 5: Ana başlıklar**

Run: `grep "^## " TDD.md`
Expected: İçindekiler, §0, §6, §7, §13 — başka yok.

- [ ] **Step 6: CLAUDE.md yeni bölümler**

Run: `grep "Dosya Rolleri\|Kural Değişikliği Protokolü" CLAUDE.md`
Expected: İki bölüm başlığı da görünür.

- [ ] **Step 7: Değer spot-check**

Her §6.X için kritik değerlerden 2-3 tanesini spot-check et:
- §6.5: `grep -c "0.05\|0.04\|0.90\|1.50" TDD.md` — §6.5 aralığında çıkmalı
- §6.8: `grep "0.85\|0.15\|0.65" TDD.md` — §6.8'de çıkmalı
- §6.15: `grep -- "-8%\|-5%" TDD.md` — §6.15'te çıkmalı

Eğer bir değer kayıpsa: durdur, kullanıcıya raporla, tekrar üzerine git.

- [ ] **Step 8: Rapor**

Kullanıcıya ver:
- Değişen dosyalar: `CLAUDE.md`, `TDD.md`
- TDD satır azalması: `<X> satır (~<Y>%)`
- Python block sayısı: `0` (önceden ~17)
- pytest: `595/595`
- Eklenen: Dosya Rolleri tablosu, Rule-Change Protokolü
- Silinen: TDD §1-§5, §8-§12; §6.X Python blokları
- Kod/config/test: dokunulmadı

---

## Self-Review Notları

**Spec kapsamı:** Spec bölüm 2 (dosya rolleri), bölüm 3 (LAYER 2 silinecekler), bölüm 4 ("§6.X'te sadece değer tabloları + neden notları + karar ağacı olmalı, Python olmamalı"), bölüm 5 (rule-change protokolü) — tümü tasklarda karşılanıyor.

**Placeholder taraması:** §6.X task'larındaki Step 1 "Oku" satır aralığı açık yazmadı — satır numaraları TDD düzenlendikçe değişecek. Bu kasıtlı; uygulayıcı Read öncesi `grep -n "^### 6\."` ile o anki satır numarasını bulur, sonra oku. Alternatif olarak her task başında `grep -n "^### 6\.<n>"` ile spot belirlenir.

**Tip tutarlılığı:** §6.X başlık numaraları tüm task-lar arası tutarlı. Değer isimleri (`effective_entry`, `elapsed_pct`, vb.) aynı anlamı taşıyor.

**Git yok:** Commit adımları yok, pytest+grep doğrulaması kullanıldı.

**Değer koruma garantisi:** Her §6.X task'ı Step 2'de "değer listesi" çıkarır, Step 4'te her değerin prose'da olduğunu doğrular. Bir değer kaybı varsa task başarısızdır.

**Execution önerisi:** Subagent-driven. Her §6.X ayrı subagent, aralarda spot-check. Hata olursa tek section'da kalır, yayılmaz.
