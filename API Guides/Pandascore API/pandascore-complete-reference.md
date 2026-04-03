# PandaScore — Complete API Reference

> **Generated:** 2026-04-03
> **Base API URL:** `https://api.pandascore.co`
> **WebSocket URL:** `wss://live.pandascore.co`
> **Auth:** Bearer token or `?token=` query parameter
> **Rate Limits:** 1k req/hr (free), 10k req/hr (paid plans)
> **Pagination:** Default 50/page, max 100, `page[number]` + `page[size]`

---

# ============================================
# PART 1: DOCUMENTATION (GUIDES & TUTORIALS)
# ============================================

# PandaScore API — Full Developer Documentation

> **Source:** https://developers.pandascore.co/docs/fundamentals
>
> Complete documentation from all 30 pages of the PandaScore developer docs.
> Base API URL: `https://api.pandascore.co`
> WebSocket URL: `wss://live.pandascore.co`
> Generated: 2026-04-03

---

# SECTION 1: GET STARTED

---

## Page 1: Introduction

Get started with PandaScore APIs for real-time esports statistics.

### Data coverage

PandaScore provides historical and real-time statistics for 13 major esports titles, including League of Legends, Counter-Strike, DotA2 and Valorant. The level of data coverage falls under three main categories: fixtures data, historical data and real-time data. Fixtures and historical data are available via the REST API. Real-time in-game statistics are accessible via the Live API.

#### Fixtures data

Fixtures data provides an overview of esports competitions, schedules and results for all available matches. Every match contains essential information such as the name, scheduled time, format (e.g. best of 5), team opponents and live streams for viewers to watch the games.

Fixtures updates for matches are provided in real-time, informing when a match begins or ends, the final match score and the winning team.

> The Fixtures Only plan is available to all users for free.

#### Historical data

Historical data displays in-depth game, team and player statistics once a game has ended, providing a detailed performance overview. Post-game statistics are available in the Historical plan for major esports titles: Counter-Strike, League of Legends, DotA2 and Valorant. The statistics available for each esports title will vary due to the differing nature of the gameplay. For example, in League of Legends, there are more than 50 unique data points related to player performance and over 20 unique data points related to team performance.

> Post-game data is available in the Historical plan and above.

#### Live data

Live data delivers in-game statistics to users in real-time. This type of data is accessible via WebSockets within the Live API. There are two live data feeds available: frames and events.

**Frames** — The frames feed presents an overview of the game-state, displaying information typically visible from an in-game HUD, e.g. current player K/D/A.

**Events** — The events feed provides a detailed timeline of key moments to give a better comprehension of pivotal events in-game, e.g. a player kill event.

> The events feed and a selection of statistics from the frames feed are exclusively available in the Pro Live plan.

### Common applications

- **Fantasy** — The large pool of esports statistics is well-suited to a fantasy platform.
- **Media and news platforms** — Keep users informed of roster changes, match outcomes, and player/team performance.
- **Data analysis** — The wealth of statistics available brings value to various analysis applications, such as scouting and performance tracking.
- **Prediction** — Historical team and player performances are ideal predictors of future head-to-head performance and match outcomes.
- **Live scores and stats applications** — Real-time match scores and in-game statistics.

### Resources

- **Documentation** — Guides for REST API and Live API.
- **API References** — Complete reference of all available endpoints at https://developers.pandascore.co/reference
- **Coverage** — Data points available for each plan at https://pandascore.co/stats#coverage
- **Support & Community** — Slack server for questions and support.

---

## Page 2: Fundamentals

Learn the fundamentals of the opinionated, flexible data structure PandaScore uses to map esports competitions across all video games.

### Leagues

Leagues are the top-level data structure used to represent a competition. Leagues are commonly named after the competition they represent. A league includes one or several children **Series**.

Examples: FIFA World Cup, The International

### Series

Series represent a single timely occurrence of their parent League. A series includes one or several children **Tournaments**.

Examples: FIFA World Cup — 2018, The International — 2018

### Tournaments

Tournaments represent a stage in their parent Series. A tournament includes one or several children **Matches** that contribute to a unique standing and possible winner.

Examples: FIFA World Cup — 2018 — Group C, The International — 2018 — Playoffs

### Matches

Matches represent a team-versus-team or player-versus-player confrontation between two participants of a parent Tournament. A match includes one or several children **Games**.

Matches is the most in-depth generic data structure. Despite many common properties, the data structure for Games (and below) is specific to each video game, and game IDs are unique for each videogame.

Examples:
- FIFA World Cup — 2018 — Group C — Denmark vs Australia (only 1 game)
- The International — 2018 — Playoffs — Final: OG vs PSG.LGD (5 games)

> In-game results should be retrieved via game-level endpoints (only available for video games supporting Historical Data).

### Hierarchy

```
League
  └── Series (yearly occurrence)
       └── Tournament (stage)
            └── Match (confrontation)
                 └── Game (individual game)
```

---

## Page 3: Authentication

Access to the APIs is restricted by token-based authentication. Your access token is available on your Dashboard at https://app.pandascore.co/dashboard.

> **Warning:** This token is private, do not use it in client-side applications.

### REST API

All requests against the REST API must be authenticated. PandaScore accepts two authentication methods:

**Bearer Token:**

```bash
curl --request GET \
     --url 'https://api.pandascore.co/videogames' \
     --header 'Accept: application/json' \
     --header 'Authorization: Bearer PLACEHOLDER_TOKEN_VALUE'
```

**URL Parameter:**

```bash
curl --request GET \
     --url 'https://api.pandascore.co/videogames?token=PLACEHOLDER_TOKEN_VALUE' \
     --header 'Accept: application/json'
```

### WebSockets API

The WebSockets API only accepts authentication via URL parameter:

```bash
wscat -c "wss://live.pandascore.co/matches/595466?token=PLACEHOLDER_TOKEN_VALUE"
```

---

## Page 4: Rate and connections limits

Usage of the PandaScore APIs is restricted depending on your plan.

### REST API

| Plan Name | Rate Limit |
| --- | --- |
| Schedules, Results & Context Data | 1k requests per hour |
| Historical & Post-Match Data | 10k requests per hour |
| Real-time Data (Basic) | 10k requests per hour |
| Real-time Data (Pro) | 10k requests per hour |

The number of remaining requests is available in the response `X-Rate-Limit-Remaining` HTTP header.

### WebSockets API

The WebSockets API is available to those on either the Real-time Data (Basic) or the Real-time Data (Pro) plans. Both allow a maximum of **3** simultaneous connections to a given match.

---

# SECTION 2: TUTORIALS

---

## Page 5: Make and interpret your first request

Send and interpret your first successful API request in less than a few minutes.

### Prerequisites

- Have your API token ready from your dashboard.
- Understand the structure of the eSports ecosystem (Fundamentals).
- Have a Postman account.

### Your first request

Navigate to the GET request in your Postman collection. The request is:

```
https://api.pandascore.co/matches/636351
```

The request pings the `/matches` endpoint and takes a unique identifier `636351` to specify a particular match.

### Understanding the result

The match contains information such as: match name, scheduled time, format (best of X), team opponents, live streams, match score, winner, league/series/tournament hierarchy, and more.

---

## Page 6: Discord match score-bot

Follow this guide to create a customised Discord score-bot.

### Functionality

The Discord bot uses PandaScore REST API to track match status changes by polling the `/matches` endpoint. Messages are sent in two instances:

- **Match start** — The match transitions from `not_started` to `running`. Message includes match name and stream URL.
- **Match end** — The match transitions from `running` to `finished`. Message includes match name, final score, and winning team.

### Pre-requisites

1. Create a new Discord application at https://discord.com/developers/applications
2. Copy the Bot Token (used as `BOT_TOKEN`)
3. Enable message content intent
4. Set bot permissions to "send messages"
5. Add bot to your Discord server

### Required constants

- `DISCORD_CHANNEL_ID` — Discord channel ID
- `BOT_TOKEN` — Discord bot token
- `PANDASCORE_TOKEN` — Your PandaScore API token

### Required packages

```
discord.py>=2.1.0
requests==2.31.0
```

### Customisation — Filter by interest

- Participating teams: `/matches?filter[opponent_id]={opponent_id_or_slug}`
- Videogame: `/matches?filter[videogame]={videogame_id_or_slug}`
- Parent tournament: `/matches?filter[tournament_id]={tournament_id}`
- Parent series: `/matches?filter[serie_id]={serie_id}`
- Parent league: `/matches?filter[league_id]={league_id}`

Filters accept comma-separated values and can be combined.

### Customisation — Tailored notifications

Available match payload fields: `opponents`, `match_type`, `number_of_games`, `league.name`, `serie.full_name`, `tournament.name`, `videogame.name`, `streams_list`, `results`, `winner.name`.

