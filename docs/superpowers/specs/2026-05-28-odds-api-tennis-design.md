# Tennis Bot — Sackmann Sil + Odds API Entegrasyonu

**Date:** 2026-05-28
**Status:** APPROVED (user, 2026-05-28)
**Applies to:** tennis-lab + tennis-paper-lab (ana bot dışında)

---

## Problem

Tennis bot'unun Sackmann/Glicko2 tahmin modeli **%36.7 doğru** (90 trade Polymarket
resolution analizinden, random'dan kötü). Aynı dönemde Polymarket market konsensüsü
**%61.1 doğru**. Basket bot'unda Odds API bookmaker konsensüsü **%61.1 doğru**
(18 trade). **Tahmin gücü zaten bookmaker'da var; Sackmann internal model'i bot'u
yanlış yöne çekiyor.**

Veri (97 closed trade):
- Sackmann saf doğruluk: %46.2 (market %61.5)
- Sackmann "%85+ kesin" dediği 55 trade'de doğruluk: %43.6 (yüksek confidence'ta yanlış)
- Sackmann set_totals'da %16 doğru (market %72)
- Sackmann anlaşmazlık'ta market'le karşılaştırıldığında: market %62 haklı

**Spike catch çıkarıldıktan sonra gerçek paper EV: -$302 (97 trade)** — bot net
negatif. Tek kârlı kategori match_total (+$117), Odds API'de var.

## Goal

Sackmann/Glicko2 modeli tamamen kaldır, **Odds API bookmaker konsensüsü** ile değiştir.
Basket bot pattern'i — ana bot'taki `derive_confidence` + `probability` mantığı tennis'e
adapte. Sadece **A confidence** (bookmaker_weight ≥ 5 + sharp Pinnacle/Betfair) trade'leri
aç. Volume **~%37'e düşer** (Odds API h2h + totals destekli market'ler) ama beklenen
EV pozitife döner.

## Non-Goals (YAGNI)

