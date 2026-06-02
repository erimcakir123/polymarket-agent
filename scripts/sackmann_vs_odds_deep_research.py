"""Sackmann silmeden önce DERIN arastirma.

Q1: match_total kazanci Sackmann sayesinde mi, sans mi?
Q2: moneyline kaybi Sackmann modelinden mi geliyor?
Q3: tennis-paper-lab gercek paper PnL (dry_run abartı yok)
Q4: Odds API consensus following ayni 36 trade'de daha iyi olur muydu?
"""
import json
import httpx
import sys
import glob
from collections import defaultdict
from datetime import datetime, timezone

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


# Tüm tenis trade audit dosyalarini topla
sources = [
    ("LAB", r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit"),
    ("PAPER", r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/logs/audit"),
]

all_trades = []
for label, base in sources:
    files = glob.glob(f"{base}/trade_history*.jsonl") + glob.glob(
        f"{base}/**/trade_history*.jsonl", recursive=True
    )
    for f in set(files):
        try:
            for l in open(f, encoding="utf-8"):
                if not l.strip():
                    continue
                try:
                    r = json.loads(l)
                except Exception:
                    continue
                r["_source"] = label
                all_trades.append(r)
        except Exception:
            pass

# Dedupe
seen = set()
unique = []
for r in all_trades:
    k = (r.get("condition_id"), r.get("token_id"), r.get("entry_timestamp"), r["_source"])
    if k in seen:
        continue
    seen.add(k)
    unique.append(r)

# Sadece closed
closed = [
    r for r in unique if r.get("exit_reason") and r.get("exit_reason") != "wipe_archived"
]
print(f"Total closed (lab + paper unique): {len(closed)}", file=sys.stderr)

# Resolve via Polymarket
print("Resolution cekiliyor...", file=sys.stderr)
for i, r in enumerate(closed):
    if i % 30 == 0:
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

# ====================================================================
# Q1: match_total kazanci real mi spike mi?
# ====================================================================
print("\n" + "=" * 78)
print("Q1: MATCH_TOTAL ANALİZİ — Sackmann sayesinde mi?")
print("=" * 78)
mt_trades = [r for r in closed if r["_mt"] == "match_total"]
print(f"\nToplam match_total trade: {len(mt_trades)}")

real_wins = []
real_losses = []
spike_wins = []
for r in mt_trades:
    if r.get("_resolved") is None:
        continue
    bot_won = r["_bot_won"]
    profit = r["exit_pnl_usdc"] > 0
    if bot_won and profit:
        real_wins.append(r)
    elif bot_won and not profit:
        real_losses.append(r)
    elif not bot_won and profit:
        spike_wins.append(r)
    else:
        real_losses.append(r)

total_pnl = sum(r["exit_pnl_usdc"] for r in mt_trades)
real_pnl = sum(r["exit_pnl_usdc"] for r in real_wins + real_losses)
spike_pnl = sum(r["exit_pnl_usdc"] for r in spike_wins)

print(
    f"  RESOLVED REAL WIN (model dogru + kar): {len(real_wins)} (+${sum(r['exit_pnl_usdc'] for r in real_wins):.2f})"
)
print(
    f"  RESOLVED REAL LOSS (model dogru ama erken cikis VEYA model yanlis + kayip): "
    f"{len(real_losses)} (${sum(r['exit_pnl_usdc'] for r in real_losses):+.2f})"
)
print(
    f"  SPIKE WIN (model yanlis ama 0.99 spike'tan kar): {len(spike_wins)} (+${spike_pnl:.2f})"
)
print(f"\n  PnL TOPLAM (spike dahil): ${total_pnl:+.2f}")
print(f"  PnL SADECE REAL (spike haric): ${real_pnl:+.2f}")
print(f"  PnL SPIKE'tan: +${spike_pnl:.2f}")

print(f"\n  match_total Sackmann saf doğruluğu (anchor > 0.5 == bot_won):")
correct_anchor = sum(
    1
    for r in mt_trades
    if r.get("_resolved") and (r.get("anchor_probability", 0) > 0.5) == r["_bot_won"]
)
resolved_count = sum(1 for r in mt_trades if r.get("_resolved") is not None)
print(f"    {correct_anchor}/{resolved_count} = {correct_anchor/resolved_count*100:.1f}%")

# ====================================================================
# Q2: moneyline kaybi neden?
# ====================================================================
print("\n" + "=" * 78)
print("Q2: MONEYLINE ANALİZİ — Sackmann modelinden mi kayıp?")
print("=" * 78)
ml_trades = [r for r in closed if r["_mt"] == "moneyline"]
print(f"\nToplam moneyline trade: {len(ml_trades)}")

resolved_ml = [r for r in ml_trades if r.get("_resolved") is not None]
# Sackmann saf accuracy
ml_sack_correct = sum(
    1 for r in resolved_ml if (r.get("anchor_probability", 0) > 0.5) == r["_bot_won"]
)
ml_market_correct = sum(
    1 for r in resolved_ml if (r["entry_price"] > 0.5) == r["_bot_won"]
)
print(f"  Sackmann (anchor > 0.5 == bot won): {ml_sack_correct}/{len(resolved_ml)} = {ml_sack_correct/len(resolved_ml)*100:.1f}%")
print(f"  Market (entry > 0.5 == bot won): {ml_market_correct}/{len(resolved_ml)} = {ml_market_correct/len(resolved_ml)*100:.1f}%")

# Bot vs Sackmann recommendation
# Bot her zaman sahip oldugu tarafa 'kazanir' der
bot_picks_correct = sum(1 for r in resolved_ml if r["_bot_won"])
print(f"\n  Bot'un picked side win rate: {bot_picks_correct}/{len(resolved_ml)} = {bot_picks_correct/len(resolved_ml)*100:.1f}%")

# Entry/anchor disagreement detaylı
print(f"\n  ANLAŞMA - ANLAŞMAZLIK matris:")
agree_both_win = sum(
    1
    for r in resolved_ml
    if r.get("anchor_probability", 0) > 0.5 and r["entry_price"] > 0.5
)
agree_both_loss = sum(
    1
    for r in resolved_ml
    if r.get("anchor_probability", 0) < 0.5 and r["entry_price"] < 0.5
)
sack_win_mkt_loss = sum(
    1
    for r in resolved_ml
    if r.get("anchor_probability", 0) > 0.5 and r["entry_price"] < 0.5
)
sack_loss_mkt_win = sum(
    1
    for r in resolved_ml
    if r.get("anchor_probability", 0) < 0.5 and r["entry_price"] > 0.5
)
print(f"    Sackmann WIN + Market WIN: {agree_both_win}")
print(f"    Sackmann LOSS + Market LOSS: {agree_both_loss}")
print(f"    Sackmann WIN + Market LOSS (Sackmann contrarian): {sack_win_mkt_loss}")
print(f"    Sackmann LOSS + Market WIN (Sackmann fade fav): {sack_loss_mkt_win}")

# ====================================================================
# Q3: Tennis-paper-lab paper mode reality
# ====================================================================
print("\n" + "=" * 78)
print("Q3: PAPER MODE REALITY — gerçek fills, spike abartısız")
print("=" * 78)
paper_trades = [r for r in closed if r["_source"] == "PAPER"]
print(f"\nTennis-paper-lab trade sayısı: {len(paper_trades)}")
if paper_trades:
    paper_pnl = sum(r["exit_pnl_usdc"] for r in paper_trades)
    paper_wins = sum(1 for r in paper_trades if r["exit_pnl_usdc"] > 0)
    print(f"  Net PnL: ${paper_pnl:+.2f}")
    print(f"  Win count: {paper_wins}/{len(paper_trades)} = {paper_wins/len(paper_trades)*100:.1f}%")

    # Exit reason
    from collections import Counter
    rsn = Counter(r["exit_reason"] for r in paper_trades)
    print(f"  Exit reasons: {dict(rsn)}")

    # Per market
    print(f"\n  Paper-only market type breakdown:")
    paper_mt = defaultdict(list)
    for r in paper_trades:
        paper_mt[r["_mt"]].append(r)
    for k, items in sorted(paper_mt.items(), key=lambda x: -sum(r["exit_pnl_usdc"] for r in x[1])):
        n = len(items)
        pnl = sum(r["exit_pnl_usdc"] for r in items)
        print(f"    {k:<22} n={n} pnl=${pnl:+.2f}")

# ====================================================================
# Q4: Odds API consensus following simülasyonu
# ====================================================================
print("\n" + "=" * 78)
print("Q4: SİMÜLASYON — Odds API consensus following ayni maclarda")
print("=" * 78)
print("\nVarsayim: Polymarket entry fiyati bookmaker consensus proxy'si.")
print("Bot favori (entry > 0.55) tarafa girseydi ne olurdu?")

# Sadece Odds API destekli: moneyline + match_total
odds_supported = [r for r in closed if r["_mt"] in ("moneyline", "match_total")]
resolved_odds = [r for r in odds_supported if r.get("_resolved") is not None]
print(f"\n  Odds API supported (ML + match_total) resolved trade: {len(resolved_odds)}")

# Sim 1: "Bot her zaman Polymarket favorisini alsaydi" (mevcut bot tersi)
sim_correct = sum(
    1 for r in resolved_odds if (r["entry_price"] > 0.5) == r["_bot_won"]
)
sim_acc = sim_correct / len(resolved_odds) * 100 if resolved_odds else 0
print(
    f"  Sim_1 (favori tarafa girilse): doğruluk {sim_correct}/{len(resolved_odds)} = {sim_acc:.1f}%"
)

# Sim 2: Sadece >= 0.55 favori al + edge calculate
strong_fav = [r for r in resolved_odds if r["entry_price"] > 0.55 or r["entry_price"] < 0.45]
print(f"\n  Sim_2 (sadece >= 0.55 / <= 0.45 entry'de): n={len(strong_fav)}")
if strong_fav:
    sim2_correct = sum(1 for r in strong_fav if (r["entry_price"] > 0.5) == r["_bot_won"])
    print(f"    Bookmaker following accuracy: {sim2_correct}/{len(strong_fav)} = {sim2_correct/len(strong_fav)*100:.1f}%")

# Sim 3: Mevcut Sackmann moneyline + match_total kombine sonuc
sack_combo_pnl = sum(r["exit_pnl_usdc"] for r in odds_supported)
sack_combo_real = sum(
    r["exit_pnl_usdc"]
    for r in odds_supported
    if r.get("_resolved") and (r["_bot_won"] == (r["exit_pnl_usdc"] > 0))
)
print(f"\n  Mevcut Sackmann ML+MT combined PnL (spike dahil): ${sack_combo_pnl:+.2f}")
print(f"  Mevcut Sackmann ML+MT combined REAL PnL (spike haric): ${sack_combo_real:+.2f}")

# ====================================================================
# KARAR MATRİSİ
# ====================================================================
print("\n" + "=" * 78)
print("KARAR MATRİSİ")
print("=" * 78)
print(f"\n  Tüm 97 trade gerçek paper EV (spike haric): hesaplandi öncesinden = ~-$302")
print(f"  Sadece Odds API destekli (ML + MT) Sackmann PnL: ${sack_combo_pnl:+.2f} (spike-li)")
print(f"\n  Soru: Odds API consensus following ayni 36 trade'de daha iyi mi?")
print(f"  Cevap için: Sim_2 doğruluğu (yukarida) ile Sackmann accuracy karşılaştır")
ml_sack = ml_sack_correct / len(resolved_ml) * 100 if resolved_ml else 0
mt_sack = correct_anchor / resolved_count * 100 if resolved_count else 0
ml_mt_combined = (
    sum(1 for r in resolved_odds if (r.get("anchor_probability", 0) > 0.5) == r["_bot_won"])
    / len(resolved_odds)
    * 100
    if resolved_odds
    else 0
)
print(f"\n  Sackmann accuracy ML+MT combined: {ml_mt_combined:.1f}%")
print(f"  Polymarket consensus accuracy (Sim_1): {sim_acc:.1f}%")
print()
if sim_acc > ml_mt_combined + 5:
    print(
        f"  ✅ Consensus accuracy {sim_acc:.1f}% > Sackmann {ml_mt_combined:.1f}% (+{sim_acc-ml_mt_combined:.0f}%)"
    )
    print(f"  KARAR: Odds API yönüne git mantıklı (Polymarket konsensüsü daha doğru)")
elif sim_acc < ml_mt_combined - 5:
    print(
        f"  ⚠️ Sackmann {ml_mt_combined:.1f}% > Consensus {sim_acc:.1f}% (-{ml_mt_combined-sim_acc:.0f}%)"
    )
    print(f"  KARAR: Sackmann silme — moneyline + match_total'da daha doğru")
else:
    print(
        f"  ⚪ Yakin doğruluk: Sackmann {ml_mt_combined:.1f}% vs Consensus {sim_acc:.1f}%"
    )
    print(f"  KARAR: Karışık — daha fazla data gerek")
