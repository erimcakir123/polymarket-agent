"""Tum bot.log + bot.log.* dosyalarindan exit listesi cikar, kayip pattern analizi."""
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
log_files = sorted(ROOT.glob("logs/runtime/bot.log*"))

exits = []
for fp in log_files:
    try:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.search(
                    r"(\d+-\d+-\d+ \d+:\d+:\d+).*EXIT (.+?): reason=(\w+) realized=\$(-?[\d.]+)",
                    line,
                )
                if m:
                    ts, slug, reason, pnl = m.group(1), m.group(2), m.group(3), float(m.group(4))
                    exits.append({"ts": ts, "slug": slug, "reason": reason, "pnl": pnl})
    except Exception:
        continue

print(f"Total EXIT events: {len(exits)}")
wins = [e for e in exits if e["pnl"] > 0]
losses = [e for e in exits if e["pnl"] < 0]
print(f"  Wins:  {len(wins)} (sum=${sum(e['pnl'] for e in wins):.2f})")
print(f"  Losses: {len(losses)} (sum=${sum(e['pnl'] for e in losses):.2f})")
print(f"  Net: ${sum(e['pnl'] for e in exits):.2f}")
print()

print("=== EXIT REASON DAGILIMI ===")
reason_counter = Counter(e["reason"] for e in exits)
reason_pnl = defaultdict(lambda: [0, 0])  # [count, sum]
for e in exits:
    reason_pnl[e["reason"]][0] += 1
    reason_pnl[e["reason"]][1] += e["pnl"]
for reason, (cnt, total) in sorted(reason_pnl.items(), key=lambda x: x[1][1]):
    avg = total / cnt if cnt else 0
    print(f"  {reason:18s} count={cnt:3d}  sum=${total:8.2f}  avg=${avg:6.2f}")
print()

print("=== EN BÜYÜK KAYIPLAR (top 10) ===")
biggest_losses = sorted(losses, key=lambda e: e["pnl"])[:10]
for e in biggest_losses:
    print(f"  {e['ts']}  {e['slug']:36s}  {e['reason']:14s}  ${e['pnl']:7.2f}")
print()

print("=== SPORT BAZLI ===")
sport_counter = Counter()
sport_pnl = defaultdict(lambda: [0, 0, 0])  # [wins, losses, total_pnl]
for e in exits:
    sport = e["slug"].split("-", 1)[0].lower()
    sport_counter[sport] += 1
    if e["pnl"] > 0:
        sport_pnl[sport][0] += 1
    else:
        sport_pnl[sport][1] += 1
    sport_pnl[sport][2] += e["pnl"]
for sport, (w, l, total) in sorted(sport_pnl.items(), key=lambda x: x[1][2]):
    cnt = w + l
    wr = (w / cnt * 100) if cnt else 0
    print(f"  {sport:12s}  {w}W/{l}L  win_rate={wr:5.1f}%  net=${total:7.2f}")
