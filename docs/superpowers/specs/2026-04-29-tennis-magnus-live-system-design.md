# Tennis Magnus-Live System — Phased Design

**Date:** 2026-04-29
**Author:** Erim + Claude (brainstorming session)
**Status:** Draft for user review
**Approach:** Option B — paper trade first, escalate by phases. **H2H ONLY for v0-v3**; Match Total Games deferred to separate Phase 4 sub-spec.

---

## 1. Motivation

Tennis is the highest-volume Polymarket sport we don't yet trade ($36M ATP + $11M WTA). Existing exit infrastructure (`tennis_score_exit.py`) is a STUB. Building it requires a different model than NHL/NBA because tennis is bimodal (1 or 0), set-paced (no clock), and prone to fast crashes followed by potential comebacks.

Pre-conditions established during brainstorming:
- Odds API tennis coverage is THIN (~5 events per active tournament, top stadium matches only). Bookmaker triangulation safety net we use in other sports is partially absent.
- Polymarket carries match-level H2H + Match Total Games + Set Handicap markets per match. Set props (Set 1 winner, etc.) also exist but skipped.
- ESPN tennis scoreboard provides live set/game scores + serve stats per match.
- No existing serve-percentage data source in our infrastructure.

**Decision:** Build the system in phases (v0.5 paper trade → v1 simple → v2 Bayesian → v3 full), gate each phase on measured performance against real Polymarket outcomes.

---

## 2. Scope

**IN scope (this spec, v0-v3 H2H only):**
- New `src/infrastructure/apis/sackmann_client.py` — Sackmann GitHub CSV fetcher + cache
- New `src/domain/matching/tennis_player_resolver.py` — fuzzy matching across Polymarket / ESPN / Sackmann name formats
- New `src/domain/math/tennis_magnus.py` — Klaassen-Magnus + O'Malley closed-form chain (H2H only)
- New `src/domain/math/tennis_bayesian.py` — Bayesian p_serve update from in-match observations
- New `src/domain/math/tennis_momentum.py` — EWMA of recent game outcomes
- Rewrite `src/strategy/exit/tennis_score_exit.py` — multi-signal risk-adjusted EV decision (H2H only)
- New `src/orchestration/tennis_paper_logger.py` — phase-0 observation logger
- Tournament tier + surface metadata in `config.yaml` + `DECISIONS.md`
- Tests for each new module (TDD per CLAUDE.md)

**OUT of scope (deferred to separate sub-specs):**
- **Match Total Games market** — deferred to Phase 4 (separate sub-spec) once H2H model validated
- Set Handicap markets (skipped permanently — Klaassen-Magnus self-contained too risky for set-bazlı spread)
- Set 1 / Total Sets prop markets (no Odds API equivalent)
- Best of 5 Grand Slam — phase-1 launches BO3 only; BO5 added in phase-2 once BO3 validated
- Cricket/MLB/NFL/Soccer exit modules (separate scope, currently STUB)
- Magnus model for entry decision (entry stays via existing `enrich_outcome` pipeline; this spec is exit-only)

**BLOCKER (must complete first, separate spec):**
- **Telegram alarm system (cross-cutting feature)** — required for retire/ESPN-outage handling. Without it, bot is blind to two critical edge cases. See `TODO.md` for separate spec. Phase 0 paper trade can run without Telegram (no real positions), but Phase 1+ requires it.

---

## 3. Phased Rollout

