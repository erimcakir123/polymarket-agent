# PandaScore Data Enrichment — Design Spec

**Date:** 2026-04-01
**Scope:** Enrich AI analyst prompts for esports markets with roster data, tournament context, tier-based performance, LAN/online split, game duration, and enhanced H2H from PandaScore free tier.
**Files affected:** `src/esports_data.py`, `src/ai_analyst.py`

---

## 1. Problem

The AI analyst currently receives shallow esports data:
- Team W/L record (last 20 matches)
- Last 5 recent match results (opponent, score, tournament, date)
- Head-to-head count (wins only, no context)
- Tournament name + tier + format

**Missing signals available in free tier:**
- Roster/player list (stand-in detection)
- Roster change detection (comparing current vs historical)
- Tournament prizepool, type (LAN/online), country/region
- Tier-based win rate breakdown (vs Tier-S, vs Tier-A, etc.)
- LAN vs online win rate split
- Game duration (from games[].length)
- H2H with context (which roster, LAN vs online)
- Team nationality/location

**NOT available in free tier (confirmed via API test):**
- Map names (games/{id} returns 403)
- Round scores (16-9, 16-12) — not in games[] response
- Player KDA, ADR, headshot% — requires Historical plan (€150/mo)
- Map pool win rates — impossible without map names

---

## 2. PandaScore API — Verified Free Tier Endpoints

All confirmed working via live API test on 2026-04-01.

### 2.1 Teams with Roster (EXISTING — enhance parsing)

```
GET https://api.pandascore.co/{game}/teams?search[name]={name}&per_page=5
```

Already called in `get_team_recent_results()`. Currently we only use `id` and `name`.

**Fields we're ignoring but available:**
```json
{
  "id": 3216,
  "name": "Natus Vincere",
  "acronym": "NAVI",
  "location": "UA",
  "players": [
    {
      "id": 17688,
      "name": "Aleksib",
      "role": null,
      "active": true,
      "nationality": "FI",
      "age": 29,
      "birthday": "1997-03-30",
      "first_name": "Aleksi",
      "last_name": "Virolainen"
    }
  ]
}
```

**New data to extract:** `location`, `players[]` (name, nationality, active status)

### 2.2 Past Matches with Games Detail (EXISTING — enhance parsing)

```
GET https://api.pandascore.co/{game}/matches/past?filter[opponent_id]={id}&per_page=20&sort=-scheduled_at
```

Already called. Currently we extract: winner, opponent, score, tournament name, date.

**Fields we're ignoring but available:**
```json
{
  "tournament": {
    "id": 20396,
    "name": "Playoffs",
    "tier": "s",
    "type": "offline",
    "country": "NL",
    "prizepool": "400000 United States Dollar"
  },
  "games": [
    {
      "position": 1,
      "status": "finished",
      "length": 3466,
      "winner": { "id": 3455, "type": "Team" },
      "detailed_stats": true
    }
  ],
  "match_type": "best_of",
  "number_of_games": 5
}
```

**New data to extract:**
- `tournament.tier` — for tier-based win rate
- `tournament.type` — "offline" (LAN) vs "online"
- `tournament.country` — venue location
- `tournament.prizepool` — stake context
- `games[].length` — average game duration in seconds
- `games[].winner.id` — which team won each game (for closer score analysis: 3-0 vs 3-2)

### 2.3 Tournament List (NEW endpoint)

```
GET https://api.pandascore.co/{game}/tournaments?per_page=5&sort=-begin_at
```

**Response (verified):**
```json
{
  "id": 20452,
  "name": "Playoffs",
  "tier": "c",
  "type": "online",
  "country": null,
  "region": "WEU",
  "prizepool": "20,000 United States Dollar",
  "has_bracket": true,
  "league": { "name": "European Pro League" },
  "serie": { "name": "Series 6", "year": 2026 }
}
```

**Use case:** When upcoming match's tournament is found, fetch prizepool + type + region for context. This data already comes embedded in match objects, so a separate call is only needed if the match object's tournament data is incomplete.

