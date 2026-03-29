# Bot Rule System Overhaul v3 — Design Spec

## Goal

Fix 3 critical bugs (P0), 4 high-risk issues (P1), and restructure the cycle architecture so the bot can act on exits and re-entries within seconds instead of waiting 30 minutes.

## Architecture

The bot moves from a 2-tier cycle (heavy 30min + light 5s) to a 3-tier model where light cycles handle ALL actions (exits, re-entries, live entries) and heavy cycles handle only scanning and AI analysis. This eliminates the 30-minute blind spot for live market events.

## Tech Stack

Python 3.11+, Pydantic config, existing module structure. No new dependencies.

---

## §1 — Cycle Architecture Redesign

### §1a. Three-Tier Model

| Tier | Interval | Responsibility |
|------|----------|----------------|
| WebSocket | Real-time | Price updates, peak tracking |
| Light cycle | 5 seconds | ALL exits, ALL re-entries, live dip, momentum, scale-out |
| Heavy cycle | 30 minutes | Market scan (Gamma API), AI analysis (Sonnet), new entries (Winner, Early, Upset, Penny), scout data fetch |

### §1b. Light Cycle Cooldowns

Light cycle runs every 5 seconds but entry/action strategies have per-strategy cooldowns measured in light cycle ticks:

| Strategy | Cooldown ticks | Wall time | Rationale |
|----------|---------------|-----------|-----------|
| Live Dip | 60 | 5 min | Dip stabilization |
| Momentum | 36 | 3 min | Score change settling |
| Farming Re-entry | 24 | 2 min | Already has stabilization logic |
| Scale-out | 12 | 1 min | Post-sell price impact |

Implementation: `_light_cooldowns: dict[str, int]` keyed by strategy name, value = `light_cycle_count` when cooldown expires. Separate from `_exit_cooldowns` (per-position, cycle_count based).

### §1c. Light Cycle Counter

Add `self.light_cycle_count: int = 0` to Agent.__init__. Increment in `run_light_cycle()`. Cooldowns reference this counter, not heavy cycle's `cycle_count`.

### §1d. Pre-Match Price Cache Safety

`_pre_match_prices` dict is populated in heavy cycle (market scan), consumed read-only in light cycle (live dip detection). Light cycle NEVER writes to this dict.

### §1e. Event Dedup for Light Cycle Entries

Extract `_get_held_event_ids() -> set[str]` helper from portfolio. Call before live_dip and momentum entries to prevent same-event dual-side positions.

---

## §2 — Entry Strategy Changes

### §2a. FAR + Scout = Early Entry

Merge FAR and Scout into a single "Early Entry" strategy:

- **Name:** `early` (entry_reason), `EarlyEntryConfig` (config class)
- **Scout becomes data provider only:** `scout_scheduler.py` fetches ESPN/PandaScore match calendars, caches sports context. No longer creates entries.
- **Early Entry pipeline:**
  1. Market is >6 hours from start (`min_hours_to_start: 6`)
  2. Scout cache has match data → inject into AI prompt as enriched context
  3. AI analysis with edge ≥10% (`min_edge: 0.10`)
  4. AI probability ≥55% (`min_ai_probability: 0.55`)
  5. Entry price ≤70¢ (`max_entry_price: 0.70`)
  6. Edge-based prioritization (higher edge = higher priority)
  7. Max 2 concurrent (`max_slots: 2`)
- **Config rename:** `FarConfig` → `EarlyEntryConfig`, add `max_entry_price: float = 0.70`
- **Position flag:** `is_far: bool` → `is_early: bool` (rename across codebase)
- **adaptive_kelly.py:** Update `is_far` → `is_early` reference (sizing multiplier 0.70×)

### §2b. Upset Hunter — Both Directions

Currently hardcoded to `BUY_YES` only. Change to evaluate both YES and NO sides:

- **`UpsetCandidate` dataclass:** Add `no_price: float`, `no_token_id: str`, `direction: str` fields
- **`pre_filter()` in upset_hunter.py:**
  - Check YES price: if 5-15¢ → candidate with `direction="BUY_YES"`
  - Check NO price (= 1 - yes_price): if 5-15¢ → candidate with `direction="BUY_NO"`
  - Same market can produce TWO candidates (one per side) — AI picks best