Discord spoiler tags: `||text||`

---

# SECTION 3: UPGRADE GUIDES

---

## Page 7: Counter-Strike 2 migration

### CS2 Game Changes

CS2 uses **MR12 format** instead of MR15. Teams spend max 12 rounds per side. First to **13** rounds wins (vs. 16 in CS:GO). Overtime occurs at 12-12 tie.

### CS2 in the PandaScore API

CS2 data belongs to videogame `counterstrike` (id: 3). Two videogame titles:
- `Counter-Strike: Global Offensive`
- `Counter-Strike 2`

The `videogame_title` is visible at the series level.

### Filtering by videogame_title

Filter: `?filter[videogame_title]=` for CS matches, tournaments and series.
Stats filter: `?videogame_title=`

- **CS:GO** — slug: `cs-go`, id: `12`
- **CS2** — slug: `cs-2`, id: `13`

### Endpoints with this filter

- `/csgo/matches`, `/csgo/matches/past`, `/csgo/matches/running`, `/csgo/matches/upcoming`
- `/csgo/players/{player_id_or_slug}/stats`, `/csgo/teams/{team_id_or_slug}/stats`
- `/csgo/series`, `/csgo/series/past`, `/csgo/series/running`, `/csgo/series/upcoming`
- `/csgo/tournaments`, `/csgo/tournaments/past`, `/csgo/tournaments/running`, `/csgo/tournaments/upcoming`

---

# SECTION 4: REST API

---

## Page 8: Formats

The REST API works over the HTTPS protocol, accessed from `api.pandascore.co`.

- Data is sent and received as JSON
- Blank fields are included with `null` values (not omitted)
- All dates are returned in ISO-8601 format, UTC time

---

## Page 9: Tracking changes

PandaScore allows tracking changes on Leagues, Series, Tournaments, Matches, Teams and Players using incidents.

### Incidents API endpoints

- `GET /additions` — track resources creation
- `GET /changes` — track resources modification
- `GET /deletions` — track resources deletion

### Polling incidents

Implement polling logic around the incidents endpoints to keep data up-to-date.

### Common use cases

**Tracking new CS:GO competitions:**
```
/additions?type=tournament,serie,league&videogame=cs-go
```

**Tracking LoL roster changes:**
```
/changes?type=team&videogame=league-of-legends
```

**Tracking deletions:**
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
  }
]
```

---

## Page 10: Tournaments in-depth

### Tournament participants

Retrieve via:
- `GET /tournaments/{id}` — `expected_roster` array
- `GET /tournaments/{id}/rosters` — `rosters` array

> Team-level players are NOT recommended to determine tournament participants. Use rosters instead.

### Tournament brackets

`has_bracket` field indicates whether tournament has a bracket. Each match has a `previous_matches` array with `match_id` and `type` (winner/loser).

### Tournament standings

`GET /tournaments/{id}/standings` — participant performance and ranking.

### Tournament tiers

5 tiers: **S > A > B > C > D**

- **S Tier** — Most prestigious (The International, Worlds, Majors). Prize pools $250k–$1M+.
- **A Tier** — High level (DPC Division 1, LPL/LCK/LCS/LEC, ESL Pro League).
- **B Tier** — Middle range (TI Qualifiers, Riot regional leagues).
- **C Tier** — Lower profile, independent organizers. Prize pools up to $75k.
- **D Tier** — Very low profile. Prize pools rarely above $10k.

Filter by tier: `?filter[tier]=s` or `?filter[tier]=s,a`

---

## Page 11: Matches lifecycle

Match statuses as a finite state machine:

### Not started
- `status`: `not_started`
- `scheduled_at`: official playing time
- `begin_at`: same as `scheduled_at`
- `end_at`: `null`
- WebSocket opens 15 minutes before scheduled time

### Rescheduled
- `rescheduled`: `true`
- `scheduled_at`: new time
- `original_scheduled_at`: initial time

### Running
- `status`: `running`
- `begin_at`: actual beginning time

### Finished
- `status`: `finished`
- `end_at`: match finish time
- `winner_id`: winning team/player id
- `complete`: `true` when all post-game stats are available

### Canceled
Without winner:
- `status`: `canceled`, `forfeit`: `false`

Forfeit:
- `status`: `canceled`, `forfeit`: `true`, `winner_id` is set

### Postponed
- `status`: `postponed`
- `scheduled_at`: not updated until new date is known

---

## Page 12: Match formats

Field: `match_type`

### Best of
- `match_type`: `best_of`
- `number_of_games`: maximum number of games
- First team to win more than half wins
- Unplayed games not returned in API

### First to
- `match_type`: `first_to`
- `number_of_games`: minimum number of games to win
- Match continues until a team wins that many games

### Red Bull Home Grounds
- `match_type`: `red_bull_home_ground`
- Best of 5, but first 2 games are "Home Ground" picks
- If one team wins both Home Ground games, they win automatically
- Otherwise standard best of 5 rules apply
- Only possible in Valorant

---

## Page 13: Filtering and sorting

### Filter (strict equality)
```
/lol/champions?filter[name]=Brand
/lol/champions?filter[name]=Brand,Twitch
```
> Dates should be in UTC. Time portion is ignored for date filters.

### Search (substring match)
```
/lol/champions?search[name]=twi
```
> Only works with string values.

### Range (numeric interval)
```
/lol/champions?range[hp]=500,1000
```
> Only works with numeric values.

### Sort
```
/lol/champions?sort=attackdamage,-name
```
- Ascending by default
- Prefix `-` for descending
- Comma-separated for multiple fields
- `null` values: first in ascending, last in descending

---

## Page 14: Pagination

Default: 50 items per page, first page = 1.

### Page number
```
/lol/champions?page[number]=2
```

### Page size
```
/lol/champions?page[size]=10
```
> Maximum 100 items per page.

### Navigating pages

`Link` header contains navigation:
- `first`, `previous`, `next`, `last`

### Response headers
- `X-Page` — current page number
- `X-Per-Page` — current page length
- `X-Total` — total count of items

---

## Page 15: Errors

### Client errors (4xx)

| HTTP Status | Definition |
| --- | --- |
| 400 — Bad Request | Malformed request / syntax error |
| 401 — Unauthorized | Missing token |
| 403 — Forbidden | URL not available with your plan |
| 404 — Not Found | Resource does not exist |
| 429 — Too Many Requests | Rate limit reached |

Response format:
```json
{
  "error": "Not Found",
  "message": "The resource does not exist."
}
```

### Server errors (5xx)

Issues on PandaScore's servers. Retry the request. Check status at https://status.pandascore.co/

---

## Page 16: Image optimization

Three resolutions served by CDN:
- **Default** — original image
- **Normalized** — 800x800px (prefix `normal_`)
- **Thumbnail** — 200x200px (prefix `thumb_`)

Example for team ID `125063`:
- Default: `https://cdn.pandascore.co/images/team/image/125063/sengoku-gaming-gnat0l9c.png`
- Normalized: `https://cdn.pandascore.co/images/team/image/125063/normal_sengoku-gaming-gnat0l9c.png`
- Thumbnail: `https://cdn.pandascore.co/images/team/image/125063/thumb_sengoku-gaming-gnat0l9c.png`

---

## Page 17: About players' age

Player object has `age` (nullable integer) and `birthday` (nullable string, `YYYY-MM-DD`).

When `birthday` is set, `age` is computed from it.

When `birthday` is `null`, `age` may still be manually set by PandaScore operations team. The age might be outdated but **never greater** than actual age.

---

## Page 18: Frequently asked questions

**Q: Difference between `status` and `complete` at game level?**
A: `status` shows current state (e.g. `finished`). `complete` indicates whether post-game stats are ready for consumption.

**Q: How to tell if a match will have post-game statistics?**
A: Boolean `detailed_stats` field at match level. Filter: `?filter[detailed_stats]=true`.

**Q: When will post-game statistics be available?**
A: Typically within 15 minutes of game ending.

**Q: Where to find tournament rosters?**
A: `/tournaments/{tournament_id_or_slug}/rosters`

**Q: What is game advantage?**
A: `game_advantage` contains opponent `id` if first game is automatically won. Otherwise `null`.

---

# SECTION 5: LIVE API

---

## Page 19: Overview (WebSockets)

### Connecting to WebSockets

**1. Retrieve matches with real-time data:**

Tournament `live_supported` must be `true`. WebSocket opens 15 minutes before scheduled time.

