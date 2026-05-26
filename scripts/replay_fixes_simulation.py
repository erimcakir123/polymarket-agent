"""Replay simulation: actual P&L vs hypothetical "fixes-active" P&L.

Reads trade audit log + Polymarket resolved market state, then for each trade
computes what P&L would have been IF today's fixes had been active:
  Fix 1: Bimodal SL exempt -> held-to-resolution simulation for SL-exited bimodal trades
  Fix 2: Same-market-type guard (A+B) -> identifies blocked duplicate trades
  Fix 3: Resolved bug fix (sustained price) -> false-positive transient exits

Outputs:
  - logs/_replay_market_state.json (Polymarket state cache; one HTTP call per
    unique condition_id)
  - data/replay_simulation.json (per-trade simulation results consumed by the
    dashboard reader)
  - Stdout: aggregate + per-trade impact summary

Re-runnable: idempotent. Re-fetches Polymarket state, regenerates the JSON.
Run manually after a session of trades to refresh dashboard simulation overlay:
  python scripts/replay_fixes_simulation.py
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRADE_LOG_AUDIT = REPO / "logs" / "audit" / "trade_history.jsonl"
TRADE_LOG_SESSION = REPO / "logs" / "session" / "trade_history.jsonl"
STATE_FILE = REPO / "logs" / "_replay_market_state.json"
SIMULATION_FILE = REPO / "data" / "replay_simulation.json"

BIMODAL_MTS = {"set_handicap", "set_totals", "match_totals", "first_set_totals"}
SL_REASONS = {"stop_loss", "graduated_sl"}
RESOLVED_TRANSIENT_PRICE = 0.05
GAMMA_BASE = "https://gamma-api.polymarket.com"
HTTP_TIMEOUT = 15
SCHEMA_VERSION = 1


def market_type(slug: str) -> str:
    m = re.search(r"\d{4}-\d{2}-\d{2}-(.+)$", slug)
    if not m:
        return "moneyline"
    tail = m.group(1)
    if tail.startswith("first-set-totals"): return "first_set_totals"
    if tail.startswith("first-set-winner"): return "first_set_winner"
    if tail.startswith("set-totals"): return "set_totals"
    if tail.startswith("set-handicap"): return "set_handicap"
    if tail.startswith("match-total"): return "match_totals"
    return tail.split("-")[0]


def actual_pnl(t: dict) -> float:
    return t["exit_pnl_usdc"] + sum(
        p.get("realized_pnl_usdc", 0) for p in t.get("partial_exits", [])
    )


def if_held_pnl(t: dict, state: dict | None) -> float | None:
    if state is None or not state.get("closed"):
        return None
    op = state.get("outcomePrices")
    if not op or len(op) < 2:
        return None
    yes_final = float(op[0])
    no_final = float(op[1])
    initial_cost = t["size_usdc"]
    initial_shares = t.get("shares", 0)
    usd_from_partials = 0.0
    rem_shares = initial_shares
    for p in t.get("partial_exits", []):
        sold = rem_shares * p.get("sell_pct", 0)
        usd_from_partials += sold * p.get("price", 0)
        rem_shares -= sold
    final_price = yes_final if t["direction"] == "BUY_YES" else no_final
    usd_from_final = rem_shares * final_price
    return (usd_from_partials + usd_from_final) - initial_cost


def fetch_market_by_slug(slug: str) -> dict | None:
    for params in ({"slug": slug}, {"slug": slug, "closed": "true"}):
        url = f"{GAMMA_BASE}/markets?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data:
                return data[0]
        except Exception:
            continue
    return None


def load_trades() -> list[dict]:
    """Audit + session birleşik (audit ground truth, session yeni eklemeler)."""
    out: list[dict] = []
    for path in (TRADE_LOG_AUDIT, TRADE_LOG_SESSION):
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    out.append(json.loads(line))
    # Dedupe by (condition_id, entry_timestamp); prefer record with more data
    by_key: dict[tuple[str, str], dict] = {}
    for r in out:
        key = (r.get("condition_id", ""), r.get("entry_timestamp", ""))
        ex = by_key.get(key)
        if ex is None:
            by_key[key] = r
            continue
        # Prefer the more-complete record
        new_score = (len(r.get("partial_exits") or []), int(r.get("exit_price") is not None))
        ex_score = (len(ex.get("partial_exits") or []), int(ex.get("exit_price") is not None))
        if new_score > ex_score:
            by_key[key] = r
    return list(by_key.values())


def refresh_market_state(trades: list[dict]) -> dict[str, dict | None]:
    """Fetch + cache Polymarket resolved state for every unique market."""
    cid_to_slug: dict[str, str] = {}
    for t in trades:
        cid_to_slug[t["condition_id"]] = t["slug"]
    results: dict[str, dict | None] = {}
    for i, (cid, slug) in enumerate(sorted(cid_to_slug.items()), 1):
        m = fetch_market_by_slug(slug)
        if m is None:
            results[cid] = None
            continue
        op = m.get("outcomePrices")
        if isinstance(op, str):
            try: op = json.loads(op)
            except Exception: pass
        results[cid] = {
            "slug": slug,
            "closed": m.get("closed"),
            "resolved": m.get("resolved"),
            "outcomePrices": op,
        }
        if i % 10 == 0:
            print(f"  fetched {i}/{len(cid_to_slug)}")
        time.sleep(0.1)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return results


def build_simulation(trades: list[dict], states: dict) -> dict:
    """Build the per-trade simulation overlay consumed by the dashboard."""
    closed = [t for t in trades if "exit_pnl_usdc" in t and t.get("exit_timestamp")]

    # Fix 2: identify duplicate (event_id, market_type) — 1st allowed, rest blocked
    seen: dict[tuple[str, str], dict] = {}
    chronological = sorted(closed, key=lambda t: t.get("entry_timestamp", ""))
    blocked_keys: set[tuple[str, str]] = set()
    for t in chronological:
        key = (t.get("event_id", ""), market_type(t["slug"]))
        if not key[0]:
            continue
        if key in seen:
            blocked_keys.add((t["condition_id"], t["entry_timestamp"]))
        else:
            seen[key] = t

    entries: list[dict] = []
    f1_delta = 0.0
    f2_delta = 0.0
    f3_delta = 0.0
    for t in closed:
        key = (t["condition_id"], t["entry_timestamp"])
        mt = market_type(t["slug"])
        actual = actual_pnl(t)
        state = states.get(t["condition_id"])
        is_blocked = key in blocked_keys
        entry: dict = {
            "condition_id": t["condition_id"],
            "entry_timestamp": t["entry_timestamp"],
            "slug": t["slug"],
            "actual_pnl_usdc": round(actual, 4),
            "market_closed": state.get("closed") if state else None,
            "market_outcome_yes": (
                float(state["outcomePrices"][0])
                if state and state.get("outcomePrices") else None
            ),
            "fixes": [],
        }
        # Fix 1: bimodal SL exempt
        if mt in BIMODAL_MTS and t.get("exit_reason") in SL_REASONS and not is_blocked:
            held = if_held_pnl(t, state)
            if held is not None:
                delta = held - actual
                f1_delta += delta
                entry["fixes"].append({
                    "label": "bimodal_sl_exempt",
                    "if_held_pnl_usdc": round(held, 4),
                    "delta_usdc": round(delta, 4),
                })
        # Fix 2: same_market_type guard (this trade would be BLOCKED)
        if is_blocked:
            f2_delta += -actual  # avoiding this trade saves us its actual P&L
            entry["fixes"].append({
                "label": "same_market_type_blocked",
                "if_held_pnl_usdc": 0.0,
                "delta_usdc": round(-actual, 4),
            })
        # Fix 3: resolved bug fix (transient false-positive)
        if (
            t.get("exit_reason") == "resolved"
            and (t.get("exit_price") or 1.0) < RESOLVED_TRANSIENT_PRICE
            and not is_blocked
        ):
            held = if_held_pnl(t, state)
            if held is not None:
                delta = held - actual
                f3_delta += delta
                entry["fixes"].append({
                    "label": "resolved_sustained_check",
                    "if_held_pnl_usdc": round(held, 4),
                    "delta_usdc": round(delta, 4),
                })
        if entry["fixes"]:
            entries.append(entry)

    overall_actual = sum(actual_pnl(t) for t in closed)
    compound_delta = f1_delta + f2_delta + f3_delta
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trades_total": len(closed),
        "trades_affected": len(entries),
        "summary": {
            "actual_pnl_usdc": round(overall_actual, 2),
            "fix1_bimodal_sl_delta": round(f1_delta, 2),
            "fix2_same_market_type_delta": round(f2_delta, 2),
            "fix3_resolved_bug_delta": round(f3_delta, 2),
            "compound_delta_usdc": round(compound_delta, 2),
            "simulated_pnl_usdc": round(overall_actual + compound_delta, 2),
        },
        "trades": entries,
    }


def print_summary(sim: dict) -> None:
    s = sim["summary"]
    print()
    print("=" * 80)
    print(f"REPLAY SIMULATION  generated_at={sim['generated_at']}")
    print("=" * 80)
    print(f"  trades_total:    {sim['trades_total']}")
    print(f"  trades_affected: {sim['trades_affected']}")
    print(f"  actual P&L:                          ${s['actual_pnl_usdc']:+.2f}")
    print(f"  Fix 1 (Bimodal SL exempt) delta:     ${s['fix1_bimodal_sl_delta']:+.2f}")
    print(f"  Fix 2 (Same market type) delta:      ${s['fix2_same_market_type_delta']:+.2f}")
    print(f"  Fix 3 (Resolved bug) delta:          ${s['fix3_resolved_bug_delta']:+.2f}")
    print(f"  Compound delta:                      ${s['compound_delta_usdc']:+.2f}")
    print(f"  Simulated (all fixes active) P&L:    ${s['simulated_pnl_usdc']:+.2f}")
    print()


def main() -> None:
    trades = load_trades()
    print(f"Loaded {len(trades)} unique trade records")
    print(f"Refreshing Polymarket state for {len({t['condition_id'] for t in trades})} markets...")
    states = refresh_market_state(trades)
    sim = build_simulation(trades, states)
    SIMULATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SIMULATION_FILE.write_text(
        json.dumps(sim, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"Wrote {SIMULATION_FILE.relative_to(REPO)} ({sim['trades_affected']} affected trades)")
    print_summary(sim)


if __name__ == "__main__":
    main()
