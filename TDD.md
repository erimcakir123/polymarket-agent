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

### Stock Queue (F1.5)

Scanner ve gate arasında persistent eligible pool. Amaç: Odds API kredi israfını
önlemek + fırsat kaybını engellemek.

**Davranış:**
- Gate `exposure_cap_reached` / `max_positions_reached` / `no_edge` / `no_bookmaker_data` ile reddettiği marketleri stock'a push eder.
- Her heavy cycle'da Gamma scan → stock refresh (MarketData güncellenir, delist edilenler düşer) → TTL eviction.
- **JIT batch:** `empty_slots × jit_batch_multiplier` (default 3) kadar stock item match_start ASC alınır, enrich + gate pipeline'a girer. Kalan slot varsa fresh-only (stock'ta olmayan) batch ekler.
- **TTL evict:** first_seen + 24h | match_start − 30dk | event açık pozisyonda | no_edge ≥ 3.
- **Persistent:** `logs/stock_queue.json` — restart'ta restore.

**Rasyonel:** 300 market enrich yerine `3 × boş_slot` kadar enrich. Örnek: 4 boş slot = en yakın 12 market (stock öncelikli). Odds kredisi ~70% tasarruf + gece enrich edilmiş marketler gündüz slot açıldığında hâlâ kullanılabilir.

---

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


## 5. Dashboard & Observability

### 5.7 Dashboard Display Rules

Dashboard presentation katmanı — kurallar domain kurallarından ayrı.
`presentation/dashboard/computed.py` + `static/js/*` sınırında enforce edilir.

#### 5.7.1 Treemap Branş Gruplaması

Gruplama anahtarı = **sport category** (baseball, hockey, tennis, ...).
Lig kodları (mlb, nhl, vb.) branşa map edilir:

```python
_LEAGUE_TO_SPORT = {
    "mlb": "baseball",
    "nhl": "hockey", "ahl": "hockey", "khl": "hockey",
    "nba": "basketball", "wnba": "basketball",
    "nfl": "football", "cfl": "football",
    "epl": "soccer", "ucl": "soccer", "mls": "soccer", "seriea": "soccer",
    "wta": "tennis", "atp": "tennis",
    "pga": "golf", "lpga": "golf", "rbc": "golf",
}
```

Öncelik: `sport_category` field → `sport_tag` split (`baseball_mlb`→baseball) →
lig map (eski kayıt: `mlb`→baseball) → sport_tag as-is → `unknown`.

Lokasyon: `presentation/dashboard/computed.py::_sport_category`.

**Partial scale-out dahil:** Treemap hem full-close hem partial scale-out event'leri
ayrı trade olarak sayar. Her partial: invested = `sell_pct × original_size_usdc`,
pnl = `realized_pnl_usdc`. Win/Loss: pnl sign'a göre. Aynı trade'in full + partial'ı
birlikte 2 event olarak görünür.

Lokasyon: `computed.py::sport_roi_treemap` — `partial_exits` listesini iterate eder.

#### 5.7.2 Direction-Adjusted Odds Display

**Saklama invariantı** (ARCH Kural 7): `anchor_probability = P(YES)`;
`entry_price`/`current_price` = token-native (BUY_YES→YES, BUY_NO→NO).

**Display kuralları:**
- Active card `Odds X%`: `direction == "BUY_NO" ? 1 − anchor : anchor`.
- `Entry/Now` fiyatları zaten token-native → ek çevrim YOK.
- YES/NO badge metni = slug team-code:
  - BUY_YES → slug pattern'deki ilk takım (yes-side).
  - BUY_NO → ikinci takım (no-side).
  - Slug eşleşmezse fallback `"YES"` / `"NO"`.

Lokasyon: `static/js/feed.js::_activeCard` + `static/js/dashboard.js::FMT.sideCode`.

#### 5.7.3 Feed Sort

Her tab (Active/Exited/Skipped/Stock): `match_start_iso` ASC (en yakın maç
yukarıda). Boş değerler sona.

Lokasyon: `static/js/feed.js::FEED.render`.

#### 5.7.4 CSS Palette — Tek Kaynak

Renkli hex literal **sadece** `static/css/dashboard.css:root` içinde tanımlı.
Başka CSS/JS dosyasında renkli hex YASAK — hep `var(--*)`.

