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
- **Normalized** — 800×800px (prefix `normal_`)
- **Thumbnail** — 200×200px (prefix `thumb_`)

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

# END OF DOCUMENTATION