Use `GET /lives` to get currently open WebSockets:

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
  ]
}
```

**2. Connect:**

```bash
wscat -c 'wss://live.pandascore.co/matches/595477?token=YOUR_TOKEN'
```

```javascript
const socket = new WebSocket('wss://live.pandascore.co/matches/8191?token=YOUR_TOKEN')
socket.onmessage = function (event) {
    console.log(JSON.parse(event.data))
}
```

Hello event after connection:
```json
{"type":"hello","payload":{}}
```

Max 3 simultaneous connections per match per endpoint.

### Frames & Events

- **Frames** — snapshot of all game data points, every 2 seconds
- **Events** — timeline of in-game events, sent as they occur (Pro Live Plan only)

---

## Page 20: Data samples

Every sub-page provides examples of:
- a Frame (snapshot of all data points at a given time)
- an Event (description of an action at a given time)

---

## Page 21: Data sample — Counter-Strike

### Frames

**Game overview:** `map` (id, name), `round`, `current_timestamp`, `bomb_planted`, `paused`, `finished`, `winner_id`

**Team statistics:** `counter_terrorists` and `terrorists` objects with `id`, `name`, `round_score`, `score`

**Player statistics:** `id`, `name`, `deaths`, `kills`, `economy`, `primary_weapon` (Pro only), `secondary_weapon` (Pro only), `hp` (Pro only), `is_alive`

### Events

Types:
- `kill` — killer info (id, name, team_id, weapon), killed info, round_number, elapsed_round_time
- `round_start` — score, round_number, round_score per side
- `round_end` — outcome (e.g. "eliminated"), winner team, round_number, round_score

> Events are only available on the Pro Live Plan.

---

## Page 22: Data sample — DotA 2

### Frames

**Game overview:** game/match/tournament ids, `current_timestamp`, `daytime`, `finished`, `winner_id`

**Team statistics:** `dire` and `radiant` objects with `id`, `name`, `score` (kills), `towers` (destroyed/remaining), `barracks` (destroyed/remaining)

**Player statistics:** `id`, `name`, `hero` (id, name), `level`, `alive`, `kills`, `deaths`, `assists`, `last_hits`

---

## Page 23: Data sample — League of Legends

### Frames

**Game overview:** game/match/tournament ids, `current_timestamp`, `paused` (Pro only), `finished`, `winner_id`

**Team statistics:** `red` and `blue` objects with `id`, `name`, `acronym`, `towers`, `gold`, `kills`, `drakes`, `nashors`, `herald` (Pro only), `inhibitors`, `score`, `voidgrubs` (Pro only)

**Player statistics:** Keyed by position (`top`, `jun`, `mid`, `adc`, `sup`). Fields: `id`, `name`, `champion` (id, name, image_url), `cs`, `level`, `kills`, `deaths`, `assists`, `summoner_spells`, `items` (Pro only), `hp` (Pro only)

### Events

Type: always `kill_feed`. Fields: `ts`, `ingame_timestamp`, `payload` with `type`, `assists`, `killer`, `killed`.

KillEntity types: `baron_nashor`, `drake`, `inhibitor`, `minion`, `other`, `player`, `rift_herald`, `tower`

> Events are only available on the Pro Live Plan.

---

## Page 24: Events recovery

When connected to `/matches/<matchID>/events`, send a Recover message to get all previous events:

```json
{
  "type": "recover",
  "payload": {
    "game_id": <gameID>
  }
}
```

Node.js example:
```javascript
const socket = new WebSocket('wss://live.pandascore.co/matches/548763/events?token=YOUR_TOKEN')
socket.onmessage = function (event) {
    console.log(JSON.parse(event.data))
}
socket.onopen = function (event) {
    socket.send(JSON.stringify({"type":"recover","payload":{"game_id":211051}}))
}
```

> Currently only available for League of Legends and Counter-Strike.

---

## Page 25: Disconnections

### Status codes

| Status Code | Definition |
| --- | --- |
| 1000 | Match finished (normal closure) |
| 4001 — Unauthorized | Missing token |
| 4003 — Forbidden | Not available with your plan |
| 4029 — Too Many Connections | Max 3 simultaneous connections reached |

Server errors (1xxx, not 1000): retry connection. Use Events Recovery for missed events.

---

## Page 26: Sandbox environment

Simulate game conditions for Counter-Strike and League of Legends for integration testing.

### League of Legends

```
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

```
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

- `playback_speed` — enum: `1` (default), `1.5`, `2`
- `ingame_timestamp` — start time in seconds (LoL only, default: 0)
- `round_number` — start round (CS only, default: 1)

---

# SECTION 6: ESPORTS

---

## Page 27: Seasons and circuits

### Dota 2
Organized around the Dota Pro Circuit. Regional leagues (NA, SA, WEU, EEU, CN, SEA) qualify for Majors. Major points qualify for The International.

### Counter-Strike
Organized around Major Championships. Independent tournament organizers run events throughout the year. Similar to Tennis structure.

### League of Legends
Regional leagues (EU, NA, CN, KR, etc.). Two splits: Spring and Summer. Spring winners go to international events. Summer Playoffs qualify for Worlds.

### Rocket League
Regional leagues (EU, NA, SA, OCE). Three splits: Fall, Winter, Spring. Split winners qualify for international Majors. Season concludes with World Championship.

### Overwatch
Overwatch League — NBA-like model with two conferences. Home and away matches. Tier 2: Overwatch Contenders.

---

## Page 28: Dota 2

5v5 MOBA. Heroes endpoint: `GET /dota2/heroes`

### Roles (1-to-5 system)

- **1** — hard carry: highest priority for XP and gold
- **2** — carry: second priority
- **3** — damage dealer, less XP/gold dependent
- **4** — secondary support
- **5** — support: buys support items

Mixed roles: e.g. `1/2` means both positions 1 and 2.

---

## Page 29: League of Legends

5v5 MOBA. Champions: `GET /lol/champions`. Items: `GET /lol/items`.

### Patches & Versioning

All LoL static resources are versioned. `videogame_versions` array shows which patches a champion version applies to.

Get champion for specific patch:
```
GET /lol/versions/9.21.1/champions?filter[name]=Sejuani
```

Compare `id` and fields across versions to see what changed between patches.

---

## Page 30: Overwatch

Class-based FPS. Heroes: `GET /ow/heroes`. Maps: `GET /ow/maps`.

### Game modes

Control, Assault, Escort, Hybrid (Assault/Escort). Each game typically on a different mode.

### Match types

- **Best of X** — standard, win more than half
- **First to X** — accounts for draws on Assault/Escort/Hybrid maps
  - `number_of_games` = minimum games needed to win
  - Actual games played = size of `games` array

### Overwatch League format (pre-2020)

Match type `ow_best_of` — required at least 4 games, 5th if tiebreaker needed. Even after 3-0, a 4th game was played.

---

# END OF PART 1 (DOCUMENTATION)

---
---
---

# ============================================
# PART 2: API REFERENCE (ALL ENDPOINTS)
# ============================================

# Common Parameters (applies to most endpoints)

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer/object | `page=2` or `page[size]=30&page[number]=2`. Default: 1 |
| `per_page` | integer | Equivalent to `page[size]`. Default: 50, max: 100 |
| `games_count` | integer | Number of recent games for statistics |

# Common Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request |
| 401 | Unauthorized (missing token) |
| 403 | Forbidden (plan restriction) |
| 404 | Not Found |
| 422 | Unprocessable Entity |
| 429 | Rate limit exceeded |

---

## CATEGORY: Incidents

### GET /additions
**Description:** Get the latest additions (newly created resources).
**URL:** `https://api.pandascore.co/additions`
**Plan:** All customers

**Query Parameters:** Standard pagination + `games_count`

**Response Schema:**
```json
[{
  "change_type": "creation",          // enum: creation, deletion, update
  "id": 12345,                        // Incident ID (resource ID)
  "modified_at": "2020-01-06T13:54:26Z",
  "object": { ... },                  // Full resource (League/Serie/Tournament/Match)
  "type": "match"                     // match, league, serie, tournament
}]
```

**cURL:**
```bash
curl -X GET "https://api.pandascore.co/additions?page[size]=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /changes
**Description:** Get the latest updates. Shows only the latest change per object (no history).
**URL:** `https://api.pandascore.co/changes`
**Plan:** All customers

**Query Parameters:** Standard pagination + `games_count`

**Response Schema:** Same as `/additions` — array of incident objects with `change_type`, `id`, `modified_at`, `object`, `type`.

**cURL:**
```bash
curl -X GET "https://api.pandascore.co/changes?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /deletions
**Description:** Get the latest deleted documents.
**URL:** `https://api.pandascore.co/deletions`
**Plan:** All customers

**Query Parameters:** Standard pagination + `games_count`

**Response Schema:** Same incident structure. `object` contains `deleted_at`, `reason`, `videogame_id`.

