# SPEC — Spesifikasyonlar

> Bu dosya aktif teknik spesifikasyonları içerir.
> Bir spec entegre edilip onaylandıktan sonra bu dosyadan **SİLİNİR**.
> Sadece aktif, henüz koda dönüşmemiş spec'ler burada durur.

---

## Nasıl Kullanılır

### Spec Ekleme
```
1. Bir özellik veya modül için detaylı spec yaz (aşağıdaki formata uy)
2. Durum: DRAFT
3. Review + onay → durum: APPROVED
4. Kod yazılıp test edildikten sonra → durum: IMPLEMENTED → sil
```

### Spec Formatı
```
### SPEC-XXX: [Modül/Özellik adı]
- **Durum**: DRAFT | APPROVED | IMPLEMENTED
- **Tarih**: YYYY-MM-DD
- **İlgili Plan**: PLAN-XXX
- **Katman**: domain | strategy | infrastructure | orchestration | presentation
- **Dosya**: src/katman/modul.py

#### Amaç
Modülün ne yaptığı, tek cümle.

#### Girdi/Çıktı
- Girdi: ...
- Çıktı: ...

#### Davranış Kuralları
1. ...
2. ...

#### Sınır Durumları (Edge Cases)
- ...

#### Test Senaryoları
- ...
```

---

## Aktif Spesifikasyonlar

### SPEC-001: Skip Observability — entry skip detaylandırma
- **Durum**: IMPLEMENTED
- **Tarih**: 2026-04-16
- **İlgili Plan**: PLAN-001 (yazılacak)
- **Katman**: domain + strategy + orchestration (çapraz, ama her dosya kendi katmanında)
- **Dosya**:
  - `src/domain/analysis/enrich_outcome.py` (YENİ)
  - `src/strategy/enrichment/odds_enricher.py` (REFACTOR)
  - `src/strategy/entry/gate.py` (REFACTOR)
  - `src/orchestration/operational_writers.py` (EXTEND)
  - `src/orchestration/entry_processor.py` (EXTEND)

Not: `src/domain/analysis/edge.py` zaten var (`calculate_edge` threshold-aware). `no_edge` detail üretimi için gate'te inline 2 satır (bm_prob vs yes_price) yeterli — ayrı saf fn YAGNI.

#### Amaç
Entry gate'in her skip ettiği market için, `SkippedTradeRecord.skip_detail` alanını yapılandırılmış bilgi ile doldurmak. Mevcut durumda reason tek-bucket (`no_bookmaker_data`, `no_edge`, `entry_price_cap`, `exposure_cap_reached` vb.) ve `skip_detail` boş — kök neden analizi için veri yetersiz. Bu spec 12 skip reason'ının her biri için detay üretir.

#### Motivasyon
Canlı log analizi (2026-04-16): `no_bookmaker_data` tek sebep altında 2329 skip var — bunların ne kadarı (a) sport_key çözümlenemedi, (b) team extract fail, (c) Odds API events boş, (d) event fuzzy match fail, (e) bookmaker list boş — ayrışmıyor. Aynı şey `no_edge` (918), `entry_price_cap` (55), `exposure_cap_reached` (233) için de geçerli — sayısal değerler kayıtta yok. Sub-spec #2 (basketball), #3 (shl), #4 (tennis) bu veri olmadan kör çalışır.

#### Girdi/Çıktı

**enrich_market() — return type değişir**
- Girdi: MarketData, odds_client
- Çıktı (eski): `BookmakerProbability | None`
- Çıktı (yeni): `EnrichResult` — probability var ya da fail_reason var (exclusive)

**gate._evaluate_one() — GateResult.skip_detail alanı eklenir**
- Girdi: MarketData
- Çıktı: `GateResult(condition_id, signal, skipped_reason, skip_detail, manipulation)`

**log_skip() — imza genişler**
- Girdi (eski): `(logger, market, reason)`
- Girdi (yeni): `(logger, market, reason, detail="")`

#### Davranış Kuralları

1. **Enrich fail taksonomisi — 5 alt-sebep.** `enrich_market` None dönmek yerine `EnrichResult(None, EnrichFailReason.X)` döner:
   - `SPORT_KEY_UNRESOLVED`: `resolve_sport_key` None döndü
   - `TEAM_EXTRACT_FAILED`: `extract_teams(question)` → (None, None)
   - `EMPTY_EVENTS`: sport_key var ama `get_odds()` [] veya None döndü
   - `EVENT_NO_MATCH`: events listesi dolu ama `find_best_event_match` None (fuzzy < 0.80)
   - `EMPTY_BOOKMAKERS`: event match var ama `_weighted_average` None (total_weight ≤ 0)

