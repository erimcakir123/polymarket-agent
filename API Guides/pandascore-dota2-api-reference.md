# PandaScore Dota 2 API Reference

**Base URL:** `https://api.pandascore.co`
**Authentication:** Bearer token (`Authorization: Bearer YOUR_TOKEN`)
**Content-Type:** `application/json`

---

## Table of Contents

1. [Abilities](#1-abilities)
2. [Games](#2-games)
3. [Heroes](#3-heroes)
4. [Items](#4-items)
5. [Leagues](#5-leagues)
6. [Matches](#6-matches)
7. [Players](#7-players)
8. [Series](#8-series)
9. [Teams](#9-teams)
10. [Tournaments](#10-tournaments)
11. [Stats Endpoints](#11-stats-endpoints)

---

## Common Query Parameters

Most list endpoints share these query parameters:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination: `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | No | Equivalent to `page[size]`. Default: 50, Max: 100, Min: 1 |
| `from` | string (date) | No | Filter start date. Format: `YYYY-MM-DD` |
| `to` | string (date) | No | Filter end date. Format: `YYYY-MM-DD` |
| `side` | string (enum) | No | Filter by faction: `radiant` or `dire` |
| `games_count` | integer | No | Number of recent games used for statistics (e.g. `?games_count=5`) |

---

## Common Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 401 | Unauthorized (invalid/missing token) |
| 404 | Resource not found |

---

## 1. Abilities

### 1.1 GET /dota2/abilities
**Description:** List all Dota 2 abilities.
**URL:** `https://api.pandascore.co/dota2/abilities`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 123,
    "name": "string",
    "image_url": "string | null",
    "level": 1,
    "localized_name": "string | null"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/abilities?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 1.2 GET /dota2/abilities/{dota2_ability_id_or_slug}
**Description:** Get a single ability by ID or by slug.
**URL:** `https://api.pandascore.co/dota2/abilities/{dota2_ability_id_or_slug}`
**Access:** Available to all customers.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dota2_ability_id_or_slug` | string | Yes | Ability ID (numeric) or slug name |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
{
  "id": 123,
  "name": "string",
  "image_url": "string | null",
  "level": 1,
  "localized_name": "string | null"
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/abilities/blink-strike" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 2. Games

### 2.1 GET /dota2/games/{dota2_game_id}
**Description:** Get a single Dota 2 game by ID.
**URL:** `https://api.pandascore.co/dota2/games/{dota2_game_id}`
**Access:** Historical or real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dota2_game_id` | string | Yes | Unique game identifier |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
{
  "id": 123,
  "match_id": 456,
  "begin_at": "2024-01-01T00:00:00Z",
  "end_at": "2024-01-01T01:00:00Z",
  "length": 2400,
  "complete": true,
  "finished": true,
  "forfeit": false,
  "detailed_stats": true,
  "first_blood": {},
  "players": [
    {
      "player": { "id": 1, "name": "string", "nationality": "string", "role": "string" },
      "hero": { "id": 1, "name": "string", "localized_name": "string", "image_url": "string" },
      "team": { "id": 1, "name": "string", "acronym": "string", "location": "string", "image_url": "string" },
      "faction": "radiant",
      "kills": 10,
      "deaths": 3,
      "assists": 15,
      "gold_per_min": 450,
      "xp_per_min": 500,
      "last_hits": 200,
      "denies": 10,
      "gold_spent": 15000,
      "net_worth": 20000,
      "hero_damage": 25000,
      "tower_damage": 3000,
      "tower_kills": 2,
      "hero_level": 25,
      "camps_stacked": 5,
      "creeps_stacked": 3,
      "observer_wards_purchased": 4,
      "observer_used": 4,
      "observer_wards_destroyed": 2,
      "sentry_wards_purchased": 6,
      "sentry_used": 6,
      "sentry_wards_destroyed": 1,
      "heal": 500,
      "damage_taken": 18000,
      "items": [
        { "id": 1, "name": "string", "image_url": "string" }
      ],
      "abilities": [
        { "id": 1, "name": "string", "level": 1, "image_url": "string" }
      ]
    }
  ]
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/games/12345" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2.2 GET /dota2/games/{dota2_game_id}/frames
**Description:** List frames for a given Dota 2 game. Returns time-series snapshots of game state.
**URL:** `https://api.pandascore.co/dota2/games/{dota2_game_id}/frames`
**Access:** Real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dota2_game_id` | string | Yes | Unique game identifier |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination. Default: 1, Min: 1 |
| `per_page` | integer | No | Results per page. Default: 50, Max: 100, Min: 1 |

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "game_id": 123,
    "timestamp": "2024-01-01T00:10:00Z",
    "players": [
      {
        "player": { "id": 1, "name": "string" },
        "hero": { "id": 1, "name": "string", "localized_name": "string", "image_url": "string" },
        "team": { "id": 1, "name": "string" },
        "abilities": [ { "id": 1, "name": "string", "level": 1, "image_url": "string" } ],
        "items": [ { "id": 1, "name": "string", "image_url": "string" } ],
        "kills": 5,
        "deaths": 2,
        "assists": 8,
        "gold_per_min": 400,
        "xp_per_min": 450
      }
    ]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/games/12345/frames?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2.3 GET /dota2/matches/{match_id_or_slug}/games
**Description:** List games for a given Dota 2 match.
**URL:** `https://api.pandascore.co/dota2/matches/{match_id_or_slug}/games`
**Access:** Historical or real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | string | Yes | Match ID (numeric) or URL slug |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 123,
    "match_id": 456,
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-01-01T01:00:00Z",
    "length": 2400,
    "complete": true,
    "finished": true,
    "forfeit": false,
    "detailed_stats": true,
    "first_blood": null,
    "players": [
      {
        "player": { "id": 1, "name": "string", "nationality": "string", "role": "string" },
        "hero": { "id": 1, "name": "string", "localized_name": "string", "image_url": "string" },
        "team": { "id": 1, "name": "string", "acronym": "string", "location": "string" },
        "faction": "radiant",
        "kills": 10,
        "deaths": 3,
        "assists": 15,
        "gold_per_min": 450,
        "xp_per_min": 500,
        "last_hits": 200,
        "denies": 10,
        "gold_spent": 15000,
        "hero_damage": 25000,
        "tower_damage": 3000,
        "items": [ { "id": 1, "name": "string" } ],
        "abilities": [ { "id": 1, "name": "string", "level": 1 } ]
      }
    ]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/matches/12345/games" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2.4 GET /dota2/teams/{team_id_or_slug}/games
**Description:** List finished games for a given Dota 2 team.
**URL:** `https://api.pandascore.co/dota2/teams/{team_id_or_slug}/games`
**Access:** Historical or real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `team_id_or_slug` | string | Yes | Team ID (numeric) or slug |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 123,
    "game_id": 789,
    "match_id": 456,
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-01-01T01:00:00Z",
    "length": 2400,
    "finished": true,
    "complete": true,
    "forfeit": false,
    "first_blood": null,
    "detailed_stats": true,
    "players": [
      {
        "player": { "id": 1, "name": "string", "age": 25, "birthday": "1999-01-01", "nationality": "string", "role": "string", "image_url": "string" },
        "hero": { "id": 1, "name": "string", "localized_name": "string", "image_url": "string" },
        "team": { "id": 1, "name": "string", "acronym": "string", "location": "string", "image_url": "string" },
        "opponent": { "id": 2, "name": "string", "acronym": "string", "location": "string", "image_url": "string" },
        "faction": "radiant",
        "kills": 10,
        "deaths": 3,
        "assists": 15,
        "gold_per_min": 450,
        "xp_per_min": 500,
        "last_hits": 200,
        "denies": 10,
        "gold_spent": 15000,
        "net_worth": 20000,
        "hero_damage": 25000,
        "hero_level": 25,
        "tower_damage": 3000,
        "tower_kills": 2,
        "camps_stacked": 5,
        "creeps_stacked": 3,
        "heal": 500,
        "damage_taken": 18000,
        "observer_used": 4,
        "observer_wards_purchased": 4,
        "observer_wards_destroyed": 2,
        "sentry_used": 6,
        "sentry_wards_purchased": 6,
        "sentry_wards_destroyed": 1,
        "items": [ { "id": 1, "name": "string", "image_url": "string" } ],
        "abilities": [ { "id": 1, "name": "string", "level": 1, "image_url": "string" } ]
      }
    ]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/teams/1647/games?page[size]=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 3. Heroes

### 3.1 GET /dota2/heroes
**Description:** List all Dota 2 heroes.
**URL:** `https://api.pandascore.co/dota2/heroes`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "earth_spirit",
    "localized_name": "Earth Spirit",
    "image_url": "https://..."
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/heroes" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 3.2 GET /dota2/heroes/{dota2_hero_id_or_slug}
**Description:** Get a single hero by ID or by slug.
**URL:** `https://api.pandascore.co/dota2/heroes/{dota2_hero_id_or_slug}`
**Access:** Available to all customers.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dota2_hero_id_or_slug` | string | Yes | Hero ID (numeric) or slug name |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
{
  "id": 1,
  "name": "earth_spirit",
  "localized_name": "Earth Spirit",
  "image_url": "https://...",
  "abilities": [
    { "id": 1, "name": "string", "level": 1, "image_url": "string" }
  ]
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/heroes/earth-spirit" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 4. Items

### 4.1 GET /dota2/items
**Description:** List all Dota 2 items.
**URL:** `https://api.pandascore.co/dota2/items`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "blink",
    "localized_name": "Blink Dagger",
    "image_url": "https://..."
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/items?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 4.2 GET /dota2/items/{dota2_item_id_or_slug}
**Description:** Get a single item by ID or by slug.
**URL:** `https://api.pandascore.co/dota2/items/{dota2_item_id_or_slug}`
**Access:** Available to all customers.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dota2_item_id_or_slug` | string | Yes | Item ID (numeric) or slug name |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Results per page. Default: 50, Max: 100 |

**Response Codes:** 200

**Response Schema:**
```json
{
  "id": 1,
  "name": "blink",
  "image_url": "https://...",
  "localized_name": "Blink Dagger"
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/items/blink" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 5. Leagues

### 5.1 GET /dota2/leagues
**Description:** List Dota 2 leagues.
**URL:** `https://api.pandascore.co/dota2/leagues`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination. Default: 1, Min: 1 |
| `per_page` | integer | No | Results per page. Default: 50, Max: 100 |

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "string",
    "slug": "string",
    "url": "string",
    "image_url": "string | null",
    "modified_at": "2024-01-01T00:00:00Z"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/leagues" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 6. Matches

### 6.1 GET /dota2/matches
**Description:** List matches for the Dota 2 videogame.
**URL:** `https://api.pandascore.co/dota2/matches`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 123,
    "match_id": 456,
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-01-01T01:00:00Z",
    "length": 2400,
    "complete": true,
    "finished": true,
    "forfeit": false,
    "detailed_stats": true,
    "first_blood": null,
    "players": [
      {
        "faction": "radiant",
        "kills": 10,
        "deaths": 3,
        "assists": 15,
        "hero": { "id": 1, "name": "string", "localized_name": "string", "image_url": "string" },
        "player": { "id": 1, "name": "string" },
        "team": { "id": 1, "name": "string" },
        "items": [],
        "abilities": []
      }
    ]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/matches?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 6.2 GET /dota2/matches/past
**Description:** List past Dota 2 matches.
**URL:** `https://api.pandascore.co/dota2/matches/past`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:** Same as [GET /dota2/matches](#61-get-dota2matches)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/matches/past?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 6.3 GET /dota2/matches/running
**Description:** List running Dota 2 matches (currently live).
**URL:** `https://api.pandascore.co/dota2/matches/running`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:** Same as [GET /dota2/matches](#61-get-dota2matches)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/matches/running" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 6.4 GET /dota2/matches/upcoming
**Description:** List upcoming Dota 2 matches.
**URL:** `https://api.pandascore.co/dota2/matches/upcoming`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:** Same as [GET /dota2/matches](#61-get-dota2matches)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/matches/upcoming?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 6.5 GET /dota2/matches/{match_id_or_slug}/players/stats
**Description:** Get detailed player statistics for a given Dota 2 match.
**URL:** `https://api.pandascore.co/dota2/matches/{match_id_or_slug}/players/stats`
**Access:** Historical or real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | string | Yes | Match ID (numeric) or slug |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "player": { "id": 1, "name": "string", "nationality": "string", "role": "string" },
    "hero": { "id": 1, "name": "string", "image_url": "string" },
    "team": { "id": 1, "name": "string" },
    "faction": "radiant",
    "kills": 10,
    "deaths": 3,
    "assists": 15,
    "gold_per_min": 450,
    "xp_per_min": 500,
    "last_hits": 200,
    "denies": 10,
    "net_worth": 20000,
    "hero_damage": 25000,
    "hero_damage_percentage": 30.5,
    "tower_damage": 3000,
    "tower_kills": 2,
    "items": [ { "id": 1, "name": "string", "image_url": "string" } ],
    "abilities": [ { "id": 1, "name": "string", "level": 1 } ]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/matches/12345/players/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 7. Players

### 7.1 GET /dota2/players
**Description:** List players for the Dota 2 videogame.
**URL:** `https://api.pandascore.co/dota2/players`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "string",
    "slug": "string",
    "first_name": "string",
    "last_name": "string",
    "nationality": "string",
    "role": "string",
    "age": 25,
    "birthday": "1999-01-01",
    "image_url": "string | null",
    "current_team": { "id": 1, "name": "string", "acronym": "string", "image_url": "string" },
    "active": true,
    "modified_at": "2024-01-01T00:00:00Z"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/players?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 7.2 GET /dota2/players/{player_id_or_slug}/stats
**Description:** Get detailed statistics of a given Dota 2 player.
**URL:** `https://api.pandascore.co/dota2/players/{player_id_or_slug}/stats`
**Access:** Historical or real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `player_id_or_slug` | string | Yes | Player ID (numeric) or slug |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "player": { "id": 1, "name": "string", "nationality": "string", "role": "string", "active": true },
    "hero": { "id": 1, "name": "string", "localized_name": "string", "image_url": "string" },
    "team": { "id": 1, "name": "string" },
    "opponent": { "id": 2, "name": "string" },
    "faction": "radiant",
    "kills": 10,
    "deaths": 3,
    "assists": 15,
    "gold_per_min": 450,
    "xp_per_min": 500,
    "last_hits": 200,
    "denies": 10,
    "net_worth": 20000,
    "gold_spent": 15000,
    "hero_damage": 25000,
    "tower_damage": 3000,
    "heal": 500,
    "camps_stacked": 5,
    "creeps_stacked": 3,
    "observer_wards_purchased": 4,
    "sentry_wards_purchased": 6,
    "items": [ { "id": 1, "name": "string", "image_url": "string" } ],
    "abilities": [ { "id": 1, "name": "string", "level": 1, "image_url": "string" } ]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/players/miracle/stats?games_count=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 8. Series

### 8.1 GET /dota2/series
**Description:** List series for the Dota 2 videogame.
**URL:** `https://api.pandascore.co/dota2/series`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination. Default: 1, Min: 1 |
| `per_page` | integer | No | Results per page. Default: 50, Max: 100 |
| `from` | string (date) | No | Filter start date. Format: `YYYY-MM-DD` |
| `to` | string (date) | No | Filter end date. Format: `YYYY-MM-DD` |

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "string",
    "slug": "string",
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-06-01T00:00:00Z",
    "league_id": 1,
    "league": { "id": 1, "name": "string", "slug": "string", "image_url": "string" },
    "full_name": "string",
    "season": "string",
    "year": 2024,
    "modified_at": "2024-01-01T00:00:00Z",
    "tournaments": []
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/series?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 8.2 GET /dota2/series/past
**Description:** List past Dota 2 series.
**URL:** `https://api.pandascore.co/dota2/series/past`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:** Same as [GET /dota2/series](#81-get-dota2series)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/series/past?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 8.3 GET /dota2/series/running
**Description:** List running Dota 2 series.
**URL:** `https://api.pandascore.co/dota2/series/running`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination. Default: 1, Min: 1 |
| `per_page` | integer | No | Results per page. Default: 50, Max: 100 |
| `from` | string (date) | No | Filter start date. Format: `YYYY-MM-DD` |
| `to` | string (date) | No | Filter end date. Format: `YYYY-MM-DD` |

**Response Codes:** 200

**Response Schema:** Same as [GET /dota2/series](#81-get-dota2series)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/series/running" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 8.4 GET /dota2/series/upcoming
**Description:** List upcoming Dota 2 series.
**URL:** `https://api.pandascore.co/dota2/series/upcoming`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:** Same as [GET /dota2/series](#81-get-dota2series)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/series/upcoming" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 8.5 GET /dota2/series/{serie_id_or_slug}/teams
**Description:** List teams for the Dota 2 videogame for a given serie.
**URL:** `https://api.pandascore.co/dota2/series/{serie_id_or_slug}/teams`
**Access:** Available to all customers.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | string | Yes | Series ID (numeric) or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Results per page. Default: 50, Max: 100 |

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "string",
    "slug": "string",
    "acronym": "string",
    "image_url": "string | null",
    "location": "string",
    "modified_at": "2024-01-01T00:00:00Z"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/series/1234/teams" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 9. Teams

### 9.1 GET /dota2/teams
**Description:** List teams for the Dota 2 videogame.
**URL:** `https://api.pandascore.co/dota2/teams`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "string",
    "slug": "string",
    "acronym": "string",
    "image_url": "string | null",
    "location": "string",
    "modified_at": "2024-01-01T00:00:00Z",
    "players": [
      { "id": 1, "name": "string", "role": "string", "age": 25, "nationality": "string", "image_url": "string" }
    ]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/teams?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 9.2 GET /dota2/teams/{team_id_or_slug}/stats
**Description:** Get detailed statistics of a given Dota 2 team.
**URL:** `https://api.pandascore.co/dota2/teams/{team_id_or_slug}/stats`
**Access:** Historical or real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `team_id_or_slug` | string | Yes | Team ID (numeric) or slug |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-01-01T01:00:00Z",
    "length": 2400,
    "match_id": 456,
    "game_id": 789,
    "players": [
      {
        "hero": { "id": 1, "name": "string" },
        "kills": 10,
        "deaths": 3,
        "assists": 15,
        "gold_per_min": 450,
        "gold_spent": 15000,
        "gold_remaining": 5000,
        "last_hits": 200,
        "denies": 10,
        "net_worth": 20000,
        "hero_damage": 25000,
        "items": [],
        "abilities": [],
        "observer_wards_purchased": 4,
        "sentry_wards_purchased": 6
      }
    ]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/teams/team-spirit/stats?games_count=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 10. Tournaments

### 10.1 GET /dota2/tournaments
**Description:** List tournaments for the Dota 2 videogame.
**URL:** `https://api.pandascore.co/dota2/tournaments`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination. Default: 1, Min: 1 |
| `per_page` | integer | No | Results per page. Default: 50, Max: 100 |
| `from` | string (date) | No | Filter start date. Format: `YYYY-MM-DD` |
| `to` | string (date) | No | Filter end date. Format: `YYYY-MM-DD` |

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 1,
    "name": "string",
    "slug": "string",
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-06-01T00:00:00Z",
    "serie_id": 1,
    "league_id": 1,
    "league": { "id": 1, "name": "string" },
    "serie": { "id": 1, "name": "string" },
    "modified_at": "2024-01-01T00:00:00Z",
    "prizepool": "string | null",
    "teams": [],
    "matches": []
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/tournaments" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 10.2 GET /dota2/tournaments/past
**Description:** List past Dota 2 tournaments.
**URL:** `https://api.pandascore.co/dota2/tournaments/past`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Results per page. Default: 50, Max: 100 |
| `from` | string (date) | No | Filter start date. Format: `YYYY-MM-DD` |
| `to` | string (date) | No | Filter end date. Format: `YYYY-MM-DD` |

**Response Codes:** 200

**Response Schema:** Same as [GET /dota2/tournaments](#101-get-dota2tournaments)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/tournaments/past?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 10.3 GET /dota2/tournaments/running
**Description:** List running Dota 2 tournaments.
**URL:** `https://api.pandascore.co/dota2/tournaments/running`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Results per page. Default: 50, Max: 100 |

**Response Codes:** 200

**Response Schema:** Same as [GET /dota2/tournaments](#101-get-dota2tournaments)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/tournaments/running" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 10.4 GET /dota2/tournaments/upcoming
**Description:** List upcoming Dota 2 tournaments.
**URL:** `https://api.pandascore.co/dota2/tournaments/upcoming`
**Access:** Available to all customers.

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Results per page. Default: 50, Max: 100 |

**Response Codes:** 200

**Response Schema:** Same as [GET /dota2/tournaments](#101-get-dota2tournaments)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/tournaments/upcoming" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 11. Stats Endpoints

### 11.1 GET /dota2/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats
**Description:** Get detailed statistics of a given Dota 2 player for a given serie.
**URL:** `https://api.pandascore.co/dota2/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats`
**Access:** Historical or real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | string | Yes | Series ID (numeric) or slug |
| `player_id_or_slug` | string | Yes | Player ID (numeric) or slug |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "player": { "id": 1, "name": "string", "nationality": "string", "role": "string" },
    "hero": { "id": 1, "name": "string", "localized_name": "string", "image_url": "string" },
    "team": { "id": 1, "name": "string" },
    "opponent": { "id": 2, "name": "string" },
    "faction": "radiant",
    "kills": 10,
    "deaths": 3,
    "assists": 15,
    "gold_per_min": 450,
    "xp_per_min": 500,
    "last_hits": 200,
    "denies": 10,
    "net_worth": 20000,
    "hero_damage": 25000,
    "tower_damage": 3000,
    "items": [],
    "abilities": []
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/series/1234/players/miracle/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 11.2 GET /dota2/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get detailed statistics of a given Dota 2 team for a given serie.
**URL:** `https://api.pandascore.co/dota2/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats`
**Access:** Historical or real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | string | Yes | Series ID (numeric) or slug |
| `team_id_or_slug` | string | Yes | Team ID (numeric) or slug |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:** Same structure as [GET /dota2/teams/{team_id_or_slug}/stats](#92-get-dota2teamsteam_id_or_slugstats) but scoped to the given serie.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/series/1234/teams/team-spirit/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 11.3 GET /dota2/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats
**Description:** Get detailed statistics of a given Dota 2 player for a given tournament.
**URL:** `https://api.pandascore.co/dota2/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats`
**Access:** Historical or real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tournament_id_or_slug` | string | Yes | Tournament ID (numeric) or slug |
| `player_id_or_slug` | string | Yes | Player ID (numeric) or slug |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:**
```json
[
  {
    "id": 123,
    "match_id": 456,
    "game_id": 789,
    "begin_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-01-01T01:00:00Z",
    "length": 2400,
    "complete": true,
    "finished": true,
    "forfeit": false,
    "player": { "id": 1, "name": "string", "nationality": "string", "role": "string" },
    "hero": { "id": 1, "name": "string", "image_url": "string" },
    "team": { "id": 1, "name": "string", "acronym": "string", "location": "string" },
    "opponent": { "id": 2, "name": "string" },
    "faction": "radiant",
    "role": 1,
    "kills": 10,
    "deaths": 3,
    "assists": 15,
    "gold_per_min": 450,
    "xp_per_min": 500,
    "last_hits": 200,
    "denies": 10,
    "net_worth": 20000,
    "gold_spent": 15000,
    "gold_remaining": 5000,
    "hero_damage": 25000,
    "hero_damage_percentage": 30.5,
    "tower_damage": 3000,
    "tower_kills": 2,
    "camps_stacked": 5,
    "creeps_stacked": 3,
    "observer_wards_purchased": 4,
    "sentry_wards_purchased": 6,
    "items": [ { "id": 1, "name": "string", "image_url": "string" } ],
    "abilities": [ { "id": 1, "name": "string", "level": 1, "image_url": "string" } ]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/tournaments/the-international-2024/players/miracle/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 11.4 GET /dota2/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get detailed statistics of a given Dota 2 team for a given tournament.
**URL:** `https://api.pandascore.co/dota2/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats`
**Access:** Historical or real-time data plan required.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tournament_id_or_slug` | string | Yes | Tournament ID (numeric) or slug |
| `team_id_or_slug` | string | Yes | Team ID (numeric) or slug |

**Query Parameters:** [Common Query Parameters](#common-query-parameters)

**Response Codes:** 200

**Response Schema:** Same structure as [GET /dota2/teams/{team_id_or_slug}/stats](#92-get-dota2teamsteam_id_or_slugstats) but scoped to the given tournament.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/dota2/tournaments/the-international-2024/teams/team-spirit/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Endpoint Summary Table

| # | Method | Endpoint | Access |
|---|--------|----------|--------|
| 1 | GET | `/dota2/abilities` | All |
| 2 | GET | `/dota2/abilities/{id_or_slug}` | All |
| 3 | GET | `/dota2/games/{game_id}` | Historical/RT |
| 4 | GET | `/dota2/games/{game_id}/frames` | RT only |
| 5 | GET | `/dota2/matches/{id_or_slug}/games` | Historical/RT |
| 6 | GET | `/dota2/teams/{id_or_slug}/games` | Historical/RT |
| 7 | GET | `/dota2/heroes` | All |
| 8 | GET | `/dota2/heroes/{id_or_slug}` | All |
| 9 | GET | `/dota2/items` | All |
| 10 | GET | `/dota2/items/{id_or_slug}` | All |
| 11 | GET | `/dota2/leagues` | All |
| 12 | GET | `/dota2/matches` | All |
| 13 | GET | `/dota2/matches/past` | All |
| 14 | GET | `/dota2/matches/running` | All |
| 15 | GET | `/dota2/matches/upcoming` | All |
| 16 | GET | `/dota2/matches/{id_or_slug}/players/stats` | Historical/RT |
| 17 | GET | `/dota2/players/{id_or_slug}/stats` | Historical/RT |
| 18 | GET | `/dota2/series/{id_or_slug}/players/{id_or_slug}/stats` | Historical/RT |
| 19 | GET | `/dota2/series/{id_or_slug}/teams/{id_or_slug}/stats` | Historical/RT |
| 20 | GET | `/dota2/teams/{id_or_slug}/stats` | Historical/RT |
| 21 | GET | `/dota2/tournaments/{id_or_slug}/players/{id_or_slug}/stats` | Historical/RT |
| 22 | GET | `/dota2/tournaments/{id_or_slug}/teams/{id_or_slug}/stats` | Historical/RT |
| 23 | GET | `/dota2/players` | All |
| 24 | GET | `/dota2/series` | All |
| 25 | GET | `/dota2/series/past` | All |
| 26 | GET | `/dota2/series/running` | All |
| 27 | GET | `/dota2/series/upcoming` | All |
| 28 | GET | `/dota2/series/{id_or_slug}/teams` | All |
| 29 | GET | `/dota2/teams` | All |
| 30 | GET | `/dota2/tournaments` | All |
| 31 | GET | `/dota2/tournaments/past` | All |
| 32 | GET | `/dota2/tournaments/running` | All |
| 33 | GET | `/dota2/tournaments/upcoming` | All |

---

## Access Level Legend

| Label | Description |
|-------|-------------|
| **All** | Available to all customers |
| **Historical/RT** | Requires historical or real-time data plan |
| **RT only** | Requires real-time data plan |
