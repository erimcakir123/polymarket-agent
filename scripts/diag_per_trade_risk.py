"""Per-trade kayip profili — hangi spor 1 trade'de daha cok kaybettiriyor."""
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
                            "pnl": t.get("exit_pnl_usdc") or 0,
                            "sport": (t.get("sport_tag") or "").lower(),
                        })
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError:
        continue

seen_log = set()
exit_re = re.compile(r"(\d+-\d+-\d+ \d+:\d+:\d+).*EXIT (\S+?): reason=(\w+) realized=\$(-?[\d.]+)")
for fp in sorted(ROOT.rglob("bot.log*")):
    if "venv" in str(fp) or "__pycache__" in str(fp):
        continue
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
                        "pnl": float(m.group(4)),
                        "sport": m.group(2).split("-")[0],
                    })
    except OSError:
        continue

by_sport: dict = defaultdict(list)
for e in all_exits:
    s = e["sport"] or "?"
    by_sport[s].append(e["pnl"])

print("Per-trade risk profili — kayip durumunda ortalama + en kotusu")
print()
print(f"{'Spor':12s} {'#':>4s} {'W':>3s} {'L':>3s}  {'AvgL':>8s} {'MaxL':>8s}  {'AvgW':>8s}  {'Net':>9s}  {'WR':>5s}")
print("-" * 88)

rows = []
for sport, pnls in by_sport.items():
    if not pnls:
        continue
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    avg_l = sum(losses) / len(losses) if losses else 0
    max_l = min(losses) if losses else 0
    avg_w = sum(wins) / len(wins) if wins else 0
    net = sum(pnls)
    wr = len(wins) / (len(wins) + len(losses)) * 100 if (wins or losses) else 0
    rows.append((sport, len(pnls), len(wins), len(losses), avg_l, max_l, avg_w, net, wr))

rows.sort(key=lambda r: r[4])
for sport, n, w, l, avg_l, max_l, avg_w, net, wr in rows:
    print(
        f"{sport:12s} {n:>4d} {w:>3d} {l:>3d}  ${avg_l:>6.2f} ${max_l:>6.2f}  "
        f"${avg_w:>6.2f}  ${net:>7.2f}  {wr:>4.1f}%",
    )
