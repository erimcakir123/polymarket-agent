"""Tennis +$708 sampyon donem icin tam Polymarket dogrulama.

Her trade icin:
- Model dogru tarafa mi girdi? (resolution'a gore)
- Bot dogru zamanda mi cikti? (resolution'la karsilastirma)
- cina-de-jong gibi "dogru ama SL yedi" var mi?
- Buyuk kazanclar nasil olustu? (resolved tam payout)
"""
import json
import httpx
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")


def fetch_resolved(token_id):
    try:
        r = httpx.get(
            "https://gamma-api.polymarket.com/markets",
            params={"clob_token_ids": token_id, "closed": "true"},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            # Try without closed filter
            r2 = httpx.get(
                "https://gamma-api.polymarket.com/markets",
                params={"clob_token_ids": token_id},
                timeout=10,
            )
            if r2.status_code != 200 or not r2.json():
                return None
            data = r2.json()
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
    except Exception as e:
        return {"error": str(e)}


# +$708 archive
arch = r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/logs/audit/trade_history.archive.20260526_172100.jsonl"
recs = [json.loads(l) for l in open(arch, encoding="utf-8") if l.strip()]
closed = [r for r in recs if r.get("exit_reason")]
print(f"Toplam audit: {len(recs)}, kapanmis: {len(closed)}\n")

# Kategoriler
stats = {
    "model_correct_exit_right": 0,
    "model_correct_exit_early": 0,  # cina-de-jong tipi
    "model_correct_exit_late": 0,
    "model_wrong": 0,
    "unresolved": 0,
    "no_info": 0,
}
details = []

for i, r in enumerate(closed):
    if i % 10 == 0:
        print(f"  {i}/{len(closed)} kontrol edildi...")
    slug = r["slug"]
    direction = r.get("direction", "-")
    entry = r["entry_price"]
    exit_p = r.get("exit_price", 0)
    pnl = r["exit_pnl_usdc"]
    tid = r.get("token_id", "")
    reason = r["exit_reason"]
    if not tid:
        stats["no_info"] += 1
        continue

    info = fetch_resolved(tid)
    if info is None or "error" in (info or {}):
        stats["no_info"] += 1
        details.append((r, "API hata"))
        continue
    if not info.get("closed"):
        stats["unresolved"] += 1
        details.append((r, "Resolved degil"))
        continue

    prices = info["prices"]
    outs = info["outcomes"]
    token_ids = info["token_ids"]
    if not prices or not token_ids:
        stats["no_info"] += 1
        continue

    # Bot'un sahip oldugu outcome
    try:
        bot_idx = token_ids.index(str(tid)) if str(tid) in token_ids else token_ids.index(tid)
    except (ValueError, IndexError):
        bot_idx = 0
    bot_outcome_price = prices[bot_idx] if bot_idx < len(prices) else 0
    # bot_outcome_price = 1 ise bot dogru tarafta (kazandi)
    # bot_outcome_price = 0 ise bot yanlis tarafta (kaybetti)

    if bot_outcome_price > 0.5:
        # Bot dogru tarafta
        if pnl > 0:
            # Bot kazandi
            stats["model_correct_exit_right"] += 1
            category = "MODEL DOGRU + EXIT IYI (+$)"
        else:
            # Bot dogru tarafta ama PnL negatif - erken cikti! (cina tipi)
            stats["model_correct_exit_early"] += 1
            category = f"!!! MODEL DOGRU AMA SL/ERKEN CIKIS (-$) — exit={exit_p:.3f} resolved=1.0"
    else:
        # Bot yanlis tarafta
        stats["model_wrong"] += 1
        category = "Model yanlis tarafta (-$)"

    details.append((r, category))

print(f"\n{'='*80}\nSONUC OZETI (+$708 donemi, {len(closed)} trade)\n{'='*80}")
total = sum(stats.values())
for k, v in stats.items():
    pct = v / total * 100 if total else 0
    print(f"  {k:<35} {v:3d} ({pct:.0f}%)")

# !!! KRITIK: model dogru ama erken cikti
print(f"\n{'='*80}\n!!! 'MODEL DOGRU AMA ERKEN CIKIS' VAKLARI (cina-de-jong tipi)\n{'='*80}")
critical = [(r, c) for r, c in details if "DOGRU AMA SL" in c]
for r, c in critical[:15]:
    print(f"  {r['slug'][:55]} dir={r['direction']} entry={r['entry_price']:.3f} exit={r.get('exit_price',0):.3f} pnl=${r['exit_pnl_usdc']:+.2f} {r['exit_reason']}")
print(f"\nToplam: {len(critical)} adet")

# Net hesap: bu vakalar gerceklesmeseydi
missed_gain = 0
for r, c in critical:
    if "DOGRU AMA SL" in c:
        # Bot'un tuttugu outcome = 1.0 -> resolution payout = $size
        # Bot'un realize ettigi: size_usdc + pnl (negatif)
        # Olabilecek: size_usdc * (1.0 / entry_price) - size_usdc
        size = r["size_usdc"]
        entry = r["entry_price"]
        actual_pnl = r["exit_pnl_usdc"]
        could_have_been = size * (1.0 / entry) - size  # tam resolved payout
        missed = could_have_been - actual_pnl
        missed_gain += missed
print(f"\nKACIRILAN POTANSIYEL KAZANC: ${missed_gain:.2f}")

# En buyuk kazanclar nasil oldu?
print(f"\n{'='*80}\nEN BUYUK 10 KAZANC — nasil ortaya cikti?\n{'='*80}")
wins = sorted([(r, c) for r, c in details if r["exit_pnl_usdc"] > 0], key=lambda x: -x[0]["exit_pnl_usdc"])[:10]
for r, c in wins:
    print(f"  ${r['exit_pnl_usdc']:+7.2f} {r['slug'][:50]} {r['direction']} ({r['entry_price']:.3f}->{r.get('exit_price',0):.3f}) {r['exit_reason']:<20} {c[:60]}")

# Genel: kac trade fully resolved'a kadar tutuldu vs erken cikis
print(f"\n{'='*80}\nEXIT TIMING\n{'='*80}")
print(f"  Total: {len(closed)}")
print(f"  'resolved' exit (mac sonu, full payout):   {sum(1 for r in closed if r['exit_reason']=='resolved')}")
print(f"  'near_resolve' exit (mac biti yakin):       {sum(1 for r in closed if r['exit_reason']=='near_resolve')}")
print(f"  'graduated_sl' exit (asamali SL):           {sum(1 for r in closed if r['exit_reason']=='graduated_sl')}")
print(f"  'stop_loss' exit (flat SL):                 {sum(1 for r in closed if r['exit_reason']=='stop_loss')}")
print(f"  'wipe_archived' (manuel):                   {sum(1 for r in closed if r['exit_reason']=='wipe_archived')}")