**cURL:**
```bash
curl -X GET "https://api.pandascore.co/deletions?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /incidents
**Description:** Get all latest incidents (additions + changes + deletions combined).
**URL:** `https://api.pandascore.co/incidents`
**Plan:** All customers

**Query Parameters:** Standard pagination + `games_count`

**Response Schema:** Same incident structure.

**cURL:**
```bash
curl -X GET "https://api.pandascore.co/incidents?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## CATEGORY: All Video Games — Videogames

### GET /videogames
**Description:** List all supported video games.
**URL:** `https://api.pandascore.co/videogames`
**Plan:** All customers

**Response Schema:**
```json
[{
  "id": 1,
  "name": "LoL",
  "slug": "league-of-legends",
  "current_version": "14.1.1"   // nullable
}]
```

**cURL:**
```bash
curl -X GET "https://api.pandascore.co/videogames" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /videogames/{videogame_id_or_slug}
**Description:** Get a single video game by ID or slug.
**URL:** `https://api.pandascore.co/videogames/{videogame_id_or_slug}`
**Path Params:** `videogame_id_or_slug` (required)

---

### GET /videogames/{videogame_id_or_slug}/leagues
**Description:** List leagues for a video game.

### GET /videogames/{videogame_id_or_slug}/series
**Description:** List series for a video game.

### GET /videogames/{videogame_id_or_slug}/titles
**Description:** List videogame titles (e.g. CS:GO vs CS2).

### GET /videogames/{videogame_id_or_slug}/tournaments
**Description:** Get tournaments for a video game.

### GET /videogames/{videogame_id_or_slug}/versions
**Description:** List videogame versions/patches.

---

## CATEGORY: All Video Games — Lives

### GET /lives
**Description:** List currently live matches with WebSocket support.
**URL:** `https://api.pandascore.co/lives`
**Plan:** All customers

**Response Schema:** Array of match objects with full match data + `live` object containing `supported`, `opens_at`, `url`.

**cURL:**
```bash
curl -X GET "https://api.pandascore.co/lives" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## CATEGORY: All Video Games — Leagues

### GET /leagues
**Description:** List all leagues across all video games.
**URL:** `https://api.pandascore.co/leagues`
**Plan:** All customers

**Response Schema:**
```json
[{
  "id": 1,
  "name": "LEC",
  "slug": "league-of-legends-emea-lec",
  "image_url": "https://cdn.pandascore.co/...",  // nullable
  "url": "https://...",                            // nullable
  "modified_at": "2024-01-15T10:30:00Z",
  "videogame": { "id": 1, "name": "LoL", "slug": "league-of-legends" },
  "series": [{ ... }]                             // array of BaseSerie
}]
```

**cURL:**
```bash
curl -X GET "https://api.pandascore.co/leagues?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /leagues/{league_id_or_slug}
**Description:** Get a single league by ID or slug.
**Path Params:** `league_id_or_slug` (required)
**Response:** Single league object with `series` array, `videogame`.

---

### GET /leagues/{league_id_or_slug}/matches
**Description:** Get matches for a league.

### GET /leagues/{league_id_or_slug}/matches/past
**Description:** Get past matches for a league.

### GET /leagues/{league_id_or_slug}/matches/running
**Description:** Get running matches for a league.

### GET /leagues/{league_id_or_slug}/matches/upcoming
**Description:** Get upcoming matches for a league.

### GET /leagues/{league_id_or_slug}/series
**Description:** List series of a league.

### GET /leagues/{league_id_or_slug}/tournaments
**Description:** Get tournaments for a league.

---

## CATEGORY: All Video Games — Matches

### GET /matches
**Description:** List all matches across all video games.
**URL:** `https://api.pandascore.co/matches`
**Plan:** All customers

**Response Schema (Match Object):**
```json
{
  "id": 636351,
  "name": "Team A vs Team B",
  "slug": "team-a-vs-team-b-2024-01-15",
  "begin_at": "2024-01-15T18:00:00Z",       // nullable
  "end_at": "2024-01-15T20:30:00Z",         // nullable
  "scheduled_at": "2024-01-15T18:00:00Z",   // nullable
  "original_scheduled_at": "2024-01-15T18:00:00Z",
  "rescheduled": false,
  "status": "finished",                      // not_started, running, finished, postponed, canceled
  "match_type": "best_of",                  // best_of, first_to, all_games_played, custom, ow_best_of, red_bull_home_ground
  "number_of_games": 3,
  "detailed_stats": true,
  "draw": false,
  "forfeit": false,
  "game_advantage": null,                   // opponent ID or null
  "league_id": 1,
  "serie_id": 10,
  "tournament_id": 100,
  "modified_at": "2024-01-15T21:00:00Z",
  "winner_id": 5,                           // nullable
  "winner_type": "Team",                    // Team or Player, nullable
  "opponents": [{
    "opponent": { "id": 5, "name": "...", "acronym": "...", "image_url": "..." },
    "type": "Team"
  }],
  "results": [{ "score": 2, "team_id": 5 }, { "score": 1, "team_id": 6 }],
  "games": [{ "id": 1, "position": 1, "status": "finished", "winner": {...}, "length": 2400 }],
  "league": { "id": 1, "name": "...", "slug": "...", "image_url": "..." },
  "serie": { "id": 10, "name": "...", "full_name": "...", "year": 2024 },
  "tournament": { "id": 100, "name": "...", "slug": "..." },
  "videogame": { "id": 1, "name": "LoL", "slug": "league-of-legends" },
  "videogame_title": { "id": 1, "name": "...", "slug": "..." },     // nullable
  "streams_list": [{ "raw_url": "...", "embed_url": "...", "language": "en", "official": true, "main": true }],
  "live": { "supported": true, "opens_at": "...", "url": "..." },
  "map_picks": null                          // Valorant only
}
```

**cURL:**
```bash
curl -X GET "https://api.pandascore.co/matches?per_page=50&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /matches/past
**Description:** Get past matches.

### GET /matches/running
**Description:** Get running matches.

### GET /matches/upcoming
**Description:** Get upcoming matches.

### GET /matches/{match_id_or_slug}
**Description:** Get a single match by ID or slug.
**Path Params:** `match_id_or_slug` (required)

### GET /matches/{match_id_or_slug}/opponents
**Description:** Get opponents for a match.

---

## CATEGORY: All Video Games — Players

### GET /players
**Description:** List all players across all video games.
**URL:** `https://api.pandascore.co/players`
**Plan:** All customers

**Response Schema (Player Object):**
```json
{
  "id": 123,
  "name": "Faker",                    // professional alias
  "first_name": "Sang-hyeok",        // nullable
  "last_name": "Lee",                // nullable
  "slug": "faker",
  "active": true,
  "age": 28,                          // nullable (Historical plan)
  "birthday": "1996-05-07",          // nullable (Historical plan)
  "nationality": "KR",               // ISO 3166-1 alpha-2, nullable
  "image_url": "https://...",        // nullable
  "role": "mid",                     // game-specific, nullable
  "modified_at": "2024-01-15T10:30:00Z"
}
```

**cURL:**
```bash
curl -X GET "https://api.pandascore.co/players?per_page=50&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /players/{player_id_or_slug}
**Description:** Get a single player by ID or slug.
**Path Params:** `player_id_or_slug` (required)

### GET /players/{player_id_or_slug}/leagues
### GET /players/{player_id_or_slug}/matches
### GET /players/{player_id_or_slug}/series
### GET /players/{player_id_or_slug}/tournaments

---

## CATEGORY: All Video Games — Series

### GET /series
**Description:** List all series.
**URL:** `https://api.pandascore.co/series`
**Plan:** All customers

**Response Schema (Serie Object):**
```json
{
  "id": 10,
  "name": "Spring",                  // nullable
  "full_name": "LEC Spring 2024",
  "slug": "lec-spring-2024",
  "season": "Spring",               // nullable
  "year": 2024,                     // nullable, min: 2012
  "begin_at": "2024-01-15T00:00:00Z",  // nullable
  "end_at": "2024-03-30T00:00:00Z",    // nullable
  "modified_at": "2024-01-15T10:30:00Z",
  "league_id": 1,
  "league": { "id": 1, "name": "LEC", ... },
  "tournaments": [{ ... }],
  "videogame": { "id": 1, "name": "LoL", ... },
  "videogame_title": null,
  "winner_id": null,                // nullable
  "winner_type": "Team"             // Team or Player
}
```

---

### GET /series/past
### GET /series/running
### GET /series/upcoming

### GET /series/{serie_id_or_slug}
**Description:** Get a single serie by ID or slug.

