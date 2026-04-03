# PandaScore League of Legends API Reference

**Base URL:** `https://api.pandascore.co`
**Authentication:** Bearer Token via `Authorization: Bearer YOUR_API_TOKEN` header
**Total Endpoints:** 48

---

## Table of Contents

1. [Champions](#1-champions)
2. [Games](#2-games)
3. [Items](#3-items)
4. [Leagues](#4-leagues)
5. [Masteries](#5-masteries)
6. [Matches](#6-matches)
7. [Players](#7-players)
8. [Player Stats](#8-player-stats)
9. [Runes](#9-runes)
10. [Runes Reforged](#10-runes-reforged)
11. [Series](#11-series)
12. [Teams](#12-teams)
13. [Spells](#13-spells)
14. [Tournaments](#14-tournaments)

---

## Common Query Parameters

Most list endpoints share these query parameters:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer or object | No | Pagination: `page=2` or `page[size]=30&page[number]=2`. Default: 1, Min: 1 |
| `per_page` | integer | No | Equivalent to `page[size]`. Default: 50, Max: 100, Min: 1 |
| `from` | date (YYYY-MM-DD) | No | Filter start date |
| `to` | date (YYYY-MM-DD) | No | Filter end date |
| `videogame_version` | string | No | `latest`, `all`, or specific version (e.g., `14.18.1`) |
| `games_count` | integer | No | Number of recent games for statistics |
| `side` | string (enum) | No | `blue` or `red` |

## Common Response Codes

All endpoints return these standard HTTP codes:

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
| 422 | Unprocessable Entity |

---

## 1. Champions

### 1.1 GET /lol/champions
**Description:** List League of Legends champions.
**URL:** `https://api.pandascore.co/lol/champions`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `games_count` | integer | No | Number of games for statistics |
| `side` | string (enum) | No | `blue` or `red` |
| `from` | date | No | Start date filter (YYYY-MM-DD) |
| `to` | date | No | End date filter (YYYY-MM-DD) |
| `videogame_version` | string | No | `latest`, `all`, or specific version |

**Response Schema (Array of LoLChampion):**
```json
[{
  "id": 3513,
  "name": "Xin Zhao",
  "slug": "XinZhao",
  "armor": 35,
  "armorperlevel": 5,
  "attackdamage": 63,
  "attackdamageperlevel": 3,
  "attackrange": 175,
  "attackspeedoffset": null,
  "attackspeedperlevel": 3.5,
  "hp": 640,
  "hpperlevel": 106,
  "hpregen": 8,
  "hpregenperlevel": 0.7,
  "mp": 274,
  "mpperlevel": 55,
  "mpregen": 7.25,
  "mpregenperlevel": 0.45,
  "movespeed": 345,
  "spellblock": 32,
  "spellblockperlevel": 2.05,
  "image_url": "https://cdn.pandascore.co/images/lol/champion/image/...",
  "big_image_url": "https://cdn.pandascore.co/images/lol/champion/big_image/...",
  "videogame_versions": ["14.18.1"]
}]
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (min: 1) | Champion ID |
| `name` | string | Champion name |
| `slug` | string | Human-readable identifier |
| `armor` | number (min: 0) | Base armor |
| `armorperlevel` | number (min: 0) | Armor per level |
| `attackdamage` | number (min: 0) | Base attack damage |
| `attackdamageperlevel` | number (min: 0) | AD per level |
| `attackrange` | number (min: 0) | Attack range |
| `attackspeedoffset` | number or null | Attack speed offset |
| `attackspeedperlevel` | number (min: 0) | Attack speed per level |
| `hp` | number (min: 0) | Base health |
| `hpperlevel` | number (min: 0) | HP per level |
| `hpregen` | number (min: 0) | HP regen |
| `hpregenperlevel` | number (min: 0) | HP regen per level |
| `mp` | number (min: 0) | Base mana |
| `mpperlevel` | number (min: 0) | Mana per level |
| `mpregen` | number (min: 0) | Mana regen |
| `mpregenperlevel` | number (min: 0) | Mana regen per level |
| `movespeed` | number (min: 0) | Movement speed |
| `spellblock` | number (min: 0) | Magic resistance |
| `spellblockperlevel` | number (min: 0) | MR per level |
| `image_url` | string (URI) | Portrait image URL |
| `big_image_url` | string (URI) | Large image URL |
| `videogame_versions` | array[string] | Patch versions |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/champions?per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 1.2 GET /lol/champions/{lol_champion_id}
**Description:** Get a single League of Legends champion by ID or slug.
**URL:** `https://api.pandascore.co/lol/champions/{lol_champion_id}`
**Access:** All customers

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_champion_id` | integer/string | Yes | Champion ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Number of recent games for statistics |
| `side` | string (enum) | No | `blue` or `red` |
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | `latest`, `all`, or specific version |

**Response Schema (LoLChampion):**
Same fields as list endpoint plus:
| Field | Type | Description |
|-------|------|-------------|
| `crit` | number (min: 0) | Base crit chance |
| `critperlevel` | number (min: 0) | Crit per level |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/champions/2527" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 1.3 GET /lol/versions/all/champions [DEPRECATED]
**Description:** List champions for all versions.
**URL:** `https://api.pandascore.co/lol/versions/all/champions`
**Deprecated:** Use `/lol/champions?filter[videogame_version]=all` instead.
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of LoLChampion objects (same as 1.1)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/versions/all/champions?per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 1.4 GET /lol/versions/{lol_version_name}/champions [DEPRECATED]
**Description:** List champions for a specific version.
**URL:** `https://api.pandascore.co/lol/versions/{lol_version_name}/champions`
**Deprecated:** Use `/lol/champions?filter[videogame_version]={version}` instead.
**Access:** All customers

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_version_name` | string | Yes | Patch version (e.g., `9.17.1`) |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |

**Response Schema:** Array of LoLChampion objects (same as 1.1)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/versions/9.17.1/champions" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 2. Games

### 2.1 GET /lol/games/{lol_game_id}
**Description:** Get a single League of Legends game by ID.
**URL:** `https://api.pandascore.co/lol/games/{lol_game_id}`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_game_id` | integer | Yes | Game ID |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games for statistics |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema (LoLGame):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Game identifier |
| `match_id` | integer | Associated match ID |
| `begin_at` | datetime | Game start timestamp |
| `end_at` | datetime | Game end timestamp |
| `finished` | boolean | Completion status |
| `complete` | boolean | Detailed stats availability |
| `detailed_stats` | boolean | Enhanced statistics flag |
| `length` | integer | Duration in seconds |
| `forfeit` | boolean | Forfeit status |
| `position` | integer | Game sequence in match |
| `status` | string | Game state |
| `winner` | object | Winning team/player data |
| `winner_id` | integer | Winner identifier |
| `winner_type` | string | `Team` or player type |
| `match` | object | Full match details |
| `players` | array | Array of player statistics |

**Player statistics fields:** `assists`, `champion`, `creep_score`, `deaths`, `gold_earned`, `items`, `kills`, `level`, `player`, `role`, `runes_reforged`, `spells`, `team`, `total_damage`, `wards`

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/games/243129" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 2.2 GET /lol/games/{lol_game_id}/events
**Description:** List play-by-play events for a given LoL game.
**URL:** `https://api.pandascore.co/lol/games/{lol_game_id}/events`
**Access:** Real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_game_id` | string | Yes | Game ID |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |

**Response Schema:** Array of game event objects containing timestamps, event types, player involvement, and gameplay actions.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/games/243129/events" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 2.3 GET /lol/games/{lol_game_id}/frames
**Description:** List play-by-play frames for a given LoL game.
**URL:** `https://api.pandascore.co/lol/games/{lol_game_id}/frames`
**Access:** Real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_game_id` | integer | Yes | Game ID |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of frame objects with per-player snapshots: champions, creep scores, damage dealt/taken, kills/deaths/assists, items, runes, gold earned, and combat metrics.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/games/243129/frames" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 2.4 GET /lol/matches/{match_id_or_slug}/games
**Description:** List games for a given LoL match.
**URL:** `https://api.pandascore.co/lol/matches/{match_id_or_slug}/games`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | string | Yes | Match ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `games_count` | integer | No | Recent games for statistics |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema (Array of LoLGame):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Game identifier |
| `match_id` | integer | Associated match ID |
| `position` | integer | Game position in series |
| `status` | string | `finished`, `running`, etc. |
| `begin_at` | datetime | Start timestamp |
| `end_at` | datetime | End timestamp |
| `length` | integer | Duration in seconds |
| `complete` | boolean | Completion status |
| `finished` | boolean | Finished flag |
| `forfeit` | boolean | Forfeit flag |
| `detailed_stats` | boolean | Stats availability |
| `winner` | object | Winning team/player |
| `winner_type` | string | `Team` or `Player` |
| `winner_id` | integer | Winner ID |
| `match` | object | Parent match (id, league_id, serie_id, tournament_id, begin_at, end_at, name, slug, status, match_type, results, opponents) |
| `players` | array | Player stats (player_id, champion, kills, deaths, assists, creep_score, gold_earned, level, items, spells, runes_reforged, damage objects, wards) |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/matches/720982/games" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 2.5 GET /lol/teams/{team_id_or_slug}/games
**Description:** List finished games for a given LoL team.
**URL:** `https://api.pandascore.co/lol/teams/{team_id_or_slug}/games`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `team_id_or_slug` | string/integer | Yes | Team ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `games_count` | integer | No | Recent games for statistics |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema:** Array of LoLGame objects (same structure as 2.4)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/teams/g2-esports/games" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 3. Items

### 3.1 GET /lol/items
**Description:** List League of Legends items.
**URL:** `https://api.pandascore.co/lol/items`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema (Array of LoLItem):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (min: 1) | Item ID |
| `name` | string | Item name |
| `slug` | string | Human-readable identifier |
| `image_url` | string (URI) | Item image URL |
| `videogame_versions` | array[string] | Patch versions |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/items" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 3.2 GET /lol/items/{lol_item_id}
**Description:** Get a single item by ID or slug.
**URL:** `https://api.pandascore.co/lol/items/{lol_item_id}`
**Access:** All customers

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_item_id` | string | Yes | Item ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |

**Response Schema (LoLItem):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (min: 1) | Item ID |
| `name` | string | Item name |
| `slug` | string | Human-readable identifier |
| `description` | string | Item description |
| `image_url` | string (URI) | Item image URL |
| `gold` | object | Gold info (cost, sell value) |
| `stats` | object | Item stat bonuses |
| `tags` | array | Classification tags |
| `videogame_versions` | array | Supported versions |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/items/3078" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 3.3 GET /lol/versions/all/items [DEPRECATED]
**Description:** List items for all versions.
**URL:** `https://api.pandascore.co/lol/versions/all/items`
**Deprecated:** Use `/lol/items?filter[videogame_version]=all` instead.
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |

**Response Schema:** Array of LoLItem objects (same as 3.1)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/versions/all/items?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 3.4 GET /lol/versions/{lol_version_name}/items [DEPRECATED]
**Description:** List items for a specific version.
**URL:** `https://api.pandascore.co/lol/versions/{lol_version_name}/items`
**Deprecated:** Use `/lol/items?filter[videogame_version]={version}` instead.
**Access:** All customers

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_version_name` | string | Yes | Patch version (e.g., `13.1.1`) |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |

**Response Schema:** Array of LoLItem objects (same as 3.1)

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/versions/13.1.1/items" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 4. Leagues

### 4.1 GET /lol/leagues
**Description:** List League of Legends leagues.
**URL:** `https://api.pandascore.co/lol/leagues`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `games_count` | integer | No | Games for statistics |
| `videogame_version` | string | No | Version filter |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema (Array of League):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | League ID |
| `name` | string | League name |
| `slug` | string | Human-readable identifier |
| `image_url` | string (URI) | League image URL |
| `modified_at` | datetime | Last modification timestamp |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/leagues?per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 5. Masteries

### 5.1 GET /lol/masteries
**Description:** List League of Legends masteries.
**URL:** `https://api.pandascore.co/lol/masteries`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games for statistics |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema:** Array of mastery objects.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/masteries?per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 5.2 GET /lol/masteries/{lol_mastery_id}
**Description:** Get a single mastery by ID.
**URL:** `https://api.pandascore.co/lol/masteries/{lol_mastery_id}`
**Access:** All customers

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_mastery_id` | integer | Yes | Mastery ID |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |

**Response Schema (LoLMastery):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Mastery ID |
| `name` | string | Mastery name |
| `description` | string | Mastery description |
| `image_url` | string (URI) | Image URL |
| `videogame_versions` | array[string] | Patch versions |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/masteries/6111" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 6. Matches

### 6.1 GET /lol/matches
**Description:** List matches for the League of Legends videogame.
**URL:** `https://api.pandascore.co/lol/matches`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games for statistics |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema:** Array of Match objects with nested game statistics, player performance, champion selections, items, runes, and damage calculations.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/matches?per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 6.2 GET /lol/matches/past
**Description:** List past League of Legends matches.
**URL:** `https://api.pandascore.co/lol/matches/past`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games for statistics |

**Response Schema (Array of Match):**

Match-level: `id`, `begin_at`, `end_at`, `scheduled_at`, `status`, `draw`, `forfeit`, `name`, `serie`, `league`, `tournament`, `opponents`, `results`, `streams_list`, `videogame_version`, `live`, `detailed_stats`

Game-level: `id`, `begin_at`, `end_at`, `length`, `position`, `status`, `complete`, `finished`, `forfeit`, `detailed_stats`, `winner`, `winner_type`, `match_id`

Player stats: `player_id`, `champion`, `kills`, `deaths`, `assists`, `creep_score`, `gold_earned`, `items`, `spells`, `runes_reforged`, `total_damage`, `role`

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/matches/past?per_page=5" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 6.3 GET /lol/matches/running
**Description:** List running League of Legends matches.
**URL:** `https://api.pandascore.co/lol/matches/running`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema (Array of Match):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Match ID |
| `name` | string | Match name |
| `status` | string | Match status |
| `scheduled_at` | datetime | Scheduled time |
| `begin_at` | datetime | Start time |
| `end_at` | datetime | End time |
| `league` | object | League (id, name, slug) |
| `serie` | object | Serie details |
| `tournament` | object | Tournament details |
| `opponents` | array | Team objects |
| `games` | array | Game objects with stats |
| `results` | array | Scores |
| `streams_list` | array | Stream URLs |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/matches/running" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 6.4 GET /lol/matches/upcoming
**Description:** List upcoming League of Legends matches.
**URL:** `https://api.pandascore.co/lol/matches/upcoming`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games for statistics |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema (Array of Match):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Match ID |
| `name` | string | Match name |
| `status` | string | Match status |
| `scheduled_at` | datetime | Scheduled time |
| `begin_at` | datetime (nullable) | Start time |
| `end_at` | datetime (nullable) | End time |
| `league_id` | integer | League ID |
| `serie_id` | integer | Serie ID |
| `tournament_id` | integer | Tournament ID |
| `videogame` | object | Videogame (id, name, slug) |
| `opponents` | array | Opponent objects |
| `results` | array | Score + team_id |
| `winner_id` | integer (nullable) | Winner ID |
| `winner_type` | string (nullable) | Winner type |
| `draw` | boolean | Draw flag |
| `forfeit` | boolean | Forfeit flag |
| `modified_at` | datetime | Last modified |

**cURL Example:**
```bash
curl --request GET \
  --url 'https://api.pandascore.co/lol/matches/upcoming?page=1&per_page=50' \
  --header 'Authorization: Bearer YOUR_API_TOKEN'
```

---

### 6.5 GET /lol/matches/{match_id_or_slug}
**Description:** Get a single League of Legends match by ID or slug.
**URL:** `https://api.pandascore.co/lol/matches/{match_id_or_slug}`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | string | Yes | Match ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** LoLGame object with full match details including `id`, `match_id`, `begin_at`, `end_at`, `length`, `complete`, `finished`, `forfeit`, `detailed_stats`, `status`, `winner`, `players` (array with stats), `match` (parent match details).

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/matches/720982" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 6.6 GET /lol/matches/{match_id_or_slug}/players/stats
**Description:** Get detailed statistics of LoL players for a given match.
**URL:** `https://api.pandascore.co/lol/matches/{match_id_or_slug}/players/stats`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id_or_slug` | string | Yes | Match ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Recent games for statistics |
| `side` | string (enum) | No | `blue` or `red` |
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema (Array of PlayerStats):**
| Field | Type | Description |
|-------|------|-------------|
| `player_id` | integer | Player ID |
| `player` | object | Player (name, id, role) |
| `team` | object | Team info |
| `opponent` | object | Opponent info |
| `champion` | object | Champion (id, name, slug, image_url) |
| `kills` | integer | Kills |
| `deaths` | integer | Deaths |
| `assists` | integer | Assists |
| `kills_series` | object | Double/triple/quadra/penta kills |
| `largest_killing_spree` | integer | Largest killing spree |
| `largest_multi_kill` | integer | Largest multi kill |
| `total_damage` | object | Damage dealt/taken/percentages |
| `physical_damage` | object | Physical damage subcategories |
| `magic_damage` | object | Magic damage subcategories |
| `true_damage` | object | True damage subcategories |
| `gold_earned` | integer | Total gold earned |
| `gold_spent` | integer | Total gold spent |
| `gold_percentage` | number | Gold share percentage |
| `creep_score` | integer | Total CS |
| `cs_at_14` | integer | CS at 14 minutes |
| `cs_diff_at_14` | integer | CS diff at 14 min |
| `minions_killed` | integer | Minions killed |
| `items` | array | Items (id, name, is_trinket) |
| `spells` | array | Summoner spells |
| `runes` | object | Rune configuration |
| `runes_reforged` | object | Primary/secondary paths + shards |
| `level` | integer | Champion level |
| `wards` | object | Wards placed/bought |
| `total_time_crowd_control_dealt` | number | CC time |
| `role` | string | Player role |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/matches/720982/players/stats?page[size]=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 7. Players

### 7.1 GET /lol/players
**Description:** List players for the League of Legends videogame.
**URL:** `https://api.pandascore.co/lol/players`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games for statistics |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema (Array of Player):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (min: 1) | Player ID |
| `name` | string | Player gamertag |
| `slug` | string | Human-readable identifier |
| `age` | integer | Player age |
| `birthday` | string (date) | Birth date |
| `first_name` | string | First name |
| `last_name` | string | Last name |
| `nationality` | string | Nationality |
| `role` | string | Role (sup, adc, mid, top, jun) |
| `active` | boolean | Active status |
| `image_url` | string (URI) | Player image URL |
| `modified_at` | datetime | Last modified |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/players?per_page=50&page=1" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 8. Player Stats

### 8.1 GET /lol/players/{player_id_or_slug}/stats
**Description:** Get detailed statistics for a specific LoL player.
**URL:** `https://api.pandascore.co/lol/players/{player_id_or_slug}/stats`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `player_id_or_slug` | string/integer | Yes | Player ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Limit to N most recent games |
| `side` | string (enum) | No | `blue` or `red` |
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Detailed player statistics including champion data, kills/deaths/assists, creep score, gold metrics, damage dealt/taken (physical, magic, true), items, runes, spells, crowd control metrics, ward placement and vision control.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/players/605/stats?games_count=5&per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 8.2 GET /lol/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats
**Description:** Get detailed statistics of a given LoL player for a given serie.
**URL:** `https://api.pandascore.co/lol/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | string/integer | Yes | Serie ID or slug |
| `player_id_or_slug` | string/integer | Yes | Player ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Recent games for statistics |
| `side` | string (enum) | No | `blue` or `red` |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |

**Response Schema:** Detailed player performance metrics: kills, deaths, assists, creep score, gold earned/spent, damage dealt/taken (magic, physical, true), items, champion, runes, spells, crowd control statistics.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/series/league-of-legends-lec-winter-2023/players/605/stats" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 8.3 GET /lol/series/{serie_id_or_slug}/teams/stats
**Description:** Get detailed statistics for LoL teams in a given serie.
**URL:** `https://api.pandascore.co/lol/series/{serie_id_or_slug}/teams/stats`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | string | Yes | Serie ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Recent games for statistics |
| `side` | string (enum) | No | `blue` or `red` |
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of team statistics: team identification (id, name, slug, acronym), aggregated performance metrics, win/loss records, champion selection data, objective control statistics, economic performance.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/series/league-of-legends-lec-winter-2023/teams/stats?per_page=50&videogame_version=latest" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 8.4 GET /lol/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get detailed statistics for a specific LoL team during a given serie.
**URL:** `https://api.pandascore.co/lol/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | string | Yes | Serie ID or slug |
| `team_id_or_slug` | string | Yes | Team ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Recent games for statistics |
| `side` | string (enum) | No | `blue` or `red` |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |

**Response Schema:** Team statistics with player-level stats (kills, deaths, assists, creep score, gold), damage metrics (physical, magic, true), item builds, champion selections, rune configurations, spell choices, aggregated team performance.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/series/league-of-legends-lec-winter-2023/teams/g2-esports/stats?games_count=5&per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 8.5 GET /lol/teams/{team_id_or_slug}/stats
**Description:** Get detailed statistics for a specific LoL team.
**URL:** `https://api.pandascore.co/lol/teams/{team_id_or_slug}/stats`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `team_id_or_slug` | string/integer | Yes | Team ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Recent games for statistics |
| `side` | string (enum) | No | `blue` or `red` |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |

**Response Schema:** Team statistics in JSON format.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/teams/g2-esports/stats?games_count=5&page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 8.6 GET /lol/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats
**Description:** Get detailed statistics of a given LoL player for a given tournament.
**URL:** `https://api.pandascore.co/lol/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tournament_id_or_slug` | string | Yes | Tournament ID or slug |
| `player_id_or_slug` | string | Yes | Player ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `games_count` | integer | No | Recent games for statistics |
| `side` | string (enum) | No | `blue` or `red` |
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Detailed player statistics including champions played, KDA, creep score, gold metrics, damage dealt/taken, items, runes, and performance indicators.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/tournaments/worlds-2023/players/605/stats" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 8.7 GET /lol/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats
**Description:** Get detailed statistics of a given LoL team for a given tournament.
**URL:** `https://api.pandascore.co/lol/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats`
**Access:** Historical or real-time data plan required

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tournament_id_or_slug` | string | Yes | Tournament ID or slug |
| `team_id_or_slug` | string | Yes | Team ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `games_count` | integer | No | Recent games for statistics |
| `side` | string (enum) | No | `blue` or `red` |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Team statistics with opponent info, match details, and aggregated performance metrics.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/tournaments/worlds-2023/teams/g2-esports/stats" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 9. Runes

### 9.1 GET /lol/runes [DEPRECATED]
**Description:** List League of Legends runes.
**URL:** `https://api.pandascore.co/lol/runes`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games for statistics |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema (Array of LoLRune):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Rune ID |
| `name` | string | Rune name |
| `image_url` | string (URI) | Rune image URL |
| `type` | string | Rune type (keystone, slot1, slot2, slot3, shard) |
| `videogame_versions` | array[string] | Patch versions |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/runes?per_page=50&page=1" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 9.2 GET /lol/runes/{lol_rune_id} [DEPRECATED]
**Description:** Get a single rune by ID.
**URL:** `https://api.pandascore.co/lol/runes/{lol_rune_id}`
**Access:** All customers

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_rune_id` | integer | Yes | Rune ID |

**Query Parameters:** None

**Response Schema (LoLRune):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Rune ID |
| `name` | string | Rune name |
| `slug` | string | Human-readable identifier |
| `image_url` | string (URI) | Rune image URL |
| `videogame_versions` | array[string] | Patch versions |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/runes/5245" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 10. Runes Reforged

### 10.1 GET /lol/runes-reforged
**Description:** List the latest version of LoL (reforged) runes.
**URL:** `https://api.pandascore.co/lol/runes-reforged`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema (Array of LoLRuneReforged):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Rune ID |
| `name` | string | Rune name |
| `image_url` | string (URI) | Rune image URL |
| `type` | string | Rune type classification |
| `videogame_versions` | array[string] | Compatible patches |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/runes-reforged?per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 10.2 GET /lol/runes-reforged-paths
**Description:** List the latest version of LoL (reforged) rune paths.
**URL:** `https://api.pandascore.co/lol/runes-reforged-paths`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |

**Response Schema (Array of LoLRunePath):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (min: 1) | Rune path ID |
| `name` | string | Path name (e.g., Inspiration, Resolve) |
| `type` | string | `path` |
| `image_url` | string (URI) | Path image URL |
| `keystone` | object | Primary rune (id, name, image_url, type) |
| `lesser_runes` | array | Secondary runes (id, name, image_url, type) |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/runes-reforged-paths?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 10.3 GET /lol/runes-reforged-paths/{lol_rune_path_id}
**Description:** Get a single LoL (reforged) rune path by ID.
**URL:** `https://api.pandascore.co/lol/runes-reforged-paths/{lol_rune_path_id}`
**Access:** All customers

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_rune_path_id` | integer | Yes | Rune path ID |

**Query Parameters:** None

**Response Schema (LoLRunePath):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Rune path ID |
| `name` | string | Path name |
| `image_url` | string (URI) | Path image URL |
| `type` | string | `path` |
| `keystone` | object | Primary keystone rune (id, name, image_url, type) |
| `lesser_runes` | array | Secondary runes (id, name, image_url, type) |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/runes-reforged-paths/8200" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 10.4 GET /lol/runes-reforged/{lol_rune_reforged_id}
**Description:** Get a single LoL (reforged) rune by ID.
**URL:** `https://api.pandascore.co/lol/runes-reforged/{lol_rune_reforged_id}`
**Access:** All customers

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_rune_reforged_id` | integer | Yes | Reforged rune ID |

**Query Parameters:** None

**Response Schema (LoLRuneReforged):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Rune ID |
| `name` | string | Rune name |
| `image_url` | string (URI) | Rune image URL |
| `type` | string | `path` classification |
| `keystone` | object | Primary rune (id, name, image_url, type) |
| `lesser_runes` | array | Secondary runes |
| `shards` | object | Stat shards (offense, flex, defense) |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/runes-reforged/15" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 11. Series

### 11.1 GET /lol/series
**Description:** List series for the League of Legends videogame.
**URL:** `https://api.pandascore.co/lol/series`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of series objects containing series ID, name, season, year, league information, begin/end dates, and winner details.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/series" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 11.2 GET /lol/series/past
**Description:** List past League of Legends series.
**URL:** `https://api.pandascore.co/lol/series/past`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games for statistics |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema:** Array of series objects with match, team, league, and tournament information.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/series/past?per_page=5" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 11.3 GET /lol/series/running
**Description:** List running League of Legends series.
**URL:** `https://api.pandascore.co/lol/series/running`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of series objects with match and tournament data.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/series/running?per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 11.4 GET /lol/series/upcoming
**Description:** List upcoming League of Legends series.
**URL:** `https://api.pandascore.co/lol/series/upcoming`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `games_count` | integer | No | Games for statistics |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of series objects with league data, team information, dates, tournament references, and status indicators.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/series/upcoming?per_page=10" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 11.5 GET /lol/series/{serie_id_or_slug}/teams
**Description:** List teams for the LoL videogame for a given serie.
**URL:** `https://api.pandascore.co/lol/series/{serie_id_or_slug}/teams`
**Access:** All customers

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `serie_id_or_slug` | string | Yes | Serie ID or slug |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of team objects (id, slug, name, acronym, location, image_url, modified_at).

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/series/league-of-legends-lec-winter-2023/teams" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 12. Teams

### 12.1 GET /lol/teams
**Description:** List teams for the League of Legends videogame.
**URL:** `https://api.pandascore.co/lol/teams`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |
| `games_count` | integer | No | Games for statistics |
| `side` | string (enum) | No | `blue` or `red` |

**Response Schema (Array of Team):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Team ID |
| `name` | string | Team name |
| `acronym` | string | Team abbreviation |
| `slug` | string | Human-readable identifier |
| `image_url` | string (URI) | Team logo URL |
| `dark_mode_image_url` | string (nullable) | Dark mode logo URL |
| `location` | string | Team location |
| `modified_at` | datetime | Last modified |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/teams?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 13. Spells

### 13.1 GET /lol/spells
**Description:** List League of Legends summoner spells.
**URL:** `https://api.pandascore.co/lol/spells`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of spell objects.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/spells?per_page=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 13.2 GET /lol/spells/{lol_spell_id}
**Description:** Get a single summoner spell by ID.
**URL:** `https://api.pandascore.co/lol/spells/{lol_spell_id}`
**Access:** All customers

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lol_spell_id` | integer | Yes | Spell ID |

**Query Parameters:** None

**Response Schema (LoLSpell):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Spell ID |
| `name` | string | Spell name |
| `image_url` | string (URI) | Spell image URL |
| `description` | string | Spell description |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/spells/4" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## 14. Tournaments

### 14.1 GET /lol/tournaments
**Description:** List tournaments for the League of Legends videogame.
**URL:** `https://api.pandascore.co/lol/tournaments`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of tournament objects.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/tournaments?per_page=50&page=1" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 14.2 GET /lol/tournaments/past
**Description:** List past League of Legends tournaments.
**URL:** `https://api.pandascore.co/lol/tournaments/past`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema (Array of Tournament):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Tournament ID |
| `name` | string | Tournament name |
| `slug` | string | Human-readable identifier |
| `begin_at` | datetime | Start time |
| `end_at` | datetime | End time |
| `league_id` | integer | League ID |
| `serie_id` | integer | Serie ID |
| `detailed_stats` | boolean | Stats availability |
| `prizepool` | string | Prize pool |
| `region` | string | Region |
| `country` | string | Country |
| `tier` | string | Tournament tier |
| `type` | string | Tournament type |
| `winner_id` | integer | Winner ID |
| `winner_type` | string | Winner type |
| `has_bracket` | boolean | Bracket flag |
| `live_supported` | boolean | Live support flag |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/tournaments/past?per_page=50&page=1" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 14.3 GET /lol/tournaments/running
**Description:** List running League of Legends tournaments.
**URL:** `https://api.pandascore.co/lol/tournaments/running`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema:** Array of tournament objects with identification, temporal info, structure (league_id, serie_id, bracket), metadata (tier, type, region, country), teams, matches, rosters, standings, prize and winner info.

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/tournaments/running?per_page=5" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### 14.4 GET /lol/tournaments/upcoming
**Description:** List upcoming League of Legends tournaments.
**URL:** `https://api.pandascore.co/lol/tournaments/upcoming`
**Access:** All customers

**Path Parameters:** None

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `page` | integer/object | No | Pagination |
| `per_page` | integer | No | Items per page (default: 50, max: 100) |
| `from` | date | No | Start date (YYYY-MM-DD) |
| `to` | date | No | End date (YYYY-MM-DD) |
| `videogame_version` | string | No | Version filter |

**Response Schema (Array of Tournament):**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Tournament ID |
| `name` | string | Tournament name |
| `slug` | string | Human-readable identifier |
| `begin_at` | datetime | Start time |
| `end_at` | datetime | End time |
| `scheduled_at` | datetime | Scheduled time |
| `league_id` | integer | League ID |
| `serie_id` | integer | Serie ID |
| `tier` | string | Tournament tier |
| `prizepool` | string | Prize pool |
| `has_bracket` | boolean | Bracket flag |
| `detailed_stats` | boolean | Stats availability |
| `winner_id` | integer | Winner ID |
| `winner_type` | string | Winner type |
| `live_supported` | boolean | Live support flag |

**cURL Example:**
```bash
curl -X GET "https://api.pandascore.co/lol/tournaments/upcoming?per_page=10" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

## Endpoint Summary Table

| # | Method | Endpoint | Access | Deprecated |
|---|--------|----------|--------|------------|
| 1 | GET | `/lol/champions` | All | No |
| 2 | GET | `/lol/champions/{lol_champion_id}` | All | No |
| 3 | GET | `/lol/versions/all/champions` | All | Yes |
| 4 | GET | `/lol/versions/{lol_version_name}/champions` | All | Yes |
| 5 | GET | `/lol/games/{lol_game_id}` | Historical/RT | No |
| 6 | GET | `/lol/games/{lol_game_id}/events` | RT only | No |
| 7 | GET | `/lol/games/{lol_game_id}/frames` | RT only | No |
| 8 | GET | `/lol/matches/{match_id_or_slug}/games` | Historical/RT | No |
| 9 | GET | `/lol/teams/{team_id_or_slug}/games` | Historical/RT | No |
| 10 | GET | `/lol/items` | All | No |
| 11 | GET | `/lol/items/{lol_item_id}` | All | No |
| 12 | GET | `/lol/versions/all/items` | All | Yes |
| 13 | GET | `/lol/versions/{lol_version_name}/items` | All | Yes |
| 14 | GET | `/lol/leagues` | All | No |
| 15 | GET | `/lol/masteries` | All | No |
| 16 | GET | `/lol/masteries/{lol_mastery_id}` | All | No |
| 17 | GET | `/lol/matches` | All | No |
| 18 | GET | `/lol/matches/past` | All | No |
| 19 | GET | `/lol/matches/running` | All | No |
| 20 | GET | `/lol/matches/upcoming` | All | No |
| 21 | GET | `/lol/matches/{match_id_or_slug}` | Historical/RT | No |
| 22 | GET | `/lol/matches/{match_id_or_slug}/players/stats` | Historical/RT | No |
| 23 | GET | `/lol/players/{player_id_or_slug}/stats` | Historical/RT | No |
| 24 | GET | `/lol/series/{serie_id_or_slug}/players/{player_id_or_slug}/stats` | Historical/RT | No |
| 25 | GET | `/lol/series/{serie_id_or_slug}/teams/stats` | Historical/RT | No |
| 26 | GET | `/lol/series/{serie_id_or_slug}/teams/{team_id_or_slug}/stats` | Historical/RT | No |
| 27 | GET | `/lol/teams/{team_id_or_slug}/stats` | Historical/RT | No |
| 28 | GET | `/lol/tournaments/{tournament_id_or_slug}/players/{player_id_or_slug}/stats` | Historical/RT | No |
| 29 | GET | `/lol/tournaments/{tournament_id_or_slug}/teams/{team_id_or_slug}/stats` | Historical/RT | No |
| 30 | GET | `/lol/players` | All | No |
| 31 | GET | `/lol/runes` | All | Yes |
| 32 | GET | `/lol/runes-reforged` | All | No |
| 33 | GET | `/lol/runes-reforged-paths` | All | No |
| 34 | GET | `/lol/runes-reforged-paths/{lol_rune_path_id}` | All | No |
| 35 | GET | `/lol/runes-reforged/{lol_rune_reforged_id}` | All | No |
| 36 | GET | `/lol/runes/{lol_rune_id}` | All | Yes |
| 37 | GET | `/lol/series` | All | No |
| 38 | GET | `/lol/series/past` | All | No |
| 39 | GET | `/lol/series/running` | All | No |
| 40 | GET | `/lol/series/upcoming` | All | No |
| 41 | GET | `/lol/series/{serie_id_or_slug}/teams` | All | No |
| 42 | GET | `/lol/teams` | All | No |
| 43 | GET | `/lol/spells` | All | No |
| 44 | GET | `/lol/spells/{lol_spell_id}` | All | No |
| 45 | GET | `/lol/tournaments` | All | No |
| 46 | GET | `/lol/tournaments/past` | All | No |
| 47 | GET | `/lol/tournaments/running` | All | No |
| 48 | GET | `/lol/tournaments/upcoming` | All | No |

---

## Access Levels

| Level | Description |
|-------|-------------|
| **All** | Available to all customers with any plan |
| **Historical/RT** | Requires historical or real-time data plan |
| **RT only** | Requires real-time data plan |

## Notes

- All endpoints are **GET** requests (read-only API)
- Bearer token authentication is required for all endpoints
- Pagination: max 100 items per page, default 50
- Deprecated endpoints have equivalent modern routes noted
- Date format: `YYYY-MM-DD` (e.g., `2024-01-15`)
- Version format: `X.Y.Z` (e.g., `14.18.1`)
- Slugs are human-readable identifiers usable in place of numeric IDs
