"""Gerçek score_exit kurallarıyla linescore-bazlı simülasyon."""
import json
from collections import defaultdict
from pathlib import Path

LOG_DIR = Path("logs/sharp_vs_poly")
MIN_FAV_PROB, MIN_ENTRY, MAX_ENTRY = 0.60, 0.60, 0.85
BANKROLL, BET_PCT = 1000.0, 0.05


def estimate_exit_price(deficit: int, period_elapsed: float) -> float:
    """Bradley-Terry proxy: severity = deficit * 0.10 + elapsed * 0.30."""
    severity = deficit * 0.10 + period_elapsed * 0.30
    return max(0.05, 0.50 - severity)


def mlb_score_exit(hls, als, our_home):
    max_i = max(len(hls), len(als))
    for i in range(max_i):
        ot = sum(hls[:i+1]) if our_home else sum(als[:i+1])
        pt = sum(als[:i+1]) if our_home else sum(hls[:i+1])
        deficit = pt - ot
        inning = i + 1
        if inning >= 7 and deficit >= 5: return True, inning, deficit
        if inning >= 8 and deficit >= 3: return True, inning, deficit
        if inning >= 9 and deficit >= 1: return True, inning, deficit
    return False, None, 0


def nba_score_exit(hls, als, our_home):
    for i in range(min(4, len(hls))):
        ot = sum(hls[:i+1]) if our_home else sum(als[:i+1])
        pt = sum(als[:i+1]) if our_home else sum(hls[:i+1])
        deficit = pt - ot
        q = i + 1
        if q == 2 and deficit >= 15: return True, q, deficit
        if q == 3 and deficit >= 20: return True, q, deficit
        if q == 4 and deficit >= 10: return True, q, deficit
    return False, None, 0


def nhl_score_exit(hls, als, our_home):
    for i in range(min(3, len(hls))):
        ot = sum(hls[:i+1]) if our_home else sum(als[:i+1])
        pt = sum(als[:i+1]) if our_home else sum(hls[:i+1])
        deficit = pt - ot
        p = i + 1
        if deficit >= 3: return True, p, deficit
        if p == 3 and deficit >= 2: return True, p, deficit
    return False, None, 0


rows = []
for f in sorted(LOG_DIR.glob("*.jsonl")):
    if f.name.startswith("_"): continue
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            try: rows.append(json.loads(line))
            except: pass

groups = defaultdict(list)
for r in rows: groups[r.get("cid")].append(r)
for cid in groups: groups[cid].sort(key=lambda x: x.get("ts", ""))

with open(LOG_DIR / "_espn_linescores.json", encoding="utf-8") as f:
    match_data = json.load(f)


def simulate(cid, use_score_exit):
    snaps = groups[cid]
    first = snaps[0]
    md = match_data.get(cid)
    if not md: return None
    sport = first.get("sport_key", "")
    sph = first.get("sharp_prob_home")
    yes_is_home = first.get("yes_is_home", True)
    pm_first = first.get("pm_yes_price")
    if sph is None or pm_first is None: return None

    sharp_favors_home = sph > 0.5
    win_prob = sph if sharp_favors_home else (1.0 - sph)
    if win_prob < MIN_FAV_PROB: return {"entered": False}

    direction = "BUY_YES" if (sharp_favors_home == yes_is_home) else "BUY_NO"
    eff_entry = pm_first if direction == "BUY_YES" else (1.0 - pm_first)
    if not (MIN_ENTRY <= eff_entry <= MAX_ENTRY): return {"entered": False}

    stake = min(BANKROLL * BET_PCT * win_prob, 50.0)
    shares = stake / eff_entry

    exit_triggered = False
    exit_reason = "resolution"
    exit_price = None
    our_home = sharp_favors_home

    if use_score_exit:
        hls, als = md["home_linescores"], md["away_linescores"]
        if sport == "baseball_mlb":
            t, p, d = mlb_score_exit(hls, als, our_home)
            total_p = 9
        elif sport == "basketball_nba":
            t, p, d = nba_score_exit(hls, als, our_home)
            total_p = 4
        elif sport == "icehockey_nhl":
            t, p, d = nhl_score_exit(hls, als, our_home)
            total_p = 3
        else:
            t = False
        if t:
            exit_triggered = True
            exit_reason = "score_exit"
            exit_price = estimate_exit_price(d, p / total_p)

    if exit_triggered:
        pnl = shares * exit_price - stake
    else:
        home_won = md.get("home_won", False)
        our_won = (our_home and home_won) or (not our_home and not home_won)
        pnl = (shares * 1.0 - stake) if our_won else -stake

    return {
        "entered": True, "sport": sport, "stake": stake, "pnl": pnl,
        "exit_reason": exit_reason, "exit_price": exit_price,
        "question": first.get("question", "")[:40]
    }


