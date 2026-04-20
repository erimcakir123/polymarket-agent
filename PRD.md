# PRD — Polymarket Agent 2.0
> v2.0 | 2026-04-13 | APPROVED
> SSOT: "what" + "why". Technical "how" → TDD.md.

---

## 1. Summary

Autonomous trading bot on Polymarket prediction markets. Extracts bookmaker consensus probability from 20+ books via Odds API. Enters favorites where market price isn't an expensive outlier. Multi-layer risk management.

**One-line logic:** Bookmaker consensus + market price opportunity → size → open → monitor → exit.

---

## 2. Iron Rules (Non-Negotiable)

### 2.1 P(YES) Anchor
`anchor_probability = P(YES)` always, regardless of direction. Direction-adjusted probability computed at decision time, never stored. (ARCHITECTURE_GUARD Rule 7)

### 2.2 Event-Level Guard
Same `event_id` → two positions impossible. BUY_YES on "City wins" blocks BUY_NO on "Brighton wins" (same event). Enforced in `entry/gate.py`. (ARCHITECTURE_GUARD Rule 8, TDD §6.4)

### 2.3 Confidence-Based Sizing
- **A:** bankroll × 5%
- **B:** bankroll × 4%
- **C:** blocked (no entry)

Additional multipliers subject to `max_bet_pct` cap (single cap, from config.yaml). (TDD §6.5)

### 2.3.1 Probability-Weighted Sizing (SPEC-016)
Formula: `stake = bankroll × bet_pct × win_prob`

Higher win_prob → larger stake. Lower-probability entries proportionally smaller. Portfolio avg stake ~30% lower → more positions open simultaneously → diversification. Expected value −3-5% but variance significantly reduced.

Rollback: `risk.probability_weighted: false` → base-only formula.

### 2.4 Bookmaker-Derived Probability
Odds API weighted average: sharp books (Pinnacle/Betfair/Smarkets) at 3.0×, reputable (Bet365/William Hill/etc.) at 1.5×, others at 1.0×. Exchange bookmakers (Betfair, Matchbook, Smarkets): no vig normalize — prices already near true probability. (TDD §6.1, §6.3)

### 2.5 3-Layer Cycle
- **WebSocket:** instant price tick (SL + scale-out)
- **Light (5s):** fast exit checks
- **Heavy (30min):** scan + enrichment + entry decisions

Heavy interleaves light (light still fires during long heavy). Night mode (UTC 08-13): heavy → 60min.

### 2.6 Circuit Breaker (Mandatory)
Entry halted when:
- Daily loss ≥ 8% → 120min cooldown
- Hourly loss ≥ 5% → 60min cooldown
- 4 consecutive losses → 60min cooldown
- Soft block: daily loss ≥ 3% → entries suspended

Checked every entry, cannot be disabled. (TDD §6.15)

### 2.7 Scale-Out Profit-Taking (SPEC-013)
1-tier midpoint-to-resolution:
- At 50% of distance from entry to 0.99 → sell 40% of position
- Entry 43¢ → trigger 71¢. Entry 70¢ → trigger 84.5¢
- Remaining position → near-resolve (94¢) or SL

Distance-based semantics (not PnL%-based — fair across all entry prices). (TDD §6.6)

### 2.8 Favorite Filter (SPEC-013 / SPEC-017)
`win_prob >= min_favorite_probability` (0.60). Underdog value bets excluded — variance reduction.

### 2.9 Directional Entry (SPEC-017)
Bookmaker strong favorite (≥60%) + market price not expensive outlier (≤80¢, no lower floor — undervalue entries welcome) → enter directly. No edge calculation. Stake proportional to win_prob (SPEC-016). All exit rules, risk caps, event guard, manipulation/liquidity filters preserved.

Rollback: `git revert SPEC-017 commits (T1-T4)` → old 3-strategy system.

---

## 3. Operational Flows

### 3.1 Bot Startup
1. `main.py`: argparse (mode: dry_run|paper|live) + config.yaml load
2. `orchestration/process_lock.py`: single instance guarantee
3. `orchestration/startup.py`: wallet connect, persistence open, reload open positions from JSON store
4. `agent.py`: main loop → heavy cycle triggered

