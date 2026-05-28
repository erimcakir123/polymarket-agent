# SPEC: "resolved" reason firing on non-resolved markets

**Status:** DRAFT 2026-05-26

## Symptom

Bot exit_reason="resolved" + exit_price=0.01 on `wta-zakharo-muchova-2026-05-24-set-totals-2pt5` at 2026-05-25T19:18Z. Polymarket cross-check at 2026-05-26 showed:
- `closed=False`, `resolved=False`
- `outcomePrices_YES=0.49` (NOT resolved)

Bot lost $19.29 on a position that should still be open (market not actually decided yet).

## Suspected location

`src/strategy/exit/resolved.py` — contains the resolved-detection logic. Other contributors:
- WS price feed (may push extreme prices like 0.01 even pre-resolution)
- Order book staleness (very thin book gives misleading "best price")

## Required investigation

1. Read `resolved.py` — what condition fires "resolved" reason?
2. Read WS price callback path — under what conditions is `current_price=0.01` pushed?
3. Reconstruct: at 19:18Z what was the actual market state?
4. Identify the false-positive condition.

## Required fix

Add guards:
- "resolved" reason must verify Polymarket flag (`market.closed=True` OR `market.resolved=True`), not just price
- Single-tick extreme price (0.01) → NOT enough to declare resolved (need confirmation tick OR Polymarket flag)
- Possibly: ignore prices below threshold (e.g., 0.02) unless other evidence

## Acceptance

- Re-running the zakharo scenario in tests: bot does NOT exit with "resolved" when current_price=0.01 but `pos.event_ended=False` and gamma flag not set
- Existing legitimate "resolved" exits (e.g., parks set-handicap at 0.005 final) still fire correctly
- All exit tests pass
