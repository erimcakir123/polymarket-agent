# MLB Submarket Wire-Up + Backtest — Implementation Plan (Plan 4 / 4)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Plan 1 (foundation), Plan 2 (domain model), Plan 3 (infrastructure) parçalarını birleştir. Gerçek `MlbSubmarketEngine` yazılır, factory inject eder, mock engine yerini alır. Backtest script ile tarihsel doğrulama. Bot reload sonrası canlı bahis akar.

**Architecture:** `MlbSubmarketEngine` strategy/entry katmanında. `process(market: MarketData) -> Signal | None` Protocol'üne uyar (Plan 1'de tanımlı). İçeride: data fetch (Plan 3 clients) → rate shrink (Plan 2 rate_shrinker + rate_cache) → PA outcome (Plan 2 pa_outcome) → simulators → pricers → EdgeCandidate → adapter → Signal. Dependency injection.

**Tech Stack:** Mevcut + datetime/pathlib parsing.

**Spec Reference:** [`docs/superpowers/specs/2026-05-21-mlb-submarket-mainbot-integration-design.md`](../specs/2026-05-21-mlb-submarket-mainbot-integration-design.md) §3.

**Prensipler:**
- TDD: engine için mock'lanmış Plan 2+3 modülleriyle birim test, sonra integration test (gerçek modüller, mock HTTP).
- ARCH_GUARD: strategy katmanı, infra ↑ ve domain ↓ import OK (üst→alt). Domain import OK çünkü strategy domain'i kullanır.
- No drift: Plan 1 placeholder warning ("engine impl Plan 4'te gelecek") kaldırılır.
- No dead code: Plan 1 protocol kullanılır. Mock helper test'lerden silinir.
- TODO-DRY (Plan 1 final review notu): `_persist_model_entry` ve `_execute_entry` ortak helper'a çıkarılır.

---

## File Structure

```
src/strategy/entry/mlb_signal_adapter.py              # T1 — EdgeCandidate → Signal
src/strategy/entry/mlb_submarket_engine.py            # T2 — Gerçek engine
scripts/mlb_submarket_backtest.py                     # T4 — Backtest script
src/orchestration/entry_processor.py                  # T3 — TODO-DRY persist refactor + factory warning kaldırma
src/orchestration/factory.py                          # T3 — Gerçek engine inject

tests/unit/strategy/entry/test_mlb_signal_adapter.py
tests/unit/strategy/entry/test_mlb_submarket_engine.py
tests/unit/orchestration/test_factory_mlb_real_engine.py
tests/integration/test_mlb_submarket_e2e.py
```

---

## Task 1: mlb_signal_adapter.py — EdgeCandidate → Signal

**Dosyalar:** `src/strategy/entry/mlb_signal_adapter.py` + test.

**Spec:** Saf fonksiyon `mlb_candidate_to_signal(candidate: EdgeCandidate, market: MarketData, tier: str, fixed_bet_usdc: dict[str, float]) -> Signal`. Tennis adapter pattern'inin klonu. P(YES) anchor preserved (model_p direkt anchor_probability).

**TDD steps:**
1. Test: positive edge → Direction.BUY_YES; negative → BUY_NO.
2. Test: anchor_probability = candidate.model_p (P(YES), DEĞİŞTİRİLMEZ).
3. Test: entry_reason = EntryReason.MLB_SUBMARKET.
4. Test: bookmaker_prob=0.0, num_bookmakers=0, has_sharp=False.
5. Test: sport_tag = "baseball_mlb".
6. Test: size_usdc = fixed_bet_usdc[tier] (A → $50, B → $30).
7. Fail → impl → pass.
8. Commit: `feat(mlb): mlb_signal_adapter — EdgeCandidate → Signal (SPEC-R Plan 4 T1)`

---

## Task 2: mlb_submarket_engine.py — Gerçek engine orchestrator

**Dosyalar:** `src/strategy/entry/mlb_submarket_engine.py` + test.

**Spec:** Sınıf `MlbSubmarketEngine`:
```python
class MlbSubmarketEngine:
    def __init__(
        self,
        statsapi: StatsApiClient,
        statcast: StatcastClient,
        weather: WeatherClient,
        rate_cache: RateCache,
        config: MlbSubmarketConfig,
        ballpark_metadata: dict[str, dict],  # park_id → {lat, lon, cf_orientation_deg}
        league_rates: dict[str, float] | None = None,
    ): ...
    def process(self, market: MarketData) -> Signal | None:
        """Plan 1 Protocol implementation. Edge varsa Signal, yoksa None."""
```

**process() flow:**
1. Market slug'dan parse: home/away team, line, market_type (totals/run_line), date.
2. Plan 3 statsapi: schedule + probable pitchers + lineup.
3. Plan 3 rate_cache.get → varsa kullan. Yoksa Plan 3 statcast.get_batter/pitcher_rates + rate_shrinker (Marcel weights) → put cache.
4. Plan 3 weather.get_conditions → ballpark coords.
5. CF projection: weather wind_dir_deg ve ballpark cf_orientation_deg'den wind_mph_to_cf hesapla.
6. Plan 2 pa_outcome.compute_pa_outcome (her batter+pitcher matchup için) → per-batter rates list.
7. Plan 2 bullpen_segmenter (her inning için pitcher rates).
8. Plan 2 inning_simulator (her inning) + game_simulator (convolution) → home_dist, away_dist.
9. Market_type "totals" → Plan 2 totals_pricer; "run_line" → spread_pricer.
10. model_p vs market.yes_price → edge = model_p - market.yes_price.
11. abs(edge) >= config.min_edge → EdgeCandidate + adapter → Signal.
12. Else → None.

