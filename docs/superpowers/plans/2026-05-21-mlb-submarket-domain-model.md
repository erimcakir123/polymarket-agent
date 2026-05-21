# MLB Submarket Domain Model — Implementation Plan (Plan 2 / 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax. Each task's detailed brief is built per-dispatch (this plan is outline format).

**Goal:** `src/domain/mlb_submarket/` altına 5-katmanlı saf domain math kur: rate shrinker → Log5 PA outcome → 24-state Markov → inning sim → game sim → totals/spread pricers. Plan 1'in mock engine'inin yerini alacak gerçek model. Saf, I/O'suz, deterministik (Monte Carlo'lar seed'li).

**Architecture:** Pure functional pipeline. Her modül tek sorumluluk, pure function (numpy isteğe bağlı). Layer ↑→↓: rate → PA outcome → state transition → inning runs → game runs → market price. ARCH_GUARD Kural 2 (no domain I/O) bütün dosyalarda zorunlu.

**Tech Stack:** Python 3.12+, numpy (convolution + Monte Carlo), pytest. Yeni paket: `numpy` (requirements.txt'e eklenir — Plan 2 öncesi check).

**Spec Reference:** [`docs/superpowers/specs/2026-05-21-mlb-submarket-mainbot-integration-design.md`](../specs/2026-05-21-mlb-submarket-mainbot-integration-design.md) §2 (akademik temel) ve §3 (5-katmanlı mimari).

**Önemli prensipler:**
- TDD: her task failing test → impl → passing → commit.
- ARCH_GUARD self-check her edit öncesi (8 madde).
- No drift: edit sonrası grep ile orphan ref kontrolü.
- No dead code: yazılan her fonksiyon başka modülde çağrılıyor olmalı.
- Per-task detail: implementer subagent dispatch'ında **bu plan'daki outline + spec akademik referansı** birleştirilir.

---

## File Structure (Plan 2'de oluşturulacak)

```
src/domain/mlb_submarket/__init__.py
src/domain/mlb_submarket/edge_candidate.py            # T1
src/domain/mlb_submarket/league_constants.py          # T2
src/domain/mlb_submarket/rate_shrinker.py             # T3
src/domain/mlb_submarket/handedness_adjust.py         # T4
src/domain/mlb_submarket/park_factor_adjust.py        # T5
src/domain/mlb_submarket/weather_adjust.py            # T6
src/domain/mlb_submarket/tto_adjust.py                # T7
src/domain/mlb_submarket/log5.py                      # T8
src/domain/mlb_submarket/pa_outcome.py                # T9 (dispatcher)
src/domain/mlb_submarket/base_out_states.py           # T10
src/domain/mlb_submarket/transition_matrix.py         # T11
src/domain/mlb_submarket/markov.py                    # T12
src/domain/mlb_submarket/lineup_order.py              # T13
src/domain/mlb_submarket/bullpen_segmenter.py         # T14
src/domain/mlb_submarket/inning_simulator.py          # T15
src/domain/mlb_submarket/game_simulator.py            # T16
src/domain/mlb_submarket/totals_pricer.py             # T17
src/domain/mlb_submarket/spread_pricer.py             # T18

tests/unit/domain/mlb_submarket/__init__.py
tests/unit/domain/mlb_submarket/test_<each_module>.py
```

**Toplam tahmini:** 18 modül × ~150 satır + testler. Hiçbir dosya 400 satır limitini aşmaz.

---

## Task 1: edge_candidate.py — dataclass (foundation)

**Dosyalar:**
- Create: `src/domain/mlb_submarket/edge_candidate.py`
- Test: `tests/unit/domain/mlb_submarket/test_edge_candidate.py`

**Spec:** `EdgeCandidate` frozen dataclass — model_p, market_p, edge (signed), market_type ("totals"|"run_line"), line (float).

**TDD steps:**
1. Test: edge magnitude pozitif (`abs(edge) > 0`); model_p ∈ [0,1]; market_type literal check.
2. Run → fail (ImportError).
3. Impl: `@dataclass(frozen=True)`, fields + `__post_init__` validation (raise ValueError if model_p out of [0,1] or market_type invalid).
4. Run → pass.
5. Commit: `feat(mlb): edge_candidate dataclass (SPEC-R Plan 2 T1)`

**Bağımlılık:** Yok. Foundation.

---

## Task 2: league_constants.py — MLB lig ortalama PA outcome rate'leri

**Dosyalar:**
- Create: `src/domain/mlb_submarket/league_constants.py`
- Test: `tests/unit/domain/mlb_submarket/test_league_constants.py`

**Spec:** Modül seviyesi `LEAGUE_PA_RATES: dict[str, float]` — 2023-2025 MLB ortalama (kaynak: Fangraphs). Outcome'lar: K (~22.5%), BB (~8.5%), HBP (~1.1%), HR (~3.0%), single (~14.0%), double (~4.5%), triple (~0.4%), out_in_play (~46.0%). Sum ≈ 1.0 ± 0.001.

**TDD steps:**
1. Test: sum(LEAGUE_PA_RATES.values()) ≈ 1.0 (tolerance 1e-3); her oran > 0; key set tam (K, BB, HBP, HR, 1B, 2B, 3B, OUT_IN_PLAY).
2. Run → fail.
3. Impl: dict + comment her oranın kaynak referansı (Fangraphs 2023-2025 league average).
4. Pass.
5. Commit: `feat(mlb): league_constants — 2023-2025 PA outcome rates (SPEC-R Plan 2 T2)`

**Bağımlılık:** Yok.

---

## Task 3: rate_shrinker.py — Empirical Bayes Beta posterior

**Dosyalar:**
- Create: `src/domain/mlb_submarket/rate_shrinker.py`
- Test: `tests/unit/domain/mlb_submarket/test_rate_shrinker.py`

**Spec:** İki public fonksiyon:
- `shrink_beta(observed_x: int, observed_n: int, prior_alpha: float, prior_beta: float) -> float` → posterior mean = (α + x) / (α + β + n) (Beta-Binomial conjugate; David Robinson — varianceexplained.org).
- `marcel_weight(observed_seasons: list[tuple[float, int]], weights: tuple[float, ...] = (5, 4, 3)) -> float` → weighted average of (rate, n) tuples ile Marcel projection ağırlıkları (Tom Tango). Genişletilebilir (sezon sayısı > weights uzunluğu olursa hata).

**TDD steps:**
1. Test:
   - `shrink_beta(50, 100, alpha=10, beta=10)` ≈ (10+50)/(10+10+100) = 60/120 = 0.5.
   - n=0 sınır → prior mean = α/(α+β).
   - `marcel_weight([(0.10, 100), (0.08, 80), (0.06, 60)])` = (5×0.10×100 + 4×0.08×80 + 3×0.06×60) / (5×100 + 4×80 + 3×60). Hesapla, assert equal.
   - Edge: x > n → ValueError.
2. Run → fail.
3. Impl: pure functions, no I/O, type hints, formula yorum satırı + citation.
4. Pass.
5. Commit: `feat(mlb): rate_shrinker — empirical Bayes Beta + Marcel weights (SPEC-R Plan 2 T3)`

**Bağımlılık:** Yok.

---

## Task 4: handedness_adjust.py — L/R platoon split

**Dosyalar:**
- Create: `src/domain/mlb_submarket/handedness_adjust.py`
- Test: `tests/unit/domain/mlb_submarket/test_handedness_adjust.py`

**Spec:** `platoon_multiplier(batter_hand: str, pitcher_hand: str, outcome: str) -> float`. Hand: "L"|"R"|"S" (switch). 4 kombinasyon (LvL, LvR, RvL, RvR) için outcome bazlı multiplier dict. Switch batter pitcher hand'inin tersi seçilir (opposite). Bilinmeyen kombinasyon → 1.0 (no adjust).

**Multiplier kaynakları:** Lifetime MLB splits (~2010-2020 average). Örnek değerler:
- LvL: K +15% (1.15), HR -8% (0.92)
- LvR: K -8% (0.92), HR +8% (1.08)
- RvR: K +5% (1.05), HR -3% (0.97)
- RvL: K -10% (0.90), HR +12% (1.12)

**TDD steps:**
1. Test: bilinmeyen outcome → 1.0; switch batter LvP=R → LvR multiplier'ı; unknown hand → 1.0.
2. Fail → impl (nested dict lookup) → pass.
3. Commit: `feat(mlb): handedness_adjust — L/R platoon multipliers (SPEC-R Plan 2 T4)`

**Bağımlılık:** Yok.

---

## Task 5: park_factor_adjust.py — Component-level park

**Dosyalar:**
- Create: `src/domain/mlb_submarket/park_factor_adjust.py`
- Test: `tests/unit/domain/mlb_submarket/test_park_factor_adjust.py`

**Spec:** Component-level park factor (HR vs 1B/2B/3B ayrı — total factor değil çünkü double-count riski). Hardcoded constants (`PARK_FACTORS: dict[str, dict[str, float]]`) — kaynak Baseball Savant/Sabermetrics Library. Örnekler:
- Coors Field: HR=1.18, 1B=1.05, 2B=1.10, 3B=1.30
- Petco Park: HR=0.92, 1B=0.97, 2B=0.95, 3B=0.85

Public fonksiyon: `park_multiplier(park_id: str, outcome: str) -> float`. Bilinmeyen park → 1.0.

**Double-count guard:** Test'te yorum açıkça yazılsın: Layer 1 pa_outcome ASLA hem total park hem component park uygulamamalı.

**TDD steps:**
1. Test: Coors HR=1.18; Petco HR=0.92; unknown park → 1.0; unknown outcome → 1.0.
2. Fail → impl → pass.
3. Commit: `feat(mlb): park_factor_adjust — component-level (SPEC-R Plan 2 T5)`

**Bağımlılık:** Yok.

---

## Task 6: weather_adjust.py — Wind/temp/humidity → HR rate

**Dosyalar:**
- Create: `src/domain/mlb_submarket/weather_adjust.py`
- Test: `tests/unit/domain/mlb_submarket/test_weather_adjust.py`

**Spec:** `weather_hr_multiplier(wind_mph_to_cf: float, temp_f: float, humidity_pct: float) -> float`.
- Rüzgâr CF'ye doğru pozitif → HR artar (+1% per mph, max +20% at 20mph CF wind).
- Rüzgâr CF'den uzağa negatif → HR azalır.
- Sıcaklık linear: 60°F baseline; her 10°F üzeri +1.5% HR. Altı simetrik (azalır).
- Humidity: yüksek → HR -0.5% per 10% humidity (drag artar).

Output: multiplier ∈ (0.5, 1.5) range, sınırlanır.

**TDD steps:**
1. Test cases:
   - Baseline (0 wind, 60°F, 50% humidity) ≈ 1.0.
   - 15 mph CF wind, 80°F, 30% humidity → > 1.0.
   - −10 mph wind (uzağa), 50°F → < 1.0.
   - Aşırı (50 mph wind) → clip to 1.5.
2. Fail → impl → pass.
3. Commit: `feat(mlb): weather_adjust — wind/temp/humidity HR multiplier (SPEC-R Plan 2 T6)`

**Bağımlılık:** Yok.

---

## Task 7: tto_adjust.py — Times Through Order penalty

**Dosyalar:**
- Create: `src/domain/mlb_submarket/tto_adjust.py`
- Test: `tests/unit/domain/mlb_submarket/test_tto_adjust.py`

**Spec:** Pitcher 3. ve sonrası TTO'da bozulur (familiarity effect — Mitchel Lichtman). `tto_multiplier(times_through: int, outcome: str) -> float`. 1TT: 1.0 (baseline). 2TT: K -2%, HR +5%. 3TT: K -8%, HR +12%. 4TT+: aynı 3TT (extreme).

**TDD steps:**
1. Test: 1TT all outcomes = 1.0; 3TT K = 0.92; clip times_through ≥ 4 to 4TT behavior.
2. Fail → impl → pass.
3. Commit: `feat(mlb): tto_adjust — times-through-order penalty (SPEC-R Plan 2 T7)`

**Bağımlılık:** Yok.

---

## Task 8: log5.py — Haechrel multi-class Log5

**Dosyalar:**
- Create: `src/domain/mlb_submarket/log5.py`
- Test: `tests/unit/domain/mlb_submarket/test_log5.py`

**Spec:** Multi-class Log5 (Matt Haechrel — SABR Journal 2014, "Estimating League Average Skill Sets"). Generalizes binary Log5 to k-class outcomes via odds ratio:

```
P(outcome=i | batter, pitcher) ∝ (batter_p_i / league_p_i) * (pitcher_p_i / league_p_i) * league_p_i
```

Normalize so sum = 1.0.

Public function: `log5_multiclass(batter_rates: dict[str, float], pitcher_rates: dict[str, float], league_rates: dict[str, float]) -> dict[str, float]`. Tüm input'larda aynı key set (8 outcome). Output normalized.

**Edge cases (test'te zorunlu):**
- Batter rates == league rates → output = pitcher rates.
- Pitcher rates == league rates → output = batter rates.
- Both equal league → output = league.
- Birinde 0 rate → corresponding output = 0.

**Bias note:** Morey & Cohen 2015 (JSA): Log5 elite × weak extremlerde sistematik bias verir. Plan 4 backtest'te flag.

**TDD steps:**
1. 4 edge case test + 1 normal matchup test (assert sum=1).
2. Fail → impl (numpy isteğe bağlı, dict comprehension yeterli) → pass.
3. Commit: `feat(mlb): log5 multi-class — Haechrel SABR 2014 (SPEC-R Plan 2 T8)`

**Bağımlılık:** Yok (sadece dict input/output).

---

## Task 9: pa_outcome.py — Layer 1 dispatcher

**Dosyalar:**
- Create: `src/domain/mlb_submarket/pa_outcome.py`
- Test: `tests/unit/domain/mlb_submarket/test_pa_outcome.py`

**Spec:** Pure orchestrator. Single function `compute_pa_outcome(batter_rates, pitcher_rates, context) -> dict[str, float]`. Context = TypedDict (park_id, batter_hand, pitcher_hand, times_through, wind_mph_to_cf, temp_f, humidity_pct, league_rates=LEAGUE_PA_RATES).

**Sıra (kritik — double-count önler):**
1. Handedness adjust → batter_rates ve pitcher_rates üzerine multiplier.
2. TTO adjust → pitcher_rates üzerine (sadece pitcher).
3. Log5 multiclass → matchup-specific distribution.
4. Park factor + weather → SADECE matchup distribution üzerine (batter/pitcher rates değil — double-count!).
5. Renormalize → sum = 1.0.

**TDD steps:**
1. Test: belirli bir input için step-by-step expected output (mock all adjust modules return identity → log5 only).
2. Park factor olmasa output ≠ park factor ile output (sanity: factor uygulanıyor).
3. Final output sum = 1.0 (tolerance 1e-6).
4. Fail → impl (importlar T3-T8'den) → pass.
5. Commit: `feat(mlb): pa_outcome — Layer 1 dispatcher (SPEC-R Plan 2 T9)`

**Bağımlılık:** T2, T4, T5, T6, T7, T8.

---

## Task 10: base_out_states.py — 24-state enum

**Dosyalar:**
- Create: `src/domain/mlb_submarket/base_out_states.py`
- Test: `tests/unit/domain/mlb_submarket/test_base_out_states.py`

**Spec:** 24 state = 8 baserunner configs × 3 out counts (0, 1, 2). State ID encoding: `(outs, runner_1B, runner_2B, runner_3B)` tuple veya `state_index: 0..23`. Helper functions:
- `encode(outs: int, runners: tuple[bool, bool, bool]) -> int` (0-23)
- `decode(idx: int) -> tuple[int, tuple[bool, bool, bool]]`
- `INITIAL_STATE: int = 0` (0 out, bases empty)
- `INNING_ENDS: frozenset[int]` = {state'ler 3 out olan} (her base config × 3 out)

**TDD steps:**
1. Test roundtrip: encode(decode(x)) == x for all x ∈ [0, 23].
2. INITIAL_STATE = 0 → (0 out, no runners).
3. INNING_ENDS contains states 21, 22, 23 (3-out family).
4. Fail → impl → pass.
5. Commit: `feat(mlb): base_out_states — 24-state enum (SPEC-R Plan 2 T10)`

**Bağımlılık:** Yok.

---

## Task 11: transition_matrix.py — Tango RE Matrix data

**Dosyalar:**
- Create: `src/domain/mlb_submarket/transition_matrix.py`
- Test: `tests/unit/domain/mlb_submarket/test_transition_matrix.py`

**Spec:** Hardcoded Tango Run Expectancy Matrix (1950-2015 MLB average — Tom Tango, *The Book* 2007). 24-state × expected runs scored from that state to end of inning. Sample values:
- (0 out, bases empty): 0.481
- (0 out, runner on 3B): 1.413
- (2 out, bases empty): 0.098
- (0 out, bases loaded): 2.282

(Tam tablo 24 satır — implementer subagent kaynaktan hardcoded array yazar.)

Public:
- `RE_MATRIX: dict[int, float]` (state_index → expected runs)
- `expected_runs(state_idx: int) -> float` lookup helper.

**TDD steps:**
1. Test: RE_MATRIX 24 entry; tüm değerler ≥ 0; INITIAL_STATE ≈ 0.481 (well-known).
2. expected_runs monoton: 0-out bases empty < 0-out runner-on-3B (sanity).
3. Fail → impl → pass.
4. Commit: `feat(mlb): transition_matrix — Tango RE Matrix data (SPEC-R Plan 2 T11)`

**Bağımlılık:** T10.

---

## Task 12: markov.py — Layer 2 state transition

**Dosyalar:**
- Create: `src/domain/mlb_submarket/markov.py`
- Test: `tests/unit/domain/mlb_submarket/test_markov.py`

**Spec:** Layer 2: PA outcome + current state → new state + runs scored. Function `transition(state_idx: int, pa_outcome: str) -> tuple[int, int]` (new_state_idx, runs_scored).

**Outcome mapping (deterministic):**
- K, OUT_IN_PLAY: out_count += 1, runners unchanged. (Special: SAC FLY — if 1+ out and runner on 3B, +1 run on out_in_play under some prob — handle separately or in inning_simulator.)
- BB, HBP: cascade — batter→1B; if 1B occupied → push to 2B; cascade through; runs if pushed home.
- 1B (single): batter→1B; runner on 1B → 2B; runner on 2B → 3B (held conservatively) or home (aggressive — use 50/50 split or aggregate via expected runs); runner on 3B → home (+1 run). Simplification: 2B→home advance probability ~50%; document constant in code.
- 2B (double): batter→2B; all runners advance 2; 3B→home, 2B→home, 1B→3B (or home with prob).
- 3B (triple): batter→3B; all runners home.
- HR: batter+all runners home.

Double-play (DP) handling: out_in_play with runner on 1B and 0/1 out → 50% DP probability. (Simplification — see implementer subagent brief for exact MLB DP rates.)

**TDD steps:**
1. Test happy paths: bases empty + K → outs+1, 0 runs.
2. Bases loaded + HR → bases empty, +4 runs.
3. Runner on 3B + 0 out + 1B (single) → runner on 1B, +1 run.
4. DP scenario (1B runner, 0 out, OUT_IN_PLAY) → some prob of double out.
5. Fail → impl → pass.
6. Commit: `feat(mlb): markov — state transition + DP/SAC FLY (SPEC-R Plan 2 T12)`

**Bağımlılık:** T10, T11.

---

## Task 13: lineup_order.py — Inning'lere göre PA pozisyonu

**Dosyalar:**
- Create: `src/domain/mlb_submarket/lineup_order.py`
- Test: `tests/unit/domain/mlb_submarket/test_lineup_order.py`

**Spec:** Lineup 9 batter, rotating. Function `batter_at_pa(lineup_index: int, total_pa_so_far: int) -> int`. Plus `times_through_order(total_pa_so_far: int) -> int` (TTO calculation: 1-9 = 1TT, 10-18 = 2TT, 19-27 = 3TT, 28+ = 4TT).

**TDD steps:**
1. Test: PA 0 → lineup 0; PA 9 → lineup 0; PA 13 → lineup 4.
2. TTO: PA 5 → 1; PA 14 → 2; PA 30 → 4.
3. Fail → impl → pass.
4. Commit: `feat(mlb): lineup_order + TTO (SPEC-R Plan 2 T13)`

**Bağımlılık:** Yok.

---

## Task 14: bullpen_segmenter.py — Leverage-aware pitcher selection

**Dosyalar:**
- Create: `src/domain/mlb_submarket/bullpen_segmenter.py`
- Test: `tests/unit/domain/mlb_submarket/test_bullpen_segmenter.py`

**Spec:** 3-segment bullpen: starter → middle (innings 6-7) → setup (8) → closer (9). Game state (inning, lead/deficit) belirler. Function `select_pitcher(inning: int, score_diff: int, starter_rates: dict, bullpen: dict[str, dict]) -> dict[str, float]`. bullpen = {"middle": rates, "setup": rates, "closer": rates}.

**Leverage rule:**
- Inning 1-5: starter.
- Inning 6-7: middle relief.
- Inning 8: setup if |score_diff| ≤ 3, else mop-up (middle).
- Inning 9: closer if home leads 1-3, else middle.

**TDD steps:**
1. Test: inning 3 → starter rates; inning 9, +2 lead → closer; inning 9, +6 blowout → middle.
2. Fail → impl → pass.
3. Commit: `feat(mlb): bullpen_segmenter — 3-segment leverage (SPEC-R Plan 2 T14)`

**Bağımlılık:** Yok.

---

## Task 15: inning_simulator.py — Layer 3 inning run distribution

**Dosyalar:**
- Create: `src/domain/mlb_submarket/inning_simulator.py`
- Test: `tests/unit/domain/mlb_submarket/test_inning_simulator.py`

**Spec:** Bir yarı-inning'i simule eder. `simulate_inning(batter_rates_list: list[dict[str, float]], lineup_start_idx: int, mc_iterations: int = 10_000, seed: int = 42) -> dict[int, float]`. Returns `{runs_scored: probability}`.

**Algoritma (Monte Carlo):**
```
for iteration in range(mc_iterations):
    state = INITIAL_STATE
    runs = 0
    lineup_idx = lineup_start_idx
    while state not in INNING_ENDS:
        rates = batter_rates_list[lineup_idx]
        outcome = sample_outcome(rates, rng)   # use np.random.default_rng(seed+iteration)
        state, scored = transition(state, outcome)
        runs += scored
        lineup_idx = (lineup_idx + 1) % 9
    counts[runs] += 1
return {r: c / mc_iterations for r, c in counts.items()}
```

**Reproducibility:** Always pass seed; same input → same output. Test verifier.

**TDD steps:**
1. Test: dummy rates (all K=1.0) → 100% prob 0 runs (3 K = 3 outs).
2. Dummy all HR=1.0 → all iterations score many runs (no inning end via outs).
   - Wait — if rates have 0 K and 0 OUT_IN_PLAY, never 3 outs. Test'te catch: should raise or detect infinite loop. Use bounded `max_pa_per_inning=30` safety.
3. Mid-realistic rates + seed → known output.
4. Fail → impl → pass.
5. Commit: `feat(mlb): inning_simulator — Monte Carlo run distribution (SPEC-R Plan 2 T15)`

**Bağımlılık:** T2, T9, T10, T12, T13.

---

## Task 16: game_simulator.py — Layer 4 9-inning convolution

**Dosyalar:**
- Create: `src/domain/mlb_submarket/game_simulator.py`
- Test: `tests/unit/domain/mlb_submarket/test_game_simulator.py`

**Spec:** Tek bir takım için tüm 9 inning'i convolve eder → team total run distribution. 9-inning (normal) ve 7-inning (DH game 2) ayrı code path.

**Algoritma:**
```
def team_run_distribution(inning_dists: list[dict[int, float]]) -> dict[int, float]:
    """inning_dists: her inning için ayrı simulate_inning output'u (9 öğe).
    
    Convolution (numpy.convolve veya pure Python):
    total[k] = sum_{i+j+...=k} prod(inning_i[outcome_i])
    """
```

Plus `simulate_game(home_pa_rates, away_pa_rates, ..., dh_game: bool = False) -> tuple[dict[int, float], dict[int, float]]` (home_runs_dist, away_runs_dist). DH ise 7 inning, normal 9.

**TDD steps:**
1. Test: 9 inning'in hepsi {0: 1.0} → game dist {0: 1.0}.
2. 9 inning'in hepsi {1: 1.0} → game dist {9: 1.0}.
3. 9 inning karışık → convolution doğru (assertion: sum probabilities = 1.0).
4. DH = True → 7 inning convolve.
5. Fail → impl (numpy.convolve önerilir) → pass.
6. Commit: `feat(mlb): game_simulator — 9-inning convolution + DH (SPEC-R Plan 2 T16)`

**Bağımlılık:** T15.

---

## Task 17: totals_pricer.py — Layer 5 totals price

**Dosyalar:**
- Create: `src/domain/mlb_submarket/totals_pricer.py`
- Test: `tests/unit/domain/mlb_submarket/test_totals_pricer.py`

**Spec:** Home + away run distributions → P(total ≥ line) ve P(total < line) (over/under).

**Algoritma:**
```
def totals_probability(home_dist: dict[int, float], away_dist: dict[int, float], line: float) -> tuple[float, float]:
    """Returns (p_over, p_under).
    
    Total = convolve(home, away). 
    Eğer line int ise: P(over) = sum(p[k] for k > line). P(push) = p[int(line)].
    Eğer line .5 ise: P(over) = sum(p[k] for k >= ceil(line)). Push yok.
    """
```

**TDD steps:**
1. Test: home={3: 1.0}, away={2: 1.0}, line=4.5 → p_over=1.0, p_under=0.0.
2. line=5.5 → p_over=0.0, p_under=1.0.
3. line=4 (int) → p_over+p_under = 1.0 - p_push, p_push = home[3]*away[2]+... (toplam 5).
4. Fail → impl → pass.
5. Commit: `feat(mlb): totals_pricer — P(total ≥ line) (SPEC-R Plan 2 T17)`

**Bağımlılık:** T16.

---

## Task 18: spread_pricer.py — Layer 5 run-line price

**Dosyalar:**
- Create: `src/domain/mlb_submarket/spread_pricer.py`
- Test: `tests/unit/domain/mlb_submarket/test_spread_pricer.py`

**Spec:** Home/away run distributions → P(home_team covers ±1.5 spread).

**Algoritma:**
```
def spread_probability(home_dist: dict[int, float], away_dist: dict[int, float], home_line: float) -> tuple[float, float]:
    """Returns (p_home_covers, p_away_covers).
    
    Spread = home_runs - away_runs.
    P(home_covers @ home_line=-1.5) = P(spread > 1.5) = sum over (h,a) where h-a > 1.5.
    P(home_covers @ home_line=+1.5) = P(spread > -1.5).
    """
```

**TDD steps:**
1. Test: home={5:1.0}, away={3:1.0}, home_line=-1.5 → p_home_covers=1.0 (5-3=2>1.5).
2. home_line=+1.5 → p_home_covers=1.0 (5-3=2>-1.5 anywhere; daha kolay).
3. home={2:1.0}, away={4:1.0}, home_line=-1.5 → p_home_covers=0.0.
4. Push handling: spread = exactly line + 0.5 → no push (.5 lines).
5. Fail → impl → pass.
6. Commit: `feat(mlb): spread_pricer — P(home covers run-line) (SPEC-R Plan 2 T18)`

**Bağımlılık:** T16.

---

## Final Tasks (DECISIONS update + plan dosyası sil)

**Plan 2 tamamlandığında:**
1. Full test suite: `pytest -q` — tüm yeni testler yeşil, regression yok.
2. DECISIONS.md §B'ye SPEC-R Plan 2 kaydı ekle (Plan 1 SPEC-R kaydının altına extension):
   ```markdown
   **Plan 2 (Domain Model) tamamlandı (2026-05-XX):** 18 saf domain modülü 
   src/domain/mlb_submarket/ altında. Rate shrinker (Empirical Bayes Beta), 
   Log5 multi-class (Haechrel SABR 2014), 24-state Markov (Tango RE Matrix), 
   inning Monte Carlo (10k iter seedlı), 9-inning convolution, totals/spread 
   pricers. Saf I/O'suz domain. Bağımlılık: numpy.
   ```
3. Plan dosyasını sil (CLAUDE.md kuralı):
   ```bash
   git rm docs/superpowers/plans/2026-05-21-mlb-submarket-domain-model.md
   git commit -m "chore(plans): SPEC-R Plan 2 (domain model) tamamlandı — kayıt DECISIONS §B"
   ```

---

## Self-Review (yazım sonrası kontrol)

- [x] 18 task, her biri tekil sorumluluk
- [x] Dependency order doğru (T1 foundation → T9 dispatcher → T12 markov → T15-16 simulators → T17-18 pricers)
- [x] Her task TDD steps + concrete commit message
- [x] Akademik formüller citation'lı (Haechrel SABR 2014, Tango RE Matrix, Marcel weights, Mitchel Lichtman TTO, Morey & Cohen bias note)
- [x] Edge case'ler her task'ta belirtildi
- [x] Bağımlılık zinciri her task'ta yazılı (subagent dispatch sıralaması doğrular)
- [x] Dosya boyutu hedef: her modül 100-200 satır (yaklaşık), 400 satır limiti güvenli
- [x] numpy bağımlılığı tek bir yerde (Plan 2 başlangıçta requirements.txt update task'ı subagent dispatch'ında brief edilir)
- [x] No drift / no dead code: her modül başka modülde çağrılır (T9 T2-T8 import; T15 T12 T13 import; T16 T15 import; T17 T18 T16 import)

**Implementer dispatch protokolü:**
Her task subagent'a şu paket gönderilir:
1. Task outline'ı (bu plan'dan)
2. Spec referansı (SPEC-R integration spec §2, §3 ilgili kısımları)
3. Bağımlılık modülleri varsa onların gerçek dosyalarının özeti
4. ARCH_GUARD self-check zorunluluğu
5. Commit message exact format

**Notes for implementer subagents:**
- Akademik formüllerin numerik doğruluğunu test'te assert et (well-known Tango RE Matrix değerleri sentinel olarak kullanılabilir).
- Monte Carlo testlerinde seed sabitlemek zorunlu (reproducibility).
- numpy 2.x ile uyumlu kod yaz.
- Domain Kural 2: import requests/httpx/file I/O ASLA bu modüllerde olmamalı.

Plan 2 hazır.
