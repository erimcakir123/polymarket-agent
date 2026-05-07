# Maç İçi Olasılık Hesaplama Modelleri — Snapshot (2026-05-04)

> **Amaç:** Bot'un maç içi p_win/p_cover/p_over hesaplama modellerini ve veri
> kaynaklarını dondurur. 2 günlük A/B test sonrası 16 Nisan baseline ile
> karşılaştırma için referans.
>
> **Kapsam:** SADECE matematiksel olasılık hesaplama. Threshold'lar, scale_out
> kuralları, exit dispatcher cascade'leri DAHIL DEĞİL — onlar p_win çıktıları
> üzerine binen ayrı bir katman.

---

## 1. NBA — Bill James Safe Lead + Poisson-based Dead Checks

**Modül:** `src/domain/math/safe_lead.py` (223 satır)

**Moneyline (`is_mathematically_dead`):**
```
deficit >= multiplier × √(clock_seconds)
```
- Bill James %99 confidence formülü
- multiplier sport-spesifik (NBA için kalibre)
- True döner → maç matematiksel ölü, comeback imkansız

**Spread (`is_spread_dead`):**
```
margin_to_cover >= 0.861 × √(seconds_remaining)
```
- multiplier 0.861 NBA spread için kalibre
- margin_to_cover = spread'i kapatmak için gereken puan farkı

**Totals (`is_total_dead`):**
```
points_needed >= 1.218 × √(seconds_remaining)   (over için)
-points_needed >= 1.218 × √(seconds_remaining)  (under için)
```
- multiplier 1.218 = 0.861 × √2 (toplam variance daha yüksek)

**Comeback rate (predictive exit için):**
- `ML_SCORE_DIFF_STD_PER_SQRT_SEC = 0.3727` (skor farkı σ/√sn)
- `TOTALS_STD_PER_SQRT_SEC = 0.5270` (toplam σ/√sn)
- Normal CDF üzerinden P(comeback) hesaplanır

**Veri:** ✗ statik tablo yok, salt analitik formül.

---

## 2. NHL — Skellam (Poisson) + Empirical Tablo Lookup

### Empirical (öncelikli) — `src/domain/math/nhl_empirical_wp.py`
**MoneyPuck 2022-25 veri tabanından lookup:**
- Key: `{period}_{abs_score_diff}_{seconds_bucket}`
- Bucket size: 60 sn
- Min sample size: 30 maç (yetersizse None döner → Skellam fallback)
- Tablolar:
  - `data/nhl_empirical_win_table.json` (2,577 satır, p_win)
  - `data/nhl_empirical_puck_line_table.json` (6,330 satır, p_cover)
  - `data/nhl_empirical_totals_table.json` (11,585 satır, p_over)
  - **Toplam: 20,492 bucket cell**

### Theoretical fallback — `src/domain/math/nhl_skellam.py`
**Skellam dağılımı (iki Poisson farkı):**
```
K = (trailing_goals - leading_goals) ~ Skellam(μ, μ)
μ = λ × seconds_remaining
P(comeback) = P(K >= deficit + 1) + 0.5 × P(K == deficit)
```
- `NHL_REGULATION_LAMBDA_PER_SEC = 0.000853` (5v5, gol/sn)
- `NHL_OT_3V3_LAMBDA_PER_SEC = 0.001400` (OT 3v3, ~1.65× regulation)
- OT/SO 50/50 (talent modellenmemiş v1)
- Symmetric lambda (talent yok, empirical bunu compense eder)

### Diğer NHL modülleri
- `nhl_puck_line.py`, `nhl_puck_line_probability.py` (53+58 satır) — spread cover Skellam
- `nhl_totals.py`, `nhl_totals_probability.py` (44+52 satır) — over/under Skellam
- `nhl_win_probability.py` (79 satır) — empirical+fallback orchestrator

**Referanslar:** Buttrey/Washburn/Price (2011) "Estimating NHL Scoring Rates", Hockey Analytics Poisson Toolbox (2006)

---

