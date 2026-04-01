# ESPN Data Enrichment — Design Spec

**Date:** 2026-04-01
**Scope:** Enrich AI analyst prompts with injuries, odds, probabilities, standings, H2H, B2B detection, and venue data from ESPN's free public API.
**Files affected:** `src/sports_data.py`, `src/ai_analyst.py`, `src/espn_enrichment.py`

---

## 1. Problem

The AI analyst currently receives minimal ESPN data per market:
- Team season record (e.g., "38-29")
- Standing/seeding (e.g., "7th in Western Conference")
- Last 5 game results with scores and home/away

**Missing signals that ESPN provides for free:**
- Injury reports (OUT/DOUBTFUL/QUESTIONABLE)
- Bookmaker odds from multiple providers (DraftKings, FanDuel, Bet365)
- ESPN BPI/predictor win probabilities
- Home/Away record splits
- Back-to-back game detection
- Head-to-head season series
- Venue information
- Team season statistics (PPG, OppPPG, Net Rating)
- Streak and Last-10 record

---

## 2. ESPN API Endpoints to Add

All endpoints are free, no API key required.

### 2.1 Injuries

**Site API v2** (preferred — structured JSON):
```
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{id}/injuries
```

Response format:
```json
{
  "injuries": [
    {
      "athlete": { "id": "3136776", "displayName": "Stephen Curry", "position": { "abbreviation": "SG" } },
      "status": "Doubtful",
      "type": { "name": "knee", "description": "Knee" },
      "detail": "Left knee soreness"
    }
  ]
}
```

**Supported sports:** NBA, NHL, NFL, MLB, Soccer, College sports
**NOT supported (returns 500):** Tennis, MMA, Cricket

### 2.2 Odds (Core API v2)

```
GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/events/{id}/competitions/{id}/odds
```

Response format:
```json
{
  "items": [
    {
      "provider": { "id": "41", "name": "DraftKings", "priority": 1 },
      "spread": -3.5,
      "overUnder": 222.5,
      "homeTeamOdds": { "moneyLine": -165, "favorite": true },
      "awayTeamOdds": { "moneyLine": 140, "underdog": true },
      "open": { "spread": { "home": { "line": -4.5 } } }
    }
  ]
}
```

Provider IDs: Caesars=38, FanDuel=37, DraftKings=41, BetMGM=58, ESPN BET=68, Bet365=2000

**Supported:** All team sports (NBA, NHL, NFL, MLB, Soccer, College)
**Integration:** Already partially implemented in `sports_data.py:get_espn_odds()` — needs expansion to extract moneyline + implied probability + line movement.

### 2.3 Win Probabilities (Core API v2)

```
GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/events/{id}/competitions/{id}/probabilities
```

Response format:
```json
{
  "items": [
    {
      "homeWinPercentage": 0.634,
      "awayWinPercentage": 0.366,
      "tiePercentage": 0.0
    }
  ]
}
```

