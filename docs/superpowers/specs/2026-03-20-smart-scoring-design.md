# Smart Scoring v1 — Design Spec

_2026-03-20_

## Problem

1. **Low confidence bets lose money** — self-improve data shows 15%+ edge bets have 40% win rate
2. **Spread eats low edge profits** — ~4.5% round-trip spread means <7% edge is break-even
3. **Time value ignored** — $2 profit in 2 hours vs $2 profit in 2 days treated equally
4. **3-level confidence too coarse** — "medium" is too broad, covers borderline-bad and borderline-good

## Solution

Three changes to the scoring/filtering system:

### 1. Four-Level Confidence

AI prompt outputs: `low | medium_low | medium_high | high`

| Level | Meaning | Action |
|-------|---------|--------|
| high | Strong data, clear direction | ENTER |
| medium_high | Good data, reasonable direction | ENTER |
| medium_low | Weak data, uncertain | SKIP |
| low | No data or contradictory | SKIP |

Confidence is determined conservatively: `min(pro_confidence, con_confidence)`.

### 2. Minimum Edge 8%

`config.yaml: min_edge: 0.08`

After ~4.5% spread cost, this guarantees ~3.5% net profit minimum.

### 3. Time-Weighted Score

```
conf_score = {high: 4, medium_high: 3, medium_low: 2, low: 1}
remaining_hours = clamp(hours_until_end_date, min=1, max=168)
score = edge × conf_score / remaining_hours
```

Higher score = better opportunity. Fast-resolving bets with good edge rank highest.

## File Changes

### `src/ai_analyst.py`
- PRO/CON prompts: `"confidence": "low|medium_low|medium_high|high"`
- `conf_order` dict: add `medium_low: 1, medium_high: 2` (reindex to 0-3)
- `conf_map` dict: 4 entries

### `config.yaml`
- `min_edge: 0.08`
- `confidence_multipliers`: add `medium_low: 1.25`, `medium_high: 1.0`

### `src/main.py`
- `_CONF_SCORE = {high: 4, medium_high: 3, medium_low: 2, low: 1}`
- After edge check, skip if `confidence in ("low", "medium_low")`
- Score formula: `edge × conf_score / remaining_hours`
- `remaining_hours`: parse `end_date_iso`, clamp 1-168
- Slot upgrade: recalculate existing position scores with current remaining_hours

### No changes to
- `src/edge_calculator.py` (reads multipliers from config)
- `src/models.py` (no schema change)
- `src/portfolio.py` (no change)

## Examples

| Bet | Edge | Conf | Hours Left | Score |
|-----|------|------|-----------|-------|
| NBA tonight | 10% | high(4) | 3h | 0.133 |
| NBA tomorrow | 10% | high(4) | 24h | 0.017 |
| Esports tomorrow | 12% | medium_high(3) | 20h | 0.018 |
| Politics next week | 15% | high(4) | 168h | 0.004 |
| Sketchy high-edge | 20% | low(1) | 5h | SKIP |

## Safety

- Does not change budget, mode, or risk limits
- Backwards compatible: existing positions unaffected
- Only affects new bet selection and slot upgrades
