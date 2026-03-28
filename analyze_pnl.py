import json

trades = []
with open("logs/trades.jsonl") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        t = json.loads(line)
        if t.get("action") == "EXIT":
            trades.append(t)

wins = []
losses = []
total = 0

for t in trades:
    pnl = t.get("pnl", 0)
    market = t["market"]
    reason = t["reason"]
    size = t.get("size", 0)
    price = t.get("price", 0)
    exit_price = t.get("exit_price", 0)
    direction = t.get("direction", "")

    total += pnl
    entry = (market, pnl, reason, size, price, exit_price, direction)
    if pnl >= 0:
        wins.append(entry)
    else:
        losses.append(entry)

print("=== WINS ===")
for m, p, r, s, ep, xp, d in sorted(wins, key=lambda x: -x[1]):
    print(f"  +${p:>7.2f}  {m[:42]:<42} | {r[:30]} | ${s:.0f} {d}")

print(f"\n=== LOSSES ===")
for m, p, r, s, ep, xp, d in sorted(losses, key=lambda x: x[1]):
    print(f"  -${abs(p):>7.2f}  {m[:42]:<42} | {r[:30]} | ${s:.0f} {d}")

total_invested = sum(s for _, _, _, s, _, _, _ in wins + losses)
print(f"\n=== SUMMARY ===")
print(f"Wins:   {len(wins)} trades, +${sum(p for _,p,_,_,_,_,_ in wins):.2f}")
print(f"Losses: {len(losses)} trades, -${abs(sum(p for _,p,_,_,_,_,_ in losses)):.2f}")
print(f"Total PnL: ${total:.2f}")
print(f"Win rate: {len(wins)}/{len(wins)+len(losses)} = {len(wins)/(len(wins)+len(losses))*100:.0f}%")
print(f"Total invested: ${total_invested:.2f}")
if total_invested > 0:
    print(f"ROI: {total/total_invested*100:.1f}%")

# Categorize by entry type
print(f"\n=== BY EXIT REASON ===")
reasons = {}
for t in trades:
    r = t["reason"].split(":")[0].strip()
    pnl = t.get("pnl", 0)
    if r not in reasons:
        reasons[r] = {"count": 0, "pnl": 0}
    reasons[r]["count"] += 1
    reasons[r]["pnl"] += pnl

for r, d in sorted(reasons.items(), key=lambda x: x[1]["pnl"]):
    print(f"  {r:<35} {d['count']} trades  ${d['pnl']:>+.2f}")

# Check remaining positions
print(f"\n=== REMAINING POSITIONS ===")
buys = {}
for line in open("logs/trades.jsonl"):
    line = line.strip()
    if not line:
        continue
    t = json.loads(line)
    action = t.get("action", "")
    market = t.get("market", "")
    if action in ("BUY", "LIVE_DIP_BUY_YES", "LIVE_DIP_BUY_NO", "BOND_ENTRY"):
        buys[market] = t
    elif action == "EXIT":
        buys.pop(market, None)

for m, t in buys.items():
    size = t.get("size_usdc", t.get("size", 0))
    price = t.get("entry_price", t.get("price", 0))
    direction = t.get("direction", t.get("action", ""))
    print(f"  OPEN: {m[:50]:<50} | ${size:.1f} @ {price} {direction}")