**Supported:** All sports with odds support. Pre-game only for our use case (we don't need live play-by-play probability).

### 2.4 Predictor (Core API v2)

Also available inside game `summary` response:
```json
{
  "predictor": {
    "header": "ESPN BPI Win Probability",
    "homeTeam": { "gameProjection": "63.4", "teamChanceLoss": "36.6" }
  }
}
```

### 2.5 Standings (Site API v2)

```
GET https://site.api.espn.com/apis/v2/sports/{sport}/{league}/standings
```

⚠️ Must use `/apis/v2/` NOT `/apis/site/v2/` (the latter returns a stub).

Response provides per-team:
- `wins`, `losses`, `winPercent`
- `gamesBehind`, `streak`
- `home` record, `away` record (in stats array)
- Conference/division grouping

### 2.6 Game Summary with Boxscore

```
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={id}
```

Contains: boxscore (team stats, player stats), plays, leaders, predictor, broadcasts, venue.
We only need: `predictor` and `venue` from here. Player-level boxscore is too much data for the prompt.

---

## 3. Implementation Plan

### 3.1 New Methods in `sports_data.py`

```python
def get_team_injuries(self, sport: str, league: str, team_id: str) -> List[Dict]:
    """Fetch injury report for a team.

    Returns list of: {player, status, detail, position}
    Status values: "Out", "Doubtful", "Questionable", "Day-To-Day", "Probable"

    Skips call for tennis/mma/cricket (returns 500).
    """

def get_standings_context(self, sport: str, league: str, team_id: str) -> Optional[Dict]:
    """Fetch team's standings data.

    Returns: {wins, losses, win_pct, home_record, away_record,
              streak, last_10, games_behind, conference_rank}

    Uses /apis/v2/ path (not /apis/site/v2/).
    Cache for 6 hours (standings don't change rapidly).
    """

def get_event_odds(self, sport: str, league: str, event_id: str, comp_id: str) -> Optional[Dict]:
    """Fetch bookmaker odds for an event.

    Returns: {providers: [{name, moneyline_home, moneyline_away, spread,
              implied_home_pct, implied_away_pct}],
              avg_implied_home, avg_implied_away, line_movement}

    Enhances existing get_espn_odds() with multi-provider support.
    """

def get_event_probabilities(self, sport: str, league: str, event_id: str, comp_id: str) -> Optional[Dict]:
    """Fetch ESPN BPI/predictor win probability.

    Returns: {home_win_pct, away_win_pct, tie_pct}
    """

def detect_back_to_back(self, recent_games: List[Dict]) -> bool:
    """Check if team played yesterday (back-to-back).

    Scans recent_games dates. If most recent game was yesterday, return True.
    """

def get_head_to_head(self, sport: str, league: str, team_a_id: str, team_b_id: str) -> List[Dict]:
    """Find H2H matchups this season from team schedule.

    Scans team_a's schedule for completed games vs team_b.
    Returns: [{date, home_team, away_team, score, winner}]

    No extra API call needed — reuse cached schedule data.
    """
```

### 3.2 Enhanced `_get_team_match_context()` in `sports_data.py`

Current flow:
```
get_team_record() → _get_team_match_context() → context string
```

New flow:
```
get_team_record()          → season record + recent games
get_team_injuries()        → injury list (skip tennis/mma)
get_standings_context()    → home/away split, streak, last 10
detect_back_to_back()      → B2B flag (from recent games, no API call)
get_head_to_head()         → H2H (from cached schedule, no API call)
─── requires event_id ───
get_event_odds()           → bookmaker odds
get_event_probabilities()  → ESPN predictor %
                           ↓
_get_team_match_context()  → enriched context string
```

### 3.3 Event ID Discovery

Odds/probabilities require `event_id` and `competition_id`. These come from the scoreboard endpoint which we already call.

Current `_find_espn_event()` in `sports_data.py` already returns `(event_id, comp_id, ...)`. We'll reuse this.

### 3.4 Prompt Format Changes in `ai_analyst.py`

The `esports_context` parameter already accepts a free-form string. No changes needed to `_build_prompt()` signature — only the content of the string changes.

New sections added to context string:
```
=== BOOKMAKER ODDS ===
(provider lines, implied probabilities, line movement)

=== ESPN PREDICTOR ===
(BPI win probability)

=== SPORTS DATA (ESPN) -- {league} ===
VENUE: ...
TEAM A: ... (record) -- standing
  Home: W-L | Away: W-L
  Last 10: W-L | Streak: ...
  Last 5 games: ...
  Season Stats: PPG ... | OppPPG ... | Net Rtg ...
  ⚠️ SCHEDULE: BACK-TO-BACK (if applicable)
  Injuries: ...

TEAM B: ... (same format)

HEAD-TO-HEAD (this season): ...
```

### 3.5 Sport-Specific Handling

| Sport | Injuries | Odds | Probabilities | Standings | H2H | B2B |
|-------|----------|------|---------------|-----------|-----|-----|
| NBA | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| NHL | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| NFL | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (weekly) |
| MLB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Soccer | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (weekly) |
| College BB | ✅ | ✅ | ✅ | ✅ (rankings) | ✅ | ✅ |
| Tennis | ❌ (500) | ✅ | ✅ | ❌ (rankings) | ✅ (from scoreboard scan) | ❌ |
| MMA | ❌ (500) | ✅ | ✅ | ❌ | ✅ (from scoreboard scan) | ❌ |
| Cricket | ❌ (no data) | ✅ | ✅ | ✅ | ✅ | ❌ |

### 3.6 `DATA SOURCES` Section Update

The `_build_prompt()` in `ai_analyst.py` currently shows:
```
✓ Match Stats: Available
✗ Bookmaker Odds: Not available
```

After enrichment, it will show:
```
✓ Match Stats: Available (ESPN)
✓ Bookmaker Odds: Available (ESPN Core API — 3 providers)
✓ ESPN Win Probability: Available
✓ Injury Reports: Available (both teams)
✓ Standings & Records: Available
```

This feeds into the confidence grading rules. With odds + stats + injuries, the AI can confidently assign **A confidence** instead of B+.

---

## 4. API Call Budget

**Per market analysis (worst case, team sport):**

| Call | Count | Cache TTL | Notes |
|------|-------|-----------|-------|
| teams/{id} (existing) | 2 | 30min | Already cached |
| teams/{id}/schedule (existing) | 2 | 30min | Already cached |
| teams/{id}/injuries | 2 | 15min | New |
| standings | 1 | 6hr | New, shared across teams |
| scoreboard (for event_id) | 1 | 5min | Already called |
| events/{id}/.../odds | 1 | 15min | Enhances existing |
| events/{id}/.../probabilities | 1 | 15min | New |
| **Total new calls** | **~5** | | |

**H2H and B2B:** Zero extra calls — derived from cached schedule data.

**Daily budget (50 markets):** ~250 new ESPN calls/day. ESPN has no published rate limit but recommends being respectful. Our 1 req/sec throttle is conservative.

---

## 5. Caching Strategy

| Data | TTL | Rationale |
|------|-----|-----------|
| Injuries | 15 min | Can change close to game time |
| Odds | 15 min | Lines move, but not every minute |
| Probabilities | 15 min | Pre-game, relatively stable |
| Standings | 6 hours | Changes only after games complete |
| Schedule/Record | 30 min | Existing, adequate |
| Scoreboard | 5 min | Existing, for event discovery |

---

## 6. Error Handling

- If injuries endpoint returns 500 (tennis/MMA): silently skip, don't add injury section
- If odds/probabilities returns 404: skip section, AI still has match stats
- If standings returns stub: try `/apis/v2/` path; if still fails, skip home/away split
- If event_id not found on scoreboard: skip odds/probabilities sections
- Never let a failed enrichment call block the entire analysis — graceful degradation

---

## 7. Confidence Grade Impact

Current grading in system prompt:
```
- "A"  = 2+ independent sources agree (bookmaker odds + match stats)
- "B+" = at least one strong source (bookmaker odds alone OR 5+ match history)
- "B-" = minimal data (1-4 matches)
- "C"  = no statistical data
```

After enrichment:
- Most NBA/NHL/NFL/MLB markets: **A** (odds + stats + injuries = 3 independent sources)
- Soccer with odds: **A** (odds + stats)
- Tennis without odds: **B+** (match stats from scoreboard scan)
- Markets where ESPN has no coverage: unchanged

---

## 8. Token Cost Impact (Sonnet 4)

| Scenario | Current tokens | Enriched tokens | Cost/analysis | Monthly (50/day) |
|----------|---------------|-----------------|---------------|------------------|
| NBA with all data | ~1100 | ~1600 | $0.0078 | $11.70 |
| Soccer with odds | ~1100 | ~1500 | $0.0075 | $11.25 |
| Tennis (no injuries) | ~1000 | ~1300 | $0.0069 | $10.35 |
| No ESPN data | ~800 | ~800 | $0.0054 | $8.10 |

**Max monthly increase: ~$2.25/month** (from $9.45 to $11.70)

---

## 9. Files to Modify

| File | Changes |
|------|---------|
| `src/sports_data.py` | Add 5 new methods: injuries, standings, odds enhancement, probabilities, B2B detection. Enhance `_get_team_match_context()` and `_get_athlete_match_context()`. |
| `src/ai_analyst.py` | Update `_build_prompt()` DATA SOURCES section to reflect new sources. Update confidence grade rules in system prompt. |
| `src/espn_enrichment.py` | May need updates if it currently handles any of these (check before implementing). |
| `src/config.py` | No changes needed — no new config parameters. |

---

## 10. What We Are NOT Doing

- **NOT** adding player-level boxscore stats to prompt (too many tokens, AI doesn't need per-player stats for moneyline prediction)
- **NOT** calling CDN game package endpoint (complex parsing, not needed)
- **NOT** adding fantasy/draft data
- **NOT** adding ATS (against the spread) records — we only bet moneyline
- **NOT** calling athlete splits/gamelog — too granular, diminishing returns
- **NOT** adding season futures odds
