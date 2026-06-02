"""TAM doğruluk analizi — 4 kategori, hiç tahmin yok.

1. RESOLUTION_WIN  : Bot tarafi resolution'da kazandi, bot kar etti (REAL MODEL DOGRU)
2. SPIKE_CATCH     : Bot tarafi resolution'da KAYBETTİ ama bot spike'ta cikti, KAR (sans)
3. EARLY_EXIT_WIN  : Bot tarafi resolution'da kazandi, bot erken cikti, KAR (model dogru)
4. EARLY_EXIT_LOSS : Bot tarafi resolution'da kazandi, bot SL'ye yedi, KAYIP (cina-tipi tragedi)
5. TRUE_LOSS       : Bot tarafi resolution'da kaybetti, bot zarar (REAL MODEL YANLIS)
6. UNRESOLVED      : Resolution bilinmiyor
"""
import json
import httpx
import sys

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
            if r2.status_code != 200 or not r2.json():
                return None
            data = r2.json()
        else:
            data = r.json()
        m = data[0] if isinstance(data, list) else data
        outs = (
            json.loads(m["outcomes"])
            if isinstance(m.get("outcomes"), str)
            else m.get("outcomes", [])
        )
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
            "closed": m.get("closed"),
            "uma": m.get("umaResolutionStatus"),
            "outcomes": outs,
            "prices": [float(p) for p in prices],
            "token_ids": token_ids,
        }
    except Exception:
        return None


def classify(r, info):
    """Bot tarafı resolution'da kazandi mı + bot kar etti mi?"""
    if info is None or not info.get("closed"):
        return "UNRESOLVED", None, None
    prices = info["prices"]
    token_ids = info["token_ids"]
    tid = r.get("token_id", "")
    if not prices or not token_ids:
        return "UNRESOLVED", None, None

    # Bot'un sahip olduğu outcome'un resolution fiyatı
    try:
        bot_idx = token_ids.index(str(tid)) if str(tid) in token_ids else 0
    except (ValueError, IndexError):
        bot_idx = 0

    bot_resolution = prices[bot_idx] if bot_idx < len(prices) else 0
    bot_won_resolution = bot_resolution > 0.5
    bot_profit = r.get("exit_pnl_usdc", 0)
    bot_made_money = bot_profit > 0

    if bot_won_resolution and bot_made_money:
        return "RESOLUTION_WIN", bot_resolution, bot_profit
    if bot_won_resolution and not bot_made_money:
        return "EARLY_EXIT_LOSS", bot_resolution, bot_profit  # cina-tipi
    if not bot_won_resolution and bot_made_money:
        return "SPIKE_CATCH", bot_resolution, bot_profit  # şans
    if not bot_won_resolution and not bot_made_money:
        return "TRUE_LOSS", bot_resolution, bot_profit
    return "?", bot_resolution, bot_profit


