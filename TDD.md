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
| 6.3   | Directional Entry (SPEC-017)    | Entry gate / directional strateji        |
| 6.4   | Three-Way Entry (SPEC-015)      | 3-way entry gate                         |
| 6.5   | Position Sizing                 | Sizing                                   |
| 6.6   | Scale-Out (1-tier)              | Exit / scale                             |
| 6.7   | Flat Stop-Loss (7-Katman)       | Exit / SL                                |
| 6.9   | Market Flip Exit                | Exit (market flip)                       |
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
- Gate `exposure_cap_reached` / `max_positions_reached` / `stale` / `no_bookmaker_data` ile reddettiği marketleri stock'a push eder.
- Her heavy cycle'da Gamma scan → stock refresh (MarketData güncellenir, delist edilenler düşer) → TTL eviction.
- **JIT batch:** `empty_slots × jit_batch_multiplier` (default 3) kadar stock item match_start ASC alınır, enrich + gate pipeline'a girer. Kalan slot varsa fresh-only (stock'ta olmayan) batch ekler.
- **TTL evict:** first_seen + 24h | match_start − 30dk | event açık pozisyonda | stale_attempts ≥ 3.
- **Persistent:** `logs/stock_queue.json` — restart'ta restore.

**Rasyonel:** 300 market enrich yerine `3 × boş_slot` kadar enrich. Örnek: 4 boş slot = en yakın 12 market (stock öncelikli). Odds kredisi ~70% tasarruf + gece enrich edilmiş marketler gündüz slot açıldığında hâlâ kullanılabilir.

---

### Güvenlik Ağı

- **§6.x cluster:** Bir alt-bölüme bakacaksan, ilgili §6 komşularını gözden geçir (sizing ↔ confidence ↔ directional entry).
- **Kod okuma:** Dosya yolu, imza, import gibi sorular → doğrudan `src/` Grep + Read.
- **Mimari soru:** → ARCHITECTURE_GUARD.md.
- **Demir kural sorusu:** → PRD.md §2.

---

## 0. Temel İlkeler (Değişmez Prensipler)

1. **Veri kaynağı = bookmaker**. Odds API 20+ bahis sitesinden konsensüs üretir.
2. **3 katmanlı cycle**: WebSocket (anlık) + Light (5 sn) + Heavy (30 dk).
3. **Pozisyon boyutu confidence'a göre**: A=%5, B=%4, C=blok.
4. **Profit taking = scale-out** (1-tier).
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

Confidence, sizing multiplier'ına (→ §6.5) ve entry kararına direkt etki eder.

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

### 6.3 Directional Entry (SPEC-017)

Edge-tabanlı karar yok. Tek strateji:

1. **Direction**: bookmaker anchor'dan
   - `anchor >= 0.50` → BUY_YES, `win_prob = anchor`
   - `anchor < 0.50` → BUY_NO, `win_prob = 1 - anchor`

2. **Favorite filter**: `win_prob >= min_favorite_probability` (default %60, price floor 60¢ ile tutarlı)
   Toss-up'lar bloklu.

3. **Price cap (üst outlier)**: `effective_entry_price <= max_entry_price`
   - effective = BUY_YES ? yes_price : 1 - yes_price
   - Default üst: 80¢
   - Üstte: R/R kötü (max payout 99¢ - entry)
   - **Alt taban YOK** (post-tuning): bookmaker güçlü favori dediği maça market 30¢ fiyat verse
     bile gireriz (undervalue → pozitif edge). Tek gerçek filtre bookmaker %60 şartı.

4. **Diğer guards** (event, liquidity, manipulation, exposure cap): değişmez

5. **Stake** (SPEC-016): `bankroll × bet_pct × win_prob`

**Neden edge kaldırıldı:** Market efficient dönemlerde (Polymarket ≈ bookmaker) edge eşiği çok az maçı geçiriyor, volume düşüyor. Directional entry bookmaker lider varsayımıyla favoriye girer, stake win_prob ile orantılı olduğu için varyans kontrollü kalır.

