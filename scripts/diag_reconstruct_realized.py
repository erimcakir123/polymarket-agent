"""bot.log'tan EXIT + SCALE-OUT realized değerlerini topla."""
import re
import sys

total_full = 0.0
exits = 0
total_so = 0.0
sos = 0

with open('logs/runtime/bot.log', encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = re.search(r"EXIT .*realized=\$(-?[\d.]+)", line)
        if m:
            total_full += float(m.group(1))
            exits += 1
            continue
        m = re.search(r"SCALE-OUT .*realized=\$(-?[\d.]+)", line)
        if m:
            total_so += float(m.group(1))
            sos += 1

print(f"Full exits: {exits}, sum realized: ${total_full:.2f}")
print(f"Scale-outs: {sos}, sum: ${total_so:.2f}")
print(f"Grand total: ${total_full + total_so:.2f}")
