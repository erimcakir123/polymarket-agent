# Tennis Prediction Lab — Sandbox

> **Sandbox environment** — totally isolated from main bot.
> Main bot stays in `Polymarket Agent 2.0/`, untouched.

## Quick Start

```bash
# 1. Download Sackmann ATP data (one-time + weekly refresh)
python scripts/download_sackmann.py

# 2. Build Glicko-2 ratings (~30-60 sec)
python scripts/build_tennis_ratings.py

# 3. Verify config + deps OK
python scripts/tennis_main.py

# 4. Start dashboard (port 5051)
python scripts/tennis_dashboard.py
# Open: http://127.0.0.1:5051
```

## Kill Switch (Zero Risk to Main Bot)

```bash
cd ../"Polymarket Agent 2.0"
taskkill /F /IM python.exe                # Stop tennis processes (or pkill on Linux)
git worktree remove ../tennis-lab --force # Remove worktree
git branch -D feature/tennis-lab          # Delete branch
```

Main bot is completely unaffected — different repo state, different processes, different port.

## Diagnose Commands

```bash
python scripts/diagnose.py --period 30d --group-by surface
python scripts/diagnose.py --period 7d --group-by tier
python scripts/diagnose.py --period 30d --group-by feature
python scripts/diagnose.py --trade <uuid>  # single trade detail
```

## Architecture

- **Sandbox isolation:** git worktree at `../tennis-lab`, branch `feature/tennis-lab`, port 5051
- **Data:** Sackmann ATP CSV (1968-present, MIT licensed) + TML backup
- **Ratings:** Glicko-2 with surface variants (clay/grass/hard) + serve/return separated
- **Math:** Klaassen-Magnus point-by-point formulas
- **Markets:** First Set Winner + Set Handicap −1.5 + Total Sets U 2.5
- **Confidence tiers:** A ($25) and B ($20), no C
- **Edge threshold:** ≥5%
- **Event guard:** Max 2 trades per match (top 2 |edge|)
- **Self-diagnostic:** Per-trade feature snapshot, `/diagnose` CLI

## Reference

- Spec: [`docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md`](docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md)
- Plan: [`docs/superpowers/plans/2026-05-19-tennis-prediction-lab.md`](docs/superpowers/plans/2026-05-19-tennis-prediction-lab.md)