### 2.4 Players Search (NEW endpoint — for validation only)

```
GET https://api.pandascore.co/{game}/players?search[name]={name}&per_page=5
```

**Response (verified):**
```json
{
  "id": 64532,
  "name": "Dejluk",
  "active": true,
  "nationality": "PL",
  "current_team": { "id": 133211, "name": "DXA Esports" },
  "current_videogame": { "id": 3, "name": "Counter-Strike" }
}
```

**Note:** `role` field is `null` for CS2. Only populated for Dota2/LoL/Overwatch.
**Use case:** Cross-validation if team roster seems inconsistent. Not primary source — team endpoint already has players[].

---

## 3. Implementation Plan

### 3.1 Enhanced `get_team_recent_results()` in `esports_data.py`

Current return:
```python
{
    "team_name": "Natus Vincere",
    "wins": 15, "losses": 5, "win_rate": 0.75,
    "recent_matches": [...]
}
```

New return:
```python
{
    "team_name": "Natus Vincere",
    "location": "UA",
    "roster": ["Aleksib", "jL", "iM", "b1t", "w0nderful"],
    "wins": 15, "losses": 5, "win_rate": 0.75,
    "tier_s_record": {"w": 8, "l": 4},    # from tournament.tier
    "tier_a_record": {"w": 7, "l": 1},
    "lan_record": {"w": 7, "l": 3},        # from tournament.type == "offline"
    "online_record": {"w": 8, "l": 2},
    "recent_matches": [
        {
            "opponent": "FaZe Clan",
            "won": True,
            "score": "2-0",
            "tournament": "ESL Pro League",
            "tier": "s",
            "is_lan": False,
            "date": "2026-03-30",
            "avg_game_length_min": 47,      # from games[].length
            "game_detail": "2-0",           # map wins breakdown
        }
    ]
}
```

### 3.2 New Method: `detect_roster_changes()`

```python
def detect_roster_changes(
    self, current_roster: List[str], match_history: List[Dict]
) -> Optional[Dict]:
    """Detect roster changes by comparing current team roster
    against players who appeared in recent matches.

    Approach: Extract unique opponent team players from recent match
    data is not available (PandaScore doesn't embed per-match rosters
    in the past matches endpoint). Instead, compare current team.players[]
    against a cached previous snapshot.

    Strategy:
    1. On first call: cache current roster to logs/roster_cache.json
    2. On subsequent calls: compare current vs cached
    3. If player missing from current → flag as "departed"
    4. If new player in current → flag as "new (possible stand-in)"
    5. Update cache after comparison

    Returns: {new_players: [...], departed_players: [...]} or None
    """
```

**Roster cache file:** `logs/roster_cache.json`
```json
{
    "team_3216": {
        "name": "Natus Vincere",
        "players": ["Aleksib", "jL", "iM", "b1t", "w0nderful"],
        "updated_at": "2026-04-01T12:00:00Z"
    }
}
```

### 3.3 Enhanced `get_match_context()` in `esports_data.py`

Current context string sections:
1. Tournament name + tier + format
2. Team A record + recent matches
3. Team B record + recent matches
4. H2H count

New context string sections:
1. **Tournament block** — name, tier, prizepool, LAN/online, country
2. **Team A block** — roster, location, overall record, tier-S/A record, LAN record, recent matches (with LAN/online tag, avg duration)
3. **Team B block** — same format + roster change alert if detected
4. **H2H block** — with LAN/online context + roster note if applicable
5. **Prompt guidance** — weight roster changes, tier performance, LAN form

### 3.4 No Changes to `ai_analyst.py` Signature

The `esports_context: str` parameter in `_build_prompt()` already accepts free-form text. Only the DATA SOURCES section needs updating to reflect new available signals:

```
✓ Match Stats: Available (PandaScore)
✓ Roster/Player Data: Available (PandaScore)
✓ Tournament Context: Available (PandaScore)
```

---

## 4. API Call Budget

**Per esports market analysis:**

