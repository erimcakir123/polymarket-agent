"""bot.log'tan tum EXIT + SCALE-OUT olaylarini listele."""
import re

exits = []
scaleouts = []
with open('logs/runtime/bot.log', encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = re.search(r"(\d+-\d+-\d+ \d+:\d+:\d+).*EXIT (.+?): reason=(\w+) realized=\$(-?[\d.]+)", line)
        if m:
            ts, slug, reason, pnl = m.group(1), m.group(2), m.group(3), float(m.group(4))
            exits.append((ts, slug, reason, pnl))
        m = re.search(r"(\d+-\d+-\d+ \d+:\d+:\d+).*SCALE-OUT (.+?): tier=(\d+) sold=[\d.]+ shares realized=\$(-?[\d.]+)", line)
        if m:
            ts, slug, tier, pnl = m.group(1), m.group(2), m.group(3), float(m.group(4))
            scaleouts.append((ts, slug, tier, pnl))

print(f"=== FULL EXITS ({len(exits)} adet) ===")
for ts, slug, reason, pnl in exits:
    sign = "+" if pnl >= 0 else ""
    print(f"  {ts}  {slug:36s}  {reason:14s}  {sign}${pnl:6.2f}")
total_exit = sum(p for _, _, _, p in exits)
print(f"  Toplam exit: ${total_exit:.2f}")
print()
print(f"=== SCALE-OUTS ({len(scaleouts)} adet) ===")
for ts, slug, tier, pnl in scaleouts:
    sign = "+" if pnl >= 0 else ""
    print(f"  {ts}  {slug:36s}  tier {tier}  {sign}${pnl:6.2f}")
total_so = sum(p for _, _, _, p in scaleouts)
print(f"  Toplam scale-out: ${total_so:.2f}")
print()
print(f"GRAND TOTAL realized: ${total_exit + total_so:.2f}")

wins = sum(1 for _, _, _, p in exits if p > 0)
losses = sum(1 for _, _, _, p in exits if p < 0)
print(f"\nFull exits: {wins}W / {losses}L")
