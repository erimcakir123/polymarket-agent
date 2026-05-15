"""NBA exits market_type bazlı W/L/PnL — audit + bot.log birleşik tarama.

Cikti: spread vs totals vs moneyline ayrı ayrı. Tum NBA tagged exit'ler (sport_tag,
slug regex, market field) dahil. Predictive_dead reason ozellikle goster.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent


def cat(slug: str) -> str:
    """Slug → market_type. Polymarket NBA naming: spread → 'spread' substring,
    totals → 'total-XXX' suffix or '-ou-NNN' pattern. Team codes (hou, ou-tex)
    yanlış eslesmesin diye sadece spesifik patternler.
    """
    s = slug.lower()
    if "spread" in s:
        return "spread"
    if (
        "-total-" in s or "-totals-" in s or s.endswith("-total")
        or "-over-" in s or "-under-" in s
        or "-highest-scoring" in s or "-most-points" in s
    ):
        return "totals"
    return "moneyline"


# ── 1. AUDIT (current 2.0) ──
seen_audit = set()
audit_recs = []
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
                    audit_recs.append(t)
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError:
        continue


def is_nba_audit(r):
    return "nba" in (r.get("sport_tag") or "").lower()


nba_audit = [r for r in audit_recs if r.get("exit_price") is not None and is_nba_audit(r)]
print(f"Audit NBA closed trades: {len(nba_audit)}")

a_buckets = defaultdict(list)
for r in nba_audit:
    mt = cat(r.get("slug", ""))
    a_buckets[mt].append(r)

for mt in ("moneyline", "spread", "totals"):
    rows = a_buckets[mt]
    if not rows:
        print(f"  {mt:10s} 0")
        continue
    w = sum(1 for r in rows if (r.get("exit_pnl_usdc") or 0) > 0)
    l = sum(1 for r in rows if (r.get("exit_pnl_usdc") or 0) < 0)
    n = len(rows) - w - l
    pnl = sum((r.get("exit_pnl_usdc") or 0) for r in rows)
    wr = (w / (w + l) * 100) if (w + l) else 0
    print(f"  {mt:10s} {w}W/{l}L/{n}N rate={wr:.1f}% net=${pnl:.2f}")
    # Reason histogram
    reasons = defaultdict(lambda: [0, 0.0])
    for r in rows:
        reasons[r.get("exit_reason", "?")][0] += 1
        reasons[r.get("exit_reason", "?")][1] += r.get("exit_pnl_usdc") or 0
    for reason, (cnt, p) in sorted(reasons.items(), key=lambda x: x[1][1]):
        print(f"      {reason:25s} cnt={cnt} pnl=${p:.2f}")

# ── 2. BOT.LOG (last 5 rotations) ──
print()
print("=" * 60)
print("Bot.log NBA EXIT lines:")
nba_logs = []
exit_re = re.compile(r"EXIT (nba\S+): reason=(\w+) realized=\$(-?[\d.]+)")
for fp in (
    list(ROOT.glob("logs/runtime/bot.log*"))
    + list(ROOT.glob("logs/bot.log*"))
):
    try:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = exit_re.search(line)
                if m:
                    nba_logs.append((m.group(1), m.group(2), float(m.group(3))))
    except OSError:
        continue

print(f"Bot.log NBA EXIT count: {len(nba_logs)}")

l_buckets = defaultdict(list)
for slug, reason, pnl in nba_logs:
    l_buckets[cat(slug)].append((slug, reason, pnl))

for mt in ("moneyline", "spread", "totals"):
    rows = l_buckets[mt]
    if not rows:
        print(f"  {mt:10s} 0")
        continue
    w = sum(1 for _, _, p in rows if p > 0)
    l = sum(1 for _, _, p in rows if p < 0)
    n = len(rows) - w - l
    pnl = sum(p for _, _, p in rows)
    wr = (w / (w + l) * 100) if (w + l) else 0
    print(f"  {mt:10s} {w}W/{l}L/{n}N rate={wr:.1f}% net=${pnl:.2f}")
    reasons = defaultdict(lambda: [0, 0.0])
    for s, r, p in rows:
        reasons[r][0] += 1
        reasons[r][1] += p
    for reason, (cnt, p) in sorted(reasons.items(), key=lambda x: x[1][1]):
        print(f"      {reason:25s} cnt={cnt} pnl=${p:.2f}")

# ── 3. SLUG SAMPLES (manual verify) ──
print()
print("=" * 60)
print("Sample NBA totals slugs (audit):")
for r in a_buckets["totals"][:10]:
    print(
        f"  {r.get('slug', '')[:55]} | "
        f"{r.get('exit_reason', '?')} | "
        f"${(r.get('exit_pnl_usdc') or 0):.2f}",
    )

print()
print("Sample NBA totals slugs (bot.log):")
for s, r, p in l_buckets["totals"][:10]:
    print(f"  {s[:55]} | {r} | ${p:.2f}")
