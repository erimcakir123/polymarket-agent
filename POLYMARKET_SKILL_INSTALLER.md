# =============================================================================
# POLYMARKET AGENT — SKILL INSTALLER
# =============================================================================
#
# BU DOSYAYI CLAUDE CODE'A YAPISTIR VE ŞU KOMUTU VER:
#
#   "Bu dosyadaki tüm skill'leri ~/.claude/skills/ altına kur.
#    Sonra CLAUDE.md snippet'ini ~/.claude/CLAUDE.md'ye ekle."
#
# Claude Code otomatik olarak:
#   1. ~/.claude/skills/ altında 4 klasör oluşturacak
#   2. Her SKILL.md dosyasını doğru yere yazacak
#   3. CLAUDE.md'ye Polymarket skill referanslarını ekleyecek
#
# Alternatif olarak kendin terminal'den kurabilirsin:
#   Aşağıdaki "MANUAL INSTALL" bölümündeki komutları çalıştır.
#
# =============================================================================


# =============================================================================
# MANUAL INSTALL — Terminal komutları (opsiyonel, Claude Code'a da yaptırabilirsin)
# =============================================================================
#
# Adım 1: Klasörleri oluştur
#
#   mkdir -p ~/.claude/skills/polymarket-api/references
#   mkdir -p ~/.claude/skills/ai-signal-engine
#   mkdir -p ~/.claude/skills/trading-risk-manager
#   mkdir -p ~/.claude/skills/polymarket-executor
#
# Adım 2: Bu dosyayı indirdiğin yere git ve skill dosyalarını kopyala
#   (Dosyaları buradan indirdin, outputs klasöründe)
#
#   cp polymarket-skills/polymarket-api/SKILL.md ~/.claude/skills/polymarket-api/
#   cp polymarket-skills/polymarket-api/references/authentication.md ~/.claude/skills/polymarket-api/references/
#   cp polymarket-skills/ai-signal-engine/SKILL.md ~/.claude/skills/ai-signal-engine/
#   cp polymarket-skills/trading-risk-manager/SKILL.md ~/.claude/skills/trading-risk-manager/
#   cp polymarket-skills/polymarket-executor/SKILL.md ~/.claude/skills/polymarket-executor/
#
# Adım 3: CLAUDE.md'ye Polymarket bloğunu ekle
#   (CLAUDE_MD_SNIPPET.md içeriğini ~/.claude/CLAUDE.md'nin sonuna yapıştır)
#
# =============================================================================


# =============================================================================
# SKILL 1/4: polymarket-api
# Dosya: ~/.claude/skills/polymarket-api/SKILL.md
# =============================================================================

