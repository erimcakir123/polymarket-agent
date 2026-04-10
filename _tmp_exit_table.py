"""Tek tablo: bugün 03:00 local'den beri tüm exit'ler.
Columns: saat, sport, slug, dir, reason, entry, exit, actual, resolved, hold_pnl
"""
import json
from collections import defaultdict

CUTOFF = "2026-04-10T00:00"  # UTC, since reset was 00:33 UTC = 03:33 local

entries, exits, scales = {}, [], []
with open("logs/trades.jsonl", encoding="utf-8") as f:
    for line in f:
        try: e = json.loads(line)
        except: continue
        ts = e.get("timestamp", "")
        if ts < CUTOFF: continue
        act = e.get("action"); slug = e.get("market","")
        if act in ("BUY","UPSET_ENTRY"): entries[slug] = e
        elif act == "EXIT": exits.append(e)
        elif act == "SCALE_OUT": scales.append(e)

resolved = {}
with open("logs/match_outcomes.jsonl", encoding="utf-8") as f:
    for line in f:
        try: d = json.loads(line)
        except: continue
        if d.get("slug"): resolved[d["slug"]] = d

def sport(slug, tag=""):
    s = (tag or "").lower() + " " + (slug or "").lower()
    if "nba" in s: return "NBA"
    if "nhl" in s: return "NHL"
    if "mlb" in s: return "MLB"
    if "atp" in s: return "ATP"
    if "wta" in s: return "WTA"
    if "boxing" in s: return "Boxing"
    if "mma" in s or "ufc" in s or "trump" in s: return "MMA"
    if "euroleague" in s: return "EuroLeague"
    if any(x in s for x in ["sud","lib","aus","fl1","fl2","fr1","fr2","bl1","bl2","bun","elc","epl","ere",
                             "sea","tur","den","ita","esp","por","ned","mls","serie","la-liga","premier",
                             "primera","a-league","bundes","eredivisie","lal","col1","itsb","es2"]):
        return "Soccer"
    return "other"

def hold_pnl_if_resolved(slug, ex):
    d = resolved.get(slug)
    if not d or d.get("yes_won") is None:
        return None
    yw = bool(d["yes_won"])
    entry = entries.get(slug, {})
    ep = entry.get("entry_price") or ex.get("price")
    dirx = ex.get("direction")
    size = entry.get("size_usdc") or ex.get("size", 0)
    if ep is None or size <= 0: return None
    cost = ep if dirx == "BUY_YES" else (1 - ep)
    if cost <= 0: return None
    shares = size / cost
    if dirx == "BUY_YES":
        return shares * (1.0 if yw else 0.0) - size
    return shares * (0.0 if yw else 1.0) - size

rows = []
for ex in exits:
    slug = ex.get("market","")
    sp = sport(slug, entries.get(slug,{}).get("sport_tag",""))
    hp = hold_pnl_if_resolved(slug, ex)
    yw = resolved.get(slug,{}).get("yes_won")
    res_str = "Y=Y" if yw is True else ("Y=N" if yw is False else "open")
    rows.append({
        "t": ex.get("timestamp","")[11:19],
        "sport": sp,
        "slug": slug,
        "dir": ex.get("direction",""),
        "reason": ex.get("reason","").replace("match_exit_","").replace("_"," "),
        "entry": entries.get(slug,{}).get("entry_price") or ex.get("price", 0),
        "exit": ex.get("exit_price", 0),
        "actual": ex.get("total_pnl", ex.get("pnl", 0)) or 0,
        "hold": hp,
        "res": res_str,
    })

# Sort by time
rows.sort(key=lambda x: x["t"])

# Per-branch summary
by_sport = defaultdict(lambda: {"n":0,"actual":0.0,"hold_sum":0.0,"hold_n":0})
for r in rows:
    s = by_sport[r["sport"]]
    s["n"] += 1
    s["actual"] += r["actual"]
    if r["hold"] is not None:
        s["hold_sum"] += r["hold"]; s["hold_n"] += 1

print("=" * 110)
print("BRANŞ ÖZETİ — sadece resolve olmuşlarda hold hesaplı")
print("=" * 110)
print(f"{'sport':12s} {'n':>3s} {'actual_sum':>11s} {'resolved':>9s} {'hold_sum':>10s} {'savings':>9s}")
tot_act = tot_hold = 0
tot_res = 0
for sp in sorted(by_sport.keys(), key=lambda x: by_sport[x]["actual"]):
    v = by_sport[sp]
    sav = v["actual"] - v["hold_sum"] if v["hold_n"] else 0
    tot_act += v["actual"]; tot_hold += v["hold_sum"]; tot_res += v["hold_n"]
    print(f"{sp:12s} {v['n']:>3d} {v['actual']:+11.2f} {v['hold_n']:>9d} {v['hold_sum']:+10.2f} {sav:+9.2f}")
print(f"{'TOTAL':12s} {sum(v['n'] for v in by_sport.values()):>3d} {tot_act:+11.2f} {tot_res:>9d} {tot_hold:+10.2f} {tot_act-tot_hold:+9.2f}")

# Full table
print()
print("=" * 110)
print("TÜM EXIT'LER (bugün UTC 00:00+ = local 03:00+)")
print("=" * 110)
print(f"{'saat':8s} {'sport':10s} {'slug':36s} {'dir':6s} {'reason':22s} {'ent':>5s} {'xit':>5s} {'res':>4s} {'actual':>8s} {'hold':>8s}")
for r in rows:
    h = f"{r['hold']:+.2f}" if r["hold"] is not None else "  --  "
    print(f"{r['t']:8s} {r['sport']:10s} {r['slug'][:36]:36s} {r['dir']:6s} {r['reason'][:22]:22s} {r['entry']:>5.2f} {r['exit']:>5.2f} {r['res']:>4s} {r['actual']:+8.2f} {h:>8s}")

print(f"\nNet actual: {sum(r['actual'] for r in rows):+.2f}")
resolved_rows = [r for r in rows if r["hold"] is not None]
print(f"Resolved ({len(resolved_rows)}): actual {sum(r['actual'] for r in resolved_rows):+.2f} vs hold {sum(r['hold'] for r in resolved_rows):+.2f}")
