"""Tennis vs Basketball model dogruluk karsilastirma.

Tennis-lab Sackmann modelini kullanir (bookmaker_prob=0).
Ana bot Odds API bookmaker konsensus kullanir (bookmaker_prob var).

Soru: Basket bot daha iyi tahmin yapiyor mu? Cunku Odds API destekli.
"""
import json
import httpx
import sys
import glob
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

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
        return {"prices": [float(p) for p in prices], "token_ids": token_ids}
    except Exception:
        return None


def analyze_set(label, trades):
    print(f"\n{'#'*78}\n# {label}\n{'#'*78}")
    print(f"Toplam: {len(trades)}", file=sys.stderr)
    if not trades:
        print("(boş)")
        return

    print(f"Polymarket resolution çekiliyor...", file=sys.stderr)
    resolved = []
    for i, r in enumerate(trades):
        if i % 20 == 0:
            print(f"  {i}/{len(trades)}", file=sys.stderr)
        info = fetch_resolved(r.get("token_id", ""))
        if info is None or not info["prices"]:
            continue
        tid = r.get("token_id", "")
        try:
            bot_idx = (
                info["token_ids"].index(str(tid))
                if str(tid) in info["token_ids"]
                else 0
            )
        except (ValueError, IndexError):
            bot_idx = 0
        bot_res = info["prices"][bot_idx] if bot_idx < len(info["prices"]) else 0
        r["_bot_won"] = bot_res > 0.5
        resolved.append(r)

    n = len(resolved)
    if not n:
        print("Resolution alinamadi")
        return

    # BOT vs MARKET
    bot_correct = sum(1 for r in resolved if r["_bot_won"])
    market_correct = sum(
        1 for r in resolved if (r["entry_price"] > 0.5) == r["_bot_won"]
    )

    # Bookmaker (sadece ana bot'ta gercek deger var)
    has_bm = [r for r in resolved if r.get("bookmaker_prob", 0) > 0.01]
    bm_correct = 0
    if has_bm:
        # bookmaker_prob: bot tarafinin bookmaker tahminli olasiligi
        # eger bookmaker_prob > 0.5 ise bookmaker bot tarafini favoriliyor
        bm_correct = sum(
            1 for r in has_bm if (r["bookmaker_prob"] > 0.5) == r["_bot_won"]
        )

    print(f"\nResolved: {n}")
    print(f"\n{'Kaynak':<30} {'Dogru':<8} {'Yanlis':<8} {'Dogruluk'}")
    print("-" * 60)
    print(
        f"{'BOT (model)':<30} {bot_correct:<8} {n-bot_correct:<8} {bot_correct/n*100:.1f}%"
    )
    print(
        f"{'MARKET (Polymarket entry)':<30} {market_correct:<8} {n-market_correct:<8} {market_correct/n*100:.1f}%"
    )
    if has_bm:
        print(
            f"{'BOOKMAKER (Odds API)':<30} {bm_correct:<8} {len(has_bm)-bm_correct:<8} {bm_correct/len(has_bm)*100:.1f}%  (sample={len(has_bm)})"
        )

    # PnL gerçekleşmesi
    net = sum(r["exit_pnl_usdc"] for r in resolved)
    wins_count = sum(1 for r in resolved if r["exit_pnl_usdc"] > 0)
    losses_count = sum(1 for r in resolved if r["exit_pnl_usdc"] < 0)
    print(
        f"\n  Net PnL: ${net:+.2f}  (W:{wins_count}/L:{losses_count}, win_rate={wins_count/n*100:.1f}%)"
    )


# === TENNIS - 90 trade tum donem (24-28 May) ===
_tennis_audit = Path(
    os.getenv("TENNIS_LAB_DIR", str(Path(__file__).resolve().parent.parent.parent / "tennis-lab"))
) / "logs" / "audit"
tennis_paths = [
    str(_tennis_audit / "trade_history.archive.20260526_172100.jsonl"),
    str(_tennis_audit / "trade_history.archive.20260527_130608.jsonl"),
    str(_tennis_audit / "trade_history.jsonl"),
]
tennis_trades = []
for p in tennis_paths:
    try:
        for l in open(p, encoding="utf-8"):
            if l.strip():
                tennis_trades.append(json.loads(l))
    except FileNotFoundError:
        pass
tennis_closed = [
    r
    for r in tennis_trades
    if r.get("exit_reason") and r.get("exit_reason") != "wipe_archived"
]
analyze_set(f"TENNIS-LAB (Sackmann/Glicko2 model) - {len(tennis_closed)} closed trade", tennis_closed)

# === BASKETBALL - ana bot audit, 24-28 May, sport_tag=nba|wnba ===
ana_audit = str(Path(__file__).resolve().parent.parent / "logs" / "audit")
all_basket = []
# All audit archive + current
for p in sorted(glob.glob(f"{ana_audit}/trade_history*.jsonl")):
    try:
        for l in open(p, encoding="utf-8"):
            if not l.strip():
                continue
            try:
                r = json.loads(l)
            except json.JSONDecodeError:
                continue
            sport = (r.get("sport_tag") or "").lower()
            entry_ts = r.get("entry_timestamp", "")
            if sport not in ("nba", "wnba", "basketball"):
                continue
            # Date filter: 24-28 May 2026
            if not entry_ts:
                continue
            try:
                d = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if d < datetime(2026, 5, 24, tzinfo=d.tzinfo) or d > datetime(2026, 5, 29, tzinfo=d.tzinfo):
                continue
            all_basket.append(r)
    except FileNotFoundError:
        continue

# Dedupe by condition_id + token_id (audit'lerin tamami audit'te kalir, dedupe)
seen = set()
unique_basket = []
for r in all_basket:
    key = (r.get("condition_id"), r.get("token_id"), r.get("entry_timestamp"))
    if key not in seen:
        seen.add(key)
        unique_basket.append(r)

basket_closed = [
    r
    for r in unique_basket
    if r.get("exit_reason") and r.get("exit_reason") != "wipe_archived"
]
print(
    f"\nBASKET: ana bot audit'inde 24-28 May arasi {len(unique_basket)} basket trade, {len(basket_closed)} kapanmis",
    file=sys.stderr,
)
analyze_set(
    f"ANA BOT — BASKETBALL (NBA/WNBA, Odds API bookmaker) - {len(basket_closed)} closed trade (24-28 May)",
    basket_closed,
)