- Challenger Tour desteği (Odds API'de yok). Skip.
- B/C confidence trade'leri (basket pattern: yasak).
- Sub-market'ler (set_handicap, set_totals, first_set_winner). Odds API'de yok, kapanır.
- Vig removal custom logic — ana bot probability.py kullanılır.
- Tennis-specific edge formula — basket aynısı.
- Parallel period (Sackmann + Odds API ikisi birden). Tek commit'te clean cut.

---

## Architecture

### Silinecek (~12 dosya + 17MB data)

**src/:**
- `src/domain/prediction/` (komple dizin) — glicko2.py, tennis_predictor.py, feature_extractor.py
- `src/domain/matching/tennis_player_resolver.py` (Sackmann player lookup)
- `src/infrastructure/data/` — sackmann_csv_client.py, sackmann_refresher.py,
  tennis_data_uk_client.py, tennis_ratings_store.py, tml_csv_client.py

**data/:**
- `data/sackmann_cache/` (komple dizin)
- `data/tennis_ratings.json` (~14MB)
- `data/tennis_ratings.before_itf_rebuild.json` (~3.5MB)
- `data/tml_cache/` (komple dizin)

**config:**
- `config_tennis.yaml` → tennis section'dan `confidence_tier_a`, `confidence_tier_b`,
  `data_dir`, `tml_dir`, `ratings_cache`, `diagnostic_log_dir`, `sackmann_years`,
  `challenger_years` kaldırılır

**tests:**
- Tüm Sackmann/Glicko2 unit testleri

### Eklenecek / Adapte edilecek (5 dosya)

**Ana bot'tan KOPYALA (verbatim):**
- `src/domain/analysis/confidence.py` (17 satır, `derive_confidence(bm_weight, has_sharp) → "A"|"B"|"C"`)
- `src/domain/analysis/probability.py` (ana bot probability calculation + vig removal)
- `src/infrastructure/apis/odds_client.py` (ana bot OddsClient, tennis methods eklenir)

**YENİ yaz:**
- `src/domain/matching/tennis_odds_matcher.py` — Polymarket slug → Odds API match
  fuzzy player name matching
- `src/strategy/enrichment/tennis_market_enricher.py` — YENİDEN YAZ (Sackmann
  predictor çağrısı yerine Odds API pipeline)

**Adapte:**
- `src/orchestration/tennis_factory.py` — Sackmann deps kaldır, odds_client ekle
- `src/strategy/entry/tennis_signal_adapter.py` — `anchor_probability =
  bm_prob.probability` (yeni enricher output'undan)

---

## Karar Mantığı

### Heavy cycle (30 dk'da bir)

1. Gamma'dan Polymarket tennis market'leri çek (mevcut Scanner)
2. **Odds API'den aktif tennis endpoint'leri çek** (yeni):
   - tennis_atp_french_open, tennis_wta_french_open (Roland Garros aktifken)
   - Wimbledon başladığında → tennis_atp_wimbledon, tennis_wta_wimbledon (config update)
   - Cache: `{endpoint_key: {match_id: odds_data}}` 30 dk TTL

### Light cycle (5 sn'de bir) — Her tenis market için

```
1. Polymarket slug parse:
   "atp-shimizu-tomic-2026-05-27" → tour=atp, tokens=["shimizu","tomic"], date=2026-05-27

2. tennis_odds_matcher.find_match(slug, active_odds_cache):
   - Aktif ATP/WTA endpoint'leri tarar
   - Token-based fuzzy match (lowercase + accent strip)
   - Tarih ± 1 gün tolerans
   - Match veya None döner

3. Eşleşme yoksa: SKIP, skipped_trades.jsonl'a yaz reason="no_bookmaker_match"
   (Challenger maçları burada elenir.)

4. probability.compute_consensus_probability(odds_match.bookmakers, side) →
   BookmakerProb(probability, num_bookmakers, has_sharp)
   - Ana bot mantığı: vig removed multi-bookmaker median
   - has_sharp = Pinnacle veya Betfair Exchange varsa True

5. confidence.derive_confidence(num_bookmakers, has_sharp):
   - bm_weight < 5 → "C" → SKIP reason="insufficient_bookmakers"
   - has_sharp=False → "B" → SKIP reason="no_sharp_book" (basket pattern)
   - has_sharp=True → "A" → devam

6. EnrichedMarket build:
   - anchor_probability = bookmaker_prob.probability (ana bot pattern)
   - bookmaker_prob = float (audit için)
   - num_bookmakers, has_sharp
   - confidence = "A"

7. Entry processor: gate.edge_check → exclude_combos kontrolü → trade aç
   (Mevcut FAZ 1 exclude_combos kuralları korunur:
    set_totals, first_set_winner kapalı.)
```

---

## Confidence & Sizing

Basket pattern + tennis-lab config:

| Confidence | Kriter | Sizing (config_tennis.yaml mevcut) | Trade Aç |
|---|---|---|---|
| A | bm_weight ≥ 5 + has_sharp | $50 (5% bankroll) | EVET |
| B | bm_weight ≥ 5, sharp YOK | $35 (3.5% bankroll, **kullanılmayacak**) | HAYIR |
| C | bm_weight < 5 | (engellenir) | HAYIR |

Bimodal markets (set_totals, first_set_totals) zaten exclude_combos'ta kapatıldı (FAZ 1).
Bimodal cap $15 config kalır ama tetiklenmez.

---

## Volume Tahmini

| Senaryo | Trade/gün |
|---|---|
| Grand Slam aktif (Roland Garros, Wimbledon, US Open, Aus Open) | **50-70** |
| ATP Masters / WTA 1000 | 20-40 |
| Slam'ler arası (Queen's, ATP 250) | 10-20 |
| Challenger only (rare) | **0** |

Şu an Roland Garros: 38 maç × (h2h + maybe totals) ≈ 50-70 günlük opportunity.

---

## Error Handling

| Durum | Davranış | Katman |
|---|---|---|
| Odds API 5xx / timeout | Cache'i son başarılıdan kullan, WARNING log | Infrastructure |
| Polymarket market Odds'da yok | SKIP, "no_bookmaker_match" reason | Strategy enricher |
| `num_bookmakers < 5` | SKIP, "insufficient_bookmakers" reason | Strategy enricher |
| `has_sharp=False` | SKIP, "no_sharp_book" reason | Strategy enricher |
| Fuzzy player match conflict (2 maç eşleşti) | İlk match'i seç, WARNING log | Domain matcher |
| Bookmaker odds malformed | Skip that bookmaker, WARNING log | Domain probability |

Sessiz hata yok. Her skip skipped_trades.jsonl'a yazılır (FAZ 1'de eksikti, bu spec'te
düzeltilir — enricher skip'leri de log'lanmalı).