- **`agent.py::_check_upset_hunter()`:** Use `candidate.direction` instead of hardcoded `"BUY_YES"`. Use appropriate `token_id` based on direction.
- **Exit rules unchanged:** All upset exit logic is direction-aware (uses effective price).

### §2c. Penny Alpha — Timing Filter

Add match elapsed check to penny entry:

- If `elapsed_pct > 0.50` (match past first half) → skip penny entry
- If no timing data available → allow entry (pre-match assumed)
- Implementation: In `agent.py::_check_penny_alpha()`, calculate elapsed from `match_start_iso` before entry.

### §2d. Global Price Filter — 5-95%

Change extreme price guard from 2-98% to 5-95% for main strategies:

- **entry_gate.py line 692:** Change `0.02`/`0.98` to `0.05`/`0.95`
- **Exempt strategies:** Upset (own 5-15¢ zone) and Penny (own 1-2¢ zone) bypass this filter — they use their own pre-filters.
- **Resolution detection (agent.py:1789):** Keep at 2-98% — this is for detecting resolved markets, not entry filtering.

### §2e. Lossy Exit Re-entry

Expand re-entry pool to accept stop-loss exits:

- **Pool acceptance:** `_exit_position()` adds to reentry pool if:
  - Exit reason is `"stop_loss"` AND
  - Cached AI probability ≥ 65% AND
  - Not already re-entered for this market (SL counter == 0)
- **Trigger:** Fiyat, düşüşün %40'ını geri almış olmalı: `effective_current >= exit_price + (original_entry - exit_price) * 0.40`. Örnek: 70¢ giriş, 58¢ SL çıkış → düşüş 12¢ → %40 recovery = 4.8¢ → tetikleme = 62.8¢
- **Entry sizing:** Same confidence-based sizing as original, but SL is tighter: `original_SL × 0.75`
- **2nd SL = permanent blacklist:** If position hits SL again after lossy re-entry → permanent blacklist, no further re-entry
- **Tracking:** Add `sl_reentry_count: int = 0` to reentry pool candidate. Increment on re-entry. If `≥ 1` → reject.

---

## §3 — Exit System Changes

### §3a. Upset Exempt from Graduated SL

In `match_exit.py`, add exemption before graduated SL layer:

```
if entry_reason == "upset":
    # Upset positions use their own SL (50%) and forced exit at 90%
    # Skip graduated SL — it kills upsets at exactly the wrong time
    skip graduated SL (Layer 2)
```

Upset positions still have:
- Flat SL at 50% (`UpsetHunterConfig.stop_loss_pct`)
- Forced exit at 90% elapsed (with PnL/price filter, see §3b)
- Catastrophic floor (Layer 1)

### §3b. Upset Forced Exit — PnL + Price Filter

Replace blind "90% elapsed → exit" with price-aware logic:

```
if entry_reason == "upset" and elapsed_pct >= 0.90:
    if effective_current >= 0.60:
        → HOLD (favori olmuş, resolve'a kadar tut)
    elif effective_current >= 0.50:
        → EXIT with layer="upset_take_profit" (risky zone, kârı al)
    else:
        → EXIT with layer="upset_forced_exit" (hâlâ underdog, çık)
```

Fallback (no timing): Keep existing 3h max hold + PnL < 0 check.

### §3c. Never-in-Profit Guard — Upset + Penny Exempt

In `match_exit.py`, add exemption before never-in-profit check:

```
if entry_reason in ("upset", "penny"):
    skip never-in-profit guard (Layer 3)
```

Rationale: Upset and penny positions are designed to stay out of profit until late resolution. This guard kills them at the 70% mark, exactly when they might pay off.

### §3d. Trailing TP — Upset Below 35¢ Disabled

In `exit_monitor.py`, for upset positions:

- If `effective_current < promotion_price (0.35)` → **skip trailing TP entirely**
- If `effective_current >= 0.35` → use core trailing TP params (activation 20%, trail 8%)
- This means below 35¢, only scale-out (25¢/35¢ tiers) and hold-to-resolve apply

Currently the code uses `trailing_activation = 1.00` (100% profit) which effectively disables it, but this is fragile — a price spike to +100% then back down would trigger it. Explicit skip is safer.

### §3e. Pre-Match Forced Exit — Remove

Delete `portfolio.check_pre_match_exits()` method and its caller in `exit_monitor.py`.

Rationale: A/B+ already exempt. B-/C positions have their own SL and trailing TP. Forcing exit 30 minutes before match start often exits positions that would have been profitable.

