# MLB Submarket — Ana Bot Entegrasyonu (Design Spec)

**Tarih:** 2026-05-21
**Durum:** DONE (2026-05-23) — SPEC-R Plan 1-4 master'a merge edildi; SPEC-S Faz A+B+C ile Plan 4 simplifications çözüldü (team+park+DH binding, moneyline pricer, Marcel+TTO+bullpen interface). Bullpen rates aggregation TODO-004 olarak ertelendi.
**Anahtar kelime / lookup:** `MLB-SUBMARKET-MAINBOT`
**Supersedes:** `docs/superpowers/specs/2026-05-21-mlb-submarket-lab-design.md` (sandbox lab versiyonu — REJECTED, kullanıcı ana bot entegrasyonu istedi 2026-05-21)

---

## 1. Hedef & Karar Bağlamı

**Hedef:** Polymarket MLB submarket'lerinde (totals O/U + run-line ±1.5) bağımsız bir tahmin modeli ile ana bot üzerinden **gerçek bahis** alabilmek.

**Karar:** MLB submarket prediction motoru ayrı sandbox laboratuvar olarak değil, ana bot kod tabanına ve runtime'ına entegre edilir. Tek bankroll, tek dashboard, tek state. Risk modu = ana bot ile aynı (canlı bahis).

**Neden ana bot:**
- Tennis Lab paper-trade sandbox olarak çalışıyor (SPEC-O, 4 hafta gözlem); MLB için kullanıcı bu adımı geçmek istiyor.
- Tek dashboard hedefi: kapanmış işlemler, açık pozisyonlar, realized PnL hep birlikte görünsün.
- Tennis Lab'in açtığı `EntryProcessor.process_signals` public API (SPEC-O) zaten bookmaker bypass eden model-anchor giriş noktası. Bu API MLB için yeniden kullanılır.

**Mevcut bot davranışı:**
- MLB moneyline: bookmaker probability anchor → trade alınıyor (mevcut).
- MLB totals/run-line: Odds API bookmaker probability YOK → entry_gate sessizce reddediyor. Bu spec onu çözer.

---

## 2. Model Teknik Detayları (Referans)

Model katmanları (rate shrinker → Log5 → 24-state Markov → inning sim → game sim → totals/spread pricer) ve akademik temelleri eski DRAFT'ta zaten detaylandırılmış:

→ `docs/superpowers/specs/2026-05-21-mlb-submarket-lab-design.md` §2 (Akademik Temel) ve §3 (5-Katmanlı Mimari).

Bu dokümanın kapsamı: **ana bot entegrasyonu**. Model formülleri eski dokümana referansla aynen kullanılır. Eski dokümanın **sadece** §1.Sandbox/§Worktree/§Dashboard-port-5052/§Ayrı-config bölümleri geçersizdir.

---

## 3. Mimari Entegrasyon

### 3.1 Yeni dosyalar

**Domain (saf, I/O yok — Kural 2):**
```
src/domain/mlb_submarket/__init__.py
src/domain/mlb_submarket/league_constants.py        # Lig ortalama PA outcome rate'leri (sabit)
src/domain/mlb_submarket/rate_shrinker.py           # Empirical Bayes Beta posterior + Marcel weights
src/domain/mlb_submarket/handedness_adjust.py       # L/R platoon split
src/domain/mlb_submarket/park_factor_adjust.py      # Component-level park
src/domain/mlb_submarket/weather_adjust.py          # Wind/temp/humidity HR rate
src/domain/mlb_submarket/tto_adjust.py              # Times Through Order penalty
src/domain/mlb_submarket/log5.py                    # Haechrel multi-class Log5
src/domain/mlb_submarket/pa_outcome.py              # Layer 1: tüm adjustment + Log5 dispatch
src/domain/mlb_submarket/transition_matrix.py       # Tango RE Matrix (sabit veri)
src/domain/mlb_submarket/markov.py                  # Layer 2: 24-state transition + DP/SAC FLY
src/domain/mlb_submarket/inning_simulator.py        # Layer 3: Monte Carlo veya analitik
src/domain/mlb_submarket/lineup_order.py            # PA pozisyon dispatcher
src/domain/mlb_submarket/bullpen_segmenter.py       # 3-segment leverage bullpen
src/domain/mlb_submarket/game_simulator.py          # Layer 4: 9-inning convolution + DH 7-inning
src/domain/mlb_submarket/totals_pricer.py           # Layer 5: P(toplam ≥ N)
src/domain/mlb_submarket/spread_pricer.py           # Layer 5: P(run-line cover)
src/domain/mlb_submarket/edge_candidate.py          # EdgeCandidate dataclass (tennis pattern)
```

