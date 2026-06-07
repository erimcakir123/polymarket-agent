"""Ana bot — TUM basket maclari, butun archive'lardan, scale-out dahil.

Tum nba/wnba trade'leri:
- Closed (exit_reason set)
- Partial exited (scale_out_realized_usdc > 0)
"""
import json
import httpx
import sys
import glob
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ana_audit = str(Path(__file__).resolve().parent.parent / "logs" / "audit")

# RECURSIVE — tum trade_history dosyalari
all_files = glob.glob(f"{ana_audit}/**/trade_history*.jsonl", recursive=True)
all_files.extend(glob.glob(f"{ana_audit}/**/positions*.json", recursive=True))
all_files = list(set(all_files))
print(f"Toplam dosya: {len(all_files)}", file=sys.stderr)

# Tum kayitlari topla — BASKET ONLY
basket = []
for f in all_files:
    if not f.endswith('.jsonl'):
        continue
    try:
        for l in open(f, encoding='utf-8'):
            if not l.strip(): continue
            try: r = json.loads(l)
            except: continue
            sport = (r.get('sport_tag') or '').lower()
            if sport in ('nba', 'wnba', 'basketball'):
                basket.append(r)
    except: pass

# Dedupe
seen = set()
unique = []
for r in basket:
    key = (r.get('condition_id'), r.get('entry_timestamp'))
    if key in seen: continue
    seen.add(key)
    unique.append(r)

print(f"Toplam unique basket trade: {len(unique)}", file=sys.stderr)

# Tarih dağılımı
date_count = defaultdict(int)
for r in unique:
    d = r.get('entry_timestamp', '')[:10]
    date_count[d] += 1
print(f"\nBASKET TRADE TARİH DAĞILIMI:")
for d, n in sorted(date_count.items()):
    print(f"  {d}: {n}")

# Closed + partials
closed = [r for r in unique if r.get('exit_reason') and r.get('exit_reason') != 'wipe_archived']
partials = [r for r in unique if (r.get('partial_exits') or []) or (r.get('scale_out_realized_usdc', 0) > 0)]
print(f"\nClosed (full exit, exit_reason set): {len(closed)}")
print(f"Pozisyonda partial exit (scale_out_realized > 0): {len(partials)}")


def fetch_resolved(token_id):
    try:
        r = httpx.get("https://gamma-api.polymarket.com/markets",
                      params={"clob_token_ids": token_id, "closed": "true"}, timeout=10)
        if r.status_code != 200 or not r.json():
            r2 = httpx.get("https://gamma-api.polymarket.com/markets",
                          params={"clob_token_ids": token_id}, timeout=10)
            if not r2.json(): return None
            data = r2.json()
        else: data = r.json()
        m = data[0] if isinstance(data, list) else data
        if not m.get('closed'): return None
        prices = json.loads(m['outcomePrices']) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices', [])
        token_ids = json.loads(m.get('clobTokenIds','[]')) if isinstance(m.get('clobTokenIds'), str) else m.get('clobTokenIds', [])
        return {'prices': [float(p) for p in prices], 'token_ids': token_ids}
    except: return None


print(f"\nResolution cekiliyor ({len(closed)} closed + {len(partials)} partial)...", file=sys.stderr)
to_check = list({(r.get('condition_id'), r.get('token_id'), r.get('entry_timestamp')): r for r in closed + partials}.values())
print(f"Unique to check: {len(to_check)}", file=sys.stderr)

resolved = []
for i, r in enumerate(to_check):
    if i % 20 == 0: print(f"  {i}/{len(to_check)}", file=sys.stderr)
    info = fetch_resolved(r.get('token_id',''))
    if info is None or not info['prices']:
        continue
    tid = r.get('token_id','')
    try: bot_idx = info['token_ids'].index(str(tid)) if str(tid) in info['token_ids'] else 0
    except: bot_idx = 0
    bot_res = info['prices'][bot_idx] if bot_idx < len(info['prices']) else 0
    r['_bot_won'] = bot_res > 0.5
    resolved.append(r)