Değişken ailesi:
- Ana: `--green`, `--red`, `--blue`, `--orange`
- Türev: `-dim`, `-dark`, `-hover`, `-strong` (opacity/shade varyantları)
- Nötr: `--bg`, `--panel*`, `--text`, `--muted*`, `--border-soft`

JS chart renkleri (Chart.js canvas) runtime'da okur:
```js
getComputedStyle(document.documentElement).getPropertyValue("--green")
```

Böylece palette değişimi tek yerden (`:root`).

#### 5.7.5 Scanner Filter Suite (h2h scope)

Bot sadece h2h moneyline + yakın pencere + live-olmayan markets alır. Filter
sırası (`_passes_filters`):

1. **Flag kontrolü:** `closed` / `resolved` / `not accepting_orders` → ele
2. **Fiyat-based resolved detection:** `yes_price >= resolved_price_threshold`
   (default 0.98) veya `<= (1 − threshold)` → ele. Polymarket'in `closed/resolved`
   flag'leri lag'li; fiyat ~1.0/~0.0 ise sonuç kesin belli, market ölü.
3. **Strict moneyline:** `sports_market_type == "moneyline"` zorunlu. Boş string
   (PGA Top-N props) reddedilir — bookmaker h2h verisi yok, yapısal.
4. **Sport whitelist:** `config.scanner.allowed_sport_tags` (wildcard support)
5. **Min liquidity:** `min_liquidity` (default $1000)
6. **Max duration:** `end_date ≤ max_duration_days` (default 14 gün)
7. **Odds API penceresi:** `match_start ≤ max_hours_to_start` (default 24h) —
   bookmaker h2h verisi bu pencereyle sınırlı, stok gürültüsünü önler
8. **Stale match_start:** 8+ saat önce başlamış maçlar (season-long futures
   artıfakt) reddedilir

Lokasyon: `orchestration/scanner.py::MarketScanner._passes_filters`.
Config: `config.yaml` altında `scanner:` bölümü.

#### 5.7.6 Enrichment Layer — Tennis Matching

Tennis markets'de iki yaygın bug için fix:

1. **Tournament prefix strip** (`question_parser.py::extract_teams`):
   "Porsche Tennis Grand Prix: Eva Lys vs Elina Svitolina" gibi formatta
   vs-split sonrası `team_a = "Porsche Tennis Grand Prix: Eva Lys"` kirli
   kalıyordu. Fix: team_a'da ":" varsa son ":"'den sonrasını al. ATP/WTA
   prefix whitelist'i dışındaki turnuva adlarını da temizler.

2. **Slug priority sport_key resolve** (`sport_key_resolver.py::resolve_sport_key`):
   Slug `wta-*` olsa bile question'da "tennis" geçip "wta" geçmediği için
   ATP branch'ine düşüyordu (WTA Stuttgart → ATP Barcelona key). Fix: slug
   prefix otoritesi question text'ten ÖNCE kontrol edilir.

Not: Odds API tennis kapsamı haftalık ~3 major turnuva; Challenger tour /
minor events yapısal coverage gap, bu fix onları karşılamaz.

#### 5.7.8 match_start_iso Kaynağı ve Date-Aware Matching

**Tek kaynak: Gamma API `event.startTime`**. Bu alan per-match doğru saati
verir (MLB, UFC prelim/main ayrımı, tenis). Odds API `commence_time`
override **yapılmaz** — UFC'de kart saati (3-4h yanlış), MLB seri
maçlarında yanlış güne eşleşme riski var.

**Date-aware matching** (`pair_matcher.find_best_event_match`):
Odds API'den bookmaker probability çekerken aynı takım çifti birden fazla
event'te eşleşebilir (MLB/KBO seri maçları). `expected_start` parametresi
(Gamma'dan gelen `match_start_iso`) ile `commence_time`'ı beklenen tarihe
en yakın event seçilir. Tek eşleşmede etkisiz.

**Immediate persist** (`entry_processor._execute_entry`):
`add_position()` başarılı olduktan hemen sonra, `trade_logger.log()`'dan
ÖNCE `positions.json` persist edilir. Crash + restart'ta event_guard
(ARCH Kural 8) tutarlılığını korur — trade_history'de kayıt var ama
positions'ta yok senaryosunu engeller.

#### 5.7.7 Total Equity Chart — Realized-Only Stepped + Period Tabs

Chart formülü: `initial_bankroll + Σ exit_pnl_usdc` (trade history üzerinden
kümülatif). **Unrealized hariç** — açık pozisyonların anlık fiyat
dalgalanması chart'ı kirletmez.

**Veri kaynağı:** `/api/trades` (`computed.exit_events`) — full-close exit'ler
+ partial scale-out event'leri. Client kronolojik sıraya çevirip
`exit_pnl_usdc` üzerinde kümülatif toplam yapar.

**Period tabs + adaptif bucketing (2026-04-16 fix, PLAN-009):**

| Tab | Granularity | Her nokta ne? | Tipik max |
|-----|------------|----------------|-----------|
| 24h | Event | Her exit = 1 basamak | ~50 |
| 7d  | Hourly | Saat sonu kümülatif | ~168 |
| 30d | Daily | Gün sonu kümülatif | 30 |
| 1y  | Weekly (ISO) | Hafta sonu kümülatif | 52 |

Default tab: `30d`. "All" yok — sınırsız scroll'u önlemek için (lifetime PnL
Balance kartında görünür). Yoğun dilimlerde (24h/7d) canvas `overflow-x: auto`
ile scroll.

