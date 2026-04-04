# The Odds API — Complete Reference Guide

> Source: https://the-odds-api.com/liveapi/guides/v4/
> Compiled: 2026-04-04

---

# Table of Contents

1. [Overview](#overview)
2. [Host](#host)
3. [GET /v4/sports](#get-sports)
4. [GET /v4/sports/{sport}/odds](#get-odds)
5. [GET /v4/sports/{sport}/scores](#get-scores)
6. [GET /v4/sports/{sport}/events](#get-events)
7. [GET /v4/sports/{sport}/events/{eventId}/odds](#get-event-odds)
8. [GET /v4/sports/{sport}/events/{eventId}/markets](#get-event-markets)
9. [GET /v4/sports/{sport}/participants](#get-participants)
10. [GET /v4/historical/sports/{sport}/odds](#get-historical-odds)
11. [GET /v4/historical/sports/{sport}/events](#get-historical-events)
12. [GET /v4/historical/sports/{sport}/events/{eventId}/odds](#get-historical-event-odds)
13. [Rate Limiting (429)](#rate-limiting)
14. [Response Headers](#response-headers)
15. [Betting Markets Reference](#betting-markets-reference)
16. [Bookmakers Reference](#bookmakers-reference)
17. [Sports Reference](#sports-reference)

---

# Overview

The Odds API provides access to sports odds data through a set of REST endpoints. Users begin by obtaining an API key, retrieving a list of available sports, and then accessing odds data for specific sports using sport keys.

# Host

All requests use:
```
https://api.the-odds-api.com
```

IPv6 connections can use:
```
https://ipv6-api.the-odds-api.com
```

---

# GET Sports

Returns a list of in-season sports. **Does NOT count against usage quota.**

## Endpoint

```
GET /v4/sports/?apiKey={apiKey}
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `apiKey` | string | Yes | Your subscription API key |
| `all` | boolean | No | Set to `true` to include both in-season and out-of-season sports |

## Example Request

```
https://api.the-odds-api.com/v4/sports/?apiKey=YOUR_API_KEY
```

## Example Response

```json
[
    {
        "key": "americanfootball_ncaaf",
        "group": "American Football",
        "title": "NCAAF",
        "description": "US College Football",
        "active": true,
        "has_outrights": false
    },
    {
        "key": "americanfootball_nfl",
        "group": "American Football",
        "title": "NFL",
        "description": "US Football",
        "active": true,
        "has_outrights": false
    },
    {
        "key": "americanfootball_nfl_super_bowl_winner",
        "group": "American Football",
        "title": "NFL Super Bowl Winner",
        "description": "Super Bowl Winner 2021/2022",
        "active": true,
        "has_outrights": true
    },
    {
        "key": "aussierules_afl",
        "group": "Aussie Rules",
        "title": "AFL",
        "description": "Aussie Football",
        "active": true,
        "has_outrights": false
    },
    {
        "key": "baseball_mlb",
        "group": "Baseball",
        "title": "MLB",
        "description": "Major League Baseball",
        "active": true,
        "has_outrights": false
    },
    {
        "key": "basketball_nba",
        "group": "Basketball",
        "title": "NBA",
        "description": "US Basketball",
        "active": true,
        "has_outrights": false
    },
    {
        "key": "cricket_test_match",
        "group": "Cricket",
        "title": "Test Matches",
        "description": "International Test Matches",
        "active": true,
        "has_outrights": false
    },
    {
        "key": "icehockey_nhl",
        "group": "Ice Hockey",
        "title": "NHL",
        "description": "US Ice Hockey",
        "active": true,
        "has_outrights": false
    },
    {
        "key": "mma_mixed_martial_arts",
        "group": "Mixed Martial Arts",
        "title": "MMA",
        "description": "Mixed Martial Arts",
        "active": true,
        "has_outrights": false
    },
    {
        "key": "soccer_epl",
        "group": "Soccer",
        "title": "EPL",
        "description": "English Premier League",
        "active": true,
        "has_outrights": false
    },
    {
        "key": "soccer_usa_mls",
        "group": "Soccer",
        "title": "MLS",
        "description": "Major League Soccer",
        "active": true,
        "has_outrights": false
    }
]
```

## Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Identifier for use in other endpoints |
| `group` | string | Sport category (e.g., "American Football") |
| `title` | string | League name (e.g., "NFL") |
| `description` | string | Human-readable description |
| `active` | boolean | Whether currently in season |
| `has_outrights` | boolean | Whether futures/outright markets are available |

## Usage Quota Cost

**Free** — does not count against quota.

---

# GET Odds

Returns upcoming and live games with current odds from bookmakers.

## Endpoint

```
GET /v4/sports/{sport}/odds/?apiKey={apiKey}&regions={regions}&markets={markets}
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sport` | string | Yes | Sport key from /sports endpoint, or `upcoming` for all sports |
| `apiKey` | string | Yes | Your subscription API key |
| `regions` | string | Yes | Comma-separated region codes: `us`, `uk`, `au`, `eu`, `us2`, `us_dfs`, `us_ex`, `fr`, `se` |
| `markets` | string | No | Comma-separated market types. Defaults to `h2h`. Valid: `h2h`, `spreads`, `totals`, `outrights` and many more (see Markets Reference) |
| `dateFormat` | string | No | `unix` or `iso` (ISO 8601). Defaults to `iso` |
| `oddsFormat` | string | No | `decimal` or `american`. Defaults to `decimal` |
| `eventIds` | string | No | Comma-separated event IDs to filter |
| `bookmakers` | string | No | Comma-separated bookmaker keys. Takes priority over `regions` |
| `commenceTimeFrom` | string | No | ISO 8601 timestamp — filter events starting on/after this time |
| `commenceTimeTo` | string | No | ISO 8601 timestamp — filter events starting on/before this time |
| `includeLinks` | boolean | No | Include bookmaker deep links |
| `includeSids` | boolean | No | Include source IDs |
| `includeBetLimits` | boolean | No | Include bet limits |
| `includeRotationNumbers` | boolean | No | Include rotation numbers |

## Example Request

```
https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/?apiKey=YOUR_API_KEY&regions=us&markets=h2h,spreads&oddsFormat=american
```

## Example Response

```json
[
    {
        "id": "bda33adca828c09dc3cac3a856aef176",
        "sport_key": "americanfootball_nfl",
        "sport_title": "NFL",
        "commence_time": "2021-09-10T00:20:00Z",
        "home_team": "Tampa Bay Buccaneers",
        "away_team": "Dallas Cowboys",
        "bookmakers": [
            {
                "key": "draftkings",
                "title": "DraftKings",
                "last_update": "2021-06-10T13:33:26Z",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {
                                "name": "Dallas Cowboys",
                                "price": 240
                            },
                            {
                                "name": "Tampa Bay Buccaneers",
                                "price": -305
                            }
                        ]
                    },
                    {
                        "key": "spreads",
                        "outcomes": [
                            {
                                "name": "Dallas Cowboys",
                                "price": -109,
                                "point": 6.5
                            },
                            {
                                "name": "Tampa Bay Buccaneers",
                                "price": -112,
                                "point": -6.5
                            }
                        ]
                    }
                ]
            },
            {
                "key": "fanduel",
                "title": "FanDuel",
                "last_update": "2021-06-10T13:33:23Z",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {
                                "name": "Dallas Cowboys",
                                "price": 225
                            },
                            {
                                "name": "Tampa Bay Buccaneers",
                                "price": -275
                            }
                        ]
                    },
                    {
                        "key": "spreads",
                        "outcomes": [
                            {
                                "name": "Dallas Cowboys",
                                "price": -110,
                                "point": 6.5
                            },
                            {
                                "name": "Tampa Bay Buccaneers",
                                "price": -110,
                                "point": -6.5
                            }
                        ]
                    }
                ]
            },
            {
                "key": "betmgm",
                "title": "BetMGM",
                "last_update": "2021-06-10T13:32:45Z",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {
                                "name": "Dallas Cowboys",
                                "price": 225
                            },
                            {
                                "name": "Tampa Bay Buccaneers",
                                "price": -275
                            }
                        ]
                    },
                    {
                        "key": "spreads",
                        "outcomes": [
                            {
                                "name": "Dallas Cowboys",
                                "price": -110,
                                "point": 6.5
                            },
                            {
                                "name": "Tampa Bay Buccaneers",
                                "price": -110,
                                "point": -6.5
                            }
                        ]
                    }
                ]
            },
            {
                "key": "bovada",
                "title": "Bovada",
                "last_update": "2021-06-10T13:35:51Z",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {
                                "name": "Dallas Cowboys",
                                "price": 240
                            },
                            {
                                "name": "Tampa Bay Buccaneers",
                                "price": -290
                            }
                        ]
                    },
                    {
                        "key": "spreads",
                        "outcomes": [
                            {
                                "name": "Dallas Cowboys",
                                "price": -110,
                                "point": 6.5
                            },
                            {
                                "name": "Tampa Bay Buccaneers",
                                "price": -110,
                                "point": -6.5
                            }
                        ]
                    }
                ]
            }
        ]
    }
]
```

## Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Event identifier |
| `sport_key` | string | Sport key |
| `sport_title` | string | Sport display name |
| `commence_time` | string | Game start time (ISO 8601 or unix) |
| `home_team` | string | Home team name |
| `away_team` | string | Away team name |
| `bookmakers` | array | Array of bookmaker objects |
| `bookmakers[].key` | string | Bookmaker key |
| `bookmakers[].title` | string | Bookmaker display name |
| `bookmakers[].last_update` | string | Last odds update time |
| `bookmakers[].markets` | array | Array of market objects |
| `bookmakers[].markets[].key` | string | Market key (h2h, spreads, totals, etc.) |
| `bookmakers[].markets[].outcomes` | array | Array of outcome objects |
| `bookmakers[].markets[].outcomes[].name` | string | Team/outcome name |
| `bookmakers[].markets[].outcomes[].price` | number | Odds value |
| `bookmakers[].markets[].outcomes[].point` | number | Point spread/total (spreads & totals only) |

## Usage Quota Cost

Formula: `[number of markets] × [number of regions]`

| Markets | Regions | Cost |
|---------|---------|------|
| 1 | 1 | 1 credit |
| 3 | 1 | 3 credits |
| 1 | 3 | 3 credits |
| 3 | 3 | 9 credits |

**Important Notes:**
- Lists currently listed events from major bookmakers
- May include current round games plus upcoming rounds
- Events become temporarily unavailable after round completion
- Does NOT return completed events
- Empty responses do NOT count against quota

---

# GET Scores

Returns upcoming, live, and recently completed games with scores.

## Endpoint

```
GET /v4/sports/{sport}/scores/?apiKey={apiKey}&daysFrom={daysFrom}
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sport` | string | Yes | Sport key from /sports endpoint |
| `apiKey` | string | Yes | Your subscription API key |
| `daysFrom` | integer | No | Integer 1-3 for completed games from past N days |
| `dateFormat` | string | No | `unix` or `iso`. Defaults to `iso` |
| `eventIds` | string | No | Comma-separated event IDs to filter |

## Example Request

```
https://api.the-odds-api.com/v4/sports/basketball_nba/scores/?daysFrom=1&apiKey=YOUR_API_KEY
```

## Example Response

```json
[
    {
        "id": "572d984e132eddaac3da93e5db332e7e",
        "sport_key": "basketball_nba",
        "sport_title": "NBA",
        "commence_time": "2022-02-06T03:10:38Z",
        "completed": true,
        "home_team": "Sacramento Kings",
        "away_team": "Oklahoma City Thunder",
        "scores": [
            {
                "name": "Sacramento Kings",
                "score": "113"
            },
            {
                "name": "Oklahoma City Thunder",
                "score": "103"
            }
        ],
        "last_update": "2022-02-06T05:18:19Z"
    },
    {
        "id": "4b25562aa9e87b57aa16f970abaec8cc",
        "sport_key": "basketball_nba",
        "sport_title": "NBA",
        "commence_time": "2022-02-07T02:11:01Z",
        "completed": false,
        "home_team": "Los Angeles Clippers",
        "away_team": "Milwaukee Bucks",
        "scores": [
            {
                "name": "Los Angeles Clippers",
                "score": "40"
            },
            {
                "name": "Milwaukee Bucks",
                "score": "37"
            }
        ],
        "last_update": "2022-02-07T02:47:23Z"
    },
    {
        "id": "19434a586e3723c55cd3d028b90eb112",
        "sport_key": "basketball_nba",
        "sport_title": "NBA",
        "commence_time": "2022-02-08T00:10:00Z",
        "completed": false,
        "home_team": "Charlotte Hornets",
        "away_team": "Toronto Raptors",
        "scores": null,
        "last_update": null
    }
]
```

## Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Event identifier |
| `sport_key` | string | Sport key |
| `sport_title` | string | Sport display name |
| `commence_time` | string | Game start time |
| `completed` | boolean | Whether game is completed |
| `home_team` | string | Home team name |
| `away_team` | string | Away team name |
| `scores` | array or null | Array of score objects (null for upcoming) |
| `scores[].name` | string | Team name |
| `scores[].score` | string | Score value |
| `last_update` | string or null | Most recent data update timestamp |

## Usage Quota Cost

| Scenario | Cost |
|----------|------|
| With `daysFrom` parameter | 2 credits |
| Without `daysFrom` (live/upcoming only) | 1 credit |

**Coverage Note:** Available for selected sports, gradually expanding to more leagues.

---

# GET Events

Returns in-play and pre-match events WITHOUT odds. **Does NOT count against quota.**

## Endpoint

```
GET /v4/sports/{sport}/events?apiKey={apiKey}
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sport` | string | Yes | Sport key |
| `apiKey` | string | Yes | Your subscription API key |
| `dateFormat` | string | No | `unix` or `iso` |
| `eventIds` | string | No | Comma-separated event IDs to filter |
| `commenceTimeFrom` | string | No | ISO 8601 start time filter |
| `commenceTimeTo` | string | No | ISO 8601 end time filter |
| `includeRotationNumbers` | boolean | No | Include rotation numbers |

## Example Request

```
https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events?apiKey=YOUR_API_KEY
```

## Example Response

```json
[
    {
        "id": "a512a48a58c4329048174217b2cc7ce0",
        "sport_key": "americanfootball_nfl",
        "sport_title": "NFL",
        "commence_time": "2023-01-01T18:00:00Z",
        "home_team": "Atlanta Falcons",
        "away_team": "Arizona Cardinals"
    },
    {
        "id": "0ba747b1414a31b05ef37f0bf3d7fbe9",
        "sport_key": "americanfootball_nfl",
        "sport_title": "NFL",
        "commence_time": "2023-01-01T18:00:00Z",
        "home_team": "Tampa Bay Buccaneers",
        "away_team": "Carolina Panthers"
    },
    {
        "id": "d7120d8231032db343cb86b20cfaaf48",
        "sport_key": "americanfootball_nfl",
        "sport_title": "NFL",
        "commence_time": "2023-01-01T18:00:00Z",
        "home_team": "Detroit Lions",
        "away_team": "Chicago Bears"
    }
]
```

## Usage Quota Cost

**Free** — does not count against quota.

---

# GET Event Odds

Returns odds for a single event across all available markets.

## Endpoint

```
GET /v4/sports/{sport}/events/{eventId}/odds?apiKey={apiKey}&regions={regions}&markets={markets}
```

## Parameters

Same as GET Odds plus:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `eventId` | string | Yes | Event ID in URL path |
| `includeMultipliers` | boolean | No | Include DFS multipliers |

**Note:** In the response, `last_update` appears at the **market level**, not the bookmaker level. Outcomes may include a `description` field for player props.

## Example Request

```
https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events/a512a48a58c4329048174217b2cc7ce0/odds?apiKey=YOUR_API_KEY&regions=us&markets=player_pass_tds&oddsFormat=american
```

## Example Response

```json
{
    "id": "a512a48a58c4329048174217b2cc7ce0",
    "sport_key": "americanfootball_nfl",
    "sport_title": "NFL",
    "commence_time": "2023-01-01T18:00:00Z",
    "home_team": "Atlanta Falcons",
    "away_team": "Arizona Cardinals",
    "bookmakers": [
        {
            "key": "draftkings",
            "title": "DraftKings",
            "markets": [
                {
                    "key": "player_pass_tds",
                    "last_update": "2023-01-01T05:31:29Z",
                    "outcomes": [
                        {
                            "name": "Over",
                            "description": "David Blough",
                            "price": -205,
                            "point": 0.5
                        },
                        {
                            "name": "Under",
                            "description": "David Blough",
                            "price": 150,
                            "point": 0.5
                        },
                        {
                            "name": "Over",
                            "description": "Desmond Ridder",
                            "price": -270,
                            "point": 0.5
                        },
                        {
                            "name": "Under",
                            "description": "Desmond Ridder",
                            "price": 195,
                            "point": 0.5
                        }
                    ]
                }
            ]
        },
        {
            "key": "fanduel",
            "title": "FanDuel",
            "markets": [
                {
                    "key": "player_pass_tds",
                    "last_update": "2023-01-01T05:35:06Z",
                    "outcomes": [
                        {
                            "name": "Over",
                            "description": "David Blough",
                            "price": -215,
                            "point": 0.5
                        },
                        {
                            "name": "Under",
                            "description": "David Blough",
                            "price": 164,
                            "point": 0.5
                        },
                        {
                            "name": "Over",
                            "description": "Desmond Ridder",
                            "price": 196,
                            "point": 1.5
                        },
                        {
                            "name": "Under",
                            "description": "Desmond Ridder",
                            "price": -260,
                            "point": 1.5
                        }
                    ]
                }
            ]
        }
    ]
}
```

## Usage Quota Cost

Formula: `[number of unique markets in response] × [number of regions]`

- Costs based on markets actually **returned**, not requested
- Empty responses do NOT count against quota

---

# GET Event Markets

Returns available market keys for each bookmaker for an event.

## Endpoint

```
GET /v4/sports/{sport}/events/{eventId}/markets?apiKey={apiKey}&regions={regions}
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sport` | string | Yes | Sport key |
| `eventId` | string | Yes | Event ID |
| `apiKey` | string | Yes | Your subscription API key |
| `regions` | string | Yes | Bookmaker regions |
| `bookmakers` | string | No | Specific bookmaker list |
| `dateFormat` | string | No | `unix` or `iso` |

## Example Request

```
https://api.the-odds-api.com/v4/sports/baseball_mlb/events/19699ba901294e39cb07fc4f19929a38/markets?apiKey=YOUR_API_KEY&regions=us
```

## Example Response

```json
{
    "id": "19699ba901294e39cb07fc4f19929a38",
    "sport_key": "baseball_mlb",
    "sport_title": "MLB",
    "commence_time": "2025-08-06T16:36:00Z",
    "home_team": "Philadelphia Phillies",
    "away_team": "Baltimore Orioles",
    "bookmakers": [
        {
            "key": "fanduel",
            "title": "FanDuel",
            "markets": [
                {
                    "key": "alternate_spreads",
                    "last_update": "2025-08-06T07:39:57Z"
                },
                {
                    "key": "batter_doubles",
                    "last_update": "2025-08-06T07:39:57Z"
                },
                {
                    "key": "batter_hits",
                    "last_update": "2025-08-06T07:39:57Z"
                },
                {
                    "key": "batter_home_runs",
                    "last_update": "2025-08-06T07:39:57Z"
                }
            ]
        }
    ]
}
```

**Notes:**
- Shows recently seen markets only, not a comprehensive list
- More markets appear as game approaches

## Usage Quota Cost

**1 credit** per request.

---

# GET Participants

Returns list of participants (teams or individuals) for a sport.

## Endpoint

```
GET /v4/sports/{sport}/participants?apiKey={apiKey}
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sport` | string | Yes | Sport key |
| `apiKey` | string | Yes | Your subscription API key |

## Example Request

```
https://api.the-odds-api.com/v4/sports/americanfootball_nfl/participants?apiKey=YOUR_API_KEY
```

## Example Response

```json
[
    {
        "full_name": "Arizona Cardinals",
        "id": "par_01hqmkr1xsfxmrj5pdq0f23asx"
    },
    {
        "full_name": "Atlanta Falcons",
        "id": "par_01hqmkr1xtexkbhkq7ct921rne"
    },
    {
        "full_name": "Baltimore Ravens",
        "id": "par_01hqmkr1xvev9rf557fy09k2cx"
    },
    {
        "full_name": "Buffalo Bills",
        "id": "par_01hqmkr1xwe6prjwr3j4gpqwx8"
    },
    {
        "full_name": "Dallas Cowboys",
        "id": "par_01hqmkr1y1esas88pmaxe87by4"
    },
    {
        "full_name": "Kansas City Chiefs",
        "id": "par_01hqmkr1y8e9gt2q2rhmv196pv"
    },
    {
        "full_name": "Philadelphia Eagles",
        "id": "par_01hqmkr1yjedgakx37g743855e"
    },
    {
        "full_name": "San Francisco 49ers",
        "id": "par_01hqmkr1ymfv0a8kfg96ha10ag"
    }
]
```

**Notes:** Should be treated as a whitelist; may include inactive participants.

## Usage Quota Cost

**1 credit** per request.

---

# GET Historical Odds

Returns historical odds snapshot at a specified timestamp. **Requires paid plan.**

- 10-minute intervals before September 2022
- 5-minute intervals after September 2022
- Data available from June 6, 2020

## Endpoint

```
GET /v4/historical/sports/{sport}/odds/?apiKey={apiKey}&regions={regions}&markets={markets}&date={date}
```

## Parameters

Same as GET Odds plus:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | Yes | ISO 8601 timestamp. Returns closest equal or earlier snapshot |

## Example Request

```
https://api.the-odds-api.com/v4/historical/sports/americanfootball_nfl/odds/?apiKey=YOUR_API_KEY&regions=us&markets=h2h&oddsFormat=american&date=2021-10-18T12:00:00Z
```

## Example Response

```json
{
    "timestamp": "2021-10-18T11:55:00Z",
    "previous_timestamp": "2021-10-18T11:45:00Z",
    "next_timestamp": "2021-10-18T12:05:00Z",
    "data": [
        {
            "id": "4edd5ce090a3ec6192053b10d27b87b0",
            "sport_key": "americanfootball_nfl",
            "sport_title": "NFL",
            "commence_time": "2021-10-19T00:15:00Z",
            "home_team": "Tennessee Titans",
            "away_team": "Buffalo Bills",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "title": "DraftKings",
                    "last_update": "2021-10-18T11:48:09Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {
                                    "name": "Buffalo Bills",
                                    "price": -294
                                },
                                {
                                    "name": "Tennessee Titans",
                                    "price": 230
                                }
                            ]
                        }
                    ]
                },
                {
                    "key": "fanduel",
                    "title": "FanDuel",
                    "last_update": "2021-10-18T11:47:58Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {
                                    "name": "Buffalo Bills",
                                    "price": -270
                                },
                                {
                                    "name": "Tennessee Titans",
                                    "price": 220
                                }
                            ]
                        }
                    ]
                },
                {
                    "key": "betmgm",
                    "title": "BetMGM",
                    "last_update": "2021-10-18T11:44:23Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {
                                    "name": "Buffalo Bills",
                                    "price": -250
                                },
                                {
                                    "name": "Tennessee Titans",
                                    "price": 210
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
```

## Response Schema (Wrapper)

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | Snapshot time (closest to requested date) |
| `previous_timestamp` | string | Earlier available snapshot |
| `next_timestamp` | string | Later available snapshot |
| `data` | array | Array of events with odds (same structure as current /odds) |

## Usage Quota Cost

Formula: `10 × [number of markets] × [number of regions]`

| Markets | Regions | Cost |
|---------|---------|------|
| 1 | 1 | 10 credits |
| 3 | 1 | 30 credits |
| 1 | 3 | 30 credits |
| 3 | 3 | 90 credits |

**Important Notes:**
- Prior to September 18, 2022: only decimal odds captured; American odds calculated from decimal
- Empty responses do NOT count against quota
- Data errors can occur; API team corrects current odds quickly but errors may persist in historical data

---

# GET Historical Events

Returns historical event list as it appeared at a given timestamp. **Requires paid plan.**

## Endpoint

```
GET /v4/historical/sports/{sport}/events?apiKey={apiKey}&date={date}
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sport` | string | Yes | Sport key |
| `apiKey` | string | Yes | Your subscription API key |
| `date` | string | Yes | ISO 8601 timestamp for snapshot |
| `dateFormat` | string | No | `unix` or `iso` |
| `eventIds` | string | No | Comma-separated event IDs |
| `commenceTimeFrom` | string | No | ISO 8601 start time filter |
| `commenceTimeTo` | string | No | ISO 8601 end time filter |
| `includeRotationNumbers` | boolean | No | Include rotation numbers |

## Example Request

```
https://api.the-odds-api.com/v4/historical/sports/basketball_nba/events?apiKey=YOUR_API_KEY&date=2023-11-29T22:42:00Z
```

## Example Response

```json
{
    "timestamp": "2023-11-29T22:40:39Z",
    "previous_timestamp": "2023-11-29T22:35:39Z",
    "next_timestamp": "2023-11-29T22:45:40Z",
    "data": [
        {
            "id": "da359da99aa27e97d38f2df709343998",
            "sport_key": "basketball_nba",
            "sport_title": "NBA",
            "commence_time": "2023-11-30T00:10:00Z",
            "home_team": "Detroit Pistons",
            "away_team": "Los Angeles Lakers"
        },
        {
            "id": "0a502b246aa29f8ac2edb7a3ddf71ae9",
            "sport_key": "basketball_nba",
            "sport_title": "NBA",
            "commence_time": "2023-11-30T00:10:00Z",
            "home_team": "Orlando Magic",
            "away_team": "Washington Wizards"
        },
        {
            "id": "2667f897a67e6cdad61bd26a3b941d83",
            "sport_key": "basketball_nba",
            "sport_title": "NBA",
            "commence_time": "2023-11-30T00:40:00Z",
            "home_team": "Toronto Raptors",
            "away_team": "Phoenix Suns"
        }
    ]
}
```

## Usage Quota Cost

**1 credit** per call. Free if no events found.

---

# GET Historical Event Odds

Returns historical odds for a single event at a specified timestamp. **Requires paid plan.**

## Endpoint

```
GET /v4/historical/sports/{sport}/events/{eventId}/odds?apiKey={apiKey}&regions={regions}&markets={markets}&date={date}
```

## Parameters

Same as GET Event Odds plus:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | Yes | ISO 8601 timestamp |

Additional markets available after `2023-05-03T05:30:00Z`. 5-minute snapshot intervals.

## Example Request

```
https://api.the-odds-api.com/v4/historical/sports/basketball_nba/events/da359da99aa27e97d38f2df709343998/odds?apiKey=YOUR_API_KEY&date=2023-11-29T22:45:00Z&regions=us&markets=player_points,h2h_q1
```

## Example Response

```json
{
    "timestamp": "2023-11-29T22:40:39Z",
    "previous_timestamp": "2023-11-29T22:35:39Z",
    "next_timestamp": "2023-11-29T22:45:40Z",
    "data": {
        "id": "da359da99aa27e97d38f2df709343998",
        "sport_key": "basketball_nba",
        "sport_title": "NBA",
        "commence_time": "2023-11-30T00:10:00Z",
        "home_team": "Detroit Pistons",
        "away_team": "Los Angeles Lakers",
        "bookmakers": [
            {
                "key": "draftkings",
                "title": "DraftKings",
                "last_update": "2023-11-29T22:40:09Z",
                "markets": [
                    {
                        "key": "h2h_q1",
                        "last_update": "2023-11-29T22:40:55Z",
                        "outcomes": [
                            {
                                "name": "Detroit Pistons",
                                "price": 2.5
                            },
                            {
                                "name": "Los Angeles Lakers",
                                "price": 1.56
                            }
                        ]
                    },
                    {
                        "key": "player_points",
                        "last_update": "2023-11-29T22:40:55Z",
                        "outcomes": [
                            {
                                "name": "Over",
                                "description": "Anthony Davis",
                                "price": 1.83,
                                "point": 23.5
                            },
                            {
                                "name": "Under",
                                "description": "Anthony Davis",
                                "price": 1.91,
                                "point": 23.5
                            },
                            {
                                "name": "Over",
                                "description": "Ausar Thompson",
                                "price": 1.87,
                                "point": 11.5
                            },
                            {
                                "name": "Under",
                                "description": "Ausar Thompson",
                                "price": 1.87,
                                "point": 11.5
                            }
                        ]
                    }
                ]
            }
        ]
    }
}
```

## Usage Quota Cost

Formula: `10 × [number of unique markets returned] × [number of regions]`

---

# Rate Limiting

The API implements rate limiting to prevent abuse. When the rate limit is exceeded, a **429** status code is returned. Wait and retry after a short delay.

---

# Response Headers

All endpoints return these headers:

| Header | Description |
|--------|-------------|
| `x-requests-remaining` | Remaining usage credits until quota reset |
| `x-requests-used` | Credits used since last quota reset |
| `x-requests-last` | Usage cost of the current API call |

---

# Betting Markets Reference

## Featured Markets

| Market Key | Name | Description |
|------------|------|-------------|
| `h2h` | Head to Head / Moneyline | Bet on the winning team or player (includes draw for soccer) |
| `spreads` | Points Spread / Handicap | Bet with point adjustments applied to teams |
| `totals` | Total Points / Over-Under | Bet on combined score over/under a threshold |
| `outrights` | Futures | Bet on long-term competition outcomes |
| `h2h_lay` | H2H Lay (Exchange) | Bet against an h2h outcome (exchanges only) |
| `outrights_lay` | Outrights Lay (Exchange) | Bet against an outrights outcome (exchanges only) |

## Additional Markets

| Market Key | Description |
|------------|-------------|
| `alternate_spreads` | All available point spread outcomes |
| `alternate_totals` | All available over/under outcomes |
| `btts` | Both Teams to Score (soccer only, Yes/No) |
| `draw_no_bet` | Match winner excluding draw (soccer) |
| `h2h_3_way` | Moneyline including draw option |
| `double_chance` | Double chance bet (soccer) |
| `team_totals` | Featured team totals |
| `alternate_team_totals` | All team totals options |

## Quarter Markets

| Market Key | Description |
|------------|-------------|
| `h2h_q1` | 1st Quarter Moneyline |
| `h2h_q2` | 2nd Quarter Moneyline |
| `h2h_q3` | 3rd Quarter Moneyline |
| `h2h_q4` | 4th Quarter Moneyline |
| `h2h_3_way_q1` | 1st Quarter 3-way |
| `h2h_3_way_q2` | 2nd Quarter 3-way |
| `h2h_3_way_q3` | 3rd Quarter 3-way |
| `h2h_3_way_q4` | 4th Quarter 3-way |
| `spreads_q1` | 1st Quarter Spreads |
| `spreads_q2` | 2nd Quarter Spreads |
| `spreads_q3` | 3rd Quarter Spreads |
| `spreads_q4` | 4th Quarter Spreads |
| `alternate_spreads_q1` | Alternate 1st Quarter Spreads |
| `alternate_spreads_q2` | Alternate 2nd Quarter Spreads |
| `alternate_spreads_q3` | Alternate 3rd Quarter Spreads |
| `alternate_spreads_q4` | Alternate 4th Quarter Spreads |
| `totals_q1` | 1st Quarter Over/Under |
| `totals_q2` | 2nd Quarter Over/Under |
| `totals_q3` | 3rd Quarter Over/Under |
| `totals_q4` | 4th Quarter Over/Under |
| `alternate_totals_q1` | Alternate 1st Quarter Totals |
| `alternate_totals_q2` | Alternate 2nd Quarter Totals |
| `alternate_totals_q3` | Alternate 3rd Quarter Totals |
| `alternate_totals_q4` | Alternate 4th Quarter Totals |
| `team_totals_q1` | Team Totals 1st Quarter |
| `team_totals_q2` | Team Totals 2nd Quarter |
| `team_totals_q3` | Team Totals 3rd Quarter |
| `team_totals_q4` | Team Totals 4th Quarter |
| `alternate_team_totals_q1` | Alternate Team Totals 1st Quarter |
| `alternate_team_totals_q2` | Alternate Team Totals 2nd Quarter |
| `alternate_team_totals_q3` | Alternate Team Totals 3rd Quarter |
| `alternate_team_totals_q4` | Alternate Team Totals 4th Quarter |

## Half Markets

| Market Key | Description |
|------------|-------------|
| `h2h_h1` | 1st Half Moneyline |
| `h2h_h2` | 2nd Half Moneyline |
| `h2h_3_way_h1` | 1st Half 3-way |
| `h2h_3_way_h2` | 2nd Half 3-way |
| `spreads_h1` | 1st Half Spreads |
| `spreads_h2` | 2nd Half Spreads |
| `alternate_spreads_h1` | Alternate 1st Half Spreads |
| `alternate_spreads_h2` | Alternate 2nd Half Spreads |
| `totals_h1` | 1st Half Over/Under |
| `totals_h2` | 2nd Half Over/Under |
| `alternate_totals_h1` | Alternate 1st Half Totals |
| `alternate_totals_h2` | Alternate 2nd Half Totals |
| `team_totals_h1` | Team Totals 1st Half |
| `team_totals_h2` | Team Totals 2nd Half |
| `alternate_team_totals_h1` | Alternate Team Totals 1st Half |
| `alternate_team_totals_h2` | Alternate Team Totals 2nd Half |

## Period Markets (Ice Hockey)

| Market Key | Description |
|------------|-------------|
| `h2h_p1` | 1st Period Moneyline |
| `h2h_p2` | 2nd Period Moneyline |
| `h2h_p3` | 3rd Period Moneyline |
| `h2h_3_way_p1` | 1st Period 3-way |
| `h2h_3_way_p2` | 2nd Period 3-way |
| `h2h_3_way_p3` | 3rd Period 3-way |
| `spreads_p1` | 1st Period Spreads |
| `spreads_p2` | 2nd Period Spreads |
| `spreads_p3` | 3rd Period Spreads |
| `alternate_spreads_p1` | Alternate 1st Period Spreads |
| `alternate_spreads_p2` | Alternate 2nd Period Spreads |
| `alternate_spreads_p3` | Alternate 3rd Period Spreads |
| `totals_p1` | 1st Period Over/Under |
| `totals_p2` | 2nd Period Over/Under |
| `totals_p3` | 3rd Period Over/Under |
| `alternate_totals_p1` | Alternate 1st Period Totals |
| `alternate_totals_p2` | Alternate 2nd Period Totals |
| `alternate_totals_p3` | Alternate 3rd Period Totals |
| `team_totals_p1` | Team Totals 1st Period |
| `team_totals_p2` | Team Totals 2nd Period |
| `team_totals_p3` | Team Totals 3rd Period |
| `alternate_team_totals_p1` | Alternate Team Totals 1st Period |
| `alternate_team_totals_p2` | Alternate Team Totals 2nd Period |
| `alternate_team_totals_p3` | Alternate Team Totals 3rd Period |

## Innings Markets (Baseball)

| Market Key | Description |
|------------|-------------|
| `h2h_1st_1_innings` | 1st Inning Moneyline |
| `h2h_1st_3_innings` | 1st 3 Innings Moneyline |
| `h2h_1st_5_innings` | 1st 5 Innings Moneyline |
| `h2h_1st_7_innings` | 1st 7 Innings Moneyline |
| `h2h_3_way_1st_1_innings` | 1st Inning 3-way |
| `h2h_3_way_1st_3_innings` | 1st 3 Innings 3-way |
| `h2h_3_way_1st_5_innings` | 1st 5 Innings 3-way |
| `h2h_3_way_1st_7_innings` | 1st 7 Innings 3-way |
| `spreads_1st_1_innings` | 1st Inning Spreads |
| `spreads_1st_3_innings` | 1st 3 Innings Spreads |
| `spreads_1st_5_innings` | 1st 5 Innings Spreads |
| `spreads_1st_7_innings` | 1st 7 Innings Spreads |
| `alternate_spreads_1st_1_innings` | Alternate 1st Inning Spreads |
| `alternate_spreads_1st_3_innings` | Alternate 1st 3 Innings Spreads |
| `alternate_spreads_1st_5_innings` | Alternate 1st 5 Innings Spreads |
| `alternate_spreads_1st_7_innings` | Alternate 1st 7 Innings Spreads |
| `totals_1st_1_innings` | 1st Inning Over/Under |
| `totals_1st_3_innings` | 1st 3 Innings Over/Under |
| `totals_1st_5_innings` | 1st 5 Innings Over/Under |
| `totals_1st_7_innings` | 1st 7 Innings Over/Under |
| `alternate_totals_1st_1_innings` | Alternate 1st Inning Totals |
| `alternate_totals_1st_3_innings` | Alternate 1st 3 Innings Totals |
| `alternate_totals_1st_5_innings` | Alternate 1st 5 Innings Totals |
| `alternate_totals_1st_7_innings` | Alternate 1st 7 Innings Totals |

## Soccer-Specific Markets

| Market Key | Description |
|------------|-------------|
| `alternate_spreads_corners` | Handicap Corners |
| `alternate_totals_corners` | Total Corners Over/Under |
| `alternate_spreads_cards` | Handicap Cards/Bookings |
| `alternate_totals_cards` | Total Cards/Bookings Over/Under |

## Player Props — NFL / NCAAF / CFL

| Market Key | Description |
|------------|-------------|
| `player_pass_tds` | Pass Touchdowns Over/Under |
| `player_pass_yds` | Pass Yards Over/Under |
| `player_pass_completions` | Pass Completions Over/Under |
| `player_pass_attempts` | Pass Attempts Over/Under |
| `player_pass_interceptions` | Pass Interceptions Over/Under |
| `player_pass_longest_completion` | Longest Pass Completion |
| `player_pass_rush_yds` | Pass + Rush Yards Over/Under |
| `player_pass_rush_reception_tds` | Pass + Rush + Reception TDs |
| `player_pass_rush_reception_yds` | Pass + Rush + Reception Yards |
| `player_pass_yds_q1` | 1st Quarter Pass Yards |
| `player_rush_yds` | Rush Yards Over/Under |
| `player_rush_tds` | Rush Touchdowns Over/Under |
| `player_rush_attempts` | Rush Attempts Over/Under |
| `player_rush_longest` | Longest Rush Over/Under |
| `player_rush_reception_tds` | Rush + Reception Touchdowns |
| `player_rush_reception_yds` | Rush + Reception Yards |
| `player_receptions` | Receptions Over/Under |
| `player_reception_yds` | Reception Yards Over/Under |
| `player_reception_tds` | Reception Touchdowns Over/Under |
| `player_reception_longest` | Longest Reception Over/Under |
| `player_assists` | Assists Over/Under |
| `player_defensive_interceptions` | Defensive Interceptions Over/Under |
| `player_field_goals` | Field Goals Over/Under |
| `player_kicking_points` | Kicking Points Over/Under |
| `player_pats` | Points After Touchdown Over/Under |
| `player_sacks` | Sacks Over/Under |
| `player_solo_tackles` | Solo Tackles Over/Under |
| `player_tackles_assists` | Tackles + Assists Over/Under |
| `player_tds_over` | Touchdowns (Over only) |
| `player_1st_td` | 1st Touchdown Scorer |
| `player_anytime_td` | Anytime Touchdown Scorer |
| `player_last_td` | Last Touchdown Scorer |

### Alternate NFL Player Props

All of the above with `_alternate` suffix (e.g., `player_pass_tds_alternate`, `player_rush_yds_alternate`, etc.)

## Player Props — NBA / NCAAB / WNBA

| Market Key | Description |
|------------|-------------|
| `player_points` | Points Over/Under |
| `player_points_q1` | 1st Quarter Points |
| `player_rebounds` | Rebounds Over/Under |
| `player_rebounds_q1` | 1st Quarter Rebounds |
| `player_assists` | Assists Over/Under |
| `player_assists_q1` | 1st Quarter Assists |
| `player_threes` | Three-Pointers Over/Under |
| `player_blocks` | Blocks Over/Under |
| `player_steals` | Steals Over/Under |
| `player_blocks_steals` | Blocks + Steals Over/Under |
| `player_turnovers` | Turnovers Over/Under |
| `player_points_rebounds_assists` | Points + Rebounds + Assists |
| `player_points_rebounds` | Points + Rebounds Over/Under |
| `player_points_assists` | Points + Assists Over/Under |
| `player_rebounds_assists` | Rebounds + Assists Over/Under |
| `player_field_goals` | Field Goals Over/Under |
| `player_frees_made` | Free Throws Made Over/Under |
| `player_frees_attempts` | Free Throw Attempts Over/Under |
| `player_first_basket` | First Basket Scorer |
| `player_first_team_basket` | First Basket on Team |
| `player_double_double` | Double Double Achievement |
| `player_triple_double` | Triple Double Achievement |
| `player_method_of_first_basket` | Method of First Basket |
| `player_fantasy_points` | Fantasy Points (DFS only) |

### Alternate NBA Player Props

`player_points_alternate`, `player_rebounds_alternate`, `player_assists_alternate`, `player_blocks_alternate`, `player_steals_alternate`, `player_turnovers_alternate`, `player_threes_alternate`, `player_points_assists_alternate`, `player_points_rebounds_alternate`, `player_rebounds_assists_alternate`, `player_points_rebounds_assists_alternate`, `player_fantasy_points_alternate`

## Player Props — MLB

| Market Key | Description |
|------------|-------------|
| `batter_home_runs` | Home Runs Over/Under |
| `batter_first_home_run` | First Home Run |
| `batter_hits` | Hits Over/Under |
| `batter_total_bases` | Total Bases Over/Under |
| `batter_rbis` | RBIs Over/Under |
| `batter_runs_scored` | Runs Scored Over/Under |
| `batter_hits_runs_rbis` | Hits + Runs + RBIs |
| `batter_singles` | Singles Over/Under |
| `batter_doubles` | Doubles Over/Under |
| `batter_triples` | Triples Over/Under |
| `batter_walks` | Walks Over/Under |
| `batter_strikeouts` | Strikeouts Over/Under |
| `batter_stolen_bases` | Stolen Bases Over/Under |
| `pitcher_strikeouts` | Strikeouts Over/Under |
| `pitcher_record_a_win` | Pitcher to Record Win |
| `pitcher_hits_allowed` | Hits Allowed Over/Under |
| `pitcher_walks` | Walks Over/Under |
| `pitcher_earned_runs` | Earned Runs Over/Under |
| `pitcher_outs` | Outs Over/Under |

### Alternate MLB Player Props

`batter_total_bases_alternate`, `batter_home_runs_alternate`, `batter_hits_alternate`, `batter_rbis_alternate`, `batter_walks_alternate`, `batter_strikeouts_alternate`, `batter_runs_scored_alternate`, `batter_singles_alternate`, `batter_doubles_alternate`, `batter_triples_alternate`, `pitcher_hits_allowed_alternate`, `pitcher_walks_alternate`, `pitcher_strikeouts_alternate`

## Player Props — NHL

| Market Key | Description |
|------------|-------------|
| `player_points` | Points Over/Under |
| `player_power_play_points` | Power Play Points |
| `player_assists` | Assists Over/Under |
| `player_blocked_shots` | Blocked Shots Over/Under |
| `player_shots_on_goal` | Shots on Goal Over/Under |
| `player_goals` | Goals Over/Under |
| `player_total_saves` | Total Saves Over/Under |
| `player_goal_scorer_first` | First Goal Scorer |
| `player_goal_scorer_last` | Last Goal Scorer |
| `player_goal_scorer_anytime` | Anytime Goal Scorer |

### Alternate NHL Player Props

`player_points_alternate`, `player_assists_alternate`, `player_power_play_points_alternate`, `player_goals_alternate`, `player_shots_on_goal_alternate`, `player_blocked_shots_alternate`, `player_total_saves_alternate`

## Player Props — AFL

| Market Key | Description |
|------------|-------------|
| `player_disposals` | Disposals Over/Under |
| `player_disposals_over` | Disposals (Over only) |
| `player_goal_scorer_first` | First Goal Scorer |
| `player_goal_scorer_last` | Last Goal Scorer |
| `player_goal_scorer_anytime` | Anytime Goal Scorer |
| `player_goals_scored_over` | Goals Scored (Over only) |
| `player_marks_over` | Marks (Over only) |
| `player_marks_most` | Most Marks |
| `player_tackles_over` | Tackles (Over only) |
| `player_tackles_most` | Most Tackles |
| `player_afl_fantasy_points` | AFL Fantasy Points |
| `player_afl_fantasy_points_over` | AFL Fantasy Points (Over) |
| `player_afl_fantasy_points_most` | Most AFL Fantasy Points |
| `player_clearances_over` | Clearances (Over only) |
| `player_kicks_over` | Kicks (Over only) |
| `player_handballs_over` | Handballs (Over only) |

## Player Props — Rugby League

| Market Key | Description |
|------------|-------------|
| `player_try_scorer_first` | First Try Scorer |
| `player_try_scorer_last` | Last Try Scorer |
| `player_try_scorer_anytime` | Anytime Try Scorer |
| `player_try_scorer_over` | Tries Scored (Over only) |

## Player Props — Soccer

| Market Key | Description |
|------------|-------------|
| `player_goal_scorer_anytime` | Anytime Goal Scorer |
| `player_first_goal_scorer` | First Goal Scorer |
| `player_last_goal_scorer` | Last Goal Scorer |
| `player_to_receive_card` | To Receive Card |
| `player_to_receive_red_card` | To Receive Red Card |
| `player_shots_on_target` | Shots on Target Over/Under |
| `player_shots` | Shots Over/Under |
| `player_assists` | Assists Over/Under |

---

# Bookmakers Reference

## US Bookmakers (Region: `us`)

| Key | Name |
|-----|------|
| `betonlineag` | BetOnline.ag |
| `betmgm` | BetMGM |
| `betrivers` | BetRivers |
| `betus` | BetUS |
| `bovada` | Bovada |
| `williamhill_us` | Caesars (paid only) |
| `draftkings` | DraftKings |
| `fanatics` | Fanatics (paid only) |
| `fanduel` | FanDuel |
| `lowvig` | LowVig.ag |
| `mybookieag` | MyBookie.ag |

## US Tier 2 Bookmakers (Region: `us2`)

| Key | Name |
|-----|------|
| `ballybet` | Bally Bet |
| `betanysports` | BetAnything |
| `betparx` | betPARX |
| `espnbet` | theScore Bet |
| `fliff` | Fliff |
| `hardrockbet` | Hard Rock Bet |
| `rebet` | ReBet (paid only) |

## US DFS Sites (Region: `us_dfs`)

| Key | Name |
|-----|------|
| `betr_us_dfs` | Betr Picks |
| `pick6` | DraftKings Pick6 |
| `prizepicks` | PrizePicks |
| `underdog` | Underdog Fantasy |

## US Exchanges (Region: `us_ex`)

| Key | Name |
|-----|------|
| `betopenly` | BetOpenly |
| `kalshi` | Kalshi |
| `novig` | Novig |
| `polymarket` | Polymarket |
| `prophetx` | ProphetX |

## UK Bookmakers (Region: `uk`)

| Key | Name |
|-----|------|
| `sport888` | 888sport |
| `betfair_ex_uk` | Betfair Exchange |
| `betfair_sb_uk` | Betfair Sportsbook |
| `betvictor` | Bet Victor |
| `betway` | Betway |
| `boylesports` | BoyleSports |
| `casumo` | Casumo |
| `coral` | Coral |
| `grosvenor` | Grosvenor |
| `ladbrokes_uk` | Ladbrokes |
| `leovegas` | LeoVegas |
| `livescorebet` | LiveScore Bet |
| `matchbook` | Matchbook |
| `paddypower` | Paddy Power |
| `skybet` | Sky Bet |
| `smarkets` | Smarkets |
| `unibet_uk` | Unibet |
| `virginbet` | Virgin Bet |
| `williamhill` | William Hill (UK) |

## EU Bookmakers (Region: `eu`)

| Key | Name |
|-----|------|
| `onexbet` | 1xBet |
| `sport888` | 888sport |
| `betclic_fr` | Betclic (FR) |
| `betanysports` | BetAnySports |
| `betfair_ex_eu` | Betfair Exchange |
| `betonlineag` | BetOnline.ag |
| `betsson` | Betsson |
| `codere_it` | Codere (IT) |
| `betvictor` | Bet Victor |
| `coolbet` | Coolbet |
| `everygame` | Everygame |
| `gtbets` | GTbets |
| `leovegas_se` | LeoVegas (SE) |
| `marathonbet` | Marathon Bet |
| `matchbook` | Matchbook |
| `mybookieag` | MyBookie.ag |
| `nordicbet` | NordicBet |
| `parionssport_fr` | Parions Sport (FR) |
| `pinnacle` | Pinnacle |
| `pmu_fr` | PMU (FR) |
| `suprabets` | Suprabets |
| `tipico_de` | Tipico (DE) |
| `unibet_fr` | Unibet (FR) |
| `unibet_it` | Unibet (IT) |
| `unibet_nl` | Unibet (NL) |
| `unibet_se` | Unibet (SE) |
| `williamhill` | William Hill |
| `winamax_de` | Winamax (DE) |
| `winamax_fr` | Winamax (FR) |

## French Bookmakers (Region: `fr`)

| Key | Name |
|-----|------|
| `betclic_fr` | Betclic (FR) |
| `netbet_fr` | NetBet (FR) |
| `parionssport_fr` | Parions Sport (FR) |
| `pmu_fr` | PMU (FR) |
| `unibet_fr` | Unibet (FR) |
| `winamax_fr` | Winamax (FR) |

## Swedish Bookmakers (Region: `se`)

| Key | Name |
|-----|------|
| `atg_se` | ATG (SE) |
| `betsson` | Betsson |
| `campobet_se` | CampoBet (SE) |
| `leovegas_se` | LeoVegas (SE) |
| `mrgreen_se` | Mr Green (SE) |
| `nordicbet` | NordicBet |
| `sport888_se` | 888sport (SE) |
| `svenskaspel_se` | Svenska Spel |
| `unibet_se` | Unibet (SE) |

## Australian Bookmakers (Region: `au`)

| Key | Name |
|-----|------|
| `betfair_ex_au` | Betfair Exchange |
| `betr_au` | Betr |
| `betright` | Bet Right |
| `bet365_au` | Bet365 AU (paid only) |
| `dabble_au` | Dabble AU (paid only) |
| `ladbrokes_au` | Ladbrokes |
| `neds` | Neds |
| `playup` | PlayUp |
| `pointsbetau` | PointsBet (AU) |
| `sportsbet` | SportsBet |
| `tab` | TAB |
| `tabtouch` | TABtouch |
| `unibet` | Unibet |

---

# Sports Reference

## American Football

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `americanfootball_cfl` | CFL | Yes |
| `americanfootball_ncaaf` | NCAAF | Yes |
| `americanfootball_ncaaf_championship_winner` | NCAAF Championship Winner | - |
| `americanfootball_nfl` | NFL | Yes |
| `americanfootball_nfl_preseason` | NFL Preseason | Yes |
| `americanfootball_nfl_super_bowl_winner` | NFL Super Bowl Winner | - |
| `americanfootball_ufl` | UFL | Yes |

## Australian Rules Football

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `aussierules_afl` | AFL | Yes |

## Baseball

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `baseball_mlb` | MLB | Yes |
| `baseball_mlb_preseason` | MLB Preseason | Yes |
| `baseball_mlb_world_series_winner` | MLB World Series Winner | - |
| `baseball_milb` | Minor League Baseball | - |
| `baseball_npb` | NPB | - |
| `baseball_kbo` | KBO League | - |
| `baseball_ncaa` | NCAA Baseball | - |

## Basketball

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `basketball_euroleague` | Basketball Euroleague | Yes |
| `basketball_nba` | NBA | Yes |
| `basketball_nba_preseason` | NBA Preseason | Yes |
| `basketball_nba_all_stars` | NBA All Star | - |
| `basketball_nba_summer_league` | NBA Summer League | Yes |
| `basketball_nba_championship_winner` | NBA Championship Winner | - |
| `basketball_wnba` | WNBA | Yes |
| `basketball_ncaab` | NCAAB | Yes |
| `basketball_wncaab` | WNCAAB | Yes |
| `basketball_ncaab_championship_winner` | NCAAB Championship Winner | - |
| `basketball_nbl` | NBL (Australia) | Yes |

## Boxing

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `boxing_boxing` | Boxing | - |

## Cricket

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `cricket_asia_cup` | Asia Cup | - |
| `cricket_big_bash` | Big Bash | - |
| `cricket_caribbean_premier_league` | Caribbean Premier League | - |
| `cricket_icc_trophy` | ICC Champions Trophy | - |
| `cricket_icc_world_cup` | ICC World Cup | - |
| `cricket_icc_world_cup_womens` | ICC Women's World Cup | - |
| `cricket_international_t20` | International Twenty20 | - |
| `cricket_ipl` | IPL | - |
| `cricket_odi` | One Day Internationals | - |
| `cricket_psl` | Pakistan Super League | - |
| `cricket_t20_blast` | T20 Blast | - |
| `cricket_t20_world_cup` | T20 World Cup | - |
| `cricket_test_match` | Test Matches | - |
| `cricket_the_hundred` | The Hundred | - |

## Golf

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `golf_masters_tournament_winner` | Masters Tournament Winner | - |
| `golf_pga_championship_winner` | PGA Championship Winner | - |
| `golf_the_open_championship_winner` | The Open Winner | - |
| `golf_us_open_winner` | US Open Winner | - |

## Handball

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `handball_germany_bundesliga` | Handball-Bundesliga | Yes |

## Ice Hockey

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `icehockey_nhl` | NHL | Yes |
| `icehockey_nhl_preseason` | NHL Preseason | Yes |
| `icehockey_ahl` | AHL | - |
| `icehockey_nhl_championship_winner` | NHL Championship Winner | - |
| `icehockey_liiga` | Finnish Liiga | - |
| `icehockey_mestis` | Finnish Mestis | - |
| `icehockey_sweden_hockey_league` | SHL | Yes |
| `icehockey_sweden_allsvenskan` | HockeyAllsvenskan | Yes |

## Lacrosse

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `lacrosse_pll` | Premier Lacrosse League | - |
| `lacrosse_ncaa` | NCAA Lacrosse | - |

## Mixed Martial Arts

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `mma_mixed_martial_arts` | MMA | - |

## Politics

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `politics_us_presidential_election_winner` | US Presidential Elections Winner | - |

## Rugby League

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `rugbyleague_nrl` | NRL | Yes |
| `rugbyleague_nrl_state_of_origin` | NRL State of Origin | - |

## Rugby Union

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `rugbyunion_six_nations` | Six Nations | - |

## Soccer

| Sport Key | Title | Scores |
|-----------|-------|--------|
| `soccer_africa_cup_of_nations` | Africa Cup of Nations | - |
| `soccer_argentina_primera_division` | Primera División - Argentina | Yes |
| `soccer_australia_aleague` | A-League | Yes |
| `soccer_austria_bundesliga` | Austrian Football Bundesliga | Yes |
| `soccer_belgium_first_div` | Belgium First Div | Yes |
| `soccer_brazil_campeonato` | Brazil Série A | Yes |
| `soccer_brazil_serie_b` | Brazil Série B | Yes |
| `soccer_chile_campeonato` | Primera División - Chile | Yes |
| `soccer_china_superleague` | Super League - China | Yes |
| `soccer_concacaf_gold_cup` | CONCACAF Gold Cup | - |
| `soccer_concacaf_leagues_cup` | CONCACAF Leagues Cup | Yes |
| `soccer_conmebol_copa_america` | Copa América | Yes |
| `soccer_conmebol_copa_libertadores` | Copa Libertadores | Yes |
| `soccer_conmebol_copa_sudamericana` | Copa Sudamericana | Yes |
| `soccer_denmark_superliga` | Denmark Superliga | Yes |
| `soccer_efl_champ` | Championship | Yes |
| `soccer_england_efl_cup` | EFL Cup | Yes |
| `soccer_england_league1` | League 1 | Yes |
| `soccer_england_league2` | League 2 | Yes |
| `soccer_epl` | EPL | Yes |
| `soccer_fa_cup` | FA Cup | Yes |
| `soccer_fifa_world_cup` | FIFA World Cup | Yes |
| `soccer_fifa_world_cup_qualifiers_europe` | FIFA World Cup Qualifiers - Europe | - |
| `soccer_fifa_world_cup_qualifiers_south_america` | FIFA WC Qualifiers - South America | - |
| `soccer_fifa_world_cup_womens` | FIFA Women's World Cup | Yes |
| `soccer_fifa_world_cup_winner` | FIFA World Cup Winner | - |
| `soccer_fifa_club_world_cup` | FIFA Club World Cup | Yes |
| `soccer_finland_veikkausliiga` | Veikkausliiga - Finland | Yes |
| `soccer_france_coupe_de_france` | Coupe de France | - |
| `soccer_france_ligue_one` | Ligue 1 - France | Yes |
| `soccer_france_ligue_two` | Ligue 2 - France | Yes |
| `soccer_germany_bundesliga` | Bundesliga - Germany | Yes |
| `soccer_germany_bundesliga2` | Bundesliga 2 - Germany | Yes |
| `soccer_germany_bundesliga_women` | Frauen-Bundesliga | - |
| `soccer_germany_dfb_pokal` | DFB-Pokal | - |
| `soccer_germany_liga3` | 3. Liga - Germany | Yes |
| `soccer_greece_super_league` | Super League - Greece | Yes |
| `soccer_italy_coppa_italia` | Coppa Italia | - |
| `soccer_italy_serie_a` | Serie A - Italy | Yes |
| `soccer_italy_serie_b` | Serie B - Italy | Yes |
| `soccer_japan_j_league` | J League | Yes |
| `soccer_korea_kleague1` | K League 1 | Yes |
| `soccer_league_of_ireland` | League of Ireland | Yes |
| `soccer_mexico_ligamx` | Liga MX | Yes |
| `soccer_netherlands_eredivisie` | Dutch Eredivisie | Yes |
| `soccer_norway_eliteserien` | Eliteserien - Norway | Yes |
| `soccer_poland_ekstraklasa` | Ekstraklasa - Poland | Yes |
| `soccer_portugal_primeira_liga` | Primeira Liga - Portugal | Yes |
| `soccer_russia_premier_league` | Premier League - Russia | Yes |
| `soccer_saudi_arabia_pro_league` | Saudi Pro League | - |
| `soccer_spain_copa_del_rey` | Copa del Rey | - |
| `soccer_spain_la_liga` | La Liga - Spain | Yes |
| `soccer_spain_segunda_division` | La Liga 2 - Spain | Yes |
| `soccer_spl` | Premiership - Scotland | Yes |
| `soccer_sweden_allsvenskan` | Allsvenskan - Sweden | Yes |
| `soccer_sweden_superettan` | Superettan - Sweden | Yes |
| `soccer_switzerland_superleague` | Swiss Superleague | Yes |
| `soccer_turkey_super_league` | Turkey Super League | Yes |
| `soccer_uefa_champs_league` | UEFA Champions League | Yes |
| `soccer_uefa_champs_league_qualification` | UEFA Champions League Qualification | Yes |
| `soccer_uefa_champs_league_women` | UEFA Women's Champions League | Yes |
| `soccer_uefa_europa_league` | UEFA Europa League | Yes |
| `soccer_uefa_europa_conference_league` | UEFA Europa Conference League | Yes |
| `soccer_uefa_european_championship` | UEFA Euro | Yes |
| `soccer_uefa_euro_qualification` | UEFA Euro Qualification | Yes |
| `soccer_uefa_nations_league` | UEFA Nations League | Yes |
| `soccer_usa_mls` | MLS | Yes |

## Tennis — ATP

| Sport Key | Title |
|-----------|-------|
| `tennis_atp_aus_open_singles` | ATP Australian Open |
| `tennis_atp_canadian_open` | ATP Canadian Open |
| `tennis_atp_china_open` | ATP China Open |
| `tennis_atp_cincinnati_open` | ATP Cincinnati Open |
| `tennis_atp_dubai` | ATP Dubai Championships |
| `tennis_atp_french_open` | ATP French Open |
| `tennis_atp_indian_wells` | ATP Indian Wells |
| `tennis_atp_italian_open` | ATP Italian Open |
| `tennis_atp_madrid_open` | ATP Madrid Open |
| `tennis_atp_miami_open` | ATP Miami Open |
| `tennis_atp_monte_carlo_masters` | ATP Monte-Carlo Masters |
| `tennis_atp_paris_masters` | ATP Paris Masters |
| `tennis_atp_qatar_open` | ATP Qatar Open |
| `tennis_atp_shanghai_masters` | ATP Shanghai Masters |
| `tennis_atp_us_open` | ATP US Open |
| `tennis_atp_wimbledon` | ATP Wimbledon |

## Tennis — WTA

| Sport Key | Title |
|-----------|-------|
| `tennis_wta_aus_open_singles` | WTA Australian Open |
| `tennis_wta_canadian_open` | WTA Canadian Open |
| `tennis_wta_china_open` | WTA China Open |
| `tennis_wta_cincinnati_open` | WTA Cincinnati Open |
| `tennis_wta_dubai` | WTA Dubai Championships |
| `tennis_wta_french_open` | WTA French Open |
| `tennis_wta_indian_wells` | WTA Indian Wells |
| `tennis_wta_italian_open` | WTA Italian Open |
| `tennis_wta_madrid_open` | WTA Madrid Open |
| `tennis_wta_miami_open` | WTA Miami Open |
| `tennis_wta_qatar_open` | WTA Qatar Open |
| `tennis_wta_us_open` | WTA US Open |
| `tennis_wta_wimbledon` | WTA Wimbledon |
| `tennis_wta_wuhan_open` | WTA Wuhan Open |

---

# Odds Formats

## Decimal Odds
Represents total return including stake. Example: 2.50 means $2.50 returned for every $1 bet ($1.50 profit).

## American Odds
- **Positive** (e.g., +240): Shows profit on a $100 bet. +240 = $240 profit on $100 bet.
- **Negative** (e.g., -275): Shows stake needed to win $100. -275 = bet $275 to win $100.

---

# Key Concepts

- **Regions** determine which bookmakers are returned
- **`upcoming`** can be used as the sport key to get odds across all in-season sports
- **Empty responses** never count against quota
- **Bookmakers may temporarily disappear** from API responses due to maintenance
- **Some bookmakers may not list odds** for less popular sports
- **Prior to September 18, 2022**: Historical data only has decimal odds; American odds are calculated

---

# Usage Quota Cost Summary

| Endpoint | Cost Formula |
|----------|-------------|
| GET /sports | Free |
| GET /odds | markets × regions |
| GET /scores (no daysFrom) | 1 |
| GET /scores (with daysFrom) | 2 |
| GET /events | Free |
| GET /event odds | unique markets returned × regions |
| GET /event markets | 1 |
| GET /participants | 1 |
| GET /historical odds | 10 × markets × regions |
| GET /historical events | 1 (free if empty) |
| GET /historical event odds | 10 × unique markets returned × regions |

---

# Code Samples

The Odds API provides code examples in Python and Node.js.

## Python

Install the requests library:

```bash
pip install requests
```

### Get Sports

```python
import requests

API_KEY = 'YOUR_API_KEY'

sports_response = requests.get(
    'https://api.the-odds-api.com/v4/sports',
    params={
        'api_key': API_KEY
    }
)

print('Remaining requests:', sports_response.headers['x-requests-remaining'])
print('Used requests:', sports_response.headers['x-requests-used'])

sports = sports_response.json()
print(sports)
```

### Get Odds

```python
import requests

API_KEY = 'YOUR_API_KEY'
SPORT = 'americanfootball_nfl'  # use sport key from /sports
REGIONS = 'us'  # us | uk | eu | au
MARKETS = 'h2h,spreads'  # h2h | spreads | totals | outrights
ODDS_FORMAT = 'american'  # decimal | american
DATE_FORMAT = 'iso'  # iso | unix

odds_response = requests.get(
    f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
    params={
        'api_key': API_KEY,
        'regions': REGIONS,
        'markets': MARKETS,
        'oddsFormat': ODDS_FORMAT,
        'dateFormat': DATE_FORMAT,
    }
)

if odds_response.status_code != 200:
    print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')
else:
    odds_json = odds_response.json()
    print('Number of events:', len(odds_json))
    print('Remaining requests:', odds_response.headers['x-requests-remaining'])
    print('Used requests:', odds_response.headers['x-requests-used'])
```

### Get Scores

```python
import requests

API_KEY = 'YOUR_API_KEY'
SPORT = 'basketball_nba'

scores_response = requests.get(
    f'https://api.the-odds-api.com/v4/sports/{SPORT}/scores',
    params={
        'api_key': API_KEY,
        'daysFrom': 1,
    }
)

scores = scores_response.json()
print(scores)
```

### Get Event Odds (Single Event)

```python
import requests

API_KEY = 'YOUR_API_KEY'
SPORT = 'americanfootball_nfl'
EVENT_ID = 'a512a48a58c4329048174217b2cc7ce0'

event_odds_response = requests.get(
    f'https://api.the-odds-api.com/v4/sports/{SPORT}/events/{EVENT_ID}/odds',
    params={
        'api_key': API_KEY,
        'regions': 'us',
        'markets': 'player_pass_tds',
        'oddsFormat': 'american',
    }
)

event_odds = event_odds_response.json()
print(event_odds)
```

### Get Historical Odds

```python
import requests

API_KEY = 'YOUR_API_KEY'
SPORT = 'americanfootball_nfl'

historical_response = requests.get(
    f'https://api.the-odds-api.com/v4/historical/sports/{SPORT}/odds',
    params={
        'api_key': API_KEY,
        'regions': 'us',
        'markets': 'h2h',
        'oddsFormat': 'american',
        'date': '2021-10-18T12:00:00Z',
    }
)

historical = historical_response.json()
print('Timestamp:', historical['timestamp'])
print('Number of events:', len(historical['data']))
```

**Security Note:** For Repl.it or similar environments, store your API key in a `.env` file:
```python
import os
api_key = os.getenv("API_KEY")
```

## Node.js

Install axios:

```bash
npm install axios
```

### Get Sports

```javascript
const axios = require('axios');

const API_KEY = 'YOUR_API_KEY';

axios.get('https://api.the-odds-api.com/v4/sports', {
    params: {
        api_key: API_KEY
    }
})
.then(response => {
    console.log('Remaining requests:', response.headers['x-requests-remaining']);
    console.log('Used requests:', response.headers['x-requests-used']);
    console.log(response.data);
})
.catch(error => {
    console.log('Error:', error.message);
});
```

### Get Odds

```javascript
const axios = require('axios');

const API_KEY = 'YOUR_API_KEY';
const SPORT = 'americanfootball_nfl';
const REGIONS = 'us';
const MARKETS = 'h2h,spreads';
const ODDS_FORMAT = 'american';
const DATE_FORMAT = 'iso';

axios.get(`https://api.the-odds-api.com/v4/sports/${SPORT}/odds`, {
    params: {
        api_key: API_KEY,
        regions: REGIONS,
        markets: MARKETS,
        oddsFormat: ODDS_FORMAT,
        dateFormat: DATE_FORMAT,
    }
})
.then(response => {
    console.log('Number of events:', response.data.length);
    console.log('Remaining requests:', response.headers['x-requests-remaining']);
    console.log('Used requests:', response.headers['x-requests-used']);
})
.catch(error => {
    console.log('Error status:', error.response.status);
    console.log('Error:', error.response.data);
});
```

**Security Note:** Store API key in `.env` file:
```javascript
const api_key = process.env.API_KEY;
```

---

# Update Intervals

Odds update frequency varies by market type and event timing.

| Market Type | Pre-Match | In-Play |
|-------------|-----------|---------|
| **Featured Markets** (h2h, spreads, totals) | 60 seconds | 40 seconds |
| **Additional Markets** (player props, alternates, period markets) | 60 seconds | 60 seconds |
| **Outrights / Futures** | 5 minutes | 60 seconds |
| **Betting Exchanges** (all markets) | 30 seconds | 20 seconds |

**Important:** Six hours before an event's start time, the update interval begins decreasing from the pre-match interval, eventually reaching the in-play interval once the event goes live.

---

# Historical Odds Data

## Data Availability

- **Featured Markets** (h2h, spreads, totals): Available from **June 6, 2020**
  - 10-minute snapshot intervals before September 2022
  - 5-minute snapshot intervals from September 2022 onwards
- **Additional Markets** (player props, period markets, alternates): Available from **May 3, 2023**
  - 5-minute snapshot intervals

## Access

Historical data is **only available on paid usage plans.**

## Endpoints

1. **Historical Odds** (`/v4/historical/sports/{sport}/odds`) — bulk snapshot for a sport
2. **Historical Events** (`/v4/historical/sports/{sport}/events`) — event list at a point in time
3. **Historical Event Odds** (`/v4/historical/sports/{sport}/events/{eventId}/odds`) — single event odds at a point in time

## Response Navigation

All historical responses include `timestamp`, `previous_timestamp`, and `next_timestamp` for navigating through snapshots chronologically.

## Cost

- Historical Odds: `10 × markets × regions` per request
- Historical Events: 1 credit per request
- Historical Event Odds: `10 × unique markets × regions` per request

---

# FAQs

**Q: What happens when I subscribe?**
A: You receive an email with your API key and starter resources.

**Q: When am I billed?**
A: For paid plans, billing happens straight away. Payment then happens automatically each month thereafter, on the same day of the month that the subscription started.

**Q: How can I cancel?**
A: Subscriptions can be cancelled anytime via the cancellation form or accounts portal. Cancellation takes effect before the next billing cycle.

**Q: What is a request?**
A: A single request returns live and upcoming games for a given sport, betting market, and bookmaker region. Each request counts as one usage quota unit.

**Q: How frequently are odds updated?**
A: See the Update Intervals section above.

**Q: When are usage credits reset?**
A: Usage credits are automatically reset on the first of every month.

**Q: How can I update my credit card details?**
A: Manage billing through the account portal using the same email as your subscription.

**Q: How can I get in touch?**
A: Contact team@the-odds-api.com or reply to the API key delivery email.

**Q: What if I'm not a programmer?**
A: Access sports odds data via Google Sheets or Excel add-ons using your API key.

**Q: What if I find an error?**
A: Verify discrepancies against the bookmaker's website before reporting. Include the API URL and relevant screenshots when contacting team@the-odds-api.com.

---

# Odds Widget

The Odds API offers an embeddable sports odds widget for websites with bookmaker affiliate link monetization.

## Pricing

| Plan | Price | Visits/Month |
|------|-------|-------------|
| Starter | Free | 500 |
| Small | $20/month | 5,000 |
| Medium | $100/month | 100,000 |

All plans include all sports, all bookmakers, and all featured betting markets. A "visit" is counted when a widget HTML tag is loaded.

## Configuration Options

- **Sport:** 200+ leagues/competitions
- **Bookmaker:** 50+ bookmakers (DraftKings, FanDuel, BetMGM, Caesars, Bovada, etc.)
- **Odds Format:** American or Decimal
- **Markets:** Head-to-head, Spreads, Totals (multi-select)
- **Custom Market Names:** Override default terminology

## Embedding

The widget uses an iframe format with customizable dimensions, border styling, and parameters.

## Features

- Affiliate links can be added post-installation through user accounts
- WordPress and Wix integration guides available
- Responsive design
