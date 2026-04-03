# PandaScore — Complete Reference Index

> **File:** `pandascore-complete-reference.md` (2354 lines)
> **Usage:** `Read("guide yazım/pandascore-complete-reference.md", offset=START, limit=SIZE)`

---

## Quick Reference

| Item | Value |
|------|-------|
| Base URL | `https://api.pandascore.co` |
| WebSocket URL | `wss://live.pandascore.co` |
| Auth | `Authorization: Bearer TOKEN` or `?token=TOKEN` |
| Pagination | `page[number]=1&page[size]=50` (max 100) |
| Rate Limit (Free) | 1,000 req/hr |
| Rate Limit (Paid) | 10,000 req/hr |
| Date Format | ISO-8601 UTC |
| CDN | `https://cdn.pandascore.co/images/...` |

### Data Hierarchy
```
League → Series → Tournament → Match → Game
```

### Plans
| Plan | Access |
|------|--------|
| Fixtures (Free) | Schedules, results, basic match data |
| Historical | Post-game stats, player/team performance |
| Real-time (Basic) | WebSocket frames |
| Real-time (Pro) | WebSocket frames + events |

### Game Prefixes
| Game | Prefix | Has Stats/Games? |
|------|--------|------------------|
| Counter-Strike | `/csgo/` | Yes (Historical) |
| Dota 2 | `/dota2/` | Yes (Historical) |
| League of Legends | `/lol/` | Yes (Historical) |
| Valorant | `/valorant/` | Yes (Historical) |
| Overwatch | `/ow/` | Yes (Historical) |
| EA Sports FC | `/fifa/` | No (Fixtures only) |
| King of Glory | `/kog/` | No |
| LoL Wild Rift | `/lol-wild-rift/` | No |
| Mobile Legends | `/mlbb/` | No |
| PUBG | `/pubg/` | No |
| R6 Siege | `/r6siege/` | No |
| Rocket League | `/rl/` | No |
| StarCraft 2 | `/starcraft-2/` | No |
| SC Brood War | `/starcraft-brood-war/` | No |
| Call of Duty | `/codmw/` | No |

---

## PART 1: Documentation (Guides & Tutorials)

| Section | Content | Lines |
|---------|---------|-------|
| Header + Overview | Title, base URLs, generated date | 1–10 |
| **SECTION 1: Get Started** | | |
| Page 1: Introduction | Data coverage, plans, common apps | 16–62 |
| Page 2: Fundamentals | League→Series→Tournament→Match→Game | 65–108 |
| Page 3: Authentication | Bearer token, URL param, WebSocket auth | 111–145 |
| Page 4: Rate Limits | Plan limits, X-Rate-Limit-Remaining | 148–167 |
| **SECTION 2: Tutorials** | | |
| Page 5: First Request | Postman, /matches/636351 | 173–197 |
| Page 6: Discord Score-Bot | Match polling, notifications, filters | 199–247 |
| **SECTION 3: Upgrade Guides** | | |
| Page 7: CS2 Migration | MR12, videogame_title filter | 253–282 |
| **SECTION 4: REST API** | | |
| Page 8: Formats | JSON, null fields, ISO-8601 | 288–296 |
| Page 9: Tracking Changes | /additions, /changes, /deletions | 298–340 |
| Page 10: Tournaments | Rosters, brackets, standings, tiers | 342–372 |
| Page 11: Match Lifecycle | FSM: not_started→running→finished | 374–411 |
| Page 12: Match Formats | best_of, first_to, red_bull_home_ground | 413–435 |
| Page 13: Filtering & Sorting | filter[], search[], range[], sort | 437–466 |
| Page 14: Pagination | page[number], page[size], Link header | 468–495 |
| Page 15: Errors | 400–429 client, 5xx server | 497–520 |
| Page 16: Image Optimization | normal_, thumb_ CDN prefixes | 522–534 |
| Page 17: Players' Age | age vs birthday fields | 536–543 |
| Page 18: FAQ | status vs complete, detailed_stats | 545–564 |
| **SECTION 5: Live API** | | |
| Page 19: WebSocket Overview | /lives, frames, events, 3 connections | 570–624 |
| Page 20: Data Samples | Frame/Event structure intro | 626–632 |
| Page 21: CS Data Sample | Frames (teams, players), Events (kill, round) | 634–652 |
| Page 22: Dota 2 Data Sample | Frames (dire/radiant, towers, barracks) | 654–665 |
| Page 23: LoL Data Sample | Frames (red/blue, drakes), Events (kill_feed) | 667–685 |
| Page 24: Events Recovery | Recover message, game_id | 687–712 |
| Page 25: Disconnections | Status codes 1000, 4001, 4003, 4029 | 714–728 |
| Page 26: Sandbox | POST /api/lol/replay, /api/csgo/replay | 730–771 |
| **SECTION 6: Esports** | | |
| Page 27: Seasons & Circuits | Dota2, CS, LoL, RL, OW structures | 777–795 |
| Page 28: Dota 2 | Heroes, 1-5 role system | 797–810 |
| Page 29: League of Legends | Champions, patches, versioning | 812–828 |
| Page 30: Overwatch | Heroes, maps, game modes | 830–848 |

