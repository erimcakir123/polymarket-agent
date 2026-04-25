# DECISIONS.md
> Kalibrasyon değerleri, threshold'lar ve "neden bu sayı" notları.
> Kod ne yaptığını anlatır. Bu dosya neden öyle yapıldığını anlatır.
> Her threshold değişikliğinde bu dosya da güncellenir (CLAUDE.md drift tablosu).

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
- Lossy reentry multiplier = ×0.80
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
- Team ID resolution: currently stubbed (both IDs = "") pending MarketData enrichment. Injury checks operate in degraded mode: B2B skipped; all injuries treated as opponent injuries. TODO: resolve ESPN team IDs from Odds API event matching.
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
