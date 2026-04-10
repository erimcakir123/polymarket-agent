"""One-shot analysis for user questions:
Q1: Was the AI layer additive vs pure Odds-API decisions today?
Q2: What would PnL look like if exits were disabled and held to ~end-of-match?
Q3: Per-sport breakdown of both above.

Read-only. No side effects. Pure analytics.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path("logs")
TRADES = ROOT / "trades.jsonl"
PRICE_HIST_DIR = ROOT / "price_history"
TODAY = "2026-04-10"

ENTRY_ACTIONS = {"BUY", "UPSET_ENTRY"}
FORCED_REASONS = {
    "match_exit_a_conf_market_flip",
    "match_exit_catastrophic_floor",
    "match_exit_graduated_sl",
    "match_exit_upset_max_hold",
    "stop_loss",
}

# =============================================================================
# Load today's entries + exits
# =============================================================================
entries: dict[str, dict] = {}
exits_by_slug: dict[str, list] = defaultdict(list)
scale_outs_by_slug: dict[str, list] = defaultdict(list)

with open(TRADES, encoding="utf-8") as f:
    for line in f:
        try:
            e = json.loads(line)
        except Exception:
            continue
        ts = e.get("timestamp", "")
        if not ts.startswith(TODAY):
            continue
        act = e.get("action")
        slug = e.get("market")
        if not slug:
            continue
        if act in ENTRY_ACTIONS:
            entries[slug] = e
        elif act == "EXIT":
            exits_by_slug[slug].append(e)
        elif act == "SCALE_OUT":
            scale_outs_by_slug[slug].append(e)

print(f"Entries today (BUY + UPSET_ENTRY): {len(entries)}")
print(f"EXIT events: {sum(len(v) for v in exits_by_slug.values())}")
print(f"SCALE_OUT events: {sum(len(v) for v in scale_outs_by_slug.values())}")
print(f"Total closure events: {sum(len(v) for v in exits_by_slug.values()) + sum(len(v) for v in scale_outs_by_slug.values())}")
print()

# =============================================================================
# Helpers
# =============================================================================
def dir_edge(model_prob: float, entry_price: float, direction: str) -> float:
    if direction == "BUY_YES":
        return model_prob - entry_price
    return entry_price - model_prob

def net_pnl(slug: str) -> float:
    total = 0.0
    for ex in exits_by_slug.get(slug, []):
        total += ex.get("total_pnl", ex.get("pnl", 0.0)) or 0.0
    if slug not in exits_by_slug:
        for so in scale_outs_by_slug.get(slug, []):
            total += so.get("realized_pnl", 0.0) or 0.0
    return total

def sport_family(tag: str, slug: str = "") -> str:
    # Combine tag + slug for better detection
    s = (tag or "").lower() + " " + (slug or "").lower()
    if not s.strip():
        return "unknown"
    if "nba" in s: return "NBA"
    if "nhl" in s: return "NHL"
    if "mlb" in s: return "MLB"
    if "atp" in s: return "ATP"
    if "wta" in s: return "WTA"
    if "boxing" in s: return "Boxing"
    if "mma" in s or "ufc" in s: return "MMA"
    if "euroleague" in s: return "EuroLeague"
    if "cricket" in s or "-ipl-" in s: return "Cricket"
    if "chess" in s: return "Chess"
    # Soccer leagues (country/league codes used in slugs)
    soccer_tags = [
        "sud","lib","aus","fl1","fl2","fr1","fr2","ligue","bl1","bl2","bun",
        "elc","epl","ere","sea","tur","den","ita","esp","por","ned","mls",
        "serie","la-liga","premier","primera","a-league","bundes","eredivisie",
        "bas-","bra-","arg-","chi-","col-","uru-","per-"
    ]
    if any(x in s for x in soccer_tags): return "Soccer"
    return tag or "unknown"

# =============================================================================
# Rows with sport tagging
# =============================================================================
rows = []
for slug, b in entries.items():
    entry_price = b.get("entry_price")
    direction = b.get("direction", "")
    ai_prob = b.get("ai_prob")
    bm_prob = b.get("bookmaker_prob")
    size = b.get("size_usdc", 0.0)
    conf = b.get("confidence", "")
    sport_raw = b.get("sport_tag", "") or ""
    sport = sport_family(sport_raw, slug)
    if entry_price is None:
        continue
    ai_edge = dir_edge(ai_prob, entry_price, direction) if ai_prob is not None else None
    bm_edge = dir_edge(bm_prob, entry_price, direction) if (bm_prob not in (None, 0, 0.0)) else None
    pnl = net_pnl(slug)
    rows.append({
        "slug": slug, "dir": direction, "conf": conf,
        "entry": entry_price, "ai_prob": ai_prob, "bm_prob": bm_prob,
        "ai_edge": ai_edge, "bm_edge": bm_edge, "size": size, "pnl": pnl,
        "has_bm": bm_edge is not None, "sport": sport, "sport_raw": sport_raw,
    })

def classify(r):
    ai_ok = r["ai_edge"] is not None and r["ai_edge"] > 0.02
    bm_ok = r["bm_edge"] is not None and r["bm_edge"] > 0.02
    if not r["has_bm"]:
        return "NO_BOOKMAKER"
    if ai_ok and bm_ok: return "CONCORDANT"
    if ai_ok and not bm_ok: return "AI_ONLY"
    if bm_ok and not ai_ok: return "BM_ONLY"
    return "BOTH_WEAK"

# =============================================================================
# Q1: AI vs Odds API — OVERALL + per sport
# =============================================================================
def print_classification(subset: list, title: str):
    cats = defaultdict(lambda: {"count": 0, "size": 0.0, "pnl": 0.0, "wins": 0, "losses": 0})
    for r in subset:
        c = classify(r)
        cats[c]["count"] += 1
        cats[c]["size"] += r["size"]
        cats[c]["pnl"] += r["pnl"]
        if r["pnl"] > 0.01: cats[c]["wins"] += 1
        elif r["pnl"] < -0.01: cats[c]["losses"] += 1
    print(f"\n[{title}]  n={len(subset)}")
    print(f"  {'Category':15s} {'Cnt':>4s} {'Size':>8s} {'PnL':>9s} {'W/L':>7s} {'ROI%':>7s}")
    for name in ["CONCORDANT","AI_ONLY","BM_ONLY","BOTH_WEAK","NO_BOOKMAKER"]:
        if name in cats:
            v = cats[name]
            roi = (v["pnl"]/v["size"]*100) if v["size"] > 0 else 0
            print(f"  {name:15s} {v['count']:4d} {v['size']:8.2f} {v['pnl']:+9.2f} {v['wins']:3d}/{v['losses']:<3d} {roi:+6.2f}%")
    total_pnl = sum(v["pnl"] for v in cats.values())
    total_size = sum(v["size"] for v in cats.values())
    roi_tot = (total_pnl/total_size*100) if total_size > 0 else 0
    print(f"  {'TOTAL':15s} {sum(v['count'] for v in cats.values()):4d} {total_size:8.2f} {total_pnl:+9.2f}  {'':>7s} {roi_tot:+6.2f}%")

print("=" * 88)
print("Q1: AI LAYER vs. ODDS API — classification (OVERALL)")
print("=" * 88)
print("Categories:")
print("  CONCORDANT   = both AI and bookmaker see edge in our direction (>2pts)")
print("  AI_ONLY      = AI sees edge, bookmaker flat/opposite -> AI's unique contribution")
print("  BM_ONLY      = bookmaker sees edge, AI flat           -> Odds-API picked, AI didn't")
print("  BOTH_WEAK    = neither clear edge (entry still triggered -- thin-data path)")
print("  NO_BOOKMAKER = no bookmaker data at all               -> AI was sole decider")
print_classification(rows, "ALL SPORTS")

# Per-sport classification
sports = sorted(set(r["sport"] for r in rows))
print("\n" + "=" * 88)
print("Q1-BRANCH: AI vs Odds — per sport")
print("=" * 88)
for s in sports:
    sub = [r for r in rows if r["sport"] == s]
    print_classification(sub, s)

# Pure-bookmaker counterfactual overall + per sport
print("\n" + "=" * 88)
print("Q1-CF: Pure Odds-API counterfactual (ignore AI, keep bets where bm_edge>2%)")
print("=" * 88)
print(f"{'Sport':12s} {'Pure BM bets':>12s} {'Invested':>10s} {'PnL':>10s} {'ROI%':>7s}  vs  {'Actual PnL':>11s}  {'AI adds':>10s}")
def pure_bm(subset):
    bets = [r for r in subset if r["bm_edge"] is not None and r["bm_edge"] > 0.02]
    pnl = sum(r["pnl"] for r in bets)
    sz = sum(r["size"] for r in bets)
    return len(bets), sz, pnl

nb, ns, np_ = pure_bm(rows)
actual_all = sum(r["pnl"] for r in rows)
print(f"{'ALL':12s} {nb:>12d} {ns:>10.2f} {np_:+10.2f} {(np_/ns*100 if ns else 0):+6.2f}%      {actual_all:+11.2f}  {actual_all - np_:+10.2f}")
for s in sports:
    sub = [r for r in rows if r["sport"] == s]
    nb, ns, np_ = pure_bm(sub)
    act = sum(r["pnl"] for r in sub)
    print(f"{s:12s} {nb:>12d} {ns:>10.2f} {np_:+10.2f} {(np_/ns*100 if ns else 0):+6.2f}%      {act:+11.2f}  {act - np_:+10.2f}")

# =============================================================================
# Q2: Exit-disabled counterfactual (hold to near-end-of-match)
# =============================================================================
print("\n" + "=" * 88)
print("Q2: EXIT-DISABLED counterfactual — hold forced-exit positions to last known price")
print("=" * 88)

hist_files = list(PRICE_HIST_DIR.glob("*.json"))
hist_by_slug: dict[str, list] = {}
for f in hist_files:
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        slug = d.get("slug")
        if slug:
            hist_by_slug.setdefault(slug, []).append(d)
    except Exception:
        pass

def hypo_pnl(direction, entry_px, size, hold_px):
    if direction == "BUY_YES":
        cost_per_share = entry_px
        if cost_per_share <= 0: return None
        shares = size / cost_per_share
        return shares * hold_px - size
    else:
        cost_per_share = 1 - entry_px
        if cost_per_share <= 0: return None
        shares = size / cost_per_share
        return shares * (1 - hold_px) - size

# Build per-sport forced-exit counterfactual
# Need sport per slug → join via entries dict
sport_by_slug = {slug: sport_family(b.get("sport_tag","") or "", slug) for slug, b in entries.items()}
# Also resolve sport for slugs that have exit events but no entry today (entered yesterday)
for slug in list(exits_by_slug.keys()) + list(scale_outs_by_slug.keys()):
    if slug not in sport_by_slug:
        sport_by_slug[slug] = sport_family("", slug)

per_sport_exit = defaultdict(lambda: {
    "forced_cnt": 0, "forced_actual": 0.0, "forced_hypo": 0.0, "missing": 0,
    "near_resolve_cnt": 0, "near_resolve_pnl": 0.0,
    "scale_out_pnl": 0.0, "scale_out_cnt": 0,
})

details = []
for slug, events in exits_by_slug.items():
    sport = sport_by_slug.get(slug, "unknown")
    for ex in events:
        reason = ex.get("reason", "")
        pnl_ex = ex.get("total_pnl", ex.get("pnl", 0.0)) or 0.0
        if reason == "near_resolve_profit":
            per_sport_exit[sport]["near_resolve_cnt"] += 1
            per_sport_exit[sport]["near_resolve_pnl"] += pnl_ex
            continue
        if reason not in FORCED_REASONS:
            continue
        direction = ex.get("direction")
        size = ex.get("size", 0.0)
        entry_px = ex.get("price")
        exit_px = ex.get("exit_price")
        per_sport_exit[sport]["forced_cnt"] += 1
        per_sport_exit[sport]["forced_actual"] += pnl_ex
        hists = hist_by_slug.get(slug, [])
        if not hists or not hists[0].get("price_history"):
            # No history → assume we'd get same as actual (conservative)
            per_sport_exit[sport]["forced_hypo"] += pnl_ex
            per_sport_exit[sport]["missing"] += 1
            continue
        hist = max(hists, key=lambda h: h.get("saved_at", ""))
        points = hist.get("price_history", [])
        if not points:
            per_sport_exit[sport]["forced_hypo"] += pnl_ex
            per_sport_exit[sport]["missing"] += 1
            continue
        hold_px = points[-1].get("p", exit_px)
        hp = hypo_pnl(direction, entry_px, size, hold_px)
        if hp is None:
            per_sport_exit[sport]["forced_hypo"] += pnl_ex
            per_sport_exit[sport]["missing"] += 1
            continue
        per_sport_exit[sport]["forced_hypo"] += hp
        details.append((sport, slug, reason, direction, entry_px, exit_px, hold_px, pnl_ex, hp))

# Scale-outs per sport
for slug, sos in scale_outs_by_slug.items():
    sport = sport_by_slug.get(slug, "unknown")
    for so in sos:
        # Only count scale-out as standalone if no EXIT captured its sibling
        # We want to report scale_out realized_pnl separately for transparency
        per_sport_exit[sport]["scale_out_cnt"] += 1
        per_sport_exit[sport]["scale_out_pnl"] += so.get("realized_pnl", 0.0) or 0.0

print(f"\n{'Sport':12s} {'FrcCnt':>6s} {'FrcAct':>9s} {'FrcHypo':>10s} {'Δ(save)':>10s} {'NearRes':>9s} {'NR PnL':>9s} {'TotalActual':>12s} {'TotalHypo':>11s}")
total_actual = 0.0
total_hypo = 0.0
for sport in sorted(per_sport_exit.keys()):
    v = per_sport_exit[sport]
    act_tot = v["forced_actual"] + v["near_resolve_pnl"]
    hypo_tot = v["forced_hypo"] + v["near_resolve_pnl"]
    diff = v["forced_hypo"] - v["forced_actual"]
    total_actual += act_tot
    total_hypo += hypo_tot
    print(f"{sport:12s} {v['forced_cnt']:>6d} {v['forced_actual']:+9.2f} {v['forced_hypo']:+10.2f} {diff:+10.2f} {v['near_resolve_cnt']:>9d} {v['near_resolve_pnl']:+9.2f} {act_tot:+12.2f} {hypo_tot:+11.2f}")
print("-" * 100)
print(f"{'TOTAL':12s} {'':>6s} {'':>9s} {'':>10s} {total_hypo-total_actual:+10.2f} {'':>9s} {'':>9s} {total_actual:+12.2f} {total_hypo:+11.2f}")

# =============================================================================
# Per-sport NET (enter → all closure events)
# =============================================================================
print("\n" + "=" * 88)
print("PER-SPORT net PnL (all closure events — EXIT + SCALE_OUT)")
print("=" * 88)
per_sport_net = defaultdict(lambda: {"pnl": 0.0, "cnt": 0})
for slug, events in exits_by_slug.items():
    sport = sport_by_slug.get(slug, "unknown")
    for ex in events:
        per_sport_net[sport]["pnl"] += ex.get("total_pnl", ex.get("pnl", 0.0)) or 0.0
        per_sport_net[sport]["cnt"] += 1
for slug, sos in scale_outs_by_slug.items():
    sport = sport_by_slug.get(slug, "unknown")
    if slug not in exits_by_slug:  # avoid double count — exit.total_pnl includes scale_out_pnl for its own slice
        for so in sos:
            per_sport_net[sport]["pnl"] += so.get("realized_pnl", 0.0) or 0.0
            per_sport_net[sport]["cnt"] += 1

print(f"{'Sport':12s} {'Closures':>10s} {'Net PnL':>10s}")
grand = 0.0
for s in sorted(per_sport_net.keys(), key=lambda x: per_sport_net[x]["pnl"]):
    v = per_sport_net[s]
    grand += v["pnl"]
    print(f"{s:12s} {v['cnt']:>10d} {v['pnl']:+10.2f}")
print(f"{'GRAND':12s} {sum(v['cnt'] for v in per_sport_net.values()):>10d} {grand:+10.2f}")

# =============================================================================
# All forced-exit detail
# =============================================================================
print("\n" + "=" * 88)
print("DETAIL: all forced exits (sorted by Δ hold-vs-actual, biggest savings first)")
print("=" * 88)
print(f"{'sport':10s} {'slug':38s} {'reason':18s} {'dir':7s} {'ent':>5s} {'exit':>5s} {'hold':>5s} {'actual':>8s} {'hypo':>8s}")
for d in sorted(details, key=lambda x: x[8]-x[7], reverse=True):
    sp, slug, rs, dr, ep, xp, hp, ap, yp = d
    rs_s = rs.replace("match_exit_", "m_")[:18]
    print(f"{sp:10s} {slug[:38]:38s} {rs_s:18s} {dr:7s} {ep:5.2f} {xp:5.2f} {hp:5.2f} {ap:+8.2f} {yp:+8.2f}")