**Strategy (entry adapter):**
```
src/strategy/entry/mlb_signal_adapter.py            # EdgeCandidate → Signal (tennis adapter klonu)
src/strategy/entry/mlb_submarket_engine.py          # Orchestrator: data fetch → model run → edge
```

**Infrastructure (I/O):**
```
src/infrastructure/mlb_data/__init__.py
src/infrastructure/mlb_data/statsapi_client.py      # MLB Stats API (schedule, lineup, GUMBO)
src/infrastructure/mlb_data/statcast_client.py      # Baseball Savant via pybaseball
src/infrastructure/mlb_data/weather_client.py       # Open-Meteo (rüzgâr/sıcaklık)
src/infrastructure/mlb_data/rate_cache.py           # Pitcher/batter rate cache (jsonl/sqlite)
src/infrastructure/mlb_data/scratch_detector.py     # GUMBO ile lineup scratch tespiti
```

### 3.2 Modifiye edilen dosyalar

- **`src/config/sport_rules.py`** — `mlb` rule'una `submarket_enabled: True` + `anchor_source: "model"` flag'leri eklenir. Diğer sport'larda default `"bookmaker"`. NHL `moneyline_only` davranışı korunur.
- **`src/config/settings.py`** — `MlbSubmarketConfig` Pydantic model (rate cache path, statsapi timeout, edge threshold, manipulation guard limit). `AppConfig`'e `mlb_submarket: MlbSubmarketConfig | None` alanı.
- **`config.yaml`** — `mlb_submarket:` bloğu (default disabled flag ile başlar; kullanıcı manuel açar).
- **`src/orchestration/scanner.py`** — MLB market'leri için anchor_source kontrolü. Bookmaker yoksa ve sport+market_type submarket_enabled ise → `mlb_submarket_engine.process(market)` çağrılır, edge varsa signal listesine eklenir. Bookmaker varsa eski yol (ML için).
- **`src/orchestration/factory.py`** — `MlbSubmarketEngine` composition (config-gated; flag kapalıysa None).

### 3.3 Akış

```
scanner cycle
   │
   ├─► MLB market keşfi (gamma_client)
   │     │
   │     ├─► market_type = MONEYLINE → mevcut yol (bookmaker anchor)
   │     └─► market_type = TOTALS / RUN_LINE → MlbSubmarketEngine
   │            │
   │            ├─► statsapi: lineup + park + weather + bullpen
   │            ├─► rate_cache: pitcher/batter rate posterior
   │            ├─► pa_outcome → markov → inning → game → pricer
   │            ├─► edge = model_prob - polymarket_price
   │            └─► EdgeCandidate (edge ≥ threshold ise)
   │                  │
   │                  └─► mlb_signal_adapter → Signal
   │                        │
   │                        └─► EntryProcessor.process_signals(markets, signals)
   │                              (mevcut portfolio guards: cooldown, exposure, blacklist…)
```

### 3.4 Anchor source dispatch

Bot karar mekanizmasının iki noktada anchor source'u sorması gerekir:

1. **Scanner**: market'ı işleme almadan önce sport_rules'tan `anchor_source(sport_tag, market_type)` sorgula. `"bookmaker"` ise mevcut odds_enricher path'i. `"model"` ise `mlb_submarket_engine` path'i.
2. **EntryProcessor**: `process_signals` API zaten model-anchor için yazılmış (Tennis Lab); bookmaker bypass eden portfolio-only path. MLB için aynısı yeniden kullanılır.

`sport_rules.py`'a eklenecek yardımcı:
```python
def anchor_source(sport_tag: str, market_type: str) -> str:
    """'model' | 'bookmaker'. Submarket için sport-specific override edilebilir."""
    rule = get_sport_rule(sport_tag, "submarket_anchor", {})
    return rule.get(market_type, "bookmaker")
```

---

## 4. State & Dashboard

- **State:** Aynı `data/positions.json`, aynı `bankroll`, aynı equity history. MLB submarket pozisyonları `sports_market_type = TOTALS` veya `SPREADS` ile diğer NBA totals trade'leriyle ayırt edilir (zaten model var).
- **Dashboard:** Yeni tab/widget yok. Active, exited, equity widget'larında diğer trade'lerle birlikte görünür.
- **Reboot:** Mevcut semantik — state/session sıfırlanır, audit korunur (PLAN-DASH-EXITED-001 sonrası archive da görsel olarak korunur).
- **Sport rules tag:** `sport_tag = "baseball"`, `market_type = TOTALS|RUN_LINE`. Trade kayıtlarında `entry_reason` yeni değer: `"mlb_submarket"` (model anchor sinyali için).