### GET /series/{serie_id_or_slug}/matches
### GET /series/{serie_id_or_slug}/matches/past
### GET /series/{serie_id_or_slug}/matches/running
### GET /series/{serie_id_or_slug}/matches/upcoming
### GET /series/{serie_id_or_slug}/tournaments

---

## CATEGORY: All Video Games — Teams

### GET /teams
**Description:** List all teams.
**URL:** `https://api.pandascore.co/teams`
**Plan:** All customers

**Response Schema (Team Object):**
```json
{
  "id": 5,
  "name": "T1",
  "acronym": "T1",                   // nullable
  "slug": "t1",
  "image_url": "https://cdn.pandascore.co/...",
  "dark_mode_image_url": "https://...",  // nullable
  "location": "KR",                  // nullable
  "modified_at": "2024-01-15T10:30:00Z"
}
```

---

### GET /teams/{team_id_or_slug}
**Description:** Get a single team by ID or slug.

### GET /teams/{team_id_or_slug}/leagues
### GET /teams/{team_id_or_slug}/matches
### GET /teams/{team_id_or_slug}/series
### GET /teams/{team_id_or_slug}/tournaments

---

## CATEGORY: All Video Games — Tournaments

### GET /tournaments
**Description:** List all tournaments.
**URL:** `https://api.pandascore.co/tournaments`
**Plan:** All customers

**Response Schema (Tournament Object):**
```json
{
  "id": 100,
  "name": "Playoffs",
  "slug": "lec-spring-2024-playoffs",
  "begin_at": "2024-03-01T00:00:00Z",    // nullable
  "end_at": "2024-03-30T00:00:00Z",      // nullable
  "modified_at": "2024-01-15T10:30:00Z",
  "country": "DE",                        // ISO 3166-1 alpha-2, nullable
  "region": "WEU",                        // AF, ASIA, EEU, ME, NA, OCE, SA, WEU; nullable
  "type": "offline",                      // offline, online, online/offline; nullable
  "prizepool": "$200,000",               // nullable
  "tier": "s",                           // s, a, b, c, d, unranked; nullable
  "detailed_stats": true,
  "has_bracket": true,
  "live_supported": true,
  "league_id": 1,
  "serie_id": 10,
  "league": { ... },
  "serie": { ... },
  "videogame": { ... },
  "videogame_title": null,
  "teams": [{ ... }],
  "matches": [{ ... }],
  "expected_roster": [{ "team": {...}, "players": [{...}] }],
  "winner_id": null,
  "winner_type": "Team"
}
```

---

### GET /tournaments/past
### GET /tournaments/running
### GET /tournaments/upcoming

### GET /tournaments/{tournament_id_or_slug}
**Description:** Get a single tournament by ID or slug.

### GET /tournaments/{tournament_id_or_slug}/brackets
**Description:** Get bracket data for a tournament. Returns matches with `previous_matches` array.
**Plan:** All customers

### GET /tournaments/{tournament_id_or_slug}/matches
**Description:** Get all matches for a tournament.

### GET /tournaments/{tournament_id_or_slug}/rosters
**Description:** List participants (team + players) for a tournament.
**Response:** Array of `{ team: BaseTeam, players: [BasePlayer] }`

### GET /tournaments/{tournament_id_or_slug}/standings
**Description:** Get current standings for a tournament.

### GET /tournaments/{tournament_id_or_slug}/teams
**Description:** Get teams for a tournament.

---

## CATEGORY: Counter-Strike

### GET /csgo/games/{csgo_game_id}
**Description:** Get a single Counter-Strike game by ID.
**URL:** `https://api.pandascore.co/csgo/games/{csgo_game_id}`
**Plan:** Historical or Real-time

**Path Params:** `csgo_game_id` (integer, required)

**Response Schema:**
```json
{
  "id": 4505,
  "begin_at": "2024-01-15T18:00:00Z",
  "end_at": "2024-01-15T19:30:00Z",
  "finished": true,
  "complete": true,
  "forfeit": false,
  "length": 5400,                    // seconds, nullable
  "detailed_stats": true,
  "status": "finished",             // finished, not_played, not_started, running
  "position": 1,                    // game position in match
  "map": { "id": 1, "name": "Mirage", "slug": "mirage", "image_url": "..." },
  "match": { ... },                 // full match object
  "winner": { "id": 5, "type": "Team" },
  "winner_type": "Team",

  // Player stats (if detailed_stats: true):
  "players": [{
    "player": { "id": 1, "name": "s1mple", "role": "...", "nationality": "UA" },
    "team": { ... },
    "opponent": { ... },
    "game_id": 4505,
    "kills": 25,
    "deaths": 15,
    "assists": 4,
    "headshots": 12,
    "adr": 85.3,                    // average damage per round
    "kast": 72.5,                   // Kill/Assist/Survival/Trade %
    "rating": 1.25,
    "k_d_diff": 10,
    "first_kills_diff": 3,
    "flash_assists": 2
  }],

  // Rounds (if detailed_stats: true):
  "rounds": [{
    "number": 1,
    "outcome": "eliminated",        // defused, eliminated, exploded, planted_eliminated, timeout
    "map": { ... },
    "counter_terrorists": {
      "team_id": 5, "team_name": "...", "round_score": 1,
      "players": [{
        "id": 1, "name": "...", "kills": 2, "assists": 0, "deaths": 0,
        "is_alive": true, "remaining_hp": 87,
        "freeze_time_economy": {
          "economy": 4750,
          "armor": "kevlar_and_helmet",   // kevlar, kevlar_and_helmet, null
          "defuse_kit": true,
          "primary_weapon": { "id": 1, "name": "AK-47", "slug": "ak-47", "image_url": "..." },
          "secondary_weapon": { ... },
          "utilities": [{ "id": 1, "name": "Flashbang", "count": 2 }]
        },
        "round_start_economy": { ... }
      }]
    },
    "terrorists": { ... },
    "winner_team": { "side": "counter_terrorists", "team_id": 5, "team_name": "..." }
  }]
}
```

---

### GET /csgo/games/{csgo_game_id}/events
**Description:** List play-by-play events for a CS game.
**Plan:** Pro Real-time only
**Extra Query Params:** `from`, `to`, `videogame_title`

---

### GET /csgo/games/{csgo_game_id}/rounds
**Description:** List rounds in a Counter-Strike game with detailed economy/weapon data.
**Plan:** Real-time
**Extra Query Params:** `from`, `to`, `videogame_title`, `games_count`
**Response:** Array of `CSGOFullRound` objects (see game schema above).

---

### GET /csgo/matches/{match_id_or_slug}/games
**Description:** List games for a given CS match.

---

### GET /csgo/leagues
**Description:** Get Counter-Strike leagues.
**Extra Query Params:** `videogame_title`

### GET /csgo/maps
**Description:** List Counter-Strike maps.
**Response:** `[{ "id": 1, "name": "Mirage", "slug": "mirage", "image_url": "..." }]`
**Extra Query Params:** `videogame_title`

### GET /csgo/maps/{csgo_map_id}
**Description:** Get a single map by ID.

---

### GET /csgo/matches
### GET /csgo/matches/past
### GET /csgo/matches/running
### GET /csgo/matches/upcoming
### GET /csgo/matches/{match_id_or_slug}

---

### GET /csgo/matches/{match_id_or_slug}/players/stats
**Description:** Get stats for all CS players on a match.
**Plan:** Historical or Real-time
**Extra Query Params:** `from`, `to`, `videogame_title`, `games_count`

**Response Schema (CS Player Stats):**
```json
[{
  "player": { "id": 1, "name": "...", "nationality": "...", ... },
  "team": { ... },
  "opponent": { ... },
  "game_id": 4505,
  "kills": 25,
  "deaths": 15,
  "assists": 4,
  "headshots": 12,
  "adr": 85.3,
  "kast": 72.5,
  "rating": 1.25,
  "k_d_diff": 10,
  "first_kills_diff": 3,
  "flash_assists": 2
}]
```

---

### GET /csgo/matches/{match_id_or_slug}/players/{player_id_or_slug}/stats
**Description:** Get stats for a specific CS player on a match.

### GET /csgo/matches/{match_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get stats for a CS team on a match.

### GET /csgo/players/{player_id_or_slug}/stats
**Description:** Get overall stats for a CS player.

### GET /csgo/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats
### GET /csgo/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats
### GET /csgo/teams/{team_id_or_slug}/stats
### GET /csgo/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats
### GET /csgo/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats

---

### GET /csgo/players
**Description:** List Counter-Strike players.

### GET /csgo/series
### GET /csgo/series/past
### GET /csgo/series/running
### GET /csgo/series/upcoming

### GET /csgo/teams
**Description:** List Counter-Strike teams.

