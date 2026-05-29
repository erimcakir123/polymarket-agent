# DECISIONS.md
> Kalibrasyon değerleri, threshold'lar ve "neden bu sayı" notları.
> Kod ne yaptığını anlatır. Bu dosya neden öyle yapıldığını anlatır.
> Her threshold değişikliğinde bu dosya da güncellenir (CLAUDE.md drift tablosu).

> **Yapı (2026-05-19 itibarıyla):**
> - **§A — CURRENT STATE**: Botun ŞU AN nasıl çalıştığı (kod-doğrultusunda snapshot). DECISIONS.md'den 2026-05-19'da merge edildi (PLAN-MIGRATION-001).
> - **§B — KRONOLOJIK LOG**: SPEC-K/J/I/... tarihli kararlar — "neden buraya geldik" arşivi.
> - Drift varsa: kod aslolan, CURRENT STATE güncellenir.

---

# §A — CURRENT STATE (Bot Davranışları, Code Snapshot)

> Bu bölüm botun ŞU AN nasıl çalıştığını anlatır.
> Numara şeması §0/§5.7/§6.X/§7/§13'ü ve eski PRD §1-§8 başlıklarını korur —
> eski kod yorumlarındaki "DECISIONS §X" ve "PRD §X" referansları geçerlidir.

---

## Vizyon

Polymarket Agent 2.0, Polymarket tahmin piyasalarında otomatik trading yapan bir bot. Odds API üzerinden 20+ bookmaker'ın konsensüs olasılığını çıkarır, Polymarket'teki piyasa fiyatıyla karşılaştırarak pozitif beklenen değer (edge) tespit eder, çok katmanlı risk yönetimiyle pozisyon açar ve yönetir.

Tek cümlede: **Bookmaker konsensüsü + piyasa fiyatı fırsatı → boyutlandır → aç → izle → çık.**

---

## Demir Kurallar

Bu kuralların hiçbiri ihlal edilemez. Her biri ya mimari bütünlüğü ya da sermaye güvenliğini korur.

### 1. P(YES) Anchor Kuralı
Olasılık her zaman P(YES) olarak saklanır. BUY_YES de BUY_NO da olsa, `anchor_probability = P(YES)` değişmez. Yön ayarlaması karar mantığında yapılır, saklama yapılmaz. (bkz. ARCHITECTURE_GUARD Kural 7)

### 2. Event-Level Guard
Aynı `event_id`'ye sahip max N pozisyon (default N=3, `config.yaml > risk.max_positions_per_event`). Bağımsız market'ler (moneyline + spread + totals) ayrı bahisler sayılır. (bkz. ARCHITECTURE_GUARD Kural 8, DECISIONS §6.18)

### 3. Confidence-Based Sizing (SPEC-P 2026-05-21 — fixed-tier)
Pozisyon boyutu confidence tier'e göre **sabit dolar** (bankroll dalgalanmasından bağımsız):
- **A**: $50 sabit
- **B**: $30 sabit
- **C**: giriş yapılmaz (blok)

Manipulation medium risk × 0.5 indirimi uygulanır. Polymarket min $5 floor. (bkz. DECISIONS §6.5)

### 4. Bookmaker-Derived Probability
P(YES), Odds API'den çekilen bookmaker verisiyle hesaplanır. Pinnacle/Betfair gibi sharp book'lar `bookmaker_weights` ile ağırlıklandırılır. (bkz. DECISIONS §6.1)

### 5. 3-Katmanlı Cycle
Bot üç cycle seviyesinde çalışır:
- **WebSocket**: anlık fiyat tick (SL + scale-out)
- **Light (5 sn)**: hızlı çıkış kontrolü
- **Heavy (30 dk)**: scan + enrichment + entry kararları

Heavy cycle içinde light cycle interleave eder. Gece modunda (UTC 08-13) heavy 60 dk'ya uzar. Adaptive cycle: maç başlangıcına yakın (≤3h) cycle 15 dk, ≤1h imminent 10 dk'ya iner.

### 6. Circuit Breaker
Aşağıdaki eşiklerden birinde bot yeni giriş yapmaz:
- Günlük kayıp ≥ %8 → 120 dk cooldown
- Saatlik kayıp ≥ %5 → 60 dk cooldown
- 4 ardışık kayıp → 60 dk cooldown
- Soft blok: günlük kayıp ≥ %3 → yeni giriş askıda

**Default `enabled: true`. Test/gözlem modu için `config.yaml > circuit_breaker.enabled: false` ile devre dışı bırakılabilir** (2026-05-19, commit cdf57c9). Multi-SL (flat + graduated) maç-içi korumayı sağlar. Production'da enabled tutulması önerilir. (bkz. DECISIONS §6.15)

### 7. Scale-Out Profit-Taking
Kâr alma tek mekanizma ile: 3-tier scale-out.
- **Tier 1**: PnL ≥ %25 → pozisyonun %40'ını sat
- **Tier 2**: PnL ≥ %50 → kalan pozisyonun %50'sini sat
- **Tier 3**: Resolution'a kadar hold

(bkz. DECISIONS §6.6)

---

## Operasyonel Akışlar

### Bot Başlatma Akışı
1. `main.py` argparse (mode: dry_run | paper | live) ve config.yaml yükler.
2. `orchestration/process_lock.py` tek instance garantisi verir.
3. `orchestration/startup.py` wallet'i bağlar, persistence'ı açar, açık pozisyonları JSON store'dan geri yükler.
4. `agent.py` ana döngüyü başlatır → heavy cycle tetiklenir.

### Entry Akışı (Heavy Cycle)
1. **Scan**: `scanner.py` Polymarket Gamma'dan `allowed_sport_tags` filtreli market'ler çeker.
2. **Stock housekeeping**: persistent pool; TTL ile expire edilir (match_start − 30dk, 24h idle, 3× no_edge, event açık).
3. **JIT pipeline**: Stock top-N (match_start ASC) + fresh-only top-M → gate'e yalnızca bu batch girer.
4. **Match**: `domain/matching/` modülleri Polymarket market'ini Odds API sport key'ine eşler.
5. **Enrich**: `strategy/enrichment/odds_enricher.py` Odds API'dan bookmaker probability çeker.
6. **Gate**: `strategy/entry/gate.py` event-guard + manipulation + liquidity + confidence + edge + entry_price_cap kontrolü yapar.
7. **Size**: `domain/risk/position_sizer.py` confidence bazlı boyut üretir, cap'lere uygular.
8. **Execute**: `infrastructure/executor.py` CLOB client üzerinden emri gönderir (dry_run modunda loglar).
9. **Record**: Pozisyon JSON store'a yazılır, trade log JSONL'e eklenir. Exposure cap aşımında signal size kırpılarak girilir.

### Light Cycle İzleme (5 sn)
1. WebSocket tick'lerinden son fiyatlar okunur.
2. Açık pozisyonlar için flat SL, graduated SL, scale-out, near-resolve kontrolü yapılır.
3. Tetiklenen çıkış sinyali varsa `exit/monitor.py` üzerinden ilkine göre emir gönderilir.

**Scanner filter scope** (SPEC-J post-rollback): moneyline + spreads + totals; basketbol için spreads/totals geçer (NBA spread BLOK), NHL ML-only; `match_start ≤ 24h` (Odds API penceresi), `yes_price < 0.98` (fiyat-based resolved detection). Detay: DECISIONS §5.7.5.

### Exit Akışı (Light + Heavy Cycle)
Tüm pozisyonlar için koşulsuz multi-SL zinciri (Faz 1 rollback 2026-05-15 sonrası):
1. **Near-Resolve**: eff_price ≥ 94¢ + 10 dk pre-match guard + spread sanity (SPEC-M) → çık (DECISIONS §6.11)
2. **Scale-out**: PnL +25%/+50% tier'larda kısmi sat (DECISIONS §6.6)
3. **NBA Totals dispatch** (basketbol totals için): structural/predictive/empirical exits
4. **Flat SL**: sport-specific eşik (NBA 0.35, MLB/NHL/diğer 0.30) (DECISIONS §6.7)
5. **Graduated SL**: elapsed-aware dinamik (DECISIONS §6.8)
6. **Never-in-Profit Guard**: peak_pnl hiç pozitif olmamış + elapsed > %70 → daha agresif (DECISIONS §6.10)
7. **Hold revocation**: hold candidate için fiyat düşüşü + skor dezavantajı → exit (DECISIONS §6.14)

> A-Conf Hold dalı (eski §6.9) 2026-05-15 Faz 1 rollback'te TAMAMEN kaldırıldı. Multi-SL universal.

### Circuit Breaker Tetiklendiğinde
1. `circuit_breaker.py` bankroll durumunu her entry öncesi kontrol eder.
2. Eşik aşılırsa yeni entry reddedilir, log + Telegram bildirimi.
3. Cooldown süresi dolana kadar bot sadece **çıkış** kararları alır (açık pozisyon yönetimi devam).
4. Cooldown sonrası otomatik devreye girer.

---

## Fonksiyonel Gereksinimler

8 yetenek grubu. Detaylar §6/§7'de.

### F1. Scan
Polymarket Gamma API'dan canlı market keşfi. `allowed_sport_tags` filtresi. Max `max_markets_per_cycle=500` limiti (24 saat içindeki tüm eligible maçlar). (`src/orchestration/scanner.py`)

### F2. Enrich
Her adaya Odds API'dan bookmaker verisi. `domain/matching/` Polymarket slug'ını Odds API sport key'ine dönüştürür. `bookmaker_weights.py` sharp book'ları ağırlıklandırır. (bkz. DECISIONS §6.1)

### F3. Entry Decision
`strategy/entry/gate.py` 3 entry stratejisi orchestrate eder: consensus (bookmaker+market aynı favori), early_entry (6+ saat öncesi), normal. Öncelik: consensus → early → normal (ilk Signal kazanır). (bkz. DECISIONS §6.4)

### F4. Position Sizing
Fixed-tier (SPEC-P): A=$50, B=$30, C=blok. Manipulation medium × 0.5. Polymarket min $5. (bkz. DECISIONS §6.5)

### F5. Execute
`executor.py` 3 modda çalışır: `dry_run` (log-only), `paper` (mock fills), `live` (gerçek CLOB emri). Her emir trade log'a JSONL formatında yazılır.

### F6. Monitor
3 katmanlı izleme: WS tick (anlık), Light cycle (5 sn), Heavy cycle (30 dk). Pozisyon durumu JSON store'da, dashboard anlık okur.

### F7. Exit
Çıkış kararı birden fazla mekanizmanın değerlendirmesiyle. İlk tetiklenen sinyal uygulanır. Tam liste DECISIONS §6.6-§6.14.

### F8. Report
3 sunum kanalı: Flask dashboard (localhost:5050), Telegram bildirim (entry/exit/CB), JSONL trade log (audit).

**Dashboard scope**:
- **Özet metrikler** (5 kart): Balance, Open P&L, Realized P&L (W/L alt-yazı), Locked in Bets, Peak Balance (drawdown%)
- **Koruma + analiz** (3 kart): Loss Protection (RISK gauge + status), Positions (slot gauge + entry_reason), Branches (sport/league ROI treemap)
- **Grafikler** (2): Total Equity zaman serisi (realized-only stepped, period tabs 24h/7d/30d/1y), Per-Trade PnL waterfall
- **Trades feed** (sağ panel, 4 sekme): Active | Exited | Skipped | Stock
- **Cycle bar** (topbar): Hard cycle (mavi) + Light cycle (teal)

**Kaldırılan**: API Usage paneli, Performance paneli, AI vs Bookmaker paneli (sonraki faza ertelendi).

---

## Non-Fonksiyonel Gereksinimler

### Latency
- Heavy cycle ≤ 30 sn (scan + enrichment + entry decision)
- Light cycle ≤ 1 sn (SL + scale-out kontrolü)
- WebSocket tick → exit decision ≤ 500 ms

### Uptime
- MVP hedefi: 48 saat kesintisiz dry_run
- WebSocket disconnect → 30 sn içinde reconnect (SPEC-I stale watchdog)

### Crash Recovery
- `startup.py` açık pozisyonları `positions.json`'dan geri yükler
- Trade log JSONL append-only, crash'ten sonra replayable
- Process lock çift instance engeller

### Observability
- Flask dashboard: pozisyonlar, PnL, circuit breaker durumu, < 3 sn gecikme, 5 sn polling
- Bot durumu her tick `data/bot_status.json`'a yazılır
- Trade history append + exit update atomic
- Equity history her heavy cycle sonunda `equity_history.jsonl`'e
- Skipped adaylar `skipped_trades.jsonl`'e
- Stock queue her heavy cycle sonunda `stock_queue.json`'a dump (restart restore)
- Telegram: entry/exit/CB olayları

### Çalışma Modları
- `dry_run`: API çağrıları canlı, emir gönderimi yok — default test modu
- `paper`: mock fills, bankroll simülasyonu
- `live`: gerçek emir + gerçek USDC

### Test Kapsamı (ARCH_GUARD Kural 15)
- Domain: > %80 coverage
- Strategy: > %75 coverage
- Orchestration: > %60 coverage
- Infrastructure: > %50 coverage

---

## Teknik Kısıtlar

### API Limitleri
- **The Odds API**: 20K kredi/ay (paid tier), her `fetch_odds` 1-10 kredi
- **Polymarket CLOB REST**: ~100 istek/dk
- **Polymarket Gamma**: rate limit belirsiz, ~300 market/cycle güvenli
- **Telegram**: 30 mesaj/sn

### Altyapı
- **Chain**: Polygon mainnet
- **Ödeme**: USDC (6 decimal)
- **Python**: 3.12+
- **OS**: Linux (production), Windows (dev)

### Cycle Süreleri
- Heavy: 30 dk (gündüz), 60 dk (gece UTC 08-13). Adaptive: near (≤3h) 15dk, imminent (≤1h) 10dk
- Light: 5 sn
- WebSocket: sürekli (disconnect + reconnect)

