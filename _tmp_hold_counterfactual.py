"""Hold-all-to-resolution counterfactual using three methods:
A) Ground truth (yes_won) — only 20 trades
B) Bookmaker-EV model — for trades with bookmaker_prob
C) AI-probability model — for all trades with ai_prob

Also: entry count, per-exit-rule behavior, full-table.
Read-only. No network. No code changes.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict

TRADES = Path("logs/trades.jsonl")
OUTCOMES = Path("logs/match_outcomes.jsonl")
TODAY = "2026-04-10"

ENTRY_ACTIONS = {"BUY", "UPSET_ENTRY"}
FORCED_REASONS = {
    "match_exit_a_conf_market_flip",
    "match_exit_catastrophic_floor",
    "match_exit_graduated_sl",
    "match_exit_upset_max_hold",
    "stop_loss",
}

def sport_family(tag: str, slug: str = "") -> str:
    s = (tag or "").lower() + " " + (slug or "").lower()
    if "nba" in s: return "NBA"
    if "nhl" in s: return "NHL"
    if "mlb" in s: return "MLB"
    if "atp" in s: return "ATP"
    if "wta" in s: return "WTA"
    if "boxing" in s: return "Boxing"
    if "mma" in s or "ufc" in s: return "MMA"
    if "euroleague" in s: return "EuroLeague"
    soccer_tags = ["sud","lib","aus","fl1","fl2","fr1","fr2","ligue","bl1","bl2","bun",
                   "elc","epl","ere","sea","tur","den","ita","esp","por","ned","mls",
                   "serie","la-liga","premier","primera","a-league","bundes","eredivisie"]
    if any(x in s for x in soccer_tags): return "Soccer"
    return "other"

def hold_pnl_outcome(direction: str, entry_price: float, size: float, yes_won: bool) -> float:
    if direction == "BUY_YES":
        cps = entry_price
        if cps <= 0: return 0.0
        shares = size / cps
        return shares * (1.0 if yes_won else 0.0) - size
    cps = 1.0 - entry_price
    if cps <= 0: return 0.0
    shares = size / cps
    return shares * (0.0 if yes_won else 1.0) - size

def ev_pnl(direction: str, entry_price: float, size: float, true_prob: float) -> float:
    """Expected value PnL if 'true_prob' is the real probability of YES winning."""
    if direction == "BUY_YES":
        cps = entry_price
        if cps <= 0: return 0.0
        shares = size / cps
        return shares * true_prob - size
    cps = 1.0 - entry_price
    if cps <= 0: return 0.0
    shares = size / cps
    return shares * (1 - true_prob) - size

# =============================================================================
# Load data
# =============================================================================
entries = {}
exits = defaultdict(list)
scale_outs = defaultdict(list)

with open(TRADES, encoding="utf-8") as f:
    for line in f:
        try: e = json.loads(line)
        except: continue
        ts = e.get("timestamp", "")
        if not ts.startswith(TODAY): continue
        act = e.get("action"); slug = e.get("market", "")
        if act in ENTRY_ACTIONS:
            entries[slug] = e
        elif act == "EXIT":
            exits[slug].append(e)
        elif act == "SCALE_OUT":
            scale_outs[slug].append(e)

resolved = {}
with open(OUTCOMES, encoding="utf-8") as f:
    for line in f:
        try: d = json.loads(line)
        except: continue
        resolved[d.get("slug")] = d

# =============================================================================
# 1) ENTRY COUNT + EXIT RULE BREAKDOWN
# =============================================================================
print("=" * 100)
print("1) TODAY'S ENTRY + EXIT RULE SUMMARY")
print("=" * 100)
print(f"\nTotal entries (BUY + UPSET_ENTRY): {len(entries)}")
buy_cnt = sum(1 for e in entries.values() if e.get("action") == "BUY")
upset_cnt = sum(1 for e in entries.values() if e.get("action") == "UPSET_ENTRY")
print(f"  BUY          : {buy_cnt}")
print(f"  UPSET_ENTRY  : {upset_cnt}")

print(f"\nClosure events:")
print(f"  EXIT         : {sum(len(v) for v in exits.values())}")
print(f"  SCALE_OUT    : {sum(len(v) for v in scale_outs.values())}")
print(f"  total        : {sum(len(v) for v in exits.values()) + sum(len(v) for v in scale_outs.values())}")

# Per exit rule
rule_stats = defaultdict(lambda: {"cnt": 0, "pnl": 0.0, "wins": 0, "losses": 0})
for slug, evs in exits.items():
    for ex in evs:
        r = ex.get("reason", "?")
        pnl = ex.get("total_pnl", ex.get("pnl", 0.0)) or 0.0
        rule_stats[r]["cnt"] += 1
        rule_stats[r]["pnl"] += pnl
        if pnl > 0.01: rule_stats[r]["wins"] += 1
        elif pnl < -0.01: rule_stats[r]["losses"] += 1
for slug, sos in scale_outs.items():
    for so in sos:
        r = f"SCALE_{so.get('tier','?')}"
        pnl = so.get("realized_pnl", 0.0) or 0.0
        rule_stats[r]["cnt"] += 1
        rule_stats[r]["pnl"] += pnl
        if pnl > 0.01: rule_stats[r]["wins"] += 1
        elif pnl < -0.01: rule_stats[r]["losses"] += 1

print(f"\n{'Exit rule':38s} {'cnt':>4s} {'W/L':>9s} {'net pnl':>10s}")
for r in sorted(rule_stats.keys(), key=lambda x: rule_stats[x]["pnl"]):
    v = rule_stats[r]
    print(f"{r:38s} {v['cnt']:>4d} {v['wins']:>3d}/{v['losses']:<4d} {v['pnl']:+10.2f}")
total_net = sum(v['pnl'] for v in rule_stats.values())
total_cnt = sum(v['cnt'] for v in rule_stats.values())
print(f"{'TOTAL':38s} {total_cnt:>4d}            {total_net:+10.2f}")

# =============================================================================
# 2) HOLD-ALL COUNTERFACTUAL — 3 METHODS
# =============================================================================
print("\n" + "=" * 100)
print("2) IF WE HAD NEVER EXITED — hold-to-resolution counterfactual (3 methods)")
print("=" * 100)

# Build a master table: one row per entry today, with actual pnl + 3 hypothetical pnls
master = []
for slug, b in entries.items():
    entry_price = b.get("entry_price")
    direction = b.get("direction", "")
    size = b.get("size_usdc", 0.0)
    ai_prob = b.get("ai_prob")
    bm_prob = b.get("bookmaker_prob")
    sport = sport_family(b.get("sport_tag", "") or "", slug)
    if entry_price is None:
        continue

    # Actual realized = sum of exit pnls + unrealized (open positions have 0 realized here)
    actual = 0.0
    has_exit = False
    for ex in exits.get(slug, []):
        actual += ex.get("total_pnl", ex.get("pnl", 0.0)) or 0.0
        has_exit = True
    if not has_exit:
        for so in scale_outs.get(slug, []):
            actual += so.get("realized_pnl", 0.0) or 0.0

    # Method A: ground truth
    ground = None
    if slug in resolved and resolved[slug].get("yes_won") is not None:
        ground = hold_pnl_outcome(direction, entry_price, size, bool(resolved[slug]["yes_won"]))

    # Method B: bookmaker EV
    bm_ev = None
    if bm_prob not in (None, 0, 0.0):
        bm_ev = ev_pnl(direction, entry_price, size, bm_prob)

    # Method C: AI EV
    ai_ev = None
    if ai_prob is not None:
        ai_ev = ev_pnl(direction, entry_price, size, ai_prob)

    # Market-implied EV (if we believe the market) — useful as sanity check
    mkt_ev = ev_pnl(direction, entry_price, size, entry_price)

    master.append({
        "slug": slug, "sport": sport, "dir": direction, "entry": entry_price,
        "size": size, "ai_prob": ai_prob, "bm_prob": bm_prob,
        "actual": actual, "ground": ground, "bm_ev": bm_ev, "ai_ev": ai_ev, "mkt_ev": mkt_ev,
        "has_exit": has_exit,
        "status": "RESOLVED" if ground is not None else ("OPEN" if not has_exit else "EXITED_UNRESOLVED"),
    })

# Summary totals
print(f"\n{'Method':35s} {'Coverage':>10s} {'Actual':>10s} {'Hypothetical':>14s} {'Δ (gain/loss)':>15s}")
actual_sum = sum(m["actual"] for m in master)

# Method A: ground truth
resolved_rows = [m for m in master if m["ground"] is not None]
actual_A = sum(m["actual"] for m in resolved_rows)
hypo_A = sum(m["ground"] for m in resolved_rows)
print(f"{'A) Ground truth (yes_won)':35s} {len(resolved_rows):>10d} {actual_A:+10.2f} {hypo_A:+14.2f} {hypo_A-actual_A:+15.2f}")

# Method B: bookmaker EV — cover all rows with bm_prob
bm_rows = [m for m in master if m["bm_ev"] is not None]
actual_B = sum(m["actual"] for m in bm_rows)
hypo_B = sum(m["bm_ev"] for m in bm_rows)
print(f"{'B) Bookmaker-EV model':35s} {len(bm_rows):>10d} {actual_B:+10.2f} {hypo_B:+14.2f} {hypo_B-actual_B:+15.2f}")

# Method C: AI EV — cover all rows with ai_prob
ai_rows = [m for m in master if m["ai_ev"] is not None]
actual_C = sum(m["actual"] for m in ai_rows)
hypo_C = sum(m["ai_ev"] for m in ai_rows)
print(f"{'C) AI-probability model':35s} {len(ai_rows):>10d} {actual_C:+10.2f} {hypo_C:+14.2f} {hypo_C-actual_C:+15.2f}")

# Mixed: A where resolved, B for rest (best available)
mixed_actual = 0.0
mixed_hypo = 0.0
used_A = used_B = used_none = 0
for m in master:
    mixed_actual += m["actual"]
    if m["ground"] is not None:
        mixed_hypo += m["ground"]; used_A += 1
    elif m["bm_ev"] is not None:
        mixed_hypo += m["bm_ev"]; used_B += 1
    elif m["ai_ev"] is not None:
        mixed_hypo += m["ai_ev"]
    else:
        mixed_hypo += m["actual"]; used_none += 1
print(f"{'MIXED (A if resolved, else B)':35s} {len(master):>10d} {mixed_actual:+10.2f} {mixed_hypo:+14.2f} {mixed_hypo-mixed_actual:+15.2f}")
print(f"  ({used_A} resolved + {len(master)-used_A-used_none} bm-ev + {used_none} no-data)")

# =============================================================================
# 3) PER-SPORT HOLD COUNTERFACTUAL (using mixed)
# =============================================================================
print("\n" + "=" * 100)
print("3) PER-SPORT HOLD COUNTERFACTUAL — mixed method")
print("=" * 100)
per_sport = defaultdict(lambda: {"cnt":0,"actual":0.0,"hypo":0.0,"resolved":0,"bm":0,"none":0})
for m in master:
    s = per_sport[m["sport"]]
    s["cnt"] += 1
    s["actual"] += m["actual"]
    if m["ground"] is not None:
        s["hypo"] += m["ground"]; s["resolved"] += 1
    elif m["bm_ev"] is not None:
        s["hypo"] += m["bm_ev"]; s["bm"] += 1
    else:
        s["hypo"] += m["actual"]; s["none"] += 1

print(f"{'Sport':12s} {'N':>4s} {'Actual':>9s} {'HypoHold':>10s} {'Δ':>9s} {'Resolved':>9s} {'BM-EV':>6s} {'?':>3s}")
for sp in sorted(per_sport.keys(), key=lambda x: per_sport[x]["hypo"]-per_sport[x]["actual"]):
    v = per_sport[sp]
    diff = v["hypo"]-v["actual"]
    print(f"{sp:12s} {v['cnt']:>4d} {v['actual']:+9.2f} {v['hypo']:+10.2f} {diff:+9.2f} {v['resolved']:>9d} {v['bm']:>6d} {v['none']:>3d}")

# =============================================================================
# 4) FULL TABLE — every entry with actual + hypotheticals
# =============================================================================
print("\n" + "=" * 110)
print("4) FULL TABLE — every entry today: actual vs. all hypotheticals")
print("=" * 110)
print(f"{'sport':10s} {'slug':36s} {'dir':7s} {'ent':>5s} {'sz':>6s} {'status':>18s} {'actual':>8s} {'ground':>8s} {'bm_ev':>8s} {'ai_ev':>8s}")
for m in sorted(master, key=lambda x: (x["sport"], -x["actual"])):
    def fmt(v): return f"{v:+8.2f}" if v is not None else "    --  "
    print(f"{m['sport']:10s} {m['slug'][:36]:36s} {m['dir']:7s} {m['entry']:5.2f} {m['size']:6.2f} {m['status']:>18s} {fmt(m['actual'])} {fmt(m['ground'])} {fmt(m['bm_ev'])} {fmt(m['ai_ev'])}")
