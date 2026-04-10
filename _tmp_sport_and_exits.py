"""Two questions:
Q1) Is wrong-direction problem sport-specific? And would PURE BOOKMAKER also pick wrong side?
Q2) What exit rules are actually active? For catastrophic_floor exits, did they resolve as losses anyway?
"""
from __future__ import annotations
import json
from collections import defaultdict

# Load entries + exits
entries = {}
exits = defaultdict(list)
with open("logs/trades.jsonl", encoding="utf-8") as f:
    for line in f:
        try: e = json.loads(line)
        except: continue
        if not e.get("timestamp","").startswith("2026-04-10"): continue
        act = e.get("action"); slug = e.get("market","")
        if act in ("BUY","UPSET_ENTRY"): entries[slug] = e
        elif act == "EXIT": exits[slug].append(e)

# Resolved
resolved = {}
with open("logs/match_outcomes.jsonl", encoding="utf-8") as f:
    for line in f:
        try: d = json.loads(line)
        except: continue
        if d.get("slug"): resolved[d["slug"]] = d

def sport(tag, slug=""):
    s = (tag or "").lower() + " " + (slug or "").lower()
    if "nba" in s: return "NBA"
    if "nhl" in s: return "NHL"
    if "mlb" in s: return "MLB"
    if "atp" in s: return "ATP"
    if "wta" in s: return "WTA"
    if "boxing" in s: return "Boxing"
    if "mma" in s or "ufc" in s: return "MMA"
    if "euroleague" in s: return "EuroLeague"
    if any(x in s for x in ["sud","lib","aus","fl1","fl2","fr1","fr2","ligue","bl1","bl2","bun",
                             "elc","epl","ere","sea","tur","den","ita","esp","por","ned","mls",
                             "serie","la-liga","premier","primera","a-league","bundes","eredivisie"]):
        return "Soccer"
    return "other"

# =============================================================================
# Q1 — Per-sport direction accuracy + pure-bookmaker counterfactual
# =============================================================================
print("=" * 90)
print("Q1) WRONG-DIRECTION per sport + PURE-BOOKMAKER hypothetical direction")
print("=" * 90)

rows = []
for slug, out in resolved.items():
    yw = out.get("yes_won")
    if yw is None: continue
    e = entries.get(slug)
    if not e: continue
    dir_ = e.get("direction"); ep = e.get("entry_price")
    ai = e.get("ai_prob"); bm = e.get("bookmaker_prob")
    if ep is None: continue
    # Our direction correct?
    our_correct = (dir_ == "BUY_YES" and yw) or (dir_ == "BUY_NO" and not yw)
    # Pure bookmaker direction: pick side where bm_prob disagrees with market
    # BUY_YES if bm_prob > entry_price (bookmaker thinks YES undervalued)
    # BUY_NO if bm_prob < entry_price
    bm_dir = None
    bm_correct = None
    if bm not in (None, 0, 0.0):
        if bm > ep:
            bm_dir = "BUY_YES"
        elif bm < ep:
            bm_dir = "BUY_NO"
        else:
            bm_dir = dir_  # tied, assume same
        bm_correct = (bm_dir == "BUY_YES" and yw) or (bm_dir == "BUY_NO" and not yw)

    rows.append({
        "slug": slug, "sport": sport(e.get("sport_tag","") or "", slug),
        "dir": dir_, "ep": ep, "ai": ai, "bm": bm, "yw": bool(yw),
        "our_correct": our_correct, "bm_dir": bm_dir, "bm_correct": bm_correct,
    })

# Per-sport stats
per_sport = defaultdict(lambda: {"n":0,"our_right":0,"bm_same":0,"bm_n":0,"bm_right":0,"bm_diff_dir":0})
for r in rows:
    s = per_sport[r["sport"]]
    s["n"] += 1
    if r["our_correct"]: s["our_right"] += 1
    if r["bm"] not in (None, 0, 0.0):
        s["bm_n"] += 1
        if r["bm_correct"]: s["bm_right"] += 1
        if r["bm_dir"] == r["dir"]:
            s["bm_same"] += 1
        else:
            s["bm_diff_dir"] += 1

print(f"\n{'sport':12s} {'n':>3s} {'our_acc':>9s} {'bm_acc':>9s} {'same_dir':>10s} {'diff_dir':>10s}")
for sp in sorted(per_sport.keys()):
    v = per_sport[sp]
    our_pct = v["our_right"]/v["n"]*100 if v["n"] else 0
    bm_pct = v["bm_right"]/v["bm_n"]*100 if v["bm_n"] else 0
    print(f"{sp:12s} {v['n']:>3d} {v['our_right']}/{v['n']} ({our_pct:>4.0f}%) {v['bm_right']}/{v['bm_n']} ({bm_pct:>4.0f}%) {v['bm_same']:>10d} {v['bm_diff_dir']:>10d}")

tot_n = sum(v["n"] for v in per_sport.values())
tot_ok = sum(v["our_right"] for v in per_sport.values())
tot_bmn = sum(v["bm_n"] for v in per_sport.values())
tot_bmok = sum(v["bm_right"] for v in per_sport.values())
tot_same = sum(v["bm_same"] for v in per_sport.values())
tot_diff = sum(v["bm_diff_dir"] for v in per_sport.values())
print(f"{'TOTAL':12s} {tot_n:>3d} {tot_ok}/{tot_n} ({tot_ok/tot_n*100:.0f}%) {tot_bmok}/{tot_bmn} ({tot_bmok/tot_bmn*100:.0f}%) {tot_same:>10d} {tot_diff:>10d}")

print()
print("same_dir = pure bookmaker would pick SAME direction as us")
print("diff_dir = pure bookmaker would pick OPPOSITE direction (bookmaker disagreed)")