| Phase | Duration | Goal | Real $ risk | Exit gate to next phase |
|---|---|---|---|---|
| **Phase -1 Telegram alarm** | 2-3 days | Cross-cutting feature, retire + outage handling | ZERO | Alarm fires on test trigger |
| **v0.5 Paper Trade (H2H only)** | 3-4 weeks | Observe 50-100 matches, log model predictions vs actual outcomes | ZERO | Magnus H2H directional accuracy ≥ 65% on logged matches |
| **v1 Simple Live (H2H only)** | 2 weeks observation | Magnus base + simple set-bazlı exit. NO Bayesian, NO momentum. BO3 only. Position cap $15. | Low ($15/match) | No structural bug, exits trigger as designed, ROI ≥ 0 over 30 matches |
| **v2 + Bayesian (H2H + BO5)** | 1 week observation | Add in-match p_serve update. Add BO5 Grand Slam support. Position cap $25. | Medium ($25/match) | Bayesian update reduces false positives by ≥ 10% vs v1 |
| **v3 + Momentum + Risk-EV (H2H)** | Steady state | Full system: Bayesian + momentum EWMA + risk-adjusted EV. Position cap $35. | Full ($35/match) | Maintained |
| **Phase 4 — Match Total Games** | Separate sub-spec | Add Match Total Games market on top of validated H2H system | TBD | Out of scope for this spec |

**Phase-0 gate is hard.** If model accuracy < 65% on paper trade, do not proceed to v1; revisit data inputs or model assumptions.

**Phase -1 (Telegram) is BLOCKING for v1+** but does NOT block v0.5 paper trade (no real positions = no urgent edge case handling needed).

---

## 4. Phase 0 — Paper Trade (start here)

### 4.1 What it does

Bot runs the full Magnus model on every eligible tennis market but **does not place trades**. For each match in the eligible universe, log:

- Pre-match: Model P(win) for both players + entry decision the bot WOULD have made
- Per-game during match: Updated P(win), updated bid prices, hypothetical exit decision
- Post-match: Actual winner + final stats

Output: Single JSONL file `logs/audit/tennis_paper_trade.jsonl` with one record per match.

### 4.2 What gets logged per match

```
{
  "match_id": "atp-medvedev-cobolli-2026-04-28",
  "tournament": "Madrid Open ATP",
  "surface": "clay",
  "format": "BO3",
  "player_a": {"name": "Medvedev", "sackmann_p_serve": 0.689, ...},
  "player_b": {"name": "Cobolli", "sackmann_p_serve": 0.642, ...},
  "pre_match": {
    "model_p_win_a": 0.628,
    "polymarket_a_price": 0.55,
    "edge": 0.078,
    "would_enter": true,
    "would_size_usdc": 35
  },
  "in_match_log": [
    {"game_n": 1, "set": 1, "score": "1-0", "model_p_win_a": 0.65, "bid": 0.56, "would_action": "HOLD"},
    {"game_n": 12, "set": 1, "score": "5-7", "model_p_win_a": 0.34, "bid": 0.30, "would_action": "HOLD"},
    ...
  ],
  "actual_outcome": {
    "winner": "a",
    "final_score": "7-5, 6-4",
    "match_duration_min": 95
  },
  "would_pnl_usdc": 28.9
}
```

### 4.3 Gate criteria for v1

After 50-100 logged matches, evaluate:

- **Directional accuracy:** Of matches where model predicted P(win) ≥ 0.55, did A actually win ≥ 65% of the time?
- **Calibration:** When model says 0.60, does actual win rate cluster near 60%?
- **Edge realism:** Average model_p_win - polymarket_implied — is there real edge or wishful thinking?

If accuracy < 65%, do NOT proceed. Investigate: data freshness, surface adjustment, missing factors. Revisit phase 0.

---

## 5. The 4-Signal Model (target architecture for v3)

Phase 1 uses only signal #1. Phase 2 adds signal #2. Phase 3 adds #3 and #4.

### 5.1 Signal 1 — Magnus base P(win)

**What:** Klaassen-Magnus + O'Malley closed-form chain. Computes P(player A wins match) given current set state, current game score, server, and serve probabilities.

**Inputs:**
- p_serve_a, p_serve_b (career rolling 12-month from Sackmann)
- surface_factor (clay/hard/grass adjustment)
- BO3 vs BO5 (tournament tier metadata)
- Current state: sets_won_a, sets_won_b, games_a, games_b, server, point_score

