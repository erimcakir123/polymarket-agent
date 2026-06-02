"""Bot Modeli vs Market Konsensüsü — 90 trade.

3 öngörü kıyaslaması:
1. BOT'un tahmini (bot'un girdiği taraf) — gerçek sonuç ne?
2. MARKET'in tahmini (entry'de hangi taraf > 0.5 = market favorisi) — gerçek sonuç ne?
3. RANDOM (50/50) — referans

Soru: Bot, market'ten daha iyi tahmin yapıyor mu?
"""
import json
import httpx
import sys
from collections import defaultdict

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


def market_type(slug):
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


paths = [
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.archive.20260526_172100.jsonl",
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.archive.20260527_130608.jsonl",
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.jsonl",
]
all_recs = []
for p in paths:
    try:
        for l in open(p, encoding="utf-8"):
            if l.strip():
                all_recs.append(json.loads(l))
    except FileNotFoundError:
        pass

closed = [r for r in all_recs if r.get("exit_reason") and r.get("exit_reason") != "wipe_archived"]
print(f"Toplam {len(closed)} closed trade analiz ediliyor (resolution çekiliyor)...\n", file=sys.stderr)

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
    bot_resolution = info["prices"][bot_idx] if bot_idx < len(info["prices"]) else 0
    r["_bot_won"] = bot_resolution > 0.5
    r["_market_favored_bot_side"] = r["entry_price"] > 0.5
    resolved.append(r)

n = len(resolved)
print(f"\n{'='*80}")
print(f"MODEL vs MARKET KARSILASTIRMA — {n} trade")
print(f"{'='*80}\n")

# Bot tahmini doğru: bot her zaman "kendi tarafı kazanır" diye girer
bot_correct = sum(1 for r in resolved if r["_bot_won"])
# Market'in favorisi: entry fiyatı > 0.5 olan taraf
# Market kazansaydı: bot'un girdiği taraf market favorisiyse VE kazandıysa, veya market underdog sandıysa VE bot kaybettiyse
market_correct = sum(
    1
    for r in resolved
    if r["_market_favored_bot_side"] == r["_bot_won"]
)

print(f"{'Tahmin Kaynağı':<25} {'Doğru':<10} {'Yanlış':<10} {'Doğruluk':<10}")
print("-" * 60)
print(
    f"{'BOT (Sackmann model)':<25} {bot_correct:<10} {n-bot_correct:<10} {bot_correct/n*100:.1f}%"
)
print(
    f"{'MARKET (Polymarket)':<25} {market_correct:<10} {n-market_correct:<10} {market_correct/n*100:.1f}%"
)

# Random 50/50 referans
print(f"{'RANDOM (50/50)':<25} {'~50%':<10}")

print(f"\n## SUB-KIRILIM: Bot ile Market ne zaman aynı/farklı tarafta?")
agree_correct = 0
agree_wrong = 0
disagree_bot_right = 0
disagree_market_right = 0
for r in resolved:
    bot_predicts_win = True  # Bot her zaman "ben aldığım taraf kazanır" der
    market_predicts_bot_win = r["_market_favored_bot_side"]
    actual_won = r["_bot_won"]

    if bot_predicts_win and market_predicts_bot_win:
        # Bot ve market anlaştı: ikisi de "bot'un tarafı kazanır" dedi
        if actual_won:
            agree_correct += 1
        else:
            agree_wrong += 1
    else:
        # Bot ve market anlaşmadı: bot "ben kazanırım" der, market "kaybeder" der (underdog)
        if actual_won:
            disagree_bot_right += 1  # Bot underdog'a girdi, underdog kazandı
        else:
            disagree_market_right += 1  # Bot underdog'a girdi, favorite kazandı (market haklı)

print(f"\n  Anlaşma (ikisi de bot kazanır) + bot kazandı: {agree_correct}")
print(f"  Anlaşma (ikisi de bot kazanır) + bot kaybetti: {agree_wrong}")
print(f"  Anlaşmazlık (bot underdog) + bot kazandı (sürpriz):  {disagree_bot_right}")
print(f"  Anlaşmazlık (bot underdog) + bot kaybetti (market haklı): {disagree_market_right}")

# Performans entry_price bucket'ına göre
print(f"\n## ENTRY PRICE BUCKET — Bot'un girdiği fiyat aralığı vs doğruluk")
buckets = defaultdict(list)
for r in resolved:
    ep = r["entry_price"]
    if ep < 0.20:
        b = "<0.20 (deep dog)"
    elif ep < 0.35:
        b = "0.20-0.35 (dog)"
    elif ep < 0.50:
        b = "0.35-0.50 (underdog)"
    elif ep < 0.65:
        b = "0.50-0.65 (slight fav)"
    else:
        b = ">0.65 (favorite)"
    buckets[b].append(r)

print(f"  {'Bucket':<25} {'N':<5} {'Bot dogru':<10} {'PnL net':<10}")
print("  " + "-" * 60)
for b in ["<0.20 (deep dog)", "0.20-0.35 (dog)", "0.35-0.50 (underdog)", "0.50-0.65 (slight fav)", ">0.65 (favorite)"]:
    items = buckets.get(b, [])
    if not items:
        continue
    correct = sum(1 for r in items if r["_bot_won"])
    pnl = sum(r["exit_pnl_usdc"] for r in items)
    print(f"  {b:<25} {len(items):<5} {correct/len(items)*100:.0f}%{'':<6} ${pnl:+.2f}")

# Edge'e göre
print(f"\n## EDGE BUCKET — Bot'un edge'i ne kadar büyükse bot kazansa daha iyi olur mu?")
edge_buckets = defaultdict(list)
for r in resolved:
    # edge = abs(bot's probability - market's probability)
    # Bot's anchor_probability vs market's entry_price (her ikisi de YES side için)
    anchor = r.get("anchor_probability", 0)
    if anchor == 0:
        continue
    market_p = r["entry_price"]  # Bot'un sahip olduğu side fiyatı = market'in o side için olasılığı
    edge = abs(anchor - market_p)
    if edge < 0.10:
        eb = "<10% edge"
    elif edge < 0.20:
        eb = "10-20% edge"
    elif edge < 0.30:
        eb = "20-30% edge"
    else:
        eb = ">30% edge"
    edge_buckets[eb].append(r)

print(f"  {'Edge bucket':<20} {'N':<5} {'Bot dogru':<10} {'PnL net':<10} {'Avg PnL'}")
print("  " + "-" * 65)
for eb in ["<10% edge", "10-20% edge", "20-30% edge", ">30% edge"]:
    items = edge_buckets.get(eb, [])
    if not items:
        continue
    correct = sum(1 for r in items if r["_bot_won"])
    pnl = sum(r["exit_pnl_usdc"] for r in items)
    print(f"  {eb:<20} {len(items):<5} {correct/len(items)*100:.0f}%{'':<6} ${pnl:+.2f}   ${pnl/len(items):+.2f}")
