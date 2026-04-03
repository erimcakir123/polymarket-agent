# PandaScore Valorant API Reference

**Base URL:** `https://api.pandascore.co`
**Authentication:** Bearer token in `Authorization` header
**Total Endpoints:** 39

---

## Table of Contents

1. [Abilities](#1-abilities)
2. [Agents](#2-agents)
3. [Games](#3-games)
4. [Matches](#4-matches)
5. [Match Stats](#5-match-stats)
6. [Leagues](#6-leagues)
7. [Maps](#7-maps)
8. [Players](#8-players)
9. [Player Stats](#9-player-stats)
10. [Series](#10-series)
11. [Series Stats](#11-series-stats)
12. [Teams](#12-teams)
13. [Team Stats](#13-team-stats)
14. [Tournaments](#14-tournaments)
15. [Tournament Stats](#15-tournament-stats)
16. [Weapons](#16-weapons)

---

## Common Parameters

These query parameters appear on most list endpoints:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination: `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | No | Equivalent to `page[size]`. Default: 50, Max: 100, Min: 1 |
| `from` | date (YYYY-MM-DD) | No | Filter results from this date |
| `to` | date (YYYY-MM-DD) | No | Filter results up to this date |
| `videogame_version` | string | No | `latest`, `all`, or specific version (e.g. `6.03`) |
| `games_count` | integer | No | Number of recent games used for statistics |

## Common Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
| 422 | Unprocessable Entity |

---

## 1. Abilities

### 1.1 GET /valorant/abilities
**Description:** List all Valorant abilities
**URL:** `https://api.pandascore.co/valorant/abilities`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |

**Response Schema:**
```json
[
  {
    "id": 402,                    // integer, min: 1
    "name": "NULL/cmd",           // string
    "ability_type": "ultimate_ability",  // enum: ability_one, ability_two, grenade_ability, ultimate_ability (nullable)
    "creds": null,                // number, min: 0 (nullable)
    "image_url": "https://cdn.pandascore.co/images/valorant/ability/image/402/null-cmd-png",  // URI (nullable)
    "videogame_versions": ["6.03"]  // string[]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/abilities?page[size]=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 1.2 GET /valorant/abilities/{valorant_ability_id}
**Description:** Get a single Valorant ability by ID
**URL:** `https://api.pandascore.co/valorant/abilities/{valorant_ability_id}`
**Access:** All customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `valorant_ability_id` | integer | Yes | ID of the ability (min: 1) |

**Query Parameters:** None

**Response Schema:**
```json
{
  "id": 15,                       // integer, min: 1
  "name": "Toxin",               // string
  "ability_type": null,          // enum: ability_one, ability_two, grenade_ability, ultimate_ability (nullable)
  "creds": null,                 // number, min: 0 (nullable)
  "image_url": null,             // URI string (nullable)
  "videogame_versions": ["6.03", "6.02", "6.01"]  // string[]
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/abilities/15" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 2. Agents

### 2.1 GET /valorant/agents
**Description:** List all Valorant agents
**URL:** `https://api.pandascore.co/valorant/agents`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date (YYYY-MM-DD) |
| `to` | date | No | Filter to date (YYYY-MM-DD) |
| `videogame_version` | string | No | `latest`, `all`, or specific version |

**Response Schema:**
```json
[
  {
    "id": 167,                    // integer, min: 1
    "name": "Fade",              // string
    "portrait_url": "https://cdn.pandascore.co/images/valorant/agent/image/167/fade_icon-png-png",  // URI
    "videogame_versions": ["5.0"]  // string[]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/agents?page[size]=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 2.2 GET /valorant/agents/{valorant_agent_id}
**Description:** Get a single Valorant agent by ID
**URL:** `https://api.pandascore.co/valorant/agents/{valorant_agent_id}`
**Access:** All customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `valorant_agent_id` | integer | Yes | Agent ID (min: 1) |

**Query Parameters:** None

**Response Schema:**
```json
{
  "id": 15,                       // integer, min: 1
  "name": "Astra",              // string
  "portrait_url": "https://cdn.pandascore.co/images/valorant/agent/image/15/Astra_icon.png",  // URI
  "videogame_versions": ["2.04"]  // string[]
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/agents/15" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 2.3 GET /valorant/versions/all/agents [DEPRECATED]
**Description:** List Valorant agents for all versions
**URL:** `https://api.pandascore.co/valorant/versions/all/agents`
**Access:** All customers
**Deprecated:** Use `/valorant/agents?filter[videogame_version]=all` instead

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `videogame_version` | string | No | Version filter |

**Response Schema:**
```json
[
  {
    "id": 167,                    // integer, min: 1
    "name": "Fade",              // string
    "portrait_url": "https://cdn.pandascore.co/...",  // URI
    "videogame_versions": ["5.0"]  // string[]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/versions/all/agents?per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 2.4 GET /valorant/versions/{valorant_version_name}/agents [DEPRECATED]
**Description:** List Valorant agents for a specific version
**URL:** `https://api.pandascore.co/valorant/versions/{valorant_version_name}/agents`
**Access:** All customers
**Deprecated:** Use `/valorant/agents?filter[videogame_version]={version}` instead

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `valorant_version_name` | string | Yes | Specific Valorant version/patch name |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |

**Response Schema:**
```json
[
  {
    "id": 167,                    // integer, min: 1
    "name": "Fade",              // string
    "portrait_url": "https://cdn.pandascore.co/...",  // URI
    "videogame_versions": ["5.0"]  // string[]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/versions/6.03/agents" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 3. Games

### 3.1 GET /valorant/games/{valorant_game_id}
**Description:** Get a single Valorant game by ID
**URL:** `https://api.pandascore.co/valorant/games/{valorant_game_id}`
**Access:** Historical or real-time data plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `valorant_game_id` | integer | Yes | Unique game identifier |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema (ValorantFullRounds):**
```json
[
  {
    "number": 1,                          // integer - round number
    "outcome": "spike_defused",           // string: spike_defused, attackers_eliminated, defenders_eliminated, spike_exploded
    "winner_team": {
      "id": 12345,                        // integer
      "side": "attackers"                 // string: attackers, defenders
    },
    "attackers": {
      "team_id": 12345,                   // integer
      "score": 5,                         // integer
      "players": [
        {
          "id": 100,                      // integer
          "name": "PlayerName",           // string
          "agent": {
            "id": 15,                     // integer
            "name": "Astra",             // string
            "portrait_url": "https://..." // URI
          },
          "kills": 2,                     // integer
          "assists": 1,                   // integer
          "combat_score": 250,            // integer
          "eco_beg_prep": 3900,           // integer
          "eco_end_prep": 1500,           // integer
          "shield_type": "heavy_shield",  // string: no_shield, light_shield, heavy_shield
          "weapon": {
            "id": 10,                     // integer
            "name": "Vandal",            // string
            "image_url": "https://..."   // URI
          }
        }
      ]
    },
    "defenders": {
      // Same structure as attackers
    }
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/games/12345" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 3.2 GET /valorant/games/{valorant_game_id}/events
**Description:** List play-by-play events for a Valorant game
**URL:** `https://api.pandascore.co/valorant/games/{valorant_game_id}/events`
**Access:** Pro historical plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `valorant_game_id` | integer | Yes | Unique game identifier |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Same ValorantFullRounds structure as endpoint 3.1 (rounds with attackers/defenders/players/agents/weapons).

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/games/12345/events?per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 3.3 GET /valorant/games/{valorant_game_id}/rounds
**Description:** List rounds in a Valorant game
**URL:** `https://api.pandascore.co/valorant/games/{valorant_game_id}/rounds`
**Access:** Pro historical plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `valorant_game_id` | integer | Yes | Unique game identifier |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |

**Response Schema:** Same ValorantFullRounds structure as endpoint 3.1.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/games/12345/rounds?per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 3.4 GET /valorant/matches/{match_id_or_slug}/games
**Description:** List games for a given Valorant match
**URL:** `https://api.pandascore.co/valorant/matches/{match_id_or_slug}/games`
**Access:** Historical or real-time data plan customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | string | Yes | Match ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games count for statistics |

**Response Schema:**
```json
[
  {
    "id": 12345,                          // integer
    "number": 1,                          // integer - game number in match
    "outcome": "spike_defused",           // string
    "winner_team": {
      "id": 100,
      "side": "attackers"
    },
    "attackers": { /* team with players array */ },
    "defenders": { /* team with players array */ }
  }
]
```

Each player object within attackers/defenders contains: `id`, `name`, `agent` (id, name, portrait_url), `kills`, `assists`, `combat_score`, `eco_beg_prep`, `eco_end_prep`, `shield_type`, `weapon` (id, name, image_url).

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/matches/12345/games?per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 4. Matches

### 4.1 GET /valorant/matches
**Description:** List all Valorant matches
**URL:** `https://api.pandascore.co/valorant/matches`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of match objects containing match metadata, team info, game data, series/tournament context.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/matches?page[size]=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 4.2 GET /valorant/matches/past
**Description:** List past (completed) Valorant matches
**URL:** `https://api.pandascore.co/valorant/matches/past`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games count for statistics |

**Response Schema:** Array of match objects with nested teams, players, games, rounds, agent selections, weapons, economic data, and combat scores.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/matches/past?page=1&per_page=50&from=2024-01-01&to=2024-12-31" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 4.3 GET /valorant/matches/running
**Description:** List currently running Valorant matches
**URL:** `https://api.pandascore.co/valorant/matches/running`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of match objects. Each match contains:
- `id` (integer), `status` (string)
- `teams` (array of team objects)
- `games` (array with rounds, each round containing attackers/defenders with player arrays)
- Player fields: `id`, `name`, `agent` (id, name, portrait_url), `kills`, `assists`, `combat_score`, `eco_beg_prep`, `eco_end_prep`, `shield_type`, `weapon` (id, name, image_url)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/matches/running?per_page=10&page=1" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 4.4 GET /valorant/matches/upcoming
**Description:** List upcoming (scheduled) Valorant matches
**URL:** `https://api.pandascore.co/valorant/matches/upcoming`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of match objects with teams, scheduling info, tournament details.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/matches/upcoming?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 5. Match Stats

### 5.1 GET /valorant/matches/{match_id_or_slug}/players/stats
**Description:** Get aggregated player statistics for all players in a Valorant match
**URL:** `https://api.pandascore.co/valorant/matches/{match_id_or_slug}/players/stats`
**Access:** Historical or real-time data plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | string | Yes | Match ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Games count for statistics |
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:**
```json
[
  {
    "id": 100,                            // integer
    "name": "PlayerName",                 // string
    "agent": {
      "id": 15,
      "name": "Astra",
      "portrait_url": "https://...",
      "videogame_versions": ["6.03"]
    },
    "kills": 20,                          // integer
    "assists": 5,                         // integer
    "combat_score": 250,                  // integer
    "eco_beg_prep": 3900,                 // integer
    "eco_end_prep": 1500,                 // integer
    "shield_type": "heavy_shield",        // string: no_shield, light_shield, heavy_shield
    "weapon": {
      "id": 10,
      "name": "Vandal",
      "image_url": "https://..."
    }
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/matches/12345/players/stats" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 5.2 GET /valorant/matches/{match_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get aggregated team statistics for a specific team in a Valorant match
**URL:** `https://api.pandascore.co/valorant/matches/{match_id_or_slug}/teams/{team_id_or_slug}/stats`
**Access:** Historical or real-time data plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | string | Yes | Match ID or slug |
| `team_id_or_slug` | string | Yes | Team ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Aggregated team statistics object (team-level performance metrics for the match).

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/matches/12345/teams/67890/stats?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 6. Leagues

### 6.1 GET /valorant/leagues
**Description:** List Valorant leagues
**URL:** `https://api.pandascore.co/valorant/leagues`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of league objects containing competitive Valorant league information.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/leagues?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 7. Maps

### 7.1 GET /valorant/maps
**Description:** List all Valorant maps
**URL:** `https://api.pandascore.co/valorant/maps`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `videogame_version` | string | No | Version filter |

**Response Schema:**
```json
[
  {
    "id": 1,                              // integer
    "name": "Ascent",                     // string
    "image_url": "https://cdn.pandascore.co/...",  // URI
    "videogame_versions": ["1.0", "2.0"]  // string[]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/maps?per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 7.2 GET /valorant/maps/{valorant_map_id}
**Description:** Get a specific Valorant map by ID
**URL:** `https://api.pandascore.co/valorant/maps/{valorant_map_id}`
**Access:** All customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `valorant_map_id` | integer | Yes | Unique map ID |

**Query Parameters:** None

**Response Schema:**
```json
{
  "id": 1,                              // integer
  "name": "Ascent",                     // string
  "image_url": "https://cdn.pandascore.co/...",  // URI
  "videogame_versions": ["1.0"]         // string[]
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/maps/1" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 7.3 GET /valorant/versions/all/maps [DEPRECATED]
**Description:** List Valorant maps for all versions
**URL:** `https://api.pandascore.co/valorant/versions/all/maps`
**Access:** All customers
**Deprecated:** Use `/valorant/maps?filter[videogame_version]=all` instead

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |

**Response Schema:**
```json
[
  {
    "id": 1,                              // integer, min: 1
    "name": "Ascent",                     // string
    "image_url": "https://cdn.pandascore.co/...",  // URI
    "videogame_versions": ["1.0"]         // string[]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/versions/all/maps?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 7.4 GET /valorant/versions/{valorant_version_name}/maps [DEPRECATED]
**Description:** List Valorant maps for a specific version
**URL:** `https://api.pandascore.co/valorant/versions/{valorant_version_name}/maps`
**Access:** All customers
**Deprecated:** Use `/valorant/maps?filter[videogame_version]={version}` instead

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `valorant_version_name` | string | Yes | Specific version/patch name |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |

**Response Schema:**
```json
[
  {
    "id": 1,                              // integer, min: 1
    "name": "Ascent",                     // string
    "image_url": "https://cdn.pandascore.co/...",  // URI
    "videogame_versions": ["6.03"]        // string[]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/versions/6.03/maps" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 8. Players

### 8.1 GET /valorant/players
**Description:** List players for the Valorant videogame
**URL:** `https://api.pandascore.co/valorant/players`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of player objects.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/players?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 9. Player Stats

### 9.1 GET /valorant/players/{player_id_or_slug}/stats
**Description:** Get a Valorant player's stats by ID or slug
**URL:** `https://api.pandascore.co/valorant/players/{player_id_or_slug}/stats`
**Access:** Historical or real-time data plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `player_id_or_slug` | string | Yes | Player ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |

**Response Schema:** Player statistics object with combat metrics, agent data, and performance aggregations.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/players/12345/stats?games_count=5&videogame_version=latest" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 10. Series

### 10.1 GET /valorant/series
**Description:** List series for the Valorant videogame
**URL:** `https://api.pandascore.co/valorant/series`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games count for statistics |

**Response Schema:** Array of series objects.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/series" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 10.2 GET /valorant/series/past
**Description:** List past Valorant series
**URL:** `https://api.pandascore.co/valorant/series/past`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games count for statistics |

**Response Schema:** Array of past series objects with nested team data, match info, game/round statistics.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/series/past?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 10.3 GET /valorant/series/running
**Description:** List running Valorant series
**URL:** `https://api.pandascore.co/valorant/series/running`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games count for statistics |

**Response Schema:** Array of currently active series objects.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/series/running" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 10.4 GET /valorant/series/upcoming
**Description:** List upcoming Valorant series
**URL:** `https://api.pandascore.co/valorant/series/upcoming`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of upcoming series objects.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/series/upcoming?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 11. Series Stats

### 11.1 GET /valorant/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats
**Description:** Get aggregated player statistics for a player within a Valorant series
**URL:** `https://api.pandascore.co/valorant/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats`
**Access:** Historical or real-time data plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | string | Yes | Series ID or slug |
| `player_id_or_slug` | string | Yes | Player ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |

**Response Schema:** Aggregated player performance metrics (kills, assists, deaths, combat stats, agent info, utility usage).

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/series/123/players/456/stats?games_count=5&videogame_version=latest" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 11.2 GET /valorant/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get aggregated team statistics for a team within a Valorant series
**URL:** `https://api.pandascore.co/valorant/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats`
**Access:** Historical or real-time data plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | string | Yes | Series ID or slug |
| `team_id_or_slug` | string | Yes | Team ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |

**Response Schema:** Aggregated team statistics for the series.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/series/123/teams/456/stats?games_count=5&videogame_version=latest" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 12. Teams

### 12.1 GET /valorant/teams
**Description:** List teams for the Valorant videogame
**URL:** `https://api.pandascore.co/valorant/teams`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of team objects (id, name, metadata).

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/teams?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 13. Team Stats

### 13.1 GET /valorant/teams/{team_id_or_slug}/stats
**Description:** Get a Valorant team's stats by ID or slug
**URL:** `https://api.pandascore.co/valorant/teams/{team_id_or_slug}/stats`
**Access:** Historical or real-time data plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `team_id_or_slug` | string | Yes | Team ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |

**Response Schema:** Aggregated team statistics.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/teams/130922/stats?games_count=5&from=2024-01-01&to=2024-03-23" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 14. Tournaments

### 14.1 GET /valorant/tournaments
**Description:** List tournaments for the Valorant videogame
**URL:** `https://api.pandascore.co/valorant/tournaments`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games count for statistics |

**Response Schema:**
```json
[
  {
    "id": 12345,                          // integer
    "name": "Tournament Name",           // string
    "slug": "tournament-slug",           // string
    "begin_at": "2024-01-15T00:00:00Z",  // datetime
    "end_at": "2024-01-20T00:00:00Z",    // datetime
    "status": "running",                  // string
    "league": { },                        // league object
    "teams": [ ]                          // team array
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/tournaments?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 14.2 GET /valorant/tournaments/past
**Description:** List past Valorant tournaments
**URL:** `https://api.pandascore.co/valorant/tournaments/past`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of completed tournament objects.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/tournaments/past?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 14.3 GET /valorant/tournaments/running
**Description:** List currently running Valorant tournaments
**URL:** `https://api.pandascore.co/valorant/tournaments/running`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:**
```json
[
  {
    "id": 12345,
    "name": "Tournament Name",
    "status": "running",
    "begin_at": "2024-01-15T00:00:00Z",
    "end_at": "2024-01-20T00:00:00Z"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/tournaments/running?per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 14.4 GET /valorant/tournaments/upcoming
**Description:** List upcoming Valorant tournaments
**URL:** `https://api.pandascore.co/valorant/tournaments/upcoming`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games count for statistics |

**Response Schema:** Array of upcoming tournament objects.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/tournaments/upcoming?page=1&per_page=10" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 15. Tournament Stats

### 15.1 GET /valorant/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats
**Description:** Get aggregated player statistics for a player within a Valorant tournament
**URL:** `https://api.pandascore.co/valorant/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats`
**Access:** Historical or real-time data plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tournament_id_or_slug` | string | Yes | Tournament ID or slug |
| `player_id_or_slug` | string | Yes | Player ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Games count for statistics |
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Aggregated player statistics within the tournament scope.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/tournaments/123/players/456/stats?games_count=5" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 15.2 GET /valorant/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get aggregated team statistics for a team within a Valorant tournament
**URL:** `https://api.pandascore.co/valorant/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats`
**Access:** Historical or real-time data plan customers only

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tournament_id_or_slug` | string | Yes | Tournament ID or slug |
| `team_id_or_slug` | string | Yes | Team ID or slug |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Games count for statistics |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `videogame_version` | string | No | Version filter |
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |

**Response Schema:** Aggregated team statistics within the tournament scope.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/tournaments/123/teams/456/stats?games_count=5&videogame_version=latest" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 16. Weapons

### 16.1 GET /valorant/weapons
**Description:** List all Valorant weapons
**URL:** `https://api.pandascore.co/valorant/weapons`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination. Default: 1 |
| `per_page` | integer | No | Page size. Default: 50, Max: 100 |
| `from` | date | No | Filter from date |
| `to` | date | No | Filter to date |
| `games_count` | integer | No | Games count for statistics |
| `videogame_version` | string | No | Version filter |

**Response Schema:**
```json
[
  {
    "id": 10,                             // integer
    "name": "Vandal",                     // string
    "image_url": "https://cdn.pandascore.co/...",  // URI
    "videogame_versions": ["1.0", "6.03"]  // string[]
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/weapons?per_page=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 16.2 GET /valorant/weapons/{valorant_weapon_id}
**Description:** Get a specific Valorant weapon by ID
**URL:** `https://api.pandascore.co/valorant/weapons/{valorant_weapon_id}`
**Access:** All customers

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `valorant_weapon_id` | integer | Yes | Unique weapon ID |

**Query Parameters:** None

**Response Schema:**
```json
{
  "id": 10,                             // integer
  "name": "Vandal",                     // string
  "image_url": "https://cdn.pandascore.co/...",  // URI
  "videogame_versions": ["1.0"]         // string[]
}
```

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/valorant/weapons/10" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Endpoint Summary (All 39)

| # | Method | Endpoint | Access | Deprecated |
|---|--------|----------|--------|------------|
| 1 | GET | `/valorant/abilities` | All | No |
| 2 | GET | `/valorant/abilities/{valorant_ability_id}` | All | No |
| 3 | GET | `/valorant/agents` | All | No |
| 4 | GET | `/valorant/agents/{valorant_agent_id}` | All | No |
| 5 | GET | `/valorant/versions/all/agents` | All | Yes |
| 6 | GET | `/valorant/versions/{valorant_version_name}/agents` | All | Yes |
| 7 | GET | `/valorant/games/{valorant_game_id}` | Historical/RT | No |
| 8 | GET | `/valorant/games/{valorant_game_id}/events` | Pro Historical | No |
| 9 | GET | `/valorant/games/{valorant_game_id}/rounds` | Pro Historical | No |
| 10 | GET | `/valorant/matches/{match_id_or_slug}/games` | Historical/RT | No |
| 11 | GET | `/valorant/leagues` | All | No |
| 12 | GET | `/valorant/maps` | All | No |
| 13 | GET | `/valorant/maps/{valorant_map_id}` | All | No |
| 14 | GET | `/valorant/versions/all/maps` | All | Yes |
| 15 | GET | `/valorant/versions/{valorant_version_name}/maps` | All | Yes |
| 16 | GET | `/valorant/matches` | All | No |
| 17 | GET | `/valorant/matches/past` | All | No |
| 18 | GET | `/valorant/matches/running` | All | No |
| 19 | GET | `/valorant/matches/upcoming` | All | No |
| 20 | GET | `/valorant/matches/{match_id_or_slug}/players/stats` | Historical/RT | No |
| 21 | GET | `/valorant/matches/{match_id_or_slug}/teams/{team_id_or_slug}/stats` | Historical/RT | No |
| 22 | GET | `/valorant/players/{player_id_or_slug}/stats` | Historical/RT | No |
| 23 | GET | `/valorant/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats` | Historical/RT | No |
| 24 | GET | `/valorant/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats` | Historical/RT | No |
| 25 | GET | `/valorant/teams/{team_id_or_slug}/stats` | Historical/RT | No |
| 26 | GET | `/valorant/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats` | Historical/RT | No |
| 27 | GET | `/valorant/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats` | Historical/RT | No |
| 28 | GET | `/valorant/players` | All | No |
| 29 | GET | `/valorant/series` | All | No |
| 30 | GET | `/valorant/series/past` | All | No |
| 31 | GET | `/valorant/series/running` | All | No |
| 32 | GET | `/valorant/series/upcoming` | All | No |
| 33 | GET | `/valorant/teams` | All | No |
| 34 | GET | `/valorant/tournaments` | All | No |
| 35 | GET | `/valorant/tournaments/past` | All | No |
| 36 | GET | `/valorant/tournaments/running` | All | No |
| 37 | GET | `/valorant/tournaments/upcoming` | All | No |
| 38 | GET | `/valorant/weapons` | All | No |
| 39 | GET | `/valorant/weapons/{valorant_weapon_id}` | All | No |

---

## Access Tiers

| Tier | Endpoints |
|------|-----------|
| **All customers** | Abilities, Agents, Leagues, Maps, Matches (list/past/running/upcoming), Players, Series, Teams, Tournaments, Weapons |
| **Historical / Real-time plan** | Games, Match games, All stats endpoints (player/team at match/series/tournament scope) |
| **Pro Historical plan** | Game events, Game rounds |

## Notes

- All endpoints are GET (read-only API)
- 4 endpoints are deprecated (version-specific agents/maps) -- use filter params instead
- Pagination max is 100 items per page, default 50
- Date format: YYYY-MM-DD
- Version format: `X.XX` or `X.XX.X` (e.g., `6.03`)
