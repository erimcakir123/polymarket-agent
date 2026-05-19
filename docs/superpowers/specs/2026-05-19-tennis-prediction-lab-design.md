# Tennis Prediction Lab — Design (2026-05-19)

> **Durum:** APPROVED
> **Yazıldı:** 2026-05-19
> **Onaylayan:** Erim
> **İlişkili:** PLAN-TENNIS-001 (yazılacak), DECISIONS §B SPEC-N (implement sonrası)

---

## 1. Amaç

Polymarket'in tenis **alt market'lerinde** (First Set Winner + Set Handicap −1.5 + Total Sets Under 2.5) **bookmaker'ın olmadığı** market inefficiency'yi exploit eden ayrı bir trading sistemi. Ana botun **hiçbir state'ine dokunmadan** çalışan ayrı sandbox.

**Hipotez:** Polymarket tenis alt market'lerinde Pinnacle/Betfair gibi sharp bookmaker yok → fiyatlar inefficient → akademik tenis modelleri (Klaassen-Magnus + Glicko-2) ile **edge** bulunabilir.

**Hedef:** 4 haftalık paper trade'de ≥%53 prediction accuracy. Tutturursa live küçük pozisyon, tutturmazsa sil ve yola devam (ana bot etkilenmez).

---

## 2. Yapısal İzolasyon (Sıfır Risk Garantisi)

**Sandbox: git worktree** — ana repodaki kodu kullanır ama ayrı klasörde, ayrı branch'te.

```
CLAUDE PROJELER/
├─ Polymarket Agent 2.0/         ← MAIN (master branch, dokunulmaz)
│  ├─ data/                       (ana bot state)
│  ├─ logs/                       (ana bot logs)
│  ├─ config.yaml                 (ana bot config)
│  └─ dashboard :5050
│
└─ tennis-lab/                   ← SANDBOX (feature/tennis-lab branch)
   ├─ data/                      (AYRI state)
   ├─ logs/                      (AYRI logs)
   ├─ config.yaml                (override: bankroll, ports, sport)
   ├─ src/ (paylaşılan + yeni tennis modülleri)
   └─ dashboard :5051
```

**Kurulum:**
```bash
git worktree add ../tennis-lab feature/tennis-lab
```

**Kill switch (3 komut, ana bota dokunmaz):**
```bash
taskkill /F /PID <tennis_bot_pid>
git worktree remove ../tennis-lab --force
git branch -D feature/tennis-lab
```

**İzolasyon garantileri:**
- Ayrı process (PID), ayrı Python instance
- Ayrı dosya sistemi (`data/`, `logs/`)
- Ayrı port (5051)
- Ayrı bankroll ($500 paper)
- Aynı git repo (code paylaşımı için cherry-pick mümkün)

---

## 3. Veri Kaynakları

### 3.1 Tarihsel Veri (Glicko ratings build için)

**Primary: Sackmann ATP** (GitHub `JeffSackmann/tennis_atp`, MIT lisansı)
- 1968-Şubat 2026 (~80K maç)
- Her maç için: ace, double fault, 1st serve %, 1st/2nd serve won, break point saved/faced, vs.
- Yıllık CSV (atp_matches_YYYY.csv)
- Download: `https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_<YYYY>.csv`

