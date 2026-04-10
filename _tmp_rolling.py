"""7-day rolling analysis from trade_archive.jsonl.
Key questions:
- AI vs Bookmaker direction accuracy over 7 days
- Exit rule effectiveness over 7 days
- Catastrophic floor specifically (is yesterday's finding a trend?)
"""
import json
from datetime import datetime, timedelta
from collections import defaultdict

ARCHIVE = "logs/trade_archive.jsonl"
OUTCOMES = "logs/match_outcomes.jsonl"

# Load archive
records = []
with open(ARCHIVE, encoding="utf-8") as f:
    for line in f:
        try: records.append(json.loads(line))
        except: pass

# Load resolved outcomes (all, not just today)
resolved = {}
with open(OUTCOMES, encoding="utf-8") as f:
    for line in f:
        try: d = json.loads(line)
        except: continue
        if d.get("slug"): resolved[d["slug"]] = d

print(f"Archive records: {len(records)}")
print(f"Resolved outcomes: {len(resolved)}")

# Filter to records that look like actual trades (not HOLDs)
trades = [r for r in records if r.get("action") not in ("HOLD",) and r.get("slug")]
print(f"Non-HOLD records: {len(trades)}")

# Split by date
by_date = defaultdict(list)
for r in trades:
    ts = r.get("timestamp","")
    if not ts: continue
    d = ts[:10]
    by_date[d].append(r)

print(f"\nDates in archive:")
for d in sorted(by_date.keys())[-10:]:
    print(f"  {d}: {len(by_date[d])} records")

# Focus on trades with resolution data
def sport_family(tag, slug=""):
    s = (tag or "").lower() + " " + (slug or "").lower()
    if "nba" in s: return "NBA"
    if "nhl" in s: return "NHL"
    if "mlb" in s: return "MLB"
    if "atp" in s: return "ATP"
    if "wta" in s: return "WTA"
    if "boxing" in s: return "Boxing"
    if "mma" in s: return "MMA"
    if "euroleague" in s: return "EuroLeague"
    if any(x in s for x in ["sud","lib","aus","fl1","fl2","fr1","fr2","bl1","bl2","bun",
                             "elc","epl","ere","sea","tur","den","serie","la-liga","premier",
                             "primera","a-league","bundes","eredivisie"]):
        return "Soccer"
    return "other"

# trade_archive uses 'yes_won' field directly from the archive
# plus entry_price, direction, size, exit_reason fields
# Let's enumerate available fields
if trades:
    print(f"\nSample archive record fields: {list(trades[0].keys())}")

# Direct analysis on archive records that have yes_won field
archive_with_outcome = [r for r in trades if r.get("yes_won") is not None]
print(f"\nArchive records with yes_won: {len(archive_with_outcome)}")

# Per-rule analysis
def hold_pnl(direction, entry_price, size, yes_won):
    if entry_price is None or size is None or size <= 0: return None
    cost = entry_price if direction == "BUY_YES" else (1 - entry_price)
    if cost <= 0: return None
    shares = size / cost
    if direction == "BUY_YES":
        return shares * (1.0 if yes_won else 0.0) - size
    return shares * (0.0 if yes_won else 1.0) - size

by_rule = defaultdict(lambda: {"n":0,"actual":0.0,"hold":0.0,"correct":0,"wrong":0})
by_sport_result = defaultdict(lambda: {"n":0,"our_right":0,"bm_right":0,"bm_n":0})

for r in archive_with_outcome:
    reason = r.get("exit_reason","").replace("post_exit_","")
    actual = r.get("pnl", 0) or 0
    dir_ = r.get("direction","")
    ep = r.get("entry_price")
    sz = r.get("size", 0)
    yw = bool(r.get("yes_won"))
    hp = hold_pnl(dir_, ep, sz, yw)

    by_rule[reason]["n"] += 1
    by_rule[reason]["actual"] += actual
    if hp is not None:
        by_rule[reason]["hold"] += hp
        # Was exit correct? If actual > hold → correct (saved money)
        if actual > hp + 0.5:
            by_rule[reason]["correct"] += 1
        elif actual < hp - 0.5:
            by_rule[reason]["wrong"] += 1

    # Per-sport direction accuracy
    sp = sport_family(r.get("sport_tag",""), r.get("slug",""))
    our_correct = (dir_ == "BUY_YES" and yw) or (dir_ == "BUY_NO" and not yw)
    by_sport_result[sp]["n"] += 1
    if our_correct: by_sport_result[sp]["our_right"] += 1
    # Bookmaker direction counterfactual
    bm = r.get("bookmaker_prob")
    if bm not in (None, 0, 0.0):
        by_sport_result[sp]["bm_n"] += 1
        if bm > ep:
            bm_dir = "BUY_YES"
        elif bm < ep:
            bm_dir = "BUY_NO"
        else:
            bm_dir = dir_
        bm_correct = (bm_dir == "BUY_YES" and yw) or (bm_dir == "BUY_NO" and not yw)
        if bm_correct: by_sport_result[sp]["bm_right"] += 1

print("\n" + "=" * 90)
print("ROLLING PER-RULE (all archive records with resolution)")
print("=" * 90)
print(f"{'rule':35s} {'n':>4s} {'actual':>10s} {'hold':>10s} {'savings':>10s} {'correct':>8s} {'wrong':>6s}")
for rule in sorted(by_rule.keys(), key=lambda x: by_rule[x]["actual"] - by_rule[x]["hold"], reverse=True):
    v = by_rule[rule]
    savings = v["actual"] - v["hold"]
    print(f"{rule[:35]:35s} {v['n']:>4d} {v['actual']:+10.2f} {v['hold']:+10.2f} {savings:+10.2f} {v['correct']:>8d} {v['wrong']:>6d}")

print("\n" + "=" * 90)
print("ROLLING PER-SPORT direction accuracy (all archive records with yes_won)")
print("=" * 90)
print(f"{'sport':12s} {'n':>4s} {'our_acc':>10s} {'bm_acc':>10s}")
for sp in sorted(by_sport_result.keys()):
    v = by_sport_result[sp]
    if v["n"] == 0: continue
    our_pct = v["our_right"]/v["n"]*100
    bm_pct = v["bm_right"]/v["bm_n"]*100 if v["bm_n"] > 0 else 0
    print(f"{sp:12s} {v['n']:>4d} {v['our_right']}/{v['n']} ({our_pct:>4.0f}%) {v['bm_right']}/{v['bm_n']} ({bm_pct:>4.0f}%)")

# Total
tot_n = sum(v["n"] for v in by_sport_result.values())
tot_our = sum(v["our_right"] for v in by_sport_result.values())
tot_bmn = sum(v["bm_n"] for v in by_sport_result.values())
tot_bm = sum(v["bm_right"] for v in by_sport_result.values())
if tot_n:
    print(f"{'TOTAL':12s} {tot_n:>4d} {tot_our}/{tot_n} ({tot_our/tot_n*100:>4.0f}%) {tot_bm}/{tot_bmn} ({tot_bm/tot_bmn*100 if tot_bmn else 0:>4.0f}%)")