## 3. MLB — Pythagorean + log5 + Pitcher ERA + Skellam

### Pythagorean (sezon win expectancy) — `src/domain/math/mlb_pythagoras.py`
```
winpct = RS^1.83 / (RS^1.83 + RA^1.83)
```
- Bill James + Steven Miller (2007) — 1.83 exponent MLB için validated
- "PythagenPat" baseline (±4 wins/162 oyun ortalama sapma)

### log5 (head-to-head) — `src/domain/math/mlb_log5.py`
```
P(A beats B) = (p_a - p_a × p_b) / (p_a + p_b - 2 × p_a × p_b)
```
- Bill James log5 (= Bradley-Terry equivalent)
- 200,000+ MLB game SABR doğrulaması
- Inputs clamp: [0.01, 0.99]

### Pitcher ERA adjustment — `src/domain/math/mlb_pitcher_adjustment.py`
```
pitcher_factor = league_avg_era / pitcher_era    (clamp 0.6-1.6)
adjusted_winpct = base_winpct + (pitcher_factor - 1.0) × 0.35
```
- `LEAGUE_AVG_ERA = 4.20` (2020-2024 MLB ortalama)
- `PITCHER_WEIGHT = 0.35` (~%35 oyun sonucu starter'a atfedilir)
- Final clamp: [0.05, 0.95]

**Pipeline:** Pythagorean → pitcher adjustment → log5 → matchup_winpct

### Run Line — `src/domain/math/mlb_run_line_probability.py`
```
M = home_runs - away_runs ~ Skellam(λ_home, λ_away)
P(cover -1.5 fav) = P(M >= 2) = 1 - CDF(1)
P(cover +1.5 dog) = P(M >= -1) = 1 - CDF(-2)
```
- `AVG_RUNS_PER_GAME_TEAM = 4.50` (2020-2024 league avg)
- λ floor: 0.5

### Totals — `src/domain/math/mlb_totals_probability.py`
- Skellam tabanlı (iki Poisson toplamı)
- Park factor + weather run bias dahil
- Bullpen ERA ek factor (mevcut: home_starter_era + home_bullpen_era ayrı)

### Win Expectancy — `src/domain/math/mlb_win_expectancy.py`
- In-game p_win lookup (inning + score state)

**Veri:** ✗ statik tablo yok, salt analitik formül + canlı pitcher/season verisi

---

## 4. Tennis — Klaassen-Magnus + O'Malley Closed-Form Chain

**Modül:** `src/domain/math/tennis_magnus.py` (199 satır)

### Game probability (Newton-Keller closed-form)
```
G(p) = p⁴ × (1 + 4q + 10q² + 20q³ × p / (p² + q²))
where q = 1 - p
```
- 4-0, 4-1, 4-2 paths + deuce geometric sum
- Verified: G(0.5) = 0.5
- Edge cases: p=0 → 0, p=1 → 1

### Set probability (`p_set`)
- O'Malley (2008) standard formülasyonu
- Tüm kazanma yollarını enumerate
- Alternating serve, A serves first

### Match probability (BO3 / BO5)
- `MatchState`: sets_won_a/b, games_a/b, server_is_a, format
- BO3: tam destek (Phase 1)
- BO5: stub (Phase 2)

**Surface adjustment:**
- Grass / hard / clay
- ATP serve_pct: {grass: 1.0, hard: 1.0, clay: 0.92}
- WTA serve_pct: {grass: 1.0, hard: 1.05, clay: 0.95}

**Bayesian + momentum:**
- `bayesian_max_shift: 0.15` — prior'dan max sapma
- `momentum_decay: 0.85`
- `momentum_window_games: 7` — son N oyun

**Referanslar:**
- O'Malley (2008) "Probability of Winning at Tennis I"
- Newton & Keller (2005) "Probability formulas in tennis"
- Klaassen & Magnus (2003) "Forecasting the winner"

**Veri:** Sackmann historical CSV (player ranking + match outcomes)

---

## 5. Veri Dosyaları (Statik) — Detay

| Dosya | Satır | Format | Kullanım |
|---|---|---|---|
| `data/nhl_empirical_win_table.json` | 2,577 | `{"period_diff_seconds": {"p_win": float, "n_games": int}}` | NHL ML p_win lookup |
| `data/nhl_empirical_puck_line_table.json` | 6,330 | Aynı | NHL spread p_cover |
| `data/nhl_empirical_totals_table.json` | 11,585 | Aynı | NHL over p_over |
| `data/sackmann_cache/atp_matches_2023.csv` | (CSV) | Jeff Sackmann tennis_atp repo | Tennis player history |
| `data/sackmann_cache/atp_matches_2024.csv` | (CSV) | Aynı | Tennis player history |
| `data/sackmann_cache/atp_players.csv` | (CSV) | Player metadata + ranking | Tennis player lookup |
| `data/tennis_player_xref.json` | — | Polymarket name → Sackmann ID | Eşleştirme |

**Yok (formül kullanılır):**
- NBA empirical table — Bill James %99 + Poisson CDF (analitik)
- MLB empirical table — Pythagorean + log5 + Skellam (analitik)
- WTA Sackmann CSV — yerel cache yok, ATP'ye benzer logic + canlı rank API

---

## 6. Canlı Veri Kaynakları (model girdileri)

| Kaynak | Modül | Sport | Ne için |
|---|---|---|---|
| **ESPN scoreboard** | `espn_client.py`, `score_client.py` | NBA/NHL/MLB/Tennis | Anlık skor, period, clock, set/game |
| **MLB Stats API** | `mlb_stats_client.py` | MLB | Pitcher confirm, season ERA, RS/RA, bullpen |
| **OpenWeather** | `openweather_client.py` | MLB | Rain forecast (game time + venue) → run bias |
| **Sackmann** | `sackmann_client.py` | Tennis | Player ranking + son N maç performans |
| **ESPN injuries** | `espn_injury_client.py` | NBA | (Entry edge için, in-game model'da yok) |

**NHL empirical table:** offline yüklenir startup'ta (no live data needed); fallback Skellam analitik.

---

## 7. Hesaplama Akışı (her sport için)

```
[Light cycle her 5 sn — açık pozisyon]
  ↓
ESPN'den skor çek (period, clock, score)
  ↓
Sport-spesifik p_win/p_cover/p_over hesapla:
  ├─ NBA → safe_lead.py (CDF + Poisson, formül)
  ├─ NHL → empirical_wp.py table lookup (yetersizse skellam.py fallback)
  ├─ MLB → pythagoras → pitcher_adj → log5 → skellam (run_line/totals)
  └─ Tennis → magnus.py (Newton-Keller game → O'Malley set → match chain)
  ↓
Sonuç p_win [0, 1] aralığında
  ↓
[Bu noktadan sonra exit kuralları (snapshot dışı) p_win'i kullanarak karar verir]
```

---

## 8. A/B Test Karşılaştırması (2026-05-06 sonu)

**Mevcut (snapshot tarihi):** Yukarıdaki 4 sport modeli aktif.

**16 Nisan baseline:** O zamanki commit'lerde aynı modellerin daha basit/farklı versiyonları (örn. NHL sadece Skellam, MLB sadece Pythagorean, MLB pitcher adjustment yoktu, Magnus modeli daha basit Bayesian'sızdı, NBA safe_lead vardı).

**2 gün test sonrası karşılaştır:**
- Sport bazlı win rate (NBA, NHL, MLB, Tennis)
- Model fair price kalibrasyonu (P=0.65 dediğinde gerçek WR ne)
- Empirical vs analitik fallback dağılımı (NHL)
- Pitcher adjustment etkisi (MLB ile/sız simulasyonu — counterfactual log)

**Karar:**
- Mevcut sonuç ≥ baseline → mevcut sistemde devam
- Mevcut sonuç < baseline → 16 Nisan'a rollback + iyi modelleri migrate (örn. NHL empirical tablosu, MLB pitcher adjustment)