"""
---
name: polymarket-api
description: >
  Polymarket API integration — market discovery, price data, order books, and
  WebSocket feeds. Use this skill whenever the user asks to fetch markets, get
  prices, read order books, query market data, connect to Polymarket, set up
  API clients, authenticate with CLOB, parse market metadata, stream real-time
  prices, or build any data pipeline that touches Polymarket endpoints. Also
  trigger when the user mentions "Gamma API", "CLOB API", "Polymarket data",
  "market discovery", "token_id", "condition_id", "order book", "midpoint",
  "py-clob-client", "polymarket-gamma", or asks "how do I get market data
  from Polymarket". Even if the user just says "fetch markets" or "show me
  Polymarket prices" without specifying the API, use this skill.
---

# Polymarket API Integration Skill

## Architecture Overview

Polymarket has 4 API layers:

| Layer | Base URL | Auth | Use For |
|-------|----------|------|---------|
| Gamma | https://gamma-api.polymarket.com | None | Market discovery, metadata |
| CLOB | https://clob.polymarket.com | L1/L2 for writes | Order book, prices, trading |
| Data | https://data-api.polymarket.com | None | User positions, activity, PnL |
| WebSocket | wss://ws-subscriptions-clob.polymarket.com/ws/market | None | Real-time price updates |

## Data Hierarchy

Event (slug, event_id) → Market (condition_id) → YES/NO outcomes → Tokens (token_id)

YES price + NO price ≈ $1.00 always.

## Gamma API — Market Discovery (NO AUTH)

GET /markets?active=true&closed=false&limit=100&order=volume24hr&ascending=false
GET /markets/{condition_id}
GET /events?active=true&limit=50
GET /events/{event_id}

CRITICAL: outcomePrices, outcomes, clobTokenIds are JSON STRINGS → always json.loads()

```python
import requests, json

GAMMA_BASE = "https://gamma-api.polymarket.com"

def fetch_active_markets(limit=100, min_volume_24h=5000, min_liquidity=1000, tag=None):
    params = {"active": "true", "closed": "false", "limit": limit,
              "order": "volume24hr", "ascending": "false"}
    if tag: params["tag"] = tag
    resp = requests.get(f"{GAMMA_BASE}/markets", params=params)
    resp.raise_for_status()
    result = []
    for m in resp.json():
        vol = float(m.get("volume24hr", 0) or 0)
        liq = float(m.get("liquidity", 0) or 0)
        if vol < min_volume_24h or liq < min_liquidity: continue
        prices = json.loads(m.get("outcomePrices", '["0.5","0.5"]'))
        tokens = json.loads(m.get("clobTokenIds", '["",""]'))
        m["_yes_price"] = float(prices[0])
        m["_no_price"] = float(prices[1])
        m["_yes_token"] = tokens[0]
        m["_no_token"] = tokens[1]
        result.append(m)
    return result
```

## CLOB API — Prices & Trading

Read-only (no auth):
```python
from py_clob_client.client import ClobClient
client = ClobClient("https://clob.polymarket.com")
mid = client.get_midpoint(token_id)
price = client.get_price(token_id, side="BUY")
book = client.get_order_book(token_id)
spread = client.get_spread(token_id)
```

Authenticated:
```python
import os
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

client = ClobClient("https://clob.polymarket.com",
    key=os.environ["PRIVATE_KEY"], chain_id=137,
    signature_type=int(os.environ.get("SIGNATURE_TYPE", "0")),
    funder=os.environ.get("PROXY_WALLET_ADDRESS"))
client.set_api_creds(ApiCreds(
    api_key=os.environ["POLY_API_KEY"],
    api_secret=os.environ["POLY_API_SECRET"],
    api_passphrase=os.environ["POLY_API_PASSPHRASE"]))
```

Trading:
```python
from py_clob_client.clob_types import OrderArgs, MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

# Limit order
order = OrderArgs(token_id=TID, price=0.55, size=10.0, side=BUY)
signed = client.create_order(order)
resp = client.post_order(signed, OrderType.GTC)

# Market order (Fill or Kill)
mo = MarketOrderArgs(token_id=TID, amount=25.0, side=BUY)
signed = client.create_market_order(mo)
resp = client.post_order(signed, OrderType.FOK)

# Cancel
client.cancel(order_id)
client.cancel_all()
```

Price history:
GET https://clob.polymarket.com/prices-history?market={token_id}&interval=1d&fidelity=60

## WebSocket
```python
import asyncio, json, websockets
async def stream_prices(token_ids, callback):
    async with websockets.connect("wss://ws-subscriptions-clob.polymarket.com/ws/market") as ws:
        for tid in token_ids:
            await ws.send(json.dumps({"type":"subscribe","market":tid,"channel":"price"}))
        async for msg in ws:
            await callback(json.loads(msg))
```

## Dependencies
pip install py-clob-client requests websockets python-dotenv pydantic

## Pitfalls
1. outcomePrices/outcomes/clobTokenIds = JSON strings, always json.loads()
2. token_id for prices, condition_id for CLOB orders
3. signature_type: 0=EOA, 1=email/Magic, 2=browser wallet
4. EOA needs on-chain allowances before first trade
5. Min order: $5 USDC, tick size: $0.01
"""