Dead code cleanup:
- Remove `check_pre_match_exits()` from `portfolio.py` (lines 579-607)
- Remove call from `exit_monitor.py::check_exits()` (line 256)
- Remove `"pre_match_exit"` from `_NEVER_STOCK_EXITS` in `agent.py` (line 53)

### §3f. Exit Detailed Logging

Add comprehensive logging inside `_add()` helper in both `check_exits()` and `check_exits_light()`:

```python
def _add(cid: str, reason: str) -> None:
    if cid not in seen_cids and cid not in self._exiting_set:
        result.append((cid, reason))
        seen_cids.add(cid)
    # Log ALL triggered rules (including duplicates blocked by seen_cids)
    _all_triggered.setdefault(cid, []).append(reason)
```

At end of check_exits/check_exits_light:
```python
for cid, rules in _all_triggered.items():
    if len(rules) > 1:
        winner = rules[0]  # First added = winner
        logger.info("EXIT_DETAIL: %s | fired=%s | also_triggered=%s",
                     cid[:20], winner, rules[1:])
```

Return type stays `list[tuple[str, str]]` — no breaking change.

---

## §4 — P0 Fixes (Critical)

### §4a. Exposure Guard

Add to entry gate before executing any candidate:

```python
total_invested = sum(p.size_usdc for p in self.portfolio.positions.values())
if (total_invested + candidate_size) / bankroll > config.risk.max_exposure_pct:
    logger.info("SKIP exposure cap: %.0f%% > %.0f%%", ...)
    continue
```

Config: Add `max_exposure_pct: float = 0.35` to `RiskConfig`.

Applies to ALL entry types (Winner, Early, Upset, Penny, Live Dip, Momentum, Re-entry).

### §4b. VS Reserved Slots — 5 → 3

Change `VolatilitySwingConfig.reserved_slots` default from 5 to 3.

### §4c. Catastrophic Floor Threshold — 25¢ → 20¢

Change `match_exit.py` line 282: `effective_entry >= 0.25` → `effective_entry >= 0.20`.

---

## §5 — File Change Map

| File | Change Type | What Changes |
|------|-------------|-------------|
| `config.py` | Modify | `FarConfig` → `EarlyEntryConfig` + `max_entry_price`, `RiskConfig` + `max_exposure_pct`, VS `reserved_slots: 3` |
| `entry_gate.py` | Modify | `is_far` → `is_early`, global filter 5-95%, exposure guard, Early Entry merge |
| `exit_monitor.py` | Modify | Remove pre-match exit call, upset trailing TP skip below 35¢, exit detailed logging |
| `match_exit.py` | Modify | Upset exempt graduated SL, upset forced exit PnL+price filter, never-in-profit upset/penny exempt, catastrophic floor 20¢ |
| `upset_hunter.py` | Modify | YES+NO direction support in UpsetCandidate and pre_filter |
| `agent.py` | Modify | Light cycle architecture (move live_dip/momentum), cooldown system, light_cycle_count, lossy re-entry, event dedup helper |
| `portfolio.py` | Modify | Remove `check_pre_match_exits()` |
| `reentry_farming.py` | Modify | Accept lossy exits, %40 recovery filter, SL counter tracking |
| `models.py` | Modify | `UpsetCandidate` direction fields |
| `scout_scheduler.py` | Modify | Remove entry logic, data provider only |
| `adaptive_kelly.py` | Modify | `is_far` → `is_early` rename |
| `scale_out.py` | No change | Already config-driven |

---

## §6 — Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `_pre_match_prices` race condition | Heavy cycle writes, light cycle reads only |
| `cycle_count` vs `light_cycle_count` confusion | Separate counters, cooldowns use appropriate one |
| Event dedup bypass by light cycle entries | `_get_held_event_ids()` helper shared by all entry paths |
| Test breakage (9 graduated_sl tests) | Update tests to pass `entry_reason != "upset"` |
| `is_far` → `is_early` rename ripple | Grep all references, rename atomically |

---

## §7 — Out of Scope

- Penny/Upset merge (P1 from Claude analysis) — deferred, keep separate for now
- Slot priority system (which strategy gets priority when slots are full) — separate spec needed
- Edge decay TP changes — works correctly as-is for non-upset positions
- VS spike detection — unchanged
- Consensus thesis invalidation — unchanged