| Call | Count | Cache TTL | Status |
|------|-------|-----------|--------|
| `/{game}/teams?search` (existing) | 2 | 30min | Already cached |
| `/{game}/matches/past` (existing) | 2 | 30min | Already cached |
| `/{game}/matches/upcoming` (existing) | 1 | 30min | Already cached |
| **Total** | **5** | | **No new API calls** |

**Key insight:** All new data comes from fields we're already fetching but ignoring. Zero additional API calls needed. The only new endpoint (`/tournaments`) is not required because tournament data is embedded in match objects.

**Rate limit:** 1000 req/hour free tier. Current usage ~4-5 calls per market. 50 markets/day = 250 calls. Well within limit.

---

## 5. Roster Cache Strategy

- **File:** `logs/roster_cache.json`
- **TTL:** 24 hours per team entry (rosters don't change hourly)
- **Write:** Atomic tmp+replace pattern (consistent with project convention)
- **Size:** ~500 bytes per team × ~200 teams = ~100KB max
- **Cleanup:** Entries older than 30 days auto-pruned on write

---

## 6. Supported Games

All games already mapped in `esports_data.py:_GAME_SLUGS`:

| Game | PandaScore slug | Roster in teams? | Role field? | Notes |
|------|----------------|-----------------|-------------|-------|
| CS2 | `csgo` | ✅ | ❌ (null) | Primary esports market |
| Valorant | `valorant` | ✅ | ❌ (null) | Similar to CS2 |
| LoL | `lol` | ✅ | ✅ (top/jun/mid/adc/sup) | Role available |
| Dota 2 | `dota2` | ✅ | ✅ | Role available |
| R6 Siege | `r6-siege` | ✅ | ❌ | Smaller market |
| Overwatch | `ow` | ✅ | ✅ | Role available |
| Mobile Legends | `mobile-legends-bang-bang` | ✅ | ❌ | Smaller market |
| StarCraft 2 | `starcraft-2` | ✅ | ❌ | 1v1, "team" = player |

---

## 7. Error Handling

- If team search returns no players[]: skip roster section, continue with match data
- If tournament data missing prizepool: omit prizepool line, keep tier/type
- If roster_cache.json corrupt/missing: treat as first run, no change detection
- If games[].length is 0 or missing: omit duration info
- Never let enrichment failure block the analysis — graceful degradation

---

## 8. Token Cost Impact (Sonnet 4)

| Scenario | Current tokens | Enriched tokens | Diff |
|----------|---------------|-----------------|------|
| CS2 with full data | ~300 | ~550 | +250 |
| Valorant with full data | ~300 | ~550 | +250 |
| LoL (with roles) | ~300 | ~580 | +280 |
| No PandaScore data | ~0 | ~0 | 0 |

**Per analysis cost increase:** +$0.00075 (250 tokens × $3/M)
**Monthly increase (50/day, 30 days):** +$1.13

---

## 9. What We Are NOT Doing

- **NOT** calling `/games/{id}` — returns 403 on free tier
- **NOT** trying to extract map names — not in free tier response
- **NOT** adding round scores — not available without game detail
- **NOT** adding player KDA/ADR — requires €150/mo Historical plan
- **NOT** building map pool analysis — impossible without map data
- **NOT** calling `/players` as primary source — team endpoint already has players[]
- **NOT** adding live WebSocket frame data — separate feature, not in scope

---

## 10. Future Upgrade Path (if bot is profitable)

If the bot generates profit and we upgrade to PandaScore Historical plan (€150/mo):

| Feature | Free (current) | Historical plan |
|---------|---------------|-----------------|
| Map names per game | ❌ | ✅ |
| Round scores (16-9) | ❌ | ✅ |
| Player KDA, ADR, HS% | ❌ | ✅ |
| Map pool win rates | ❌ | ✅ |
| Rate limit | 1000/hr | 10000/hr |

This would unlock the "Map Win Rates" and "Round Score Depth" sections from the example prompts. The architecture should be designed so these can be plugged in later without restructuring.