---

## 5. Risk & Guard'lar

MLB submarket'e özel cap **YOK**. Ana bot'un mevcut çok katmanlı guard sistemi yeterli:

- `max_positions_per_event = 2` → bir maçta ML + totals + run_line için max 2.
- Exposure cap (PLAN-FIXED-SIZING-001 sonrası: total_portfolio_value × max_exposure_pct).
- Circuit breaker (daily loss limit).
- Blacklist + cooldown.
- Manipulation guard.
- Entry price cap.

Yeni eklenen guard tek bir mantık:
- **Confidence tier**: model çıktısı edge magnitude'una göre A/B'ye çevrilir (NBA totals tier mantığıyla aynı). Tier C yok (girilmez).

---

## 6. Test Stratejisi

- **Domain (Kural 11 — zorunlu):** Her saf modül için unit test. Lig ortalama vs gözlem bias kontrolü. Tango RE Matrix doğrulaması. Log5 sınır durumları (0.5 × 0.5 = 0.5, 1.0 × X = X). Park factor double-count guard.
- **Strategy:** `mlb_signal_adapter` → Signal dönüşümü, edge threshold filter.
- **Orchestration:** Scanner'da MONEYLINE→bookmaker, TOTALS→model dispatch testi (mocked enricher).
- **Integration:** `EntryProcessor.process_signals` MLB için açılan pozisyonun audit'e doğru `entry_reason` ile yazıldığı.
- **Backtest:** Tarihsel veri (Statcast geçmişi) üzerinde model accuracy ölçümü — implementation plan'ında ayrı task.

---

## 7. Kapsamla DAHIL OLMAYANLAR

- ❌ Tennis Lab'e dokunma yok. Tennis Lab paper-trade modu, ayrı worktree, ayrı state olarak kalır.
- ❌ NRFI pricer (likidite ~$954/maç — Polymarket'te ölü). Eski DRAFT'ta vardı, ana bot integration'a girmiyor.
- ❌ F5 / inning props / player props.
- ❌ Yeni dashboard tab. Mevcut active/exited tabları yeterli.
- ❌ Shadow mode / paper trading dönemi. Kullanıcı kararı: canlı bahis.

---

## 8. Sport_rules Değişiklik Önerisi

```python
"mlb": {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 3.0,
    ...mevcut...
    "submarket_anchor": {
        "moneyline": "bookmaker",
        "totals": "model",
        "run_line": "model",
    },
},
```

`anchor_source(sport_tag, market_type)` yardımcı fonksiyonu yukarıdaki dict'i okur.

---

## 9. Açık Sorular (Implementation Plan'da Karar)

1. **Rate cache backend:** jsonl (basit) mı sqlite (sorgulanabilir) mı? Spec öncesi seçim: jsonl, başlangıç için yeterli; sonra sqlite migration ayrı task.
2. **Model çalıştırma sıklığı:** Her market scan cycle'ında full simulation (yavaş) mı, T-30 minute cache (hızlı) mı? Spec önerisi: T-30 cache + lineup change tetikleyici recompute.
3. **Edge threshold:** Başlangıç değeri? Tennis Lab `min_edge = 0.05`. MLB için aynı mı, farklı mı? Plan'da empirical başlangıç + ilk hafta gözlem sonrası ayar.
4. **Statcast lookback:** Pitcher rate posterior için kaç sezon? Marcel 5/4/3 ağırlık → 3 sezon. Plan'a sabit.

---

## 10. Başarı Kriteri

- [ ] MLB totals + run-line market'lerinde model anchor ile gerçek bahis girer.
- [ ] Bot zaten aldığı MLB ML trade'lerine ek olarak bu market'leri de görür.
- [ ] Dashboard'da MLB totals/run-line trade'leri diğer trade'lerle aynı listede.
- [ ] Tennis Lab davranışı etkilenmez (regression yok).
- [ ] `pytest -q` tümü yeşil.
- [ ] Backtest accuracy ≥ %52 (raw — kalibrasyon sonrası min beklenti; spec değil plan'da test edilecek).

---

## 11. Sonraki Adım

Kullanıcı onayından sonra: `superpowers:writing-plans` ile implementation plan yazılır. Plan: domain modüllerinin TDD sırası (rate_shrinker → log5 → markov → inning → game → pricer → adapter → engine → scanner dispatch), her aşama için ayrı task.

Tahmini boyut: 18-25 task, her biri 30dk-2sa, toplam ~3-5 gün full-time implementasyon. Plan dosyası implementation sırasında task-by-task checkbox ilerleyecek.
