# ESPN Public API — Complete Developer Guide

> **Purpose:** Antigravity-ready reference document for integrating ESPN's undocumented public API into Optimus Claudeus or any sports prediction/trading bot.
>
> **Source:** https://github.com/pseudo-r/Public-ESPN-API
>
> **DISCLAIMER:** This is ESPN's undocumented public API. No authentication required for most endpoints. No official rate limits published — implement caching. APIs may change without notice.

---

## Table of Contents

1. [Base URLs](#1-base-urls)
2. [Quick Start](#2-quick-start)
3. [URL Pattern](#3-url-pattern)
4. [NFL Endpoints](#4-nfl-endpoints)
5. [NBA Endpoints](#5-nba-endpoints)
6. [MLB Endpoints](#6-mlb-endpoints)
7. [NHL Endpoints](#7-nhl-endpoints)
8. [College Football Endpoints](#8-college-football-endpoints)
9. [College Basketball Endpoints](#9-college-basketball-endpoints)
10. [WNBA Endpoints](#10-wnba-endpoints)
11. [Soccer Endpoints](#11-soccer-endpoints)
12. [UFC / MMA Endpoints](#12-ufc--mma-endpoints)
13. [Golf Endpoints](#13-golf-endpoints)
14. [Racing Endpoints (F1, NASCAR, IndyCar)](#14-racing-endpoints)
15. [Tennis Endpoints](#15-tennis-endpoints)
16. [Other Sports](#16-other-sports)
17. [Betting & Odds Endpoints](#17-betting--odds-endpoints)
18. [Advanced / Core API Endpoints](#18-advanced--core-api-endpoints)
19. [Athlete Detail Endpoints](#19-athlete-detail-endpoints)
20. [CDN Endpoints (Live/Fast Data)](#20-cdn-endpoints-livefast-data)
21. [Search API](#21-search-api)
22. [Fantasy Sports API](#22-fantasy-sports-api)
23. [Parameters Reference](#23-parameters-reference)
24. [Python Client Template](#24-python-client-template)
25. [All Sports & League Codes](#25-all-sports--league-codes)

---

## 1. Base URLs

| Domain | Purpose | Auth Required |
|--------|---------|--------------|
| `site.api.espn.com` | Scores, news, teams, standings | No |
| `sports.core.api.espn.com` | Athletes, stats, odds, detailed data | No |
| `site.web.api.espn.com` | Search, athlete profiles | No |
| `cdn.espn.com` | CDN-optimized live data | No |
| `fantasy.espn.com` | Fantasy sports leagues | Cookies for private leagues |
| `now.core.api.espn.com` | Real-time news feeds | No |

---

## 2. Quick Start

```bash
# Get NFL Scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

# Get NBA Teams
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"

# Get MLB Scores for Specific Date
curl "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates=20241215"
```

---

## 3. URL Pattern

### Site API (most common)
```
https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/{resource}
```

### Core API (detailed data)
```
https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/{resource}
```

### CDN (live/fast)
```
https://cdn.espn.com/core/{league}/{resource}?xhr=1
```

---

## 4. NFL Endpoints

| Resource | URL |
|----------|-----|
| Scoreboard | `site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard` |
| Teams | `site.api.espn.com/apis/site/v2/sports/football/nfl/teams` |
| Team Detail | `site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{id}` |
| Team Roster | `site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{id}/roster` |
| Team Schedule | `site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{id}/schedule` |
| Standings | `site.api.espn.com/apis/site/v2/sports/football/nfl/standings` |
| News | `site.api.espn.com/apis/site/v2/sports/football/nfl/news` |
| Game Summary | `site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={id}` |
| Leaders | `site.api.espn.com/apis/site/v3/sports/football/nfl/leaders` |

### NFL Parameters
```bash
# Specific week
?dates=20241215&week=15&seasontype=2

# Team with extra data
/teams/12?enable=roster,stats
```

---

## 5. NBA Endpoints

| Resource | URL |
|----------|-----|
| Scoreboard | `site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard` |
| Teams | `site.api.espn.com/apis/site/v2/sports/basketball/nba/teams` |
| Team Detail | `site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{id}` |
| Standings | `site.api.espn.com/apis/site/v2/sports/basketball/nba/standings` |
| News | `site.api.espn.com/apis/site/v2/sports/basketball/nba/news` |
| Players | `site.api.espn.com/apis/site/v2/sports/basketball/nba/players` |

---

## 6. MLB Endpoints

| Resource | URL |
|----------|-----|
| Scoreboard | `site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard` |
| Teams | `site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams` |
| Standings | `site.api.espn.com/apis/site/v2/sports/baseball/mlb/standings` |
| News | `site.api.espn.com/apis/site/v2/sports/baseball/mlb/news` |

---

## 7. NHL Endpoints

| Resource | URL |
|----------|-----|
| Scoreboard | `site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard` |
| Teams | `site.api.espn.com/apis/site/v2/sports/hockey/nhl/teams` |
| Standings | `site.api.espn.com/apis/site/v2/sports/hockey/nhl/standings` |
| News | `site.api.espn.com/apis/site/v2/sports/hockey/nhl/news` |

---

## 8. College Football Endpoints

| Resource | URL |
|----------|-----|
| Scoreboard | `site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard` |
| Rankings | `site.api.espn.com/apis/site/v2/sports/football/college-football/rankings` |
| Teams | `site.api.espn.com/apis/site/v2/sports/football/college-football/teams` |
| News | `site.api.espn.com/apis/site/v2/sports/football/college-football/news` |

### Conference IDs (use `groups` parameter)

| Conference | ID |
|-----------|-----|
| SEC | 8 |
| Big Ten | 5 |
| ACC | 1 |
| Big 12 | 4 |
| Pac-12 | 9 |
| American (AAC) | 151 |
| Mountain West | 17 |
| MAC | 15 |
| Sun Belt | 37 |
| Top 25 | 80 |

```bash
# SEC games only
?groups=8
```

---

## 9. College Basketball Endpoints

| Resource | URL |
|----------|-----|
| Men's Scoreboard | `site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard` |
| Men's Rankings | `site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings` |
| Women's Scoreboard | `site.api.espn.com/apis/site/v2/sports/basketball/womens-college-basketball/scoreboard` |

---

## 10. WNBA Endpoints

| Resource | URL |
|----------|-----|
| Scoreboard | `site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard` |
| Teams | `site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams` |

---

## 11. Soccer Endpoints

### URL Pattern
```
site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/{resource}
```

### Available Resources per League
| Resource | Path |
|----------|------|
| Scoreboard | `/scoreboard` |
| Teams | `/teams` |
| Standings | `/standings` |

### Complete League Codes

| League | Code |
|--------|------|
| Premier League | `eng.1` |
| Championship | `eng.2` |
| La Liga | `esp.1` |
| Bundesliga | `ger.1` |
| Serie A | `ita.1` |
| Ligue 1 | `fra.1` |
| MLS | `usa.1` |
| NWSL | `usa.nwsl` |
| Champions League | `uefa.champions` |
| Europa League | `uefa.europa` |
| World Cup | `fifa.world` |
| Liga MX | `mex.1` |
| Eredivisie | `ned.1` |
| Primeira Liga | `por.1` |
| Scottish Premiership | `sco.1` |
| Brasileirão | `bra.1` |
| Copa Libertadores | `conmebol.libertadores` |

### Examples
```bash
# Premier League scoreboard
https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard

# La Liga standings
https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/standings

# Champions League teams
https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/teams
```

---

## 12. UFC / MMA Endpoints

| Resource | URL |
|----------|-----|
| Scoreboard | `site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard` |
| Rankings | `site.api.espn.com/apis/site/v2/sports/mma/ufc/rankings` |
| Athletes | `site.api.espn.com/apis/site/v2/sports/mma/ufc/athletes` |
| News | `site.api.espn.com/apis/site/v2/sports/mma/ufc/news` |

---

## 13. Golf Endpoints

| Resource | URL |
|----------|-----|
| PGA Scoreboard | `site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard` |
| PGA Leaderboard | `site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard` |
| LPGA Scoreboard | `site.api.espn.com/apis/site/v2/sports/golf/lpga/scoreboard` |

Golf tour slugs: `pga`, `lpga`, `eur`, `champions-tour`

---

## 14. Racing Endpoints

| Resource | URL |
|----------|-----|
| F1 Scoreboard | `site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard` |
| F1 Standings | `site.api.espn.com/apis/site/v2/sports/racing/f1/standings` |
| NASCAR Cup | `site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard` |
| IndyCar | `site.api.espn.com/apis/site/v2/sports/racing/irl/scoreboard` |

---

## 15. Tennis Endpoints

| Resource | URL |
|----------|-----|
| ATP Scoreboard | `site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard` |
| WTA Scoreboard | `site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard` |
| ATP Rankings | `site.api.espn.com/apis/site/v2/sports/tennis/atp/rankings` |

---

## 16. Other Sports

| Sport | League Code (use in URL pattern) |
|-------|----------------------------------|
| Rugby | `rugby/rugby-union` |
| Cricket | `cricket` |
| Lacrosse (PLL) | `lacrosse/pll` |
| Boxing | `boxing` |

---

## 17. Betting & Odds Endpoints

Base: `sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}`

| Resource | Path |
|----------|------|
| Game Odds | `/events/{id}/competitions/{id}/odds` |
| Win Probabilities | `/events/{id}/competitions/{id}/probabilities` |
| Futures | `/seasons/{year}/futures` |
| ATS Records | `/seasons/{year}/types/{type}/teams/{id}/ats` |

### Betting Provider IDs

| Provider | ID |
|----------|-----|
| Caesars | 38 |
| Bet365 | 2000 |
| DraftKings | 41 |

### Examples
```bash
# NFL game odds
https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{eventId}/competitions/{eventId}/odds

# NBA win probabilities
https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{eventId}/competitions/{eventId}/probabilities

# NFL futures
https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2025/futures
```

---

## 18. Advanced / Core API Endpoints

Base: `sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}`

| Resource | Path |
|----------|------|
| Athletes | `/athletes?limit=1000` |
| Active Athletes | `/athletes?limit=1000&active=true` |
| Seasons | `/seasons` |
| Teams (Season) | `/seasons/{year}/teams` |
| Draft | `/seasons/{year}/draft` |
| Events | `/events?dates=2024` |
| Venues | `/venues?limit=500` |
| Franchises | `/franchises` |
| Positions | `/positions` |
| Play-by-Play | `/events/{eventId}/competitions/{eventId}/plays?limit=400` |

### Core API v3 (newer)
```bash
# All NFL athletes (v3)
https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=1000&active=true
```

---

## 19. Athlete Detail Endpoints

Base: `site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}`

| Resource | Path |
|----------|------|
| Overview | `/overview` |
| Game Log | `/gamelog` |
| Splits | `/splits` |
| Stats | `/stats` |

### Examples
```bash
# Patrick Mahomes overview
https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/3139477/overview

# LeBron James game log
https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/1966/gamelog
```

---

## 20. CDN Endpoints (Live/Fast Data)

These are CDN-optimized and faster for live data. Always include `?xhr=1`.

| Resource | URL |
|----------|-----|
| Scoreboard | `cdn.espn.com/core/{league}/scoreboard?xhr=1` |
| Boxscore | `cdn.espn.com/core/{league}/boxscore?xhr=1&gameId={id}` |
| Play-by-Play | `cdn.espn.com/core/{league}/playbyplay?xhr=1&gameId={id}` |
| Schedule | `cdn.espn.com/core/{league}/schedule?xhr=1` |
| Standings | `cdn.espn.com/core/{league}/standings?xhr=1` |

### League slugs for CDN
`nfl`, `nba`, `mlb`, `nhl`, `college-football`, `mens-college-basketball`

### Examples
```bash
# Live NFL scoreboard
https://cdn.espn.com/core/nfl/scoreboard?xhr=1

# Live NBA boxscore
https://cdn.espn.com/core/nba/boxscore?xhr=1&gameId=401584793
```

---

## 21. Search API

```bash
# Search for players, teams, etc.
https://site.web.api.espn.com/apis/common/v3/search?query=mahomes&limit=10
```

---

## 22. Fantasy Sports API

Base: `https://fantasy.espn.com/apis/v3/games/{sport_code}/seasons/{year}`

### Game Codes

| Sport | Code |
|-------|------|
| Football | `ffl` |
| Basketball | `fba` |
| Baseball | `flb` |
| Hockey | `fhl` |

### League Endpoints
```bash
# Get league data (public leagues)
GET /apis/v3/games/ffl/seasons/2024/segments/0/leagues/{league_id}

# With views (combine multiple with repeated ?view= params)
?view=mTeam
?view=mRoster
?view=mMatchup
?view=mSettings
?view=mDraftDetail
```

### Authentication for Private Leagues
Requires cookies: `espn_s2` and `SWID` (extract from browser after ESPN login)

### X-Fantasy-Filter Header
For filtering player data, send as JSON header:
```json
{
  "players": {
    "filterSlotIds": {"value": [0,1,2]},
    "sortPercOwned": {"sortAsc": false, "sortPriority": 1},
    "limit": 50
  }
}
```

---

## 23. Parameters Reference

### Common Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `dates` | Filter by date (YYYYMMDD) | `20241215` or `20241201-20241231` |
| `week` | Week number | `1` through `18` |
| `seasontype` | Season type | `1`=preseason, `2`=regular, `3`=postseason |
| `season` | Year | `2024` |
| `limit` | Results limit | `100`, `1000` |
| `groups` | Conference ID | `8` (SEC) |
| `enable` | Include extra data | `roster,stats,projection` |
| `xhr` | CDN flag | `1` |

### Season Types

| Type | Value |
|------|-------|
| Preseason | 1 |
| Regular Season | 2 |
| Postseason | 3 |
| Off Season | 4 |

---

## 24. Python Client Template

```python
import httpx
import asyncio
from typing import Optional
from datetime import datetime

class ESPNClient:
    """Async ESPN API client for bot integration."""

    SITE_API = "https://site.api.espn.com/apis/site/v2/sports"
    CORE_API = "https://sports.core.api.espn.com/v2/sports"
    WEB_API = "https://site.web.api.espn.com/apis/common/v3/sports"
    CDN_API = "https://cdn.espn.com/core"

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"Accept": "application/json"},
            timeout=30.0
        )

    async def get_scoreboard(
        self,
        sport: str,
        league: str,
        dates: Optional[str] = None,
        week: Optional[int] = None,
        seasontype: Optional[int] = None
    ) -> dict:
        """Get scoreboard for any sport/league."""
        params = {}
        if dates:
            params["dates"] = dates
        if week:
            params["week"] = week
        if seasontype:
            params["seasontype"] = seasontype

        url = f"{self.SITE_API}/{sport}/{league}/scoreboard"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_teams(self, sport: str, league: str) -> dict:
        """Get all teams for a sport/league."""
        url = f"{self.SITE_API}/{sport}/{league}/teams"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_team(
        self,
        sport: str,
        league: str,
        team_id: int,
        enable: Optional[str] = None
    ) -> dict:
        """Get team details."""
        params = {}
        if enable:
            params["enable"] = enable
        url = f"{self.SITE_API}/{sport}/{league}/teams/{team_id}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_standings(self, sport: str, league: str) -> dict:
        """Get standings for a sport/league."""
        url = f"{self.SITE_API}/{sport}/{league}/standings"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_game_summary(
        self,
        sport: str,
        league: str,
        event_id: int
    ) -> dict:
        """Get detailed game summary."""
        url = f"{self.SITE_API}/{sport}/{league}/summary"
        response = await self.client.get(url, params={"event": event_id})
        response.raise_for_status()
        return response.json()

    async def get_game_odds(
        self,
        sport: str,
        league: str,
        event_id: int
    ) -> dict:
        """Get betting odds for a game."""
        url = (
            f"{self.CORE_API}/{sport}/leagues/{league}"
            f"/events/{event_id}/competitions/{event_id}/odds"
        )
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_win_probabilities(
        self,
        sport: str,
        league: str,
        event_id: int
    ) -> dict:
        """Get win probabilities for a game."""
        url = (
            f"{self.CORE_API}/{sport}/leagues/{league}"
            f"/events/{event_id}/competitions/{event_id}/probabilities"
        )
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_athlete_overview(
        self,
        sport: str,
        league: str,
        athlete_id: int
    ) -> dict:
        """Get athlete profile and stats overview."""
        url = f"{self.WEB_API}/{sport}/{league}/athletes/{athlete_id}/overview"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_athlete_gamelog(
        self,
        sport: str,
        league: str,
        athlete_id: int
    ) -> dict:
        """Get athlete game log."""
        url = f"{self.WEB_API}/{sport}/{league}/athletes/{athlete_id}/gamelog"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_live_scoreboard(self, league: str) -> dict:
        """Get live scoreboard via CDN (faster)."""
        url = f"{self.CDN_API}/{league}/scoreboard"
        response = await self.client.get(url, params={"xhr": 1})
        response.raise_for_status()
        return response.json()

    async def get_live_boxscore(self, league: str, game_id: int) -> dict:
        """Get live boxscore via CDN."""
        url = f"{self.CDN_API}/{league}/boxscore"
        response = await self.client.get(
            url, params={"xhr": 1, "gameId": game_id}
        )
        response.raise_for_status()
        return response.json()

    async def search(self, query: str, limit: int = 10) -> dict:
        """Search ESPN for players, teams, etc."""
        url = "https://site.web.api.espn.com/apis/common/v3/search"
        response = await self.client.get(
            url, params={"query": query, "limit": limit}
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()


# === USAGE EXAMPLES ===
async def main():
    espn = ESPNClient()

    # Get today's NBA scoreboard
    nba_scores = await espn.get_scoreboard("basketball", "nba")
    print(f"NBA games today: {len(nba_scores.get('events', []))}")

    # Get NFL standings
    nfl_standings = await espn.get_standings("football", "nfl")

    # Get Premier League scores
    epl_scores = await espn.get_scoreboard("soccer", "eng.1")

    # Get odds for NFL game
    odds = await espn.get_game_odds("football", "nfl", event_id=401547417)

    await espn.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 25. All Sports & League Codes

### Complete Sport/League Mapping for URL Construction

| Sport Category | Sport Slug | League Slug | Example Scoreboard URL |
|---------------|-----------|-------------|----------------------|
| American Football | `football` | `nfl` | `.../sports/football/nfl/scoreboard` |
| American Football | `football` | `college-football` | `.../sports/football/college-football/scoreboard` |
| Basketball | `basketball` | `nba` | `.../sports/basketball/nba/scoreboard` |
| Basketball | `basketball` | `wnba` | `.../sports/basketball/wnba/scoreboard` |
| Basketball | `basketball` | `mens-college-basketball` | `.../sports/basketball/mens-college-basketball/scoreboard` |
| Basketball | `basketball` | `womens-college-basketball` | `.../sports/basketball/womens-college-basketball/scoreboard` |
| Baseball | `baseball` | `mlb` | `.../sports/baseball/mlb/scoreboard` |
| Hockey | `hockey` | `nhl` | `.../sports/hockey/nhl/scoreboard` |
| Soccer | `soccer` | `eng.1` | `.../sports/soccer/eng.1/scoreboard` |
| Soccer | `soccer` | `esp.1` | `.../sports/soccer/esp.1/scoreboard` |
| Soccer | `soccer` | `ger.1` | `.../sports/soccer/ger.1/scoreboard` |
| Soccer | `soccer` | `ita.1` | `.../sports/soccer/ita.1/scoreboard` |
| Soccer | `soccer` | `fra.1` | `.../sports/soccer/fra.1/scoreboard` |
| Soccer | `soccer` | `usa.1` | `.../sports/soccer/usa.1/scoreboard` |
| Soccer | `soccer` | `uefa.champions` | `.../sports/soccer/uefa.champions/scoreboard` |
| Soccer | `soccer` | `uefa.europa` | `.../sports/soccer/uefa.europa/scoreboard` |
| Soccer | `soccer` | `fifa.world` | `.../sports/soccer/fifa.world/scoreboard` |
| Soccer | `soccer` | `mex.1` | `.../sports/soccer/mex.1/scoreboard` |
| Soccer | `soccer` | `ned.1` | `.../sports/soccer/ned.1/scoreboard` |
| Soccer | `soccer` | `por.1` | `.../sports/soccer/por.1/scoreboard` |
| Soccer | `soccer` | `sco.1` | `.../sports/soccer/sco.1/scoreboard` |
| Soccer | `soccer` | `bra.1` | `.../sports/soccer/bra.1/scoreboard` |
| Soccer | `soccer` | `conmebol.libertadores` | `.../sports/soccer/conmebol.libertadores/scoreboard` |
| MMA | `mma` | `ufc` | `.../sports/mma/ufc/scoreboard` |
| Golf | `golf` | `pga` | `.../sports/golf/pga/scoreboard` |
| Golf | `golf` | `lpga` | `.../sports/golf/lpga/scoreboard` |
| Golf | `golf` | `eur` | `.../sports/golf/eur/scoreboard` |
| Racing | `racing` | `f1` | `.../sports/racing/f1/scoreboard` |
| Racing | `racing` | `nascar-premier` | `.../sports/racing/nascar-premier/scoreboard` |
| Racing | `racing` | `irl` | `.../sports/racing/irl/scoreboard` |
| Tennis | `tennis` | `atp` | `.../sports/tennis/atp/scoreboard` |
| Tennis | `tennis` | `wta` | `.../sports/tennis/wta/scoreboard` |
| Rugby | `rugby` | `rugby-union` | `.../sports/rugby/rugby-union/scoreboard` |
| Cricket | `cricket` | (varies) | `.../sports/cricket/scoreboard` |
| Lacrosse | `lacrosse` | `pll` | `.../sports/lacrosse/pll/scoreboard` |
| Boxing | `boxing` | (default) | `.../sports/boxing/scoreboard` |

### Important Bot Integration Notes

1. **No auth required** — just hit the endpoints directly. No API key needed.

2. **Rate limiting** — unofficial, but be respectful. Implement caching (60s minimum for scoreboards, 5min for standings/teams).

3. **Event IDs** — get from scoreboard response → `events[].id`. Use this ID for odds, probabilities, summary, boxscore.

4. **Date format** — always `YYYYMMDD` (e.g., `20241215`). Date ranges: `YYYYMMDD-YYYYMMDD`.

5. **CDN vs Site API** — CDN endpoints (`cdn.espn.com`) are faster for live data. Always include `?xhr=1`.

6. **Odds data** — available via Core API, not Site API. Different base URL pattern.

7. **Soccer leagues** — use the code directly in the URL (e.g., `eng.1` for Premier League). Full list above.

8. **Response structure** — scoreboards return `{events: [...]}`. Each event has `competitions[0]` with `competitors`, `odds`, `status`, etc.
