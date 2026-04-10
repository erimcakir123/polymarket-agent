"""FINAL comparison — two questions, clean answers.

Q1: Is AI needed? → Compare AI vs Bookmaker forecast accuracy on resolved trades.
Q2: Are exit rules needed? → Compare 4 scenarios:
    S0 = Actual (current system)
    S1 = AI entries + ONLY 94c TP (no forced exits)
    S2 = Odds-API filtered entries + ONLY 94c TP (no AI, no forced exits)
    S3 = Odds-API filtered entries + actual exits (keep exits)

Read-only.
"""
from __future__ import annotations
import json, glob
from pathlib import Path
from datetime import datetime
from collections import defaultdict

TODAY = "2026-04-10"
TP94 = 0.94

# -----------------------------------------------------------------------------
# Load data
# -----------------------------------------------------------------------------
entries = {}           # slug -> entry event
exits = defaultdict(list)
scale_outs = defaultdict(list)

with open("logs/trades.jsonl", encoding="utf-8") as f:
    for line in f:
        try: e = json.loads(line)
        except: continue
        ts = e.get("timestamp", "")
        if not ts.startswith(TODAY): continue
        act = e.get("action"); slug = e.get("market", "")
        if act in ("BUY", "UPSET_ENTRY"):
            entries[slug] = e
        elif act == "EXIT":
            exits[slug].append(e)
        elif act == "SCALE_OUT":
            scale_outs[slug].append(e)

resolved = {}
with open("logs/match_outcomes.jsonl", encoding="utf-8") as f:
    for line in f:
        try: d = json.loads(line)
        except: continue
        if d.get("slug"):
            resolved[d["slug"]] = d

# Open positions from positions.json
open_positions = {}
pj = Path("logs/positions.json")
if pj.exists():
    for cid, pos in json.loads(pj.read_text(encoding="utf-8")).items():
        slug = pos.get("slug")
        if slug:
            open_positions[slug] = pos

# Price history: slug -> list of price points sorted
hist_by_slug = defaultdict(list)
for fp in glob.glob("logs/price_history/*.json"):
    try:
        d = json.loads(Path(fp).read_text(encoding="utf-8"))
        slug = d.get("slug")
        if slug:
            hist_by_slug[slug].extend(d.get("price_history", []))
    except: pass
for slug in hist_by_slug:
    hist_by_slug[slug].sort(key=lambda x: x.get("t", 0))

def parse_ts(s):
    try: return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except: return 0

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def position_side_cost(entry_price, direction):
    """Cost per share on our side."""
    return entry_price if direction == "BUY_YES" else (1 - entry_price)

def pos_side_price_from_yes(yes_price, direction):
    return yes_price if direction == "BUY_YES" else (1 - yes_price)

def actual_pnl_slug(slug):
    p = 0.0
    for ex in exits.get(slug, []):
        p += ex.get("total_pnl", ex.get("pnl", 0.0)) or 0.0
    if slug not in exits:
        for so in scale_outs.get(slug, []):
            p += so.get("realized_pnl", 0.0) or 0.0
    return p

def hypothetical_tp94_then_hold(entry, hist_points):
    """Simulate: enter at entry, exit at 0.94 if reached, else hold to resolve.
    Returns (pnl, fate_label).
    Note: price_history stores YES price (mark). Position-side price is transformed.
    """
    ep = entry.get("entry_price")
    direction = entry.get("direction")
    size = entry.get("size_usdc", 0)
    slug = entry.get("market")
    if ep is None or size <= 0:
        return None, "no-data"

    cost = position_side_cost(ep, direction)
    if cost <= 0:
        return None, "invalid"
    shares = size / cost

    entry_ts = parse_ts(entry.get("timestamp", ""))
    # Filter post-entry history and convert YES price (mark in file may be YES or position-side)
    # Empirical check: in price_history files, 'p' field appears to be the position-side
    # price (the token we hold). For BUY_NO, lower entries mean market moving toward YES.
    # We treat 'p' as the mark for OUR side — if p >= 0.94, take profit.
    post = [pt for pt in hist_points if pt.get("t", 0) >= entry_ts - 60]

    # Check if 0.94 was ever hit
    if post:
        max_p = max(pt.get("p", 0) for pt in post)
        if max_p >= TP94:
            return shares * TP94 - size, "94c_hit"

    # Not hit: check resolution
    if slug in resolved and resolved[slug].get("yes_won") is not None:
        yw = bool(resolved[slug]["yes_won"])
        final_yes = 1.0 if yw else 0.0
        final_pos = pos_side_price_from_yes(final_yes, direction)
        return shares * final_pos - size, f"resolved_{('Y' if yw else 'N')}"

    # Open position: use current_price from positions.json
    if slug in open_positions:
        cp = open_positions[slug].get("current_price")
        bid = open_positions[slug].get("bid_price")
        px = bid if bid else cp
        if px:
            return shares * px - size, "open_markt"

    # Exited but unresolved — use last known price from history as proxy
    if post:
        last_p = post[-1].get("p", cost)
        return shares * last_p - size, "proxy_last"

    return None, "no-data"

