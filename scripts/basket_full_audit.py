"""Ana bot basket trade tam tarama — TUM audit dosyalari, genis tarih araligi.

Tennis 90 trade aralinda: 24-28 May
Basket icin: 22-28 May (biraz daha genis, daha cok sample icin)
"""
import json
import httpx
import sys
import glob
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

ana_audit = r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/logs/audit"

# TUM audit dosyalari (recursive)
all_files = []
for pat in [
    f"{ana_audit}/trade_history*.jsonl",
    f"{ana_audit}/_history/**/trade_history*.jsonl",
    f"{ana_audit}/_history/trade_history*.jsonl",
]:
    all_files.extend(glob.glob(pat, recursive=True))
all_files = list(set(all_files))
print(f"Toplam audit dosyasi: {len(all_files)}", file=sys.stderr)

# Tum kayitlari topla
all_trades = []
for f in all_files:
    try:
        for l in open(f, encoding="utf-8"):
            if not l.strip():
                continue
            try:
                r = json.loads(l)
            except json.JSONDecodeError:
                continue
            all_trades.append(r)
    except Exception:
        pass

print(f"Toplam audit kaydi: {len(all_trades)}", file=sys.stderr)

# Sport dagilimi
sport_count = defaultdict(int)
for r in all_trades:
    sport_count[r.get("sport_tag", "?").lower()] += 1
print(f"\nSPORT DAGILIMI (tum tarihler):")
for s, n in sorted(sport_count.items(), key=lambda x: -x[1]):
    print(f"  {s:<20} {n}")

# Tarihe gore basket filtrele
basket_trades = []
for r in all_trades:
    sport = (r.get("sport_tag") or "").lower()
    if sport not in ("nba", "wnba", "basketball"):
        continue
    ts = r.get("entry_timestamp", "")
    if not ts:
        continue
    try:
        d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        continue
    # Tennis donemine yakin: 22-29 May (biraz genis)
    if d < datetime(2026, 5, 22, tzinfo=d.tzinfo) or d > datetime(2026, 5, 29, tzinfo=d.tzinfo):
        continue
    basket_trades.append(r)

print(f"\n22-29 May araliginda basket trade: {len(basket_trades)}", file=sys.stderr)

# Dedupe by condition_id + entry_timestamp
seen = set()
unique = []
for r in basket_trades:
    key = (r.get("condition_id"), r.get("entry_timestamp"))
    if key in seen:
        continue
    seen.add(key)
    unique.append(r)
print(f"Dedupe sonrasi: {len(unique)}", file=sys.stderr)

# Closed vs open
closed = [r for r in unique if r.get("exit_reason") and r.get("exit_reason") not in ("wipe_archived", "")]
print(f"Kapanmis (exit_reason var): {len(closed)}", file=sys.stderr)

# Tarih dagilimi
date_count = defaultdict(int)
for r in closed:
    d = r.get("entry_timestamp", "")[:10]
    date_count[d] += 1
print(f"\nKapanmis basket trade tarih dagilimi:")
for d, n in sorted(date_count.items()):
    print(f"  {d}: {n}")


def fetch_resolved(token_id):
    try:
        r = httpx.get(
            "https://gamma-api.polymarket.com/markets",
            params={"clob_token_ids": token_id, "closed": "true"},
            timeout=10,
        )
        if r.status_code != 200 or not r.json():
            r2 = httpx.get(
                "https://gamma-api.polymarket.com/markets",
                params={"clob_token_ids": token_id},
                timeout=10,
            )
            if not r2.json():
                return None
            data = r2.json()
        else:
            data = r.json()
        m = data[0] if isinstance(data, list) else data
        if not m.get("closed"):
            return None
        prices = (
            json.loads(m["outcomePrices"])
            if isinstance(m.get("outcomePrices"), str)
            else m.get("outcomePrices", [])
        )
        token_ids = (
            json.loads(m.get("clobTokenIds", "[]"))
            if isinstance(m.get("clobTokenIds"), str)
            else m.get("clobTokenIds", [])
        )
        return {"prices": [float(p) for p in prices], "token_ids": token_ids}
    except Exception:
        return None


