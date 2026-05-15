"""Tum bot.log + audit .bak dosyalarindan COMPREHENSIVE performans analizi.

Cikti:
- Sport x market_type matrisi (W/L, net PnL, ortalama win/loss)
- Exit reason dagilimi
- Saat-bazli analiz (UFC ozellikle)
- market_flip risk degerlendirmesi (sport+market_type bazli)
"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Kaynak 1: Audit .bak dosyalari (deduplikasyonlu)
seen_cids = set()
audit_records = []
for fp in ROOT.glob("logs/audit/trade_history.jsonl*"):
    try:
        with open(fp, encoding="utf-8") as f:
            for line in f:
                try:
                    t = json.loads(line)
                    cid = t.get("condition_id", "")
                    if cid and cid in seen_cids:
                        continue
                    if cid:
                        seen_cids.add(cid)
                    audit_records.append(t)
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError:
        continue

# Kaynak 2: bot.log (.log + .log.1...5)
bot_log_exits = []
for fp in sorted(ROOT.glob("logs/runtime/bot.log*")) + sorted(ROOT.glob("logs/bot.log*")):
    try:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.search(
                    r"(\d+-\d+-\d+ \d+:\d+:\d+).*EXIT (.+?): reason=(\w+) realized=\$(-?[\d.]+)",
                    line,
                )
                if m:
                    bot_log_exits.append({
                        "ts": m.group(1),
                        "slug": m.group(2),
                        "reason": m.group(3),
                        "pnl": float(m.group(4)),
                    })
    except OSError:
        continue


def market_type(slug: str) -> str:
    s = slug.lower()
    if "spread" in s:
        return "spread"
    if "total" in s or "ou-" in s:
        return "total"
    return "moneyline"


# ── 1. Sport x Market Type Matrisi (audit) ──
print("=" * 80)
print("1. SPORT x MARKET TYPE — kar/zarar matrisi")
print("=" * 80)
matrix = defaultdict(lambda: {"w": 0, "l": 0, "neutral": 0, "pnl": 0.0, "max_loss": 0.0})
for r in audit_records:
    if r.get("exit_price") is None:
        continue
    sport = r.get("sport_tag", "?").lower().split("_")[0] or "?"
    mt = market_type(r.get("slug", ""))
    pnl = r.get("exit_pnl_usdc", 0) or 0
    key = f"{sport}/{mt}"
    if pnl > 0:
        matrix[key]["w"] += 1
    elif pnl < 0:
        matrix[key]["l"] += 1
        matrix[key]["max_loss"] = min(matrix[key]["max_loss"], pnl)
    else:
        matrix[key]["neutral"] += 1
    matrix[key]["pnl"] += pnl

print(f"{'Sport/Market':22s}  {'W':>3s} {'L':>3s} {'N':>3s}  {'WinRate':>8s}  {'NetPnL':>10s}  {'MaxLoss':>10s}")
print("-" * 80)
for key in sorted(matrix, key=lambda k: matrix[k]["pnl"], reverse=True):
    s = matrix[key]
    total = s["w"] + s["l"]
    wr = (s["w"] / total * 100) if total else 0
    print(f"{key:22s}  {s['w']:>3d} {s['l']:>3d} {s['neutral']:>3d}  {wr:>7.1f}%  ${s['pnl']:>9.2f}  ${s['max_loss']:>9.2f}")

# ── 2. Exit Reason Dagilimi ──
print()
print("=" * 80)
print("2. EXIT REASON BREAKDOWN — market_flip riski")
print("=" * 80)
reason_matrix = defaultdict(lambda: defaultdict(lambda: {"count": 0, "pnl": 0.0}))
for r in audit_records:
    if r.get("exit_price") is None:
        continue
    sport = r.get("sport_tag", "?").lower().split("_")[0] or "?"
    mt = market_type(r.get("slug", ""))
    reason = r.get("exit_reason", "?")
    key = f"{sport}/{mt}"
    reason_matrix[key][reason]["count"] += 1
    reason_matrix[key][reason]["pnl"] += r.get("exit_pnl_usdc", 0) or 0

print(f"{'Sport/Market':22s}  {'Reason':22s}  {'Count':>5s}  {'PnL':>10s}")
print("-" * 80)
for key in sorted(reason_matrix):
    for reason, stats in sorted(reason_matrix[key].items(), key=lambda x: x[1]["pnl"]):
        flag = "  !" if reason in ("market_flip", "stop_loss") and stats["pnl"] < 0 else ""
        print(f"{key:22s}  {reason:22s}  {stats['count']:>5d}  ${stats['pnl']:>9.2f}{flag}")

# ── 3. UFC saat-bazli analiz ──
print()
print("=" * 80)
print("3. UFC EXITS — saat dagilimi (kayip pattern arastir)")
print("=" * 80)
ufc_by_hour = defaultdict(lambda: {"w": 0, "l": 0, "pnl": 0.0})
for ex in bot_log_exits:
    if not ex["slug"].startswith("ufc"):
        continue
    try:
        dt = datetime.strptime(ex["ts"], "%Y-%m-%d %H:%M:%S")
        hour = dt.hour
    except ValueError:
        continue
    if ex["pnl"] > 0:
        ufc_by_hour[hour]["w"] += 1
    elif ex["pnl"] < 0:
        ufc_by_hour[hour]["l"] += 1
    ufc_by_hour[hour]["pnl"] += ex["pnl"]

print(f"{'Hour (UTC)':12s}  {'W':>3s} {'L':>3s}  {'NetPnL':>10s}")
print("-" * 50)
for hour in sorted(ufc_by_hour):
    s = ufc_by_hour[hour]
    total = s["w"] + s["l"]
    print(f"{hour:>02d}:00       {s['w']:>3d} {s['l']:>3d}  ${s['pnl']:>9.2f}")
print(f"  Total UFC exits: {sum((v['w']+v['l']) for v in ufc_by_hour.values())}")
print(f"  Total UFC PnL: ${sum(v['pnl'] for v in ufc_by_hour.values()):.2f}")

# ── 4. Sport bazinda toplam ozet ──
print()
print("=" * 80)
print("4. SPORT TOPLAM (tum market types)")
print("=" * 80)
sport_total = defaultdict(lambda: {"w": 0, "l": 0, "pnl": 0.0})
for r in audit_records:
    if r.get("exit_price") is None:
        continue
    sport = r.get("sport_tag", "?").lower().split("_")[0] or "?"
    pnl = r.get("exit_pnl_usdc", 0) or 0
    if pnl > 0:
        sport_total[sport]["w"] += 1
    elif pnl < 0:
        sport_total[sport]["l"] += 1
    sport_total[sport]["pnl"] += pnl

for sport in sorted(sport_total, key=lambda k: sport_total[k]["pnl"], reverse=True):
    s = sport_total[sport]
    total = s["w"] + s["l"]
    wr = (s["w"] / total * 100) if total else 0
    sign = "[+]" if s["pnl"] > 0 else "[-]"
    print(f"  {sign} {sport:10s}  {s['w']}W/{s['l']}L  win_rate={wr:5.1f}%  net=${s['pnl']:>8.2f}")
