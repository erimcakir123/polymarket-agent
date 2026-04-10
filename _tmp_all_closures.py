"""List ALL closure events today (since reset at 00:33 UTC).
Includes EXIT + SCALE_OUT events, grouped by sport, with resolution status.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict

TODAY = "2026-04-10"
TRADES = Path("logs/trades.jsonl")
OUTCOMES = Path("logs/match_outcomes.jsonl")

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

# Resolved outcomes (ground truth)
resolved = {}
with open(OUTCOMES, encoding="utf-8") as f:
    for line in f:
        try:
            d = json.loads(line)
            resolved[d.get("slug")] = d.get("yes_won")
        except: pass

# Entries (for sport_tag + entry price reference)
entries = {}
events = []  # list of (time, type, slug, direction, reason, pnl, sport, size_or_shares)

with open(TRADES, encoding="utf-8") as f:
    for line in f:
        try: d = json.loads(line)
        except: continue
        ts = d.get("timestamp", "")
        if not ts.startswith(TODAY): continue
        act = d.get("action")
        slug = d.get("market", "")
        if act in ("BUY", "UPSET_ENTRY"):
            entries[slug] = d
            continue
        if act == "EXIT":
            pnl = d.get("total_pnl", d.get("pnl", 0)) or 0
            reason = d.get("reason", "")
            direction = d.get("direction", "")
            size = d.get("size", 0)
            sport = sport_family(entries.get(slug, {}).get("sport_tag", ""), slug)
            events.append({
                "t": ts[11:19], "type": "EXIT", "slug": slug, "sport": sport,
                "dir": direction, "reason": reason, "pnl": pnl, "size": size,
                "yes_won": resolved.get(slug),
            })
        elif act == "SCALE_OUT":
            pnl = d.get("realized_pnl", 0) or 0
            tier = d.get("tier", "")
            sport = sport_family(entries.get(slug, {}).get("sport_tag", ""), slug)
            events.append({
                "t": ts[11:19], "type": "SCALEOUT", "slug": slug, "sport": sport,
                "dir": entries.get(slug, {}).get("direction", ""),
                "reason": tier, "pnl": pnl, "size": d.get("sell_pct", 0) * 100,
                "yes_won": resolved.get(slug),
            })

# Summary
wins = [e for e in events if e["pnl"] > 0.01]
losses = [e for e in events if e["pnl"] < -0.01]
flats = [e for e in events if -0.01 <= e["pnl"] <= 0.01]

print(f"Total closure events today: {len(events)}")
print(f"  Wins  (pnl > 0): {len(wins)}    sum = {sum(e['pnl'] for e in wins):+.2f}")
print(f"  Losses (pnl < 0): {len(losses)}  sum = {sum(e['pnl'] for e in losses):+.2f}")
print(f"  Flat  (pnl ~0):  {len(flats)}")
print(f"  Net PnL: {sum(e['pnl'] for e in events):+.2f}")
print()

# ------ Per-sport summary ------
by_sport = defaultdict(lambda: {"cnt":0,"w":0,"l":0,"pnl":0.0,"forced":0,"near":0,"so":0})
for e in events:
    s = by_sport[e["sport"]]
    s["cnt"] += 1
    s["pnl"] += e["pnl"]
    if e["pnl"] > 0.01: s["w"] += 1
    elif e["pnl"] < -0.01: s["l"] += 1
    if e["type"] == "SCALEOUT":
        s["so"] += 1
    elif e["reason"].startswith("match_exit") or e["reason"] == "stop_loss":
        s["forced"] += 1
    elif e["reason"] == "near_resolve_profit":
        s["near"] += 1

print("=" * 90)
print("PER-SPORT SUMMARY")
print("=" * 90)
print(f"{'sport':12s} {'events':>7s} {'W/L':>9s} {'net pnl':>10s} | {'forced':>7s} {'near_res':>9s} {'scale':>6s}")
for sp in sorted(by_sport.keys(), key=lambda x: by_sport[x]["pnl"]):
    v = by_sport[sp]
    print(f"{sp:12s} {v['cnt']:>7d} {v['w']:>3d}/{v['l']:<4d} {v['pnl']:+10.2f} | {v['forced']:>7d} {v['near']:>9d} {v['so']:>6d}")
print("-" * 90)
tot = sum(v['pnl'] for v in by_sport.values())
print(f"{'GRAND':12s} {len(events):>7d} {len(wins):>3d}/{len(losses):<4d} {tot:+10.2f}")

# ------ Full list sorted by PnL ------
print()
print("=" * 95)
print("ALL CLOSURE EVENTS (sorted by PnL descending)")
print("=" * 95)
print(f"{'time':8s} {'type':8s} {'sport':10s} {'slug':38s} {'dir':7s} {'reason':22s} {'won':>4s} {'pnl':>8s}")
for e in sorted(events, key=lambda x: x["pnl"], reverse=True):
    yw = "?" if e["yes_won"] is None else ("Y" if e["yes_won"] else "N")
    rsn = e["reason"].replace("match_exit_", "m_")[:22]
    print(f"{e['t']:8s} {e['type']:8s} {e['sport']:10s} {e['slug'][:38]:38s} {e['dir']:7s} {rsn:22s} {yw:>4s} {e['pnl']:+8.2f}")