def bookmaker_edge(entry):
    ep = entry.get("entry_price")
    bm = entry.get("bookmaker_prob")
    d = entry.get("direction")
    if ep is None or bm in (None, 0, 0.0):
        return None
    return (bm - ep) if d == "BUY_YES" else (ep - bm)

# =============================================================================
# PART 1 — AI vs Bookmaker accuracy on resolved trades
# =============================================================================
print("=" * 88)
print("PART 1 — AI vs. BOOKMAKER ACCURACY on 20 resolved trades")
print("=" * 88)

rows = []
for slug, out in resolved.items():
    yw = out.get("yes_won")
    if yw is None: continue
    entry = entries.get(slug)
    if not entry: continue
    ai = entry.get("ai_prob")
    bm = entry.get("bookmaker_prob")
    ep = entry.get("entry_price")
    rows.append({"slug": slug, "yes_won": bool(yw), "ai": ai, "bm": bm, "entry": ep})

def brier(p, y):
    return (p - (1 if y else 0)) ** 2

def direction_hit(prob, y):
    # If prob > 0.5 we "predict YES"; match to actual
    if prob is None: return None
    pred = prob > 0.5
    return pred == y

ai_brier = [brier(r["ai"], r["yes_won"]) for r in rows if r["ai"] is not None]
bm_brier = [brier(r["bm"], r["yes_won"]) for r in rows if r["bm"] not in (None, 0, 0.0)]
mkt_brier = [brier(r["entry"], r["yes_won"]) for r in rows]

ai_hits = [direction_hit(r["ai"], r["yes_won"]) for r in rows if r["ai"] is not None]
bm_hits = [direction_hit(r["bm"], r["yes_won"]) for r in rows if r["bm"] not in (None, 0, 0.0)]
mkt_hits = [direction_hit(r["entry"], r["yes_won"]) for r in rows]

def pct(hits): return sum(1 for h in hits if h) / len(hits) * 100 if hits else 0

print(f"\n{'Source':15s}  {'n':>4s}  {'Direction %':>12s}  {'Brier (lower=better)':>22s}")
print(f"{'AI':15s}  {len(ai_brier):>4d}  {pct(ai_hits):>11.1f}%  {sum(ai_brier)/len(ai_brier):>22.4f}")
print(f"{'Bookmaker':15s}  {len(bm_brier):>4d}  {pct(bm_hits):>11.1f}%  {sum(bm_brier)/len(bm_brier):>22.4f}" if bm_brier else "Bookmaker: no data")
print(f"{'Market (entry)':15s}  {len(mkt_brier):>4d}  {pct(mkt_hits):>11.1f}%  {sum(mkt_brier)/len(mkt_brier):>22.4f}")
print("\nLower Brier = more accurate probabilistic forecast")
print("Higher Direction% = more often right about winner")

# Per-trade detail
print(f"\nPer-trade (Y=YES won):")
print(f"{'slug':36s}  {'won':>4s}  {'AI':>6s}  {'BM':>6s}  {'entry':>6s}  {'AI_correct':>10s}  {'BM_correct':>10s}")
for r in rows:
    ai_str = f"{r['ai']:.2f}" if r['ai'] is not None else "  -  "
    bm_str = f"{r['bm']:.2f}" if r['bm'] not in (None, 0, 0.0) else "  -  "
    ai_c = "Y" if direction_hit(r["ai"], r["yes_won"]) else ("N" if r["ai"] is not None else "-")
    bm_c = "Y" if direction_hit(r["bm"], r["yes_won"]) else ("N" if r["bm"] not in (None,0,0.0) else "-")
    print(f"{r['slug'][:36]:36s}  {'Y' if r['yes_won'] else 'N':>4s}  {ai_str:>6s}  {bm_str:>6s}  {r['entry']:>6.2f}  {ai_c:>10s}  {bm_c:>10s}")