Rendering: `stepped: "before"`, `tension: 0` — yumuşak eğri yerine
basamaklı plateau.

**Neden trade-cumsum + bucketing:** Eski implementasyon `equity_history.jsonl`
snapshot'larını çiziyordu; partial exit basis-leak'i (PLAN-008) nedeniyle
identity kırılıyordu. Trade cumsum inşaat gereği identity-correct;
bucketing ise geniş dilimlerde (30d/1y) nokta yoğunluğunu ekran-dostu
seviyede tutar.

Identity (her period için): son nokta = `initial + Σ exit_pnl_usdc`
(dilim içindeki). `30d` tab'ında chart sonu = başlangıç + son 30 günün
realized PnL toplamı.

**Tab-altı PnL özeti** (yalnızca Total Equity kartında):
Format: `<strong>±$XX.XX</strong> · N trades`. Pozitif yeşil, negatif
kırmızı; rakam `tabular-nums` ile hizalı. Period prefix yok (aktif tab
zaten seçili görünür). Per Trade PnL kartında bu satır yok.

**Per Trade PnL chart:** Aynı 4 tab kullanılır; period filter uygulanır
fakat bucketing YAPILMAZ — her bar bir exit event. `waterfallMaxBars = 40`
üst limit + CSS scroll ile eski trade'lere erişim.

**Sticky y-axis** (2026-04-16, review round 3):
Canvas içindeki y-axis label'ları gizli (`scales.y.ticks.display: false`,
`afterFit: s.width = 0`). Yerine canvas DIŞINDA sabit `.chart-y-axis` DOM
element'i; Chart.js plugin `externalYAxis` her `afterUpdate`'te scale
tick'lerini DOM'a yansıtır. Scroll yapılsa bile y-axis label'ları sabit
kalır. $-prefix + kilo notation (`$1.00k`, `$20`) tabular-nums ile hizalı.
Renk: CSS `--axis-label` (x-axis ile paylaşılan tek kaynak).

**Hitbox doğruluğu:** Canvas'ın genişliği doğrudan `canvas.style.minWidth`
ile değil, parent `.chart-canvas-wrap`'in `style.width` ile set edilir.
Chart.js ResizeObserver parent wrap'i izleyip canvas internal pixel grid'i
senkron tutar → tooltip hit-detection bar sınırlarında doğru tetiklenir.

Lokasyon:
- `static/js/trade_filter.js::FILTER.cumulativeByResolution`, `.periodLabel`
- `static/js/dashboard.js::CHARTS.setEquity(trades, initialBankroll)`
- `static/js/chart_tabs.js` — `stickyScrollRight`, `externalYAxis` Chart.js plugin'leri

### 5.8 Restart Protokolleri

İki mod. Her ikisi de bot (`src.main`) + dashboard (`src.presentation.dashboard.app`) kapsar.

#### Reload (veri korunur)

1. Bot + Dashboard PID bul → `taskkill`
2. `process.lock` sil
3. `pytest -q` → FAIL varsa **DURDUR**
4. `python -m src.main --mode dry_run &`
5. `python -m src.presentation.dashboard.app &`
6. `bot_status.json` kontrol + dashboard erişim doğrula

Korunan dosyalar: `positions.json`, `trade_history.jsonl`, `circuit_breaker_state.json`, `stock_queue.json`, `equity_history.jsonl`, `skipped_trades.jsonl`.

#### Reboot (tam sıfırlama)