**Output:** P(A wins match) ∈ [0, 1]

**Reference formulas:**
- Game on serve: `G(p) = p^4 × (15 - 4p - 10p^2) / (1 - 2p(1-p))`
- Set: recursive sum over all paths to 6-x or 7-x
- Match BO3: 2-out-of-3 sets, BO5: 3-out-of-5

### 5.2 Signal 2 — Bayesian in-match update (added v2)

**What:** Update p_serve_a and p_serve_b based on actual in-match performance. ESPN tennis scoreboard provides "service points won %" per set.

**Formula:**
```
posterior_p = w_career × p_career + w_match × p_match_observed

w_match grows with sample size:
- 0-2 service games observed: w_match = 0.05
- 3-5 service games: w_match = 0.25
- 6-10 service games: w_match = 0.40
- 10+ service games: w_match = 0.55
```

Posterior bounded: `|posterior_p - p_career| ≤ 0.15` (no wild swings from one bad set).

### 5.3 Signal 3 — Momentum EWMA (added v3)

**What:** Exponentially weighted moving average of recent game outcomes. Captures "fighting back" vs "deteriorating" trend.

**Formula:**
```
momentum = EWMA(last_N_game_outcomes, decay=0.85)

Each game outcome = 1 (won) or 0 (lost)
N = up to 7 most recent games
Result ∈ [0, 1]
0.5 = neutral, > 0.5 = winning streak, < 0.5 = losing streak
```

### 5.4 Signal 4 — Value loss penalty (added v3)

**What:** Sermaye verimi factor. The more position value has eroded, the higher penalty for holding.

```
value_loss = max(0, (entry_value - current_value) / entry_value)
value_loss ∈ [0, 1]
```

### 5.5 Combined risk-adjusted EV decision

```
risk_penalty = w_momentum × max(0, 0.5 - momentum) + w_value × value_loss
risk_penalty = min(0.70, risk_penalty)   # cap

EV(hold) = P_live(win) × 1.0 × (1 - risk_penalty)
EV(sell) = bid - slippage_estimate

SELL if EV(sell) > EV(hold)
HOLD otherwise
```

**Initial weights (start v3 with these, recalibrate after first 30 v3 matches):**
- w_momentum = 0.35
- w_value = 0.40

---

## 6. Exit Hierarchy (v3 final)

Evaluated in priority order each ESPN game completion:

| # | Layer | Trigger | Action |
|---|---|---|---|
| 1 | NEAR_RESOLVE | bid ≥ 0.95 | SELL_ALL |
| 2 | PROFIT_LOCK | bid ≥ 0.80 first time | SELL_50 |
| 3 | Risk-Adjusted EV | EV(sell) > EV(hold) | SELL |
| 4 | Sanity check | Magnus P(win) ≥ 0.40 but bid < 0.10 (panic) | HOLD (override SELL) |
| 5 | Edge case: retire | ESPN reports retirement | HOLD + Telegram alarm |
| 6 | Edge case: ESPN outage | No ESPN data ≥ 5 min | HOLD + Telegram alarm |

**Disabled for tennis:**
- ❌ CRITICAL_DROP (15min %25 drop) — tennis prices crash naturally at set boundaries
- ❌ STRUCTURAL_DAMAGE (price/entry ≤ 0.40) — same reason

---

## 7. Data Sources

### 7.1 Sackmann GitHub (player stats — NEW dependency)

**Source:** https://github.com/JeffSackmann/tennis_atp + tennis_wta
**Format:** CSV, machine-readable
**Update cadence:** Weekly (every Monday)
**Cache:** `data/sackmann_cache/` (CSV files, 50-100 MB total)

**Required fields per player (rolling 12-month aggregate):**
- 1st serve %
- 1st serve points won %
- 2nd serve points won %
- Surface-specific breakdowns (clay/hard/grass)
- Last match date
- ATP/WTA ranking

**Cold start handling:** Player not in Sackmann (qualifier, new pro) → fall back to ranking-based prior table:

ATP (men):
```
rank 1-20: p_serve = 0.70
21-50: p_serve = 0.66
51-100: p_serve = 0.62
101+: p_serve = 0.58 (skipped — outside our ranking gap filter anyway)
```

WTA (women) — lower baseline serve %:
```
rank 1-20: p_serve = 0.62
21-50: p_serve = 0.58
51-100: p_serve = 0.55
101+: p_serve = 0.51 (skipped)
```

### 7.2 ESPN tennis scoreboard (live state — already wired)

**Source:** `https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard` + wta
**Already integrated:** `src/infrastructure/apis/espn_client.py` + `src/config/sport_rules.py`
**Per-game data:** set scores, current game score, server, service points won, break points faced/saved

### 7.3 Polymarket Gamma (market prices — already wired)

**Source:** Existing `GammaClient`
**Used for:** Live bid/ask, position value tracking

### 7.4 Odds API tennis (sanity check only)

**Source:** Existing `OddsAPIClient` with sport keys `tennis_atp_*` + `tennis_wta_*`
**Coverage:** Top 5 matches per tournament only
**Used for:** Sanity check signal — if Polymarket bid drops but Odds API h2h still favors our side, treat as panic and HOLD

### 7.5 Player Name Resolution (CRITICAL INFRASTRUCTURE)

Three data sources use different name formats — must be reconciled before Magnus model can run.

| Source | Format example | Quirks |
|---|---|---|
| Polymarket slug | `atp-medvedev-cobolli-2026-04-28` | Surname only, ASCII normalized, lowercase |
| Polymarket question text | "Madrid Open: Daniil Medvedev vs Flavio Cobolli" | Full name, sometimes "D. Medvedev" |
| ESPN scoreboard | `competitor.athlete.displayName: "Daniil Medvedev"` | Full name with diacritics ("Šafářová" preserved) |
| Sackmann CSV | `winner_name: "Daniil Medvedev"` | Full name, hyphenated for surnames ("Auger-Aliassime") |

**Resolver strategy** (`src/domain/matching/tennis_player_resolver.py`):

1. **Build canonical registry** at startup from Sackmann player file (master ID list)
2. **Polymarket slug parse:** `atp-{slug}-{slug}-{date}` → split, lowercase, normalize accents
3. **Question text parse:** existing `extract_teams()` already returns first/last name pairs
4. **Match resolution priority:**
   - Exact lowercase + accent-stripped match
   - Surname-only fuzzy match (rapidfuzz token_sort_ratio ≥ 0.85)
   - First-letter + surname pattern ("D. Medvedev" → match anyone with surname Medvedev + first name starting D)
   - Fail-loud if no confident match (log + skip the market)

**Edge cases handled:**
- Hyphenated surnames (Auger-Aliassime)
- Diacritics (Šafářová, Tsitsipas)
- Asian name conventions (Wu Yibing — first vs last ambiguity)
- Same surname in same match (rare but exists — disambiguate by first letter)

**Blocker:** No registry resolution = no Magnus run. Test coverage required across 50+ name variations.

---

## 8. Tournament Tier + Surface Metadata

Static configuration in `config.yaml`:

```yaml
tennis:
  tournaments:
    grand_slam:    # BO5 men, BO3 women
      surface_map:
        australian_open: hard
        french_open: clay
        wimbledon: grass
        us_open: hard
    masters_1000:  # BO3
      surface_map:
        indian_wells: hard
        miami_open: hard
        monte_carlo_masters: clay
        madrid_open: clay
        italian_open: clay
        canadian_open: hard
        cincinnati_open: hard
        shanghai_masters: hard
        paris_masters: hard
    atp_500:       # BO3 — populated as tournaments come into season
      # surface_map keys generated during Phase 0 by scanning Polymarket slugs
      # against ATP/WTA official 500 tour calendar
      surface_map: {}
    excluded_tiers: [atp_250, wta_250, itf, challenger, futures]

  surface_factors:
    serve_pct:
      grass: 1.00
      hard: 1.00
      clay: 0.92      # men's
    serve_pct_wta:
      grass: 1.00
      hard: 1.05
      clay: 0.95
```