for mode_name, use_se in [("HOLD_ONLY", False), ("SCORE_EXIT", True)]:
    stats = defaultdict(lambda: {"trades": 0, "wins": 0, "losses": 0, "score_exits": 0, "stake": 0.0, "pnl": 0.0})
    saved_by_score_exit = []
    for cid in match_data:
        r = simulate(cid, use_se)
        if not r or not r.get("entered"): continue
        sp = r["sport"]
        stats[sp]["trades"] += 1
        stats[sp]["stake"] += r["stake"]
        stats[sp]["pnl"] += r["pnl"]
        if r["pnl"] > 0: stats[sp]["wins"] += 1
        else: stats[sp]["losses"] += 1
        if r["exit_reason"] == "score_exit":
            stats[sp]["score_exits"] += 1

    print("=" * 100)
    print(f"{mode_name}")
    print("=" * 100)
    print(f"{'Sport':<25}{'Trades':<8}{'Wins':<6}{'Loss':<6}{'ScoreEx':<9}{'Stake':<10}{'PnL':<12}{'ROI'}")
    print("-" * 100)
    total = {"trades": 0, "wins": 0, "losses": 0, "score_exits": 0, "stake": 0.0, "pnl": 0.0}
    for sp, s in sorted(stats.items(), key=lambda x: -x[1]["trades"]):
        if s["trades"] == 0: continue
        roi = s["pnl"] / s["stake"] * 100 if s["stake"] > 0 else 0
        print(f"{sp:<25}{s['trades']:<8}{s['wins']:<6}{s['losses']:<6}{s['score_exits']:<9}${s['stake']:<9.2f}${s['pnl']:<+11.2f}{roi:+.1f}%")
        for k in total: total[k] += s[k]
    roi = total["pnl"] / total["stake"] * 100 if total["stake"] > 0 else 0
    print("-" * 100)
    print(f"{'TOPLAM':<25}{total['trades']:<8}{total['wins']:<6}{total['losses']:<6}{total['score_exits']:<9}${total['stake']:<9.2f}${total['pnl']:<+11.2f}{roi:+.1f}%")
    print()

# Delta
print("=" * 100)
print("SCORE_EXIT KATKISI")
print("=" * 100)
hold_pnl = {}
se_pnl = {}
for mode_name, use_se in [("hold", False), ("se", True)]:
    for cid in match_data:
        r = simulate(cid, use_se)
        if not r or not r.get("entered"): continue
        sp = r["sport"]
        if mode_name == "hold":
            hold_pnl[sp] = hold_pnl.get(sp, 0) + r["pnl"]
        else:
            se_pnl[sp] = se_pnl.get(sp, 0) + r["pnl"]

for sp in sorted(set(hold_pnl) | set(se_pnl)):
    h = hold_pnl.get(sp, 0)
    s = se_pnl.get(sp, 0)
    delta = s - h
    mark = "+" if delta >= 0 else ""
    print(f"  {sp:<25} hold=${h:+.2f}  score_exit=${s:+.2f}  Δ=${mark}{delta:.2f}")

total_h = sum(hold_pnl.values())
total_s = sum(se_pnl.values())
print(f"\n  TOTAL  hold=${total_h:+.2f}  score_exit=${total_s:+.2f}  Δ=${total_s-total_h:+.2f}")
