# Polymarket API Reference — Index

> Compact index for `polymarket-full-api-reference.md` (78,024 lines).
> Use `Read(offset=START, limit=SIZE)` to load any endpoint on demand.

## How to Use
1. Find the endpoint you need in the table below
2. Read from the full reference: `Read("polymarket-full-api-reference.md", offset=START, limit=SIZE)`
3. No data is lost — full cURL examples, parameters, response schemas, and JSON examples are all preserved

## Overview (L176–L3157)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 1 | [Introduction](polymarket-full-api-reference.md) | 176–647 | 471 |
| 2 | [Authentication](polymarket-full-api-reference.md) | 648–1450 | 802 |
| 3 | [Rate Limits](polymarket-full-api-reference.md) | 1451–2009 | 558 |
| 4 | [Clients & SDKs](polymarket-full-api-reference.md) | 2010–2520 | 510 |
| 5 | [Geographic Restrictions](polymarket-full-api-reference.md) | 2521–3157 | 636 |

## Events (L3158–L10614)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 6 | [List events](polymarket-full-api-reference.md) | 3158–5538 | 2380 |
| 7 | [Get event by id](polymarket-full-api-reference.md) | 5539–7781 | 2242 |
| 8 | [Get event by slug](polymarket-full-api-reference.md) | 7782–10028 | 2246 |
| 9 | [Get event tags](polymarket-full-api-reference.md) | 10029–10614 | 585 |

## Markets (L10615–L20552)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 10 | [List markets](polymarket-full-api-reference.md) | 10615–13291 | 2676 |
| 11 | [Get market by id](polymarket-full-api-reference.md) | 13292–15818 | 2526 |
| 12 | [Get market by slug](polymarket-full-api-reference.md) | 15819–18349 | 2530 |
| 13 | [Get market tags by id](polymarket-full-api-reference.md) | 18350–18932 | 582 |
| 14 | [Get top holders for markets](polymarket-full-api-reference.md) | 18933–19503 | 570 |
| 15 | [Get open interest](polymarket-full-api-reference.md) | 19504–20024 | 520 |
| 16 | [Get live volume for an event](polymarket-full-api-reference.md) | 20025–20552 | 527 |

## Orderbook & Pricing (L20553–L31062)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 17 | [Get order book](polymarket-full-api-reference.md) | 20553–21246 | 693 |
| 18 | [Get order books (request body)](polymarket-full-api-reference.md) | 21247–21965 | 718 |
| 19 | [Get market price](polymarket-full-api-reference.md) | 21966–22491 | 525 |
| 20 | [Get market prices (query parameters)](polymarket-full-api-reference.md) | 22492–23016 | 524 |
| 21 | [Get market prices (request body)](polymarket-full-api-reference.md) | 23017–23582 | 565 |
| 22 | [Get midpoint price](polymarket-full-api-reference.md) | 23583–24096 | 513 |
| 23 | [Get midpoint prices (query parameters)](polymarket-full-api-reference.md) | 24097–24606 | 509 |
| 24 | [Get midpoint prices (request body)](polymarket-full-api-reference.md) | 24607–25162 | 555 |
| 25 | [Get spread](polymarket-full-api-reference.md) | 25163–25676 | 513 |
| 26 | [Get spreads](polymarket-full-api-reference.md) | 25677–26232 | 555 |
| 27 | [Get last trade price](polymarket-full-api-reference.md) | 26233–26768 | 535 |
| 28 | [Get last trade prices (query parameters)](polymarket-full-api-reference.md) | 26769–27330 | 561 |
| 29 | [Get last trade prices (request body)](polymarket-full-api-reference.md) | 27331–27938 | 607 |
| 30 | [Get prices history](polymarket-full-api-reference.md) | 27939–28503 | 564 |
| 31 | [Get fee rate](polymarket-full-api-reference.md) | 28504–29019 | 515 |
| 32 | [Get fee rate by path parameter](polymarket-full-api-reference.md) | 29020–29540 | 520 |
| 33 | [Get tick size](polymarket-full-api-reference.md) | 29541–30056 | 515 |
| 34 | [Get tick size by path parameter](polymarket-full-api-reference.md) | 30057–30577 | 520 |
| 35 | [Get server time](polymarket-full-api-reference.md) | 30578–31062 | 484 |

