"""Bot lifetime P&L analizi — audit + bot.log birleşik."""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent

seen_audit = set()
all_exits = []

for fp in ROOT.glob("logs/audit/trade_history.jsonl*"):
    try:
        with open(fp, encoding="utf-8") as f:
            for line in f:
                try:
                    t = json.loads(line)
                    cid = t.get("condition_id", "")
                    if cid and cid in seen_audit:
                        continue
                    if cid:
                        seen_audit.add(cid)
                    if t.get("exit_price") is not None:
                        all_exits.append({
                            "ts": t.get("exit_timestamp", ""),
                            "pnl": t.get("exit_pnl_usdc") or 0,
                            "reason": t.get("exit_reason", ""),
                            "sport": (t.get("sport_tag") or "").lower(),
                        })
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError:
        continue

seen_log = set()
exit_re = re.compile(r"(\d+-\d+-\d+ \d+:\d+:\d+).*EXIT (\S+?): reason=(\w+) realized=\$(-?[\d.]+)")
for fp in (
    sorted(ROOT.glob("logs/runtime/bot.log*"))
    + sorted(ROOT.glob("logs/bot.log*"))
):
    try:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = exit_re.search(line)
                if m:
                    key = (m.group(2), m.group(3), m.group(4))
                    if key in seen_log:
                        continue
                    seen_log.add(key)
                    all_exits.append({
                        "ts": m.group(1),
                        "pnl": float(m.group(4)),
                        "reason": m.group(3),
                        "sport": m.group(2).split("-")[0],
                    })
    except OSError:
        continue

print(f"Total trades (dedupe): {len(all_exits)}")
print()

total_pnl = sum(e["pnl"] for e in all_exits)
wins = [e for e in all_exits if e["pnl"] > 0]
losses = [e for e in all_exits if e["pnl"] < 0]
avg_w = sum(e["pnl"] for e in wins) / len(wins) if wins else 0
avg_l = sum(e["pnl"] for e in losses) / len(losses) if losses else 0
wr = len(wins) / (len(wins) + len(losses)) * 100 if (wins or losses) else 0
ratio = abs(avg_w / avg_l) if avg_l else 0

print(f"Net P&L: ${total_pnl:.2f}")
print(f"Wins: {len(wins)}  avg=${avg_w:.2f}")
print(f"Losses: {len(losses)}  avg=${avg_l:.2f}")
print(f"Win rate: {wr:.1f}%")
print(f"W/L ratio: {ratio:.2f}x")

# Breakeven analysis
print()
breakeven_wr = (-avg_l) / (avg_w - avg_l) * 100 if (avg_w - avg_l) else 0
print(f"Breakeven win rate (avg_w/avg_l ile): {breakeven_wr:.1f}%")
print(f"Mevcut win rate yeterli mi? {'EVET' if wr > breakeven_wr else 'HAYIR'}")

print()
print("Per-sport net P&L:")
sport_totals: dict = defaultdict(lambda: [0, 0, 0.0])
for e in all_exits:
    s = e["sport"] or "?"
    if e["pnl"] > 0:
        sport_totals[s][0] += 1
    elif e["pnl"] < 0:
        sport_totals[s][1] += 1
    sport_totals[s][2] += e["pnl"]
for sport, (w, l, pnl) in sorted(sport_totals.items(), key=lambda x: x[1][2]):
    wr2 = w / (w + l) * 100 if (w + l) else 0
    print(f"  {sport:10s}  {w}W/{l}L  rate={wr2:5.1f}%  net=${pnl:>8.2f}")

print()
print("Per-reason (sorted by net P&L):")
reason_pnl: dict = defaultdict(lambda: [0, 0.0])
for e in all_exits:
    reason_pnl[e["reason"]][0] += 1
    reason_pnl[e["reason"]][1] += e["pnl"]
for reason, (cnt, pnl) in sorted(reason_pnl.items(), key=lambda x: x[1][1]):
    print(f"  {reason:25s}  cnt={cnt:>3d}  net=${pnl:>8.2f}")