2. **Skip reason bucket'ı değişmez.** Gate hala `skipped_reason="no_bookmaker_data"` atar; fail detail ayrı alanda (`skip_detail`) tutulur. Mevcut log analiz pipeline'ı kırılmaz.

3. **Tablo — 12 skip reason için detail formatı:**

   | reason | detail formatı |
   |---|---|
   | `circuit_breaker` | `"daily_loss -3.1% vs -3%"` (breaker reason text'in `breaker: ` prefix'i sökülmüş hali) |
   | `cooldown_active` | `"cycles_remaining=2"` (CooldownTracker cycle-bazlı, zaman değil) |
   | `max_positions_reached` | `"count=50/50"` |
   | `event_already_held` | `"event_id=378836"` |
   | `blacklisted` | `"match=condition_id"` veya `"match=event_id"` (gate iki ayrı `is_blacklisted(...)` çağrısıyla ayırır — condition_id önce, sonra event_id) |
   | `manipulation_high_risk` | `manip.reason` (string, boş değil) |
   | `no_bookmaker_data` | 5 enum değeri: `sport_key_unresolved` \| `team_extract_failed` \| `empty_events` \| `event_no_match` \| `empty_bookmakers` |
   | `confidence_C` | `"num_bookmakers=1.5"` (1 ondalık) |
   | `no_edge` | `"edge=0.042, min=0.06, bm=0.65, yes=0.60"` |
   | `entry_price_cap` | `"price=0.905, cap=0.88"` |
   | `size_below_min` | `"size=0.42, min=5.00"` (şu an `size_below_min (0.42 < 5.00)` reason string'e gömülü — ayrıştır) |
   | `exposure_cap_reached` | `"available=0.8, min=15.0"` |

4. **Reason normalize edilen iki istisna:**
   - `"breaker: Daily loss -3.1% exceeded soft limit -3%"` → reason=`"circuit_breaker"`, detail=`"daily_loss -3.1% vs -3%"` (tam text değil, önekini sök)
   - `"size_below_min (0.42 < 5.00)"` → reason=`"size_below_min"`, detail=`"size=0.42, min=5.00"`

5. **no_edge detail hesabı — gate'te inline.** Ayrı saf fn yok. Gate line 141'de:
   ```python
   edge_raw = abs(bm_prob.probability - market.yes_price)
   direction_guess = "BUY_YES" if bm_prob.probability >= market.yes_price else "BUY_NO"
   detail = f"edge={edge_raw:.3f}, min={self.config.min_edge}, bm={bm_prob.probability:.2f}, yes={market.yes_price:.2f}"
   ```

6. **Geriye uyum — migration yok.** `skipped_trades.jsonl` eski satırlarda `skip_detail=""` kalır; yeni satırlar dolu olur. Dashboard/analytics bu alanı zaten opsiyonel okuyor.

7. **log_skip() default parametre.** `detail=""` default; çağıranlar yavaş yavaş geçebilir. Entry skip noktaları bu spec'te tamamen dönüştürülür.

#### Sınır Durumları (Edge Cases)

1. **enrich_market() OK yolu** — probability dolu, fail_reason None. Caller `result.probability` ile devam eder.
2. **enrich_market() fail yolu** — probability None, fail_reason dolu. Caller skip_detail'e fail_reason.value yazar.
3. **Gate'de manipulation OK ama bm_prob fail** — `skipped_reason="no_bookmaker_data"`, `manipulation=manip` (boş değil, test/debug için).
4. **no_edge + bm_prob None olamaz** — bu satıra gelmek için bm_prob zaten dolu (line 133-134'te None kontrolü var). Invariant.
5. **size_below_min iki farklı yerde atılıyor** (line 159 ve 175). İki noktada da aynı detail formatı.
6. **circuit breaker reason'ı** breaker modülünden gelir ve dinamik (her ihlal tipine göre). Reason string'i `"breaker: <rest>"` formatında olduğundan `rest` kısmı detail olur; bucket "circuit_breaker".
7. **exposure_cap_reached entry_processor.py:111'de de atılıyor** — gate'in dışında bir skip noktası. O da detail ile güncellenir.

#### Test Senaryoları

Test convention: `tests/unit/<layer>/<module>/test_*.py`. Mevcut test dosyalarına ekleme yapılır (yeni dosya yaratılmaz).

**A) Domain — `tests/unit/domain/analysis/test_enrich_outcome.py` (YENİ)**
- `test_enrich_result_ok_has_probability_and_null_fail_reason`
- `test_enrich_result_fail_has_null_probability_and_fail_reason`
- `test_enrich_fail_reason_values_match_spec` (5 enum değeri)

**B) Strategy — `tests/unit/strategy/enrichment/test_odds_enricher.py` (mevcut, EKLE)**
- `test_enrich_market_no_sport_key_returns_sport_key_unresolved`
- `test_enrich_market_team_extract_fail_returns_team_extract_failed`
- `test_enrich_market_empty_events_returns_empty_events`
- `test_enrich_market_no_event_match_returns_event_no_match`
- `test_enrich_market_empty_bookmakers_returns_empty_bookmakers`
- `test_enrich_market_ok_returns_probability_and_no_fail_reason`