**Hata yönetimi:** Veri eksik (lineup posted değil, scratch detected, weather hatası, vs) → log INFO + return None (skip). Plan-3 client'ları StatsApiError/StatcastError/WeatherError fırlatırsa engine yakalar, log + None.

**Confidence tier:** edge magnitude → A (≥ 0.07) veya B (≥ 0.05); altı None.

**TDD steps:**
1. Test: tüm Plan 2+3 modüller mock'lanır. Engine end-to-end signal üretir mock data ile.
2. Test: edge < min_edge → None.
3. Test: lineup empty (T-90 öncesi) → None + INFO log.
4. Test: StatsApiError → None (no crash).
5. Test: rate_cache hit → statcast asla çağrılmaz (cache verimliliği).
6. Test: rate_cache miss → statcast çağrılır + put yapılır.
7. Test: scratch detected (mock detector return non-empty) → None.
8. Test: confidence tier A vs B doğru.
9. Fail → impl → pass.
10. Commit: `feat(mlb): mlb_submarket_engine — orchestrator (SPEC-R Plan 4 T2)`

---

## Task 3: Factory inject + TODO-DRY persist refactor + warning kaldırma

**Dosyalar:** `src/orchestration/factory.py`, `src/orchestration/entry_processor.py`, `src/orchestration/agent.py` (gerekirse) + test.

**Spec:**
- `factory.build_agent`: `config.mlb_submarket.enabled=True` ise gerçek `MlbSubmarketEngine` inject et. Ballpark metadata constant (hardcoded 30 ballpark — Plan 4'te tam liste, Plan 1'de 5'ti).
- Plan 1'deki warning kaldır ("engine impl Plan 4'te gelecek"). 
- TODO-DRY (Plan 1 final review notu): `_persist_model_entry` ve `_execute_entry`'nin ortak persist logic'i `_persist_filled_position(market, signal, result)` shared helper'a çıkarılır.

**TDD steps:**
1. Test: enabled=True → engine **not** None (gerçek instance).
2. Test: enabled=False → engine None (mevcut davranış).
3. Test: process_markets ve process_signals her ikisi de `_persist_filled_position` çağırır (DRY).
4. Test: persist davranışı değişmedi (mevcut tüm entry_processor testleri geçer — zero regression).
5. Fail → impl → pass.
6. Commit: `feat(mlb): factory inject real engine + TODO-DRY persist refactor (SPEC-R Plan 4 T3)`

---

## Task 4: Backtest script + accuracy ölçüm

**Dosyalar:** `scripts/mlb_submarket_backtest.py` + test (smoke).

**Spec:** Tarihsel pencere için (örn. 2024 sezon) model fiyatı vs Polymarket fiyatı + actual outcome karşılaştır.

```python
def backtest(
    start_date: str,
    end_date: str,
    season_for_rates: int,
    out_path: Path,
) -> dict[str, float]:
    """Tarihsel pencerede her MLB totals/run_line market için:
    - Model fiyatı hesapla
    - Polymarket fiyatı al (mevcut audit'ten veya manuel)
    - Actual outcome (MLB Stats API final scores)
    - Edge ölçüm: model_p vs market_p
    - Accuracy ölçüm: model favored side gerçekten kazandı mı?
    
    Returns: {n_markets, accuracy, mean_edge, sharpe_proxy}
    """
```

**TDD steps:**
1. Test: 5-game synthetic data → accuracy hesapla.
2. Test: empty window → empty result.
3. Test: outcome flip (sportsdata.io alternatif) — not in Plan 4, sadece happy path.
4. Fail → impl → pass.
5. Commit: `feat(mlb): backtest script + accuracy ölçüm (SPEC-R Plan 4 T4)`

**Backtest çıktısı (Plan 4 onayında karar):**
- Accuracy ≥ %52 → bot canlı bahis için hazır.
- < %50 → kalibrasyon hatası, Plan 2 review.

---

## Final Tasks

**Plan 4 tamamlandığında:**
1. Full test suite: `pytest -q` — tüm yeşil.
2. Backtest çalıştır: küçük pencere (örn. 7 gün, 2024 sezon Mayıs) → log accuracy.
3. **Master'a rebase + merge** (feature/mlb-submarket → master). Conflict resolution: dead-reentry cleanup master'da yapıldı, branch position.py'de hâlâ alan olabilir → branch tarafı dropla.
4. DECISIONS §B SPEC-R kaydına Plan 4 tamamlandı + accuracy notu ekle.
5. config.yaml manuel olarak `mlb_submarket.enabled: true` yapılır (kullanıcı onayıyla).
6. `python scripts/reboot.py reload` → bot yeniden başlar, MLB submarket akışı aktif.

---

## Self-Review

- [x] 4 task — adapter + engine + factory wire + backtest
- [x] Plan 1+2+3 birleştirme noktası — drift bırakmaz (placeholder + warning kaldırılır)
- [x] TODO-DRY (Plan 1 final review) çözülür
- [x] Backtest script accuracy validate eder
- [x] Master'a merge planı net (conflict resolution noted)

Plan 4 hazır.
