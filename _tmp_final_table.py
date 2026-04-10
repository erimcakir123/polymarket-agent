"""Final table: every exit today, using bot's own hypothetical_pnl from match_outcomes.jsonl.
For exits not yet in match_outcomes (still waiting), mark as 'pending'.
"""
import json
from collections import defaultdict

CUTOFF = "2026-04-10T00:00:00"

# Load bot's own resolved outcomes with hypothetical_pnl
with open('logs/match_outcomes.jsonl','r',encoding='utf-8') as f:
    resolved = [json.loads(l) for l in f if l.strip()]

resolved_by_slug = {}
for r in resolved:
    slug = r.get('slug','')
    if r.get('hypothetical_pnl') is not None:
        resolved_by_slug[slug] = r

# Load all trade_archive exits since morning (with dedup vs trades.jsonl)
with open('logs/trades.jsonl','r',encoding='utf-8') as f:
    live = [json.loads(l) for l in f if l.strip()]
with open('logs/trade_archive.jsonl','r',encoding='utf-8') as f:
    archive = [json.loads(l) for l in f if l.strip()]

seen = set()
all_recs = []
for t in live + archive:
    k = (t.get('market',''), t.get('action',''), t.get('timestamp',''), t.get('reason',''))
    if k in seen: continue
    seen.add(k)
    all_recs.append(t)

# Buy records (for confidence, size, entry_price, direction)
buys = {}
for t in all_recs:
    if t.get('action') in ('BUY','UPSET_ENTRY') and t.get('market') not in buys:
        buys[t['market']] = t

# All exits since morning, per market
exits_per_market = defaultdict(list)
for t in all_recs:
    if t.get('action') in ('EXIT','SCALE_OUT') and t.get('timestamp','') >= CUTOFF:
        exits_per_market[t.get('market','')].append(t)

# Build rows
rows = []
for slug, exs in exits_per_market.items():
    buy = buys.get(slug, {})
    direction = buy.get('direction','?')
    confidence = buy.get('confidence','?')
    entry_reason = buy.get('entry_reason','?')
    bcnt = buy.get('bookmaker_count', 0) or 0
    entry_yes = buy.get('entry_price', 0) or 0
    size = buy.get('size_usdc', 0) or 0
    sport = (buy.get('sport_tag','') or '')

    # Actual pnl from exits
    actual = sum(x.get('total_pnl', x.get('pnl', 0)) or 0 for x in exs)
    exit_reason_last = exs[-1].get('reason','?') or '?'

    # Bot's own "if held" if available
    res = resolved_by_slug.get(slug)
    if res:
        if_held = res.get('hypothetical_pnl')
        our_won = res.get('our_side_won')
        yes_won = res.get('yes_won')
        bot_actual = res.get('actual_pnl', actual)  # prefer bot's number
        resolved_flag = True
    else:
        if_held = None
        our_won = None
        yes_won = None
        bot_actual = actual
        resolved_flag = False

    rows.append({
        'slug': slug,
        'direction': direction,
        'confidence': confidence,
        'entry_reason': entry_reason,
        'bcnt': int(bcnt),
        'entry_yes': entry_yes,
        'size': size,
        'sport': sport,
        'actual': bot_actual,
        'if_held': if_held,
        'exit_reason': exit_reason_last,
        'resolved': resolved_flag,
        'our_won': our_won,
        'yes_won': yes_won,
    })

# Sort: resolved first, then by delta savings
rows.sort(key=lambda r: (not r['resolved'], -(r['actual'] - (r['if_held'] if r['if_held'] is not None else 0))))

# Print simple table
print("=" * 135)
print("EVERY EXIT TODAY — Actual vs If Held (using bot's own outcome_tracker numbers)")
print("=" * 135)
print()
print(f"{'#':<3} {'market':<38} {'dir':<7} {'conf':<5} {'reason':<30} {'actual':>9} {'if_held':>9}  {'delta':>9}  {'status'}")
print('-' * 135)

# Resolved trades first
tot_actual = 0
tot_held = 0
n_resolved = 0
savings_rows = []
cost_rows = []

resolved_rows = [r for r in rows if r['resolved']]
unresolved_rows = [r for r in rows if not r['resolved']]

i = 0
for r in resolved_rows:
    i += 1
    actual = r['actual']
    held = r['if_held']
    delta = actual - held  # positive = exit saved us
    if delta > 0.5:
        status = 'EXIT SAVED'
        savings_rows.append((r, delta))
    elif delta < -0.5:
        status = 'EXIT COST  '
        cost_rows.append((r, -delta))
    else:
        status = '~neutral'
    tot_actual += actual
    tot_held += held
    n_resolved += 1
    print(f"{i:<3} {r['slug'][:38]:<38} {r['direction']:<7} {r['confidence']:<5} {r['exit_reason'][:30]:<30} {actual:>+9.2f} {held:>+9.2f}  {delta:>+9.2f}  {status}")

