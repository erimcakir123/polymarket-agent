# PandaScore Counter-Strike API Reference

**Base URL:** `https://api.pandascore.co`
**Authentication:** Bearer token in `Authorization` header
**Total Endpoints:** 33

---

## Table of Contents

1. [Games](#games)
2. [Matches](#matches)
3. [Match Stats](#match-stats)
4. [Player Stats](#player-stats)
5. [Team Stats](#team-stats)
6. [Leagues](#leagues)
7. [Series](#series)
8. [Tournaments](#tournaments)
9. [Players](#players)
10. [Teams](#teams)
11. [Maps](#maps)
12. [Weapons](#weapons)

---

## Common Query Parameters

Most list endpoints share these query parameters:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination: `page=2` or `page[size]=30&page[number]=2`. Default: 1, min: 1 |
| `per_page` | integer | No | Equivalent to `page[size]`. Default: 50, max: 100, min: 1 |
| `from` | date (YYYY-MM-DD) | No | Filter results from this date |
| `to` | date (YYYY-MM-DD) | No | Filter results up to this date |
| `videogame_title` | integer or string | No | Videogame title ID or slug (pattern: `^[a-z0-9_-]+$`) |
| `games_count` | integer | No | Limit statistics to the most recent N games |

---

## Games

### 1. GET /csgo/games/{csgo_game_id}
**Description:** Get a single Counter-Strike game by ID. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/games/{csgo_game_id}`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `csgo_game_id` | integer | Yes | Counter-Strike game identifier (min: 1) |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "id": 1,
  "begin_at": "2024-01-01T00:00:00Z",
  "end_at": "2024-01-01T01:00:00Z",
  "finished": true,
  "complete": true,
  "detailed_stats": true,
  "forfeit": false,
  "length": 3600,
  "position": 1,
  "status": "finished | not_played | not_started | running",
  "map": {
    "id": 1,
    "name": "Dust2",
    "slug": "dust2",
    "image_url": "https://..."
  },
  "match": { "id": 1, "...": "full match object" },
  "rounds_score": [
    { "team_id": 1, "score": 13 },
    { "team_id": 2, "score": 7 }
  ],
  "teams": ["... team objects"],
  "players": ["... player stat objects (when detailed_stats=true)"],
  "rounds": ["... CSGOFullRound objects (when detailed_stats=true)"],
  "winner": { "id": 1, "type": "Team" }
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/games/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2. GET /csgo/games/{csgo_game_id}/events
**Description:** List play-by-play events for a given Counter-Strike game. Requires real-time data pro plan.
**URL:** `https://api.pandascore.co/csgo/games/{csgo_game_id}/events`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `csgo_game_id` | integer | Yes | Counter-Strike game identifier (min: 1) |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "... play-by-play event objects with granular match event data"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/games/1/events" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 3. GET /csgo/games/{csgo_game_id}/rounds
**Description:** List rounds in a Counter-Strike game. Requires real-time data plan.
**URL:** `https://api.pandascore.co/csgo/games/{csgo_game_id}/rounds`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `csgo_game_id` | integer | Yes | Counter-Strike game identifier (min: 1) |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "number": 1,
    "map": {
      "id": 1,
      "name": "Dust2",
      "image_url": "https://...",
      "slug": "dust2"
    },
    "outcome": "defused | eliminated | exploded | planted_eliminated | timeout",
    "terrorists": {
      "round_score": 5,
      "players": [
        {
          "id": 1,
          "name": "player_name",
          "kills": 2,
          "assists": 1,
          "is_alive": true,
          "remaining_hp": 45,
          "freeze_time_economy": {
            "economy": 5000,
            "armor": 1000,
            "defuse_kit": false,
            "weapons": { "primary": "...", "secondary": "..." },
            "utilities": ["flashbang", "smoke"]
          },
          "round_start_economy": { "...same structure" }
        }
      ]
    },
    "counter_terrorists": { "...same structure as terrorists" },
    "winner_team": {
      "team_id": 1,
      "team_name": "Team Name",
      "side": "counter_terrorists | terrorists"
    }
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/games/1/rounds" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 4. GET /csgo/matches/{match_id_or_slug}/games
**Description:** List games for a given Counter-Strike match. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/matches/{match_id_or_slug}/games`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | integer/string | Yes | Match ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `games_count` | integer | No | Number of recent games for statistics |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-01-01T01:00:00Z",
    "finished": true,
    "complete": true,
    "detailed_stats": true,
    "forfeit": false,
    "length": 3600,
    "position": 1,
    "status": "finished | not_played | not_started | running",
    "map": { "id": 1, "name": "Dust2", "slug": "dust2", "image_url": "..." },
    "match": { "...match object" },
    "rounds_score": [{ "team_id": 1, "score": 13 }],
    "winner": { "id": 1, "type": "Team" }
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/matches/1/games" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Matches

### 5. GET /csgo/matches
**Description:** List matches for the Counter-Strike videogame. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/matches`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |
| `games_count` | integer | No | Number of recent games for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "Match Name",
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-01-01T02:00:00Z",
    "status": "finished | running | not_started",
    "draw": false,
    "forfeit": false,
    "detailed_stats": true,
    "number_of_games": 3,
    "opponents": [
      { "type": "Team", "opponent": { "id": 1, "name": "...", "acronym": "...", "image_url": "..." } }
    ],
    "results": [
      { "team_id": 1, "score": 2 },
      { "team_id": 2, "score": 1 }
    ],
    "games": ["... game objects"],
    "league": { "id": 1, "name": "...", "slug": "..." },
    "serie": { "id": 1, "name": "..." },
    "tournament": { "id": 1, "name": "..." },
    "winner": { "id": 1, "type": "Team" },
    "winner_id": 1,
    "winner_type": "Team",
    "videogame_version": "..."
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/matches" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 6. GET /csgo/matches/past
**Description:** List past Counter-Strike matches. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/matches/past`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |
| `games_count` | integer | No | Number of recent games for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-01-01T02:00:00Z",
    "draw": false,
    "forfeit": false,
    "status": "finished",
    "results": [{ "team_id": 1, "score": 2 }],
    "opponents": ["... opponent objects"],
    "league": { "...league object" },
    "serie": { "...serie object" },
    "tournament": { "...tournament object" },
    "winner": { "id": 1, "type": "Team" },
    "winner_id": 1,
    "winner_type": "Team"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/matches/past?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 7. GET /csgo/matches/running
**Description:** List running Counter-Strike matches. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/matches/running`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |
| `games_count` | integer | No | Number of recent games for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "begin_at": "2024-01-01T00:00:00Z",
    "scheduled_at": "2024-01-01T00:00:00Z",
    "status": "running",
    "opponents": [
      { "type": "Team", "opponent": { "id": 1, "name": "...", "acronym": "...", "image_url": "...", "location": "..." } }
    ],
    "results": [{ "team_id": 1, "score": 1 }],
    "league": { "...league object" },
    "serie": { "...serie object" },
    "tournament": { "...tournament object" },
    "winner": null,
    "winner_id": null,
    "winner_type": null
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/matches/running" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 8. GET /csgo/matches/upcoming
**Description:** List upcoming Counter-Strike matches. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/matches/upcoming`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |
| `games_count` | integer | No | Number of recent games for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "Match Name",
    "begin_at": null,
    "scheduled_at": "2024-02-01T00:00:00Z",
    "status": "not_started",
    "opponents": ["... opponent objects"],
    "league": { "...league object" },
    "serie": { "...serie object" },
    "tournament": { "...tournament object" },
    "winner": null
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/matches/upcoming" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 9. GET /csgo/matches/{match_id_or_slug}
**Description:** Get a single Counter-Strike match by ID or slug. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/matches/{match_id_or_slug}`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | integer/string | Yes | Match ID or slug |

**Query Parameters:** None

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "id": 1,
  "begin_at": "2024-01-01T00:00:00Z",
  "end_at": "2024-01-01T02:00:00Z",
  "status": "finished | running | not_started",
  "forfeit": false,
  "draw": false,
  "detailed_stats": true,
  "games": [
    {
      "id": 1,
      "begin_at": "...",
      "end_at": "...",
      "position": 1,
      "status": "finished",
      "winner": { "id": 1, "type": "Team" },
      "map": { "id": 1, "name": "Dust2" }
    }
  ],
  "opponents": ["... opponent objects"],
  "league": { "...league object" },
  "tournament": { "...tournament object" },
  "series": { "...series object" },
  "winner": { "id": 1, "name": "Team Name" }
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/matches/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Match Stats

### 10. GET /csgo/matches/{match_id_or_slug}/players/stats
**Description:** Get detailed statistics of Counter-Strike players for the given match. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/matches/{match_id_or_slug}/players/stats`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | integer/string | Yes | Match ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "adr": 85.2,
    "assists": 12,
    "deaths": 15,
    "first_kills_diff": 3,
    "flash_assists": 2,
    "game_id": 1,
    "headshots": 8,
    "k_d_diff": 5,
    "kast": 72.5,
    "kills": 20,
    "rating": 1.15,
    "player": {
      "id": 1,
      "name": "player_name",
      "nationality": "US",
      "age": 25
    },
    "team": {
      "id": 1,
      "name": "Team Name",
      "acronym": "TN",
      "location": "US"
    },
    "opponent": {
      "id": 2,
      "name": "Opposing Team"
    }
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/matches/1/players/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 11. GET /csgo/matches/{match_id_or_slug}/players/{player_id_or_slug}/stats
**Description:** Get detailed statistics for a specific Counter-Strike player during a given match. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/matches/{match_id_or_slug}/players/{player_id_or_slug}/stats`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | integer/string | Yes | Match ID or slug |
| `player_id_or_slug` | integer/string | Yes | Player ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "kills": 20,
  "deaths": 15,
  "assists": 12,
  "rating": 1.15,
  "adr": 85.2,
  "kast": 72.5,
  "headshots": 8,
  "k_d_diff": 5,
  "first_kills_diff": 3,
  "flash_assists": 2,
  "player": { "id": 1, "name": "...", "slug": "..." },
  "team": { "id": 1, "name": "..." },
  "opponent": { "id": 2, "name": "..." }
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/matches/1/players/1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 12. GET /csgo/matches/{match_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get detailed statistics for a specific Counter-Strike team during a match. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/matches/{match_id_or_slug}/teams/{team_id_or_slug}/stats`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | integer/string | Yes | Match ID or slug |
| `team_id_or_slug` | integer/string | Yes | Team ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "team": { "id": 1, "name": "...", "acronym": "..." },
  "kills": 250,
  "deaths": 200,
  "assists": 80,
  "adr": 82.5,
  "kast": 70.0,
  "headshots": 100,
  "rating": 1.10,
  "... economy and round-level statistics"
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/matches/1/teams/1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Player Stats

### 13. GET /csgo/players/{player_id_or_slug}/stats
**Description:** Get detailed statistics of a given Counter-Strike player. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/players/{player_id_or_slug}/stats`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `player_id_or_slug` | integer/string | Yes | Player ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "kills": 20,
    "deaths": 15,
    "assists": 12,
    "rating": 1.15,
    "adr": 85.2,
    "kast": 72.5,
    "headshots": 8,
    "k_d_diff": 5,
    "player": { "id": 1, "name": "...", "slug": "..." }
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/players/1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 14. GET /csgo/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats
**Description:** Get detailed statistics of a given Counter-Strike player for the given serie. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | integer/string | Yes | Serie ID or slug |
| `player_id_or_slug` | integer/string | Yes | Player ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "kills": 200,
  "deaths": 150,
  "assists": 80,
  "adr": 85.2,
  "kast": 72.5,
  "headshots": 60,
  "k_d_diff": 50,
  "first_kills_diff": 10,
  "flash_assists": 15,
  "rating": 1.15,
  "player": { "id": 1, "name": "...", "slug": "..." }
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/series/1/players/1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 15. GET /csgo/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats
**Description:** Get detailed statistics of a given Counter-Strike player for the given tournament. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tournament_id_or_slug` | integer/string | Yes | Tournament ID or slug |
| `player_id_or_slug` | integer/string | Yes | Player ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "kills": 200,
  "deaths": 150,
  "assists": 80,
  "adr": 85.2,
  "kast": 72.5,
  "headshots": 60,
  "k_d_diff": 50,
  "first_kills_diff": 10,
  "flash_assists": 15,
  "rating": 1.15,
  "player": { "id": 1, "name": "...", "slug": "..." }
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/tournaments/1/players/1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Team Stats

### 16. GET /csgo/teams/{team_id_or_slug}/stats
**Description:** Get detailed statistics of a given Counter-Strike team. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/teams/{team_id_or_slug}/stats`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `team_id_or_slug` | integer/string | Yes | Team ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "team": { "id": 1, "name": "...", "acronym": "..." },
  "kills": 500,
  "deaths": 400,
  "assists": 200,
  "adr": 82.5,
  "kast": 70.0,
  "headshots": 200,
  "rating": 1.10,
  "... player-level metrics, map info, economy indicators"
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/teams/1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 17. GET /csgo/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get detailed statistics of a given Counter-Strike team for the given serie. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | integer/string | Yes | Serie ID or slug |
| `team_id_or_slug` | integer/string | Yes | Team ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "team": { "id": 1, "name": "...", "acronym": "..." },
  "... performance metrics across games and rounds within the serie"
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/series/1/teams/1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 18. GET /csgo/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get detailed statistics of a given Counter-Strike team for the given tournament. Requires historical or real-time data plan.
**URL:** `https://api.pandascore.co/csgo/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tournament_id_or_slug` | integer/string | Yes | Tournament ID or slug |
| `team_id_or_slug` | integer/string | Yes | Team ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "team": { "id": 1, "name": "...", "acronym": "..." },
  "... performance metrics across games within the tournament"
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/tournaments/1/teams/1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Leagues

### 19. GET /csgo/leagues
**Description:** List Counter-Strike leagues. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/leagues`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `games_count` | integer | No | Number of recent games for statistics |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "ESL Pro League",
    "slug": "esl-pro-league",
    "image_url": "https://...",
    "modified_at": "2024-01-01T00:00:00Z",
    "url": "https://..."
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/leagues" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Series

### 20. GET /csgo/series
**Description:** List series for the Counter-Strike videogame. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/series`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `games_count` | integer | No | Number of recent games for statistics |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "Season 20",
    "slug": "season-20",
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-06-01T00:00:00Z",
    "league_id": 1,
    "... match information, team details, tournament context"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/series" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 21. GET /csgo/series/past
**Description:** List past Counter-Strike series. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/series/past`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |
| `games_count` | integer | No | Number of recent games for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  { "... series objects with match info, team details, dates, tournament context" }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/series/past?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 22. GET /csgo/series/running
**Description:** List running Counter-Strike series. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/series/running`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "...",
    "slug": "...",
    "begin_at": "...",
    "end_at": "...",
    "league_id": 1,
    "... nested opponent/team structures"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/series/running" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 23. GET /csgo/series/upcoming
**Description:** List upcoming Counter-Strike series. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/series/upcoming`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |
| `games_count` | integer | No | Number of recent games for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  { "... series objects with competition data, team info, scheduling, tournament/league metadata" }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/series/upcoming?per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Tournaments

### 24. GET /csgo/tournaments
**Description:** List tournaments for the Counter-Strike videogame. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/tournaments`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "Tournament Name",
    "slug": "tournament-name",
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-01-15T00:00:00Z",
    "country": "US",
    "region": "NA",
    "tier": "s",
    "prizepool": "$1,000,000",
    "league": { "... league object" },
    "serie": { "... serie object" },
    "winner": { "id": 1, "name": "..." },
    "has_bracket": true
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/tournaments" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 25. GET /csgo/tournaments/past
**Description:** List past Counter-Strike tournaments. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/tournaments/past`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |
| `games_count` | integer | No | Number of recent games for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "...",
    "slug": "...",
    "begin_at": "...",
    "end_at": "...",
    "prizepool": "...",
    "tier": "...",
    "winner": { "..." },
    "has_bracket": true,
    "league": { "..." },
    "serie": { "..." }
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/tournaments/past?per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 26. GET /csgo/tournaments/running
**Description:** List running Counter-Strike tournaments. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/tournaments/running`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "... tournament objects with metadata, brackets, matches, rosters, standings, team info"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/tournaments/running?per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 27. GET /csgo/tournaments/upcoming
**Description:** List upcoming Counter-Strike tournaments. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/tournaments/upcoming`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "...",
    "slug": "...",
    "begin_at": "...",
    "country": "...",
    "region": "...",
    "tier": "...",
    "prizepool": "...",
    "league": { "..." },
    "serie": { "..." },
    "winner": null,
    "has_bracket": false
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/tournaments/upcoming?per_page=50&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Players

### 28. GET /csgo/players
**Description:** List players for the Counter-Strike videogame. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/players`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `games_count` | integer | No | Number of recent games for statistics |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "s1mple",
    "slug": "s1mple",
    "age": 26,
    "birthday": "1997-10-02",
    "nationality": "UA",
    "active": true,
    "image_url": "https://...",
    "role": "awper"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/players?per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Teams

### 29. GET /csgo/teams
**Description:** List teams for the Counter-Strike videogame. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/teams`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `games_count` | integer | No | Number of recent games for statistics |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "Natus Vincere",
    "acronym": "NAVI",
    "slug": "natus-vincere",
    "image_url": "https://...",
    "dark_mode_image_url": "https://...",
    "location": "UA",
    "modified_at": "2024-01-01T00:00:00Z"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/teams?per_page=50&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Maps

### 30. GET /csgo/maps
**Description:** List Counter-Strike maps. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/maps`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |
| `games_count` | integer | No | Number of recent games for statistics |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "Dust2",
    "slug": "dust2",
    "image_url": "https://..."
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/maps" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 31. GET /csgo/maps/{csgo_map_id}
**Description:** Get a single Counter-Strike map by ID or slug. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/maps/{csgo_map_id}`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `csgo_map_id` | integer/string | Yes | Map ID (min: 1) or slug |

**Query Parameters:** None

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "id": 1,
  "name": "Dust2",
  "slug": "dust2",
  "image_url": "https://..."
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/maps/dust2" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Weapons

### 32. GET /csgo/weapons
**Description:** List Counter-Strike weapons. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/weapons`

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination (default: 1) |
| `per_page` | integer | No | Results per page (default: 50, max: 100) |
| `games_count` | integer | No | Number of recent games for statistics |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_title` | integer/string | No | Videogame title ID or slug |

**Response Codes:** 200 OK

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "AK-47",
    "slug": "ak-47",
    "image_url": "https://..."
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/weapons?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 33. GET /csgo/weapons/{csgo_weapon_id_or_slug}
**Description:** Get a single Counter-Strike weapon by ID or slug. Available to all customers.
**URL:** `https://api.pandascore.co/csgo/weapons/{csgo_weapon_id_or_slug}`

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `csgo_weapon_id_or_slug` | integer/string | Yes | Weapon ID (min: 1) or slug |

**Query Parameters:** None

**Response Codes:** 200 OK

**Response Schema:**
```json
{
  "id": 1,
  "name": "AK-47",
  "slug": "ak-47",
  "image_url": "https://..."
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/csgo/weapons/ak-47" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Endpoint Summary Table

| # | Method | Endpoint | Access Level |
|---|--------|----------|--------------|
| 1 | GET | `/csgo/games/{csgo_game_id}` | Historical/Real-time |
| 2 | GET | `/csgo/games/{csgo_game_id}/events` | Real-time Pro |
| 3 | GET | `/csgo/games/{csgo_game_id}/rounds` | Real-time |
| 4 | GET | `/csgo/matches/{match_id_or_slug}/games` | Historical/Real-time |
| 5 | GET | `/csgo/matches` | All |
| 6 | GET | `/csgo/matches/past` | All |
| 7 | GET | `/csgo/matches/running` | All |
| 8 | GET | `/csgo/matches/upcoming` | All |
| 9 | GET | `/csgo/matches/{match_id_or_slug}` | Historical/Real-time |
| 10 | GET | `/csgo/matches/{match_id_or_slug}/players/stats` | Historical/Real-time |
| 11 | GET | `/csgo/matches/{match_id_or_slug}/players/{player_id_or_slug}/stats` | Historical/Real-time |
| 12 | GET | `/csgo/matches/{match_id_or_slug}/teams/{team_id_or_slug}/stats` | Historical/Real-time |
| 13 | GET | `/csgo/players/{player_id_or_slug}/stats` | Historical/Real-time |
| 14 | GET | `/csgo/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats` | Historical/Real-time |
| 15 | GET | `/csgo/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats` | Historical/Real-time |
| 16 | GET | `/csgo/teams/{team_id_or_slug}/stats` | Historical/Real-time |
| 17 | GET | `/csgo/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats` | Historical/Real-time |
| 18 | GET | `/csgo/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats` | Historical/Real-time |
| 19 | GET | `/csgo/leagues` | All |
| 20 | GET | `/csgo/series` | All |
| 21 | GET | `/csgo/series/past` | All |
| 22 | GET | `/csgo/series/running` | All |
| 23 | GET | `/csgo/series/upcoming` | All |
| 24 | GET | `/csgo/tournaments` | All |
| 25 | GET | `/csgo/tournaments/past` | All |
| 26 | GET | `/csgo/tournaments/running` | All |
| 27 | GET | `/csgo/tournaments/upcoming` | All |
| 28 | GET | `/csgo/players` | All |
| 29 | GET | `/csgo/teams` | All |
| 30 | GET | `/csgo/maps` | All |
| 31 | GET | `/csgo/maps/{csgo_map_id}` | All |
| 32 | GET | `/csgo/weapons` | All |
| 33 | GET | `/csgo/weapons/{csgo_weapon_id_or_slug}` | All |
