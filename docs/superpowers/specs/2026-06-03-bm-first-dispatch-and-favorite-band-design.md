# SPEC: BM-first Dispatch + Favorite-band Edge Relax

**Tarih:** 2026-06-03
**Tetik:** Kullanıcı analizi — bookmaker-source ML trade'leri %83 WR / +$28, model-source ML trade'leri %40 WR / -$9. Bookmaker phantom-restored bug düzeltildi (önceki commit). Sonuç değişen örneklem küçük (6/11) ama sinyal güçlü.

## Karar

Mevcut "model-first, BM fallback" dispatch'i **TERSİNE** çevir:
- **Moneyline (h2h)**: BM ÖNCELİKLİ → BM yoksa/başarısızsa model fallback
- **Alt market (totals / set handicap / spread)**: Sadece model (BM zaten h2h dışı veri vermiyor — odds_enricher.py:39)

Ek: SPEC-Z13 ile eklenen `consensus_min_model_edge=0.0` guard'ı (Azkara'da tetiklenen) — **direction-adjusted model olasılığı ∈ [favorite_band_min_prob, favorite_band_max_prob)** aralığında **bypass** edilir (2026-06-04 revize: entry_price yerine prob_for_side). Kullanıcı gözlemi: orta-yüksek favori bandında (60-80% güven) negatif direction-edge consensus trade'leri tarihsel olarak kazanıyor (Shimabukuro +$17.89, Zhang +$15.00).

## Kapsam

### Değişen

1. **`src/strategy/enrichment/tennis_dispatch.py`** — `enrich_with_tennis_dispatch()` akışı:
   - ML ise → `bookmaker_enricher(market)` İLK çağrılır.
   - BM `probability is None` ise → model akışına geç.
   - Non-ML ise → BM denemesi atlanır (h2h dışı veri yok).
   - 5 yerde dağılmış `if is_moneyline: return bookmaker_enricher(...)` blokları kaldırılır (artık BM yukarıda denendi, model fail'i `EnrichResult` olarak döndürülür).

2. **`src/strategy/enrichment/basketball_dispatch.py`** — aynı akış değişimi. 6 ayrı `if is_moneyline: return bookmaker_enricher(...)` bloğu sadeleşir.

3. **`src/strategy/entry/consensus.py`** — `evaluate()` imzasına `favorite_band_min_prob`, `favorite_band_max_prob` parametreleri eklenir. `model_edge < min_model_edge` kontrolü sadece `prob_for_side < favorite_band_min_prob OR prob_for_side >= favorite_band_max_prob` durumunda uygulanır (06-04 revize: önceki sürüm entry_price idi).

4. **`src/strategy/entry/gate.py`** — `GateConfig`'e iki yeni alan: `consensus_favorite_band_min_prob: float = 0.60`, `consensus_favorite_band_max_prob: float = 0.80`. `_evaluate_strategies()` consensus'e bu parametreleri geçirir.

   **2026-06-04 revize:** Önceki sürüm alan adları `favorite_band_min_entry/max_entry` idi ve entry_price üzerinden kontrol yapıyordu. Kullanıcı kararıyla **direction-adjusted model olasılığı** (botun seçtiği taraf için tahmini kazanma olasılığı) üzerinden bant kontrolüne çevrildi. Alan adları `_prob` suffix'i ile yeniden adlandırıldı, semantik artık "güven bandı" (price bandı değil).

5. **`src/config/settings.py`** — `EdgeConfig`'e iki yeni alan (config.yaml mapping'i için).

6. **`config.yaml`** — `edge:` bölümüne iki yeni satır.

### Değişmeyen

- Anti-edge guard'lar (`anti_edge_high_price_threshold`, `anti_edge_absolute_max`) — favorite_band içinde de uygulanır.
- `extreme_disagreement_threshold` (model-market 30+ puan gap) — değişmez.
- `entry_price_cap` (0.80) — değişmez.
- Bimodal floor (0.20) — değişmez.
- SPEC-Z13'ün asıl koruması (model_edge < 0 → consensus kapatma) → favorite_band DIŞINDA hâlâ aktif.

## Davranış Tablosu

| Durum | prob_for_side | model_edge | Önce | Sonra |
|---|---|---|---|---|
| ML, BM var | herhangi | herhangi | model ÖNCE | **BM ÖNCE** |
| ML, BM yok | herhangi | herhangi | model | model (fallback) |
| Alt market | herhangi | herhangi | model | model (aynı) |
| Consensus, prob 0.70 | 0.70 | -0.05 | RED (SPEC-Z13) | **GEÇER (favorite_band)** |
| Consensus, prob 0.55 | 0.55 | -0.05 | RED | RED (band dışı) |
| Consensus, prob 0.70 | 0.70 | -0.20 | RED (anti_edge_absolute_max) | RED (anti_edge hâlâ aktif) |

## Risk

- Favorite_band içinde negatif edge'i serbest bırakmak, anti_edge_absolute_max (0.15) hâlâ guard. Maksimum "kötü" trade: prob_for_side 0.79, paid 0.94 → 0.15 anti_edge'ye yakın eşik. Ama prob 0.79 + paid 0.94 vakası anti_edge_high_price_threshold (0.80) ile de yakalanır.
- BM-first swap ile bazı maçlarda model'in "daha akıllı" tahmin verebileceği durumlar kaçırılır. Karşı tez: küçük örneklemde model %40 WR, BM %83 WR — şu an BM açık ara önde.

## Geri Alma

Tek tek geri alınır:
- Dispatch swap: tek dosya patch, eski "model first" pattern geri yüklenir.
- Favorite_band: config'de `favorite_band_min_prob: 0.99` ya da `favorite_band_max_prob: 0.0` ile efektif kapatma (range boş olur → kontrol her zaman uygulanır).

## Test

- `tests/unit/strategy/entry/test_consensus.py` — favorite_band exception için yeni 2 test: in-band negatif edge geçer, out-of-band negatif edge reddedilir.
- `tests/integration/test_tennis_dispatch.py` — BM-first sıralama testi: BM önce çağrılır, BM None dönerse model çağrılır.
- Basket dispatch için paralel test (varsa).
