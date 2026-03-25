import json, sys
from collections import defaultdict
from pathlib import Path

def analyze(path):
    trades = [json.loads(l) for l in open(path)]

    entries = [t for t in trades if t.get("action") in ("BUY_YES","BUY_NO") and t.get("size")]
    exits = [t for t in trades if t.get("action") == "EXIT"]
    rejects = [t for t in trades if t.get("rejected")]

    entry_map = {}
    for e in entries:
        entry_map[e["market"]] = e

    print(f"=== CURRENT SESSION ===")
    print(f"Entries: {len(entries)} | Exits: {len(exits)} | Rejects: {len(rejects)}")
    print()

    total_pnl = 0
    wins = 0
    losses = 0
    by_sport = defaultdict(lambda: {"pnl": 0, "count": 0, "wins": 0})
    by_conf = defaultdict(lambda: {"pnl": 0, "count": 0, "wins": 0})
    by_reason = defaultdict(lambda: {"pnl": 0, "count": 0})

    print("=== EXITED POSITIONS ===")
    for ex in exits:
        slug = ex["market"]
        pnl = ex.get("pnl", 0)
        reason = ex.get("reason", "?")
        entry = entry_map.get(slug, {})
        direction = entry.get("action", "?")
        ai_prob = entry.get("ai_probability", 0)
        conf = entry.get("confidence", "?")
        edge = entry.get("edge", 0)
        size = entry.get("size", 0)
        sources = entry.get("data_sources", [])
        sport = entry.get("sport_tag", "?")

        total_pnl += pnl
        w = 1 if pnl > 0 else 0
        if pnl > 0: wins += 1
        else: losses += 1

        by_sport[sport]["pnl"] += pnl
        by_sport[sport]["count"] += 1
        by_sport[sport]["wins"] += w

        by_conf[conf]["pnl"] += pnl
        by_conf[conf]["count"] += 1
        by_conf[conf]["wins"] += w

        by_reason[reason]["pnl"] += pnl
        by_reason[reason]["count"] += 1

        pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"
        src_str = ",".join(s for s in sources if s != "claude_sonnet")
        print(f"  {slug[:42]:42s} {direction:8s} AI={ai_prob:.0%} {conf:3s} edge={edge:.0%} ${size:.0f} | {reason:30s} | {pnl_str}")

    wr = wins/(wins+losses)*100 if wins+losses else 0
    print(f"\nTotal PnL: ${total_pnl:.2f} | Wins: {wins} | Losses: {losses} | WR: {wr:.0f}%")

    print("\n=== BY SPORT ===")
    for sport, d in sorted(by_sport.items(), key=lambda x: x[1]["pnl"]):
        swr = d["wins"]/d["count"]*100 if d["count"] else 0
        print(f"  {sport:20s} PnL=${d['pnl']:+.2f}  trades={d['count']}  WR={swr:.0f}%")

    print("\n=== BY CONFIDENCE ===")
    for conf, d in sorted(by_conf.items(), key=lambda x: x[1]["pnl"]):
        cwr = d["wins"]/d["count"]*100 if d["count"] else 0
        print(f"  {conf:5s} PnL=${d['pnl']:+.2f}  trades={d['count']}  WR={cwr:.0f}%")

    print("\n=== BY EXIT REASON ===")
    for reason, d in sorted(by_reason.items(), key=lambda x: x[1]["pnl"]):
        print(f"  {reason:35s} PnL=${d['pnl']:+.2f}  count={d['count']}")

    print("\n=== OPEN POSITIONS ===")
    exited_slugs = set()
    for ex in exits:
        exited_slugs.add(ex["market"])
    open_entries = [e for e in entries if e["market"] not in exited_slugs]
    total_invested = sum(e.get("size",0) for e in open_entries)
    for e in open_entries:
        sport = e.get("sport_tag","?")
        print(f"  {e['market'][:42]:42s} {e['action']:8s} AI={e.get('ai_probability',0):.0%} {e.get('confidence','?'):3s} edge={e.get('edge',0):.0%} ${e.get('size',0):.0f} | {sport}")
    print(f"Open: {len(open_entries)} | Invested: ${total_invested:.0f}")

    print("\n=== REJECTION BREAKDOWN ===")
    reject_reasons = defaultdict(int)
    for r in rejects:
        reason = r.get("rejected","").split(":")[0]
        reject_reasons[reason] += 1
    for reason, count in sorted(reject_reasons.items(), key=lambda x: -x[1]):
        print(f"  {count:3d}x {reason}")

    # Also analyze archived runs
    archive = Path(path).parent / "archive"
    if archive.exists():
        print("\n\n========== ARCHIVED RUNS ==========")
        for run_dir in sorted(archive.iterdir()):
            tfile = run_dir / "trades.jsonl"
            if not tfile.exists():
                continue
            run_trades = [json.loads(l) for l in open(tfile)]
            run_entries = [t for t in run_trades if t.get("action") in ("BUY_YES","BUY_NO") and t.get("size")]
            run_exits = [t for t in run_trades if t.get("action") == "EXIT"]
            run_pnl = sum(ex.get("pnl",0) for ex in run_exits)
            run_wins = sum(1 for ex in run_exits if ex.get("pnl",0) > 0)
            run_losses = len(run_exits) - run_wins
            rwr = run_wins/(run_wins+run_losses)*100 if run_wins+run_losses else 0
            print(f"\n--- {run_dir.name} ---")
            print(f"Entries: {len(run_entries)} | Exits: {len(run_exits)} | PnL: ${run_pnl:.2f} | WR: {rwr:.0f}%")

            # Show each exit
            re_map = {e["market"]: e for e in run_entries}
            for ex in run_exits:
                slug = ex["market"]
                pnl = ex.get("pnl", 0)
                reason = ex.get("reason", "?")
                ent = re_map.get(slug, {})
                conf = ent.get("confidence", "?")
                edge = ent.get("edge", 0)
                sport = ent.get("sport_tag", "?")
                pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"
                print(f"  {slug[:42]:42s} {conf:3s} edge={edge:.0%} {sport:15s} {reason:30s} {pnl_str}")

if __name__ == "__main__":
    analyze(sys.argv[1] if len(sys.argv) > 1 else "logs/trades.jsonl")
