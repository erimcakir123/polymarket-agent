# Basketball Model Foundation — Tasarım Belgesi

> **Faz 1 / 3** — NBA + WNBA temel altyapısı.
> Tarih: 2026-06-01
> Sonraki fazlar: Faz 2 (NCAAB + WNCAAB), Faz 3 (Euroleague).

---

## 1. Amaç ve Bağlam

Polymarket basketbol marketleri için **bookmaker'sız**, **Polymarket fiyatına edge** atan tahmin modeli kurulur. Mevcut tenis Sackmann-modeli ile birebir aynı paradigma uygulanır.

### Tenis Pattern'inin Kanıtı (referans)

[src/strategy/enrichment/tennis_anchor_enricher.py:1-3](src/strategy/enrichment/tennis_anchor_enricher.py#L1-L3) dosya başlığı net söylüyor:

> "Sport_tag tennis ise odds_enricher (bookmaker h2h) **yerine** bu modül çağrılır."

[src/strategy/entry/gate.py:218](src/strategy/entry/gate.py#L218) edge hesabı:

```
edge_raw = abs(bm_prob.probability - market.yes_price)
```

Tenisin `bm_prob.probability` zaten model çıktısı (sarmal). `market.yes_price` = Polymarket fiyatı. **Bookmaker veriye dokunulmaz.** Aynı paradigmayı basket için kuruyoruz.

### Faz 1 Kapsamı

| Lig | Kapsamda mı? | Veri kaynağı | Not |
|---|---|---|---|
| NBA | ✅ Kesin | `nba_api` (birincil) + ESPN (yedek) | Veri en zengin |
| WNBA | ⚠️ Veri doğrulamalı | `nba_api` (kapsam belirsiz) | Faz 1 başında 1 sezon tarama; kalite ≥%65 doğruluk → kapsamda kal, altında → bahisçi konsensüsünde kal |
| NCAAB / WNCAAB / Euroleague | ❌ Faz 2-3 | — | Bu spec dışında |
| NBL | ❌ Kapsam dışı | Python paketi yok | Bahisçi konsensüsünde kalır |

CBB = NCAAB aynı lig (Polymarket "cbb" kısaltması). Whitelist'te ikisi de varsa Faz 1'in başında biri temizlenir.

---

## 2. Mimari — 5 Katman Eşleşmesi

```
src/
  presentation/   (dashboard panelinde basket bölümü güncellenmez — değişiklik yok)
  orchestration/
    factory.py    (+) Basketball refresh hook (sport_tag basketball ise tetikle)
    scanner.py    (—) değişiklik yok (mevcut whitelist filtresi yeter)
  strategy/
    enrichment/
      basketball_anchor_enricher.py     ★ YENİ (tennis_anchor_enricher kopya pattern)
      basketball_model_anchor.py        ★ YENİ (tennis_model_anchor kopya pattern)
      basketball_dispatch.py            ★ YENİ (market type → pricer dispatch)
    entry/
      gate.py     (—) değişiklik yok (model_anchor → BookmakerProbability sarmalı kullanılır)
  domain/
    pricing/
      basketball/
        team_elo.py            ★ YENİ — Glicko muadili (takım rating)
        pace_efficiency.py     ★ YENİ — Markov muadili (closed-form total sim)
        efficiency_metrics.py  ★ YENİ — KenPom-tarzı AdjO/AdjD hesabı
        game_record.py         ★ YENİ — Maç kayıt dataclass'ı
        match_pricer.py        ★ YENİ — Blend(elo, pace_eff) → P(YES)
        calibration.py         ★ YENİ — Tarihsel kalibrasyon eğrisi (Faz 1 sonrası)
    matching/
      basketball_team_resolver.py  ★ YENİ — Polymarket slug ↔ NBA team ID
  infrastructure/
    data/
      basketball/
        nba_api_refresher.py        ★ YENİ — Birincil kaynak (NBA + WNBA)
        espn_pbp_refresher.py       ★ YENİ — Yedek kaynak
        team_ratings_store.py       ★ YENİ — Elo + AdjO/AdjD JSON cache
        data_source_health.py       ★ YENİ — Kaynak sağlık takibi
        schema_validator.py         ★ YENİ — Pydantic ile format değişiklik yakalama
  config/
    sport_rules.py  (+) basketball lig override
  models/
    enums.py        (—) SportsMarketType genişletmesi yok (mevcut MONEYLINE/SPREADS/TOTALS yeterli)
```

**Yeni soyutlama yok.** Tüm pattern tenisten kopya. Tek dosya max 400 satır kuralı her dosya için.

---

## 3. Veri Pipeline ve Güncelleme Stratejisi

### Çift-Kaynak Redundancy

Her lig için **birincil + yedek**. Birincil çökünce otomatik yedeğe düş.

| Lig | Birincil | Yedek | Yedeğe geçiş tetiği |
|---|---|---|---|
| NBA | `nba_api` (stats.nba.com) | ESPN (`hoopR-py`) | birincil 3 ardışık başarısızlık → 15 dk |
| WNBA | `nba_api` | ESPN (`hoopR-py`) | aynı |

### Güncelleme Tetikleyicileri (3 Katmanlı)

| Tetik | Sıklık | Kapsam | Amaç |
|---|---|---|---|
| **Bot başlangıçta** | 1x | Tam refresh (tüm lig × tarihsel veri delta) | Tenis Sackmann pattern muadili |
| **Maç-pencere farkındalıklı** | 5 dk (maç sırasında veya son maç bitimi sonrası 60 dk içinde) / 6 saat (boş pencere) | Son N saat biten maçlar + Elo/AdjO/AdjD incremental update | Veri tazeliği |
| **Sağlık kontrolü** | 15 dk | Her kaynak ping + son başarılı çağrı timestamp | Kaynak çökmesi alarmı + yedeğe geçiş |

### Schema Drift Koruması

Her kaynak çıktısı Pydantic modeliyle doğrulanır. Kolon adı değişirse fail-fast → log + alarm + yedeğe geç. Sessiz kabul yok (ARCH_GUARD §12).

### Cache Yapısı

```
data/basketball_cache/
  nba/
    games_{season}.csv         (raw — atomic write tmp → rename)
    ratings_elo.json           (incremental — son güncelleme timestamp ile)
    efficiency_{season}.json   (AdjO/AdjD per team)
  wnba/
    (aynı yapı)
  _health/
    sources_status.json        (her kaynak: last_success, last_fail, fail_count)
```

---

## 4. Model Katmanı — Bilim

### Team Elo (Glicko muadili)

Klasik Elo + ev sahibi avantajı. NBA için lig-spesifik `home_advantage` ve `k_factor` config'den okunur. K-factor şu kurallarla:

- Sezon başında yüksek (rating volatilite),
- Sezon ortasında düşük (stabilize),
- Playoff'larda tekrar yüksek (rotasyon farklı).

Çıktı: `P(team_A_wins_moneyline)`.

### Pace × Efficiency (Markov muadili)

KenPom formülü:

```
proj_pace = (team_A_pace + team_B_pace) / 2
proj_score_A = proj_pace × (team_A_AdjO + team_B_AdjD) / 200
proj_score_B = proj_pace × (team_B_AdjO + team_A_AdjD) / 200
proj_total = proj_score_A + proj_score_B
```

Çıktı: `P(over_total_X)`, `P(spread_A_covers_Y)` türevleri.

### Blend (model_anchor)

`match_pricer.py` market_type'a göre Elo + Pace×Efficiency harmanı yapar:

- Moneyline → `blend_elo * P_elo + (1 - blend_elo) * P_pace_eff_implied_moneyline`
- Totals → ağırlık tamamen pace_efficiency (Elo totals'a göre zayıf sinyal)
- Spread → ağırlık pace_efficiency + Elo margin yorumu

Lig başına `blend_elo` config'de ayrı. Magic number yasak (ARCH_GUARD §6).

### Confidence Sarmalı

Tenis pattern'i birebir:
```
_MODEL_EQUIV_BOOKMAKERS = 5.0
_MODEL_HAS_SHARP = True
```
Confidence grading mevcut `calculate_bookmaker_probability` ile uyumlu → A confidence, canlı trade aktif. Faz 1 sonrası kalibrasyon eğrisiyle revize.

---

## 5. Strateji Entegrasyon

`factory.py` build_deps'te sport_tag dispatcher genişletilir:

```
if sport_tag in TENNIS_TAGS:
    enricher = tennis_anchor_enricher
elif sport_tag in BASKETBALL_TAGS:        # ★ YENİ DALLAMA
    enricher = basketball_anchor_enricher
else:
    enricher = odds_enricher                # mevcut bookmaker
```

`basketball_anchor_enricher` tennis_anchor_enricher'ın paralel kopyası:
1. Takım rating lookup (`team_ratings_store`)
2. Eksik takım veya eksik veri → `EnrichFailReason.MODEL_TEAM_NOT_IN_RATINGS`
3. `basketball_model_anchor.compute` → `model_p`
4. Kalibrasyon eğrisi varsa uygula
5. `calculate_bookmaker_probability(model_p, num=5, has_sharp=True, source="model")` sarmalı
6. `EnrichResult` döndür

**Entry gate dokunulmaz.** Sarmal sayesinde mevcut consensus/early/normal stratejileri otomatik çalışır.

---

## 6. Risk ve Fallback

### Graceful Degradation

| Senaryo | Davranış |
|---|---|
| Birincil + yedek kaynak ikisi de çöker | Lig için model None → bot otomatik bahisçi konsensüsüne düşer (mevcut odds_enricher) |
| Takım rating cache bozulur | Atomic write garantisi (tmp → rename) — partial dosya görülmez |
| Bilinmeyen takım slug | `EnrichFailReason` ile skip — log'a "team_not_in_ratings" |
| Schema drift (kolon değişir) | Pydantic validation fail-fast → log error + dashboard alarm |
| Model `model_p` üretemez | Bahisçi konsensüsüne düş (degrade — block değil) |

### Sessiz Hata Yasağı

ARCH_GUARD §12: Bare `except: pass` YOK. Her hata loglanır + degrade yolu net.

### WNBA Veri Doğrulama Adımı

Faz 1'in **ilk planında** (Plan 1.A) WNBA için "veri kalitesi spike testi" yapılır:
1. Son 1 sezon WNBA maçları `nba_api` üzerinden çekilir
2. Maç sayısı, kolon dolgunluğu, takım kapsamı kontrol edilir
3. Eşik: ≥%90 maç kapsamı + tüm takımlar bulunmalı
4. Geçerse → WNBA Faz 1 kapsamında kalır
5. Geçmezse → WNBA kapsam dışı bırakılır, sonraki faza ertelenir (TODO.md)

---

## 7. Test Stratejisi

ARCH_GUARD §11 + §15 uyumlu:

| Katman | Hedef coverage | Test türü |
|---|---|---|
| Domain (`pricing/basketball/`) | %80+ | Unit (saf fonksiyonlar — Elo, Pace×Eff, blend) |
| Strategy (`enrichment/`) | %75+ | Unit + mocked input (model_p hesabı, fail_reason yolları) |
| Orchestration (`factory.py` dispatcher) | %60+ | Integration (sport_tag → enricher seçimi) |
| Infrastructure (`data/basketball/`) | %50+ | Mock HTTP + atomic write doğrulaması |

### Kritik Test Senaryoları

- `test_elo_update_home_advantage_applied`
- `test_pace_efficiency_total_projection_matches_kenpom_example`
- `test_basketball_enricher_returns_a_confidence_with_complete_data`
- `test_basketball_enricher_returns_fail_reason_when_team_missing`
- `test_data_source_health_falls_back_to_secondary_after_3_failures`
- `test_schema_validator_detects_kolumn_change`
- `test_atomic_write_no_partial_file_on_interrupt`

### Backtest Doğrulama (Faz 1 sonu)

Son 1 NBA sezonu için:
1. Her gün modelle P(YES) üret
2. Polymarket fiyatına karşı kağıt-edge hesapla
3. Brier score + doğruluk oranı raporu
4. Hedef: ≥%66 moneyline doğruluk (FiveThirtyEight referans)

---

## 8. Out of Scope (Faz 1'de yapılmaz)

- NCAAB / WNCAAB / Euroleague (Faz 2-3)
- NBL (kapsam dışı — Python verisi yok)
- Kalibrasyon eğrisi eğitimi (Faz 1 sonrası kanıta göre)
- Player-level model (takım seviyesi yeterli)
- In-game live update (sezon başı maç başı update yeter)
- Bookmaker tamamen iptal kararı (ayrı brainstorm — tenis + MLB + diğer sporları etkiler)

---

## 9. Plan Zinciri — Ardışık Uygulama

Faz 1 üç ardışık plan dosyasına bölünür. Her plan kendi oturumunda uygulanır (context şişmesin):

### Plan 1.A — Veri Katmanı (1-2 hafta)
- `nba_api_refresher` + `espn_pbp_refresher`
- `team_ratings_store` (Elo + AdjO/AdjD JSON cache)
- `data_source_health` + `schema_validator`
- WNBA veri doğrulama spike testi
- Maç-pencere farkındalıklı tetikleyici (factory hook)
- Test: infra mock + atomic write + health fail-over

### Plan 1.B — Model Katmanı (2-3 hafta)
- `team_elo` (Glicko muadili)
- `pace_efficiency` (Markov muadili)
- `efficiency_metrics` (KenPom AdjO/AdjD hesabı)
- `match_pricer` (blend logic)
- `basketball_team_resolver` (slug ↔ NBA ID)
- Test: domain unit + Elo backtest + KenPom örnek doğrulaması

### Plan 1.C — Strateji Entegrasyon + Backtest (1-2 hafta)
- `basketball_model_anchor` (tennis_model_anchor paralel)
- `basketball_anchor_enricher` (tennis_anchor_enricher paralel)
- `basketball_dispatch` (market type dispatch)
- `factory.py` sport_tag dispatcher genişletme
- Test: enricher fail_reason yolları + A confidence sarmalı + dispatcher integration
- **Backtest doğrulama (son adım):** Son 1 NBA sezonu → günlük model_p → Polymarket fiyatına karşı kağıt-edge → Brier score + doğruluk raporu (hedef ≥%66 moneyline). Hedef altında ise Faz 1 "yayında" sayılmaz, kalibrasyon revize edilir

**Plan zincir kuralı:** Bir önceki plan "DONE" işaretine ulaşmadan sonraki başlamaz. Yarım iş bırakma yasak.

---

## 10. Onay ve Sonraki Adım

Bu spec onaylanırsa:

1. Spec git'e commit edilir
2. `writing-plans` skill ile **Plan 1.A** detaylı plan dosyası yazılır
3. Plan 1.A uygulama oturumuna geçilir (executing-plans skill)
4. Plan 1.A bittiğinde → Plan 1.B yazılır + uygulanır
5. Plan 1.C bittiğinde → Faz 1 done → Faz 2 brainstorm aşaması

Her geçiş **kullanıcı onayıyla** olur. Otomatik zincir değil.