## Orders (L31063–L37965)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 36 | [Post a new order](polymarket-full-api-reference.md) | 31063–31837 | 774 |
| 37 | [Cancel single order](polymarket-full-api-reference.md) | 31838–32466 | 628 |
| 38 | [Get single order by ID](polymarket-full-api-reference.md) | 32467–33314 | 847 |
| 39 | [Post multiple orders](polymarket-full-api-reference.md) | 33315–34180 | 865 |
| 40 | [Get user orders](polymarket-full-api-reference.md) | 34181–34918 | 737 |
| 41 | [Cancel multiple orders](polymarket-full-api-reference.md) | 34919–35545 | 626 |
| 42 | [Cancel all orders](polymarket-full-api-reference.md) | 35546–36146 | 600 |
| 43 | [Cancel orders for a market](polymarket-full-api-reference.md) | 36147–36794 | 647 |
| 44 | [Get order scoring status](polymarket-full-api-reference.md) | 36795–37384 | 589 |
| 45 | [Send heartbeat](polymarket-full-api-reference.md) | 37385–37965 | 580 |

## Trades (L37966–L39434)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 46 | [Get trades](polymarket-full-api-reference.md) | 37966–38701 | 735 |
| 47 | [Get builder trades](polymarket-full-api-reference.md) | 38702–39434 | 732 |

## CLOB Markets (L39435–L41192)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 48 | [Get simplified markets](polymarket-full-api-reference.md) | 39435–40003 | 568 |
| 49 | [Get sampling markets](polymarket-full-api-reference.md) | 40004–40620 | 616 |
| 50 | [Get sampling simplified markets](polymarket-full-api-reference.md) | 40621–41192 | 571 |

## Rebates (L41193–L41790)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 51 | [Get current rebated fees for a maker](polymarket-full-api-reference.md) | 41193–41790 | 597 |

## Rewards (L41791–L46755)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 52 | [Get current active rewards configurations](polymarket-full-api-reference.md) | 41791–42414 | 623 |
| 53 | [Get raw rewards for a specific market](polymarket-full-api-reference.md) | 42415–43077 | 662 |
| 54 | [Get multiple markets with rewards](polymarket-full-api-reference.md) | 43078–43856 | 778 |
| 55 | [Get earnings for user by date](polymarket-full-api-reference.md) | 43857–44544 | 687 |
| 56 | [Get total earnings for user by date](polymarket-full-api-reference.md) | 44545–45236 | 691 |
| 57 | [Get reward percentages for user](polymarket-full-api-reference.md) | 45237–45844 | 607 |
| 58 | [Get user earnings and markets configuration](polymarket-full-api-reference.md) | 45845–46755 | 910 |

