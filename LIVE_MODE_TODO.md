# Live Mode — Pre-Launch Checklist

Features to implement before switching from dry_run to live trading.

## Must-Have

### Order Book Depth Analysis (from poly-maker)
- Before placing orders, check CLOB order book depth
- Skip thin levels (< $500 liquidity)
- Step one tick ahead of best bid/ask for better fill
- Respect spread boundaries (don't cross spread)
- Check bid/ask volume ratio for direction signal
- Reference: [poly-maker](https://github.com/warproxxx/poly-maker) — production market maker with smart order placement
- Files to modify: `src/executor.py`

### Smart Order Management (from poly-maker)
- Only cancel/replace orders when price diff > 0.5 cents or size diff > 10%
- Avoid unnecessary order churn (saves gas, reduces footprint)
- Per-market async locks to prevent race conditions

### Fill Rate Tracking
- Log whether orders actually filled (FOK vs GTC)
- Track slippage: expected price vs actual fill price
- Adjust order strategy based on historical fill rates

### Real Wallet Integration
- Verify `src/wallet.py` balance checks work with Polygon mainnet
- Test CLOB client authentication flow
- Ensure API key derivation works

### Penny Token Scalping (user idea)
- Buy extreme underdog tokens at 1-3¢ in lopsided markets (95%+ favorite)
- Target: 2x exit (1¢→2¢, 2¢→4¢) — don't hold to resolution
- Any in-game event (goal, foul, run) causes temporary spike
- Requires: WebSocket for real-time price tracking (can't catch 1→2¢ with 3min polling)
- Requires: Order book depth check (liquidity is very thin at 1-3¢)
- Risk: token goes to 0 = small fixed loss. Reward: 2-3x quick flip
- Extends VS module: lower min_token_price from 3¢ to 1¢, add quick-exit 2x rule

## Should-Have

### WebSocket Price Feed (from poly-maker)
- Replace polling with WebSocket for real-time order book updates
- React in milliseconds to price changes instead of 3-30 min cycles
- Critical for VS module and stop-loss triggers

### Position Merging (from poly-maker)
- When holding both YES and NO tokens on same market, merge to free capital
- Reference: poly-maker's merge logic
- Reduces locked collateral

### Stop-Loss Volatility Gate (from poly-maker)
- Before triggering stop-loss, check 3-hour volatility
- If spread is tight and volatility is low, delay exit (temporary dip)
- Prevents stop-loss hunting in thin markets

## Nice-to-Have

### Anti-Reversal Guard (from poly-maker)
- Don't buy more of one outcome if already holding significant position in opposite outcome

### Incentive-Aware Pricing (from poly-maker)
- Check against Polymarket's incentive threshold
- Factor rewards into effective edge calculation

### On-Chain Whale Monitoring (from echandsome)
- Decode Polygon transactions for large buy/sell signals
- WSS connection to Polygon for real-time block receipts
- Use as additional signal (whale buys = confidence boost)
