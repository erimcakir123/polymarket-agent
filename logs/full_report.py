import json
from pathlib import Path
from collections import defaultdict

archive = Path("logs/archive")
all_exits = []
all_entries_map = {}

for run_dir in sorted(archive.iterdir()):
    tfile = run_dir / "trades.jsonl"
    if not tfile.exists():
        continue
    trades = []
    for line in open(tfile):
        line = line.strip()
        if line and line[0] == "{":
            try:
                trades.append(json.loads(line))
            except Exception:
                pass
    entries = {t["market"]: t for t in trades if t.get("action") in ("BUY_YES", "BUY_NO") and t.get("size")}
    exits = [t for t in trades if t.get("action") == "EXIT"]
    pnl = sum(e.get("pnl", 0) for e in exits)
    wins = sum(1 for e in exits if e.get("pnl", 0) > 0)
    losses = len(exits) - wins
    wr = wins / (wins + losses) * 100 if wins + losses else 0
    print(f"=== {run_dir.name} === PnL=${pnl:.2f} W={wins} L={losses} WR={wr:.0f}%")
    for e in exits:
        s = e["market"][:42]
        p = e.get("pnl", 0)
        r = e.get("reason", "?")[:28]
        ent = entries.get(e["market"], {})
        conf = ent.get("confidence", "?")
        sport = ent.get("sport_tag", "?")[:15]
        edge = ent.get("edge", 0)
        ai = ent.get("ai_probability", 0)
        direction = ent.get("action", "?")
        ps = f"+${p:.2f}" if p > 0 else f"-${abs(p):.2f}"
        print(f"  {s:42s} {direction:8s} {conf:3s} AI={ai:.0%} edge={edge:.0%} {sport:15s} {r:28s} {ps}")
        all_exits.append({"pnl": p, "reason": r.strip(), "sport": sport.strip(), "conf": conf, "edge": edge, "ai": ai, "direction": direction})
    print()

# Current session
tfile = Path("logs/trades.jsonl")
if tfile.exists():
    trades = []
    for line in open(tfile):
        line = line.strip()
        if line and line[0] == "{":
            try:
                trades.append(json.loads(line))
            except Exception:
                pass
    entries = {t["market"]: t for t in trades if t.get("action") in ("BUY_YES", "BUY_NO") and t.get("size")}
    exits = [t for t in trades if t.get("action") == "EXIT"]
    pnl = sum(e.get("pnl", 0) for e in exits)
    wins = sum(1 for e in exits if e.get("pnl", 0) > 0)
    losses = len(exits) - wins
    wr = wins / (wins + losses) * 100 if wins + losses else 0
    print(f"=== CURRENT SESSION === PnL=${pnl:.2f} W={wins} L={losses} WR={wr:.0f}%")
    for e in exits:
        s = e["market"][:42]
        p = e.get("pnl", 0)
        r = e.get("reason", "?")[:28]
        ent = entries.get(e["market"], {})
        conf = ent.get("confidence", "?")
        sport = ent.get("sport_tag", "?")[:15]
        edge = ent.get("edge", 0)
        ai = ent.get("ai_probability", 0)
        direction = ent.get("action", "?")
        ps = f"+${p:.2f}" if p > 0 else f"-${abs(p):.2f}"
        print(f"  {s:42s} {direction:8s} {conf:3s} AI={ai:.0%} edge={edge:.0%} {sport:15s} {r:28s} {ps}")
        all_exits.append({"pnl": p, "reason": r.strip(), "sport": sport.strip(), "conf": conf, "edge": edge, "ai": ai, "direction": direction})
    print()

