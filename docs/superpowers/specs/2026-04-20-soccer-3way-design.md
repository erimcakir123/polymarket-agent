# SPEC-015: Soccer 3-Way Market Support

> **Durum**: IMPLEMENTED (2026-04-20)
> **Tarih**: 2026-04-20
> **Kapsam**: Soccer + diğer 3-way branşlar (Rugby/AFL/Handball) için aynı kod altyapısı

---

## 1. Problem

Mevcut bot 2-way (binary) sporlar için tasarlandı: MLB, NBA, NHL, Tennis, Cricket. Polymarket'in en yüksek hacimli market'i soccer ama 3-way structure (Home/Draw/Away) → şu an scanner'da "end in a draw" filter ile bloklu.

Trade hacmi düşüklüğü stabilizasyonu engelliyor (gece saatleri 0-2 trade). Soccer açılırsa günde 30-50 trade hedefi mümkün.

## 2. 3-Way Market Mantığı

### Polymarket Yapısı
- Aynı maç için **3 ayrı binary market** açılır:
  - "Will {Home} win?"
  - "Will the match end in a draw?"
  - "Will {Away} win?"
- 3'ü aynı `event_id` paylaşır
- 3 market'in `yes_price` toplamı ≈ 1.0 (juice ±%5)

### Odds API
- Soccer h2h endpoint 3-way probability döner: P(Home) + P(Draw) + P(Away) = 1.0
- Sharp bookmaker'lar (Pinnacle, Betfair Exchange) bol coverage

## 3. Direction Selection

**Felsefe**: Bot, bookmaker'a göre **kazanması en muhtemel** outcome'a girer (favori).

### Algoritma
1. 3 outcome arasında **bookmaker probability'si en yüksek** olanı seç
2. Eşitlik durumunda → SKIP (tie-break: `argmax` belirsiz)
3. Seçili outcome için filter kontrol et (madde 4)

## 4. Favorite Filter

İki şart birlikte sağlanmalı:

```
favorite_prob >= 0.40                              (absolute threshold)
AND
favorite_prob - second_highest_prob >= 0.07        (relative margin)
```

### Örnek
| Senaryo | Home | Draw | Away | Sonuç |
|---|---|---|---|---|
| Açık favori | 45% | 27% | 28% | ENTER (Ev — fark 17pp) |
| Hafif favori | 42% | 28% | 30% | ENTER (Ev — fark 12pp) |
| Sınırda | 41% | 30% | 29% | ENTER (Ev — fark 11pp) |
| Tossup | 40% | 32% | 28% | SKIP (margin 8pp ama threshold 7pp ✓) → ENTER |
| Çok dengeli | 38% | 30% | 32% | SKIP (40% altı) |
| Noise | 40.5% | 39.5% | 20% | SKIP (margin 1pp) |

### Kalibrasyon Notu
- 2-way'deki %52'nin 3-way karşılığı (uniform 33%, %40 = hafif favori)
- 7pp margin "noise tossup'ları" eler
- 100+ resolved soccer trade sonra calibration report ile re-evaluate

## 5. Edge Threshold

**%6 unified** (mevcut sistem ile aynı). Confidence multiplier A=B=1.00.

