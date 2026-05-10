"""bot.log'daki yeni real exit'ler audit'te var mi? Eslesmeyenleri raporla."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
real_exits = []
with open(ROOT / "logs/runtime/bot.log", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if "2026-05-10" not in line:
            continue
        m = re.search(r"EXIT (.+?): reason=(\w+) realized=\$(-?[\d.]+)", line)
        if m:
            real_exits.append((m.group(1), m.group(2), float(m.group(3))))

print(f"bot.log 2026-05-10 EXIT count: {len(real_exits)}")
total_real = sum(p for _, _, p in real_exits)
print(f"Sum: ${total_real:.2f}")

with open(ROOT / "logs/audit/trade_history.jsonl", encoding="utf-8") as f:
    audit = [json.loads(l) for l in f if l.strip()]
audit_slugs_exited = {r["slug"]: r.get("condition_id", "") for r in audit if r.get("exit_price") is not None}
audit_slugs_open = {r["slug"]: r.get("condition_id", "") for r in audit if r.get("exit_price") is None}

print(f"audit exited count: {len(audit_slugs_exited)}")
print(f"audit open (phantom) count: {len(audit_slugs_open)}")
print()
print("Per-exit audit status:")
for slug, reason, pnl in real_exits:
    in_exited = slug in audit_slugs_exited
    in_open = slug in audit_slugs_open
    cid = audit_slugs_exited.get(slug) or audit_slugs_open.get(slug, "")
    status = "EXITED" if in_exited else ("OPEN-PHANTOM" if in_open else "MISSING")
    print(f"  {slug:35s} reason={reason:14s} pnl=${pnl:6.2f}  audit={status}  cid={cid[:25]}")