### 3.2 Entry Flow (Heavy Cycle)
1. **Scan:** `scanner.py` pulls Gamma markets filtered by `allowed_sport_tags` (max 300/cycle)
2. **Stock housekeeping:** `orchestration/stock_queue.py` refresh + TTL eviction (match_start−30min, 24h idle, 3× stale, event open)
3. **JIT pipeline:** stock top-N (match_start ASC) + fresh-only top-M → gate batch. N, M = `empty_slots × stock.jit_batch_multiplier` (default 3)
4. **Match:** `domain/matching/` → Polymarket slug to Odds API sport key
5. **Enrich:** `strategy/enrichment/odds_enricher.py` → bookmaker probability
6. **Gate:** `strategy/entry/gate.py` → event-guard + manipulation + liquidity + confidence + favorite_filter + entry_price_range
7. **Size:** `domain/risk/position_sizer.py` → confidence-based size + caps
8. **Execute:** `infrastructure/executor.py` → CLOB order (dry_run: log only)
9. **Record:** position → JSON store; trade → JSONL. Exposure cap excess → clip size (soft+hard); min_entry below → push to stock; other rejects (max_positions / below_fav_prob / price_out_of_range / no_bookmaker_data) → push to stock

### 3.3 Light Cycle Monitor (5s)
1. Read latest prices from WebSocket ticks
2. Check near_resolve (94¢) + scale-out for all open positions
3. First triggered exit signal → `exit/monitor.py` sends order

Exposure cap enforced both gate-time and execution-time. Denominator = total portfolio value (cash + invested). (TDD §6.15)

Scanner filter scope: moneyline only, `match_start ≤ 24h`, `yes_price < 0.98`. (TDD §5.7.5)

### 3.4 Exit Flow (Heavy Cycle)
1. **Never-in-Profit Guard:** peak_pnl never positive + elapsed > 70% → exit (TDD §6.10)
2. **Near-Resolve:** current_price ≥ 94¢ + 10min post-start guard → exit (TDD §6.11)
3. **A-Conf Hold:** confidence=A + entry ≥ 60¢ → skip never_in_profit; scale-out + near-resolve + market_flip (elapsed ≥ 85%, price < 0.50) active (TDD §6.9)
4. **Favored:** eff_price ≥ 65¢ + confidence ∈ {A,B} → promoted; below → demoted (TDD §6.13)

### 3.5 Circuit Breaker Triggered
1. `circuit_breaker.py` checks bankroll state before each entry
2. Threshold breached → entry rejected + log + Telegram
3. Cooldown period: exits only (open position management continues)
4. Cooldown expired → auto-resume

---

## 4. Functional Requirements

### F1. Scan
Gamma API market discovery. `allowed_sport_tags` filter. Max `max_markets_per_cycle=300`. (config.yaml `scanner:`, `src/orchestration/scanner.py`)

### F2. Enrich
Odds API bookmaker data per candidate. `domain/matching/` for slug→sport key. `bookmaker_weights.py` for sharp weighting. (TDD §6.1)

### F3. Entry Decision
`strategy/entry/gate.py`. Single strategy: directional entry (SPEC-017). All guards preserved. (TDD §6.3)

### F4. Position Sizing
Confidence-based: A=5%, B=4%, C=blocked. Single cap: `max_bet_pct` (config.yaml). (TDD §6.5)

### F5. Execute
`executor.py` in 3 modes: `dry_run` (log-only), `paper` (mock fills), `live` (real CLOB). Every order → JSONL trade log. (`src/infrastructure/executor.py`)

### F6. Monitor
3-layer: WS tick (instant), Light (5s), Heavy (30min). Position state in JSON store; dashboard reads live.

### F7. Exit
Mechanisms (first signal wins): near_resolve (94¢), market_flip (elapsed ≥ 85% + price flip), scale_out (midpoint partial), score_exit (7 sports), never_in_profit, hold_revoked, ultra_low_guard, circuit_breaker, manual. Full list + priority: TDD §6.6–§6.14. ExitReason enum: `src/models/`.

### F8. Report
3 channels: Flask dashboard (localhost:5050), Telegram (entry/exit/CB), JSONL audit log.

