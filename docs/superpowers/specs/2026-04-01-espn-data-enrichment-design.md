# ESPN Data Enrichment — Design Spec

**Date:** 2026-04-01
**Scope:** Enrich AI analyst prompts with injuries, ESPN BPI predictor, standings, H2H, B2B detection, and venue data from ESPN's free public API. Bookmaker odds come from The Odds API (paid, more bookmakers) — ESPN odds endpoint is NOT used to avoid duplicate data.
**Files affected:** `src/sports_data.py`, `src/ai_analyst.py`, `src/espn_enrichment.py`

---

## 1. Problem

The AI analyst currently receives minimal ESPN data per market:
- Team season record (e.g., "38-29")
- Standing/seeding (e.g., "7th in Western Conference")
- Last 5 game results with scores and home/away

**Missing signals that ESPN provides for free:**
- Injury reports (OUT/DOUBTFUL/QUESTIONABLE)
- ESPN BPI/predictor win probabilities (model-based, independent from bookmaker odds)
- Home/Away record splits
- Back-to-back game detection
- Head-to-head season series
- Venue information
- Team season statistics (PPG, OppPPG, Net Rating)
- Streak and Last-10 record

**NOT using from ESPN (duplicate with The Odds API):**
- Bookmaker odds (DraftKings, FanDuel, Bet365) — ~70% overlap with The Odds API which already provides 8-10 bookmakers including sharp lines (Pinnacle). Sending duplicate bookmaker data wastes tokens without adding signal.

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

### 2.2 ~~Odds (Core API v2)~~ — SKIPPED (duplicate)

**Decision:** ESPN odds endpoint shares ~70% of the same bookmakers as The Odds API (DraftKings, FanDuel, BetMGM, Bet365, Caesars). The Odds API already provides 8-10 bookmakers with historical line movement and sharp bookmaker data (Pinnacle). Adding ESPN odds would send duplicate probability data to the AI, wasting ~100 tokens per analysis with no new signal.

**Existing `get_espn_odds()` in `sports_data.py`:** Keep as fallback — if The Odds API key expires or quota runs out, ESPN odds can serve as free backup. No enhancement needed.

**What ESPN provides that The Odds API doesn't:** ESPN BPI Predictor (section 2.3/2.4 below) — this is ESPN's own win probability MODEL, completely independent from bookmaker lines.

### 2.3 ESPN BPI Predictor / Win Probabilities (Core API v2)

**This is the key ESPN-exclusive signal** — ESPN's own statistical model (BPI), completely independent from bookmaker odds. Combined with The Odds API bookmaker consensus, gives the AI two independent probability estimates.

**Option A — Probabilities endpoint:**
```
GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/events/{id}/competitions/{id}/probabilities
```

Response:
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

**Option B — Game summary (contains predictor + venue):**
```
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={id}
```

```json
{
  "predictor": {
    "header": "ESPN BPI Win Probability",
    "homeTeam": { "gameProjection": "63.4", "teamChanceLoss": "36.6" }
  }
}
```

**Implementation:** Try probabilities endpoint first (lighter response). If unavailable, fall back to summary endpoint and extract `predictor` block.

**Supported:** All team sports + Tennis + MMA. Pre-game only.

### 2.4 Standings (Site API v2)

```
GET https://site.api.espn.com/apis/v2/sports/{sport}/{league}/standings
```

⚠️ Must use `/apis/v2/` NOT `/apis/site/v2/` (the latter returns a stub).

Response provides per-team:
- `wins`, `losses`, `winPercent`
- `gamesBehind`, `streak`
- `home` record, `away` record (in stats array)
- Conference/division grouping

### 2.5 Game Summary with Boxscore

```
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={id}
```

Contains: boxscore (team stats, player stats), plays, leaders, predictor, broadcasts, venue.
We only need: `predictor` and `venue` from here. Player-level boxscore is too much data for the prompt.

---

## 2.6 Supported Sports & Leagues

All leagues already mapped in `sports_data.py:_SPORT_LEAGUES` (90+ entries). Enrichment applies to ALL of them:

**Team Sports (injuries + BPI predictor + standings + H2H + B2B):**
- Basketball: NBA, WNBA, CBB, WCBB, G-League, FIBA, NBL
- Hockey: NHL, NCAA Hockey
- Football: NFL, CFB, CFL, UFL, XFL
- Baseball: MLB, College Baseball, WBC
- Soccer: EPL, Championship, FA Cup, La Liga, La Liga 2, Copa del Rey, Bundesliga, 2.Bundesliga, DFB Pokal, Serie A, Serie B, Coppa Italia, Ligue 1, Ligue 2, Coupe de France, Super Lig, Eredivisie, Primeira Liga, Pro League (BEL), Bundesliga AT, Super League (GRE), Superliga (DEN), Eliteserien (NOR), Allsvenskan (SWE), MLS, NWSL, Liga Profesional (ARG), Brasileirao, Liga MX, J1 League, CSL, ISL, A-League, PSL, UCL, Europa League, Conference League, World Cup, Euro, Libertadores, Sudamericana, Copa America, Gold Cup, Friendlies
- Cricket: via ESPN fallback (primary is cricket_data.py)
- Rugby, AFL, Lacrosse (NLL, PLL), Volleyball (NCAA)