# =============================================================================
# SKILL 1 REFERENCE: authentication.md
# Dosya: ~/.claude/skills/polymarket-api/references/authentication.md
# =============================================================================

"""
# Polymarket Authentication Reference

## Three Auth Levels

Level 0 (no auth): read-only — prices, order books, markets
Level 1 (private key): EIP-712 signing — derive API credentials
Level 2 (API key): HMAC-SHA256 — trading, orders, positions

## Signature Types
| Type | Value | Use |
|------|-------|-----|
| EOA | 0 | MetaMask, hardware wallet |
| Email/Magic | 1 | Polymarket email login |
| Browser Wallet | 2 | Coinbase Wallet via proxy |

For types 1 & 2: must provide funder= (proxy wallet from polymarket.com/settings)

## Generate Credentials (run once, save to .env)
```python
from py_clob_client.client import ClobClient
client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
creds = client.create_or_derive_api_creds()
# Save: creds.api_key, creds.api_secret, creds.api_passphrase
```

## EOA Token Allowances
Must approve USDC + CTF contracts on Polygon before first trade.
Email/Magic wallets skip this — allowances are automatic.
Key contracts: USDC 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174,
CTF 0x4D97DCd97eC945f40cF65F87097ACe5EA0476045,
Exchange 0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E
"""


# =============================================================================
# SKILL 2/4: ai-signal-engine
# Dosya: ~/.claude/skills/ai-signal-engine/SKILL.md
# =============================================================================

"""
---
name: ai-signal-engine
description: >
  AI-powered prediction market signal generation using Claude API. Use this skill
  whenever the user wants to build probability estimation, market analysis, AI
  forecasting, signal generation, edge detection, or news-driven analysis for
  prediction markets. Also trigger for "AI analyzer", "Claude API for predictions",
  "probability estimation", "superforecaster", "signal engine", "edge calculation",
  "sinyal motoru", "market mispricing", or "how should the AI analyze markets".
---

# AI Signal Engine Skill

Pipeline: Market Data → AI Probability → Edge Calculator → Signal Combiner → BUY/SELL/HOLD

## 1. AI Probability Estimator

System prompt — calibrated superforecaster:
```python
AI_SYSTEM_PROMPT = '''You are an expert superforecaster. Estimate probabilities for prediction market questions.
Rules:
1. Start with base rate, update incrementally with evidence
2. Consider both sides — why it might AND might not happen
3. Account for time remaining until resolution
4. Be calibrated — 70% should resolve YES ~70% of the time
5. Respond with ONLY JSON, no markdown

Output: {"probability": 0.XX, "confidence": "low|medium|high",
"reasoning": "...", "base_rate": "...",
"key_evidence_for": [...], "key_evidence_against": [...],
"risks_to_estimate": [...]}'''
```

Calling Claude:
```python
import anthropic, json

def estimate_probability(market, news_items=None, model="claude-sonnet-4-20250514"):
    client = anthropic.Anthropic()
    prompt = f'''Question: {market["question"]}
Description: {market.get("description", "")}
Market price (YES): ${market["_yes_price"]:.2f}
Resolution: {market.get("end_date_iso", "Unknown")}
Provide your independent probability estimate as JSON.'''

    resp = client.messages.create(model=model, max_tokens=1024,
        system=AI_SYSTEM_PROMPT, messages=[{"role":"user","content":prompt}])
    text = resp.content[0].text.strip()
    if text.startswith("```"): text = text.split("\n",1)[1].rsplit("```",1)[0]
    return json.loads(text)
```

## 2. Edge Calculation

```python
from dataclasses import dataclass
from enum import Enum

class Direction(Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    HOLD = "HOLD"

def calculate_edge(ai_prob, market_yes_price, min_edge=0.06, confidence="medium"):
    thresholds = {"low": 1.5, "medium": 1.0, "high": 0.75}
    adjusted = min_edge * thresholds.get(confidence, 1.0)
    raw = ai_prob - market_yes_price

    if raw > adjusted:    return Direction.BUY_YES, raw
    elif raw < -adjusted: return Direction.BUY_NO, abs(raw)
    else:                 return Direction.HOLD, abs(raw)
```

## 3. Additional Signals

Momentum: price trend over 1h/6h/24h → -1 to +1
Volume spike: volume_24h / avg_7d → 0 (normal) to 1 (spike)
Spread: bid-ask spread → 0 (wide=avoid) to 1 (tight=safe)

## 4. Arbitrage Detection

Multi-outcome events: sum of YES prices should ≈ $1.00
If sum > 1.05 → sell overpriced outcomes
If sum < 0.95 → buy underpriced outcomes

## 5. Cost Management

Use claude-sonnet-4-20250514 (not Opus) — ~$0.01-0.03 per analysis
Cache estimates 15-30 min, only analyze top 10-20 markets per cycle
"""