# Resolution + analiz
print(f"\nPolymarket resolution cekiliyor ({len(closed)} trade)...", file=sys.stderr)
resolved = []
for i, r in enumerate(closed):
    if i % 20 == 0:
        print(f"  {i}/{len(closed)}", file=sys.stderr)
    info = fetch_resolved(r.get("token_id", ""))
    if info is None or not info["prices"]:
        continue
    tid = r.get("token_id", "")
    try:
        bot_idx = info["token_ids"].index(str(tid)) if str(tid) in info["token_ids"] else 0
    except (ValueError, IndexError):
        bot_idx = 0
    bot_res = info["prices"][bot_idx] if bot_idx < len(info["prices"]) else 0
    r["_bot_won"] = bot_res > 0.5
    resolved.append(r)

n = len(resolved)
if not n:
    print("Resolved trade yok")
    sys.exit()

bot_correct = sum(1 for r in resolved if r["_bot_won"])
market_correct = sum(1 for r in resolved if (r["entry_price"] > 0.5) == r["_bot_won"])
has_bm = [r for r in resolved if r.get("bookmaker_prob", 0) > 0.01]
bm_correct = sum(1 for r in has_bm if (r["bookmaker_prob"] > 0.5) == r["_bot_won"])

print(f"\n{'='*70}")
print(f"BASKETBALL — {n} resolved trade (22-29 May)")
print(f"{'='*70}")
print(f"\n{'Kaynak':<28} {'Dogru':<8} {'Yanlis':<8} {'Dogruluk'}")
print("-" * 60)
print(f"{'BOT (Odds API based)':<28} {bot_correct:<8} {n-bot_correct:<8} {bot_correct/n*100:.1f}%")
print(f"{'MARKET (Polymarket entry)':<28} {market_correct:<8} {n-market_correct:<8} {market_correct/n*100:.1f}%")
if has_bm:
    print(f"{'BOOKMAKER (raw bookmaker_prob)':<28} {bm_correct:<8} {len(has_bm)-bm_correct:<8} {bm_correct/len(has_bm)*100:.1f}%  (n={len(has_bm)})")

# PnL
net = sum(r["exit_pnl_usdc"] for r in resolved)
wins = sum(1 for r in resolved if r["exit_pnl_usdc"] > 0)
print(f"\nNet PnL: ${net:+.2f} (W:{wins}/L:{n-wins}, win_rate={wins/n*100:.1f}%)")

# Confidence dagilimi
print(f"\n## BASKET CONFIDENCE BREAKDOWN")
print(f"  {'Conf':<6} {'Total':<7} {'Dogru':<7} {'Dogruluk':<10} {'Net PnL':<12} {'BM_Acc'}")
print("  " + "-" * 65)
for conf in ["A", "B", "C"]:
    items = [r for r in resolved if r.get("confidence") == conf]
    if not items:
        continue
    c_correct = sum(1 for r in items if r["_bot_won"])
    c_net = sum(r["exit_pnl_usdc"] for r in items)
    c_bm = [r for r in items if r.get("bookmaker_prob", 0) > 0.01]
    bm_acc = sum(1 for r in c_bm if (r["bookmaker_prob"] > 0.5) == r["_bot_won"])
    bm_str = f"{bm_acc/len(c_bm)*100:.0f}% (n={len(c_bm)})" if c_bm else "N/A"
    print(
        f"  {conf:<6} {len(items):<7} {c_correct:<7} {c_correct/len(items)*100:<10.1f} ${c_net:+10.2f}  {bm_str}"
    )

# Market type
print(f"\n## BASKET MARKET TYPE BREAKDOWN")
print(f"  {'Type':<25} {'N':<5} {'Bot dogru':<10} {'BM dogru':<10} {'Net PnL'}")
print("  " + "-" * 65)
mt_groups = defaultdict(list)
for r in resolved:
    smt = r.get("sports_market_type") or "?"
    mt_groups[smt].append(r)
for mt, items in sorted(mt_groups.items(), key=lambda x: -len(x[1])):
    c_correct = sum(1 for r in items if r["_bot_won"])
    c_bm = [r for r in items if r.get("bookmaker_prob", 0) > 0.01]
    bm_acc = sum(1 for r in c_bm if (r["bookmaker_prob"] > 0.5) == r["_bot_won"])
    bm_str = f"{bm_acc/len(c_bm)*100:.0f}%" if c_bm else "N/A"
    c_net = sum(r["exit_pnl_usdc"] for r in items)
    print(
        f"  {mt:<25} {len(items):<5} {c_correct/len(items)*100:.0f}%{'':<6} {bm_str:<10} ${c_net:+10.2f}"
    )
