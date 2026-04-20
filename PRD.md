# PRD — Polymarket Agent 2.0

> Ürün gereksinimleri ve demir kurallar.
> Version: 2.0 | Tarih: 2026-04-13 | Durum: APPROVED
>
> **SSOT ilkesi**: Bu dosya "ne" ve "neden" sorularına cevap verir. Teknik "nasıl" için TDD.md'ye referans verilir.

---

## 1. Giriş

Polymarket Agent 2.0, Polymarket tahmin piyasalarında otomatik trading yapan bir bot. Odds API üzerinden 20+ bookmaker'ın konsensüs olasılığını çıkarır, Polymarket'teki piyasa fiyatıyla karşılaştırarak pozitif beklenen değer (edge) tespit eder, çok katmanlı risk yönetimiyle pozisyon açar ve yönetir.

Çalışma mantığı tek cümlede: **Bookmaker konsensüsü + piyasa fiyatı fırsatı → boyutlandır → aç → izle → çık.**

---

## 2. Demir Kurallar

Bu kuralların hiçbiri ihlal edilemez. Her biri ya mimari bütünlüğü ya da sermaye güvenliğini korur.

### 2.1 P(YES) Anchor Kuralı
Olasılık her zaman P(YES) olarak saklanır. BUY_YES de BUY_NO da olsa, `anchor_probability = P(YES)` değişmez. Yön ayarlaması karar mantığında yapılır, saklama yapılmaz. (bkz. ARCHITECTURE_GUARD Kural 7)

### 2.2 Event-Level Guard
Aynı `event_id`'ye sahip iki pozisyon ASLA açılamaz. "Man City vs Brighton" maçında BUY_YES "City wins" varsa, BUY_NO "Brighton wins" açılamaz — aynı event. Bu kural `entry/gate.py` seviyesinde kontrol edilir. (bkz. ARCHITECTURE_GUARD Kural 8, TDD §6.4)

### 2.3 Confidence-Based Sizing
Pozisyon boyutu confidence seviyesine göre belirlenir:
- **A**: bankroll × %5
- **B**: bankroll × %4
- **C**: giriş yapılmaz (blok)

Ek çarpanlar `max_bet_pct` cap'ine tabidir (tek cap, config.yaml'dan). (bkz. TDD §6.5)

### 2.3.1 Probability-Weighted Sizing (SPEC-016)

**Demir kural:** Stake, model'in win probability'si ile doğrudan orantılıdır.

Formül: `stake = bankroll × bet_pct × win_prob`

Bu, "kazanma ihtimali yüksek olana daha çok para, düşük olana daha az" prensibini enforce eder. Yüksek-varyans düşük-prob girişlerin bankroll üzerindeki marjinal etkisi azaltılır.

**Etkisi:** Portföy ortalama stake'i ~%30 düşer → daha çok pozisyon alma alanı → diversification artar. Expected value %3-5 düşer ama variance ciddi azalır (kazanma oranı stabilleşir).

**Rollback:** `risk.probability_weighted: false` → eski base-only formül.