### GET /csgo/tournaments
### GET /csgo/tournaments/past
### GET /csgo/tournaments/running
### GET /csgo/tournaments/upcoming

---

### GET /csgo/weapons
**Description:** List all CS weapons.
**Response:** `[{ "id": 28, "name": "Glock-18", "slug": "glock", "image_url": "..." }]`

### GET /csgo/weapons/{csgo_weapon_id_or_slug}
**Description:** Get a single weapon by ID or slug.

---

## CATEGORY: Dota 2

### GET /dota2/abilities
**Description:** List all Dota 2 abilities.
**Extra Query Params:** `from`, `to`, `side` (radiant/dire), `games_count`
**Response:** `[{ "id": 1, "name": "earth_spirit_boulder_smash", "image_url": "...", "level": 1 }]`

### GET /dota2/abilities/{dota2_ability_id_or_slug}
**Description:** Get a single ability.

---

### GET /dota2/games/{dota2_game_id}
**Description:** Get a single Dota 2 game by ID.
**Plan:** Historical or Real-time
**Extra Query Params:** `side` (radiant/dire), `from`, `to`

**Response Schema:**
```json
{
  "id": 718605,
  "match_id": 123,
  "begin_at": "...", "end_at": "...",
  "length": 2400,
  "complete": true, "finished": true, "detailed_stats": true,
  "first_blood": { ... },
  "winner": { ... },

  "players": [{
    "player": { "id": 1, "name": "...", "role": "1", ... },
    "team": { ... },
    "opponent": { ... },
    "faction": "radiant",           // radiant or dire
    "role": 1,                      // 1-5 (carry to support)
    "hero": { "id": 1, "name": "earth_spirit", "localized_name": "Earth Spirit", "image_url": "..." },
    "abilities": [{ "id": 1, "name": "...", "level": 1, "image_url": "..." }],
    "items": [{ "id": 1, "name": "...", "image_url": "..." }],

    // Stats
    "kills": 10, "deaths": 5, "assists": 15,
    "last_hits": 200, "denies": 10,
    "gold_per_min": 450, "gold_remaining": 2000, "gold_spent": 15000, "gold_percentage": 25.5,
    "xp_per_min": 550,
    "net_worth": 17000,
    "hero_damage": 25000, "hero_damage_percentage": 30.5,
    "tower_damage": 3000, "tower_kills": 2,
    "damage_taken": 18000,
    "heal": 500,
    "hero_level": 25,

    // Wards
    "observer_used": 5, "observer_wards_purchased": 6, "observer_wards_destroyed": 2,
    "sentry_used": 8, "sentry_wards_purchased": 10, "sentry_wards_destroyed": 1,

    // Jungle
    "camps_stacked": 3, "creeps_stacked": 12,
    "lane_creep": 150, "neutral_creep": 50
  }]
}
```

---

### GET /dota2/games/{dota2_game_id}/frames
**Description:** List frames (snapshots) for a Dota 2 game.
**Plan:** Real-time only
**Extra Query Params:** `from`, `to`, `side`, `games_count`

---

### GET /dota2/matches/{match_id_or_slug}/games
**Description:** List games for a Dota 2 match.

### GET /dota2/teams/{team_id_or_slug}/games
**Description:** List finished games for a Dota 2 team.

---

### GET /dota2/heroes
**Description:** List all Dota 2 heroes.
**Extra Query Params:** `from`, `to`, `side` (radiant/dire), `games_count`
**Response:** `[{ "id": 1, "name": "earth_spirit", "localized_name": "Earth Spirit", "image_url": "..." }]`

### GET /dota2/heroes/{dota2_hero_id_or_slug}
**Description:** Get a single hero.

---

### GET /dota2/items
**Description:** List all Dota 2 items.
**Extra Query Params:** `from`, `to`, `side`, `games_count`
**Response:** `[{ "id": 1, "name": "Blink Dagger", "image_url": "..." }]`

### GET /dota2/items/{dota2_item_id_or_slug}
**Description:** Get a single item.

---

### GET /dota2/leagues
### GET /dota2/matches
### GET /dota2/matches/past
### GET /dota2/matches/running
### GET /dota2/matches/upcoming

---

### GET /dota2/matches/{match_id_or_slug}/players/stats
**Description:** Get stats for all Dota 2 players on a match.
**Plan:** Historical or Real-time

### GET /dota2/players/{player_id_or_slug}/stats
### GET /dota2/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats
### GET /dota2/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats
### GET /dota2/teams/{team_id_or_slug}/stats
### GET /dota2/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats
### GET /dota2/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats

---

### GET /dota2/players
### GET /dota2/series
### GET /dota2/series/past
### GET /dota2/series/running
### GET /dota2/series/upcoming
### GET /dota2/series/{serie_id_or_slug}/teams

### GET /dota2/teams
### GET /dota2/tournaments
### GET /dota2/tournaments/past
### GET /dota2/tournaments/running
### GET /dota2/tournaments/upcoming

---

## CATEGORY: League of Legends

### GET /lol/champions
**Description:** List LoL champions with base stats.
**Extra Query Params:** `side` (blue/red), `from`, `to`, `videogame_version` (latest/all/specific)

**Response Schema (Champion):**
```json
{
  "id": 1, "name": "Ahri", "slug": "ahri",
  "image_url": "...", "big_image_url": "...",
  "videogame_versions": ["14.1.1"],
  "hp": 570, "hpperlevel": 92, "hpregen": 5.5, "hpregenperlevel": 0.6,
  "mp": 418, "mpperlevel": 25, "mpregen": 8, "mpregenperlevel": 0.8,
  "armor": 21, "armorperlevel": 4.7,
  "attackdamage": 53, "attackdamageperlevel": 3,
  "attackrange": 550, "attackspeedoffset": null, "attackspeedperlevel": 2,
  "crit": 0, "critperlevel": 0,
  "movespeed": 330,
  "spellblock": 30, "spellblockperlevel": 1.3
}
```

### GET /lol/champions/{lol_champion_id}
### GET /lol/versions/all/champions
### GET /lol/versions/{lol_version_name}/champions

---

### GET /lol/games/{lol_game_id}
**Description:** Get a single LoL game by ID.
**Plan:** Historical or Real-time
**Extra Query Params:** `from`, `to`, `videogame_version`

**Response Schema (LoL Game — Player Stats):**
```json
{
  "player_id": 1,
  "player": { ... },
  "champion": { "id": 1, "name": "Ahri", ... },
  "team": { ... }, "opponent": { ... },
  "role": "mid",                    // top, jun, mid, adc, sup
  "level": 18,
  "kills": 8, "deaths": 3, "assists": 12,

  // Economy
  "gold_earned": 15000, "gold_spent": 14500, "gold_percentage": 22.5,
  "creep_score": 250, "minions_killed": 250,
  "cs_at_14": 120, "cs_diff_at_14": 15,

  // Kill series
  "largest_killing_spree": 5, "largest_multi_kill": 3,
  "kills_series": { "double_kills": 2, "triple_kills": 1, "quadra_kills": 0, "penta_kills": 0 },
  "kills_counters": { "players": 8, "turrets": 2, "inhibitors": 1, "wards": 5, "neutral_minions": 30 },

  // Damage breakdown
  "total_damage": { "dealt": 45000, "dealt_percentage": 28.5, "dealt_to_champions": 22000, "dealt_to_champions_percentage": 30.1, "taken": 18000 },
  "physical_damage": { ... },
  "magic_damage": { ... },
  "true_damage": { ... },

  // Items & Abilities
  "items": [{ "id": 1, "name": "...", "is_trinket": false, "image_url": "..." }],
  "spells": [{ "id": 1, "name": "Flash", "image_url": "..." }],
  "runes_reforged": {
    "primary_path": { ... },
    "secondary_path": { ... },
    "shards": { ... }
  },

  // Vision
  "wards": { "placed": 15, "sight_wards_bought_in_game": 0, "vision_wards_bought_in_game": 5 },

  // Flags
  "flags": {
    "first_blood_kill": true, "first_blood_assist": false,
    "first_tower_kill": false, "first_tower_assist": true,
    "first_inhibitor_kill": false, "first_inhibitor_assist": false
  },

  // Utility
  "total_heal": 3000,
  "total_time_crowd_control_dealt": 45,
  "total_units_healed": 12
}
```

---

### GET /lol/games/{lol_game_id}/events
**Description:** List play-by-play events for a LoL game.
**Plan:** Real-time

### GET /lol/games/{lol_game_id}/frames
**Description:** List frames for a LoL game.
**Plan:** Real-time

### GET /lol/matches/{match_id_or_slug}/games
### GET /lol/teams/{team_id_or_slug}/games

---