# =============================================================================
# SKILL 3/4: trading-risk-manager
# Dosya: ~/.claude/skills/trading-risk-manager/SKILL.md
# =============================================================================

"""
---
name: trading-risk-manager
description: >
  Risk management and position sizing for prediction market trading. Use this
  skill for risk management, Kelly criterion, position sizing, stop-loss,
  portfolio limits, bankroll management, exposure tracking, drawdown protection,
  or "how much should I bet". Also trigger for "risk yönetimi", "pozisyon boyutu",
  "Kelly formülü", "stop loss", "max drawdown", "portfolio tracking".
  This is the most important module — its rules must NEVER be bypassed.
---

# Trading Risk Manager Skill

## Iron Rules (NEVER break these)

1. Max portfolio deployment: never exceed max_portfolio_usdc total (default $500)
2. Max single bet: never exceed max_single_bet_usdc per market (default $75)
3. Max portfolio %: never put >max_bet_pct (15%) in one position
4. Max concurrent positions: hard cap on open positions
5. Min liquidity: never trade below min_liquidity threshold
6. Stop-loss: exit if position loses >stop_loss_pct (30%) of entry value
7. Dry-run safety: NEVER execute real orders in dry_run/paper mode
8. Correlation cap: max 30% in correlated markets
9. Cool-down: pause after 3 consecutive losses

## Kelly Criterion

```python
def kelly_position_size(ai_prob, market_price, bankroll,
                        kelly_fraction=0.50,  # HALF-KELLY (orta risk profili)
                        max_bet_usdc=75, max_bet_pct=0.15,
                        direction="BUY_YES"):
    if direction == "BUY_YES":
        p, cost = ai_prob, market_price
    else:
        p, cost = 1 - ai_prob, 1 - market_price

    q = 1 - p
    b = (1 - cost) / cost  # Net odds
    full_kelly = max(0, (p * b - q) / b) if b > 0 else 0
    actual = full_kelly * kelly_fraction

    bet = min(bankroll * actual, max_bet_usdc, bankroll * max_bet_pct, bankroll)
    return max(0, bet)
```

Why half-Kelly: Full Kelly = max growth but extreme volatility.
Half-Kelly = ~75% of full growth rate with much lower drawdown risk. Best for mid-risk profiles.

## Risk Manager — Gatekeeper

Every signal passes through here. Can downsize or reject any trade:
- Check portfolio capacity
- Check single bet limit
- Check portfolio % limit
- Check position count
- Check correlation exposure
- Check cool-down status
- Check confidence level

## Stop-Loss Monitor

Run every cycle:
```python
def check_stop_losses(portfolio, stop_loss_pct=0.30):
    return [slug for slug, pos in portfolio.positions.items()
            if pos.unrealized_pnl_pct < -stop_loss_pct]
```

## Correlation Tags

Auto-tag markets: "us-politics", "crypto", "fed", "ai", "geopolitics"
Cap correlated exposure at 30% of portfolio.
"""