---

## Implementation Order

| Faz | İş | Süre | Risk |
|---|---|---|---|
| **1** | tennis-paper-lab: yeni componentler + Sackmann delete (tek commit) | 1 gün | Orta |
| **2** | tennis-paper-lab live: bot reload + 24h gözlem | 24h | Düşük |
| **3** | tennis-lab: mirror Faz 1 (paper-lab'dan kopya + adapte) | 0.5 gün | Düşük |
| **4** | tennis-lab live: bot reload + 24h gözlem | 24h | Düşük |
| **5** | Stable → master merge | 5 dk | Düşük |

**Toplam: ~3-4 gün iş + 2 gün gözlem.**

### Branch isolation

- tennis-paper-lab (ayrı repo): `feature/odds-api-tennis`
- tennis-lab (ana bot worktree): `feature/odds-api-tennis-lab` (ana bot
  `feature/odds-api-tennis-mainbot` ile çakışmaz)

---

## Testing (ARCH_GUARD Kural 11)

**Unit tests (zorunlu):**
- `test_tennis_odds_matcher.py` — 10+ case (lowercase, hyphen, accent, date ±1)
- `test_tennis_market_enricher.py` — YENİDEN YAZ (Sackmann test'leri gider, Odds
  pipeline test'leri gelir, 15+ case)
- `test_odds_client.py` — tennis endpoint'leri için 5 case + cache + 5xx fallback
- `test_confidence.py` ve `test_probability.py` — ana bot'tan kopya gelir (zaten testli)

**Integration test:**
- Polymarket market dict → tennis_market_enricher → EnrichedMarket
  - Mock OddsClient response + gerçek probability + confidence
  - Beklenen: anchor_probability set + confidence=A + ready for entry

**Regression:** Mevcut tüm exit_processor, force_close, gate, sport_rules, scanner
testleri hâlâ geçmelidir.

---

## Rollback Planı

Sorun çıkarsa:
1. Bot'u durdur (kill PID)
2. `git checkout <previous-stable-branch>` (worktree değiştir)
3. Bot yeniden başlat (eski Sackmann kodu aktif değil — silindi)

**Critical:** Sackmann silindiği için "eski koda dön" yok. Çözüm: rollback öncesi
backup branch tut. Eğer rollback gerekirse `feature/odds-api-tennis-rollback` branch'ten
revert et.

Pratik plan: 24h gözlem süresinde sorun yoksa master merge. Sorun varsa branch'te
kal ve düzelt.

---

## Open Questions (implementation sırasında karar)

1. **Player name normalization sınırı:** "Karen Khachanov" → "khachanov" mu, "karen
   khachanov" mu? **Tokenize + last name match** ile başla, gerekirse genişlet.
2. **Aktif Odds endpoint listesi:** Wimbledon başladığında manuel config update —
   MVP'de bu yeterli. Otomatik discovery v2'de.
3. **Match totals önceliği:** Tek maçta h2h + totals iki market var — ikisi de
   evaluate edilir, edge'i büyük olan tetiklenir.

---

## Acceptance Criteria

- [ ] `grep -ri "sackmann\|Sackmann\|Glicko"` 0 sonuç tennis-lab + tennis-paper-lab src/, tests/, data/
- [ ] `data/sackmann_cache/`, `tennis_ratings.json`, `tennis_ratings.before_itf_rebuild.json`,
      `tml_cache/` silindi
- [ ] `config_tennis.yaml`'da Sackmann config sectionları kaldırıldı
- [ ] Yeni odds_client + probability + confidence + tennis_odds_matcher + enricher unit testleri PASS
- [ ] Integration test: Polymarket market → EnrichedMarket pipeline PASS
- [ ] Tennis Paper Lab 24h live: A-confidence pozisyonları açılıyor (skipped_trades'de
      "low_confidence" ve "no_bookmaker_match" reason'ları görünmeli)
- [ ] Tennis Lab same after mirror
- [ ] pytest full suite PASS her iki bot
- [ ] Bot.log'da Sackmann referansı YOK
