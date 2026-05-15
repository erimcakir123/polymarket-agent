"""NBA totals trade exhaustive count — bağımsız doğrulama."""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

exits = []
exit_re = re.compile(r"EXIT (nba-\S*-total\S*): reason=(\w+) realized=\$(-?[\d.]+)")

for fp in sorted(set(ROOT.rglob("bot.log*"))):
    if "venv" in str(fp) or "__pycache__" in str(fp):
        continue
    try:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for ln, line in enumerate(f, 1):
                m = exit_re.search(line)
                if m:
                    exits.append((str(fp.relative_to(ROOT)), ln, m.group(1), m.group(2), float(m.group(3))))
    except OSError:
        continue

print(f"NBA totals exit count (ALL bot.log files in repo): {len(exits)}")
print()
print(f"{'File':40s} {'Line':>6s} {'Slug':45s} {'Reason':20s} {'PnL':>10s}")
print("-" * 130)
for fn, ln, slug, reason, pnl in exits:
    print(f"{fn:40s} {ln:>6d} {slug:45s} {reason:20s} ${pnl:>8.2f}")

W = sum(1 for *_, p in exits if p > 0)
L = sum(1 for *_, p in exits if p < 0)
N = sum(1 for *_, p in exits if p == 0)
total = sum(p for *_, p in exits)
print()
print(f"FINAL: {W}W / {L}L / {N}N (neutral) — net ${total:.2f}")

# De-dup by (slug,reason,pnl) — log rotation might double-count
seen = set()
uniq = []
for r in exits:
    key = (r[2], r[3], r[4])
    if key in seen:
        continue
    seen.add(key)
    uniq.append(r)
print()
print(f"DE-DUPED (by slug+reason+pnl): {len(uniq)} unique trades")
W2 = sum(1 for *_, p in uniq if p > 0)
L2 = sum(1 for *_, p in uniq if p < 0)
N2 = sum(1 for *_, p in uniq if p == 0)
total2 = sum(p for *_, p in uniq)
print(f"  → {W2}W / {L2}L / {N2}N — net ${total2:.2f}")
