# Exit Card Redesign — Design

**Date:** 2026-04-20
**Status:** DRAFT → user review
**Goal:** Raise exit card information density to match the active card. Surface entry odds, realized PnL %, partial-exit price, remaining position %, and a humanized `exit_reason` label.

---

## Problem

Today the exited-tab card shows only: market title, direction, `entry_price`, either `Exit Xc` (full) or `Partial N%` (scale-out), `$PnL`, raw `exit_reason` string, relative time, and `final_outcome` — see [feed.js:168-199](../../src/presentation/dashboard/static/js/feed.js#L168-L199).

Missing compared to the active card:
- No confidence/entry-reason parity fields (owner selected only a subset — see §Selected Fields).
- No entry odds → no context for whether the exit price beat the book.
- No PnL % — only the dollar figure.
- Partial scale-outs do **not** show the sell price (`trade_logger.log_partial_exit()` does not persist it — [trade_logger.py:142-159](../../src/infrastructure/persistence/trade_logger.py#L142-L159)).
- No "remaining in position" indicator after a partial.
- `exit_reason` is the raw token (`scale_out_tier_1`, `score_exit_home_goal`, `stop_loss_l3`, `market_flip`, `time_exit`, …) — unreadable at a glance, negative reasons not visually distinct.

---

## Selected Fields (owner-approved)

| ID  | Field | Source | Cost |
|-----|-------|--------|------|
| A4  | Entry odds % | `anchor_probability` (direction-adjusted on render, BUY_NO → `1 − anchor`) | zero — field exists |
| A5  | PnL % | `exit_pnl_usdc / invested_notional` | zero — computed on render |
| B7  | Remaining % (partial events only) | `1 − Σ(sell_pct)` cumulative up to and including the event | zero — computed in `computed.py::exit_events()` |
| C11 | Partial sell price | **New:** `partial_exits[].price` | small backend — `trade_logger.log_partial_exit()` + `exit_processor.py` call site |
| C12 | Entry → Exit price delta | Derived from `entry_price` + `exit_price` (full) / `partial_exits[].price` (partial) | zero once C11 is live |
| —   | Humanized `exit_reason` label | New frontend map in `fmt.js` | zero |

Out of scope (owner rejected / deferred): confidence pill, entry-reason tag, size $ on card, hold duration, peak unrealized PnL, match state at exit.

---

## Exit Reason Label Map

Single source of truth: `FMT.exitReasonLabel(raw)` in [fmt.js](../../src/presentation/dashboard/static/js/fmt.js). Returns `{ text, emoji, tone }` where `tone ∈ { "pos", "neg", "neutral" }`. Tone drives CSS colour; `emoji` prefixes the text.

| Raw `exit_reason`              | Humanized text          | Emoji | Tone    |
|--------------------------------|-------------------------|-------|---------|
| `scale_out_tier_1`             | `TP1`                   | 🎯    | pos     |
| `scale_out_tier_2`             | `TP2`                   | 🎯    | pos     |
| `scale_out_tier_3`             | `TP3`                   | 🎯    | pos     |
| `stop_loss_l1` … `stop_loss_l9`| `SL L{n}`               | 🛑    | neg     |
| `score_exit_home_goal`         | `Score against (home)`  | ⚠️    | neg     |
| `score_exit_away_goal`         | `Score against (away)`  | ⚠️    | neg     |
| `score_exit_*`                 | `Score against`         | ⚠️    | neg     |
| `market_flip`                  | `Market flipped`        | 🔄    | neg     |
| `time_exit`                    | `Time exit`             | ⏱    | neutral |
| `directional_reversal`         | `Direction reversed`    | ↩️    | neg     |
| `manual_override`              | `Manual`                | 👤    | neutral |
| Unknown fallback               | raw string              | (none)| neutral |

Negative tone → card reason line rendered with existing `.feed-pnl-neg` colour so the reason itself reads "red" when the exit was adverse, independent of PnL sign.

---

## Layout

Three scenarios. All cards keep the existing anchor link, sport emoji, market title, and direction badge. The `feed-details`, `feed-impact`, and `feed-time` rows are recomposed.

### Full exit — winning

```
⚾  CAC vs CA Platense                          [PLA]
Entry 40¢  →  Exit 62¢              Odds 60.1%
+$18.20  (+55%)                     🎯 TP2
Held 2h 15m · 8m ago                            W
```

### Partial exit — Tier 1

```
⚾  CAC vs CA Platense               [PARTIAL] [PLA]
Entry 40¢  →  @ 48¢                 Odds 60.1%
+$7.68  (+24%)  ·  Remaining 60%
🎯 TP1
2m ago
```

### Full exit — negative (score exit)

```
⚽  Arsenal vs Man City                         [ARS]
Entry 55¢  →  Exit 32¢              Odds 58.0%
−$11.40  (−42%)                     ⚠️ Score against
Held 45m · 1h ago                               L
```

### Hold duration ("Held …")

The "Held …" string is a render-side computation from `entry_timestamp` → `exit_timestamp` via `FMT.durationShort(ms)`. Not a persisted field. Shown on full exits only; partial events omit it because the position is still open.

---

## HTML Structure

Target structure for `_exitedCard(t)` in [feed.js:168-199](../../src/presentation/dashboard/static/js/feed.js#L168-L199):

```html
<a class="feed-item" href="...">
  <div class="feed-top">
    <div class="feed-market-wrap">
      <span class="feed-tick">{emoji}</span>
      <span class="feed-market">{teams}</span>
    </div>
    {partialBadge?}<span class="feed-badge {dirCls}">{dir}</span>
  </div>

  <div class="feed-details">
    <span>Entry {entry}¢  →  {exitCell}</span>
    <span class="feed-odds">Odds {oddsPct}%</span>
  </div>

  <div class="feed-impact">
    <span class="{pnlClass}">{$PnL}</span>
    <span class="feed-pnl-pct {pnlClass}">({±pct}%)</span>
    {remainingCell?}
  </div>

  <div class="feed-exit-reason-row {toneClass}">
    {emoji} {humanizedReason}
  </div>

  <div class="feed-time">
    <span>{heldPrefix?}{relTime}</span>
    <span>{final_outcome}</span>
  </div>
</a>
```

Where:
- `exitCell` = `Exit {price}¢` (full) or `@ {price}¢` (partial with price) or `@ —` (legacy partial, no price).
- `oddsPct` = direction-adjusted render: `BUY_NO ? (1 − anchor) : anchor`, rounded to 0.1. Same formula as [feed.js:140-141](../../src/presentation/dashboard/static/js/feed.js#L140-L141) in the active card (DRY — reuse, do not duplicate).
- `remainingCell` rendered only when `partial === true`: `· Remaining {remainingPct}%`.
- `toneClass` ∈ `feed-reason-pos | feed-reason-neg | feed-reason-neutral`.
- `heldPrefix` rendered only on full exits: `Held {duration} · `.

---

## Backend Changes

### 1. `partial_exits[].price` — persist the fill price

[trade_logger.py:142-159](../../src/infrastructure/persistence/trade_logger.py#L142-L159) `log_partial_exit()` signature gains a `price: float` parameter. The serialized entry dict gains `"price": price`. Field is required going forward.

### 2. `exit_processor.py` call site — pass the price

[exit_processor.py:127-146](../../src/orchestration/exit_processor.py#L127-L146) — the partial call site already has access to the sell price in the exit signal (`signal.price` — the price at which the scale-out was evaluated against). Pass it through:

```python
trade_logger.log_partial_exit(
    condition_id=pos.condition_id,
    tier=signal.tier,
    sell_pct=signal.sell_pct,
    realized_pnl_usdc=realized,
    timestamp=now_iso,
    price=signal.price,   # NEW
)
```

If `signal.price` is not already the actual fill price, the existing source-of-truth for "price at scale-out" is used — this is a spec requirement, not a new field on `ExitSignal` unless verification shows it is missing. The plan phase verifies.

### 3. `computed.py::exit_events()` — enrich partial event dicts

[computed.py:131-159](../../src/presentation/dashboard/computed.py#L131-L159) — the partial branch currently returns a narrow dict. Extend it:

```python
cumulative_sell_pct = 0.0
for pe in (t.get("partial_exits") or []):
    cumulative_sell_pct += float(pe.get("sell_pct") or 0.0)
    events.append({
        # existing fields …
        "anchor_probability": t.get("anchor_probability"),   # NEW — needed for Odds %
        "partial_price": pe.get("price"),                    # NEW — may be None on legacy rows
        "remaining_pct": max(0.0, 1.0 - cumulative_sell_pct),# NEW
    })
```

Full-exit branch (`ev = dict(t)`) already carries `anchor_probability`; it additionally sets `"remaining_pct": 0.0` for uniformity.

### 4. `fmt.js` — new helpers

- `FMT.exitReasonLabel(raw) → { text, emoji, tone }` — the table above, pure function.
- `FMT.durationShort(ms) → string` — `"Xh Ym"` / `"Xm"` / `"Xs"`. Truncate, do not round up.

### 5. `feed.js::_exitedCard()` — recompose

Read the new fields, call the helpers, emit the HTML structure above. No business logic added; this file remains a pure renderer.

---

## Backward Compatibility

Historical `partial_exits[]` entries do not carry `price`. For those:
- `partial_price` is `None` / missing in the event dict.
- `exitCell` renders `@ —` (em-dash) instead of `@ {price}¢`.
- C12 "price delta" is not shown (no delta computable).
- No migration, no backfill. Legacy rows stay as-is; new partials carry the field.

`anchor_probability` is present on all trade rows (persisted since project start per the `P(YES)` rule — ARCHITECTURE_GUARD Rule 7). No legacy gap expected; if `None`, Odds % cell is hidden.

---

## Layer Boundaries

| Change               | Layer          | Rationale |
|----------------------|----------------|-----------|
| `trade_logger.log_partial_exit()` signature | Infrastructure | Persistence concern. |
| `exit_processor.py` call site               | Orchestration  | Glues strategy signal to persistence. |
| `computed.py::exit_events()`                | Presentation   | View-model computation. Already lives here for the exited tab. |
| `fmt.js` helpers                            | Presentation   | Pure formatting. |
| `feed.js::_exitedCard()`                    | Presentation   | Pure rendering. |

No domain changes. No new files. No new directories.

---

## Tests

### Unit — `computed.py::exit_events()`

- Trade with two partials (sell_pct 0.40, 0.30) and no full exit → two events with `remaining_pct = 0.60` and `0.30`, `partial_price` passed through.
- Trade with one partial then a full exit → three events (two partial + one final); final event `remaining_pct = 0.0`.
- Legacy partial without `price` key → event `partial_price is None`, other fields populated.
- `anchor_probability` propagated on both partial and full branches.

### Unit — `fmt.js` (JS testing pattern from existing suite, if present; otherwise skipped per repo convention)

- `FMT.exitReasonLabel("scale_out_tier_2")` → `{ text: "TP2", emoji: "🎯", tone: "pos" }`.
- `FMT.exitReasonLabel("stop_loss_l5")` → `{ text: "SL L5", emoji: "🛑", tone: "neg" }`.
- `FMT.exitReasonLabel("score_exit_home_goal")` → `{ text: "Score against (home)", emoji: "⚠️", tone: "neg" }`.
- Unknown string → raw passthrough, tone `"neutral"`.
- `FMT.durationShort(135 * 60 * 1000)` → `"2h 15m"`; `(45 * 60 * 1000)` → `"45m"`; `(30 * 1000)` → `"30s"`.

### Unit — `trade_logger.log_partial_exit()`

- New `price` argument persisted verbatim in the appended `partial_exits[]` entry.
- Missing `price` (if kept optional for a transition) defaults to `None` — *decision to defer to plan phase: required vs. optional.*

### Manual — dashboard

- Open dashboard with a recent partial scale-out. Card shows `@ {price}¢` and `Remaining {pct}%`.
- Trigger (or replay) a score-exit loss. Reason line renders `⚠️ Score against` in the negative tone colour.
- Open an old partial predating this change. Card shows `@ —`, no crash.

---

## Out of Scope

- Confidence pill / entry-reason tag on exit card (owner rejected).
- Peak unrealized PnL tracking (new state, deferred).
- Match state at exit (`Q3 08:45`, `FT`) — not persisted on the trade record, deferred.
- Migration/backfill of legacy `partial_exits[]` rows.
- CSS colour tokens for `feed-reason-pos/neg/neutral` — reuse existing `.feed-pnl-pos` / `.feed-pnl-neg` / default text colour.

---

## Open Questions (resolve in plan phase)

1. **`ExitSignal.price`** — does the scale-out signal already carry the evaluation price at the orchestration call site? If not, surface it or fetch from the current `MarketState` at call time. Plan must verify against [scale_out.py](../../src/strategy/exit/scale_out.py) and [exit_processor.py](../../src/orchestration/exit_processor.py).
2. **`price` as required vs. optional** on `log_partial_exit()` — required (no overload period) unless any live code path cannot supply it. Default recommendation: required.