**C) Strategy — `tests/unit/strategy/entry/test_gate.py` (mevcut, EKLE)**
- `test_evaluate_one_event_already_held_sets_skip_detail_event_id`
- `test_evaluate_one_blacklisted_condition_id_sets_skip_detail_match_condition_id`
- `test_evaluate_one_blacklisted_event_id_sets_skip_detail_match_event_id`
- `test_evaluate_one_manipulation_high_risk_sets_skip_detail_reason`
- `test_evaluate_one_no_bookmaker_data_sets_skip_detail_fail_reason`
- `test_evaluate_one_confidence_c_sets_skip_detail_num_bookmakers`
- `test_evaluate_one_no_edge_sets_skip_detail_edge_values`
- `test_evaluate_one_entry_price_cap_sets_skip_detail_price_cap`
- `test_evaluate_one_size_below_min_raw_sets_skip_detail_size_min`
- `test_evaluate_one_size_below_min_final_sets_skip_detail_size_min`
- `test_evaluate_one_exposure_cap_sets_skip_detail_available_min`
- `test_run_circuit_breaker_sets_skip_detail_breaker_reason_normalized`
- `test_run_cooldown_sets_skip_detail_cycles_remaining`
- `test_run_max_positions_sets_skip_detail_count_slash_limit`

**D) Orchestration — `tests/unit/orchestration/test_entry_processor.py` (mevcut ya da yeni, EKLE)**
- `test_process_markets_exposure_cap_logs_detail_with_available_min`

**E) Orchestration — `tests/unit/orchestration/test_operational_writers.py` (mevcut ya da yeni, EKLE)**
- `test_log_skip_writes_skip_detail_field_when_provided`
- `test_log_skip_default_detail_is_empty_string`

#### Mimari Uyum (ARCH_GUARD)
- Kural 1 (katman): enrich_outcome.py ve edge.py domain; üstten aşağı import. ✓
- Kural 2 (domain I/O yok): yeni dosyalar pure, requests/file yok. ✓
- Kural 3 (400 satır): gate.py 209 → ~244; enricher 170 → ~180; limitin altında. ✓
- Kural 4 (10 method): yeni class yok, dataclass + enum. ✓
- Kural 6 (magic number): eşikler config'den; formatlamadaki `.2f` gibi rakamlar format specifier, magic değil. ✓
- Kural 11 (test): her domain fn + her strategy karar noktası için test yazılı. ✓
- Kural 12 (hata yönetimi): domain exception fırlatmaz; enricher şimdiki exception davranışını değiştirmez. ✓

#### Yapılmayacaklar (YAGNI)
- ❌ Exit skip'lerine detay (scope: entry)
- ❌ Dashboard'a skip analytics paneli
- ❌ Geriye dönük `skipped_trades.jsonl` migration
- ❌ Skip reason'larını Enum'a taşıma (string kalır; tek yerde üretilip tek yerde tüketilen lokal vocabulary)
- ❌ `operational_writers.log_skip` çağrılarının exit path'te de detail alması (scope dışı)
- ❌ `_match_tennis_key` fallback sorununu düzeltme (bu sub-spec #4'ün işi)
- ❌ basketball/CBA mapping ekleme (sub-spec #2'nin işi)
- ❌ shl coverage teşhisi (sub-spec #3'ün işi)

#### Doğrulama
1. `pytest tests/domain/analysis/test_edge.py tests/strategy/enrichment/test_odds_enricher.py tests/strategy/entry/test_gate_observability.py tests/orchestration/test_entry_processor_skip_detail.py -v` → tümü yeşil.
2. Mevcut test suite regresyon: `pytest -q` → geçen testler korunur.
3. Canlı 1 cycle çalıştırma (ya da kuru run) → `logs/skipped_trades.jsonl` son satırlarda `skip_detail` dolu.
4. Grep: `grep -l "breaker: " logs/` eski formatı doğrular; yeni kayıtlarda `"skip_reason":"circuit_breaker"` + `"skip_detail":"daily_loss ...` olmalı.

#### Başarı Kriteri
`logs/skipped_trades.jsonl` yeni satırlarda:
- Her skip kaydının `skip_detail` alanı boş değil (12 reason'ın hepsi için).
- Sub-spec #2/#3/#4 analiz yaparken `no_bookmaker_data` alt sebebini, `no_edge` edge değerini, `exposure_cap` mevcut değerini sayısal olarak görebilir.