### 2.4 Bookmaker-Derived Probability
P(YES), Odds API'den çekilen bookmaker verisiyle hesaplanır. Pinnacle/Betfair/Smarkets gibi sharp book'lar 3.0× ağırlıkla, reputable book'lar (Bet365, William Hill vb.) 1.5× ağırlıkla, diğerleri 1.0× ağırlıkla ortalaması alınır. Exchange bookmaker'lara (Betfair, Matchbook, Smarkets) vig normalize uygulanmaz — fiyatları zaten gerçek olasılığa yakın. Edge eşiği unified: A-conf %6, B-conf %6 (confidence_multipliers A=1.00, B=1.00 — SPEC-010 rollback + Bug #2 fix). (bkz. TDD §6.1, §6.3)

### 2.5 3-Katmanlı Cycle
Bot üç cycle seviyesinde çalışır:
- **WebSocket**: anlık fiyat tick (SL + scale-out)
- **Light (5 sn)**: hızlı çıkış kontrolü
- **Heavy (30 dk)**: scan + enrichment + entry kararları

Heavy cycle içinde light cycle interleave eder (heavy uzun sürerse light yine tetiklenir). Gece modunda (UTC 08-13) heavy 60 dk'ya uzar.

### 2.6 Circuit Breaker Zorunludur
Aşağıdaki eşiklerden birinde bot yeni giriş yapmaz:
- Günlük kayıp ≥ %8 → 120 dk cooldown
- Saatlik kayıp ≥ %5 → 60 dk cooldown
- 4 ardışık kayıp → 60 dk cooldown
- Soft blok: günlük kayıp ≥ %3 → yeni giriş askıda

Circuit breaker her entry öncesi kontrol edilir ve devre dışı bırakılamaz. (bkz. TDD §6.15)

### 2.7 Scale-Out Profit-Taking (Midpoint) — SPEC-013
Kâr alma tek mekanizma ile: 1-tier scale-out.
- **Tier 1**: Entry fiyatı ile resolution (0.99) arasındaki yolun yarısına geldiğinde pozisyonun %40'ını sat.
  - Entry 43¢ → 71¢ tetik, Entry 70¢ → 84.5¢ tetik
- Kalan pozisyon near-resolve (94¢) veya SL'ye kalır.

Eski PnL% bazlı semantik (entry fiyatına bağımlı adaletsiz) değişti — şimdi
"kalan mesafe" bazında her entry için adil tetikleme.

(bkz. TDD §6.6)

### 2.8 Favorite Filter — SPEC-013
Bot **sadece favori taraflara** girer: normal + early entry'de bookmaker'ın
bizim tarafa verdiği olasılık %52'den az ise trade atlanır (`min_favorite_probability`, SPEC-013 rev).
Underdog value bet'leri (low market price + yüksek bookmaker) artık alınmıyor —
varyans düşürme amacıyla. Consensus stratejisi zaten EV guard ile favori-biased.

---

## 3. Operasyonel Akışlar

### 3.1 Bot Başlatma Akışı
1. `main.py` argparse (mode: dry_run | paper | live) ve config.yaml yükler.
2. `orchestration/process_lock.py` tek instance garantisi verir.
3. `orchestration/startup.py` wallet'i bağlar, persistence'ı açar, açık pozisyonları JSON store'dan geri yükler.
4. `agent.py` ana döngüyü başlatır → heavy cycle tetiklenir.

### 3.2 Entry Akışı (Heavy Cycle)
1. **Scan**: `scanner.py` Polymarket Gamma'dan `allowed_sport_tags` filtreli market'ler çeker (bkz. `config.yaml` scanner bölümü).
2. **Stock housekeeping**: `orchestration/stock_queue.py` persistent pool; taze scan sonucuyla refresh edilir, TTL ile expire edilir (match_start - 30dk, 24h idle, 3× no_edge, event açık).
3. **JIT pipeline**: Stock top-N (match_start ASC) + fresh-only top-M → gate'e yalnızca bu batch girer. N ve M = `empty_slots × stock.jit_batch_multiplier` (default 3). Odds API kredisi sadece bu alt küme için harcanır.
4. **Match**: `domain/matching/` modülleri Polymarket market'ini Odds API sport key'ine eşler.
5. **Enrich**: `strategy/enrichment/odds_enricher.py` Odds API'dan bookmaker probability çeker.
6. **Gate**: `strategy/entry/gate.py` event-guard + manipulation + liquidity + confidence + edge + entry_price_cap kontrolü yapar.
7. **Size**: `domain/risk/position_sizer.py` confidence bazlı boyut üretir, cap'lere uygular.
8. **Execute**: `infrastructure/executor.py` CLOB client üzerinden emri gönderir (dry_run modunda loglar).
9. **Record**: Pozisyon JSON store'a yazılır, trade log JSONL'e eklenir. Exposure cap aşımında signal size kırpılarak girilir (soft+hard cap clipping); min_entry altında veya cap tamamen doluysa stock bekleme odasına push edilir. Diğer red sebepleri (max_positions / no_edge / no_bookmaker_data) de stock'a push edilir.

### 3.3 Light Cycle İzleme (5 sn)
Her 5 saniyede bir:
1. WebSocket tick'lerinden son fiyatlar okunur.
2. Açık pozisyonlar için flat SL (`stop_loss.py`) ve scale-out (`scale_out.py`) kontrolü yapılır.
3. Tetiklenen çıkış sinyali varsa `exit/monitor.py` üzerinden ilkine göre emir gönderilir.

**Exposure cap enforcement:** hem gate-time (entry öncesi) hem execution-time
(order öncesi) kontrol edilir, payda **toplam portföy değeri** (nakit + açık
pozisyonlar) — nakit değil. Detay: TDD §6.15.

**Scanner filter scope (h2h only):** sadece moneyline markets, `match_start`
≤ 24h (Odds API penceresi), `yes_price < 0.98` (fiyat-based resolved detection,
Polymarket flag lag atlatması). PGA Top-N props + futures (>24h) + bitmiş
marketler scanner seviyesinde elenir. Detay: TDD §5.7.5.

### 3.4 Exit Akışı (Heavy Cycle)
Heavy cycle sırasında açık pozisyonlar için:
1. **Graduated SL**: elapsed-aware dinamik SL (TDD §6.8).
2. **Near-Resolve**: eff_price ≥ 94¢ + 5 dk pre-match guard → çık (TDD §6.11).
3. **A-Conf Hold**: confidence=A + entry ≥ 60¢ → **flat SL ve graduated SL atlanır**; sadece scale-out, near-resolve ve market_flip (elapsed ≥ %85'te `current_price < 0.50`) aktif (TDD §6.9).
4. **Favored**: eff_price ≥ 65¢ + confidence ∈ {A, B} → promoted; altı demoted (TDD §6.13).
5. **Never-in-Profit Guard**: peak_pnl hiç pozitif olmamış + elapsed > %70 → daha agresif SL (TDD §6.10).

### 3.5 Circuit Breaker Tetiklendiğinde
1. `circuit_breaker.py` bankroll durumunu her entry öncesi kontrol eder.
2. Eşik aşılırsa yeni entry reddedilir, log + Telegram bildirimi.
3. Cooldown süresi dolana kadar bot sadece **çıkış** kararları alır (açık pozisyon yönetimi devam).
4. Cooldown sonrası otomatik devreye girer.

---

## 4. Fonksiyonel Gereksinimler

8 yetenek grubu. Detaylar TDD'ye referans.

### F1. Scan
Bot Polymarket Gamma API'dan canlı market'leri keşfeder. `allowed_sport_tags` filtresi uygular. Max `max_markets_per_cycle=300` limitiyle sınırlı. (bkz. `config.yaml` scanner bölümü, `src/orchestration/scanner.py`)

### F2. Enrich
Her adaya Odds API'dan bookmaker verisi çekilir. `domain/matching/` modülleri Polymarket slug'ını Odds API sport key'ine dönüştürür. `bookmaker_weights.py` sharp book'ları ağırlıklandırır. (bkz. TDD §6.1)

### F3. Entry Decision
`strategy/entry/gate.py` giriş kararını orchestrate eder. 3 entry stratejisi: consensus (bookmaker+market aynı favori, 60-80¢ aralığı + EV guard), early_entry (6+ saat öncesi), normal (bookmaker P(YES) vs market). Her strateji edge + confidence + guards'tan geçer. Öncelik: consensus → early → normal (ilk Signal kazanır). Consensus'e EV guard: bookmaker'in bizim tarafa olasılığı entry price'tan düşükse skip (negatif EV koruması — Spurs 84¢ senaryosu). (bkz. TDD §6.4)

### F4. Position Sizing
Confidence-based. A=%5, B=%4, C=blok. Tek cap: `max_bet_pct` (config.yaml'dan). (bkz. TDD §6.5)

### F5. Execute
`executor.py` 3 modda çalışır: `dry_run` (log-only), `paper` (mock fills), `live` (gerçek CLOB emri). Her emir trade log'a JSONL formatında yazılır. (bkz. `src/infrastructure/executor.py`)

### F6. Monitor
3 katmanlı izleme: WS tick (anlık), Light cycle (5 sn), Heavy cycle (30 dk). Pozisyon durumu JSON store'da tutulur, dashboard anlık okur.

### F7. Exit
Çıkış kararı birden fazla mekanizmanın değerlendirmesiyle verilir: flat SL, graduated SL, scale-out, never-in-profit, market_flip, near-resolve, hold_revoked, ultra_low_guard, circuit_breaker, manual. İlk tetiklenen sinyal uygulanır. Tam liste ve öncelik sırası TDD §6.6–§6.14'te; ExitReason enum `src/models/` altında.

### F8. Report
3 sunum kanalı: Flask dashboard (localhost:5050), Telegram bildirim (entry/exit/CB), JSONL trade log (audit).

**Dashboard scope**:
- **Özet metrikler** (5 kart): Balance, Open P&L, Realized P&L (W/L alt-yazı), Locked in Bets, Peak Balance (total equity peak'ten drawdown%)
- **Koruma + analiz göstergeleri** (3 kart):
  - **Loss Protection** — RISK gauge + Down% + Stop at% (CB günlük eşik) + Status (Safe/Caution/Warning/Stopped)
  - **Positions** — slot gauge (current/max) + entry_reason tag'leri (NOR/CON/EAR)
  - **Branches** — sport/league ROI treemap: alan ∝ invested USDC, renk ∝ ROI (yeşil+/kırmızı−/sıfıra yakın mavi), hover tooltip
- **Grafikler** (2): Total Equity zaman serisi (realized-only: `initial + Σ exit_pnl_usdc`, stepped; period tabs 24h/7d/30d/1y + adaptif bucketing), Per-Trade PnL waterfall (aynı period tabs). Detay: TDD §5.7.7
- **Trades feed** (sağ panel, 4 sekme): Active | Exited | Skipped | Stock — her kart tıklanabilir (Polymarket event sayfasını yeni sekmede açar), branş ikonlarıyla
- **Cycle bar** (topbar): Hard cycle (mavi) + Light cycle (teal) durumu; bot offline/idle gri

**Kaldırılan bölümler**:
- **API Usage** paneli — Odds API quota tracking henüz implement edilmedi; kart + endpoint kaldırıldı (sonraki faza ertelendi)
- **Performance** paneli (Wins%, Avg Edge, Brier Score, Best Topic) — MVP dışı
- **AI vs Bookmaker** paneli (divergence chart) — MVP dışı

**Rationale**: MVP odak sermaye yönetimi + pozisyon takibi + per-branch ROI sağlığı. Model karşılaştırması ve API quota dashboardu sonraki faza ertelendi.

Teknik detaylar: `src/presentation/dashboard/` kod tabanı.

### F9: Retrospektif Analiz Arşivi (SPEC-009)

**Amaç**: Kural (scale-out, exit threshold'ları, near_resolve) etkinliğini
geriye dönük veriyle değerlendirmek.

**Ne tutulur**:
- `logs/archive/exits.jsonl` — her exit tam snapshot + o anki skor
- `logs/archive/score_events.jsonl` — maç içindeki her skor değişikliği
- `logs/archive/match_results.jsonl` — maç final result

**Koruma**: Reboot/reload/trade silme archive'a dokunmaz. Append-only.

**Analiz örneği**: "MLB'de 2-1 gerideyken çıktığımız maçların kaçı geri dönüp
kazandı?" sorusu event_id JOIN ile cevaplanabilir.

### F10: Baseball Score Exit (SPEC-010)

**Amaç**: A-conf baseball pozisyonlarda maç tersine giderken full wipeout
önlenir. Tennis T1/T2 ve hockey K1-K4 ile simetrik FORCED exit.

**Kurallar**:
- M1: 7. inning+ ve ≥5 run deficit → exit (blowout)
- M2: 8. inning+ ve ≥3 run deficit → exit (late big deficit)
- M3: 9. inning+ ve ≥1 run deficit → exit (final inning)

**Eski sistem (SPEC-008)**: defensive guard (SL ertele), A-conf'ta
çalışmıyordu. SPEC-010 ile kaldırıldı.

### F11: Cricket Cluster (SPEC-011)

**Amaç**: 7 cricket ligi entegre — IPL (aktif Nisan-Haziran), ODI (yıl boyu),
International T20, PSL, Big Bash, CPL, T20 Blast.

**Veri Kaynakları**:
- Odds API (bookmaker consensus, sharp 3-5)
- Polymarket (event markets)
- CricAPI free tier (canlı skor — runs, wickets, overs; 100 hit/gün)

**Score Exit (C1/C2/C3)**:
Tennis T1/T2, hockey K1-K4, baseball M1/M2/M3 ile simetrik. Sadece 2. innings
chase + biz chasing iken tetiklenir. ESPN cricket yok, CricAPI kullanılır.

**Rate Limit**: CricAPI quota dolunca (100/gün) cricket entry'ler
`cricapi_unavailable` skip_reason ile atlanır, log'a yazılır.

**TODO-003**: Paid tier upgrade ($10/ay, 1000+ hit/gün) — cricket hacmi
arttığında gerekli.

### F12: 3-Way Market Support (SPEC-015)

**Amaç**: Polymarket'in en yüksek hacimli market kategorisi (soccer, rugby,
AFL, handball) için 3-way binary market (Home/Draw/Away) desteği.

**Kapsam**:
- 60+ soccer ligi (EPL, La Liga, Serie A, Bundesliga, Ligue 1, Champions
  League, Europa, MLS, Süper Lig, Eredivisie, Brasileirão, Liga MX, 40+ ülke
  ligi)
- Rugby Union + Rugby League
- AFL
- Handball

**Mimari**: `EventGrouper` 3 binary market'i event_id ile grupluyor. `ThreeWayEntry`
direction seçimi yapar (favori = en yüksek bookmaker olasılığı). `SoccerScoreExit`
DRAW ve HOME/AWAY için ayrı kurallar (65'+ lock). Aynı altyapı tüm 3-way sporlara
DRY pattern ile çalışır.

**Entry kuralları**:
- Favorite threshold: %40 absolute + 7pp margin (tossup eler)
- Edge: %6 unified (mevcut sistemle aynı)
- Sum filter: 3 market yes_price toplamı 0.95-1.05 (double chance eler)
- Excluded competitions: international/club friendly, preseason, testimonial

**Exit kuralları**:
- First-half lock (0-65'): HOLD (comeback potential)
- 65'+ 2 gol geride → EXIT
- 75'+ 1 gol geride → EXIT
- DRAW: 0-70' HOLD, 75'+ gol EXIT, knockout 90+ AUTO-EXIT

**Credit budget**: SPEC-015 günlük cap 800 credit (20K aylık bütçeden %4 tampon).
Aşılırsa fetch'ler skip, mevcut pozisyonlar etkilenmez.

**Kapsam dışı**:
- Live direction switch (pozisyon outcome değiştirme) — SPEC-016 ileride
- Underdog/draw value bet yakalama — SPEC-017 ileride (100+ favori trade sonrası)

---

## 5. Non-Fonksiyonel Gereksinimler

### 5.1 Latency
- Heavy cycle ≤ 30 sn (scan + enrichment + entry decision)
- Light cycle ≤ 1 sn (SL + scale-out kontrolü)
- WebSocket tick → exit decision ≤ 500 ms

### 5.2 Uptime
- MVP hedefi: 48 saat kesintisiz dry_run
- WebSocket disconnect → 30 sn içinde reconnect

### 5.3 Crash Recovery
- `startup.py` açık pozisyonları `positions.json`'dan geri yükler
- Trade log JSONL append-only, crash'ten sonra replayable
- Process lock çift instance engeller

### 5.4 Observability
- Flask dashboard: pozisyonlar, PnL, circuit breaker durumu, < 3 sn gecikme, 5 sn polling
- Bot durumu her tick `logs/bot_status.json`'a yazılır (mode, last_cycle, last_cycle_at, reason) → dashboard cycle bar
- Trade history append + exit update (`TradeHistoryLogger.update_on_exit` atomic rewrite); dashboard Exited/Stats/Branches/Waterfall bu dosyadan beslenir
- Equity history her heavy cycle sonunda `equity_history.jsonl`'e snapshot yazılır (audit + Peak Balance hesabı); Total Equity chart ise `/api/trades` cumsum'dan beslenir (PLAN-008/009, bkz. TDD §5.7.7). Peak Balance tüm zamanların total_equity zirvesidir (cash-only HWM değil)
- Skipped adaylar `skipped_trades.jsonl`'e (orchestration'dan) yazılır; dashboard Skipped sekmesinde gösterir
- Stock queue her heavy cycle sonunda `stock_queue.json`'a dump edilir; dashboard Stock sekmesinde gösterir (persistent pool: restart sonrası restore edilir)
- Telegram: entry/exit/CB olayları
- JSONL trade log: audit için append + exit güncelleme (append-only değil artık)

### 5.5 Çalışma Modları
- `dry_run`: API çağrıları canlı, emir gönderimi yok — default test modu
- `paper`: mock fills, bankroll simülasyonu
- `live`: gerçek emir + gerçek USDC

### 5.6 Test Kapsamı
- Domain katmanı: > %90 unit test coverage zorunlu
- Strategy katmanı: > %80 unit test coverage
- Integration test: entry pipeline + exit pipeline + WS reconnect

---

## 6. Teknik Kısıtlar

### 6.1 API Limitleri
- **The Odds API**: 20K kredi/ay (paid tier), her `fetch_odds` 1-10 kredi
- **Polymarket CLOB REST**: ~100 istek/dk
- **Polymarket Gamma**: rate limit belirsiz, ~300 market/cycle güvenli
- **Telegram**: 30 mesaj/sn

### 6.2 Altyapı
- **Chain**: Polygon mainnet
- **Ödeme**: USDC (6 decimal)
- **Python**: 3.12+
- **OS**: Linux (production), Windows (dev)

### 6.3 Cycle Süreleri
- Heavy: 30 dk (gündüz), 60 dk (gece UTC 08-13)
- Light: 5 sn
- WebSocket: sürekli (disconnect + reconnect)

### 6.4 Market Filtreleme
- Min likidite: $1000
- Max süre: 14 gün (maç başlangıcından öncesi)
- Allowed categories: `sports` (yalnızca)
- Allowed sport_tags: `baseball_*`, `basketball_*`, `icehockey_*`, `americanfootball_ncaaf|cfl|ufl`, `tennis_*` (dinamik), `golf_lpga_tour|liv_tour` (bkz. `config.yaml` scanner bölümü)

### 6.5 Sport Tag Güvenilirlik
- Gamma API event tag sırası güvenilmez — bir event birden fazla tag taşıyabilir ve yanlış tag önce gelebilir
- **Slug-based override**: Market slug prefix'i (ör. `atp-`, `wta-`, `nhl-`) event tag'inden güvenilir kabul edilir; tutarsızlık varsa slug prefix kazanır (bkz. TDD §7.3)
- Yanlış sport_tag tüm downstream'i bozar: exit kuralları (market_flip tennis hariç tutması), treemap kategorizasyonu, sport_rules seçimi

---

## 7. Savunma Mekanizmaları

4 katmanlı koruma. Her biri pozitif feature — bot'un aktif yaptığı kontroller.

### 7.1 Manipulation Guard
`domain/guards/manipulation.py` şu kontrolleri yapar:
- Min likidite: $10K toplam book
- Self-resolving market tespiti (kişi/kurum + self-resolving fiil paterni)

(bkz. TDD §6.16)

### 7.2 Liquidity Check
`domain/guards/liquidity.py` entry + exit seviyelerinde:
- **Entry**: min $100 depth; pozisyon > %20 book payı ise boyut yarıya iner
- **Exit**: min %80 fill ratio; altıysa emir bölünür

(bkz. TDD §6.17)

### 7.3 Circuit Breaker
Bölüm 2.6'daki eşiklerin aktif enforcement'ı. `domain/risk/circuit_breaker.py` her entry öncesi bankroll durumunu kontrol eder. (bkz. TDD §6.15)

### 7.4 Event-Level Guard
`strategy/entry/gate.py` her entry kararında event_id kontrolü yapar. Açık pozisyon listesinde aynı event_id varsa entry reddedilir. (bkz. Demir Kural 2.2, ARCHITECTURE_GUARD Kural 8)

---

## 8. Sözlük

| Terim | Tanım |
|---|---|
| **anchor** / `anchor_probability` | Bookmaker konsensüsünden hesaplanan P(YES). Pozisyon yönünden bağımsız saklanır. |
| **P(YES)** | Polymarket market'indeki YES outcome'unun olasılığı (0.0 – 1.0) |
| **edge** | Piyasa fiyatı ile anchor arasındaki beklenen değer farkı (`anchor - market_price` BUY_YES için) |
| **eff_price** | Effective price — pozisyon için pratik fiyat (market mid ± slippage tahmini) |
| **direction** | `BUY_YES` / `BUY_NO` / `HOLD` — Direction enum |
| **confidence** | `A` (sharp book veya ≥5 bookmaker) / `B` (≥3 bookmaker) / `C` (yetersiz, giriş blok) |
| **favored** | Pozisyonun elverişli durumda olduğunu işaretleyen flag (eff ≥ 65¢ + conf ∈ {A,B}) |
| **scale-out** | Kademeli kâr alma: PnL eşiklerinde pozisyonun bir kısmı satılır |
| **elapsed** | Maç ilerleme oranı (0.0 = başlangıç, 1.0 = bitiş) |
| **consensus** | Bookmaker ve Polymarket market'inin aynı favori üzerinde anlaşması |

---

## 9. Referanslar

- [TDD.md](TDD.md) — Teknik tasarım, algoritmalar, veri modelleri, cycle detayları
- [ARCHITECTURE_GUARD.md](ARCHITECTURE_GUARD.md) — Mimari kurallar (12 demir kural + anti-pattern'ler)
- [TODO.md](TODO.md) — Ertelenmiş işler ve branşlar
- [CLAUDE.md](CLAUDE.md) — Geliştirme asistanı kuralları (TODO yönetimi, mimari koruma)
- [PLAN.md](PLAN.md) — Aktif implementation planları (PLAN-001..PLAN-007)