## Profile (L46756–L52809)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 59 | [Get public profile by wallet address](polymarket-full-api-reference.md) | 46756–47364 | 608 |
| 60 | [Get current positions for a user](polymarket-full-api-reference.md) | 47365–48206 | 841 |
| 61 | [Get closed positions for a user](polymarket-full-api-reference.md) | 48207–48960 | 753 |
| 62 | [Get user activity](polymarket-full-api-reference.md) | 48961–49799 | 838 |
| 63 | [Get total value of a user's positions](polymarket-full-api-reference.md) | 49800–50336 | 536 |
| 64 | [Get trades for a user or markets](polymarket-full-api-reference.md) | 50337–51101 | 764 |
| 65 | [Get total markets a user has traded](polymarket-full-api-reference.md) | 51102–51628 | 526 |
| 66 | [Get positions for a market](polymarket-full-api-reference.md) | 51629–52298 | 669 |
| 67 | [Download an accounting snapshot (ZIP of CSVs)](polymarket-full-api-reference.md) | 52299–52809 | 510 |

## Leaderboard (L52810–L53504)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 68 | [Get trader leaderboard rankings](polymarket-full-api-reference.md) | 52810–53504 | 694 |

## Builders (L53505–L54695)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 69 | [Get aggregated builder leaderboard](polymarket-full-api-reference.md) | 53505–54103 | 598 |
| 70 | [Get daily builder volume time-series](polymarket-full-api-reference.md) | 54104–54695 | 591 |

## Search (L54696–L56577)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 71 | [Search markets, events, and profiles](polymarket-full-api-reference.md) | 54696–56577 | 1881 |

## Tags (L56578–L60673)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 72 | [List tags](polymarket-full-api-reference.md) | 56578–57184 | 606 |
| 73 | [Get tag by id](polymarket-full-api-reference.md) | 57185–57767 | 582 |
| 74 | [Get tag by slug](polymarket-full-api-reference.md) | 57768–58354 | 586 |
| 75 | [Get related tags (relationships) by tag id](polymarket-full-api-reference.md) | 58355–58901 | 546 |
| 76 | [Get related tags (relationships) by tag slug](polymarket-full-api-reference.md) | 58902–59452 | 550 |
| 77 | [Get tags related to a tag id](polymarket-full-api-reference.md) | 59453–60059 | 606 |
| 78 | [Get tags related to a tag slug](polymarket-full-api-reference.md) | 60060–60673 | 613 |

## Series (L60674–L64568)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 79 | [List series](polymarket-full-api-reference.md) | 60674–62646 | 1972 |
| 80 | [Get series by id](polymarket-full-api-reference.md) | 62647–64568 | 1921 |

## Comments (L64569–L66852)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 81 | [List comments](polymarket-full-api-reference.md) | 64569–65347 | 778 |
| 82 | [Get comments by comment id](polymarket-full-api-reference.md) | 65348–66084 | 736 |
| 83 | [Get comments by user address](polymarket-full-api-reference.md) | 66085–66852 | 767 |

## Sports (L66853–L68476)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 84 | [Get sports metadata information](polymarket-full-api-reference.md) | 66853–67387 | 534 |
| 85 | [Get valid sports market types](polymarket-full-api-reference.md) | 67388–67876 | 488 |
| 86 | [List teams](polymarket-full-api-reference.md) | 67877–68476 | 599 |

## Bridge (L68477–L71394)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 87 | [Get supported assets](polymarket-full-api-reference.md) | 68477–68989 | 512 |
| 88 | [Create deposit addresses](polymarket-full-api-reference.md) | 68990–69536 | 546 |
| 89 | [Get a quote](polymarket-full-api-reference.md) | 69537–70231 | 694 |
| 90 | [Get transaction status](polymarket-full-api-reference.md) | 70232–70796 | 564 |
| 91 | [Create withdrawal addresses](polymarket-full-api-reference.md) | 70797–71394 | 597 |

## Relayer (L71395–L75882)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 92 | [Submit a transaction](polymarket-full-api-reference.md) | 71395–72148 | 753 |
| 93 | [Get a transaction by ID](polymarket-full-api-reference.md) | 72149–72889 | 740 |
| 94 | [Get recent transactions for a user](polymarket-full-api-reference.md) | 72890–73717 | 827 |
| 95 | [Get current nonce for a user](polymarket-full-api-reference.md) | 73718–74241 | 523 |
| 96 | [Get relayer address and nonce](polymarket-full-api-reference.md) | 74242–74785 | 543 |
| 97 | [Check if a safe is deployed](polymarket-full-api-reference.md) | 74786–75301 | 515 |
| 98 | [Get all relayer API keys](polymarket-full-api-reference.md) | 75302–75882 | 580 |

## WebSocket (L75883–L78024)

| # | Endpoint | Lines | Size |
|---|----------|-------|------|
| 99 | [Market Channel](polymarket-full-api-reference.md) | 75883–76817 | 934 |
| 100 | [User Channel](polymarket-full-api-reference.md) | 76818–77514 | 696 |
| 101 | [Sports Channel](polymarket-full-api-reference.md) | 77515–78024 | 509 |
