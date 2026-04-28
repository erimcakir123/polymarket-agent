# Polymarket Agent 2.0

Polymarket otonom trading botu — temiz mimari, sport-aware exit logic.

## Sport Coverage

- **NBA** (Basketball): Moneyline, Spread, Totals
- **NHL** (Ice Hockey): Moneyline, Puck Line, Totals — see below
- **NFL** (American Football): Moneyline, Spread, Totals
- **MLB** (Baseball): Moneyline
- **Soccer**: 1X2 (3-way)
- **Tennis**: Match Winner

## NHL (Ice Hockey)

- **Markets:** Moneyline, Puck Line (-1.5), Totals (Over/Under 5.5 + 6.5).
- **Math:** Skellam (puck line), Poisson (totals), 4198-game empirical lookup hybrid.
- **Special dynamics:**
  - SO resolution: winner +1 goal (counted in puck line + totals)
  - OT goal handling
  - Pulled-goalie effect captured in empirical tables (no separate modifier)
- **Build empirical tables:**
  ```bash
  python scripts/build_nhl_empirical_table.py        # moneyline (4198 maç)
  python scripts/build_nhl_puck_line_table.py        # puck line (1217 entry)
  python scripts/build_nhl_totals_table.py           # totals (2484 entry, 5.5+6.5)
  ```
- **Active in:** `config.yaml entry.active_sports: [icehockey_nhl]`
- **Gracefal degradation:** Tablolar yoksa Skellam/Poisson fallback otomatik.

## Documentation

- `CLAUDE.md` — Development assistant rules
- `ARCHITECTURE_GUARD.md` — Architecture rules and layering
- `DECISIONS.md` — Calibration values, rationale notes
- `PRD.md` — Product requirements (iron rules)
- `config.yaml` — All numeric configuration