**Onay zorunlu.** Kullanıcıya uyarı göster: açık pozisyonlar silinecek, trade geçmişi arşivlenecek, circuit breaker sıfırlanacak. Geri alınamaz.

1. Bot + Dashboard PID bul → `taskkill`
2. `process.lock` sil
3. Arşivle: `trade_history.jsonl` → `.bak` (timestamp'li), `equity_history.jsonl` → `.bak`
4. Sıfırla: `positions.json` → `{"positions":{}, "realized_pnl":0.0, "high_water_mark":0.0}`, `circuit_breaker_state.json` / `stock_queue.json` / `skipped_trades.jsonl` sil
5. `pytest -q` → FAIL varsa **DURDUR**
6. `python -m src.main --mode dry_run &`
7. `python -m src.presentation.dashboard.app &`
8. Doğrula

**Archive Koruma (SPEC-009)**:

Reboot aşağıdaki dosyalara ASLA dokunmaz (active logs sıfırlansa bile):
- `logs/archive/exits.jsonl`
- `logs/archive/score_events.jsonl`
- `logs/archive/match_results.jsonl`

Archive retrospektif rule analysis için kullanılır. Reboot sonrası bot yeni
trade'leri bu dosyalara appending devam eder.

---


## 6. Kritik Algoritmalar

### 6.1 Bookmaker Probability

Bookmaker konsensüsünden olasılık türetir.

**Girdi:**
- `bookmaker_prob` — no-vig sonrası olasılık (0–1)
- `num_bookmakers` — toplam bookmaker ağırlığı (her bookie weighted)
- `has_sharp` — Pinnacle veya Betfair Exchange/Smarkets/Matchbook dahil mi

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
| **A** | `has_sharp = True` (Pinnacle / Betfair Exchange / Matchbook / Smarkets) ve `bm_weight ≥ 5` |
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

| Confidence | Multiplier | Efektif eşik | Not |
|---|---|---|---|
| A | 0.67 | %4 | Sharp data güvenilir → düşük eşik kabul |
| B | 1.00 | %6 | Baz eşik, daha geniş güvenlik marjı |
| C | — | — | Entry bloklanır, sizing'e ulaşmaz |

**Default `min_edge`:** `0.06` (config.yaml `edge.min_edge`)

**Exchange vig-free kuralı**: Betfair Exchange, Matchbook, Smarkets gibi exchange
bookmaker'larda vig yok — `1/price` zaten gerçek olasılığa yakın. Bu bookmaker'lara
vig normalize uygulanmaz (`odds_enricher._parse_bookmaker_markets` `skip_vig_normalize`).
Geleneksel bookmaker'larda %4-8 overround → normalize gerekli.

**Bookmaker tier'ları** (bookmaker_weights.py):

| Tier | Ağırlık | Bookmaker'lar |
|---|---|---|
| Sharp | 3.0× | Pinnacle, Betfair Exchange (EU/UK/AU), Matchbook, Smarkets |
| Reputable | 1.5× | Bet365, William Hill, Unibet, Betclic, Marathon |
| Standard | 1.0× | Diğer hepsi |

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
- **Entry price aralığı:** `[0.60, 0.88)` — alt sınır consensus.min_price, üst sınır gate.max_entry_price (bkz. §6.5 R/R gerekçesi)

**Consensus yoksa (Case B):** standart edge hesabı (§6.3) kullanılır.

### 6.5 Position Sizing

Confidence + market koşullarına göre trade boyutu.

**Base sizing (`confidence_bet_pct` — config.yaml'dan):**
| Confidence | Yüzde | Uygulama |
|---|---|---|
| A | 5% | bankroll × 0.05 |
| B | 4% | bankroll × 0.04 |
| C | — | 0 (entry bloklanır) |

**Çarpanlar (bet_pct üzerine uygulanır):**
| Koşul | Çarpan |
|---|---|
| Lossy reentry — `is_reentry = True` | × 0.80 |

**Entry price cap:** `effective_entry ≥ 0.88` → gate reddeder (`entry_price_cap`). Gerekçe: 88¢+ girişlerde max payout `0.99 − entry ≤ 0.11` → $25 pozisyon max ~$2.75 kâr; SL tetiklenirse `-$7.50`. Risk/reward çürük olduğu için strateji bağımsız kesilir.

**Formül:**
```
size = bankroll × bet_pct × multiplier(s)
size = min(size, bankroll × max_bet_pct, bankroll)
size = max(0, round(size, 2))
```

**Kaplar:**
- `max_bet_pct` = 5% bankroll (tek cap; config.yaml'dan)
- Bankroll üst sınırı (sanity)
- Polymarket minimum: $5 — altında reddet

### 6.6 Scale-Out (3-tier)

Kâr biriktikçe pozisyonun parçasını satmak.

| Tier | Tetikleyici (unrealized PnL) | Satış oranı | Amaç |
|---|---|---|---|
| 1 | ≥ +35% | 25% | Risk azaltma |
| 2 | ≥ +50% | 50% | Profit lock |
| 3 | Resolution / trailing | — | PnL-tetikli değil; §6.9-6.14 |

**Geçiş:** `tier 0 → 1 → 2` sırayla. Tier atlanmaz; ileri gider veya aynı kalır.

**Config:** Tier eşikleri ve satış oranları `config.yaml` altındaki `scale_out.tiers` listesinden okunur — hardcoded değil.

### 6.7 Flat Stop-Loss Helper (7-Katman Öncelik)

Pozisyon için flat SL yüzdesi. Katmanlar öncelik sırasıyla; ilk eşleşen döner. `None` dönerse flat SL uygulanmaz.

| # | Katman | Koşul | Sonuç |
|---|---|---|---|
| 1 | Stale price skip | `current_price ≤ 0.001` AND `current_price ≠ entry_price` | `None` (WS tick beklenir) |
| 2 | Totals/spread skip | question veya slug "o/u", "total", "spread" içerir | `None` (resolution'a kadar tut) |
| 3 | Ultra-low entry | `effective_entry < 0.09` | `0.50` (geniş tolerans) |
| 4 | Low-entry graduated | `0.09 ≤ effective_entry < 0.20` | Linear: `sl = 0.60 − t × 0.20`, `t = (eff − 0.09) / (0.20 − 0.09)` — 60% → 40% |
| 5 | B confidence | `pos.confidence == "B"` | `0.30` (tighter) |
| 6 | Sport-specific (default) | Yukarıdakiler eşleşmedi | `get_stop_loss(sport_tag)` (§7) |
| 7 | Lossy reentry modifier | `sl_reentry_count ≥ 1` | Yukarıdaki `sl × 0.75` |

**Default parametreler:** `base_sl_pct = 0.30`.

**Effective price:** `effective_price(entry_price, direction)` — direction BUY_NO ise `1 − entry_price`, aksi `entry_price`.

### 6.8 Graduated Stop-Loss (Elapsed-Aware)

Zaman/fiyat/score'a duyarlı max allowed loss.

> **Not:** PnL% hesaplamaları `pos.entry_price` ve `pos.current_price` ile direkt
> yapılır — her iki alan da token-native (owned side). `effective_price()`
> uygulanmaz. Bkz. §6.11 notu.

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
| < 0.85 (erken/orta) | **Flat SL (§6.7)**, Graduated SL (§6.8), Never-in-profit (§6.10), Hold revocation (§6.14), Edge-decay TP | Scale-out (§6.6), Near-resolve profit (§6.11), **Score exit (hockey §6.9a, tennis §6.9d, baseball §6.9e)**, Catastrophic watch (§6.9b) |
| ≥ 0.85 (geç) | Flat SL, Graduated SL | **market_flip**: `pos.current_price < 0.50` → `exit("market_flip")`; near-resolve; scale-out; **Score exit (hockey/tennis/baseball)**; Catastrophic watch |

#### 6.9a Score-Based Exit (Hockey Only — SPEC-004)

A-conf hold hockey pozisyonlarında skor + süre + fiyat kombinasyonuyla çıkış:
| Kural | Koşul | Config key |
|---|---|---|
| K1 Ağır yenilgi | deficit ≥ `period_exit_deficit` (3) | sport_rules |
| K2 Geç dezavantaj | deficit ≥ `late_deficit` (2) + elapsed ≥ `late_elapsed_gate` (0.67) | sport_rules |
| K3 Skor+fiyat | deficit ≥ `late_deficit` (2) + fiyat < `score_price_confirm` (0.35) | sport_rules |
| K4 Son dakika | deficit ≥ 1 + elapsed ≥ `final_elapsed_gate` (0.92) | sport_rules |

Backtest (9 hockey trade): mevcut -$23.24 → score exit ile +$3.70 (+$26.94 iyileşme). Kazançlara ($76.84) sıfır dokunma.

#### 6.9b Catastrophic Watch (Sadece NHL — SPEC-004 K5)

Fiyat < `catastrophic_trigger` (0.25) → watch modu → bounce + ikinci düşüş → çıkış.
Recovery 0.50+ geçerse iptal (gerçek comeback). Config: `config.yaml → exit` bölümü.
**Sadece NHL** pozisyonlarında aktif — tennis/diğer sporlarda set kaybı fiyatı düşürür
ama maç dönebilir, false positive riski yüksek (regression: Fonseca-Shelton,
Muchova-Gauff, Fernandez-Sonmez 2026-04-17).

> **Kritik invariant:** A-conf hold pozisyonları **flat SL'den de muaftır**.
> `strategy/exit/monitor.py::evaluate` sırası: near-resolve → scale-out →
> catastrophic-watch (NHL only) → A-conf hold dalı (hockey_score_exit + market_flip) →
> else branch (flat SL + graduated + vs). Flat SL a-conf check'inden ÖNCE
> konursa A-conf koruması bozulur (regression: Rangers-Lightning 2026-04-15,
> `test_a_conf_hold_skips_flat_sl`).

**Veri dayanağı** (25 A-conf resolved trade analizi):
| Senaryo | Sonuç |
|---|---|
| Market_flip kuralıyla (mevcut) | -$15.86 |
| Hold'a bekleseydik | -$126.64 |
| **Market flip farkı** | **+$110.78 tasarruf** |

Kural korunacak; elapsed gate early-match false positive'leri eler.

#### 6.9c Score Polling Altyapısı (SPEC-005)

**Primary:** ESPN public API (`site.api.espn.com`) — ücretsiz, API key gereksiz.
Hockey (gol), Tennis (set+game), MLB (koşu), NBA (sayı) skor verir.

**Fallback:** Odds API `/scores` — hockey/MLB/NBA için çalışır, tennis'te skor vermiyor.

**Adaptif polling:** Normal 60s, fiyat ≤ 35¢ → 30s. Config: `config.yaml → score`.

**Kill switch:** `score.enabled: false` → tüm skor polling durur.

#### 6.9d Tennis Score-Based Exit (SPEC-006)

ESPN set/game skoru ile tennis A-conf hold pozisyonlarda erken çıkış. BO3 only.

**T1 — Straight set kaybı:** 0-1 set + current set deficit ≥ 3 + games_total ≥ 7 (veya deficit ≥ 4).
Tiebreak buffer: 1. set dar kaybı (our ≥ 5 game, ör: 6-7) → deficit eşiği +1 (3→4).
Blowout (our < 5, ör: 2-6) → buffer yok.

**T2 — Decider set kaybı:** 1-1 set + 3. set deficit ≥ 3 + games_total ≥ 7 (veya deficit ≥ 4).
Tiebreak buffer uygulanmaz (3. set decider, tolerans yok).

Config: `sport_rules.py → tennis → set_exit_*`. Dönüş ihtimali %3-8.

**Serve-for-match (SFM):** Maç bitirici sette (T1: set 2 when 0-1, T2: set 3
when 1-1) rakip ≥ 5 game + gerideyiz → çık. Config: `set_exit_serve_for_match_games`.
Deficit eşiği ve games_total kontrolü bu durumda atlanır — rakip seti/maçı
bitirmek için 1 game uzakta, dönüş ihtimali %8-15.

#### 6.9e Baseball Score Exit (SPEC-010)

Tennis T1/T2 ve hockey K1-K4 ile simetrik: A-conf baseball pozisyonlarda FORCED exit.
Kurallar (`baseball_score_exit.py`):

| Kural | Koşul | Açıklama |
|---|---|---|
| M1 | `inning >= 7 AND deficit >= 5` | Blowout — geri dönülemez açık |
| M2 | `inning >= 8 AND deficit >= 3` | Geç aşama büyük açık |
| M3 | `inning >= 9 AND deficit >= 1` | Son inning, her deficit |

Config (`sport_rules.py`):
- `score_exit_m1_inning`, `score_exit_m1_deficit`
- `score_exit_m2_inning`, `score_exit_m2_deficit`
- `score_exit_m3_inning`, `score_exit_m3_deficit`

Sport tags: `mlb`, `kbo`, `npb`, `baseball` (hepsi aynı kurallar, default'lar).
Tetiklendiğinde `ExitReason.SCORE_EXIT` döner.

`deficit = opp_score - our_score` (pozitif = geride).

**Eski sistem (SPEC-008)**: defensive guard (SL ertele), A-conf'ta çalışmıyordu.
SPEC-010 ile kaldırıldı, yerine bu FORCED exit geldi.

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

**Tetikleyici:** `pos.current_price ≥ 0.94` (token-native, owned side)

> **Not:** `current_price` alanı zaten owned token fiyatıdır (BUY_YES → YES token,
> BUY_NO → NO token). `effective_price()` UYGULANMAZ — çift flip olur.
> Exit modüllerinde `pos.current_price` ve `pos.entry_price` direkt kullanılır.
> `effective_price()` sadece market-side YES input için (gate.py).

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

**NET PnL Takibi:** Günlük/saatlik PnL **USD cinsinden** (kazanç + kayıp net)
biriktirilir. Kontrol anında güncel `portfolio_value`'ya bölünerek yüzdeye çevrilir.
Partial exit kârları da dahildir — tüm realized PnL sayılır.

**Neden USD:** Eski yöntemde her exit'te farklı `portfolio_value`'ya bölünüp
yüzde toplanıyordu — net kârlı günlerde bile circuit breaker tetikleniyordu.
USD birikimi + anlık yüzde dönüşümü doğru net PnL verir.

**Eşikler:**
| Parametre | Değer | Etki |
|---|---|---|
| Günlük max NET loss (hard halt) | -8% | Halt + 120 dk cooldown |
| Saatlik max NET loss (hard halt) | -5% | Halt + 60 dk cooldown |
| Ardışık kayıp limiti | 4 trade | Halt + 60 dk cooldown |
| Günlük entry soft block | -3% | Soft block (entry askıya alınır ama hard halt değil) |

**`should_halt_entries(portfolio_value)` kontrol sırası:**
1. Cooldown aktif mi? → halt (kalan dk gösterilir)
2. Günlük NET loss ≤ -8% → halt 120 dk ("Daily limit hit")
3. Saatlik NET loss ≤ -5% → halt 60 dk ("Hourly limit hit")
4. Ardışık kayıp ≥ 4 → halt 60 dk ("Consecutive loss limit")
5. Günlük NET loss ≤ -3% → soft block ("Soft block (-3%)")
6. Aksi → devam

**Kritik:** Exit kararları breaker'dan asla etkilenmez — zarar artıyorsa SL tetiklenmeli.

**Exposure Cap (entry blok):**

Formül:
```
exposure = (toplam_yatırılan + aday_size) / toplam_portföy_değeri
toplam_portföy_değeri = portfolio.bankroll (nakit) + portfolio.total_invested()
```

`max_exposure_pct` (config `risk.max_exposure_pct`, default 0.50) **soft cap**'tir.
Gate ve agent, cap aşımında entry'yi tamamen reddetmek yerine **size kırparak** girer:

- `soft_cap = portfolio × max_exposure_pct` (default %50)
- `hard_cap = portfolio × (max_exposure_pct + hard_cap_overflow_pct)` (default %52)
- `available = max(0, hard_cap − total_invested)`
- `min_size = bankroll × min_entry_size_pct` (default %1.5)

**Akış:**
1. `available ≤ 0` → skip (`exposure_cap_reached`)
2. `available < min_size` → skip (tx-cost floor; komisyonla zararlı mini-pozisyon)
3. diğer → `entry_size = min(kelly, available)` ile gir

**Neden:** Kelly-sizing büyük-edge fırsatlarda cap'i aşar; tamamen reddetmek yakın
yüksek-edge pozisyonları kaybettiriyordu (2026-04-15 SF-CIN live-edge kaybı).

**Match-start ASC priority:** Agent entry loop'unda approved signal'ler
`match_start ASC, volume_24h DESC` sıralanır. Erken başlayan maçlar cap'ten
yerini önce alır; yakın maçlar cap dolmadan girer, 10h sonraki adaylar
kalan yere bakar.

**Kritik invariant:** payda TOPLAM portföy değeri — nakit değil. `portfolio.bankroll`
açık pozisyonlar düşülmüş kullanılabilir nakit olduğundan, doğrudan payda
yapılırsa pozisyon açıldıkça küçülüp cap erken tetikler.

**Pure function:** `domain/portfolio/exposure.py::available_under_cap`.
**Caller:** `strategy/entry/gate.py` + `orchestration/agent.py` her ikisi de
`pm.bankroll + pm.total_invested()` hesaplayıp geçer.
**Test:** `tests/unit/domain/portfolio/test_exposure.py` (5 test) +
`tests/unit/strategy/entry/test_gate.py` (clip testleri) +
`tests/unit/orchestration/test_agent.py` (priority testleri)

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
- Combat: MMA, UFC, Boxing (2-outcome, draw yok — mevcut pipeline uyumlu)

**MVP dışı** (draw-possible, 3-way Kelly + exit logic gerektirir):
- Soccer (tüm ligler) — `odds_enricher._parse_bookmaker_markets` 3-way aggregate
  destekler ama strategy/gate/exit 2-outcome varsayar. Whitelist'e eklenmez.
- Cricket — test match draw olasılığı
- Golf outright / Top-N — yapısal h2h değil (PGA prop bahisleri scanner'da elenir)

### 7.2 Sport-Specific Kurallar (özet)

| Sport | stop_loss_pct | match_duration_hours | Özel exit |
|---|---|---|---|
| NBA | 0.35 | 2.5 | halftime_exit @ -15 pts |
| American Football (NCAAF/CFL/UFL) | 0.30 | 3.25 | halftime_exit @ -14 pts |
| NHL (AHL/Liiga/...) | 0.30 | 2.5 | hockey_score_exit K1-K4 (deficit/elapsed/price combo) + catastrophic_watch K5 |
| MLB (+ MiLB/NPB/KBO/NCAA) | 0.30 | 3.0 | baseball_score_exit M1-M3 (inning+deficit combo — SPEC-010) |
| Tennis (ATP/WTA) | 0.35 | 1.75-3.5 (BO3/BO5) | T1/T2 set-game exit + market_flip DISABLED + catastrophic DISABLED |
| Golf (LPGA/LIV) | 0.30 | 4.0 | playoff-aware |
| DEFAULT | 0.30 | 2.0 | - |

**Not**: Detaylı sport_rules tabloları `src/config/sport_rules.py`'de tutulur. Ertelenmiş branşların kuralları için bkz. `TODO.md` TODO-001.

### 7.3 Sport Tag Doğrulama (Slug-Based Override)

Gamma API event tag'leri güvenilmez: bir event birden fazla tag taşıyabiliyor ve
ilk generic-olmayan tag seçiliyor. Tag sırası yanlışsa (ör. `ncaab` tag'i `atp-`
slug'lu bir tennis market'e atanıyor) tüm downstream akış bozulur — yanlış exit
kuralları, yanlış treemap kategorizasyonu, yanlış sport_rules seçimi.

**Savunma mekanizması** (`gamma_client._parse_market`): Market slug prefix'i
`_SLUG_PREFIX_SPORT` lookup tablosuna göre kontrol edilir. Slug prefix bilinen bir
sporu işaret ediyorsa ve event tag farklıysa → slug prefix kazanır, WARNING loglanır.

```
Öncelik: slug prefix (en güvenilir) > event tag (Gamma API sırasına bağımlı)
```

**Tablo** (infrastructure/apis/gamma_client.py):

| Slug prefix | Doğru sport_tag |
|---|---|
| atp, wta | tennis |
| nhl, ahl | hockey |
| nba, wnba | basketball |
| mlb, kbo | baseball |
| nfl, ncaaf | football |
| ufc | mma |

**Gerekçe**: 2026-04-17'de `atp-medjedo-borges` market'i Gamma'dan `ncaab` tag'iyle
geldi. Sonuç: (1) market_flip tennis hariç tutması atlandı → gereksiz kayıp, (2)
treemap'te yanlış kategori. Slug prefix override bu tür hataları kaynağında önler.

---


## 13. Açık Noktalar (ilerisi için)

1. **Golf outright futures**: Sadece H2H (`golf_lpga_tour`, `golf_liv_tour`) MVP'de. `golf_masters_tournament_winner` vb. outright'lar scope dışı.
2. **Tennis dinamik matching**: `odds_client.py`'de `_get_active_tennis_keys` + `_match_tennis_key` migrate edilecek.
3. **Baseball preseason**: `baseball_mlb_preseason` aktif ama preseason maçlarında motivasyon düşük — potansiyel bir `allow_preseason: false` flag eklenebilir.
4. **Draw-possible sporlar**: Tümü TODO-001'de. MVP'de scanner bu sport_tag'leri filter'lar.