**Athlete Sports (BPI predictor + form, NO injuries endpoint):**
- Tennis: ATP, WTA
- MMA: UFC, Bellator, PFL
- Golf: PGA, LPGA, LIV, DP World Tour, Champions Tour

**Event Sports (recent results only — no BPI/injuries):**
- Racing: F1, IndyCar, NASCAR Cup

**Sport-specific endpoint availability:**

| Feature | Team Sports | Tennis | MMA | Golf | Racing | Cricket |
|---------|------------|--------|-----|------|--------|---------|
| Injuries | ✅ | ❌ (500) | ❌ (500) | ❌ | ❌ | ❌ |
| BPI Predictor | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Standings | ✅ | ❌ (rankings) | ❌ | ❌ | ❌ | ✅ |
| H2H | ✅ | ✅ (scoreboard scan) | ✅ (scoreboard scan) | ❌ | ❌ | ✅ |
| B2B detection | ✅ (daily sports) | ❌ | ❌ | ❌ | ❌ | ❌ |
| Venue | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ~~Odds~~ | ~~SKIPPED~~ | — | — | — | — | — |

> **Note:** Bookmaker odds come from The Odds API (paid, 8-10 bookmakers, sharp lines). ESPN odds endpoint is kept as emergency fallback only.

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

def get_espn_predictor(self, sport: str, league: str, event_id: str, comp_id: str) -> Optional[Dict]:
    """Fetch ESPN BPI/predictor win probability (ESPN's own model, NOT bookmaker odds).

    This is the key ESPN-exclusive signal — independent from The Odds API bookmaker data.
    Tries probabilities endpoint first, falls back to summary endpoint.

    Returns: {home_win_pct, away_win_pct, tie_pct, source: "espn_bpi"}
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
get_espn_predictor()       → ESPN BPI win probability (model-based, NOT bookmaker odds)
                           ↓
_get_team_match_context()  → enriched context string

Note: Bookmaker odds come from The Odds API (already integrated in odds_api.py).
ESPN get_espn_odds() kept as fallback only — not called in normal flow.
```

### 3.3 Event ID Discovery

Odds/probabilities require `event_id` and `competition_id`. These come from the scoreboard endpoint which we already call.

Current `_find_espn_event()` in `sports_data.py` already returns `(event_id, comp_id, ...)`. We'll reuse this.

### 3.4 Prompt Format Changes in `ai_analyst.py`

The `esports_context` parameter already accepts a free-form string. No changes needed to `_build_prompt()` signature — only the content of the string changes.

New sections added to context string:
```
=== ESPN BPI PREDICTOR ===
(ESPN's own win probability model — independent from bookmaker odds)

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

| Sport | Injuries | BPI Predictor | Standings | H2H | B2B |
|-------|----------|--------------|-----------|-----|-----|
| NBA | ✅ | ✅ | ✅ | ✅ | ✅ |
| NHL | ✅ | ✅ | ✅ | ✅ | ✅ |
| NFL | ✅ | ✅ | ✅ | ✅ | ❌ (weekly) |
| MLB | ✅ | ✅ | ✅ | ✅ | ✅ |
| Soccer | ✅ | ✅ | ✅ | ✅ | ❌ (weekly) |
| College BB | ✅ | ✅ | ✅ (rankings) | ✅ | ✅ |
| Tennis | ❌ (500) | ✅ | ❌ (rankings) | ✅ (scoreboard scan) | ❌ |
| MMA | ❌ (500) | ✅ | ❌ | ✅ (scoreboard scan) | ❌ |
| Cricket | ❌ (no data) | ✅ | ✅ | ✅ | ❌ |

> Bookmaker odds column removed — handled by The Odds API (`src/odds_api.py`).

### 3.6 `DATA SOURCES` Section Update

The `_build_prompt()` in `ai_analyst.py` currently shows:
```
✓ Match Stats: Available
✗ Bookmaker Odds: Not available
```

After enrichment, it will show:
```
✓ Match Stats: Available (ESPN)
✓ Bookmaker Odds: Available (The Odds API — 8-10 providers)
✓ ESPN BPI Predictor: Available (ESPN's own model — independent signal)
✓ Injury Reports: Available (both teams)
✓ Standings & Records: Available
```

This feeds into the confidence grading rules. With bookmaker odds (The Odds API) + ESPN BPI predictor + injuries + stats, the AI has **3 independent sources** → **A confidence**.

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
| ~~events/{id}/.../odds~~ | ~~1~~ | — | ~~REMOVED — duplicate with The Odds API~~ |
| events/{id}/.../probabilities | 1 | 15min | New (ESPN BPI predictor) |
| **Total new calls** | **~4** | | |

**H2H and B2B:** Zero extra calls — derived from cached schedule data.

**Daily budget (50 markets):** ~250 new ESPN calls/day. ESPN has no published rate limit but recommends being respectful. Our 1 req/sec throttle is conservative.

---

## 5. Caching Strategy

| Data | TTL | Rationale |
|------|-----|-----------|
| Injuries | 15 min | Can change close to game time |
| BPI Predictor | 15 min | Pre-game model, relatively stable |
| Standings | 6 hours | Changes only after games complete |
| Schedule/Record | 30 min | Existing, adequate |
| Scoreboard | 5 min | Existing, for event discovery |

---

## 6. Error Handling

- If injuries endpoint returns 500 (tennis/MMA): silently skip, don't add injury section
- If BPI predictor returns 404: skip section, AI still has The Odds API bookmaker data + match stats
- If standings returns stub: try `/apis/v2/` path; if still fails, skip home/away split
- If event_id not found on scoreboard: skip BPI predictor section
- If The Odds API also unavailable: fall back to `get_espn_odds()` as emergency backup
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

After enrichment (3 independent signal sources):
1. **The Odds API** — 8-10 bookmaker consensus + historical line movement
2. **ESPN BPI Predictor** — ESPN's own statistical model (independent from bookmakers)
3. **ESPN enrichment** — injuries, standings, H2H, B2B, venue

- Most NBA/NHL/NFL/MLB markets: **A** (all 3 sources available)
- Soccer with BPI: **A** (bookmaker odds + BPI + stats)
- Tennis: **A** if The Odds API has coverage, **B+** if only ESPN BPI
- Markets where ESPN has no coverage: depends on The Odds API alone

---

## 8. Token Cost Impact (Sonnet 4)

| Scenario | Current tokens | Enriched tokens | Cost/analysis | Monthly (50/day) |
|----------|---------------|-----------------|---------------|------------------|
| NBA with all data | ~1100 | ~1500 | $0.0075 | $11.25 |
| Soccer with BPI | ~1100 | ~1400 | $0.0072 | $10.80 |
| Tennis (no injuries) | ~1000 | ~1250 | $0.0068 | $10.13 |
| No ESPN data | ~800 | ~800 | $0.0054 | $8.10 |

**Max monthly increase: ~$2.00/month** (from $9.45 to $11.25)
Slightly less than before since ESPN bookmaker odds section removed (~100 tokens saved per analysis).

---

## 9. Files to Modify — Consolidation Approach (Option B)

**Decision:** Consolidate team-sport enrichment into `sports_data.py`. The existing `espn_enrichment.py` has overlapping functionality (standings, win probability via odds). Instead of two files calling similar endpoints, we merge team-sport enrichment into the main ESPN client and slim down `espn_enrichment.py` to athlete-specific extras only.

| File | Changes |
|------|---------|
| `src/sports_data.py` | Add 5 new methods: `get_team_injuries()`, `get_standings_context()`, `get_espn_predictor()`, `detect_back_to_back()`, `get_head_to_head()`. Enhance `_get_team_match_context()` to call them. Keep existing `get_espn_odds()` as emergency fallback. |
| `src/ai_analyst.py` | Update `_build_prompt()` DATA SOURCES section to reflect new sources (ESPN BPI Predictor, Injury Reports, Standings). Update confidence grade rules in system prompt. |
| `src/espn_enrichment.py` | Remove team-sport methods now handled by `sports_data.py` (`get_league_standing()`, `get_win_probability()`, `get_cdn_scoreboard()`). Keep athlete-specific methods (`get_athlete_overview()`, `get_athlete_splits()`, `get_rankings()`, `get_h2h()`). Update `enrich()` to only handle athlete sports — team sports enrichment flows through `sports_data.py._get_team_match_context()`. |
| `src/config.py` | No changes needed — no new config parameters. |

**Migration safety:** Team-sport callers that used `ESPNEnrichment.enrich()` will now get richer data from `sports_data.py` directly. The `enrich()` method still works for athlete sports (tennis, MMA, golf). No circular imports — `espn_enrichment.py` depends on `sports_data.py` (not the other way).

---

## 10. What We Are NOT Doing

- **NOT** using ESPN odds endpoint as primary source — ~70% overlap with The Odds API (DraftKings, FanDuel, BetMGM, Bet365, Caesars). Kept as fallback only.
- **NOT** adding player-level boxscore stats to prompt (too many tokens, AI doesn't need per-player stats for moneyline prediction)
- **NOT** calling CDN game package endpoint (complex parsing, not needed)
- **NOT** adding fantasy/draft data
- **NOT** adding ATS (against the spread) records — we only bet moneyline
- **NOT** calling athlete splits/gamelog — too granular, diminishing returns
- **NOT** adding season futures odds