# Detailed per-trade for the disagreement cases
print(f"\nTrades where PURE BOOKMAKER would have picked DIFFERENT direction:")
diffs = [r for r in rows if r["bm_dir"] and r["bm_dir"] != r["dir"]]
if not diffs:
    print("  (none — bookmaker agreed with us on every trade)")
else:
    for r in diffs:
        print(f"  {r['slug'][:40]:40s} we={r['dir']:7s} bm={r['bm_dir']:7s} bm_prob={r['bm']:.2f} entry={r['ep']:.2f} won={r['yw']}  we_ok={r['our_correct']} bm_ok={r['bm_correct']}")

# =============================================================================
# Q2 — Active exit rules + catastrophic_floor resolution check
# =============================================================================
print("\n" + "=" * 90)
print("Q2) Active exit rules + catastrophic_floor counterfactual")
print("=" * 90)

print("""
Active exit layers (from src/match_exit.py + other files):
  1. score_terminal_loss / score_terminal_win  [esports only, BO series]
  2. catastrophic_floor    [price < entry * 0.50 (re-entry: 0.75), if entry >= 0.20]
  3. ultra_low_guard       [entry <9c, >75% done, price <5c]
  4. a_conf_market_flip    [A-conf, entry >=60c, price <50c]
  5. graduated_sl          [PnL% < time-scaled max_loss]
  6. never_in_profit       [>70% done, never profited, price < entry*0.75]
  7. hold_revoked          [hold-to-resolve, price drops below 70-75% of entry mid-match]
  8. edge_decay            [underdog TP based on AI target decay]

From other files:
  9. stop_loss             [portfolio.py — flat SL]
  10. near_resolve_profit  [agent.py — take profit near match end]
  11. SCALE_OUT tier1/2    [scale_out.py — partial profit taking]

REMOVED (you deleted these, bot needs restart to apply):
  X. UPSET_ENTRY           [no longer in src/ — in-memory cache still active]
  X. match_exit_upset_max_hold  [ditto]
  X. trailing_tp           [disabled earlier per memory]
""")

# Catastrophic_floor today
cat_exits = []
for slug, evs in exits.items():
    for ex in evs:
        if ex.get("reason") == "match_exit_catastrophic_floor":
            cat_exits.append((slug, ex))

print(f"Catastrophic_floor exits today: {len(cat_exits)}")
print(f"{'slug':40s} {'dir':8s} {'ent':>5s} {'exit':>5s} {'actual':>8s} {'resolved':>10s} {'hold_pnl':>10s}")
for slug, ex in cat_exits:
    ep_exit = ex.get("price", 0)
    xp = ex.get("exit_price", 0)
    pnl = ex.get("total_pnl", ex.get("pnl", 0))
    direction = ex.get("direction")
    size = ex.get("size", 0)
    # Get original entry price
    entry = entries.get(slug, {})
    entry_price = entry.get("entry_price", ep_exit)
    # Resolution check
    if slug in resolved and resolved[slug].get("yes_won") is not None:
        yw = resolved[slug]["yes_won"]
        cost = entry_price if direction == "BUY_YES" else (1 - entry_price)
        shares = size / cost if cost > 0 else 0
        if direction == "BUY_YES":
            hold_pnl = shares * (1.0 if yw else 0.0) - size
        else:
            hold_pnl = shares * (0.0 if yw else 1.0) - size
        status = f"Y={'Y' if yw else 'N'}"
    else:
        hold_pnl = None
        status = "open/?"
    hp_str = f"{hold_pnl:+.2f}" if hold_pnl is not None else "  --  "
    print(f"{slug[:40]:40s} {direction:8s} {entry_price:>5.2f} {xp:>5.2f} {pnl:+8.2f} {status:>10s} {hp_str:>10s}")

# Other forced-exit reasons counterfactual (same check)
print("\nAll forced exits resolved -- actual vs hold-to-resolution:")
FORCED = {"match_exit_a_conf_market_flip","match_exit_catastrophic_floor",
          "match_exit_graduated_sl","match_exit_upset_max_hold","stop_loss"}
by_reason = defaultdict(lambda: {"n":0,"actual":0.0,"hypo":0.0,"resolved":0})
for slug, evs in exits.items():
    for ex in evs:
        r = ex.get("reason","")
        if r not in FORCED: continue
        pnl = ex.get("total_pnl", ex.get("pnl", 0)) or 0
        by_reason[r]["n"] += 1
        by_reason[r]["actual"] += pnl
        if slug in resolved and resolved[slug].get("yes_won") is not None:
            yw = resolved[slug]["yes_won"]
            entry = entries.get(slug, {})
            entry_price = entry.get("entry_price", ex.get("price"))
            direction = ex.get("direction")
            size = ex.get("size", 0)
            cost = entry_price if direction == "BUY_YES" else (1 - entry_price)
            if cost > 0:
                shares = size / cost
                if direction == "BUY_YES":
                    hp = shares * (1.0 if yw else 0.0) - size
                else:
                    hp = shares * (0.0 if yw else 1.0) - size
                by_reason[r]["hypo"] += hp
                by_reason[r]["resolved"] += 1
            else:
                by_reason[r]["hypo"] += pnl
        else:
            by_reason[r]["hypo"] += pnl  # unknown -> assume same

print(f"\n{'reason':38s} {'n':>3s} {'resolved':>9s} {'actual':>9s} {'hold_to_end':>12s} {'savings':>10s}")
for r in sorted(by_reason.keys()):
    v = by_reason[r]
    diff = v["actual"] - v["hypo"]
    print(f"{r:38s} {v['n']:>3d} {v['resolved']:>9d} {v['actual']:+9.2f} {v['hypo']:+12.2f} {diff:+10.2f}")