---

## PART 2: API Reference (All Endpoints)

| Section | Content | Lines |
|---------|---------|-------|
| Common Parameters & Response Codes | Shared params, HTTP codes | 860–885 |
| **Incidents** | /additions, /changes, /deletions, /incidents | 887–950 |
| **Videogames** | /videogames, versions, titles, leagues, series | 952–985 |
| **Lives** | /lives (WebSocket-ready matches) | 987–1000 |
| **Leagues** | /leagues, get by ID, matches, series, tournaments | 1002–1060 |
| **Matches** | /matches, past/running/upcoming, opponents | 1062–1145 |
| **Players** | /players, get by ID, leagues/matches/series/tournaments | 1147–1195 |
| **Series** | /series, past/running/upcoming, get by ID, matches, tournaments | 1197–1240 |
| **Teams** | /teams, get by ID, leagues/matches/series/tournaments | 1242–1280 |
| **Tournaments** | /tournaments, brackets, rosters, standings, teams | 1282–1365 |
| **Counter-Strike** | Games, rounds, events, maps, weapons, stats (33 endpoints) | 1367–1510 |
| **Dota 2** | Games, frames, heroes, abilities, items, stats (33 endpoints) | 1512–1640 |
| **League of Legends** | Games, events, frames, champions, items, runes, spells, stats (48 endpoints) | 1642–1850 |
| **Valorant** | Games, rounds, events, agents, abilities, maps, weapons, stats (39 endpoints) | 1852–1985 |
| **Overwatch** | Games, heroes, maps, stats (27 endpoints) | 1987–2070 |
| **EA Sports FC** | Standard pattern, /fifa/ prefix (15 endpoints) | 2072–2095 |
| **King of Glory** | Standard pattern, /kog/ prefix (15 endpoints) | 2097–2120 |
| **LoL Wild Rift** | Standard pattern, /lol-wild-rift/ prefix (15 endpoints) | 2122–2145 |
| **Mobile Legends** | Standard pattern, /mlbb/ prefix (15 endpoints) | 2147–2170 |
| **PUBG** | Standard pattern, /pubg/ prefix (15 endpoints) | 2172–2195 |
| **Rainbow Six Siege** | Standard pattern, /r6siege/ prefix (15 endpoints) | 2197–2220 |
| **Rocket League** | Standard pattern, /rl/ prefix (15 endpoints) | 2222–2245 |
| **StarCraft 2** | Standard pattern, /starcraft-2/ prefix (15 endpoints) | 2247–2270 |
| **StarCraft Brood War** | Standard pattern, /starcraft-brood-war/ prefix (15 endpoints) | 2272–2295 |
| **Call of Duty** | Standard pattern, /codmw/ prefix (15 endpoints) | 2297–2320 |
| **Appendix** | Simple game pattern table, endpoint count summary | 2322–2354 |

---

## Endpoint Count Summary

| Category | Count |
|----------|-------|
| Incidents | 4 |
| All Video Games (generic) | 57 |
| Counter-Strike | 33 |
| Dota 2 | 33 |
| League of Legends | 48 |
| Valorant | 39 |
| Overwatch | 27 |
| Simple games (10 x 15) | 150 |
| **TOTAL** | **~251** |

---

## Key Response Schemas (Quick Lookup)

| Schema | Where to find | Lines |
|--------|---------------|-------|
| Match Object | PART 2 > Matches | ~1080–1140 |
| Player Object | PART 2 > Players | ~1155–1185 |
| Team Object | PART 2 > Teams | ~1250–1270 |
| Serie Object | PART 2 > Series | ~1205–1235 |
| Tournament Object | PART 2 > Tournaments | ~1295–1355 |
| League Object | PART 2 > Leagues | ~1010–1045 |
| CS Game + Rounds | PART 2 > Counter-Strike | ~1375–1480 |
| Dota 2 Game + Stats | PART 2 > Dota 2 | ~1530–1620 |
| LoL Game + Stats | PART 2 > League of Legends | ~1670–1800 |
| Valorant Game + Rounds | PART 2 > Valorant | ~1870–1950 |
| OW Game + Heroes | PART 2 > Overwatch | ~1995–2060 |
| Incident Object | PART 2 > Incidents | ~895–930 |
