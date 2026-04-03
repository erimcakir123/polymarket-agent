# Polymarket API — Complete Developer Guide

> **Purpose:** Antigravity-ready reference for integrating Polymarket prediction market APIs into Optimus Claudeus or any trading bot.
>
> **Source:** https://docs.polymarket.com/api-reference/introduction
>
> **Network:** Polygon Mainnet (Chain ID: 137)
>
> **Currency:** USDC (on Polygon)

---

## Table of Contents

1. [Overview & Base URLs](#1-overview--base-urls)
2. [Authentication](#2-authentication)
3. [Rate Limits](#3-rate-limits)
4. [Clients & SDKs](#4-clients--sdks)
5. [Events Endpoints](#5-events-endpoints)
6. [Markets Endpoints](#6-markets-endpoints)
7. [Orderbook & Pricing Endpoints](#7-orderbook--pricing-endpoints)
8. [Orders Endpoints (Authenticated)](#8-orders-endpoints-authenticated)
9. [Trades Endpoints](#9-trades-endpoints)
10. [CLOB Markets Endpoints](#10-clob-markets-endpoints)
11. [Profile & Positions Endpoints](#11-profile--positions-endpoints)
12. [Leaderboard Endpoints](#12-leaderboard-endpoints)
13. [Rewards & Rebates Endpoints](#13-rewards--rebates-endpoints)
14. [Search Endpoint](#14-search-endpoint)
15. [Tags Endpoints](#15-tags-endpoints)
16. [Series Endpoints](#16-series-endpoints)
17. [Comments Endpoints](#17-comments-endpoints)
18. [Sports Endpoints](#18-sports-endpoints)
19. [Bridge Endpoints](#19-bridge-endpoints)
20. [Relayer Endpoints](#20-relayer-endpoints)
21. [Builders Endpoints](#21-builders-endpoints)
22. [WebSocket Channels](#22-websocket-channels)
23. [Python Client Template](#23-python-client-template)
24. [All Documentation Page Links](#24-all-documentation-page-links)

---

## 1. Overview & Base URLs

Polymarket is served by **three separate APIs**, each handling a different domain:

| API | Base URL | Auth Required | Purpose |
|-----|----------|---------------|---------|
| **Gamma API** | `https://gamma-api.polymarket.com` | No | Markets, events, tags, series, comments, sports, search, public profiles |
| **Data API** | `https://data-api.polymarket.com` | No | User positions, trades, activity, holder data, open interest, leaderboards, builder analytics |
| **CLOB API** | `https://clob.polymarket.com` | Partial | Orderbook data, pricing, midpoints, spreads, price history. Order placement/cancellation (authenticated) |
| **Bridge API** | `https://bridge.polymarket.com` | No | Deposits and withdrawals (proxy of fun.xyz) |

### Auth Summary
- **Gamma API + Data API:** Fully public, no auth needed
- **CLOB API read endpoints** (orderbook, prices, spreads): No auth needed
- **CLOB API trading endpoints** (orders, cancellation, heartbeat): Requires L2 auth headers

---

## 2. Authentication

The CLOB API uses **two levels** of authentication:

### L1 Authentication (Private Key)
- Uses wallet's private key to sign an EIP-712 message
- Proves ownership of the wallet
- **Used for:** Creating/deriving API credentials, signing orders locally

### L2 Authentication (API Key)
- Uses API credentials (apiKey, secret, passphrase) generated from L1
- Requests signed using HMAC-SHA256
- **Used for:** Cancel/get orders, check balances, post signed orders

### Getting API Credentials

```python
from py_clob_client.client import ClobClient
import os

client = ClobClient(
    host="https://clob.polymarket.com",
    chain_id=137,
    key=os.getenv("PRIVATE_KEY")
)

credentials = client.create_or_derive_api_creds()
# Returns: { "apiKey": "...", "secret": "...", "passphrase": "..." }
```

### REST API Credential Endpoints

| Method | URL | Purpose |
|--------|-----|---------|
| POST | `https://clob.polymarket.com/auth/api-key` | Create new API credentials |
| GET | `https://clob.polymarket.com/auth/derive-api-key` | Derive existing API credentials |

### L1 Headers (for credential creation)

| Header | Description |
|--------|-------------|
| `POLY_ADDRESS` | Polygon signer address |
| `POLY_SIGNATURE` | CLOB EIP-712 signature |
| `POLY_TIMESTAMP` | Current UNIX timestamp |
| `POLY_NONCE` | Nonce (default: 0) |

### L2 Headers (for all trading endpoints)

| Header | Description |
|--------|-------------|
| `POLY_ADDRESS` | Polygon signer address |
| `POLY_SIGNATURE` | HMAC-SHA256 signature (using API secret) |
| `POLY_TIMESTAMP` | Current UNIX timestamp |
| `POLY_API_KEY` | API key value |
| `POLY_PASSPHRASE` | API passphrase value |

### Signature Types

| Type | Value | Description |
|------|-------|-------------|
| EOA | `0` | Standard Ethereum wallet (MetaMask). Needs POL for gas. |
| POLY_PROXY | `1` | Custom proxy wallet (Magic Link email/Google login users) |
| GNOSIS_SAFE | `2` | Gnosis Safe multisig proxy (most common for new users) |

### Authenticated Client Setup

```python
from py_clob_client.client import ClobClient
import os

client = ClobClient(
    host="https://clob.polymarket.com",
    chain_id=137,
    key=os.getenv("PRIVATE_KEY"),
    creds=api_creds,        # From create_or_derive_api_creds()
    signature_type=1,        # POLY_PROXY
    funder=os.getenv("FUNDER_ADDRESS")  # Proxy wallet address from polymarket.com/settings
)
```

---

## 3. Rate Limits

Rate limits are applied per API. Exceeding them returns HTTP 429.

| API | Limit | Notes |
|-----|-------|-------|
| Gamma API | Not officially published | Be respectful, implement caching |
| Data API | Not officially published | Be respectful, implement caching |
| CLOB API | Not officially published | Trading endpoints more restrictive |

Best practice: implement exponential backoff on 429 responses.

---

## 4. Clients & SDKs

| Language | Package | Repository |
|----------|---------|------------|
| Python | `py-clob-client` | https://github.com/Polymarket/py-clob-client |
| TypeScript | `@polymarket/clob-client` | https://github.com/Polymarket/clob-client |
| Rust | `polymarket-client-sdk` | https://github.com/Polymarket/polymarket-rs |

```bash
# Python
pip install py-clob-client

# TypeScript
npm install @polymarket/clob-client
```

---

## 5. Events Endpoints

**Base:** `https://gamma-api.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/events` | List events |
| GET | `/events/{id}` | Get event by ID |
| GET | `/events/slug/{slug}` | Get event by slug |
| GET | `/events/{id}/tags` | Get event tags |

---

## 6. Markets Endpoints

**Base:** `https://gamma-api.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/markets` | List markets |
| GET | `/markets/{id}` | Get market by ID |
| GET | `/markets/slug/{slug}` | Get market by slug |
| GET | `/markets/{id}/tags` | Get market tags by ID |

**Base:** `https://data-api.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/top-holders` | Get top holders for markets |
| GET | `/open-interest` | Get open interest |
| GET | `/live-volume` | Get live volume for an event |

---

## 7. Orderbook & Pricing Endpoints

**Base:** `https://clob.polymarket.com` (all public, no auth)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/book` | Get order book for a token |
| POST | `/books` | Get order books (multiple, via request body) |
| GET | `/price` | Get market price |
| GET | `/prices` | Get market prices (query params) |
| POST | `/prices` | Get market prices (request body) |
| GET | `/midpoint` | Get midpoint price |
| GET | `/midpoints` | Get midpoint prices (query params) |
| POST | `/midpoints` | Get midpoint prices (request body) |
| GET | `/spread` | Get spread |
| POST | `/spreads` | Get spreads (multiple) |
| GET | `/last-trade-price` | Get last trade price |
| GET | `/last-trade-prices` | Get last trade prices (query params) |
| POST | `/last-trade-prices` | Get last trade prices (request body) |
| GET | `/prices-history` | Get prices history |
| GET | `/fee-rate` | Get fee rate |
| GET | `/fee-rate/{tokenId}` | Get fee rate by token ID |
| GET | `/tick-size` | Get tick size |
| GET | `/tick-size/{tokenId}` | Get tick size by token ID |
| GET | `/time` | Get server time |

---

## 8. Orders Endpoints (Authenticated)

**Base:** `https://clob.polymarket.com` — All require L2 auth headers

| Method | Path | Description |
|--------|------|-------------|
| POST | `/order` | Post a new order |
| DELETE | `/order/{orderId}` | Cancel single order |
| GET | `/order/{orderId}` | Get single order by ID |
| POST | `/orders` | Post multiple orders |
| GET | `/orders` | Get user orders |
| DELETE | `/orders` | Cancel multiple orders |
| DELETE | `/cancel-all` | Cancel all orders |
| DELETE | `/cancel-market-orders` | Cancel orders for a market |
| GET | `/order-scoring` | Get order scoring status |
| POST | `/heartbeat` | Send heartbeat |

### Order Placement Example

```python
order = client.create_and_post_order(
    {
        "token_id": "123456...",
        "price": 0.65,
        "size": 100,
        "side": "BUY"      # or "SELL"
    },
    {
        "tick_size": "0.01",
        "neg_risk": False
    }
)
```

---

## 9. Trades Endpoints

**Base:** `https://clob.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/trades` | Get trades |
| GET | `/builder-trades` | Get builder trades |

---

## 10. CLOB Markets Endpoints

**Base:** `https://clob.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/simplified-markets` | Get simplified markets |
| GET | `/sampling-markets` | Get sampling markets |
| GET | `/sampling-simplified-markets` | Get sampling simplified markets |

---

## 11. Profile & Positions Endpoints

**Base:** `https://gamma-api.polymarket.com` (profiles)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/profiles/{address}` | Get public profile by wallet address |

**Base:** `https://data-api.polymarket.com` (positions & activity)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/positions` | Get current positions for a user |
| GET | `/closed-positions` | Get closed positions for a user |
| GET | `/activity` | Get user activity |
| GET | `/portfolio-value` | Get total value of user's positions |
| GET | `/trades` | Get trades for a user or markets |
| GET | `/total-markets-traded` | Get total markets a user has traded |
| GET | `/market-positions` | Get positions for a specific market |
| GET | `/accounting-snapshot` | Download accounting snapshot (ZIP of CSVs) |

---

## 12. Leaderboard Endpoints

**Base:** `https://data-api.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/leaderboard` | Get trader leaderboard rankings |

---

## 13. Rewards & Rebates Endpoints

**Base:** `https://clob.polymarket.com`

### Rebates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/rebates` | Get current rebated fees for a maker |

### Rewards

| Method | Path | Description |
|--------|------|-------------|
| GET | `/rewards/configurations` | Get current active rewards configurations |
| GET | `/rewards/markets/{conditionId}` | Get raw rewards for a specific market |
| GET | `/rewards/markets` | Get multiple markets with rewards |
| GET | `/rewards/earnings` | Get earnings for user by date |
| GET | `/rewards/total-earnings` | Get total earnings for user by date |
| GET | `/rewards/percentages` | Get reward percentages for user |
| GET | `/rewards/user-earnings` | Get user earnings and markets configuration |

---

## 14. Search Endpoint

**Base:** `https://gamma-api.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/search` | Search markets, events, and profiles |

---

## 15. Tags Endpoints

**Base:** `https://gamma-api.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tags` | List all tags |
| GET | `/tags/{id}` | Get tag by ID |
| GET | `/tags/slug/{slug}` | Get tag by slug |
| GET | `/tags/{id}/relationships` | Get related tags by tag ID |
| GET | `/tags/slug/{slug}/relationships` | Get related tags by tag slug |
| GET | `/tags/{id}/related` | Get tags related to a tag ID |
| GET | `/tags/slug/{slug}/related` | Get tags related to a tag slug |

---

## 16. Series Endpoints

**Base:** `https://gamma-api.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/series` | List series |
| GET | `/series/{id}` | Get series by ID |

---

## 17. Comments Endpoints

**Base:** `https://gamma-api.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/comments` | List comments |
| GET | `/comments/{id}` | Get comments by comment ID |
| GET | `/comments/user/{address}` | Get comments by user address |

---

## 18. Sports Endpoints

**Base:** `https://gamma-api.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sports/metadata` | Get sports metadata information |
| GET | `/sports/market-types` | Get valid sports market types |
| GET | `/sports/teams` | List teams |

---

## 19. Bridge Endpoints

**Base:** `https://bridge.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/supported-assets` | Get supported assets |
| POST | `/deposit-addresses` | Create deposit addresses |
| POST | `/quote` | Get a quote |
| GET | `/transaction-status` | Get transaction status |
| POST | `/withdrawal-addresses` | Create withdrawal addresses |

---

## 20. Relayer Endpoints

**Base:** `https://clob.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/relayer/transaction` | Submit a transaction |
| GET | `/relayer/transaction/{id}` | Get transaction by ID |
| GET | `/relayer/transactions` | Get recent transactions for user |
| GET | `/relayer/nonce` | Get current nonce for user |
| GET | `/relayer/address` | Get relayer address and nonce |
| GET | `/relayer/safe-deployed` | Check if a safe is deployed |
| GET | `/relayer/api-keys` | Get all relayer API keys |

---

## 21. Builders Endpoints

**Base:** `https://data-api.polymarket.com`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/builders/leaderboard` | Get aggregated builder leaderboard |
| GET | `/builders/volume-timeseries` | Get daily builder volume time-series |

---

## 22. WebSocket Channels

**Base:** `wss://ws-subscriptions-clob.polymarket.com/ws`

### Market Channel
Subscribe to real-time orderbook updates for specific tokens.

```json
// Subscription request
{
  "assets_ids": [
    "65818619657568813474341868652308942079804919287380422192892211131408793125422"
  ],
  "type": "market"
}
```

### User Channel
Subscribe to real-time updates for a specific user's orders and positions.

```json
{
  "auth": { ... },
  "type": "user"
}
```

### Sports Channel
Subscribe to real-time sports event updates.

```json
{
  "type": "sports"
}
```

---

## 23. Python Client Template

```python
import httpx
import asyncio
from typing import Optional, List

class PolymarketClient:
    """Async Polymarket API client for bot integration.
    Handles Gamma API (discovery), Data API (analytics), and CLOB API (trading).
    """

    GAMMA = "https://gamma-api.polymarket.com"
    DATA = "https://data-api.polymarket.com"
    CLOB = "https://clob.polymarket.com"

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"Accept": "application/json"},
            timeout=30.0
        )

    # ==================== GAMMA API (Discovery) ====================

    async def list_events(self, **params) -> list:
        """List events. Params: active, closed, limit, offset, slug, tag, etc."""
        r = await self.client.get(f"{self.GAMMA}/events", params=params)
        r.raise_for_status()
        return r.json()

    async def get_event(self, event_id: str) -> dict:
        r = await self.client.get(f"{self.GAMMA}/events/{event_id}")
        r.raise_for_status()
        return r.json()

    async def list_markets(self, **params) -> list:
        """List markets. Params: active, closed, limit, offset, etc."""
        r = await self.client.get(f"{self.GAMMA}/markets", params=params)
        r.raise_for_status()
        return r.json()

    async def get_market(self, market_id: str) -> dict:
        r = await self.client.get(f"{self.GAMMA}/markets/{market_id}")
        r.raise_for_status()
        return r.json()

    async def search(self, query: str, **params) -> dict:
        params["query"] = query
        r = await self.client.get(f"{self.GAMMA}/search", params=params)
        r.raise_for_status()
        return r.json()

    async def list_tags(self) -> list:
        r = await self.client.get(f"{self.GAMMA}/tags")
        r.raise_for_status()
        return r.json()

    async def get_sports_metadata(self) -> dict:
        r = await self.client.get(f"{self.GAMMA}/sports/metadata")
        r.raise_for_status()
        return r.json()

    async def get_sports_teams(self) -> list:
        r = await self.client.get(f"{self.GAMMA}/sports/teams")
        r.raise_for_status()
        return r.json()

    # ==================== DATA API (Analytics) ====================

    async def get_positions(self, address: str, **params) -> list:
        params["user"] = address
        r = await self.client.get(f"{self.DATA}/positions", params=params)
        r.raise_for_status()
        return r.json()

    async def get_trades(self, **params) -> list:
        """Get trades. Params: user, market, limit, offset, etc."""
        r = await self.client.get(f"{self.DATA}/trades", params=params)
        r.raise_for_status()
        return r.json()

    async def get_open_interest(self, **params) -> dict:
        r = await self.client.get(f"{self.DATA}/open-interest", params=params)
        r.raise_for_status()
        return r.json()

    async def get_leaderboard(self, **params) -> list:
        r = await self.client.get(f"{self.DATA}/leaderboard", params=params)
        r.raise_for_status()
        return r.json()

    # ==================== CLOB API (Pricing - Public) ====================

    async def get_orderbook(self, token_id: str) -> dict:
        r = await self.client.get(f"{self.CLOB}/book", params={"token_id": token_id})
        r.raise_for_status()
        return r.json()

    async def get_price(self, token_id: str) -> dict:
        r = await self.client.get(f"{self.CLOB}/price", params={"token_id": token_id})
        r.raise_for_status()
        return r.json()

    async def get_midpoint(self, token_id: str) -> dict:
        r = await self.client.get(f"{self.CLOB}/midpoint", params={"token_id": token_id})
        r.raise_for_status()
        return r.json()

    async def get_spread(self, token_id: str) -> dict:
        r = await self.client.get(f"{self.CLOB}/spread", params={"token_id": token_id})
        r.raise_for_status()
        return r.json()

    async def get_last_trade_price(self, token_id: str) -> dict:
        r = await self.client.get(f"{self.CLOB}/last-trade-price", params={"token_id": token_id})
        r.raise_for_status()
        return r.json()

    async def get_prices_history(self, token_id: str, **params) -> list:
        params["token_id"] = token_id
        r = await self.client.get(f"{self.CLOB}/prices-history", params=params)
        r.raise_for_status()
        return r.json()

    async def get_tick_size(self, token_id: str) -> dict:
        r = await self.client.get(f"{self.CLOB}/tick-size/{token_id}")
        r.raise_for_status()
        return r.json()

    async def get_server_time(self) -> dict:
        r = await self.client.get(f"{self.CLOB}/time")
        r.raise_for_status()
        return r.json()

    async def get_simplified_markets(self) -> list:
        r = await self.client.get(f"{self.CLOB}/simplified-markets")
        r.raise_for_status()
        return r.json()

    async def close(self):
        await self.client.aclose()


# === For AUTHENTICATED trading, use the official py-clob-client ===
#
# from py_clob_client.client import ClobClient
#
# client = ClobClient(
#     host="https://clob.polymarket.com",
#     chain_id=137,
#     key=os.getenv("PRIVATE_KEY"),
#     creds=api_creds,
#     signature_type=1,
#     funder=os.getenv("FUNDER_ADDRESS")
# )
#
# # Place order
# order = client.create_and_post_order(
#     {"token_id": "...", "price": 0.65, "size": 100, "side": "BUY"},
#     {"tick_size": "0.01", "neg_risk": False}
# )
#
# # Cancel order
# client.cancel(order_id="...")
#
# # Cancel all
# client.cancel_all()
#
# # Get open orders
# orders = client.get_orders()
```

---

## 24. All Documentation Page Links

### Overview
| Page | URL |
|------|-----|
| Introduction | https://docs.polymarket.com/api-reference/introduction |
| Authentication | https://docs.polymarket.com/api-reference/authentication |
| Rate Limits | https://docs.polymarket.com/api-reference/rate-limits |
| Clients & SDKs | https://docs.polymarket.com/api-reference/clients-sdks |
| Geographic Restrictions | https://docs.polymarket.com/api-reference/geoblock |

### Events
| Page | URL |
|------|-----|
| List events | https://docs.polymarket.com/api-reference/events/list-events |
| Get event by id | https://docs.polymarket.com/api-reference/events/get-event-by-id |
| Get event by slug | https://docs.polymarket.com/api-reference/events/get-event-by-slug |
| Get event tags | https://docs.polymarket.com/api-reference/events/get-event-tags |

### Markets
| Page | URL |
|------|-----|
| List markets | https://docs.polymarket.com/api-reference/markets/list-markets |
| Get market by id | https://docs.polymarket.com/api-reference/markets/get-market-by-id |
| Get market by slug | https://docs.polymarket.com/api-reference/markets/get-market-by-slug |
| Get market tags | https://docs.polymarket.com/api-reference/markets/get-market-tags-by-id |
| Get top holders | https://docs.polymarket.com/api-reference/core/get-top-holders-for-markets |
| Get open interest | https://docs.polymarket.com/api-reference/misc/get-open-interest |
| Get live volume | https://docs.polymarket.com/api-reference/misc/get-live-volume-for-an-event |

### Orderbook & Pricing
| Page | URL |
|------|-----|
| Get order book | https://docs.polymarket.com/api-reference/market-data/get-order-book |
| Get order books (POST) | https://docs.polymarket.com/api-reference/market-data/get-order-books-request-body |
| Get market price | https://docs.polymarket.com/api-reference/market-data/get-market-price |
| Get market prices (GET) | https://docs.polymarket.com/api-reference/market-data/get-market-prices-query-parameters |
| Get market prices (POST) | https://docs.polymarket.com/api-reference/market-data/get-market-prices-request-body |
| Get midpoint price | https://docs.polymarket.com/api-reference/data/get-midpoint-price |
| Get midpoint prices (GET) | https://docs.polymarket.com/api-reference/market-data/get-midpoint-prices-query-parameters |
| Get midpoint prices (POST) | https://docs.polymarket.com/api-reference/market-data/get-midpoint-prices-request-body |
| Get spread | https://docs.polymarket.com/api-reference/market-data/get-spread |
| Get spreads (POST) | https://docs.polymarket.com/api-reference/market-data/get-spreads |
| Get last trade price | https://docs.polymarket.com/api-reference/market-data/get-last-trade-price |
| Get last trade prices (GET) | https://docs.polymarket.com/api-reference/market-data/get-last-trade-prices-query-parameters |
| Get last trade prices (POST) | https://docs.polymarket.com/api-reference/market-data/get-last-trade-prices-request-body |
| Get prices history | https://docs.polymarket.com/api-reference/markets/get-prices-history |
| Get fee rate | https://docs.polymarket.com/api-reference/market-data/get-fee-rate |
| Get fee rate (path) | https://docs.polymarket.com/api-reference/market-data/get-fee-rate-by-path-parameter |
| Get tick size | https://docs.polymarket.com/api-reference/market-data/get-tick-size |
| Get tick size (path) | https://docs.polymarket.com/api-reference/market-data/get-tick-size-by-path-parameter |
| Get server time | https://docs.polymarket.com/api-reference/data/get-server-time |

### Orders
| Page | URL |
|------|-----|
| Post new order | https://docs.polymarket.com/api-reference/trade/post-a-new-order |
| Cancel single order | https://docs.polymarket.com/api-reference/trade/cancel-single-order |
| Get order by ID | https://docs.polymarket.com/api-reference/trade/get-single-order-by-id |
| Post multiple orders | https://docs.polymarket.com/api-reference/trade/post-multiple-orders |
| Get user orders | https://docs.polymarket.com/api-reference/trade/get-user-orders |
| Cancel multiple orders | https://docs.polymarket.com/api-reference/trade/cancel-multiple-orders |
| Cancel all orders | https://docs.polymarket.com/api-reference/trade/cancel-all-orders |
| Cancel market orders | https://docs.polymarket.com/api-reference/trade/cancel-orders-for-a-market |
| Order scoring status | https://docs.polymarket.com/api-reference/trade/get-order-scoring-status |
| Send heartbeat | https://docs.polymarket.com/api-reference/trade/send-heartbeat |

### Trades
| Page | URL |
|------|-----|
| Get trades | https://docs.polymarket.com/api-reference/trade/get-trades |
| Get builder trades | https://docs.polymarket.com/api-reference/trade/get-builder-trades |

### CLOB Markets
| Page | URL |
|------|-----|
| Simplified markets | https://docs.polymarket.com/api-reference/markets/get-simplified-markets |
| Sampling markets | https://docs.polymarket.com/api-reference/markets/get-sampling-markets |
| Sampling simplified | https://docs.polymarket.com/api-reference/markets/get-sampling-simplified-markets |

### Rebates & Rewards
| Page | URL |
|------|-----|
| Rebated fees | https://docs.polymarket.com/api-reference/rebates/get-current-rebated-fees-for-a-maker |
| Rewards config | https://docs.polymarket.com/api-reference/rewards/get-current-active-rewards-configurations |
| Market rewards | https://docs.polymarket.com/api-reference/rewards/get-raw-rewards-for-a-specific-market |
| Multiple markets rewards | https://docs.polymarket.com/api-reference/rewards/get-multiple-markets-with-rewards |
| User earnings by date | https://docs.polymarket.com/api-reference/rewards/get-earnings-for-user-by-date |
| Total earnings by date | https://docs.polymarket.com/api-reference/rewards/get-total-earnings-for-user-by-date |
| Reward percentages | https://docs.polymarket.com/api-reference/rewards/get-reward-percentages-for-user |
| User earnings config | https://docs.polymarket.com/api-reference/rewards/get-user-earnings-and-markets-configuration |

### Profile
| Page | URL |
|------|-----|
| Public profile | https://docs.polymarket.com/api-reference/profiles/get-public-profile-by-wallet-address |
| Current positions | https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user |
| Closed positions | https://docs.polymarket.com/api-reference/core/get-closed-positions-for-a-user |
| User activity | https://docs.polymarket.com/api-reference/core/get-user-activity |
| Portfolio value | https://docs.polymarket.com/api-reference/core/get-total-value-of-a-users-positions |
| User trades | https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets |
| Total markets traded | https://docs.polymarket.com/api-reference/misc/get-total-markets-a-user-has-traded |
| Market positions | https://docs.polymarket.com/api-reference/core/get-positions-for-a-market |
| Accounting snapshot | https://docs.polymarket.com/api-reference/misc/download-an-accounting-snapshot-zip-of-csvs |

### Leaderboard & Builders
| Page | URL |
|------|-----|
| Trader leaderboard | https://docs.polymarket.com/api-reference/core/get-trader-leaderboard-rankings |
| Builder leaderboard | https://docs.polymarket.com/api-reference/builders/get-aggregated-builder-leaderboard |
| Builder volume | https://docs.polymarket.com/api-reference/builders/get-daily-builder-volume-time-series |

### Search
| Page | URL |
|------|-----|
| Search | https://docs.polymarket.com/api-reference/search/search-markets-events-and-profiles |

### Tags
| Page | URL |
|------|-----|
| List tags | https://docs.polymarket.com/api-reference/tags/list-tags |
| Tag by id | https://docs.polymarket.com/api-reference/tags/get-tag-by-id |
| Tag by slug | https://docs.polymarket.com/api-reference/tags/get-tag-by-slug |
| Related tags (id) | https://docs.polymarket.com/api-reference/tags/get-related-tags-relationships-by-tag-id |
| Related tags (slug) | https://docs.polymarket.com/api-reference/tags/get-related-tags-relationships-by-tag-slug |
| Tags related to id | https://docs.polymarket.com/api-reference/tags/get-tags-related-to-a-tag-id |
| Tags related to slug | https://docs.polymarket.com/api-reference/tags/get-tags-related-to-a-tag-slug |

### Series & Comments
| Page | URL |
|------|-----|
| List series | https://docs.polymarket.com/api-reference/series/list-series |
| Series by id | https://docs.polymarket.com/api-reference/series/get-series-by-id |
| List comments | https://docs.polymarket.com/api-reference/comments/list-comments |
| Comment by id | https://docs.polymarket.com/api-reference/comments/get-comments-by-comment-id |
| Comments by user | https://docs.polymarket.com/api-reference/comments/get-comments-by-user-address |

### Sports
| Page | URL |
|------|-----|
| Sports metadata | https://docs.polymarket.com/api-reference/sports/get-sports-metadata-information |
| Sports market types | https://docs.polymarket.com/api-reference/sports/get-valid-sports-market-types |
| Sports teams | https://docs.polymarket.com/api-reference/sports/list-teams |

### Bridge
| Page | URL |
|------|-----|
| Supported assets | https://docs.polymarket.com/api-reference/bridge/get-supported-assets |
| Deposit addresses | https://docs.polymarket.com/api-reference/bridge/create-deposit-addresses |
| Get quote | https://docs.polymarket.com/api-reference/bridge/get-a-quote |
| Transaction status | https://docs.polymarket.com/api-reference/bridge/get-transaction-status |
| Withdrawal addresses | https://docs.polymarket.com/api-reference/bridge/create-withdrawal-addresses |

### Relayer
| Page | URL |
|------|-----|
| Submit transaction | https://docs.polymarket.com/api-reference/relayer/submit-a-transaction |
| Transaction by ID | https://docs.polymarket.com/api-reference/relayer/get-a-transaction-by-id |
| Recent transactions | https://docs.polymarket.com/api-reference/relayer/get-recent-transactions-for-a-user |
| Current nonce | https://docs.polymarket.com/api-reference/relayer/get-current-nonce-for-a-user |
| Relayer address | https://docs.polymarket.com/api-reference/relayer/get-relayer-address-and-nonce |
| Safe deployed | https://docs.polymarket.com/api-reference/relayer/check-if-a-safe-is-deployed |
| Relayer API keys | https://docs.polymarket.com/api-reference/relayer-api-keys/get-all-relayer-api-keys |

### WebSocket
| Page | URL |
|------|-----|
| Market Channel | https://docs.polymarket.com/api-reference/wss/market |
| User Channel | https://docs.polymarket.com/api-reference/wss/user |
| Sports Channel | https://docs.polymarket.com/api-reference/wss/sports |
