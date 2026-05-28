# ESPN Scoreboard + match_start_iso Refresh Plan

> **For agentic workers:** Use superpowers:subagent-driven-development.

**Goal:** Fix the stale-cache bug where bot's `match_start_iso` is set once at position open and never refreshed — even when Polymarket reschedules a match. Symptoms:
- LIVE badge fires falsely (cached start passed, real start later)
- graduated_sl uses wrong elapsed_pct (over-aggressive SL)
- Scanner can't distinguish today vs tomorrow matches properly

**Approach:**
- (Light fix) Light cycle re-fetches `gameStartTime` from Polymarket for open positions periodically.
- (Optional, larger) ESPN scoreboard integration for live match status — separate from this minimal fix.

**Repo:** `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\`

---

## Task 1: Light-cycle match_start_iso refresh

**Files:**
- Modify: `src/orchestration/tennis_agent.py` (light cycle hook)
- Modify: `src/orchestration/scanner.py` OR a new small helper that re-fetches `gameStartTime` per condition_id
- Modify: tests

**Approach:** every N light cycles (configurable, default every 60 ticks = ~5 min), fetch fresh `gameStartTime` for open positions from Polymarket gamma API. Update position's `match_start_iso` in-place if changed.

- [ ] **Step 1: Inspect current light cycle structure**

```bash
PYTHONIOENCODING=utf-8 grep -n "light_cycle\|run_light\|_light_tick" src/orchestration/tennis_agent.py
```

Read the function. Note where exit_processor is called and add a refresh hook BEFORE exit checks (so SL/scale-out use fresh data).

- [ ] **Step 2: Write failing test**

```python
def test_light_cycle_refreshes_match_start_periodically() -> None:
    """Every Nth light tick, open positions get match_start_iso updated from gamma."""
    # Mock gamma_client returning different gameStartTime
    # Run light cycle N+1 times
    # Assert position's match_start_iso updated to new value on Nth call
    pass  # IMPLEMENT
```

- [ ] **Step 3: Add refresh helper**

New helper in `src/orchestration/tennis_agent.py` (or new file `src/orchestration/match_start_refresh.py`):

```python
def refresh_match_start_for_open_positions(
    portfolio,
    gamma_client,
) -> int:
    """Re-fetch gameStartTime from gamma for each open position; update in-place.

    Returns: count of positions whose match_start_iso changed.
    """
    updated = 0
    for pos in portfolio.positions:
        cid = pos.condition_id
        try:
            market = gamma_client.fetch_market_by_condition_id(cid)
            new_start = (market.get("gameStartTime") or "").replace(" ", "T").replace("+00", "Z")
            if new_start and new_start != pos.match_start_iso:
                pos.match_start_iso = new_start
                updated += 1
        except Exception as e:
            logger.debug("Failed to refresh match_start for %s: %s", cid, e)
    return updated
```

(`gamma_client.fetch_market_by_condition_id` may not exist — add it. Mirror existing fetch_events but filter by condition_id.)

- [ ] **Step 4: Wire into light cycle**

In tennis_agent light cycle:

```python
_light_tick_state["count"] += 1
if _light_tick_state["count"] % cfg.tennis.match_start_refresh_every_n_ticks == 0:
    n_updated = refresh_match_start_for_open_positions(
        portfolio=deps.state.portfolio,
        gamma_client=deps.gamma_client,
    )
    if n_updated > 0:
        logger.info("Refreshed match_start for %d positions", n_updated)
```

Add `match_start_refresh_every_n_ticks: int = 60` to TennisConfig.

- [ ] **Step 5: Tests + commit**

```bash
git add src/ tests/ config_tennis.yaml
git commit -m "fix(agent): refresh match_start_iso periodically (stale-cache bug fix)"
```

---

## Per-task drift check

```bash
PYTHONIOENCODING=utf-8 grep -rn "refresh_match_start\|match_start_refresh" src/ tests/ 2>/dev/null
```

All hits in new code.

---

## ESPN scoreboard integration — DEFERRED

ESPN live scoreboard for live tennis scores would be a useful addition for graduated_sl's score_info input. But ESPN's tennis API is limited and unreliable (we tested earlier — returns single "Final" event). Better alternative: tennis-live-data APIs (paid). Defer until later.