### GET /lol/items
**Description:** List LoL items.
**Extra Query Params:** `from`, `to`, `videogame_version`
**Response:** `[{ "id": 1, "name": "...", "image_url": "...", "is_trinket": false, "videogame_versions": [...] }]`

### GET /lol/items/{lol_item_id}
### GET /lol/versions/all/items
### GET /lol/versions/{lol_version_name}/items

---

### GET /lol/leagues
### GET /lol/masteries
**Description:** List LoL masteries.
### GET /lol/masteries/{lol_mastery_id}

---

### GET /lol/matches
### GET /lol/matches/past
### GET /lol/matches/running
### GET /lol/matches/upcoming
### GET /lol/matches/{match_id_or_slug}

---

### GET /lol/matches/{match_id_or_slug}/players/stats
**Description:** Get detailed stats for all LoL players on a match.
**Plan:** Historical or Real-time
**Extra Query Params:** `side` (blue/red), `from`, `to`, `videogame_version`, `games_count`
**Response:** See LoL Game Player Stats schema above.

### GET /lol/players/{player_id_or_slug}/stats
### GET /lol/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats
### GET /lol/series/{serie_id_or_slug}/teams/stats
### GET /lol/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats
### GET /lol/teams/{team_id_or_slug}/stats
### GET /lol/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats
### GET /lol/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats

---

### GET /lol/players
### GET /lol/runes
**Description:** List legacy runes.
### GET /lol/runes/{lol_rune_id}

### GET /lol/runes-reforged
**Description:** List latest reforged runes.
**Response:** `[{ "id": 1, "name": "Electrocute", "image_url": "...", "type": "..." }]`

### GET /lol/runes-reforged-paths
**Description:** List rune paths.
### GET /lol/runes-reforged-paths/{lol_rune_path_id}
### GET /lol/runes-reforged/{lol_rune_reforged_id}

---

### GET /lol/series
### GET /lol/series/past
### GET /lol/series/running
### GET /lol/series/upcoming
### GET /lol/series/{serie_id_or_slug}/teams

### GET /lol/teams

### GET /lol/spells
**Description:** List summoner spells.
**Extra Query Params:** `videogame_version`
**Response:** `[{ "id": 1, "name": "Flash", "image_url": "...", "videogame_versions": [...] }]`
### GET /lol/spells/{lol_spell_id}

### GET /lol/tournaments
### GET /lol/tournaments/past
### GET /lol/tournaments/running
### GET /lol/tournaments/upcoming

---

## CATEGORY: Valorant

### GET /valorant/abilities
**Description:** List all Valorant abilities.
**Response:**
```json
[{
  "id": 1,
  "name": "Paranoia",
  "ability_type": "ability_one",     // ability_one, ability_two, grenade_ability, ultimate_ability
  "creds": 300,                      // nullable (cost)
  "image_url": "...",
  "videogame_versions": ["5.0"]
}]
```

### GET /valorant/abilities/{valorant_ability_id}

---

### GET /valorant/agents
**Description:** List all Valorant agents.
**Response:** `[{ "id": 167, "name": "Fade", "portrait_url": "...", "videogame_versions": ["5.0"] }]`

### GET /valorant/agents/{valorant_agent_id}
### GET /valorant/versions/all/agents
### GET /valorant/versions/{valorant_version_name}/agents

---

### GET /valorant/games/{valorant_game_id}
**Description:** Get a single Valorant game by ID.
**Plan:** Historical or Real-time

**Response Schema (Valorant Game — Rounds):**
```json
{
  "rounds": [{
    "number": 1,
    "outcome": "spike_defused",      // spike_defused, spike_exploded, attackers_eliminated, defenders_eliminated
    "winner_team": { "id": 5, "side": "defenders" },
    "attackers": {
      "team_id": 6, "score": 0,
      "players": [{
        "id": 1, "name": "...",
        "agent": { "id": 167, "name": "Fade", "portrait_url": "..." },
        "kills": 2, "assists": 1,
        "combat_score": 250,
        "weapon": { "id": 1, "name": "Vandal", "image_url": "..." },
        "shield_type": "heavy_shield",  // no_shield, light_shield, heavy_shield
        "eco_beg_prep": 4000,           // credits at round start
        "eco_end_prep": 1500            // credits remaining
      }]
    },
    "defenders": { ... }
  }]
}
```

---

### GET /valorant/games/{valorant_game_id}/events
**Description:** List play-by-play events for a Valorant game.
**Plan:** Pro Real-time

### GET /valorant/games/{valorant_game_id}/rounds
**Description:** List detailed rounds for a Valorant game.
**Plan:** Pro Historical
**Response:** Array of `ValorantFullRound` (see game schema above).

### GET /valorant/matches/{match_id_or_slug}/games

---

### GET /valorant/leagues
### GET /valorant/maps
**Description:** List Valorant maps.
**Extra Query Params:** `videogame_version`
**Response:** `[{ "id": 1, "name": "Bind", "image_url": "...", "videogame_versions": [...] }]`

### GET /valorant/maps/{valorant_map_id}
### GET /valorant/versions/all/maps
### GET /valorant/versions/{valorant_version_name}/maps

---

### GET /valorant/matches
### GET /valorant/matches/past
### GET /valorant/matches/running
### GET /valorant/matches/upcoming

---

### GET /valorant/matches/{match_id_or_slug}/players/stats
**Description:** Get player stats for a Valorant match.
**Plan:** Historical or Real-time

### GET /valorant/matches/{match_id_or_slug}/teams/{team_id_or_slug}/stats
### GET /valorant/players/{player_id_or_slug}/stats
### GET /valorant/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats
### GET /valorant/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats
### GET /valorant/teams/{team_id_or_slug}/stats
### GET /valorant/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats
### GET /valorant/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats

---

### GET /valorant/players
### GET /valorant/series
### GET /valorant/series/past
### GET /valorant/series/running
### GET /valorant/series/upcoming

### GET /valorant/teams
### GET /valorant/tournaments
### GET /valorant/tournaments/past
### GET /valorant/tournaments/running
### GET /valorant/tournaments/upcoming

---

### GET /valorant/weapons
**Description:** List Valorant weapons.
**Response:** `[{ "id": 1, "name": "Vandal", "image_url": "...", "videogame_versions": [...] }]`

### GET /valorant/weapons/{valorant_weapon_id}

---

## CATEGORY: Overwatch

### GET /ow/games/{ow_game_id}
**Description:** Get a single Overwatch game by ID.
**Plan:** Historical or Real-time
**Extra Query Params:** `from`, `to`, `games_count`
**Response:** Game object with map (including `game_mode`: Assault/Control/Escort/Hybrid/Push), rounds with player heroes/kills/deaths.

### GET /ow/matches/{match_id_or_slug}/games

### GET /ow/games/{ow_game_id}/players/{player_id_or_slug}/stats
### GET /ow/matches/{match_id_or_slug}/players/stats
### GET /ow/matches/{match_id_or_slug}/players/{player_id_or_slug}/stats
### GET /ow/players/{player_id_or_slug}/stats
### GET /ow/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats
### GET /ow/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats

---

### GET /ow/heroes
**Description:** List Overwatch heroes.
**Extra Query Params:** `from`, `to`, `games_count`
**Response:**
```json
[{
  "id": 1,
  "name": "Ana",
  "slug": "ana",
  "role": "support",                // damage, defense, offense, support, tank
  "difficulty": 3,
  "image_url": "...",
  "portrait_url": "...",
  "real_name": "Ana Amari"
}]
```

### GET /ow/heroes/{ow_hero_id_or_slug}

---

### GET /ow/leagues
### GET /ow/maps
**Description:** List Overwatch maps.
**Response:**
```json
[{
  "id": 1, "name": "Hanamura", "slug": "hanamura",
  "game_mode": "Assault",           // Assault, Control, Escort, Hybrid, Push
  "image_url": "...",
  "thumbnail_url": "..."
}]
```

### GET /ow/maps/{ow_map_id_or_slug}

---

### GET /ow/matches
### GET /ow/matches/past
### GET /ow/matches/running
### GET /ow/matches/upcoming

### GET /ow/players
### GET /ow/series
### GET /ow/series/past
### GET /ow/series/running
### GET /ow/series/upcoming

### GET /ow/teams
### GET /ow/tournaments
### GET /ow/tournaments/past
### GET /ow/tournaments/running
### GET /ow/tournaments/upcoming

---

## CATEGORY: EA Sports FC

> API prefix: `/fifa/`
> These endpoints follow the standard pattern (leagues, matches, players, series, teams, tournaments).