**Dashboard scope:**
- **5 summary cards:** Balance, Open P&L, Realized P&L (W/L sub-line), Locked in Bets, Peak Balance (HWM + drawdown%)
- **3 protection/analysis cards:**
  - Loss Protection — RISK gauge + Down% + Stop at% (CB daily threshold) + Status (Safe/Caution/Warning/Stopped)
  - Positions — slot gauge (current/max) + entry_reason tags (DIRECTIONAL / THREEWAY)
  - Branches — sport/league ROI treemap (area ∝ invested USDC, color ∝ ROI, hover tooltip)
- **2 charts:** Total Equity time series (realized-only stepped, period tabs 24h/7d/30d/1y + adaptive bucketing) + Per-Trade PnL waterfall (same period tabs). (TDD §5.7.7)
- **Trades feed (right panel, 4 tabs):** Active | Exited | Skipped | Stock — each card clickable (Polymarket event page), sport icons
- **Cycle bar (topbar):** Hard cycle (blue) + Light cycle (teal); offline/idle = grey

**Removed sections:** API Usage panel (not implemented), Performance panel (Wins%, Avg Edge, Brier Score — MVP-out), AI vs Bookmaker panel (divergence chart — MVP-out).

Source: `src/presentation/dashboard/`

### F9: Retrospective Analysis Archive (SPEC-009)
- `logs/archive/exits.jsonl` — full exit snapshot + score at exit
- `logs/archive/score_events.jsonl` — in-match score changes
- `logs/archive/match_results.jsonl` — final results

Reboot/reload/trade deletion: archive untouched. Append-only. JOIN by event_id for retrospective rule analysis.

### F10: Baseball Score Exit (SPEC-010)
FORCED exit, all confidence classes. Symmetric to tennis T1/T2 + hockey K1-K4.
- M1: inning ≥ 7 + deficit ≥ 5 (blowout)
- M2: inning ≥ 8 + deficit ≥ 3 (late large deficit)
- M3: inning ≥ 9 + deficit ≥ 1 (final inning)

### F11: Cricket Cluster (SPEC-011)
7 leagues: IPL (Apr-Jun), ODI (year-round), International T20, PSL, Big Bash, CPL, T20 Blast.
- Score source: CricAPI free tier (100 hits/day; ESPN has no cricket)
- Score exit C1/C2/C3: 2nd innings chase + our_chasing only
- Rate limit hit → `cricapi_unavailable` skip; existing positions unaffected
- TODO-003: Paid tier ($10/mo, 1000+ hits/day) when cricket volume grows

### F12: 3-Way Market Support (SPEC-015)
Soccer (60+ leagues: EPL, La Liga, Serie A, Bundesliga, Ligue 1, UCL, UEL, MLS, Süper Lig, Eredivisie, Brasileirão, Liga MX, 40+ country leagues), Rugby Union + League, AFL, Handball.