**Neden alt fiyat tabanı yok:** Bookmaker güçlü favori diyor ama Polymarket fiyatı düşük = piyasa underprice yapıyor = bizim lehimize edge. Bu girişi engellemek mantıksız.

**Geçmiş not:** Önceki sistem A-conf için %6 unified edge eşiği kullanıyordu (SPEC-010 rollback + Bug #2 fix). Market efficient dönemlerde bu eşik neredeyse hiç maçı geçirmediğinden SPEC-017 ile kaldırıldı. min_entry_price de post-tuning ile kaldırıldı (bookmaker tutarsızlık giderildi).

**Config:** `entry.min_favorite_probability`, `entry.max_entry_price`.

### 6.4 ThreeWayEntry (SPEC-015)

Soccer/rugby/AFL/handball: event_id paylaşan 3 market (Home/Draw/Away) `EventGrouper` ile
gruplanır. `three_way.evaluate()` karar verir:

1. Bookmaker'ın 3 outcome arasında en yüksek olasılığına göre favori seç
2. Tie-break: eşitlik → SKIP
3. Absolute threshold: `favorite_prob >= 0.40` (3-way için kalibre, 2-way'deki %55'in karşılığı)
4. Relative margin: `favorite - second_highest >= 0.07` (tossup'ları eler)
5. Price cap (üst outlier): `favorite market yes_price <= max_entry_price (0.80)` — alt taban yok (directional entry ile aynı mantık)

**Live direction switch yok** — pozisyon açıldıktan sonra outcome değiştirme yok.
**Underdog/draw value bet yok** — sadece favori tarafa gir (varyans azaltma).

Scanner'a `sum_filter` (3 market'in yes_price toplamı 0.95-1.05) eklendi —
double chance/handicap/special market'leri eler.

### 6.5 Position Sizing (SPEC-010 + SPEC-016)

Stake hesabı:
```
stake = bankroll × confidence_bet_pct × win_prob   (SPEC-016)
      capped by max_single_bet_usdc ($75)
      capped by bankroll × max_bet_pct (%5)
      floored by Polymarket $5 min-order
```

`win_prob` = direction-adjusted probability:
- `BUY_YES` → `anchor_probability` (P(YES))
- `BUY_NO`  → `1 - anchor_probability`

P(YES) her zaman anchor olarak saklı (ARCH_GUARD Kural 8). Direction-adjustment sadece sizing hesabında `effective_win_prob(anchor, direction)` helper'ı ile uygulanır.

**Neden win_prob ile çarpılır:** Yüksek-olasılıklı girişler daha büyük stake alır, düşük-olasılıklı girişler daha küçük. Zamana göre sıralı bet-pct sizing'in yarattığı "kaybetme ihtimali yüksek olana çok para" anomalisini çözer. Variance contribution favori pozisyonlarda artar, underdog'larda azalır (Quarter-Kelly benzeri muhafazakâr ağırlıklandırma).

Config flag: `risk.probability_weighted: true` (false → eski base-only formül, rollback).

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

**Kaplar:**
- `max_bet_pct` = 5% bankroll (tek cap; config.yaml'dan)
- Bankroll üst sınırı (sanity)
- Polymarket minimum: $5 — altında reddet

### 6.6 Scale-Out (Midpoint-to-Resolution) — SPEC-013

Config-driven tier listesi. Her tier'da:
- `threshold`: entry ile 0.99 arasındaki mesafenin fraction'ı. 0.50 = midpoint.
- `sell_pct`: tier tetiklendiğinde satılacak pozisyon %'si.

**Trigger formülü** (pure, `scale_out.py`):
```
max_distance = 0.99 - entry_price
current_distance = current_price - entry_price
distance_fraction = current_distance / max_distance
if distance_fraction >= tier.threshold AND not yet triggered: SELL
```

**Örnek** (default threshold 0.50, 40% sell):
| Entry | Trigger price | Locked PnL ($45 stake) |
|---|---|---|
| 0.30 | 0.645 | ≈$14 |
| 0.43 | 0.71 | ≈$11 |
| 0.70 | 0.845 | ≈$8 |
| 0.80 | 0.895 | ≈$4 |

**Geçiş:** `tier 0 → 1`. Tier 1 tetiklendikten sonra kalan pozisyon near-resolve veya SL'ye kalır.

**Eski semantik**: `unrealized_pnl_pct >= threshold` — entry fiyatına göre
adaletsizdi (43¢ entry'de +%15 PnL = 49¢ fiyat, 70¢ entry'de = 80¢ fiyat).
Yeni semantik her entry için adil (distance-based).

**Direction-aware**: `entry_price` ve `current_price` effective prices
(BUY_YES için yes_price, BUY_NO için no_price). Position model'de zaten
böyle saklanır (`src/models/position.py`).

**Config:** Tier eşikleri ve satış oranları `config.yaml` altındaki `scale_out.tiers` listesinden okunur — hardcoded değil. `check_scale_out` fonksiyonu N-tier listeyi destekler; gelecekte tier eklenebilir. Near-resolve (§6.11, 94¢) priority olduğundan tier eşiği near-resolve'den düşük tutulur; aksi halde sıçrayan spor fiyatlarında by-pass olur.

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

### 6.9 Market Flip Exit

A3 score-only spec (2026-04-20) sonrasında: A-conf hold branching + is_a_conf_hold
kaldırıldı. Tüm pozisyonlar aynı zinciri takip eder; score-based exit tüm confidence
sınıflarında gerekli tüm sporlar için tetiklenir. Market flip ayrı bir geç-faz guard.

**Market flip koşulu** (tüm sporlar, tennis hariç):
- `elapsed_pct ≥ 0.85` AND `effective_price(pos.current_price, pos.direction) < 0.50`
- → `exit("market_flip")`

**Tennis immune**: Set yapısı fiyatı volatil yapar (set kaybı %40-50 düşüş normal),
false positive riski yüksek. Tennis için sadece T1/T2/SFM score exit tetiklenir.

**SPEC-004 K5 catastrophic_watch**: A3 ile kaldırıldı (2026-04-20). Regression
deneyimi (Fonseca-Shelton, Muchova-Gauff, Fernandez-Sonmez 2026-04-17): set/period
kaybı fiyatı düşürür ama maç dönebilir — score-based exit daha güvenli sinyal.

#### 6.9a Score-Based Exit (Hockey Family — SPEC-004, SPEC-014)

Hockey pozisyonlarında skor + süre + fiyat kombinasyonuyla çıkış (A3 sonrası tüm
confidence sınıflarında aktif):
| Kural | Koşul | Config key |
|---|---|---|
| K1 Ağır yenilgi | deficit ≥ `period_exit_deficit` (3) | sport_rules |
| K2 Geç dezavantaj | deficit ≥ `late_deficit` (2) + elapsed ≥ `late_elapsed_gate` (0.67) | sport_rules |
| K3 Skor+fiyat | deficit ≥ `late_deficit` (2) + fiyat < `score_price_confirm` (0.35) | sport_rules |
| K4 Son dakika | deficit ≥ 1 + elapsed ≥ `final_elapsed_gate` (0.92) | sport_rules |

Backtest (9 hockey trade): mevcut -$23.24 → score exit ile +$3.70 (+$26.94 iyileşme). Kazançlara ($76.84) sıfır dokunma.

**NHL / AHL Hockey Ailesi (SPEC-014):** `SPORT_RULES["ahl"]` NHL eşiklerini spread ile
paylaşır; sadece `espn_league` farklı. `hockey_score_exit._is_hockey_family` tek set
(`{"nhl", "ahl"}`) ile kontrol eder. `monitor.py` AHL + NHL için aynı çağrıyı yapar.
Eşik drift imkansız: NHL K1-K4 değişirse AHL otomatik takip eder.

#### 6.9c Score Polling Altyapısı (SPEC-005)

**Primary:** ESPN public API (`site.api.espn.com`) — ücretsiz, API key gereksiz.
Hockey (gol), Tennis (set+game), MLB (koşu), NBA (sayı) skor verir.

**Fallback:** Odds API `/scores` — hockey/MLB/NBA için çalışır, tennis'te skor vermiyor.

**Adaptif polling:** Normal 60s, fiyat ≤ 35¢ → 30s. Config: `config.yaml → score`.

**Kill switch:** `score.enabled: false` → tüm skor polling durur.

**Archive score_at_exit (SPEC-014):** `score_enricher._match_cached` eşleşme bulunca
`pos.match_score` ve `pos.match_period` yazar. `exit_processor._log_exit_to_archive`
zaten `pos.match_score or ""` okuyordu; SPEC-014 öncesi yazan yoktu → 13/13 archive
kaydı boştu. Şimdi dolu, retrospektif score-exit analizi kullanılabilir.

#### 6.9d Tennis Score-Based Exit (SPEC-006)

ESPN set/game skoru ile tennis pozisyonlarda erken çıkış (A3 sonrası tüm confidence sınıflarında). BO3 only.

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

**Inning Kaynağı (SPEC-014):** ESPN response `status.period` field'ı inning'i int olarak
verir (1-9+, 0=pregame). `status.type.description` dilsel ("Top of 5th", "In Progress") —
format değişken, regex parse güvensiz. SPEC-014 öncesi `_parse_inning` regex `(\d+)(?:st|nd|rd|th)`
M1/M2/M3'ü tetiklemiyordu (audit: 13 exit kaydında tek score-exit yok).
Fix: `ESPNMatchScore.inning: int | None` (baseball dışında None); `_parse_inning` ve
`_INNING_RE` kaldırıldı (dead code).

#### 6.9f Cricket Score Exit (SPEC-011)

Tennis T1/T2, hockey K1-K4, baseball M1/M2/M3 ile simetrik. A-conf
pozisyonlar için FORCED exit. Sadece 2. innings (chase) + biz chasing
tarafındaysak (our_chasing=True) C1/C2/C3 tetiklenir.

**Kurallar** (`cricket_score_exit.py`):

- **C1**: `balls_remaining < c1_balls AND required_rate > c1_rate` (impossible chase)
- **C2**: `wickets_lost >= c2_wickets AND runs_remaining > c2_runs` (çok wicket kaybı)
- **C3**: `balls_remaining < c3_balls AND runs_remaining > c3_runs` (final over + gap)

**Config** (`sport_rules.py`):
- T20 default: c1_balls=30, c1_rate=18, c2_wickets=8, c2_runs=20, c3_balls=6, c3_runs=10
- ODI gevşek: c1_balls=60, c1_rate=12, c2_wickets=8, c2_runs=40, c3_balls=30, c3_runs=30

**Skor kaynağı**: CricAPI free tier 100 hit/gün (ESPN cricket yok).
Limit dolunca entry gate `cricapi_unavailable` skip eder.

**Direction-aware**: `our_chasing` = bizim takımımız 2. innings'te mi batting.
Defending tarafındaysak (our_chasing=False) C1/C2/C3 skip — chase çökmek
BİZİM lehimize.

#### 6.9g Soccer Score Exit (SPEC-015)

Tennis T1/T2, hockey K1-K4, baseball M1/M2/M3, cricket C1/C2/C3 ile simetrik.
A-conf pozisyonlar için FORCED exit. Sport config (SOCCER_CONFIG) parametrelerini
kullanır (DRY — aynı fonksiyon rugby/AFL/handball için de çalışır, sadece
config farklı).

**HOME/AWAY pozisyon**:
- 0-65' HOLD (comeback potential korunur)
- 65'+ 2 gol geride → EXIT
- 75'+ 1 gol geride → EXIT

**DRAW pozisyon**:
- 0-70' 0-0 → HOLD (draw değeri zirvede)
- 75'+ herhangi gol → EXIT (draw cliff)
- Knockout + 90+stoppage → AUTO-EXIT (uzatma+pen draw'ı bitirir)

**Tasarım kararları**:
- Red card özel exit YOK — ESPN reliability belirsiz + gol sonrası zaten
  market flip yaşanır, score exit yakalar.
- First-half lock 0-65': soccer comeback rate (0-1 HT) ~%25-30, erken çıkmak
  EV'den zarar.
- Knockout flag: position.tags veya question'dan tespit ("Cup", "Champions
  League", "Final", vs.).

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
| Aradaki (`0.75 ≤ ratio < 0.90`) | Flat SL (§6.7) devralır |

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

**Davranış:** `favored = True` pozisyonlar market_flip + score_exit zinciri üzerinden yönetilir (§6.9) — state tracking FAV promotion/demotion için, ayrı exit branch değil (A3 sonrası A-conf hold kaldırıldı).

**Veri dayanağı:** 5 favored trade = **+$42.90, %100 WR** — sistem korunacak.

### 6.14 Hold Revocation

Non-favored pozisyonlar için hold iptali — ciddi fiyat düşüşü + skor dezavantajı altında (A3 sonrası A-conf hold branch'i yok).

**Hold candidate:**
- `favored` OR (`anchor_probability ≥ 0.65` AND `confidence ∈ {A, B}`)

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

**Neden:** Büyük pozisyonlar cap'i aşar; tamamen reddetmek yakın
yüksek-olasılıklı pozisyonları kaybettiriyordu (2026-04-15 SF-CIN kaybı).

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
- American Football: NFL, NCAAF, CFL, UFL
- Tennis: Tüm ATP/WTA turnuvaları (dinamik matching)

**Not**: MMA TODO-002, Golf TODO-003 altında — canlı skor kaynağı olunca ele alınacak.

**MVP dışı** (draw-possible, 3-way Kelly + exit logic gerektirir):
- Soccer (tüm ligler) — `odds_enricher._parse_bookmaker_markets` 3-way aggregate
  destekler ama strategy/gate/exit 2-outcome varsayar. Whitelist'e eklenmez.
- Cricket — test match draw olasılığı

### 7.2 Sport-Specific Kurallar (özet)

| Sport | stop_loss_pct | match_duration_hours | Özel exit |
|---|---|---|---|
| NBA | 0.35 | 2.5 | nba_score_exit N1/N2 (elapsed + deficit — A3) |
| NFL | 0.30 | 3.25 | nfl_score_exit N1/N2 (elapsed + deficit — A3) |
| American Football (NCAAF/CFL/UFL) | 0.30 | 3.25 | late-game deficit exit |
| NHL (AHL/Liiga/...) | 0.30 | 2.5 | hockey_score_exit K1-K4 (deficit/elapsed/price combo) |
| MLB (+ MiLB/NPB/KBO/NCAA) | 0.30 | 3.0 | baseball_score_exit M1-M3 (inning+deficit combo — SPEC-010) |
| Tennis (ATP/WTA) | 0.35 | 1.75-3.5 (BO3/BO5) | T1/T2 set-game exit + market_flip DISABLED |
| cricket_ipl | 0.30 | 3.5 | C1/C2/C3 (T20) |
| cricket_odi | 0.30 | 8.0 | C1/C2/C3 (ODI, gevşek) |
| cricket_international_t20 | 0.30 | 3.5 | C1/C2/C3 (T20) |
| cricket_psl | 0.30 | 3.5 | C1/C2/C3 (T20) |
| cricket_big_bash | 0.30 | 3.5 | C1/C2/C3 (T20) |
| cricket_caribbean_premier_league | 0.30 | 3.5 | C1/C2/C3 (T20) |
| cricket_t20_blast | 0.30 | 3.5 | C1/C2/C3 (T20) |
| soccer | 0.30 | 2.0 | soccer_score_exit (HOME/AWAY 65'+ + DRAW 70'+) — SPEC-015 |
| rugby_union | 0.30 | 1.75 | blowout 50'+ 14pt, late 70'+ 7pt |
| afl | 0.30 | 2.0 | blowout 60'+ 30pt, late 75'+ 15pt |
| handball | 0.30 | 1.5 | blowout 45'+ 8goals, late 55'+ 4goals |
| DEFAULT | 0.30 | 2.0 | - |

**Not**: Detaylı sport_rules tabloları `src/config/sport_rules.py`'de tutulur. Soccer/rugby_union/afl/handball SPEC-015 ile eklendi. Ertelenmiş branşlar için bkz. `TODO.md` TODO-001.

#### 7.2.1 NBA Score Exit (A3)

- N1: elapsed ≥ 0.75 + deficit ≥ 20 (Q3 sonu + ağır fark)
- N2: elapsed ≥ 0.92 + deficit ≥ 10 (son dakikalar + 2 possession)

Threshold'lar sport_rules.py'den okunur.

#### 7.2.2 NFL Score Exit (A3)

- N1: elapsed ≥ 0.75 + deficit ≥ 21 (3-skor farkı)
- N2: elapsed ≥ 0.92 + deficit ≥ 11 (2-possession, son 5dk)

Threshold'lar sport_rules.py'den okunur.

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

**Tablo** (infrastructure/apis/gamma_client.py — config.scanner.allowed_sport_tags ile hizalı):

| Slug prefix | Doğru sport_tag | Not |
|---|---|---|
| atp, wta | tennis | generic `tennis` + `atp*`/`wta*` wildcard whitelist'te |
| nhl, ahl, liiga, mestis, shl, allsvenskan | (prefix = kendisi) | specific lig — SPEC-003 `hockey` generic kaldırılmış (KHL coverage yok) |
| nba, wnba, ncaab, wncaab, cbb, euroleague, nbl | (prefix = kendisi) | specific lig — SPEC-003 `basketball` generic kaldırılmış (CBA/KBL/VTB coverage yok) |
| mlb, milb, npb, kbo | baseball | generic `baseball` whitelist'te |
| ncaaf, cfl, ufl, nfl | (prefix = kendisi) | specific lig — `football` generic whitelist'te yok; NFL MVP dışı (TODO-001) — tag="nfl" whitelist'te olmadığı için scanner ele alır |
| ufc, mma | mma | generic `mma` whitelist'te |
| boxing | boxing | `boxing` whitelist'te |
| lpga, liv, pga | (prefix = kendisi) | `lpga*`/`liv*`/`pga*` wildcard whitelist'te |

**Gerekçe**: 2026-04-17'de `atp-medjedo-borges` market'i Gamma'dan `ncaab` tag'iyle
geldi (ters yön: spor A slug, spor B tag). Ek olarak 2026-04-19'da tespit edildi
ki gamma NBA event'lerini team tag'iyle (`raptors`, `magic` vb.) gönderiyor ve
önceki tablo `nba → basketball` mapping'i sport_tag'i whitelist'te olmayan
`basketball` generic'e çeviriyordu — NBA/NHL/NFL market'leri yanlışlıkla
filtreleniyordu. Değerlerin config whitelist'iyle hizalanması bu bug'ı çözer.

---


## 13. Açık Noktalar (ilerisi için)

1. **Golf outright futures**: Sadece H2H (`golf_lpga_tour`, `golf_liv_tour`) MVP'de. `golf_masters_tournament_winner` vb. outright'lar scope dışı.
2. **Tennis dinamik matching**: `odds_client.py`'de `_get_active_tennis_keys` + `_match_tennis_key` migrate edilecek.
3. **Baseball preseason**: `baseball_mlb_preseason` aktif ama preseason maçlarında motivasyon düşük — potansiyel bir `allow_preseason: false` flag eklenebilir.
4. **Draw-possible sporlar**: Soccer/rugby/AFL/handball SPEC-015 ile eklendi. Kalan (Cricket Test, Boxing, NFL draw) TODO-001'de.