### Market Filtreleme
- Min likidite: $1000
- Max süre: 14 gün
- Allowed categories: `sports` (yalnızca)
- Allowed sport_tags (kısa liste, ayrıntı için §7.1): MLB/KBO/NPB/MiLB/NCAA baseball, NBA/WNBA/NCAAB/Euroleague/NBL basketball, NHL hockey (ML-only), NCAAF/CFL/UFL football, MMA/UFC/Boxing combat, LPGA/LIV/PGA H2H golf. Tennis ana botta KAPALI (steril ayrım — tennis lab `feature/tennis-lab` branch'ında, 2026-05-23); `sport_rules.py`'de entry korunur (açık tenis pozisyonların ESPN `match_start_iso` refresh'i için).

### Savunma Mekanizmaları (cross-ref)
- Manipulation Guard → §6.16
- Liquidity Check → §6.17
- Circuit Breaker → §6.15
- Event-Level Guard → §6.18

---

## Sözlük

| Terim | Tanım |
|---|---|
| **anchor** / `anchor_probability` | Bookmaker konsensüsünden hesaplanan P(YES). Pozisyon yönünden bağımsız saklanır. |
| **P(YES)** | Polymarket market'indeki YES outcome'unun olasılığı (0.0 – 1.0) |
| **edge** | Piyasa fiyatı ile anchor arasındaki beklenen değer farkı (`anchor − market_price` BUY_YES için) |
| **eff_price** | Effective price — market-side YES input için (gate.py). Exit modüllerinde KULLANILMAZ (DECISIONS §6.11 notu). |
| **direction** | `BUY_YES` / `BUY_NO` / `HOLD` — Direction enum |
| **confidence** | `A` (sharp book var + `bm_weight ≥ 5`) / `B` (`bm_weight ≥ 5`, sharp yok) / `C` (yetersiz, giriş blok) |
| **favored** | Pozisyonun elverişli durumda olduğunu işaretleyen flag (eff ≥ 65¢ + conf ∈ {A,B}). Faz 1 rollback sonrası exit davranışını değiştirmez (state-only). |
| **scale-out** | Kademeli kâr alma: PnL eşiklerinde pozisyonun bir kısmı satılır |
| **elapsed** | Maç ilerleme oranı (0.0 = başlangıç, 1.0 = bitiş) |
| **consensus** | Bookmaker ve Polymarket market'inin aynı favori üzerinde anlaşması |
| **whipsaw** | Bot SL ile çıktıktan sonra fiyatın geri zıplaması (doğru tahmin + yanlış exit timing) |
| **DORMANT** | Modül kodda var ama config/sport_rules'tan çıkarılmış, aktif kullanılmıyor |

---

## İçindekiler — Hangi Bölümü Ne Zaman Oku

> **Her zaman oku:** §0 (Temel İlkeler).
> **Göreve göre oku:** Aşağıdaki tabloya bak.
> **Şüphe varsa:** İlgili §6 ve §7 bölümlerinin tamamını oku.

Bu CURRENT STATE formüller, kalibrasyon sayıları, iş kuralları, "neden" notları içerir. Implementation detayları (dosya yolu, imza, dizin yapısı) için doğrudan kodu oku (`src/`).

| §     | Başlık                          | Ne zaman gerekli?                       |
|-------|---------------------------------|------------------------------------------|
| 0     | Temel İlkeler                   | **HER ZAMAN**                            |
| 5.7   | Dashboard Display Rules         | Dashboard / presentation işi             |
| 6.1   | Bookmaker Probability           | Olasılık / edge işi                      |
| 6.2   | Confidence Grading              | Confidence işi                           |
| 6.3   | Edge Calculation                | Edge işi                                 |
| 6.4   | Consensus Entry (Case A/B)      | Entry gate                               |
| 6.5   | Position Sizing                 | Sizing                                   |
| 6.6   | Scale-Out (3-tier)              | Exit / scale                             |
| 6.7   | Flat Stop-Loss (6-Katman)       | Exit / SL                                |
| 6.8   | Graduated Stop-Loss             | Exit / SL                                |
| 6.9   | ~~A-conf Hold-to-Resolve~~      | **KALDIRILDI** (Faz 1 rollback 2026-05-15) |
| 6.10  | Never-in-Profit Guard           | Exit                                     |
| 6.11  | Near-Resolve Profit Exit        | Exit                                     |
| 6.12  | Ultra-Low Guard                 | Exit                                     |
| 6.13  | FAV Promotion                   | Pozisyon yönetimi                        |
| 6.14  | Hold Revocation                 | Pozisyon yönetimi                        |
| 6.15  | Circuit Breaker                 | Risk yönetimi                            |
| 6.16  | Manipulation Guard              | Entry / risk                             |
| 6.17  | Liquidity Check                 | Entry                                    |
| 6.18  | Event-Level Guard               | Entry (concentration)                    |
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
- **Demir kural sorusu:** → DECISIONS §A Demir Kurallar.

---

## 0. Temel İlkeler (Değişmez Prensipler)

1. **Veri kaynağı = bookmaker**. Odds API 20+ bahis sitesinden konsensüs üretir.
2. **3 katmanlı cycle**: WebSocket (anlık) + Light (5 sn) + Heavy (30 dk).
3. **Pozisyon boyutu confidence'a göre**: A=%5, B=%4, C=blok.
4. **Profit taking = scale-out** (3-tier).
5. **MVP kapsamı = 2-way sporlar**. Ertelenmiş branşlar için bkz. `TODO.md`.
6. **P(YES) her zaman anchor** — direction-adjusted saklanmaz.
7. **Event-level guard**: aynı event_id'ye max N pozisyon (default 3 — §6.18).

---

## 5. Dashboard & Observability

### 5.7 Dashboard Display Rules

Dashboard presentation katmanı — kurallar domain kurallarından ayrı.
`presentation/dashboard/computed.py` + `static/js/*` sınırında enforce edilir.

#### 5.7.1 Treemap Branş Gruplaması

Gruplama anahtarı = **sport category** (baseball, hockey, basketball, ...).
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

**Partial scale-out dahil:** Treemap hem full-close hem partial scale-out event'leri ayrı trade olarak sayar. Her partial: invested = `sell_pct × original_size_usdc`, pnl = `realized_pnl_usdc`. Win/Loss: pnl sign'a göre. Aynı trade'in full + partial'ı birlikte 2 event olarak görünür.

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

Her tab (Active/Exited/Skipped/Stock): `match_start_iso` ASC (en yakın maç yukarıda). Boş değerler sona.

Lokasyon: `static/js/feed.js::FEED.render`.

#### 5.7.4 CSS Palette — Tek Kaynak

Renkli hex literal **sadece** `static/css/dashboard.css:root` içinde tanımlı. Başka CSS/JS dosyasında renkli hex YASAK — hep `var(--*)`.

Değişken ailesi: Ana (`--green`, `--red`, `--blue`, `--orange`), türev (`-dim`, `-dark`, `-hover`, `-strong`), nötr (`--bg`, `--panel*`, `--text`, `--muted*`, `--border-soft`).

JS chart renkleri runtime'da okur: `getComputedStyle(document.documentElement).getPropertyValue("--green")`.

#### 5.7.5 Scanner Filter Suite

Bot sadece izinli market tipleri + yakın pencere + live-olmayan markets alır. Filter sırası (`_passes_filters`):

1. **Flag kontrolü:** `closed` / `resolved` / `not accepting_orders` → ele
2. **Fiyat-based resolved detection:** `yes_price >= resolved_price_threshold` (default 0.98) veya `<= (1 − threshold)` → ele. Polymarket'in `closed/resolved` flag'leri lag'li; fiyat ~1.0/~0.0 ise sonuç kesin belli.
3. **Market type:** `sports_market_type ∈ {moneyline, spreads, totals}` zorunlu. Boş string (PGA Top-N props) reddedilir.
4. **Basketball-only totals/spreads:** `sports_market_type ∈ {spreads, totals}` ise sport_tag ∈ BASKETBALL_TAGS olmalı (NBA/WNBA/NCAAB/Euroleague/NBL).
5. **NHL moneyline-only flag** (`sport_rules.is_moneyline_only`): NHL pozisyonu sadece moneyline olabilir.
6. **NBA/WNBA spread-blocked flag** (`sport_rules.is_spread_blocked`): basketbol spread reddedilir (Faz 1 rollback + 0 trade kanıtı).
7. **Sport whitelist:** `config.scanner.allowed_sport_tags` (wildcard support)
8. **Min liquidity:** `min_liquidity` (default $1000)
9. **Max duration:** `end_date ≤ max_duration_days` (default 14 gün)
10. **Odds API penceresi:** `match_start ≤ max_hours_to_start` (default 24h)
11. **Stale match_start:** `max_post_start_hours` (default 8h) sonra başlamış maçlar reddedilir

Lokasyon: `orchestration/scanner.py::MarketScanner._passes_filters`. Config: `config.yaml > scanner:`.

#### 5.7.6 Enrichment Layer — Tennis Matching (DORMANT)

> **DORMANT 2026-05-05:** Tennis `sport_rules.py`'den kaldırıldı, config'de allow listede ama uygulamada aktif değil. Aşağıdaki matching modülleri (`domain/matching/tennis_*_resolver.py`) korunur — tenis Faz 2'de geri açılırsa direkt kullanıma hazır.

Eski (DORMANT) davranış — tennis markets'de iki yaygın bug için fix:

1. **Tournament prefix strip** (`question_parser.py::extract_teams`): "Porsche Tennis Grand Prix: Eva Lys vs Elina Svitolina" formatı → vs-split sonrası `team_a` kirli kalıyordu. Fix: ":" varsa son ":"'den sonrasını al.
2. **Slug priority sport_key resolve**: Slug `wta-*` olsa bile question'da "wta" geçmediği için ATP branch'ine düşüyordu. Fix: slug prefix otoritesi question text'ten ÖNCE kontrol edilir.

#### 5.7.7 Total Equity Chart — Realized-Only Stepped + Period Tabs

Chart formülü: `initial_bankroll + Σ exit_pnl_usdc` (trade history üzerinden kümülatif). **Unrealized hariç**.

**Veri kaynağı:** `/api/trades` (`computed.exit_events`) — full-close exit'ler + partial scale-out event'leri.

**Period tabs + adaptif bucketing (2026-04-16 fix, PLAN-009):**

| Tab | Granularity | Her nokta ne? | Tipik max |
|-----|------------|----------------|-----------|
| 24h | Event | Her exit = 1 basamak | ~50 |
| 7d  | Hourly | Saat sonu kümülatif | ~168 |
| 30d | Daily | Gün sonu kümülatif | 30 |
| 1y  | Weekly (ISO) | Hafta sonu kümülatif | 52 |

Default tab: `30d`. Rendering: `stepped: "before"`, `tension: 0` — basamaklı plateau.

**Neden trade-cumsum + bucketing:** Eski implementasyon `equity_history.jsonl` snapshot'larını çiziyordu; partial exit basis-leak'i (PLAN-008) nedeniyle identity kırılıyordu. Trade cumsum identity-correct.

**Sticky y-axis** (2026-04-16): Canvas içindeki y-axis label'ları gizli. Yerine canvas DIŞINDA sabit `.chart-y-axis` DOM element'i; Chart.js plugin `externalYAxis` her `afterUpdate`'te scale tick'lerini DOM'a yansıtır.

**Hitbox doğruluğu:** Canvas'ın genişliği parent `.chart-canvas-wrap`'in `style.width` ile set edilir.

Lokasyon: `static/js/trade_filter.js`, `dashboard.js::CHARTS.setEquity`, `chart_tabs.js`.

---

## 6. Kritik Algoritmalar

### 6.1 Bookmaker Probability

Bookmaker konsensüsünden olasılık türetir.

**Girdi:** `bookmaker_prob` (no-vig 0–1), `num_bookmakers` (ağırlıklı), `has_sharp` (Pinnacle veya Betfair Exchange).

**Kurallar:**
- **Geçersiz girdi** → `probability = 0.5` fallback. Koşul: `bookmaker_prob` None VEYA ≤ 0, VEYA `num_bookmakers < 1`
- **Geçerli girdi** → `probability = clamp(bookmaker_prob, 0.05, 0.95)`
- Round: 4 decimal

**Dönüş:** `BookmakerProbability` (probability, confidence, bookmaker_prob ham, num_bookmakers, has_sharp). Confidence türetmesi için → §6.2.

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

**Confidence multipliers (Faz 1 rollback 2026-05-15 — 19 Apr peak değerleri):**

| Confidence | Multiplier | Not |
|---|---|---|
| A | **1.00** | 19 Apr peak (önceden 1.25 idi — A-conf cezası rollback'te kaldırıldı) |
| B | 1.00 | Baz |
| C | — | Entry bloklanır |

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
- **Entry price aralığı:** `[0.60, 0.88)` — alt sınır consensus.min_price, üst sınır gate.max_entry_price (§6.5 R/R)

**Consensus yoksa (Case B):** standart edge hesabı (§6.3) kullanılır.

### 6.5 Position Sizing (SPEC-P 2026-05-21 — fixed-tier)

Confidence tier'e göre **sabit dolar** bahis. Bankroll dalgalanmasından bağımsız.

**Sizing tablosu (`fixed_bet_usdc` config dict — `risk.fixed_bet_usdc`):**
| Confidence | Miktar (USDC) | Gerekçe |
|---|---|---|
| A | $50 | sharp bookmaker + 5+ ağırlık |
| B | $30 | 5+ ağırlık, sharp yok |
| C | — | 0 (entry bloklanır) |

> SPEC-P (2026-05-21): bankroll-relative sizing (`bankroll × confidence_bet_pct`) kaldırıldı. Açık pozisyon sayısı arttıkça payda küçülüyor, geç gelen iyi maç küçük bahis alıyordu (path-dependence). Yeni model: tier başına sabit dolar — sıra önemsiz.

**Çarpanlar:**
| Koşul | Çarpan |
|---|---|
| Manipulation medium risk | × 0.5 |

**Entry price cap:** `effective_entry ≥ 0.88` → gate reddeder (`entry_price_cap`). Gerekçe: 88¢+ girişlerde max payout `0.99 − entry ≤ 0.11` → R/R çürük.

**Formül:**
```
size = fixed_bet_usdc[confidence]
if manipulation == medium: size *= 0.5
size = max(0, round(size, 2))
```

**Kaplar:**
- Polymarket minimum: $5 — altında reddet (`size_below_min`)
- Bankroll-relative cap'ler (`max_bet_usdc`, `max_bet_pct`) **kaldırıldı** — sabit-tier mantığında gereksiz.

### 6.6 Scale-Out (3-tier)

Kâr biriktikçe pozisyonun parçasını satmak.

| Tier | Tetikleyici (unrealized PnL) | Satış oranı | Amaç |
|---|---|---|---|
| 1 | ≥ +25% | 40% | Risk-free |
| 2 | ≥ +50% | 50% | Profit lock |
| 3 | Resolution / trailing | — | PnL-tetikli değil; §6.11-6.14 |

**Geçiş:** `tier 0 → 1 → 2` sırayla. Tier atlanmaz; ileri gider veya aynı kalır.

### 6.7 Flat Stop-Loss Helper (6-Katman Öncelik)

Pozisyon için flat SL yüzdesi. Katmanlar öncelik sırasıyla; ilk eşleşen döner. `None` dönerse flat SL uygulanmaz.

| # | Katman | Koşul | Sonuç |
|---|---|---|---|
| 1 | Stale price skip | `current_price ≤ 0.001` AND `current_price ≠ entry_price` | `None` (WS tick beklenir) |
| 2 | Totals/spread skip | question veya slug "o/u", "total", "spread" içerir | `None` (resolution'a kadar tut) |
| 3 | Ultra-low entry | `effective_entry < 0.09` | `0.50` (geniş tolerans) |
| 4 | Low-entry graduated | `0.09 ≤ effective_entry < 0.20` | Linear: `sl = 0.60 − t × 0.20`, `t = (eff − 0.09) / (0.20 − 0.09)` — 60% → 40% |
| 5 | Sport-specific (default) | Yukarıdakiler eşleşmedi | `get_stop_loss(sport_tag)` (§7) |

**Default parametreler:** `base_sl_pct = 0.30`.

> Eski "B confidence → 0.30" katmanı (Faz 1 rollback öncesi) kaldırıldı; B-conf de sport-specific SL kullanır.

### 6.8 Graduated Stop-Loss (Elapsed-Aware)

Zaman/fiyat/score'a duyarlı max allowed loss.

> **Not:** PnL% hesaplamaları `pos.entry_price` ve `pos.current_price` ile direkt yapılır — her iki alan da token-native. `effective_price()` uygulanmaz.

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

**Entry price multiplier:**
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

### 6.9 ~~A-conf Hold-to-Resolve~~ — KALDIRILDI

> **Faz 1 Rollback 2026-05-15:** A-conf hold dalı + market_flip kuralı TAMAMEN kaldırıldı. Sebep: post-peak veri analizi `market_flip`'in **−$310 / 0W-14L katil** olduğunu gösterdi. `evaluate()` zinciri artık koşulsuz multi-SL: near-resolve → scale-out → NBA totals → flat SL → graduated SL (tüm pozisyonlara, 19 Apr peak pattern).
>
> Tarihsel kayıt için bkz. §B kronolojik log + commit `4c44ae0`.

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

> **Not:** `current_price` alanı zaten owned token fiyatıdır (BUY_YES → YES token, BUY_NO → NO token). `effective_price()` UYGULANMAZ — çift flip olur.

**Sanity guard'ları (WS spike koruması):**
| Koşul | Aksiyon |
|---|---|
| Pre-match (maç başlamadı) | Reject |
| `mins_since_start < 10.0` | Reject (açılış spike'ı; `DEFAULT_PRE_MATCH_GUARD_MIN = 10`) |
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

**PROMOTE — tüm koşullar:**
- `not favored`
- AND `effective_price ≥ 0.65`
- AND `confidence ∈ {A, B}`

→ `favored = True`

**DEMOTE:**
- `favored = True`
- AND `effective_price < 0.65`

→ `favored = False`

**Davranış:** `favored = True` pozisyonlar Hold Revocation (§6.14) için "hold candidate" sayılır. Faz 1 rollback sonrası FAV statüsü exit davranışını DEĞİŞTİRMEZ — tüm pozisyonlar koşulsuz multi-SL (near-resolve → scale-out → flat SL → graduated SL) uygular.

**Veri dayanağı (tarihsel):** 5 favored trade = +$42.90, %100 WR.

### 6.14 Hold Revocation

Hold candidate pozisyonlar için hold iptali — ciddi fiyat düşüşü + skor dezavantajı altında.

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

**enabled flag (2026-05-19):** `circuit_breaker.enabled: bool = True` (default). `False` ise tüm halt kontrolleri bypass edilir — test/gözlem modu için. Multi-SL (flat + graduated) maç-içi korumayı sağlar.

**Eşikler:**
| Parametre | Değer | Etki |
|---|---|---|
| Günlük max loss (hard halt) | -8% | Halt + 120 dk cooldown |
| Saatlik max loss (hard halt) | -5% | Halt + 60 dk cooldown |
| Ardışık kayıp limiti | 4 trade | Halt + 60 dk cooldown |
| Günlük entry soft block | -3% | Soft block |

**`should_halt_entries` kontrol sırası:**
1. **Enabled check:** `self.config.enabled = False` → erken return (no halt). (2026-05-19 SPEC)
2. Cooldown aktif mi? → halt (kalan dk gösterilir)
3. Günlük loss ≤ -8% → halt 120 dk
4. Saatlik loss ≤ -5% → halt 60 dk
5. Ardışık kayıp ≥ 4 → halt 60 dk
6. Günlük loss ≤ -3% → soft block
7. Aksi → devam

**Kritik:** Exit kararları breaker'dan asla etkilenmez.

**Exposure Cap (yumuşak — SPEC-P 2026-05-21):**

Formül:
```
total_portfolio_value = portfolio.bankroll (nakit) + portfolio.total_invested()
                     = initial + realized_pnl  (kullanıcı tanımı: locked + non-lost)
cap = total_portfolio_value × max_exposure_pct  (default %50)
exposure = total_invested / total_portfolio_value
```

**Kural (SPEC-P):**
- `exposure < cap` → yeni trade **tam sabit-tier boyutuyla** alınır (sonuç cap'i geçse de OK).
- `exposure ≥ cap` → yeni trade reddedilir (`exposure_cap_reached`).
- **Size clipping uygulanmaz** — trade ya tam girer ya hiç.

**Örnek:** bankroll $978 (initial $1000 − realized $22), cap = $489.
- invested $440 → A trade $50 girer → invested $490 ✓ (cap'i geçti, yumuşak)
- invested $490 → yeni trade reddedilir (≥ cap)

> SPEC-P (2026-05-21): eski "soft+hard buffer + clipping" mantığı (`hard_cap_overflow_pct`, `min_entry_size_pct`, `available_under_cap`) kaldırıldı. Tek sade kural: cap'in altında tam trade, üstünde blok.

**Kritik invariant:** payda TOPLAM portföy değeri (initial + realized) — nakit değil. Pure function: `domain/portfolio/exposure.py::at_or_over_cap`.

### 6.16 Manipulation Guard

Self-resolving marketler + düşük likidite tespiti.

**Self-resolving subjects** (16 kişi):
`trump, biden, elon, musk, putin, zelensky, xi jinping, desantis, vance, newsom, harris, netanyahu, modi, zuckerberg, bezos, altman`

**Self-resolving verbs** (regex):
`say, tweet, post, announce, sign, veto, pardon, fire, hire, appoint, endorse, resign, visit, meet with, call, respond, comment, declare`

**Risk skoru:**
| Kontrol | Koşul | Score |
|---|---|---|
| Self-resolving | Subject AND verb metinde birlikte | +3 |
| Low liquidity | `liquidity < 10_000` | +1 (+2 eğer `liquidity ≤ 0`) |

**Risk seviyesi → davranış:**
| Toplam score | Level | Davranış |
|---|---|---|
| ≥ 3 | high | **SKIP** |
| = 2 | medium | Size × 0.5 |
| < 2 | low | OK (tam size) |

**Default `min_liquidity_usd`:** `10000`.

### 6.17 Liquidity Check

Entry ve exit sırasında orderbook derinliği kontrolü.

**Entry check:** `total_ask_depth = sum(ask.price × ask.size)`.

| Koşul | Aksiyon |
|---|---|
| `total_ask_depth < $100` | **Reject** (reason: "Depth < $100") |
| `size_usdc / total_ask_depth > 0.20` | Halve size (slippage koruması) |
| Aksi | Accept, orijinal size |

**Default `min_depth`:** `100.0`.

**Exit check:** `floor_price = best_bid × 0.95`; `fill_ratio = available / shares_to_sell`.

| `fill_ratio` | Strategy |
|---|---|
| ≥ 1.0 | `market` |
| `min_fill_ratio` ≤ ratio < 1.0 | `limit` (floor_price'ta) |
| < `min_fill_ratio` | `split` |

**Default `min_fill_ratio`:** `0.80`.

### 6.18 Event-Level Guard (max_positions_per_event)

Aynı event_id'ye max N pozisyon (default N=3, `config.yaml > risk.max_positions_per_event`).

**Mantık:** Bir maçın bağımsız market'leri (moneyline + spread + totals) ayrı bahisler sayılır ve birden fazla pozisyon açılabilir. Karşıt aynı-tip pozisyonu (örn 2 moneyline) uygulamada görülmez çünkü Polymarket bir maç moneyline'ı için tek market açar.

**Örnek:** "Spurs vs Timberwolves" event_id=446693 → moneyline + total + spread açılabilir, 4. pozisyon AÇILAMAZ.

**Race-condition fix (commit 2e9116e — Pistons-Cavaliers bug):** Batch entry sırasında per-iteration `count_event` check yapılır. Tek cycle'da 11+ pozisyon açılması önlendi.

**Lokasyon:** `src/orchestration/entry_processor.py::_add_position` + `src/strategy/entry/gate.py`. Bkz. ARCHITECTURE_GUARD.md Kural 8.

### 6.19 Bimodal Entry Floor + LIVE Yasağı (SPEC-X 2026-05-24)

Bimodal market'ler (totals + spread/spreads) için entry kapısında iki ek kontrol. **Sport bağımsız** — `market.sports_market_type` doğrudan kontrol edilir (`_is_bimodal_market_type` helper). SPEC-W'nin sport-aware sizing classifier'ından kasıtlı olarak ayrı tutulmuştur: SPEC-W "bu market'te bimodal sizing $15 mı $50 mı" sorusunu cevaplar (SL yakalama hızı), SPEC-X ise "bu market type yapısal olarak bimodal mı" sorusunu cevaplar (entry kapı kuralı).

1. **Min entry floor:** `effective_entry < 0.20` → reject (`bimodal_entry_below_floor`)
   - Gerekçe: Ultra-low guard (§6.12) zaten `effective_entry < 0.09 AND elapsed ≥ 0.75 AND current < 0.05`'de anında çıkış yapıyor. 20¢ altı entry'de bu üç şart yüksek ihtimalle başlangıçta sağlanıyor → mikro-trade üretiyor. Floor entry'de keser, runtime'da hiç slot açılmaz.
2. **LIVE yasağı:** `market.event_live == True` → reject (`bimodal_entry_live`)
   - Gerekçe: Bimodal market'lerde model olasılığı pre-match (MLB için Marcel/TTO/bullpen; diğer sporlar için bookmaker). LIVE'da skor/kalan-süre değişmiş → tahmin bayatlamış → asimetrik risk (küçük yukarı, büyük aşağı). Konkre vaka: 2026-05-23 WSH-ATL spread (entry 4¢, 9s sonra ultra_low_guard exit) + LAD-MIL/STL-CIN spread (entry 40-42¢, LIVE, yüksek risk profili).

**Config:** `risk.bimodal_min_entry_price: 0.20`. Mevcut MLB submarket engine içindeki `mlb_min_polymarket_price: 0.20` kuralı korunur (defense-in-depth).

**Lokasyon:** `src/strategy/entry/gate.py::_evaluate_one` adım 6b + 6c. Helper `_is_bimodal_market_type(market)`.

---

## 7. Sport Rules (MVP için)

### 7.1 Kapsam

**MVP'de aktif sporlar** (2-way — draw içermeyen):
- **Baseball**: MLB, MiLB, NPB, KBO, NCAA
- **Basketball**: NBA, WNBA, NCAAB, WNCAAB, CBB, Euroleague, NBL
- **Ice Hockey**: NHL (ML-only — flag, §7.2)
- **American Football**: NCAAF, CFL, UFL
- **Combat**: MMA, UFC, Boxing
- **Golf**: LPGA, LIV, PGA H2H

**MVP dışı / kaldırılmış:**
- **Tennis**: Ana botta KAPALI (steril ayrım, 2026-05-23 — STOCK kirlenmesi + bookmaker yokluğu). Tahmin laboratuvarı `feature/tennis-lab` branch'ında ayrı pipeline'da çalışır. `sport_rules.py` tenis entry'si korunur (mevcut açık tenis pozisyonların `match_start_iso` ESPN refresh'i için — bkz. §B 2026-05-23 position refresh kararı).
- **NHL secondary leagues** (AHL/Liiga/SHL/Mestis/Allsvenskan): Config + `sport_rules.py`'den kaldırıldı — sadece NHL.
- **Soccer** (tüm ligler): 3-way market yapısı, MVP 2-way pipeline ile uyumsuz (SPEC-015 rollback'le silindi).
- **Cricket**: Test match draw olasılığı (SPEC-011 rollback'le silindi).
- **Golf outright / Top-N**: Yapısal h2h değil.

### 7.2 Sport-Specific Kurallar (özet)

| Sport | stop_loss_pct | match_duration_hours | Özel exit / flag |
|---|---|---|---|
| **NBA** | 0.35 | 2.5 | halftime_exit @ -15 pts; **spread_blocked: True** (Faz 1 rollback, 0 trade kanıtı) |
| **WNBA + diğer basketbol** (NCAAB/Euroleague/NBL) | 0.35 | 2.5 | NBA kuralları (BASKETBALL_TAGS normalize) |
| **American Football** (NCAAF/CFL/UFL) | 0.30 | 3.25 | halftime_exit @ -14 pts |
| **NHL** | 0.30 | 2.5 | period_exit @ -3 goals after P2; **moneyline_only: True** (SPEC-L, 4 günde 13W/2L ML kanıt) |
| **MLB** (+ MiLB/NPB/KBO/NCAA) | 0.30 | 3.0 | inning_exit @ -5 runs after 6th; submarket_anchor: {totals: model, run_line: model} — SPEC-R model-anchor entry path |
| **Golf** (LPGA/LIV/PGA H2H) | 0.30 | 4.0 | playoff-aware |
| **DEFAULT** | 0.30 | 2.0 | - |

**Flag mantığı:** `sport_rules.is_spread_blocked()` ve `sport_rules.is_moneyline_only()` scanner filter + entry gate'te kontrol edilir. Tek doğruluk kaynağı: `src/config/sport_rules.py::SPORT_RULES` dict.

**Not**: Detaylı sport_rules tabloları `src/config/sport_rules.py`'de tutulur. Ertelenmiş branşların kuralları için bkz. `TODO.md` TODO-001.

---

## 13. Açık Noktalar (ilerisi için)

1. **Golf outright futures**: Sadece H2H (`golf_lpga_tour`, `golf_liv_tour`, `golf_pga_*` H2H) MVP'de. `golf_masters_tournament_winner` vb. outright'lar scope dışı.
2. ~~**Tennis dinamik matching**~~: ✅ DONE — `tennis_tournament_resolver.py` + `tennis_player_resolver.py` migrate edildi. Tenis 2026-05-05'te DORMANT'a alındı (yeni trade yok), Faz 2'de geri açma kararı.
3. **Baseball preseason**: `baseball_mlb_preseason` aktif ama preseason maçlarında motivasyon düşük — potansiyel bir `allow_preseason: false` flag eklenebilir.
4. **Draw-possible sporlar**: Tümü TODO-001'de. MVP'de scanner bu sport_tag'leri filter'lar.

---

# §B — KRONOLOJIK LOG (SPEC Kararları)

> Aşağıdaki bölümler kronolojik (en yeni üstte). Her SPEC: ne yapıldı + neden + kanıt + commit referansı.

---

### 2026-05-23 — Tennis ana bot izin listesinden kaldırıldı (steril ayrım)

**Karar:** `config.yaml` `scanner.allowed_sport_tags` listesinden `tennis`, `atp*`, `wta*` üç giriş silindi. Ana botun scanner'ı artık tenis maçlarını görmüyor.

**Neden:** Tenis ana bot için DORMANT (2026-05-05'te `sport_rules.py`'den çıkarılmış, sonra 2026-05-22'de SADECE `match_start_iso` ESPN refresh'i için geri eklenmişti — skor/bookmaker entegrasyonu yok). Tenis maçları config allow listesinde olduğu için scanner tarıyor → `odds_enricher` `no_bookmaker_data` ile reddediyor → STOCK kuyruğuna düşüyor (24h TTL'e kadar bekliyor). Sonuç: dashboard STOCK sekmesi tenis maçlarıyla kirleniyor + her tur boşa Odds API kredisi harcanıyor. Kullanıcı tenis lab (`feature/tennis-lab` branch) ile ana bot arasında steril ayrım istedi.

**Etki:**
- `config.yaml` — `allowed_sports` listesinden 3 satır silindi, kapatma sebebi olarak yorum kondu
- `tests/unit/config/test_settings.py::test_repo_config_yaml_parses` — `must_have` listesinden tenis çıktı, "ana botta olmamalı" guard'ı eklendi (gelecek drift'i yakalar)
- `sport_rules.py` tennis entry KORUNDU — açık tenis pozisyonların `TennisStartEnricher.refresh_positions()` üzerinden ESPN match_start refresh'i çalışmaya devam ediyor
- `tennis_start_enricher.py` + `tennis_player_resolver.py` + `tennis_tournament_resolver.py` KORUNDU — mevcut pozisyon yönetimi için lazım
- 1451 test yeşil (0 regresyon)

**Sonuç:** Ana bot tenis maçlarını taramıyor → STOCK temiz, API kredisi tasarruflu. Açık tenis pozisyonlar (varsa) normal yönetilmeye devam ediyor. Tenis lab branch'ı etkilenmedi.

---

### SPEC-W — Empirical Bimodal Classification (sport-aware) (2026-05-23)

**Karar:** Bimodal sizing dispatch artık **sport-aware**. Hangi (sport × market_type) kombinasyonlarının "SL yakalayamadığı, anlık çakılan" market olduğu Polymarket public API'den 238 maç (24 cell) empirical analiziyle belirlendi. Hardcoded `_BIMODAL_MARKET_TYPES = {"totals","spreads"}` (gate.py) ve `{"totals","run_line","spreads"}` (mlb_signal_adapter.py) **drift olarak silindi**; tek doğruluk kaynağı `sport_rules.is_bimodal_market(sport_tag, market_type)`.

**Neden:** Önceki SPEC-U mantıksal varsayım yapıyordu (totals + spreads = bimodal). Empirical analiz çürüttü: MLB run_line %93, MLB totals %73, NBA spread %100, NBA totals %67 KADEMELI (SL yakalar). NHL ML audit n=6 ort -%50 GERÇEKTEN bimodal. Mantıksal kategori + empirical kanıt birleşik = doğru karar.

**Metodoloji:** `analysis/bimodal_analyzer.py` script — Polymarket Gamma API'den kapanmış maç sample + CLOB prices-history (1-dk floor) + drop-window analiz. Cell başına 15 hedef (audit yeterli olunca audit override). Rapor: `analysis/bimodal_classification_2026-05-23.md`.

**API limitasyonu:** Polymarket public CLOB minimum 1-dk floor. <60s anlık çakılmalar görünmüyor — bu nedenle hokey (düşük olay sayılı, +1 gol büyük etki) için mantıksal kategori + audit kanıt empirical'ı override eder.

**BIMODAL ($15 cap) cell'ler:**
| Cell | Kanıt |
|---|---|
| nhl/moneyline | audit n=6, ort -%50; mantıksal yüksek (5-7 gol) |
| nhl/totals, spread | mantıksal yüksek (1 gol = büyük etki); empirical insufficient |
| wnba/spread | empirical n=8, %13 instant + %38 borderline |
| tennis/set_totals, set_handicap | empirical n=11-15 ambiguous |
| tennis/match_total_games | empirical n=15, %53 no_sig_drop |

**NON_BIMODAL ($50) cell'ler:**
- MLB tümü (moneyline/nrfi/run_line/totals): %69-93 kademeli, n=13-15
- NBA tümü (moneyline/spread/totals): %67-100 kademeli (n=8-9, ML/1h n=1 audit destek)
- WNBA moneyline + totals: %89 kademeli, audit %50 win
- ATP moneyline/first_set_winner/set_handicap/set_totals: %60-73 kademeli
- WTA moneyline/first_set_winner/match_total_games: %67-71 kademeli

**Etki:**
- `src/config/sport_rules.py` — `bimodal_market_types` her sport için liste; `is_bimodal_market()` fonksiyonu eklendi
- `src/strategy/entry/gate.py` — hardcoded `_BIMODAL_MARKET_TYPES` SİLİNDİ, sport_rules delege
- `src/strategy/entry/mlb_signal_adapter.py` — aynı drift SİLİNDİ, sport_rules delege
- `src/orchestration/portfolio_guards.py` — `_MarketLike.sports_market_type: object` → `str` tip düzeltmesi
- `analysis/bimodal_analyzer.py` + `analysis/bimodal_classification_2026-05-23.{json,md}` — empirical kanıt korunur
- 1451 test yeşil (0 regresyon)
- Tenis lab worktree'ye dokunulmadı (ayrı yapı kullanır)

**Sonuç:** Sizing artık her cell için empirical/mantıksal birleşik kanıtla karar verilir. Yeni branş/market için default non-bimodal ($50) — empirical kanıt gelene kadar konservatif değil, çünkü mantıksal "bimodal" kategori ekstrem (hokey) için zaten yakalandı.

---

### SPEC-T — Circuit Breaker Tamamen Kaldırıldı (2026-05-23)

**Karar:** `CircuitBreaker.should_halt_entries` her zaman `(False, "")` döndürür. CB state dosyası (`data/circuit_breaker_state.json`) silindi. Kod yapısı korundu (state, `record_exit`, `reset_if_needed`) ama entry kararını ETKİLEMEZ — ileride gerekirse açmak için tek satır revert yeterli.

**Neden:** 22-23 May UTC+3 gecesi 5 ardışık kayıp sonrası CB state'i 60-90 dakikalık cooldown tetikledi. `config.yaml`'da `circuit_breaker.enabled: false` olmasına rağmen state dosyası respect ediliyordu — bug niteliğinde. Bot reload sonrası bile state'i okuyup cooldown uyguluyordu, audit'i ilerletemedik. Kullanıcı kararı: CB'yi tamamen kaldır.

CB'nin kuralı: 4 ardışık kayıpta tüm liglerden 60 dakika blok. Bu bağımsız maçlar arası gereksiz bloklama yapıyordu. Multi-SL (graduated_sl + flat stop_loss + market_flip) zaten maç-içi koruma sağlıyor — CB üst-seviye stop unnecessary.

**Etki:**
- `src/domain/risk/circuit_breaker.py` — `should_halt_entries` her zaman False döner; `timedelta` import kaldırıldı
- `tests/unit/domain/risk/test_circuit_breaker.py` — modül-level `pytestmark = pytest.mark.skip(reason="CB removed 2026-05-23 SPEC-T")`
- `tests/unit/strategy/entry/test_gate.py::test_circuit_breaker_halts_all` — `@pytest.mark.skip` ile devre dışı
- `data/circuit_breaker_state.json` silindi
- 16 CB tetikleyici test skip; 1444 diğer test yeşil
- Commit: `792378d`

**Sonuç:** Bot artık ardışık kayıplarda durmaz. Çok büyük drawdown riski varsa kullanıcı bot'u manuel durdurur. Multi-SL ve same-type-per-event guard (SPEC-S Faz D) maç-içi/portföy seviyesinde yeterli koruma sağlar.

---

### SPEC-S Faz D — Bimodal Sizing + Same-Type-Per-Event Guard (2026-05-23)

**Karar:** İki bağımsız risk yönetimi kuralı eklendi:

1. **Bimodal sizing** — Tüm spor marketleri (moneyline, totals, spread) binary olduğundan ("bir anda fiyat çakılır" karakterli), tek tip bahis cap'i uygulandı: A=$15, B=$10 (önceden A=$50, B=$30). Tenis Lab SPEC-N paritesi.

2. **Same-market-type-per-event guard** — Aynı `event_id`'de aynı `sports_market_type`'tan ikinci pozisyon yasaklandı. `max_positions_per_event=3` cap'i korunur, ancak her biri farklı tür olmalı (1 ML + 1 totals + 1 spread). Tüm branş ve liglerde geçerli, sport-bazlı istisna yok.

**Neden:** 22-23 May UTC+3 gecesi analizi:
- A güveni $50 sabit sizing × 13 trade × 3 saat = $700 risk penceresi (kayıp -$107)
- NBA OKC/SAS aynı maçta 2 farklı totals (215.5 + 222.5) — ikisi de kayıp -$52. Aynı maç ters giderse korelasyonlu kayıp 2-3 kat ödenir
- Bimodal sizing aynı oranda kayıp/kazanç oranını korur ama nominal tutarı %70 düşürür → tek günlük risk -$107 → ~-$32 tahmini

**Etki:**
- `config.yaml` — `risk.fixed_bet_usdc: A: 15, B: 10` (önceden 50/30)
- `src/config/settings.py` — `RiskConfig.fixed_bet_usdc` default `{"A": 15.0, "B": 10.0}`
- `src/strategy/entry/mlb_submarket_engine.py` — constructor fallback güncellendi
- `src/strategy/entry/gate.py` — `GateConfig` default güncellendi
- `src/orchestration/factory.py` — factory fallback güncellendi
- `src/domain/portfolio/manager.py` — `positions_for_event(event_id)` helper eklendi
- `src/orchestration/portfolio_guards.py` — `check_per_market_guards` same-type check + `_normalize_market_type` helper; `_MarketLike`/`_PortfolioLike` protokol genişletmesi
- `src/presentation/dashboard/static/js/skip_reason_help.js` — `same_market_type_per_event` + `event_already_held` skip-reason açıklamaları
- 4 test dosyası sizing 50/30 → 15/10 güncellendi (test_position_sizer, test_mlb_signal_adapter, test_mlb_submarket_engine, test_gate)
- 9 yeni test (positions_for_event 4, same-type guard 5)
- Toplam 1460 testin tümü yeşil (full suite smoke)
- Commit'ler: `b68407a`, `2b9567c`, `6b38482`

**Sonuç:** Tek gece kayıpları geriye-bakım simülasyonda -$107 → -$24 (her iki kural birlikte: bimodal $50→$15 + NBA 2. totals açılmaz). Yapısal değişiklik tüm sporlarda geçerli; MLB modeline bağımsız çalışır.

---

### SPEC-S Faz B — MLB Engine Doğruluk Artırımları (2026-05-23)

**Karar:** Engine'in 3 doğruluk simplification'ı çözüldü:

1. **Marcel 5/4/3 multi-season weighting** — `rate_shrinker.marcel_weighted_rates(current, prev, prev_prev)` her oyuncu için 3 sezonun PA-weighted ortalamasını döndürür (ağırlık 5/4/3 — Tom Tango Marcel projeksiyon). Engine `_get_batter_rates`/`_get_pitcher_rates` artık 3 sezon fetch eder + `_rates_for_season` helper'ı ile cache+statcast birlikte. Eksik sezonlar (boş dict / pa=0) otomatik atlanır.

2. **TTO refinement** — Önceden inning-bazlı kaba formül `((inning-1)//3)+1` (1-3 → TTO1, 4-6 → TTO2, 7-9 → TTO3) kullanılıyordu. Yeni `_tto_for_pa(cumulative_pa) = min(cumulative_pa // 9 + 1, 4)` cumulative PA tracking ile: her 9 PA = +1 TTO tier. Engine `_build_inning_lineups` döngüsünde her batter sonrası sayaç +1.

3. **Bullpen opt-in interface (kısmi)** — Engine constructor'a `team_bullpen_rates: dict[int, dict[str, dict[str, float]]] | None = None` opsiyonel parametresi eklendi. Verilirse `bullpen_segmenter.select_pitcher(inning, score_diff=0, starter, bullpen)` ile inning-bazlı seçim yapılır; None ise eski "starter all innings" davranışı korunur (geriye uyumlu). Pre-game `score_diff=0` (close-game) varsayımı; V3 Monte Carlo dinamik state'e geçilebilir.

**Bullpen rates aggregation kapsam dışı (TODO):** Engine bullpen rates dict bekliyor ama factory default `None` geçiyor — yani şu an aktif değil. Bullpen rates statcast'tan team-bazlı leverage tier (middle/setup/closer) aggregation gerektirir; bu Statcast client'a yeni method + Stats API team roster fetch ekleme gerektirir (ayrı mini-proje). Bu kapsam dışı bırakıldı; engine interface hazır, rates yüklendiğinde otomatik devreye girer. TODO-002 olarak kaydedilecek.

**Neden:** Marcel ve TTO doğruluk artırımı; bullpen sıralaması starter'ı 9 inning kullanmaktansa gerçekçi pitcher rotasyonu sağlar. SPEC-R Plan 4 simplifications listesinde 6 madde vardı; Faz A 3'ünü, Faz B kalan 3'ü çözer (kısmi bullpen + Marcel + TTO).

**Etki:**
- `src/domain/mlb_submarket/rate_shrinker.py` — `marcel_weighted_rates()` eklendi
- `src/strategy/entry/mlb_submarket_engine.py` — `_tto_for_pa`, `_select_pitcher_for_inning`, `_rates_for_season` helpers; constructor `team_bullpen_rates` parametresi; `_build_inning_lineups` `pitching_team_id` parametresi + cumulative_pa + dinamik pitcher seçimi
- Engine dosyası 400 satır (ARCH_GUARD Kural 3 sınırında)
- 18 yeni test (Marcel 5, multiseason 2, TTO 6, bullpen 5)
- Toplam 1451 testin tümü yeşil (full suite smoke)
- Commit'ler: `1affbcf`, `07bf6ce`, `d359d05`

**Sonuç:** Engine artık 3-sezon Marcel weighted rates + PA-tracked TTO + opt-in bullpen rotasyon altyapısı ile çalışır. Faz B kapsamı dışı kalan bullpen rates aggregation TODO-002 olarak işaretlendi. Sonraki Faz D: bimodal sizing + same-type-per-event guard (genel risk yönetimi, MLB modeline bağımsız).

---

### SPEC-S Faz C — MLB Moneyline Model Anchor (2026-05-23)

**Karar:** MLB moneyline marketleri artık model anchor kullanır (önceden bookmaker konsensüsündeydi). Engine'in mevcut `home_dist`/`away_dist` çıktısından yeni `moneyline_pricer.moneyline_probability()` ile P(home wins) hesaplanır; berabere kalan dağılımlar 50/50 split edilir (ekstra inning rastgele varsayımı).

**Neden:** Audit son 13 saatte MLB moneyline 5/5 kayıp (-$83). Bahisçi konsensüsü beyzbol için yetersiz (atıcı/bullpen/hava günlük değişir). Engine zaten totals + run-line için doğru çalışan domain motoruna sahip — moneyline pricer eklemek ~40 satır iş; sıfırdan model değil.

**Etki:**
- `src/domain/mlb_submarket/moneyline_pricer.py` (yeni, 39 satır) — pattern: totals_pricer + spread_pricer
- `src/strategy/entry/mlb_submarket_engine.py` — `_SLUG_MONEYLINE_RE` regex, `_parse_slug_static` moneyline branch, `process()` dispatch elif branch
- `src/domain/mlb_submarket/edge_candidate.py` — `_VALID_MARKET_TYPES` setine `"moneyline"` eklendi
- `src/config/sport_rules.py` — `mlb.submarket_anchor.moneyline = "model"` (önceden eksik, default "bookmaker"a düşüyordu)
- 11 yeni test (moneyline_pricer 5, parse_slug 2, engine moneyline 3, sport_rules anchor 6 — bazıları mevcut testlerin güncellenmiş hali)
- Scanner dispatch testi: MLB moneyline artık `collect_model_signals` üzerinden engine'e yönlendiriliyor (önceden bookmaker yoluna düşüyordu)
- Commit'ler: `a048631`, `26c1561`, `19032e2`, `8057588`

**Sonuç:** MLB için tüm submarket türleri (moneyline + totals + run-line) artık aynı domain motorundan model-anchor edge üretir. Sonraki Faz B (bullpen + Marcel + TTO) ile motorun doğruluk artırımları yapılır.

---

### SPEC-S Faz A — MLB Submarket Engine Plan 4 Simplifications Resolved (2026-05-23)

**Karar:** MLB submarket engine'inin (`src/strategy/entry/mlb_submarket_engine.py`) 3 kritik "Plan 4 simplification" hardcoded davranışı düzeltildi:

1. **Team matching** — slug'tan home/away abbreviation parse edilip Stats API `team_id` ile schedule içinde eşleşen maç bulunur. Önceden: `schedule[0]` (o günün ilk maçı, yanlış takım). Yeni: `TEAM_ABBREVIATIONS` lookup table (`src/infrastructure/mlb_data/team_lookup.py`) + schedule filtreleme.
2. **Park binding** — `home_team_id → park_id → ballpark_metadata`. Önceden: `next(iter(ballpark_metadata.values()))` (sözlüğün ilk park'ı, yanlış stadyum). Yeni: `TEAM_ID_TO_PARK_ID` mapping (`src/orchestration/factory.py`) + `park_meta_for_team()` helper.
3. **DH detection** — `gameType == "D"` AND `scheduled_innings < 9` → `dh_game=True`. Önceden: `dh_game=False` hardcoded. Yeni: `StatsApiClient.get_schedule()` `game_type`, `scheduled_innings`, `double_header` alanlarını döndürür; engine bunları okuyarak 7-inning DH path'e geçer.

**Neden:** Audit'te son 13 saatte MLB totals/run-line trade SAYISI 0 idi; MLB ML trade'leri ise %0 kazanma oranıyla -$83 (5/5 kayıp). Engine aktif (`enabled: true`) ama yanlış maç + yanlış stadyum verileriyle edge hesaplıyordu → güvenilmez edge → no_edge skip. Bu 3 simplification çözülmeden model anchor pratikte değer üretmiyordu.

**Etki:**
- `src/infrastructure/mlb_data/team_lookup.py` (yeni, 65 satır) — 30 takım abbreviation ↔ team_id sabit veri
- `src/orchestration/factory.py` — `TEAM_ID_TO_PARK_ID` (30 takım → park_id), `park_meta_for_team()` helper; engine instantiation'a `team_id_to_park_id` parametresi eklendi
- `src/strategy/entry/mlb_submarket_engine.py` — `_parse_slug_static` 5-tuple (date, market_type, line, away_abbr, home_abbr); `process()` team matching + home-park binding + DH detection
- `src/infrastructure/mlb_data/statsapi_client.py` — `get_schedule()` her game dict'ine `game_type`/`scheduled_innings`/`double_header` ekler (default `"R"`/`9`/`"N"`)
- 14 yeni test (team_lookup 7, park_mapping 5, parse_slug 4, team_matching 3, park_matching 2, dh statsapi 2, dh engine 3) — toplam 1423 testin tümü yeşil
- Commit'ler: `14cae46`, `cf5488b`, `f043102`, `76d4964`, `4b7098b`, `5432c94`

**Sonuç:** MLB totals + run-line için model anchor artık doğru maç + doğru stadyum + DH-duyarlı edge üretir. Sonraki adımlar SPEC-S Faz C (moneyline pricer) ve Faz B (bullpen + Marcel + TTO doğruluk iyileştirmeleri) içinde.

---

### 2026-05-26 — Baseball Portföyden Çıkarıldı (Bleed Kontrolü)

**Bağlam:** Dashboard branş kırılımı + audit tüm-tarih analizi: baseball 5 haftada (19 Nis → 26 May) 122 pozisyon, **67 kapanış, %37 win, net −$297**. Post-reboot 48 saatte (24 May 18:00 → 26 May): 21 pozisyon, **12 kapanış, %25 win, net −$107**. Aynı dönemde NBA +$21, WNBA −$1, NHL −$3 → diğer üç spor net **+$17 artıda**. Baseball tek başına bot'u eksiye çekti. Counterfactual: baseball hiç açılmasaydı dashboard realized **+$120.88 yerine +$185.88** olurdu.

**Çıkış sebebi mucize deseni (39 SL exit / 25 near-resolve exit):** her SL'ye düşen pozisyon %100 kaybetti, her maç-sonuna varan pozisyon %100 kazandı. Yani edge yanlış değil, **giriş zamanlaması + SL bizi kestirmeden atıyor**. Submarket kırılımı: moneyline n=98 %34 −$319, runline n=9 %0 −$74, totals n=11 %100 +$88 — yalnız totals pozitif ama (a) örneklem 11, (b) totals path'i `mlb_submarket.enabled=false` ile zaten kapalı (SPEC-Y7 — heavy cycle API bottleneck).

**Karar:** `config.yaml > scanner > allowed_sport_tags` listesinden 5 baseball etiketi (`mlb, milb, npb, kbo, baseball`) çıkarıldı. Scanner artık baseball marketlerini sport_tag filter'da reddeder ([src/orchestration/scanner.py:174-176](src/orchestration/scanner.py#L174-L176)). Yeni MLB pozisyonu açılmaz; mevcut 9 açık MLB pozisyonu doğal SL/scale-out/near_resolve ile kapanır (~$450 exposure azalır).

**Geri-açma protokolü:** Bu liste-bazlı kapatma 5 satır geri ekleme ile çözülür. Tekrar açma kararı için ön koşul: (a) MLB submarket engine performans bottleneck çözümlü (mevcut: 30 market × 30s = 12+dk heavy cycle bloğu), (b) totals-only başlangıç (moneyline + runline kapalı kalır — empirik kanıt zayıf), (c) 50+ trade örneklemle paper test.

**Etki:**
- [config.yaml](config.yaml#L29-L34) `allowed_sport_tags` baseball satırları silindi (yorum eklendi)
- [tests/unit/config/test_settings.py](tests/unit/config/test_settings.py) `must_have`'dan baseball çıkarıldı + yeni `banned_baseball` assertion eklendi
- Açık 9 MLB pozisyon: hold-to-resolve modunda doğal kapanış
- mlb_submarket.enabled=false dokunulmadı (geri-açma yolu açık)

**Açık takip:**
- Mevcut 9 açık pozisyon kapanınca lifetime baseball P&L kesinleşir (şu an −$107 + open −$65 = ~−$172 dashboard'a göre)
- Totals path'i bağımsız ve verimli hale getirilirse (Polymarket Agent 2.0 MLB Submarket Lab spec'i) baseball totals geri açılabilir — moneyline ve runline kalıcı kapalı tutulmalı

---

### 2026-05-25 — SPEC-Z2..Z10: Bot İyileştirme Paketi (phantom market + dashboard parity + audit ground truth)

**Bağlam:** 2026-05-24 SPEC-Z lookback fix sonrası bot trade almaya başladı. Aynı gün/ertesi gün audit'inde 4× Detroit-Baltimore $476 phantom trade tespit edildi (bestBid=None + entry 4¢ → exit 100¢ — matematiksel olarak imkansız "kazanç"). Aynı oturumda dashboard'da realized widget ↔ EXITED tab tutarsızlığı + gizemli archive scheduler'ın trade_history.jsonl'i boşaltması + LIVE rozet eksikliği + score enricher'ın tüm sporlar için çalışmaması ortaya çıktı. Tek brainstorming → spec → subagent TDD zinciriyle 9 düzeltme uygulandı.

**Z2 — Scanner: tennis_enricher filter sonrası çağrılıyor.** Tennis enricher heavy cycle'da filtre öncesi çalışıyordu → 20k market için ESPN dereference cycle'ı bloke ediyordu. Filter sonrasına alındı, sadece eligible tennis market'leri enrich edilir.

**Z3 — Phantom market detection (bestBid sanity).** `MarketData` modeli `best_bid: float | None` + `best_ask: float | None` ile genişletildi. `gamma_client._safe_float()` yeni helper bestBid/bestAsk'i güvenle parse eder. Scanner filter: `m.best_bid is None or m.best_bid <= 0.0` → reject. `gameStartTime` parsing de düzeltildi (`_normalize_iso()` helper). Detroit-Baltimore tipi phantom market'ler (zaten resolve olmuş, orderbook boş) artık scanner aşamasında elenir.

**Z4 — LIVE rozet (dashboard).** `_countdownPill` (feed.js) artık `delta ≤ 0 AND match_start ≤ 8h önce` → "LIVE" basıyor. Polymarket `event.live` flag'i gecikmeli güncellendiği için saat-bazlı fallback gerekli; `match_live` argümanı tek başına yeterli değil (önceki SPEC 2026-04-15 zaten saat-bazlı tasarımı şart koşmuştu).

**Z5 — Score enricher tüm sporlar için ESPN live sync.** `score_enricher.refresh_match_status(positions)` yeni public method + `_match_position_to_any` (live + completed) yardımcısı. Agent light cycle her döngüde `refresh_match_status()` çağırıp pozisyonların `match_live` field'ını günceller. Önceden sadece skor poll'u vardı, status (live/completed) güncellemesi yoktu — dashboard'da maç bitse bile "LIVE" görünmeye devam ediyordu.

**Z6 — Orphan exit kaydı.** `trade_logger`'da bir pozisyon için `log_partial_exit` çağrıldığında karşılık gelen `entry` kaydı yoksa (reboot sonrası snapshot yüklenmiş ama trade_history temizlenmiş senaryo), eskiden exit kaydı sessizce atılıyordu. Yeni davranış: orphan exit standalone kayıt olarak yazılır (entry_ts=None, partial=True). Audit kaybı engellendi.

**Z7 — Archive rename → copy.** `scripts/reboot.py:archive_audit_logs` artık `shutil.copy2` kullanır (önceden `Path.rename`). Gizemli bir scheduler (henüz tespit edilmedi — TODO-007 forensic logger) reboot dışında bu fonksiyonu çağırıyor; rename davranışı dashboard'ı boşaltıyordu. Copy ile asıl dosya korunur, snapshot forensic için yaratılır. Reboot modu `reset_state` ile asıl temizliği yapar — bu değişiklik reboot semantiğini bozmaz.

**Z8 — startup `_reconcile_realized_pnl` snapshot öncelik (GUARD-5).** Reboot/reload sonrası `positions.json.snapshot.realized_pnl != 0` ise audit'tan yeniden hesaplama yapılmaz, snapshot trust edilir. Audit (trade_history) silinmiş olsa bile lifetime realized PnL kaybolmaz.

**Z10 — Dashboard realized widget = read_trades toplamı.** `computed.realized = sum(read_trades())` — snapshot priority kaldırıldı. Önceden widget snapshot.realized'i okuyordu ($95) ama EXITED tab `read_trades`'i okuyordu ($33) → kullanıcıya çelişkili görünüyordu. Kullanıcı direktifi: "realized PnL ile EXITED tab aynı yerden bilgi çekiyor olmalı." Z8 (snapshot reconcile) backend bütünlüğünü korur, Z10 (dashboard parity) görsel tutarlılığı sağlar — ikisi farklı katmanda.

**TODO-005 — Slug parser ayrı modüle.** `mlb_submarket_engine.py` 419 satır → 385 satır. Regex'ler `src/strategy/entry/mlb_slug_parser.py`'a taşındı (pure static, no I/O). Engine `parse_slug` import eder; parser kendi başına test edilebilir. ARCH_GUARD Kural 3 uyumu.

**TODO-006 — SPEC-Y7/Y8 commit + test fix.** `config.yaml`: `heavy_interval_min: 30 → 25`, `max_markets_per_cycle: 300 → 500` (SPEC-Y8 throughput), tennis/atp*/wta* `allowed_sport_tags`'ten çıkarıldı (SPEC-Y7 — tennis ana botta yok, tennis lab ayrı branch). `test_repo_config_yaml_parses` güncellendi: tennis tag'leri `must_have`'den çıkarıldı + explicit "banned_tennis" kontrolü eklendi (SPEC-Y7 enforcement).

**TODO-007 — Archive trigger forensic logger.** `archive_audit_logs` başlangıcında `inspect.stack()[1:5]` ile çağıran 4 frame loglanıyor. Geçici — gizli scheduler tespit edilince kaldırılacak. DECISIONS satır 1137 "TODO investigate" notunun aktif takip mekanizması.

**Etki (özet):**
- `src/orchestration/scanner.py`, `src/orchestration/score_enricher.py`, `src/orchestration/agent.py`, `src/orchestration/startup.py`, `src/orchestration/factory.py`
- `src/infrastructure/apis/gamma_client.py`, `src/infrastructure/persistence/trade_logger.py`
- `src/models/market.py` (best_bid, best_ask alanları)
- `src/presentation/dashboard/computed.py`, `src/presentation/dashboard/readers.py`, `src/presentation/dashboard/static/js/feed.js`
- `src/strategy/entry/mlb_slug_parser.py` (yeni), `src/strategy/entry/mlb_submarket_engine.py` (refactor)
- `scripts/reboot.py` (Z7 copy + TODO-007 forensic)
- `config.yaml`, `tests/unit/config/test_settings.py`
- 1469 testin tümü yeşil. Phantom Detroit-Baltimore tipi trade artık scanner aşamasında elenir; dashboard realized ↔ EXITED tab tutarlı; reboot dışı audit kayıpları engellendi.

**Açık takip:**
- TODO-007 forensic logger'ın çıktısından gizli archive scheduler tespit edilecek (kaynak belirlenince logger kaldırılır)
- MLB SL %30 → %25 sıkılaştırma kullanıcı onayına bağlı (henüz uygulanmadı)

---

### 2026-05-24 — SPEC-Z: Gamma fetch lookback hack kaldırıldı

**Problem:** 2026-05-24 sabah saatlerinde bot 8+ saat 0 trade aldı. Tanı: scanner her cycle "Scanner: 1825 raw → 0 filtered → top 0" yazıyordu. Direkt Polymarket API testi ile bugünkü 16 MLB maçı + diğer sporlarda eligible market'ler olduğu doğrulandı, ama fetch_events bunları getirmedi.

**Root cause:** `gamma_client.py` içindeki `_FETCH_LOOKBACK_HOURS = 24` sabiti API çağrısına `start_date_min = now - 24h` ekliyordu. Polymarket `event.startDate` field'ı **event yaratım zamanı civarı** — bugünkü MLB market'leri 5-7 gün önce yaratılmış (event.startDate ≈ 2026-05-17), 24h lookback penceresinin dışında kaldı, kaçırıldı. Eski yorum bu sabitin "Polymarket-side bug için workaround" olduğunu söylüyordu (yakın event'leri tag fetch'inde göstermeme). 2026-05-24 test'lerinde o bug görünmüyor; API artık `start_date` filter olmadan tüm aktif event'leri döndürüyor.

**Çözüm:** Lookback hack tamamen kaldırıldı. `_FETCH_LOOKBACK_HOURS` + `_FETCH_LOOKFORWARD_HOURS` sabitleri silindi, `_fetch_by_tag` params dict'inden `start_date_min/max` satırları silindi, `fetch_events`'tan `now`/`start_min`/`start_max` hesaplamaları silindi, `datetime`/`timedelta`/`timezone` import'ları silindi. Match-saat filtreleme zaten `MarketScanner._passes_filters` içinde match_start_iso bazlı yapılıyor (`_hours_to_start ≤ max_hours_to_start=24` + `_match_start_recent_or_future`).

**Etki:**
- Fetch raw count: 1825 → **20,854** (10x artış, çünkü tüm aktif event'ler döner)
- Bugün MLB: 0 → **263 market** (moneyline + spreads + totals)
- Scanner.scan() top eligible: 0 → **40**
- Fetch süresi: 74s → 72s (no regression)
- Scan süresi (filter dahil): ~85s, heavy cycle 25dk içinde toplam tolere edilebilir

**Mimari prensip:** API-side filter ile bizim domain-side filter çakışmamalı. Bir bilgiyi bir kez filtre — daha basit, daha az hata yüzeyi. Lookback hack iki katmanlı filtreleme yarattığı için bugünkü maçları kaybediyordu.

**Geri çevrilebilirlik:** Polymarket eski bug'ı yeniden ortaya çıkarsa (yakın event'leri tag fetch'inde göstermeme), `_fetch_by_tag` params'a `start_date_min/max` geri eklenir; ama BU SEFER lookback değeri 240h+ olmalı (test edildi, 168h'den itibaren bugünkü maçlar yakalanır).

---

### 2026-05-24 — SPEC-X: MLB Submarket Entry Yolu Sağlamlaştırması

**Problem:** 2026-05-23 üretim verisinde 3 problemli MLB spread trade'i tespit edildi:
- `mlb-wsh-atl-2026-05-23-spread-home-3pt5`: entry 4¢ → 9s sonra `ultra_low_guard` exit, $0 zarar (gereksiz mikro-trade)
- `mlb-lad-mil-2026-05-23-spread-away-1pt5`: entry 42¢, LIVE, asimetrik risk
- `mlb-stl-cin-2026-05-23-spread-away-1pt5`: entry 40¢, LIVE, benzer profil

**Root cause:** `mlb_submarket_engine.py`'daki `_SLUG_RUN_LINE_RE` regex'i eski varsayım (`spread-(pos|neg)1pt5`) ile yazılmıştı; gerçek Polymarket slug formatı `spread-(home|away)-{N}pt5` (değişken N). Eşleşme olmadığı için MLB submarket engine `None` döndürdü → trade ana botun Normal entry'sine düştü → bookmaker pre-match prob ile market price farkı edge sanıldı.

**Çözüm (3 faz, 11 commit):**
1. **Faz 1 — Slug parser fix:** regex `spread-(home|away)-(\d+)pt5` formatına çekildi; line yorumu: home → -N.5, away → +N.5.
2. **Faz 2A — Bimodal entry floor:** `effective_entry < 0.20` → reject (`bimodal_entry_below_floor`).
3. **Faz 2B — Bimodal LIVE yasağı:** `market.event_live == True` → reject (`bimodal_entry_live`).

**Spec-implementation revize:** Plan başlangıcında `_is_bimodal_market` (SPEC-W sport-aware sizing classifier) kullanılması düşünüldü; Task 4 testinde MLB için `bimodal_market_types=[]` olduğu için tetiklenmeyeceği fark edildi. Yeni helper `_is_bimodal_market_type(market)` eklendi: `sports_market_type in ("totals", "spreads", "spread")` doğrudan kontrol — sport bağımsız. Ayrıca `MarketData.event_live` (`match_live` değil) kullanıldı.

**Etki:** MLB spread/total trade'leri artık MLB submarket engine'den geçer (Marcel + TTO + spread_pricer). Bimodal market'lere bayalı tahmin + asimetrik risk profili olan girişler kapıda kesilir.

**Kapsam dışı:** Moneyline min/max price, diğer sporların submarket engine'leri (yok), bookmaker prob clamp.

---

### 2026-05-23 — Position match_start refresh + LIVE rozet düzeltmesi

**Karar:**
1. Açık tennis pozisyonların `match_start_iso`'su her light cycle'da `TennisStartEnricher.refresh_positions()` ile ESPN'den güncellenir
2. `Position.match_live` entry'de `market.event_live`'den (Polymarket Gamma flag) doldurulur
3. Dashboard `_countdownPill` JS'i artık `match_live` argümanını gerçekten kullanır (SPEC 2026-04-15 uyumu)

**Neden:**
- Önceki ESPN entegrasyonu yalnızca scanner'a inject'liydi; entry sonrası `Position.match_start_iso` Polymarket startTime'da donuyordu → exit kararları yanlış saatle çalışabiliyordu
- `Position.match_live` ölü field'tı (default False, hiçbir yerde set edilmiyordu); dashboard JS `match_live` argümanı kullanılmıyordu (saat geçince otomatik LIVE basıyordu, gerçek live değilken de)

**Etki:**
- `src/orchestration/tennis_start_enricher.py` — `refresh_positions()` + slug-bazlı helper refactor (DRY: `enrich` ve `refresh_positions` ortak pipeline)
- `src/orchestration/entry_processor.py` — Position(...) constructor'lara `match_live=market.event_live`
- `src/orchestration/agent.py` — light cycle'a refresh hook
- `src/orchestration/factory.py` — `AgentDeps`'e tennis_start_enricher inject
- `src/presentation/dashboard/static/js/feed.js` — `_countdownPill` SPEC uyumu
- Commits: `498d8d8`, `756b49c`, `e6843c8`, `6f69923`

---

### 2026-05-23 — Tennis ESPN gerçek-fetch düzeltmesi

**Karar:** ESPN tennis için 3-aşamalı public metod `ESPNClient.fetch_tennis_matches_today` eklendi (scoreboard → competitions → athlete dereference, 24h athlete cache). `TennisStartEnricher` market'lerin `match_start_iso` tarihlerinden ihtiyaç duyulan ESPN günlerini çıkarıp her unique gün için ayrı fetch yapar. Doubles slug formatı (`atp-doubles-{p1}-{p2}-date`) parser'a eklendi. Same-day guard: ESPN eşleşmesi market'in günüyle aynı UTC günde değilse override iptal.

**Neden:** Önceki entegrasyon (2026-05-22) `fetch_scoreboard` çağrısı yapıyordu; ESPN tennis scoreboard'u turnuvaları döndürür, tek tek maçları değil. Canlı doğrulamada 0 maç çıkmıştı — enricher fiilen no-op'tu. Doğru endpoint: `sports.core.api.espn.com/.../competitions`.

**Etki:**
- `src/infrastructure/apis/espn_client.py` — `fetch_tennis_matches_today` + athlete cache (~140 satır eklendi)
- `src/orchestration/tennis_start_enricher.py` — yeni metoda yönlendi, doubles desteği, same-day guard, market-tarih-bazlı fetch
- `src/orchestration/factory.py` — `ESPNClient(athlete_cache_ttl_sec=...)` config-driven
- `src/config/settings.py`, `config.yaml` — `tennis_athlete_cache_ttl_sec: 86400`
- `scripts/verify_tennis_enricher.py` — canlı doğrulama scripti
- Canlı sonuç: 14/66 tennis market başarıyla ESPN'den override (geri kalan 52 expired turnuva = doğru fallback)
- ITF/Challenger ESPN'de yok → Polymarket fallback (mevcut, doğru)

---

### 2026-05-22 — Tennis ESPN match_start (geri açıldı)

**Karar:** Tennis market'leri için `match_start_iso` ESPN ATP/WTA scoreboard'dan çekilir. Polymarket startTime fallback. İkisi de yoksa scanner filtresi market'i eler.

**Neden:** Polymarket tennis startTime'ı zaman zaman boş veya gecikmeli (turnuva-level event); `end_date_iso` fallback'i turnuva sonunu gösterip 24h filtresini şişiriyor. ESPN otorite + program değişikliklerini günceller. Tennis 2026-05-05'te `sport_rules`'tan kaldırılmıştı (skor scope dışıydı); şimdi sadece match_start metadata için geri açıldı.

**Etki:**
- `src/orchestration/tennis_start_enricher.py` (yeni — 185 satır, TDD 7 unit test)
- `src/config/sport_rules.py` — `tennis` entry geri (`start_source: "espn"`, `espn_leagues: ("atp", "wta")`); `score_source` yok (skor entegrasyonu kapalı)
- `src/orchestration/scanner.py` — `tennis_start_enricher` optional DI; enrich → filter → sort
- `src/orchestration/factory.py` — mevcut `ESPNClient` instance'ı paylaşılır
- `config.yaml` — `scanner.tennis_start_cache_ttl_sec: 300`

---

### 2026-05-22 — Event cap 2 → 3
**Karar:** `max_positions_per_event` default 2'den 3'e çıkarıldı.
**Neden:** Aynı event'te moneyline + totals + run_line (MLB submarket) üçü birden çalışabilmeli. SPEC-J/K bağımsız bahis tanımına uyumlu.
**Etki:** `config.yaml`, `src/config/settings.py`, `src/strategy/entry/gate.py`, `ARCHITECTURE_GUARD.md`. Test güncellemeleri ayrı görevde (Task 2).

---

## SPEC-UNIFIED-PAPER-LAB: Tek Bot — Basket + Tenis Paper (2026-05-29)

**Karar:** Tennis lab + main bot birleştirildi. Tek bot, tek bankroll, sadece basket + tenis, mode=paper default.

**Sebep:** Tennis lab ayrı branch'ta + ayrı process + ayrı config + ayrı dashboard yorucu hale gelmişti. Diğer sporlar (NHL 13 trade %0 WR -$57, NCAAF/CFL/UFL/golf 0 trade) portföyde anlam taşımıyordu. Gerçek paraya geçiş öncesi HIPER GERÇEKÇİ tek paper bot kurmak hedef.

**Üç fazlı uygulama (rollback-friendly):**
- **Faz 1** (commit 56a4a52): rollback safety (git tag `pre-unified-2026-05-29` + state snapshot `_archive/2026-05-29/`) + spor whitelist daraltma (basket-only).
- **Faz 2** (commit c506fee, tag `phase2-paper-executor-2026-05-29`): paper realism executor — `PaperConfig` + `ClobBook` (5sn TTL cache) + `paper_fill.py` (pure walk_buy/walk_sell) + `PaperExecutor` (FOK/GTC strategy parity, 1¢ tick, $1 min order, fee + gas) + force-close paper-aware (no_bids → stuck, no zero-realize). Mode hala dry_run.
- **Faz 3**: tennis cherry-pick (gamma series_id + Sackmann refresher) + factory tennis startup hook + config.yaml (tennis whitelist + exclude_combos + mode=paper) + reboot.py paper desteği + `_backup_tennis_lab/` arşivlendi.

**Whitelist (final):** nba, wnba, ncaab, wncaab, cbb, euroleague, nbl, atp, wta (9 entry).

**Exclude combos (Phase 3):** tennis_set_totals (atp/wta × A/B), tennis_first_set_winner (atp/wta × A/B) — paper lab analizinden negative-EV kanıtı (97 trade post-spike-removal: -$63 ve -$162 net).

**HIPER gerçekçilik (yapay simülasyon YOK):** Gerçek Polymarket orderbook → FOK/GTC choose_order_strategy (live ile aynı) → walk_buy/walk_sell slippage tolerans + min_fill_ratio %95 → fee/gas modelleme → audit log (paper_executions.jsonl, book snapshot dahil). Mevcut "bid yoksa 0 realize" davranışı paper'da KAPATILDI; pozisyon stuck açık kalır.

**Etki:** `config.yaml`, `src/config/settings.py` (PaperConfig + EdgeConfig.exclude_combos), 5 yeni modül (`src/domain/execution/paper_fill.py`, `src/infrastructure/apis/clob_book.py`, `src/infrastructure/audit/paper_executions.py`, `src/infrastructure/data/sackmann_refresher.py`, `src/orchestration/paper_executor.py`), `src/infrastructure/executor.py` (mode dispatch), `src/orchestration/factory.py` (Sackmann hook + paper config wire), `src/orchestration/exit_processor.py` (paper force-close), `src/infrastructure/apis/gamma_client.py` (series_id), `scripts/reboot.py` (paper choice), `scripts/refresh_sackmann.py`, ~29 yeni test (full suite 1579 passed).

**Rollback:** `git reset --hard pre-unified-2026-05-29` + `cp -r _archive/2026-05-29/data/* data/`.

---

## SPEC-Q: Dashboard Archive Birleştirme — Exited Tab Kalıcı Geçmiş (2026-05-21)

**Karar:** Dashboard `read_trades` fonksiyonu artık `logs/audit/trade_history.archive.*.jsonl` dosyalarını da okuyor (Tennis Lab pattern'i: `sorted(audit_dir.glob("trade_history.archive.*.jsonl"))`). Realized PnL widget aynı listeden hesaplandığı için widget toplamı ↔ exited tab toplamı her zaman uyumlu.

**Neden:** 2026-05-21 12:35'te bir tetikleyici (henüz tespit edilemedi — TODO investigate) reboot dışında `archive_audit_logs` çalıştırdı; 26 kapanmış işlem `trade_history.archive.20260521_093516.jsonl`'a taşındı. Dashboard arşivleri okumadığı için exited tab boşaldı ve realized PnL widget 0 gösterdi. Kullanıcı talebi: reboot yapılmadığı sürece exited tab dolu kalmalı. Çözüm: Tennis Prediction Lab spec'inde aynı problem `glob("*.jsonl")` ile çözülmüş (`docs/superpowers/plans/2026-05-19-tennis-prediction-lab.md:3296`), aynı pattern normal dashboard'a uygulandı.

**Etki:**
- `src/presentation/dashboard/readers.py` — `read_trades` path listesine archive glob eklendi; dedupe (cid, entry_ts) zaten vardı.
- `tests/unit/presentation/dashboard/test_readers.py` — eski "archive okunmaz" testi tersine çevrildi, multi-archive merge testi eklendi.

**Sonuç:** 86 dashboard testi yeşil. Reload sonrası exited tab arşiv kayıtları dahil tüm geçmişi gösteriyor. Reboot semantiği değişmedi (ana dosya hâlâ archive ediliyor) ama dashboard arşivi de okuduğu için görsel kayıp yok.

**TODO (investigation):** 12:35'teki gizemli archive tetikleyicisinin kaynağı (scheduled task, hook, IDE script). Bu SPEC onu çözmüyor — sadece dashboard görsel kaybını gideriyor.

---

## SPEC-P: Fixed-Tier Sizing + Yumuşak Exposure Cap (2026-05-21)

**Karar:** Bankroll-relative sizing kaldırıldı. Tier başına sabit dolar: A=$50, B=$30, C=0. Exposure cap "yumuşak" — exposure < cap iken tam trade alınır (cap'i geçebilir), exposure ≥ cap → blok. Size clipping yok.

**Neden:** Mevcut `bankroll × confidence_bet_pct` formülünde bankroll = nakit (initial + realized − açık invested). 12 pozisyon açıkken bankroll küçülür → geç gelen iyi maç küçük bahis alır. Kullanıcı kanıtı: WNBA Portland A-tier $18.35 (beklenen $50). Yeni model path-independent: sıra önemsiz.

**Cap motivasyonu:** Eski "soft+hard buffer + clipping" mantığı (`hard_cap_overflow_pct: 0.02` + `min_entry_size_pct: 0.015` + `min(adjusted, available)`) yerine tek sade kural: cap'in altında tam trade, üstünde blok. Tek bir trade ile cap'in geçilebilmesi (yumuşaklık) zaten mevcut overflow buffer'ın amacıydı — sabit-tier dünyada bu buffer doğal şekilde "tek trade'lik".

**Yapısal değişiklikler:**
- `config.yaml` + `RiskConfig`: `max_single_bet_usdc`, `max_bet_pct`, `confidence_bet_pct`, `hard_cap_overflow_pct`, `min_entry_size_pct` kaldırıldı. `fixed_bet_usdc: {A: 50, B: 30}` eklendi.
- `position_sizer.confidence_position_size`: `bankroll` + cap parametreleri kalktı; sadece `(confidence, fixed_bet_usdc)` alır.
- `exposure.at_or_over_cap(positions, total_portfolio_value, soft_cap_pct) -> bool`: yeni helper. Eski `exceeds_exposure_limit` + `available_under_cap` kaldırıldı (dashboard'a hizmet eden `fill_ratio` korundu).
- `gate.py` + `entry_processor.py`: clipping (`min(adjusted, available)`) kaldırıldı; cap kontrolü `at_or_over_cap` ile.

**Test delta:** 1106 → 1113 (+7). `test_position_sizer` ve `test_exposure` sıfırdan yazıldı; `test_gate` clipping testleri "yumuşak cap" davranışına dönüştü; `test_entry_processor` skip_detail formatı `available/min` → `invested/cap`.

**Plan referansı:** [PLAN.md](PLAN.md) PLAN-FIXED-SIZING-001 (uygulama bitince silinir).

**Mimari uyumluluk:** ARCH_GUARD 8 anti-pattern ✓ (config kaynak, dosyalar küçüldü, domain saf kaldı).

---

## SPEC-R: MLB Submarket Foundation — Model-Anchor Entry Path Altyapısı (2026-05-21)

**Karar:** Sport+market_type kombinasyonu için anchor kaynağı seçilebilir hale getirildi (`anchor_source(sport_tag, market_type) → 'bookmaker'|'model'`). MLB totals/run-line için model anchor. `EntryProcessor.process_signals` public API model-path için bookmaker bypass entry noktası. Gate.py'daki 5 sport-agnostic portfolio guard `portfolio_guards.py` modülüne extract edildi (DRY refactor, zero-regression).

**Neden:** Odds API baseball için sadece moneyline probability sağlıyor; totals/run-line bookmaker yok. Eski DRAFT (sandbox lab) reddedildi; kullanıcı ana bot entegrasyonu istedi. Bu plan altyapıyı kurar — Plan 2-3-4 modeli ve veri katmanlarını ekler.

**Etki:**
- Yeni: `src/orchestration/portfolio_guards.py`, `src/strategy/entry/mlb_submarket_engine_protocol.py`
- Modifiye: `src/models/enums.py` (EntryReason.MLB_SUBMARKET), `src/config/sport_rules.py` (anchor_source), `src/config/settings.py` (MlbSubmarketConfig), `config.yaml` (disabled default), `src/strategy/entry/gate.py` (portfolio_guards kullanır), `src/orchestration/entry_processor.py` (process_signals + run_heavy dispatch), `src/orchestration/scanner.py` (anchor dispatch + collect_model_signals), `src/orchestration/factory.py` (engine inject), `src/orchestration/agent.py` (AgentDeps.mlb_submarket_engine field)
- 10 task TDD ile uygulandı. Mock engine ile end-to-end smoke test PASS.

**Sonraki:** Plan 2 (domain model — rate shrinker, Log5, Markov, simulators, pricers), Plan 3 (infrastructure data — Stats API, Statcast, weather, rate cache), Plan 4 (wire-up gerçek engine + backtest).

**Plan 2 (Domain Model) tamamlandı (2026-05-21):**
18 saf domain modülü `src/domain/mlb_submarket/` altında. Layer 0 (rate shrinker — empirical Bayes Beta + Marcel weights), Layer 1 (PA outcome dispatcher: handedness/TTO/Log5 + park/weather), Layer 2 (24-state Markov + DP/SAC FLY), Layer 3 (Monte Carlo inning, 10k iter seedli reproducible), Layer 4 (9-inning convolution + DH 7-inning), Layer 5 (totals + spread pricers). Akademik temel: Haechrel SABR 2014 multi-class Log5, Tango RE Matrix (1950-2015 MLB average), Marcel 5/4/3 weighting. 133 yeni test (8/18 Layer 1 + 19 Markov + 9 simulators + 8 totals + 7 spread + ...), 1290/1290 full suite. Tek yeni bağımlılık: numpy. Plan dosyası silindi.

**Plan 3 (Infrastructure) tamamlandı (2026-05-21):**
5 infrastructure modülü `src/infrastructure/mlb_data/` altında. statsapi_client (MLB Stats API schedule + game feed + lineup, exponential backoff retry), statcast_client (pybaseball wrapper + event aggregation, JSON file cache), weather_client (Open-Meteo raw conditions, C→F + km/h→mph conversion), rate_cache (JSONL append-only persistence + clear_expired), scratch_detector (lineup change detection). 39 yeni test, 1329/1329 full suite. Yeni bağımlılık: pybaseball>=2.2. Domain layer DIRECTLY çağırmıyor — Plan 4 engine bağlayacak.

**Plan 4 (Wire-Up + Backtest) tamamlandı (2026-05-21):**
Gerçek `MlbSubmarketEngine` (`src/strategy/entry/mlb_submarket_engine.py`) Plan 2 (domain math) ve Plan 3 (data clients) modüllerini bağlar; Plan 1 Protocol'üne uyar. `mlb_signal_adapter.py` saf converter (EdgeCandidate → Signal, P(YES) preserved). Factory artık `config.mlb_submarket.enabled=True` ise gerçek engine inject ediyor — Plan 1 placeholder warning kaldırıldı. TODO-DRY persist refactor: `_persist_filled_position` shared helper hem bookmaker-anchor (`_execute_entry`) hem model-anchor (`_persist_model_entry`) path'leri tarafından kullanılıyor. Backtest CLI scaffold `scripts/mlb_submarket_backtest.py` accuracy + edge-weighted accuracy ölçer. 30 yeni test, **1359/1359 full suite**. Plan 4 simplifications (v2'ye ertelendi): Marcel multi-season weighting, bullpen segmentation, full ballpark roster (Plan 4 v1: 5 representative), DH detection, batter/pitcher handedness lookup. SPEC-R 4 fazlı plan TAMAMLANDI.

**Aktivasyon (production):** `config.yaml`'da `mlb_submarket.enabled: true` yapılır + `python scripts/reboot.py reload`. Default `false` — kullanıcı manuel açar.

---

## SPEC-O: Tennis Lab Full Paper Trading Wire-Up (2026-05-20)

**Karar:** Tennis sandbox artık ana botun entry/exit/state machinery'sini paper modda kullanır; edge kaynağı = Glicko-2 + Klaassen-Magnus iid model (bookmaker konsensüsü değil). 10 aşamalı PLAN-TENNIS-001 ile bağlandı.

**Neden:** SPEC-N diagnostic-only tennis loop yetersizdi — kullanıcı dashboard widget'larını besleyen tam paper trading istedi ("öbür dashboard'dakilerin aynısı aynı mantık sadece tennis için"). Diagnostic JSONL kaydı korunur, üstüne gerçek pozisyon yaşam döngüsü eklenir.

**Mimari karar (Stage 4 BLOCKED → resolved):**
EntryGate (`src/strategy/entry/gate.py`) bookmaker konsensüsüne hardwired — odds_enricher tüm tennis signal'larını `no_bookmaker_data` ile reddediyor. **Çözüm: Option (a)** — tennis_agent process_signals'ı çağırmadan ÖNCE sizing'i confidence_position_size ile yapar; EntryProcessor.process_signals tennis için sadece portfolio-level guard'ları (circuit_breaker, cooldown, max_positions, event_cap, blacklist, manipulation, entry_price_cap, exposure_cap) koşar.

**Yeni public API:** `EntryProcessor.process_signals(markets, signals) -> None` — bookmaker bypass eden tennis paper trading giriş noktası.

**Yeni dosyalar (tennis-lab branch feature/tennis-lab):**
- `src/strategy/entry/tennis_signal_adapter.py` — EdgeCandidate → Signal dönüşümü
- `src/orchestration/_entry_processor_signals.py` — 8 portfolio guard impl (DRY-DEBT: TODO-TENNIS-DRY ile gate.py ile birleştirilecek)
- `scripts/debug_tennis_markets.py` — Polymarket tennis market_type/sport_tag denetimi
- `scripts/verify_tennis_isolation.py` — tennis-lab path isolation guard
- `scripts/inject_fake_tennis_position.py` — dashboard visual testi için sahte position
- `scripts/close_fake_tennis_position.py` — sahte position kapatma
- `scripts/dashboard_audit.py` — 11 dashboard endpoint sanity check

**Modified (tennis-lab branch only):**
- `src/orchestration/tennis_agent.py` — heavy + light cycle, sizing+process_signals+persist+equity_snapshot
- `src/orchestration/tennis_factory.py` — state/executor/gate/EntryProcessor/ExitProcessor/equity_logger(dual-write)/trade_logger(dual-write)/skipped_logger composition
- `src/orchestration/entry_processor.py` — process_signals public API
- `src/models/enums.py` — EntryReason.TENNIS değeri eklendi
- `config_tennis.yaml` — bankroll $500, A→$50 (10%), B→$40 (8%), max_duration_days 10
- `scripts/tennis_main.py` + `scripts/tennis_dashboard.py` — absolute path anchoring

**Mitigation (ana bot risk yok):**
- Tüm src değişiklikleri feature/tennis-lab branch'inde (worktree); master'a SADECE bu SPEC-O entry merge edilir.
- entry_processor.py'a EKLENEN process_signals public API run_heavy davranışını DEĞİŞTİRMEDİ (test_run_heavy_behavior_unchanged_after_refactor doğruladı).
- EntryReason enum genişlemesi backward-compat (yeni değer).
- tennis-lab state izolasyonu: ayrı `tennis-lab/data/positions.json`, `tennis-lab/logs/audit/*`, vs. — main bot dosyalarına sıfır yazma (verify_tennis_isolation.py garantörü).

**Toplam değişim:**
- 13 commit (Stages 0-9.5) on feature/tennis-lab
- 1303 test geçiyor (15 stage ekledi, 0 regression)
- Dashboard: 11/11 endpoint PASS

**Sonraki adımlar (ertelenmiş):**
1. **TODO-TENNIS-DRY** — 8 guard predicate gate.py ↔ _entry_processor_signals.py duplication; portfolio_guards.py'a extract et.
2. **sport_rules tennis lookup** — tennis sport_tag duration map'te yok; graduated SL skipped, sadece flat SL + near_resolve fire. Sport-specific exit rules sonraki yinelemede.
3. **4 hafta paper trade gözlemi** — sonra accuracy ≥ %53 ise canlıya geç ($5-10 pozisyon).
4. **Legacy orphan file cleanup** — `tennis-lab/logs/trade_history.jsonl` + `logs/skipped_trades.jsonl` (root) artık kullanılmıyor; Stage 10'da silindi.

---

## SPEC-N: Tennis Prediction Lab v1.0 (2026-05-19)

**Karar**: Polymarket tenis alt market'lerinde (First Set Winner + Set Handicap −1.5 + Total Sets U 2.5) bookmaker'ın olmadığı market inefficiency'yi exploit eden ayrı sandbox sistem inşa edildi. Glicko-2 + Klaassen-Magnus tahmin motoru.

**Kanıt**: Polymarket scan tennis market analizi (2026-05-19): 66 unique ATP singles match, alt market liquidity $4.6M, alt market 24h volume sadece $61K — derin orderbook ama düşük aktivite = sharp bookmaker yok = inefficient pricing.

**Implementasyon**:
- **Sandbox**: git worktree `../tennis-lab`, `feature/tennis-lab` branch
- **Bankroll**: $500 paper, dashboard port 5051
- **Data**: Sackmann ATP CSV (1968-Şubat 2026, 13,092 maç indi 2022-2026 için) + TML backup
- **Rating**: Glicko-2, surface ayrı (clay/grass/hard), serve/return ayrı — 817 oyuncu için rating üretildi
- **Math**: Klaassen-Magnus point-by-point (Newton-Keller game formula düzeltildi — plan'daki polynomial yanlıştı, iid recursion + deuce kısayoluyla değiştirildi)
- **Markets**: 3 — First Set Winner, Set Handicap −1.5, Total Sets U 2.5
- **Confidence**: A-tier ($25) + B-tier ($20), C YOK; min_h2h_years yalnızca A-tier'de zorunlu
- **Edge**: ≥%5
- **Event guard**: Max 2 trade/event (best |edge| 2 tanesi seçilir)
- **Self-diagnostic**: Per-trade feature snapshot + `/diagnose` CLI (group-by surface/tier/feature)

**Yeni modüller**:
- `src/domain/prediction/glicko2.py` — pure Glicko-2 math (Glickman paper exact örneği test edildi)
- `src/domain/prediction/klaassen_magnus.py` — pure tennis probability formulas (g(0.5)=0.5 doğrulandı)
- `src/domain/prediction/feature_extractor.py` — H2H + form + counts
- `src/domain/prediction/tennis_predictor.py` — 3 market dispatcher
- `src/infrastructure/data/sackmann_csv_client.py` + `tml_csv_client.py` + `tennis_ratings_store.py`
- `src/strategy/entry/tennis_entry.py` — max 2 per event
- `src/orchestration/tennis_diagnostic_logger.py` — per-trade JSONL
- `src/orchestration/tennis_factory.py` — sandbox composition root
- `scripts/build_tennis_ratings.py` + `download_sackmann.py` + `diagnose.py` + `tennis_main.py` + `tennis_dashboard.py`

**Değişen modüller (sandbox-only, ana bot unaffected)**:
- `src/config/settings.py` (+TennisConfig + TennisConfidenceTier)
- `src/orchestration/scanner.py` (allowed_sports_market_types opsiyonel, fallback to legacy)
- `config.yaml` → `config_tennis.yaml` override

**Test delta**: 1114 → 1181 (+67 yeni tennis unit + integration test)

**Top 5 ATP rating**: Sinner 2160 | Alcaraz 2028 | Djokovic 1947 | Zverev 1874 | Fils 1809 (sanity check geçti)

**Live'a geçiş**: Paper trade 4 hafta → accuracy ≥%53 → live küçük pozisyon ($5-10).

**Kill switch**: `git worktree remove ../tennis-lab --force` (3 komut, ana bot etkilenmez).

**Riskler ve mitigasyon**:
- Sackmann veri 3 ay eski (clay sezonu eksik) → self-diagnostic surface tag ile gözle
- Model accuracy <%50 → /diagnose ile sebep bul, model güncelle, paper tekrar
- Sandbox kod main bot'u etkiler → git worktree izolasyon

**Açık V2 noktalar**: WTA support, doubles, live in-game prediction, daily ATP scrape, paid live API.

---

## SPEC-M: PriceFeed Sanity Layer (2026-05-19)

**Karar**: WS price feed'e 4 yapısal koruma — spike rejection, REST 404 cache invalidate, asks/bids sort-agnostic, near-resolve spread sanity.

**Kanıt**: KBO bug 2026-05-19. Bilgisayar 6.5 saat uyudu → WS reconnect → REST `/book` 404 → eski cache fiyat ($0.61) kaldı → sonraki WS mesajında sahte $0.97 spike geldi → bot near_resolve tetikleyip "+$10.62 realized" kaydetti. Gerçek market max $0.68'di, $0.97 hiç işlem olmamış sahte fiyattı. Dry_run modu olduğu için para kaybı yok; live modunda exposure tracking bozulurdu.

**Root cause**: `_update_price` sanity check'siz; `_fetch_rest_snapshots` 404'te cache'i invalidate etmiyordu (eski stale fiyat kalıyor); `_best_ask_from_snapshot` sort yönüne kör güveniyordu (`asks[-1]`); near_resolve sadece ask kontrol ediyordu (bid spread'i ignore).

**Implementasyon**:
- **Fix 1** (`_update_price`): tek tick'te |Δ| > `max_spike_pct` (default 0.50) → WARNING log + reject. `stats["spikes_rejected"]` sayacı.
- **Fix 2** (`_fetch_rest_snapshots`): `status_code == 404` → `self._prices.pop(tid, None)` + WARNING log. Bot fiyat bulamayınca exit kararı vermez (mevcut `get_price()=None` handle var).
- **Fix 3** (`_best_ask/bid_from_snapshot`): `min(prices)` / `max(prices)` — sort yönünden bağımsız. Eski `[-1]` indexing ASC sort durumunda HIGHEST ask döndürüyordu.
- **Fix 4** (`near_resolve.check`): `ask - bid > max_spread` (default 0.10) → sahte likidite, reddet. KBO bug bid=0.60 ask=0.97 → 37¢ spread fake'lendi.

**Config**:
- `config.yaml > price_feed.max_spike_pct: 0.50`
- `config.yaml > price_feed.max_spread_for_near_resolve: 0.10`
- `PriceFeedConfig` Pydantic model `settings.py`'a eklendi
- `PriceFeed(max_spike_pct=cfg.price_feed.max_spike_pct)` factory'de wire edildi
- `monitor.evaluate(near_resolve_max_spread=...)` → `exit_processor.run_light` config'den geçer

**Yeni dosyalar**: 0 (mevcut dosyalara guard eklendi)
**Değişen dosyalar (6)**: `price_feed.py`, `near_resolve.py`, `monitor.py`, `exit_processor.py`, `factory.py`, `settings.py` + `config.yaml`

**Test delta**: 1106 → 1114 (+8 yeni SPEC-M test):
- `test_update_price_rejects_spike_above_50pct`
- `test_update_price_accepts_normal_change_below_50pct`
- `test_fetch_rest_snapshots_404_invalidates_existing_cache`
- `test_best_ask_works_regardless_of_sort_order`
- `test_best_bid_works_regardless_of_sort_order`
- `test_near_resolve_rejects_when_spread_above_threshold`
- `test_near_resolve_accepts_when_spread_within_threshold`
- `test_near_resolve_spread_check_skipped_when_bid_zero`

**Mimari uyumluluk**: ARCH_GUARD Kural 6 (config'den, magic number yok), Kural 12 (Infrastructure WARNING log), Kural 11 (test zorunlu), Kural 7 (P(YES) ilgisiz).

---

## SPEC-K: Bookmaker Spread/Totals Köprüsü (2026-05-10)

**Karar**: SPEC-J basketbol spread/totals exit pipeline'ını ekledi ama entry tarafı için bookmaker prob köprüsü yoktu — bot Odds API'dan SADECE `markets=h2h` (moneyline) çekiyordu. SPEC-K bu köprüyü kurar: Odds API'dan spread + totals da çek, parser yaz, entry pipeline'a wire et.

**Kanıt**: SPEC-J reload sonrası 18:57 cycle'da scanner 15 NBA spread/totals market'i geçirdi (liquidity $19k-$806k, accepting=True) ama HİÇ entry açılmadı çünkü bookmaker prob hesaplanamıyordu.

**Implementasyon**:
- **Odds API**: `markets=h2h,spreads,totals` — tek çağrı, 3 market tipi birden
- **Spread parser**: bookmaker `spreads` market'inden `(line, home_prob, away_prob)` — vig normalize, ±0.5 line tolerance
- **Totals parser**: bookmaker `totals` market'inden `(line, over_prob, under_prob)` — aynı vig + tolerance
- **Vig bounds**: yeni domain modülü `src/domain/analysis/vig_bounds.py` (VIG_2WAY_MIN/MAX=0.85/1.20, VIG_3WAY_MAX=1.30) — DRY (h2h + spread + totals tek kaynak)
- **EnrichResult genişler**: spread_line, total_line, total_side alanları eklendi
- **Entry processor**: Position constructor'a 4 yeni alan (sports_market_type, spread_line, total_line, total_side) wire edildi
- **Config**: `odds_api.spread_totals_line_tolerance: 0.5` (single source of truth, parser default kaldırıldı)
- **Dosya split**: odds_enricher.py 413 → 236 satır (ARCH_GUARD <400), spread/totals branch'leri `_spread_totals_enricher.py`'a taşındı

**Yeni dosyalar (3)**: `src/domain/analysis/vig_bounds.py`, `src/strategy/enrichment/_spread_totals_parser.py`, `src/strategy/enrichment/_spread_totals_enricher.py`
**Değişen dosyalar (6)**: enrich_outcome (4 yeni alan + 2 fail reason), odds_enricher (split + branch), settings (OddsApiConfig), config.yaml (odds_api section), factory (line_tolerance wiring), entry_processor (Position fields)

**Test delta**: 1115 → 1146 (+31 yeni test, 0 regresyon)
**5 commit**: 4 init + 1 quality fix (split + vig consts + tolerance source-of-truth).

**Açık konular (gelecek SPEC)**:
- `parse_total_line` regex Polymarket totals question pattern variant'larıyla uyumsuz olabilir → SPEC-L?
- Sport-specific tolerance (NCAAF spread line variance daha geniş) → SPEC-M?
- Sport-specific edge threshold kalibrasyonu (NBA spread için 0.04 vs moneyline 0.06) → gerçek veri sonrası

---

## SPEC-J: Basketbol Spread + Totals + Combat Sports Kapatma (2026-05-10)

**Karar**: Basketbol spread + totals piyasaları aktive edildi (önce sadece moneyline çalışıyordu). Aynı turda combat sports (UFC + MMA + boxing) kapatıldı (canlı skor yok → reaksiyon imkansız).

**Veri arka planı**:
- **NBA spread** (canlı bot.log): 10W/7L/3N, %58.8 winrate, **+$114.18 net**. predictive_dead 3 trade'de +$54.70 (en kârlı tek kural).
- **NBA totals**: SADECE 2 trade canlı veri (her ikisi near_resolve, +$44.23, %100 winrate). İstatistiki yetersiz; kullanıcı bilerek yetersiz veriyle risk aldı.
- **NBA moneyline**: 4W/2L, sadece +$0.39 net — başarısız.
- **UFC**: 7 trade net **-$51**, hep zarar (KO/karar bazlı, fiyat çakılır + reaksiyon yok).

**Migrate edilen mantık** (pre-rollback `pre-rollback-2026-05-04` git tag'inden, 0 satır kopya):
- **Bill James %99 safe lead** formülü: `margin >= 0.861 × √seconds` → spread ölü
- **Poisson totals dead**: `points_diff > 1.218 × √seconds` → totals ölü (1.218 = 0.861 × √2 toplam variance)
- **EV-bazlı predictive_dead**: `comeback < hold_threshold AND (bid + safety_margin) > comeback` → şimdi sat
- **Empirical NBA key numbers**: 6dk-7pt, 3dk-4pt, 1dk-3pt eşikleri

**Pipeline katmanları**:
- Spread (5 katman): OT_DEAD → STRUCTURAL_DAMAGE → SPREAD_MATH_DEAD → PREDICTIVE_DEAD → EMPIRICAL_DEAD
- Totals (4 katman): STRUCTURAL_DAMAGE → TOTALS_MATH_DEAD → PREDICTIVE_DEAD → EMPIRICAL_DEAD (OT YAGNI olarak hariç)

**Yeni dosyalar (5)**: `src/domain/math/safe_lead.py`, `src/strategy/exit/{nba_spread_exit,nba_totals_exit,_nba_dispatch,_nba_score_mapper}.py`
**Değişen dosyalar (8)**: enums (PREDICTIVE_DEAD/SCORE_EXIT + SportsMarketType + TotalSide), position model (4 yeni alan), settings (BasketballExitConfig), monitor (priority 2.5 dispatch), scanner (spreads/totals filter), exit_processor (config wiring), config.yaml (combat sil), sport_rules (BASKETBALL_TAGS DRY)

**Test delta**: 1018 → 1115 (+97 yeni test, 0 regresyon)

**14 commit**: 4 grup × (init + quality fix). Subagent-driven development + 2-stage review (spec uyum + kod kalitesi). Her grup için ARCH_GUARD self-check + TDD.

**Kapsam dışı (gelecek SPEC)**: NHL/MLB spread/totals (farklı sport math), WNBA-spesifik multiplier kalibrasyonu, NBA totals OT pipeline, scale-out tier spread/totals kalibrasyonu.

---

## Sessiz Bug Audit + Fix Stratejisi (2026-05-08)

**Karar**: 3 günlük dry_run sonrası bot'ta **sessiz state corruption** keşfedildi. Bot 40 işlem yapmış, $195 realized PnL biriktirmiş ama trade_history.jsonl'e **tek satır yazmamış**. Reload sonrası reconcile snapshot'ı log ground truth'a göre zerodu, $195 buharlaştı.

**Kök sebep**: `exit_processor.log_partial_exit(...)` migration sırasında `price` parametresinin zorunlu olduğu yeni signature'a göre güncellenmemiş. Her scale-out'ta TypeError fırladı, `agent.run()` cycle try/except yutuyordu.

**Hemen uygulanan fix'ler**:
- `exit_processor.py:108` — `price=pos.current_price` eklendi
- `startup.py:_reconcile_realized_pnl` — trade_history boş + snapshot dolu → "logging gap suspected, trusting snapshot" davranışı (otomatik zerolama YOK)

**Audit sonuçları (10 sorun, severity sıralı)** — Detayları `SPEC.md` SPEC-A/SPEC-B/SPEC-C:

| # | Sorun | Severity | Fix Konumu |
|---|---|---|---|
| 1 | agent.py cycle silent except | CRITICAL | SPEC-A1 |
| 2 | apply_partial_exit silent no-op | CRITICAL | SPEC-A2 |
| 3 | score_info hiç geçilmiyor → guard'lar pasif | HIGH | SPEC-B (ESPN) |
| 4 | match_start ParseError → tüm guard'lar bypass | HIGH | SPEC-B (ESPN fallback) |
| 5 | scanner ParseError → kabul + magic 8.0 | HIGH | SPEC-B + config |
| 6 | 3-way bookmaker silent skip | MED | SPEC-C (futbol açılınca) |
| 7 | tennis sport_classifier ölü kod | MED | SPEC-A5 (eksik kalan) |
| 8 | trade_logger.read_all corrupt skip | MED | SPEC-A3 |
| 9 | factory private attribute mutation | LOW | SPEC-A4 |
| 10 | tennis resolver erken return yok | LOW | SPEC-A5 |

**Yapılış sırası**:
1. **SPEC-A** (5 fix, ~1 gün): Sessiz hata yutma kalıbı kalıcı kapatılır → bundan sonra yeni bug'lar HEMEN ortaya çıkar
2. **SPEC-B** (ESPN client wire, ~3-5 gün): Skor-aware exit guard'lar aktifleşir, ParseError fallback'i ESPN'den gelir
3. **SPEC-C** (futbol açılana kadar park): 3-way bookmaker sanity

**Sebep bu sıra**: A1 (silent except) en kritik çünkü VARLIĞI tüm diğer bug'ları gizliyor. A1 olmadan B veya C içinde yeni bug'lar yine sessiz yutulur.

**Yasak (SPEC-A süresince)**:
- Entry/exit kuralları (gate.py, monitor.py): DOKUNMA
- ESPN client: SPEC-B kapsamı, SPEC-A'da değil
- 16 Nisan baseline davranışı: değişmiyor, sadece hata kalıbı

**SPEC-A tamamlandı (2026-05-08):**
- A1 — cycle programatik-hata 2-strike stop ✅ (commit 51cd558 + quality fix 25b239f)
  - Yeni: `src/orchestration/_agent_resilience.py` (CycleResilience + is_programmatic_error)
  - `agent.py` cycle except daraltıldı; programatik hata 2 ardışık → otomatik stop
  - Threshold `config.yaml → agent.cycle_max_consecutive_errors`'a taşındı (magic number yok)
- A2 — apply_partial_exit fail-loud + caller rollback ✅ (commit 9ed5121)
  - `manager.py:apply_partial_exit` — pozisyon yoksa ValueError
  - `exit_processor._execute_partial_exit` — try/except + state mutation rollback
- A3 — trade_logger corrupt-row counter + reconcile abort ✅ (commit 96886e9)
  - `trade_logger.read_all` — JSONDecodeError sayar; threshold (3) → flag
  - `startup._reconcile_realized_pnl` — GUARD-2 corrupt threshold abort
- A4 — TelegramCommandPoller public set_on_stop API ✅ (commit de7e8f2)
  - Private mutation kaldırıldı; public method ile callback wiring
- A5 — Tennis resolver erken return ✅ (commit 5b56500 + dormant markers 05d579a)
  - `sport_key_resolver` — atp/wta prefix veya tennis-related kw → erken None
  - `_match_tennis_key` + sponsor alias table DORMANT olarak korundu
  - 4 test silindi (eski tennis routing testleri); TODO-002 eklendi (re-enable safety net)

Test toplamı: 956 → 968 (+12 net yeni test). Bot artık sessiz hata yutmayacak — programatik bug 2 ardışıkta otomatik stop.

## SPEC-B Tamamlandı (2026-05-08): ESPN Score Client Wire

**Karar**: Audit'teki 3 sorun çözüldü:
- (3) score_info gate'lere geçiyor — ScoreEnricher light cycle'da pozisyonlar için ESPN skor çeker, exit_processor monitor.evaluate'a geçirir
- (4) match_start ParseError → guard bypass FIX'i — compute_elapsed_pct artık score_info varsa sport+period bazlı estimate döner
- (5) scanner magic 8.0 → config — ScannerConfig.max_post_start_hours; ParseError artık skip + warning (eskiden kabul ediyordu)

**Yeni dosyalar (taze yazıldı, pre-rollback REFERANS):**
- `src/infrastructure/apis/espn_client.py` (~200 sat) — ESPN public scoreboard fetcher (NBA/MLB/NHL)
- `src/orchestration/score_enricher.py` (~135 sat) — sport-dispatch + polling throttle + Odds fallback
- 3 yeni test dosyası (test_espn_client, test_score_enricher, test_monitor_elapsed_fallback, test_exit_processor_score)

**Değiştirilen dosyalar:**
- `src/strategy/exit/monitor.py` — compute_elapsed_pct(pos, score_info=None) signature + _estimate_elapsed_from_score helper
- `src/orchestration/exit_processor.py:run_light` — score_map parametre + monitor.evaluate'a score_info geçirir
- `src/orchestration/agent.py:run` — light cycle'da score_enricher.get_scores_if_due (try/except + log fallback)
- `src/orchestration/factory.py` — ESPNClient + ScoreEnricher build/wire
- `src/orchestration/agent.py:AgentDeps` — score_enricher field eklendi
- `src/config/settings.py` — ScoreConfig + ScannerConfig.max_post_start_hours
- `src/config/sport_rules.py` — NHL/MLB/NBA score_source/espn_sport/espn_league
- `src/orchestration/scanner.py` — magic 8.0 → config + ParseError skip
- `config.yaml` — score: section + scanner.max_post_start_hours

**Yapılmadı (kasıt):**
- Tennis ESPN parsing — kapalı (SPEC-A5)
- Soccer ESPN — futbol kapalı (SPEC-C parked)
- Polymarket↔ESPN team_resolver gelişmiş eşleşme — basit "question contains home/away" heuristic kullanıldı; gelişmiş eşleştirme TODO
- Odds API skor fallback — opt-in, varsayılan skip (Odds API skor opsiyonel + tennis/golf yok)

**Test toplamı:** 968 → 1002 (+34 yeni test).

**ESPN polling konfigürasyonu (config.yaml score:):**
- enabled: true (kill switch)
- poll_normal_sec: 60 (fiyat > 0.35)
- poll_critical_sec: 30 (fiyat ≤ 0.35)
- critical_price_threshold: 0.35

## Tarihsel Kayıt: 2026-05-08/09 Trade Geçmişi (audit kayıp, bot.log'dan çıkarıldı)

**Bağlam**: Reset/reboot zincirinde audit/trade_history.jsonl silindi. Geçmiş 9 full exit + 7 scale-out kayıtları kaybolduğu için dashboard EXITED panel'inde görünmedi. Bot.log'dan grep ile çıkarılıp buraya geri-yüklendi (sadece referans — dashboard'a etki etmez). Toplam +$58.31, dashboard'daki realized ile uyumlu.

### Full Exits (9 adet — 7W / 2L)

| Saat | Maç | Sebep | PnL |
|---|---|---|---|
| 02:11 | AHL Man-Gra | near_resolve | +$10.42 |
| 02:44 | WNBA Conn-NYL | near_resolve | +$6.55 |
| 03:15 | NHL Mon-Buf | stop_loss | **-$7.87** |
| 04:13 | MLB Col-Phi | market_flip | **-$43.08** |
| 04:27 | MLB LAA-Tor | near_resolve | +$8.11 |
| 06:26 | WNBA GSV-Sea | near_resolve | +$9.72 |
| 07:18 | NBA SAS-Min | near_resolve | +$14.53 |
| 12:22 | KBO Sam-NC | near_resolve | +$9.69 |
| 13:31 | KBO Kia-Lot | near_resolve | +$10.83 |

Toplam full exit net: **+$18.90**

### Scale-Outs (7 adet — hepsi pozitif)

| Maç | Tier | PnL |
|---|---|---|
| AHL Man-Gra | 1 | +$5.83 |
| MLB LAA-Tor | 1 | +$6.56 |
| MLB LAA-Tor | 2 | +$7.62 |
| NBA SAS-Min | 1 | +$5.00 |
| WNBA GSV-Sea | 1 | +$5.07 |
| KBO Sam-NC | 1 | +$4.52 |
| KBO Kia-Lot | 1 | +$4.81 |

Toplam scale-out: **+$39.41**

### Grand Total: +$58.31

### Notlar (gözleme değer)

- **Win rate %78** (7/9 full) — küçük örneklem ama iyi
- **MLB Col-Phi -$43.08 (market_flip)** — tek başına en büyük loss. market_flip exit kuralının agresifliği ileride incelenebilir
- **Tüm scale-out'lar pozitif** — tier 1 (+%25 PnL) ve tier 2 (+%50) trigger'ları doğru zamanlamış
- Trade kaynak: `scripts/diag_list_history.py` (bot.log'dan grep ederek üretir)

---

## SPEC-I Tamamlandı (2026-05-10): PriceFeed WebSocket Reliability

**Karar**: Polymarket CLOB WebSocket bağlantısının 3 zayıf noktası tespit edildi (web research) ve tamir edildi. Mid-game flip kayıplarının %50-70'ini önlemesi bekleniyor.

**3 Fix:**
1. **HEARTBEAT_INTERVAL_SEC**: 30s → **10s** (Polymarket protokolü 10s ping ister; 30s'de server silent close yapıyordu)
2. **STALE_TIMEOUT_SEC**: 120s → **60s** + watchdog aktif (Polymarket WS bilinen donma sorunu — GitHub Issue #26 — şimdi 60s data sessizliği force reconnect tetikler)
3. **Reconnect REST snapshot**: yeni `_fetch_rest_snapshots()` — subscribe öncesi `clob.polymarket.com/book?token_id=...` çağırır, disconnect sırasında kaçan fiyatları cache'e koyar, eski cache ile karar verme önler

**Dosyalar:**
- `src/infrastructure/websocket/price_feed.py` — sabitler güncellendi, `_stale_watchdog` async task eklendi, `_fetch_rest_snapshots` helper eklendi, `requests` import eklendi
- `tests/unit/infrastructure/websocket/test_price_feed.py` — 4 yeni test (ping interval, stale timeout, REST snapshot success, REST 404 graceful)

**Test toplamı:** 1014 → 1018 (+4 yeni test).

**Sebep — Web research bulguları (kaynak: arxiv 2605.00864, Polymarket docs, GitHub Issues #26 #292)**:
- Polymarket WS resmi dokümanı 10s ping interval bekliyor; biz 30s gönderiyorduk → server silent close
- "PriceFeed connection error: no close frame received" warning'leri bot.log'da çok sık görünüyordu — root cause budur
- Reconnect sonrası eski cache → bot 5-10s eski fiyatla karar verirken market_flip kuralı geç tetikleniyordu

---

## SPEC-C Tamamlandı (2026-05-08): 3-Way Bookmaker Sanity (Defensive)

**Karar**: Audit MED-1 — futbol açılınca aktif olacak silent bug'lar pre-emptive olarak kapatıldı (commit ee051d7):

- Soccer 3-way bookmaker draw odds yoksa silent skip → şimdi skip + INFO log (kaç drop)
- 3-way ve 2-way vig sanity check eklendi: pre-normalize total < 0.85 veya > 1.30 (3-way) / > 1.20 (2-way) → bookmaker reddedilir (outlier data koruması)

**Mevcut etki**: Yok — soccer kapalı (allowed_sport_tags'de yok), bu kod path'i runtime'da dormant.

**Futbol açılınca etki**: Soccer market'leri için bookmaker sayımı doğru loglanır + suspicious vig'li bookmaker'lar atlanır. Sum ranges:
- 3-way (soccer) tipik vig %5-10 → pre-normalize total [1.05, 1.10] beklenir; [0.85, 1.30] dışı outlier
- 2-way tipik vig %2-8 → pre-normalize total [1.02, 1.08] beklenir; [0.85, 1.20] dışı outlier

**Test toplamı:** 1002 → 1005 (+3 yeni test).

## SPEC-D Tamamlandı (2026-05-09): Silent log_partial_exit + Orphan Recovery

**Karar**: SPEC-A2'de gözden kaçan silent failure düzeltildi.

**Bug**: `trade_logger.log_partial_exit` matching entry bulamayınca `False` döndürüyordu sessizce. Reset/reboot sonrası audit silinmiş, pozisyonlar `data/positions.json`'dan restore edilmişti → scale-out olunca `log_partial_exit` `False` döndü, dashboard W/L counter (0W) ile in-memory `realized_pnl` (+$42.68) tutarsız oldu. Bot.log'da 6 SCALE-OUT vardı ama `trade_history.jsonl`'de 0 partial_exit.

**3 katmanlı fix:**
1. **trade_logger._rewrite_matching**: matching record bulamayınca WARNING log (sessiz değil). Hem `update_on_exit` hem `log_partial_exit` bu helper'ı kullanır → ikisi de WARN üretir.
2. **exit_processor._execute_partial_exit**: `log_partial_exit` dönüş değeri capture edilir; `False` ise SCALE-OUT log'undan önce ek warning ("trade_history defter kayit yapilamadi (orphan?)").
3. **startup.bootstrap**: Orphan pozisyon tespiti — `data/positions.json`'da olup audit'te entry'si olmayan pozisyonlar için `entry_reason="phantom-restored:{original}"` prefix'iyle audit entry yazılır → gelecek scale-out'lar matching bulur. Reconcile'dan ÖNCE çalışır. TradeRecord schema'ya dokunulmadı (sadece string prefix).

**Test toplamı:** 1005 → 1008 (+3 yeni test: 2 trade_logger warn, 1 startup orphan recovery).

**Kullanıcı etkisi**: Mevcut +$42.68 dashboard'da görünmeye devam eder. Yarın reload edilirse phantom-restored entry'ler audit'e yazılacak; scale-out'lar artık doğru kaydedilecek. Geçmiş scale-out'lar (bot.log'da var) audit'e geriye dönük yazılmaz — yeni scale-out'lardan itibaren defter düzgün.

---

## Tennis Devre Dışı (2026-05-05)

**Karar**: Tennis tarama + entry pipeline'dan tamamen çıkarıldı. **Matching katmanı korundu** (geri açmak istenirse hazır).

**Kaldırılan (5 dosya, ~20 satır):**
- `config.yaml` — `allowed_sport_tags`'den `tennis`, `"atp*"`, `"wta*"` (3 satır)
- `src/config/sport_rules.py` — `"tennis": {...}` SPORT_RULES entry + `tennis_atp/tennis_wta` _ALIASES + `tennis_*` prefix match
- `src/config/_sport_aliases.py` — `tennis_atp/tennis_wta` aliases

**Test güncellemesi:** `test_sport_rules.py`'dan tennis 3 testi sil + loop'tan çıkar; `test_scanner.py`'dan `test_tennis_wildcard_matches` + tennis_* allowed_tag sil. Test toplamı 960 → 956.

**Korunan (matching infrastructure — dormant):**
- `src/domain/matching/tennis_player_resolver.py` (Sackmann xref + fuzzy name)
- `src/domain/matching/tennis_tournament_resolver.py` (ATP/WTA tier + surface)
- `src/domain/matching/sport_classifier.py` — `atp/wta → tennis` mapping
- `src/domain/matching/odds_sport_keys.py` + `src/strategy/enrichment/sport_key_resolver.py` — dinamik turnuva resolver
- `src/infrastructure/apis/gamma_client.py` — tennis sport_tag override (slug normalization)
- `tests/unit/domain/matching/test_tennis_*.py` (3 dosya)

**Sebep**:
1. **Kâr/zarar**: Tenis pozisyonları açıldı ama in-match olasılık modeli yok (Tennis Magnus migrate edilmedi). Çıkış kararı "sport-agnostic" genel kurallarla — set/oyun seviyesinde kalibre değil. 2026-05-04 reboot sonrası 11 tenis pozisyon açıldı, hepsinin exit kararı geç oldu.
2. **Token tasarrufu**: Allowed tags'den çıkınca scanner tennis market'leri filter aşamasında eler → odds_enricher tetiklenmez → Odds API tennis çağrısı = 0. ESPN tennis polling = 0.
3. **Risk azaltma**: 16 Nisan baseline NBA/MLB/NHL moneyline + temel exit kurallarıyla kanıtlanmış. Tenis sport-specific davranışları olmadan riskli.

**Geri açma koşulu**: 16 Nisan baseline'a tennis_magnus.py + _tennis_exit_dispatch.py + sackmann_client.py migrate edilmesi + paper-test win rate ≥ %55 doğrulaması.

**Geri açma adımları (config-only)**: 5 dosyada toplam ~20 satır geri ekle (yorum satırlarına bakarak), reboot. Matching infrastructure zaten hazır.

---

## Altyapı Migration (2026-05-04 baseline rollback + selective infra)

**Karar**: `pre-rollback-2026-05-04` snapshot'tan **sadece altyapı paketlerini** kabul ederek `baseline-2026-04-16` (commit `11d0954`) üzerine kuruldu. Entry kuralları, exit kuralları, in-match olasılık modelleri ve sport-specific dispatcher'lar 16 Nisan halinde kaldı.

**Migrate edilen paketler (4):**
- **A — Dashboard görsel iyileştirmeleri**: `src/presentation/dashboard/` (chart_tabs, modal, sounds, balance-from-session) + `Sound/` (mp3) + dashboard testleri.
- **B — Slug + market eşleştirme**: `src/domain/sports/` (MLB+NHL question parsers, team aliases), `src/domain/matching/` (three_way_title, market_line_parser, tennis player/tournament resolvers, event_grouper), `gamma_client` sport_tag override (mlb→baseball), `scanner` 3-way sum filter + NBA/NHL spread+totals kabul, `src/config/sport_configs/` (3-way sport config map), `src/config/_sport_aliases.py`. **`models/market.py`**'a yalnızca `match_title: str = ""` field'ı eklendi (entry/exit kural değişikliği değil).
- **C — Log mimarisi**: `trade_logger` dual-write (audit + session), `archive_logger` audit-only kalıcı yedek, `equity_history`/`skipped_trade_logger` 3-tier path discipline, `_factory_loggers` DI builder, `operational_writers` skip-event yazıcı, `scripts/reboot.py` reload/reboot komutları + PID tekillik, `data/.gitignore`.
- **H — Slippage**: `executor.py` post-fill edge re-check + `STALE_PRICE_REJECT` path; yeni `fair_price`/`min_edge` parametreleri optional default `None` (16 Nisan entry_processor signature uyumu için).

**Atlanan paketler (kasıt):**
- Entry kuralları: `gate.py`, `_gate_helpers.py`, `_mlb_edge.py` — 16 Nisan halinde.
- Exit kuralları: `monitor.py`, `price_cap`, `scale_out`, `near_resolve`, `favored`, `market_flip`, `_*_dispatch.py`, tüm `*_score_exit.py` — 16 Nisan halinde.
- In-match olasılık modelleri: `src/domain/math/` tamamen — NHL empirical, MLB Pythagorean+log5+pitcher, Tennis Magnus, NBA safe_lead — hiçbiri migrate edilmedi.
- Yeni API client'ları: `mlb_stats_client`, `openweather_client`, `sackmann_client`, `espn_*_client` — migrate edilmedi (gamma_client + odds_client istisna).

**Sebep**: 16 Nisan baseline kanıtlanmış basit kural seti — pre-rollback'teki sport-specific in-match komplikasyonlarına dönmek istenmedi. Altyapı (görsel, log, slippage, market eşleştirme) iyileştirmeleri korundu çünkü trading kararına dokunmuyor; sadece bot'un veriyi nasıl topladığı, sakladığı ve gösterdiğini etkiliyor.

**Test düzeltmeleri**:
- `tests/unit/presentation/dashboard/test_routes.py`: `stop_at_pct` 12.0 → 8.0 (16 Nisan `daily_max_loss_pct: -0.08`).
- `tests/unit/domain/matching/test_odds_sport_keys.py`: tennis static "atp"/"wta" mapping testi 16 Nisan davranışına çekildi (None döner, dinamik resolver tournament-key türetiyor).
- `tests/unit/domain/matching/test_sport_mapping.py` ve `test_cricket_mapping.py` silindi (16 Nisan'da yok, pre-rollback'in genişletilmiş alias chain meta-testleri).
- `src/domain/matching/odds_sport_keys.py`: tennis static `"atp": "tennis_atp"` + `"wta": "tennis_wta"` satırları kaldırıldı.

**Sonuç**: 967 test pass, 0 fail. Bot 16 Nisan kararıyla trade ediyor, altyapı modernize edildi.

---

## Reboot/Reload Tekillik Garantisi

**Karar**: `scripts/reboot.py` — tek komut, hem reload hem reboot. `agent.pid` + `dashboard.pid` ile 1 bot + 1 dashboard garantisi.

**Neden**: Önceden bot ve dashboard elle `kill <PID>` + `python -m src.main` ile yönetiliyordu.
Tekillik yoktu — aynı anda 2 bot aynı cüzdana order gönderebilirdi. PID file kontrolü bu riski ortadan kaldırdı.
`process_lock.py` (bot) zaten `agent.pid` yazıyordu; `dashboard.pid` `src/presentation/dashboard/app.py main()` içine eklendi.

**Reload vs Reboot farkı**:
- Reload: kill → start. State (positions, circuit_breaker) dokunulmaz.
- Reboot: kill → arşivle → sil → start. `bot.log` ve `logs/archive/` asla silinmez (audit trail).

**Graceful window**: `kill → 2s bekle → start`. Windows'ta `taskkill /f /pid`.

---

## Live Event Entry — Odds API Penceresi

**Karar**: `commenceTimeFrom = now - 8h` (scanner'ın `_match_start_recent_or_future` 8h penceresiyle eşleşir).

**Neden**: Odds API `/v4/sports/{sport}/odds` endpoint'i "upcoming AND live games" döndürür.
`commenceTimeFrom=now` live eventleri dışarıda bırakır: `commence_time < now` → filter dışı → EVENT_NO_MATCH.
Doğrulama (2026-04-26): MIN/DEN Q1'de (T+25 dk), 8 US bookmaker, `last_update` saniyeler önce — suspended değil.
Gate filtreleri (max_entry_price=0.80, gap_threshold=0.08) Q4 near-resolve marketlerini zaten eler.

**Kapsam**: Sadece pre-game değil, live Q1-Q2 döneminde de entry mümkün.
Late-game (Q3+) → Polymarket fiyatı skoru yansıtır → GAP_TOO_LOW ile doğal elenir.

**Bilinen kısıtlama — Maç sonu EVENT_NO_MATCH**: Oyun bittikten ~30-60 dk sonra Odds API pre-game endpoint'i maçı listesinden düşürür. Bookmaker'lar pre-game line'ı çekiyor. Bu Odds API'nin tasarımı — bot bug'ı değil. Mevcut `-8h` penceresi live Q1-Q3 için yeterli; maç sonrası Polymarket marketi zaten near-resolve (gap yoksa GAP_TOO_LOW, event_elapsed → elenir). v2'de live odds endpoint araştırılacak (paid feature olabilir).

---

## NBA Totals Question Parser — Suffix Strip

**Karar**: `extract_teams("Cavaliers vs Raptors: O/U 220.5")` → `("Cavaliers", "Raptors")`.

**Neden**: Totals Polymarket formatı `"Team A vs. Team B: O/U XXX.X"`. `extract_teams()` `" vs "` ayracında bölerken team_b = `"Raptors: O/U 220.5"` alıyordu. `normalize()` tokenize ettiğinde `"raptors:"` (sondaki `:` dahil) `"raptors"` ile token overlap sağlamıyordu → `match_team()` → `no_match` → EVENT_NO_MATCH.

**Fix (2026-04-26)**: `question_parser.py` vs-split bloğuna `if ":" in b: b = b.split(":", 1)[0].strip()` eklendi. `a` için `rsplit(":", 1)[-1]` (son parça — turnuva prefix), `b` için `split(":", 1)[0]` (ilk parça — team_b suffix temizle).

---

## NBA Spread Question Parsing

**Karar**: `extract_teams("Spread: Knicks (-2.5)")` → `("Knicks", None)`.

**Neden**: Polymarket spread formatı `"Spread: TeamName (line)"` — tek takım, ikincisi yok.
`_PREFIXES`'e `"Spread:"` eklendi; yeni pattern 6 parantez öncesi metni yakaladı.
Tek takım → `find_best_single_team_match()` kullanılır, karşı takım event'ten alınır.
`parse_spread_line("Spread: Knicks (-2.5)")` zaten `2.5` döndürüyordu (`_SPREAD_RE` parantez içini yakalar).

---

## Circuit Breaker is_active Semantiği

**Karar**: `CircuitBreaker.is_active` property → `now < breaker_active_until`.

**Neden**: `startup.py` önceden `breaker.state.breaker_active_until is not None` kullanıyordu.
Bu field'ın set edilip edilmediğini kontrol eder, expire edilip edilmediğini değil.
`breaker_active_until=2026-04-22` (geçmiş) → non-None → `True` loglanıyordu.
`is_active` property yan etki olmadan doğru boolean döndürür.

---

## NBA Team ID Resolution

**Yaklaşım**: `team_resolver.py` (Domain katmanı) içinde statik `_NBA_NAME_TO_ESPN_ID` dict.
Gate, `extract_teams(market.question)` → `resolve_nba_espn_id()` → ESPN numeric ID zincirini kullanır.
Direction mapping: "Will X beat Y?" + BUY_YES → X = our_team_id.
Graceful fallback: bilinmeyen takım veya parse hatası → boş string → EdgeEnricher B2B kontrolünü atlar.
Short canonical form'lar (Trail Blazers, Timberwolves, Cavaliers, Mavericks, Wizards, Pistons) dahil edildi —
`canonicalize()` bu takımlar için şehir adını genişletmez.

---

## Entry Gate Safety Wiring (2026-04-26)

**Bulgu**: `EntryGate.__init__` 4 güvenlik bağımlılığını parametre olarak alıyor ama `self.`'ye atamayıp sessizce çöpe atıyordu. PRD §90, §270 ve aşağıdaki "Daily soft block" satırı bunların aktif çalışmasını gerektiriyor — kod'da yarı bağlıydı, hiç çalışmıyordu.

**Bağlanan kontroller** (gate.run() akışında sırayla):

| # | Konum | Skip reason | Davranış |
|---|---|---|---|
| 1 | run() başı (global) | `CIRCUIT_BREAKER_ACTIVE` | `should_halt_entries(portfolio_value)` True → tüm market'ler skip. Daily/hourly loss limitleri + soft block (-3%) + ardışık kayıp + cooldown burada toplanır. |
| 2 | run() başı (global) | `COOLDOWN_ACTIVE` | `cooldown.is_active()` True → tüm market'ler skip (ardışık kayıp cycle-bazlı cooldown). |
| 3 | per-market (INACTIVE_SPORT'tan sonra) | `BLACKLISTED` | `Blacklist.is_blacklisted(condition_id, event_id)` True → market skip. |
| 4 | per-market (blacklist'ten sonra) | `MANIPULATION_HIGH` | `manipulation_check(question, liquidity)` risk_level=="high" → market skip. SELF_RESOLVING + LOW_LIQUIDITY (<$10K) burada filtrelenir. |
| 5 | stake compute'tan sonra | (stake adjust) | Manipulation risk_level=="medium" → `adjust_position_size` ile stake × 0.5. Halved stake `min_bet_usd`'in altına düşerse `BELOW_MIN_BET` ile zaten skip olur. |

**Neden**: Sessiz güvenlik gap'i — system risk guard'larını record ediyor ama enforce etmiyordu. Circuit breaker exit'leri kaydediyordu, blacklist persist/restore ediliyordu, manipulation check factory'de oluşturuluyordu — ama hiçbiri entry'leri bloklayamıyordu. Bağlama TDD ile yapıldı (8 yeni test, 1131 → 1139, 0 regresyon).

---

## Pre-Match Guard NHL Score-Based Exit Kapsama (2026-04-28)

**Bulgu**: Sabres -1.5 spread (event 410180), bot 6 kez aynı pozisyonu açıp anında `nhl_puck_line_predictive_dead` ile kapattı (entry=exit=39¢, pnl=0, ~3 dk arayla). Tüm exit'lerde `period_at_exit="Scheduled"`, `elapsed_pct_at_exit≈-1.58` — yani maç başlamadan ESPN pre-match data döndürmüş, bot da phantom çıkış yapmış.

**Mekanizma**: `decide_nhl_puck_line_exit` PREDICTIVE_DEAD koşulu `p_cover < bid + 0.03`. Pre-match'te:
- bid ≈ 0.39 (Polymarket spread fiyatı)
- score_info.available=True (period=1, 0-0, full clock — ESPN'in pre-match snapshot'ı)
- Skellam fallback p_cover ≈ 0.13 (full-game cover olasılığı düşük)
- 0.13 < 0.39 + 0.03 = 0.42 → SELL_ALL anında

PREDICTIVE_DEAD'in tasarım amacı *"skor değişti, bid hâlâ aşağı düşmedi → çık"*. Pre-match'te bid efficient market estimate'ine yakın olduğundan kural **doğru ama zamansız** ateşliyor — phantom değil, kalibrasyon kapsamı sorunu.

**Bağlanan guard**: `b990ff0` commit'i pre-match guard'ı sadece `near_resolve` + `scale_out`'a uygulamıştı. NHL score-based dispatch ([monitor.py](src/strategy/exit/monitor.py)) bu kontrolü içermiyordu. Düzeltme: `_is_hockey_family(...) and score_info.get("available") and not match_pre_start` — pre-match'te tüm NHL exit'leri (ml/spread/totals) atlanır.

**Test**: 3 yeni vaka (puck line + ML + totals × pre-match) `test_monitor_nhl_routing.py`. Suite 1269/1269.

**Cleanup**: 6 phantom kaydı `trade_history.jsonl` + `exits.jsonl`'den çıkarıldı (`.bak.phantom-fix-2`). PnL=0 olduğu için equity_history etkilenmedi, circuit_breaker temiz.

**İkinci tur (ESPN-delay phantom)**: `match_pre_start = elapsed_pct < 0` guard'ı yetmiyordu — ESPN bazen `match_start_iso` zamanı GEÇTİĞİ halde hâlâ pre-match snapshot döndürüyor (puck drop gecikmesi / API delay). Bu durumda `elapsed_pct ≈ 0+` (pozitif) → guard atlatamıyor.

Asıl bug: 3 NHL dispatch'inde `period = score_info.get("period") or score_info.get("period_number")`. ESPN pre-match'te `period` field'ı string ("Scheduled") truthy → `period_number=None` (int) yerine string period'a düşüyor. Sonra `seconds_remaining=0` ile Skellam → `0.0` < bid+0.03 → PREDICTIVE_DEAD anında.

**Düzeltme**: `_nhl_exit_dispatch.py`, `_nhl_puck_line_dispatch.py`, `_nhl_totals_dispatch.py` — period extraction `period_number` int öncelikli, `isinstance(period, int) and period > 0` validation. ESPN string description ("Scheduled", "1st Period") int değilse → return None → exit fire etmez. `period_number` field'ı ESPN client `raw_period > 0` ise int set ediyor; pre-match/invalid'da None.

3 yeni regresyon testi (ESPN-delay × ml/spread/totals) prod verisini birebir taklit ediyor. Suite 1269 → 1272 (3 yeni). Toplam 8 phantom kaydı temizlendi.

**Üçüncü tur (Skellam-fallback kalibrasyon)**: Maç gerçekten başlayıp `period_number=1` (int) gelince guard'lar artık koruyor değildi — yine 3 phantom (28 Apr 23:39/23:42/23:46, period="In Progress", elapsed≈0.07). Empirical puck line tablosu (`data/nhl_empirical_puck_line_table.json`, 142KB) value'ları **null** içeriyor (sample size eksik); ML için empirical wp_table dosyası **yok**. Sonuç: tüm dispatch çağrıları `skellam_fallback`'e düşüyor; Skellam NHL -1.5 cover'ını under-estimate ediyor (low-scoring + OT/SO modifier yok) → erken-game'de p_cover bid'in hemen altına düşüyor → PREDICTIVE_DEAD false fire.

**Düzeltme**: 3 NHL exit fonksiyonu (`nhl_puck_line_exit.py`, `nhl_score_exit.py`, `nhl_totals_exit.py`) PREDICTIVE_DEAD bloğuna `source == "empirical"` koşulu eklendi. Empirical kalibrasyon olmayan vakada PREDICTIVE_DEAD kapalı; NEAR_RESOLVE (94¢) + SCALE_OUT (85¢) bid-tabanlı kâr lock'u + STRUCTURAL_DAMAGE (current/entry < 0.30) + dolar SL korumayı sağlar. Empirical tablo dolduğunda kural otomatik geri açılır.

3 yeni regresyon testi (`test_predictive_dead_skipped_when_source_not_empirical` × ml/spread/totals). Mevcut 2 dispatch testi empirical mock table ile güncellendi. Suite 1272 → 1275 (3 yeni). Toplam 11 phantom kaydı temizlendi.

**Dördüncü tur (clock semantik mismatch)**: Empirical tablo aslında **dolu** (4198 maç verisi: puck line %84 non-null, totals %73 non-null). Sorun build script ve dispatch arasındaki saniye semantik uyumsuzluğu — tablo regulation-total bazlı kalibre (P1 başlangıcı = 3600s), ESPN displayClock periyot bazlı (P1'de 0–1200s). Dispatch ESPN değerini doğrudan tabloya gönderiyordu → her çağrı MISS → Skellam fallback → PREDICTIVE_DEAD false fire (üçüncü tur guard'ı önledi ama 4198 maçlık veri israf).

**Düzeltme**: `src/domain/sports/nhl_match_clock.py`'ye public helper eklendi: `period_clock_to_regulation_seconds(period, period_clock_seconds)` — `(3 - period) * 1200 + period_clock`, period<=0 veya >3 için 0. `_nhl_puck_line_dispatch.py` ve `_nhl_totals_dispatch.py` ESPN clock'unu bu helper ile regulation-total bazlı dönüştürüp tabloya / Skellam'a gönderiyor. P3'te dönüşüm transparent (period_clock ≡ regulation), bu yüzden mevcut testler etkilenmedi.

7 yeni helper testi (`TestPeriodClockToRegulationSeconds`) + 1 dispatch P1 empirical-hit testi (`test_period_1_clock_converted_to_regulation_for_table_lookup`). Suite 1275 → 1432 (8 yeni; geri kalan delta domain testlerinin unit'ten ayrı koşmasından).

**Not**: Empirical artık aktif. PREDICTIVE_DEAD bundan sonra empirical kalibrasyon altında çalışacak. P1 0-0 başlangıçta empirical p_cover ≈ 0.10-0.15 — bid 0.39+0.03=0.42 üstündeyse fire eder. Erken-game'de market kalibrasyonunun empirical ortalama'dan farklı olduğu durumda meşru "early exit" üretebilir; bu phantom değildir, kalibrasyon kararıdır. Gerçek market'in 4198 maçlık ortalamadan ayrıştığı durumlarda PREDICTIVE_DEAD'in `predictive_safety_margin` veya minimum elapsed guard'ı yeniden değerlendirilebilir.

**Beşinci tur (P3-only PREDICTIVE_DEAD — NBA Q4-only paraleli)**: Empirical aktifleşince P1 0-0 başlangıçta tarihsel cover oranı düşük olduğu için PREDICTIVE_DEAD meşru ama zamansız tetiklenir. Erken oyunda skor henüz "geri dönülemez" değil; market'in maça özel bilgisi (line value, puck drop dinamiği) tarihsel ortalama'dan ayrışabilir. Bu noktada NBA pattern'i izlendi: NBA score/spread/totals exit'leri **Q4 only** kalibre (q4_late, q4_final, q4_endgame); Q1-Q3'te score-based exit yok. NHL'de paraleli **P3+ only**.

**Düzeltme**: 3 NHL exit fonksiyonunun (`nhl_puck_line_exit.py`, `nhl_score_exit.py`, `nhl_totals_exit.py`) PREDICTIVE_DEAD bloğuna `period >= 3` koşulu eklendi. P1/P2'de PREDICTIVE_DEAD pasif (skor değişebilir, ölü pozisyon yok); P3 ve sonrasında empirical kalibrasyon altında aktif. NEAR_RESOLVE/SCALE_OUT/SHOOTOUT_PROFIT/STRUCTURAL_DAMAGE + dolar SL erken oyunda da çalışır.

7 yeni regresyon testi (P1/P2 skip × 3 dosya) + 1 dispatch testi (P1 empirical hit guard altında skip). Suite 1432 → 1438.

**Sonuç**: NBA'nın yıllarca olgunlaşmış "Q4 only" mantığı NHL'e taşındı. Predictive exit artık iki katmanlı korumayla çalışır: (1) periyot ≥ 3 (geri dönülemez aşama), (2) source == empirical (kalibrasyonlu tahmin). Pre-P3 phantom riski tamamen kapalı.

**Altıncı tur (period boundary key mismatch — 2026-04-30)**: Beşinci turdan sonra P3+ + source==empirical guard'ları aktif olmasına rağmen iki gerçek trade'de PREDICTIVE_DEAD sessiz kaldı: bos-buf NHL spread (28 Apr, end-of-P2 1-1, stop_loss -$23.53 / -%58) ve mon-tb NHL spread (29 Apr, end-of-P2 2-2, stop_loss -$12.34 / -%33). bot.log'da `p_cover=0.000 (skellam_fallback)` görüldü — ama tablo gerçekte dolu (4198 maç, P3 tied 1200s buckets `n_games≈890, p_cover≈0.17`).

**Mekanizma**: Lookup key `f"{period}_{margin}_{time_bucket}"`. Dispatch `period_clock_to_regulation_seconds` ile sec_remaining'i regulation-total'a çeviriyor ama **period parametresini dönüştürmüyor** — caller'ın gönderdiği raw ESPN period (`2`) ile beraber sec=1200 gönderince key `"2_0_1200"` oluyor. Tablo build script'i bu boundary'i P3 namespace'ine yazmış (`"3_0_1200"` exists, `"2_0_1200"` doesn't). MISS → Skellam fallback → `source != "empirical"` guard PREDICTIVE_DEAD'i bloke ediyor → exit fire etmedi → stop_loss tetiklendi.

Aynı bug nhl_totals_probability'de de mevcut (her iki dosyada da düz `period_{margin}_{bucket}` lookup).

**Düzeltme**: `nhl_puck_line_probability.py` ve `nhl_totals_probability.py`'de `_period_from_seconds(time_bucket)` helper'ı eklendi — period parametresi yerine **time_bucket'tan türetilen period** lookup'a gönderiliyor:
- `time_bucket > 2400` → P1
- `1200 < time_bucket ≤ 2400` → P2
- `time_bucket ≤ 1200` → P3

OT (period >= 4) için: empirical tablo regulation kapsıyor, normalize öncesi short-circuit ile direkt Skellam'a düşülüyor — aksi halde sec_remaining=0 → "3_X_0" yanlış hit.

5 yeni regresyon testi (3 puck line + 2 totals): `test_period_boundary_p2_end_normalizes_to_p3`, `test_period_boundary_p1_end_normalizes_to_p2`, `test_period_boundary_caller_period_inconsistent_uses_seconds`, totals'da `test_period_boundary_p2_end_normalizes_to_p3` + `test_period_boundary_ot_skips_empirical`. Suite 298/298 green.

**Karşıt kanıt — sistem sağlığı doğrulandı**: Aynı maçın (mon-tb 29 Apr) ML pozisyonu `nhl_score_exit.py` üzerinden çalıştı. ML lookup `nhl_empirical_wp` modülünde delegasyon yaparak boundary sorununu yaşamadı → `source="empirical"` döndü → PREDICTIVE_DEAD doğru fire etti (entry 0.46 → exit 0.74, **+$23.01**). Bug puck_line + totals'a özgü key formatında.

**Sonuç (altıncı tur sonrası state)**: Predictive exit üç katmanlı: (1) periyot ≥ 3, (2) source == empirical, (3) period boundary lookup-aware (P2 sonu = P3 başı namespace'i). Empirical tablonun 4198 maçlık verisi artık tam tüketiliyor — özellikle `end-of-P2 tied` senaryolarında PREDICTIVE_DEAD ~$11–17/trade kayıp önler.

---

## Instant-Exit Phantom Defense Layers (2026-04-30)

**Bulgu**: NBA orl-det Spread Pistons(-13.5) (event 408550), bot 0.805 saniye içinde aynı pozisyonu açıp `predictive_dead` ile kapattı (entry=exit=33¢, P&L=$0). Audit: `score_at_exit="2-2"`, `period_at_exit="In Progress"`, `elapsed_pct=0.943` — Q4 elapsed %94'te skor "2-2" NBA'de imkansız (gerçek ~100+). bot.log: `PREDICTIVE_DEAD margin=13.5 clock=442s bid=0.330`. Aynı oscillating skor paterni phi-bos ve atl-nyk score_events'lerinde de kanıtlı (2-1, 3-0, 0-1, 1-0...).

**Kök Neden Hipotezi (henüz canlı raw API loguyla kesinleşmedi)**: ESPN client (`src/infrastructure/apis/espn_client.py::_parse_competition`) NBA için `linescores` toplamı + `competitor.score` fallback uygular. Live NBA maçında ya linescores boş dönüyor (fallback bozuk competitor.score'a düşülüyor) ya da match name fuzzy-match yanlış maça denk geliyor (Game 4 vs Game 5 aynı slug). Root cause sonraki canlı NBA cycle'da raw response logging ile çözülecek.

**Acil çözüm — iki defense layer**:

**Layer 1: Entry-cycle cooldown (PLAN-025 Part B)**. `Position.seconds_since_entry(now=None)` helper + `ExitMonitorConfig.entry_cooldown_sec: int = 60` config + `ExitProcessor.run_light` başında gate: `if pos.seconds_since_entry() < cooldown_sec: continue`. Yeni açılan pozisyona 60 sn (≈ 1 cycle + güvenlik buffer) exit dispatch çağrılmaz. Bug score adapter'da olsa bile entry sonrası anında kapatma imkansız hale gelir.

**Layer 2: NBA live skor sanity guard (PLAN-025 Part A)**. `score_helpers.is_score_sane(sport_tag, ms, min_total)` saf helper + `ScoreConfig.nba_live_min_total: int = 20` config + `ScoreEnricher._match_cached` ESPN/Odds dual-path uygulama: `home_score+away_score < 20` ve `is_completed=False` → skor reject + WARNING log + `result[cid]` setlenmez (exit dispatch o cycle skip). Final maç skorları (`is_completed=True`) ve non-NBA spor her zaman geçer. `min_total=0` → guard kapalı (development escape hatch). Floor 20 muhafazakar — Q1'in ilk 5 dk total ≥ 25 normal NBA'de, false positive minimal.

**Test**: 3 yeni `Position.seconds_since_entry` testi + 7 yeni `TestIsScoreSane` testi (NBA reject, non-NBA passthrough, completed pass, missing→False, disabled flag). Suite 1383 → 1390 (10 yeni).

**Cleanup**: 1 phantom kayıt (`nba-orl-det-2026-04-29-spread-home-13pt5` 2026-04-30T01:21:26 entry, P&L=$0) `trade_history.jsonl`'den kaldırıldı (CLAUDE.md TRADE SİLME PROTOKOLÜ uygulandı: realized invariant korundu, equity_history dokunulmadı çünkü P&L=0, exits.jsonl audit kaydı aynen kaldı). Backup: `trade_history.jsonl.bak.phantom-cleanup-orldet`.

**Sonuç**: Bu iki defense layer **kök nedeni çözmüyor** — sadece symptom'u nötralize ediyor. Live mode'a geçmeden önce raw NBA API response logging eklenip root cause kesinleştirilecek. Şu an dry_run'da P&L kaybı yok; live'da CLOB fee + spread kaybı (~$0.50-1.50/instant phantom) iki layer ile imkansız hale geldi.

**Bonus arch_guard fix (aynı oturum)**: 3 NHL exit dosyasında (`nhl_puck_line_exit.py`, `nhl_score_exit.py`, `nhl_totals_exit.py`) `except Exception: p_X = None; p_X_source = "error"` paternine `logger.warning(exc_info=True)` eklendi. CLAUDE.md "Sessiz hata yutma yasak" kuralı: hata davranışı (predictive skip) korunur, exception bilgisi artık görünür.

**PLAN-025 Güncelleme (2026-04-29)**: utah-las phantom 61 saniyede gerçekleşti — 60sn cooldown yetersiz. `entry_cooldown_sec` 60 → 120 artırıldı. Config: `config.yaml` + `settings.py`.

**PLAN-026: Late-entry guard (2026-04-29)**: Utah-LAS ikinci phantom pattern: bot maç %98.3 tamamlanmışken pre-game bookmaker odds'uyla entry yaptı (stale anchor). `_match_status.elapsed_fraction_estimate()` + `is_too_late_to_enter()` helper'ları eklendi. `GateConfig.max_live_elapsed_pct=0.85` — maçın %85'i wall-clock zamanına göre geçmişse `MATCH_TOO_FAR_ELAPSED` ile entry bloklama. Guard `max_elapsed_pct=0.0` ile kapatılabilir. Test: 11 yeni test (elapsed_fraction + is_too_late 2 sınıf). Suite 1390 → 1401.

---

## ENTRY

### Confidence Grading
| Grade | Koşul | Rationale |
|---|---|---|
| A | `has_sharp=True` AND `bm_weight ≥ 5` | Sharp book (Pinnacle/Betfair/Matchbook/Smarkets) consensus = en güvenilir sinyal |
| B | `bm_weight ≥ 5`, sharp yok | Yeterli volume ama sharp konfirmasyonu yok |
| C | `bm_weight < 5` | Yetersiz veri — entry blocked |

### Position Sizing
- A = bankroll × 5%, B = bankroll × 4%, C = 0 (blocked)
- `max_bet_pct` = 5% (single cap)
- `max_single_bet_usdc` = $75
- Polymarket minimum = $5 — altındaysa reject
- `stake = bankroll × bet_pct × win_prob` (probability-weighted, SPEC-016)
- **Neden win_prob çarpanı:** Portfolio avg stake ~%30 düşer → daha fazla eş zamanlı pozisyon → diversification

### Favorite Filter
- `min_favorite_probability` = 0.60 (2-way)
- `min_favorite_probability` = 0.40 (3-way, absolute) + margin ≥ 0.07 (relative)
- **Neden 0.60:** Toss-up maçlarda edge tespiti güvenilmez, variance çok yüksek
- **Neden 0.40 3-way:** 3 outcome dağılımında 0.40 = 2-way 0.55 eşdeğeri

### Entry Price
- `max_entry_price` = 0.80 (üst cap)
- Alt floor yok — bookmaker 60%+ favorisi ama Polymarket 30¢ = undervalue = positive edge
- `entry_price_cap_reject` = 0.88 — üstünde R/R kırık (max $2.75 kazanç vs $7.50 SL riski)

### Exposure Cap
- Soft cap = 50%, hard cap = 52%
- Denominator = total portfolio value (cash + invested) — sadece cash kullanılırsa cap erken tetiklenir
- `min_entry_size_pct` = 1.5% — micro-pozisyon fee'den kârsız

### Bookmaker Tier Weights
| Tier | Weight | Bookmakers |
|---|---|---|
| Sharp | 3.0× | Pinnacle, Betfair Exchange, Matchbook, Smarkets |
| Reputable | 1.5× | Bet365, William Hill, Unibet, Betclic, Marathon |
| Standard | 1.0× | Diğerleri |

Exchange'ler (Betfair, Matchbook, Smarkets): vig-free → normalize edilmez.

---

## EXIT

### Event Guard Kuralları

| Durum | Sonuç | Neden |
|---|---|---|
| Aynı event + aynı market_type | BLOCK (EVENT_GUARD_SAME_MARKET_TYPE) | Aynı sonucu iki kez bahsemek |
| Aynı event + ML + Spread + aynı yön | BLOCK (EVENT_GUARD_ML_SPREAD_CORRELATED) | Yüksek korelasyon |
| Aynı event + ML + Totals | ALLOW | Bağımsız sonuçlar (kazanan ≠ toplam skor) |
| Aynı event + Spread + Totals | ALLOW | Bağımsız sonuçlar |
| Aynı event + 2 açık pozisyon | BLOCK (EVENT_GUARD_MAX_POSITIONS) | Hard cap |

### Scale-Out (SPEC-013)
- Threshold = 0.50 (entry→0.99 mesafesinin %50'si)
- Sell pct = %40
- **Neden mesafe bazlı, PnL% değil:** Farklı entry fiyatlarında adil davranır (0.30 entry vs 0.70 entry)
- Near-resolve (0.94) her zaman scale-out threshold'unun üstünde olmalı — aksi halde price spike'ta bypass riski

### Near-Resolve Profit Exit
- Trigger = `bid_price ≥ 0.94`
- Pre-match reject, `mins_since_start < 10` reject (açılış spike koruması)
- **Neden bid, ask değil:** ask manipüle edilebilir, bid gerçekleşebilir fiyat (PLAN-023)
- Data: 27 exit = +$140.31, %93 WR — en büyük kâr kaynağı

### Market Flip Exit
- `elapsed_pct ≥ 0.85` AND `bid_price < 0.50`
- Tennis'te DEVRE DIŞI — set yapısı 40-50% swing yaratır, false positive çok fazla

### Never-in-Profit Guard
- `elapsed_pct ≥ 0.70` AND `peak_pnl_pct ≤ 0.01` AND `bid_price < entry × 0.75`
- 0.75–0.90 aralığında: exit yok — Flat SL A3'te kaldırıldı, bu aralık dollar-based SL'ye düşer

### Ultra-Low Guard
- `effective_entry < 0.09` AND `elapsed_pct ≥ 0.75` AND `bid_price < 0.05`
- Çok düşük olasılıklı pozisyon zaten iyice battıysa temizle

### Dollar-Based Stop Loss (PLAN-023)
4 şartın tümü: `elapsed_pct ≥ 0.75` AND `loss_usd > max_loss_usd` AND pozisyon lider değil
- 2-way: `bid_price < 0.50`
- 3-way: `bid_price < event_sibling_bids max`
- **Neden 4 şart:** Geçici dalgalanmalarda erken çıkışı önler

### FAV Promotion
- Promote: `effective_price ≥ 0.65` AND confidence ∈ {A, B}
- Demote: `effective_price < 0.65`
- Data: 5 favored trade = +$42.90, %100 WR

---

## NBA MONEYLINE

### Bill James Safe Lead

- **Formül:** `deficit >= 0.861 × √(clock_seconds)` → geri dönüş matematiksel imkânsız
- **Multiplier 0.861:** NBA 14-yıl verisiyle %99 güven aralığı (orijinal formül college için 0.4538 × √t)
- **Kaynak:** Basketball Reference season data 2010-2024

### Empirical Q4 Eşikleri (14-yıl NBA)

| Durum | Kalan süre | Fark | Geri dönüş ihtimali |
|---|---|---|---|
| Blowout | ≤12 dk (720s) | ≥20 | ~%1 |
| Late | ≤6 dk (360s) | ≥15 | ~%2 |
| Final | ≤3 dk (180s) | ≥10 | ~%3 |
| Endgame | ≤1 dk (60s) | ≥6 | ~%2 |

Bill James önce kontrol edilir; pas geçerse empirical devreye girer.

### Q1-Q3 HOLD

- **Neden hold:** Q1-Q3'te 10 puanlık fark ile geri dönüş ihtimali %5-13. Erken exit edge yiyor.
- **Kural:** period < 4 AND not OT → return None.

### Overtime

- **OT < 60s + fark ≥ 8 → EXIT.** OT'da küçük farklar kapanabilir; 60s'de 8 puan imkânsız.

### Near-Resolve + Scale-Out

- Near-resolve (94¢) ve scale-out (85¢) monitor.py priority 1-2'de, sport-agnostic.
  nba_score_exit.py'de duplicate yok.

### Structural Damage

- Son çare: `bid/entry < 0.30 AND math_dead` — çift kilitlendi, spread'e kaptırmadan çık.
- price_cap SL (PLAN-014) ile örtüşebilir; NBA exit daha önce (monitor priority 3) tetikler.

### Entry — Gap Thresholds

| Eşik | Değer | Rationale |
|---|---|---|
| min_gap | 0.08 | Ana edge zone; altında noise > signal |
| high_zone | 0.15 | Belirgin misprice; stake ×1.2 |
| extreme_zone | 0.25 | Güçlü misprice; stake ×1.3 |
| max_entry_price | 0.80 | R/R kırık (zaten EntryConfig'den) |
| min_polymarket | 0.15 | Uç outlier reddi; spike koruması |

### Entry — Sizing

- `stake = bankroll × confidence_pct × gap_mult × win_prob`
- A = 5%, B = 3% (B eski değer 4%'ten düşürüldü — gap filtresi zaten kaliteyi kısıtlıyor)
- Hard cap: `bankroll × 5%` veya `max_single_bet_usdc` ($75) hangisi küçükse

---

## NBA Spread

**Entry:**
- Gap threshold moneyline ile aynı (0.08). Spread ≥ 10 → +0.02 bonus (garbage time blowout riski).
- Fiyat aralığı 0.20-0.80 (moneyline'dan dar: uç noktalar daha volatil).
- Polymarket format: "Spread: TEAM_NAME (-X.5)" — SMT='spreads'.

**Exit — Math:**
- Bill James multiplier 0.861 (moneyline ile aynı — spread Poisson dağılımı identik).
- margin_to_cover = spread_line - (our_score - opp_score) [BUY_YES / favorite].
- margin_to_cover = -(our_score - opp_score) - spread_line [BUY_NO / underdog].
- Q1-Q3 her zaman HOLD (spread variance Q4'te kristalleşir).

**Exit — Empirical key numbers:**
- 360s kala, margin ≥ 7: 1 possession farkı kritik threshold.
- 180s kala, margin ≥ 4: ~2 dakika, 4 puan geri dönüş zorlaşır.
- 60s kala, margin ≥ 3: "key number 3" — NBA spread'de kritik.
- Kaynak: 14 yıl NBA spread kapama verisi.

---

## NBA Totals

**Entry:**
- Min target total: 200 (likidite + edge optimum zone — düşük totals thin market).
- Fiyat aralığı 0.20-0.80.
- Polymarket format: "TEAM vs TEAM: O/U X.5" — SMT='totals'. YES=over konvansiyonu.

**Exit — Math:**
- Multiplier 1.218 = 0.861 × √2 (toplam variance = iki takım toplamı → √2 factor).
- Over: is_total_dead(target, current, clock, "over") → points_needed > 1.218*sqrt(clock).
- Under: is_total_dead(target, current, clock, "under") → excess > 1.218*sqrt(clock).

**Exit — OT:**
- Over + OT → OT_OVER_WINDFALL: %75 sat (her OT ~25 puan ekler, kâr kilitle).
- Under + OT → OT_UNDER_DEAD: tam çıkış (total kesinlikle artar, under kaybetti).

**Exit — Empirical:**
- Over: 360s kala points_needed ≥ 20 / 180s kala ≥ 12 / 60s kala ≥ 6.
- Under: 360s kala excess ≥ 20 / 60s kala excess ≥ 6.

---

## NBA Predictive Exit (EV Bazlı)

### Matematik Temeli

Kalan sürede **skor farkının** standart sapması σ/√s modeliyle tahmin edilir:

| Market tipi | σ/√s sabiti | Kaynak |
|---|---|---|
| Moneyline / Spread | 0.3727 | Skor farkı volatilitesi, 14-yıl NBA |
| Totals | 0.5270 | Toplam puan volatilitesi (= 0.3727 × √2) |

Geri dönüş olasılığı (comeback rate): P = ½ × (1 − erf(z/√2)) şeklinde standart normal CDF kuyruğu. z = deficit / (σ × √seconds).

### Karar Mantığı

```
comeback = estimate_comeback_rate_ml(deficit, seconds)

if comeback >= 0.20:          → HOLD (istatistiksel olarak hâlâ geri dönülebilir)
elif (bid + 0.03) > comeback: → EXIT (EV_sell > EV_hold + güvenlik payı)
else:                         → HOLD
```

- **Hold threshold 0.20:** %20'nin üzerindeki comeback ihtimallerinde pozisyonu tutmak EV pozitif. Altında piyasa fiyatı + 0.03 güvenlik payı ile EV karşılaştırması yapılır.
- **Safety margin 0.03:** Slippage + bid-ask spread toleransı. Çok küçük seçilirse sinyal gürültü içinde kaybolur; çok büyük seçilirse gerçek sinyaller engellenir.
- **Config:** `exit_basketball.predictive_exit.{enabled, hold_threshold, safety_margin}`

### Totals Under Semantiği

`points_until_decision = target_total − current_total` (her zaman, under için de).

| Durum | points_until_decision | comeback_under | Karar |
|---|---|---|---|
| current < target | > 0 | 0.5×(1+erf(z/√2)) → yüksek | HOLD (güvendeyiz) |
| current = target | 0 | 0.0 | EXIT (herhangi bir puan kaybettirir) |
| current > target | < 0 | 0.0 (özel durum) | EXIT (zaten kaybettik) |

### Öncelik Sırası

```
1. Near-resolve (94¢)        — monitor.py priority 1
2. Scale-out (85¢)           — monitor.py priority 2
3. Structural damage         — price_ratio < 0.30 AND math_dead
4. Bill James MATH_DEAD      — deficit ≥ 0.861 × √clock
5. PREDICTIVE_DEAD           ← YENİ: EV bazlı, math_dead tetiklemediyse
6. Empirical backup          — 14-yıl NBA verisi (hard thresholds)
7. SL / price_cap            — monitor.py alt öncelik
```

### v2 Yol Haritası

- ML modeli (XGBoost / logistic regression): Gerçek 14-yıl NBA pozisyon verisiyle eğitilmiş, deficite ek olarak possession count, foul trouble, momentum sinyalleri eklenebilir.
- Şimdiki normal dağılım modeli: Kaba ama tutarlı. Gerçek NBA comeback dağılımı sağa çarpık (blowout'lar asimetriktir) — bias v2'de düzeltilecek.

---

## NBA Edge Modifiers

### Injury Detection

**Window: 2 hours**
Polymarket price lags ESPN injury reports by ~15-60 minutes. A 2-hour lookback captures fresh information the market hasn't fully priced in yet. Older injuries (>2h) are assumed priced in.

**Gap threshold drop: -0.02 (opponent injury)**
When the opponent has a recent Out/Doubtful player, Polymarket prices adjust slowly. A -0.02 reduction allows borderline gaps (6-8%) to qualify when the bookmaker edge is genuine. Limited to 0.02 to avoid entering on pure speculation.

**Size multiplier: 1.3 (opponent injury)**
Opponent injury increases edge confidence. 1.3 is conservative — a 30% stake increase reflects marginal confidence improvement, not a major edge. Capped at max_single_bet_usdc after multiplication.

**Star out self gap bonus: +0.05 (own team injury)**
When the team we're backing loses a key player, the bookmaker gap may be an artifact (stale lines) rather than genuine edge. Raising threshold by 0.05 requires a stronger signal before entry.

### Back-to-Back (B2B) Detection

**Opponent B2B gap bonus: +0.03**
Fatigue effect is real but often priced in within hours of the schedule becoming public. Adding +0.03 to gap threshold compensates for manipulation risk: bookmakers and sharp bettors front-run B2B scenarios, so Polymarket lines may already reflect the edge. Entry only when gap is genuinely above the higher bar.

**Self B2B gap bonus: +0.05**
If we are backing a team that played yesterday, the bookmaker's probability may be overstating our team's advantage. The market may be right that the favorite is actually weaker today. Require a stronger edge before committing.

### Implementation Notes

- ESPN endpoint: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries` — 30 teams in a single call, 60s cache
- Schedule endpoint: per-team, 6h cache (schedules rarely change intraday)
- Team ID resolution: `extract_teams(market.question)` → `resolve_nba_espn_id()` → ESPN numeric ID. BUY_YES → team_a = our_team. Bilinmeyen takım veya parse hatası → "" → EdgeEnricher B2B skip, injury opponent olarak işler. Kaynaklar: `src/domain/matching/team_resolver.py`.
- Priority: Out+starter > Doubtful+starter > Out non-starter > Doubtful non-starter

---

## SPORT EXIT THRESHOLD'LARI

### Hockey (NHL/AHL/Liiga/SHL/Allsvenskan/Mestis)
| Kural | Koşul | Rationale |
|---|---|---|
| K1 | deficit ≥ 3 (herhangi period) | Blowout — comeback %2-3 |
| K2 | deficit ≥ 2 AND elapsed ≥ 0.67 | Geç dönem büyük fark |
| K3 | deficit ≥ 2 AND price < 0.35 | Skor + market konfirmasyonu |
| K4 | deficit ≥ 1 AND elapsed ≥ 0.92 | Final dakika |
Backtest: −$23.24 → +$3.70 (+$26.94 improvement)

### Tennis (ATP/WTA)
- T1: 0-1 set + current set deficit ≥ 3 + games_total ≥ 7 (veya deficit ≥ 4)
- T2: 1-1 set + 3. set deficit ≥ 3 + games_total ≥ 7 (veya deficit ≥ 4)
- SFM: opponent ≥ 5 game + biz gerideyiz → exit (maç puanında)
- Tiebreak buffer: 1. set dar kayıp (bizim ≥ 5 game) → threshold +1
- **Neden bu eşikler:** Comeback rate bu noktada %3-8

### Baseball (MLB/KBO/NPB/MiLB)
| Kural | Koşul |
|---|---|
| M1 | inning ≥ 7 AND deficit ≥ 5 |
| M2 | inning ≥ 8 AND deficit ≥ 3 |
| M3 | inning ≥ 9 AND deficit ≥ 1 |
Score source: ESPN `status.period` (int) — `status.type.description` unreliable (SPEC-014)

### NBA
- N1: elapsed ≥ 0.75 + deficit ≥ 18
- N2: elapsed ≥ 0.92 + deficit ≥ 8
- N3: period=4 AND clock ≤ 120s AND deficit ≥ 5
- **Neden 18:** 17pt comeback = %2-3 ihtimal

### NFL
- N1: elapsed ≥ 0.75 + deficit ≥ 17
- N2: elapsed ≥ 0.92 + deficit ≥ 9
- N3: period=4 AND clock ≤ 150s AND deficit ≥ 4
- **Neden 17:** 2.5-score gap, σ-model %99 confidence

### Soccer
- HOME/AWAY: 0-65' HOLD → 65'+ 2 gol fark EXIT → 75'+ 1 gol fark EXIT
- DRAW: 0-70' HOLD → 75'+ herhangi gol EXIT → knockout 90+ AUTO-EXIT
- **Neden 0-65' lock:** 0-1 HT'den geri dönüş ~%25-30, erken çıkış EV'yi bozar
- Kırmızı kart için ayrı exit yok — ESPN reliability düşük, market flip zaten yakalar

### Rugby
- Blowout: elapsed ≥ 0.50 (50') + deficit ≥ 14pt
- Late: elapsed ≥ 0.70 (70') + deficit ≥ 7pt

### AFL
- Blowout: elapsed ≥ 0.60 (60') + deficit ≥ 30pt
- Late: elapsed ≥ 0.75 (75') + deficit ≥ 15pt

### Handball
- Blowout: elapsed ≥ 0.45 (45') + deficit ≥ 8 gol
- Late: elapsed ≥ 0.55 (55') + deficit ≥ 4 gol

---

## CIRCUIT BREAKER

| Parametre | Değer | Cooldown |
|---|---|---|
| Daily max NET loss | -%8 | 120 dk |
| Hourly max NET loss | -%5 | 60 dk |
| Consecutive loss limit | 4 trade | 60 dk |
| Daily soft block | -%3 | Entry suspend (hard halt değil) |

- **Neden NET USD tracking:** Yüzde toplama farklı portfolio değerlerinde false trigger üretir
- Exit'leri durdurmaz — sadece entry halt

---

## SCORE POLLING

- Normal: 60s
- Price ≤ 0.35: 30s (adaptive)
- Primary: ESPN public API — free, key gerekmez
- Fallback: Odds API `/scores` — tennis score yok
- Kill switch: `score.enabled: false`

---

## MANIPULATION GUARD

- Self-resolving subjects (16): trump, biden, elon, musk, putin, zelensky, xi jinping, desantis, vance, newsom, harris, netanyahu, modi, zuckerberg, bezos, altman
- Risk ≥ 3 → SKIP, Risk = 2 → size ×0.5, Risk < 2 → OK
- Min liquidity: $10,000

---

## LIKIDITE CHECK

Entry: `total_ask_depth < $100` → reject; pozisyon > %20 depth → halve size
Exit: fill_ratio ≥ 1.0 → market order; ≥ 0.80 → limit; < 0.80 → split

---

## AKTIF SPORLAR

```
baseball    (MLB, MiLB, NPB, KBO, NCAA)
basketball  (NBA, WNBA, NCAAB, WNCAAB, Euroleague, NBL)
hockey      (NHL, AHL, Liiga, Mestis, SHL, Allsvenskan)
football    (NCAAF, CFL, UFL)    ← NFL şu an scanner'dan drop
tennis      (tüm ATP/WTA)
soccer      (60+ lig — 3-way)
rugby       (3-way)
afl         (3-way)
handball    (3-way)
```

Kapsam dışı (scope kararı, 2026-04-22):
- Cricket (tüm leaguelar) — CricAPI 100/day limit, test match draw modeli eksik
- MMA/UFC/Boxing — pipeline eksik (TODO-002)
- Golf — outright market pipeline eksik (TODO-003)
- NFL — scanner'da drop (TODO-001, whitelist'te değil)

---

## NHL Empirical Win Probability Table — MoneyPuck — 2026-04-27

### Karar
NBA paketindeki "14-yıl empirical thresholds"un NHL muadili. MoneyPuck.com'un
public play-by-play datasından kendi güncel empirical tablomuzu türettik.

### Kaynak veri
- 3 sezon: 2022-23, 2023-24, 2024-25
- 4198 maç, 364368 satır
- MoneyPuck.com, public CSV downloads
- License: free for non-commercial use, credit required

### Niye Pettigrew (2014) / Bernier (2018) kullanılmadı?
8-10 yaşında. NHL scoring environment ciddi değişti:
- 2024-25 ortalama 6.142 G/maç (MoneyPuck türevi)
- 2024-25 comeback rate %43 (tarihsel %2'lik)
- League SV% 0.915 → 0.904 (10 yılda)
- Empty net pull timing daha agresif
Bu değişimler eski thresholds'u yanıltırdı.

### Yöntem
1. Her maç için score timeline shots DataFrame'inden reconstructed
2. 30-saniye bucket'larında score differential kayıt
3. Final outcome (OT/SO dahil) per game
4. Empirical frequency by (period, abs_diff_clamped, time_bucket)
5. Wilson 95% CI
6. <30 games olan bucket'lar None döner (yetersiz sample → fallback Skellam)

### Output
- data/nhl_empirical_win_table.json (committed, 53KB)
- data/nhl_shots/*.csv (gitignored, ~198MB cache)

### Sanity (8 anchor noktası, 2026-04-27 build)
| State | p(leader wins) | n_games | CI |
|---|---|---|---|
| 3-gol P3 başı | 96.0% | 489 | [94.3, 97.7] |
| 2-gol P3 başı | 89.6% | 1013 | [87.7, 91.5] |
| 1-gol P3 başı | 74.0% | 1511 | [71.8, 76.2] |
| 1-gol P3 mid (600s) | 80.8% | 1394 | [78.8, 82.9] |
| 1-gol last 5min | 86.3% | 1373 | [84.5, 88.1] |
| 1-gol last 60s | 92.3% | 1254 | [90.8, 93.8] |
| 2-gol last 5min | 98.1% | 962 | [97.3, 99.0] |
| 2-gol last 60s | 99.2% | 789 | [98.7, 99.8] |

### Implementation bug log (referans)
İlk build iki bug ile çıktı:
1. `time` kümülatif game seconds, period-local DEĞİL — yanlış formül
   `(period-1)*1200 + time` çift ekleme yapıyordu
2. `game_id` sezonlar arası çakışıyor (2022 ve 2023'te 1391 ortak ID) —
   season prefix ile çözüldü

Fix sonrası 8/8 sanity anchor beklenen aralıkta.

### Bilinen kısıtlamalar
1. Symmetric (tied = 0.50, home edge yok v1)
2. No talent adjustment (bookmaker prior yok)
3. No goalie quality, no manpower (PP/PK), no travel
4. Empty net dynamics dolaylı içerilir (final outcome'da görülür)
5. Period 4+ (OT/SO) outcome'a bucketlanır, ayrı table değil

### Sonraki adımlar
- Task 1B: Skellam math + bu empirical tablo ile cross-validate ✓
- Task 1C: ESPN NHL probe + MatchClock + alias
- Task 1D: Polymarket NHL parser
- Task 2-5: Entry/Exit logic
- Faz 2: Talent-aware Bayesian extension

---

## NHL Skellam Math + Hybrid Wrapper — 2026-04-27

### Karar
Skellam-distribution-based theoretical win probability empirical lookup'a
FALLBACK olarak eklendi. Empirical bucket <30 sample ise Skellam kullanılır.

### Neden iki katman?
1. Empirical (MoneyPuck 2022-25, 4198 maç): yüksek kalite, sample sınırı var
2. Skellam: tüm state'lere yanıt veriyor, theoretical floor

### Lambda kalibrasyonu
lambda_5v5_per_sec = 0.000853 (6.142 G/mac MoneyPuck turev / 2 / 3600)
lambda_3v3_OT_per_sec = 0.001400 (~1.65x reg)

### Cross-validation
Skellam vs empirical 8 anchor noktasi:
- +/-10pp tolerance (P3 mid-late, P3 basi)
- +/-15pp tolerance (last 5min — EN etkisi baslar)
- +/-25pp tolerance (last 60s — EN heavy, Skellam underestimate beklenen)

Gercek diff'ler: max 5.28pp (3_1_60), diger 7 kase <4pp.

### Hybrid wrapper davranisi
src/domain/math/nhl_win_probability.py:
- (probability, source) tuple doner
- source in {"empirical", "skellam_fallback", "trivial"}
- Production exit logic bunu cagiracak (Task 3'te)

### Bilinen kisitlamalar
1. Symmetric lambda (talent yok, v2)
2. Constant lambda (score-state aware DEGIL)
3. Empty net dynamics SADECE empirical layer'da yakalanir
4. OT icin ayri 3v3 lambda kullanildi

### Sonraki adimlar
- Task 1D: Polymarket NHL parser
- Task 2-5: Entry/Exit logic

---

## NHL MatchClock + Team Aliases (Task 1C)

**Dosyalar:**
- `src/domain/sports/nhl_match_clock.py` — ESPN status → NHLClock dataclass
- `src/domain/sports/nhl_team_aliases.py` — 32 takim, alias normalizasyonu
- `scripts/probe_espn_nhl.py` — ESPN endpoint probe (read-only, tek seferlik)
- `data/probes/nhl/SUMMARY.md` — probe sonuclari (2026-04-27)

### ESPN status ayrıstirma mantigi

Probe'dan ogrenilenler (4 mac, 2026-04-27 playoffs):
- `status.period`: int — 1/2/3 regulation, 4=OT, 5=SO
- `status.displayClock`: str "MM:SS" countdown (final'de "0:00")
- `status.type.state`: "pre" | "in" | "post"
- `status.type.detail`: "Final", "Final/OT", "Final/SO", "OT", "Shootout", "1st Period", vb.

Period promotion: ESPN bazen `period=3` ile `detail="Final/OT"` gonderiyor.
`parse_nhl_status()` bunu yakaliyor, period'u 4'e yukar cekiyor.

`is_pre` default: `state not in ("in", "post")` — tanimsiz/bos state
guvenceli "pre" davranisi (ESPN hata halinde oyun henuz baslamamis gibi isleniyor).

`seconds_remaining_in_regulation` hesabi:
```
regulation_remaining = max(0, 3600 - ((period-1)*1200 + (1200 - clock_seconds)))
```
Period >= 4 (OT/SO/final) icin 0 doner.

### Takim alias tasarimi

Canonical key: ESPN abbreviation (probe'dan dogrulanmis: BOS, EDM, ANA, BUF).
Alt abbr gereksinimi: Odds API bazi takimlar icin farkli abbr kullaniyor:
- LAK → LA, NJD → NJ, SJS → SJ, TBL → TB

Eski isim: Utah Hockey Club → UTA (Mammoth oldu, sorularda her ikisi gorulebilir).

`resolve_nhl_team()` None-safe, whitespace-stripped, case-insensitive.

### Probe sonuclari ozeti

Scoreboard'da `probables` field her zaman dolu (goalie kimlik + istatistik).
Summary `boxscore.players[team].statistics[name="goalies"]` tam goalie stats.
Live `situation` field final'de bos, live'da dolu (live probe eksik — SO hic gorulmedi).
Linescore: summary `header.competitions.0.competitors.X.linescores` array, OT'de 4. eleman otomatik ekleniyor.

### Bilinen kisitlamalar
1. SO detail pattern ("Shootout", "Final/SO") live probe'da dogrulanamadi — teorik.
2. Live "P1, 10:35" detail format'i gorulmedi; period number fallback kullaniliyor.
3. Goalie confirmation logic (teyid, "probable" vs "actual starter") Task 2'de.

### Sonraki adimlar
- Task 2: NHL entry gate (goalie confirmation + Polymarket matching)
- Task 3: NHL exit (NHLClock + hybrid WP → K1-K4 kurallar)

---

## NHL Polymarket Question Parser (Task 1D) — 2026-04-27

**Dosya:** `src/domain/sports/nhl_question_parser.py`

### Karar
Polymarket NHL market question metninden iki takim abbreviation'ini cikaran
parser. Home/away siralamasini YAPMAZ — slug parser'in isi.

### Desteklenen pattern'lar (gercek Polymarket ornekleri)
- "Bruins vs. Sabres" / "Bruins vs Sabres"  (mascot, en yaygin)
- "NHL: Lightning vs. Canadiens"
- "NHL Playoffs: Oilers vs. Ducks"
- "Boston Bruins vs. Buffalo Sabres"
- "Will the Bruins win against the Sabres?"
- "Will the Oilers beat the Ducks?"

### Tasarim kararlari
1. Pattern oncelik sirasi onemli: spesifik (Will/NHL prefix) once, generic
   (X vs Y) sonra — "NHL: Bruins vs. Sabres" generic'e dusmesini engeller
2. Same-team kontrol: "Bruins vs. Bruins" None doner
3. Case-insensitive matching
4. Whitespace tolerant
5. Bilinmeyen takim her iki tarafta None
6. nhl_team_aliases.resolve_nhl_team ile decoupled (32 takim listesi
   orada, parser sadece extraction yapar)

### Niye home/away yok?
Polymarket question metni "X vs Y" formatinda ama hangi taraf home
GUVENILIR DEGIL. Slug formati (nhl-AWAY-HOME-DATE) explicit. Cross-source
discrepancy riskini azaltmak icin question parser sadece takim ciftini
dondurur, siralamay orchestration katmani (entry processor) slug'dan cozer.

### Bilinen kisitlamalar
1. Cok eski question formatlari (orn. "Game 7: ...") henuz gorulmedi,
   gerekirse pattern eklenir
2. All-Star, 4 Nations, Olympics gibi exhibition match'ler v1'de skip
   ediliyor zaten (entry gate)
3. Pre-season match'ler icin ayri sport_key, parser etkilenmez

### Sonraki adimlar
- Task 2: NHL Moneyline Entry Gate (parser'i kullanir)
- Task 3: NHL Moneyline Exit Logic (NHLClock kullanir)
- Task 4: NHL Moneyline Integration


---

## NHL MONEYLINE

### Exit Logic — Priority Chain

| Priority | Rule | Condition | Action |
|---|---|---|---|
| 1 | NEAR_RESOLVE | bid >= 0.94 | SELL_ALL |
| 2 | SCALE_OUT | bid >= 0.85 AND not yet scaled | SELL_50 |
| 3 | SHOOTOUT_PROFIT | is_shootout AND bid >= 0.52 | SELL_ALL |
| 4 | PREDICTIVE_DEAD | p_win < bid + 0.03 | SELL_ALL |
| 5 | STRUCTURAL_DAMAGE | price/entry < 0.30 | SELL_ALL |
| 6 | HOLD | default | HOLD |

### Threshold Rationale

- **near_resolve_threshold = 0.94**: Sport-agnostic — consistent with NBA/soccer pipeline
- **scale_out_threshold = 0.85**: Sport-agnostic — lock partial profit before near-resolve
- **shootout_profit_threshold = 0.52**: SO is a 50/50 coin flip; if market gives 52c+ sell — holding for 1-2c extra EV not worth variance
- **predictive_safety_margin = 0.03**: Slippage + bid-ask spread tolerance — consistent with NBA predictive exit
- **structural_damage_ratio = 0.30**: Price collapsed to 30% of entry -> catastrophic loss, salvage remaining value

### PREDICTIVE_DEAD Logic

`win_probability_fn(period, abs_score_diff, seconds_remaining) -> (float, str)` is injected by Task 3C wiring (hybrid empirical-first + Skellam fallback). Fire condition: `p_win < bid + 0.03`. Exception from fn: p_win=None, skip check, fall through to STRUCTURAL_DAMAGE / HOLD.

### Price Field Usage

NEAR_RESOLVE / SCALE_OUT / SHOOTOUT_PROFIT / PREDICTIVE_DEAD: use `current_bid` (executable sell price).
STRUCTURAL_DAMAGE: uses `current_price` (mid/last) — bid can be artificially low in thin books, causing false-positive structural exits.

### v1 Scope

Moneyline ONLY. No puck line (spread), no totals, no three-way ML.

---

## NHL Wire — Task 3B: is_overtime / is_shootout Flags

### Değişiklik özeti (2026-04-27)

`ESPNMatchScore.raw_status: dict` alanı eklendi. `_parse_competition()` içinde `sport == "hockey"` iken `status_block` tamamı bu alana yazılır; diğer sporlar için boş dict kalır.

`build_score_info()` (`score_helpers.py`) NHL sport_tag'i algıladığında `parse_nhl_status(raw_status)` çağırır ve dönen `NHLClock.is_overtime` / `NHLClock.is_shootout` değerlerini score_info dict'ine ekler.

### Neden bu yapı?

- **raw_status dict olarak taşınır** — ESPNMatchScore domain modeli değil infrastructure DTO'su; ESPN status payload'ını olduğu gibi tutmak downcast sorununu önler.
- **parse_nhl_status sadece hockey'de çağrılır** — diğer sporlar için sıfır maliyet; `sport_tag` kontrolü `score_helpers` katmanında yapılır.
- **Hata yutma izni (tek istisna)** — `parse_nhl_status` başarısız olursa `is_overtime=False, is_shootout=False` default'u korunur ve pipeline kırılmaz. Bu "sessiz hata" değil; parse hatası exit kararını pasif tarafta bırakır, yanlış exit tetiklemez.
- **raw_status boş dict → flag'ler False** — Odds API MatchScore veya pre-game ESPN skoru geldiyse `raw_status={}` olur; `if raw_status:` guard ile parse atlanır, güvenli default.

### Etkilenen dosyalar

| Dosya | Değişiklik |
|---|---|
| `src/infrastructure/apis/espn_client.py` | `ESPNMatchScore.raw_status: dict` field eklendi; `_parse_competition()` hockey için `raw_nhl_status = status_block` |
| `src/orchestration/score_helpers.py` | `build_score_info()` NHL branch: `parse_nhl_status(raw_status)` → `is_overtime`, `is_shootout` |
| `src/domain/sports/nhl_match_clock.py` | Değişmedi (Task 3A'dan geliyor) |
| `tests/unit/orchestration/test_score_helpers.py` | 5 NHL flag testi eklendi |

---

## NHL Puck Line (Task 6, 2026-04-28)

**Entry:**
- Standart line: -1.5 (Polymarket'te %95 örnekler).
- Fiyat aralığı 0.20-0.80, volume ≥ 3000 USDC.
- Gap threshold ana moneyline ile aynı (0.05).

**Exit (decide_nhl_puck_line_exit, priority sıralı):**
1. NEAR_RESOLVE — bid ≥ 0.94 → SELL_ALL
2. SCALE_OUT — bid ≥ 0.85 + ilk kez → SELL_50
3. PREDICTIVE_DEAD — p_cover < bid + 0.03 (hybrid: empirical → Skellam fallback) → SELL_ALL
4. STRUCTURAL_DAMAGE — current_price/entry < 0.30 → SELL_ALL
5. HOLD

**Math:**
- Skellam dağılımı: home-away skor farkı değişimi ~ Skellam(λ_home×t, λ_away×t).
- λ_5v5 = 0.000853 per-team-per-second (lig avg 6.142 / 2 / 3600).
- Cover threshold: final_margin >= 2 (favori -1.5 için).

**Empirical tablo:**
- 4198 maç, MoneyPuck 2022-2024 sezonları.
- Key: `period_currentMargin_secondsRemaining` → p_favorite_covers.
- 1217 entry (1019 non-null, n>=30).
- Wilson CI %95, min_sample=30.
- SO winner +1 gol konvansiyonu (Polymarket "incl. OT/SO" resolution).

**Empty net:** Heuristik — ESPN raw_status'ta flag yok. P3 son 3dk + 1 gol fark → empirical tabloda inheresi yansır (modifier gereksiz).

---

## NHL Totals (Task 7, 2026-04-28)

**Entry:**
- Target lines: 5.5 ve 6.5 (Polymarket NHL standart).
- Fiyat aralığı 0.20-0.80, min target 4.5 (4.5 altı thin market).
- Volume ≥ 3000 USDC.
- YES = OVER, NO = UNDER (NBA konvansiyonu paralel).

**Exit (decide_nhl_totals_exit, priority sıralı):**
1. NEAR_RESOLVE — bid ≥ 0.94 → SELL_ALL
2. SCALE_OUT — bid ≥ 0.85 + ilk kez → SELL_50
3. PREDICTIVE_DEAD — p_side < bid + 0.03 (over: p_over; under: 1 - p_over) → SELL_ALL
4. STRUCTURAL_DAMAGE — current_price/entry < 0.30 → SELL_ALL
5. HOLD

**Math:**
- Poisson dağılımı: future_total_goals ~ Poisson(λ_total × t).
- λ_total = 6.142 / 3600 = 0.001706 per-second.
- P(over X.5) = P(future_goals >= ceil(X + 0.5 - current)).

**Empirical tablo:**
- Aynı 4198 maç, target 5.5 + 6.5 için ayrı bucket.
- Key: `period_currentTotal_secondsRemaining_targetTotal` → p_over.
- 2484 entry (1816 non-null, n>=30).
- SO winner +1 gol konvansiyonu (Karar 3).

**Pulled-goalie effect:** Empirik tabloda otomatik gömülü. Son 5 dk'da empirical p_over Poisson'dan **+5-10pp daha yüksek** (kayıp takım kaleciyi çekince gol oranı artar). Modeling ek modifier gerektirmez.

**OT/SO modifier:** OT'ye gidince Over yararı yansır (her OT goal +1, SO +1). Empirical tabloda final_total bu kuralla hesaplanmıştır.

---

## NHL 3-way ML — Skip (v1)

**Karar (2026-04-28)**: NHL 3-way regulation winner market'i Task 6/7 kapsamı dışı bırakıldı. Polymarket NHL'de bu market type %5'ten az gözlemlendi (manuel inceleme). MVP scope odakta tutmak için skip; Task 5 dry-run verisinde sıkça yakalanırsa Task 8 olarak açılır.

---

## Match Finished Entry Guard (2026-04-28)

**Sorun:** Bot bitmiş NBA maçına girdi. Pattern: Trade 1 NEAR_RESOLVE @ 04:45 (kâr) → Trade 2 entry @ 05:18 (33dk sonra, aynı event farklı spread) → 1 saniye sonra score_exit (SPREAD_MATH_DEAD margin=9.5 clock=0). Production'da round-trip fee ~$2/trade, worst case 10 maç/gün × 3 trade = ~$150/gün burn riski.

**Kök neden:** `gate.py` `max_match_start_hours: 6.0` config field tanımlı ama hiçbir yerde enforce edilmiyor. Scanner'ın `_match_start_recent_or_future` 8h post-start'a kadar kabul ediyor — NBA 2.5h maç → 5.5h dead window'da bot resolve-edilmemiş market'e giriyor.

**Çözüm:** `src/strategy/entry/_match_status.py` (yeni) — `is_match_likely_finished(match_start_iso, sport_tag)` → sport-aware heuristic. Threshold: `get_match_duration_hours(sport) + 0.5h tampon`.

| Sport | Duration | Threshold (bitmiş kabul) |
|---|---|---|
| NBA | 2.5h | 3.0h |
| NHL | 2.5h | 3.0h |
| NFL | 3.25h | 3.75h |
| MLB | 3.0h | 3.5h |
| Tennis | 2.5h | 3.0h |

`gate.run()` market loop başına check eklendi → MATCH_FINISHED skip with debug detail. Sport-agnostic, score data gerekmez (cheap entry-time heuristic).

**Trade 2 senaryosu:** hours_since=6.3 > NBA threshold=3.0 → reddedildi.

**Test:** 9 unit test (`tests/unit/strategy/entry/test_match_status.py`) + 3 integration test (gate skip path).

---

## Tennis (Phase 0 Paper Trade) — 2026-04-29

### Active scope

- H2H markets only (Match Total Games deferred to Phase 4)
- BO3 only (BO5 Grand Slam in Phase 2)
- Tournament tiers: Grand Slam + Masters 1000 + ATP/WTA 500 + ATP/WTA 250 (250 included only in Phase 0 for sample size)
- ITF, Challenger, Futures: excluded permanently

### Filter thresholds

| Filter | Phase 0 value | Source |
|---|---|---|
| Min ranking | top 100 | Spec Section 9 |
| Max ranking gap | < 100 | User decision (match-fixing risk filter) |
| Min model edge | 0.05 | Spec Section 9 |
| Match window | 0-24h pre-match | Spec Section 9 |
| Position size | $0 (paper) | Spec Section 9 |

### Surface factors (serve % multiplier)

| Surface | ATP | WTA | Source |
|---|---|---|---|
| Grass | 1.00 | 1.00 | Tennisnerd 2026 baseline |
| Hard | 1.00 | 1.05 | empirical study |
| Clay | 0.92 | 0.95 | empirical study |

### Magnus formulas

- Game on serve: O'Malley (2008) eq.3 / Newton-Keller (2005) `G(p) = p^4 * (1 + 4q + 10q^2 + 20q^3*p/(p^2+q^2))` where q=1-p (verified G(0.5)=0.5)
- Set: recursive sum to 6-x or 7-x, tiebreak via binomial approximation
- Match BO3: 2-of-3 sets independent
- Match from state: combinatorial with current set + game state
- BO5: NotImplementedError (Phase 2)

### Data source

- Sackmann GitHub `tennis_atp` + `tennis_wta` repos
- Cache: `data/sackmann_cache/`, refresh weekly
- Player xref persisted: `data/tennis_player_xref.json`

### Gate criteria for Phase 1

- ≥ 50 finished matches in paper log
- Directional accuracy (high-confidence calls, model ≥ 0.55) ≥ 65%
- No structural bug in resolver (resolver fail rate < 1%)

---

## Tennis Phase 1 v1 — Live (dry_run) — 2026-04-28

### Active scope

- **Active in `entry.active_sports`:** `tennis` (ATP) + `tennis_wta` (WTA)
- **Mode:** `dry_run` end-to-end simulation (entry + exit, no real orders)
- **Markets:** H2H only (Match Total Games still deferred to Phase 4)
- **Format:** BO3 only (BO5 Grand Slam = HOLD-safe fallback until Phase 2)
- **Position cap:** inherits global `risk.max_single_bet_usdc=$75` and `risk.max_bet_pct=5%`
  cap (no separate tennis cap in Phase 1 — sizing handled by directional entry pipeline)

### Exit thresholds (table-based, BO3)

`src/strategy/exit/_tennis_exit_dispatch.py`:

| Priority | Layer | Trigger | Action |
|---|---|---|---|
| 1 | NEAR_RESOLVE | bid ≥ 0.95 | SELL_ALL |
| 2 | STRUCTURAL_DAMAGE | current_price/entry ≤ 0.30 | SELL_ALL |
| 3 | MATHEMATICAL_DEATH | sets 0-2 (BO3) / 0-3 (BO5) | SELL_ALL |
| 4 | SET_LOSS_BAGEL | last completed set lost 0-6 (BO3 only) | SELL_75 |
| 5 | SET_LOSS_DECISIVE | last completed set lost {1,2,3}-6 (BO3 only) | SELL_50 |
| 6 | PROFIT_LOCK | bid ≥ 0.80 | SELL_50 |
| 7 | HOLD | default | — |

Direction handling: `BUY_YES` = bet on player A (home); `BUY_NO` = bet on B (away).
For `BUY_NO`, "home won set" is reframed as "we lost set" — bagel/decisive
threshold applied symmetrically.

### BO5 deferral

BO5 (Grand Slam ATP men's singles) intentionally falls back to HOLD on
SET_LOSS_DECISIVE / SET_LOSS_BAGEL. NEAR_RESOLVE / PROFIT_LOCK / STRUCTURAL_DAMAGE /
MATHEMATICAL_DEATH (now triggered at 0-3 sets) still active. Phase 2 adds
Bayesian model + full BO5 set-state logic.

### Phase 0 paper observer disabled

`config.yaml → tennis.enabled: false` + `tennis.phase: disabled`. Paper observer
becomes redundant in dry_run because real (simulated) entries land in
`logs/audit/trade_history.jsonl` with the same event_id / outcome pairing.
Magnus model + Sackmann predictor are no longer wired into the heavy cycle.
v2 reactivation: flip `tennis.enabled: true` + `tennis.phase: v2` when Bayesian
work begins.

### Skipped / deferred to Phase 2-3

- Magnus base p(win) model (entry-side enrichment)
- Bayesian in-match p_serve update
- Momentum EWMA
- Risk-adjusted EV combiner
- BO5 set-bazlı decisive/bagel handling

### Why these specific thresholds

- **0.95 NEAR_RESOLVE / 0.80 PROFIT_LOCK:** match `config.yaml → tennis.exit.near_resolve_bid` / `profit_lock_bid` — set during Phase 0 spec design.
- **0.30 STRUCTURAL_DAMAGE:** mirrors NHL `exit_nhl.structural_damage_ratio=0.30` — calibrated empirical threshold for "price collapse beyond comeback".
- **SELL_75 on bagel vs SELL_50 on decisive:** bagel (0-6) signals decisive serve
  break collapse; recovery rate ≪ 5%. Decisive (1-6 to 3-6) recovery ~5-8%.
  Asymmetric sizing reflects the gap.
- **MATHEMATICAL_DEATH SELL_ALL:** 0-2 BO3 / 0-3 BO5 = literally cannot win → no
  reason to hold for residual bid. Liquidity exit while market still has bid.

---

## MLB Sport Package — Sprint 1 Ship (2026-04-30)

**Karar:** MLB (Major League Baseball) sport pkg infrastructure tamamlandı, **DORMANT** olarak ship'lendi. `baseball_mlb` `active_sports`'ta YOK — gate skip eder. Sprint 1.5'te gate.py refactor + MLB router eklenince aktive olur.

**Active markets (Sprint 1.5'te):** ML + RL + Totals

**Fair price model:**
- ML: Pythagorean expectation (exponent 1.83, Steven Miller verified) + log5 (Bill James) + pitcher ERA adjustment (weight 0.35, league avg 4.20)
- RL: Skellam-distributed margin from team Poisson runs/game
- Totals: Poisson-sum with park factor (Baseball Savant 5-yr) + weather run bias

**Pre-game window:** 2-12h (pitcher confirmation locks ~12h ahead)

**M1/M2/M3 (SPEC-014 implemented):**
- M1: inning >= 7 AND deficit >= 5 → SELL_ALL
- M2: inning >= 8 AND deficit >= 3 → SELL_ALL
- M3: inning >= 9 AND deficit >= 1 → SELL_ALL

**PREDICTIVE_DEAD margin:** 0.04 (vs NHL 0.03; MLB variance higher due to discrete run scoring).

**Rain handling:** >= 0.60 chance → SKIP. 0.30-0.60 → size × 0.7 (partial).

**Run Line -1.5 favorite:** forbidden (math: P(margin >= 2 for favored side) low yield given Polymarket pricing).

**Bookmaker:** alignment sanity check only, NOT fair price source. Internal model is the truth source.

**Win Expectancy table:** ~120 hand-coded critical cells; out-of-table fallback returns 0.5 (HOLD-safe). Phase 2 candidate: full empirical Retrosheet table.

**External dependencies:**
- `MLB-StatsAPI` (pip): probable pitcher + ERA + season stats
- OpenWeather API (free tier): 3h forecast for park-specific weather

**Sprint 1 ship state:** Tüm kod yazıldı, ~150 yeni test geçiyor. Factory MLB enricher'ı **conditional** instantiate ediyor (active_sports'ta `baseball_mlb` varsa). Şu an yok → enricher None → MLB markets gate active_sports filter'ında SKIP.

**Sprint 1.5 (next):** gate.py refactor (god-object 600+ satır, ARCH violation) + MLB sport router. MLB aktivasyonu o sprint'te olur.

**Files:** 21 new + 5 modified. NHL pattern parity (per-market-type exit + dispatch). Old `baseball_score_exit.py` stub silindi.

---

## Sprint 1.5: Gate Refactor + MLB Activation (2026-04-30)

**Karar:** Sprint 1 dormant ship'inden sonra MLB aktif edildi. gate.py refactor edilerek 400-satır ARCH limitine uydu, MLB sport routing inline branch ile eklendi.

**gate.py refactor:**
- 451 → 358 satır
- 5 helper extracted to `src/strategy/entry/_gate_helpers.py` (~140 satır)
- MLB eval logic da `_gate_helpers._evaluate_mlb()` fonksiyonuna taşındı (~75 satır)
- Helpers: _classify_confidence, _gap_multiplier, _passes_filters, _compute_stake, _check_event_guard, _evaluate_mlb

**MLB routing:**
- `EntryGate.__init__` constructor'a `mlb_edge_enricher` param eklendi
- `EntryGate.run()` içinde MLB early-branch: sport_tag in (baseball_mlb, mlb) ise `_evaluate_mlb_market()` çağrılır, normal bookmaker_prob akışı bypass
- `_evaluate_mlb_market`: parse_mlb_question → enricher.enrich → MLBEntryConfig → apply_mlb_entry_filters → Signal veya skipped_reason
- BUY: Signal(direction=BUY_YES, anchor_probability=fair_price, confidence="B") — MLB always B (no sharp-book classification yet)
- SKIP: skipped_reason (MLB_QUESTION_PARSE_FAIL / MLB_ENRICHER_UNAVAILABLE / MLB_ENRICHMENT_ERROR / MLB_ENRICHMENT_NONE / MLB_GATE_REJECT)

**GateConfig MLB fields (12 adet):**
- mlb_min/max_polymarket_price: 0.20 / 0.75
- mlb_min_market_volume: 3000 USDC
- mlb_min_liquidity: 3000 USDC
- mlb_pre_game_window: 2–12 saat
- mlb_min_gap_threshold: 0.05
- mlb_position_cap_pct: 0.03, mlb_max_position_usdc: 75
- mlb_rain_skip_threshold: 0.60, mlb_rain_partial_threshold: 0.30
- mlb_forbid_runline_minus_15_favorite: True

**Active sports:** baseball_mlb eklendi

**Sport handler registry pattern:** ertelendi (premature abstraction; 3. sport internal model gerektirinceye kadar inline branch yeterli).

**Test:** +30 (25 helper unit + 5 gate flow smoke)

**Bot durumu:** MLB markets gate'e girdiğinde Pythagorean+log5+pitcher modelimizle değerlendiriliyor. Bookmaker konsensüsü sanity check olarak kullanılmaz (apply_mlb_entry_filters içinde değil; gelecek iş — Sprint 2 sonrası).

---

## Pre-Game Window Widening — NBA + NHL (2026-04-30)

**Karar:** NBA `max_match_start_hours: 6.0 → 24.0`, NHL `nhl_max_match_start_hours: 4 → 24`. Tennis already at 24h (unchanged). MLB at 12h per Sprint 1 design.

**Gerekçe (kod incelemesi):**
- Fair price source = `bookmaker_prob` (gate.py line 115/168/407)
- Bookmaker odds reflect injury / lineup news within seconds via Odds API
- ESPN injury client = bonus modifier only (gate.py line 452-457), NOT base fair price
- Narrow window had no model-driven justification — assumption that "lineup must be confirmed" was wrong; lineup info is encoded in bookmaker_prob already
- Scanner stock_queue 30-min re-evaluation handles capital rotation safely (cycle_manager.py + stock_queue.py)
- Tennis 24h precedent proven safe in production

**Risk math (NHL example):**
- Late goalie scratch: ~3-5% of games × ~$2-3 per-position adverse-move loss × ~100 NHL pos/month = ~$10-15/mo loss
- Wider window upside: ~2-3× position frequency × ~$3 expected value/position = ~$300-600/mo gain
- Ratio: ~20:1 favorable

**Rollback triggers (any one within 7 days post-deploy):**
- Exposure cap saturated > 80% sustained 24h
- Daily PnL < -2× rolling 30-day baseline for 3 consecutive days
- Position count > 2× rolling baseline for 3 consecutive days

**Rollback action:** Revert this commit (single `git revert`); restart bot with `scripts/reboot.py reload`.

**Metrics to watch (first 7 days):** position count, daily PnL, capital lock duration, exposure cap saturation.

**Sprint sequence note:** Sprint 1 (MLB dormant) → Sprint 1.5 (gate refactor + MLB activation) → Sprint 2 (this — NBA/NHL window widening).

---

## SPEC-force-close (2026-05-27) — DONE

**Sorun:** Bazı pozisyonlar -%99 zarara düşüp orderbook'ta alıcı kalmayınca SL bypass'a takılıp açık kalıyordu. Concrete: `atp-humbert-halys-2026-05-27-first-set-winner` entry 0.567 → current 0.0005, 162+ retry sonra hâlâ açık. `stop_loss.py:36-37`'deki "stale price" skip (`current_price <= 0.001`) gerçek -%99 düşüşü "WS tick gelmedi" sanıyordu.

**Çözüm:** Hybrid time+ESPN force-close güvenlik ağı, normal SL/TP/scale-out zincirinden bağımsız:

1. **ESPN-first kontrol:** `MatchStatus` event-state çekilir; `is_completed=True` veya market_type-specific period bitmiş ise (first_set için period>=2, quarter_1 için period>=2) → signal "espn_event_ended"
2. **Time fallback:** ESPN cevap yok ise `now - match_start_iso` elapsed hesaplanır; `force_close_timeouts[market_type]` (veya default) aşıldıysa → signal "time_expired"
3. **Slippage bypass:** Sinyal varsa bid book full slippage (`max_slippage_pct=1.0`) ile walk → ne fiyatta olursa olsun satılır
4. **Bid yoksa 0 realize:** Orderbook'ta hiç bid yoksa pozisyon 0 fiyatla manuel realize edilir, `FORCE_CLOSE_NO_BIDS` reason ile audit'e yazılır

**Trigger gate:** `unrealized_pnl_pct <= -0.50` (CPU + false-positive korumacı, normal SL'in alanına girmez). `force_close_timeouts` config boş ise feature devre dışı (yeni proje için opt-in).

**Karar mantığı saf:** `src/strategy/exit/time_force_close.py:check()` — I/O yok, sadece state + ESPN status + zaman → signal. Orchestration `force_close_executor.py`'da, normal exit chain'den sonra çağrılır. `_execute_exit` artık status string döndürür ("FILLED"/"REJECTED"/"PARTIAL_FILL") → REJECTED'da `continue` etmez, force-close branch'i devreye girer. (Phase 1 bug fix.)

**Etki:** 3 bot (Polymarket Agent 2.0 ana bot + tennis-lab + tennis-paper-lab) aynı stratejik mantık, ayrı config. Tennis Paper Lab'da canlı doğrulandı (2026-05-27 21:56:46-47): humbert-halys 2 pozisyon `force_close_no_bids` ile kapandı, audit + dashboard güncellendi.

**Yeni spor eklendiğinde:**
- ESPN destekliyorsa → otomatik (sport_tag mapper'a satır eklemek yeterli olabilir)
- Desteklemiyorsa → `config*.yaml` `risk.force_close_timeouts` tablosuna 1-2 satır ekle

**Spec:** docs/superpowers/specs/2026-05-27-force-close-design.md
**Plan:** docs/superpowers/plans/2026-05-27-force-close.md
