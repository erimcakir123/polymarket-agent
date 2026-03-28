# ESPN API Reference (from pseudo-r/Public-ESPN-API)

## Base URLs
- **Site API v2:** `https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/{resource}`
- **Core API v2:** `https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/{resource}`
- **Search:** `https://site.web.api.espn.com/apis/common/v3/search?query={q}&limit={n}`
- **Athlete Overview:** `https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}/overview`
- **CDN:** `https://cdn.espn.com/core/{sport}/{resource}?xhr=1`

## Sport-Specific Quirks

### Soccer
- Standings: `/apis/site/v2/` returns empty `{}` — use `/apis/v2/` instead
- seasontype param may return 0 events — try without it first
- Athlete stats via Site API partially limited

### Tennis
- Scoreboard uses tournament/groupings structure, NOT flat competitions
- Response: `events[].groupings[].competitions[].competitors[].athlete.displayName`
- No "team" concept — use athlete endpoints
- Injuries endpoint returns 500 (not supported)
- Rankings available at core v2: `/leagues/{league}/rankings`

### Cricket
- **Scoreboard returns 404** — use core API events endpoint instead
- League slugs: `icc.t20`, `ipl`, etc.

### MMA
- Injuries returns 500 (not supported)
- Standings not applicable
- Fighters use athletes endpoint, not teams

### All Sports
- Season types: 1=preseason, 2=regular, 3=postseason, 4=offseason

## Complete League Slugs

### Soccer (24+ leagues)
eng.1, eng.2, eng.3, eng.4, eng.5, eng.fa, eng.league_cup
esp.1, esp.2, esp.copa_del_rey
ger.1, ger.2, ger.dfb_pokal
ita.1, ita.2, ita.coppa_italia
fra.1, fra.2, fra.coupe_de_france
ned.1, por.1, bel.1, aut.1, gre.1, tur.1, den.1, nor.1, swe.1, sco.1
usa.1, usa.nwsl, mex.1
bra.1, bra.2, arg.1, col.1, chi.1
jpn.1, chn.1, ind.1, aus.1, ksa.1
uefa.champions, uefa.europa, uefa.europa.conf
conmebol.libertadores, conmebol.sudamericana
afc.champions

### Basketball
nba, wnba, nba-development, mens-college-basketball, womens-college-basketball, nbl, fiba

### Football
nfl, college-football, cfl, ufl

### Baseball
mlb, college-baseball, world-baseball-classic

### Hockey
nhl, mens-college-hockey, womens-college-hockey

### Tennis
atp, wta

### MMA
ufc, bellator, ksw, cage-warriors, lfa

### Cricket
(league slugs vary — icc.t20, ipl, etc.)

## Key Endpoints We Use

| What | Endpoint | Notes |
|------|----------|-------|
| Search | `site.web.api.espn.com/apis/common/v3/search` | Returns items[] |
| Scoreboard | `site.api.v2/.../scoreboard?dates=YYYYMMDD` | Tennis uses groupings |
| Team list | `site.api.v2/.../teams?limit=500` | |
| Team detail | `site.api.v2/.../teams/{id}` | |
| Team schedule | `site.api.v2/.../teams/{id}/schedule` | No seasontype for soccer |
| Standings | `site.api.espn.com/apis/v2/...` | NOT /apis/site/v2/ |
| Athlete overview | `common/v3/.../athletes/{id}/overview` | gamelog, stats, nextGame |
| Rankings | `core.api.v2/.../rankings` | Tennis/MMA/etc |
| Odds | `core.api.v2/.../events/{id}/competitions/{id}/odds` | Betting odds |
| Win prob | `core.api.v2/.../events/{id}/competitions/{id}/probabilities` | |

## Athlete Endpoints (for individual sports: tennis, mma, boxing)
- `/athletes/{id}/overview` — stats snapshot, news, next game
- `/athletes/{id}/gamelog` — game-by-game log (works for NBA/NFL/MLB, NOT soccer/tennis)
- `/athletes/{id}/splits` — home/away/opponent splits
- `/athletes/{id}/vsathlete/{opponentId}` — head-to-head stats