print("=" * 70)
print("GRAND TOTAL (ALL RUNS)")
print("=" * 70)
total_pnl = sum(e["pnl"] for e in all_exits)
total_wins = sum(1 for e in all_exits if e["pnl"] > 0)
total_losses = len(all_exits) - total_wins
total_wr = total_wins / (total_wins + total_losses) * 100 if all_exits else 0
print(f"PnL: ${total_pnl:.2f} | Trades: {len(all_exits)} | W: {total_wins} | L: {total_losses} | WR: {total_wr:.0f}%")
print(f"Avg win: ${sum(e['pnl'] for e in all_exits if e['pnl']>0)/(total_wins or 1):.2f}")
print(f"Avg loss: ${sum(e['pnl'] for e in all_exits if e['pnl']<=0)/(total_losses or 1):.2f}")

print("\nBY SPORT (all-time):")
by_sport = defaultdict(lambda: {"pnl": 0, "count": 0, "wins": 0})
for e in all_exits:
    by_sport[e["sport"]]["pnl"] += e["pnl"]
    by_sport[e["sport"]]["count"] += 1
    if e["pnl"] > 0:
        by_sport[e["sport"]]["wins"] += 1
for sp, d in sorted(by_sport.items(), key=lambda x: x[1]["pnl"]):
    swr = d["wins"] / d["count"] * 100 if d["count"] else 0
    print(f"  {sp:20s} PnL=${d['pnl']:+.2f}  trades={d['count']}  WR={swr:.0f}%")

print("\nBY CONFIDENCE (all-time):")
by_conf = defaultdict(lambda: {"pnl": 0, "count": 0, "wins": 0})
for e in all_exits:
    by_conf[e["conf"]]["pnl"] += e["pnl"]
    by_conf[e["conf"]]["count"] += 1
    if e["pnl"] > 0:
        by_conf[e["conf"]]["wins"] += 1
for c, d in sorted(by_conf.items(), key=lambda x: x[1]["pnl"]):
    cwr = d["wins"] / d["count"] * 100 if d["count"] else 0
    print(f"  {c:12s} PnL=${d['pnl']:+.2f}  trades={d['count']}  WR={cwr:.0f}%")

print("\nBY EXIT REASON (all-time):")
by_reason = defaultdict(lambda: {"pnl": 0, "count": 0})
for e in all_exits:
    by_reason[e["reason"]]["pnl"] += e["pnl"]
    by_reason[e["reason"]]["count"] += 1
for r, d in sorted(by_reason.items(), key=lambda x: x[1]["pnl"]):
    print(f"  {r:35s} PnL=${d['pnl']:+.2f}  count={d['count']}")

print("\nBY DIRECTION (all-time):")
by_dir = defaultdict(lambda: {"pnl": 0, "count": 0, "wins": 0})
for e in all_exits:
    by_dir[e["direction"]]["pnl"] += e["pnl"]
    by_dir[e["direction"]]["count"] += 1
    if e["pnl"] > 0:
        by_dir[e["direction"]]["wins"] += 1
for d_name, d in sorted(by_dir.items(), key=lambda x: x[1]["pnl"]):
    dwr = d["wins"] / d["count"] * 100 if d["count"] else 0
    print(f"  {d_name:12s} PnL=${d['pnl']:+.2f}  trades={d['count']}  WR={dwr:.0f}%")

print("\nBY EDGE RANGE (all-time):")
by_edge = defaultdict(lambda: {"pnl": 0, "count": 0, "wins": 0})
for e in all_exits:
    edge = e["edge"]
    if edge < 0.08:
        bucket = "0-8%"
    elif edge < 0.12:
        bucket = "8-12%"
    elif edge < 0.18:
        bucket = "12-18%"
    else:
        bucket = "18%+"
    by_edge[bucket]["pnl"] += e["pnl"]
    by_edge[bucket]["count"] += 1
    if e["pnl"] > 0:
        by_edge[bucket]["wins"] += 1
for b in ["0-8%", "8-12%", "12-18%", "18%+"]:
    d = by_edge[b]
    if d["count"] == 0:
        continue
    bwr = d["wins"] / d["count"] * 100
    print(f"  {b:12s} PnL=${d['pnl']:+.2f}  trades={d['count']}  WR={bwr:.0f}%")
