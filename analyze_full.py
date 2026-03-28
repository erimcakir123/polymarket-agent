import json

exits = []
with open("logs/trades.jsonl") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        t = json.loads(line)
        if t.get("action") == "EXIT":
            exits.append(t)

print("=" * 80)
print("FULL EXIT ANALYSIS — All resolved trades")
print("=" * 80)

total_pnl = 0
total_invested = 0
wins = 0
losses = 0

# What-if: with 15% stop-loss
sl_pnl = 0
SL_PCT = 0.15

for t in exits:
    pnl = t.get("pnl", 0)
    size = t.get("size", 0)
    price = t.get("price", 0)
    market = t["market"]
    reason = t["reason"]
    direction = t.get("direction", "")

    total_pnl += pnl
    total_invested += size

    if pnl >= 0:
        wins += 1
        sl_pnl += pnl  # wins stay the same
    else:
        losses += 1
        # With stop-loss: max loss is SL_PCT of position size
        max_loss = -size * SL_PCT
        capped_loss = max(pnl, max_loss)  # cap the loss
        sl_pnl += capped_loss

    status = "WIN" if pnl >= 0 else "LOSS"
    sl_loss = max(pnl, -size * SL_PCT) if pnl < 0 else pnl
    saved = sl_loss - pnl if pnl < 0 else 0

    print(f"  {status:4} ${pnl:>+8.2f}  {market[:45]:<45} | {reason[:30]}")
    if saved > 0:
        print(f"         SL would cap at ${sl_loss:>+8.2f}  (saved ${saved:.2f})")

print(f"\n{'=' * 80}")
print(f"ACTUAL RESULTS")
print(f"{'=' * 80}")
print(f"  Wins:     {wins} trades  +${sum(t.get('pnl',0) for t in exits if t.get('pnl',0)>=0):.2f}")
print(f"  Losses:   {losses} trades  -${abs(sum(t.get('pnl',0) for t in exits if t.get('pnl',0)<0)):.2f}")
print(f"  Win rate: {wins}/{wins+losses} = {wins/(wins+losses)*100:.0f}%")
print(f"  Total PnL:      ${total_pnl:>+.2f}")
print(f"  Total invested: ${total_invested:.2f}")
if total_invested > 0:
    print(f"  ROI:            {total_pnl/total_invested*100:.1f}%")

print(f"\n{'=' * 80}")
print(f"WITH 15% STOP-LOSS")
print(f"{'=' * 80}")
print(f"  Total PnL:      ${sl_pnl:>+.2f}")
if total_invested > 0:
    print(f"  ROI:            {sl_pnl/total_invested*100:.1f}%")
print(f"  Savings:        ${sl_pnl - total_pnl:.2f}")

# Also check with different SL levels
print(f"\n{'=' * 80}")
print(f"STOP-LOSS SENSITIVITY ANALYSIS")
print(f"{'=' * 80}")
for sl in [0.10, 0.12, 0.15, 0.20, 0.25, 0.30]:
    test_pnl = 0
    for t in exits:
        pnl = t.get("pnl", 0)
        size = t.get("size", 0)
        if pnl >= 0:
            test_pnl += pnl
        else:
            test_pnl += max(pnl, -size * sl)
    roi = test_pnl / total_invested * 100 if total_invested > 0 else 0
    print(f"  SL {sl*100:>4.0f}%: PnL=${test_pnl:>+8.2f}  ROI={roi:>+.1f}%")

# Avg win vs avg loss
avg_win = sum(t.get('pnl',0) for t in exits if t.get('pnl',0)>=0) / max(wins, 1)
avg_loss = abs(sum(t.get('pnl',0) for t in exits if t.get('pnl',0)<0)) / max(losses, 1)
print(f"\n  Avg win:  ${avg_win:.2f}")
print(f"  Avg loss: ${avg_loss:.2f}")
print(f"  Win/Loss ratio: {avg_win/avg_loss:.2f}")
print(f"  Need win rate > {avg_loss/(avg_win+avg_loss)*100:.0f}% to break even")
