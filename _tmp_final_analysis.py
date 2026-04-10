"""FINAL analysis using match_outcomes.jsonl (ground truth) + trades.jsonl

Q1: Is the AI layer additive vs pure Odds API?
Q2: What would PnL look like if exits disabled and held to RESOLUTION?
Q3: Per-sport breakdown.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path("logs")
TRADES = ROOT / "trades.jsonl"
OUTCOMES = ROOT / "match_outcomes.jsonl"
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
# Load entries, exits, and ALL trade history for prior entries
# =============================================================================
entries_all: dict[str, dict] = {}    # slug -> entry event (any day)
exits_today: dict[str, list] = defaultdict(list)
scale_outs_today: dict[str, list] = defaultdict(list)

with open(TRADES, encoding="utf-8") as f:
    for line in f:
        try:
            e = json.loads(line)
        except Exception:
            continue
        act = e.get("action")
        slug = e.get("market")
        if not slug:
            continue
        if act in ENTRY_ACTIONS:
            entries_all[slug] = e  # keep latest entry per slug
        ts = e.get("timestamp", "")
        if not ts.startswith(TODAY):
            continue
        if act == "EXIT":
            exits_today[slug].append(e)
        elif act == "SCALE_OUT":
            scale_outs_today[slug].append(e)

# Also include trade_archive (older entries not in trades.jsonl tail)
ARCHIVE = ROOT / "trade_archive.jsonl"
if ARCHIVE.exists():
    with open(ARCHIVE, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            slug = d.get("slug")
            if slug and slug not in entries_all:
                # Mimic BUY event shape
                entries_all[slug] = {
                    "market": slug,
                    "direction": d.get("direction"),
                    "entry_price": d.get("entry_price"),
                    "size_usdc": d.get("size"),
                    "ai_prob": d.get("ai_probability"),
                    "bookmaker_prob": d.get("bookmaker_prob"),
                    "sport_tag": d.get("sport_tag", ""),
                    "confidence": d.get("confidence", ""),
                }

# Resolved outcomes
resolved: dict[str, dict] = {}
with open(OUTCOMES, encoding="utf-8") as f:
    for line in f:
        try:
            d = json.loads(line)
        except Exception:
            continue
        slug = d.get("slug")
        if slug:
            resolved[slug] = d

today_closures = len(set(list(exits_today.keys()) + list(scale_outs_today.keys())))
today_exit_events = sum(len(v) for v in exits_today.values()) + sum(len(v) for v in scale_outs_today.values())

print(f"Today's closure events (EXIT + SCALE_OUT): {today_exit_events}")
print(f"Today's unique closed slugs:               {today_closures}")
print(f"Resolved (yes_won known):                  {len(resolved)}")
print()

# =============================================================================
# Helpers
# =============================================================================
def sport_family(tag: str, slug: str = "") -> str:
    s = (tag or "").lower() + " " + (slug or "").lower()
    if "nba" in s: return "NBA"
    if "nhl" in s: return "NHL"
    if "mlb" in s: return "MLB"
    if "atp" in s: return "ATP"
    if "wta" in s: return "WTA"
    if "boxing" in s: return "Boxing"
    if "mma" in s or "ufc" in s: return "MMA"
    if "euroleague" in s: return "EuroLeague"
    soccer_tags = ["sud","lib","aus","fl1","fl2","fr1","fr2","ligue","bl1","bl2","bun",
                   "elc","epl","ere","sea","tur","den","ita","esp","por","ned","mls",
                   "serie","la-liga","premier","primera","a-league","bundes","eredivisie"]
    if any(x in s for x in soccer_tags): return "Soccer"
    return "other"

def dir_edge(model_prob, entry_price, direction):
    if direction == "BUY_YES":
        return model_prob - entry_price
    return entry_price - model_prob

def hold_to_resolution_pnl(direction: str, entry_price: float, size: float, yes_won: bool) -> float:
    """Payout if held to full resolution."""
    if direction == "BUY_YES":
        cost_per_share = entry_price
        if cost_per_share <= 0:
            return 0.0
        shares = size / cost_per_share
        return (shares * (1.0 if yes_won else 0.0)) - size
    # BUY_NO
    cost_per_share = 1.0 - entry_price
    if cost_per_share <= 0:
        return 0.0
    shares = size / cost_per_share
    return (shares * (0.0 if yes_won else 1.0)) - size

def net_pnl_today(slug: str) -> float:
    total = 0.0
    for ex in exits_today.get(slug, []):
        total += ex.get("total_pnl", ex.get("pnl", 0.0)) or 0.0
    if slug not in exits_today:
        for so in scale_outs_today.get(slug, []):
            total += so.get("realized_pnl", 0.0) or 0.0
    return total

# =============================================================================
# Q2: HOLD-TO-RESOLUTION counterfactual (20 resolved trades)
# =============================================================================
print("=" * 100)
print("Q2: HOLD-TO-RESOLUTION counterfactual — 20 resolved markets (ground truth)")
print("=" * 100)

by_reason = defaultdict(lambda: {"cnt": 0, "actual": 0.0, "hypo": 0.0})
by_sport  = defaultdict(lambda: {"cnt": 0, "actual": 0.0, "hypo": 0.0})
details = []

for slug, out in resolved.items():
    # Get actual pnl from today's exit events + scale_outs (across multiple exits for same slug)
    actual = net_pnl_today(slug)
    # Fallback: if no exit in trades today (pre-today exit archived), use outcome's own pnl
    if actual == 0.0 and slug not in exits_today and slug not in scale_outs_today:
        actual = out.get("pnl", 0.0) or 0.0

    direction = out.get("direction")
    # Use ORIGINAL entry price from entries_all (not the exit-time "price" field)
    entry_rec = entries_all.get(slug, {})
    entry_price = entry_rec.get("entry_price") or out.get("entry_price")
    size = entry_rec.get("size_usdc") or out.get("size", 0.0)
    yes_won = out.get("yes_won")

    if entry_price is None or yes_won is None:
        continue

    hypo = hold_to_resolution_pnl(direction, entry_price, size, bool(yes_won))
    reason = out.get("exit_reason", "unknown").replace("post_exit_", "")
    sport = sport_family(out.get("sport_tag", "") or entry_rec.get("sport_tag", "") or "", slug)

    by_reason[reason]["cnt"] += 1
    by_reason[reason]["actual"] += actual
    by_reason[reason]["hypo"] += hypo
    by_sport[sport]["cnt"] += 1
    by_sport[sport]["actual"] += actual
    by_sport[sport]["hypo"] += hypo

    details.append({
        "slug": slug, "sport": sport, "reason": reason, "dir": direction,
        "entry": entry_price, "size": size, "yes_won": yes_won,
        "actual": actual, "hypo": hypo, "diff": hypo - actual,
    })

print("\nBY EXIT REASON:")
print(f"  {'reason':38s}  {'cnt':>3s}  {'actual':>9s}  {'hold2resolve':>14s}  {'Δ':>9s}")
tot_act = tot_hyp = 0
for r in sorted(by_reason.keys()):
    v = by_reason[r]
    tot_act += v["actual"]; tot_hyp += v["hypo"]
    diff = v["hypo"] - v["actual"]
    print(f"  {r:38s}  {v['cnt']:3d}  {v['actual']:+9.2f}  {v['hypo']:+14.2f}  {diff:+9.2f}")
print(f"  {'TOTAL (resolved 20)':38s}       {tot_act:+9.2f}  {tot_hyp:+14.2f}  {tot_hyp-tot_act:+9.2f}")

print("\nBY SPORT (resolved only):")
print(f"  {'sport':12s}  {'cnt':>3s}  {'actual':>9s}  {'hold2resolve':>14s}  {'Δ':>9s}")
for s in sorted(by_sport.keys()):
    v = by_sport[s]
    diff = v["hypo"] - v["actual"]
    print(f"  {s:12s}  {v['cnt']:3d}  {v['actual']:+9.2f}  {v['hypo']:+14.2f}  {diff:+9.2f}")

print("\nPER-TRADE DETAIL (sorted by Δ hold-vs-actual):")
print(f"  {'sport':10s} {'slug':38s} {'reason':25s} {'dir':7s} {'ent':>5s} {'sz':>6s} {'won':>4s} {'actual':>8s} {'hold':>8s} {'Δ':>8s}")
for d in sorted(details, key=lambda x: x["diff"], reverse=True):
    print(f"  {d['sport']:10s} {d['slug'][:38]:38s} {d['reason'][:25]:25s} {d['dir']:7s} {d['entry']:5.2f} {d['size']:6.2f} {'Y' if d['yes_won'] else 'N':>4s} {d['actual']:+8.2f} {d['hypo']:+8.2f} {d['diff']:+8.2f}")

# =============================================================================
# Q1: AI LAYER vs. ODDS API — per-sport on today's entries
# =============================================================================
print("\n" + "=" * 100)
print("Q1: AI LAYER vs. ODDS API — classification of today's entries")
print("=" * 100)

today_entries = {}
with open(TRADES, encoding="utf-8") as f:
    for line in f:
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not e.get("timestamp", "").startswith(TODAY):
            continue
        if e.get("action") in ENTRY_ACTIONS:
            today_entries[e.get("market")] = e

rows = []
for slug, b in today_entries.items():
    entry_price = b.get("entry_price")
    direction = b.get("direction", "")
    ai_prob = b.get("ai_prob")
    bm_prob = b.get("bookmaker_prob")
    size = b.get("size_usdc", 0.0)
    sport = sport_family(b.get("sport_tag","") or "", slug)
    if entry_price is None:
        continue
    ai_edge = dir_edge(ai_prob, entry_price, direction) if ai_prob is not None else None
    bm_edge = dir_edge(bm_prob, entry_price, direction) if (bm_prob not in (None,0,0.0)) else None
    pnl = net_pnl_today(slug)
    rows.append({"slug":slug,"dir":direction,"entry":entry_price,"ai_prob":ai_prob,
                 "bm_prob":bm_prob,"ai_edge":ai_edge,"bm_edge":bm_edge,"size":size,
                 "pnl":pnl,"has_bm":bm_edge is not None,"sport":sport})

def classify(r):
    ai_ok = r["ai_edge"] is not None and r["ai_edge"] > 0.02
    bm_ok = r["bm_edge"] is not None and r["bm_edge"] > 0.02
    if not r["has_bm"]: return "NO_BOOKMAKER"
    if ai_ok and bm_ok: return "CONCORDANT"
    if ai_ok and not bm_ok: return "AI_ONLY"
    if bm_ok and not ai_ok: return "BM_ONLY"
    return "BOTH_WEAK"

# Overall
def print_cats(subset, title):
    cats = defaultdict(lambda: {"cnt":0,"size":0.0,"pnl":0.0,"w":0,"l":0})
    for r in subset:
        c = classify(r); cats[c]["cnt"] += 1
        cats[c]["size"] += r["size"]; cats[c]["pnl"] += r["pnl"]
        if r["pnl"] > 0.01: cats[c]["w"] += 1
        elif r["pnl"] < -0.01: cats[c]["l"] += 1
    print(f"\n[{title}] n={len(subset)}")
    print(f"  {'category':14s} {'cnt':>4s} {'size':>8s} {'pnl':>9s} {'W/L':>7s} {'ROI%':>7s}")
    for name in ["CONCORDANT","AI_ONLY","BM_ONLY","BOTH_WEAK","NO_BOOKMAKER"]:
        if name in cats:
            v = cats[name]
            roi = (v["pnl"]/v["size"]*100) if v["size"]>0 else 0
            print(f"  {name:14s} {v['cnt']:4d} {v['size']:8.2f} {v['pnl']:+9.2f} {v['w']:3d}/{v['l']:<3d} {roi:+6.2f}%")

print_cats(rows, "ALL SPORTS")
for s in sorted(set(r["sport"] for r in rows)):
    print_cats([r for r in rows if r["sport"]==s], s)

# Summary - bookmaker coverage
no_bm_count = sum(1 for r in rows if not r["has_bm"])
both_weak_count = sum(1 for r in rows if classify(r) == "BOTH_WEAK")
ai_additive = sum(1 for r in rows if classify(r) == "AI_ONLY")
print(f"\nKey ratios:")
print(f"  Entries without bookmaker:  {no_bm_count}/{len(rows)} ({no_bm_count/len(rows)*100:.0f}%) — AI was sole decider")
print(f"  Both AI and BM flat (<2%):  {both_weak_count}/{len(rows)} ({both_weak_count/len(rows)*100:.0f}%) — AI just echoing market")
print(f"  AI edge beyond bookmaker:   {ai_additive}/{len(rows)} ({ai_additive/len(rows)*100:.0f}%) — AI's real unique contribution")

# =============================================================================
# Q3: PER-SPORT NET today (all 50 closure events)
# =============================================================================
print("\n" + "=" * 100)
print("PER-SPORT NET PnL today (all 50 closure events — EXIT + SCALE_OUT)")
print("=" * 100)
sport_by_slug = {}
for slug, b in today_entries.items():
    sport_by_slug[slug] = sport_family(b.get("sport_tag","") or "", slug)
for slug in list(exits_today.keys()) + list(scale_outs_today.keys()):
    if slug not in sport_by_slug:
        sport_by_slug[slug] = sport_family("", slug)

per_sport = defaultdict(lambda: {"cnt":0,"pnl":0.0,"forced_pnl":0.0,"forced_cnt":0,"nr_pnl":0.0,"nr_cnt":0,"so_pnl":0.0,"so_cnt":0})
for slug, evs in exits_today.items():
    sp = sport_by_slug.get(slug, "other")
    for ex in evs:
        pnl = ex.get("total_pnl", ex.get("pnl", 0.0)) or 0.0
        reason = ex.get("reason","")
        per_sport[sp]["cnt"] += 1
        per_sport[sp]["pnl"] += pnl
        if reason in FORCED_REASONS:
            per_sport[sp]["forced_pnl"] += pnl
            per_sport[sp]["forced_cnt"] += 1
        elif reason == "near_resolve_profit":
            per_sport[sp]["nr_pnl"] += pnl
            per_sport[sp]["nr_cnt"] += 1
for slug, sos in scale_outs_today.items():
    sp = sport_by_slug.get(slug, "other")
    if slug not in exits_today:
        for so in sos:
            per_sport[sp]["so_pnl"] += so.get("realized_pnl",0.0) or 0.0
            per_sport[sp]["so_cnt"] += 1
            per_sport[sp]["cnt"] += 1
            per_sport[sp]["pnl"] += so.get("realized_pnl",0.0) or 0.0

print(f"{'sport':12s} {'closes':>7s} {'net':>9s}  |  {'forced':>7s} {'forced_pnl':>11s}  {'near_res':>9s} {'nr_pnl':>9s}  {'sc_out':>7s} {'so_pnl':>8s}")
grand = 0
for s in sorted(per_sport.keys(), key=lambda x: per_sport[x]["pnl"]):
    v = per_sport[s]
    grand += v["pnl"]
    print(f"{s:12s} {v['cnt']:>7d} {v['pnl']:+9.2f}  |  {v['forced_cnt']:>7d} {v['forced_pnl']:+11.2f}  {v['nr_cnt']:>9d} {v['nr_pnl']:+9.2f}  {v['so_cnt']:>7d} {v['so_pnl']:+8.2f}")
print(f"{'GRAND':12s} {sum(v['cnt'] for v in per_sport.values()):>7d} {grand:+9.2f}")
