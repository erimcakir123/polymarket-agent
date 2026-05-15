"""Tum bot.log dosyalarindan MLB exit'lerini liste."""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
logs = sorted(ROOT.glob("logs/runtime/bot.log*"))
mlb_exits = []
for fp in logs:
    try:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.search(
                    r"(\d+-\d+-\d+ \d+:\d+:\d+).*EXIT (mlb-.+?): reason=(\w+) realized=\$(-?[\d.]+)",
                    line,
                )
                if m:
                    mlb_exits.append(
                        (m.group(1), m.group(2), m.group(3), float(m.group(4)), fp.name),
                    )
    except Exception:
        continue

print(f"MLB EXIT total: {len(mlb_exits)}")
wins = [e for e in mlb_exits if e[3] > 0]
losses = [e for e in mlb_exits if e[3] < 0]
print(f"  Wins: {len(wins)} (sum=${sum(e[3] for e in wins):.2f})")
print(f"  Losses: {len(losses)} (sum=${sum(e[3] for e in losses):.2f})")
print(f"  Net: ${sum(e[3] for e in mlb_exits):.2f}")
print()
print("Detay:")
for ts, slug, reason, pnl, src in mlb_exits:
    sign = "+" if pnl >= 0 else ""
    print(f"  {ts}  {slug:36s}  {reason:14s}  {sign}${pnl:7.2f}  ({src})")

# scale-out'lar da
print()
print("=== MLB SCALE-OUT ===")
mlb_so = []
for fp in logs:
    try:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.search(
                    r"(\d+-\d+-\d+ \d+:\d+:\d+).*SCALE-OUT (mlb-.+?): tier=(\d+) sold=[\d.]+ shares realized=\$(-?[\d.]+)",
                    line,
                )
                if m:
                    mlb_so.append((m.group(1), m.group(2), m.group(3), float(m.group(4))))
    except Exception:
        continue
print(f"MLB SCALE-OUT total: {len(mlb_so)}")
for ts, slug, tier, pnl in mlb_so:
    sign = "+" if pnl >= 0 else ""
    print(f"  {ts}  {slug:36s}  tier {tier}  {sign}${pnl:6.2f}")
print(f"  Sum: ${sum(e[3] for e in mlb_so):.2f}")
