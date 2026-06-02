"""Tennis kategori bazli gercek paper EV — spike catch cikarilmis.

Odds API kapsama testi de var.
"""
import json
import httpx
import sys
import glob
from collections import defaultdict
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

# 1) ODDS API SPORT LISTESI
print("=== ODDS API TENNIS KAPSAMA ===\n")
r = httpx.get("https://api.the-odds-api.com/v4/sports", timeout=10)
if r.status_code == 200:
    sports = r.json()
    tennis = [s for s in sports if "tennis" in s.get("key", "").lower()]
    print(f"Aktif tenis sport key'leri ({len(tennis)} adet):")
    for s in tennis:
        print(f"  {s['key']:<35} title={s.get('title', '')}")
    print(
        "\nNOT: Standart paket head-to-head (ML) + totals + spreads sunar."
    )
    print(
        "Set 1 Winner, Set Totals, Set Handicap GENELLIKLE odds API'de YOK."
    )
else:
    print(f"API hata: {r.status_code}")


# 2) KATEGORI BAZLI GERCEK EV
print("\n" + "=" * 78)
print("KATEGORI BAZLI — SPIKE CATCH'SIZ GERCEK PAPER EV")
print("=" * 78)

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
    r for r in trades if r.get("exit_reason") and r.get("exit_reason") != "wipe_archived"
]
print(f"\nToplam closed: {len(closed)}")


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


def mt(slug):
    if "first-set-winner" in slug:
        return "first_set_winner"
    if "first-set-totals" in slug:
        return "first_set_totals"
    if "set-totals" in slug:
        return "set_totals"
    if "set-handicap" in slug:
        return "set_handicap"
    if "match-total" in slug:
        return "match_total"
    return "moneyline"


print("\nPolymarket resolution cekiliyor...", file=sys.stderr)
for i, r in enumerate(closed):
    if i % 20 == 0:
        print(f"  {i}/{len(closed)}", file=sys.stderr)
    info = fetch_resolved(r.get("token_id", ""))
    r["_resolved"] = None
    if info and info["prices"]:
        tid = r.get("token_id", "")
        try:
            bi = (
                info["token_ids"].index(str(tid))
                if str(tid) in info["token_ids"]
                else 0
            )
        except (ValueError, IndexError):
            bi = 0
        bot_res = info["prices"][bi] if bi < len(info["prices"]) else 0
        r["_resolved"] = True
        r["_bot_won"] = bot_res > 0.5
    r["_mt"] = mt(r["slug"])

print(
    f"\n{'Market':<22}{'N':<5}{'RealWin':<9}{'RealLoss':<10}{'SpikeWin':<10}{'PnL_All':<11}{'PnL_NoSpike':<14}{'InOddsAPI'}"
)
print("-" * 105)
groups = defaultdict(list)
for r in closed:
    groups[r["_mt"]].append(r)

odds_avail = {
    "moneyline": "YES",
    "match_total": "MAYBE",
    "set_totals": "NO",
    "set_handicap": "NO",
    "first_set_winner": "NO",
    "first_set_totals": "NO",
}
total_with = 0
total_no_spike = 0
total_no_spike_in_odds = 0
for mtype, items in sorted(
    groups.items(), key=lambda x: -sum(r["exit_pnl_usdc"] for r in x[1])
):
    real_wins = []
    real_losses = []
    spike_wins = []
    for r in items:
        won = r["exit_pnl_usdc"] > 0
        if r.get("_resolved") is None:
            if won:
                spike_wins.append(r)
            else:
                real_losses.append(r)
            continue
        bot_won = r["_bot_won"]
        if bot_won and won:
            real_wins.append(r)
        elif bot_won and not won:
            real_losses.append(r)  # cina
        elif not bot_won and won:
            spike_wins.append(r)
        else:
            real_losses.append(r)
    pnl_all = sum(r["exit_pnl_usdc"] for r in items)
    pnl_no_spike = sum(r["exit_pnl_usdc"] for r in (real_wins + real_losses))
    in_odds = odds_avail.get(mtype, "?")
    total_with += pnl_all
    total_no_spike += pnl_no_spike
    if in_odds == "YES":
        total_no_spike_in_odds += pnl_no_spike
    print(
        f"  {mtype:<22}{len(items):<5}{len(real_wins):<9}{len(real_losses):<10}{len(spike_wins):<10}"
        f"${pnl_all:>+9.2f}  ${pnl_no_spike:>+12.2f}  {in_odds}"
    )

print(f"\n  TOPLAM PnL (spike dahil — dry_run goruntusu): ${total_with:+.2f}")
print(f"  TOPLAM PnL (spike haric — paper gercek beklenen): ${total_no_spike:+.2f}")
print(f"  Odds API'de OLAN market'lerde TOPLAM (spike haric): ${total_no_spike_in_odds:+.2f}")

# Cina-tipi sayisi (real loss ama bot doğru tarafta)
cina_count = 0
cina_pnl = 0
for r in closed:
    if r.get("_resolved") is None or not r["_bot_won"]:
        continue
    if r["exit_pnl_usdc"] >= 0:
        continue
    cina_count += 1
    cina_pnl += r["exit_pnl_usdc"]
print(f"\n  Cina-tipi 'bot dogru ama erken cikti': {cina_count} adet, kayip ${cina_pnl:.2f}")
print(f"  Bunlar real exit-ability sorunundan kaynakli — paper REJECTED + SL")