# =============================================================================
# PART 2 — Exit rule counterfactuals
# =============================================================================
print("\n" + "=" * 88)
print("PART 2 — EXIT RULE counterfactuals (all 66 entries)")
print("=" * 88)

# Scenario 0: actual
S0_pnl = sum(actual_pnl_slug(slug) for slug in entries)
S0_count = len(entries)

# Scenario 1: Current entries + 94c TP only (no forced exits)
S1_pnl = 0.0; S1_count = 0; s1_fates = defaultdict(int)
for slug, e in entries.items():
    h = hist_by_slug.get(slug, [])
    pnl, fate = hypothetical_tp94_then_hold(e, h)
    if pnl is not None:
        S1_pnl += pnl; S1_count += 1
        s1_fates[fate] += 1

# Scenario 2: Odds-API filtered entries + 94c TP only
S2_pnl = 0.0; S2_count = 0; S2_invested = 0.0; s2_fates = defaultdict(int)
for slug, e in entries.items():
    edge = bookmaker_edge(e)
    if edge is None or edge <= 0: continue
    h = hist_by_slug.get(slug, [])
    pnl, fate = hypothetical_tp94_then_hold(e, h)
    if pnl is not None:
        S2_pnl += pnl; S2_count += 1
        S2_invested += e.get("size_usdc", 0)
        s2_fates[fate] += 1

# Scenario 3: Odds-API filtered entries + actual exits
S3_pnl = 0.0; S3_count = 0; S3_invested = 0.0
for slug, e in entries.items():
    edge = bookmaker_edge(e)
    if edge is None or edge <= 0: continue
    S3_pnl += actual_pnl_slug(slug); S3_count += 1
    S3_invested += e.get("size_usdc", 0)

# Scenario 4: Loose odds filter (edge >= -0.05, allow mild bookmaker disagreement)
# To see what a wider bookmaker filter gives
S4_pnl = 0.0; S4_count = 0
for slug, e in entries.items():
    edge = bookmaker_edge(e)
    if edge is None or edge < -0.05: continue
    h = hist_by_slug.get(slug, [])
    pnl, fate = hypothetical_tp94_then_hold(e, h)
    if pnl is not None:
        S4_pnl += pnl; S4_count += 1

print(f"\n{'Scenario':60s}  {'n':>4s}  {'PnL':>10s}  {'vs S0':>10s}")
print(f"{'S0 = Actual (AI entries + all exits)':60s}  {S0_count:>4d}  {S0_pnl:+10.2f}  {0:+10.2f}")
print(f"{'S1 = All entries + only 94c TP (no forced exits)':60s}  {S1_count:>4d}  {S1_pnl:+10.2f}  {S1_pnl-S0_pnl:+10.2f}")
print(f"{'S2 = Odds-filter (bm_edge>0) + only 94c TP':60s}  {S2_count:>4d}  {S2_pnl:+10.2f}  {S2_pnl-S0_pnl:+10.2f}")
print(f"{'S3 = Odds-filter (bm_edge>0) + actual exits':60s}  {S3_count:>4d}  {S3_pnl:+10.2f}  {S3_pnl-S0_pnl:+10.2f}")
print(f"{'S4 = Loose odds-filter (bm_edge>-0.05) + 94c TP':60s}  {S4_count:>4d}  {S4_pnl:+10.2f}  {S4_pnl-S0_pnl:+10.2f}")

print(f"\nS1 fate distribution (what happened to each position):")
for k, v in sorted(s1_fates.items()): print(f"  {k:20s} {v}")
print(f"S2 fate distribution:")
for k, v in sorted(s2_fates.items()): print(f"  {k:20s} {v}")

# =============================================================================
# Sanity checks
# =============================================================================
print("\n" + "=" * 88)
print("DATA COVERAGE NOTE (important for interpreting hypotheticals)")
print("=" * 88)
print(f"Total entries today:                {len(entries)}")
print(f"  with price_history file:          {sum(1 for s in entries if s in hist_by_slug)}")
print(f"  with resolved outcome (yes_won):  {sum(1 for s in entries if s in resolved)}")
print(f"  still open (positions.json):      {sum(1 for s in entries if s in open_positions)}")
print(f"  with bookmaker_prob data:         {sum(1 for s in entries.values() if s.get('bookmaker_prob') not in (None, 0, 0.0))}")
print(f"  with ai_prob data:                {sum(1 for s in entries.values() if s.get('ai_prob') is not None)}")
