"""Tennis model kalite analizi — 88 trade + 6 trade = 94 trade.

Sadece sample boyutunda anlamlı.
Resolution'a göre model doğruluk + confidence + market_type kırılımı.
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


def tour(slug):
    return slug.split("-")[0] if "-" in slug else "?"


def analyze(paths, label):
    print(f"\n{'#'*78}\n# {label}\n{'#'*78}")
    all_recs = []
    for p in paths:
        try:
            for l in open(p, encoding="utf-8"):
                if l.strip():
                    all_recs.append(json.loads(l))
        except FileNotFoundError:
            pass

    closed = [r for r in all_recs if r.get("exit_reason") and r.get("exit_reason") != "wipe_archived"]
    print(f"Toplam audit: {len(all_recs)}, kapanmis (wipe haric): {len(closed)}")

    # Token başına resolution çek
    print("Polymarket resolution çekiliyor...", file=sys.stderr)
    for i, r in enumerate(closed):
        if i % 20 == 0:
            print(f"  {i}/{len(closed)}", file=sys.stderr)
        info = fetch_resolved(r.get("token_id", ""))
        if info is None or not info["prices"]:
            r["_model_correct"] = None
            r["_bot_res"] = None
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
        r["_model_correct"] = bot_res > 0.5  # Bot'un sahip olduğu outcome kazandı mı
        r["_bot_res"] = bot_res

    resolved = [r for r in closed if r.get("_model_correct") is not None]
    n_correct = sum(1 for r in resolved if r["_model_correct"])
    print(f"Resolution alınabilen: {len(resolved)}")
    print(
        f"\n## GENEL MODEL DOĞRULUK (resolution'a göre)"
    )
    print(f"  Bot dogru tarafa girdi: {n_correct}/{len(resolved)} = {n_correct/len(resolved)*100:.1f}%")
    print(f"  Bot yanlis tarafa girdi: {len(resolved)-n_correct}/{len(resolved)} = {(len(resolved)-n_correct)/len(resolved)*100:.1f}%")

    # Confidence kirilimi
    print("\n## CONFIDENCE KIRILIMI (model doğruluk = bot tarafı resolution'da kazandı mı)")
    print(f"  {'Conf':<6} {'Total':<7} {'Doğru':<7} {'Yanlış':<7} {'Doğruluk':<10} {'Net PnL':<12} {'Avg PnL'}")
    print("  " + "-" * 75)
    for conf in ["A", "B", "C"]:
        items = [r for r in resolved if r.get("confidence") == conf]
        if not items:
            continue
        correct = sum(1 for r in items if r["_model_correct"])
        n = len(items)
        net = sum(r["exit_pnl_usdc"] for r in items)
        avg = net / n
        acc = correct / n * 100
        print(
            f"  {conf:<6} {n:<7} {correct:<7} {n-correct:<7} {acc:<10.1f} ${net:+10.2f}  ${avg:+.2f}"
        )

    # Market type kirilimi
    print("\n## MARKET TIPI KIRILIMI")
    print(f"  {'Market':<22} {'Total':<7} {'Doğru':<7} {'Doğruluk':<10} {'Net PnL':<12} {'Avg PnL'}")
    print("  " + "-" * 75)
    mt_groups = defaultdict(list)
    for r in resolved:
        mt_groups[market_type(r["slug"])].append(r)
    for mt, items in sorted(mt_groups.items(), key=lambda x: -len(x[1])):
        correct = sum(1 for r in items if r["_model_correct"])
        n = len(items)
        net = sum(r["exit_pnl_usdc"] for r in items)
        acc = correct / n * 100
        print(
            f"  {mt:<22} {n:<7} {correct:<7} {acc:<10.1f} ${net:+10.2f}  ${net/n:+.2f}"
        )

    # Tour kirilimi (ATP vs WTA)
    print("\n## TUR KIRILIMI")
    print(f"  {'Tour':<6} {'Total':<7} {'Doğru':<7} {'Doğruluk':<10} {'Net PnL':<12} {'Avg PnL'}")
    print("  " + "-" * 75)
    tour_groups = defaultdict(list)
    for r in resolved:
        tour_groups[tour(r["slug"])].append(r)
    for t, items in sorted(tour_groups.items(), key=lambda x: -len(x[1])):
        correct = sum(1 for r in items if r["_model_correct"])
        n = len(items)
        net = sum(r["exit_pnl_usdc"] for r in items)
        acc = correct / n * 100
        print(
            f"  {t:<6} {n:<7} {correct:<7} {acc:<10.1f} ${net:+10.2f}  ${net/n:+.2f}"
        )

    # Confidence + Market_type combo
    print("\n## CONFIDENCE × MARKET_TYPE COMBOS (min 3 trade)")
    print(f"  {'Combo':<35} {'N':<5} {'Doğru':<7} {'Doğruluk':<10} {'Net':<10} {'Avg'}")
    print("  " + "-" * 80)
    combo_groups = defaultdict(list)
    for r in resolved:
        key = f"{r.get('confidence','-')} / {market_type(r['slug'])}"
        combo_groups[key].append(r)
    for k, items in sorted(combo_groups.items(), key=lambda x: -sum(r['exit_pnl_usdc'] for r in x[1])):
        if len(items) < 3:
            continue
        correct = sum(1 for r in items if r["_model_correct"])
        n = len(items)
        net = sum(r["exit_pnl_usdc"] for r in items)
        acc = correct / n * 100
        marker = " ✅" if net > 0 else " ❌"
        print(
            f"  {k:<35} {n:<5} {correct:<7} {acc:<10.1f} ${net:+10.2f}  ${net/n:+.2f}{marker}"
        )


# 88 trade (champion) + 6 trade (önceki reboot) + 6 trade (current) = 100 trade
paths = [
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.archive.20260526_172100.jsonl",
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.archive.20260527_130608.jsonl",
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.jsonl",
]
analyze(paths, "TÜM TENNIS-LAB TARİHİ (88 + 6 + 6 = 100 trade, 5 günlük tüm dönem)")