Edge hesabı: `bookmaker_prob - polymarket_yes_price` (3 outcome ayrı ayrı, en yüksek edge'li olan değil — favoriye sabit).

## 6. Sum Filter (3-Way Detection)

3 market'in `yes_price` toplamı 0.95-1.05 dışındaysa → **bu gerçek 1X2 değil** (double chance / handicap / başka prop) → SKIP.

```
total = home_yes_price + draw_yes_price + away_yes_price
if not (0.95 <= total <= 1.05):
    skip(reason="not_three_way_h2h")
```

## 7. Event-Level Guard

3 market aynı `event_id` paylaşır. Bot:
- 1 outcome'a girdikten sonra **diğer 2'sine kapalı** (mevcut event_guard genişler)
- 1 maç = 1 pozisyon kuralı korunur

## 8. Score-Based Exit (65'+ kuralı)

### HOME / AWAY pozisyon
| Dakika | Durum | Aksiyon |
|---|---|---|
| 0-65' | Herhangi | **HOLD** (comeback rate ~20-30% — vazgeçme) |
| 65'+ | 2 gol geride | EXIT |
| 75'+ | 1 gol geride | EXIT |

### DRAW pozisyon
| Dakika | Durum | Aksiyon |
|---|---|---|
| 0-70' | 0-0 | **HOLD** (draw değeri zirvede) |
| 75'+ | Herhangi gol atıldı | EXIT |
| Knockout maçında 90+stoppage | Draw pozisyonu | AUTO-EXIT (uzatma+pen draw'ı bitirir) |

### Mevcut Exit Kurallarıyla Etkileşim
- **Flat SL** mevcut kuralları geçerli (entry < 60¢ A-conf değilse)
- **A-conf hold**: entry ≥ 60¢ + A-conf → flat SL muaf, sadece score exit + scale-out + market_flip
- **Scale-out** (midpoint) aynen geçerli
- **Near-resolve** (94¢) aynen geçerli

### NOT — Kaldırılan Kurallar
- ~~Red card özel exit~~ → ESPN reliability belirsiz, score-based 65'+ rule yeterli
- ~~Price emergency -%25~~ → goller zaten market flip yaratır, score exit yakalar; çift kural gereksiz

## 9. Excluded Competitions

Sport config'te `excluded_competitions` listesi:
```yaml
soccer:
  excluded_competitions:
    - "International Friendly"
    - "Club Friendly"
    - "Preseason"
    - "Testimonial"
```

Polymarket competition tag'inden filter edilir. Friendly/preseason maçları edge reliability düşük (takımlar ciddi oynamaz).

## 10. Sport Config Pattern (DRY)

Tüm 3-way branşları aynı kod paylaşır, sadece config farklı:

```python
# src/config/sport_configs/soccer.py
SOCCER_CONFIG = {
    "regulation_minutes": 90,
    "stoppage_buffer": 6,          # ~4-6 dk ortalama
    "score_exit_first_half_lock": 65,    # < 65' HOLD
    "score_exit_2goal_minute": 65,
    "score_exit_1goal_minute": 75,
    "draw_protect_until": 70,
    "draw_exit_after_goal": 75,
    "knockout_auto_exit_draw": True,
    "excluded_competitions": ["International Friendly", "Preseason", ...],
}

# src/config/sport_configs/rugby_union.py
RUGBY_CONFIG = {
    "regulation_minutes": 80,
    "stoppage_buffer": 3,
    # Rugby gol farkı yerine puan farkı (deficit ≥ 10)
    ...
}
```

Score exit logic generic — minute + deficit + position type (home/away/draw) → karar. Sport config parametreleri sağlar.

## 11. Live Direction Switch

**YOK** — pozisyon açıldıktan sonra outcome değiştirme yapılmaz (Ev → Draw geçiş yok). Sebep:
- Slippage + fee × 2
- State management 3x karmaşık
- Bug yüzeyi büyük

İleride SPEC-016 olabilir, şimdi değil.

## 12. Underdog/Draw Value Bet

**YOK** — sadece favori tarafa girilir. Polymarket'te draw bahsi nadir under-priced olur ama:
- Edge reliability düşük
- Varyans yüksek
- Disiplin için: 100+ favorite trade ROI kanıtlandıktan sonra ayrı SPEC (SPEC-017)

## 13. Resolution Rules Verify (GO-LIVE BLOCKER)

Polymarket'te knockout (cup) maçları için resolution kuralı **manuel doğrulama gerekli**:

- "Home win" market 90 dk + uzatma + penaltı sonrası mı çözer?
- Yoksa sadece regulation time mı?

**Yanlış varsayım = yanlış edge hesabı**. Implementation öncesi bir Polymarket cup market örneği incelenip resolution criteria okunmalı.

Tahminen: **Polymarket "extra time + penalty dahil"** (sportsbook standardı) — ama verify edilmeli.

## 14. ESPN Soccer Diag

Cricket'teki yaklaşımla tutarlı: Implementation öncesi ESPN soccer endpoint'ini incele:

`scripts/diag_soccer_espn.py`:
- `https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard`
- Skor verir mi? (büyük ihtimalle evet)
- Dakika verir mi? `status.displayClock` formatı? ("45+2'", "67'")
- Stoppage time `regulation_ended` flag'i var mı?
- Match window: pre/in/post detection?

Diag çıktısına göre `_parse_competition` soccer için inning benzeri bir field çıkarır.

## 15. Observability

Her 3-way entry için detaylı log:
```
[soccer-entry] event_id=X
  outcomes: home=0.45 / draw=0.27 / away=0.28
  selected: home (favorite, margin 17pp)
  edge: 0.08 (yes_price 0.37)
  confidence: A
  competition: EPL
```

Live debug için kritik. Skip kararları da log'lanmalı (favorite_filter_failed, sum_filter_failed, vs.).

## 16. Credit Budget Monitoring

Soccer 60+ lig açılınca Odds API yükü artar. Mevcut bot ~500 credit/gün, soccer sonrası 1500-2500/gün tahmin.

**Hard cap**: Günlük 600 credit limiti (config'den ayarlanır). Aşılırsa:
1. Tier-2 ligleri otomatik pause (sadece tier-1 polled)
2. Telegram alarm
3. Sonraki gün reset

Mevcut JIT mantığı (sadece stock'taki sport_key'leri poll et) zaten optimization yapıyor — gerçek kullanım tahminden düşük olabilir.

## 17. Kapsam — Tüm Ligler

TODO-001'deki 60+ lig listesinin tamamı açılır:
- Tier-1: EPL, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa, Conference
- Tier-2: MLS, Süper Lig, Eredivisie, Primeira Liga, Brasileirão, Liga MX, Argentine, Türkiye Kupası
- Tier-3: Smaller European/Asian leagues

Tüm ligler aynı kod, aynı config (sadece `excluded_competitions` farklılaşabilir gelecekte).

**Pilot dönem yok** — credit monitoring guardrail var, post-launch günlük takip yapılır.

## 18. Diğer 3-Way Branşları

Aynı kod base ile aktive edilir:
- **Rugby Union** (Six Nations, Premiership, URC, Top 14)
- **Rugby League** (NRL)
- **AFL** (nadir berabere ama 3-way structure)
- **Handball** (Bundesliga Handball + Avrupa Şampiyonası)

Sport config'leri ayrı oluşturulur, mantık paylaşılır.

## 19. Etkilenen Dosyalar

### Yeni
- `src/orchestration/event_grouper.py` — 3 market'i event_id ile grupla
- `src/strategy/entry/three_way_entry.py` — 3-way direction selection + favorite filter + edge
- `src/strategy/exit/soccer_score_exit.py` — soccer score exit (DRAW + HOME/AWAY)
- `src/config/sport_configs/__init__.py` + `soccer.py` + `rugby_union.py` + ...
- `tests/unit/orchestration/test_event_grouper.py`
- `tests/unit/strategy/entry/test_three_way_entry.py`
- `tests/unit/strategy/exit/test_soccer_score_exit.py`
- `scripts/diag_soccer_espn.py`

### Modify
- `src/orchestration/scanner.py` — sum filter (0.95-1.05) entegrasyonu
- `src/strategy/entry/gate.py` — 3-way path için three_way_entry çağrısı
- `src/strategy/exit/monitor.py` — soccer score exit dispatch
- `src/orchestration/score_enricher.py` — soccer için ESPN endpoint
- `src/infrastructure/apis/espn_client.py` — soccer minute parse
- `src/config/settings.py` — credit_budget_daily field
- `src/config/sport_rules.py` — soccer/rugby/AFL/handball entries
- `config.yaml` — soccer + rugby + AFL + handball blokları
- `TDD.md` §6.4, §7 — 3-way logic + soccer/rugby
- `PRD.md` — F12 (3-way market support)

### Dokunulmaz
- `ARCHITECTURE_GUARD.md` — yapısal invariant değişmiyor
- `TODO.md` — TODO-001 (Soccer) → IMPLEMENTED, çıkarılır

## 20. Implementation Tasks (Plan)

Subagent-driven plan ayrı dosya: `docs/superpowers/plans/2026-04-20-soccer-3way.md`

Phase'ler:
1. Diag (ESPN soccer) + resolution rules verify
2. EventGrouper + sum filter (mimari)
3. ThreeWayEntry strategy (direction + favorite filter + edge)
4. Soccer score exit (DRAW + HOME/AWAY rules)
5. Sport config pattern (soccer + rugby + AFL + handball)
6. Credit monitoring + observability log
7. TDD/PRD update + go-live checklist

Tahmini süre: **5-6 gün**

## 21. Go-Live Checklist

- [ ] Diag confirmed (ESPN minute format, status fields)
- [ ] Resolution rules verified (knockout extra time + pen?)
- [ ] All tests passing (922 + ~50 yeni soccer tests)
- [ ] ARCH_GUARD self-check her commit'te
- [ ] PRD F12 + TDD §6.4/§7 güncel
- [ ] Credit monitor live (600/gün hard cap)
- [ ] Observability log konfigüre
- [ ] Dry_run test 24 saat (ilk 24 saat live trade yok, log'a bak)

## 22. Risk Notları

- **Comeback rate tahminleri kabaca**: 75'+ 1 gol geride %10-15 comeback. Live Pinnacle data eklendiğinde re-evaluate.
- **Home/away simetrik kural**: ev sahibi avantajı asimetri ihmal ediliyor. 100 trade sonra calibration.
- **Excluded competitions liste eksik olabilir**: ilk dönem unforeseen friendly tipleri girebilir, monitor.
- **ESPN soccer reliability**: red card data yoksa price emergency yokluğu hissedilebilir, monitor.

---

## Implementation Commits

- Task 1 (diag ESPN soccer): committed
- Task 2 (ESPN parse minute+state): `8020532`
- Task 3 (sum filter scanner): `8a032a7`
- Task 4 (EventGrouper): `79b4a64`
- Task 5 (ThreeWayEntry): `5fe1d07`
- Task 6 (Sport configs DRY): `260a06c`
- Task 7 (Soccer score exit): `8308bb3`
- Task 8a (soccer_score_builder): `397b77e`
- Task 8b-monitor (soccer dispatch): `b17606a`
- Task 8b-gate/scanner (3-way dispatch): `09f92b3`
- Task 9 (Credit hard cap): `d46974c`
- Task 10 (Observability log): `fd95bfb`
- Task 11 (Config enable 60+ lig): `6e8a8d0`

**Tests**: 987 passed, 2 skipped (integration manual)
**ARCH_GUARD**: All files <400 lines (score_enricher.py at exact 400 — tight)
