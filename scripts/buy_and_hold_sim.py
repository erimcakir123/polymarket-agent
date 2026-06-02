"""Buy-and-hold to resolution simulation.

Soru: Bot SL yemese, spike umurlamasa, MAÇ SONUNA kadar tutsaydı net ne olurdu?
"""
import json
import httpx
import sys
import glob

sys.stdout.reconfigure(encoding="utf-8")


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
        return {
            "prices": [float(p) for p in prices],
            "token_ids": token_ids,
        }
    except Exception:
        return None


files = [
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.archive.20260526_172100.jsonl",
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.archive.20260527_130608.jsonl",
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.jsonl",
]
trades = []
for f in files:
    try:
        for l in open(f, encoding="utf-8"):
            if l.strip():
                trades.append(json.loads(l))
    except Exception:
        pass

closed = [
    r
    for r in trades
    if r.get("exit_reason") and r.get("exit_reason") != "wipe_archived"
]
print(f"Toplam closed: {len(closed)}", file=sys.stderr)

print("Resolution cekiliyor...", file=sys.stderr)
resolved = []
for i, r in enumerate(closed):
    if i % 30 == 0:
        print(f"  {i}/{len(closed)}", file=sys.stderr)
    info = fetch_resolved(r.get("token_id", ""))
    if not info or not info["prices"]:
        continue
    tid = r.get("token_id", "")
    try:
        bi = (
            info["token_ids"].index(str(tid))
            if str(tid) in info["token_ids"]
            else 0
        )
    except (ValueError, IndexError):
        bi = 0
    r["_bot_res"] = info["prices"][bi] if bi < len(info["prices"]) else 0
    r["_bot_won"] = r["_bot_res"] > 0.5
    resolved.append(r)


def market_type(slug):
    if "first-set-winner" in slug:
        return "first_set_winner"
    if "set-totals" in slug:
        return "set_totals"
    if "set-handicap" in slug:
        return "set_handicap"
    if "match-total" in slug:
        return "match_total"
    return "moneyline"


# SİMULATION
buy_hold_pnl = 0.0
real_pnl = 0.0
wins = 0
losses = 0
total_size = 0.0
per_market = {}

for r in resolved:
    size = r["size_usdc"]
    entry = r["entry_price"]
    won = r["_bot_won"]
    if entry <= 0:
        continue
    if won:
        pnl = size * (1 - entry) / entry
        wins += 1
    else:
        pnl = -size
        losses += 1
    buy_hold_pnl += pnl
    real_pnl += r["exit_pnl_usdc"]
    total_size += size
    mt = market_type(r["slug"])
    if mt not in per_market:
        per_market[mt] = {"n": 0, "w": 0, "pnl": 0, "real": 0, "size": 0}
    per_market[mt]["n"] += 1
    per_market[mt]["size"] += size
    if won:
        per_market[mt]["w"] += 1
    per_market[mt]["pnl"] += pnl
    per_market[mt]["real"] += r["exit_pnl_usdc"]

n = wins + losses
print(f"\n{'=' * 72}")
print(f"BUY-AND-HOLD SİMULASYONU — SL YOK + SPIKE YOK + MAÇ SONUNA KADAR TUT")
print(f"{'=' * 72}")
print(f"\nResolved trade: {n}")
print(f"Wins (bot tarafi resolution'da kazandi): {wins} ({wins / n * 100:.1f}%)")
print(f"Losses (bot tarafi kaybetti): {losses} ({losses / n * 100:.1f}%)")
print(f"Toplam yatirilan: ${total_size:.2f}")
print()
print(f"  {'Senaryo':<32}{'PnL':>16}")
print("-" * 52)
print(f"  {'REAL (mevcut bot, SL+spike)':<32}${real_pnl:>+14.2f}")
print(f"  {'BUY-AND-HOLD (maç sonuna tut)':<32}${buy_hold_pnl:>+14.2f}")
print(f"  {'FARK':<32}${buy_hold_pnl - real_pnl:>+14.2f}")

ev_per_trade = buy_hold_pnl / n if n else 0
print(f"\n  Buy-and-hold beklenen deger/trade: ${ev_per_trade:+.2f}")
print(f"  100 trade için: ${ev_per_trade * 100:+.0f}")

print(f"\n{'=' * 72}")
print(f"MARKET TYPE BAZLI")
print(f"{'=' * 72}")
print(
    f"  {'Market':<22}{'N':>4}{'Win%':>7}{'Real PnL':>13}{'Hold PnL':>13}{'Fark':>11}"
)
print("-" * 75)
for mt, d in sorted(per_market.items(), key=lambda x: -x[1]["pnl"]):
    wr = d["w"] / d["n"] * 100
    real_str = f"${d['real']:+.2f}"
    hold_str = f"${d['pnl']:+.2f}"
    fark_str = f"${d['pnl'] - d['real']:+.2f}"
    print(f"  {mt:<22}{d['n']:>4}{wr:>6.0f}%{real_str:>13}{hold_str:>13}{fark_str:>11}")