# =============================================================================
# SKILL 4/4: polymarket-executor
# Dosya: ~/.claude/skills/polymarket-executor/SKILL.md
# =============================================================================

"""
---
name: polymarket-executor
description: >
  Order execution, trade lifecycle, and the main agent loop for Polymarket.
  Use for placing orders, executing trades, the main loop, order management,
  dry-run mode, paper trading, going live, or agent orchestration. Also trigger
  for "order execution", "emir gönder", "bot loop", "dry run", "live trading",
  "agent çalıştır", "FOK order", "GTC order", "limit order", "market order".
---

# Polymarket Executor Skill

## Operating Modes

| Mode | Orders | Money |
|------|--------|-------|
| dry_run | Simulated in logs | None |
| paper | Simulated with price tracking | None |
| live | Real orders on CLOB | Real USDC |

ALWAYS start with dry_run. Never skip to live.

## Order Types

GTC: Good Till Cancelled — default for value trades
FOK: Fill or Kill — for immediate execution (stop-loss exits)
GTD: Good Till Date — auto-cancel at expiry

## Main Agent Loop

```
Every N minutes:
  1. Fetch active markets (Gamma API)
  2. Update position prices (CLOB midpoints)
  3. Check stop-losses → exit if triggered
  4. Check take-profits → exit if triggered
  5. Analyze top 10-20 markets (AI signal engine)
  6. For each signal with edge:
     a. Calculate Kelly position size
     b. Run through risk manager
     c. If approved → execute order
     d. Update portfolio
  7. Log portfolio summary
  8. Sleep until next cycle
```

## Execution Pattern

```python
from py_clob_client.clob_types import OrderArgs, MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

# Limit order (GTC)
order = OrderArgs(token_id=tid, price=0.55, size=10.0, side=BUY)
signed = client.create_order(order)
resp = client.post_order(signed, OrderType.GTC)

# Market order for exits (FOK)
mo = MarketOrderArgs(token_id=tid, amount=shares, side=SELL)
signed = client.create_market_order(mo)
resp = client.post_order(signed, OrderType.FOK)
```

## Trade Logging

Log every trade to JSONL: timestamp, market, direction, size, price, edge, mode, status

## Getting Started Checklist

1. Set up .env with wallet credentials
2. Generate API keys (run once)
3. Set allowances if EOA wallet
4. config.yaml with conservative settings
5. dry_run for 24-48h → review logs
6. paper mode for 1-2 weeks → track PnL
7. live with $5-10 bets → gradually increase

## Dependencies
pip install py-clob-client anthropic requests websockets python-dotenv pydantic pyyaml
"""


# =============================================================================
# CLAUDE.md SNIPPET
# Bu bloğu ~/.claude/CLAUDE.md dosyasının SONUNA ekle
# =============================================================================

"""
## Polymarket Agent Skills

When working on the Polymarket prediction market agent project, these skills are available:

| Skill | Path | Trigger |
|-------|------|---------|
| polymarket-api | ~/.claude/skills/polymarket-api/SKILL.md | Polymarket API, market data, CLOB, Gamma |
| ai-signal-engine | ~/.claude/skills/ai-signal-engine/SKILL.md | AI analysis, probability, edge, signals |
| trading-risk-manager | ~/.claude/skills/trading-risk-manager/SKILL.md | Risk, Kelly, position sizing, stop-loss |
| polymarket-executor | ~/.claude/skills/polymarket-executor/SKILL.md | Execution, main loop, orders, dry-run |

Rules:
1. Always read the relevant SKILL.md before writing code
2. Risk manager has veto power — no trade bypasses risk checks
3. Default to dry_run mode. Never suggest live without explicit confirmation
4. Never hardcode secrets — always use .env
5. Type hints on all functions, Pydantic for models, log every decision
"""