- `EventGrouper` groups 3 binary markets by event_id
- `ThreeWayEntry` selects direction (highest bookmaker probability = favorite)
- `SoccerScoreExit` separate rules for DRAW vs HOME/AWAY (65'+ lock)
- Same infrastructure DRY across all 3-way sports

Entry rules: favorite ≥ 40% absolute + 7pp margin + yes_price ≤ 80¢ + sum filter [0.95, 1.05]. Excluded: friendlies, preseason, testimonials.

Exit rules: first-half lock (0-65'), 65'+ 2-down EXIT, 75'+ 1-down EXIT, DRAW: 0-70' HOLD → 75'+ goal EXIT → knockout 90+ AUTO-EXIT.

Credit budget: 800 credits/day (20K monthly budget ~4% buffer). Exceeded → skip fetches; open positions unaffected.

---

## 5. Non-Functional Requirements

### 5.1 Latency
- Heavy cycle ≤ 30s
- Light cycle ≤ 1s
- WS tick → exit decision ≤ 500ms

### 5.2 Uptime
- MVP target: 48h continuous dry_run
- WS disconnect → reconnect within 30s

### 5.3 Crash Recovery
- `startup.py` reloads from `positions.json`
- JSONL trade log: append-only, replayable post-crash
- Process lock prevents dual instances

### 5.4 Observability
- Flask dashboard: < 3s lag, 5s polling
- `logs/bot_status.json` every tick (mode, last_cycle, last_cycle_at, reason) → cycle bar
- Trade history: append + exit update (`TradeHistoryLogger.update_on_exit` atomic rewrite)
- Equity history: snapshot per heavy cycle to `equity_history.jsonl`; Total Equity chart uses `/api/trades` cumsum (PLAN-008/009)
- Peak Balance: all-time total_equity peak (not cash-only HWM)
- Skipped candidates → `skipped_trades.jsonl`; Stock queue → `stock_queue.json` (persistent, restored on restart)
- Telegram: entry/exit/CB events

### 5.5 Run Modes
- `dry_run`: live API calls, no order submission (default test mode)
- `paper`: mock fills, bankroll simulation
- `live`: real orders + real USDC

### 5.6 Test Coverage
- Domain: > 90% unit test coverage
- Strategy: > 80% unit test coverage
- Integration: entry pipeline + exit pipeline + WS reconnect

---

## 6. Technical Constraints

### 6.1 API Limits
- **The Odds API:** 20K credits/month (paid), 1-10 credits per `fetch_odds`
- **Polymarket CLOB REST:** ~100 req/min
- **Polymarket Gamma:** ~300 markets/cycle safe
- **Telegram:** 30 msg/s

### 6.2 Infrastructure
- Chain: Polygon mainnet
- Payment: USDC (6 decimal)
- Python: 3.12+
- OS: Linux (prod), Windows (dev)

### 6.3 Cycle Times
- Heavy: 30min (day), 60min (night UTC 08-13)
- Light: 5s
- WebSocket: continuous (reconnect)

### 6.4 Market Filtering
- Min liquidity: $1000
- Max duration: 14 days
- Allowed categories: `sports` only
- Allowed sport_tags: `baseball_*`, `basketball_*`, `icehockey_*`, `americanfootball_ncaaf|cfl|ufl`, `tennis_*`, `golf_lpga_tour|liv_tour` (see config.yaml)

### 6.5 Sport Tag Reliability
Gamma event tags unreliable — multiple tags per event, wrong tag first possible. Slug-based override: market slug prefix takes authority over event tag. Broken sport_tag breaks exit rules + treemap + sport_rules selection. (TDD §7.3)

---

## 7. Defense Mechanisms

### 7.1 Manipulation Guard
`domain/guards/manipulation.py`: min liquidity $10K + self-resolving market detection (person + self-resolving verb pattern). (TDD §6.16)

### 7.2 Liquidity Check
`domain/guards/liquidity.py`: entry min $100 depth; position > 20% of book → halve size. Exit: min 80% fill ratio; below → split order. (TDD §6.17)

### 7.3 Circuit Breaker
Active enforcement of §2.6 thresholds. `domain/risk/circuit_breaker.py` checks bankroll state every entry. (TDD §6.15)

### 7.4 Event-Level Guard
`strategy/entry/gate.py` checks event_id on every entry decision. Same event_id open → reject. (Iron Rule 2.2, ARCHITECTURE_GUARD Rule 8)

---

## 8. Glossary

| Term | Definition |
|---|---|
| `anchor` / `anchor_probability` | Bookmaker consensus P(YES). Direction-independent. |
| `P(YES)` | Probability of YES outcome (0.0–1.0) |
| `win_prob` | Direction-adjusted: BUY_YES=anchor, BUY_NO=1−anchor. Used in stake calc. |
| `eff_price` | Effective price for position (market mid ± slippage estimate) |
| `direction` | `BUY_YES` / `BUY_NO` / `HOLD` |
| `confidence` | A (sharp or ≥5 books) / B (≥5 books, no sharp) / C (insufficient, blocked) |
| `favored` | Position flag: eff_price ≥ 65¢ + conf ∈ {A,B} |
| `scale-out` | Staged profit-taking: partial sell at PnL thresholds |
| `elapsed` | Match progress ratio (0.0=start, 1.0=end) |
| `directional entry` | Single entry strategy (SPEC-017): anchor → direction → favorable favorite → enter |

---

## 9. References

- [TDD.md](TDD.md) — algorithms, formulas, calibration numbers, data models
- [ARCHITECTURE_GUARD.md](ARCHITECTURE_GUARD.md) — architectural rules (15 rules + anti-patterns)
- [TODO.md](TODO.md) — deferred work and branches
- [CLAUDE.md](CLAUDE.md) — dev assistant rules (TODO management, arch protection)
- [PLAN.md](PLAN.md) — active implementation plans
