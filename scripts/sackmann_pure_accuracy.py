"""Sackmann modelinin SAF tahmin dogrulugu — SL/exit/spike yok.

Her trade icin:
- anchor_probability = Sackmann'in OWNED side icin tahmin ettigi olasilik
- Eger anchor > 0.5: Sackmann owned side kazanir diyor
- Eger anchor < 0.5: Sackmann owned side kaybeder (other side kazanir) diyor
- Polymarket resolution: gercek sonuc
- Sackmann_correct = (anchor > 0.5) == (bot_won)

Bonus: anchor probability confidence bucket'lari.
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
print(f"Toplam closed tennis trade: {len(closed)}", file=sys.stderr)

# Resolution cek
print("Polymarket resolution cekiliyor...", file=sys.stderr)
resolved = []
for i, r in enumerate(closed):
    if i % 20 == 0:
        print(f"  {i}/{len(closed)}", file=sys.stderr)
    anchor = r.get("anchor_probability", None)
    if anchor is None or anchor == 0:
        continue
    info = fetch_resolved(r.get("token_id", ""))
    if not info or not info["prices"]:
        continue
    tid = r.get("token_id", "")
    try:
        bi = info["token_ids"].index(str(tid)) if str(tid) in info["token_ids"] else 0
    except (ValueError, IndexError):
        bi = 0
    bot_res = info["prices"][bi] if bi < len(info["prices"]) else 0
    r["_bot_won"] = bot_res > 0.5
    r["_anchor"] = anchor
    r["_mt"] = mt(r["slug"])
    resolved.append(r)

n = len(resolved)
print(f"\nResolved + anchor olan trade: {n}")

# Sackmann SAF dogruluk
sackmann_correct = sum(1 for r in resolved if (r["_anchor"] > 0.5) == r["_bot_won"])
# Polymarket entry SAF dogruluk (karsilastirma)
market_correct = sum(1 for r in resolved if (r["entry_price"] > 0.5) == r["_bot_won"])

print(f"\n{'='*70}")
print(f"SAF TAHMIN DOGRULUK (execution mantigi yok)")
print(f"{'='*70}")
print(f"\n{'Kaynak':<35}{'Dogru':<8}{'Yanlis':<8}{'Dogruluk'}")
print("-" * 65)
print(
    f"{'SACKMANN (anchor_probability)':<35}{sackmann_correct:<8}{n-sackmann_correct:<8}{sackmann_correct/n*100:.1f}%"
)
print(
    f"{'MARKET (Polymarket entry price)':<35}{market_correct:<8}{n-market_correct:<8}{market_correct/n*100:.1f}%"
)

# Confidence bucket — Sackmann ne kadar "guvenli" tahmin ettiyse o kadar dogru mu?
print(f"\n{'='*70}")
print(f"ANCHOR PROBABILITY BUCKET — Sackmann ne kadar sure dogru?")
print(f"{'='*70}")
print(f"\n{'Bucket':<25}{'N':<5}{'Dogru':<8}{'Dogruluk':<10}{'Net PnL':<12}{'Ort PnL'}")
print("-" * 75)
buckets = [
    ("anchor > 0.85 (cok yuksek)", lambda a: a > 0.85),
    ("0.70-0.85 (yuksek)", lambda a: 0.70 <= a <= 0.85),
    ("0.50-0.70 (orta)", lambda a: 0.50 <= a < 0.70),
    ("0.30-0.50 (dusuk)", lambda a: 0.30 <= a < 0.50),
    ("0.15-0.30 (cok dusuk)", lambda a: 0.15 <= a < 0.30),
    ("anchor < 0.15 (deep dog)", lambda a: a < 0.15),
]
for label, cond in buckets:
    items = [r for r in resolved if cond(r["_anchor"])]
    if not items:
        continue
    correct = sum(1 for r in items if (r["_anchor"] > 0.5) == r["_bot_won"])
    net = sum(r["exit_pnl_usdc"] for r in items)
    print(
        f"  {label:<25}{len(items):<5}{correct:<8}{correct/len(items)*100:<10.1f}${net:>+10.2f}  ${net/len(items):>+.2f}"
    )

# Market type kirilimi — Sackmann hangi marketlerde iyi/kotu?
print(f"\n{'='*70}")
print(f"MARKET TYPE — Sackmann hangi alanlarda iyi/kotu?")
print(f"{'='*70}")
print(f"\n{'Market':<22}{'N':<5}{'Sackmann Dogru':<16}{'Market Dogru':<14}{'Sackmann avantaj'}")
print("-" * 85)
mt_groups = defaultdict(list)
for r in resolved:
    mt_groups[r["_mt"]].append(r)
for mtype, items in sorted(
    mt_groups.items(), key=lambda x: -sum((r["_anchor"] > 0.5) == r["_bot_won"] for r in x[1])
):
    s_correct = sum(1 for r in items if (r["_anchor"] > 0.5) == r["_bot_won"])
    m_correct = sum(1 for r in items if (r["entry_price"] > 0.5) == r["_bot_won"])
    s_acc = s_correct / len(items) * 100
    m_acc = m_correct / len(items) * 100
    advantage = s_acc - m_acc
    print(
        f"  {mtype:<22}{len(items):<5}{s_correct}/{len(items)} = {s_acc:.0f}%{'':<5}{m_correct}/{len(items)} = {m_acc:.0f}%{'':<2}{advantage:+.0f}%"
    )

# Sackmann ile Market hangi yonde ayrismiyor?
print(f"\n{'='*70}")
print(f"SACKMANN vs MARKET — uyusma ve ayrisma")
print(f"{'='*70}")
agree_both_predict_win = sum(
    1 for r in resolved if r["_anchor"] > 0.5 and r["entry_price"] > 0.5
)
agree_both_predict_loss = sum(
    1 for r in resolved if r["_anchor"] < 0.5 and r["entry_price"] < 0.5
)
disagree_sack_win_mkt_loss = sum(
    1 for r in resolved if r["_anchor"] > 0.5 and r["entry_price"] < 0.5
)
disagree_sack_loss_mkt_win = sum(
    1 for r in resolved if r["_anchor"] < 0.5 and r["entry_price"] > 0.5
)
print(f"  Anlasma — ikisi de bot kazanir: {agree_both_predict_win}")
print(f"  Anlasma — ikisi de bot kaybeder: {agree_both_predict_loss}")
print(f"  Anlasmazlik — Sackmann WIN, market LOSS dedi: {disagree_sack_win_mkt_loss}")
print(f"  Anlasmazlik — Sackmann LOSS, market WIN dedi: {disagree_sack_loss_mkt_win}")

# Anlasmazlik durumunda kim hakli oldu?
print(f"\n## ANLASMAZLIK durumlarinda KIM hakli cikti?")
disagree_trades = [r for r in resolved if (r["_anchor"] > 0.5) != (r["entry_price"] > 0.5)]
sack_right_in_disagree = sum(
    1 for r in disagree_trades if (r["_anchor"] > 0.5) == r["_bot_won"]
)
mkt_right_in_disagree = len(disagree_trades) - sack_right_in_disagree
print(f"  Toplam anlasmazlik: {len(disagree_trades)}")
print(f"  Sackmann hakli ciktigi: {sack_right_in_disagree} ({sack_right_in_disagree/len(disagree_trades)*100:.0f}%)")
print(f"  Market hakli ciktigi: {mkt_right_in_disagree} ({mkt_right_in_disagree/len(disagree_trades)*100:.0f}%)")