print('-' * 135)
print(f"{'RESOLVED TOTAL ('+str(n_resolved)+' exits)':<82} {tot_actual:>+9.2f} {tot_held:>+9.2f}  {tot_actual-tot_held:>+9.2f}  NET")

# Unresolved trades (still waiting)
print()
print("=" * 135)
print(f"STILL PENDING RESOLUTION — {len(unresolved_rows)} exits (bot hasn't confirmed outcome yet)")
print("=" * 135)
print(f"{'#':<3} {'market':<38} {'dir':<7} {'conf':<5} {'reason':<30} {'actual':>9}")
print('-' * 135)
j = 0
pending_actual = 0
for r in unresolved_rows:
    j += 1
    pending_actual += r['actual']
    print(f"{j:<3} {r['slug'][:38]:<38} {r['direction']:<7} {r['confidence']:<5} {r['exit_reason'][:30]:<30} {r['actual']:>+9.2f}")
print('-' * 135)
print(f"{'PENDING TOTAL':<82} {pending_actual:>+9.2f}")

# Summary
print()
print("=" * 135)
print("SUMMARY (RESOLVED ONLY — uses bot's own hold-to-resolution math)")
print("=" * 135)
print(f"\nResolved exits: {n_resolved}")
print(f"Actual total:     ${tot_actual:+.2f}")
print(f"If-held total:    ${tot_held:+.2f}")
delta_tot = tot_actual - tot_held
if delta_tot > 0:
    print(f"Exit rules SAVED us: +${delta_tot:.2f}")
else:
    print(f"Exit rules COST us: -${-delta_tot:.2f}")

# Savings vs cost breakdown
print(f"\nExits that SAVED us: {len(savings_rows)} (total +${sum(d for _,d in savings_rows):.2f})")
for r, d in sorted(savings_rows, key=lambda x: -x[1])[:10]:
    print(f"  +${d:>6.2f}  {r['slug'][:40]:<40}  {r['exit_reason']} [{r['confidence']}]")

print(f"\nExits that COST us: {len(cost_rows)} (total -${sum(d for _,d in cost_rows):.2f})")
for r, d in sorted(cost_rows, key=lambda x: -x[1])[:10]:
    print(f"  -${d:>6.2f}  {r['slug'][:40]:<40}  {r['exit_reason']} [{r['confidence']}]")

# Per exit reason
print(f"\n--- Per exit_reason (resolved only) ---")
by_reason = defaultdict(lambda: {'n':0,'actual':0,'held':0})
for r in resolved_rows:
    reason = r['exit_reason']
    by_reason[reason]['n'] += 1
    by_reason[reason]['actual'] += r['actual']
    by_reason[reason]['held'] += r['if_held']
print(f"{'reason':<42} {'n':>3} {'actual':>9} {'held':>9} {'save(+)/cost(-)':>16}")
for reason, d in sorted(by_reason.items(), key=lambda x: -(x[1]['actual']-x[1]['held'])):
    d_delta = d['actual'] - d['held']
    tag = '✅ SAVED' if d_delta > 0 else '❌ COST '
    print(f"  {reason:<40} {d['n']:>3} {d['actual']:>+9.2f} {d['held']:>+9.2f} {d_delta:>+9.2f} {tag}")

# Per confidence
print(f"\n--- Per confidence (resolved only) ---")
by_conf = defaultdict(lambda: {'n':0,'actual':0,'held':0,'w':0,'l':0})
for r in resolved_rows:
    c = r['confidence']
    by_conf[c]['n'] += 1
    by_conf[c]['actual'] += r['actual']
    by_conf[c]['held'] += r['if_held']
    if r['our_won']:
        by_conf[c]['w'] += 1
    else:
        by_conf[c]['l'] += 1
print(f"{'conf':<6} {'n':>3} {'W':>3} {'L':>3} {'actual':>9} {'held':>9} {'delta':>9}")
for c in ['A','B+','B-','C','?']:
    if c not in by_conf: continue
    d = by_conf[c]
    print(f"  {c:<4} {d['n']:>3} {d['w']:>3} {d['l']:>3} {d['actual']:>+9.2f} {d['held']:>+9.2f} {d['actual']-d['held']:>+9.2f}")