**Backup: TML** (GitHub `Tennismylife/TML-Database`)
- 2026.csv (Ocak 2026'a kadar)
- Sackmann ile aynı schema
- Sackmann eksikse fallback

**Veri freshness limitasyonu:**
- Mart-Mayıs 2026 clay sezonu YOK
- French Open 2026 YOK (25 May - 9 Jun)
- Bu eksiklik **self-diagnostic ile gözlenir** — clay'de patlama olursa `/diagnose --group-by surface` gösterir
- V2: Daily ATP scrape (atptour.com) veya paid API

### 3.2 Live Data (anlık)

- **Polymarket Gamma API** (ana bot ile aynı): event/market scan
- **Polymarket CLOB API** (ana bot ile aynı): price feed + execute (paper)
- **Odds API** KULLANILMAZ tennis için (bookmaker yok zaten)

### 3.3 Veri Güncelleme Stratejisi

- Sackmann CSV haftalık otomatik refresh (cron veya startup)
- 5 yıl yeterli: `atp_matches_2022.csv` → `atp_matches_2026.csv`
- Eski yıllar one-time download, sonra dokunulmaz

---

## 4. Rating Sistemi — Glicko-2

### 4.1 Neden Glicko-2?

| Özellik | Elo | Glicko-2 |
|---|---|---|
| Rating | Tek skaler | Rating + RD (uncertainty) + volatility |
| Az maç oynanan oyuncu | Sabit K, yanlış değerlendirme | Yüksek RD → düşük confidence |
| Surface-spesifik | Manuel ayrım | Built-in support |
| Tennis literature | %69 accuracy | %70 accuracy + uncertainty bonus |

### 4.2 Yapı (her oyuncu için)

```
Player Rating Profile:
├─ overall: (rating, rd, volatility)
├─ serve_clay: (rating, rd, volatility)
├─ serve_grass: (rating, rd, volatility)
├─ serve_hard: (rating, rd, volatility)
├─ return_clay: (rating, rd, volatility)
├─ return_grass: (rating, rd, volatility)
└─ return_hard: (rating, rd, volatility)
```

Toplam 7 rating × oyuncu (overall + 3 surface × 2 side).

### 4.3 Build Süreci (offline batch)

1. Sackmann CSV'leri kronolojik sıraya koy (en eski → en yeni)
2. Her maç için:
   - Winner ve loser oyuncu profillerini güncelle
   - Match score parse → serve/return performance derive
   - Surface bonus uygula
3. Cache: `data/tennis_ratings.json` (player → rating dict)
4. Haftalık rebuild (yeni Sackmann CSV gelince)

---

## 5. Tahmin Motoru — Klaassen-Magnus

### 5.1 Point Win Probability

```python
def point_win_prob(server_serve_rating, returner_return_rating, surface):
    delta = server_serve_rating - returner_return_rating
    # Sigmoid map: Glicko diff → point win probability
    # Tennis baseline: ~60% on serve in ATP
    return 0.60 + sigmoid_adjusted(delta / 200)
```

### 5.2 Game / Set / Match Probability

**Klaassen-Magnus (literatür formülleri):**
- `game_win_prob(p)` = serve point win prob → game win prob (Newton-Keller formula)
- `set_win_prob(p_serve_A, p_serve_B)` = 6 game alternation + tie-break (analytic)
- `match_win_prob(p_set, format)` = sets best-of-3 or best-of-5

### 5.3 3 Market İçin Türevler

```python
def predict_first_set_winner(p1_profile, p2_profile, surface):
    """p(p1 wins first set)"""
    p_serve_p1 = point_win_prob(p1.serve[surface], p2.return[surface])
    p_serve_p2 = point_win_prob(p2.serve[surface], p1.return[surface])
    base = set_win_prob(p_serve_p1, p_serve_p2)
    return adjust_with_features(base, p1, p2, surface)

def predict_set_handicap_minus_1_5(p1, p2, surface):
    """p(p1 wins 2-0 in BO3)"""
    p_set = predict_first_set_winner(p1, p2, surface)
    # Momentum bonus: set 2 winning prob conditioned on set 1
    p_set2 = p_set + 0.05  # winner momentum
    return p_set * p_set2

def predict_total_sets_under_2_5(p1, p2, surface):
    """p(maç 2 set'te biter) = p(p1 2-0) + p(p2 2-0)"""
    p_p1_2_0 = predict_set_handicap_minus_1_5(p1, p2, surface)
    p_p2_2_0 = predict_set_handicap_minus_1_5(p2, p1, surface)
    return p_p1_2_0 + p_p2_2_0
```

### 5.4 Feature Adjustments

`adjust_with_features()` aşağıdaki feature'larla base'i revize eder:

| Feature | Etki |
|---|---|
| **Recent form** | Son 60-90 gün W% > %60 → +%3 boost; < %40 → −%3 |
| **H2H** (var ve same-surface) | Son 2 yıl içinde + same surface ise: %5'e kadar swing |
| **Tournament tier** | Grand Slam veya Masters → biraz daha emin (rating effect büyük) |
| **Form data eskiliği** | Son maç > 90 gün → confidence düşürür (B-tier'a iter) |

---

## 6. Confidence Tier — A ve B (C YOK)

| Tier | Koşullar (HEPSİ true olmalı) | Pozisyon Boyutu |
|---|---|---|
| **A** | ≥40 maç son 12 ay AND ≥15 same-surface maç AND H2H ≥1 (son 5 yıl) AND form data <60 gün AND Glicko RD < 100 (her ikisinde) | `bankroll × 0.05` = $25 (def bankroll $500) |
| **B** | ≥20 maç son 12 ay AND ≥8 same-surface maç AND form data <90 gün AND Glicko RD < 150 (her ikisinde) | `bankroll × 0.04` = $20 |
| Skip | < B koşulları | — |

**Sizing:** Ana bot ile aynı `position_sizer.compute_size()` kullanılır. Config:
```yaml
risk:
  confidence_bet_pct: {A: 0.05, B: 0.04}
  max_single_bet_usdc: 50
```

---

## 7. Edge Threshold ve Entry Logic

### 7.1 Edge Calculation (per market)

```python
model_p = model.predict(market_type, p1, p2, surface)
market_p = polymarket_price
edge = model_p - market_p  # positive → BUY, negative → BUY_NO equivalent
```

### 7.2 Entry Koşulu

- `|edge| ≥ 0.05` (5%)
- Confidence tier A veya B
- Bot'un manipulation/liquidity guard'larını geçer (ana bot ile aynı)

### 7.3 Maç Başına Max 2 Pozisyon

**Critical constraint:** Tek bir tenis maçında **en iyi 2 edge** seçilir (3 market içinden), kalan 1'i skip.

```python
def select_best_2_per_match(predictions):
    """3 market prediction'tan en yüksek edge'li 2'sini seç."""
    sorted_by_edge = sorted(predictions, key=lambda p: -abs(p.edge))
    return sorted_by_edge[:2]
```

Bu **event-level guard** ana bot ile aynı pattern (max_positions_per_event=2, DECISIONS §6.18).

---

## 8. Self-Diagnostic System

### 8.1 Per-Trade Log Format

Her tahmin/trade kaydedilirken **tüm feature snapshot** saklanır:

```json
{
  "trade_id": "uuid",
  "timestamp": "2026-05-20T13:25:00Z",
  "match": {
    "slug": "atp-djere-cerund-2026",
    "tournament": "Geneva Open",
    "tournament_tier": "ATP 250",
    "surface": "clay",
    "format": "BO3",
    "match_start_iso": "2026-05-20T17:45:00Z"
  },
  "market": {
    "type": "first_set_winner",
    "polymarket_price": 0.55,
    "direction": "BUY_YES"
  },
  "prediction": {
    "model_prob": 0.62,
    "edge": 0.07,
    "confidence_tier": "A"
  },
  "features": {
    "p1_name": "Djere",
    "p1_match_count_12mo": 87,
    "p1_surface_count": 23,
    "p1_form_w_pct_60d": 0.55,
    "p1_form_data_age_days": 45,
    "p1_glicko_overall_rating": 1820,
    "p1_glicko_overall_rd": 95,
    "p1_glicko_surface_rating": 1850,
    "p1_glicko_surface_rd": 110,
    "p2_name": "Cerundolo",
    "p2_match_count_12mo": 42,
    "p2_surface_count": 9,
    "p2_form_w_pct_60d": 0.50,
    "p2_form_data_age_days": 67,
    "p2_glicko_overall_rating": 1780,
    "p2_glicko_overall_rd": 142,
    "p2_glicko_surface_rating": 1820,
    "p2_glicko_surface_rd": 138,
    "h2h_matches_total": 2,
    "h2h_matches_same_surface": 1,
    "h2h_p1_wins": 1,
    "h2h_last_meeting_days_ago": 380
  },
  "outcome": null,
  "exit_price": null,
  "realized_pnl_usdc": null
}
```

Lokasyon: `logs/tennis_diagnostics/<date>.jsonl`

### 8.2 `/diagnose` CLI Komutu

```bash
python scripts/diagnose.py --period 30d --group-by surface
python scripts/diagnose.py --period 7d --group-by tier
python scripts/diagnose.py --period 30d --group-by feature
python scripts/diagnose.py --trade <uuid>  # Single trade detay
```

**Group-by surface çıktı örneği:**
```
SURFACE BAZLI PERFORMANS (son 30 gün):
  clay:    7W/12L (37%)  net -$45.00   ⚠️ DİKKAT
  hard:    8W/4L  (67%)  net +$22.00
  grass:   3W/2L  (60%)  net +$11.00
```

**Group-by feature: hangi data zayıf?**
```
KAYIP TRADE'LERDE EN SIK GÖRÜLEN ZAYIF FEATURE:
  - form_data_age > 60 gün:    %68 (15/22 kayıp)
  - surface_rating RD > 130:   %50 (11/22 kayıp)
  - H2H = 0:                    %45 (10/22 kayıp)
  - surface_count < 12:         %41 (9/22 kayıp)
```

**Trade detay:**
```
> /diagnose --trade abc-123

TRADE: atp-djere-cerund first_set_winner
PREDICTION: 0.62 BUY @ 0.55, edge +0.07, A-tier
ACTUAL: LOSS (token resolved 0.001)
ZAYIF NOKTALAR:
  ⚠️ p2 surface_count=9 (sınırda)
  ⚠️ p2 form_data_age=67 (gözlem: kötü form?)
  ✓ Genel rating sağlam
  ✓ H2H bilgi mevcut (Djere 1-0)
HİPOTEZ: Cerundolo'nun son 2 ay clay form data'sı yok (Sackmann eksik), 
          form factor yanlış değerlendirildi.
```

### 8.3 Otomatik Pattern Tespit

Haftada bir cron job: tüm trade'leri tara, hangi feature kayıplarla korelasyonlu? Output: `logs/tennis_diagnostics/weekly_pattern_report.md`.

---

## 9. Live'a Geçiş Kriteri

### 9.1 Paper Trade Aşaması (varsayılan başlangıç)

- **Süre:** 4 hafta minimum
- **Min sample:** ≥30 tamamlanmış trade
- **Accuracy hedef:** ≥%53 (Polymarket pricing'i yenmek için kritik eşik)
- Tüm trade'ler sandbox `data/positions.json`'da yaşar, paper PnL hesaplanır

### 9.2 Live Geçiş Kararı

| Paper Sonuç | Aksiyon |
|---|---|
| Accuracy ≥%53 + Net positive PnL | Live aç (küçük pozisyon başla) |
| Accuracy ≥%50, marjinal kâr | 4 hafta daha paper |
| Accuracy < %50 | **KAPAT** — `/diagnose` ile sebebi bul, model güncelle, yeniden paper |
| Net negative PnL > −$50 | Erken durdurma — diagnose |

### 9.3 Live Mode

- `config.yaml > mode: live`
- Bankroll yine $500 (tennis lab sınırı)
- Pozisyon boyutu A=$25, B=$20 (config'den)
- Otomatik kill kriterleri: net kayıp >−$100 (toplam) → otomatik paper'a döner

---

## 10. Sandbox Dashboard (Port 5051)

### 10.1 Bileşenler (ana dashboard'dan basitleştirilmiş)

- **5 özet kart:** Balance ($500 paper), Open PnL, Realized PnL, Locked, Peak
- **Loss Protection:** RISK gauge + Stop at%
- **Tier breakdown:** A trades count vs B trades count + win rate
- **Surface chart:** clay vs grass vs hard performance
- **Trades feed:** Active | Exited | Skipped (4. sekme yok — stock_queue tennis için YOK)
- **Cycle bar:** Hard cycle + Light cycle

### 10.2 Diagnostic Tab (yeni — bot 2.0'da yok)

- **By Surface** widget — clay/grass/hard W/L heatmap
- **By Tier** widget — A vs B comparison
- **Feature weakness** chart — son 7 günkü kayıplarda hangi feature en zayıf
- **Per-trade drill-down**: trade tıkla → tam diagnostic JSON

### 10.3 Kill Button (UI'da değil — manuel kontrol kabul)

UI'a kill button koymak risk → manuel komut yeterli (CLAUDE.md "executing actions with care" — destructive operations confirmation).

---

## 11. Implementation Mimarisi

### 11.1 Yeni Modüller (tennis-specific, sandbox'a özel)

```
src/
├─ domain/
│  ├─ prediction/                    ← YENİ
│  │  ├─ glicko2.py                  Pure Glicko-2 math
│  │  ├─ klaassen_magnus.py          Pure tennis probability math
│  │  ├─ tennis_predictor.py         Orchestrator (3 market dispatch)
│  │  └─ feature_extractor.py        Per-player profile builder
│  └─ matching/                      ← MEVCUT (kullanılır)
│
├─ infrastructure/
│  ├─ data/
│  │  ├─ sackmann_csv_client.py      ← YENİ (download + cache + parse)
│  │  └─ tml_csv_client.py           ← YENİ (backup)
│  └─ apis/
│     └─ gamma_client.py             ← MEVCUT (paylaşılır)
│
├─ strategy/
│  ├─ entry/
│  │  └─ tennis_entry.py             ← YENİ (3 market entry orchestrator)
│  └─ exit/
│     └─ (mevcut exit kuralları — paper mode'da basit hold to resolution + scale_out)
│
├─ orchestration/
│  ├─ tennis_diagnostic_logger.py    ← YENİ
│  └─ (mevcut agent.py paylaşılır, tennis-specific entry processor wire'lanır)
│
└─ presentation/
   └─ dashboard/
      ├─ (mevcut dashboard paylaşılır + tennis-spesifik widget'lar eklenir)
      └─ tennis_diagnostic_view.py   ← YENİ

scripts/
├─ build_tennis_ratings.py           ← YENİ (offline batch)
├─ download_sackmann.py              ← YENİ (haftalık cron)
└─ diagnose.py                       ← YENİ (CLI)

config_tennis.yaml                   ← YENİ (override config)
```

### 11.2 Paylaşılan Modüller (ana bot ile)

- `src/infrastructure/apis/gamma_client.py` (Polymarket fetch)
- `src/infrastructure/apis/clob_client.py` (price feed + execute)
- `src/orchestration/scanner.py` (genişletilir: yeni sport_market_type'lar kabul)
- `src/strategy/exit/` (scale_out + near_resolve, paper'da yeterli)
- `src/domain/risk/position_sizer.py` (sizing logic aynı)
- `src/presentation/dashboard/` (templates ortak, widget'lar eklenir)

### 11.3 Konfigürasyon — Override Pattern

`tennis-lab/config_tennis.yaml`:

```yaml
mode: paper
initial_bankroll: 500

scanner:
  allowed_sport_tags: [tennis, atp]  # Sadece tennis
  allowed_sports_market_types:       # YENİ — tennis-specific tipler
    - moneyline
    - tennis_first_set_winner
    - tennis_set_handicap
    - tennis_set_totals
  max_post_start_hours: 1.0          # Tennis live'a daha hassas

edge:
  min_edge: 0.05                     # %5
  confidence_multipliers: {A: 1.00, B: 1.00}

risk:
  confidence_bet_pct: {A: 0.05, B: 0.04}
  max_single_bet_usdc: 50
  max_bet_pct: 0.05
  max_positions_per_event: 2         # En iyi 2 edge (bizim constraint)

dashboard:
  port: 5051
  enabled: true

# YENİ tennis-specific bölüm
tennis:
  data_dir: "data/sackmann_cache"
  ratings_cache: "data/tennis_ratings.json"
  diagnostic_log_dir: "logs/tennis_diagnostics"
  confidence_tier_a:
    min_matches_12mo: 40
    min_surface_matches: 15
    min_h2h_years: 5
    max_form_age_days: 60
    max_glicko_rd: 100
  confidence_tier_b:
    min_matches_12mo: 20
    min_surface_matches: 8
    max_form_age_days: 90
    max_glicko_rd: 150
```

---

## 12. Mimari Uyumluluk (ARCHITECTURE_GUARD)

- ✅ **Kural 1 (Katman):** Tennis modülleri 5-katman mimariye uyar (domain pure, infrastructure I/O, strategy decision, orchestration glue)
- ✅ **Kural 2 (Domain I/O yok):** `glicko2.py`, `klaassen_magnus.py`, `tennis_predictor.py` saf hesap; CSV okuma `infrastructure/data/`'da
- ✅ **Kural 3 (<400 satır):** Her modül tek sorumluluk
- ✅ **Kural 6 (Magic number yok):** Tüm eşikler `config_tennis.yaml`'de
- ✅ **Kural 7 (P(YES) anchor):** Tennis için de P(YES) saklanır; direction adjustment caller'da
- ✅ **Kural 8 (Event-level guard):** max_positions_per_event=2 zaten config'de
- ✅ **Kural 11 (Test):** Her domain fonksiyonu için unit test (Glicko + Klaassen + predictor)

---

## 13. Test Stratejisi

### 13.1 Unit Tests (zorunlu, ARCH_GUARD Kural 11)

- `test_glicko2.py`: Glicko update math (against known examples)
- `test_klaassen_magnus.py`: game/set/match prob formulas (against literature values)
- `test_tennis_predictor.py`: 3 market dispatcher
- `test_feature_extractor.py`: H2H + form + RD extraction
- `test_sackmann_csv_client.py`: CSV parse + cache
- `test_tennis_entry.py`: Max 2 per event constraint
- `test_diagnostic_logger.py`: Per-trade snapshot format

**Coverage hedef:** Domain %80+, Strategy %75+ (ARCH_GUARD Kural 15)

### 13.2 Integration Tests

- End-to-end: Sackmann data → ratings build → prediction → edge → entry
- Sandbox izolasyon testi: tennis-lab değişikliği main bot dosyalarına dokunmaz

### 13.3 Backtest (gelecek)

- TML 2025 ile train, Sackmann 2026 ilk 2 ayını test → accuracy ölç
- Eğer accuracy <%50 → model güncelle baştan
- Bu paper trade öncesi sanity check

---

## 14. Riskler ve Mitigasyonlar

| Risk | Mitigasyon |
|---|---|
| Sackmann data 3 ay eski → clay sezonu eksik | Self-diagnostic surface tag'i ile gözle; V2 daily scrape |
| Glicko rating yanlış kalibre | Backtest with literature values; paper trade'de gözlem |
| Polymarket alt market low liquidity | Pozisyon $20-25 küçük; spread sanity (SPEC-M reuse) |
| Model accuracy <%50 (kâr etmez) | 4 hafta paper trade kapısı; başarısız → /diagnose + iterate |
| Sandbox kod main bot'u etkilemesi | git worktree izolasyon + ayrı state files |
| Doubles'a yanlışlıkla girer | scanner filter: `'doubles' in slug` → skip |
| WTA'ya yanlışlıkla girer | scanner filter: sadece `atp-` prefix kabul |

---

## 15. Onay Sonrası Sıralama

1. ✅ Spec doc (bu) — yazıldı, commit
2. **writing-plans skill** → `docs/superpowers/plans/2026-05-19-tennis-prediction-lab.md` (detaylı task task implementation plan)
3. **subagent-driven development skill** → task task uygulanır:
   - Sandbox setup
   - Sackmann downloader
   - Glicko-2 motor + test
   - Klaassen-Magnus motor + test
   - Predictor + test
   - Feature extractor + test
   - Scanner extension
   - Edge calculator
   - Tennis entry + max-2 constraint
   - Diagnostic logger
   - Dashboard widgets
   - Paper trade başlat
4. **Paper trade 4 hafta** → gözlem
5. **DECISIONS §B'ye SPEC-N kaydı** (implementation tamamlanınca)

---

## 16. Açık Noktalar (V2'ye Ertelenenler)

- **WTA desteği**: Sackmann WTA repo var ama Glicko-2 farklı kalibre + WTA literature ayrı (V2)
- **Doubles desteği**: Pair-level data yok (V2)
- **Live in-game prediction**: Set-by-set update (V3)
- **Daily ATP scrape**: Sackmann eski oldukça (V2)
- **Tennis-specific exit logic**: Şu an scale_out + near_resolve yeterli, ileride set_exit eklenebilir (V2)
- **Paid live API**: Maliyet/fayda Faz 2 sonu değerlendirilir