n = len(resolved)
if n == 0:
    print("Resolved trade yok"); sys.exit()

bot_correct = sum(1 for r in resolved if r['_bot_won'])
market_correct = sum(1 for r in resolved if (r['entry_price'] > 0.5) == r['_bot_won'])
has_bm = [r for r in resolved if r.get('bookmaker_prob', 0) > 0.01]
bm_correct = sum(1 for r in has_bm if (r['bookmaker_prob'] > 0.5) == r['_bot_won'])

print(f"\n{'='*72}")
print(f"BASKET — {n} resolved trade (closed + partial-exit, tum tarihler)")
print(f"{'='*72}")
print(f"\n{'Kaynak':<30} {'Dogru':<8} {'Yanlis':<8} {'Dogruluk'}")
print("-" * 65)
print(f"{'BOT model':<30} {bot_correct:<8} {n-bot_correct:<8} {bot_correct/n*100:.1f}%")
print(f"{'MARKET (Polymarket entry)':<30} {market_correct:<8} {n-market_correct:<8} {market_correct/n*100:.1f}%")
if has_bm:
    print(f"{'BOOKMAKER (Odds API)':<30} {bm_correct:<8} {len(has_bm)-bm_correct:<8} {bm_correct/len(has_bm)*100:.1f}%  (n={len(has_bm)})")

# Net Realized PnL (closed exit_pnl + partial scale_out_realized)
total_pnl = 0
for r in resolved:
    if r.get('exit_reason'):
        total_pnl += r.get('exit_pnl_usdc', 0)
    else:
        total_pnl += r.get('scale_out_realized_usdc', 0)
print(f"\nNet realized (closed + partials): ${total_pnl:+.2f}")

# Confidence
print(f"\n## BASKET CONFIDENCE")
print(f"  {'Conf':<5} {'N':<5} {'Bot Acc':<10} {'BM Acc':<10} {'Net PnL'}")
print("  " + "-" * 55)
for conf in ['A', 'B']:
    items = [r for r in resolved if r.get('confidence') == conf]
    if not items: continue
    c_correct = sum(1 for r in items if r['_bot_won'])
    c_bm = [r for r in items if r.get('bookmaker_prob', 0) > 0.01]
    c_bm_correct = sum(1 for r in c_bm if (r['bookmaker_prob'] > 0.5) == r['_bot_won'])
    c_pnl = sum((r.get('exit_pnl_usdc', 0) if r.get('exit_reason') else r.get('scale_out_realized_usdc', 0)) for r in items)
    bm_str = f"{c_bm_correct/len(c_bm)*100:.0f}% (n={len(c_bm)})" if c_bm else "N/A"
    print(f"  {conf:<5} {len(items):<5} {c_correct/len(items)*100:.0f}%{'':<6} {bm_str:<10} ${c_pnl:+.2f}")

# Market type
print(f"\n## BASKET MARKET TYPE")
print(f"  {'Type':<25} {'N':<5} {'Bot Acc':<10} {'BM Acc':<10} {'Net PnL'}")
print("  " + "-" * 70)
mt_groups = defaultdict(list)
for r in resolved:
    smt = r.get('sports_market_type') or '?'
    mt_groups[smt].append(r)
for mt, items in sorted(mt_groups.items(), key=lambda x: -len(x[1])):
    c_correct = sum(1 for r in items if r['_bot_won'])
    c_bm = [r for r in items if r.get('bookmaker_prob', 0) > 0.01]
    c_bm_correct = sum(1 for r in c_bm if (r['bookmaker_prob'] > 0.5) == r['_bot_won'])
    bm_str = f"{c_bm_correct/len(c_bm)*100:.0f}%" if c_bm else "N/A"
    c_pnl = sum((r.get('exit_pnl_usdc', 0) if r.get('exit_reason') else r.get('scale_out_realized_usdc', 0)) for r in items)
    print(f"  {mt:<25} {len(items):<5} {c_correct/len(items)*100:.0f}%{'':<6} {bm_str:<10} ${c_pnl:+.2f}")
