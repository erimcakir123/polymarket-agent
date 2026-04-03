# PandaScore API Reference

> Scraped from https://developers.pandascore.co/reference on 2026-04-03
> Base URL: `https://api.pandascore.co`
> Authentication: Bearer token in header (`Authorization: Bearer YOUR_TOKEN`)

---

## Table of Contents

### Incidents
1. [GET /additions](#get-additions)
2. [GET /changes](#get-changes)
3. [GET /deletions](#get-deletions)
4. [GET /incidents](#get-incidents)

### All Video Games - Videogames
5. [GET /videogames](#get-videogames)
6. [GET /videogames/{videogame_id_or_slug}](#get-videogamesvideogame_id_or_slug)
7. [GET /videogames/{videogame_id_or_slug}/leagues](#get-videogamesvideogame_id_or_slugleagues)
8. [GET /videogames/{videogame_id_or_slug}/series](#get-videogamesvideogame_id_or_slugseries)
9. [GET /videogames/{videogame_id_or_slug}/titles](#get-videogamesvideogame_id_or_slugtitles)
10. [GET /videogames/{videogame_id_or_slug}/tournaments](#get-videogamesvideogame_id_or_slugtournaments)
11. [GET /videogames/{videogame_id_or_slug}/versions](#get-videogamesvideogame_id_or_slugversions)

### All Video Games - Lives
12. [GET /lives](#get-lives)

### All Video Games - Leagues
13. [GET /leagues](#get-leagues)
14. [GET /leagues/{league_id_or_slug}](#get-leaguesleague_id_or_slug)
15. [GET /leagues/{league_id_or_slug}/matches](#get-leaguesleague_id_or_slugmatches)
16. [GET /leagues/{league_id_or_slug}/matches/past](#get-leaguesleague_id_or_slugmatchespast)
17. [GET /leagues/{league_id_or_slug}/matches/running](#get-leaguesleague_id_or_slugmatchesrunning)
18. [GET /leagues/{league_id_or_slug}/matches/upcoming](#get-leaguesleague_id_or_slugmatchesupcoming)
19. [GET /leagues/{league_id_or_slug}/series](#get-leaguesleague_id_or_slugseries)
20. [GET /leagues/{league_id_or_slug}/tournaments](#get-leaguesleague_id_or_slugtournaments)

---

## INCIDENTS ENDPOINTS

---

### GET /additions

**Description:** Get the latest additions. This endpoint only shows unchanged objects.

**URL:** `https://api.pandascore.co/additions`

**Plan:** Available to all customers

**Path Parameters:**
None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics. E.g. `?games_count=5` shows stats for the most recent 5 games played |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "change_type": "creation | deletion | update",
    "id": 123,
    "modified_at": "2024-01-01T00:00:00Z",
    "object": {
      // League, Serie, Tournament, or Match object (varies)
    },
    "type": "string (object type: league, match, serie, tournament, player, team)"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/additions?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /changes

**Description:** Get the latest updates. This endpoint only provides the latest change for an object. It does not keep track of previous changes.

**URL:** `https://api.pandascore.co/changes`

**Plan:** Available to all customers

**Path Parameters:**
None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics. E.g. `?games_count=5` shows stats for the most recent 5 games played |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "change_type": "creation | deletion | update",
    "id": 123,
    "modified_at": "2024-01-01T00:00:00Z",
    "object": {
      // League, Serie, Tournament, or Match object (varies)
    },
    "type": "string (object type)"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/changes?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /deletions

**Description:** Get the latest deleted documents.

**URL:** `https://api.pandascore.co/deletions`

**Plan:** Available to all customers

**Path Parameters:**
None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "change_type": "creation | deletion | update",
    "id": 123,
    "modified_at": "2024-01-01T00:00:00Z",
    "object": {
      // Deleted resource details (league, match, serie, tournament, player, team)
    },
    "type": "string (resource type)"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/deletions?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /incidents

**Description:** Get the latest updates and additions. This endpoint provides the most recent incident for an object without tracking previous incidents. Combines additions, changes, and deletions.

**URL:** `https://api.pandascore.co/incidents`

**Plan:** Available to all customers

**Path Parameters:**
None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics. E.g. `?games_count=5` shows stats for the most recent 5 games played |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "change_type": "creation | deletion | update",
    "id": 123,
    "modified_at": "2024-01-01T00:00:00Z",
    "object": {
      // League, Serie, Tournament, or Match object (varies)
    },
    "type": "string (object type: league, match, player, serie, team, tournament)"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/incidents?page[size]=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ALL VIDEO GAMES - VIDEOGAMES ENDPOINTS

---

### GET /videogames

**Description:** List videogames.

**URL:** `https://api.pandascore.co/videogames`

**Plan:** Available to all customers

**Path Parameters:**
None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | Amount of games used for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "League of Legends",
    "slug": "league-of-legends",
    "current_version": "14.1.0"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (min: 1) | Unique videogame identifier |
| `name` | string | Videogame title |
| `slug` | string | Human-readable identifier, pattern: `^[a-z0-9_-]+$` |
| `current_version` | string, nullable | Current version, pattern: `^[0-9]+\.[0-9]+(\.[0-9]+)?$` |

**Supported Videogames:** League of Legends, Counter-Strike, Dota 2, Overwatch, PUBG, Rocket League, Call of Duty, Rainbow Six Siege, EA Sports FC, Valorant, King of Glory, LoL Wild Rift, StarCraft 2, StarCraft Brood War, Mobile Legends: Bang Bang, eSoccer, eBasketball, eCricket, eHockey

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/videogames" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /videogames/{videogame_id_or_slug}

**Description:** Get a single videogame by ID or by slug.

**URL:** `https://api.pandascore.co/videogames/{videogame_id_or_slug}`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `videogame_id_or_slug` | integer or string | Required | Videogame numeric ID or slug (e.g. `1` or `league-of-legends`) |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | Amount of games used for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "id": 1,
  "name": "League of Legends",
  "slug": "league-of-legends",
  "current_version": "14.1.0"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (min: 1) | Unique videogame identifier |
| `name` | string | Videogame title |
| `slug` | string | Human-readable identifier |
| `current_version` | string, nullable | Current version number |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/videogames/league-of-legends" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /videogames/{videogame_id_or_slug}/leagues

**Description:** List leagues for a given videogame.

**URL:** `https://api.pandascore.co/videogames/{videogame_id_or_slug}/leagues`

**Plan:** Available to all customers (some fields like player age/birthday require Historical plan or above)

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `videogame_id_or_slug` | integer or string | Required | Videogame numeric ID or slug (e.g. `league-of-legends`) |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics. E.g. `?games_count=5` shows stats for the most recent 5 games played |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 123,
    "name": "LEC",
    "slug": "lol-lec",
    "image_url": "https://...",
    "url": "https://...",
    "modified_at": "2024-01-01T00:00:00Z",
    "videogame": {
      "id": 1,
      "name": "League of Legends",
      "slug": "league-of-legends",
      "current_version": "14.1.0"
    },
    "series": [
      {
        "id": 456,
        "name": "Spring 2024",
        "full_name": "...",
        "slug": "...",
        "begin_at": "2024-01-01T00:00:00Z",
        "end_at": "2024-06-01T00:00:00Z",
        "season": "Spring",
        "year": 2024,
        "tournaments": [...]
      }
    ]
  }
]
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | League identifier |
| `name` | string | No | League name |
| `slug` | string | No | Human-readable league identifier |
| `image_url` | string (URI) | Yes | League logo URL |
| `url` | string (URI) | Yes | League website URL |
| `modified_at` | datetime | No | Last modification timestamp |
| `videogame` | object | No | Associated videogame (id, name, slug, current_version) |
| `series` | array | No | Associated competition series with nested tournament data |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/videogames/league-of-legends/leagues" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /videogames/{videogame_id_or_slug}/series

**Description:** List series for the given videogame.

**URL:** `https://api.pandascore.co/videogames/{videogame_id_or_slug}/series`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `videogame_id_or_slug` | integer or string | Required | Videogame numeric ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 456,
    "name": "Spring 2024",
    "full_name": "LEC Spring 2024",
    "slug": "lol-lec-spring-2024",
    "season": "Spring",
    "year": 2024,
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-06-01T00:00:00Z",
    "league": {
      "id": 123,
      "name": "LEC",
      "slug": "lol-lec",
      "image_url": "https://...",
      "url": "https://..."
    },
    "tournaments": [...],
    "winner_id": 789,
    "winner_type": "Team",
    "modified_at": "2024-01-01T00:00:00Z"
  }
]
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | Serie identifier |
| `name` | string | Yes | Serie name |
| `full_name` | string | No | Complete serie designation |
| `slug` | string | No | URL-friendly identifier |
| `season` | string | Yes | Season designation (e.g. "Spring") |
| `year` | integer | Yes | Year (minimum 2012) |
| `begin_at` | datetime | Yes | Start timestamp |
| `end_at` | datetime | Yes | End timestamp |
| `league` | object | No | Associated league (id, name, slug, image_url, url) |
| `tournaments` | array | No | Tournament objects within the serie |
| `winner_id` | integer | Yes | Winning team/player ID |
| `winner_type` | enum | No | "Player" or "Team" |
| `modified_at` | datetime | No | Last modification timestamp |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/videogames/league-of-legends/series" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /videogames/{videogame_id_or_slug}/titles

**Description:** List available titles for a given videogame.

**URL:** `https://api.pandascore.co/videogames/{videogame_id_or_slug}/titles`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `videogame_id_or_slug` | integer or string | Required | Videogame numeric ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "Counter-Strike 2",
    "slug": "cs-2",
    "videogame_id": 3
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (min: 1) | VideogameTitleID |
| `name` | string | VideogameTitleName |
| `slug` | string | Human-readable identifier, pattern: `[a-z0-9_-]+` |
| `videogame_id` | integer | Associated videogame ID |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/videogames/cs-go/titles" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /videogames/{videogame_id_or_slug}/tournaments

**Description:** List tournaments of the given videogame.

**URL:** `https://api.pandascore.co/videogames/{videogame_id_or_slug}/tournaments`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `videogame_id_or_slug` | integer or string | Required | Videogame numeric ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics. E.g. `?games_count=5` shows stats for the most recent 5 games played |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 789,
    "name": "Playoffs",
    "slug": "lol-lec-spring-2024-playoffs",
    "begin_at": "2024-03-01T00:00:00Z",
    "end_at": "2024-04-15T00:00:00Z",
    "league_id": 123,
    "serie_id": 456,
    "prizepool": "$200,000",
    "region": "WEU",
    "tier": "s",
    "type": "offline",
    "has_bracket": true,
    "detailed_stats": true,
    "live_supported": true,
    "teams": [...],
    "matches": [...],
    "expected_roster": [...],
    "videogame": {
      "id": 1,
      "name": "League of Legends",
      "slug": "league-of-legends"
    },
    "videogame_title": null,
    "modified_at": "2024-01-01T00:00:00Z"
  }
]
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | Tournament identifier |
| `name` | string | No | Tournament name |
| `slug` | string | No | Human-readable identifier |
| `begin_at` | datetime | Yes | Tournament start time |
| `end_at` | datetime | Yes | Tournament end time |
| `league_id` | integer | No | Associated league ID |
| `serie_id` | integer | No | Associated series ID |
| `prizepool` | string | Yes | Prize pool information |
| `region` | string | Yes | Geographic region (AF, ASIA, EEU, ME, NA, OCE, SA, WEU) |
| `tier` | string | Yes | Ranking tier: s, a, b, c, d, unranked |
| `type` | string | Yes | Location type: online, offline, online/offline |
| `has_bracket` | boolean | No | Bracket availability |
| `detailed_stats` | boolean | No | Full statistics availability |
| `live_supported` | boolean | No | Live coverage support |
| `teams` | array | No | Participating teams |
| `matches` | array | No | Tournament matches |
| `expected_roster` | array | No | Expected team rosters |
| `videogame` | object | No | Videogame details (id, name, slug) |
| `videogame_title` | object | Yes | Specific game title version |
| `modified_at` | datetime | No | Last modification timestamp |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/videogames/league-of-legends/tournaments" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /videogames/{videogame_id_or_slug}/versions

**Description:** List available versions for a given videogame.

**URL:** `https://api.pandascore.co/videogames/{videogame_id_or_slug}/versions`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `videogame_id_or_slug` | integer or string | Required | Videogame numeric ID or slug (e.g. `league-of-legends`) |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "current": true,
    "name": "14.1.0"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `current` | boolean | Whether this is the current active version |
| `name` | string | Version number string |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/videogames/league-of-legends/versions" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ALL VIDEO GAMES - LIVES ENDPOINT

---

### GET /lives

**Description:** List currently running live matches, available from PandaScore with live websocket data.

**URL:** `https://api.pandascore.co/lives`

**Plan:** Available to all customers

**Path Parameters:**
None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics. E.g. `?games_count=5` shows stats for the most recent 5 games played |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "match": {
      "id": 123,
      "name": "Team A vs Team B",
      "status": "running",
      "match_type": "best_of",
      "number_of_games": 3,
      "scheduled_at": "2024-01-01T18:00:00Z",
      "begin_at": "2024-01-01T18:05:00Z",
      "end_at": null,
      "league": { "id": 1, "name": "...", "slug": "..." },
      "serie": { "id": 1, "name": "...", "slug": "..." },
      "tournament": { "id": 1, "name": "...", "slug": "..." },
      "opponents": [...],
      "games": [...],
      "results": [...],
      "streams_list": [...]
    }
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `match` | object | Full match object with all metadata |
| `match.id` | integer | Match identifier |
| `match.name` | string | Match display name |
| `match.status` | enum | "running" (always for live) |
| `match.match_type` | enum | best_of, all_games_played, custom, first_to, ow_best_of, red_bull_home_ground |
| `match.scheduled_at` | datetime | UTC scheduled time |
| `match.begin_at` | datetime | Actual start time |
| `match.league` | object | League info (id, name, slug, image_url, url) |
| `match.opponents` | array | Competing teams/players |
| `match.games` | array | Individual game records |
| `match.streams_list` | array | Broadcast streams |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lives" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ALL VIDEO GAMES - LEAGUES ENDPOINTS

---

### GET /leagues

**Description:** List leagues.

**URL:** `https://api.pandascore.co/leagues`

**Plan:** Available to all customers

**Path Parameters:**
None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | Amount of games used for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 123,
    "name": "LEC",
    "slug": "lol-lec",
    "image_url": "https://cdn.pandascore.co/...",
    "url": "https://lolesports.com/...",
    "modified_at": "2024-01-01T00:00:00Z",
    "videogame": {
      "id": 1,
      "name": "League of Legends",
      "slug": "league-of-legends"
    },
    "videogame_title": null,
    "series": [...]
  }
]
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | League identifier |
| `name` | string | No | League name |
| `slug` | string | No | Unique, human-readable identifier |
| `image_url` | string (URI) | Yes | League logo URL |
| `url` | string (URI) | Yes | External league URL |
| `modified_at` | datetime | No | Last modification timestamp |
| `videogame` | object | No | Associated videogame (id, name, slug) |
| `videogame_title` | object | Yes | Specific game title information |
| `series` | array | No | League's tournament series |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/leagues?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /leagues/{league_id_or_slug}

**Description:** Get a single league by ID or slug.

**URL:** `https://api.pandascore.co/leagues/{league_id_or_slug}`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `league_id_or_slug` | integer or string | Required | League numeric ID or slug (e.g. `5232` or `lol-lec`) |

**Query Parameters:**
None

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "id": 5232,
  "name": "LEC",
  "slug": "lol-lec",
  "image_url": "https://cdn.pandascore.co/...",
  "url": "https://...",
  "modified_at": "2024-01-01T00:00:00Z",
  "videogame": {
    "id": 1,
    "name": "League of Legends",
    "slug": "league-of-legends"
  },
  "series": [...]
}
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | League numeric identifier |
| `name` | string | No | League display name |
| `slug` | string | No | Human-readable identifier, pattern: `^[a-z0-9:_-]+$` |
| `image_url` | string (URI) | Yes | URL of the league logo |
| `url` | string (URI) | Yes | League's external URL |
| `modified_at` | datetime | No | Last modification timestamp |
| `videogame` | object | No | Associated esports title |
| `series` | array | No | Collection of series within the league |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/leagues/lol-lec" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /leagues/{league_id_or_slug}/matches

**Description:** List matches of the given league.

**URL:** `https://api.pandascore.co/leagues/{league_id_or_slug}/matches`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `league_id_or_slug` | integer or string | Required | League numeric ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 123,
    "name": "Round 1: Team A vs Team B",
    "slug": "team-a-vs-team-b-2024-01-01",
    "status": "finished",
    "match_type": "best_of",
    "number_of_games": 3,
    "scheduled_at": "2024-01-01T18:00:00Z",
    "begin_at": "2024-01-01T18:05:00Z",
    "end_at": "2024-01-01T20:30:00Z",
    "draw": false,
    "forfeit": false,
    "detailed_stats": true,
    "modified_at": "2024-01-01T20:35:00Z",
    "league": {
      "id": 123, "name": "LEC", "slug": "lol-lec",
      "image_url": "...", "url": "..."
    },
    "serie": {
      "id": 456, "name": "Spring 2024",
      "begin_at": "...", "end_at": "...", "year": 2024
    },
    "tournament": {
      "id": 789, "name": "Playoffs", "slug": "...",
      "has_bracket": true
    },
    "opponents": [
      {
        "opponent": { "id": 1, "name": "Team A", "slug": "team-a", "image_url": "..." },
        "type": "Team"
      }
    ],
    "games": [
      {
        "id": 1, "position": 1, "status": "finished",
        "winner": { "id": 1, "type": "Team" },
        "length": 1800
      }
    ],
    "results": [
      { "team_id": 1, "score": 2 },
      { "team_id": 2, "score": 1 }
    ],
    "streams_list": [
      {
        "raw_url": "https://twitch.tv/...",
        "language": "en",
        "official": true
      }
    ],
    "winner_id": 1,
    "winner_type": "Team"
  }
]
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | Match identifier |
| `name` | string | No | Match display name |
| `slug` | string | No | URL-friendly identifier |
| `status` | enum | No | finished, not_started, postponed, running, canceled |
| `match_type` | enum | No | best_of, all_games_played, custom, first_to, ow_best_of, red_bull_home_ground |
| `number_of_games` | integer | No | Game count in series |
| `scheduled_at` | datetime | Yes | UTC match time |
| `begin_at` | datetime | Yes | Actual start time |
| `end_at` | datetime | Yes | Completion time |
| `draw` | boolean | No | Whether result is a draw |
| `forfeit` | boolean | No | Match forfeiture status |
| `detailed_stats` | boolean | No | Full statistics availability |
| `modified_at` | datetime | No | Last update timestamp |
| `league` | object | No | League info (id, name, slug, image_url, url) |
| `serie` | object | No | Series context |
| `tournament` | object | No | Tournament context with brackets, rosters, standings |
| `opponents` | array | No | Competing teams/players with type indicator |
| `games` | array | No | Individual game records (position, winner, length) |
| `results` | array | No | Match outcome scores by team/player |
| `streams_list` | array | No | Broadcast streams (URL, language, official status) |
| `winner_id` | integer | Yes | Winning opponent ID |
| `winner_type` | enum | Yes | "Player" or "Team" |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/leagues/lol-lec/matches?per_page=50&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /leagues/{league_id_or_slug}/matches/past

**Description:** List past matches for the given league.

**URL:** `https://api.pandascore.co/leagues/{league_id_or_slug}/matches/past`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `league_id_or_slug` | integer or string | Required | League numeric ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics |

**Response Codes:** 200 OK

**Response Schema:**
Same as [GET /leagues/{league_id_or_slug}/matches](#get-leaguesleague_id_or_slugmatches) -- returns an array of match objects with identical fields. All returned matches will have `status: "finished"`.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/leagues/lol-lec/matches/past?per_page=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /leagues/{league_id_or_slug}/matches/running

**Description:** List currently running matches for the given league.

**URL:** `https://api.pandascore.co/leagues/{league_id_or_slug}/matches/running`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `league_id_or_slug` | integer or string | Required | League numeric ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics |

**Response Codes:** 200 OK

**Response Schema:**
Same as [GET /leagues/{league_id_or_slug}/matches](#get-leaguesleague_id_or_slugmatches) -- returns an array of match objects with identical fields. All returned matches will have `status: "running"`.

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | Match identifier |
| `status` | enum | No | "running" (always for this endpoint) |
| `scheduled_at` | datetime | Yes | Scheduled time |
| `begin_at` | datetime | Yes | Actual start time |
| `end_at` | datetime | Yes | Always null for running matches |
| `name` | string | No | Match identifier |
| `opponents` | array | No | Competing players/teams |
| `games` | array | No | Individual game data |
| `league_id` | integer | No | Associated league ID |
| `tournament_id` | integer | No | Associated tournament ID |
| `serie_id` | integer | No | Associated series ID |
| `winner_id` | integer | Yes | null for running matches |
| `match_type` | enum | No | Match format type |
| `number_of_games` | integer | No | Game count |
| `draw` | boolean | No | Draw status |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/leagues/lol-lec/matches/running" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /leagues/{league_id_or_slug}/matches/upcoming

**Description:** List upcoming matches for the given league.

**URL:** `https://api.pandascore.co/leagues/{league_id_or_slug}/matches/upcoming`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `league_id_or_slug` | integer or string | Required | League numeric ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics |

**Response Codes:** 200 OK

**Response Schema:**
Same as [GET /leagues/{league_id_or_slug}/matches](#get-leaguesleague_id_or_slugmatches) -- returns an array of match objects with identical fields. All returned matches will have `status: "not_started"`.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/leagues/lol-lec/matches/upcoming?per_page=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /leagues/{league_id_or_slug}/series

**Description:** List series for the given league.

**URL:** `https://api.pandascore.co/leagues/{league_id_or_slug}/series`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `league_id_or_slug` | integer or string | Required | League numeric ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | Amount of games used for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 456,
    "name": "Spring 2024",
    "full_name": "LEC Spring 2024",
    "slug": "lol-lec-spring-2024",
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-06-01T00:00:00Z",
    "season": "Spring",
    "year": 2024,
    "league_id": 123,
    "league": {
      "id": 123,
      "name": "LEC",
      "slug": "lol-lec",
      "image_url": "...",
      "url": "..."
    },
    "tournaments": [...],
    "videogame": {
      "id": 1,
      "name": "League of Legends",
      "slug": "league-of-legends"
    },
    "videogame_title": null,
    "winner_id": 789,
    "winner_type": "Team",
    "modified_at": "2024-01-01T00:00:00Z"
  }
]
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | Serie identifier |
| `name` | string | Yes | Serie name |
| `full_name` | string | No | Complete series designation |
| `slug` | string | No | URL-friendly identifier |
| `begin_at` | datetime | Yes | Start time |
| `end_at` | datetime | Yes | End time |
| `season` | string | Yes | Season designation |
| `year` | integer | Yes | Year (min: 2012) |
| `league_id` | integer | No | Associated league ID |
| `league` | object | No | League details (id, name, slug, image_url, url) |
| `tournaments` | array | No | Associated tournament objects |
| `videogame` | object | No | Game identifier (id, name, slug) |
| `videogame_title` | object | Yes | Specific game title version |
| `winner_id` | integer | Yes | Winning player or team ID |
| `winner_type` | enum | No | "Player" or "Team" |
| `modified_at` | datetime | No | Last modification timestamp |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/leagues/lol-lec/series" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /leagues/{league_id_or_slug}/tournaments

**Description:** List tournaments of the given league.

**URL:** `https://api.pandascore.co/leagues/{league_id_or_slug}/tournaments`

**Plan:** Available to all customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `league_id_or_slug` | integer or string | Required | League numeric ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | Optional | Pagination in the form of `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | Optional | Equivalent to `page[size]`. Default: 50, Min: 1, Max: 100 |
| `games_count` | integer | Optional | The amount of games used for the statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 789,
    "name": "Playoffs",
    "slug": "lol-lec-spring-2024-playoffs",
    "begin_at": "2024-03-01T00:00:00Z",
    "end_at": "2024-04-15T00:00:00Z",
    "prizepool": "$200,000",
    "region": "WEU",
    "tier": "s",
    "type": "offline",
    "has_bracket": true,
    "detailed_stats": true,
    "live_supported": true,
    "league": {
      "id": 123, "name": "LEC", "slug": "lol-lec",
      "image_url": "...", "url": "..."
    },
    "serie_id": 456,
    "teams": [...],
    "matches": [...],
    "expected_roster": [...],
    "videogame": { "id": 1, "name": "League of Legends", "slug": "league-of-legends" },
    "videogame_title": null,
    "modified_at": "2024-01-01T00:00:00Z"
  }
]
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | Tournament identifier |
| `name` | string | No | Tournament name |
| `slug` | string | No | Human-readable identifier |
| `begin_at` | datetime | Yes | Start date/time |
| `end_at` | datetime | Yes | End date/time |
| `prizepool` | string | Yes | Prize pool information |
| `region` | string | Yes | Tournament region (AF, ASIA, EEU, ME, NA, OCE, SA, WEU) |
| `tier` | string | Yes | Ranking tier: a, b, c, d, s, unranked |
| `type` | string | Yes | Location type: offline, online, online/offline |
| `has_bracket` | boolean | No | Bracket availability |
| `detailed_stats` | boolean | No | Statistical detail availability |
| `live_supported` | boolean | No | Live coverage support |
| `league` | object | No | Associated league data (id, name, slug, image_url, url) |
| `serie_id` | integer | No | Series identifier |
| `teams` | array | No | Participating teams |
| `matches` | array | No | Tournament matches |
| `expected_roster` | array | No | Expected team rosters |
| `videogame` | object | No | Videogame details (id, name, slug) |
| `videogame_title` | object | Yes | Specific game title version |
| `modified_at` | datetime | No | Last modification timestamp |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/leagues/lol-lec/tournaments" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Common Notes

### Authentication
All endpoints require a Bearer token passed in the `Authorization` header:
```
Authorization: Bearer YOUR_TOKEN
```

### Pagination
All list endpoints support pagination via:
- `page=N` (simple page number, default: 1)
- `page[size]=N&page[number]=N` (explicit size + number)
- `per_page=N` (alias for page size, default: 50, max: 100)

### Supported Videogames (IDs)
| ID | Name |
|----|------|
| 1 | League of Legends |
| 3 | Counter-Strike |
| 4 | Dota 2 |
| 14 | Overwatch |
| 20 | PUBG |
| 22 | Rocket League |
| 23 | Call of Duty |
| 24 | Rainbow Six Siege |
| 25 | EA Sports FC |
| 26 | Valorant |
| 27 | King of Glory |
| 28 | LoL Wild Rift |
| 29 | StarCraft 2 |
| 30 | StarCraft Brood War |
| 31 | Mobile Legends: Bang Bang |
| 32 | eSoccer |
| 33 | eBasketball |
| 34 | eCricket |
| 35 | eHockey |

### Match Status Enum Values
- `not_started` - Match has not begun
- `running` - Match is currently in progress
- `finished` - Match has completed
- `postponed` - Match has been postponed
- `canceled` - Match has been canceled

### Match Type Enum Values
- `best_of` - Best of N games
- `all_games_played` - All scheduled games are played
- `custom` - Custom format
- `first_to` - First to N wins
- `ow_best_of` - Overwatch best of format
- `red_bull_home_ground` - Red Bull Home Ground format

### Tournament Tier Values
- `s` - S-tier (premier events)
- `a` - A-tier
- `b` - B-tier
- `c` - C-tier
- `d` - D-tier
- `unranked` - Unranked

### Tournament Region Values
- `AF` - Africa
- `ASIA` - Asia
- `EEU` - Eastern Europe
- `ME` - Middle East
- `NA` - North America
- `OCE` - Oceania
- `SA` - South America
- `WEU` - Western Europe
