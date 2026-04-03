# PandaScore API — Complete Developer Guide

> **Purpose:** Antigravity-ready reference document for integrating PandaScore esports data API into Optimus Claudeus or any esports prediction/trading bot.
>
> **Source:** https://developers.pandascore.co/docs
>
> **API Version:** v2
>
> **Base URL (REST):** `https://api.pandascore.co`
>
> **Base URL (WebSocket):** `wss://live.pandascore.co`
>
> **API Reference:** https://developers.pandascore.co/reference

---

## Table of Contents

1. [Introduction & Data Coverage](#1-introduction--data-coverage)
2. [Fundamentals — Data Structure](#2-fundamentals--data-structure)
3. [Authentication](#3-authentication)
4. [Rate & Connection Limits](#4-rate--connection-limits)
5. [REST API — Formats](#5-rest-api--formats)
6. [Tracking Changes (Incidents API)](#6-tracking-changes-incidents-api)
7. [Tournaments In-Depth](#7-tournaments-in-depth)
8. [Matches Lifecycle](#8-matches-lifecycle)
9. [Match Formats](#9-match-formats)
10. [Filtering and Sorting](#10-filtering-and-sorting)
11. [Pagination](#11-pagination)
12. [Errors](#12-errors)
13. [Live API — WebSockets Overview](#13-live-api--websockets-overview)
14. [Events Recovery](#14-events-recovery)
15. [Disconnections](#15-disconnections)
16. [Sandbox Environment](#16-sandbox-environment)
17. [Frequently Asked Questions](#17-frequently-asked-questions)
18. [Quick Reference for Bot Integration](#18-quick-reference-for-bot-integration)

---

## 1. Introduction & Data Coverage

**Source:** https://developers.pandascore.co/docs/introduction

PandaScore provides historical and real-time statistics for **13 major esports titles**, including League of Legends, Counter-Strike, DotA2, and Valorant.

### Three Data Categories

#### Fixtures Data (Free Tier)
- Overview of esports competitions, schedules, and results
- Every match contains: name, scheduled time, format (e.g. best of 5), team opponents, live streams
- Real-time updates: match begin/end, final score, winning team

#### Historical Data (Paid)
- In-depth post-game team and player statistics
- Available for: Counter-Strike, League of Legends, DotA2, Valorant
- LoL example: 50+ unique player data points, 20+ unique team data points
- Available via REST API

#### Live Data (Paid — Pro)
- Real-time in-game statistics via WebSockets
- Two feeds: **Frames** (game-state snapshots every 2 seconds) and **Events** (key moment timeline)
- May experience delay from actual game server

### Common Applications
- Fantasy platforms
- Media and news platforms
- Data analysis (scouting, performance tracking)
- **Prediction** — historical team/player performances as predictors of future match outcomes
- Live scores and stats applications

### Key Resources
- Documentation: https://developers.pandascore.co/docs
- API Reference: https://developers.pandascore.co/reference/get_additions
- Coverage/Plans: https://pandascore.co/stats#coverage
- Support (Slack): https://join.slack.com/t/pandascore/shared_invite/zt-3ljcjj4mo-5q0ON2~qdef5umvzqq3mZw

---

## 2. Fundamentals — Data Structure

**Source:** https://developers.pandascore.co/docs/fundamentals

PandaScore uses a hierarchical data structure to map esports competitions:

```
League
  └── Series (timely occurrence of a League)
        └── Tournament (stage within a Series)
              └── Match (team-vs-team or player-vs-player)
                    └── Game (individual game within a match)
```

### Leagues
Top-level data structure representing a competition.
- Examples: "FIFA World Cup", "The International"
- Contains one or several child **Series**

### Series
A single timely occurrence of a parent League.
- Examples: "FIFA World Cup — 2018", "The International — 2018"
- Contains one or several child **Tournaments**

### Tournaments
A stage within a parent Series.
- Examples: "FIFA World Cup — 2018 — Group C", "The International — 2018 — Playoffs"
- Contains one or several child **Matches**
- Has unique standings and possible winner

### Matches
Team-vs-team or player-vs-player confrontation.
- Examples: "Denmark vs Australia" (1 game), "OG vs PSG.LGD" (5 games)
- Contains one or several child **Games**
- Most in-depth generic data structure

### Games
Game-level data structure is **specific to each video game**.
- Game IDs are unique per videogame
- In-game results should be retrieved via game-level endpoints (only for videogames supporting Historical Data)

---

## 3. Authentication

**Source:** https://developers.pandascore.co/docs/authentication

Access is restricted by token-based authentication. Token available at: https://app.pandascore.co/dashboard

> **WARNING:** Token is private — do NOT use in client-side applications.

### REST API — Two Methods

**Method 1: Bearer Token (Recommended)**

```bash
curl --request GET \
     --url 'https://api.pandascore.co/videogames' \
     --header 'Accept: application/json' \
     --header 'Authorization: Bearer YOUR_TOKEN'
```

**Method 2: URL Parameter**

```bash
curl --request GET \
     --url 'https://api.pandascore.co/videogames?token=YOUR_TOKEN' \
     --header 'Accept: application/json'
```

### WebSockets API — URL Parameter Only

```bash
wscat -c "wss://live.pandascore.co/matches/595466?token=YOUR_TOKEN"
```

### Python Example

```python
import httpx

PANDASCORE_TOKEN = "your_token_here"
BASE_URL = "https://api.pandascore.co"

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {PANDASCORE_TOKEN}"
}

response = httpx.get(f"{BASE_URL}/videogames", headers=headers)
data = response.json()
```

---

## 4. Rate & Connection Limits

**Source:** https://developers.pandascore.co/docs/rate-and-connections-limits

### REST API Rate Limits

| Plan | Rate Limit |
|------|-----------|
| Schedules, Results & Context Data (Free) | 1,000 requests/hour |
| Historical & Post-Match Data | 10,000 requests/hour |
| Real-time Data (Basic) | 10,000 requests/hour |
| Real-time Data (Pro) | 10,000 requests/hour |

- Remaining requests available in response header: `X-Rate-Limit-Remaining`
- Exceeding limit returns HTTP 429

### WebSocket Connection Limits
- Available on Real-time Data (Basic) and (Pro) plans
- Maximum **3 simultaneous connections** per match

---

## 5. REST API — Formats

**Source:** https://developers.pandascore.co/docs/formats

- Protocol: HTTPS
- Domain: `api.pandascore.co`
- Data format: JSON (sent and received)
- Blank fields: included with `null` values (not omitted)
- Dates: ISO-8601 format, UTC time

---

## 6. Tracking Changes (Incidents API)

**Source:** https://developers.pandascore.co/docs/tracking-changes

Track changes on Leagues, Series, Tournaments, Matches, Teams, and Players using the Incidents API.

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /additions` | Track resource creation |
| `GET /changes` | Track resource modification |
| `GET /deletions` | Track resource deletion |

### Common Use Cases

**Track new CS competitions:**
```
GET /additions?type=tournament,serie,league&videogame=cs-go
```

**Track LoL roster changes:**
```
GET /changes?type=team&videogame=league-of-legends
```

**Track deletions:**
```
GET /deletions
```

### Deletion Response Example

```json
[
  {
    "change_type": "deletion",
    "id": 3521,
    "modified_at": "2020-01-06T13:54:26Z",
    "object": {
      "deleted_at": "2020-01-06T13:54:26Z",
      "reason": "Model deleted",
      "videogame_id": 4
    },
    "type": "tournament"
  },
  {
    "change_type": "deletion",
    "id": 19766,
    "modified_at": "2020-01-05T19:53:52Z",
    "object": {
      "deleted_at": "2020-01-05T19:53:52Z",
      "reason": "Merged with 3428",
      "videogame_id": 1
    },
    "type": "player"
  }
]
```

> **Recommendation:** Implement polling logic around incidents endpoints to keep data up-to-date.

---

## 7. Tournaments In-Depth

**Source:** https://developers.pandascore.co/docs/tournaments-in-depth

### Retrieving Tournaments

| Endpoint | Purpose |
|----------|---------|
| `GET /tournaments` | All tournaments |
| `GET /tournaments/past` | Past tournaments |
| `GET /tournaments/running` | Ongoing tournaments |
| `GET /tournaments/upcoming` | Upcoming tournaments |
| `GET /tournaments/{id_or_slug}` | Specific tournament |

### Tournament Participants (Rosters)

**IMPORTANT:** Use tournament rosters, NOT team-level players to determine tournament participants. Team-level players represent contracted players, not necessarily tournament participants.

Roster endpoints:
- `GET /tournaments/{id_or_slug}` → `expected_roster` array
- `GET /tournaments/{id_or_slug}/rosters` → `rosters` array

### Tournament Brackets

- `has_bracket` field indicates if a tournament has a bracket
- `GET /tournaments/{id_or_slug}/brackets` → returns matches with `previous_matches` array
- Each predecessor has `match_id` and `type` (winner/loser)

### Tournament Standings

- `GET /tournaments/{id_or_slug}/standings` → participant performance and ranking

### Tournament Tiers

5 tiers: **S > A > B > C > D**

| Tier | Description | Examples |
|------|-------------|---------|
| S | Most prestigious, prize pool $250K-$1M+ | The International, LoL Worlds, CS Majors, VCT Masters |
| A | High level, international events & regional leagues | DPC Division 1, LPL/LCK/LCS/LEC, ESL Pro League |
| B | Middle-range, less common | International Qualifiers, TCL/LLA/CBLOL, DreamHack |
| C | Low profile, independent organizers, up to $75K prize | DPC Division 2, EU Regional leagues, ESL Impact |
| D | Very low profile, rarely above $10K prize | Most small CS tournaments, minor Valorant regions |

**Filtering by tier:**
```
GET /tournaments?filter[tier]=s
GET /tournaments?filter[tier]=s,a
```

---

## 8. Matches Lifecycle

**Source:** https://developers.pandascore.co/docs/matches-lifecycle

Match statuses follow a finite state machine:

```
not_started → running → finished
                     ↘ canceled (with or without winner/forfeit)
not_started → postponed → not_started (rescheduled)
not_started → canceled
```

### Status: `not_started`
- `status`: `not_started`
- `scheduled_at`: official playing time
- `begin_at`: same as `scheduled_at` (legacy)
- `end_at`: `null`
- WebSocket opens **15 minutes before** scheduled time

### Rescheduled Matches
- `rescheduled`: `true`
- `scheduled_at`: new date
- `original_scheduled_at`: initial date
- Only marked rescheduled when organizer officially announces new date (delays don't count)

### Status: `running`
- `status`: `running`
- `begin_at`: actual beginning time

### Status: `finished`
- `status`: `finished`
- `end_at`: match finish time
- `winner_id`: winning team/player ID
- `complete`: `true` when post-game stats are whole and available (for `detailed_stats=true` matches)

### Status: `canceled`
Without winner:
- `forfeit`: `false`, `begin_at`: `null`, `end_at`: `null`

With forfeit:
- `forfeit`: `true`, `winner_id`: set to winner

### Status: `postponed`
- Rescheduled to unknown date
- `scheduled_at` NOT updated until new date known

---

## 9. Match Formats

**Source:** https://developers.pandascore.co/docs/match-formats

Three match formats exist, indicated by the `match_type` field:

### `best_of`
- Maximum number of games specified in `number_of_games`
- Win condition: win more than half the games
- Unplayed games NOT returned in API

Example (Best of 3, ends 2-0):
- Game 1: winner team A
- Game 2: winner team A
- Game 3: not played, not in API response

### `first_to`
- Minimum games to win specified in `number_of_games`
- Match continues until a team reaches that number

Example (First to 3, ends 3-2):
- 5 games played total

### `red_bull_home_ground`
- Best of 5 with a twist (Valorant only)
- Each opponent picks a "Home Ground" map
- If one wins both Home Ground games → automatic match win
- If 1-1 after Home Grounds → standard best of 5 rules apply

---

## 10. Filtering and Sorting

**Source:** https://developers.pandascore.co/docs/filtering-and-sorting

### Filter (strict equality)

```
# Single value
GET /lol/champions?filter[name]=Brand

# Multiple values (comma-separated)
GET /lol/champions?filter[name]=Brand,Twitch
```

- Dates: UTC format, only date portion (day/month/year) is compared, time is ignored

### Search (substring match — strings only)

```
GET /lol/champions?search[name]=twi
```

### Range (numeric interval)

```
GET /lol/champions?range[hp]=500,1000
```

### Sort

```
# Ascending (default)
GET /lol/champions?sort=attackdamage

# Descending (prefix with minus)
GET /lol/champions?sort=-name

# Multi-field sort
GET /lol/champions?sort=attackdamage,-name
```

- `null` values: first in ascending, last in descending

---

## 11. Pagination

**Source:** https://developers.pandascore.co/docs/pagination

- Default: 50 items per page
- Maximum: 100 items per page
- First page: page 1

### Query Parameters

```
# Page number
GET /lol/champions?page[number]=2

# Page size
GET /lol/champions?page[size]=10
```

### Response Headers

| Header | Description |
|--------|-------------|
| `Link` | Navigation links (first, previous, next, last) |
| `X-Page` | Current page number |
| `X-Per-Page` | Current page length |
| `X-Total` | Total count of items |

### Link Header Example

```
<https://api.pandascore.co/matches/upcoming?page=18>; rel="last",
<https://api.pandascore.co/matches/upcoming?page=2>; rel="next"
```

---

## 12. Errors

**Source:** https://developers.pandascore.co/docs/errors

### Client Errors (4xx)

| Code | Definition |
|------|-----------|
| 400 | Bad Request — malformed request, syntax error in query params |
| 401 | Unauthorized — missing token |
| 403 | Forbidden — URL not available with your plan |
| 404 | Not Found — resource doesn't exist |
| 429 | Too Many Requests — rate limit reached |

### Error Response Format

```json
{
  "error": "Not Found",
  "message": "The resource does not exist."
}
```

### Server Errors (5xx)
- Issues on PandaScore's servers (rare)
- Retry the request — downtimes are often short
- Status page: https://status.pandascore.co/

---

## 13. Live API — WebSockets Overview

**Source:** https://developers.pandascore.co/docs/websockets-overview

### Connecting to WebSockets

**Step 1: Find live matches**

```
GET /lives
```

Returns matches with WebSocket endpoints:

```json
{
  "endpoints": [
    {
      "match_id": 595477,
      "open": true,
      "type": "frames",
      "url": "wss://live.pandascore.co/matches/595477"
    },
    {
      "match_id": 595477,
      "open": true,
      "type": "events",
      "url": "wss://live.pandascore.co/matches/595477/events"
    }
  ],
  "match": { ... }
}
```

**Step 2: Connect**

```bash
wscat -c 'wss://live.pandascore.co/matches/595477?token=YOUR_TOKEN'
```

```javascript
const socket = new WebSocket('wss://live.pandascore.co/matches/8191?token=YOUR_TOKEN')
socket.onmessage = function (event) {
    console.log(JSON.parse(event.data))
}
```

After successful connection, server sends:
```json
{"type":"hello","payload":{}}
```

### Frames Feed
- Snapshot of all game data points every **2 seconds**
- Contains all team statistics
- Available on Basic and Pro plans
- Post-game retrieval: LoL via `GET /lol/games/{id}/frames`, CS via `GET /csgo/games/{id}/rounds`

### Events Feed
- Timeline of key in-game events (kills, objectives, etc.)
- Sent as they occur
- **Pro plan only**
- Post-game retrieval: LoL and CS specific endpoints

### Connection Limits
- Max **3 simultaneous connections** per match per endpoint

---

## 14. Events Recovery

**Source:** https://developers.pandascore.co/docs/events-recovery

> **Pro plan only.** Available for League of Legends and Counter-Strike only.

Recover all previously sent events (even if client was not connected):

```json
// Send this message on the events WebSocket channel:
{
  "type": "recover",
  "payload": {
    "game_id": 211051
  }
}
```

### Node.js Example

```javascript
const socket = new WebSocket('wss://live.pandascore.co/matches/548763/events?token=YOUR_TOKEN')

socket.onmessage = function (event) {
    console.log(JSON.parse(event.data))
}

socket.onopen = function (event) {
    socket.send(JSON.stringify({
        "type": "recover",
        "payload": {"game_id": 211051}
    }))
}
```

---

## 15. Disconnections

**Source:** https://developers.pandascore.co/docs/disconnections

### Disconnect Status Codes

| Code | Meaning |
|------|---------|
| 1000 | Match finished (normal closure) |
| 4001 | Unauthorized — missing token |
| 4003 | Forbidden — not available with your plan |
| 4029 | Too Many Connections — max 3 simultaneous per match |
| Other 1xxx | Server error — retry connection |

On server error disconnect: reconnect and use Events Recovery to get missed events.

---

## 16. Sandbox Environment

**Source:** https://developers.pandascore.co/docs/sandbox-environment

Simulate game conditions for Counter-Strike and League of Legends without waiting for live matches.

### League of Legends

```bash
POST https://live.pandascore.co/api/lol/replay
```

Response:
```json
{
    "playback_speed": 1.0,
    "ingame_timestamp": null,
    "events_url": "wss://live.pandascore.co/replays/league-of-legends/events",
    "frames_url": "wss://live.pandascore.co/replays/league-of-legends/frames"
}
```

### Counter-Strike

```bash
POST https://live.pandascore.co/api/csgo/replay
```

Response:
```json
{
    "playback_speed": 1.0,
    "round_number": null,
    "events_url": "wss://live.pandascore.co/replays/cs-go/events",
    "frames_url": "wss://live.pandascore.co/replays/cs-go/frames"
}
```

### Query Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `playback_speed` | enum | Speed: `1`, `1.5`, `2` | `1` |
| `ingame_timestamp` | int | Start timestamp in seconds (LoL only) | `0` |
| `round_number` | int | Start round number (CS only) | `1` |

Example: `?playback_speed=2&ingame_timestamp=600`

---

## 17. Frequently Asked Questions

**Source:** https://developers.pandascore.co/docs/frequently-asked-questions

### Q: Difference between `status` and `complete` at game level?
- `status` = current state (e.g. `finished`)
- `complete` = whether post-game stats are ready for consumption (only relevant when `detailed_stats=true`)
- Once `complete=true`, statistics should not change

### Q: How to tell if a match will have post-game stats?
- Check `detailed_stats` boolean at match level
- Filter: `GET /matches/upcoming?filter[detailed_stats]=true`
- Rare edge case: individual games may lack stats even if match-level says `true`

### Q: When are post-game stats available?
- Results: real-time
- Detailed post-game statistics: typically within **15 minutes** of game ending

### Q: Where to find tournament rosters?
- `GET /tournaments/{id_or_slug}/rosters`

### Q: What is a game advantage?
- First game automatically won by specified opponent (due to tournament format, e.g. lower bracket)
- `game_advantage` field contains opponent `id`, or `null` if none

---

## 18. Complete API Endpoint Catalog

### General Endpoints (All Videogames)

| Method | Endpoint | Description | Plan |
|--------|----------|-------------|------|
| GET | `/videogames` | List all videogames | Free |
| GET | `/videogames/{id}` | Get videogame by ID or slug | Free |
| GET | `/leagues` | List all leagues | Free |
| GET | `/leagues/{id}` | Get league by ID or slug | Free |
| GET | `/series` | List all series | Free |
| GET | `/series/{id}` | Get series by ID or slug | Free |
| GET | `/series/past` | List past series | Free |
| GET | `/series/running` | List ongoing series | Free |
| GET | `/series/upcoming` | List upcoming series | Free |
| GET | `/tournaments` | List all tournaments | Free |
| GET | `/tournaments/{id}` | Get tournament by ID or slug | Free |
| GET | `/tournaments/past` | List past tournaments | Free |
| GET | `/tournaments/running` | List ongoing tournaments | Free |
| GET | `/tournaments/upcoming` | List upcoming tournaments | Free |
| GET | `/tournaments/{id}/brackets` | Get tournament brackets | Free |
| GET | `/tournaments/{id}/standings` | Get tournament standings | Free |
| GET | `/tournaments/{id}/rosters` | Get tournament rosters | Free |
| GET | `/matches` | List all matches | Free |
| GET | `/matches/{id}` | Get match by ID or slug | Free |
| GET | `/matches/past` | List past matches | Free |
| GET | `/matches/running` | List running matches | Free |
| GET | `/matches/upcoming` | List upcoming matches | Free |
| GET | `/teams` | List all teams | Free |
| GET | `/teams/{id}` | Get team by ID or slug | Free |
| GET | `/players` | List all players | Free |
| GET | `/players/{id}` | Get player by ID or slug | Free |
| GET | `/lives` | List live matches with WebSocket URLs | Free |
| GET | `/additions` | List added resources (incidents) | Free |
| GET | `/changes` | List changed resources (incidents) | Free |
| GET | `/deletions` | List deleted resources (incidents) | Free |

### Game-Specific Endpoints

Each videogame has its own set of endpoints. The pattern is:

```
GET /{videogame_slug}/matches
GET /{videogame_slug}/matches/{id}
GET /{videogame_slug}/matches/past
GET /{videogame_slug}/matches/running
GET /{videogame_slug}/matches/upcoming
GET /{videogame_slug}/teams
GET /{videogame_slug}/teams/{id}
GET /{videogame_slug}/players
GET /{videogame_slug}/players/{id}
GET /{videogame_slug}/leagues
GET /{videogame_slug}/series
GET /{videogame_slug}/tournaments
```

### Complete Videogame Slugs

| Game | API Slug | Has Historical Data | Has Live Data |
|------|----------|-------------------|---------------|
| League of Legends | `lol` | Yes | Yes |
| Counter-Strike 2 | `csgo` | Yes | Yes |
| DotA 2 | `dota2` | Yes | Yes |
| Valorant | `valorant` | Yes | No |
| Overwatch | `ow` | No | No |
| Call of Duty MW | `codmw` | No | No |
| King of Glory | `arena-of-valor` | No | No |
| PUBG | `pubg` | No | No |
| Rainbow Six Siege | `r6siege` | No | No |
| Rocket League | `rl` | No | No |
| StarCraft 2 | `starcraft-2` | No | No |
| StarCraft: BW | `starcraft-brood-war` | No | No |
| EA Sports FC | `fifa` | No | No |
| Mobile Legends | `mlbb` | No | No |

### LoL-Specific Endpoints (Historical + Live)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/lol/champions` | List all LoL champions |
| GET | `/lol/champions/{id}` | Get champion by ID |
| GET | `/lol/items` | List all LoL items |
| GET | `/lol/masteries` | List all masteries |
| GET | `/lol/runes` | List all runes |
| GET | `/lol/spells` | List all summoner spells |
| GET | `/lol/games/{id}` | Get game details |
| GET | `/lol/games/{id}/frames` | Get game play-by-play frames |
| GET | `/lol/games/{id}/events` | Get game play-by-play events |

### CS-Specific Endpoints (Historical + Live)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/csgo/maps` | List all CS maps |
| GET | `/csgo/weapons` | List all CS weapons |
| GET | `/csgo/games/{id}` | Get game details |
| GET | `/csgo/games/{id}/rounds` | Get game play-by-play rounds |
| GET | `/csgo/games/{id}/events` | Get game play-by-play events |

### DotA 2-Specific Endpoints (Historical)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dota2/heroes` | List all DotA 2 heroes |
| GET | `/dota2/items` | List all DotA 2 items |
| GET | `/dota2/games/{id}` | Get game details |
| GET | `/dota2/games/{id}/frames` | Get game play-by-play frames |
| GET | `/dota2/games/{id}/events` | Get game play-by-play events |

### WebSocket Endpoints (Live API)

| URL Pattern | Feed Type | Plan |
|-------------|-----------|------|
| `wss://live.pandascore.co/matches/{matchId}` | Frames (every 2s) | Basic+ |
| `wss://live.pandascore.co/matches/{matchId}/events` | Events (as they happen) | Pro |

### Sandbox Replay Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | `https://live.pandascore.co/api/lol/replay` | Start LoL replay sandbox |
| POST | `https://live.pandascore.co/api/csgo/replay` | Start CS replay sandbox |

---

## 19. Quick Reference for Bot Integration

### Key Endpoints for an Esports Prediction Bot

```python
# === DISCOVERY ===

# List all videogames
GET /videogames

# List upcoming matches (all games)
GET /matches/upcoming

# List upcoming matches for specific videogame
GET /matches/upcoming?filter[videogame]=cs-go
GET /matches/upcoming?filter[videogame]=league-of-legends
GET /matches/upcoming?filter[videogame]=dota-2
GET /matches/upcoming?filter[videogame]=valorant

# List running matches
GET /matches/running

# List past matches
GET /matches/past

# Filter by tier
GET /tournaments/upcoming?filter[tier]=s,a

# === MATCH DETAILS ===

# Get specific match
GET /matches/{match_id_or_slug}

# Get match opponents (within match response)
# → response.opponents[] contains team/player info

# === TEAM/PLAYER STATS ===

# Get team info
GET /teams/{team_id_or_slug}

# Get player info
GET /players/{player_id_or_slug}

# === TOURNAMENT CONTEXT ===

# Tournament standings
GET /tournaments/{id}/standings

# Tournament brackets
GET /tournaments/{id}/brackets

# Tournament rosters
GET /tournaments/{id}/rosters

# === LIVE DATA ===

# List currently live WebSocket endpoints
GET /lives

# === TRACKING ===

# Poll for new/changed/deleted resources
GET /additions
GET /changes
GET /deletions
```

### Python Client Template

```python
import httpx
import asyncio
from typing import Optional

class PandaScoreClient:
    """Async PandaScore API client for bot integration."""
    
    BASE_URL = "https://api.pandascore.co"
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self.headers,
            timeout=30.0
        )
    
    async def get_upcoming_matches(
        self,
        videogame: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
        detailed_stats: Optional[bool] = None
    ) -> list:
        """Get upcoming matches, optionally filtered by videogame."""
        params = {
            "page[number]": page,
            "page[size]": per_page,
            "sort": "scheduled_at"
        }
        if videogame:
            params["filter[videogame]"] = videogame
        if detailed_stats is not None:
            params["filter[detailed_stats]"] = str(detailed_stats).lower()
        
        response = await self.client.get("/matches/upcoming", params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_match(self, match_id: int) -> dict:
        """Get specific match details."""
        response = await self.client.get(f"/matches/{match_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_running_matches(self) -> list:
        """Get currently running matches."""
        response = await self.client.get("/matches/running")
        response.raise_for_status()
        return response.json()
    
    async def get_past_matches(
        self,
        videogame: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> list:
        """Get past matches for historical analysis."""
        params = {
            "page[number]": page,
            "page[size]": per_page,
            "sort": "-scheduled_at"
        }
        if videogame:
            params["filter[videogame]"] = videogame
        
        response = await self.client.get("/matches/past", params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_tournament_standings(self, tournament_id: int) -> list:
        """Get tournament standings."""
        response = await self.client.get(
            f"/tournaments/{tournament_id}/standings"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_team(self, team_id: int) -> dict:
        """Get team details."""
        response = await self.client.get(f"/teams/{team_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_live_endpoints(self) -> list:
        """Get currently open WebSocket endpoints."""
        response = await self.client.get("/lives")
        response.raise_for_status()
        return response.json()
    
    async def get_incidents(
        self,
        incident_type: str = "additions",
        videogame: Optional[str] = None
    ) -> list:
        """Get additions/changes/deletions for tracking updates."""
        params = {}
        if videogame:
            params["videogame"] = videogame
        
        response = await self.client.get(f"/{incident_type}", params=params)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        await self.client.aclose()
```

### Videogame Slugs

| Game | Slug |
|------|------|
| League of Legends | `league-of-legends` |
| Counter-Strike 2 | `cs-go` (legacy slug still used) |
| DotA 2 | `dota-2` |
| Valorant | `valorant` |
| Overwatch | `ow` |
| Call of Duty | `codmw` |
| King of Glory | `arena-of-valor` |
| PUBG | `pubg` |
| Rainbow Six Siege | `r6siege` |
| Rocket League | `rl` |
| StarCraft 2 | `starcraft-2` |
| StarCraft: Brood War | `starcraft-brood-war` |
| FIFA | `fifa` |

### Important Notes for Bot Development

1. **Rate limiting:** Free tier = 1K req/hr. With polling every 60s for upcoming matches + team lookups, budget carefully.

2. **Match status polling:** Use `GET /matches/running` to detect live matches. Don't poll individual match IDs — use list endpoints.

3. **Historical data timing:** Post-game stats available ~15 minutes after game ends. Check `complete=true` before consuming.

4. **Roster accuracy:** Always use tournament rosters (`/tournaments/{id}/rosters`), not team-level players, for tournament participant info.

5. **Tier filtering:** For prediction quality, focus on S and A tier tournaments: `filter[tier]=s,a`

6. **Pagination:** Max 100 items per page. Use `X-Total` header to know total results. Follow `Link` header for navigation.

7. **Dates:** All in ISO-8601 UTC. Filter by date ignores time portion.

8. **Counter-Strike 2 migration:** CS2 still uses `cs-go` slug. See https://developers.pandascore.co/docs/counter-strike-2-migration

---

## Appendix: All Documentation Page Links

| Section | Page | URL |
|---------|------|-----|
| Get Started | Introduction | https://developers.pandascore.co/docs/introduction |
| Get Started | Fundamentals | https://developers.pandascore.co/docs/fundamentals |
| Get Started | Authentication | https://developers.pandascore.co/docs/authentication |
| Get Started | Rate Limits | https://developers.pandascore.co/docs/rate-and-connections-limits |
| Tutorials | First Request | https://developers.pandascore.co/docs/make-your-first-request |
| Tutorials | Discord Bot | https://developers.pandascore.co/docs/discord-score-bot |
| Upgrade | CS2 Migration | https://developers.pandascore.co/docs/counter-strike-2-migration |
| REST API | Formats | https://developers.pandascore.co/docs/formats |
| REST API | Tracking Changes | https://developers.pandascore.co/docs/tracking-changes |
| REST API | Tournaments | https://developers.pandascore.co/docs/tournaments-in-depth |
| REST API | Match Lifecycle | https://developers.pandascore.co/docs/matches-lifecycle |
| REST API | Match Formats | https://developers.pandascore.co/docs/match-formats |
| REST API | Filtering/Sorting | https://developers.pandascore.co/docs/filtering-and-sorting |
| REST API | Pagination | https://developers.pandascore.co/docs/pagination |
| REST API | Errors | https://developers.pandascore.co/docs/errors |
| REST API | Image Optimization | https://developers.pandascore.co/docs/image-optimization |
| REST API | Players' Age | https://developers.pandascore.co/docs/about-players-age |
| REST API | FAQ | https://developers.pandascore.co/docs/frequently-asked-questions |
| Live API | Overview | https://developers.pandascore.co/docs/websockets-overview |
| Live API | Data Samples | https://developers.pandascore.co/docs/data-samples |
| Live API | CS Data Sample | https://developers.pandascore.co/docs/data-sample-csgo |
| Live API | DotA 2 Data Sample | https://developers.pandascore.co/docs/data-sample-dota-2 |
| Live API | LoL Data Sample | https://developers.pandascore.co/docs/data-sample-league-of-legends |
| Live API | Events Recovery | https://developers.pandascore.co/docs/events-recovery |
| Live API | Disconnections | https://developers.pandascore.co/docs/disconnections |
| Live API | Sandbox | https://developers.pandascore.co/docs/sandbox-environment |
| Esports | Seasons & Circuits | https://developers.pandascore.co/docs/seasons-and-circuits |
| Esports | DotA 2 | https://developers.pandascore.co/docs/dota-2 |
| Esports | League of Legends | https://developers.pandascore.co/docs/league-of-legends |
| Esports | Overwatch | https://developers.pandascore.co/docs/overwatch |
| Reference | API Reference | https://developers.pandascore.co/reference |
| Recipes | Recipes | https://developers.pandascore.co/recipes |
| Changelog | Changelog | https://developers.pandascore.co/changelog |