### GET /fifa/leagues
### GET /fifa/matches
### GET /fifa/matches/past
### GET /fifa/matches/running
### GET /fifa/matches/upcoming
### GET /fifa/players
### GET /fifa/series
### GET /fifa/series/past
### GET /fifa/series/running
### GET /fifa/series/upcoming
### GET /fifa/teams
### GET /fifa/tournaments
### GET /fifa/tournaments/past
### GET /fifa/tournaments/running
### GET /fifa/tournaments/upcoming

---

## CATEGORY: King of Glory

> API prefix: `/kog/`

### GET /kog/leagues
### GET /kog/matches
### GET /kog/matches/past
### GET /kog/matches/running
### GET /kog/matches/upcoming
### GET /kog/players
### GET /kog/series
### GET /kog/series/past
### GET /kog/series/running
### GET /kog/series/upcoming
### GET /kog/teams
### GET /kog/tournaments
### GET /kog/tournaments/past
### GET /kog/tournaments/running
### GET /kog/tournaments/upcoming

---

## CATEGORY: LoL Wild Rift

> API prefix: `/lol-wild-rift/`

### GET /lol-wild-rift/leagues
### GET /lol-wild-rift/matches
### GET /lol-wild-rift/matches/past
### GET /lol-wild-rift/matches/running
### GET /lol-wild-rift/matches/upcoming
### GET /lol-wild-rift/players
### GET /lol-wild-rift/series
### GET /lol-wild-rift/series/past
### GET /lol-wild-rift/series/running
### GET /lol-wild-rift/series/upcoming
### GET /lol-wild-rift/teams
### GET /lol-wild-rift/tournaments
### GET /lol-wild-rift/tournaments/past
### GET /lol-wild-rift/tournaments/running
### GET /lol-wild-rift/tournaments/upcoming

---

## CATEGORY: Mobile Legends: Bang Bang

> API prefix: `/mlbb/`

### GET /mlbb/leagues
### GET /mlbb/matches
### GET /mlbb/matches/past
### GET /mlbb/matches/running
### GET /mlbb/matches/upcoming
### GET /mlbb/players
### GET /mlbb/series
### GET /mlbb/series/past
### GET /mlbb/series/running
### GET /mlbb/series/upcoming
### GET /mlbb/teams
### GET /mlbb/tournaments
### GET /mlbb/tournaments/past
### GET /mlbb/tournaments/running
### GET /mlbb/tournaments/upcoming

---

## CATEGORY: PUBG

> API prefix: `/pubg/`

### GET /pubg/leagues
### GET /pubg/matches
### GET /pubg/matches/past
### GET /pubg/matches/running
### GET /pubg/matches/upcoming
### GET /pubg/players
### GET /pubg/series
### GET /pubg/series/past
### GET /pubg/series/running
### GET /pubg/series/upcoming
### GET /pubg/teams
### GET /pubg/tournaments
### GET /pubg/tournaments/past
### GET /pubg/tournaments/running
### GET /pubg/tournaments/upcoming

---

## CATEGORY: Rainbow Six Siege

> API prefix: `/r6siege/`

### GET /r6siege/leagues
### GET /r6siege/matches
### GET /r6siege/matches/past
### GET /r6siege/matches/running
### GET /r6siege/matches/upcoming
### GET /r6siege/players
### GET /r6siege/series
### GET /r6siege/series/past
### GET /r6siege/series/running
### GET /r6siege/series/upcoming
### GET /r6siege/teams
### GET /r6siege/tournaments
### GET /r6siege/tournaments/past
### GET /r6siege/tournaments/running
### GET /r6siege/tournaments/upcoming

---

## CATEGORY: Rocket League

> API prefix: `/rl/`

### GET /rl/leagues
### GET /rl/matches
### GET /rl/matches/past
### GET /rl/matches/running
### GET /rl/matches/upcoming
### GET /rl/players
### GET /rl/series
### GET /rl/series/past
### GET /rl/series/running
### GET /rl/series/upcoming
### GET /rl/teams
### GET /rl/tournaments
### GET /rl/tournaments/past
### GET /rl/tournaments/running
### GET /rl/tournaments/upcoming

---

## CATEGORY: StarCraft 2

> API prefix: `/starcraft-2/`

### GET /starcraft-2/leagues
### GET /starcraft-2/matches
### GET /starcraft-2/matches/past
### GET /starcraft-2/matches/running
### GET /starcraft-2/matches/upcoming
### GET /starcraft-2/players
### GET /starcraft-2/series
### GET /starcraft-2/series/past
### GET /starcraft-2/series/running
### GET /starcraft-2/series/upcoming
### GET /starcraft-2/teams
### GET /starcraft-2/tournaments
### GET /starcraft-2/tournaments/past
### GET /starcraft-2/tournaments/running
### GET /starcraft-2/tournaments/upcoming

---

## CATEGORY: StarCraft Brood War

> API prefix: `/starcraft-brood-war/`

### GET /starcraft-brood-war/leagues
### GET /starcraft-brood-war/matches
### GET /starcraft-brood-war/matches/past
### GET /starcraft-brood-war/matches/running
### GET /starcraft-brood-war/matches/upcoming
### GET /starcraft-brood-war/players
### GET /starcraft-brood-war/series
### GET /starcraft-brood-war/series/past
### GET /starcraft-brood-war/series/running
### GET /starcraft-brood-war/series/upcoming
### GET /starcraft-brood-war/teams
### GET /starcraft-brood-war/tournaments
### GET /starcraft-brood-war/tournaments/past
### GET /starcraft-brood-war/tournaments/running
### GET /starcraft-brood-war/tournaments/upcoming

---

## CATEGORY: Call of Duty (CODMW)

> API prefix: `/codmw/`

### GET /codmw/leagues
### GET /codmw/matches
### GET /codmw/matches/past
### GET /codmw/matches/running
### GET /codmw/matches/upcoming
### GET /codmw/players
### GET /codmw/series
### GET /codmw/series/past
### GET /codmw/series/running
### GET /codmw/series/upcoming
### GET /codmw/teams
### GET /codmw/tournaments
### GET /codmw/tournaments/past
### GET /codmw/tournaments/running
### GET /codmw/tournaments/upcoming

---

# END OF PART 2 (API REFERENCE)

---

# APPENDIX: Simple Game Category Pattern

All "simple" game categories (EA FC, KoG, Wild Rift, MLBB, PUBG, R6, RL, SC2, SC:BW, CODMW) share the same endpoint structure:

| Endpoint Pattern | Description |
|-----------------|-------------|
| `GET /{prefix}/leagues` | List leagues |
| `GET /{prefix}/matches` | List matches |
| `GET /{prefix}/matches/past` | Past matches |
| `GET /{prefix}/matches/running` | Running matches |
| `GET /{prefix}/matches/upcoming` | Upcoming matches |
| `GET /{prefix}/players` | List players |
| `GET /{prefix}/series` | List series |
| `GET /{prefix}/series/past` | Past series |
| `GET /{prefix}/series/running` | Running series |
| `GET /{prefix}/series/upcoming` | Upcoming series |
| `GET /{prefix}/teams` | List teams |
| `GET /{prefix}/tournaments` | List tournaments |
| `GET /{prefix}/tournaments/past` | Past tournaments |
| `GET /{prefix}/tournaments/running` | Running tournaments |
| `GET /{prefix}/tournaments/upcoming` | Upcoming tournaments |

All use standard pagination params (`page`, `per_page`) and return the same response schemas as the generic endpoints (League, Match, Player, Serie, Team, Tournament objects).

| Game | API Prefix |
|------|-----------|
| EA Sports FC | `/fifa/` |
| King of Glory | `/kog/` |
| LoL Wild Rift | `/lol-wild-rift/` |
| Mobile Legends | `/mlbb/` |
| PUBG | `/pubg/` |
| Rainbow Six Siege | `/r6siege/` |
| Rocket League | `/rl/` |
| StarCraft 2 | `/starcraft-2/` |
| StarCraft Brood War | `/starcraft-brood-war/` |
| Call of Duty | `/codmw/` |

---

# ENDPOINT COUNT SUMMARY

| Category | Endpoints |
|----------|-----------|
| Incidents | 4 |
| All Video Games (generic) | 57 |
| Counter-Strike | 33 |
| Dota 2 | 33 |
| League of Legends | 48 |
| Valorant | 39 |
| Overwatch | 27 |
| EA Sports FC | 15 |
| King of Glory | 15 |
| LoL Wild Rift | 15 |
| Mobile Legends | 15 |
| PUBG | 15 |
| Rainbow Six Siege | 15 |
| Rocket League | 15 |
| StarCraft 2 | 15 |
| StarCraft Brood War | 15 |
| Call of Duty (CODMW) | 15 |
| **TOTAL** | **~251** |