Tournament tier extraction from Polymarket slug: parse `atp-{tournament}-{date}` → match against `surface_map` keys.

---

## 9. Position Sizing & Filters

**Position size:**
- Phase 0: $0 (paper)
- Phase 1: max $15 / match
- Phase 2: max $25 / match
- Phase 3: max $35 / match (1.5% of $2333 bankroll)

**Entry filters:**
- Tournament tier ∈ {Grand Slam, Masters 1000, ATP/WTA 500}
- Both players ranked top 100
- Ranking gap < 100
- Match start within 0-24 hours
- Model edge ≥ 0.05 (P_model - P_polymarket)

**Multi-position rule:** Same event_id → max 1 position (H2H only) for v0-v3 scope. (Phase 4 will allow +1 Match Total Games when added.)

---

## 10. Configuration (config.yaml additions)

```yaml
tennis:
  enabled: false              # toggle to activate
  phase: disabled             # disabled | paper_trade | v1 | v2 | v3
  position_size_usdc:
    paper_trade: 0
    v1: 15
    v2: 25
    v3: 35
  filters:
    min_ranking: 100          # top 100 only
    max_ranking_gap: 100
    min_edge: 0.05
  exit:
    near_resolve_bid: 0.95
    profit_lock_bid: 0.80
    risk_penalty_cap: 0.70
    w_momentum: 0.35          # v3 only
    w_value: 0.40             # v3 only
    bayesian_max_shift: 0.15  # v2+
    momentum_decay: 0.85      # v3 only
    momentum_window_games: 7  # v3 only
  data:
    sackmann_cache_dir: "data/sackmann_cache/"
    sackmann_refresh_days: 7
  alerts:
    telegram_enabled: false   # separate feature, see TODO
```

All numeric thresholds documented in `DECISIONS.md` with rationale.

---

## 11. Edge Cases

