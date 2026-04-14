# TDD — Technical Design Document

> Polymarket Agent 2.0 — Mimari ve Teknik Tasarım
> Version: 2.0 | Tarih: 2026-04-13
> Durum: APPROVED (2026-04-13)

---

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

---

## 0. Temel İlkeler (Değişmez Prensipler)

1. **Veri kaynağı = bookmaker**. Odds API 20+ bahis sitesinden konsensüs üretir.
2. **3 katmanlı cycle**: WebSocket (anlık) + Light (5 sn) + Heavy (30 dk).
3. **Pozisyon boyutu confidence'a göre**: A=%5, B=%4, C=blok.
4. **Profit taking = scale-out** (3-tier).
5. **MVP kapsamı = 2-way sporlar**. Ertelenmiş branşlar için bkz. `TODO.md`.
6. **P(YES) her zaman anchor** — direction-adjusted saklanmaz.
7. **Event-level guard**: aynı event_id'ye iki pozisyon açılamaz.

---


## 6. Kritik Algoritmalar

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

### 6.2 Confidence Grading

Bookmaker ağırlığı + sharp var mı → A/B/C.

| Confidence | Koşul |
|---|---|
| **A** | `has_sharp = True` (Pinnacle veya Betfair Exchange var) ve `bm_weight ≥ 5` |
| **B** | `bm_weight ≥ 5`, sharp yok |
| **C** | `bm_weight` None VEYA < 5 — entry bloklanır |

Confidence, sizing multiplier'ına (→ §6.3) ve entry kararına direkt etki eder.

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

### 6.6 Scale-Out (3-tier)

Kâr biriktikçe pozisyonun parçasını satmak.

| Tier | Tetikleyici (unrealized PnL) | Satış oranı | Amaç |
|---|---|---|---|
| 1 | ≥ +25% | 40% | Risk-free |
| 2 | ≥ +50% | 50% | Profit lock |
| 3 | Resolution / trailing | — | PnL-tetikli değil; §6.9-6.14 |

**Geçiş:** `tier 0 → 1 → 2` sırayla. Tier atlanmaz; ileri gider veya aynı kalır.

**İstisna:** `volatility_swing = True` pozisyonlar scale-out'a girmez (kendi TP'sini kullanır).

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

### 6.12 Ultra-Low Guard

Ultra-düşük giriş pozisyonlarında geç fazda çıkış.

**Tüm koşullar birlikte:**
- `effective_entry < 0.09`
- AND `elapsed_pct ≥ 0.75`
- AND `effective_current < 0.05`

→ **Exit** (`ultra_low_guard`)

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

---

## 7. Sport Rules (MVP için)

### 7.1 Kapsam

**MVP'de aktif sporlar** (2-way — draw içermeyen):
- Baseball: MLB, MiLB, NPB, KBO, NCAA
- Basketball: NBA, WNBA, NCAAB, WNCAAB, Euroleague, NBL, NBA Summer
- Ice Hockey: NHL, AHL, Liiga, Mestis, SHL, Allsvenskan
- American Football: NCAAF, CFL, UFL
- Tennis: Tüm ATP/WTA turnuvaları (dinamik matching)
- Golf: LPGA Tour, LIV Tour (H2H)

### 7.2 Sport-Specific Kurallar (özet)

| Sport | stop_loss_pct | match_duration_hours | Özel exit |
|---|---|---|---|
| NBA | 0.35 | 2.5 | halftime_exit @ -15 pts |
| American Football (NCAAF/CFL/UFL) | 0.30 | 3.25 | halftime_exit @ -14 pts |
| NHL (AHL/Liiga/...) | 0.30 | 2.5 | period_exit @ -3 goals after P2 |
| MLB (+ MiLB/NPB/KBO/NCAA) | 0.30 | 3.0 | inning_exit @ -5 runs after 6th |
| Tennis (ATP/WTA) | 0.35 | 1.75-3.5 (BO3/BO5) | set-based exit |
| Golf (LPGA/LIV) | 0.30 | 4.0 | playoff-aware |
| DEFAULT | 0.30 | 2.0 | - |

**Not**: Detaylı sport_rules tabloları `src/config/sport_rules.py`'de tutulur. Ertelenmiş branşların kuralları için bkz. `TODO.md` TODO-001.

---


## 13. Açık Noktalar (ilerisi için)

1. **Golf outright futures**: Sadece H2H (`golf_lpga_tour`, `golf_liv_tour`) MVP'de. `golf_masters_tournament_winner` vb. outright'lar scope dışı.
2. **Tennis dinamik matching**: `odds_client.py`'de `_get_active_tennis_keys` + `_match_tennis_key` migrate edilecek.
3. **Baseball preseason**: `baseball_mlb_preseason` aktif ama preseason maçlarında motivasyon düşük — potansiyel bir `allow_preseason: false` flag eklenebilir.
4. **Draw-possible sporlar**: Tümü TODO-001'de. MVP'de scanner bu sport_tag'leri filter'lar.

