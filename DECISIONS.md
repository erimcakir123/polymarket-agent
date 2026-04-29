# DECISIONS.md
> Kalibrasyon değerleri, threshold'lar ve "neden bu sayı" notları.
> Kod ne yaptığını anlatır. Bu dosya neden öyle yapıldığını anlatır.
> Her threshold değişikliğinde bu dosya da güncellenir (CLAUDE.md drift tablosu).

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
| 3 | MATEMATICAL_DEATH | sets 0-2 (BO3) / 0-3 (BO5) | SELL_ALL |
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
MATEMATICAL_DEATH (now triggered at 0-3 sets) still active. Phase 2 adds
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
- **MATEMATICAL_DEATH SELL_ALL:** 0-2 BO3 / 0-3 BO5 = literally cannot win → no
  reason to hold for residual bid. Liquidity exit while market still has bid.