| Case | Handling |
|---|---|
| Player retires mid-match | HOLD + Telegram alarm. Wait for Polymarket resolution (likely VOID per market description) |
| Walkover (no first point played) | Polymarket auto-resolves VOID, no bot action needed |
| Rain delay / suspended match | HOLD, no time-based exits trigger during gap |
| ESPN feed missing > 5 min | HOLD + alarm, no decisions |
| Tiebreak (7-6) | Counted as set win (decisive=False, treat as "close win/loss") |
| Player not in Sackmann | Ranking-based prior, log warning |
| Same-day rematch (rare) | Treat as separate match, no carry-over from earlier match |
| Surface unknown (slug doesn't parse) | Default to `hard`, log warning, skip if confidence low |

---

## 12. Testing Strategy

Per CLAUDE.md TDD:

- **Magnus chain unit tests:** Known closed-form values (e.g., p=0.5 → game = 0.5; p=0.7 → set ≈ 0.85)
- **Bayesian update tests:** Posterior bounded, direction correct (low match → posterior < career)
- **Momentum EWMA tests:** Edge cases (all wins, all losses, alternating)
- **Risk-adjusted EV tests:** Hand-computed scenarios (deficit + value loss → SELL)
- **Sackmann parser tests:** Known CSV row → expected fields
- **Phase 0 paper logger tests:** JSONL format integrity

Integration tests using mock ESPN + Sackmann fixtures.

Diag scripts:
- `scripts/diag_tennis_magnus.py` — sanity check Magnus output for a known match
- `scripts/diag_tennis_paper_replay.py` — replay logged matches with new model versions

---

## 13. Implementation Order

Per phased rollout. **H2H ONLY through Phase 3.** Match Total Games is Phase 4 separate sub-spec.

**Phase -1 (Telegram alarm system — BLOCKING for v1+):**
1. Telegram bot setup + token config (separate spec — see TODO.md)
2. Alarm dispatcher abstraction in `src/infrastructure/alerts/`
3. Wire into bot lifecycle (startup/shutdown notifications)
4. Test triggers from sport-agnostic events (circuit breaker, etc.)
5. Gate: alarm test message received

**Phase 0 (paper trade — H2H only, NO live trades):**
6. **Player name resolver** (`src/domain/matching/tennis_player_resolver.py`) — Polymarket slug parse + ESPN athlete normalization + Sackmann full-name matching with fuzzy fallback
7. Sackmann CSV fetcher + cache (`src/infrastructure/apis/sackmann_client.py`)
8. Tournament tier + surface metadata config (`config.yaml` + `DECISIONS.md`)
9. Magnus closed-form chain — H2H only (`src/domain/math/tennis_magnus.py`)
10. Tennis paper logger (`src/orchestration/tennis_paper_logger.py`)
11. Wire into existing `monitor.py` for tennis sport_tag (READ-ONLY path, no trades)
12. Activate paper mode, observe 50-100 matches, **GATE: directional accuracy ≥ 65%**

**Phase 1 (v1 simple live — H2H only, BO3 only):**
13. Replace stub `tennis_score_exit.py` with set-bazlı sabit tablo + Magnus base
14. Enable tennis in `active_sports` with size cap $15
15. Activate Telegram alarm wiring for tennis-specific events (retire, outage)
16. Observe 30 live matches, **GATE: ROI ≥ 0 + no structural bugs**

**Phase 2 (v2 Bayesian — H2H + add BO5 Grand Slam):**
17. Bayesian update module (`src/domain/math/tennis_bayesian.py`)
18. Wire into exit decision
19. Add BO5 (best of 5) Grand Slam support to Magnus chain
20. Increase size cap $25, observe 30 matches, **GATE: Bayesian reduces false positives by ≥ 10%**

**Phase 3 (v3 full — H2H complete):**
21. Momentum EWMA module (`src/domain/math/tennis_momentum.py`)
22. Risk-adjusted EV combiner integrated into `tennis_score_exit.py`
23. Increase size cap $35, steady state

**Phase 4 (separate sub-spec, future):**
- Add Match Total Games market layer once v3 H2H is stable

---

## 14. Open Questions / Future v4+

- Match-fixing detection (currently relying on tier filter — ATP 250 still has some risk)
- Head-to-head historical lookup (Sackmann has match results, not yet in model)
- Player coaching change / equipment change (out of scope, no data source)
- Fatigue model (set 4-5 in BO5 — degraded serve %)
- Common-opponent stochastic model (alternative to Klaassen-Magnus)
- Move from CSV-based Sackmann to GitHub API direct calls (faster updates)

---

## 14b. Pre-Implementation Risk Audit (added during review)

Risks identified during final review before commit. Each must be addressed in implementation plan.

### Risk 1: Sample size math — paper trade needs longer window

**Issue:** Our entry filters (Grand Slam + Masters 1000 + ATP/WTA 500, ranking gap < 100) restrict eligible matches significantly:
- Grand Slam: 1 every 3 months
- Masters 1000: ~2 per month
- ATP/WTA 500: ~3-4 per month
- After ranking gap filter (< 100): ~30-50% eliminated

Realistic eligible matches: **~30-40 per month**, NOT per week.

**Impact:** Phase 0 paper trade needs **6-12 weeks**, not 3-4 weeks, to reach 50-100 sample.

**Mitigation:**
- Option A: Extend Phase 0 to 8-12 weeks
- Option B: During paper trade ONLY, relax to include ATP 250 + WTA 250 for sample size, then tighten for live trading
- **Recommended: Option B** — paper trade has zero $ risk, broader sample is safer than waiting

### Risk 2: Phase 0 should log Match Total predictions too (free Phase 4 data)

**Issue:** If Phase 0 only logs H2H predictions, Phase 4 (Match Total Games) starts cold without paper data.

**Mitigation:** Paper logger logs BOTH H2H and Match Total predictions during Phase 0 (just observation, no action). When Phase 4 starts, we already have months of Match Total prediction data to validate model.

### Risk 3: Test data fixtures — hermetic CI required

**Issue:** Tests must run without network. Sackmann CSV + ESPN scoreboard + Polymarket Gamma all need fixture files.

**Mitigation:**
- Commit `tests/fixtures/sackmann/` with sample player + matches CSV (~2 MB)
- Commit `tests/fixtures/espn/tennis/` with mock scoreboard JSON
- Commit `tests/fixtures/polymarket/tennis/` with mock event/market JSON
- Pure domain math tests use synthetic data only (no fixtures needed)

### Risk 4: ESPN vs Sackmann player ID alignment

**Issue:** Sackmann uses internal `player_id`, ESPN uses `athlete.id`. Different namespaces. Player resolver must map between them via name (which is fuzzy).

**Mitigation:** Build cross-reference table at startup:
```
canonical_name → (sackmann_id, espn_id, polymarket_slug_form)
```
Persisted to `data/tennis_player_xref.json` for stability across restarts. Refreshed weekly with Sackmann update.

### Risk 5: Telegram delivery reliability

**Issue:** Telegram itself can be down. If retire detected and alarm fails to deliver, we're blind.

**Mitigation:**
- Retry with exponential backoff (3 attempts, 1s/5s/30s)
- Fallback: log alarm to dedicated `logs/audit/critical_alarms.jsonl` regardless of Telegram success
- Bot startup health check: send "bot online" message; if fails → log warning + continue (don't block startup)

### Risk 6: Rollback procedure per phase

**Issue:** If Phase 1 reveals structural bug (e.g., Magnus formula error), we need clean rollback to Phase 0 (paper) without losing data.

**Mitigation:**
- `tennis.phase` config flag controls behavior — flip to `paper_trade` or `disabled` immediately
- All exit decisions logged with phase tag — easy to filter post-hoc
- Position close-only mode: when phase changes mid-match, finish existing positions with last-known logic, no new entries
- Document rollback runbook in `DECISIONS.md`

### Risk 7: Bayesian bootstrap (first few games)

**Issue:** Bayesian update needs ≥3 service games for meaningful posterior. First 0-2 service games of a match → posterior = career prior basically.

**Mitigation:** Spec already handles via `w_match` table (0-2 games → w_match=0.05, almost no update). Confirm in implementation: skip Bayesian application entirely for matches with < 2 service games observed; use career prior only.

### Risk 8: Cache hot-reload during running bot

**Issue:** Sackmann CSV updated weekly. If bot is running when update comes, do we reload or wait until restart?

**Mitigation:** Hot-reload on next light cycle (5s). Atomicity via temp-file-then-rename. Lock during reload to prevent partial reads.

### Risk 9: Time zone consistency

**Issue:** ESPN returns UTC, Sackmann uses YYYY-MM-DD (no time zone), Polymarket uses ISO 8601 with Z suffix. Cross-system date comparisons are landmine.

**Mitigation:** All internal datetime objects are `datetime` with `tzinfo=timezone.utc`. Convert at boundaries (parse Sackmann date strings as UTC midnight). One helper: `parse_iso_to_utc(s)`.

### Risk 10: A/B testing v1/v2/v3 — sequential, not parallel

**Decision:** Phases v1/v2/v3 are SEQUENTIAL upgrades, not parallel comparison. Each phase replaces the previous in production. We measure improvement against the baseline established in the previous phase, not by running both side-by-side.

This avoids:
- Position size duplication
- Conflicting decisions on same market
- Operational complexity of multi-version deployment

Trade-off: slower iteration (must run each phase 30+ matches before next), but cleaner attribution and risk management.

---

## 15. Success Metrics

**Per phase (H2H only through v3):**
- Phase -1 (Telegram): test alarm received end-to-end
- Phase 0 (paper): H2H directional accuracy ≥ 65% on 50-100 matches
- Phase 1 (v1 BO3 only): positive ROI over 30 matches (excluding fees), no structural bugs
- Phase 2 (v2 + Bayesian + BO5): Bayesian reduces false positives by ≥ 10% vs v1
- Phase 3 (v3 full): maintain Phase 2 metrics + improved Sharpe ratio
- Phase 4 (Match Total Games): separate metrics in sub-spec

**Long-term (after Phase 3):**
- Tennis ROI within 0.5σ of NHL ROI (proves spec is comparable to validated sports)
- < 5% of trades trigger Sanity Check override (tight calibration)
- Telegram alarms < 2 per week (system stable)
- Player resolver fail rate < 1% (matches skipped due to name resolution failure)

---

## References

### Academic foundation
- Klaassen & Magnus (2003) — Forecasting the winner of a tennis match. European Journal of Operational Research.
- Klaassen & Magnus (2001) — Are Points in Tennis Independent and Identically Distributed? Journal of the American Statistical Association.
- O'Malley (2008) — Probability of Winning at Tennis I. Theory and Data.
- Newton & Keller (2005) — Probability formulas and statistical analysis in tennis.
- Ingram (2019) — A point-based Bayesian hierarchical model. JQAS.

### Empirical data
- Surface effects: Tennisnerd betting analysis 2026.
- Risk-Constrained Kelly Criterion: QuantInsti.

### Data sources
- Sackmann tennis_atp / tennis_wta: https://github.com/JeffSackmann/tennis_atp

### Local API guides (in old project, reference during implementation)

**Polymarket API guide:** `../Polymarket Agent_Eski/API Guides/Polymarket API/`
- `polymarket-api-index.md` — START HERE (compact index of 78,024-line full reference)
- `polymarket-full-api-reference.md` — read by line offset based on index
- Tennis-relevant sections:
  - L66853-67387: Get sports metadata (`GET /sports`)
  - L67388-67876: Get valid sports market types
  - L67877-68476: List teams (note: tennis uses individual athletes, not teams — schema may differ)
  - L77515-78024: WSS Sports Channel (real-time)
  - L3158-5538: List events (event/market structure for slug parsing)

**ESPN API guide:** `../Polymarket Agent_Eski/API Guides/ESPN API/`
- `espn-api-index.md` — START HERE (compact index of 18,617-line full reference)
- `Public-ESPN-API-FULL.md` — read by line offset
- Tennis-specific section: L6201-L6358 (158 lines, fully relevant)
- Key tennis endpoints found:
  - `site.api.espn.com/apis/site/v2/sports/tennis/{atp|wta}/scoreboard` — live scores (already wired)
  - `sports.core.api.espn.com/v2/sports/tennis/leagues/{atp|wta}/athletes?active=true` — player roster (NEW, for resolver registry)
  - `sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/rankings` — current ATP/WTA rankings
  - `sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/tournaments?majorsOnly` — tier metadata
- ⚠ Caveats: tennis injuries endpoint returns 500, athletes endpoint requires `atp`/`wta` slug (not numeric ID)

**The Odds API guide:** `../Polymarket Agent_Eski/API Guides/ODDS API guide.md`
- Key tennis endpoint discovered: `GET /v4/sports/{sport}/participants` — returns full player list per sport key (could be alternate name source for cold-start cases)
- Sports keys: `tennis_atp_*`, `tennis_wta_*` (city-based, ~17 ATP + 17 WTA tournaments)

### Implementation reading order

When entering Phase 0, read in this order:
1. ESPN tennis section (L6201-L6358) — fully understand live data schema
2. Polymarket Sports endpoint (L66853-67387) + List events (L3158-5538) — understand market/event structure
3. The Odds API tennis section + participants endpoint — confirm sport key list
4. Sackmann GitHub README + sample CSV row inspection

---

**End of design doc. Pending user review.**
