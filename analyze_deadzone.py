import json

TRADES_FILE = "logs/trades.jsonl"

buys = {}
exits = {}

with open(TRADES_FILE) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        t = json.loads(line)
        action = t.get("action", "")
        market = t.get("market", "")
        if action == "BUY":
            buys[market] = {
                "reason": t.get("entry_reason", ""),
                "direction": t.get("direction", ""),
                "edge": t.get("edge", 0),
                "consensus": t.get("is_consensus", False),
                "ai_prob": t.get("ai_prob", 0),
                "price": t.get("entry_price", 0),
                "size": t.get("size_usdc", 0),
            }
        elif action == "EXIT":
            exits[market] = t

for label, filter_reason in [("DEADZONE", "deadzone"), ("WINNER", "winner")]:
    trades = [(m, b) for m, b in buys.items() if b["reason"] == filter_reason]
    wins = 0
    losses = 0
    total_pnl = 0
    print(f"\n{'='*70}")
    print(f"{label} TRADES ({len(trades)} total)")
    print(f"{'='*70}")
    for m, b in trades:
        e = exits.get(m)
        if e:
            pnl = e.get("pnl", 0)
            exit_reason = e.get("reason", "?")
            status = "WIN" if pnl >= 0 else "LOSS"
            if pnl >= 0:
                wins += 1
            else:
                losses += 1
            total_pnl += pnl
        else:
            pnl = 0
            exit_reason = "STILL OPEN"
            status = "OPEN"
        print(f"  {status:4} ${pnl:>+8.2f}  edge={b['edge']*100:>+5.1f}%  AI={b['ai_prob']*100:.0f}%  {b['direction']:8}  {m[:40]}  | {exit_reason[:30]}")

    print(f"\n  Summary: {wins}W {losses}L | PnL: ${total_pnl:>+.2f}")
    if wins + losses > 0:
        print(f"  Win rate: {wins/(wins+losses)*100:.0f}%")
