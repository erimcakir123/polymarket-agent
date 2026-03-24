import json
from datetime import datetime, timezone, timedelta

# Load positions
with open('logs/positions.json') as f:
    positions = json.load(f)

# Load trades for exits
exits = []
buys = []
with open('logs/trades.jsonl') as f:
    for line in f:
        t = json.loads(line)
        if t.get('action') == 'EXIT':
            exits.append(t)
        elif t.get('action') in ('BUY_YES', 'BUY_NO') and not t.get('rejected'):
            buys.append(t)

print('=== CURRENT POSITIONS ===')
total_invested = 0
total_pnl = 0
for cid, p in positions.items():
    entry = p['entry_price']
    current = p.get('current_price', entry)
    size = p['size_usdc']
    shares = p['shares']
    direction = p['direction']

    if direction == 'BUY_NO':
        eff_entry = 1 - entry
        eff_current = 1 - current
    else:
        eff_entry = entry
        eff_current = current

    current_value = shares * eff_current
    pnl = current_value - size
    pnl_pct = (pnl / size * 100) if size > 0 else 0
    total_invested += size
    total_pnl += pnl

    status = '+' if pnl >= 0 else '-'
    pending = ' [PENDING]' if p.get('pending_resolution') else ''
    slug = p["slug"][:42]
    print(f'  {status} {slug:42s} | {direction:8s} | entry={eff_entry:.1%} now={eff_current:.1%} | ${size:.0f} | PnL=${pnl:+.2f} ({pnl_pct:+.1f}%){pending}')

print(f'\nTotal positions: {len(positions)}')
print(f'Total invested: ${total_invested:.2f}')
print(f'Total unrealized PnL: ${total_pnl:+.2f}')

print(f'\n=== EXITS (last 24h) ===')
cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
recent_exits = []
for e in exits:
    ts = e.get('timestamp', '')
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            if dt > cutoff:
                recent_exits.append(e)
        except:
            pass

if recent_exits:
    total_exit_pnl = 0
    for e in recent_exits:
        pnl = e.get('pnl', 0)
        total_exit_pnl += pnl
        status = 'W' if pnl >= 0 else 'L'
        market = e["market"][:42]
        reason = e.get("reason", "?")[:20]
        print(f'  {status} {market:42s} | {reason:20s} | PnL=${pnl:+.2f}')
    print(f'  Total realized (24h): ${total_exit_pnl:+.2f}')
else:
    print('  No exits in last 24 hours')

# Bankroll
with open('logs/portfolio_state.json') as f:
    state = json.load(f)
bankroll = state.get("bankroll", 0)
realized = state.get("realized_pnl", 0)
total_value = bankroll + total_invested + total_pnl

print(f'\n=== BANKROLL ===')
print(f'  Cash available: ${bankroll:.2f}')
print(f'  Invested: ${total_invested:.2f}')
print(f'  Realized PnL (all time): ${realized:+.2f}')
print(f'  Unrealized PnL: ${total_pnl:+.2f}')
print(f'  Starting: $1000 | Current value: ${total_value:.2f} ({(total_value/1000-1)*100:+.1f}%)')

print(f'\n=== TRADE STATS ===')
print(f'  Total BUY entries: {len(buys)}')
print(f'  Total EXITs: {len(exits)}')
wins = sum(1 for e in exits if e.get('pnl', 0) > 0)
losses = sum(1 for e in exits if e.get('pnl', 0) < 0)
print(f'  Wins: {wins} | Losses: {losses} | Win rate: {wins/(wins+losses)*100:.0f}%' if wins+losses > 0 else '  No completed trades')