def analyze(path, label):
    print(f"\n{'#'*78}\n# {label}\n{'#'*78}")
    try:
        recs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    except FileNotFoundError:
        print("(dosya yok)")
        return
    closed = [r for r in recs if r.get("exit_reason")]
    if not closed:
        print("Kapanmis trade yok")
        return

    categories = {
        "RESOLUTION_WIN": [],
        "EARLY_EXIT_LOSS": [],
        "SPIKE_CATCH": [],
        "TRUE_LOSS": [],
        "UNRESOLVED": [],
    }
    for i, r in enumerate(closed):
        if i % 20 == 0:
            print(f"  {i}/{len(closed)} kontrol edildi...")
        tid = r.get("token_id", "")
        info = fetch_resolved(tid) if tid else None
        cat, bot_res, profit = classify(r, info)
        categories[cat].append((r, bot_res))

    print(f"\nTOPLAM {len(closed)} kapanmis trade analiz edildi\n")
    print(f"{'Kategori':<22} {'Sayi':<5} {'Net PnL':<12} {'Aciklama'}")
    print("-" * 78)
    total_pnl = 0
    for cat in ["RESOLUTION_WIN", "EARLY_EXIT_LOSS", "SPIKE_CATCH", "TRUE_LOSS", "UNRESOLVED"]:
        items = categories[cat]
        if not items:
            continue
        net = sum(it[0]["exit_pnl_usdc"] for it in items)
        total_pnl += net
        desc = {
            "RESOLUTION_WIN": "Model DOGRU, kar (REAL WIN)",
            "EARLY_EXIT_LOSS": "Model DOGRU AMA SL/ERKEN CIKIS (cina-tipi)",
            "SPIKE_CATCH": "Model YANLIS ama spike'tan kar (sans)",
            "TRUE_LOSS": "Model YANLIS, kayip (REAL LOSS)",
            "UNRESOLVED": "Resolution belirsiz",
        }[cat]
        print(f"  {cat:<22} {len(items):<5} ${net:+10.2f}   {desc}")
    print(f"  {'TOPLAM':<22} {len(closed):<5} ${total_pnl:+10.2f}")

    # GERÇEK MODEL DOĞRULUK ORANI (resolution'a göre)
    real_correct = len(categories["RESOLUTION_WIN"]) + len(categories["EARLY_EXIT_LOSS"])
    real_wrong = len(categories["SPIKE_CATCH"]) + len(categories["TRUE_LOSS"])
    resolved_total = real_correct + real_wrong
    if resolved_total:
        print(f"\n## GERCEK MODEL DOGRULUK (resolution'a gore)")
        print(f"  Bot tarafi kazanan resolution: {real_correct}/{resolved_total} = {real_correct/resolved_total:.1%}")
        print(f"  Bot tarafi kaybeden resolution: {real_wrong}/{resolved_total} = {real_wrong/resolved_total:.1%}")

    # KAR KAYNAGI ANALIZI
    print(f"\n## KAR KAYNAGI ANALIZI")
    rw_pnl = sum(r["exit_pnl_usdc"] for r, _ in categories["RESOLUTION_WIN"])
    sc_pnl = sum(r["exit_pnl_usdc"] for r, _ in categories["SPIKE_CATCH"])
    ee_pnl = sum(r["exit_pnl_usdc"] for r, _ in categories["EARLY_EXIT_LOSS"])
    tl_pnl = sum(r["exit_pnl_usdc"] for r, _ in categories["TRUE_LOSS"])
    total_wins = rw_pnl + sc_pnl
    total_losses = ee_pnl + tl_pnl
    print(f"  Resolution kazanci (REAL):  ${rw_pnl:+.2f}")
    print(f"  Spike kazanci (SANS):       ${sc_pnl:+.2f}")
    print(f"  Toplam kazanc:              ${total_wins:+.2f}")
    print(f"  Cina-tipi kayip (HAKLI):    ${ee_pnl:+.2f}")
    print(f"  True loss (MODEL YANLIS):   ${tl_pnl:+.2f}")
    print(f"  Toplam kayip:               ${total_losses:+.2f}")
    print(f"  NET:                        ${rw_pnl+sc_pnl+ee_pnl+tl_pnl:+.2f}")

    # Spike catch detayları
    if categories["SPIKE_CATCH"]:
        print(f"\n## SPIKE CATCH detayları (model yanlis ama bot kazandi)")
        for r, br in sorted(categories["SPIKE_CATCH"], key=lambda x: -x[0]["exit_pnl_usdc"])[:10]:
            slug = r["slug"][:50]
            print(f"  ${r['exit_pnl_usdc']:+7.2f} {slug} {r['direction']} entry={r['entry_price']:.3f} exit={r.get('exit_price',0):.3f} bot_res={br:.2f} {r['exit_reason']}")

    # True loss detayları
    if categories["TRUE_LOSS"]:
        print(f"\n## TRUE_LOSS en buyuk 10 (model yanlis + bot kaybetti)")
        for r, br in sorted(categories["TRUE_LOSS"], key=lambda x: x[0]["exit_pnl_usdc"])[:10]:
            slug = r["slug"][:50]
            print(f"  ${r['exit_pnl_usdc']:+7.2f} {slug} {r['direction']} entry={r['entry_price']:.3f} exit={r.get('exit_price',0):.3f} bot_res={br:.2f} {r['exit_reason']}")


analyze(
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.archive.20260526_172100.jsonl",
    "DONEM A: +$708 ŞAMPİYON (24-26 May, 83 trade)",
)
analyze(
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.archive.20260527_130608.jsonl",
    "DONEM D: -$102 ÖNCEKİ REBOOT (26-27 May, 6 trade)",
)
analyze(
    r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.jsonl",
    "DONEM E: -$41 CANLI (27 May, 6 trade)",
)
