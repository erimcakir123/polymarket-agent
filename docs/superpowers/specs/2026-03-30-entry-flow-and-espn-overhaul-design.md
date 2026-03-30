# Entry Flow Fix + ESPN Overhaul — Design Spec

## Problem Statement

The bot has 2 categories of failure:

**Category A — Entry flow timing & ranking:**
1. Enters finished esports matches (esports excluded from all time filters)
2. Cannot find close/imminent matches (`_hours_to_start` uses `end_date_iso` instead of `match_start_iso`)
3. 100% favorites, zero underdogs (ranking formula penalizes underdogs 2-3x)
4. Esports slug mismatch (Polymarket tags don't map to PandaScore API slugs)
5. PandaScore C/D tier filter deletes 60-70% of esports match history

**Category B — ESPN data gaps:**
6. Tennis returns zero match data (code only fetches player name, never stats/history)
7. MMA returns zero fight data (same broken code path as tennis)
8. Soccer has only 6 leagues mapped (ESPN supports 50+)
9. Basketball, hockey, football missing secondary leagues
10. Golf, Racing, Rugby, AFL, Lacrosse, Volleyball, Field Hockey not integrated at all
11. Thin data threshold (5 match results) rejects 68% of markets

Combined result: 120 markets scanned → 82 rejected (thin data) → only 6 qualify.

## Design

### Part A: Entry Flow Fixes (4 files)

#### A1. `_hours_to_start()` — Use match_start_iso (entry_gate.py)

Current: Uses `end_date_iso` (market close date, not match start). Esports have empty `end_date_iso` → returns 99h → always discovery bucket.

Fix: Use `match_start_iso` (Gamma event.startTime) as primary. Proven accurate for both sports and esports (Sinners 08:10, Passion UA 11:15 — both correct).

```python
def _hours_to_start(market) -> float:
    # Primary: Gamma event startTime (accurate for sports + esports)
    start_iso = getattr(market, "match_start_iso", "") or ""
    if start_iso:
        try:
            start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            return (start_dt - datetime.now(timezone.utc)).total_seconds() / 3600
        except (ValueError, TypeError):
            pass
    # Fallback: Polymarket end date
    end_iso = getattr(market, "end_date_iso", "") or ""
    if not end_iso:
        return 99.0
    try:
        end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        return (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600
    except (ValueError, TypeError):
        return 99.0
```

#### A2. Remove esports time filter exemption (market_scanner.py)

Current (lines 329-349): Esports explicitly excluded from `event_ended` check and late-match elapsed% check with comment "Gamma API/Polymarket startTime unreliable for esports".

Fix: Remove the esports exemption. `match_start_iso` is proven reliable. All sports go through the same time filters.

#### A3. Edge-only ranking (entry_gate.py)

Current (line 611): `rank_score = (direction_prob + edge) * conf_score`
- 85% favorite with 5% edge: (0.85 + 0.05) * 1.0 = 0.90
- 55% underdog with 5% edge: (0.55 + 0.05) * 1.0 = 0.60

Fix: `rank_score = edge * conf_score`
- Both get 0.05 * 1.0 = 0.05 — equal ranking for equal edge.

#### A4. Esports slug fix (esports_data.py)

Restore comprehensive `_GAME_SLUGS` mapping that was in the auto-commit:

```python
_GAME_SLUGS = {
    "cs2": "csgo", "csgo": "csgo", "counter-strike": "csgo", "cs-go": "csgo",
    "lol": "lol", "league-of-legends": "lol",
    "dota2": "dota2", "dota-2": "dota2",
    "valorant": "valorant",
    "r6-siege": "r6-siege",
    "ow": "ow", "overwatch": "ow",
    "mobile-legends": "mobile-legends-bang-bang",
    "starcraft-2": "starcraft-2", "starcraft": "starcraft-2",
}
```

Plus normalize PandaScore `videogame.slug` in `detect_game()` dynamic search path.

#### A5. Remove PandaScore C/D tier filter (esports_data.py)

Current (lines 277-280):
```python
tier = (m.get("tournament", {}).get("tier") or "").lower()
if tier in ("d", "c"):
    continue
```

Fix: Remove entirely. Include all tiers. User decision: all data is valuable, manipulation risk accepted.

#### A6. Stale match guard (esports_data.py)

Add guard in `get_match_context()`: if PandaScore upcoming match `status == "running"` and `scheduled_at` is >4h ago, return None. Prevents entering finished esports matches that PandaScore still reports as "running".

```python
if upcoming:
    sched = upcoming.get("scheduled_at") or ""
    status = upcoming.get("status", "")
    if sched and status == "running":
        try:
            start = datetime.fromisoformat(sched.replace("Z", "+00:00"))
            elapsed_h = (datetime.now(timezone.utc) - start).total_seconds() / 3600
            if elapsed_h > 4:  # BO5 max ~4h
                logger.warning("SKIP stale match: started %.1fh ago", elapsed_h)
                return None
        except (ValueError, TypeError):
            pass
```

### Part B: ESPN Overhaul (1 file: sports_data.py)

#### B1. Complete league slug mapping

Replace hardcoded `_SPORT_LEAGUES` with comprehensive mapping from ESPN API docs.

**Soccer (50+ leagues):**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/soccer.md
"epl": ("soccer", "eng.1", "EPL"),
"eng2": ("soccer", "eng.2", "Championship"),
"lal": ("soccer", "esp.1", "La Liga"),
"esp2": ("soccer", "esp.2", "La Liga 2"),
"bun": ("soccer", "ger.1", "Bundesliga"),
"ger2": ("soccer", "ger.2", "2. Bundesliga"),
"ser": ("soccer", "ita.1", "Serie A"),
"ita2": ("soccer", "ita.2", "Serie B"),
"lig": ("soccer", "fra.1", "Ligue 1"),
"fra2": ("soccer", "fra.2", "Ligue 2"),
"mls": ("soccer", "usa.1", "MLS"),
"nwsl": ("soccer", "usa.nwsl", "NWSL"),
"tur": ("soccer", "tur.1", "Super Lig"),
"ned": ("soccer", "ned.1", "Eredivisie"),
"ned2": ("soccer", "ned.2", "Eerste Divisie"),
"por": ("soccer", "por.1", "Primeira Liga"),
"bel": ("soccer", "bel.1", "Pro League"),
"aut": ("soccer", "aut.1", "Bundesliga AT"),
"gre": ("soccer", "gre.1", "Super League"),
"den": ("soccer", "den.1", "Superliga"),
"nor": ("soccer", "nor.1", "Eliteserien"),
"swe": ("soccer", "swe.1", "Allsvenskan"),
"arg": ("soccer", "arg.1", "Liga Profesional"),
"bra": ("soccer", "bra.1", "Brasileirao"),
"mex": ("soccer", "mex.1", "Liga MX"),
"jpn": ("soccer", "jpn.1", "J1 League"),
"chn": ("soccer", "chn.1", "CSL"),
"ind": ("soccer", "ind.1", "ISL"),
"aus": ("soccer", "aus.1", "A-League"),
"rsa": ("soccer", "rsa.1", "PSL"),
"nga": ("soccer", "nga.1", "NPFL"),
# Cups & international
"ucl": ("soccer", "uefa.champions", "Champions League"),
"uel": ("soccer", "uefa.europa", "Europa League"),
"uecl": ("soccer", "uefa.europa.conf", "Conference League"),
"wcup": ("soccer", "fifa.world", "World Cup"),
"euro": ("soccer", "uefa.euro", "Euro"),
"copa": ("soccer", "conmebol.libertadores", "Libertadores"),
"suda": ("soccer", "conmebol.sudamericana", "Sudamericana"),
"cona": ("soccer", "conmebol.america", "Copa America"),
"gold": ("soccer", "concacaf.gold", "Gold Cup"),
"frien": ("soccer", "fifa.friendly", "Friendlies"),
"facup": ("soccer", "eng.fa", "FA Cup"),
"copdr": ("soccer", "esp.copa_del_rey", "Copa del Rey"),
"dfbp": ("soccer", "ger.dfb_pokal", "DFB Pokal"),
"copit": ("soccer", "ita.coppa_italia", "Coppa Italia"),
"coudf": ("soccer", "fra.coupe_de_france", "Coupe de France"),
```

**Basketball (9 leagues):**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/basketball.md
"nba": ("basketball", "nba", "NBA"),
"wnba": ("basketball", "wnba", "WNBA"),
"cbb": ("basketball", "mens-college-basketball", "CBB"),
"cwbb": ("basketball", "womens-college-basketball", "WCBB"),
"gleague": ("basketball", "nba-development", "G-League"),
"fiba": ("basketball", "fiba", "FIBA"),
"nbl": ("basketball", "nbl", "NBL Australia"),
```

**Hockey (6 leagues):**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/hockey.md
"nhl": ("hockey", "nhl", "NHL"),
"nchm": ("hockey", "mens-college-hockey", "NCAA Hockey"),
"nchw": ("hockey", "womens-college-hockey", "NCAA W Hockey"),
```

**Football (5 leagues):**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/football.md
"nfl": ("football", "nfl", "NFL"),
"cfb": ("football", "college-football", "CFB"),
"cfl": ("football", "cfl", "CFL"),
"ufl": ("football", "ufl", "UFL"),
"xfl": ("football", "xfl", "XFL"),
```

**Baseball (10 leagues):**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/baseball.md
"mlb": ("baseball", "mlb", "MLB"),
"cbase": ("baseball", "college-baseball", "College Baseball"),
"wbc": ("baseball", "world-baseball-classic", "WBC"),
```

**MMA (key organizations):**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/mma.md
"ufc": ("mma", "ufc", "UFC"),
"bellator": ("mma", "bellator", "Bellator"),
"pfl": ("mma", "pfl", "PFL"),
```

**Tennis:**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/tennis.md
"atp": ("tennis", "atp", "ATP"),
"wta": ("tennis", "wta", "WTA"),
```

**Golf (9 leagues):**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/golf.md
"pga": ("golf", "pga", "PGA Tour"),
"lpga": ("golf", "lpga", "LPGA"),
"liv": ("golf", "liv", "LIV Golf"),
"dpw": ("golf", "eur", "DP World Tour"),
"champ": ("golf", "champions-tour", "Champions Tour"),
```

**Racing (5 leagues):**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/racing.md
"f1": ("racing", "f1", "Formula 1"),
"irl": ("racing", "irl", "IndyCar"),
"nascar": ("racing", "nascar-premier", "NASCAR Cup"),
```

**Rugby:**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/rugby.md
# Rugby uses numeric league IDs — discovery via ESPN search fallback
"rugby": ("rugby", None, "Rugby"),  # Dynamic discovery
```

**Australian Football:**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/australian_football.md
"afl": ("australian-football", "afl", "AFL"),
```

**Cricket:**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/cricket.md
# Cricket has a dedicated client (cricket_data.py) — ESPN cricket as fallback
"cric": ("cricket", None, "Cricket"),
```

**Lacrosse:**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/lacrosse.md
"nll": ("lacrosse", "nll", "NLL"),
"pll": ("lacrosse", "pll", "PLL"),
```

**Volleyball:**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/volleyball.md
"mcvb": ("volleyball", "mens-college-volleyball", "NCAA M Volleyball"),
"wcvb": ("volleyball", "womens-college-volleyball", "NCAA W Volleyball"),
```

**Field Hockey:**
```python
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/field_hockey.md
"cfhoc": ("field-hockey", "womens-college-field-hockey", "NCAA Field Hockey"),
```

#### B2. Fix tennis data fetching

Rewrite `_get_athlete_match_context()` for tennis to actually fetch match history.

ESPN tennis has NO dedicated athlete gamelog endpoint. Solution: use `scoreboard?dates=YYYYMMDD` to scan recent dates and extract player's completed matches.

**Endpoint (from tennis.md):**
```
GET https://site.api.espn.com/apis/site/v2/sports/tennis/{league}/scoreboard?dates={YYYYMMDD}
```

**Implementation:**
```python
def _get_tennis_match_history(self, league: str, player_name: str, days_back: int = 14) -> List[Dict]:
    """Scan recent scoreboard dates to build player match history."""
    matches = []
    today = datetime.now(timezone.utc).date()
    for i in range(days_back):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y%m%d")
        url = f"{ESPN_BASE}/tennis/{league}/scoreboard?dates={date_str}"
        data = self._get(url)
        if not data:
            continue
        for event in data.get("events", []):
            for comp in event.get("competitions", []):
                status = comp.get("status", {}).get("type", {})
                if not status.get("completed", False):
                    continue
                competitors = comp.get("competitors", [])
                if len(competitors) != 2:
                    continue
                # Check if our player is in this match
                player_comp = None
                opp_comp = None
                for c in competitors:
                    athlete = c.get("athlete", {})
                    name = athlete.get("displayName", "")
                    # Reuse match_team() from src/team_matcher.py
                    if match_team(name.lower(), player_name.lower())[0]:
                        player_comp = c
                    else:
                        opp_comp = c
                if player_comp and opp_comp:
                    won = player_comp.get("winner", False)
                    opp_name = opp_comp.get("athlete", {}).get("displayName", "Unknown")
                    # Extract set scores from linescores
                    score = _extract_tennis_score(player_comp, opp_comp)
                    matches.append({
                        "opponent": opp_name,
                        "won": won,
                        "score": score,
                        "tournament": event.get("name", ""),
                        "date": date.isoformat(),
                    })
    return matches
```

Then rewrite `_get_athlete_match_context()` to use this for tennis, building a context string with [W]/[L] markers that passes the thin data gate.

#### B3. Fix MMA data fetching

Same scoreboard-scan approach as tennis but with wider window (MMA fighters fight ~3-4x per year).

**Endpoint (from mma.md):**
```
GET https://site.api.espn.com/apis/site/v2/sports/mma/{league}/scoreboard?dates={YYYYMMDD}
```

Implementation: `_get_mma_fight_history(league, fighter_name, days_back=90)` — scans 90 days of scoreboard, finds completed bouts where fighter is a competitor, extracts win/loss/method/round. Builds context string with [W]/[L] markers identical to tennis format.

For fighter name matching, reuse `match_team()` from `src/team_matcher.py` (already handles fuzzy matching).

#### B4. Add sport-type routing for new sports

New sports (golf, racing, rugby, AFL, lacrosse, volleyball, field hockey) use **team-based** schedule endpoint where applicable:

**Endpoint pattern (from respective docs):**
```
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{id}/schedule
```

For individual sports (golf, racing), use scoreboard date scan similar to tennis.

**Sport type routing logic in `get_match_context()`:**
- `_TEAM_SPORTS` = basketball, hockey, football, baseball, soccer, rugby, australian-football, lacrosse, volleyball, field-hockey → use existing `_get_team_match_context()` with `teams/{id}/schedule`
- `_ATHLETE_SPORTS` = tennis, mma → use new scoreboard-scan functions
- `_EVENT_SPORTS` = golf, racing → use `scoreboard?dates=YYYYMMDD`, find event by tournament name or competitor, return recent results. Golf uses `leaderboard?tournamentId={id}` (from golf.md) for position/score data. Racing uses `scoreboard` for race results.

#### B5. Dynamic league detection

Current `detect_sport()` uses hardcoded keyword matching. Enhancement: if a market's `seriesSlug` from Gamma API directly matches an ESPN league slug, use it without keyword guessing.

Map common Gamma seriesSlug values to ESPN league slugs:
```python
_SERIES_TO_ESPN = {
    "la-liga-2": ("soccer", "esp.2"),
    "primeira-divisin-argentina": ("soccer", "arg.1"),
    "brazil-serie-b": ("soccer", "bra.2"),  # Need to add bra.2
    "womens-champions-league": ("soccer", "uefa.champions.w"),
    "fifa-friendly": ("soccer", "fifa.friendly"),
    "shl-2026": ("hockey", "shl"),  # Swedish Hockey League
    "khl-2026": ("hockey", "khl"),  # KHL - may not be in ESPN
    "snhl-2026": ("hockey", "snhl"),
    "indian-premier-league": ("cricket", "ipl"),
    "cba": ("basketball", "cba"),  # Chinese Basketball
    "cbl": ("basketball", "cbl"),
    "kbl": ("basketball", "kbl"),  # Korean Basketball
}
```

Note: Some Gamma tags (KHL, SHL, CBA, KBL) may not have ESPN endpoints. These will gracefully fall through to "no data" with reduced thin data threshold.

### Part C: Thin Data Threshold (entry_gate.py)

Current: hardcoded 5 for all sports.

Fix: Sport-aware dynamic threshold:

```python
_THIN_DATA_THRESHOLDS = {
    "tennis": 2,
    "mma": 2,
    "golf": 1,
    "racing": 1,
    "cricket": 3,
    "default": 3,  # Lowered from 5
}
```

After ESPN overhaul most sports will have 5+ results naturally. Lower thresholds are safety net for sparse-data sports.

## Files Changed

| File | Changes | Risk |
|------|---------|------|
| `src/entry_gate.py` | `_hours_to_start()`, ranking formula, thin data threshold | Low — isolated functions |
| `src/market_scanner.py` | Remove esports time filter exemption (~20 lines deleted) | Low — removing code |
| `src/esports_data.py` | Slug fix, remove tier filter, add stale guard | Low — isolated |
| `src/sports_data.py` | League slugs, tennis/MMA rewrite, new sport routing | Medium — most new code |

## What This Does NOT Change

- AI analysis prompt (unchanged)
- Risk management / position sizing (unchanged)
- Order execution (unchanged)
- Dashboard (unchanged)
- Config structure (unchanged)
- Models / MarketData fields (unchanged)

## Success Criteria

1. Tennis markets produce [W]/[L] match history from ESPN scoreboard
2. MMA markets produce fight history from ESPN scoreboard
3. Soccer markets for Süper Lig, Eredivisie, etc. produce team records
4. Esports matches that started >4h ago are skipped
5. Close matches (0-2h) appear in imminent bucket
6. Underdogs with high edge rank equally to favorites
7. Thin data rejection rate drops from 68% to <30%
8. No regressions in existing working sports (NBA, NFL, EPL, etc.)
